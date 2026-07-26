"""Full squeeze, then re-inflate every shortened pipe to its original length.

Capacity is preserved by construction: same ports, same cell count per pipe;
only the geometry between the ports changes. Pipes are matched between the
original and squeezed program by (source room index, dest room index), which
parse in the same reading order on both sides.
"""
import sys, time
from littleman.alexey_squeeze import squeeze
from littleman.alexey_piperoute import Router, RouteError
from littleman.sim import Machine

S = '/tmp/claude-1003/-home-claudebox-projects-icfpc2026/c1f1ea3d-8df4-4f21-b4a0-f17910d5660d/scratchpad/'
orig = open(S + 'ss00.man').read()
out = squeeze(orig, rows=True, cols=True)
text = out[0] if isinstance(out, tuple) else out

def pipe_map(t):
    m = Machine.parse(t)
    ridx = {id(r): i for i, r in enumerate(m.rooms)}
    d = {}
    for p in m.pipes:
        key = (ridx[id(p.source)], ridx[id(p.dest)])
        d.setdefault(key, []).append(p)
    return m, d

m0, map0 = pipe_map(orig)
m1, map1 = pipe_map(text)
assert set(map0) == set(map1)
todo = []
for key, ps0 in sorted(map0.items()):
    ps1 = map1[key]
    assert len(ps0) == len(ps1), key
    ps0s = sorted(ps0, key=lambda p: p.cells[0]); ps1s = sorted(ps1, key=lambda p: p.cells[0])
    for a, b in zip(ps0s, ps1s):
        if len(b.cells) < len(a.cells):
            todo.append((key, b, len(a.cells)))
print('pipes to re-inflate:', len(todo))

DIR = {(-1,0):'^',(1,0):'v',(0,-1):'<',(0,1):'>'}
def arrow_dir(t, cell):
    lines = t.split('\n')
    ch = lines[cell[0]][cell[1]]
    return {v:k for k,v in DIR.items()}[ch]

t0 = time.time(); done = fail = 0
for key, b, want in todo:
    rt = Router(text)
    start, end = b.cells[0], b.cells[-1]
    into = arrow_dir(text, end)
    outd = arrow_dir(text, start)
    rt.erase(b.cells)
    try:
        cells = rt.route(start, end, into=into, target=want, out=outd)
        cand = rt.apply(cells, into=into)
        # cheap structural gate before accepting
        mm = Machine.parse(cand)
        if len(mm.pipes) != 2164:
            raise RouteError('pipe count changed')
        text = cand; done += 1
    except (RouteError, Exception) as e:
        fail += 1
        print('  KEEP-SHORT', key, want, '->', len(b.cells), type(e).__name__, str(e)[:60])
    if (done+fail) % 20 == 0:
        print(f'  {done+fail}/{len(todo)} ({round(time.time()-t0,1)}s)')
print('re-inflated', done, 'failed', fail, 'wall', round(time.time()-t0,1))
open('experiments/alexey-subset-sum/ss_reinflated.man','w').write(text)
m2 = Machine.parse(text)
l0 = sorted(len(p.cells) for p in m0.pipes); l2 = sorted(len(p.cells) for p in m2.pipes)
print('length multiset restored:', l0 == l2)
lines = text.split('\n'); cells=[(r,c) for r,l in enumerate(lines) for c,ch in enumerate(l) if ch!=' ']
w=max(c for _,c in cells)+1; h=max(r for r,_ in cells)+1
print('box', w, 'x', h, 'fp', max(w,h)**2)
