import { spawn } from "child_process";
import path from "path";

export const runtime = "nodejs";

export async function POST() {
  const scraperDir =
    process.env.SCRAPER_DIR ?? path.join(process.cwd(), "../scraper");

  const enc = new TextEncoder();

  const stream = new ReadableStream({
    start(controller) {
      const proc = spawn("uv", ["run", "python", "run.py"], {
        cwd: scraperDir,
        env: { ...process.env },
      });

      let done = false;
      let outBuf = "";
      let errBuf = "";

      function send(text: string) {
        if (done || !text.trim()) return;
        try { controller.enqueue(enc.encode(text + "\n")); } catch {}
      }

      function flushBuf(buf: string, chunk: string): string {
        const lines = (buf + chunk).split("\n");
        const remaining = lines.pop() ?? "";
        lines.forEach(send);
        return remaining;
      }

      proc.stdout.on("data", (chunk: Buffer) => {
        outBuf = flushBuf(outBuf, chunk.toString());
      });

      proc.stderr.on("data", (chunk: Buffer) => {
        errBuf = flushBuf(errBuf, chunk.toString());
      });

      proc.on("close", (code: number) => {
        if (done) return;
        done = true;
        send(outBuf);
        send(errBuf);
        send(`__DONE__:${code ?? 1}`);
        controller.close();
      });

      proc.on("error", (err: Error) => {
        if (done) return;
        done = true;
        send(`__ERROR__:${err.message}`);
        controller.close();
      });
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
