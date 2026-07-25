// CLI harness over the organizers' WASM littleman engine.
// stdin JSON: { program | programPath, input, expected, frames, maxTicks,
//               trace }  — input/expected: string "1 2 / 3", flat [ints]
//               (one round) or [[ints],...] (rounds).
// stdout JSON: { status, ticks, output, reason, fatal, menTimeline?,
//                runners, inputReleased, inputRead, outputSettled, displays }
import { readFileSync } from "node:fs";
import { bootEngine, parseResp } from "./engine.mjs";

function encodeRounds(v) {
  if (v == null) return "";
  if (typeof v === "string") return v;
  if (Array.isArray(v) && v.length > 0 && v.every(Array.isArray))
    return v.map((r) => r.join(" ")).join(" / ");
  return v.join(" ");
}

const req = JSON.parse(readFileSync(0, "utf8"));
const text = req.program ?? readFileSync(req.programPath, "utf8");
const rows = text.replace(/\n+$/, "").split("\n");
const maxTicks = req.maxTicks ?? 20000;
const trace = !!req.trace;

const eng = await bootEngine();
const sess = eng.newSession();
let st;
try {
  st = parseResp(
    eng.load(
      sess,
      rows,
      encodeRounds(req.input),
      encodeRounds(req.expected),
      req.frames?.length ? JSON.stringify(req.frames) : ""
    )
  );
} catch (e) {
  console.log(
    JSON.stringify({ status: "load-error", message: e.message, pos: e.pos ?? null })
  );
  process.exit(0);
}

const menTimeline = [];
const record = (s) => {
  const rn = s.entities?.runners ?? [];
  menTimeline.push({
    t: s.step,
    men: rn.length,
    alive: rn.filter((m) => !m.halted).length,
  });
};
if (trace) record(st);
let stalled = false;
let prev = st.step;
while (!st.halted && st.step < maxTicks) {
  st = trace
    ? parseResp(eng.step(sess))
    : parseResp(eng.stepN(sess, Math.min(5000, maxTicks - st.step), false));
  if (trace) record(st);
  if (st.step === prev) {
    stalled = true;
    break;
  }
  prev = st.step;
  if (req.stopOnSettle && st.outputSettled) break;
}
eng.closeSession(sess);

const res = {
  status: st.halted ? (st.reason === "done" ? "done" : "error") : stalled ? "stalled" : "tick-cap",
  ticks: st.step,
  reason: st.reason ?? null,
  fatal: st.fatal ?? null,
  output: st.output ?? [],
  inputReleased: st.inputReleased ?? 0,
  inputRead: st.inputRead ?? 0,
  outputSettled: !!st.outputSettled,
  runners: (st.entities?.runners ?? []).map((m) => ({
    id: m.id, pos: m.pos, dir: m.dir, halted: m.halted,
    a: m.a, b: m.b, backpack: m.backpack,
  })),
  displays: (st.entities?.displays ?? []).map((d) => ({
    w: d.w, h: d.h, front: d.front, frames: d.frames, cursor: d.cursor,
  })),
};
if (trace) res.menTimeline = menTimeline;
console.log(JSON.stringify(res));
process.exit(0);
