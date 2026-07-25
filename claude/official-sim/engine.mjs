// Boot the organizers' Go-WASM littleman engine headlessly under Node v18.
// Engine files: vendor/wasm_exec.js + vendor/littleman.wasm (downloaded from
// icfpcontest2026.com). API discovered from embed-BPxB0RIR.js (see NOTES.md).
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const VENDOR = join(dirname(fileURLToPath(import.meta.url)), "vendor");

if (!globalThis.crypto) {
  const { webcrypto } = await import("node:crypto");
  globalThis.crypto = webcrypto;
}

let bootPromise = null;

export function bootEngine() {
  return (bootPromise ||= (async () => {
    if (globalThis.littlemanWasm) return globalThis.littlemanWasm;
    const shim = readFileSync(join(VENDOR, "wasm_exec.js"), "utf8");
    (0, eval)(shim); // defines globalThis.Go
    const go = new globalThis.Go();
    const buf = readFileSync(join(VENDOR, "littleman.wasm"));
    const { instance } = await WebAssembly.instantiate(buf, go.importObject);
    go.run(instance); // resident program; do not await
    const t0 = Date.now();
    while (!globalThis.littlemanWasm) {
      if (Date.now() - t0 > 10_000)
        throw new Error("littlemanWasm global never appeared");
      await new Promise((r) => setTimeout(r, 5));
    }
    return globalThis.littlemanWasm;
  })());
}

// Engine responses are JSON strings; type:"error" carries message + pos.
export function parseResp(s) {
  const t = JSON.parse(s);
  if (t.type === "error") {
    const e = new Error(t.message || "wasm error");
    e.pos = t.pos ?? null;
    e.isEngineError = true;
    throw e;
  }
  return t;
}
