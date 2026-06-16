"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

export function RunButton() {
  const [state, setState] = useState<"idle" | "running" | "done" | "error">("idle");
  const [message, setMessage] = useState<string>("");

  async function handleRun() {
    setState("running");
    setMessage("");
    try {
      const res = await fetch("/api/run", { method: "POST" });
      const data = await res.json();
      if (data.ok) {
        setState("done");
        setMessage("Scraper concluído com sucesso.");
        setTimeout(() => window.location.reload(), 1500);
      } else {
        setState("error");
        setMessage(data.error || "Erro desconhecido.");
      }
    } catch (e) {
      setState("error");
      setMessage(String(e));
    }
  }

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={handleRun}
        disabled={state === "running"}
        className={cn(
          "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
          state === "running"
            ? "bg-gray-700 text-gray-400 cursor-not-allowed"
            : "bg-blue-600 hover:bg-blue-500 text-white"
        )}
      >
        {state === "running" ? "Rodando..." : "Rodar agora"}
      </button>
      <a
        href="/api/export"
        className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-800 hover:bg-gray-700 text-gray-300 transition-colors"
      >
        Exportar
      </a>
      {message && (
        <span className={cn("text-sm", state === "error" ? "text-red-400" : "text-green-400")}>
          {message}
        </span>
      )}
    </div>
  );
}
