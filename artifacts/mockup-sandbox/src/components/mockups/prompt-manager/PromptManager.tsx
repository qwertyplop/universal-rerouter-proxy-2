import { useState } from "react";

type Role = "system" | "user" | "assistant";
type Position = "prepend" | "append";

interface Block {
  id: number;
  position: Position;
  role: Role;
  content: string;
}

const ROLE_COLOR: Record<Role, { bg: string; border: string; label: string }> = {
  system:    { bg: "#1a1f2e", border: "#3b4a6b", label: "#93c5fd" },
  user:      { bg: "#1a2e1a", border: "#3b6b3b", label: "#86efac" },
  assistant: { bg: "#2e1a2e", border: "#6b3b6b", label: "#d8b4fe" },
};

const SAMPLE_CONVERSATION = [
  { role: "system" as Role,    content: "You are a helpful assistant." },
  { role: "user" as Role,      content: "Tell me a short story." },
  { role: "assistant" as Role, content: "Once upon a time..." },
  { role: "user" as Role,      content: "[latest message from JanitorAI]" },
];

export function PromptManager() {
  const [blocks, setBlocks] = useState<Block[]>([
    { id: 1, position: "prepend", role: "system",    content: "Always respond in a formal tone." },
    { id: 2, position: "append",  role: "assistant", content: "((OOC: Sure, let's proceed!))" },
  ]);
  const [tab, setTab] = useState<"editor" | "preview">("editor");

  function addBlock(position: Position) {
    setBlocks(b => [...b, { id: Date.now(), position, role: "system", content: "" }]);
  }

  function removeBlock(id: number) {
    setBlocks(b => b.filter(x => x.id !== id));
  }

  function updateBlock(id: number, field: keyof Block, value: string) {
    setBlocks(b => b.map(x => x.id === id ? { ...x, [field]: value } : x));
  }

  function moveBlock(id: number, dir: -1 | 1) {
    setBlocks(prev => {
      const idx = prev.findIndex(x => x.id === id);
      if (idx < 0) return prev;
      const next = idx + dir;
      if (next < 0 || next >= prev.length) return prev;
      const arr = [...prev];
      [arr[idx], arr[next]] = [arr[next], arr[idx]];
      return arr;
    });
  }

  const prepend = blocks.filter(b => b.position === "prepend");
  const append  = blocks.filter(b => b.position === "append");

  const finalMessages = [
    ...prepend.map(b => ({ role: b.role, content: b.content || "(empty)" })),
    ...SAMPLE_CONVERSATION,
    ...append.map(b => ({ role: b.role, content: b.content || "(empty)" })),
  ];

  return (
    <div className="min-h-screen font-mono text-sm" style={{ background: "#111218", color: "#e5e7eb" }}>
      {/* Header */}
      <div className="px-5 py-4 flex items-center justify-between sticky top-0 z-10" style={{ background: "#111218", borderBottom: "1px solid #2a2b38" }}>
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center text-base" style={{ background: "#3b1f5e" }}>🧠</div>
          <span className="font-bold text-white text-sm tracking-wide">Prompt Manager</span>
          <span className="text-xs px-2 py-0.5 rounded font-semibold" style={{ background: "#2a2b38", color: "#9ca3af" }}>Full mode</span>
        </div>
        <div className="flex rounded-lg overflow-hidden" style={{ border: "1px solid #2a2b38" }}>
          {(["editor", "preview"] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className="px-4 py-1.5 text-xs font-semibold capitalize transition-all"
              style={{ background: tab === t ? "#7c3aed" : "transparent", color: tab === t ? "#fff" : "#9ca3af" }}>
              {t === "editor" ? "✏️ Editor" : "👁 Preview"}
            </button>
          ))}
        </div>
      </div>

      {tab === "editor" ? (
        <div className="p-5 space-y-4 max-w-2xl mx-auto">

          {/* Flow diagram */}
          <div className="rounded-xl p-4 space-y-1 text-xs" style={{ background: "#1a1b23", border: "1px solid #2a2b38" }}>
            <div className="text-gray-500 uppercase tracking-widest mb-2">Message flow (sent to upstream)</div>
            <FlowRow label={`↑ Prepend (${prepend.length})`} color="#1e3a5f" textColor="#93c5fd" />
            <FlowRow label="💬 Conversation from JanitorAI/ST" color="#1c1c24" textColor="#6b7280" italic />
            <FlowRow label={`↓ Append (${append.length})`} color="#3b1f5e" textColor="#c4b5fd" />
          </div>

          {/* Prepend section */}
          <Section
            title="Prepend blocks"
            subtitle="Injected before the conversation"
            accent="#93c5fd"
            bgAccent="#1e3a5f"
            onAdd={() => addBlock("prepend")}
            addLabel="+ Add prepend"
          >
            {prepend.length === 0 ? (
              <EmptySlot label="No prepend blocks" />
            ) : (
              prepend.map((b, i) => (
                <BlockCard key={b.id} block={b} index={i} total={prepend.length}
                  allBlocks={blocks}
                  onChange={(f, v) => updateBlock(b.id, f, v)}
                  onRemove={() => removeBlock(b.id)}
                  onMove={dir => moveBlock(b.id, dir)}
                />
              ))
            )}
          </Section>

          {/* Divider */}
          <div className="flex items-center gap-3 text-xs" style={{ color: "#4b5563" }}>
            <div className="flex-1 h-px" style={{ background: "#2a2b38" }} />
            <span>💬 Conversation (untouched)</span>
            <div className="flex-1 h-px" style={{ background: "#2a2b38" }} />
          </div>

          {/* Append section */}
          <Section
            title="Append blocks"
            subtitle="Injected after the last user message"
            accent="#c4b5fd"
            bgAccent="#3b1f5e"
            onAdd={() => addBlock("append")}
            addLabel="+ Add append"
          >
            {append.length === 0 ? (
              <EmptySlot label="No append blocks" />
            ) : (
              append.map((b, i) => (
                <BlockCard key={b.id} block={b} index={i} total={append.length}
                  allBlocks={blocks}
                  onChange={(f, v) => updateBlock(b.id, f, v)}
                  onRemove={() => removeBlock(b.id)}
                  onMove={dir => moveBlock(b.id, dir)}
                />
              ))
            )}
          </Section>
        </div>
      ) : (
        /* Preview tab */
        <div className="p-5 space-y-3 max-w-2xl mx-auto">
          <div className="text-xs uppercase tracking-widest mb-1" style={{ color: "#6b7280" }}>
            Final messages array sent to upstream ({finalMessages.length} messages)
          </div>
          {finalMessages.map((m, i) => {
            const c = ROLE_COLOR[m.role];
            const isInjected =
              i < prepend.length ||
              i >= prepend.length + SAMPLE_CONVERSATION.length;
            return (
              <div key={i} className="rounded-xl p-3.5 space-y-1.5"
                style={{ background: c.bg, border: `1px solid ${c.border}`, opacity: isInjected ? 1 : 0.55 }}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-widest" style={{ color: c.label }}>{m.role}</span>
                  {isInjected ? (
                    <span className="text-xs px-2 py-0.5 rounded font-semibold" style={{ background: "#2a2b38", color: "#a78bfa" }}>injected</span>
                  ) : (
                    <span className="text-xs" style={{ color: "#4b5563" }}>from client</span>
                  )}
                </div>
                <p className="text-xs leading-relaxed whitespace-pre-wrap" style={{ color: "#d1d5db" }}>{m.content}</p>
              </div>
            );
          })}
          <div className="text-xs pt-2 text-center" style={{ color: "#4b5563" }}>
            Dimmed = original messages from JanitorAI/SillyTavern · Bright = your injected blocks
          </div>
        </div>
      )}
    </div>
  );
}

function FlowRow({ label, color, textColor, italic }: { label: string; color: string; textColor: string; italic?: boolean }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold" style={{ background: color, color: textColor, fontStyle: italic ? "italic" : "normal" }}>
      <span>{label}</span>
    </div>
  );
}

function Section({ title, subtitle, accent, bgAccent, onAdd, addLabel, children }: {
  title: string; subtitle: string; accent: string; bgAccent: string;
  onAdd: () => void; addLabel: string; children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl p-4 space-y-3" style={{ background: "#1a1b23", border: "1px solid #2a2b38" }}>
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs font-bold" style={{ color: accent }}>{title}</div>
          <div className="text-xs" style={{ color: "#6b7280" }}>{subtitle}</div>
        </div>
        <button onClick={onAdd}
          className="text-xs px-3 py-1.5 rounded-lg font-semibold transition-all hover:opacity-80"
          style={{ background: bgAccent, color: accent }}>
          {addLabel}
        </button>
      </div>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function EmptySlot({ label }: { label: string }) {
  return (
    <div className="rounded-lg py-5 text-center text-xs" style={{ border: "1px dashed #2a2b38", color: "#4b5563" }}>
      {label}
    </div>
  );
}

function BlockCard({ block, index, total, allBlocks, onChange, onRemove, onMove }: {
  block: Block; index: number; total: number; allBlocks: Block[];
  onChange: (field: keyof Block, value: string) => void;
  onRemove: () => void;
  onMove: (dir: -1 | 1) => void;
}) {
  const globalIdx = allBlocks.findIndex(b => b.id === block.id);
  const c = ROLE_COLOR[block.role];

  return (
    <div className="rounded-xl p-3.5 space-y-2.5"
      style={{ background: c.bg, border: `1px solid ${c.border}` }}>
      <div className="flex items-center justify-between gap-2">
        <select
          value={block.role}
          onChange={e => onChange("role", e.target.value)}
          className="text-xs px-2 py-1 rounded-lg font-semibold outline-none"
          style={{ background: "#111218", border: `1px solid ${c.border}`, color: c.label }}>
          <option value="system">system</option>
          <option value="user">user</option>
          <option value="assistant">assistant</option>
        </select>
        <div className="flex items-center gap-1">
          <button onClick={() => onMove(-1)} disabled={index === 0}
            className="w-6 h-6 rounded text-xs flex items-center justify-center disabled:opacity-20 transition-colors hover:text-white"
            style={{ background: "#111218", color: "#6b7280" }}>▲</button>
          <button onClick={() => onMove(1)} disabled={index === total - 1}
            className="w-6 h-6 rounded text-xs flex items-center justify-center disabled:opacity-20 transition-colors hover:text-white"
            style={{ background: "#111218", color: "#6b7280" }}>▼</button>
          <button onClick={onRemove}
            className="w-6 h-6 rounded text-xs flex items-center justify-center transition-colors"
            style={{ background: "#111218", color: "#ef4444" }}>✕</button>
        </div>
      </div>
      <textarea
        rows={3}
        value={block.content}
        placeholder="Message content..."
        onChange={e => onChange("content", e.target.value)}
        className="w-full rounded-lg px-3 py-2 text-xs outline-none placeholder-gray-600"
        style={{ background: "#111218", border: `1px solid ${c.border}`, color: "#e5e7eb", resize: "vertical" }}
      />
    </div>
  );
}
