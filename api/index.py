import json
import os
import base64
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime


PUBLIC_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'public'))

MIME_TYPES = {
    '.html': 'text/html',
    '.css': 'text/css',
    '.js': 'application/javascript',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.woff2': 'font/woff2',
    '.woff': 'font/woff',
    '.ttf': 'font/ttf',
}

STATUS_TEXT = {
    200: 'OK', 201: 'Created', 204: 'No Content',
    301: 'Moved Permanently', 302: 'Found', 304: 'Not Modified',
    400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden', 404: 'Not Found',
    405: 'Method Not Allowed', 500: 'Internal Server Error',
    502: 'Bad Gateway', 503: 'Service Unavailable',
}


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
    decoded = decode_b64(c)
    if decoded:
        try:
            return json.loads(decoded)
        except Exception:
            pass
    return {"mode": "base"}


def proxy_request(path, query_string, headers_in, method, body):
    query = urllib.parse.parse_qs(query_string)

    target_url = get_target_url(query)
    if not target_url:
        return {
            'status': 400,
            'headers': {'content-type': 'application/json'},
            'body': json.dumps({
                'error': 'No target URL set.',
                'hint': 'Open the proxy UI, enter your upstream URL, and copy the generated endpoint.'
            }).encode('utf-8')
        }

    models_mode = path in ('/sillytavern/models',)

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

    try:
        ts = datetime.now().isoformat()
        print(f'[{ts}] proxy -> {target_url} mode={mode}', flush=True)

        req = urllib.request.Request(
            url=target_url,
            data=json.dumps(json_body).encode('utf-8') if json_body is not None else data_body,
            headers=clean_headers,
            method=method or 'GET'
        )

        if json_body is not None:
            req.add_header('Content-Type', 'application/json')

        with urllib.request.urlopen(req, timeout=60) as resp:
            resp_headers = {}
            for k, v in resp.getheaders():
                if k.lower() not in {'content-encoding', 'content-length', 'transfer-encoding', 'connection'}:
                    resp_headers[k] = v

            return {
                'status': resp.status,
                'headers': resp_headers,
                'body': resp.read()
            }

    except urllib.error.HTTPError as e:
        return {
            'status': e.code,
            'headers': {'content-type': 'application/json'},
            'body': json.dumps({'error': f'Proxy error: {str(e)}'}).encode('utf-8')
        }
    except Exception as e:
        print(f'[ERROR] {e}', flush=True)
        return {
            'status': 500,
            'headers': {'content-type': 'application/json'},
            'body': json.dumps({'error': f'Proxy error: {str(e)}'}).encode('utf-8')
        }


def serve_static(path):
    if path == '/' or path == '':
        path = '/index.html'

    file_path = os.path.normpath(os.path.join(PUBLIC_DIR, path.lstrip('/')))
    if not file_path.startswith(PUBLIC_DIR):
        return {
            'status': 403,
            'headers': {'content-type': 'text/plain'},
            'body': b'Forbidden'
        }

    if not os.path.isfile(file_path):
        return {
            'status': 404,
            'headers': {'content-type': 'text/plain'},
            'body': b'Not Found'
        }

    ext = os.path.splitext(file_path)[1].lower()
    content_type = MIME_TYPES.get(ext, 'application/octet-stream')

    with open(file_path, 'rb') as f:
        body_bytes = f.read()

    return {
        'status': 200,
        'headers': {'content-type': content_type},
        'body': body_bytes
    }


def _wsgi_headers(environ):
    headers = {}
    for key, value in environ.items():
        if key.startswith('HTTP_'):
            name = key[5:].replace('_', '-').title()
            # title() lowercases everything after the first letter of each part, fix that
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


def _dispatch(method, path, query_string, headers_in, body):
    if method == 'OPTIONS':
        return {
            'status': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS, PATCH',
                'Access-Control-Allow-Headers': '*',
            },
            'body': b''
        }

    api_prefixes = ('/janitorai', '/sillytavern', '/health')
    is_api = path in api_prefixes or path.startswith(tuple(p + '/' for p in api_prefixes))

    if is_api:
        body_str = body.decode('utf-8', errors='replace') if isinstance(body, (bytes, bytearray)) else body
        return proxy_request(path, query_string, headers_in, method, body_str)

    return serve_static(path)


def app(environ, start_response):
    try:
        method = environ.get('REQUEST_METHOD', 'GET')
        path = environ.get('PATH_INFO', '/')
        query_string = environ.get('QUERY_STRING', '') or ''
        headers_in = _wsgi_headers(environ)
        body = _read_body(environ)

        result = _dispatch(method, path, query_string, headers_in, body)

        result_headers = dict(result.get('headers') or {})
        result_headers.setdefault('Access-Control-Allow-Origin', '*')
        result_headers.setdefault('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS, PATCH')
        result_headers.setdefault('Access-Control-Allow-Headers', '*')

        status_code = int(result.get('status', 200))
        status_text = STATUS_TEXT.get(status_code, 'OK')
        status = f"{status_code} {status_text}"

        headers_list = [(k, str(v)) for k, v in result_headers.items()]

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
