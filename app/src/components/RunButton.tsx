"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

export function RunButton() {
  const [state, setState] = useState<"idle" | "running" | "done" | "error">("idle");
  const [msg, setMsg] = useState<string>("");

  async function handleRun() {
    setState("running");
    setMsg("");
    try {
      const res = await fetch("/api/run", { method: "POST" });
      const data = await res.json();
      if (data.ok) {
        setState("done");
        setMsg("concluído");
        setTimeout(() => window.location.reload(), 1800);
      } else {
        setState("error");
        setMsg("falhou");
      }
    } catch {
      setState("error");
      setMsg("falhou");
    }
  }

  return (
    <div className="flex items-stretch border-2 border-ink shadow-brutal-sm">
      <button
        onClick={handleRun}
        disabled={state === "running"}
        className={cn(
          "px-5 py-2 text-xs font-satoshi font-bold uppercase tracking-[0.18em]",
          "border-r-2 border-ink transition-colors",
          state === "running" && "bg-surface text-muted cursor-not-allowed",
          state === "done" && "bg-ink text-cream",
          state === "error" && "bg-accent text-cream",
          state === "idle" && "bg-ink text-cream hover:bg-muted"
        )}
      >
        {state === "running"
          ? "rodando (~5min)..."
          : state === "done"
          ? "✓ ok"
          : state === "error"
          ? "✕ erro"
          : "rodar agora"}
      </button>

      <a
        href="/api/export"
        className="px-5 py-2 text-xs font-satoshi font-bold uppercase tracking-[0.18em] bg-paper text-ink hover:bg-surface transition-colors border-r-2 border-ink"
      >
        exportar
      </a>

      {msg && (
        <span
          className={cn(
            "px-4 py-2 text-xs font-courier",
            state === "error" ? "bg-accent text-cream" : "bg-surface text-muted"
          )}
        >
          {msg}
        </span>
      )}
    </div>
  );
}
