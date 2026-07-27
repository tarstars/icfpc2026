"""Focused release gate for the tagged-loop Sudoku candidate."""
from __future__ import annotations
import hashlib, importlib.util, json, random
from pathlib import Path
from littleman.judge import judge_case, judge_problem
from littleman.server_compat import validate_layout
from littleman.sim import Machine

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ART=HERE/'sudoku_tagged_loop.man'

def _builder():
 spec=importlib.util.spec_from_file_location('builder',HERE/'build_candidate.py')
 if spec is None or spec.loader is None: raise RuntimeError('builder')
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def rounds(cells):
 rows=[set() for _ in range(9)];cols=[set() for _ in range(9)];boxes=[set() for _ in range(9)];out=[]
 for r,c,v in cells:
  b=3*(r//3)+c//3;ok=v not in rows[r] and v not in cols[c] and v not in boxes[b]
  out.append({'in':[r,c,v],'out':[int(ok)]})
  if not ok: break
  rows[r].add(v);cols[c].add(v);boxes[b].add(v)
 return out

def main():
 text=ART.read_text();assert _builder().build()==text
 validate_layout(text);m=Machine.parse(text);assert min(len(p.cells) for p in m.pipes)>=2
 parent=(ROOT/'submissions/sudoku-validity/sudoku_05.man').read_text()
 assert sorted(len(p.cells) for p in Machine.parse(parent).pipes)==sorted(len(p.cells) for p in m.pipes)
 problem=json.loads((ROOT/'data/small/problems/sudoku-validity.json').read_text())
 public=judge_problem(text,problem);assert public.cases_passed==public.cases_total==6
 solved=[(r,c,(r*3+r//3+c)%9+1) for r in range(9) for c in range(9)]
 directed=[]
 for seed in range(60):
  rng=random.Random(20260727+seed);grid=solved[:];rng.shuffle(grid);prefix=grid[:2+rng.randrange(39)];used={(r,c) for r,c,_ in prefix};sr,sc,v=rng.choice(prefix)
  if seed%3==0: opts=[(sr,c,v) for c in range(9) if (sr,c) not in used]
  elif seed%3==1: opts=[(r,sc,v) for r in range(9) if (r,sc) not in used]
  else:
   br,bc=(sr//3)*3,(sc//3)*3;opts=[(r,c,v) for r in range(br,br+3) for c in range(bc,bc+3) if (r,c) not in used]
  if opts: directed.append(rounds(prefix+[rng.choice(opts)]))
 directed += [rounds(solved),rounds([(0,0,4),(0,8,4)]),rounds([(0,0,4),(8,0,4)]),rounds([(0,0,4),(2,2,4)]),rounds([(0,0,1),(0,1,2),(1,0,3)]),rounds([(8,8,9),(8,7,8),(7,8,7)])]
 results=[judge_case(text,x) for x in directed];assert all(r.passed for r in results)
 print(json.dumps({'sha256':hashlib.sha256(text.encode()).hexdigest(),'public':public.case_ticks,'score':public.score,'directed':len(results),'maxDirectedTicks':max(r.ticks for r in results),'dimensions':[max(map(len,text.rstrip().splitlines())),len(text.rstrip().splitlines())],'rooms':len(m.rooms),'pipes':len(m.pipes)},sort_keys=True))
if __name__=='__main__':main()
