import { bootEngine, parseResp } from "./engine.mjs";

const eng = await bootEngine();
console.log("api:", Object.keys(eng).sort().join(","));
console.log("validOps:", JSON.stringify(eng.validOps()));
console.log("structural:", JSON.stringify(eng.structuralGlyphs()));
const s = eng.newSession();
const rows = ["+----+", "|@ > |", "| H  |", "+----+"];
const st = parseResp(eng.load(s, rows, "", "", ""));
console.log("load keys:", Object.keys(st).sort().join(","));
console.log("runners:", JSON.stringify(st.entities?.runners ?? st.runners));
let cur = st;
for (let i = 0; i < 8 && !cur.halted; i++) {
  cur = parseResp(eng.step(s));
  const r = (cur.entities?.runners ?? []).map((m) => [m.pos, m.dir, m.halted]);
  console.log("step", cur.step, JSON.stringify(r), cur.halted, cur.reason);
}
eng.closeSession(s);
process.exit(0);
