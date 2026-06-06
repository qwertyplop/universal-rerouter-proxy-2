# Universal Rerouter

A zero-config AI proxy for JanitorAI and SillyTavern. Deploy to Vercel in one click — no environment variables required.

## What it does

- **CORS bypass** — removes browser CORS restrictions that block direct API calls from AI clients
- **Region bypass** — traffic routes through Vercel's global servers, bypassing geographic blocks
- **Prompt Manager** *(Full mode)* — inject custom system / user / assistant blocks into every request, built visually in the UI

## Deploy

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/YOUR_USERNAME/universal-rerouter)

Or manually:

1. Fork this repo
2. Go to [vercel.com](https://vercel.com) → New Project → Import your fork
3. Click **Deploy** — no settings needed

## Usage

1. Open your deployed Vercel URL in the browser
2. Paste your upstream API URL (e.g. `https://api.openai.com/v1/chat/completions`)
3. Choose **Base** (pure proxy) or **Full** (with prompt blocks)
4. Copy the generated URL and paste it into JanitorAI or SillyTavern as the custom API endpoint

## Modes

### Base
Pure proxy. The request body is forwarded unchanged. Only strips identity headers (Origin, Referer) and handles CORS.

### Full
Everything in Base, plus a **no-code Prompt Manager**:
- Add **Prepend blocks** — injected at the start of the messages array
- Add **Append blocks** — injected at the end (after the user's last message)
- Each block has a role (`system`, `user`, `assistant`) and custom content
- All config is encoded in the generated URL — no database needed

## How the URL encoding works

Settings are stored in your browser's localStorage and encoded into the proxy URL as base64 query parameters:

```
https://your-app.vercel.app/janitorai?t=<upstream_b64>&c=<config_b64>
```

- `t` — base64url of the upstream API URL
- `c` — base64url of a JSON config object (mode + prompt blocks)

No server-side state. Anyone can deploy this repo and use it immediately.

## Endpoints

| Path | Use with |
|------|----------|
| `/janitorai` | JanitorAI custom API URL |
| `/sillytavern` | SillyTavern base URL |
| `/sillytavern/chat/completions` | SillyTavern full completions path |
| `/sillytavern/models` | SillyTavern model list |
| `/health` | Health check |

## Tech stack

- Python (Flask) — Vercel serverless functions
- Vanilla JS + Tailwind CSS — configuration UI
- No database, no environment variables required
