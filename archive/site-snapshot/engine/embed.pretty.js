import {
    at as e,
    ot as t,
    st as n,
    v as r,
    w as i
} from "./ui-wC2GCM-8.js";
import {
    _ as a,
    a as o,
    c as s,
    d as c,
    f as l,
    g as u,
    h as d,
    i as f,
    l as p,
    m,
    n as h,
    o as g,
    p as _,
    r as v,
    s as y,
    t as b,
    u as x
} from "./dist-D92dEv3Y.js";
var S = n(e()),
    C = 6,
    w = 2e4,
    T = 250,
    ee = 100;

function E({
    runner: e,
    cells: t,
    input: n = ``,
    expected: r = ``,
    frames: i = null,
    ticksPerSecond: a = 10,
    paceToDisplay: o = !1
}) {
    let [s, c] = S.useState(null), [l, u] = S.useState(!1), [d, f] = S.useState(null), [p, m] = S.useState(null), h = S.useRef(t);
    h.current = t;
    let g = S.useRef(n);
    g.current = n;
    let _ = S.useRef(r);
    _.current = r;
    let v = S.useRef(i);
    v.current = i, S.useEffect(() => {
        let t = !1;
        return e.getCapabilities().then(e => {
            t || f(e)
        }), () => {
            t = !0
        }
    }, [e]), S.useEffect(() => {
        c(null), u(!1), m(null)
    }, [e]);
    let y = d !== null,
        b = s !== null,
        x = !!d?.canStep && !!s && !s.halted,
        E = !!d?.canBack && !!s && s.step > 0,
        D = !!d?.canPlay && x,
        O = S.useRef(!1),
        k = S.useCallback(async ({
            autoPlay: t = !0
        } = {}) => {
            if (O.current) return;
            O.current = !0, m(null);
            let n;
            try {
                n = await e.load(h.current, {
                    input: g.current,
                    expected: _.current,
                    frames: v.current
                })
            } catch (e) {
                m({
                    message: e.message,
                    cell: e.cell ?? null
                });
                return
            } finally {
                O.current = !1
            }
            n && (c(n), u(t && !n.halted))
        }, [e]),
        A = S.useCallback(() => {
            c(null), u(!1), m(null)
        }, []),
        j = S.useCallback(async () => {
            let t = await e.step();
            t && c(t)
        }, [e]),
        te = S.useCallback(async () => {
            if (!d?.canBack) return;
            let t = await e.back();
            t && (c(t), u(!1))
        }, [e, d]),
        M = S.useCallback(() => {
            u(e => !(e || !s || s.halted))
        }, [s]),
        ne = S.useRef(e);
    ne.current = e;
    let N = S.useRef(s);
    N.current = s;
    let re = S.useRef(1);
    return S.useEffect(() => {
        if (!l || !N.current) return;
        let t = !1,
            n = null,
            r = null,
            i = 0,
            s = null,
            d = async l => {
                if (s !== null) {
                    if (l < s) {
                        r = l, i = 0, n = requestAnimationFrame(d);
                        return
                    }
                    s = null
                }
                let f = r === null ? 0 : Math.min(l - r, T);
                r = l;
                let p = i + f / 1e3 * a,
                    m = Math.floor(p);
                i = p - m;
                let h = Math.min(m, re.current, w);
                if (h === 0) {
                    n = requestAnimationFrame(d);
                    return
                }
                let g = o && (N.current?.entities?.displays?.length ?? 0) > 0,
                    _ = h < m,
                    v = performance.now(),
                    y = await e.stepMany(h, {
                        stopOnFrame: g
                    });
                if (_ && y && !y.halted && !y.outputSettled && !y.frameCommitted) {
                    let e = Math.max(performance.now() - v, .25),
                        t = Math.round(h * C / e);
                    re.current = Math.max(1, Math.min(t, h * 4, w))
                }
                if (ne.current === e) {
                    if (y && c(y), !y || y.halted || y.outputSettled) {
                        u(!1);
                        return
                    }
                    y.frameCommitted && (s = performance.now() + ee), t || (n = requestAnimationFrame(d))
                }
            };
        return n = requestAnimationFrame(d), () => {
            t = !0, cancelAnimationFrame(n)
        }
    }, [l, a, e, o]), {
        snapshot: s,
        loadError: p,
        capabilities: d,
        ready: y,
        isSimulating: b,
        isPlaying: l,
        canNext: x,
        canBack: E,
        canPlay: D,
        onRun: k,
        onNext: j,
        onBack: te,
        onStop: A,
        onTogglePlay: M
    }
}
var D = {
        NO_SELECTION: `no-selection`,
        SELECTED_AREA: `selected-area`,
        SELECTED_CELL: `selected-cell`
    },
    O = 5e6,
    k = typeof navigator < `u` && /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent || ``) ? {
        mod: `⌘`,
        shift: `⇧`,
        alt: `⌥`,
        enter: `↩`
    } : {
        mod: `⌃`,
        shift: `⇧`,
        alt: `Alt`,
        enter: `↵`
    };

function A(e, t) {
    return `${e}:${t}`
}
var j = new Set([`range`, `checkbox`, `radio`, `button`, `submit`, `reset`, `color`, `file`, `image`]);

function te() {
    let e = document.activeElement;
    if (!e || e.dataset?.littlemanHiddenInput !== void 0) return !1;
    let t = e.tagName;
    return t === `TEXTAREA` || t === `SELECT` ? !0 : t === `INPUT` ? !j.has(e.type) : !!e.isContentEditable
}

function M(e) {
    let t = e.indexOf(`:`);
    return {
        x: Number(e.slice(0, t)),
        y: Number(e.slice(t + 1))
    }
}

function ne(e, t, n) {
    return e >= n.left && e <= n.right && t >= n.top && t <= n.bottom
}

function N({
    anchor: e,
    active: t
}) {
    return {
        left: Math.min(e.x, t.x),
        top: Math.min(e.y, t.y),
        right: Math.max(e.x, t.x),
        bottom: Math.max(e.y, t.y)
    }
}

function re(e) {
    return e.state === D.NO_SELECTION
}

function P(e) {
    return e.state === D.SELECTED_CELL
}

function F(e) {
    return e.state === D.SELECTED_AREA
}

function I(e, t) {
    if (P(e)) return t(e.cell.x, e.cell.y) || ` `;
    if (!F(e)) return;
    let n = N(e),
        r = 1 / 0,
        i = -1 / 0,
        a = 1 / 0,
        o = -1 / 0;
    for (let e = n.top; e <= n.bottom; e++)
        for (let s = n.left; s <= n.right; s++) t(s, e) && (s < r && (r = s), s > i && (i = s), e < a && (a = e), e > o && (o = e));
    if (r === 1 / 0) return ``;
    let s = [];
    for (let e = a; e <= o; e++) {
        for (let n = r; n <= i; n++) s.push(t(n, e) || ` `);
        s.push(`
`)
    }
    return s.join(``)
}

function ie(e) {
    let t = [],
        n = 0,
        r = 0;
    for (let i of e) {
        if (i === `
`) {
            r += 1, n = 0;
            continue
        }
        i !== `\r` && (t.push({
            dx: n,
            dy: r,
            content: i === ` ` ? `` : i
        }), n += 1)
    }
    return t
}

function ae(e) {
    let t = {};
    for (let {
            dx: n,
            dy: r,
            content: i
        }
        of ie(e)) i !== `` && (t[A(n, r)] = i);
    return t
}

function oe(e) {
    let t = 1 / 0,
        n = -1 / 0,
        r = 1 / 0,
        i = -1 / 0;
    for (let a of Object.keys(e)) {
        if (!e[a]) continue;
        let {
            x: o,
            y: s
        } = M(a);
        o < t && (t = o), o > n && (n = o), s < r && (r = s), s > i && (i = s)
    }
    if (t === 1 / 0) return ``;
    let a = [];
    for (let o = r; o <= i; o++) {
        let r = ``;
        for (let i = t; i <= n; i++) r += e[A(i, o)] || ` `;
        a.push(r)
    }
    return a.join(`
`) + `
`
}

function se(e, t) {
    let n = URL.createObjectURL(new Blob([t], {
            type: `text/plain`
        })),
        r = document.createElement(`a`);
    r.href = n, r.download = e, r.click(), URL.revokeObjectURL(n)
}
var ce = `littleman:v2:`,
    le = `${ce}programs`,
    ue = `${ce}active`,
    L = e => `${ce}files:${e}`,
    R = e => `${ce}input:${e}`,
    z = e => `${ce}expected:${e}`,
    de = e => `${ce}view:${e}`,
    fe = [L, R, z, de];

function pe(e) {
    let t = new Set(e),
        n = fe.map(e => e(``));
    for (let e = localStorage.length - 1; e >= 0; e--) {
        let r = localStorage.key(e),
            i = r && n.find(e => r.startsWith(e));
        i && !t.has(r.slice(i.length)) && localStorage.removeItem(r)
    }
}

function me(e) {
    let t = 1 / 0,
        n = 1 / 0,
        r = -1 / 0,
        i = new Map;
    for (let a in e) {
        let o = e[a];
        if (!o) continue;
        let {
            x: s,
            y: c
        } = M(a);
        s < t && (t = s), c < n && (n = c), c > r && (r = c);
        let l = i.get(c);
        l || i.set(c, l = []), l.push({
            x: s,
            c: o
        })
    }
    if (!Number.isFinite(t)) return {
        rows: [],
        offset: {
            ox: 0,
            oy: 0
        }
    };
    let a = [];
    for (let e = n; e <= r; e++) {
        let n = i.get(e);
        if (!n) {
            a.push(``);
            continue
        }
        let r = -1 / 0;
        for (let {
                x: e
            }
            of n) e > r && (r = e);
        let o = Array(r - t + 1).fill(` `);
        for (let {
                x: e,
                c: r
            }
            of n) o[e - t] = r.charAt(0);
        a.push(o.join(``))
    }
    return {
        rows: a,
        offset: {
            ox: t,
            oy: n
        }
    }
}

function he(e, t) {
    let {
        entities: n
    } = e, r = t.ox, i = t.oy, a = (n?.runners ?? []).map(e => ({
        id: e.id,
        pos: [e.pos[0] + r, e.pos[1] + i],
        dir: e.dir,
        halted: !!e.halted,
        a: e.a ?? 0,
        b: e.b ?? 0,
        backpack: e.backpack ?? 0
    })), o = (n?.pipes ?? []).map(e => ({
        id: e.id,
        path: e.path.map(([e, t]) => [e + r, t + i]),
        values: e.values ?? []
    })), s = (n?.rooms ?? []).map(e => ({
        id: e.id,
        min: [e.min[0] + r, e.min[1] + i],
        max: [e.max[0] + r, e.max[1] + i],
        runners: e.runners ?? []
    })), c = e.fatal ? {
        reason: e.fatal.reason,
        pos: [e.fatal.pos[0] + r, e.fatal.pos[1] + i],
        cell: e.fatal.cell,
        value: e.fatal.value ?? null
    } : null;
    return {
        entities: {
            runners: a,
            pipes: o,
            rooms: s,
            displays: (n?.displays ?? []).map(e => ({
                id: e.id,
                min: [e.min[0] + r, e.min[1] + i],
                max: [e.max[0] + r, e.max[1] + i],
                w: e.w,
                h: e.h,
                front: e.front ?? [],
                back: e.back ?? [],
                cursor: e.cursor ?? 0,
                frames: e.frames ?? 0
            }))
        },
        step: Number(e.step) || 0,
        halted: !!e.halted,
        reason: e.reason ?? null,
        fatal: c,
        output: e.output ?? [],
        inputReleased: e.inputReleased ?? 0,
        inputRead: e.inputRead ?? 0,
        outputSettled: !!e.outputSettled,
        frameCommitted: !!e.frameCommitted,
        frameJudge: e.frameJudge ?? null
    }
}

function ge(e, t, n) {
    let r = Error(e || `load failed`);
    return t && (r.cell = {
        x: t[0] + n.ox,
        y: t[1] + n.oy
    }), r
}
var _e = `/wasm_exec.js`,
    ve = `/littleman.wasm`,
    ye = null,
    be = null,
    xe = null;

function B(e) {
    return new Promise((t, n) => {
        if (typeof document > `u`) {
            n(Error(`wasm: no document to load wasm_exec.js`));
            return
        }
        let r = document.querySelector(`script[src="${e}"]`);
        if (r) {
            if (r.dataset.loaded) {
                t();
                return
            }
            r.addEventListener(`load`, () => t()), r.addEventListener(`error`, () => n(Error(`wasm: failed to load ${e}`)));
            return
        }
        let i = document.createElement(`script`);
        i.src = e, i.addEventListener(`load`, () => {
            i.dataset.loaded = `1`, t()
        }), i.addEventListener(`error`, () => n(Error(`wasm: failed to load ${e}`))), document.head.appendChild(i)
    })
}

function Se() {
    return new Promise((e, t) => {
        if (globalThis.littlemanWasm) {
            e();
            return
        }
        let n = Date.now(),
            r = setInterval(() => {
                globalThis.littlemanWasm ? (clearInterval(r), e()) : Date.now() - n > 1e4 && (clearInterval(r), t(Error(`wasm: littlemanWasm global never appeared`)))
            }, 10)
    })
}

function Ce({
    wasmUrl: e,
    wasmExecUrl: t
} = {}) {
    return ye ? ((e && e !== be.wasmUrl || t && t !== be.wasmExecUrl) && console.warn(`whenWasmReady: boot already started with different URLs`), ye) : (be = {
        wasmUrl: e ?? ve,
        wasmExecUrl: t ?? _e
    }, ye = H(), ye.catch(() => {
        ye = null, be = null
    }), ye)
}

function V() {
    return xe !== null
}

function H() {
    return (async () => {
        if (!globalThis.littlemanWasm) {
            if (await B(be.wasmExecUrl), typeof Go > `u`) throw Error(`wasm: Go runtime missing after wasm_exec.js`);
            let e = new Go,
                t = await WebAssembly.instantiateStreaming(fetch(be.wasmUrl), e.importObject);
            e.run(t.instance), await Se()
        }
        return xe = globalThis.littlemanWasm, xe
    })()
}

function we() {
    if (!xe) throw Error(`wasm: called before boot — gate on whenWasmReady()`);
    return xe
}

function Te(e) {
    let t = JSON.parse(e);
    if (t.type === `error`) {
        let e = Error(t.message || `wasm error`);
        throw e.pos = t.pos ?? null, e
    }
    return t
}

function Ee() {
    return new Set(we().validOps())
}
var De = null;

function Oe() {
    return De ||= new Set(we().structuralGlyphs()), De
}

function ke(e, t) {
    let n = Oe();
    return t.some(({
        x: t,
        y: r,
        content: i
    }) => n.has(i) || n.has(e[A(t, r)]))
}
var U = null;

function Ae(e) {
    let {
        rows: t,
        offset: n
    } = me(e);
    if (t.length === 0) return {
        rooms: [],
        pipes: [],
        displays: []
    };
    let {
        ox: r,
        oy: i
    } = n, a = t.join(`
`);
    if (U && U.key === a && U.ox === r && U.oy === i) return U.result;
    let o = Te(we().analyze(t)),
        s = e => ({
            minX: e.min[0] + r,
            minY: e.min[1] + i,
            maxX: e.max[0] + r,
            maxY: e.max[1] + i
        }),
        c = {
            rooms: o.rooms.map(s),
            pipes: o.pipes.map(e => ({
                path: e.path.map(e => ({
                    x: e.pos[0] + r,
                    y: e.pos[1] + i,
                    dir: {
                        dx: e.dir[0],
                        dy: e.dir[1]
                    }
                })),
                srcIdx: e.src < 0 ? null : e.src,
                dstIdx: e.dst < 0 ? null : e.dst
            })),
            displays: o.displays.map(s)
        };
    return U = {
        key: a,
        ox: r,
        oy: i,
        result: c
    }, c
}
var je = null;

function Me(e) {
    let {
        rows: t,
        offset: n
    } = me(e);
    if (t.length === 0) return {
        cells: {},
        terminals: {}
    };
    let {
        ox: r,
        oy: i
    } = n, a = t.join(`
`);
    if (je && je.key === a && je.ox === r && je.oy === i) return je.result;
    let o = Te(we().flow(t)),
        s = {
            cells: {},
            terminals: {}
        };
    for (let e of o.cells) s.cells[A(e.pos[0] + r, e.pos[1] + i)] = e.dirs;
    for (let e of o.terminals) s.terminals[A(e.pos[0] + r, e.pos[1] + i)] = e.kind;
    return je = {
        key: a,
        ox: r,
        oy: i,
        result: s
    }, s
}

function Ne(e, t, n) {
    let {
        rows: r,
        offset: i
    } = me(e);
    return r.length === 0 ? [] : Te(we().route(r, t - i.ox, n - i.oy)).cells.map(([e, t]) => A(e + i.ox, t + i.oy))
}
var Pe = 2,
    W = 300;

function Fe(e) {
    try {
        let t = localStorage.getItem(e);
        if (!t) return null;
        let n = JSON.parse(t);
        return n?.version === Pe ? n.cells ?? {} : {}
    } catch {
        return {}
    }
}

function Ie(e, t) {
    try {
        localStorage.setItem(e, JSON.stringify({
            version: Pe,
            cells: t
        }))
    } catch (e) {
        console.warn(`useRawCells: failed to persist`, e)
    }
}

function Le(e, t) {
    let n = {
        ...e
    };
    for (let {
            x: e,
            y: r,
            content: i
        }
        of t) {
        let t = A(e, r);
        i === `` ? delete n[t] : n[t] = i
    }
    return n
}

function Re(e, t) {
    return t.map(({
        x: t,
        y: n
    }) => ({
        x: t,
        y: n,
        content: e[A(t, n)] ?? ``
    }))
}

function ze(e, t) {
    return t.every(({
        x: t,
        y: n,
        content: r
    }) => (e[A(t, n)] ?? ``) === r)
}

function Be(e, t) {
    return ke(e.cells, t) ? e.structuralRev + 1 : e.structuralRev
}

function Ve(e, t) {
    switch (t.type) {
        case `setCells`: {
            if (t.entries.length === 0 || ze(e.cells, t.entries)) return e;
            let n = Re(e.cells, t.entries);
            return {
                cells: Le(e.cells, t.entries),
                undoStack: [...e.undoStack, {
                    entries: n
                }],
                redoStack: [],
                structuralRev: Be(e, t.entries)
            }
        }
        case `undo`: {
            if (e.undoStack.length === 0) return e;
            let t = e.undoStack[e.undoStack.length - 1],
                n = Re(e.cells, t.entries);
            return {
                cells: Le(e.cells, t.entries),
                undoStack: e.undoStack.slice(0, -1),
                redoStack: [...e.redoStack, {
                    entries: n
                }],
                structuralRev: Be(e, t.entries)
            }
        }
        case `redo`: {
            if (e.redoStack.length === 0) return e;
            let t = e.redoStack[e.redoStack.length - 1],
                n = Re(e.cells, t.entries);
            return {
                cells: Le(e.cells, t.entries),
                undoStack: [...e.undoStack, {
                    entries: n
                }],
                redoStack: e.redoStack.slice(0, -1),
                structuralRev: Be(e, t.entries)
            }
        }
        case `reset`:
            return {
                cells: t.cells, undoStack: [], redoStack: [], structuralRev: e.structuralRev + 1
            };
        default:
            return e
    }
}

function He({
    programId: e,
    persist: t = !0,
    initialCells: n = null
}) {
    let [r] = S.useState(() => t ? {
        load: e => Fe(e) ?? n ?? {},
        save: Ie
    } : {
        load: () => n ?? {},
        save: () => {}
    }), i = L(e), [a, o] = S.useReducer(Ve, void 0, () => ({
        cells: r.load(i),
        undoStack: [],
        redoStack: [],
        structuralRev: 0
    })), s = S.useRef(a.cells);
    s.current = a.cells;
    let c = S.useRef(i);
    S.useEffect(() => {
        c.current !== i && (r.save(c.current, s.current), c.current = i, o({
            type: `reset`,
            cells: r.load(i)
        }))
    }, [r, i]), S.useEffect(() => {
        let e = setTimeout(() => r.save(i, a.cells), W);
        return () => clearTimeout(e)
    }, [r, i, a.cells]), S.useEffect(() => {
        let e = () => r.save(i, s.current);
        return window.addEventListener(`beforeunload`, e), () => window.removeEventListener(`beforeunload`, e)
    }, [r, i]);
    let l = S.useCallback((e, t) => a.cells[A(e, t)] ?? ``, [a.cells]),
        u = S.useCallback(({
            x: e,
            y: t,
            content: n
        }) => {
            o({
                type: `setCells`,
                entries: [{
                    x: e,
                    y: t,
                    content: n
                }]
            })
        }, []),
        d = S.useCallback(e => {
            o({
                type: `setCells`,
                entries: e
            })
        }, []),
        f = S.useCallback(() => o({
            type: `undo`
        }), []),
        p = S.useCallback(() => o({
            type: `redo`
        }), []);
    return {
        cells: a.cells,
        structuralRev: a.structuralRev,
        getCellContent: l,
        setCellContent: u,
        setCellsBulk: d,
        undo: f,
        redo: p,
        canUndo: a.undoStack.length > 0,
        canRedo: a.redoStack.length > 0
    }
}

function Ue(e, t) {
    return e > 0 ? `>` : e < 0 ? `<` : t > 0 ? `v` : `^`
}

function We(e, t) {
    return e === 0 ? `|` : `-`
}

function Ge(e) {
    let t = new Set;
    for (let n of e)
        for (let e = n.minX; e <= n.maxX; e++)
            for (let r = n.minY; r <= n.maxY; r++) t.add(A(e, r));
    return t
}

function Ke(e, t) {
    return e.path.every(e => t.has(A(e.x, e.y)))
}

function qe(e, t, n) {
    let r = [];
    for (let i of e) {
        if (Ke(i, t)) continue;
        let e = i.path,
            a = 0;
        for (; a < e.length;) {
            for (; a < e.length && !t.has(A(e[a].x, e[a].y));) a++;
            if (a >= e.length) break;
            let i = a;
            for (; a < e.length && t.has(A(e[a].x, e[a].y));) a++;
            let o = a - 1;
            if (i > 0) {
                let t = e[i - 1];
                r.push({
                    x: t.x,
                    y: t.y,
                    content: Ue(t.dir.dx, t.dir.dy)
                })
            }
            if (o < e.length - 1) {
                let t = e[o + 1];
                r.push({
                    x: t.x,
                    y: t.y,
                    content: Ue(t.dir.dx, t.dir.dy)
                })
            }
            for (let t = i; t <= o; t++) {
                let i = e[t],
                    a = A(i.x, i.y);
                n.has(a) || r.push({
                    x: i.x,
                    y: i.y,
                    content: ``
                })
            }
        }
    }
    return r
}

function Je(e, t) {
    return !(e.maxX < t.minX || t.maxX < e.minX || e.maxY < t.minY || t.maxY < e.minY)
}

function Ye(e, t) {
    return e.x >= t.minX && e.x <= t.maxX && e.y >= t.minY && e.y <= t.maxY
}

function Xe(e) {
    return [{
        x: e.minX,
        y: e.minY
    }, {
        x: e.maxX,
        y: e.minY
    }, {
        x: e.minX,
        y: e.maxY
    }, {
        x: e.maxX,
        y: e.maxY
    }]
}

function Ze(e, t, n) {
    switch (e) {
        case `S`: {
            if (n.x < t.minX || n.x > t.maxX) return null;
            let e = n.y - (t.maxY + 1);
            return e >= 0 ? e : null
        }
        case `N`: {
            if (n.x < t.minX || n.x > t.maxX) return null;
            let e = t.minY - 1 - n.y;
            return e >= 0 ? e : null
        }
        case `E`: {
            if (n.y < t.minY || n.y > t.maxY) return null;
            let e = n.x - (t.maxX + 1);
            return e >= 0 ? e : null
        }
        case `W`: {
            if (n.y < t.minY || n.y > t.maxY) return null;
            let e = t.minX - 1 - n.x;
            return e >= 0 ? e : null
        }
        default:
            return null
    }
}

function Qe(e, t, n, r) {
    let i = null,
        a = 1 / 0;
    for (let o of t) {
        if (!Je(e, o) || !Xe(o).some(t => Ye(t, e))) continue;
        let t = Ze(r, o, n);
        t !== null && t < a && (i = o, a = t)
    }
    return i
}

function $e(e, t, n, r) {
    switch (r) {
        case `W`:
            return t === e.minX && n >= e.minY && n <= e.maxY;
        case `E`:
            return t === e.maxX && n >= e.minY && n <= e.maxY;
        case `N`:
            return n === e.minY && t >= e.minX && t <= e.maxX;
        case `S`:
            return n === e.maxY && t >= e.minX && t <= e.maxX;
        default:
            return !1
    }
}

function et(e, t) {
    let {
        dx: n,
        dy: r
    } = e.dir;
    return t === `src` ? n > 0 ? `E` : n < 0 ? `W` : r > 0 ? `S` : `N` : n > 0 ? `W` : n < 0 ? `E` : r > 0 ? `N` : `S`
}

function tt(e, t, n, r) {
    switch (e) {
        case `E`:
            return r < t.minY || r > t.maxY ? null : {
                x: t.maxX + 1,
                y: r
            };
        case `W`:
            return r < t.minY || r > t.maxY ? null : {
                x: t.minX - 1,
                y: r
            };
        case `S`:
            return n < t.minX || n > t.maxX ? null : {
                x: n,
                y: t.maxY + 1
            };
        case `N`:
            return n < t.minX || n > t.maxX ? null : {
                x: n,
                y: t.minY - 1
            };
        default:
            return null
    }
}

function nt(e, t) {
    if (e.x === t.x) {
        let n = e.y < t.y ? 1 : -1,
            r = [];
        for (let i = e.y + n; i !== t.y + n; i += n) r.push({
            x: e.x,
            y: i
        });
        return r
    }
    if (e.y === t.y) {
        let n = e.x < t.x ? 1 : -1,
            r = [];
        for (let i = e.x + n; i !== t.x + n; i += n) r.push({
            x: i,
            y: e.y
        });
        return r
    }
    return null
}

function rt({
    pipe: e,
    endpoint: t,
    which: n,
    side: r,
    oldRoom: i,
    newRoom: a,
    newFootprint: o
}) {
    if (o.has(A(t.x, t.y))) return null;
    let s = n === `src` ? {
        x: t.x - t.dir.dx,
        y: t.y - t.dir.dy
    } : {
        x: t.x + t.dir.dx,
        y: t.y + t.dir.dy
    };
    if (!$e(i, s.x, s.y, r)) return null;
    let c = tt(r, a, t.x, t.y);
    if (!c || c.x === t.x && c.y === t.y) return null;
    let l = Ue(t.dir.dx, t.dir.dy),
        u = We(t.dir.dx, t.dir.dy),
        d = [];
    if (d.push({
            x: c.x,
            y: c.y,
            content: l
        }), n === `src`) {
        let e = nt(c, t);
        if (!e) return null;
        for (let t of e) d.push({
            x: t.x,
            y: t.y,
            content: u
        })
    } else {
        let e = nt(t, c);
        if (!e) return null;
        d.push({
            x: t.x,
            y: t.y,
            content: u
        });
        for (let t of e) t.x === c.x && t.y === c.y || d.push({
            x: t.x,
            y: t.y,
            content: u
        })
    }
    return d
}

function it({
    oldPipes: e,
    oldRooms: t,
    newRooms: n,
    newFootprint: r,
    dissolvedOldRoomIds: i,
    oldRoomId: a
}) {
    let o = [],
        s = new Map;
    if (t.forEach((e, t) => {
            i.has(a(e)) && s.set(t, e)
        }), s.size === 0) return o;
    let c = (e, t, i, a) => {
        let c = s.get(a);
        if (!c) return;
        let l = et(t, i),
            u = Qe(c, n, t, l);
        if (!u) return;
        let d = rt({
            pipe: e,
            endpoint: t,
            which: i,
            side: l,
            oldRoom: c,
            newRoom: u,
            newFootprint: r
        });
        d && o.push(...d)
    };
    for (let t of e) Ke(t, r) || (t.srcIdx !== null && c(t, t.path[0], `src`, t.srcIdx), t.dstIdx !== null && c(t, t.path[t.path.length - 1], `dst`, t.dstIdx));
    return o
}

function at(e, t) {
    let n = Math.abs(t.x - e.x) - 1,
        r = Math.abs(t.y - e.y) - 1;
    return n < 1 || r < 1 ? null : {
        x: Math.min(e.x, t.x),
        y: Math.min(e.y, t.y),
        w: n,
        h: r
    }
}

function ot({
    minX: e,
    minY: t,
    maxX: n,
    maxY: r
}, i, a) {
    let o = [{
        x: e,
        y: t,
        content: `+`
    }, {
        x: n,
        y: t,
        content: `+`
    }, {
        x: e,
        y: r,
        content: `+`
    }, {
        x: n,
        y: r,
        content: `+`
    }];
    for (let a = e + 1; a < n; a++) o.push({
        x: a,
        y: t,
        content: i
    }, {
        x: a,
        y: r,
        content: i
    });
    for (let i = t + 1; i < r; i++) o.push({
        x: e,
        y: i,
        content: a
    }, {
        x: n,
        y: i,
        content: a
    });
    return o
}

function st(e) {
    return ot(e, `-`, `|`)
}

function ct({
    x: e,
    y: t,
    w: n,
    h: r
}) {
    return st({
        minX: e,
        minY: t,
        maxX: e + n + 1,
        maxY: t + r + 1
    })
}

function G({
    w: e,
    h: t
}) {
    return {
        w: Math.min(e, 64),
        h: Math.min(t, 64)
    }
}

function lt(e) {
    return ot(e, `=`, `:`)
}

function K({
    x: e,
    y: t,
    w: n,
    h: r
}) {
    let {
        w: i,
        h: a
    } = G({
        w: n,
        h: r
    });
    return lt({
        minX: e,
        minY: t,
        maxX: e + i + 1,
        maxY: t + a + 1
    })
}

function ut(e, t) {
    let n = t ? dt(e, t) : e;
    return n ? n.map(({
        x: e,
        y: t,
        content: n
    }) => ({
        x: e,
        y: t,
        content: n
    })) : null
}

function dt(e, t) {
    let n = e => t.has(A(e.x, e.y)),
        r = 0,
        i = e.length - 1;
    for (; r <= i && n(e[r]);) r++;
    for (; i > r && n(e[i]);) i--;
    if (i - r < 1) return null;
    let a = e.slice(r, i + 1);
    a[0] = {
        ...a[0],
        content: a[0].head
    };
    let o = a.length - 1;
    return a[o] = {
        ...a[o],
        content: a[o].head
    }, a
}

function ft(e, t, {
    flip: n = !1,
    roomCells: r
} = {}) {
    return pt([e, t], {
        flips: [n],
        roomCells: r
    })
}

function pt(e, {
    flips: t = [],
    roomCells: n
} = {}) {
    let r = [];
    for (let n = 0; n + 1 < e.length; n++) {
        let i = e[n],
            a = e[n + 1];
        if (i.x === a.x && i.y === a.y) continue;
        let o = mt(i, a, !!t[n]);
        r.push(...r.length ? o.slice(1) : o)
    }
    if (r.length < 2) return null;
    let i = [],
        a = new Set;
    for (let e = 0; e < r.length; e++) {
        let t = r[e],
            n = e < r.length - 1 ? {
                dx: r[e + 1].x - t.x,
                dy: r[e + 1].y - t.y
            } : {
                dx: t.x - r[e - 1].x,
                dy: t.y - r[e - 1].y
            },
            o = e > 0 ? {
                dx: t.x - r[e - 1].x,
                dy: t.y - r[e - 1].y
            } : n,
            s = Ue(n.dx, n.dy),
            c = n.dx !== o.dx || n.dy !== o.dy,
            l = e === 0 || e === r.length - 1,
            u = n.dx === 0 ? `|` : `-`,
            d = `${t.x},${t.y}`;
        a.has(d) || (a.add(d), i.push({
            x: t.x,
            y: t.y,
            content: l || c ? s : u,
            head: s
        }))
    }
    return ut(i, n)
}

function mt(e, t, n) {
    let r = t.x - e.x,
        i = t.y - e.y,
        a = [],
        o = (e, t, n) => ht(e, t, n, (e, t) => a.push({
            x: e,
            y: t
        }));
    if (r === 0 || i === 0) return o(e, t, i === 0 ? `h` : `v`), a;
    let s = Math.abs(r) >= Math.abs(i),
        c = n ? !s : s,
        l = c ? {
            x: t.x,
            y: e.y
        } : {
            x: e.x,
            y: t.y
        };
    return o(e, l, c ? `h` : `v`), a.pop(), o(l, t, c ? `v` : `h`), a
}

function ht(e, t, n, r) {
    if (n === `h`) {
        let n = Math.sign(t.x - e.x) || 1;
        for (let i = e.x; r(i, e.y, i === e.x, i === t.x), i !== t.x; i += n);
    } else {
        let n = Math.sign(t.y - e.y) || 1;
        for (let i = e.y; r(e.x, i, i === e.y, i === t.y), i !== t.y; i += n);
    }
}

function gt(e, t) {
    let n = new Set,
        r = new Set;
    for (let i of e) {
        if (i.maxX - i.minX !== 2 || i.maxY - i.minY !== 2) continue;
        let e = A(i.minX + 1, i.minY + 1),
            a = t[e];
        if (!(a !== `I` && a !== `O`)) {
            r.add(e);
            for (let {
                    x: e,
                    y: t
                }
                of st(i)) n.add(A(e, t))
        }
    }
    return {
        specialWallCells: n,
        specialMarkerCells: r
    }
}

function _t(e, t) {
    return e.dx === t.dx && e.dy === t.dy
}

function vt(e, t) {
    return {
        x: e.x + t.dx,
        y: e.y + t.dy
    }
}

function yt(e) {
    return `${e.x},${e.y}`
}

function bt(e, t) {
    return {
        dx: Math.sign(t.x - e.x),
        dy: Math.sign(t.y - e.y)
    }
}

function xt(e, t) {
    if (e.x !== t.x && e.y !== t.y) return null;
    let n = bt(e, t),
        r = [],
        i = {
            ...e
        };
    for (; r.push({
            ...i
        }), !(i.x === t.x && i.y === t.y);) i = vt(i, n);
    return r
}

function St(e) {
    let t = [],
        n = new Set;
    for (let r = 0; r < e.length - 1; r++) {
        let i = xt(e[r], e[r + 1]);
        if (!i) return null;
        for (let e of i) {
            let r = yt(e);
            n.has(r) || (n.add(r), t.push(e))
        }
    }
    return t
}

function Ct(e, t, n) {
    if (!e || e.length < 2) return !1;
    for (let t = 1; t < e.length; t++)
        if (Math.abs(e[t].x - e[t - 1].x) + Math.abs(e[t].y - e[t - 1].y) !== 1) return !1;
    if (!_t(bt(e[0], e[1]), t) || !_t(bt(e[e.length - 2], e[e.length - 1]), n)) return !1;
    let r = new Set;
    for (let t of e) {
        let e = yt(t);
        if (r.has(e)) return !1;
        r.add(e)
    }
    for (let t = 1; t < e.length - 1; t++) {
        let n = bt(e[t - 1], e[t]),
            r = bt(e[t], e[t + 1]);
        if (_t(n, {
                dx: -r.dx,
                dy: -r.dy
            })) return !1
    }
    return !0
}

function wt(e, t, n, r) {
    if (e.x === n.x && e.y === n.y) return null;
    let i = {
            dx: -r.dx,
            dy: -r.dy
        },
        a = vt(e, t),
        o = vt(n, i),
        s = Math.round((e.x + n.x) / 2),
        c = Math.round((e.y + n.y) / 2),
        l = [
            [e, n],
            [e, {
                x: n.x,
                y: e.y
            }, n],
            [e, {
                x: e.x,
                y: n.y
            }, n],
            [e, {
                x: s,
                y: e.y
            }, {
                x: s,
                y: n.y
            }, n],
            [e, {
                x: e.x,
                y: c
            }, {
                x: n.x,
                y: c
            }, n],
            [e, a, {
                x: a.x,
                y: o.y
            }, o, n],
            [e, a, {
                x: o.x,
                y: a.y
            }, o, n]
        ];
    for (let e of l) {
        let n = St(e);
        if (Ct(n, t, r)) return n
    }
    return null
}

function Tt(e) {
    if (!e || e.length < 2) return [];
    let t = [];
    for (let n = 0; n < e.length; n++) {
        let r = e[n],
            i;
        if (n === e.length - 1) {
            let t = bt(e[n - 1], r);
            i = Ue(t.dx, t.dy)
        } else {
            let t = bt(r, e[n + 1]),
                a = n > 0 && !_t(bt(e[n - 1], r), t);
            i = n === 0 || a ? Ue(t.dx, t.dy) : We(t.dx, t.dy)
        }
        t.push({
            x: r.x,
            y: r.y,
            content: i
        })
    }
    return t
}

function Et(e, t, n) {
    return e.some(e => t >= e.minX && t <= e.maxX && n >= e.minY && n <= e.maxY && (t === e.minX || t === e.maxX || n === e.minY || n === e.maxY))
}

function Dt(e, t, n, r, i, a) {
    let o = e.path[0],
        s = e.path[e.path.length - 1],
        c = t === `src` ? e.dstIdx : e.srcIdx,
        l = c === null && (t === `src` ? Et(a, s.x + s.dir.dx, s.y + s.dir.dy) : Et(a, o.x - o.dir.dx, o.y - o.dir.dy));
    if (c === null && !l) return e.path.map(e => ({
        x: e.x + n,
        y: e.y + r,
        content: i[A(e.x, e.y)] ?? ``
    }));
    let u;
    if (t === `src`) u = wt({
        x: o.x + n,
        y: o.y + r
    }, o.dir, {
        x: s.x,
        y: s.y
    }, s.dir);
    else {
        let e = {
            x: s.x + n,
            y: s.y + r
        };
        u = wt({
            x: o.x,
            y: o.y
        }, o.dir, e, s.dir)
    }
    return u ? Tt(u) : null
}

function Ot(e, t, n, r, i, a, o = []) {
    let s = e[t];
    if (!s) return [];
    let c = [];
    for (let e = s.minX; e <= s.maxX; e++)
        for (let t = s.minY; t <= s.maxY; t++) c.push({
            x: e,
            y: t,
            content: ``
        }), c.push({
            x: e + n,
            y: t + r,
            content: ``
        });
    for (let e of i)
        for (let t of e.path) c.push({
            x: t.x,
            y: t.y,
            content: ``
        });
    for (let e of st(s)) c.push({
        x: e.x + n,
        y: e.y + r,
        content: e.content
    });
    for (let e = s.minX + 1; e < s.maxX; e++)
        for (let t = s.minY + 1; t < s.maxY; t++) {
            let i = a[A(e, t)];
            i === void 0 || i === `` || c.push({
                x: e + n,
                y: t + r,
                content: i
            })
        }
    for (let e of i) {
        let i = Dt(e, e.srcIdx === t ? `src` : `dst`, n, r, a, o);
        i && c.push(...i)
    }
    return c
}

function kt({
    minX: e,
    minY: t,
    maxX: n,
    maxY: r
}) {
    return `${e}-${t}-${n}-${r}`
}
var At = /^[\x20-\x7e]?$/;

function jt(e, t) {
    let n = {
        ...e
    };
    for (let {
            x: e,
            y: r,
            content: i
        }
        of t) {
        let t = A(e, r);
        i === `` ? delete n[t] : n[t] = i
    }
    return n
}

function Mt(e, t) {
    let n = new Set(e.map(kt));
    return t.filter(e => !n.has(kt(e)))
}

function Nt(e, t, n) {
    let r = new Set(t.map(kt));
    return e.filter(e => r.has(kt(e)) ? n.some(t => Je(e, t)) : !0)
}

function Pt(e, t, n = st) {
    return e.length === 0 ? [] : e.flatMap(n).filter(({
        x: e,
        y: n
    }) => !t.has(A(e, n))).map(({
        x: e,
        y: t
    }) => ({
        x: e,
        y: t,
        content: ``
    }))
}

function Ft(e, t, n) {
    if (n = n.filter(e => At.test(e.content)), n.length === 0) return [];
    if (!ke(e, n)) return n;
    let r = new Set(n.map(e => A(e.x, e.y))),
        {
            rooms: i,
            pipes: a,
            displays: o
        } = t,
        s = jt(e, n),
        c = Ae(s),
        l = c.rooms,
        u = c.displays,
        d = [...Mt(i, l), ...Mt(o, u)],
        f = Nt(i, l, d),
        p = Nt(o, u, d),
        m = [...Pt(f, r), ...Pt(p, r, lt)],
        h = new Set(f.map(kt)),
        g = (m.length ? Ae(jt(s, m)).rooms : l).filter(e => !h.has(kt(e))),
        _ = [],
        v = [];
    if (a.length > 0) {
        let e = Ge(g);
        _ = qe(a, e, r), h.size > 0 && (v = it({
            oldPipes: a,
            oldRooms: i,
            newRooms: g,
            newFootprint: e,
            dissolvedOldRoomIds: h,
            oldRoomId: kt
        }))
    }
    return [...n, ...m, ..._, ...v]
}

function It(e, t) {
    return t.filter(t => t.content !== `` || e[A(t.x, t.y)] !== void 0)
}

function Lt(e, t, n, r, i) {
    if (r === 0 && i === 0) return [];
    let {
        rooms: a,
        pipes: o
    } = t;
    if (!a[n]) return [];
    let s = It(e, Ot(a, n, r, i, o.filter(e => e.srcIdx === n || e.dstIdx === n), e, t.displays).filter(e => At.test(e.content))),
        c = a.filter((e, t) => t !== n),
        l = o.filter(e => e.srcIdx !== n && e.dstIdx !== n),
        u = t.displays;
    if (c.length === 0 && l.length === 0 && u.length === 0) return s;
    let d = new Set(s.map(e => A(e.x, e.y))),
        f = Ae(jt(e, s)),
        p = f.rooms,
        m = Mt(c, p),
        h = Nt(c, p, m),
        g = Nt(u, f.displays, m),
        _ = [...Pt(h, d), ...Pt(g, d, lt)],
        v = [];
    if (l.length > 0) {
        let e = new Set(h.map(kt));
        v = qe(l, Ge(p.filter(t => !e.has(kt(t)))), d).filter(e => !d.has(A(e.x, e.y)))
    }
    return [...s, ..._, ...v]
}

function Rt({
    programId: e,
    persist: t = !0,
    initialCells: n = null
}) {
    let {
        cells: r,
        structuralRev: i,
        getCellContent: a,
        setCellsBulk: o,
        undo: s,
        redo: c,
        canUndo: l,
        canRedo: u
    } = He({
        programId: e,
        persist: t,
        initialCells: n
    }), d = S.useMemo(() => Ae(r), [i]), f = d.rooms, p = S.useMemo(() => {
        let e = new Set;
        for (let t of f)
            for (let {
                    x: n,
                    y: r
                }
                of st(t)) e.add(A(n, r));
        return e
    }, [f]), m = S.useMemo(() => {
        let e = new Set;
        for (let t of f)
            for (let n = t.minX; n <= t.maxX; n++)
                for (let r = t.minY; r <= t.maxY; r++) e.add(A(n, r));
        return e
    }, [f]), {
        specialWallCells: h,
        specialMarkerCells: g
    } = S.useMemo(() => gt(f, r), [f, r]), _ = S.useMemo(() => {
        let e = new Set;
        for (let t of d.pipes)
            if (!(t.path.length < 2 && t.srcIdx === null && t.dstIdx === null))
                for (let n of t.path) e.add(A(n.x, n.y));
        return e
    }, [d]), v = d.displays, {
        displayWallCells: y,
        displayCells: b
    } = S.useMemo(() => {
        let e = new Set,
            t = new Set;
        for (let n of v)
            for (let r = n.minX; r <= n.maxX; r++)
                for (let i = n.minY; i <= n.maxY; i++) {
                    let a = A(r, i);
                    t.add(a), (r === n.minX || r === n.maxX || i === n.minY || i === n.maxY) && e.add(a)
                }
        return {
            displayWallCells: e,
            displayCells: t
        }
    }, [v]), x = S.useCallback(e => {
        if (e.length === 0) return;
        let t = Ft(r, d, e);
        t.length > 0 && o(t)
    }, [r, d, o]);
    return {
        cells: r,
        rooms: f,
        wallCells: p,
        roomCells: m,
        pipeCells: _,
        specialWallCells: h,
        specialMarkerCells: g,
        displayWallCells: y,
        displayCells: b,
        getCellContent: a,
        setCellContent: S.useCallback(({
            x: e,
            y: t,
            content: n
        }) => x([{
            x: e,
            y: t,
            content: n
        }]), [x]),
        setCellsBulk: x,
        moveRoom: S.useCallback((e, t, n) => {
            let i = Lt(r, d, e, t, n);
            i.length > 0 && o(i)
        }, [r, d, o]),
        previewMoveRoom: S.useCallback((e, t, n) => {
            if (!d.rooms[e]) return null;
            let i = d.pipes.filter(t => t.srcIdx === e || t.dstIdx === e);
            return Ot(d.rooms, e, t, n, i, r, d.displays)
        }, [r, d]),
        undo: s,
        redo: c,
        canUndo: l,
        canRedo: u
    }
}

function zt(e, t) {
    if (t === void 0 || t === `any`) return !0;
    let n = t === `none` ? [] : t.split(`+`);
    return e.shiftKey === n.includes(`shift`) && e.ctrlKey === n.includes(`ctrl`) && e.altKey === n.includes(`alt`) && e.metaKey === n.includes(`meta`)
}
var q = i(),
    Bt = S.createContext(null);

function Vt() {
    return S.useContext(Bt)
}

function Ht(e) {
    e?.closest?.(`[data-littleman-key-scope]`)?.focus()
}

function Ut(e, t) {
    return e ? e.add(t) : (window.addEventListener(`keydown`, t), () => window.removeEventListener(`keydown`, t))
}
var Wt = r.div`
  height: 100%;
  outline: none;
`;

function Gt({
    children: e,
    global: t = !1
}) {
    let [n] = S.useState(() => {
        let e = new Set;
        return {
            add(t) {
                return e.add(t), () => e.delete(t)
            },
            dispatch(t) {
                for (let n of [...e]) n(t)
            }
        }
    });
    return (0, q.jsx)(Bt.Provider, {
        value: t ? null : n,
        children: (0, q.jsx)(Wt, {
            tabIndex: -1,
            "data-littleman-key-scope": !0,
            onKeyDown: t ? void 0 : n.dispatch,
            children: e
        })
    })
}

function J({
    key: e,
    callback: t,
    modifiers: n,
    allowInFormControl: r = !1
}) {
    let i = Vt();
    S.useEffect(() => Ut(i, i => {
        i.key === e && zt(i, n) && (!r && te() || t(i))
    }), [e, t, n, r, i])
}
var Kt = 300;

function qt(e, t, n) {
    try {
        let r = localStorage.getItem(e);
        if (r === null) return t;
        let i = JSON.parse(r);
        return n && !n(i) ? t : i
    } catch {
        return t
    }
}

function Jt(e, t) {
    try {
        localStorage.setItem(e, JSON.stringify(t))
    } catch (e) {
        console.warn(`usePersistedState: failed to persist`, e)
    }
}

function Yt(e, t, n) {
    let [r, i] = S.useState(() => e ? qt(e, t, n) : t), a = S.useRef(r);
    a.current = r;
    let o = S.useRef(t);
    o.current = t;
    let s = S.useRef(n);
    s.current = n;
    let c = S.useRef(e);
    return S.useEffect(() => {
        c.current !== e && (c.current && Jt(c.current, a.current), c.current = e, i(e ? qt(e, o.current, s.current) : o.current))
    }, [e]), S.useEffect(() => {
        if (!e) return;
        let t = setTimeout(() => Jt(e, r), Kt);
        return () => clearTimeout(t)
    }, [e, r]), S.useEffect(() => {
        if (!e) return;
        let t = () => Jt(e, a.current);
        return window.addEventListener(`beforeunload`, t), () => window.removeEventListener(`beforeunload`, t)
    }, [e]), [r, i]
}
var Xt = [{
        id: `1`,
        name: `Program 1`
    }],
    Zt = `1`;

function Qt(e) {
    return Array.isArray(e) && e.every(e => typeof e?.id == `string` && typeof e?.name == `string`)
}

function $t(e) {
    return typeof e == `string`
}

function en(e) {
    let t = e.map(e => Number(e.id)).filter(Number.isFinite);
    return String(Math.max(0, ...t) + 1)
}

function tn(e, t) {
    let n = new Set(t.map(e => e.name));
    if (!n.has(e)) return e;
    let r = 1;
    for (; n.has(`${e} ${r}`);) r += 1;
    return `${e} ${r}`
}

function nn() {
    let [e, t] = Yt(le, Xt, Qt), [n, r] = Yt(ue, Zt, $t), i = e.some(e => e.id === n) ? n : e[0]?.id ?? null;
    return {
        programs: e,
        activeId: i,
        setActive: r,
        create: S.useCallback(n => {
            pe(e.map(e => e.id));
            let i = en(e);
            return t(e => [...e, {
                id: i,
                name: n ?? `Program ${i}`
            }]), r(i), i
        }, [e, t, r]),
        rename: S.useCallback((e, n) => {
            t(t => t.map(t => t.id === e ? {
                ...t,
                name: n
            } : t))
        }, [t]),
        remove: S.useCallback(n => {
            let a = e.filter(e => e.id !== n);
            a.length !== 0 && (t(a), i === n && r(a[0].id))
        }, [e, i, t, r])
    }
}
var rn = r.button`
  display: inline;
  padding: 0;
  border: none;
  background: none;
  font: inherit;
  color: inherit;
  text-decoration: underline;
  text-underline-offset: 2px;
  cursor: pointer;

  &:hover {
    color: var(--color-amber-300);
  }
`;

function an({
    x: e,
    y: t,
    onJump: n
}) {
    return (0, q.jsxs)(rn, {
        type: `button`,
        onClick: S.useCallback(() => n(e, t), [n, e, t]),
        children: [`(`, e, `, `, t, `)`]
    })
}
var on = 4;

function sn({
    viewportRef: e,
    enabled: t,
    threshold: n = on,
    suppressClick: r = `drag`,
    onDown: i,
    onMove: a,
    onUp: o,
    controlRef: s
}) {
    let c = S.useRef({
        onDown: i,
        onMove: a,
        onUp: o
    });
    S.useLayoutEffect(() => {
        c.current = {
            onDown: i,
            onMove: a,
            onUp: o
        }
    });
    let l = S.useRef({
            status: `idle`
        }),
        [u, d] = S.useState(!1);
    return S.useEffect(() => {
        if (!t) return;
        let i = e.current;
        if (!i) return;
        let a = () => {
                let e = t => {
                    t.stopPropagation(), t.preventDefault(), window.removeEventListener(`click`, e, !0)
                };
                window.addEventListener(`click`, e, !0), setTimeout(() => window.removeEventListener(`click`, e, !0), 100)
            },
            o = () => {
                window.removeEventListener(`pointerup`, m), window.removeEventListener(`pointermove`, p), d(!1)
            },
            u = e => e.preventDefault(),
            f = e => {
                if (e.button !== 0) return;
                let t = i.getBoundingClientRect();
                l.current = {
                    status: `pending`,
                    bounds: t,
                    startX: e.clientX,
                    startY: e.clientY
                }, c.current.onDown?.(e, {
                    bounds: t
                }), window.addEventListener(`pointerup`, m), window.addEventListener(`pointermove`, p)
            },
            p = e => {
                let {
                    status: t
                } = l.current;
                if (t !== `pending` && t !== `dragging`) return;
                let r = e.clientX - l.current.startX,
                    i = e.clientY - l.current.startY;
                if (t === `pending`) {
                    if (Math.abs(r) < n && Math.abs(i) < n) return;
                    l.current.status = `dragging`, d(!0)
                }
                c.current.onMove?.(e, {
                    deltaX: r,
                    deltaY: i,
                    bounds: l.current.bounds
                })
            },
            m = e => {
                let t = l.current.status;
                if (o(), l.current = {
                        status: `idle`
                    }, t === `cancelled`) {
                    r === `always` && a();
                    return
                }
                let n = t === `dragging`;
                c.current.onUp?.(e, {
                    wasDragging: n
                }), (r === `always` || r === `drag` && n) && a()
            };
        return s && (s.current = {
            cancel: () => {
                l.current.status !== `idle` && (l.current.status = `cancelled`, d(!1))
            },
            isDragging: () => l.current.status === `dragging`,
            isActive: () => l.current.status === `pending` || l.current.status === `dragging`
        }), i.addEventListener(`pointerdown`, f), i.addEventListener(`dragstart`, u), () => {
            o(), i.removeEventListener(`pointerdown`, f), i.removeEventListener(`dragstart`, u), l.current = {
                status: `idle`
            }, s && (s.current = null)
        }
    }, [t, n, r, e, s]), u
}

function cn(e) {
    let t = S.useRef(e);
    return S.useLayoutEffect(() => {
        t.current = e
    }), S.useCallback((...e) => t.current(...e), [])
}

function ln({
    viewportRef: e,
    setSelectedArea: t,
    spacePressed: n,
    coordsToCell: r,
    enabled: i = !0
}) {
    let a = cn(r),
        o = S.useRef(null);
    return sn({
        viewportRef: e,
        enabled: i && !n,
        onDown: (e, {
            bounds: t
        }) => {
            o.current = a(e.clientX - t.left, e.clientY - t.top)
        },
        onMove: (e, {
            bounds: n
        }) => {
            t({
                anchor: o.current,
                active: a(e.clientX - n.left, e.clientY - n.top)
            })
        }
    })
}

function un({
    ref: e
}) {
    let [t, n] = S.useState({
        width: 0,
        height: 0
    });
    return S.useEffect(() => {
        if (!e.current) return;
        let t = () => {
            n({
                width: e.current.clientWidth,
                height: e.current.clientHeight
            })
        };
        return t(), window.addEventListener(`resize`, t), () => window.removeEventListener(`resize`, t)
    }, [e]), t
}
var dn = {};

function fn() {
    let [e, t] = S.useState(dn);
    return {
        has: S.useCallback((t, n = !1) => e[t] ?? n, [e]),
        toggle: S.useCallback((e, n = !1) => {
            t(t => ({
                ...t,
                [e]: !(t[e] ?? n)
            }))
        }, []),
        clear: S.useCallback(() => t(dn), [])
    }
}

function pn({
    undo: e,
    redo: t
}) {
    let n = S.useCallback(t => {
            t.preventDefault(), e()
        }, [e]),
        r = S.useCallback(e => {
            e.preventDefault(), t()
        }, [t]);
    J({
        key: `z`,
        modifiers: `meta`,
        callback: n
    }), J({
        key: `z`,
        modifiers: `ctrl`,
        callback: n
    }), J({
        key: `Z`,
        modifiers: `meta+shift`,
        callback: r
    }), J({
        key: `z`,
        modifiers: `meta+shift`,
        callback: r
    }), J({
        key: `Z`,
        modifiers: `ctrl+shift`,
        callback: r
    }), J({
        key: `z`,
        modifiers: `ctrl+shift`,
        callback: r
    }), J({
        key: `y`,
        modifiers: `ctrl`,
        callback: r
    })
}

function mn({
    key: e,
    onDown: t,
    onUp: n,
    modifiers: r,
    allowInFormControl: i = !1
}) {
    let a = Vt();
    S.useEffect(() => {
        let o = n => {
                n.key === e && (n.repeat || zt(n, r) && (!i && te() || t?.(n)))
            },
            s = t => {
                t.key === e && n?.(t)
            },
            c = Ut(a, o);
        return window.addEventListener(`keyup`, s), () => {
            c(), window.removeEventListener(`keyup`, s)
        }
    }, [e, t, n, r, i, a])
}

function hn({
    moveCursor: e,
    extendSelection: t
}) {
    J({
        key: `ArrowUp`,
        modifiers: `none`,
        callback: () => e(0, -1)
    }), J({
        key: `ArrowDown`,
        modifiers: `none`,
        callback: () => e(0, 1)
    }), J({
        key: `ArrowLeft`,
        modifiers: `none`,
        callback: () => e(-1, 0)
    }), J({
        key: `ArrowRight`,
        modifiers: `none`,
        callback: () => e(1, 0)
    }), J({
        key: `ArrowUp`,
        modifiers: `shift`,
        callback: () => t(0, -1)
    }), J({
        key: `ArrowDown`,
        modifiers: `shift`,
        callback: () => t(0, 1)
    }), J({
        key: `ArrowLeft`,
        modifiers: `shift`,
        callback: () => t(-1, 0)
    }), J({
        key: `ArrowRight`,
        modifiers: `shift`,
        callback: () => t(1, 0)
    });
    let n = (t, n) => r => {
        r.preventDefault(), e(t, n)
    };
    J({
        key: `h`,
        modifiers: `ctrl`,
        callback: n(-1, 0)
    }), J({
        key: `j`,
        modifiers: `ctrl`,
        callback: n(0, 1)
    }), J({
        key: `k`,
        modifiers: `ctrl`,
        callback: n(0, -1)
    }), J({
        key: `l`,
        modifiers: `ctrl`,
        callback: n(1, 0)
    })
}

function gn({
    viewportRef: e,
    setPixelCoordinates: t,
    spacePressed: n,
    forcePan: r = !1
}) {
    return sn({
        viewportRef: e,
        enabled: n || r,
        onMove: (e, {
            deltaX: n,
            deltaY: r
        }) => {
            t(e => ({
                ...e,
                xOffset: -n,
                yOffset: -r
            }))
        },
        onUp: (e, {
            wasDragging: n
        }) => {
            n && t(e => ({
                ...e,
                x: e.x + e.xOffset,
                y: e.y + e.yOffset,
                xOffset: 0,
                yOffset: 0
            }))
        }
    })
}
var _n = {
    state: D.NO_SELECTION
};

function vn(e, t) {
    return {
        state: D.SELECTED_CELL,
        cell: {
            x: e,
            y: t
        }
    }
}

function yn(e, t) {
    return {
        state: D.SELECTED_AREA,
        anchor: e,
        active: t
    }
}

function bn() {
    let [e, t] = S.useState(_n);
    return {
        currentSelection: e,
        setSelectedCell: S.useCallback(({
            x: e,
            y: n
        }) => {
            t(vn(e, n))
        }, []),
        setSelectedArea: S.useCallback(({
            anchor: e,
            active: n
        }) => {
            e.x === n.x && e.y === n.y ? t(vn(e.x, e.y)) : t(yn(e, n))
        }, []),
        clearSelection: S.useCallback(() => {
            t(_n)
        }, []),
        moveCursor: S.useCallback((e, n) => {
            t(t => {
                if (re(t)) return t;
                let r = P(t) ? t.cell : t.active;
                return vn(r.x + e, r.y + n)
            })
        }, []),
        extendSelection: S.useCallback((e, n) => {
            t(t => {
                if (re(t)) return t;
                let r = P(t) ? t.cell : t.anchor,
                    i = P(t) ? t.cell : t.active,
                    a = {
                        x: i.x + e,
                        y: i.y + n
                    };
                return r.x === a.x && r.y === a.y ? vn(r.x, r.y) : yn(r, a)
            })
        }, [])
    }
}

function xn(e, {
    modifiers: t = `none`,
    allowInFormControl: n = !1
} = {}) {
    let r = S.useRef(e);
    S.useLayoutEffect(() => {
        r.current = e
    });
    let i = Vt();
    S.useEffect(() => Ut(i, e => {
        if (!zt(e, t) || !n && te()) return;
        let i = r.current[e.key];
        i && i(e)
    }), [t, n, i])
}
var Y = {
        SELECT: `select`,
        HAND: `hand`,
        ROOM: `room`,
        PIPE: `pipe`,
        DISPLAY: `display`,
        MOVE: `move`
    },
    Sn = [];

function Cn({
    currentSelection: e,
    clearSelection: t,
    setCellsBulk: n,
    roomCells: r,
    readOnly: i,
    toolsDisabled: a
}) {
    let [o, s] = S.useState(Y.SELECT), c = S.useMemo(() => a ? [Y.ROOM, Y.PIPE, Y.DISPLAY, Y.MOVE] : Sn, [a]), l = S.useCallback(e => {
        s(e), t()
    }, [t]), u = t => n => {
        c.includes(t) || !a && P(e) || (n?.preventDefault(), l(t))
    }, d = (t, r) => i => {
        if (!c.includes(t) && !P(e)) {
            if (F(e)) {
                let t = r(e);
                if (!t || t.length === 0) return;
                i?.preventDefault(), n(t);
                return
            }
            i?.preventDefault(), l(t)
        }
    };
    return xn({
        v: u(Y.SELECT),
        h: u(Y.HAND),
        r: d(Y.ROOM, e => {
            let t = at(e.anchor, e.active);
            return t ? ct(t) : null
        }),
        p: d(Y.PIPE, e => ft(e.anchor, e.active, {
            roomCells: r
        })),
        d: d(Y.DISPLAY, e => {
            let t = at(e.anchor, e.active);
            return t ? K(t) : null
        }),
        m: u(Y.MOVE),
        Escape: () => {
            P(e) || o !== Y.SELECT && l(Y.SELECT)
        }
    }), S.useEffect(() => {
        c.includes(o) && s(Y.SELECT)
    }, [o, c]), {
        tool: o,
        setTool: l,
        disabledTools: c
    }
}

function wn({
    viewportRef: e,
    tool: t,
    coordsToCell: n,
    setCellsBulk: r,
    roomCells: i,
    readOnly: a,
    spacePressed: o,
    onPendingChange: s
}) {
    let c = cn(n),
        l = cn(r),
        u = cn(s),
        d = S.useRef(null),
        f = S.useRef(null),
        p = S.useRef(!1),
        m = S.useRef(null),
        h = S.useRef([]),
        g = S.useRef([]),
        [_, v] = S.useState(0),
        y = S.useCallback(() => {
            let e = f.current;
            if (t === Y.PIPE && h.current.length > 0) return e ? pt([...h.current, e], {
                flips: [...g.current, p.current],
                roomCells: i
            }) : null;
            let n = d.current;
            if (!n || !e) return null;
            if (t === Y.ROOM) {
                let t = at(n, e);
                return t ? ct(t) : null
            }
            if (t === Y.DISPLAY) {
                let t = at(n, e);
                return t ? K(t) : null
            }
            return t === Y.PIPE ? ft(n, e, {
                flip: p.current,
                roomCells: i
            }) : null
        }, [t, i]),
        b = S.useCallback(() => {
            if (t !== Y.DISPLAY) return null;
            let e = d.current,
                n = f.current;
            if (!e || !n) return null;
            let r = at(e, n);
            if (!r) return null;
            let {
                w: i,
                h: a
            } = G(r);
            return {
                w: i,
                h: a,
                cell: e,
                side: n.y < e.y ? `below` : `above`
            }
        }, [t]),
        x = S.useCallback(() => {
            let e = y();
            if (e && e.length > 0) {
                u({
                    kind: t,
                    entries: e,
                    sizeHint: b()
                });
                return
            }
            let n = h.current[h.current.length - 1] ?? d.current;
            if (!n) {
                u(null);
                return
            }
            u({
                kind: `placeholder`,
                entries: [{
                    x: n.x,
                    y: n.y,
                    content: ``
                }]
            })
        }, [y, b, u, t]),
        C = S.useCallback(() => {
            h.current = [], g.current = [], v(0)
        }, []),
        w = S.useCallback((e, t) => {
            let n = pt(e, {
                flips: t,
                roomCells: i
            });
            return !n || n.length === 0 ? !1 : (l(n), C(), u(null), !0)
        }, [i, l, C, u]),
        T = S.useCallback(e => {
            let t = h.current;
            if (t.length > 0 && i?.has(A(e.x, e.y)) && w([...t, e], [...g.current, p.current])) return;
            let n = t[t.length - 1];
            if (n && n.x === e.x && n.y === e.y) {
                w(t, g.current);
                return
            }
            h.current = [...t, e], t.length > 0 && (g.current = [...g.current, p.current]), v(h.current.length), x()
        }, [i, w, x]),
        ee = !a && !o && (t === Y.ROOM || t === Y.PIPE || t === Y.DISPLAY),
        E = t === Y.PIPE && _ > 0,
        D = sn({
            viewportRef: e,
            enabled: ee,
            suppressClick: `always`,
            controlRef: m,
            onDown: (e, {
                bounds: t
            }) => {
                let n = c(e.clientX - t.left, e.clientY - t.top);
                if (f.current = n, p.current = e.shiftKey, h.current.length > 0) {
                    x();
                    return
                }
                d.current = n, x()
            },
            onMove: (e, {
                bounds: t
            }) => {
                f.current = c(e.clientX - t.left, e.clientY - t.top), x()
            },
            onUp: (e, {
                wasDragging: n
            }) => {
                if (h.current.length > 0) {
                    f.current && T(f.current);
                    return
                }
                if (n) {
                    let e = y();
                    e && e.length > 0 && l(e), u(null);
                    return
                }
                u(null), t === Y.PIPE && f.current && T(f.current)
            }
        });
    return S.useEffect(() => {
        if (!ee || !E) return;
        let t = e.current;
        if (!t) return;
        let n = e => {
            let n = t.getBoundingClientRect();
            f.current = c(e.clientX - n.left, e.clientY - n.top), x()
        };
        return t.addEventListener(`pointermove`, n), () => t.removeEventListener(`pointermove`, n)
    }, [ee, E, e, c, x]), S.useEffect(() => {
        if (!ee) return;
        let e = () => h.current.length > 0,
            t = t => {
                if (t.key === `Escape`) {
                    if (m.current?.isActive()) {
                        t.stopPropagation(), m.current.cancel(), e() ? x() : u(null);
                        return
                    }
                    e() && (t.stopPropagation(), C(), u(null));
                    return
                }
                if (t.key === `Enter` && e() && !m.current?.isActive()) {
                    w(f.current ? [...h.current, f.current] : h.current, [...g.current, p.current]);
                    return
                }
                t.key === `Shift` && (m.current?.isActive() || e()) && (p.current = !0, x())
            },
            n = t => {
                t.key === `Shift` && (m.current?.isActive() || e()) && (p.current = !1, x())
            };
        return window.addEventListener(`keydown`, t, !0), window.addEventListener(`keyup`, n, !0), () => {
            window.removeEventListener(`keydown`, t, !0), window.removeEventListener(`keyup`, n, !0)
        }
    }, [ee, x, u, C, w]), S.useEffect(() => () => {
        C(), u(null)
    }, [t, u, C]), S.useEffect(() => {
        a && (C(), u(null))
    }, [a, C, u]), D
}

function Tn(e, t) {
    return e && t && e.minX === t.minX && e.minY === t.minY && e.maxX === t.maxX && e.maxY === t.maxY
}

function En({
    viewportRef: e,
    tool: t,
    coordsToCell: n,
    rooms: r,
    previewMoveRoom: i,
    moveRoom: a,
    readOnly: o,
    spacePressed: s,
    onPendingChange: c
}) {
    let l = cn(n),
        u = cn(c),
        d = S.useRef(null),
        f = S.useRef({
            dx: 0,
            dy: 0
        }),
        p = S.useRef(null),
        m = !o && !s && t === Y.MOVE,
        h = S.useCallback(() => {
            d.current = null, u(null)
        }, [u]),
        g = S.useCallback((e, t, n, r) => {
            if (!r) {
                u(null);
                return
            }
            u({
                kind: `move`,
                entries: r,
                destRect: {
                    minX: e.minX + t,
                    minY: e.minY + n,
                    maxX: e.maxX + t,
                    maxY: e.maxY + n
                }
            })
        }, [u]),
        _ = sn({
            viewportRef: e,
            enabled: m,
            suppressClick: `always`,
            controlRef: p,
            onDown: (e, {
                bounds: t
            }) => {
                let n = l(e.clientX - t.left, e.clientY - t.top),
                    a = -1,
                    o = 1 / 0;
                if (r.forEach((e, t) => {
                        if (n.x < e.minX || n.x > e.maxX || n.y < e.minY || n.y > e.maxY) return;
                        let r = (e.maxX - e.minX) * (e.maxY - e.minY);
                        r < o && (o = r, a = t)
                    }), a < 0) {
                    d.current = null;
                    return
                }
                d.current = {
                    roomIdx: a,
                    room: r[a],
                    grabCell: n
                }, f.current = {
                    dx: 0,
                    dy: 0
                }, g(r[a], 0, 0, i(a, 0, 0))
            },
            onMove: (e, {
                bounds: t
            }) => {
                let n = d.current;
                if (!n) return;
                let a = l(e.clientX - t.left, e.clientY - t.top),
                    o = a.x - n.grabCell.x,
                    s = a.y - n.grabCell.y;
                if (!(o === f.current.dx && s === f.current.dy)) {
                    if (f.current = {
                            dx: o,
                            dy: s
                        }, !Tn(r[n.roomIdx], n.room)) {
                        h();
                        return
                    }
                    g(n.room, o, s, i(n.roomIdx, o, s))
                }
            },
            onUp: (e, {
                wasDragging: t
            }) => {
                let n = d.current,
                    {
                        dx: i,
                        dy: o
                    } = f.current;
                t && n && (i !== 0 || o !== 0) && Tn(r[n.roomIdx], n.room) && a(n.roomIdx, i, o), h()
            }
        });
    return S.useEffect(() => {
        if (!m) return;
        let e = e => {
            e.key === `Escape` && p.current?.isActive() && (e.stopPropagation(), p.current.cancel(), h())
        };
        return window.addEventListener(`keydown`, e, !0), () => window.removeEventListener(`keydown`, e, !0)
    }, [m, h]), S.useEffect(() => {
        m || h()
    }, [m, h]), _
}
var Dn = [`east`, `south`, `west`, `north`],
    On = {
        east: {
            dx: 1,
            dy: 0
        },
        south: {
            dx: 0,
            dy: 1
        },
        west: {
            dx: -1,
            dy: 0
        },
        north: {
            dx: 0,
            dy: -1
        }
    },
    kn = {
        ">": `east`,
        "<": `west`,
        "^": `north`,
        v: `south`
    };

function An({
    currentSelection: e,
    moveCursor: t,
    setSelectedCell: n,
    setCellContent: r
}) {
    let [i, a] = S.useState(null), o = S.useRef([]), s = S.useCallback(() => {
        o.current = []
    }, []), c = S.useCallback(() => {
        o.current = [], a(null)
    }, []), l = S.useCallback((t, n) => {
        P(e) && (t.preventDefault(), a(e => {
            let t = Dn.indexOf(e),
                r = Dn.length;
            return Dn[(t + n + r) % r]
        }))
    }, [e]);
    return J({
        key: `Tab`,
        modifiers: `none`,
        callback: e => l(e, 1)
    }), J({
        key: `Tab`,
        modifiers: `shift`,
        callback: e => l(e, -1)
    }), {
        direction: i,
        clearTrail: s,
        onEscape: S.useCallback(() => i == null ? !1 : (c(), !0), [i, c]),
        onAfterType: S.useCallback(n => {
            let r = i;
            if (r == null) return;
            let s = kn[n];
            s && (r = s, a(s));
            let c = On[r];
            P(e) && o.current.push({
                cell: e.cell,
                direction: r
            }), t(c.dx, c.dy)
        }, [i, t, e]),
        onBackspace: S.useCallback(({
            shiftPressed: t
        }) => {
            if (!t && o.current.length > 0) {
                let {
                    cell: e,
                    direction: t
                } = o.current.pop();
                n(e), a(t), r({
                    x: e.x,
                    y: e.y,
                    content: ``
                });
                return
            }
            if (P(e)) {
                let {
                    x: t,
                    y: n
                } = e.cell;
                r({
                    x: t,
                    y: n,
                    content: ``
                })
            }
        }, [n, r, e])
    }
}
var jn = {
        east: {
            dcx: 1,
            dcy: .5,
            clip: `polygon(0 0, 100% 50%, 0 100%)`
        },
        west: {
            dcx: 0,
            dcy: .5,
            clip: `polygon(100% 0, 0 50%, 100% 100%)`
        },
        south: {
            dcx: .5,
            dcy: 1,
            clip: `polygon(0 0, 100% 0, 50% 100%)`
        },
        north: {
            dcx: .5,
            dcy: 0,
            clip: `polygon(50% 0, 100% 100%, 0 100%)`
        }
    },
    Mn = r.div`
  position: absolute;
  width: var(--arrow-size);
  height: var(--arrow-size);
  left: calc(var(--cx) * var(--cell-size) - var(--arrow-size) / 2);
  top: calc(var(--cy) * var(--cell-size) - var(--arrow-size) / 2);
  background-color: var(--color-blue-500);
  clip-path: var(--arrow-clip);
  pointer-events: none;
`;

function Nn({
    readOnly: e,
    currentSelection: t,
    direction: n,
    currentStep: r
}) {
    if (e || !P(t)) return null;
    let i = t.cell;
    if (!i || !n) return null;
    let a = jn[n];
    return a ? (0, q.jsx)(Mn, {
        style: {
            "--cx": i.x + a.dcx,
            "--cy": i.y + a.dcy,
            "--arrow-size": `${r.typeaheadArrow}px`,
            "--arrow-clip": a.clip
        }
    }) : null
}
var Pn = 50,
    Fn = 60;

function In({
    prev: e,
    oldCellSize: t,
    newCellSize: n,
    anchorVx: r,
    anchorVy: i
}) {
    let a = n / t,
        o = e.x + e.xOffset,
        s = e.y + e.yOffset;
    return {
        x: (o + r) * a - r,
        y: (s + i) * a - i
    }
}

function Ln({
    viewportRef: e,
    viewportSize: t,
    setPixelCoordinates: n,
    steps: r,
    defaultStepIndex: i
}) {
    let a = S.useCallback((e, t, i) => {
        n(n => {
            let a = n.stepIndex,
                o = e(a),
                s = Math.max(0, Math.min(r.length - 1, o));
            if (s === a) return n;
            let {
                x: c,
                y: l
            } = In({
                prev: n,
                oldCellSize: r[a].cellSize,
                newCellSize: r[s].cellSize,
                anchorVx: t,
                anchorVy: i
            });
            return {
                ...n,
                stepIndex: s,
                x: c,
                y: l,
                xOffset: 0,
                yOffset: 0
            }
        })
    }, [n, r]);
    S.useEffect(() => {
        let t = e.current;
        if (!t) return;
        let n = 0,
            r = 0,
            i = e => {
                if (!e.ctrlKey && !e.metaKey || (e.preventDefault(), e.deltaY === 0) || (n !== 0 && Math.sign(e.deltaY) !== Math.sign(n) && (n = 0), n += e.deltaY, Math.abs(n) < Pn)) return;
                let i = performance.now();
                if (i - r < Fn) return;
                let o = n < 0 ? 1 : -1;
                n = 0, r = i;
                let s = t.getBoundingClientRect();
                a(e => e + o, e.clientX - s.left, e.clientY - s.top)
            };
        return t.addEventListener(`wheel`, i, {
            passive: !1
        }), () => t.removeEventListener(`wheel`, i)
    }, [e, a]);
    let o = S.useCallback(e => {
            e?.preventDefault(), a(e => e + 1, t.width / 2, t.height / 2)
        }, [a, t]),
        s = S.useCallback(e => {
            e?.preventDefault(), a(e => e - 1, t.width / 2, t.height / 2)
        }, [a, t]),
        c = S.useCallback(e => {
            e?.preventDefault(), a(() => i, t.width / 2, t.height / 2)
        }, [a, i, t]);
    return J({
        key: `=`,
        modifiers: `meta`,
        callback: o,
        allowInFormControl: !0
    }), J({
        key: `=`,
        modifiers: `ctrl`,
        callback: o,
        allowInFormControl: !0
    }), J({
        key: `+`,
        modifiers: `meta+shift`,
        callback: o,
        allowInFormControl: !0
    }), J({
        key: `+`,
        modifiers: `ctrl+shift`,
        callback: o,
        allowInFormControl: !0
    }), J({
        key: `+`,
        modifiers: `meta`,
        callback: o,
        allowInFormControl: !0
    }), J({
        key: `+`,
        modifiers: `ctrl`,
        callback: o,
        allowInFormControl: !0
    }), J({
        key: `-`,
        modifiers: `meta`,
        callback: s,
        allowInFormControl: !0
    }), J({
        key: `-`,
        modifiers: `ctrl`,
        callback: s,
        allowInFormControl: !0
    }), J({
        key: `0`,
        modifiers: `meta`,
        callback: c,
        allowInFormControl: !0
    }), J({
        key: `0`,
        modifiers: `ctrl`,
        callback: c,
        allowInFormControl: !0
    }), {
        zoomIn: o,
        zoomOut: s
    }
}
var Rn = `var(--color-red-400)`,
    X = {
        wall: `var(--color-indigo-500)`,
        ioRoomWall: `var(--color-stone-500)`,
        ioRoomMarker: `var(--color-stone-300)`,
        pipe: `var(--color-indigo-300)`,
        comment: `var(--color-stone-100)`,
        display: `var(--color-violet-500)`,
        displayScreen: `var(--color-violet-100)`,
        spawn: Rn,
        movement: `var(--color-yellow-400)`,
        io: `var(--color-pink-400)`,
        literal: `var(--color-slate-400)`,
        register: `var(--color-blue-300)`,
        arithmetic: `var(--color-green-400)`,
        runner: Rn,
        pipeValue: `var(--color-indigo-700)`,
        pipeHighlight: `var(--color-pink-300)`,
        flowLine: `var(--color-purple-600)`,
        flowWash: `rgba(147, 51, 234, 0.18)`,
        flowHalt: `var(--color-green-600)`,
        flowDeath: `var(--color-red-500)`,
        errorBorder: `var(--color-red-600)`,
        errorHalo: `var(--color-red-100)`,
        overlayPreview: `var(--color-amber-300)`,
        overlayLift: `var(--color-amber-100)`,
        cellDefault: `var(--color-stone-300)`,
        cellGap: `var(--color-stone-400)`,
        selection: `var(--color-blue-200)`,
        glyph: `#000`,
        glyphGhost: `rgba(0, 0, 0, 0.6)`
    },
    zn = new Map;

function Bn(e) {
    if (!e.startsWith(`var(`)) return e;
    let t = zn.get(e);
    if (t === void 0) {
        let n = e.slice(4, -1).split(`,`)[0].trim();
        if (t = getComputedStyle(document.documentElement).getPropertyValue(n).trim(), !t) return e;
        zn.set(e, t)
    }
    return t
}
var Vn = [`#0a0a0a`, `#dc2626`, `#16a34a`, `#eab308`, `#2563eb`, `#c026d3`, `#0891b2`, `#e5e5e5`, `#737373`, `#f87171`, `#4ade80`, `#fde047`, `#60a5fa`, `#e879f9`, `#22d3ee`, `#ffffff`];

function Hn(e) {
    return Vn[Number(e)] ?? Vn[0]
}
var Un = [{
        name: `spawn`,
        color: X.spawn,
        chars: [`@`]
    }, {
        name: `nop`,
        color: X.comment,
        chars: [`.`]
    }, {
        name: `movement`,
        color: X.movement,
        chars: [`v`, `V`, `<`, `>`, `^`, `X`, `Y`, `H`, `a`, `d`, `x`]
    }, {
        name: `io`,
        color: X.io,
        chars: [`s`, `S`, `r`, `R`, `U`, `q`]
    }, {
        name: `literal`,
        color: X.literal,
        chars: [`0`, `1`, `2`, `3`, `4`, `5`, `6`, `7`, `8`, `9`, "`"]
    }, {
        name: `register`,
        color: X.register,
        chars: [`M`, `W`, `b`, `m`, `]`]
    }, {
        name: `arithmetic`,
        color: X.arithmetic,
        chars: [`+`, `-`, `*`, `%`, `/`, `N`, `&`, `|`, `~`, `{`, `}`]
    }],
    Wn = (() => {
        let e = {};
        for (let t of Un)
            for (let n of t.chars) e[n] = t.color;
        return e
    })();

function Gn({
    content: e,
    isWall: t,
    isPipe: n,
    isDisplayWall: r,
    inDisplay: i,
    inRoom: a,
    isSpecialWall: o,
    isSpecialMarker: s,
    validOps: c
}) {
    return t ? o ? X.ioRoomWall : X.wall : r ? X.display : n ? X.pipe : i ? e === ` ` ? X.displayScreen : /^[0-9a-f]$/.test(e) ? Hn(parseInt(e, 16)) : X.comment : e === ` ` ? null : a ? s ? X.ioRoomMarker : Wn[e] || (c && !c.has(e) ? X.comment : null) : X.comment
}
var Kn = 2,
    qn = {},
    Jn = new Set,
    Yn = new Map;

function Xn(e, t) {
    let n = Yn.get(t);
    if (n === void 0) {
        let r = e.measureText(`@M<>+0y`);
        n = r.actualBoundingBoxAscent === void 0 ? 0 : (r.actualBoundingBoxAscent - r.actualBoundingBoxDescent) / 2, Yn.set(t, n)
    }
    return n
}

function Zn(e, t) {
    let {
        width: n,
        height: r,
        originX: i,
        originY: a,
        visible: o,
        step: s,
        getDisplayCellContent: c,
        wallCells: l,
        roomCells: u,
        pipeCells: d,
        specialWallCells: f = Jn,
        specialMarkerCells: p = Jn,
        displayWallCells: m,
        displayCells: h,
        validOps: g,
        cellTints: _,
        cellGlyphs: v,
        linkTints: y,
        overlayTints: b,
        overlayGlyphs: x,
        ghostGlyphs: S,
        flowCells: C = qn,
        flowTerminals: w = qn,
        selectedCell: T,
        areaBounds: ee,
        errorCell: E,
        resolveColor: D
    } = t, {
        cellSize: O,
        fontSize: k,
        padding: j
    } = s, te = null, M = t => {
        t !== te && (e.fillStyle = t, te = t)
    };
    M(D(j > 0 ? X.cellGap : X.cellDefault)), e.fillRect(0, 0, n + 1, r + 1);
    let N = k === 0,
        re = 0;
    if (!N) {
        let t = `${k}px monospace`;
        e.font = t, e.textAlign = `center`, e.textBaseline = `middle`, re = Xn(e, t)
    }
    let P = O - 2 * j,
        F = O / 2,
        I = O / 4,
        ie = [],
        ae = [],
        oe = [],
        se = [],
        ce = [],
        le = [],
        ue = [],
        L = [],
        R = [],
        z = [];
    for (let t = 0; t < o.cellsTall; t++) {
        let n = o.top + t,
            r = n * O - a;
        for (let t = 0; t < o.cellsWide; t++) {
            let a = o.left + t,
                s = a * O - i,
                E = A(a, n),
                k = c(a, n) || ` `,
                te = C[E];
            te !== void 0 && (ue.push(te), L.push(s), R.push(r), z.push(w[E]));
            let N = _[E],
                re = T && T.x === a && T.y === n || ee && ne(a, n, ee),
                F = b[E];
            F || (re ? F = X.selection : N ? F = N : y[E] ? F = y[E] : (k !== ` ` || l.has(E) || d.has(E) || h.has(E)) && (F = Gn({
                content: k,
                isWall: l.has(E),
                isPipe: d.has(E),
                isDisplayWall: m.has(E),
                inDisplay: h.has(E),
                inRoom: u.has(E),
                isSpecialWall: f.has(E),
                isSpecialMarker: p.has(E),
                validOps: g
            }))), j > 0 ? (M(D(F || X.cellDefault)), e.beginPath(), e.roundRect(s + j, r + j, P, P, Kn), e.fill()) : F && (M(D(F)), e.fillRect(s, r, O, O));
            let I = x[E],
                de = !1;
            if (I === void 0) {
                let e = S[E];
                e === void 0 ? I = v[E] ?? k : (I = e, de = !0)
            }
            I !== ` ` && I !== `` && (de ? (se.push(I), ce.push(s), le.push(r)) : (ie.push(I), ae.push(s), oe.push(r)))
        }
    }
    let de = (t, n, r) => {
            for (let i = 0; i < t.length; i++) N ? e.fillRect(n[i] + I, r[i] + I, O - 2 * I, O - 2 * I) : e.fillText(t[i], n[i] + F, r[i] + F + re)
        },
        fe = () => {
            M(D(X.flowWash));
            for (let t = 0; t < ue.length; t++) e.fillRect(L[t], R[t], O, O)
        },
        pe = () => {
            e.strokeStyle = D(X.flowLine), e.lineWidth = Math.max(1, O / 12);
            let t = Math.max(2, Math.round(O / 7));
            e.setLineDash([t, t]), e.beginPath();
            for (let t = 0; t < ue.length; t++) {
                let n = ue[t],
                    r = L[t] + F,
                    i = R[t] + F;
                n & 1 && (e.moveTo(r, i), e.lineTo(r + F, i)), n & 2 && (e.moveTo(r, i), e.lineTo(r - F, i)), n & 4 && (e.moveTo(r, i), e.lineTo(r, i + F)), n & 8 && (e.moveTo(r, i), e.lineTo(r, i - F))
            }
            e.stroke(), e.setLineDash([])
        },
        me = () => {
            let t = Math.max(1.5, O / 8);
            for (let n = 0; n < ue.length; n++) {
                let r = z[n];
                r !== void 0 && (M(D(r === `halt` ? X.flowHalt : X.flowDeath)), e.beginPath(), e.arc(L[n] + F, R[n] + F, t, 0, 2 * Math.PI), e.fill())
            }
        };
    if (ue.length > 0 && fe(), E) {
        let t = E.x * O - i,
            n = E.y * O - a,
            r = Math.max(2, Math.min(4, Math.round(O / 4))),
            o = r + 2,
            s = O - 2 * j - o >= 3,
            c = j + (s ? o : r) / 2,
            l = O - 2 * c,
            u = (r, i) => {
                e.strokeStyle = D(i), e.lineWidth = r, e.beginPath(), e.roundRect(t + c, n + c, l, l, Kn), e.stroke()
            };
        s && u(o, X.errorHalo), u(r, X.errorBorder)
    }
    M(D(X.glyph)), de(ie, ae, oe), M(D(X.glyphGhost)), de(se, ce, le), ue.length > 0 && (pe(), me())
}
var Qn = r.canvas`
  position: absolute;
  top: 0;
  left: 0;
`;

function $n(e, t) {
    if (e === t) return !0;
    let n = Object.keys(e);
    if (n.length !== Object.keys(t).length) return !1;
    for (let r of n)
        if (e[r] !== t[r]) return !1;
    return !0
}

function er({
    width: e,
    height: t,
    inputs: n,
    onClick: r
}) {
    let i = S.useRef(null),
        a = S.useRef(null),
        [o, s] = S.useReducer(e => e + 1, 0);
    return S.useEffect(() => {
        let e = window.matchMedia(`(resolution: ${window.devicePixelRatio}dppx)`);
        return e.addEventListener?.(`change`, s), () => e.removeEventListener?.(`change`, s)
    }, [o]), S.useLayoutEffect(() => {
        let r = i.current;
        if (!r || !e || !t) return;
        let o = window.devicePixelRatio || 1,
            s = a.current;
        if (s && s.width === e && s.height === t && s.dpr === o && $n(s.inputs, n)) return;
        a.current = {
            width: e,
            height: t,
            dpr: o,
            inputs: n
        };
        let c = Math.round(e * o),
            l = Math.round(t * o);
        r.width !== c && (r.width = c), r.height !== l && (r.height = l);
        let u = r.getContext(`2d`);
        u.setTransform(o, 0, 0, o, 0, 0), Zn(u, {
            ...n,
            width: e,
            height: t,
            resolveColor: Bn
        })
    }), (0, q.jsx)(Qn, {
        ref: i,
        onClick: r,
        style: {
            width: e,
            height: t
        }
    })
}
var tr = r.textarea`
  position: fixed;
  top: 0;
  left: 0;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
  user-select: none;
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
`,
    nr = [`ArrowUp`, `ArrowDown`, `ArrowLeft`, `ArrowRight`, `Enter`, ` `, `Tab`];

function rr({
    autoFocus: e = !1,
    currentSelection: t,
    setCellContent: n,
    setCellsBulk: r,
    clearSelection: i,
    getSelectionAsText: a,
    readOnly: o,
    spacePressed: s,
    onAfterType: c,
    onBackspace: l,
    onEscape: u,
    onCopyToGhost: d,
    onDismissGhost: f
}) {
    let p = S.useRef(null),
        m = S.useMemo(() => P(t) ? t.cell : null, [t]),
        h = S.useMemo(() => F(t) ? t : null, [t]),
        g = !!(m || h);
    S.useEffect(() => {
        p.current && g && (s ? p.current.blur() : p.current.focus())
    }, [g, t, s]);
    let _ = S.useCallback(e => {
            p.current && g && (s || e.relatedTarget && e.relatedTarget !== p.current || p.current.focus())
        }, [g, s]),
        v = S.useCallback(e => {
            if (e.preventDefault(), o) return;
            let t = e.data;
            t && m && (f?.(), n({
                x: m.x,
                y: m.y,
                content: t
            }), c?.(t))
        }, [m, n, o, c, f]),
        y = S.useCallback(e => {
            let t = N(e),
                n = [];
            for (let e = t.left; e <= t.right; e++)
                for (let r = t.top; r <= t.bottom; r++) n.push({
                    x: e,
                    y: r,
                    content: ``
                });
            r(n)
        }, [r]),
        b = S.useCallback(e => {
            e.preventDefault(), !o && (m && n({
                x: m.x,
                y: m.y,
                content: ``
            }), h && y(h))
        }, [m, h, n, y, o]),
        x = S.useCallback(e => {
            e.preventDefault(), !o && (f?.(), m ? l?.({
                shiftPressed: e.shiftKey
            }) : h && y(h))
        }, [m, h, l, y, o, f]),
        C = S.useCallback(e => {
            if (nr.includes(e.key)) {
                e.preventDefault();
                return
            }
            if (e.key === `Enter`) {
                if (e.preventDefault(), !p.current) return;
                p.current.blur(), Ht(p.current)
            } else if (e.key === `Escape`) {
                if (e.preventDefault(), f?.(), u?.()) return;
                i(), p.current.blur(), Ht(p.current)
            } else(e.key === `Backspace` || e.key === `Delete`) && x(e)
        }, [i, x, u, f]),
        w = S.useCallback(e => {
            e.preventDefault();
            let t = a();
            t && (e.clipboardData.setData(`text/plain`, t), o || d?.(t))
        }, [a, d, o]);
    return (0, q.jsx)(tr, {
        ref: p,
        onBlur: _,
        onBeforeInput: v,
        onKeyDown: C,
        autoFocus: e,
        autoCapitalize: `off`,
        autoCorrect: `off`,
        autoComplete: `off`,
        spellCheck: !1,
        onCopy: w,
        onCut: S.useCallback(e => {
            e.preventDefault(), w(e), b(e)
        }, [w, b]),
        onPaste: S.useCallback(e => {
            if (e.preventDefault(), o) return;
            let t = e.clipboardData.getData(`text/plain`);
            if (!t) return;
            let n, i;
            if (m) n = m.x, i = m.y;
            else if (h) {
                let e = N(h);
                n = e.left, i = e.top
            } else return;
            let a = ie(t).map(e => ({
                x: n + e.dx,
                y: i + e.dy,
                content: e.content
            }));
            a.length !== 0 && (r(a), f?.())
        }, [m, h, r, o, f]),
        "data-littleman-hidden-input": !0
    })
}
var ir = S.useId || (() => void 0),
    ar = 0;

function or(e) {
    let [t, n] = S.useState(ir());
    return p(() => {
        e || n(e => e ?? String(ar++))
    }, [e]), e || (t ? `radix-${t}` : ``)
}
var sr = Object.freeze({
        position: `absolute`,
        border: 0,
        width: 1,
        height: 1,
        padding: 0,
        margin: -1,
        overflow: `hidden`,
        clip: `rect(0, 0, 0, 0)`,
        whiteSpace: `nowrap`,
        wordWrap: `normal`
    }),
    cr = `VisuallyHidden`,
    lr = S.forwardRef((e, t) => (0, q.jsx)(l.span, {
        ...e,
        ref: t,
        style: {
            ...sr,
            ...e.style
        }
    }));
lr.displayName = cr;
var ur = lr,
    [dr, fr] = d(`Tooltip`, [s]),
    pr = s(),
    mr = `TooltipProvider`,
    hr = 700,
    gr = `tooltip.open`,
    [_r, vr] = dr(mr),
    yr = e => {
        let {
            __scopeTooltip: t,
            delayDuration: n = hr,
            skipDelayDuration: r = 300,
            disableHoverableContent: i = !1,
            children: a
        } = e, o = S.useRef(!0), s = S.useRef(!1), c = S.useRef(0);
        return S.useEffect(() => {
            let e = c.current;
            return () => window.clearTimeout(e)
        }, []), (0, q.jsx)(_r, {
            scope: t,
            isOpenDelayedRef: o,
            delayDuration: n,
            onOpen: S.useCallback(() => {
                window.clearTimeout(c.current), o.current = !1
            }, []),
            onClose: S.useCallback(() => {
                window.clearTimeout(c.current), c.current = window.setTimeout(() => o.current = !0, r)
            }, [r]),
            isPointerInTransitRef: s,
            onPointerInTransitChange: S.useCallback(e => {
                s.current = e
            }, []),
            disableHoverableContent: i,
            children: a
        })
    };
yr.displayName = mr;
var br = `Tooltip`,
    [xr, Sr] = dr(br),
    Cr = e => {
        let {
            __scopeTooltip: t,
            children: n,
            open: r,
            defaultOpen: i,
            onOpenChange: a,
            disableHoverableContent: o,
            delayDuration: s
        } = e, c = vr(br, e.__scopeTooltip), l = pr(t), [u, d] = S.useState(null), f = or(), p = S.useRef(0), m = o ?? c.disableHoverableContent, h = s ?? c.delayDuration, g = S.useRef(!1), [_, v] = b({
            prop: r,
            defaultProp: i ?? !1,
            onChange: e => {
                e ? (c.onOpen(), document.dispatchEvent(new CustomEvent(gr))) : c.onClose(), a?.(e)
            },
            caller: br
        }), x = S.useMemo(() => _ ? g.current ? `delayed-open` : `instant-open` : `closed`, [_]), C = S.useCallback(() => {
            window.clearTimeout(p.current), p.current = 0, g.current = !1, v(!0)
        }, [v]), w = S.useCallback(() => {
            window.clearTimeout(p.current), p.current = 0, v(!1)
        }, [v]), T = S.useCallback(() => {
            window.clearTimeout(p.current), p.current = window.setTimeout(() => {
                g.current = !0, v(!0), p.current = 0
            }, h)
        }, [h, v]);
        return S.useEffect(() => () => {
            p.current &&= (window.clearTimeout(p.current), 0)
        }, []), (0, q.jsx)(y, {
            ...l,
            children: (0, q.jsx)(xr, {
                scope: t,
                contentId: f,
                open: _,
                stateAttribute: x,
                trigger: u,
                onTriggerChange: d,
                onTriggerEnter: S.useCallback(() => {
                    c.isOpenDelayedRef.current ? T() : C()
                }, [c.isOpenDelayedRef, T, C]),
                onTriggerLeave: S.useCallback(() => {
                    m ? w() : (window.clearTimeout(p.current), p.current = 0)
                }, [w, m]),
                onOpen: C,
                onClose: w,
                disableHoverableContent: m,
                children: n
            })
        })
    };
Cr.displayName = br;
var wr = `TooltipTrigger`,
    Tr = S.forwardRef((e, t) => {
        let {
            __scopeTooltip: n,
            ...r
        } = e, i = Sr(wr, n), o = vr(wr, n), s = pr(n), c = u(t, S.useRef(null), i.onTriggerChange), d = S.useRef(!1), p = S.useRef(!1), m = S.useCallback(() => d.current = !1, []);
        return S.useEffect(() => () => document.removeEventListener(`pointerup`, m), [m]), (0, q.jsx)(f, {
            asChild: !0,
            ...s,
            children: (0, q.jsx)(l.button, {
                "aria-describedby": i.open ? i.contentId : void 0,
                "data-state": i.stateAttribute,
                ...r,
                ref: c,
                onPointerMove: a(e.onPointerMove, e => {
                    e.pointerType !== `touch` && !p.current && !o.isPointerInTransitRef.current && (i.onTriggerEnter(), p.current = !0)
                }),
                onPointerLeave: a(e.onPointerLeave, () => {
                    i.onTriggerLeave(), p.current = !1
                }),
                onPointerDown: a(e.onPointerDown, () => {
                    i.open && i.onClose(), d.current = !0, document.addEventListener(`pointerup`, m, {
                        once: !0
                    })
                }),
                onFocus: a(e.onFocus, () => {
                    d.current || i.onOpen()
                }),
                onBlur: a(e.onBlur, i.onClose),
                onClick: a(e.onClick, i.onClose)
            })
        })
    });
Tr.displayName = wr;
var Er = `TooltipPortal`,
    [Dr, Or] = dr(Er, {
        forceMount: void 0
    }),
    kr = e => {
        let {
            __scopeTooltip: t,
            forceMount: n,
            children: r,
            container: i
        } = e, a = Sr(Er, t);
        return (0, q.jsx)(Dr, {
            scope: t,
            forceMount: n,
            children: (0, q.jsx)(h, {
                present: n || a.open,
                children: (0, q.jsx)(v, {
                    asChild: !0,
                    container: i,
                    children: r
                })
            })
        })
    };
kr.displayName = Er;
var Ar = `TooltipContent`,
    jr = S.forwardRef((e, t) => {
        let n = Or(Ar, e.__scopeTooltip),
            {
                forceMount: r = n.forceMount,
                side: i = `top`,
                ...a
            } = e,
            o = Sr(Ar, e.__scopeTooltip);
        return (0, q.jsx)(h, {
            present: r || o.open,
            children: o.disableHoverableContent ? (0, q.jsx)(Ir, {
                side: i,
                ...a,
                ref: t
            }) : (0, q.jsx)(Mr, {
                side: i,
                ...a,
                ref: t
            })
        })
    }),
    Mr = S.forwardRef((e, t) => {
        let n = Sr(Ar, e.__scopeTooltip),
            r = vr(Ar, e.__scopeTooltip),
            i = S.useRef(null),
            a = u(t, i),
            [o, s] = S.useState(null),
            {
                trigger: c,
                onClose: l
            } = n,
            d = i.current,
            {
                onPointerInTransitChange: f
            } = r,
            p = S.useCallback(() => {
                s(null), f(!1)
            }, [f]),
            m = S.useCallback((e, t) => {
                let n = e.currentTarget,
                    r = {
                        x: e.clientX,
                        y: e.clientY
                    },
                    i = Br(r, zr(r, n.getBoundingClientRect())),
                    a = Vr(t.getBoundingClientRect());
                s(Ur([...i, ...a])), f(!0)
            }, [f]);
        return S.useEffect(() => () => p(), [p]), S.useEffect(() => {
            if (c && d) {
                let e = e => m(e, d),
                    t = e => m(e, c);
                return c.addEventListener(`pointerleave`, e), d.addEventListener(`pointerleave`, t), () => {
                    c.removeEventListener(`pointerleave`, e), d.removeEventListener(`pointerleave`, t)
                }
            }
        }, [c, d, m, p]), S.useEffect(() => {
            if (o) {
                let e = e => {
                    let t = e.target,
                        n = {
                            x: e.clientX,
                            y: e.clientY
                        },
                        r = c?.contains(t) || d?.contains(t),
                        i = !Hr(n, o);
                    r ? p() : i && (p(), l())
                };
                return document.addEventListener(`pointermove`, e), () => document.removeEventListener(`pointermove`, e)
            }
        }, [c, d, o, l, p]), (0, q.jsx)(Ir, {
            ...e,
            ref: a
        })
    }),
    [Nr, Pr] = dr(br, {
        isInside: !1
    }),
    Fr = m(`TooltipContent`),
    Ir = S.forwardRef((e, t) => {
        let {
            __scopeTooltip: n,
            children: r,
            "aria-label": i,
            onEscapeKeyDown: a,
            onPointerDownOutside: o,
            ...s
        } = e, c = Sr(Ar, n), l = pr(n), {
            onClose: u
        } = c;
        return S.useEffect(() => (document.addEventListener(gr, u), () => document.removeEventListener(gr, u)), [u]), S.useEffect(() => {
            if (c.trigger) {
                let e = e => {
                    e.target?.contains(c.trigger) && u()
                };
                return window.addEventListener(`scroll`, e, {
                    capture: !0
                }), () => window.removeEventListener(`scroll`, e, {
                    capture: !0
                })
            }
        }, [c.trigger, u]), (0, q.jsx)(x, {
            asChild: !0,
            disableOutsidePointerEvents: !1,
            onEscapeKeyDown: a,
            onPointerDownOutside: o,
            onFocusOutside: e => e.preventDefault(),
            onDismiss: u,
            children: (0, q.jsxs)(g, {
                "data-state": c.stateAttribute,
                ...l,
                ...s,
                ref: t,
                style: {
                    ...s.style,
                    "--radix-tooltip-content-transform-origin": `var(--radix-popper-transform-origin)`,
                    "--radix-tooltip-content-available-width": `var(--radix-popper-available-width)`,
                    "--radix-tooltip-content-available-height": `var(--radix-popper-available-height)`,
                    "--radix-tooltip-trigger-width": `var(--radix-popper-anchor-width)`,
                    "--radix-tooltip-trigger-height": `var(--radix-popper-anchor-height)`
                },
                children: [(0, q.jsx)(Fr, {
                    children: r
                }), (0, q.jsx)(Nr, {
                    scope: n,
                    isInside: !0,
                    children: (0, q.jsx)(ur, {
                        id: c.contentId,
                        role: `tooltip`,
                        children: i || r
                    })
                })]
            })
        })
    });
jr.displayName = Ar;
var Lr = `TooltipArrow`,
    Rr = S.forwardRef((e, t) => {
        let {
            __scopeTooltip: n,
            ...r
        } = e, i = pr(n);
        return Pr(Lr, n).isInside ? null : (0, q.jsx)(o, {
            ...i,
            ...r,
            ref: t
        })
    });
Rr.displayName = Lr;

function zr(e, t) {
    let n = Math.abs(t.top - e.y),
        r = Math.abs(t.bottom - e.y),
        i = Math.abs(t.right - e.x),
        a = Math.abs(t.left - e.x);
    switch (Math.min(n, r, i, a)) {
        case a:
            return `left`;
        case i:
            return `right`;
        case n:
            return `top`;
        case r:
            return `bottom`;
        default:
            throw Error(`unreachable`)
    }
}

function Br(e, t, n = 5) {
    let r = [];
    switch (t) {
        case `top`:
            r.push({
                x: e.x - n,
                y: e.y + n
            }, {
                x: e.x + n,
                y: e.y + n
            });
            break;
        case `bottom`:
            r.push({
                x: e.x - n,
                y: e.y - n
            }, {
                x: e.x + n,
                y: e.y - n
            });
            break;
        case `left`:
            r.push({
                x: e.x + n,
                y: e.y - n
            }, {
                x: e.x + n,
                y: e.y + n
            });
            break;
        case `right`:
            r.push({
                x: e.x - n,
                y: e.y - n
            }, {
                x: e.x - n,
                y: e.y + n
            });
            break
    }
    return r
}

function Vr(e) {
    let {
        top: t,
        right: n,
        bottom: r,
        left: i
    } = e;
    return [{
        x: i,
        y: t
    }, {
        x: n,
        y: t
    }, {
        x: n,
        y: r
    }, {
        x: i,
        y: r
    }]
}

function Hr(e, t) {
    let {
        x: n,
        y: r
    } = e, i = !1;
    for (let e = 0, a = t.length - 1; e < t.length; a = e++) {
        let o = t[e],
            s = t[a],
            c = o.x,
            l = o.y,
            u = s.x,
            d = s.y;
        l > r != d > r && n < (u - c) * (r - l) / (d - l) + c && (i = !i)
    }
    return i
}

function Ur(e) {
    let t = e.slice();
    return t.sort((e, t) => e.x < t.x ? -1 : e.x > t.x ? 1 : e.y < t.y ? -1 : +(e.y > t.y)), Wr(t)
}

function Wr(e) {
    if (e.length <= 1) return e.slice();
    let t = [];
    for (let n = 0; n < e.length; n++) {
        let r = e[n];
        for (; t.length >= 2;) {
            let e = t[t.length - 1],
                n = t[t.length - 2];
            if ((e.x - n.x) * (r.y - n.y) >= (e.y - n.y) * (r.x - n.x)) t.pop();
            else break
        }
        t.push(r)
    }
    t.pop();
    let n = [];
    for (let t = e.length - 1; t >= 0; t--) {
        let r = e[t];
        for (; n.length >= 2;) {
            let e = n[n.length - 1],
                t = n[n.length - 2];
            if ((e.x - t.x) * (r.y - t.y) >= (e.y - t.y) * (r.x - t.x)) n.pop();
            else break
        }
        n.push(r)
    }
    return n.pop(), t.length === 1 && n.length === 1 && t[0].x === n[0].x && t[0].y === n[0].y ? t : t.concat(n)
}
var Gr = yr,
    Kr = Cr,
    qr = Tr,
    Jr = kr,
    Yr = jr,
    Xr = Rr,
    Zr = t(((e, t) => {
        t.exports = `SECRET_DO_NOT_PASS_THIS_OR_YOU_WILL_BE_FIRED`
    })),
    Qr = t(((e, t) => {
        var n = Zr();

        function r() {}

        function i() {}
        i.resetWarningCache = r, t.exports = function() {
            function e(e, t, r, i, a, o) {
                if (o !== n) {
                    var s = Error("Calling PropTypes validators directly is not supported by the `prop-types` package. Use PropTypes.checkPropTypes() to call them. Read more at http://fb.me/use-check-prop-types");
                    throw s.name = `Invariant Violation`, s
                }
            }
            e.isRequired = e;

            function t() {
                return e
            }
            var a = {
                array: e,
                bigint: e,
                bool: e,
                func: e,
                number: e,
                object: e,
                string: e,
                symbol: e,
                any: e,
                arrayOf: t,
                element: e,
                elementType: e,
                instanceOf: t,
                node: e,
                objectOf: t,
                oneOf: t,
                oneOfType: t,
                shape: t,
                exact: t,
                checkPropTypes: i,
                resetWarningCache: r
            };
            return a.PropTypes = a, a
        }
    })),
    Z = n(t(((e, t) => {
        t.exports = Qr()()
    }))());

function $r() {
    return $r = Object.assign || function(e) {
        for (var t = 1; t < arguments.length; t++) {
            var n = arguments[t];
            for (var r in n) Object.prototype.hasOwnProperty.call(n, r) && (e[r] = n[r])
        }
        return e
    }, $r.apply(this, arguments)
}

function ei(e, t) {
    if (e == null) return {};
    var n = ti(e, t),
        r, i;
    if (Object.getOwnPropertySymbols) {
        var a = Object.getOwnPropertySymbols(e);
        for (i = 0; i < a.length; i++) r = a[i], !(t.indexOf(r) >= 0) && Object.prototype.propertyIsEnumerable.call(e, r) && (n[r] = e[r])
    }
    return n
}

function ti(e, t) {
    if (e == null) return {};
    var n = {},
        r = Object.keys(e),
        i, a;
    for (a = 0; a < r.length; a++) i = r[a], !(t.indexOf(i) >= 0) && (n[i] = e[i]);
    return n
}
var ni = (0, S.forwardRef)(function(e, t) {
    var n = e.color,
        r = n === void 0 ? `currentColor` : n,
        i = e.size,
        a = i === void 0 ? 24 : i,
        o = ei(e, [`color`, `size`]);
    return S.createElement(`svg`, $r({
        ref: t,
        xmlns: `http://www.w3.org/2000/svg`,
        width: a,
        height: a,
        viewBox: `0 0 24 24`,
        fill: `none`,
        stroke: r,
        strokeWidth: `2`,
        strokeLinecap: `round`,
        strokeLinejoin: `round`
    }, o), S.createElement(`polyline`, {
        points: `20 6 9 17 4 12`
    }))
});
ni.propTypes = {
    color: Z.default.string,
    size: Z.default.oneOfType([Z.default.string, Z.default.number])
}, ni.displayName = `Check`;

function ri() {
    return ri = Object.assign || function(e) {
        for (var t = 1; t < arguments.length; t++) {
            var n = arguments[t];
            for (var r in n) Object.prototype.hasOwnProperty.call(n, r) && (e[r] = n[r])
        }
        return e
    }, ri.apply(this, arguments)
}

function ii(e, t) {
    if (e == null) return {};
    var n = ai(e, t),
        r, i;
    if (Object.getOwnPropertySymbols) {
        var a = Object.getOwnPropertySymbols(e);
        for (i = 0; i < a.length; i++) r = a[i], !(t.indexOf(r) >= 0) && Object.prototype.propertyIsEnumerable.call(e, r) && (n[r] = e[r])
    }
    return n
}

function ai(e, t) {
    if (e == null) return {};
    var n = {},
        r = Object.keys(e),
        i, a;
    for (a = 0; a < r.length; a++) i = r[a], !(t.indexOf(i) >= 0) && (n[i] = e[i]);
    return n
}
var oi = (0, S.forwardRef)(function(e, t) {
    var n = e.color,
        r = n === void 0 ? `currentColor` : n,
        i = e.size,
        a = i === void 0 ? 24 : i,
        o = ii(e, [`color`, `size`]);
    return S.createElement(`svg`, ri({
        ref: t,
        xmlns: `http://www.w3.org/2000/svg`,
        width: a,
        height: a,
        viewBox: `0 0 24 24`,
        fill: `none`,
        stroke: r,
        strokeWidth: `2`,
        strokeLinecap: `round`,
        strokeLinejoin: `round`
    }, o), S.createElement(`path`, {
        d: `M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z`
    }))
});
oi.propTypes = {
    color: Z.default.string,
    size: Z.default.oneOfType([Z.default.string, Z.default.number])
}, oi.displayName = `Edit2`;

function si() {
    return si = Object.assign || function(e) {
        for (var t = 1; t < arguments.length; t++) {
            var n = arguments[t];
            for (var r in n) Object.prototype.hasOwnProperty.call(n, r) && (e[r] = n[r])
        }
        return e
    }, si.apply(this, arguments)
}

function ci(e, t) {
    if (e == null) return {};
    var n = li(e, t),
        r, i;
    if (Object.getOwnPropertySymbols) {
        var a = Object.getOwnPropertySymbols(e);
        for (i = 0; i < a.length; i++) r = a[i], !(t.indexOf(r) >= 0) && Object.prototype.propertyIsEnumerable.call(e, r) && (n[r] = e[r])
    }
    return n
}

function li(e, t) {
    if (e == null) return {};
    var n = {},
        r = Object.keys(e),
        i, a;
    for (a = 0; a < r.length; a++) i = r[a], !(t.indexOf(i) >= 0) && (n[i] = e[i]);
    return n
}
var ui = (0, S.forwardRef)(function(e, t) {
    var n = e.color,
        r = n === void 0 ? `currentColor` : n,
        i = e.size,
        a = i === void 0 ? 24 : i,
        o = ci(e, [`color`, `size`]);
    return S.createElement(`svg`, si({
        ref: t,
        xmlns: `http://www.w3.org/2000/svg`,
        width: a,
        height: a,
        viewBox: `0 0 24 24`,
        fill: `none`,
        stroke: r,
        strokeWidth: `2`,
        strokeLinecap: `round`,
        strokeLinejoin: `round`
    }, o), S.createElement(`rect`, {
        x: `2`,
        y: `3`,
        width: `20`,
        height: `14`,
        rx: `2`,
        ry: `2`
    }), S.createElement(`line`, {
        x1: `8`,
        y1: `21`,
        x2: `16`,
        y2: `21`
    }), S.createElement(`line`, {
        x1: `12`,
        y1: `17`,
        x2: `12`,
        y2: `21`
    }))
});
ui.propTypes = {
    color: Z.default.string,
    size: Z.default.oneOfType([Z.default.string, Z.default.number])
}, ui.displayName = `Monitor`;

function di() {
    return di = Object.assign || function(e) {
        for (var t = 1; t < arguments.length; t++) {
            var n = arguments[t];
            for (var r in n) Object.prototype.hasOwnProperty.call(n, r) && (e[r] = n[r])
        }
        return e
    }, di.apply(this, arguments)
}

function fi(e, t) {
    if (e == null) return {};
    var n = pi(e, t),
        r, i;
    if (Object.getOwnPropertySymbols) {
        var a = Object.getOwnPropertySymbols(e);
        for (i = 0; i < a.length; i++) r = a[i], !(t.indexOf(r) >= 0) && Object.prototype.propertyIsEnumerable.call(e, r) && (n[r] = e[r])
    }
    return n
}

function pi(e, t) {
    if (e == null) return {};
    var n = {},
        r = Object.keys(e),
        i, a;
    for (a = 0; a < r.length; a++) i = r[a], !(t.indexOf(i) >= 0) && (n[i] = e[i]);
    return n
}
var mi = (0, S.forwardRef)(function(e, t) {
    var n = e.color,
        r = n === void 0 ? `currentColor` : n,
        i = e.size,
        a = i === void 0 ? 24 : i,
        o = fi(e, [`color`, `size`]);
    return S.createElement(`svg`, di({
        ref: t,
        xmlns: `http://www.w3.org/2000/svg`,
        width: a,
        height: a,
        viewBox: `0 0 24 24`,
        fill: `none`,
        stroke: r,
        strokeWidth: `2`,
        strokeLinecap: `round`,
        strokeLinejoin: `round`
    }, o), S.createElement(`circle`, {
        cx: `12`,
        cy: `12`,
        r: `1`
    }), S.createElement(`circle`, {
        cx: `12`,
        cy: `5`,
        r: `1`
    }), S.createElement(`circle`, {
        cx: `12`,
        cy: `19`,
        r: `1`
    }))
});
mi.propTypes = {
    color: Z.default.string,
    size: Z.default.oneOfType([Z.default.string, Z.default.number])
}, mi.displayName = `MoreVertical`;

function hi() {
    return hi = Object.assign || function(e) {
        for (var t = 1; t < arguments.length; t++) {
            var n = arguments[t];
            for (var r in n) Object.prototype.hasOwnProperty.call(n, r) && (e[r] = n[r])
        }
        return e
    }, hi.apply(this, arguments)
}

function gi(e, t) {
    if (e == null) return {};
    var n = _i(e, t),
        r, i;
    if (Object.getOwnPropertySymbols) {
        var a = Object.getOwnPropertySymbols(e);
        for (i = 0; i < a.length; i++) r = a[i], !(t.indexOf(r) >= 0) && Object.prototype.propertyIsEnumerable.call(e, r) && (n[r] = e[r])
    }
    return n
}

function _i(e, t) {
    if (e == null) return {};
    var n = {},
        r = Object.keys(e),
        i, a;
    for (a = 0; a < r.length; a++) i = r[a], !(t.indexOf(i) >= 0) && (n[i] = e[i]);
    return n
}
var vi = (0, S.forwardRef)(function(e, t) {
    var n = e.color,
        r = n === void 0 ? `currentColor` : n,
        i = e.size,
        a = i === void 0 ? 24 : i,
        o = gi(e, [`color`, `size`]);
    return S.createElement(`svg`, hi({
        ref: t,
        xmlns: `http://www.w3.org/2000/svg`,
        width: a,
        height: a,
        viewBox: `0 0 24 24`,
        fill: `none`,
        stroke: r,
        strokeWidth: `2`,
        strokeLinecap: `round`,
        strokeLinejoin: `round`
    }, o), S.createElement(`path`, {
        d: `M3 3l7.07 16.97 2.51-7.39 7.39-2.51L3 3z`
    }), S.createElement(`path`, {
        d: `M13 13l6 6`
    }))
});
vi.propTypes = {
    color: Z.default.string,
    size: Z.default.oneOfType([Z.default.string, Z.default.number])
}, vi.displayName = `MousePointer`;

function yi() {
    return yi = Object.assign || function(e) {
        for (var t = 1; t < arguments.length; t++) {
            var n = arguments[t];
            for (var r in n) Object.prototype.hasOwnProperty.call(n, r) && (e[r] = n[r])
        }
        return e
    }, yi.apply(this, arguments)
}

function bi(e, t) {
    if (e == null) return {};
    var n = xi(e, t),
        r, i;
    if (Object.getOwnPropertySymbols) {
        var a = Object.getOwnPropertySymbols(e);
        for (i = 0; i < a.length; i++) r = a[i], !(t.indexOf(r) >= 0) && Object.prototype.propertyIsEnumerable.call(e, r) && (n[r] = e[r])
    }
    return n
}

function xi(e, t) {
    if (e == null) return {};
    var n = {},
        r = Object.keys(e),
        i, a;
    for (a = 0; a < r.length; a++) i = r[a], !(t.indexOf(i) >= 0) && (n[i] = e[i]);
    return n
}
var Si = (0, S.forwardRef)(function(e, t) {
    var n = e.color,
        r = n === void 0 ? `currentColor` : n,
        i = e.size,
        a = i === void 0 ? 24 : i,
        o = bi(e, [`color`, `size`]);
    return S.createElement(`svg`, yi({
        ref: t,
        xmlns: `http://www.w3.org/2000/svg`,
        width: a,
        height: a,
        viewBox: `0 0 24 24`,
        fill: `none`,
        stroke: r,
        strokeWidth: `2`,
        strokeLinecap: `round`,
        strokeLinejoin: `round`
    }, o), S.createElement(`line`, {
        x1: `12`,
        y1: `5`,
        x2: `12`,
        y2: `19`
    }), S.createElement(`line`, {
        x1: `5`,
        y1: `12`,
        x2: `19`,
        y2: `12`
    }))
});
Si.propTypes = {
    color: Z.default.string,
    size: Z.default.oneOfType([Z.default.string, Z.default.number])
}, Si.displayName = `Plus`;

function Ci() {
    return Ci = Object.assign || function(e) {
        for (var t = 1; t < arguments.length; t++) {
            var n = arguments[t];
            for (var r in n) Object.prototype.hasOwnProperty.call(n, r) && (e[r] = n[r])
        }
        return e
    }, Ci.apply(this, arguments)
}

function wi(e, t) {
    if (e == null) return {};
    var n = Ti(e, t),
        r, i;
    if (Object.getOwnPropertySymbols) {
        var a = Object.getOwnPropertySymbols(e);
        for (i = 0; i < a.length; i++) r = a[i], !(t.indexOf(r) >= 0) && Object.prototype.propertyIsEnumerable.call(e, r) && (n[r] = e[r])
    }
    return n
}

function Ti(e, t) {
    if (e == null) return {};
    var n = {},
        r = Object.keys(e),
        i, a;
    for (a = 0; a < r.length; a++) i = r[a], !(t.indexOf(i) >= 0) && (n[i] = e[i]);
    return n
}
var Ei = (0, S.forwardRef)(function(e, t) {
    var n = e.color,
        r = n === void 0 ? `currentColor` : n,
        i = e.size,
        a = i === void 0 ? 24 : i,
        o = wi(e, [`color`, `size`]);
    return S.createElement(`svg`, Ci({
        ref: t,
        xmlns: `http://www.w3.org/2000/svg`,
        width: a,
        height: a,
        viewBox: `0 0 24 24`,
        fill: `none`,
        stroke: r,
        strokeWidth: `2`,
        strokeLinecap: `round`,
        strokeLinejoin: `round`
    }, o), S.createElement(`rect`, {
        x: `3`,
        y: `3`,
        width: `18`,
        height: `18`,
        rx: `2`,
        ry: `2`
    }))
});
Ei.propTypes = {
    color: Z.default.string,
    size: Z.default.oneOfType([Z.default.string, Z.default.number])
}, Ei.displayName = `Square`;

function Di() {
    return Di = Object.assign || function(e) {
        for (var t = 1; t < arguments.length; t++) {
            var n = arguments[t];
            for (var r in n) Object.prototype.hasOwnProperty.call(n, r) && (e[r] = n[r])
        }
        return e
    }, Di.apply(this, arguments)
}

function Oi(e, t) {
    if (e == null) return {};
    var n = ki(e, t),
        r, i;
    if (Object.getOwnPropertySymbols) {
        var a = Object.getOwnPropertySymbols(e);
        for (i = 0; i < a.length; i++) r = a[i], !(t.indexOf(r) >= 0) && Object.prototype.propertyIsEnumerable.call(e, r) && (n[r] = e[r])
    }
    return n
}

function ki(e, t) {
    if (e == null) return {};
    var n = {},
        r = Object.keys(e),
        i, a;
    for (a = 0; a < r.length; a++) i = r[a], !(t.indexOf(i) >= 0) && (n[i] = e[i]);
    return n
}
var Ai = (0, S.forwardRef)(function(e, t) {
    var n = e.color,
        r = n === void 0 ? `currentColor` : n,
        i = e.size,
        a = i === void 0 ? 24 : i,
        o = Oi(e, [`color`, `size`]);
    return S.createElement(`svg`, Di({
        ref: t,
        xmlns: `http://www.w3.org/2000/svg`,
        width: a,
        height: a,
        viewBox: `0 0 24 24`,
        fill: `none`,
        stroke: r,
        strokeWidth: `2`,
        strokeLinecap: `round`,
        strokeLinejoin: `round`
    }, o), S.createElement(`polyline`, {
        points: `3 6 5 6 21 6`
    }), S.createElement(`path`, {
        d: `M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2`
    }), S.createElement(`line`, {
        x1: `10`,
        y1: `11`,
        x2: `10`,
        y2: `17`
    }), S.createElement(`line`, {
        x1: `14`,
        y1: `11`,
        x2: `14`,
        y2: `17`
    }))
});
Ai.propTypes = {
    color: Z.default.string,
    size: Z.default.oneOfType([Z.default.string, Z.default.number])
}, Ai.displayName = `Trash2`;

function ji() {
    return ji = Object.assign || function(e) {
        for (var t = 1; t < arguments.length; t++) {
            var n = arguments[t];
            for (var r in n) Object.prototype.hasOwnProperty.call(n, r) && (e[r] = n[r])
        }
        return e
    }, ji.apply(this, arguments)
}

function Mi(e, t) {
    if (e == null) return {};
    var n = Ni(e, t),
        r, i;
    if (Object.getOwnPropertySymbols) {
        var a = Object.getOwnPropertySymbols(e);
        for (i = 0; i < a.length; i++) r = a[i], !(t.indexOf(r) >= 0) && Object.prototype.propertyIsEnumerable.call(e, r) && (n[r] = e[r])
    }
    return n
}

function Ni(e, t) {
    if (e == null) return {};
    var n = {},
        r = Object.keys(e),
        i, a;
    for (a = 0; a < r.length; a++) i = r[a], !(t.indexOf(i) >= 0) && (n[i] = e[i]);
    return n
}
var Pi = (0, S.forwardRef)(function(e, t) {
    var n = e.color,
        r = n === void 0 ? `currentColor` : n,
        i = e.size,
        a = i === void 0 ? 24 : i,
        o = Mi(e, [`color`, `size`]);
    return S.createElement(`svg`, ji({
        ref: t,
        xmlns: `http://www.w3.org/2000/svg`,
        width: a,
        height: a,
        viewBox: `0 0 24 24`,
        fill: `none`,
        stroke: r,
        strokeWidth: `2`,
        strokeLinecap: `round`,
        strokeLinejoin: `round`
    }, o), S.createElement(`line`, {
        x1: `18`,
        y1: `6`,
        x2: `6`,
        y2: `18`
    }), S.createElement(`line`, {
        x1: `6`,
        y1: `6`,
        x2: `18`,
        y2: `18`
    }))
});
Pi.propTypes = {
    color: Z.default.string,
    size: Z.default.oneOfType([Z.default.string, Z.default.number])
}, Pi.displayName = `X`;
var Fi = r.div`
  position: absolute;
  bottom: 6px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 0;
  padding: 2px;
  background-color: var(--color-stone-200);
  border: 1px solid var(--color-blue-800);
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
  z-index: 100;
`,
    Ii = r(Yr)`
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px 8px;
  line-height: 1;
  background-color: var(--color-blue-700);
  color: var(--color-stone-100);
  border-radius: 8px;
  font-size: 14px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  user-select: none;
  z-index: 200;
`,
    Li = r(Xr)`
  fill: var(--color-blue-700);
`,
    Ri = r.span`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  aspect-ratio: 1;
  border-radius: 6px;
  background-color: ${e=>e.$active?`var(--color-blue-700)`:`transparent`};
  color: ${e=>e.$active?`var(--color-stone-200)`:`var(--color-blue-800)`};
  transition: background-color 0.08s;
`,
    zi = r.button`
  display: flex;
  padding: 2px;
  background: transparent;
  border: none;
  cursor: pointer;

  &:hover ${Ri} {
    background-color: ${e=>e.$active?`var(--color-blue-700)`:`var(--color-blue-300)`};
  }

  &:focus-visible ${Ri} {
    outline: 2px solid var(--color-blue-500);
    outline-offset: 1px;
  }

  &:disabled {
    cursor: not-allowed;
  }

  &:disabled ${Ri} {
    opacity: 0.3;
  }
`,
    Bi = 20,
    Vi = [{
        id: Y.SELECT,
        key: `V`,
        label: `Select`,
        Icon: vi
    }, {
        id: Y.HAND,
        key: `H`,
        label: `Hand`,
        Icon: ({
            size: e = Bi
        }) => (0, q.jsxs)(`svg`, {
            width: e,
            height: e,
            viewBox: `0 0 24 24`,
            fill: `none`,
            stroke: `currentColor`,
            strokeWidth: `2`,
            strokeLinecap: `round`,
            strokeLinejoin: `round`,
            children: [(0, q.jsx)(`path`, {
                d: `M18 11V6a2 2 0 0 0-4 0v5`
            }), (0, q.jsx)(`path`, {
                d: `M14 10V4a2 2 0 0 0-4 0v6`
            }), (0, q.jsx)(`path`, {
                d: `M10 10.5V6a2 2 0 0 0-4 0v8`
            }), (0, q.jsx)(`path`, {
                d: `M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15`
            })]
        })
    }, {
        id: Y.ROOM,
        key: `R`,
        label: `Room`,
        Icon: Ei
    }, {
        id: Y.PIPE,
        key: `P`,
        label: `Pipe`,
        Icon: ({
            size: e = Bi
        }) => (0, q.jsxs)(`svg`, {
            width: e,
            height: e,
            viewBox: `0 0 24 24`,
            fill: `none`,
            stroke: `currentColor`,
            strokeWidth: `2`,
            strokeLinecap: `round`,
            strokeLinejoin: `round`,
            children: [(0, q.jsx)(`polyline`, {
                points: `3 5 8 12 3 19`
            }), (0, q.jsx)(`line`, {
                x1: `10`,
                y1: `12`,
                x2: `14`,
                y2: `12`
            }), (0, q.jsx)(`polyline`, {
                points: `16 5 21 12 16 19`
            })]
        })
    }, {
        id: Y.DISPLAY,
        key: `D`,
        label: `Display`,
        Icon: ui
    }, {
        id: Y.MOVE,
        key: `M`,
        label: `Move room`,
        Icon: ({
            size: e = Bi
        }) => (0, q.jsxs)(`svg`, {
            width: e,
            height: e,
            viewBox: `0 0 24 24`,
            fill: `none`,
            stroke: `currentColor`,
            strokeWidth: `2`,
            strokeLinecap: `round`,
            strokeLinejoin: `round`,
            children: [(0, q.jsx)(`rect`, {
                x: `2`,
                y: `8`,
                width: `7`,
                height: `8`,
                rx: `1`
            }), (0, q.jsx)(`rect`, {
                x: `15`,
                y: `8`,
                width: `7`,
                height: `8`,
                rx: `1`
            }), (0, q.jsx)(`line`, {
                x1: `9`,
                y1: `12`,
                x2: `13`,
                y2: `12`
            }), (0, q.jsx)(`polyline`, {
                points: `11 10 13 12 11 14`
            })]
        })
    }];

function Hi({
    tool: e,
    setTool: t,
    hidden: n,
    disabledTools: r = []
}) {
    if (n) return null;
    let i = new Set(r);
    return (0, q.jsx)(Gr, {
        delayDuration: 400,
        skipDelayDuration: 300,
        children: (0, q.jsx)(Fi, {
            children: Vi.map(({
                id: n,
                key: r,
                label: a,
                Icon: o
            }) => {
                let s = i.has(n);
                return (0, q.jsxs)(Kr, {
                    children: [(0, q.jsx)(qr, {
                        asChild: !0,
                        children: (0, q.jsx)(zi, {
                            $active: e === n,
                            disabled: s,
                            tabIndex: -1,
                            onClick: e => {
                                t(n), e.currentTarget.blur()
                            },
                            children: (0, q.jsx)(Ri, {
                                $active: e === n,
                                children: (0, q.jsx)(o, {
                                    size: Bi
                                })
                            })
                        })
                    }), (0, q.jsx)(Jr, {
                        children: (0, q.jsxs)(Ii, {
                            side: `top`,
                            sideOffset: 4,
                            children: [a, ` — `, r, (0, q.jsx)(Li, {})]
                        })
                    })]
                }, n)
            })
        })
    })
}
var Ui = r.div`
  background-color: var(--color-stone-800);
  border: 1px solid var(--color-stone-600);
  border-radius: 3px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
  font-family: monospace;
  font-size: 12px;
`,
    Wi = `var(--color-stone-400)`,
    Gi = `var(--color-amber-300)`;

function Ki(e, t) {
    let n = String(e);
    return n.length <= t ? {
        text: n,
        title: void 0
    } : {
        text: n.slice(0, t - 1) + `…`,
        title: n
    }
}
var qi = 7,
    Ji = r(Ui)`
  display: inline-flex;
  flex-direction: column;
  gap: 2px;
  padding: 4px 8px;
  color: ${Wi};
  letter-spacing: 0.04em;
  white-space: nowrap;
`,
    Yi = r.span`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  opacity: ${({$halted:e})=>e?.5:1};
`,
    Xi = r.span`
  color: ${Gi};
`;

function Zi({
    value: e
}) {
    let {
        text: t,
        title: n
    } = Ki(e, qi);
    return (0, q.jsx)(Xi, {
        title: n,
        children: t
    })
}

function Qi({
    runners: e
}) {
    return (0, q.jsx)(Ji, {
        children: e.map(e => (0, q.jsxs)(Yi, {
            $halted: e.halted,
            children: [(0, q.jsx)(`span`, {
                children: `A`
            }), (0, q.jsx)(Zi, {
                value: e.a
            }), (0, q.jsx)(`span`, {
                children: `B`
            }), (0, q.jsx)(Zi, {
                value: e.b
            }), (0, q.jsx)(`span`, {
                children: `BP`
            }), (0, q.jsx)(Zi, {
                value: e.backpack
            })]
        }, e.id))
    })
}
var $i = r.div`
  display: flex;
  flex-direction: column;
  align-items: center;
`,
    ea = r(Ui).attrs({
        as: `button`
    })`
  cursor: pointer;
  position: relative;
  z-index: 1;
  min-width: 24px;
  height: 16px;
  padding: 0;
  line-height: 1;
  color: ${Gi};
  box-shadow: none;
  border-bottom-style: ${({$attached:e})=>e?`
none`:`
solid`};
  border-radius: ${({$attached:e})=>e?`
6 px 6 px 0 0`:`
3 px`};
  margin-bottom: ${({$attached:e})=>e?` - 1 px`:`
0`};
`;

function ta({
    runners: e,
    collapsed: t,
    toggle: n
}) {
    return (0, q.jsxs)($i, {
        children: [(0, q.jsx)(ea, {
            $attached: !t,
            onClick: n,
            children: t ? `+` : `–`
        }), !t && (0, q.jsx)(Qi, {
            runners: e
        })]
    })
}
var na = (...e) => e.filter((e, t, n) => !!e && e.trim() !== `` && n.indexOf(e) === t).join(` `).trim(),
    ra = e => e.replace(/([a-z0-9])([A-Z])/g, `$1-$2`).toLowerCase(),
    ia = e => e.replace(/^([A-Z])|[\s-_]+(\w)/g, (e, t, n) => n ? n.toUpperCase() : t.toLowerCase()),
    aa = e => {
        let t = ia(e);
        return t.charAt(0).toUpperCase() + t.slice(1)
    },
    oa = {
        xmlns: `http://www.w3.org/2000/svg`,
        width: 24,
        height: 24,
        viewBox: `0 0 24 24`,
        fill: `none`,
        stroke: `currentColor`,
        strokeWidth: 2,
        strokeLinecap: `round`,
        strokeLinejoin: `round`
    },
    sa = e => {
        for (let t in e)
            if (t.startsWith(`aria-`) || t === `role` || t === `title`) return !0;
        return !1
    },
    ca = (0, S.createContext)({}),
    la = () => (0, S.useContext)(ca),
    ua = (0, S.forwardRef)(({
        color: e,
        size: t,
        strokeWidth: n,
        absoluteStrokeWidth: r,
        className: i = ``,
        children: a,
        iconNode: o,
        ...s
    }, c) => {
        let {
            size: l = 24,
            strokeWidth: u = 2,
            absoluteStrokeWidth: d = !1,
            color: f = `currentColor`,
            className: p = ``
        } = la() ?? {}, m = r ?? d ? Number(n ?? u) * 24 / Number(t ?? l) : n ?? u;
        return (0, S.createElement)(`svg`, {
            ref: c,
            ...oa,
            width: t ?? l ?? oa.width,
            height: t ?? l ?? oa.height,
            stroke: e ?? f,
            strokeWidth: m,
            className: na(`lucide`, p, i),
            ...!a && !sa(s) && {
                "aria-hidden": `true`
            },
            ...s
        }, [...o.map(([e, t]) => (0, S.createElement)(e, t)), ...Array.isArray(a) ? a : [a]])
    }),
    da = (e, t) => {
        let n = (0, S.forwardRef)(({
            className: n,
            ...r
        }, i) => (0, S.createElement)(ua, {
            ref: i,
            iconNode: t,
            className: na(`lucide-${ra(aa(e))}`, `lucide-${e}`, n),
            ...r
        }));
        return n.displayName = aa(e), n
    },
    fa = da(`pin`, [
        [`path`, {
            d: `M12 17v5`,
            key: `bb1du9`
        }],
        [`path`, {
            d: `M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z`,
            key: `1nkz8b`
        }]
    ]),
    pa = da(`rabbit`, [
        [`path`, {
            d: `M13 16a3 3 0 0 1 2.24 5`,
            key: `1epib5`
        }],
        [`path`, {
            d: `M18 12h.01`,
            key: `yjnet6`
        }],
        [`path`, {
            d: `M18 21h-8a4 4 0 0 1-4-4 7 7 0 0 1 7-7h.2L9.6 6.4a1 1 0 1 1 2.8-2.8L15.8 7h.2c3.3 0 6 2.7 6 6v1a2 2 0 0 1-2 2h-1a3 3 0 0 0-3 3`,
            key: `ue9ozu`
        }],
        [`path`, {
            d: `M20 8.54V4a2 2 0 1 0-4 0v3`,
            key: `49iql8`
        }],
        [`path`, {
            d: `M7.612 12.524a3 3 0 1 0-1.6 4.3`,
            key: `1e33i0`
        }]
    ]),
    ma = da(`turtle`, [
        [`path`, {
            d: `m12 10 2 4v3a1 1 0 0 0 1 1h2a1 1 0 0 0 1-1v-3a8 8 0 1 0-16 0v3a1 1 0 0 0 1 1h2a1 1 0 0 0 1-1v-3l2-4h4Z`,
            key: `1lbbv7`
        }],
        [`path`, {
            d: `M4.82 7.9 8 10`,
            key: `m9wose`
        }],
        [`path`, {
            d: `M15.18 7.9 12 10`,
            key: `p8dp2u`
        }],
        [`path`, {
            d: `M16.93 10H20a2 2 0 0 1 0 4H2`,
            key: `12nsm7`
        }]
    ]),
    ha = da(`x`, [
        [`path`, {
            d: `M18 6 6 18`,
            key: `1bl5f8`
        }],
        [`path`, {
            d: `m6 6 12 12`,
            key: `d8bk6v`
        }]
    ]),
    ga = 5,
    _a = r(Ui)`
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 4px 6px;
`,
    va = r.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: ${Wi};
`,
    ya = r.button`
  display: inline-flex;
  cursor: pointer;
  padding: 0;
  background: none;
  border: none;
  color: ${({$pinned:e})=>e?Gi:Wi};
`,
    ba = r.div`
  display: flex;
  flex-direction: ${({$vertical:e})=>e?`
column`:`
row`};
  align-items: flex-start;
  gap: 3px;
  ${({$vertical:e})=>e?`
max - height: 132 px;
overflow - y: auto;
padding - right: 12 px;
`:`
max - width: 168 px;
overflow - x: auto;
padding - bottom: 12 px;
`}
`, xa = r.span`
  flex-shrink: 0;
  min-height: 1.5em;
  padding: 0 3px;
  line-height: 1.5;
  text-align: center;
  border-radius: 2px;
  color: ${({$filled:e,$selected:t})=>e?t?`
var (--color - slate - 900)`:Gi:`
transparent`};
  background-color: ${({$selected:e})=>e?`
var (--color - blue - 200)`:`
transparent`};
`;

function Sa(e, t) {
    return e == null ? {
        text: `0`,
        title: void 0,
        filled: !1
    } : t ? {
        ...Ki(e, ga),
        filled: !0
    } : {
        text: e,
        title: void 0,
        filled: !0
    }
}

function Ca({
    pipe: e,
    flowDirection: t,
    pinned: n,
    togglePin: r,
    selectedKey: i
}) {
    let a = e.path.length,
        o = new Map(e.values.map(e => [e.index, e.value])),
        s = i == null ? -1 : e.path.findIndex(([e, t]) => A(e, t) === i),
        c = t === `S` || t === `N`,
        l = t === `W` || t === `N`,
        u = Array.from({
            length: a
        }, (e, t) => l ? a - 1 - t : t),
        d = S.useRef(null),
        f = S.useRef(null);
    return S.useLayoutEffect(() => {
        let e = d.current,
            t = f.current;
        if (!e || !t) return;
        let n = e.getBoundingClientRect(),
            r = t.getBoundingClientRect();
        c ? r.top < n.top ? e.scrollTop -= n.top - r.top : r.bottom > n.bottom && (e.scrollTop += r.bottom - n.bottom) : r.left < n.left ? e.scrollLeft -= n.left - r.left : r.right > n.right && (e.scrollLeft += r.right - n.right)
    }, [s, c]), (0, q.jsxs)(_a, {
        children: [(0, q.jsxs)(va, {
            children: [(0, q.jsxs)(`span`, {
                children: [e.values.length, `/`, a]
            }), (0, q.jsx)(ya, {
                $pinned: n,
                onClick: r,
                children: (0, q.jsx)(fa, {
                    size: 15,
                    fill: `currentColor`
                })
            })]
        }), (0, q.jsx)(ba, {
            $vertical: c,
            ref: d,
            children: u.map(e => {
                let t = e === s,
                    {
                        text: n,
                        title: r,
                        filled: i
                    } = Sa(o.has(e) ? String(o.get(e)) : null, c);
                return (0, q.jsx)(xa, {
                    ref: t ? f : null,
                    $filled: i,
                    $selected: t,
                    title: r,
                    children: n
                }, e)
            })
        })]
    })
}
var wa = r(Ui)`
  display: inline-flex;
  flex-direction: column;
  gap: 3px;
  padding: 5px 9px;
  color: ${Wi};
  letter-spacing: 0.04em;
  white-space: nowrap;
`,
    Ta = r.span`
  display: inline-flex;
  align-items: center;
  gap: 6px;
`,
    Ea = r.span`
  color: ${Gi};
`,
    Da = r.div`
  display: flex;
  flex-direction: column;
  align-items: center;
`,
    Oa = r(Ui).attrs({
        as: `button`
    })`
  cursor: pointer;
  position: relative;
  z-index: 1;
  min-width: 24px;
  height: 16px;
  padding: 0;
  line-height: 1;
  color: ${Gi};
  box-shadow: none;
  border-bottom-style: ${({$attached:e})=>e?`
none`:`
solid`};
  border-radius: ${({$attached:e})=>e?`
6 px 6 px 0 0`:`
3 px`};
  margin-bottom: ${({$attached:e})=>e?` - 1 px`:`
0`};
`, ka = r.span`
  display: inline-flex;
  align-self: center;
  border: 1px solid var(--color-stone-500);
  border-radius: 3px;
  overflow: hidden;
`, Aa = r.button`
  background: ${({$on:e})=>e?`
var (--color - stone - 600)`:`
transparent`};
  color: ${({$on:e})=>e?Gi:Wi};
  border: none;
  padding: 1px 7px;
  font: inherit;
  letter-spacing: inherit;
  cursor: pointer;
  & + & {
    border-left: 1px solid var(--color-stone-500);
  }
`;

function ja({
    display: e,
    showBack: t,
    onToggleBuffer: n
}) {
    let r = e.cursor % e.w,
        i = Math.floor(e.cursor / e.w),
        a = e => {
            e !== !!t && n?.()
        };
    return (0, q.jsxs)(wa, {
        children: [(0, q.jsxs)(Ta, {
            children: [(0, q.jsxs)(Ea, {
                children: [e.w, `×`, e.h]
            }), (0, q.jsx)(`span`, {
                children: `cursor at`
            }), (0, q.jsxs)(Ea, {
                children: [r, `,`, i]
            })]
        }), n && (0, q.jsxs)(ka, {
            children: [(0, q.jsx)(Aa, {
                $on: !t,
                onClick: () => a(!1),
                title: `Show the current frame — what the last SWAP put on screen (the front buffer)`,
                children: `current`
            }), (0, q.jsx)(Aa, {
                $on: !!t,
                onClick: () => a(!0),
                title: `Show the next frame as it's drawn — pixels land here at the cursor, and SWAP puts it on screen (the back buffer)`,
                children: `next`
            })]
        })]
    })
}

function Ma({
    display: e,
    collapsed: t,
    toggle: n,
    showBack: r,
    onToggleBuffer: i
}) {
    return (0, q.jsxs)(Da, {
        children: [(0, q.jsx)(Oa, {
            $attached: !t,
            onClick: n,
            children: t ? `+` : `–`
        }), !t && (0, q.jsx)(ja, {
            display: e,
            showBack: r,
            onToggleBuffer: i
        })]
    })
}
var Na = r(Ui)`
  position: absolute;
  top: 8px;
  left: 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 5px;
`,
    Pa = r.button`
  display: inline-flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  padding: 3px 6px;
  font: inherit;
  letter-spacing: 0.04em;
  border: none;
  border-radius: 2px;
  background-color: ${({$active:e})=>e?`
var (--color - stone - 600)`:`
transparent`};
  color: ${({$active:e})=>e?Gi:Wi};
`, Fa = 13, Ia = r.span`
  display: inline-block;
  width: ${Fa}px;
  text-align: center;
  margin-right: -2px;
`, La = r.span`
  /* font-size: 10px; */
  /* color: ${Wi}; */
  // nroyalty: I think without using a non-standard color for the title,
  // the whole element just isn't visible enough.
  color: var(--color-stone-200);
`;

function Ra({
    roomsCollapsed: e,
    toggleRoomsCollapsed: t,
    pipesPinned: n,
    togglePipesPinned: r
}) {
    return (0, q.jsxs)(Na, {
        children: [(0, q.jsx)(La, {
            children: `Panel Visibility`
        }), (0, q.jsxs)(Pa, {
            $active: e,
            onClick: t,
            title: e ? `Show all room panels` : `Hide all room panels`,
            children: [(0, q.jsx)(Ia, {
                children: e ? `+` : `–`
            }), `rooms`]
        }), (0, q.jsxs)(Pa, {
            $active: n,
            onClick: r,
            title: n ? `Unpin all pipe panels` : `Pin all pipe panels`,
            children: [(0, q.jsx)(fa, {
                size: Fa,
                fill: n ? `currentColor` : `none`
            }), `pipes`]
        })]
    })
}

function za([e, t, n, r], {
    px: i,
    py: a,
    cellSize: o
}) {
    return {
        leftPx: e * o - i,
        rightPx: (n + 1) * o - i,
        topPx: t * o - a,
        bottomPx: (r + 1) * o - a
    }
}

function Ba({
    rect: e,
    position: t,
    viewTransform: n
}) {
    let {
        leftPx: r,
        rightPx: i,
        topPx: a,
        bottomPx: o
    } = za(e, n), s = (r + i) / 2, c = (a + o) / 2;
    return t === `above` ? {
        left: `${s}px`,
        top: `${a- -2}px`,
        transform: `translate(-50%, -100%)`
    } : t === `left` ? {
        left: `${r- -2}px`,
        top: `${c}px`,
        transform: `translate(-100%, -50%)`
    } : t === `right` ? {
        left: `${i+-2}px`,
        top: `${c}px`,
        transform: `translate(0, -50%)`
    } : {
        left: `${s}px`,
        top: `${o+-2}px`,
        transform: `translateX(-50%)`
    }
}
var Va = {
        E: {
            xEdge: `right`,
            yEdge: `top`,
            transform: `translate(-100%, -100%)`
        },
        W: {
            xEdge: `left`,
            yEdge: `bottom`,
            transform: `translate(0, 0)`
        },
        S: {
            xEdge: `right`,
            yEdge: `bottom`,
            transform: `translate(0, -100%)`
        },
        N: {
            xEdge: `left`,
            yEdge: `top`,
            transform: `translate(-100%, 0)`
        }
    },
    Ha = {
        xEdge: `left`,
        yEdge: `top`,
        transform: `translate(-100%, -100%)`
    };

function Ua({
    cell: e,
    flowDirection: t,
    viewTransform: n
}) {
    let [r, i] = e, {
        leftPx: a,
        rightPx: o,
        topPx: s,
        bottomPx: c
    } = za([r, i, r, i], n), {
        xEdge: l,
        yEdge: u,
        transform: d
    } = Va[t] ?? Ha;
    return {
        left: `${l===`right`?o:a}px`,
        top: `${u===`bottom`?c:s}px`,
        transform: d
    }
}

function Wa(e, t) {
    return e.pipeAnchor ? {
        ...Ua({
            ...e.pipeAnchor,
            viewTransform: t
        }),
        zIndex: 2
    } : Ba({
        rect: e.rect,
        position: e.position ?? `below`,
        viewTransform: t
    })
}

function Ga({
    pixelCoordinates: e,
    viewportSize: t,
    cellSize: n
}) {
    let r = e.x + e.xOffset,
        i = e.y + e.yOffset,
        a = Math.floor(r / n) - 1,
        o = Math.floor(i / n) - 1,
        s = Math.ceil(t.width / n) + 2,
        c = Math.ceil(t.height / n) + 2;
    return {
        left: a,
        top: o,
        right: a + s,
        bottom: o + c,
        cellsWide: s,
        cellsTall: c
    }
}

function Ka({
    x: e,
    y: t,
    cellSize: n,
    pixelCoordinates: r
}) {
    let i = r.x + r.xOffset,
        a = r.y + r.yOffset;
    return {
        x: Math.floor((i + e) / n),
        y: Math.floor((a + t) / n)
    }
}
var qa = [{
        cellSize: 4,
        fontSize: 0,
        padding: 0,
        typeaheadArrow: 2
    }, {
        cellSize: 6,
        fontSize: 5,
        padding: 0,
        typeaheadArrow: 2
    }, {
        cellSize: 8,
        fontSize: 6,
        padding: 0,
        typeaheadArrow: 3
    }, {
        cellSize: 12,
        fontSize: 9,
        padding: 0,
        typeaheadArrow: 4
    }, {
        cellSize: 20,
        fontSize: 14,
        padding: 1,
        typeaheadArrow: 6
    }, {
        cellSize: 28,
        fontSize: 20,
        padding: 1,
        typeaheadArrow: 8
    }, {
        cellSize: 36,
        fontSize: 26,
        padding: 1,
        typeaheadArrow: 10
    }, {
        cellSize: 44,
        fontSize: 32,
        padding: 1,
        typeaheadArrow: 12
    }],
    Ja = 5,
    Ya = 12,
    Xa = 100,
    Za = r.div`
  position: relative;
  width: 100%;
  height: 100%;
  // without this, off-screen panels add scrollbars
  overflow: hidden;
`,
    Qa = r.div`
  position: relative;
  width: 100%;
  height: 100%;
  background-color: #222;
  overflow: hidden;
  cursor: var(--cursor);
`,
    $a = r.div`
  position: absolute;
  transform-origin: 0 0;
  transform: translate(var(--x), var(--y));
`,
    eo = r.div`
  position: absolute;
  top: calc(var(--gy) * var(--cell-size));
  left: calc(var(--gx) * var(--cell-size));
  width: calc(var(--gw) * var(--cell-size));
  height: calc(var(--gh) * var(--cell-size));
  border: 2px solid var(--color-blue-700);
  pointer-events: none;
`,
    to = r.div`
  position: absolute;
  padding: 2px 7px;
  background-color: var(--color-blue-700);
  color: var(--color-stone-100);
  border-radius: 6px;
  font-size: 13px;
  font-family: monospace;
  white-space: nowrap;
  pointer-events: none;
  z-index: 100;
`,
    no = r.span`
  position: absolute;
  top: 0;
  right: 0;
  padding: 4px;
  background-color: var(--color-stone-300);
  font-family: monospace;
`;

function ro({
    children: e
}) {
    return e ? (0, q.jsx)(no, {
        children: e
    }) : null
}
var io = r.div`
  position: absolute;
  pointer-events: auto;
`;

function ao({
    label: e,
    viewTransform: t,
    selectedKey: n,
    collapse: r,
    pins: i,
    defaults: a
}) {
    let o = i.has(e.id, a.pipesPinned);
    if (e.pipeCells) {
        let t = n != null && e.pipeCells.includes(n);
        if (!o && !t) return null
    }
    let s = e.kind === `display` ? a.displaysCollapsed : a.roomsCollapsed,
        c = {
            collapsed: r.has(e.id, s),
            toggle: () => r.toggle(e.id, s),
            pinned: o,
            togglePin: () => i.toggle(e.id, a.pipesPinned),
            selectedKey: n
        };
    return (0, q.jsx)(io, {
        style: Wa(e, t),
        children: e.render(c)
    })
}

function oo({
    labels: e,
    viewTransform: t,
    selectedKey: n,
    collapse: r,
    pins: i,
    defaults: a
}) {
    return e.map(e => (0, q.jsx)(ao, {
        label: e,
        viewTransform: t,
        selectedKey: n,
        collapse: r,
        pins: i,
        defaults: a
    }, e.id))
}

function so({
    spacePressed: e,
    dragActive: t,
    dragSelectActive: n,
    tool: r
}) {
    let i = `default`;
    return (r === Y.ROOM || r === Y.PIPE || r === Y.DISPLAY) && (i = `crosshair`), r === Y.MOVE && (i = `move`), (r === Y.HAND || e) && (i = `grab`), t && (i = `grabbing`), n && (i = `nwse-resize`), i
}
var co = new Set,
    lo = {},
    uo = [],
    fo = () => lo,
    po = () => {},
    mo = () => null;

function ho({
    getDisplayCellContent: e,
    getSourceCellContent: t,
    setCellContent: n,
    setCellsBulk: r,
    undo: i,
    redo: a,
    wallCells: o = co,
    roomCells: s = co,
    pipeCells: c = co,
    rooms: l = uo,
    moveRoom: u = po,
    previewMoveRoom: d = mo,
    specialWallCells: f = co,
    specialMarkerCells: p = co,
    displayWallCells: m = co,
    displayCells: h = co,
    validOps: g = null,
    cellTints: _ = lo,
    errorCell: v = null,
    cellGlyphs: y = lo,
    flowCells: b = lo,
    flowTerminals: x = lo,
    regionLabels: C = uo,
    highlightForSelection: w = fo,
    viewPersistKey: T,
    initialCenter: ee = null,
    initialCellSize: E = null,
    autoFocus: D = !1,
    readOnly: O = !1,
    showToolPalette: k = !0,
    showRuntimePanels: j = !0,
    showPanelControls: te = !0,
    initialRoomsCollapsed: M = null,
    initialDisplaysCollapsed: ne = null,
    initialPipesPinned: ae = !1,
    isSimulating: oe = !1
}, se) {
    let ce = T ? de(T) : null,
        [le] = S.useState(() => {
            if (E == null) return Ja;
            let e = 0;
            for (let t = 1; t < qa.length; t++) Math.abs(qa[t].cellSize - E) < Math.abs(qa[e].cellSize - E) && (e = t);
            return e
        }),
        ue = qa[le].cellSize,
        [L, R] = Yt(ce, {
            x: Xa * ue,
            y: Xa * ue,
            xOffset: 0,
            yOffset: 0,
            stepIndex: le
        }, e => Number.isInteger(e?.stepIndex) && e.stepIndex >= 0 && e.stepIndex < qa.length),
        z = qa[L.stepIndex],
        fe = window.devicePixelRatio || 1,
        pe = Math.round((L.x + L.xOffset) * fe) / fe,
        me = Math.round((L.y + L.yOffset) * fe) / fe,
        he = fn(),
        ge = fn(),
        [_e, ve] = S.useState({
            roomsCollapsed: M,
            displaysCollapsed: ne,
            pipesPinned: ae
        }),
        ye = z.cellSize < Ya,
        be = _e.roomsCollapsed ?? ye,
        xe = _e.displaysCollapsed ?? ye,
        {
            clear: B
        } = he,
        {
            clear: Se
        } = ge,
        Ce = S.useCallback(() => {
            B();
            let e = !be;
            ve(t => ({
                ...t,
                roomsCollapsed: e,
                displaysCollapsed: e
            }))
        }, [B, be]),
        V = S.useCallback(() => {
            Se(), ve(e => ({
                ...e,
                pipesPinned: !e.pipesPinned
            }))
        }, [Se]),
        {
            currentSelection: H,
            setSelectedCell: we,
            setSelectedArea: Te,
            clearSelection: Ee,
            moveCursor: De,
            extendSelection: Oe
        } = bn(),
        {
            direction: ke,
            clearTrail: U,
            onEscape: Ae,
            onAfterType: je,
            onBackspace: Me
        } = An({
            currentSelection: H,
            moveCursor: De,
            setSelectedCell: we,
            setCellContent: n
        }),
        Ne = S.useCallback(() => {
            U(), Ee()
        }, [U, Ee]),
        Pe = S.useRef(null),
        W = un({
            ref: Pe
        });
    S.useEffect(() => {
        R(e => e.xOffset === 0 && e.yOffset === 0 ? e : {
            ...e,
            xOffset: 0,
            yOffset: 0
        })
    }, [R]);
    let Fe = S.useRef(!1);
    S.useEffect(() => {
        if (!ee || Fe.current || !W.width || !W.height) return;
        Fe.current = !0;
        let e = z.cellSize;
        R(t => ({
            ...t,
            x: (ee.x + .5) * e - W.width / 2,
            y: (ee.y + .5) * e - W.height / 2,
            xOffset: 0,
            yOffset: 0
        }))
    }, [ee, W.width, W.height, z.cellSize, R]);
    let Ie = S.useMemo(() => {
            if (h.size === 0) return s;
            let e = new Set(s);
            for (let t of h) e.add(t);
            return e
        }, [s, h]),
        Le = O || oe,
        {
            tool: Re,
            setTool: ze,
            disabledTools: Be
        } = Cn({
            currentSelection: H,
            clearSelection: Ne,
            setCellsBulk: r,
            roomCells: Ie,
            readOnly: O,
            toolsDisabled: Le
        }),
        [Ve, He] = S.useState(!1),
        Ue = gn({
            viewportRef: Pe,
            setPixelCoordinates: R,
            spacePressed: Ve,
            forcePan: Re === Y.HAND
        }),
        We = S.useRef(!1),
        Ge = S.useCallback((e, t) => {
            U(), We.current = !0, De(e, t)
        }, [U, De]),
        Ke = S.useCallback((e, t) => {
            U(), We.current = !0, Oe(e, t)
        }, [U, Oe]),
        qe = S.useCallback(e => {
            U(), We.current = !1, Te(e)
        }, [U, Te]),
        Je = S.useCallback(e => {
            U(), We.current = !1, we(e)
        }, [U, we]);
    hn({
        moveCursor: Ge,
        extendSelection: Ke
    });
    let Ye = P(H) ? H.cell : F(H) ? H.active : null,
        Xe = cn((e, t) => {
            if (!We.current || (We.current = !1, !W.width || !W.height)) return;
            let n = z.cellSize;
            R(r => {
                let i = r.x + r.xOffset,
                    a = r.y + r.yOffset,
                    o = e * n,
                    s = o + n,
                    c = t * n,
                    l = c + n,
                    u = i,
                    d = a;
                return s <= i ? u = o : o >= i + W.width && (u = s - W.width), l <= a ? d = c : c >= a + W.height && (d = l - W.height), u === i && d === a ? r : {
                    ...r,
                    x: u,
                    y: d,
                    xOffset: 0,
                    yOffset: 0
                }
            })
        }),
        Ze = Ye?.x,
        Qe = Ye?.y;
    S.useEffect(() => {
        Ze != null && Xe(Ze, Qe)
    }, [Ze, Qe, Xe]), mn({
        key: ` `,
        onDown: () => {
            He(!0)
        },
        onUp: () => He(!1)
    });
    let [$e, et] = S.useState(null), tt = S.useCallback(e => et(ie(e)), []), nt = S.useCallback(() => et(null), []);
    S.useEffect(() => {
        (re(H) || Le) && et(null)
    }, [H, Le]);
    let rt = S.useCallback(() => {
            nt(), U(), i()
        }, [nt, U, i]),
        it = S.useCallback(() => {
            nt(), U(), a()
        }, [nt, U, a]);
    pn({
        undo: rt,
        redo: it
    });
    let {
        zoomIn: at,
        zoomOut: ot
    } = Ln({
        viewportRef: Pe,
        viewportSize: W,
        setPixelCoordinates: R,
        steps: qa,
        defaultStepIndex: Ja
    });
    S.useImperativeHandle(se, () => ({
        jumpToCell: (e, t) => {
            let n = z.cellSize;
            R(r => ({
                ...r,
                x: (e + .5) * n - W.width / 2,
                y: (t + .5) * n - W.height / 2,
                xOffset: 0,
                yOffset: 0
            })), Je({
                x: e,
                y: t
            })
        },
        undo: rt,
        redo: it,
        zoomIn: at,
        zoomOut: ot
    }), [z.cellSize, W.width, W.height, R, Je, rt, it, at, ot]);
    let st = S.useMemo(() => Ga({
            pixelCoordinates: L,
            viewportSize: W,
            cellSize: z.cellSize
        }), [pe, me, W, z]),
        ct = S.useCallback(() => I(H, t), [H, t]),
        G = S.useCallback((e, t) => Ka({
            x: e,
            y: t,
            cellSize: z.cellSize,
            pixelCoordinates: L
        }), [L, z]),
        lt = ln({
            viewportRef: Pe,
            setSelectedArea: qe,
            spacePressed: Ve,
            coordsToCell: G,
            enabled: Re === Y.SELECT
        }),
        [K, ut] = S.useState(null);
    wn({
        viewportRef: Pe,
        tool: Re,
        coordsToCell: G,
        setCellsBulk: r,
        roomCells: Ie,
        readOnly: Le,
        spacePressed: Ve,
        onPendingChange: ut
    }), En({
        viewportRef: Pe,
        tool: Re,
        coordsToCell: G,
        rooms: l,
        previewMoveRoom: d,
        moveRoom: u,
        readOnly: Le,
        spacePressed: Ve,
        onPendingChange: ut
    });
    let dt = S.useMemo(() => {
            if (P(H)) return H.cell;
            if (F(H)) {
                let e = N(H);
                return {
                    x: e.left,
                    y: e.top
                }
            }
            return null
        }, [H]),
        {
            overlayTints: ft,
            overlayGlyphs: pt
        } = S.useMemo(() => {
            if (!K) return {
                overlayTints: lo,
                overlayGlyphs: lo
            };
            let e = {},
                t = {},
                n = K.kind === `move` ? K.destRect : null;
            for (let r of K.entries) {
                let i = A(r.x, r.y);
                e[i] = n && r.content === `` && !(r.x >= n.minX && r.x <= n.maxX && r.y >= n.minY && r.y <= n.maxY) ? X.overlayLift : X.overlayPreview, t[i] = r.content
            }
            return {
                overlayTints: e,
                overlayGlyphs: t
            }
        }, [K]),
        mt = S.useMemo(() => {
            if (!$e || !dt) return lo;
            let e = {};
            for (let t of $e) t.content && (e[A(dt.x + t.dx, dt.y + t.dy)] = t.content);
            return e
        }, [$e, dt]),
        ht = S.useMemo(() => F(H) ? N(H) : null, [H]),
        gt = P(H) ? H.cell : null,
        _t = S.useMemo(() => w({
            selectedCell: gt
        }), [w, gt]),
        vt = S.useCallback(e => {
            let t = e.currentTarget.getBoundingClientRect();
            Je(G(e.clientX - t.left, e.clientY - t.top))
        }, [G, Je]);
    return (0, q.jsxs)(Za, {
        children: [(0, q.jsxs)(Qa, {
            ref: Pe,
            style: {
                "--cursor": so({
                    spacePressed: Ve,
                    dragActive: Ue,
                    dragSelectActive: lt,
                    tool: Re
                })
            },
            children: [(0, q.jsx)(rr, {
                autoFocus: D,
                currentSelection: H,
                setCellContent: n,
                setCellsBulk: r,
                clearSelection: Ne,
                getSelectionAsText: ct,
                readOnly: O,
                spacePressed: Ve,
                onAfterType: je,
                onBackspace: Me,
                onEscape: Ae,
                onCopyToGhost: tt,
                onDismissGhost: nt
            }), (0, q.jsx)(er, {
                width: W.width,
                height: W.height,
                onClick: vt,
                inputs: {
                    originX: pe,
                    originY: me,
                    visible: st,
                    step: z,
                    getDisplayCellContent: e,
                    wallCells: o,
                    roomCells: s,
                    pipeCells: c,
                    specialWallCells: f,
                    specialMarkerCells: p,
                    displayWallCells: m,
                    displayCells: h,
                    validOps: g,
                    cellTints: _,
                    cellGlyphs: y,
                    linkTints: _t,
                    overlayTints: ft,
                    overlayGlyphs: pt,
                    ghostGlyphs: mt,
                    flowCells: b,
                    flowTerminals: x,
                    selectedCell: gt,
                    areaBounds: ht,
                    errorCell: v
                }
            }), (0, q.jsxs)($a, {
                style: {
                    "--x": -pe + `px`,
                    "--y": -me + `px`,
                    "--cell-size": z.cellSize + `px`
                },
                children: [ht && (0, q.jsx)(eo, {
                    style: {
                        "--gx": ht.left,
                        "--gy": ht.top,
                        "--gw": ht.right - ht.left + 1,
                        "--gh": ht.bottom - ht.top + 1
                    }
                }), (0, q.jsx)(Nn, {
                    readOnly: O,
                    currentSelection: H,
                    direction: ke,
                    currentStep: z
                })]
            }), (0, q.jsx)(ro, {})]
        }), K?.sizeHint && (0, q.jsxs)(to, {
            style: Ba({
                rect: [K.sizeHint.cell.x, K.sizeHint.cell.y, K.sizeHint.cell.x, K.sizeHint.cell.y],
                position: K.sizeHint.side,
                viewTransform: {
                    px: pe,
                    py: me,
                    cellSize: z.cellSize
                }
            }),
            children: [K.sizeHint.w, `×`, K.sizeHint.h]
        }), (0, q.jsx)(oo, {
            labels: j ? C : uo,
            viewTransform: {
                px: pe,
                py: me,
                cellSize: z.cellSize
            },
            selectedKey: gt ? A(gt.x, gt.y) : null,
            collapse: he,
            pins: ge,
            defaults: {
                roomsCollapsed: be,
                displaysCollapsed: xe,
                pipesPinned: _e.pipesPinned
            }
        }), oe && j && te && (0, q.jsx)(Ra, {
            roomsCollapsed: be,
            toggleRoomsCollapsed: Ce,
            pipesPinned: _e.pipesPinned,
            togglePipesPinned: V
        }), k && (0, q.jsx)(Hi, {
            tool: Re,
            setTool: ze,
            disabledTools: Be
        })]
    })
}
var go = S.forwardRef(ho),
    _o = r.div`
  position: absolute;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  max-width: min(80%, 640px);
  padding: 10px 36px 10px 12px;
  border-radius: 4px;
  background-color: var(--color-red-950);
  color: var(--color-stone-300);
  font-family: monospace;
  line-height: 1.5;
  box-shadow: 0 4px 12px rgb(0 0 0 / 0.4);
  z-index: 4;
  user-select: text;
`,
    vo = r.span`
  color: var(--color-red-300);
  font-weight: bold;
`,
    yo = r.span`
  min-width: 0;
`,
    bo = r.button`
  position: absolute;
  top: 6px;
  right: 6px;
  display: inline-flex;
  align-items: center;
  padding: 2px;
  border: none;
  border-radius: 3px;
  background: none;
  color: var(--color-stone-300);
  cursor: pointer;

  &:hover {
    background-color: var(--color-red-900);
    color: var(--color-red-100);
  }
`;

function xo({
    onDismiss: e,
    children: t
}) {
    return J({
        key: `Escape`,
        modifiers: `none`,
        callback: e
    }), (0, q.jsxs)(_o, {
        role: `alert`,
        tabIndex: -1,
        children: [(0, q.jsx)(vo, {
            children: `error`
        }), (0, q.jsx)(bo, {
            type: `button`,
            "aria-label": `dismiss`,
            onClick: t => {
                Ht(t.currentTarget), e()
            },
            children: (0, q.jsx)(ha, {
                size: 18,
                strokeWidth: 2
            })
        }), (0, q.jsx)(yo, {
            children: t
        })]
    })
}
var So = `var(--font-size-xsmall)`,
    Co = r.div`
  display: flex;
  flex-direction: column;
  gap: 18px;
`,
    wo = r.h3`
  margin: 0;
  font-size: var(--font-size-small);
  font-weight: 600;
  color: var(--color-stone-200);
  border-bottom: 1px solid var(--color-blue-800);
  padding-bottom: 4px;
`,
    To = r.p`
  margin: 4px 0 4px 0;
  font-size: ${So};
  line-height: 1.5;
  color: var(--color-blue-200);
`,
    Eo = r.div`
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 4px 12px;
  align-items: baseline;
`,
    Do = r.code`
  font-family: monospace;
  font-size: var(--font-size-small);
  font-weight: 700;
  color: var(--color-amber-300);
  background-color: var(--color-blue-900);
  padding: 1px 6px;
  border-radius: 3px;
  text-align: center;
  white-space: pre;
`,
    Oo = r.span`
  font-size: ${So};
  line-height: 1.4;
  color: var(--color-stone-100);
`;
r.div`
  font-size: ${So};
  line-height: 1.5;
  color: var(--color-stone-100);

  p {
    margin: 0 0 6px 0;
  }
  code {
    font-family: monospace;
    background-color: var(--color-blue-900);
    padding: 0 4px;
    border-radius: 2px;
  }
`;
var ko = r.button`
  background: var(--color-blue-700);
  color: var(--color-stone-100);
  border: none;
  border-radius: 3px;
  padding: 3px 8px;
  font-family: monospace;
  font-size: ${So};
  cursor: pointer;
  &:hover:not(:disabled) {
    background: var(--color-blue-600);
  }
  &:disabled {
    opacity: 0.5;
    cursor: default;
  }
`,
    Ao = [{
        title: `Direction & turns`,
        rows: [{
            g: `>`,
            d: `Head east.`
        }, {
            g: `<`,
            d: `Head west.`
        }, {
            g: `^`,
            d: `Head north.`
        }, {
            g: `V v`,
            d: `Head south (both cases).`
        }, {
            g: `X`,
            d: `Turn by sign(A): clockwise if A>0, counter-clockwise if A<0, straight if A=0. A unchanged.`
        }, {
            g: `Y`,
            d: `Split in two: copies are born on the cells to his left and right (relative to his heading), each heading away from the Y; the original does not continue. Copies keep A, B, and backpack.`
        }, {
            g: `H`,
            d: `Halt (success).`
        }, {
            g: `.`,
            d: `Do nothing.`
        }]
    }, {
        title: `Numbers`,
        rows: [{
            g: `0-9`,
            d: `A = that single digit.`
        }, {
            g: "`123`",
            d: "Multi-digit literal: the digits between two backticks (spaces ignored) load into A at the closing backtick. Read in the direction of travel, so `123` is 123 forwards and 321 backwards; works vertically too."
        }]
    }, {
        title: `Registers`,
        rows: [{
            g: `M`,
            d: `B = A (A unchanged).`
        }, {
            g: `W`,
            d: `Swap A and B.`
        }]
    }, {
        title: `Arithmetic`,
        rows: [{
            g: `+`,
            d: `A = A + B.`
        }, {
            g: `-`,
            d: `A = A - B.`
        }, {
            g: `*`,
            d: `A = A * B.`
        }, {
            g: `%`,
            d: `A = A mod B (floored: result takes B's sign; 0 if B=0).`
        }, {
            g: `/`,
            d: `A = floor(A / B), remainder into B. If B=0: A=0, B keeps the dividend.`
        }, {
            g: `N`,
            d: `A = -A.`
        }]
    }, {
        title: `Bitwise`,
        blurb: "Two's-complement on all 64 bits; result to A, B unchanged. (A `|` on a wall or pipe is structure, not this op — same as `-`.)",
        rows: [{
            g: `&`,
            d: `A = A AND B.`
        }, {
            g: `|`,
            d: `A = A OR B.`
        }, {
            g: `~`,
            d: `A = A XOR B.`
        }, {
            g: `{`,
            d: `A = A << B (0 if B outside 0-63).`
        }, {
            g: `}`,
            d: `A = A >> B, arithmetic (sign-filling). 0 if B < 0; sign-fill if B > 63.`
        }]
    }, {
        title: `Backpack`,
        blurb: `A write-only third slot for loop counters. No op reads it back into A or B.`,
        rows: [{
            g: `b`,
            d: `Backpack = A (A unchanged).`
        }, {
            g: `m`,
            d: `Backpack -= 1 (may go negative).`
        }, {
            g: `d`,
            d: `Turn clockwise if Backpack > 0, else straight.`
        }, {
            g: `a`,
            d: `Turn counter-clockwise if Backpack > 0, else straight.`
        }, {
            g: `]`,
            d: `Backpack >>= 1 (arithmetic shift right; sign-preserving).`
        }, {
            g: `x`,
            d: `Turn clockwise if Backpack's low bit is set, else counter-clockwise. Always turns.`
        }, {
            g: `q`,
            d: `Backpack = number of values waiting in the nearest incoming pipe.`
        }]
    }, {
        title: `Pipes (messaging)`,
        rows: [{
            g: `s`,
            d: `Send A on the nearest outgoing pipe. Blocks if full.`
        }, {
            g: `S`,
            d: `Send A on every outgoing pipe. Blocks if any is full.`
        }, {
            g: `r`,
            d: `Receive into A from the nearest incoming pipe. Blocks if empty.`
        }, {
            g: `R`,
            d: `Receive into A from the first ready incoming pipe in reading order. Blocks if all empty.`
        }, {
            g: `U`,
            d: `Like R, but on a read turn to head in that pipe's flow direction. Blocks if all empty.`
        }]
    }, {
        title: `Grid characters`,
        blurb: `Glyphs you draw, not ops a little man executes.`,
        rows: [{
            g: `@`,
            d: `Spawn marker: a little man starts here heading east.`
        }, {
            g: `+ - |`,
            d: `Room walls (corners, horizontal, vertical). Rooms are rectangles; ops only run inside one. Stepping onto a wall halts the little man.`
        }, {
            g: `> < ^ v`,
            d: "Pipe arrowheads: mark a pipe's flow direction at its start, bends, and end. `-` and `|` fill the straight runs."
        }]
    }, {
        title: `I/O rooms`,
        blurb: `Input and output are special 3x3 rooms (walls included) with one interior cell, each wired to a single pipe. Read and write them with the pipe ops above.`,
        rows: [{
            g: `I`,
            d: `Input-room marker. Its one outgoing pipe feeds one input value per tick; it runs dry at end of input.`
        }, {
            g: `O`,
            d: `Output-room marker. Every value arriving on its incoming pipe becomes program output.`
        }]
    }, {
        title: `Displays (LM-75 screen)`,
        blurb: "A screen drawn like a room but with `+` corners, `=` top/bottom, and `:` sides. The interior is a grid of pixels (each a 0-15 color). Driven over pipes by which edge they enter.",
        rows: [{
            g: `= :`,
            d: "Display borders (with `+` corners)."
        }, {
            g: `left`,
            d: `DATA pipe: write the next pixel (0-15) and advance the cursor.`
        }, {
            g: `top`,
            d: `ADDR pipe: move the write cursor to a pixel index.`
        }, {
            g: `bottom`,
            d: `SWAP pipe: send 0 or 1 to commit the drawn frame to the screen. 0 then clears the canvas; 1 keeps it for incremental drawing.`
        }]
    }];

function jo(e, t) {
    return (0, q.jsxs)(`div`, {
        children: [(0, q.jsx)(wo, {
            children: e.title
        }), e.blurb && (0, q.jsx)(To, {
            children: e.blurb
        }), e.rows && (0, q.jsx)(Eo, {
            children: e.rows.map(e => (0, q.jsxs)(S.Fragment, {
                children: [(0, q.jsx)(Do, {
                    children: e.g
                }), (0, q.jsx)(Oo, {
                    children: e.d
                })]
            }, e.g))
        })]
    }, t)
}

function Mo() {
    return (0, q.jsx)(Co, {
        children: Ao.map(jo)
    })
}
var No = 28,
    Po = 380,
    Fo = r.div`
  position: absolute;
  top: 8px;
  right: 0;
  width: ${No}px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  z-index: 100;
`,
    Io = r.button`
  writing-mode: vertical-rl;
  transform: rotate(180deg);
  background-color: ${({$active:e})=>e?`
var (--color - amber - 300)`:`
var (--color - blue - 800)`};
  color: ${({$active:e})=>e?`
var (--color - blue - 900)`:`
var (--color - stone - 100)`};
  border: none;
  border-right: none;
  padding: 8px 4px;
  font-family: monospace;
  font-size: var(--font-size-xsmall);
  cursor: pointer;
  min-height: 80px;
  border-radius: 0 3px 3px 0;

  &:hover {
    background-color: ${({$active:e})=>e?`
var (--color - amber - 300)`:`
var (--color - blue - 700)`};
  }
`, Lo = r.aside`
  position: absolute;
  top: 0;
  right: ${No}px;
  bottom: 0;
  width: ${Po}px;
  background-color: ${({$surface:e})=>e===`
light`?`
var (--color - paper)`:`
var (--color - blue - 900)`};
  color: ${({$surface:e})=>e===`
light`?`
var (--color - ink)`:`
var (--color - stone - 100)`};
  box-shadow: -6px 0 14px rgba(0, 0, 0, 0.35);
  overflow-y: auto;
  padding: 14px 16px;
  z-index: 95;
`, Ro = {
    key: `reference`,
    label: `reference`,
    title: `Language reference`,
    render: () => (0, q.jsx)(Mo, {})
};

function zo({
    tabs: e,
    editorApi: t
}) {
    let [n, r] = S.useState(null), i = S.useCallback(e => {
        r(t => t === e ? null : e)
    }, []), a = S.useCallback(() => r(null), []);
    J({
        key: `Escape`,
        modifiers: `none`,
        callback: S.useCallback(() => {
            n && a()
        }, [n, a]),
        allowInFormControl: !0
    });
    let o = e.find(e => e.key === n);
    return (0, q.jsxs)(q.Fragment, {
        children: [o && (0, q.jsx)(Lo, {
            "aria-label": o.title,
            $surface: o.surface,
            children: o.render(t)
        }), (0, q.jsx)(Fo, {
            children: e.map(e => (0, q.jsx)(Io, {
                $active: n === e.key,
                onClick: () => i(e.key),
                title: e.title,
                "aria-expanded": n === e.key,
                children: e.label
            }, e.key))
        })]
    })
}
var Bo = S.memo(zo);

function Vo(e) {
    return e === `done`
}
var Ho = {
        S: `'S' has no pipe to send to — the room has no outgoing pipe`,
        s: `'s' has no pipe to send to — the room has no outgoing pipe`,
        r: `'r' has no pipe to read from — the room has no incoming pipe`,
        R: `'R' has no pipe to read from — the room has no incoming pipe`,
        U: `'U' has no pipe to read from — the room has no incoming pipe`,
        q: `'q' has no pipe to query — the room has no incoming pipe`
    },
    Uo = {
        "step-cap": `the step limit was exceeded`,
        "op-cap": `the operation limit was exceeded`,
        "time-cap": `the time limit was exceeded`
    };

function Wo(e, t) {
    let n = e.value == null ? `a value` : String(e.value);
    switch (e.reason) {
        case `display-value`:
            return `the display was sent ${n} as a pixel color — colors are 0 to 15`;
        case `display-addr`: {
            let r = t?.entities?.displays?.find(t => t.min[0] === e.pos[0] && t.min[1] === e.pos[1]);
            return `the display was sent ${n} as a cursor address — ${r?`this ${r.w}×${r.h} screen's addresses are 0 to ${r.w*r.h-1}`:`that is outside the screen`}`
        }
        case `display-swap`:
            return `the display was sent ${n} as a SWAP token — only 0 (commit, clear canvas) and 1 (commit, keep canvas) are allowed`;
        default:
            return null
    }
}

function Ko(e) {
    if (!e?.halted || Vo(e.reason)) return null;
    let t = e.fatal;
    if (t) {
        let n = {
            x: t.pos[0],
            y: t.pos[1]
        };
        if (t.reason === `wall`) return {
            message: `a little man hit a wall`,
            cell: n
        };
        if (t.reason === `split-limit`) return {
            message: `a split would have exceeded the little-man limit`,
            cell: n
        };
        if (t.reason === `bad-op`) return {
            message: `a little man stepped on '${t.cell}', which is not an instruction`,
            cell: n
        };
        if (t.reason === `no-pipe`) return {
            message: Ho[t.cell] ?? `'${t.cell}' has no pipe attached to its room`,
            cell: n
        };
        let r = Wo(t, e);
        return r ? {
            message: r,
            cell: n
        } : {
            message: `program crashed: ${t.reason}`,
            cell: n
        }
    }
    return {
        message: Uo[e.reason] ?? `program failed: ${e.reason}`,
        cell: null
    }
}

function qo(e) {
    return e.replace(/[^\d\s/-]+/g, ` `).replace(/\//g, ` / `)
}

function Jo(e) {
    return !e || !e.trim() ? [] : e.trim().split(/\s+/)
}

function Yo(e) {
    return Jo(e).filter(e => e !== `/`)
}

function Xo(e, t) {
    let n = Math.min(e.length, t.length);
    for (let r = 0; r < n; r++)
        if (String(e[r]) !== t[r]) return `diverged`;
    return e.length > t.length ? `extra` : e.length === t.length ? `match` : `pending`
}
var Zo = `/`;

function Qo(e) {
    let t = [],
        n = 0;
    for (let r of e) r === Zo ? n++ : t.push(n);
    return t
}

function $o(e) {
    let t = [0];
    for (let n of e) n === Zo ? t.push(0) : t[t.length - 1]++;
    return t
}

function es(e, t) {
    let n = [],
        r = 0;
    for (let i of t) {
        if (r >= e.length) break;
        n.push(e.slice(r, r + i).join(` `)), r += i
    }
    return r < e.length && n.push([n.pop(), ...e.slice(r)].filter(e => e !== ``).join(` `)), n.join(` / `)
}

function ts(e, {
    inputReleased: t = 0,
    outputDone: n = !1
}) {
    let r = Qo(e),
        i = n ? 1 / 0 : t > 0 ? r[t - 1] : 0,
        a = 0;
    return e.map(e => {
        if (e === Zo) return `separator`;
        let n = a++;
        return n >= t ? `future` : r[n] < i ? `past` : `current`
    })
}

function ns(e, t) {
    let n = Qo(e),
        r = t < n.length ? n[t] : -1,
        i = 0;
    return e.map(e => {
        if (e === Zo) return `separator`;
        let a = i < t ? `past` : n[i] === r ? `current` : `future`;
        return i++, a
    })
}
var Q = class extends Error {
        constructor(e) {
            super(e), this.name = `IoFormatError`
        }
    },
    rs = {
        lengthPrefixedAscii: {
            lengthPrefixed: `ascii`
        },
        lengthPrefixedInts: {
            lengthPrefixed: `int`
        }
    };

function is(e) {
    return typeof e == `string` && Object.prototype.hasOwnProperty.call(rs, e) ? rs[e] : e
}

function as(e) {
    if (typeof e == `string`) {
        if (e === `int` || e === `ascii`) return e;
        if (Object.prototype.hasOwnProperty.call(rs, e)) return rs[e];
        throw new Q(`unknown format node "${e}"`)
    }
    if (e && typeof e == `object` && !Array.isArray(e)) return e;
    throw new Q(`invalid format node: ${JSON.stringify(e)}`)
}

function os(e, t) {
    if (t.i >= e.length) throw new Q(`unexpected end of input at token ${t.i}`);
    let n = e[t.i],
        r = typeof n == `number` ? n : Number(n);
    if (!Number.isInteger(r)) throw new Q(`token ${t.i} is not an integer: ${JSON.stringify(n)}`);
    let i = t.i;
    return t.i += 1, {
        value: r,
        index: i
    }
}

function ss(e, t) {
    if (typeof e == `number`) {
        if (!Number.isInteger(e) || e < 0) throw new Q(`count literal must be a non-negative integer, got ${e}`);
        return e
    }
    if (typeof e == `string`) {
        if (!Object.prototype.hasOwnProperty.call(t, e)) throw new Q(`count references "${e}", which is not bound by an earlier label in scope (forward or out-of-scope reference)`);
        return t[e]
    }
    if (e && typeof e == `object` && !Array.isArray(e)) {
        if (Array.isArray(e[`*`])) {
            if (e[`*`].length === 0) throw new Q(`count "*" must have at least one operand`);
            return e[`*`].reduce((e, n) => e * ss(n, t), 1)
        }
        if (Array.isArray(e[`+`])) {
            if (e[`+`].length === 0) throw new Q(`count "+" must have at least one operand`);
            return e[`+`].reduce((e, n) => e + ss(n, t), 0)
        }
    }
    throw new Q(`invalid count expression: ${JSON.stringify(e)}`)
}

function cs(e, t, n, r) {
    let i = as(e);
    if (i === `int` || i === `ascii`) {
        let {
            value: e,
            index: r
        } = os(n, t), a = {
            kind: `token`,
            role: i,
            value: e,
            index: r
        };
        return i === `ascii` && (e < 0 || e > 255) && (a.outOfRange = !0), a
    }
    if (Object.prototype.hasOwnProperty.call(i, `literal`)) {
        let e = i.literal,
            {
                value: r,
                index: a
            } = os(n, t);
        if (r !== e) throw new Q(`token ${a} = ${r}, expected literal ${e}`);
        return {
            kind: `token`,
            role: `literal`,
            value: r,
            index: a
        }
    }
    if (Object.prototype.hasOwnProperty.call(i, `lengthPrefixed`)) {
        let {
            value: e,
            index: a
        } = os(n, t);
        if (e < 0) throw new Q(`length at token ${a} is negative: ${e}`);
        let o = {
                kind: `token`,
                role: `length`,
                value: e,
                index: a
            },
            s = [];
        for (let a = 0; a < e; a++) s.push(cs(i.lengthPrefixed, t, n, r));
        return {
            kind: `group`,
            node: `lengthPrefixed`,
            length: e,
            lengthToken: o,
            children: s
        }
    }
    if (Object.prototype.hasOwnProperty.call(i, `count`)) {
        if (!Object.prototype.hasOwnProperty.call(i, `of`)) throw new Q(`count node missing "of": ${JSON.stringify(i)}`);
        let e = ss(i.count, r),
            a = [];
        for (let o = 0; o < e; o++) a.push(cs(i.of, t, n, r));
        return {
            kind: `group`,
            node: `count`,
            length: e,
            children: a
        }
    }
    if (Object.prototype.hasOwnProperty.call(i, `repeat`)) {
        let e = [];
        for (; t.i < n.length;) {
            let a = t.i;
            if (e.push(cs(i.repeat, t, n, r)), t.i === a) throw new Q(`repeat body consumed no tokens (would loop forever)`)
        }
        return {
            kind: `group`,
            node: `repeat`,
            children: e
        }
    }
    if (Object.prototype.hasOwnProperty.call(i, `seq`)) {
        if (!Array.isArray(i.seq)) throw new Q(`seq must be an array: ${JSON.stringify(i)}`);
        return {
            kind: `group`,
            node: `seq`,
            children: i.seq.map(e => cs(e, t, n, r))
        }
    }
    if (Object.prototype.hasOwnProperty.call(i, `of`)) {
        let e = cs(i.of, t, n, r);
        return i.label && e.kind === `token` && (r[i.label] = e.value), {
            kind: `group`,
            node: `annotation`,
            label: i.label,
            note: i.note,
            children: [e]
        }
    }
    throw new Q(`unrecognized format node: ${JSON.stringify(i)}`)
}

function ls(e, t, n = Object.create(null)) {
    if (!Array.isArray(t)) throw new Q(`tokens must be an array, got ${typeof t}`);
    let r = {
            i: 0
        },
        i = cs(e, r, t, n);
    if (r.i !== t.length) throw new Q(`format left ${t.length-r.i} of ${t.length} tokens unconsumed (used ${r.i})`);
    return i
}

function us(e, t = []) {
    if (e.kind === `token`) return t.push(e), t;
    e.lengthToken && t.push(e.lengthToken);
    for (let n of e.children) us(n, t);
    return t
}

function ds(e, t, n = Object.create(null)) {
    return us(ls(e, t, n))
}

function fs(e) {
    if (e == null) return !1;
    let t = is(e);
    return typeof t == `string` ? t === `ascii` : typeof t != `object` || Array.isArray(t) ? !1 : Object.prototype.hasOwnProperty.call(t, `lengthPrefixed`) ? fs(t.lengthPrefixed) : Object.prototype.hasOwnProperty.call(t, `repeat`) ? fs(t.repeat) : Object.prototype.hasOwnProperty.call(t, `seq`) ? Array.isArray(t.seq) && t.seq.some(fs) : Object.prototype.hasOwnProperty.call(t, `of`) ? fs(t.of) : !1
}

function ps(e) {
    return typeof e != `object` || !e ? !1 : fs(e.input) || fs(e.output)
}

function ms(e) {
    return !!(e && typeof e == `object` && e.display != null)
}
var hs = `/`,
    gs = `␣`,
    _s = {
        textDecoration: `underline`,
        textDecorationColor: `var(--color-blue-300)`,
        textUnderlineOffset: `2px`,
        cursor: `help`
    },
    vs = {
        cursor: `help`
    };

function ys(e) {
    if (e.underline) return _s;
    if (e.char) return vs
}

function bs(e) {
    return e === 32 ? gs : e >= 33 && e <= 126 ? String.fromCharCode(e) : String(e)
}

function xs(e) {
    return `ASCII ${e===32?`space`:`‘${String.fromCharCode(e)}’`} = byte ${e}`
}

function Ss(e, t) {
    try {
        return ds(e, t).map(e => e.role === `ascii` ? {
            role: `ascii`,
            value: e.value
        } : {
            role: `other`,
            text: String(e.value)
        })
    } catch {
        return t.map(e => ({
            role: `other`,
            text: String(e)
        }))
    }
}

function Cs(e, t, {
    raw: n = !1
} = {}) {
    if (!e) return t.map(e => ({
        text: String(e),
        char: !1
    }));
    let r = [],
        i = [];
    for (let n of t) n === hs ? (r.push(...Ss(e, i), {
        role: `sep`
    }), i = []) : i.push(n);
    return r.push(...Ss(e, i)), r.map(e => e.role === `sep` ? {
        text: hs,
        char: !1
    } : e.role === `ascii` ? {
        text: n ? String(e.value) : bs(e.value),
        char: !0,
        underline: !n,
        tip: xs(e.value)
    } : {
        text: e.text,
        char: !1
    })
}

function ws(e, t, {
    raw: n = !1
} = {}) {
    return t.map((t, r) => {
        if (t === hs) return {
            text: hs,
            char: !1
        };
        if (e[r] && e[r].char) {
            let e = Number(t);
            if (e >= 32 && e <= 126) return {
                text: n ? String(t) : bs(e),
                char: !0,
                underline: !n,
                tip: xs(e)
            }
        }
        return {
            text: String(t),
            char: !1
        }
    })
}
var Ts = r(Yr)`
  background: var(--color-blue-950);
  color: var(--color-stone-100);
  border: 1px solid var(--color-blue-700);
  border-radius: 3px;
  padding: 2px 6px;
  font-family: monospace;
  font-size: 12px;
  z-index: 1000;
`;

function Es({
    children: e
}) {
    return (0, q.jsx)(Gr, {
        delayDuration: 0,
        skipDelayDuration: 0,
        disableHoverableContent: !0,
        children: e
    })
}

function Ds({
    label: e,
    children: t
}) {
    return (0, q.jsxs)(Kr, {
        children: [(0, q.jsx)(qr, {
            asChild: !0,
            children: t
        }), (0, q.jsx)(Jr, {
            children: (0, q.jsx)(Ts, {
                side: `top`,
                sideOffset: 4,
                children: e
            })
        })]
    })
}
var Os = r.section`
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
  padding: 12px 12px 10px;
  background-color: var(--color-blue-900);
  color: var(--color-stone-100);
  font-family: monospace;
  font-size: 14px;
  min-height: 0;
  position: relative;
  z-index: 3;
`,
    ks = r.div`
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 0;
  // Without this the sim-time TokenArea (white-space: nowrap) sets a wide
  // min-content on its 1fr grid track, so a long value grows the column and
  // shifts the layout vs. the shrinkable <input> shown when not running.
  // min-width: 0 pins the tracks to equal thirds; TokenArea scrolls instead.
  min-width: 0;
`,
    As = .54,
    js = r.input`
  font-family: inherit;
  font-size: inherit;
  padding: 6px 8px;
  background-color: var(--color-blue-950);
  color: var(--color-stone-100);
  border: none;
  border-radius: 3px;
  outline: 2px solid var(--verdict-outline, transparent);
  outline-offset: -2px;
  &::placeholder {
    color: var(--color-stone-100);
    opacity: ${As};
  }
  &:focus {
    outline: 2px solid var(--color-amber-300);
    outline-offset: -1px;
  }
  &:read-only {
    color: var(--color-stone-200);
  }
`,
    Ms = r.div`
  font-family: inherit;
  font-size: inherit;
  padding: 6px 8px;
  background-color: var(--color-blue-950);
  color: var(--color-stone-100);
  border-radius: 3px;
  white-space: nowrap;
  overflow-x: auto;
`,
    Ns = {
        past: {
            opacity: .35
        },
        current: {
            color: `var(--color-amber-300)`
        },
        future: {
            color: `var(--color-stone-400)`,
            opacity: .65
        },
        separator: {
            opacity: .5
        }
    };

function Ps({
    cells: e,
    states: t,
    testId: n,
    style: r,
    placeholder: i
}) {
    return (0, q.jsx)(Ms, {
        "data-testid": n,
        style: r,
        children: e.length === 0 ? i ? (0, q.jsx)(`span`, {
            style: {
                opacity: As
            },
            children: i
        }) : `\xA0` : e.map((e, n) => {
            let r = (0, q.jsx)(`span`, {
                style: {
                    ...Ns[t[n]],
                    ...ys(e)
                },
                "data-state": t[n],
                children: e.text
            });
            return (0, q.jsxs)(S.Fragment, {
                children: [n > 0 ? ` ` : ``, e.char ? (0, q.jsx)(Ds, {
                    label: e.tip,
                    children: r
                }) : r]
            }, n)
        })
    })
}
var $ = {
    pass: {
        color: `var(--color-emerald-300)`,
        outline: `var(--color-emerald-400)`
    },
    fail: {
        color: `var(--color-red-300)`,
        outline: `var(--color-red-400)`
    }
};

function Fs({
    isSimulating: e,
    snapshot: t,
    expected: n
}) {
    let r = t?.frameJudge ?? null;
    if (n.length === 0 && !r || !e) return null;
    let i = t?.output ?? [],
        a = Xo(i, n);
    if (r?.mismatch) return {
        tone: `fail`,
        label: `fail: frame ${r.mismatch.index+1} of ${r.total} wrong`,
        output: i,
        frameJudge: r
    };
    let o = !r || r.matched >= r.total;
    if (a === `match` && o) return {
        tone: `pass`,
        label: `pass`,
        output: i,
        frameJudge: r
    };
    if (a === `diverged`) return {
        tone: `fail`,
        label: `fail: wrong output`,
        output: i,
        frameJudge: r
    };
    if (a === `extra`) return {
        tone: `fail`,
        label: `fail: extra output`,
        output: i,
        frameJudge: r
    };
    if (t?.halted) {
        let e = `fail: crashed`;
        return Vo(t.reason) && (e = a === `match` && r ? `fail: missing frames (${r.matched}/${r.total})` : `fail: missing output`), {
            tone: `fail`,
            label: e,
            output: i,
            frameJudge: r
        }
    }
    return null
}

function Is({
    input: e,
    setInput: t,
    expected: n,
    setExpected: r,
    expectedTokens: i,
    snapshot: a,
    isSimulating: o,
    ioSpec: s,
    showRaw: c
}) {
    let l = a?.output ?? [],
        u = Fs({
            isSimulating: o,
            snapshot: a,
            expected: i
        }),
        d = u && i.length > 0 ? $[u.tone] : null,
        f = o && a,
        p = Jo(qo(e)),
        m = Jo(qo(n)),
        h = Cs(s?.input, p, {
            raw: c
        }),
        g = Cs(s?.output, m, {
            raw: c
        }),
        _ = es(l, $o(m)),
        v = ws(g, Jo(_), {
            raw: c
        }),
        y = `INPUT (e.g. 1 2 3)`,
        b = `EXPECTED (e.g. 1 2 3)`,
        x = `(your output here)`;
    return (0, q.jsx)(Es, {
        children: (0, q.jsxs)(Os, {
            children: [(0, q.jsx)(ks, {
                children: f ? (0, q.jsx)(Ps, {
                    testId: `io-input-tokens`,
                    cells: h,
                    placeholder: y,
                    states: ts(p, {
                        inputReleased: a.inputReleased,
                        outputDone: i.length > 0 && l.length >= i.length
                    })
                }) : (0, q.jsx)(js, {
                    id: `io-input`,
                    type: `text`,
                    value: e,
                    onChange: e => t(e.target.value),
                    spellCheck: !1,
                    placeholder: y
                })
            }), (0, q.jsx)(ks, {
                children: f ? (0, q.jsx)(Ps, {
                    testId: `io-expected-tokens`,
                    cells: g,
                    placeholder: b,
                    states: ns(m, l.length)
                }) : (0, q.jsx)(js, {
                    id: `io-expected`,
                    type: `text`,
                    value: n,
                    onChange: e => r(e.target.value),
                    spellCheck: !1,
                    placeholder: b
                })
            }), (0, q.jsx)(ks, {
                children: f ? (0, q.jsx)(Ps, {
                    testId: `io-observed-tokens`,
                    cells: v,
                    placeholder: x,
                    states: v.map(() => void 0),
                    style: {
                        outline: `2px solid ${d?.outline??`transparent`}`,
                        outlineOffset: -2
                    }
                }) : (0, q.jsx)(js, {
                    id: `io-observed`,
                    type: `text`,
                    readOnly: !0,
                    value: _,
                    spellCheck: !1,
                    placeholder: x,
                    style: {
                        "--verdict-outline": d?.outline
                    }
                })
            })]
        })
    })
}

function Ls(e) {
    return e && e.rounds && e.rounds.length > 0 ? e.rounds : [{
        in: e && e.in || [],
        out: e && e.out || [],
        frames: e && e.frames || []
    }]
}

function Rs(e, t, {
    ended: n,
    frameJudge: r = null
}) {
    let i = 0,
        a = !1,
        o = 0;
    return e.map(e => {
        let s = (e.out ?? []).map(String),
            c = [],
            l = a ? `pending` : `pass`;
        for (let e = 0; e < s.length; e++) a ? c.push(`pending`) : i >= t.length ? (a = !0, l = n ? `fail` : `pending`, c.push(n ? `missing` : `pending`)) : String(t[i]) === s[e] ? (c.push(`match`), i++) : (a = !0, l = `fail`, c.push(`wrong`));
        let u = (e.frames ?? []).length,
            d = o + u;
        if (!a && u > 0 && r) {
            let e = r.mismatch;
            e && e.index >= o && e.index < d ? (l = `fail`, a = !0) : r.matched < d && (l = n ? `fail` : `pending`, a = !0)
        }
        return o = d, {
            state: l,
            outStates: c
        }
    })
}

function zs(e, t, n, {
    ended: r,
    live: i = !1
}) {
    return Array.from({
        length: e
    }, (e, a) => {
        if (!n) return null;
        let o = t + a;
        return o < n.matched ? `match` : n.mismatch ? o === n.mismatch.index ? `wrong` : `pending` : i && o === n.matched ? `current` : r ? `missing` : `pending`
    })
}

function Bs(e) {
    let t = e.map(e => e.frames ?? []);
    return {
        input: e.map(e => (e.in ?? []).join(` `)).join(` / `),
        expected: e.map(e => (e.out ?? []).join(` `)).join(` / `),
        frames: t.some(e => e.length > 0) ? t : null
    }
}
var Vs = `#ff3355`,
    Hs = 4;

function Us(e) {
    let t = /^var\((--[^,)]+)\)$/.exec(e);
    return t ? getComputedStyle(document.documentElement).getPropertyValue(t[1]).trim() || `#a8a29e` : e
}

function Ws(e) {
    if (!Array.isArray(e) || e.length === 0) return null;
    let t = e[0]?.length ?? 0;
    if (t === 0) return null;
    let n = [];
    for (let r of e) {
        if (typeof r != `string` || r.length !== t) return null;
        for (let e of r) {
            let t = parseInt(e, 16);
            if (Number.isNaN(t)) return null;
            n.push(t)
        }
    }
    return {
        w: t,
        h: e.length,
        pixels: n
    }
}

function Gs(e, t, n) {
    return Math.max(2, Math.min(12, Math.floor(n / Math.max(e, t))))
}

function Ks({
    rows: e = null,
    pixels: t = null,
    w: n = null,
    diff: r = null,
    maxSize: i = 96,
    title: a = null,
    lineColor: o = `var(--color-stone-400)`
}) {
    let s = S.useMemo(() => e ? Ws(e) : t && n > 0 && t.length % n === 0 ? {
            w: n,
            h: t.length / n,
            pixels: t.map(Number)
        } : null, [e, t, n]),
        c = S.useMemo(() => r ? Array.isArray(r) && typeof r[0] == `string` ? Ws(r) : Array.isArray(r) && s && r.length === s.pixels.length ? {
            w: s.w,
            h: s.h,
            pixels: r.map(Number)
        } : null : null, [r, s]),
        l = S.useRef(null),
        u = s ? Gs(s.w, s.h, i) : 0,
        d = u >= Hs,
        f = s ? s.w * u + +!!d : 0,
        p = s ? s.h * u + +!!d : 0;
    return S.useEffect(() => {
        if (!s || !l.current) return;
        let e = l.current,
            t = window.devicePixelRatio || 1;
        e.width = f * t, e.height = p * t;
        let n = e.getContext(`2d`);
        n.scale(t, t), d && (n.fillStyle = Us(o), n.fillRect(0, 0, f, p));
        let r = +!!d;
        for (let e = 0; e < s.pixels.length; e++) {
            let t = e % s.w * u,
                i = Math.floor(e / s.w) * u;
            n.fillStyle = Hn(s.pixels[e]), n.fillRect(t + r, i + r, u - r, u - r), c && c.pixels[e] !== s.pixels[e] && (n.strokeStyle = Vs, n.lineWidth = 1, n.strokeRect(t + r + .5, i + r + .5, u - r - 1, u - r - 1))
        }
    }, [s, c, u, d, f, p, o]), s ? (0, q.jsx)(`canvas`, {
        ref: l,
        title: a ?? void 0,
        style: {
            width: f,
            height: p,
            display: `block`,
            outline: d ? `none` : `1px solid ${o}`
        }
    }) : null
}

function qs(e) {
    return Bs(Ls(e))
}
var Js = r.div`
  display: flex;
  flex-direction: column;
  height: 100%;
  font-family: monospace;
  font-size: ${So};
`,
    Ys = r.div`
  flex: 1;
  min-height: 0;
  overflow-y: auto;
`,
    Xs = r.div`
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  border-bottom: 1px solid var(--color-blue-800);
  padding-bottom: 8px;
  margin-bottom: 8px;
`,
    Zs = r.span`
  color: var(--color-amber-300);
  min-height: 2.8em;
`,
    Qs = r.button`
  background: transparent;
  border: none;
  padding: 0;
  font: inherit;
  color: var(--color-blue-300);
  text-decoration: underline;
  cursor: pointer;
  white-space: nowrap;
  &:hover {
    color: var(--color-blue-200);
  }
`,
    $s = r.div`
  border: 1px solid var(--color-blue-700);
  border-radius: 4px;
  padding: 8px;
  margin-bottom: 8px;
`,
    ec = r.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
`,
    tc = r.span`
  color: var(--color-stone-400);
  font-weight: 400;
`,
    nc = r.div`
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 6px;
`,
    rc = r.div`
  display: flex;
  gap: 8px;
  opacity: ${({$pass:e})=>e?.5:1};
`,
    ic = r.div`
  flex: 1;
  min-width: 0;
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 1px 8px;
`,
    ac = r.span`
  color: var(--color-stone-400);
`,
    oc = r.span`
  color: var(--color-stone-100);
`,
    sc = {
        match: `var(--color-stone-400)`,
        wrong: $.fail.color,
        missing: `var(--color-amber-300)`
    },
    cc = r.span`
  color: ${({$state:e})=>sc[e]??`
inherit`};
  font-weight: ${({$state:e})=>e===`
wrong`?700:400};
`, lc = r.div`
  grid-column: 2;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  overflow-x: auto;
  /* The current-frame ring (2px outline + 1px offset) extends 3px past the
     thumbs; the scroll container clips at its padding edge, so leave room on
     every side. */
  padding: 3px 3px 4px;
`, uc = r.div`
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
`, dc = {
    match: $.pass.color,
    wrong: $.fail.color,
    missing: sc.missing,
    current: `var(--color-amber-300)`
}, fc = r.span`
  color: ${({$state:e})=>dc[e]??`
var (--color - stone - 400)`};
`, pc = r.div`
  outline: ${({$current:e})=>e?`
2 px solid
var (--color - amber - 300)`:`
none`};
  outline-offset: 1px;
`;

function mc(e, t, n) {
    return t === `match` ? `✓` : t === `wrong` ? `want` : t === `missing` ? `missing` : t === `current` ? `▶` : n > 1 ? String(e + 1) : ``
}
var hc = r.span`
  align-self: center;
  color: ${({$state:e})=>e===`
pass`?$.pass.color:$.fail.color};
`, gc = r.div`
  margin-top: 4px;
  color: ${$.fail.color};
`, _c = r.div`
  border-top: 1px solid var(--color-blue-800);
  padding-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
`, vc = r.div`
  min-height: 1.4em;
`, yc = r.div`
  display: flex;
  gap: 8px;
  & > button {
    flex: 1;
    padding: 6px 8px;
  }
`, bc = r(ko)`
  background: transparent;
  border: 1px solid var(--color-blue-600);
  &:hover:not(:disabled) {
    background: var(--color-blue-800);
  }
`, xc = {
    pass: {
        glyph: `✓ pass`,
        color: $.pass.color
    },
    fail: {
        glyph: `✗ fail`,
        color: $.fail.color
    },
    crash: {
        glyph: `✗ crash`,
        color: $.fail.color
    },
    timeout: {
        glyph: `? timeout`,
        color: `var(--color-amber-300)`
    },
    error: {
        glyph: `! error`,
        color: $.fail.color
    }
};

function Sc({
    result: e
}) {
    if (!e) return null;
    let t = xc[e.status];
    return (0, q.jsx)(`span`, {
        style: {
            color: t.color
        },
        title: e.message,
        children: t.glyph
    })
}

function Cc(e, t) {
    if (!e || e.status === `pass`) return null;
    if (e.output.length > 0) {
        let n = e.message ? ` — ${e.message}` : ``;
        return `got: ${es(e.output,t.map(e=>(e.out??[]).length))}${n}`
    }
    return e.message ?? `failed`
}

function wc({
    tokens: e,
    spec: t,
    raw: n,
    states: r
}) {
    return e.length === 0 ? `(none)` : Cs(t, e, {
        raw: n
    }).map((e, t) => {
        let n = ys(e),
            i = r ? (0, q.jsx)(cc, {
                $state: r[t],
                style: n,
                children: e.text
            }) : (0, q.jsx)(`span`, {
                style: n,
                children: e.text
            });
        return (0, q.jsxs)(S.Fragment, {
            children: [t > 0 ? ` ` : ``, e.char ? (0, q.jsx)(Ds, {
                label: e.tip,
                children: i
            }) : i]
        }, t)
    })
}

function Tc({
    cases: e,
    onSubmit: t,
    editorApi: n,
    ioSpec: r,
    showRaw: i,
    onToggleRaw: a
}) {
    let o = n,
        [s, c] = S.useState({}),
        [l, u] = S.useState(!1),
        [d, f] = S.useState(null),
        [p, m] = S.useState({
            status: `idle`
        }),
        h = e => {
            c(t => {
                let n = {
                    ...t
                };
                return delete n[e.name], n
            }), f(e.name), o.runWithIO(qs(e))
        },
        g = S.useRef(!1);
    S.useEffect(() => {
        if (d)
            if (o.isSimulating && (g.current = !0), o.verdict) {
                let e = o.verdict;
                c(t => ({
                    ...t,
                    [d]: {
                        status: e.tone === `pass` ? `pass` : `fail`,
                        output: e.output ?? [],
                        message: e.label,
                        frameJudge: e.frameJudge ?? null
                    }
                })), f(null), g.current = !1
            } else if (o.loadError) {
            let e = o.loadError.message;
            c(t => ({
                ...t,
                [d]: {
                    status: `error`,
                    output: [],
                    message: e
                }
            })), f(null), g.current = !1
        } else g.current && !o.isSimulating && (f(null), g.current = !1)
    }, [d, o.verdict, o.isSimulating, o.loadError]), S.useEffect(() => {
        if (!d || g.current) return;
        let e = setTimeout(() => {
            c(e => ({
                ...e,
                [d]: {
                    status: `error`,
                    output: [],
                    message: `program did not start`
                }
            })), f(null)
        }, 2e3);
        return () => clearTimeout(e)
    }, [d, o.isSimulating, o.verdict, o.loadError]);
    let _ = async () => {
        o.isSimulating && o.onStop(), f(null), m({
            status: `idle`
        }), u(!0), c({});
        for (let t of e) {
            let e = await o.runCase(qs(t));
            c(n => ({
                ...n,
                [t.name]: e
            }))
        }
        u(!1)
    }, v = async () => {
        m({
            status: `submitting`
        });
        try {
            await t(o.getProgramText()), m({
                status: `submitted`
            })
        } catch (e) {
            m({
                status: `error`,
                message: e?.message ?? String(e)
            })
        }
    }, y = Object.keys(s).length, b = Object.values(s).filter(e => e.status === `pass`).length, x = e.length, C = y === x && x > 0, w = p.status === `submitted` ? {
        text: `submitted — view status on the problem page.`,
        color: $.pass.color
    } : p.status === `error` ? {
        text: p.message,
        color: $.fail.color
    } : l ? {
        text: `running… ${y}/${x}`,
        color: `var(--color-amber-300)`
    } : C ? {
        text: `${b}/${x} passed`,
        color: b === x ? $.pass.color : $.fail.color
    } : {
        text: ``,
        color: void 0
    };
    return (0, q.jsx)(Es, {
        children: (0, q.jsxs)(Js, {
            children: [r && a && (0, q.jsxs)(Xs, {
                children: [(0, q.jsx)(Zs, {
                    children: i ? `Showing raw values` : `Converting relevant values to ASCII`
                }), (0, q.jsx)(Qs, {
                    onClick: a,
                    children: i ? `show ASCII` : `show raw values`
                })]
            }), (0, q.jsx)(Ys, {
                children: e.map(e => {
                    let t = Ls(e),
                        n = s[e.name],
                        a = Cc(n, t),
                        c = d === e.name,
                        u = n ? n.status !== `timeout` : !1,
                        f = c ? o.liveFrameJudge : n?.frameJudge ?? null,
                        p = n && n.status !== `error` ? Rs(t, n.output, {
                            ended: u,
                            frameJudge: f
                        }) : null,
                        m = [],
                        g = 0;
                    for (let e of t) m.push(g), g += (e.frames ?? []).length;
                    return (0, q.jsxs)($s, {
                        children: [(0, q.jsxs)(ec, {
                            children: [(0, q.jsxs)(`span`, {
                                children: [(0, q.jsx)(`strong`, {
                                    children: e.name
                                }), t.length > 1 && (0, q.jsxs)(tc, {
                                    children: [` · `, t.length, ` rounds`]
                                })]
                            }), (0, q.jsxs)(`span`, {
                                style: {
                                    display: `flex`,
                                    gap: 8,
                                    alignItems: `center`
                                },
                                children: [d === e.name ? (0, q.jsx)(`span`, {
                                    style: {
                                        color: `var(--color-amber-300)`
                                    },
                                    children: `running…`
                                }) : (0, q.jsx)(Sc, {
                                    result: n
                                }), (0, q.jsx)(ko, {
                                    onClick: () => h(e),
                                    disabled: l || d !== null,
                                    title: `Load this case into the IO panel and run it`,
                                    children: `run`
                                })]
                            })]
                        }), a && (0, q.jsx)(gc, {
                            children: a
                        }), (0, q.jsx)(nc, {
                            children: t.map((e, t) => {
                                let n = p?.[t],
                                    a = e.frames ?? [],
                                    o = zs(a.length, m[t], f, {
                                        ended: !c && u,
                                        live: c
                                    }).map(e => e === `missing` && n?.state === `pending` ? `pending` : e),
                                    s = f?.mismatch?.got ?? null;
                                return (0, q.jsxs)(rc, {
                                    $pass: n?.state === `pass`,
                                    children: [(0, q.jsxs)(ic, {
                                        children: [(0, q.jsx)(ac, {
                                            children: `in`
                                        }), (0, q.jsx)(oc, {
                                            children: (0, q.jsx)(wc, {
                                                tokens: e.in,
                                                spec: r?.input,
                                                raw: i
                                            })
                                        }), (e.out?.length > 0 || a.length === 0) && (0, q.jsxs)(q.Fragment, {
                                            children: [(0, q.jsx)(ac, {
                                                children: `out`
                                            }), (0, q.jsx)(oc, {
                                                children: (0, q.jsx)(wc, {
                                                    tokens: e.out ?? [],
                                                    spec: r?.output,
                                                    raw: i,
                                                    states: n?.outStates
                                                })
                                            })]
                                        }), a.length > 0 && (0, q.jsxs)(q.Fragment, {
                                            children: [(0, q.jsx)(ac, {
                                                children: `screen`
                                            }), (0, q.jsx)(lc, {
                                                children: a.map((e, n) => {
                                                    let r = o[n];
                                                    return (0, q.jsxs)(S.Fragment, {
                                                        children: [(0, q.jsxs)(uc, {
                                                            children: [(0, q.jsx)(pc, {
                                                                $current: r === `current`,
                                                                children: (0, q.jsx)(Ks, {
                                                                    rows: e,
                                                                    maxSize: 64,
                                                                    lineColor: `var(--color-stone-600)`,
                                                                    title: `expected frame ${m[t]+n+1}`
                                                                })
                                                            }), (0, q.jsx)(fc, {
                                                                $state: r,
                                                                children: mc(n, r, a.length)
                                                            })]
                                                        }), r === `wrong` && s && (0, q.jsxs)(uc, {
                                                            children: [(0, q.jsx)(Ks, {
                                                                pixels: s,
                                                                w: e[0]?.length ?? 0,
                                                                diff: e,
                                                                maxSize: 64,
                                                                lineColor: `var(--color-stone-600)`,
                                                                title: `the frame your program committed — differing pixels outlined`
                                                            }), (0, q.jsx)(fc, {
                                                                $state: `wrong`,
                                                                children: `got`
                                                            })]
                                                        })]
                                                    }, n)
                                                })
                                            })]
                                        })]
                                    }), n && n.state !== `pending` && (0, q.jsx)(hc, {
                                        $state: n.state,
                                        children: n.state === `pass` ? `✓` : `✗`
                                    })]
                                }, t)
                            })
                        })]
                    }, e.name)
                })
            }), (0, q.jsxs)(_c, {
                children: [(0, q.jsx)(vc, {
                    style: {
                        color: w.color
                    },
                    children: w.text
                }), (0, q.jsxs)(yc, {
                    children: [(0, q.jsx)(ko, {
                        onClick: _,
                        disabled: l || d !== null,
                        children: `run public tests`
                    }), t && (0, q.jsx)(bc, {
                        onClick: v,
                        disabled: p.status === `submitting`,
                        children: p.status === `submitting` ? `submitting…` : `submit program`
                    })]
                })]
            })]
        })
    })
}
var Ec = r.button`
  font-size: 12px;
  padding: 6px 10px;
  min-width: 88px;
  border-radius: 3px;
  border: none;
  background-color: var(--color-blue-700);
  color: var(--color-stone-100);
  cursor: pointer;

  &:hover:not(:disabled) {
    background-color: var(--color-blue-600);
  }

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
`,
    Dc = 0;

function Oc() {
    S.useEffect(() => {
        let e = document.querySelectorAll(`[data-radix-focus-guard]`);
        return document.body.insertAdjacentElement(`afterbegin`, e[0] ?? kc()), document.body.insertAdjacentElement(`beforeend`, e[1] ?? kc()), Dc++, () => {
            Dc === 1 && document.querySelectorAll(`[data-radix-focus-guard]`).forEach(e => e.remove()), Dc--
        }
    }, [])
}

function kc() {
    let e = document.createElement(`span`);
    return e.setAttribute(`data-radix-focus-guard`, ``), e.tabIndex = 0, e.style.outline = `none`, e.style.opacity = `0`, e.style.position = `fixed`, e.style.pointerEvents = `none`, e
}
var Ac = `focusScope.autoFocusOnMount`,
    jc = `focusScope.autoFocusOnUnmount`,
    Mc = {
        bubbles: !1,
        cancelable: !0
    },
    Nc = `FocusScope`,
    Pc = S.forwardRef((e, t) => {
        let {
            loop: n = !1,
            trapped: r = !1,
            onMountAutoFocus: i,
            onUnmountAutoFocus: a,
            ...o
        } = e, [s, d] = S.useState(null), f = c(i), p = c(a), m = S.useRef(null), h = u(t, e => d(e)), g = S.useRef({
            paused: !1,
            pause() {
                this.paused = !0
            },
            resume() {
                this.paused = !1
            }
        }).current;
        S.useEffect(() => {
            if (r) {
                let e = function(e) {
                        if (g.paused || !s) return;
                        let t = e.target;
                        s.contains(t) ? m.current = t : Vc(m.current, {
                            select: !0
                        })
                    },
                    t = function(e) {
                        if (g.paused || !s) return;
                        let t = e.relatedTarget;
                        t !== null && (s.contains(t) || Vc(m.current, {
                            select: !0
                        }))
                    },
                    n = function(e) {
                        if (document.activeElement === document.body)
                            for (let t of e) t.removedNodes.length > 0 && Vc(s)
                    };
                document.addEventListener(`focusin`, e), document.addEventListener(`focusout`, t);
                let r = new MutationObserver(n);
                return s && r.observe(s, {
                    childList: !0,
                    subtree: !0
                }), () => {
                    document.removeEventListener(`focusin`, e), document.removeEventListener(`focusout`, t), r.disconnect()
                }
            }
        }, [r, s, g.paused]), S.useEffect(() => {
            if (s) {
                Hc.add(g);
                let e = document.activeElement;
                if (!s.contains(e)) {
                    let t = new CustomEvent(Ac, Mc);
                    s.addEventListener(Ac, f), s.dispatchEvent(t), t.defaultPrevented || (Fc(Gc(Lc(s)), {
                        select: !0
                    }), document.activeElement === e && Vc(s))
                }
                return () => {
                    s.removeEventListener(Ac, f), setTimeout(() => {
                        let t = new CustomEvent(jc, Mc);
                        s.addEventListener(jc, p), s.dispatchEvent(t), t.defaultPrevented || Vc(e ?? document.body, {
                            select: !0
                        }), s.removeEventListener(jc, p), Hc.remove(g)
                    }, 0)
                }
            }
        }, [s, f, p, g]);
        let _ = S.useCallback(e => {
            if (!n && !r || g.paused) return;
            let t = e.key === `Tab` && !e.altKey && !e.ctrlKey && !e.metaKey,
                i = document.activeElement;
            if (t && i) {
                let t = e.currentTarget,
                    [r, a] = Ic(t);
                r && a ? !e.shiftKey && i === a ? (e.preventDefault(), n && Vc(r, {
                    select: !0
                })) : e.shiftKey && i === r && (e.preventDefault(), n && Vc(a, {
                    select: !0
                })) : i === t && e.preventDefault()
            }
        }, [n, r, g.paused]);
        return (0, q.jsx)(l.div, {
            tabIndex: -1,
            ...o,
            ref: h,
            onKeyDown: _
        })
    });
Pc.displayName = Nc;

function Fc(e, {
    select: t = !1
} = {}) {
    let n = document.activeElement;
    for (let r of e)
        if (Vc(r, {
                select: t
            }), document.activeElement !== n) return
}

function Ic(e) {
    let t = Lc(e);
    return [Rc(t, e), Rc(t.reverse(), e)]
}

function Lc(e) {
    let t = [],
        n = document.createTreeWalker(e, NodeFilter.SHOW_ELEMENT, {
            acceptNode: e => {
                let t = e.tagName === `INPUT` && e.type === `hidden`;
                return e.disabled || e.hidden || t ? NodeFilter.FILTER_SKIP : e.tabIndex >= 0 ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP
            }
        });
    for (; n.nextNode();) t.push(n.currentNode);
    return t
}

function Rc(e, t) {
    for (let n of e)
        if (!zc(n, {
                upTo: t
            })) return n
}

function zc(e, {
    upTo: t
}) {
    if (getComputedStyle(e).visibility === `hidden`) return !0;
    for (; e;) {
        if (t !== void 0 && e === t) return !1;
        if (getComputedStyle(e).display === `none`) return !0;
        e = e.parentElement
    }
    return !1
}

function Bc(e) {
    return e instanceof HTMLInputElement && `select` in e
}

function Vc(e, {
    select: t = !1
} = {}) {
    if (e && e.focus) {
        let n = document.activeElement;
        e.focus({
            preventScroll: !0
        }), e !== n && Bc(e) && t && e.select()
    }
}
var Hc = Uc();

function Uc() {
    let e = [];
    return {
        add(t) {
            let n = e[0];
            t !== n && n?.pause(), e = Wc(e, t), e.unshift(t)
        },
        remove(t) {
            e = Wc(e, t), e[0]?.resume()
        }
    }
}

function Wc(e, t) {
    let n = [...e],
        r = n.indexOf(t);
    return r !== -1 && n.splice(r, 1), n
}

function Gc(e) {
    return e.filter(e => e.tagName !== `A`)
}
var Kc = function(e) {
        return typeof document > `u` ? null : (Array.isArray(e) ? e[0] : e).ownerDocument.body
    },
    qc = new WeakMap,
    Jc = new WeakMap,
    Yc = {},
    Xc = 0,
    Zc = function(e) {
        return e && (e.host || Zc(e.parentNode))
    },
    Qc = function(e, t) {
        return t.map(function(t) {
            if (e.contains(t)) return t;
            var n = Zc(t);
            return n && e.contains(n) ? n : (console.error(`aria-hidden`, t, `in not contained inside`, e, `. Doing nothing`), null)
        }).filter(function(e) {
            return !!e
        })
    },
    $c = function(e, t, n, r) {
        var i = Qc(t, Array.isArray(e) ? e : [e]);
        Yc[n] || (Yc[n] = new WeakMap);
        var a = Yc[n],
            o = [],
            s = new Set,
            c = new Set(i),
            l = function(e) {
                !e || s.has(e) || (s.add(e), l(e.parentNode))
            };
        i.forEach(l);
        var u = function(e) {
            !e || c.has(e) || Array.prototype.forEach.call(e.children, function(e) {
                if (s.has(e)) u(e);
                else try {
                    var t = e.getAttribute(r),
                        i = t !== null && t !== `false`,
                        c = (qc.get(e) || 0) + 1,
                        l = (a.get(e) || 0) + 1;
                    qc.set(e, c), a.set(e, l), o.push(e), c === 1 && i && Jc.set(e, !0), l === 1 && e.setAttribute(n, `true`), i || e.setAttribute(r, `true`)
                } catch (t) {
                    console.error(`aria-hidden: cannot operate on `, e, t)
                }
            })
        };
        return u(t), s.clear(), Xc++,
            function() {
                o.forEach(function(e) {
                    var t = qc.get(e) - 1,
                        i = a.get(e) - 1;
                    qc.set(e, t), a.set(e, i), t || (Jc.has(e) || e.removeAttribute(r), Jc.delete(e)), i || e.removeAttribute(n)
                }), Xc--, Xc || (qc = new WeakMap, qc = new WeakMap, Jc = new WeakMap, Yc = {})
            }
    },
    el = function(e, t, n) {
        n === void 0 && (n = `data-aria-hidden`);
        var r = Array.from(Array.isArray(e) ? e : [e]),
            i = t || Kc(e);
        return i ? (r.push.apply(r, Array.from(i.querySelectorAll(`[aria-live], script`))), $c(r, i, n, `aria-hidden`)) : function() {
            return null
        }
    },
    tl = function() {
        return tl = Object.assign || function(e) {
            for (var t, n = 1, r = arguments.length; n < r; n++)
                for (var i in t = arguments[n], t) Object.prototype.hasOwnProperty.call(t, i) && (e[i] = t[i]);
            return e
        }, tl.apply(this, arguments)
    };

function nl(e, t) {
    var n = {};
    for (var r in e) Object.prototype.hasOwnProperty.call(e, r) && t.indexOf(r) < 0 && (n[r] = e[r]);
    if (e != null && typeof Object.getOwnPropertySymbols == `function`)
        for (var i = 0, r = Object.getOwnPropertySymbols(e); i < r.length; i++) t.indexOf(r[i]) < 0 && Object.prototype.propertyIsEnumerable.call(e, r[i]) && (n[r[i]] = e[r[i]]);
    return n
}

function rl(e, t, n) {
    if (n || arguments.length === 2)
        for (var r = 0, i = t.length, a; r < i; r++)(a || !(r in t)) && (a ||= Array.prototype.slice.call(t, 0, r), a[r] = t[r]);
    return e.concat(a || Array.prototype.slice.call(t))
}
var il = `right-scroll-bar-position`,
    al = `width-before-scroll-bar`,
    ol = `with-scroll-bars-hidden`,
    sl = `--removed-body-scroll-bar-size`;

function cl(e, t) {
    return typeof e == `function` ? e(t) : e && (e.current = t), e
}

function ll(e, t) {
    var n = (0, S.useState)(function() {
        return {
            value: e,
            callback: t,
            facade: {
                get current() {
                    return n.value
                },
                set current(e) {
                    var t = n.value;
                    t !== e && (n.value = e, n.callback(e, t))
                }
            }
        }
    })[0];
    return n.callback = t, n.facade
}
var ul = typeof window < `u` ? S.useLayoutEffect : S.useEffect,
    dl = new WeakMap;

function fl(e, t) {
    var n = ll(t || null, function(t) {
        return e.forEach(function(e) {
            return cl(e, t)
        })
    });
    return ul(function() {
        var t = dl.get(n);
        if (t) {
            var r = new Set(t),
                i = new Set(e),
                a = n.current;
            r.forEach(function(e) {
                i.has(e) || cl(e, null)
            }), i.forEach(function(e) {
                r.has(e) || cl(e, a)
            })
        }
        dl.set(n, e)
    }, [e]), n
}

function pl(e) {
    return e
}

function ml(e, t) {
    t === void 0 && (t = pl);
    var n = [],
        r = !1;
    return {
        read: function() {
            if (r) throw Error("Sidecar: could not `read` from an `assigned` medium. `read` could be used only with `useMedium`.");
            return n.length ? n[n.length - 1] : e
        },
        useMedium: function(e) {
            var i = t(e, r);
            return n.push(i),
                function() {
                    n = n.filter(function(e) {
                        return e !== i
                    })
                }
        },
        assignSyncMedium: function(e) {
            for (r = !0; n.length;) {
                var t = n;
                n = [], t.forEach(e)
            }
            n = {
                push: function(t) {
                    return e(t)
                },
                filter: function() {
                    return n
                }
            }
        },
        assignMedium: function(e) {
            r = !0;
            var t = [];
            if (n.length) {
                var i = n;
                n = [], i.forEach(e), t = n
            }
            var a = function() {
                    var n = t;
                    t = [], n.forEach(e)
                },
                o = function() {
                    return Promise.resolve().then(a)
                };
            o(), n = {
                push: function(e) {
                    t.push(e), o()
                },
                filter: function(e) {
                    return t = t.filter(e), n
                }
            }
        }
    }
}

function hl(e) {
    e === void 0 && (e = {});
    var t = ml(null);
    return t.options = tl({
        async: !0,
        ssr: !1
    }, e), t
}
var gl = function(e) {
    var t = e.sideCar,
        n = nl(e, [`sideCar`]);
    if (!t) throw Error("Sidecar: please provide `sideCar` property to import the right car");
    var r = t.read();
    if (!r) throw Error(`Sidecar medium not found`);
    return S.createElement(r, tl({}, n))
};
gl.isSideCarExport = !0;

function _l(e, t) {
    return e.useMedium(t), gl
}
var vl = hl(),
    yl = function() {},
    bl = S.forwardRef(function(e, t) {
        var n = S.useRef(null),
            r = S.useState({
                onScrollCapture: yl,
                onWheelCapture: yl,
                onTouchMoveCapture: yl
            }),
            i = r[0],
            a = r[1],
            o = e.forwardProps,
            s = e.children,
            c = e.className,
            l = e.removeScrollBar,
            u = e.enabled,
            d = e.shards,
            f = e.sideCar,
            p = e.noRelative,
            m = e.noIsolation,
            h = e.inert,
            g = e.allowPinchZoom,
            _ = e.as,
            v = _ === void 0 ? `div` : _,
            y = e.gapMode,
            b = nl(e, [`forwardProps`, `children`, `className`, `removeScrollBar`, `enabled`, `shards`, `sideCar`, `noRelative`, `noIsolation`, `inert`, `allowPinchZoom`, `as`, `gapMode`]),
            x = f,
            C = fl([n, t]),
            w = tl(tl({}, b), i);
        return S.createElement(S.Fragment, null, u && S.createElement(x, {
            sideCar: vl,
            removeScrollBar: l,
            shards: d,
            noRelative: p,
            noIsolation: m,
            inert: h,
            setCallbacks: a,
            allowPinchZoom: !!g,
            lockRef: n,
            gapMode: y
        }), o ? S.cloneElement(S.Children.only(s), tl(tl({}, w), {
            ref: C
        })) : S.createElement(v, tl({}, w, {
            className: c,
            ref: C
        }), s))
    });
bl.defaultProps = {
    enabled: !0,
    removeScrollBar: !0,
    inert: !1
}, bl.classNames = {
    fullWidth: al,
    zeroRight: il
};
var xl, Sl = function() {
    if (xl) return xl;
    if (typeof __webpack_nonce__ < `u`) return __webpack_nonce__
};

function Cl() {
    if (!document) return null;
    var e = document.createElement(`style`);
    e.type = `text/css`;
    var t = Sl();
    return t && e.setAttribute(`nonce`, t), e
}

function wl(e, t) {
    e.styleSheet ? e.styleSheet.cssText = t : e.appendChild(document.createTextNode(t))
}

function Tl(e) {
    (document.head || document.getElementsByTagName(`head`)[0]).appendChild(e)
}
var El = function() {
        var e = 0,
            t = null;
        return {
            add: function(n) {
                e == 0 && (t = Cl()) && (wl(t, n), Tl(t)), e++
            },
            remove: function() {
                e--, !e && t && (t.parentNode && t.parentNode.removeChild(t), t = null)
            }
        }
    },
    Dl = function() {
        var e = El();
        return function(t, n) {
            S.useEffect(function() {
                return e.add(t),
                    function() {
                        e.remove()
                    }
            }, [t && n])
        }
    },
    Ol = function() {
        var e = Dl();
        return function(t) {
            var n = t.styles,
                r = t.dynamic;
            return e(n, r), null
        }
    },
    kl = {
        left: 0,
        top: 0,
        right: 0,
        gap: 0
    },
    Al = function(e) {
        return parseInt(e || ``, 10) || 0
    },
    jl = function(e) {
        var t = window.getComputedStyle(document.body),
            n = t[e === `padding` ? `paddingLeft` : `marginLeft`],
            r = t[e === `padding` ? `paddingTop` : `marginTop`],
            i = t[e === `padding` ? `paddingRight` : `marginRight`];
        return [Al(n), Al(r), Al(i)]
    },
    Ml = function(e) {
        if (e === void 0 && (e = `margin`), typeof window > `u`) return kl;
        var t = jl(e),
            n = document.documentElement.clientWidth,
            r = window.innerWidth;
        return {
            left: t[0],
            top: t[1],
            right: t[2],
            gap: Math.max(0, r - n + t[2] - t[0])
        }
    },
    Nl = Ol(),
    Pl = `data-scroll-locked`,
    Fl = function(e, t, n, r) {
        var i = e.left,
            a = e.top,
            o = e.right,
            s = e.gap;
        return n === void 0 && (n = `margin`), `
  .${ol} {
   overflow: hidden ${r};
   padding-right: ${s}px ${r};
  }
  body[${Pl}] {
    overflow: hidden ${r};
    overscroll-behavior: contain;
    ${[t&&`position: relative ${r};`,n===`margin`&&`
    padding-left: ${i}px;
    padding-top: ${a}px;
    padding-right: ${o}px;
    margin-left:0;
    margin-top:0;
    margin-right: ${s}px ${r};
    `,n===`padding`&&`padding-right: ${s}px ${r};`].filter(Boolean).join(``)}
  }
  
  .${il} {
    right: ${s}px ${r};
  }
  
  .${al} {
    margin-right: ${s}px ${r};
  }
  
  .${il} .${il} {
    right: 0 ${r};
  }
  
  .${al} .${al} {
    margin-right: 0 ${r};
  }
  
  body[${Pl}] {
    ${sl}: ${s}px;
  }
`
    },
    Il = function() {
        var e = parseInt(document.body.getAttribute(`data-scroll-locked`) || `0`, 10);
        return isFinite(e) ? e : 0
    },
    Ll = function() {
        S.useEffect(function() {
            return document.body.setAttribute(Pl, (Il() + 1).toString()),
                function() {
                    var e = Il() - 1;
                    e <= 0 ? document.body.removeAttribute(Pl) : document.body.setAttribute(Pl, e.toString())
                }
        }, [])
    },
    Rl = function(e) {
        var t = e.noRelative,
            n = e.noImportant,
            r = e.gapMode,
            i = r === void 0 ? `margin` : r;
        Ll();
        var a = S.useMemo(function() {
            return Ml(i)
        }, [i]);
        return S.createElement(Nl, {
            styles: Fl(a, !t, i, n ? `` : `!important`)
        })
    },
    zl = !1;
if (typeof window < `u`) try {
    var Bl = Object.defineProperty({}, "passive", {
        get: function() {
            return zl = !0, !0
        }
    });
    window.addEventListener(`test`, Bl, Bl), window.removeEventListener(`test`, Bl, Bl)
} catch {
    zl = !1
}
var Vl = zl ? {
        passive: !1
    } : !1,
    Hl = function(e) {
        return e.tagName === `TEXTAREA`
    },
    Ul = function(e, t) {
        if (!(e instanceof Element)) return !1;
        var n = window.getComputedStyle(e);
        return n[t] !== `hidden` && !(n.overflowY === n.overflowX && !Hl(e) && n[t] === `visible`)
    },
    Wl = function(e) {
        return Ul(e, `overflowY`)
    },
    Gl = function(e) {
        return Ul(e, `overflowX`)
    },
    Kl = function(e, t) {
        var n = t.ownerDocument,
            r = t;
        do {
            if (typeof ShadowRoot < `u` && r instanceof ShadowRoot && (r = r.host), Yl(e, r)) {
                var i = Xl(e, r);
                if (i[1] > i[2]) return !0
            }
            r = r.parentNode
        } while (r && r !== n.body);
        return !1
    },
    ql = function(e) {
        return [e.scrollTop, e.scrollHeight, e.clientHeight]
    },
    Jl = function(e) {
        return [e.scrollLeft, e.scrollWidth, e.clientWidth]
    },
    Yl = function(e, t) {
        return e === `v` ? Wl(t) : Gl(t)
    },
    Xl = function(e, t) {
        return e === `v` ? ql(t) : Jl(t)
    },
    Zl = function(e, t) {
        return e === `h` && t === `rtl` ? -1 : 1
    },
    Ql = function(e, t, n, r, i) {
        var a = Zl(e, window.getComputedStyle(t).direction),
            o = a * r,
            s = n.target,
            c = t.contains(s),
            l = !1,
            u = o > 0,
            d = 0,
            f = 0;
        do {
            if (!s) break;
            var p = Xl(e, s),
                m = p[0],
                h = p[1] - p[2] - a * m;
            (m || h) && Yl(e, s) && (d += h, f += m);
            var g = s.parentNode;
            s = g && g.nodeType === Node.DOCUMENT_FRAGMENT_NODE ? g.host : g
        } while (!c && s !== document.body || c && (t.contains(s) || t === s));
        return (u && (i && Math.abs(d) < 1 || !i && o > d) || !u && (i && Math.abs(f) < 1 || !i && -o > f)) && (l = !0), l
    },
    $l = function(e) {
        return `changedTouches` in e ? [e.changedTouches[0].clientX, e.changedTouches[0].clientY] : [0, 0]
    },
    eu = function(e) {
        return [e.deltaX, e.deltaY]
    },
    tu = function(e) {
        return e && `current` in e ? e.current : e
    },
    nu = function(e, t) {
        return e[0] === t[0] && e[1] === t[1]
    },
    ru = function(e) {
        return `
  .block-interactivity-${e} {pointer-events: none;}
  .allow-interactivity-${e} {pointer-events: all;}
`
    },
    iu = 0,
    au = [];

function ou(e) {
    var t = S.useRef([]),
        n = S.useRef([0, 0]),
        r = S.useRef(),
        i = S.useState(iu++)[0],
        a = S.useState(Ol)[0],
        o = S.useRef(e);
    S.useEffect(function() {
        o.current = e
    }, [e]), S.useEffect(function() {
        if (e.inert) {
            document.body.classList.add(`block-interactivity-${i}`);
            var t = rl([e.lockRef.current], (e.shards || []).map(tu), !0).filter(Boolean);
            return t.forEach(function(e) {
                    return e.classList.add(`allow-interactivity-${i}`)
                }),
                function() {
                    document.body.classList.remove(`block-interactivity-${i}`), t.forEach(function(e) {
                        return e.classList.remove(`allow-interactivity-${i}`)
                    })
                }
        }
    }, [e.inert, e.lockRef.current, e.shards]);
    var s = S.useCallback(function(e, t) {
            if (`touches` in e && e.touches.length === 2 || e.type === `wheel` && e.ctrlKey) return !o.current.allowPinchZoom;
            var i = $l(e),
                a = n.current,
                s = `deltaX` in e ? e.deltaX : a[0] - i[0],
                c = `deltaY` in e ? e.deltaY : a[1] - i[1],
                l, u = e.target,
                d = Math.abs(s) > Math.abs(c) ? `h` : `v`;
            if (`touches` in e && d === `h` && u.type === `range`) return !1;
            var f = window.getSelection(),
                p = f && f.anchorNode;
            if (p && (p === u || p.contains(u))) return !1;
            var m = Kl(d, u);
            if (!m) return !0;
            if (m ? l = d : (l = d === `v` ? `h` : `v`, m = Kl(d, u)), !m) return !1;
            if (!r.current && `changedTouches` in e && (s || c) && (r.current = l), !l) return !0;
            var h = r.current || l;
            return Ql(h, t, e, h === `h` ? s : c, !0)
        }, []),
        c = S.useCallback(function(e) {
            var n = e;
            if (!(!au.length || au[au.length - 1] !== a)) {
                var r = `deltaY` in n ? eu(n) : $l(n),
                    i = t.current.filter(function(e) {
                        return e.name === n.type && (e.target === n.target || n.target === e.shadowParent) && nu(e.delta, r)
                    })[0];
                if (i && i.should) {
                    n.cancelable && n.preventDefault();
                    return
                }
                if (!i) {
                    var c = (o.current.shards || []).map(tu).filter(Boolean).filter(function(e) {
                        return e.contains(n.target)
                    });
                    (c.length > 0 ? s(n, c[0]) : !o.current.noIsolation) && n.cancelable && n.preventDefault()
                }
            }
        }, []),
        l = S.useCallback(function(e, n, r, i) {
            var a = {
                name: e,
                delta: n,
                target: r,
                should: i,
                shadowParent: su(r)
            };
            t.current.push(a), setTimeout(function() {
                t.current = t.current.filter(function(e) {
                    return e !== a
                })
            }, 1)
        }, []),
        u = S.useCallback(function(e) {
            n.current = $l(e), r.current = void 0
        }, []),
        d = S.useCallback(function(t) {
            l(t.type, eu(t), t.target, s(t, e.lockRef.current))
        }, []),
        f = S.useCallback(function(t) {
            l(t.type, $l(t), t.target, s(t, e.lockRef.current))
        }, []);
    S.useEffect(function() {
        return au.push(a), e.setCallbacks({
                onScrollCapture: d,
                onWheelCapture: d,
                onTouchMoveCapture: f
            }), document.addEventListener(`wheel`, c, Vl), document.addEventListener(`touchmove`, c, Vl), document.addEventListener(`touchstart`, u, Vl),
            function() {
                au = au.filter(function(e) {
                    return e !== a
                }), document.removeEventListener(`wheel`, c, Vl), document.removeEventListener(`touchmove`, c, Vl), document.removeEventListener(`touchstart`, u, Vl)
            }
    }, []);
    var p = e.removeScrollBar,
        m = e.inert;
    return S.createElement(S.Fragment, null, m ? S.createElement(a, {
        styles: ru(i)
    }) : null, p ? S.createElement(Rl, {
        noRelative: e.noRelative,
        gapMode: e.gapMode
    }) : null)
}

function su(e) {
    for (var t = null; e !== null;) e instanceof ShadowRoot && (t = e.host, e = e.host), e = e.parentNode;
    return t
}
var cu = _l(vl, ou),
    lu = S.forwardRef(function(e, t) {
        return S.createElement(bl, tl({}, e, {
            ref: t,
            sideCar: cu
        }))
    });
lu.classNames = bl.classNames;
var uu = `Popover`,
    [du, fu] = d(uu, [s]),
    pu = s(),
    [mu, hu] = du(uu),
    gu = e => {
        let {
            __scopePopover: t,
            children: n,
            open: r,
            defaultOpen: i,
            onOpenChange: a,
            modal: o = !1
        } = e, s = pu(t), c = S.useRef(null), [l, u] = S.useState(!1), [d, f] = b({
            prop: r,
            defaultProp: i ?? !1,
            onChange: a,
            caller: uu
        });
        return (0, q.jsx)(y, {
            ...s,
            children: (0, q.jsx)(mu, {
                scope: t,
                contentId: or(),
                triggerRef: c,
                open: d,
                onOpenChange: f,
                onOpenToggle: S.useCallback(() => f(e => !e), [f]),
                hasCustomAnchor: l,
                onCustomAnchorAdd: S.useCallback(() => u(!0), []),
                onCustomAnchorRemove: S.useCallback(() => u(!1), []),
                modal: o,
                children: n
            })
        })
    };
gu.displayName = uu;
var _u = `PopoverAnchor`,
    vu = S.forwardRef((e, t) => {
        let {
            __scopePopover: n,
            ...r
        } = e, i = hu(_u, n), a = pu(n), {
            onCustomAnchorAdd: o,
            onCustomAnchorRemove: s
        } = i;
        return S.useEffect(() => (o(), () => s()), [o, s]), (0, q.jsx)(f, {
            ...a,
            ...r,
            ref: t
        })
    });
vu.displayName = _u;
var yu = `PopoverTrigger`,
    bu = S.forwardRef((e, t) => {
        let {
            __scopePopover: n,
            ...r
        } = e, i = hu(yu, n), o = pu(n), s = u(t, i.triggerRef), c = (0, q.jsx)(l.button, {
            type: `button`,
            "aria-haspopup": `dialog`,
            "aria-expanded": i.open,
            "aria-controls": i.contentId,
            "data-state": Fu(i.open),
            ...r,
            ref: s,
            onClick: a(e.onClick, i.onOpenToggle)
        });
        return i.hasCustomAnchor ? c : (0, q.jsx)(f, {
            asChild: !0,
            ...o,
            children: c
        })
    });
bu.displayName = yu;
var xu = `PopoverPortal`,
    [Su, Cu] = du(xu, {
        forceMount: void 0
    }),
    wu = e => {
        let {
            __scopePopover: t,
            forceMount: n,
            children: r,
            container: i
        } = e, a = hu(xu, t);
        return (0, q.jsx)(Su, {
            scope: t,
            forceMount: n,
            children: (0, q.jsx)(h, {
                present: n || a.open,
                children: (0, q.jsx)(v, {
                    asChild: !0,
                    container: i,
                    children: r
                })
            })
        })
    };
wu.displayName = xu;
var Tu = `PopoverContent`,
    Eu = S.forwardRef((e, t) => {
        let n = Cu(Tu, e.__scopePopover),
            {
                forceMount: r = n.forceMount,
                ...i
            } = e,
            a = hu(Tu, e.__scopePopover);
        return (0, q.jsx)(h, {
            present: r || a.open,
            children: a.modal ? (0, q.jsx)(Ou, {
                ...i,
                ref: t
            }) : (0, q.jsx)(ku, {
                ...i,
                ref: t
            })
        })
    });
Eu.displayName = Tu;
var Du = _(`PopoverContent.RemoveScroll`),
    Ou = S.forwardRef((e, t) => {
        let n = hu(Tu, e.__scopePopover),
            r = S.useRef(null),
            i = u(t, r),
            o = S.useRef(!1);
        return S.useEffect(() => {
            let e = r.current;
            if (e) return el(e)
        }, []), (0, q.jsx)(lu, {
            as: Du,
            allowPinchZoom: !0,
            children: (0, q.jsx)(Au, {
                ...e,
                ref: i,
                trapFocus: n.open,
                disableOutsidePointerEvents: !0,
                onCloseAutoFocus: a(e.onCloseAutoFocus, e => {
                    e.preventDefault(), o.current || n.triggerRef.current?.focus()
                }),
                onPointerDownOutside: a(e.onPointerDownOutside, e => {
                    let t = e.detail.originalEvent,
                        n = t.button === 0 && t.ctrlKey === !0;
                    o.current = t.button === 2 || n
                }, {
                    checkForDefaultPrevented: !1
                }),
                onFocusOutside: a(e.onFocusOutside, e => e.preventDefault(), {
                    checkForDefaultPrevented: !1
                })
            })
        })
    }),
    ku = S.forwardRef((e, t) => {
        let n = hu(Tu, e.__scopePopover),
            r = S.useRef(!1),
            i = S.useRef(!1);
        return (0, q.jsx)(Au, {
            ...e,
            ref: t,
            trapFocus: !1,
            disableOutsidePointerEvents: !1,
            onCloseAutoFocus: t => {
                e.onCloseAutoFocus?.(t), t.defaultPrevented || (r.current || n.triggerRef.current?.focus(), t.preventDefault()), r.current = !1, i.current = !1
            },
            onInteractOutside: t => {
                e.onInteractOutside?.(t), t.defaultPrevented || (r.current = !0, t.detail.originalEvent.type === `pointerdown` && (i.current = !0));
                let a = t.target;
                n.triggerRef.current?.contains(a) && t.preventDefault(), t.detail.originalEvent.type === `focusin` && i.current && t.preventDefault()
            }
        })
    }),
    Au = S.forwardRef((e, t) => {
        let {
            __scopePopover: n,
            trapFocus: r,
            onOpenAutoFocus: i,
            onCloseAutoFocus: a,
            disableOutsidePointerEvents: o,
            onEscapeKeyDown: s,
            onPointerDownOutside: c,
            onFocusOutside: l,
            onInteractOutside: u,
            ...d
        } = e, f = hu(Tu, n), p = pu(n);
        return Oc(), (0, q.jsx)(Pc, {
            asChild: !0,
            loop: !0,
            trapped: r,
            onMountAutoFocus: i,
            onUnmountAutoFocus: a,
            children: (0, q.jsx)(x, {
                asChild: !0,
                disableOutsidePointerEvents: o,
                onInteractOutside: u,
                onEscapeKeyDown: s,
                onPointerDownOutside: c,
                onFocusOutside: l,
                onDismiss: () => f.onOpenChange(!1),
                children: (0, q.jsx)(g, {
                    "data-state": Fu(f.open),
                    role: `dialog`,
                    id: f.contentId,
                    ...p,
                    ...d,
                    ref: t,
                    style: {
                        ...d.style,
                        "--radix-popover-content-transform-origin": `var(--radix-popper-transform-origin)`,
                        "--radix-popover-content-available-width": `var(--radix-popper-available-width)`,
                        "--radix-popover-content-available-height": `var(--radix-popper-available-height)`,
                        "--radix-popover-trigger-width": `var(--radix-popper-anchor-width)`,
                        "--radix-popover-trigger-height": `var(--radix-popper-anchor-height)`
                    }
                })
            })
        })
    }),
    ju = `PopoverClose`,
    Mu = S.forwardRef((e, t) => {
        let {
            __scopePopover: n,
            ...r
        } = e, i = hu(ju, n);
        return (0, q.jsx)(l.button, {
            type: `button`,
            ...r,
            ref: t,
            onClick: a(e.onClick, () => i.onOpenChange(!1))
        })
    });
Mu.displayName = ju;
var Nu = `PopoverArrow`,
    Pu = S.forwardRef((e, t) => {
        let {
            __scopePopover: n,
            ...r
        } = e, i = pu(n);
        return (0, q.jsx)(o, {
            ...i,
            ...r,
            ref: t
        })
    });
Pu.displayName = Nu;

function Fu(e) {
    return e ? `open` : `closed`
}
var Iu = gu,
    Lu = bu,
    Ru = wu,
    zu = r(Eu)`
  background-color: var(--color-blue-700);
  color: var(--color-stone-100);
  border: 1px solid var(--color-blue-600);
  border-radius: 4px;
  min-width: 220px;
  max-width: 360px;
  padding: 6px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.45);
  font-size: 13px;
  z-index: 10;
`,
    Bu = r.div`
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 6px;
  border-radius: 3px;
  background-color: ${({$active:e})=>e?`
var (--color - blue - 600)`:`
transparent`};
`, Vu = r.div`
  padding: 1px 0;
  cursor: pointer;
  &:hover ${Bu} {
    background-color: var(--color-blue-600);
  }
`, Hu = r.div`
  height: 1px;
  background-color: var(--color-blue-600);
  margin: 4px 0;
`;

function Uu({
    trigger: e,
    open: t,
    onOpenChange: n,
    children: r,
    ...i
}) {
    return (0, q.jsxs)(Iu, {
        open: t,
        onOpenChange: n,
        children: [(0, q.jsx)(Lu, {
            asChild: !0,
            children: e
        }), (0, q.jsx)(Ru, {
            children: (0, q.jsx)(zu, {
                sideOffset: 4,
                align: `start`,
                ...i,
                children: r
            })
        })]
    })
}
var Wu = r.span`
  display: inline-flex;
  align-items: center;
  gap: 8px;
`,
    Gu = r.span`
  font-weight: 600;
  text-transform: uppercase;
`,
    Ku = r.span`
  color: var(--color-blue-300);
  font-weight: 400;
  user-select: none;
`,
    qu = r.button`
  display: inline-flex;
  align-items: center;
  background: transparent;
  border: none;
  border-radius: 3px;
  color: inherit;
  font: inherit;
  padding: 3px 6px;
  cursor: pointer;
  &:hover {
    background-color: var(--color-blue-700);
  }
  &[data-state="open"] {
    background-color: var(--color-blue-800);
  }
`,
    Ju = r.div`
  display: flex;
  flex-direction: column;
  max-height: 280px;
  overflow-y: auto;
`,
    Yu = r.span`
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding-left: 2px;
`,
    Xu = r.span`
  display: inline-flex;
  align-items: center;
  gap: 2px;
  visibility: ${({$alwaysVisible:e})=>e?`
visible`:`
hidden`};
  ${Vu}:hover & {
    visibility: visible;
  }
`, Zu = r.button`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  background: transparent;
  border: none;
  border-radius: 3px;
  color: inherit;
  opacity: 0.6;
  cursor: pointer;
  &:hover:not(:disabled) {
    opacity: 1;
    background-color: var(--color-blue-500);
  }
  &:disabled {
    opacity: 0.25;
    cursor: not-allowed;
  }
`, Qu = r.input`
  flex: 1;
  min-width: 0;
  background-color: var(--color-blue-900);
  border: 1px solid var(--color-blue-500);
  border-radius: 3px;
  color: inherit;
  font: inherit;
  padding: 2px 4px;
  outline: none;
  &:focus {
    border-color: var(--color-amber-300);
  }
`, $u = r.span`
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding-left: 2px;
  color: var(--color-stone-200);
`, ed = r.button`
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 5px 8px;
  border: none;
  background-color: transparent;
  color: inherit;
  font: inherit;
  border-radius: 3px;
  cursor: pointer;
  text-align: left;
  &:hover {
    background-color: var(--color-blue-600);
  }
  & svg {
    opacity: 0.7;
  }
`;

function td(e) {
    e.stopPropagation()
}

function nd(e, t) {
    S.useLayoutEffect(() => {
        if (!t) return;
        let n = e.current,
            r = n?.parentElement;
        if (!n || !r) return;
        let i = r.getBoundingClientRect(),
            a = n.getBoundingClientRect();
        a.top < i.top ? r.scrollTop -= i.top - a.top : a.bottom > i.bottom && (r.scrollTop += a.bottom - i.bottom)
    }, [e, t])
}

function rd({
    program: e,
    isActive: t,
    canRemove: n,
    isEditing: r,
    isConfirmingDelete: i,
    draft: a,
    onDraftChange: o,
    onSelect: s,
    onStartRename: c,
    onCommitRename: l,
    onCancelRename: u,
    onStartDelete: d,
    onConfirmDelete: f,
    onCancelDelete: p
}) {
    let m = S.useRef(null),
        h = S.useRef(null);
    return nd(h, t), S.useEffect(() => {
        r && (m.current?.focus(), m.current?.select())
    }, [r]), r ? (0, q.jsx)(Vu, {
        ref: h,
        onClick: td,
        children: (0, q.jsx)(Bu, {
            $active: t,
            children: (0, q.jsx)(Qu, {
                ref: m,
                value: a,
                onChange: e => o(e.target.value),
                onKeyDown: e => {
                    e.key === `Enter` ? l() : e.key === `Escape` && u()
                },
                onBlur: l,
                onClick: td
            })
        })
    }) : i ? (0, q.jsx)(Vu, {
        ref: h,
        onClick: td,
        children: (0, q.jsxs)(Bu, {
            $active: t,
            children: [(0, q.jsxs)($u, {
                children: [`Delete "`, e.name, `"?`]
            }), (0, q.jsxs)(Xu, {
                $alwaysVisible: !0,
                children: [(0, q.jsx)(Zu, {
                    onClick: e => {
                        td(e), f()
                    },
                    title: `Confirm delete`,
                    children: (0, q.jsx)(ni, {
                        size: 14
                    })
                }), (0, q.jsx)(Zu, {
                    onClick: e => {
                        td(e), p()
                    },
                    title: `Cancel`,
                    children: (0, q.jsx)(Pi, {
                        size: 14
                    })
                })]
            })]
        })
    }) : (0, q.jsx)(Vu, {
        ref: h,
        onClick: () => s(e.id),
        children: (0, q.jsxs)(Bu, {
            $active: t,
            children: [(0, q.jsx)(Yu, {
                children: e.name
            }), (0, q.jsxs)(Xu, {
                children: [(0, q.jsx)(Zu, {
                    onClick: e => {
                        td(e), c()
                    },
                    title: `Rename`,
                    children: (0, q.jsx)(oi, {
                        size: 13
                    })
                }), (0, q.jsx)(Zu, {
                    onClick: e => {
                        td(e), d()
                    },
                    disabled: !n,
                    title: n ? `Delete` : `Can't delete last program`,
                    children: (0, q.jsx)(Ai, {
                        size: 13
                    })
                })]
            })]
        })
    })
}

function id({
    programs: e,
    activeId: t,
    onSelect: n,
    onCreate: r,
    onRename: i,
    onRemove: a
}) {
    let [o, s] = S.useState(!1), [c, l] = S.useState(null), [u, d] = S.useState(``), [f, p] = S.useState(null), m = e.find(e => e.id === t) ?? e[0] ?? null;

    function h(e) {
        s(e), e || (l(null), d(``), p(null))
    }

    function g(e) {
        n(e)
    }

    function _(e) {
        p(null), l(e.id), d(e.name)
    }

    function v() {
        if (c === null) return;
        let t = e.find(e => e.id === c),
            n = u.trim();
        t && n && n !== t.name && i(c, n), l(null), d(``)
    }

    function y() {
        l(null), d(``)
    }

    function b(e) {
        l(null), p(e.id)
    }

    function x() {
        f !== null && (a(f), p(null))
    }

    function C() {
        p(null)
    }

    function w() {
        let e = r();
        p(null), e != null && (l(e), d(`Program ${e}`))
    }
    return (0, q.jsxs)(Wu, {
        children: [(0, q.jsx)(Gu, {
            children: `lm`
        }), (0, q.jsx)(Ku, {
            children: `/`
        }), (0, q.jsxs)(Uu, {
            open: o,
            onOpenChange: h,
            trigger: (0, q.jsx)(qu, {
                children: m ? m.name : `(no program)`
            }),
            children: [(0, q.jsx)(Ju, {
                children: e.map(n => (0, q.jsx)(rd, {
                    program: n,
                    isActive: n.id === t,
                    canRemove: e.length > 1,
                    isEditing: n.id === c,
                    isConfirmingDelete: n.id === f,
                    draft: u,
                    onDraftChange: d,
                    onSelect: g,
                    onStartRename: () => _(n),
                    onCommitRename: v,
                    onCancelRename: y,
                    onStartDelete: () => b(n),
                    onConfirmDelete: x,
                    onCancelDelete: C
                }, n.id))
            }), (0, q.jsx)(Hu, {}), (0, q.jsxs)(ed, {
                onClick: w,
                children: [(0, q.jsx)(`span`, {
                    children: `Create new program`
                }), (0, q.jsx)(Si, {
                    size: 14
                })]
            })]
        })]
    })
}
var ad = r.button`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 3px;
  color: inherit;
  padding: 4px;
  cursor: pointer;
  opacity: 0.75;
  &:hover {
    background-color: var(--color-blue-700);
    opacity: 1;
  }
  &[data-state="open"] {
    background-color: var(--color-blue-800);
    opacity: 1;
  }
`,
    od = r.span`
  flex: 1;
  white-space: nowrap;
`,
    sd = r.span`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding-left: 24px;
  color: var(--color-blue-300);
`,
    cd = r.span`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 15px;
  font-size: 15px;
  line-height: 1;
`,
    {
        mod: ld,
        shift: ud,
        alt: dd
    } = k,
    fd = {
        undo: [ld, `Z`],
        redo: [ud, ld, `Z`],
        zoomIn: [ld, `+`],
        zoomOut: [ld, `−`],
        flow: [dd, `F`]
    };

function pd({
    label: e,
    keys: t,
    checked: n,
    onSelect: r
}) {
    return (0, q.jsx)(Vu, {
        onClick: r,
        children: (0, q.jsxs)(Bu, {
            children: [(0, q.jsx)(od, {
                children: e
            }), t ? (0, q.jsx)(sd, {
                children: t.map((e, t) => (0, q.jsx)(cd, {
                    children: e
                }, t))
            }) : null, n === void 0 ? null : (0, q.jsx)(sd, {
                children: (0, q.jsx)(cd, {
                    children: n ? (0, q.jsx)(ni, {
                        size: 14
                    }) : null
                })
            })]
        })
    })
}

function md({
    onCopy: e,
    onSave: t,
    onUndo: n,
    onRedo: r,
    onZoomIn: i,
    onZoomOut: a,
    showFlow: o = !1,
    onToggleFlow: s = null,
    showRaw: c = !1,
    onToggleRaw: l = null,
    paceToDisplay: u = !1,
    onTogglePace: d = null,
    fileActions: f = !0
}) {
    let [p, m] = S.useState(!1), h = e => () => {
        e(), m(!1)
    };
    return (0, q.jsxs)(Uu, {
        open: p,
        onOpenChange: m,
        trigger: (0, q.jsx)(ad, {
            "aria-label": `Program actions`,
            children: (0, q.jsx)(mi, {
                size: 16
            })
        }),
        children: [f && (0, q.jsxs)(q.Fragment, {
            children: [(0, q.jsx)(pd, {
                label: `Copy to clipboard`,
                onSelect: h(e)
            }), (0, q.jsx)(pd, {
                label: `Save to file`,
                onSelect: h(t)
            }), (0, q.jsx)(Hu, {})]
        }), (0, q.jsx)(pd, {
            label: `Undo`,
            keys: fd.undo,
            onSelect: h(n)
        }), (0, q.jsx)(pd, {
            label: `Redo`,
            keys: fd.redo,
            onSelect: h(r)
        }), (0, q.jsx)(Hu, {}), (0, q.jsx)(pd, {
            label: `Zoom in`,
            keys: fd.zoomIn,
            onSelect: h(i)
        }), (0, q.jsx)(pd, {
            label: `Zoom out`,
            keys: fd.zoomOut,
            onSelect: h(a)
        }), s && (0, q.jsxs)(q.Fragment, {
            children: [(0, q.jsx)(Hu, {}), (0, q.jsx)(pd, {
                label: `Show program flow`,
                keys: fd.flow,
                checked: o,
                onSelect: h(s)
            })]
        }), l && (0, q.jsxs)(q.Fragment, {
            children: [(0, q.jsx)(Hu, {}), (0, q.jsx)(pd, {
                label: `Always show raw values`,
                checked: c,
                onSelect: h(l)
            })]
        }), d && (0, q.jsxs)(q.Fragment, {
            children: [!l && (0, q.jsx)(Hu, {}), (0, q.jsx)(pd, {
                label: `Show every display frame`,
                checked: u,
                onSelect: h(d)
            })]
        })]
    })
}

function hd(e) {
    let t = 1 / 0,
        n = 1 / 0,
        r = -1 / 0,
        i = -1 / 0;
    for (let a in e) {
        let o = e[a];
        if (!o || o === ` `) continue;
        let {
            x: s,
            y: c
        } = M(a);
        s < t && (t = s), c < n && (n = c), s > r && (r = s), c > i && (i = c)
    }
    return Number.isFinite(t) ? {
        w: r - t + 1,
        h: i - n + 1
    } : {
        w: 0,
        h: 0
    }
}
var gd = `${k.mod}${k.enter}`,
    _d = `@media (max-width: 720px)`,
    vd = r.header`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px 16px;
  /* Narrow hosts (embeds on phones/tablets) flow the controls onto extra
     rows instead of overflowing. */
  flex-wrap: wrap;
  padding: 6px 14px 8px;
  background-color: var(--color-blue-900);
  color: var(--color-stone-100);
  font-size: 13px;
  position: relative;
  z-index: 3;

  ${_d} {
    gap: 4px 8px;
    padding: 5px 8px 6px;
  }
`,
    yd = r.span`
  display: flex;
  align-items: center;
  gap: 2px;
`,
    bd = r.span`
  display: flex;
  align-items: center;
  gap: 6px 20px;
  flex-wrap: wrap;
  justify-content: flex-end;

  ${_d} {
    gap: 5px 8px;
  }
`,
    xd = r.span`
  display: inline-flex;
  align-items: center;
  gap: 6px;

  ${_d} {
    gap: 4px;
  }
`,
    Sd = r(Ec)`
  ${_d} {
    min-width: 0;
    padding: 4px 7px;
    font-size: 11px;
  }
`,
    Cd = r.span`
  ${_d} {
    display: none;
  }
`,
    wd = r.span`
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--color-amber-300);

  ${_d} {
    gap: 3px;
  }
`,
    Td = r.button`
  display: inline-flex;
  align-items: center;
  padding: 0;
  border: none;
  background: none;
  color: inherit;
  cursor: pointer;

  ${_d} {
    svg {
      width: 16px;
      height: 16px;
    }
  }
`,
    Ed = r.input.attrs({
        type: `range`
    })`
  width: 100px;
  margin: 0;
  accent-color: var(--color-amber-300);

  ${_d} {
    width: 56px;
  }
`,
    Dd = r.span`
  font-family: monospace;
  color: var(--color-stone-100);
  min-width: 48px;
  text-align: center;
  display: inline-block;

  ${_d} {
    min-width: 40px;
    font-size: 12px;
  }
`,
    Od = r.span`
  font-family: monospace;
  color: var(--color-stone-400);
  white-space: nowrap;
`,
    kd = r.span`
  font-family: monospace;
  min-width: 44px;

  ${_d} {
    min-width: 32px;
    font-size: 11px;
  }
`;

function Ad(e) {
    return e >= 1e3 ? `${e/1e3}k/s` : `${e}/s`
}

function jd(e) {
    return e < 1e5 ? String(e).padStart(5, `0`) : e < 1e6 ? `${Math.floor(e/1e3)}k`.padStart(5, ` `) : e < 1e9 ? `${(e/1e6).toFixed(1)}m`.padStart(5, ` `) : `${(e/1e9).toFixed(1)}g`.padStart(5, ` `)
}

function Md({
    isSimulating: e,
    snapshot: t,
    isPlaying: n,
    canNext: r,
    canBack: i,
    canPlay: a,
    ready: o,
    onRun: s,
    onNext: c,
    onBack: l,
    onTogglePlay: u,
    onStop: d,
    showStepCounter: f
}) {
    let p = n ? `pause` : `play`,
        m = !n && !a,
        h = e ? `stop` : o ? `run` : `connecting…`,
        g = e || o;
    return (0, q.jsxs)(q.Fragment, {
        children: [(0, q.jsxs)(xd, {
            children: [(0, q.jsxs)(Sd, {
                onClick: l,
                disabled: !i,
                children: [`back`, (0, q.jsx)(Cd, {
                    children: ` (b)`
                })]
            }), (0, q.jsxs)(Sd, {
                onClick: c,
                disabled: !r,
                children: [`next`, (0, q.jsx)(Cd, {
                    children: ` (n)`
                })]
            }), (0, q.jsxs)(Sd, {
                onClick: u,
                disabled: m,
                children: [p, (0, q.jsx)(Cd, {
                    children: ` (p)`
                })]
            })]
        }), f && (0, q.jsx)(Dd, {
            children: t ? jd(t.step) : `—`
        }), (0, q.jsxs)(Sd, {
            onClick: e ? d : s,
            disabled: !e && !o,
            children: [h, g && (0, q.jsxs)(Cd, {
                children: [` (`, gd, `)`]
            })]
        })]
    })
}

function Nd({
    program: e,
    driver: t,
    actions: n,
    speeds: r,
    speedIndex: i,
    setSpeedIndex: a,
    showProgramPicker: o = !0,
    fileActions: s = !0,
    showStepCounter: c = !0,
    showFootprint: l = !0,
    cells: u
}) {
    let d = S.useMemo(() => l && u ? hd(u) : null, [l, u]),
        {
            snapshot: f,
            ready: p,
            isSimulating: m,
            isPlaying: h,
            canNext: g,
            canBack: _,
            canPlay: v,
            onRun: y,
            onNext: b,
            onBack: x,
            onStop: C,
            onTogglePlay: w
        } = t;
    return (0, q.jsxs)(vd, {
        children: [(0, q.jsxs)(yd, {
            children: [o && (0, q.jsx)(id, {
                programs: e.programs,
                activeId: e.activeId,
                onSelect: e.setActive,
                onCreate: e.create,
                onRename: e.rename,
                onRemove: e.remove
            }), (0, q.jsx)(md, {
                onCopy: n.onCopy,
                onSave: n.onSave,
                onUndo: n.onUndo,
                onRedo: n.onRedo,
                onZoomIn: n.onZoomIn,
                onZoomOut: n.onZoomOut,
                showFlow: n.showFlow,
                onToggleFlow: n.onToggleFlow,
                showRaw: n.showRaw,
                onToggleRaw: n.onToggleRaw,
                paceToDisplay: n.paceToDisplay,
                onTogglePace: n.onTogglePace,
                fileActions: s
            })]
        }), (0, q.jsxs)(bd, {
            children: [d && (0, q.jsxs)(Od, {
                title: `program footprint — the bounding box of every non-space cell; scoring uses max(width, height)²`,
                children: [d.w, `×`, d.h]
            }), (0, q.jsxs)(wd, {
                title: `speed`,
                children: [(0, q.jsx)(Td, {
                    type: `button`,
                    "aria-label": `slowest`,
                    onClick: () => a(0),
                    children: (0, q.jsx)(ma, {
                        size: 20,
                        fill: `none`,
                        strokeWidth: 1.5
                    })
                }), (0, q.jsx)(Ed, {
                    min: 0,
                    max: r.length,
                    step: 1,
                    value: i,
                    "aria-label": `speed`,
                    onChange: e => a(Number(e.target.value))
                }), (0, q.jsx)(Td, {
                    type: `button`,
                    "aria-label": `fastest`,
                    onClick: () => a(r.length),
                    children: (0, q.jsx)(pa, {
                        size: 20,
                        fill: `none`,
                        strokeWidth: 1.5
                    })
                }), (0, q.jsx)(kd, {
                    children: i === r.length ? `max` : Ad(r[i])
                })]
            }), (0, q.jsx)(Md, {
                isSimulating: m,
                snapshot: f,
                isPlaying: h,
                canNext: g,
                canBack: _,
                canPlay: v,
                ready: p,
                onRun: y,
                onNext: b,
                onBack: x,
                onTogglePlay: w,
                onStop: C,
                showStepCounter: c
            })]
        })]
    })
}
var Pd = {
    canStep: !0,
    canBack: !0,
    canPlay: !0
};

function Fd(e, t) {
    let n = {
        ox: 0,
        oy: 0
    };
    async function r(t) {
        try {
            return he(await t(), n)
        } catch (t) {
            return console.warn(`${e}-runner: request failed`, t), null
        }
    }
    return {
        name: e,
        async getCapabilities() {
            return t.warmup?.(), Pd
        },
        async load(e, {
            input: r = ``,
            expected: i = ``,
            frames: a = null
        } = {}) {
            let {
                rows: o,
                offset: s
            } = me(e);
            if (o.length === 0) return null;
            n = s;
            try {
                return he(await t.load(o, r, i, a), s)
            } catch (e) {
                throw ge(e.message, e.pos, s)
            }
        },
        async step() {
            return r(() => t.step())
        },
        async stepMany(e, {
            stopOnFrame: n = !1
        } = {}) {
            return r(() => t.stepN(e, n))
        },
        async back() {
            return r(() => t.back())
        },
        dispose() {
            t.dispose?.()
        }
    }
}

function Id() {
    let e = null,
        t = 0;
    async function n(n) {
        let r = t,
            i = await Ce();
        if (t !== r) throw Error(`wasm-runner: disposed while call was in flight`);
        return e === null && (e = i.newSession()), Te(n(i, e))
    }
    return Fd(`wasm`, {
        warmup: () => Ce().catch(() => {}),
        load: (e, t, r, i) => n((n, a) => n.load(a, e, t, r, i?.length ? JSON.stringify(i) : ``)),
        step: () => n((e, t) => e.step(t)),
        stepN: (e, t) => n((n, r) => n.stepN(r, e, !!t)),
        back: () => n((e, t) => e.back(t)),
        dispose: () => {
            if (t += 1, e === null) return;
            let n = e;
            e = null, Ce().then(e => e.closeSession(n)).catch(() => {})
        }
    })
}

function Ld(e, t) {
    let n = t[0] - e[0],
        r = t[1] - e[1];
    return n > 0 ? `E` : n < 0 ? `W` : r > 0 ? `S` : r < 0 ? `N` : null
}
var Rd = {
    cellTints: {},
    cellGlyphs: {},
    regionLabels: []
};

function zd(e, t = {}) {
    if (!e) return Rd;
    let {
        runners: n = [],
        pipes: r = [],
        rooms: i = [],
        displays: a = []
    } = e, {
        backBufferIds: o = null,
        onToggleBuffer: s = null
    } = t, c = {}, l = {}, u = [];
    for (let e of a) {
        let t = [e.min[0], e.min[1], e.max[0], e.max[1]],
            n = `display-${t.join(`-`)}`,
            r = !!o?.has(n) && (e.back?.length ?? 0) > 0,
            i = r ? e.back : e.front;
        for (let t = 0; t < i.length; t++) {
            let n = A(e.min[0] + 1 + t % e.w, e.min[1] + 1 + Math.floor(t / e.w));
            c[n] = Hn(i[t]), l[n] = ` `
        }
        u.push({
            id: n,
            kind: `display`,
            rect: t,
            position: `below`,
            render: ({
                collapsed: t,
                toggle: i
            }) => (0, q.jsx)(Ma, {
                display: e,
                collapsed: t,
                toggle: i,
                showBack: r,
                onToggleBuffer: s ? () => s(n) : null
            })
        })
    }
    for (let e of r) {
        for (let t of e.values) {
            let n = e.path[t.index];
            if (!n) continue;
            let r = A(n[0], n[1]);
            c[r] = X.pipeValue
        }
        if (e.path.length === 0) continue;
        let t = e.path[0],
            n = e.path[e.path.length - 1],
            r = e.path[e.path.length - 2],
            i = r ? Ld(r, n) : null;
        u.push({
            id: `pipe-${t[0]}-${t[1]}-${n[0]}-${n[1]}`,
            pipeAnchor: {
                cell: n,
                flowDirection: i
            },
            pipeCells: e.path.map(([e, t]) => A(e, t)),
            render: ({
                pinned: t,
                togglePin: n,
                selectedKey: r
            }) => (0, q.jsx)(Ca, {
                pipe: e,
                flowDirection: i,
                pinned: t,
                togglePin: n,
                selectedKey: r
            })
        })
    }
    for (let e of n) {
        let t = A(e.pos[0], e.pos[1]);
        c[t] = X.runner, l[t] = `@`
    }
    let d = new Map(n.map(e => [e.id, e]));
    for (let e of i) {
        if (!e.runners || e.runners.length === 0) continue;
        let t = e.runners.map(e => d.get(e)).filter(Boolean);
        if (t.length === 0) continue;
        let n = [e.min[0], e.min[1], e.max[0], e.max[1]];
        u.push({
            id: `room-${n.join(`-`)}`,
            kind: `room`,
            rect: n,
            position: `below`,
            render: ({
                collapsed: e,
                toggle: n
            }) => (0, q.jsx)(ta, {
                runners: t,
                collapsed: e,
                toggle: n
            })
        })
    }
    return {
        cellTints: c,
        cellGlyphs: l,
        regionLabels: u
    }
}
var Bd = {
        x: 103,
        y: 102
    },
    Vd = `+-+
|I|
+-+

+-+
|O|
+-+`;

function Hd() {
    let e = ae(Vd),
        t = {};
    for (let n of Object.keys(e)) {
        let {
            x: r,
            y: i
        } = M(n);
        t[A(r + Bd.x, i + Bd.y)] = e[n]
    }
    return t
}

function Ud({
    w: e,
    h: t
}) {
    let n = Hd();
    if (!Number.isInteger(e) || !Number.isInteger(t) || e < 1 || t < 1 || e > 64 || t > 64) return n;
    let r = Bd.x + 8,
        i = Bd.y;
    for (let {
            x: a,
            y: o,
            content: s
        }
        of lt({
            minX: r,
            minY: i,
            maxX: r + e + 1,
            maxY: i + t + 1
        })) n[A(a, o)] = s;
    return n
}
var Wd = r.div`
  display: flex;
  flex-direction: column;
  height: 100%;
`,
    Gd = r.div`
  position: relative;
  flex: 1;
  min-height: 0;
`,
    Kd = r.div`
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-stone-500);
`,
    qd = () => {},
    Jd = [1, 3, 10, 30, 100, 300, 1e3, 3e3],
    Yd = Jd.length,
    Xd = 1e6,
    Zd = 2;

function Qd({
    error: e,
    onDismiss: t,
    onJumpToCell: n
}) {
    if (!e) return null;
    let r = e.cell ? (0, q.jsxs)(q.Fragment, {
        children: [` at `, (0, q.jsx)(an, {
            x: e.cell.x,
            y: e.cell.y,
            onJump: n
        })]
    }) : null;
    return (0, q.jsxs)(xo, {
        onDismiss: t,
        children: [e.message, r]
    })
}

function $d({
    program: e,
    gridPersist: t,
    gridInitialCells: n,
    runnerFactory: r = Id,
    io: i = {
        mode: `none`
    },
    editable: a = !0,
    autoFocus: o = !1,
    showHeader: s = !1,
    showProgramPicker: c = !0,
    fileActions: l = !0,
    showStepCounter: u = !0,
    showFootprint: d = !0,
    showToolPalette: f = !0,
    showRuntimePanels: p = !0,
    showPanelControls: m = !0,
    initialRoomsCollapsed: h = null,
    initialDisplaysCollapsed: g = null,
    initialPipesPinned: _ = !1,
    initialCellSize: v = null,
    initialTicksPerSecond: y = null,
    showReference: b = !0,
    testCases: x = null,
    onSubmitProgram: C = null,
    ioSpec: w = null,
    problemReference: T = null
}) {
    let ee = i.mode === `panel`,
        D = e.activeId,
        k = Rt({
            programId: D,
            persist: t,
            initialCells: n
        }),
        A = S.useMemo(() => {
            if (t) return null;
            let e = n ? Object.keys(n) : [];
            if (e.length === 0) return null;
            let r = 1 / 0,
                i = -1 / 0,
                a = 1 / 0,
                o = -1 / 0;
            for (let t of e) {
                let {
                    x: e,
                    y: n
                } = M(t);
                e < r && (r = e), e > i && (i = e), n < a && (a = n), n > o && (o = n)
            }
            return {
                x: Math.round((r + i) / 2),
                y: Math.round((a + o) / 2)
            }
        }, [t, n]),
        j = S.useMemo(() => r(), [D, r]);
    S.useEffect(() => () => j.dispose?.(), [j]);
    let ne = S.useRef(k.cells);
    ne.current = k.cells;
    let N = i.mode === `panel` && i.persist !== !1,
        [re, P] = Yt(N ? R(D) : null, i.initialInput ?? ``),
        [F, I] = Yt(N ? z(D) : null, i.initialExpected ?? ``),
        [ie, ae] = S.useState(null),
        [ce, le] = S.useState(!0),
        ue = S.useCallback(() => le(e => !e), []),
        [L, de] = S.useState(() => new Set),
        fe = S.useCallback(e => {
            de(t => {
                let n = new Set(t);
                return n.has(e) ? n.delete(e) : n.add(e), n
            })
        }, []);
    S.useEffect(() => {
        de(new Set)
    }, [D]);
    let pe = S.useCallback(e => {
            ae(null), P(e)
        }, [P]),
        me = S.useCallback(e => {
            ae(null), I(e)
        }, [I]),
        [he, ge] = S.useState(null),
        _e = S.useCallback((e = {}) => {
            ae(null), ge(e)
        }, []),
        ve = S.useMemo(() => Ee(), []),
        [ye, be] = S.useState(() => {
            if (y == null) return Zd;
            let e = 0;
            for (let t = 1; t < Jd.length; t++) Math.abs(Jd[t] - y) < Math.abs(Jd[e] - y) && (e = t);
            return e
        }),
        xe = E({
            runner: j,
            cells: k.cells,
            input: qo(re),
            expected: qo(F),
            frames: ie,
            ticksPerSecond: ye === Yd ? Xd : Jd[ye],
            paceToDisplay: ce
        }),
        {
            snapshot: B,
            loadError: Se,
            ready: Ce,
            isSimulating: V,
            isPlaying: H,
            onRun: we,
            onNext: Te,
            onBack: De,
            onStop: Oe,
            onTogglePlay: ke
        } = xe,
        U = S.useMemo(() => Yo(qo(F)), [F]),
        Ae = S.useCallback(() => {
            V ? Oe() : Ce && _e()
        }, [V, Ce, _e, Oe]),
        je = S.useCallback(() => {
            V ? Oe() : Ce && _e({
                autoPlay: !1
            })
        }, [V, Ce, _e, Oe]);
    J({
        key: `Enter`,
        modifiers: `meta`,
        callback: Ae,
        allowInFormControl: !0
    }), J({
        key: `Enter`,
        modifiers: `ctrl`,
        callback: Ae,
        allowInFormControl: !0
    }), J({
        key: `Enter`,
        modifiers: `meta+shift`,
        callback: je,
        allowInFormControl: !0
    }), J({
        key: `Enter`,
        modifiers: `ctrl+shift`,
        callback: je,
        allowInFormControl: !0
    }), J({
        key: `Escape`,
        modifiers: `none`,
        callback: S.useCallback(e => {
            te() && (e?.target?.closest?.(`[data-littleman-key-scope]`) ?? document).querySelector(`[data-littleman-hidden-input]`)?.focus()
        }, []),
        allowInFormControl: !0
    });
    let Pe = S.useCallback(e => {
            V && (e.preventDefault(), ke())
        }, [V, ke]),
        W = S.useCallback(e => {
            V && (e.preventDefault(), H && ke(), Te())
        }, [V, H, ke, Te]),
        Fe = S.useCallback(e => {
            V && (e.preventDefault(), H && ke(), De())
        }, [V, H, ke, De]);
    J({
        key: `p`,
        modifiers: `none`,
        callback: Pe
    }), J({
        key: `n`,
        modifiers: `none`,
        callback: W
    }), J({
        key: `b`,
        modifiers: `none`,
        callback: Fe
    });
    let Ie = S.useCallback(e => {
            V && (e.preventDefault(), be(e => Math.min(Yd, e + 1)))
        }, [V]),
        Le = S.useCallback(e => {
            V && (e.preventDefault(), be(e => Math.max(0, e - 1)))
        }, [V]);
    J({
        key: `+`,
        modifiers: `shift`,
        callback: Ie
    }), J({
        key: `+`,
        modifiers: `none`,
        callback: Ie
    }), J({
        key: `=`,
        modifiers: `none`,
        callback: Ie
    }), J({
        key: `-`,
        modifiers: `none`,
        callback: Le
    });
    let Re = k.getCellContent,
        ze = S.useCallback((e, t) => {
            let n = Re(e, t);
            return B && n === `@` ? `` : n
        }, [B, Re]),
        Be = e => S.useMemo(() => a ? V ? (...t) => (Oe(), e(...t)) : e : qd, [a, V, e, Oe]),
        Ve = Be(k.setCellContent),
        He = Be(k.setCellsBulk),
        Ue = Be(k.moveRoom),
        We = Be(k.undo),
        Ge = Be(k.redo),
        Ke = S.useMemo(() => zd(B?.entities, {
            backBufferIds: L,
            onToggleBuffer: fe
        }), [B?.entities, L, fe]),
        [qe, Je] = S.useState(!1),
        Ye = S.useCallback(() => Je(e => !e), []),
        [Xe, Ze] = S.useState(!1),
        Qe = S.useCallback(() => Ze(e => !e), []),
        $e = S.useMemo(() => qe && !V ? Me(k.cells) : null, [qe, V, k.cells]),
        et = S.useCallback(e => {
            e.preventDefault(), Ye()
        }, [Ye]);
    J({
        key: `f`,
        modifiers: `alt`,
        callback: et
    }), J({
        key: `ƒ`,
        modifiers: `alt`,
        callback: et
    });
    let tt = S.useMemo(() => Fs({
            isSimulating: V,
            snapshot: B,
            expected: U
        }), [V, B, U]),
        nt = S.useMemo(() => Ko(B), [B]),
        [rt, it] = S.useState(null),
        at = V ? tt?.tone === `pass` ? null : nt : Se,
        ot = at === rt ? null : at,
        st = S.useCallback(() => it(at), [at]),
        ct = ot?.cell ?? null,
        G = S.useRef(null),
        lt = S.useCallback((e, t) => {
            G.current?.jumpToCell(e, t)
        }, []),
        K = e.programs.find(e => e.id === D)?.name ?? `program`,
        ut = S.useMemo(() => ({
            onCopy: () => navigator.clipboard.writeText(oe(k.cells)),
            onSave: () => se(`${K.replace(/[^\w.-]+/g,`_`)}.man`, oe(k.cells)),
            onUndo: () => G.current?.undo(),
            onRedo: () => G.current?.redo(),
            onZoomIn: () => G.current?.zoomIn(),
            onZoomOut: () => G.current?.zoomOut(),
            showFlow: qe,
            onToggleFlow: Ye,
            showRaw: Xe,
            onToggleRaw: w ? Qe : null,
            paceToDisplay: ce,
            onTogglePace: ue
        }), [k.cells, K, qe, Ye, Xe, Qe, w, ce, ue]),
        dt = S.useCallback(({
            selectedCell: e
        }) => {
            let t = {};
            if (!e) return t;
            let {
                x: n,
                y: r
            } = e;
            for (let e of Ne(k.cells, n, r)) t[e] = X.pipeHighlight;
            return t
        }, [k.cells]),
        ft = S.useCallback(async ({
            input: e,
            expected: t,
            frames: n = null,
            maxTicks: i = O
        }) => {
            let a = r();
            try {
                let r = Yo(qo(t ?? ``)),
                    o;
                try {
                    o = await a.load(ne.current, {
                        input: qo(e ?? ``),
                        expected: qo(t ?? ``),
                        frames: n
                    })
                } catch (e) {
                    return {
                        status: `error`,
                        output: [],
                        message: e.message
                    }
                }
                if (!o) return {
                    status: `error`,
                    output: [],
                    message: `empty program`
                };
                for (; !o.halted && !o.outputSettled && o.step < i;) {
                    let e = await a.stepMany(5e3);
                    if (!e) return {
                        status: `error`,
                        output: o.output ?? [],
                        message: `execution failed`
                    };
                    if (e.step === o.step) break;
                    o = e
                }
                let s = o.output ?? [],
                    c = o.frameJudge ?? null,
                    l = Xo(s, r);
                if (c?.mismatch) return {
                    status: `fail`,
                    output: s,
                    message: `frame ${c.mismatch.index+1} of ${c.total} wrong`,
                    frameJudge: c
                };
                let u = !c || c.matched >= c.total;
                return l === `match` && u ? {
                    status: `pass`,
                    output: s,
                    frameJudge: c
                } : l === `diverged` || l === `extra` ? {
                    status: `fail`,
                    output: s,
                    frameJudge: c
                } : o.halted && !Vo(o.reason) ? {
                    status: `crash`,
                    output: s,
                    message: o.fatal?.reason ?? o.reason,
                    frameJudge: c
                } : o.halted ? {
                    status: `fail`,
                    output: s,
                    message: l === `match` && c ? `missing frames (${c.matched}/${c.total})` : `missing output`,
                    frameJudge: c
                } : {
                    status: `timeout`,
                    output: s,
                    message: `no verdict after ${o.step} ticks`,
                    frameJudge: c
                }
            } finally {
                a.dispose?.()
            }
        }, [r]),
        pt = S.useCallback(({
            input: e,
            expected: t,
            frames: n
        }) => {
            Oe(), P(e ?? ``), I(t ?? ``), ae(n?.length ? n : null), ge({})
        }, [Oe, P, I]);
    S.useEffect(() => {
        he && (ge(null), we(he))
    }, [he, we]);
    let mt = S.useMemo(() => {
            let e = [];
            return T && e.push({
                key: `problem`,
                label: `problem`,
                title: `Problem reference`,
                surface: `light`,
                render: () => T
            }), x?.length && e.push({
                key: `tests`,
                label: `test cases`,
                title: `Test cases`,
                render: e => (0, q.jsx)(Tc, {
                    cases: x,
                    onSubmit: C,
                    editorApi: e,
                    ioSpec: w,
                    showRaw: Xe,
                    onToggleRaw: w ? Qe : null
                })
            }), b && e.push(Ro), e
        }, [T, x, C, b, w, Xe, Qe]),
        ht = S.useMemo(() => ({
            input: re,
            expected: F,
            setInput: pe,
            setExpected: me,
            isSimulating: V,
            isPlaying: H,
            verdict: tt,
            loadError: Se,
            onRun: _e,
            onStop: Oe,
            runWithIO: pt,
            getProgramText: () => oe(ne.current),
            runCase: ft,
            liveFrameJudge: B?.frameJudge ?? null
        }), [re, F, pe, me, V, H, tt, Se, _e, Oe, pt, ft, B?.frameJudge]);
    return (0, q.jsxs)(Wd, {
        children: [s && (0, q.jsx)(Nd, {
            program: e,
            driver: {
                ...xe,
                onRun: _e
            },
            actions: ut,
            speeds: Jd,
            speedIndex: ye,
            setSpeedIndex: be,
            showProgramPicker: c,
            fileActions: l,
            showStepCounter: u,
            showFootprint: d,
            cells: k.cells
        }), (0, q.jsxs)(Gd, {
            children: [(0, q.jsx)(go, {
                ref: G,
                getDisplayCellContent: ze,
                getSourceCellContent: k.getCellContent,
                setCellContent: Ve,
                setCellsBulk: He,
                undo: We,
                redo: Ge,
                wallCells: k.wallCells,
                roomCells: k.roomCells,
                pipeCells: k.pipeCells,
                displayWallCells: k.displayWallCells,
                displayCells: k.displayCells,
                rooms: k.rooms,
                moveRoom: Ue,
                previewMoveRoom: k.previewMoveRoom,
                specialWallCells: k.specialWallCells,
                specialMarkerCells: k.specialMarkerCells,
                validOps: ve,
                cellTints: Ke.cellTints,
                errorCell: ct,
                cellGlyphs: Ke.cellGlyphs,
                flowCells: $e?.cells,
                flowTerminals: $e?.terminals,
                regionLabels: Ke.regionLabels,
                highlightForSelection: dt,
                viewPersistKey: t ? D : null,
                initialCenter: A,
                initialCellSize: v,
                autoFocus: o,
                readOnly: !a,
                showToolPalette: f && a,
                showRuntimePanels: p,
                showPanelControls: m,
                initialRoomsCollapsed: h,
                initialDisplaysCollapsed: g,
                initialPipesPinned: _,
                isSimulating: V
            }), (0, q.jsx)(Qd, {
                error: ot,
                onDismiss: st,
                onJumpToCell: lt
            }), mt.length > 0 && (0, q.jsx)(Bo, {
                tabs: mt,
                editorApi: ht
            })]
        }), ee && (0, q.jsx)(Is, {
            input: re,
            setInput: pe,
            expected: F,
            setExpected: me,
            expectedTokens: U,
            snapshot: B,
            isSimulating: V,
            ioSpec: w,
            showRaw: Xe
        })]
    })
}

function ef(e, t) {
    let n = t != null,
        r = t?.id ?? null,
        i = t?.createName ?? null,
        a = S.useRef(e);
    a.current = e;
    let o = S.useRef(null);
    o.current = t?.onChange ?? null;
    let s = S.useRef(null);
    S.useLayoutEffect(() => {
        if (!n) return;
        let e = a.current;
        if (r != null && e.programs.some(e => e.id === r)) {
            e.activeId !== r && e.setActive(r);
            return
        }
        i == null || s.current === i || (s.current = i, e.create(tn(i, e.programs)))
    }, [n, r, i]);
    let c = e.activeId;
    S.useEffect(() => {
        n && o.current?.(c)
    }, [n, c])
}

function tf({
    restoreProgram: e,
    source: t,
    ...n
}) {
    let r = nn(),
        i = t?.template ?? null,
        a = S.useMemo(() => i ?? Hd(), [i]);
    return ef(r, e), (0, q.jsx)($d, {
        ...n,
        program: r,
        gridPersist: !0,
        gridInitialCells: a
    })
}

function nf(e) {
    let t = e.id ?? `embed`,
        n = e.name ?? `program`;
    return S.useMemo(() => ({
        programs: [{
            id: t,
            name: n
        }],
        activeId: t,
        setActive: qd,
        create: qd,
        rename: qd,
        remove: qd
    }), [t, n])
}

function rf({
    source: e,
    ...t
}) {
    let n = nf(e),
        r = S.useMemo(() => e.cells ?? (e.text == null ? {} : ae(e.text)), [e.cells, e.text]);
    return (0, q.jsx)($d, {
        ...t,
        showProgramPicker: !1,
        program: n,
        gridPersist: !1,
        gridInitialCells: r
    })
}

function af({
    wasmUrl: e,
    wasmExecUrl: t
}) {
    let [n, r] = S.useState(() => V() ? {
        ready: !0,
        error: null
    } : {
        ready: !1,
        error: null
    });
    return S.useEffect(() => {
        if (n.ready) return;
        let i = !0;
        return Ce({
            wasmUrl: e,
            wasmExecUrl: t
        }).then(() => i && r({
            ready: !0,
            error: null
        })).catch(e => i && r({
            ready: !1,
            error: e?.message ?? String(e)
        })), () => {
            i = !1
        }
    }, [n.ready, e, t]), n
}

function of({
    source: e,
    ...t
}) {
    return e.mode === `fixed` ? (0, q.jsx)(rf, {
        source: e,
        ...t
    }) : (0, q.jsx)(tf, {
        source: e,
        ...t
    })
}

function sf({
    source: e = {
        mode: `localStorage`
    },
    wasmUrl: t,
    wasmExecUrl: n,
    gate: r = !0,
    globalHotkeys: i = !1,
    ...a
}) {
    let o = af({
        wasmUrl: t,
        wasmExecUrl: n
    });
    return r && !o.ready ? (0, q.jsx)(Kd, {
        children: o.error ? `interpreter failed to load (${o.error}) — reload to retry` : `Loading…`
    }) : (0, q.jsx)(Gt, {
        global: i,
        children: (0, q.jsx)(of, {
            source: e,
            ...a
        })
    })
}
export {
    ps as a, Yr as c, Kr as d, qr as f, is as i, Jr as l, Ud as n, ms as o, Ks as r, ls as s, sf as t, Gr as u
};