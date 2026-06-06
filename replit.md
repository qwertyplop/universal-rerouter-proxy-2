# Universal Rerouter

An open-source, zero-config AI proxy for JanitorAI / SillyTavern. Deploy to Vercel in one click — no environment variables needed. Configure everything through the built-in UI.

## Deploy to Vercel

1. Fork this repo on GitHub
2. Go to [vercel.com](https://vercel.com) → New Project → Import your fork
3. Click **Deploy** — no settings needed

## Project Structure

```
api/
  index.py        Flask proxy (Vercel serverless function)
public/
  index.html      Configuration UI (single-file, vanilla JS + Tailwind)
vercel.json       Vercel routing
requirements.txt  Python dependencies
```

## Stack

- Python 3 + Flask + flask-cors (Vercel serverless)
- Vanilla JS + Tailwind CSS CDN (no build step)
- No database — config encoded in generated URLs (base64)

## Proxy Endpoints

| Path | Use with |
|------|----------|
| `/janitorai?t=...&c=...` | JanitorAI custom API URL |
| `/sillytavern?t=...&c=...` | SillyTavern base URL |
| `/sillytavern/chat/completions` | SillyTavern full completions path |
| `/sillytavern/models` | SillyTavern model list |
| `/health` | Health check |

## URL Parameters

- `t` — base64url of the upstream API URL
- `c` — base64url of JSON config: `{"mode":"base"}` or `{"mode":"full","prepend_blocks":[...],"append_blocks":[...]}`

## Modes

- **Base** — pure proxy + CORS + region bypass, no body modification
- **Full** — everything in Base + prompt block injection (prepend/append system/user/assistant messages)

## User Preferences

_Populate as you build._
