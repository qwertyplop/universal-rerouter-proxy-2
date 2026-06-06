export function App() {
  return (
    <div className="min-h-screen font-mono" style={{ background: "#111218", color: "#f3f4f6" }}>

      {/* Header */}
      <header style={{ background: "#111218", borderBottom: "1px solid #2a2b38" }} className="px-6 py-4 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "#4c1d95" }}>
            <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="#a78bfa" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <div className="text-sm font-bold text-white tracking-wide">Universal Rerouter</div>
            <div className="text-xs" style={{ color: "#6b7280" }}>AI Proxy for JanitorAI / SillyTavern</div>
          </div>
        </div>
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs" style={{ background: "#14532d", color: "#86efac" }}>
          <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ background: "#4ade80" }}></span>
          Deployed
        </span>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8 space-y-5">

        {/* Upstream URL */}
        <section className="rounded-xl p-5 space-y-3" style={{ background: "#1a1b23", border: "1px solid #2a2b38" }}>
          <div className="text-xs uppercase tracking-widest" style={{ color: "#6b7280" }}>Upstream API URL</div>
          <div className="flex gap-2">
            <div className="flex-1 rounded-lg px-3 py-2.5 text-sm" style={{ background: "#0d0e14", border: "1px solid #2a2b38", color: "#9ca3af" }}>
              https://api.openai.com/v1/chat/completions
            </div>
            <button className="px-4 py-2.5 rounded-lg text-sm font-semibold text-white" style={{ background: "#7c3aed" }}>
              Save
            </button>
          </div>
          <div className="text-xs" style={{ color: "#4b5563" }}>
            The API endpoint requests will be forwarded to. Examples: <span style={{ color: "#a78bfa" }}>https://api.openai.com/v1/chat/completions</span>
          </div>
        </section>

        {/* Mode selector */}
        <section className="rounded-xl p-5 space-y-4" style={{ background: "#1a1b23", border: "1px solid #2a2b38" }}>
          <div className="text-xs uppercase tracking-widest" style={{ color: "#6b7280" }}>Proxy Mode</div>
          <div className="grid grid-cols-2 gap-3">
            <button className="rounded-lg py-3 px-4 text-sm font-semibold text-white" style={{ background: "#7c3aed" }}>
              ⚡ Base
            </button>
            <button className="rounded-lg py-3 px-4 text-sm font-semibold" style={{ background: "transparent", border: "1px solid #2a2b38", color: "#9ca3af" }}>
              🧠 Full
            </button>
          </div>
          <div className="text-xs space-y-1" style={{ color: "#6b7280" }}>
            <p>🔒 <strong style={{ color: "#d1d5db" }}>CORS bypass</strong> — removes Origin/Referer headers so browser restrictions don't apply.</p>
            <p>🌍 <strong style={{ color: "#d1d5db" }}>Region bypass</strong> — traffic goes through the Vercel server, not the user's location.</p>
            <p>🔁 <strong style={{ color: "#d1d5db" }}>Pure forwarding</strong> — the request body is not modified in any way.</p>
          </div>
        </section>

        {/* Generated URLs */}
        <section className="rounded-xl p-5 space-y-4" style={{ background: "#1a1b23", border: "1px solid #2a2b38" }}>
          <div className="text-xs uppercase tracking-widest" style={{ color: "#6b7280" }}>Generated Proxy URLs</div>
          <div className="text-xs" style={{ color: "#4b5563" }}>Copy the URL for your AI client and paste it as the custom API endpoint.</div>

          <div className="space-y-3">
            <div>
              <div className="text-xs mb-1.5" style={{ color: "#4b5563" }}>JanitorAI (Custom API URL field)</div>
              <div className="flex gap-2 items-center">
                <code className="flex-1 text-xs px-3 py-2.5 rounded-lg truncate" style={{ background: "#0d0e14", border: "1px solid #2a2b38", color: "#a78bfa" }}>
                  https://my-proxy.vercel.app/janitorai?t=aHR0cHM6Ly...&c=eyJtb2Rl...
                </code>
                <button className="px-3 py-2.5 rounded-lg text-xs font-semibold text-white" style={{ background: "#2a2b38", minWidth: 64 }}>Copy</button>
              </div>
            </div>

            <div>
              <div className="text-xs mb-1.5" style={{ color: "#4b5563" }}>SillyTavern (API Base URL)</div>
              <div className="flex gap-2 items-center">
                <code className="flex-1 text-xs px-3 py-2.5 rounded-lg truncate" style={{ background: "#0d0e14", border: "1px solid #2a2b38", color: "#a78bfa" }}>
                  https://my-proxy.vercel.app/sillytavern?t=aHR0cHM6Ly...&c=eyJtb2Rl...
                </code>
                <button className="px-3 py-2.5 rounded-lg text-xs font-semibold text-white" style={{ background: "#2a2b38", minWidth: 64 }}>Copy</button>
              </div>
            </div>
          </div>

          <details>
            <summary className="text-xs cursor-pointer" style={{ color: "#4b5563" }}>Setup guide</summary>
            <div className="mt-3 space-y-3 text-xs" style={{ color: "#6b7280" }}>
              <div>
                <div className="font-semibold mb-1" style={{ color: "#d1d5db" }}>JanitorAI</div>
                <ol className="list-decimal list-inside space-y-1">
                  <li>Open JanitorAI → Settings → API</li>
                  <li>Select <strong>OpenAI</strong> as provider</li>
                  <li>Paste the URL above into <strong>Custom API URL</strong></li>
                </ol>
              </div>
              <div>
                <div className="font-semibold mb-1" style={{ color: "#d1d5db" }}>SillyTavern</div>
                <ol className="list-decimal list-inside space-y-1">
                  <li>Open ST → API Connections</li>
                  <li>Choose <strong>OpenAI Compatible</strong></li>
                  <li>Paste into <strong>Custom Endpoint (Base URL)</strong></li>
                </ol>
              </div>
            </div>
          </details>
        </section>

        <footer className="text-center text-xs pt-2 pb-4 space-y-1" style={{ color: "#374151" }}>
          <p>Settings are stored locally in your browser.</p>
          <p>The upstream URL is encoded in the generated link — no server-side config needed.</p>
        </footer>
      </main>
    </div>
  );
}
