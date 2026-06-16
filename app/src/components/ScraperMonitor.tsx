"use client";

import { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";

type Status = "idle" | "running" | "done" | "error";
type Level = "info" | "warn" | "error" | "sys";

interface LogLine {
  text: string;
  level: Level;
}

// Strip "2026-06-16 00:33:45,931 " prefix
const TIMESTAMP_RE = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+ /;

function parseLine(raw: string): LogLine | null {
  const text = raw.replace(TIMESTAMP_RE, "").trim();
  if (!text) return null;
  if (text.includes("[ERROR]")) return { text, level: "error" };
  if (text.includes("[WARNING]")) return { text, level: "warn" };
  return { text, level: "info" };
}

const LEVEL_COLOR: Record<Level, string> = {
  info: "text-green-400/80",
  warn: "text-yellow",
  error: "text-red-400",
  sys: "text-yellow font-bold",
};

export function ScraperMonitor() {
  const [status, setStatus] = useState<Status>("idle");
  const [lines, setLines] = useState<LogLine[]>([]);
  const [open, setOpen] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [lines, open]);

  async function handleRun() {
    setStatus("running");
    setLines([]);
    setOpen(true);

    try {
      const res = await fetch("/api/run", { method: "POST" });
      if (!res.body) throw new Error("sem resposta do servidor");

      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buf += dec.decode(value, { stream: true });
        const parts = buf.split("\n");
        buf = parts.pop() ?? "";

        for (const part of parts) {
          const trimmed = part.trim();
          if (!trimmed) continue;

          if (trimmed.startsWith("__DONE__:")) {
            const code = parseInt(trimmed.slice(9));
            const ok = code === 0;
            setStatus(ok ? "done" : "error");
            setLines((prev) => [
              ...prev,
              {
                text: ok ? "✓ Concluído com sucesso" : `✕ Processo encerrou com código ${code}`,
                level: "sys",
              },
            ]);
            if (ok) setTimeout(() => window.location.reload(), 2000);
            continue;
          }

          if (trimmed.startsWith("__ERROR__:")) {
            setStatus("error");
            setLines((prev) => [
              ...prev,
              { text: `✕ ${trimmed.slice(9)}`, level: "error" },
            ]);
            continue;
          }

          const parsed = parseLine(trimmed);
          if (parsed) setLines((prev) => [...prev, parsed]);
        }
      }
    } catch (err) {
      setStatus("error");
      setLines((prev) => [
        ...prev,
        { text: `✕ Erro: ${String(err)}`, level: "error" },
      ]);
    }
  }

  const hasLog = lines.length > 0;

  return (
    <div className="relative flex flex-col items-end gap-0 shrink-0">
      {/* Button bar */}
      <div className="flex items-stretch border-2 border-ink shadow-brutal-sm">
        <button
          onClick={handleRun}
          disabled={status === "running"}
          className={cn(
            "px-5 py-2 text-xs font-satoshi font-bold uppercase tracking-[0.18em] border-r-2 border-ink transition-colors",
            status === "running" && "bg-surface text-muted cursor-not-allowed",
            status === "done" && "bg-accent text-yellow",
            status === "error" && "bg-red-700 text-cream",
            status === "idle" && "bg-ink text-cream hover:bg-accent hover:text-yellow"
          )}
        >
          {status === "running"
            ? "rodando…"
            : status === "done"
            ? "✓ ok"
            : status === "error"
            ? "✕ erro"
            : "rodar agora"}
        </button>

        {hasLog && (
          <button
            onClick={() => setOpen((v) => !v)}
            className="border-r-2 border-ink px-4 py-2 text-xs font-satoshi font-bold uppercase tracking-[0.18em] bg-ink text-yellow hover:bg-accent transition-colors"
          >
            {open ? "ocultar" : "log"}
          </button>
        )}

        <a
          href="/api/export"
          className="px-5 py-2 text-xs font-satoshi font-bold uppercase tracking-[0.18em] bg-paper text-ink hover:bg-surface transition-colors"
        >
          exportar
        </a>
      </div>

      {/* Log panel — drops down absolutely below the button */}
      {open && hasLog && (
        <div className="absolute top-full right-0 mt-1 z-50 w-[min(600px,90vw)] border-2 border-ink bg-ink shadow-brutal-lg">
          {/* header bar */}
          <div className="border-b border-ink/30 px-4 py-2 flex items-center justify-between">
            <div className="flex items-center gap-2">
              {status === "running" && (
                <span className="inline-block w-1.5 h-1.5 bg-yellow animate-pulse" />
              )}
              <span className="font-satoshi text-xs font-bold uppercase tracking-[0.18em] text-yellow">
                {status === "running"
                  ? "rodando"
                  : status === "done"
                  ? "concluído"
                  : "erro"}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-courier text-xs text-muted/60">{lines.length} linhas</span>
              <button
                onClick={() => setOpen(false)}
                className="font-satoshi text-xs text-muted hover:text-cream transition-colors"
              >
                ✕
              </button>
            </div>
          </div>

          {/* log lines */}
          <div
            ref={logRef}
            className="h-72 overflow-y-auto px-4 py-3 space-y-px"
            style={{ scrollbarWidth: "thin", scrollbarColor: "#2A1C71 transparent" }}
          >
            {lines.map((line, i) => (
              <p
                key={i}
                className={cn(
                  "font-courier text-xs leading-[1.65] whitespace-pre-wrap break-all",
                  LEVEL_COLOR[line.level]
                )}
              >
                {line.text}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
