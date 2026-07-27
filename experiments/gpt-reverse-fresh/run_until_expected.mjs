import { readFileSync } from "node:fs";
import { bootEngine, parseResp } from "../../claude/official-sim/engine.mjs";

const req = JSON.parse(readFileSync(0, "utf8"));
const rows = readFileSync(req.programPath, "utf8").replace(/\n+$/, "").split("\n");
const encode = (value) =>
  Array.isArray(value) && value.every(Array.isArray)
    ? value.map((round) => round.join(" ")).join(" / ")
    : value.join(" ");

const eng = await bootEngine();
const sess = eng.newSession();
let state = parseResp(
  eng.load(sess, rows, encode(req.input), encode(req.expected), ""),
);
const needed = Array.isArray(req.expected[0])
  ? req.expected.reduce((sum, round) => sum + round.length, 0)
  : req.expected.length;
while (
  (state.output?.length ?? 0) < needed &&
  !state.halted &&
  state.step < req.maxTicks
) {
  state = parseResp(eng.step(sess));
}
console.log(
  JSON.stringify({
    ticks: state.step,
    output: state.output,
    reason: state.reason ?? null,
    fatal: state.fatal ?? null,
    inputRead: state.inputRead,
    inputReleased: state.inputReleased,
    runners: state.entities.runners.length,
  }),
);
eng.closeSession(sess);
