import { readFileSync } from "node:fs";
import { bootEngine, parseResp } from "../../claude/official-sim/engine.mjs";

const request = JSON.parse(readFileSync(0, "utf8"));
const rows = readFileSync(request.programPath, "utf8")
  .replace(/\n+$/, "")
  .split("\n");
const encode = (rounds) => rounds.map((round) => round.join(" ")).join(" / ");
const engine = await bootEngine();
const results = [];

for (const testCase of request.cases) {
  const session = engine.newSession();
  let state = parseResp(
    engine.load(
      session,
      rows,
      encode(testCase.input),
      encode(testCase.expected),
      "",
    ),
  );
  const expected = testCase.expected.flat().map(String);
  while (
    (state.output?.length ?? 0) < expected.length &&
    !state.halted &&
    state.step < request.maxTicks
  ) {
    state = parseResp(engine.step(session));
  }
  results.push({
    name: testCase.name,
    ticks: state.step,
    good: JSON.stringify(state.output) === JSON.stringify(expected),
    output: state.output,
    expected,
    reason: state.reason ?? null,
    fatal: state.fatal ?? null,
    inputRead: state.inputRead,
    inputReleased: state.inputReleased,
    runners: state.entities.runners.length,
  });
  engine.closeSession(session);
}

console.log(JSON.stringify(results));
