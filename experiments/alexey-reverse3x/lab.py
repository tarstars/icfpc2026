"""Triple-extraction reverse lab. Build/check/trace helpers."""
import json, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"src"))
from littleman.sim import Machine
from littleman.judge import judge_case, judge_problem
from littleman.server_compat import find_shared_walls, judge_problem as sc_judge
PROB = json.loads((ROOT/"data/small/problems/reverse-a-list.json").read_text())

def rounds(lists):
    return [{"in":[str(len(v))]+[str(x) for x in v],
             "out":[str(x) for x in reversed(v)]} for v in lists]

def check(text, name="cand", verbose=True):
    lines=[l for l in text.split("\n")]
    cells=[(r,c) for r,l in enumerate(lines) for c,ch in enumerate(l) if ch!=" "]
    w=max(c for _,c in cells)+1; h=max(r for r,_ in cells)+1
    try:
        rep=judge_problem(text,PROB)
        s=rep.score if rep.cases_passed==8 else float('inf')
        if verbose: print(f"[{name}] {w}x{h} fp {max(w,h)**2} cases {rep.cases_passed}/8 score {s}")
        return max(w,h)**2, rep.cases_passed, s
    except Exception as e:
        if verbose: print(f"[{name}] PARSE/RUN FAIL: {e}")
        return max(w,h)**2, 0, float('inf')

def trace(text, vals, max_ticks=400):
    """Run one round, print output collected + final man states."""
    m=Machine.parse(text)
    from littleman.judge import RoundController
    ctl=RoundController(rounds([vals]))
    res=m.run(max_ticks=max_ticks, controller=ctl)
    print(f"n={len(vals)} status={res.status} ticks={res.ticks}", end=" ")
    print("men:", [(man.r,man.c,man.A,man.B,man.BP,man.direction) for man in m.men if not man.halted][:3])
    return res

def resolve_all(text):
    m=Machine.parse(text)
    class F: pass
    out={}
    for r,line in enumerate(text.split("\n")):
        for c,ch in enumerate(line):
            if ch not in "srRUq": continue
            room=next((rm for rm in m.rooms if rm.contains_interior(r,c)),None)
            if room is None: continue
            f=F(); f.r,f.c,f.room=r,c,room
            p=(m._nearest_outgoing(f) if ch in "sS" else m._nearest_incoming(f))
            out[(r,c,ch)]=(p.cells[0],p.cells[-1]) if p else None
    return out

def stress(text, n=150):
    random.seed(9); bad=[]
    for _ in range(n):
        lists=[[random.randint(-10**6,10**6) for _ in range(random.randint(1,16))]
               for _ in range(random.randint(1,3))]
        r=judge_case(text, rounds(lists))
        if not r.passed: bad.append((lists,r.reason)); break
    return bad
