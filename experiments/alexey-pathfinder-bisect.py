import json, sys, time
sys.path.insert(0,'src')
from littleman.judge import judge_problem
PROB=json.loads(open('data/small/problems/pathfinder.json').read())
ORIG=open('submissions/pathfinder/pathfinder_01.man').read()
lines=ORIG.rstrip('\n').split('\n'); W=max(len(l) for l in lines)
grid=[l.ljust(W) for l in lines]; H=len(grid)
rows=[r for r in range(H) if all(ch in ' |' for ch in grid[r])]
print('deletable rows',len(rows),flush=True)
def build(rs):
    s=set(rs)
    return '\n'.join(l.rstrip() for r,l in enumerate(grid) if r not in s)+'\n'
def ok(rs,tag):
    t0=time.time(); rep=judge_problem(build(rs),PROB)
    good=rep.cases_passed==rep.cases_total
    print(f'[{tag}] rows={len(rs)} -> {rep.cases_passed}/{rep.cases_total} fp={rep.footprint} score={rep.score if good else "x"} ({round(time.time()-t0)}s)',flush=True)
    return good,rep
k=max(1,len(rows)//8)
gs=[rows[i:i+k] for i in range(0,len(rows),k)]
passing=[g for g in gs if ok(g,f'{g[0]}-{g[-1]}')[0]]
cur=[x for g in passing for x in g]
good,rep=ok(cur,'union')
work=list(passing)
while not good and work:
    drop=max(work,key=len); work.remove(drop)
    cur=[x for g in work for x in g]
    good,rep=ok(cur,f'minus {drop[0]}-{drop[-1]}')
if good and cur:
    open('experiments/alexey-pathfinder_02.man','w').write(build(cur))
    print('WRITTEN experiments/alexey-pathfinder_02.man rows',len(cur),'score',rep.score,flush=True)
