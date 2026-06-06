from flask import Flask, request, jsonify, Response, stream_with_context, send_from_directory
from flask_cors import CORS
import json
import requests
import base64
import os
from datetime import datetime

app = Flask(__name__, static_folder=None)
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), '..', 'public')
CORS(app, origins="*", allow_headers="*", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])

# ============================================================================
# Helpers
# ============================================================================

def decode_b64(s):
    if not s:
        return None
    try:
        s = s + '=' * (4 - len(s) % 4)
        return base64.urlsafe_b64decode(s).decode('utf-8')
    except Exception:
        return None

def get_target_url():
    t = request.args.get('t')
    if t:
        decoded = decode_b64(t)
        if decoded:
            return decoded.strip()
    return None

def get_config():
    c = request.args.get('c')
    if c:
        decoded = decode_b64(c)
        if decoded:
            try:
                return json.loads(decoded)
            except Exception:
                pass
    return {"mode": "base"}

def proxy_request(source_label="proxy", models_mode=False):
    target_url = get_target_url()

    if not target_url:
        return jsonify({
            "error": "No target URL set.",
            "hint": "Open the proxy UI, enter your upstream URL, and copy the generated endpoint."
        }), 400

    if models_mode:
        target_url = target_url.replace("/chat/completions", "/models")

    config = get_config()
    mode = config.get("mode", "base")

    # Strip identity/origin headers
    excluded = {
        'content-length', 'host', 'origin', 'referer', 'cookie',
        'user-agent', 'x-forwarded-for', 'x-forwarded-host', 'accept-encoding'
    }
    clean_headers = {k: v for k, v in request.headers.items() if k.lower() not in excluded}
    clean_headers["User-Agent"] = "Mozilla/5.0 (compatible; UniversalRerouter/2.0)"

    # Body
    json_body = None
    data_body = None

    if request.is_json:
        try:
            json_body = request.get_json(force=True)

            # Full mode: apply prompt blocks
            if mode == "full" and isinstance(json_body, dict) and "messages" in json_body:
                messages = list(json_body["messages"])

                for block in reversed(config.get("prepend_blocks", [])):
                    messages.insert(0, {"role": block["role"], "content": block["content"]})

                for block in config.get("append_blocks", []):
                    messages.append({"role": block["role"], "content": block["content"]})

                json_body["messages"] = messages

        except Exception as e:
            print(f"[WARN] Body parse error: {e}")
            json_body = None
            data_body = request.get_data()
    else:
        data_body = request.get_data()

    # Forward
    try:
        ts = datetime.now().isoformat()
        print(f"[{ts}] {source_label} -> {target_url} mode={mode}")

        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=clean_headers,
            json=json_body,
            data=data_body,
            stream=True,
            timeout=60,
        )

        excluded_resp = {'content-encoding', 'content-length', 'transfer-encoding', 'connection'}
        resp_headers = [(k, v) for k, v in resp.raw.headers.items() if k.lower() not in excluded_resp]

        def generate():
            for chunk in resp.iter_content(chunk_size=4096):
                if chunk:
                    yield chunk

        return Response(stream_with_context(generate()), resp.status_code, resp_headers)

    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"error": f"Proxy error: {str(e)}"}), 500


# ============================================================================
# Routes
# ============================================================================

@app.route("/janitorai", methods=["POST", "GET", "OPTIONS"])
def janitor_proxy():
    if request.method == "OPTIONS":
        return "", 200
    return proxy_request("janitorai")


@app.route("/sillytavern", methods=["POST", "GET", "OPTIONS"])
def sillytavern_proxy():
    if request.method == "OPTIONS":
        return "", 200
    return proxy_request("sillytavern")


@app.route("/sillytavern/chat/completions", methods=["POST", "GET", "OPTIONS"])
def sillytavern_chat_proxy():
    if request.method == "OPTIONS":
        return "", 200
    return proxy_request("sillytavern")


@app.route("/sillytavern/models", methods=["GET", "OPTIONS"])
def sillytavern_models_proxy():
    if request.method == "OPTIONS":
        return "", 200
    return proxy_request("sillytavern_models", models_mode=True)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "platform": "vercel", "version": "2.0"}), 200


@app.route("/", methods=["GET"])
def index():
    return send_from_directory(os.path.abspath(PUBLIC_DIR), "index.html")


@app.route("/<path:filename>", methods=["GET"])
def static_files(filename):
    return send_from_directory(os.path.abspath(PUBLIC_DIR), filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=False)
