import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";

export async function POST(request: NextRequest) {
  const scraperDir = process.env.SCRAPER_DIR;
  if (!scraperDir) {
    return NextResponse.json(
      { error: "SCRAPER_DIR env var not set" },
      { status: 500 }
    );
  }

  const runPy = path.join(scraperDir, "run.py");

  return new Promise<NextResponse>((resolve) => {
    const proc = spawn("uv", ["run", "python", runPy], {
      cwd: scraperDir,
      env: { ...process.env },
    });

    const stdout: string[] = [];
    const stderr: string[] = [];

    proc.stdout.on("data", (chunk: Buffer) => stdout.push(chunk.toString()));
    proc.stderr.on("data", (chunk: Buffer) => stderr.push(chunk.toString()));

    proc.on("close", (code: number) => {
      if (code === 0) {
        resolve(
          NextResponse.json({
            ok: true,
            output: stdout.join(""),
          })
        );
      } else {
        resolve(
          NextResponse.json(
            {
              ok: false,
              error: stderr.join("") || stdout.join(""),
              exitCode: code,
            },
            { status: 500 }
          )
        );
      }
    });

    proc.on("error", (err: Error) => {
      resolve(
        NextResponse.json(
          { ok: false, error: err.message },
          { status: 500 }
        )
      );
    });
  });
}
