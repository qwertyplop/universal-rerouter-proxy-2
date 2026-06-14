import json
import base64
import http.client
import os
import threading
import time
import urllib.request
import urllib.error
import urllib.parse
from collections import deque
from datetime import datetime


STATUS_TEXT = {
    200: 'OK', 201: 'Created', 204: 'No Content',
    400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden', 404: 'Not Found',
    405: 'Method Not Allowed', 500: 'Internal Server Error',
    502: 'Bad Gateway', 503: 'Service Unavailable',
}


# ============================================================
# In-memory log buffer (per warm Vercel function instance)
# ============================================================
LOG_MAX = int(os.environ.get('PROXY_LOG_MAX', '200'))
LOG_BODY_MAX = 32 * 1024  # 32KB cap on each logged body
LOG_BUFFER = deque(maxlen=LOG_MAX)
LOG_LOCK = threading.Lock()
LOG_COUNTER = [0]


def _next_log_id():
    with LOG_LOCK:
        LOG_COUNTER[0] += 1
        return f"{int(time.time() * 1000)}-{LOG_COUNTER[0]}"


def record_log(entry):
    with LOG_LOCK:
        LOG_BUFFER.append(entry)


def get_logs():
    with LOG_LOCK:
        return list(LOG_BUFFER)


def clear_logs():
    with LOG_LOCK:
        LOG_BUFFER.clear()


def _should_log(query, config=None):
    # 1. URL param must explicitly request logging
    if query.get('log', [''])[0].lower() not in ('1', 'true', 'yes', 'on'):
        return False
    # 2. Config can disable logging even if &log=1 is present in URL
    if config is not None and config.get('logsEnabled') is False:
        return False
    return True


def _truncate_for_log(s, cap=LOG_BODY_MAX):
    if s is None:
        return None, False
    if isinstance(s, (bytes, bytearray)):
        s = bytes(s).decode('utf-8', errors='replace')
    s = str(s)
    if len(s) > cap:
        return s[:cap] + f"\n... [truncated, {len(s) - cap} bytes omitted]", True
    return s, False


def _safe_json_parse(s):
    if s is None:
        return None
    if isinstance(s, (bytes, bytearray)):
        s = bytes(s).decode('utf-8', errors='replace')
    try:
        return json.loads(s)
    except Exception:
        return None


def _new_log_state(method, path, query_string, is_stream, clean_headers, body_bytes, json_body):
    return {
        'id': _next_log_id(),
        'timestamp': datetime.now().isoformat(),
        'method': (method or 'GET').upper(),
        'path': path,
        'query': query_string,
        'isStream': is_stream,
        'requestHeaders': dict(clean_headers),
        'requestBody': None,
        'requestBodyRaw': None,
        'requestBodyTruncated': False,
        'responseHeaders': {},
        'responseBody': None,
        'responseBodyRaw': None,
        'responseBodyTruncated': False,
        'status': None,
        'durationMs': None,
        'error': None,
        'bytesReceived': 0,
        'chunksCount': 0,
        'startedAt': time.time(),
        'remoteAddr': None,
    }


def _finalize_log(log_state, err=None):
    if log_state is None:
        return
    if log_state.get('durationMs') is None:
        log_state['durationMs'] = int((time.time() - log_state['startedAt']) * 1000)
    if err is not None and not log_state.get('error'):
        log_state['error'] = str(err)
    try:
        record_log(log_state)
    except Exception:
        pass


# ============================================================
# /api/logs endpoint
# ============================================================
def _handle_logs_endpoint(method, query, headers_in):
    if method == 'GET':
        logs = get_logs()
        body = json.dumps({'logs': logs, 'count': len(logs), 'max': LOG_MAX}).encode('utf-8')
        return {
            'isStream': False,
            'status': 200,
            'headers': {'content-type': 'application/json'},
            'body': body,
        }
    if method == 'DELETE':
        clear_logs()
        return {
            'isStream': False,
            'status': 200,
            'headers': {'content-type': 'application/json'},
            'body': json.dumps({'cleared': True, 'count': 0}).encode('utf-8'),
        }
    if method == 'OPTIONS':
        return {
            'isStream': False,
            'status': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': '*',
            },
            'body': b'',
        }
    return {
        'isStream': False,
        'status': 405,
        'headers': {'content-type': 'application/json'},
        'body': json.dumps({'error': 'Method not allowed'}).encode('utf-8'),
    }


# ============================================================
# Streaming proxy (uses http.client directly for chunked reads)
# ============================================================
def _streaming_proxy(target_url, method, body_bytes, clean_headers, log_state):
    parsed = urllib.parse.urlparse(target_url)
    conn = None
    try:
        if parsed.scheme == 'https':
            conn = http.client.HTTPSConnection(
                parsed.hostname, parsed.port or 443, timeout=60
            )
        else:
            conn = http.client.HTTPConnection(
                parsed.hostname, parsed.port or 80, timeout=60
            )

        path_q = parsed.path or '/'
        if parsed.query:
            path_q += '?' + parsed.query

        conn.request(method or 'POST', path_q, body=body_bytes, headers=clean_headers)
        resp = conn.getresponse()

        resp_headers = {}
        for k, v in resp.getheaders():
            if k.lower() not in {'content-encoding', 'content-length', 'transfer-encoding', 'connection'}:
                resp_headers[k] = v
        if 'Content-Type' not in resp_headers:
            resp_headers['Content-Type'] = 'text/event-stream'
        resp_headers['Cache-Control'] = 'no-cache'
        resp_headers['X-Accel-Buffering'] = 'no'

        if log_state is not None:
            log_state['status'] = resp.status
            log_state['responseHeaders'] = dict(resp_headers)

        def iter_chunks():
            chunks_count = 0
            bytes_received = 0
            collected = []
            collected_bytes = 0
            body_truncated = False
            try:
                while True:
                    try:
                        chunk = resp.read(4096)
                    except Exception as e:
                        if log_state is not None and not log_state.get('error'):
                            log_state['error'] = f"Stream read error: {e}"
                        break
                    if not chunk:
                        break
                    chunks_count += 1
                    bytes_received += len(chunk)
                    if log_state is not None and collected_bytes < LOG_BODY_MAX:
                        remaining = LOG_BODY_MAX - collected_bytes
                        if len(chunk) <= remaining:
                            collected.append(chunk)
                            collected_bytes += len(chunk)
                        else:
                            collected.append(chunk[:remaining])
                            collected_bytes = LOG_BODY_MAX
                            body_truncated = True
                    yield chunk
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
                if log_state is not None:
                    log_state['chunksCount'] = chunks_count
                    log_state['bytesReceived'] = bytes_received
                    if collected_bytes > 0 or chunks_count > 0:
                        raw = b''.join(collected).decode('utf-8', errors='replace')
                        log_state['responseBodyRaw'] = raw
                        log_state['responseBody'] = _safe_json_parse(raw)
                        if body_truncated:
                            log_state['responseBodyTruncated'] = True

        return {
            'isStream': True,
            'status': resp.status,
            'headers': resp_headers,
            'body_iter': iter_chunks(),
        }
    except Exception:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        raise


# ============================================================
# Base64 / target URL helpers
# ============================================================
def decode_b64(s):
    if not s:
        return None
    try:
        s = s + '=' * (4 - len(s) % 4)
        return base64.urlsafe_b64decode(s).decode('utf-8')
    except Exception:
        return None


def get_target_url(query):
    t = query.get('t', [''])[0]
    if not t:
        return None
    decoded = decode_b64(t)
    if decoded:
        return decoded.strip()
    return None


def get_config(query):
    c = query.get('c', [''])[0]
    if not c:
        return {"mode": "base"}
    for suffix in ('/v1/models', '/v1/chat/completions', '/models', '/chat/completions'):
        if c.endswith(suffix):
            c = c[:-len(suffix)]
            break
    decoded = decode_b64(c)
    if decoded:
        try:
            cfg = json.loads(decoded)
            if isinstance(cfg, dict):
                cfg.setdefault('mode', 'base')
                cfg.setdefault('logsEnabled', True)
                return cfg
        except Exception:
            pass
    return {"mode": "base"}


# ============================================================
# Main proxy dispatcher
# ============================================================
def proxy_request(path, query_string, headers_in, method, body):
    query = urllib.parse.parse_qs(query_string)

    if path == '/api/logs':
        return _handle_logs_endpoint(method, query, headers_in)

    target_url = get_target_url(query)
    if not target_url:
        return {
            'isStream': False,
            'status': 400,
            'headers': {'content-type': 'application/json'},
            'body': json.dumps({
                'error': 'No target URL set.',
                'hint': 'Open the proxy UI, enter your upstream URL, and copy the generated endpoint.'
            }).encode('utf-8')
        }

    models_mode = urllib.parse.unquote(query_string).lower().endswith('/models')
    if models_mode:
        target_url = target_url.replace('/chat/completions', '/models')

    config = get_config(query)
    mode = config.get('mode', 'base')

    excluded = {
        'content-length', 'host', 'origin', 'referer', 'cookie',
        'user-agent', 'x-forwarded-for', 'x-forwarded-host', 'accept-encoding'
    }
    clean_headers = {k: v for k, v in headers_in.items() if k.lower() not in excluded}
    clean_headers['User-Agent'] = 'Mozilla/5.0 (compatible; UniversalRerouter/2.0)'

    json_body = None
    data_body = None
    body_bytes = None

    if body:
        try:
            json_body = json.loads(body)
            if mode == 'full' and isinstance(json_body, dict) and 'messages' in json_body:
                messages = list(json_body['messages'])
                for block in reversed(config.get('prepend_blocks', [])):
                    messages.insert(0, {'role': block['role'], 'content': block['content']})
                for block in config.get('append_blocks', []):
                    messages.append({'role': block['role'], 'content': block['content']})
                json_body['messages'] = messages
        except Exception:
            data_body = body.encode('utf-8') if isinstance(body, str) else body

    if json_body is not None:
        body_bytes = json.dumps(json_body).encode('utf-8')
    elif isinstance(data_body, (bytes, bytearray)):
        body_bytes = bytes(data_body)
    elif isinstance(data_body, str):
        body_bytes = data_body.encode('utf-8')
    elif isinstance(body, str):
        body_bytes = body.encode('utf-8')
    elif isinstance(body, (bytes, bytearray)):
        body_bytes = bytes(body)

    is_stream = False
    if json_body and isinstance(json_body, dict) and json_body.get('stream'):
        is_stream = True
    if query.get('stream', [''])[0].lower() in ('1', 'true', 'yes', 'on'):
        is_stream = True

    log_requested = _should_log(query, config)
    log_state = _new_log_state(method, path, query_string, is_stream, clean_headers, body_bytes, json_body) if log_requested else None
    if log_state is not None:
        if json_body is not None:
            log_state['requestBody'] = json_body
        elif body_bytes is not None:
            text, truncated = _truncate_for_log(body_bytes)
            log_state['requestBodyRaw'] = text
            log_state['requestBody'] = _safe_json_parse(text)
            log_state['requestBodyTruncated'] = truncated

    try:
        ts = datetime.now().isoformat()
        print(f'[{ts}] proxy -> {target_url} mode={mode} stream={is_stream} log={log_requested}', flush=True)

        if is_stream:
            try:
                result = _streaming_proxy(target_url, method, body_bytes, clean_headers, log_state)
                if log_state is not None:
                    original_iter = result['body_iter']
                    def _wrap_logged(it):
                        try:
                            for chunk in it:
                                yield chunk
                        finally:
                            _finalize_log(log_state)
                    result['body_iter'] = _wrap_logged(original_iter)
                return result
            except Exception as e:
                if log_state is not None:
                    log_state['status'] = 502
                    _finalize_log(log_state, err=e)
                return {
                    'isStream': False,
                    'status': 502,
                    'headers': {'content-type': 'application/json'},
                    'body': json.dumps({'error': f'Stream proxy error: {str(e)}'}).encode('utf-8'),
                }

        req = urllib.request.Request(
            url=target_url,
            data=body_bytes,
            headers=clean_headers,
            method=method or 'GET'
        )
        if json_body is not None:
            req.add_header('Content-Type', 'application/json')

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                resp_headers = {}
                for k, v in resp.getheaders():
                    if k.lower() not in {'content-encoding', 'content-length', 'transfer-encoding', 'connection'}:
                        resp_headers[k] = v

                if log_state is not None:
                    log_state['status'] = resp.status
                    log_state['responseHeaders'] = dict(resp_headers)

                body_out = resp.read()

                if log_state is not None:
                    log_state['bytesReceived'] = len(body_out)
                    text, truncated = _truncate_for_log(body_out)
                    log_state['responseBodyRaw'] = text
                    log_state['responseBody'] = _safe_json_parse(text)
                    log_state['responseBodyTruncated'] = truncated
                    _finalize_log(log_state)

                return {
                    'isStream': False,
                    'status': resp.status,
                    'headers': resp_headers,
                    'body': body_out,
                }

        except urllib.error.HTTPError as e:
            err_text = b''
            try:
                err_text = e.read() if hasattr(e, 'read') else b''
            except Exception:
                pass
            if log_state is not None:
                log_state['status'] = e.code
                log_state['error'] = f"HTTP {e.code}: {err_text[:200]!r}" if err_text else f"HTTP {e.code}"
                if err_text:
                    text, _ = _truncate_for_log(err_text)
                    log_state['responseBodyRaw'] = text
                _finalize_log(log_state)
            return {
                'isStream': False,
                'status': e.code,
                'headers': {'content-type': 'application/json'},
                'body': json.dumps({'error': f'Proxy error: {str(e)}'}).encode('utf-8'),
            }
        except Exception as e:
            print(f'[ERROR] {e}', flush=True)
            if log_state is not None:
                _finalize_log(log_state, err=e)
            return {
                'isStream': False,
                'status': 500,
                'headers': {'content-type': 'application/json'},
                'body': json.dumps({'error': f'Proxy error: {str(e)}'}).encode('utf-8'),
            }

    except Exception as e:
        if log_state is not None:
            _finalize_log(log_state, err=e)
        raise


# ============================================================
# WSGI helpers
# ============================================================
def _wsgi_headers(environ):
    headers = {}
    for key, value in environ.items():
        if key.startswith('HTTP_'):
            name = key[5:].replace('_', '-').title()
            parts = name.split('-')
            name = '-'.join(p[:1].upper() + p[1:] for p in parts)
            headers[name] = value
    if 'CONTENT_TYPE' in environ:
        headers['Content-Type'] = environ['CONTENT_TYPE']
    if 'CONTENT_LENGTH' in environ:
        headers['Content-Length'] = environ['CONTENT_LENGTH']
    return headers


def _read_body(environ):
    try:
        length = int(environ.get('CONTENT_LENGTH') or 0)
    except (TypeError, ValueError):
        length = 0
    if length <= 0:
        return None
    try:
        return environ['wsgi.input'].read(length)
    except Exception:
        return None


# ============================================================
# WSGI entrypoint
# ============================================================
def app(environ, start_response):
    try:
        method = environ.get('REQUEST_METHOD', 'GET')
        path = environ.get('PATH_INFO', '/')
        query_string = environ.get('QUERY_STRING', '') or ''
        headers_in = _wsgi_headers(environ)
        body = _read_body(environ)

        if method == 'OPTIONS':
            result = {
                'status': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS, PATCH',
                    'Access-Control-Allow-Headers': '*',
                },
                'body': b''
            }
        else:
            body_str = body.decode('utf-8', errors='replace') if isinstance(body, (bytes, bytearray)) else body
            result = proxy_request(path, query_string, headers_in, method, body_str)

        result_headers = dict(result.get('headers') or {})
        result_headers.setdefault('Access-Control-Allow-Origin', '*')
        result_headers.setdefault('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS, PATCH')
        result_headers.setdefault('Access-Control-Allow-Headers', '*')

        status_code = int(result.get('status', 200))
        status_text = STATUS_TEXT.get(status_code, 'OK')
        status = f"{status_code} {status_text}"
        headers_list = [(k, str(v)) for k, v in result_headers.items()]

        # Streaming response: return iterator directly
        if result.get('isStream') and 'body_iter' in result:
            start_response(status, headers_list)
            return result['body_iter']

        # Non-streaming response
        body_out = result.get('body') or b''
        if isinstance(body_out, str):
            body_out = body_out.encode('utf-8')
        if not isinstance(body_out, (bytes, bytearray)):
            body_out = b''

        start_response(status, headers_list)
        return [bytes(body_out)]
    except Exception as e:
        try:
            print(f'[FATAL] {e}', flush=True)
        except Exception:
            pass
        try:
            start_response('500 Internal Server Error', [('Content-Type', 'application/json')])
        except Exception:
            pass
        return [json.dumps({'error': f'Internal error: {str(e)}'}).encode('utf-8')]
