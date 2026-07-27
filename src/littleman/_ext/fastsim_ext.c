/* fastsim_ext: bit-exact C transcription of littleman/fastsim.py's run_program,
 * which is itself a transcription of sim.py's Machine._tick / _execute.
 *
 * Boundary: one function, run(spec_dict, controller, input_queue, max_ticks).
 * Everything is handed over as flat Python lists of ints, converted once. */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

#define OP_LIT 5
#define OP_HALT 7

typedef struct {
    int32_t len;
    int32_t *runs;   /* flat [s0,e0,s1,e1,...] */
    int32_t nruns;   /* number of ints used (2 * runs) */
    int32_t runs_cap;
    int64_t *vals;   /* ring buffer, capacity len */
    int32_t head;
    int32_t count;
    int32_t turn;
    int32_t src_pos, dst_pos;
    int32_t *recv_w; int32_t recv_n, recv_cap;
    int32_t *send_w; int32_t send_n, send_cap;
} Pipe;

typedef struct {
    int32_t addr, data, swap, w, h;
    int8_t *cur, *nxt;
    int32_t cursor;
} Disp;

/* ------------------------------------------------------------- conversion */
static int32_t *list_i32(PyObject *o, Py_ssize_t *n_out)
{
    Py_ssize_t n = PyList_Size(o);
    if (n < 0) return NULL;
    int32_t *a = (int32_t *)PyMem_Malloc((n ? n : 1) * sizeof(int32_t));
    if (!a) { PyErr_NoMemory(); return NULL; }
    for (Py_ssize_t i = 0; i < n; i++) {
        long v = PyLong_AsLong(PyList_GET_ITEM(o, i));
        if (v == -1 && PyErr_Occurred()) { PyMem_Free(a); return NULL; }
        a[i] = (int32_t)v;
    }
    if (n_out) *n_out = n;
    return a;
}

static int64_t *list_i64(PyObject *o, Py_ssize_t *n_out)
{
    Py_ssize_t n = PyList_Size(o);
    if (n < 0) return NULL;
    int64_t *a = (int64_t *)PyMem_Malloc((n ? n : 1) * sizeof(int64_t));
    if (!a) { PyErr_NoMemory(); return NULL; }
    for (Py_ssize_t i = 0; i < n; i++) {
        int64_t v = (int64_t)PyLong_AsLongLong(PyList_GET_ITEM(o, i));
        if (v == -1 && PyErr_Occurred()) { PyMem_Free(a); return NULL; }
        a[i] = v;
    }
    if (n_out) *n_out = n;
    return a;
}

static PyObject *get(PyObject *d, const char *k)
{
    PyObject *v = PyDict_GetItemString(d, k);
    if (!v) PyErr_Format(PyExc_KeyError, "missing spec key %s", k);
    return v;
}

/* --------------------------------------------------------------- int64 ops */
static inline int64_t wrap_add(int64_t a, int64_t b)
{ return (int64_t)((uint64_t)a + (uint64_t)b); }
static inline int64_t wrap_sub(int64_t a, int64_t b)
{ return (int64_t)((uint64_t)a - (uint64_t)b); }
static inline int64_t wrap_mul(int64_t a, int64_t b)
{ return (int64_t)((uint64_t)a * (uint64_t)b); }

/* Python floored division / modulo on int64, then wrapped. */
static inline void floordivmod(int64_t a, int64_t b, int64_t *q, int64_t *r)
{
    if (b == -1) {                       /* covers INT64_MIN / -1 */
        *q = (int64_t)(0 - (uint64_t)a);
        *r = 0;
        return;
    }
    int64_t tq = a / b, tr = a % b;
    if (tr != 0 && ((tr < 0) != (b < 0))) { tq -= 1; tr += b; }
    *q = tq; *r = tr;
}

/* ------------------------------------------------------------------ state */
typedef struct {
    int32_t W, H, size;
    int32_t *code[4];
    int64_t *lit[4];
    int32_t *step[4];
    int32_t *cellpos;
    int32_t n_cells;

    int32_t n_men;
    int32_t *mcell, *mdir, *mroom, *mhalt;
    int64_t *mA, *mB, *mBP;
    int32_t *wkind;          /* 0 none, 1 r, 2 RU, 3 s, 4 S */
    int32_t **wptr; int32_t *wlen;
    int32_t *wsingle;        /* per-man one-slot buffer for r/s */
    int32_t n_recv_wait, n_send_wait;

    int32_t *runflag, *runbuf, runbuf_n, n_runnable;
    int32_t *heap, heap_n;
    int64_t *stamp; int64_t tick;
    int32_t cur_index, in_execute;

    int32_t n_pipes;
    Pipe *pipes;
    int32_t *act_buf, *act_pos, act_n;

    int32_t *room_out_off, *room_out_idx;
    int32_t *room_in_off, *room_in_idx;
    int32_t *room_ins_off, *room_ins_idx;
    int32_t *near_out, *near_in;

    int32_t input_pipe, output_pipe;
    int32_t *disp_pipes, n_disp_pipes;
    Disp *disps; int32_t n_disps;

    int32_t *occ;            /* pos -> man index, -1 empty */
} Ctx;

static void heap_push(Ctx *x, int32_t v)
{
    int32_t i = x->heap_n++;
    x->heap[i] = v;
    while (i > 0) {
        int32_t p = (i - 1) >> 1;
        if (x->heap[p] <= x->heap[i]) break;
        int32_t t = x->heap[p]; x->heap[p] = x->heap[i]; x->heap[i] = t;
        i = p;
    }
}

static int32_t heap_pop(Ctx *x)
{
    int32_t top = x->heap[0];
    int32_t n = --x->heap_n;
    x->heap[0] = x->heap[n];
    int32_t i = 0;
    for (;;) {
        int32_t l = 2 * i + 1, r = l + 1, m = i;
        if (l < n && x->heap[l] < x->heap[m]) m = l;
        if (r < n && x->heap[r] < x->heap[m]) m = r;
        if (m == i) break;
        int32_t t = x->heap[m]; x->heap[m] = x->heap[i]; x->heap[i] = t;
        i = m;
    }
    return top;
}

static void runnable_add(Ctx *x, int32_t i)
{
    if (x->runflag[i]) return;
    x->runflag[i] = 1;
    x->runbuf[x->runbuf_n++] = i;
    x->n_runnable++;
}

static void runnable_discard(Ctx *x, int32_t i)
{
    if (!x->runflag[i]) return;
    x->runflag[i] = 0;
    x->n_runnable--;
}

static void act_add(Ctx *x, int32_t pi)
{
    if (x->act_pos[pi] >= 0) return;
    x->act_pos[pi] = x->act_n;
    x->act_buf[x->act_n++] = pi;
}

static void act_del(Ctx *x, int32_t pi)
{
    int32_t p = x->act_pos[pi];
    if (p < 0) return;
    int32_t last = x->act_buf[--x->act_n];
    x->act_buf[p] = last;
    x->act_pos[last] = p;
    x->act_pos[pi] = -1;
}

static void wlist_add(int32_t **arr, int32_t *n, int32_t *cap, int32_t v)
{
    for (int32_t i = 0; i < *n; i++) if ((*arr)[i] == v) return;
    if (*n == *cap) {
        int32_t nc = *cap ? *cap * 2 : 4;
        *arr = (int32_t *)PyMem_Realloc(*arr, nc * sizeof(int32_t));
        *cap = nc;
    }
    (*arr)[(*n)++] = v;
}

static void wlist_del(int32_t *arr, int32_t *n, int32_t v)
{
    for (int32_t i = 0; i < *n; i++)
        if (arr[i] == v) { arr[i] = arr[--(*n)]; return; }
}

static void clear_wait(Ctx *x, int32_t i)
{
    int32_t k = x->wkind[i];
    if (!k) { x->wlen[i] = 0; return; }
    int recv = (k == 1 || k == 2);
    for (int32_t j = 0; j < x->wlen[i]; j++) {
        Pipe *p = &x->pipes[x->wptr[i][j]];
        if (recv) wlist_del(p->recv_w, &p->recv_n, i);
        else      wlist_del(p->send_w, &p->send_n, i);
    }
    if (recv) x->n_recv_wait--; else x->n_send_wait--;
    x->wkind[i] = 0;
    x->wlen[i] = 0;
}

static int cond_ready(Ctx *x, int32_t i)
{
    int32_t k = x->wkind[i];
    int32_t n = x->wlen[i];
    int32_t *w = x->wptr[i];
    if (k == 1) {
        Pipe *p = &x->pipes[w[0]];
        return p->nruns && p->runs[p->nruns - 1] == p->len - 1;
    }
    if (k == 2) {
        for (int32_t j = 0; j < n; j++) {
            Pipe *p = &x->pipes[w[j]];
            if (p->nruns && p->runs[p->nruns - 1] == p->len - 1) return 1;
        }
        return 0;
    }
    if (k == 3) {
        Pipe *p = &x->pipes[w[0]];
        return !(p->nruns && p->runs[0] == 0);
    }
    if (k == 4) {
        for (int32_t j = 0; j < n; j++) {
            Pipe *p = &x->pipes[w[j]];
            if (p->nruns && p->runs[0] == 0) return 0;
        }
        return 1;
    }
    return 0;
}

static void maybe_wake(Ctx *x, int32_t i)
{
    if (!x->wkind[i] || !cond_ready(x, i)) return;
    if (x->mhalt[i]) return;
    clear_wait(x, i);
    if (x->in_execute && i > x->cur_index && x->stamp[i] != x->tick)
        heap_push(x, i);
    else
        runnable_add(x, i);
}

static void wake_list(Ctx *x, int32_t *src, int32_t n)
{
    int32_t buf[64], *tmp = buf;
    if (n <= 0) return;
    if (n > 64) tmp = (int32_t *)PyMem_Malloc(n * sizeof(int32_t));
    memcpy(tmp, src, n * sizeof(int32_t));
    for (int32_t i = 0; i < n; i++) maybe_wake(x, tmp[i]);
    if (tmp != buf) PyMem_Free(tmp);
}

static inline void wake_recv(Ctx *x, int32_t pi)
{ Pipe *p = &x->pipes[pi]; if (p->recv_n) wake_list(x, p->recv_w, p->recv_n); }
static inline void wake_send(Ctx *x, int32_t pi)
{ Pipe *p = &x->pipes[pi]; if (p->send_n) wake_list(x, p->send_w, p->send_n); }

static void put0(Ctx *x, int32_t pi, int64_t v)
{
    Pipe *p = &x->pipes[pi];
    p->head = (p->head + p->len - 1) % p->len;
    p->vals[p->head] = v;
    p->count++;
    if (p->nruns && p->runs[0] == 1) {
        p->runs[0] = 0;
    } else {
        memmove(p->runs + 2, p->runs, p->nruns * sizeof(int32_t));
        p->runs[0] = 0; p->runs[1] = 0;
        p->nruns += 2;
    }
    int32_t last = p->len - 1;
    if (p->nruns > 2 || p->runs[p->nruns - 1] != last) act_add(x, pi);
    else act_del(x, pi);
    if (p->runs[p->nruns - 1] == last) wake_recv(x, pi);
}

static int64_t take_last(Ctx *x, int32_t pi)
{
    Pipe *p = &x->pipes[pi];
    p->count--;
    int64_t v = p->vals[(p->head + p->count) % p->len];
    int32_t last = p->len - 1;
    if (p->runs[p->nruns - 2] == last) p->nruns -= 2;
    else p->runs[p->nruns - 1] = last - 1;
    if (p->nruns && (p->nruns > 2 || p->runs[p->nruns - 1] != last)) act_add(x, pi);
    else act_del(x, pi);
    if (!p->nruns || p->runs[0] != 0) wake_send(x, pi);
    return v;
}

static int32_t nearest_pick(Ctx *x, int32_t *idx, int32_t n, int32_t pos, int is_out)
{
    if (n <= 0) return -1;
    int32_t r = pos / x->W, c = pos % x->W;
    int32_t best = -1;
    int64_t bd = 0; int32_t br = 0, bc = 0;
    for (int32_t i = 0; i < n; i++) {
        int32_t pi = idx[i];
        int32_t sp = is_out ? x->pipes[pi].src_pos : x->pipes[pi].dst_pos;
        int32_t sr = sp / x->W, sc = sp % x->W;
        int64_t d = (int64_t)labs(sr - r) + labs(sc - c);
        if (best < 0 || d < bd || (d == bd && (sr < br || (sr == br && sc < bc)))) {
            best = pi; bd = d; br = sr; bc = sc;
        }
    }
    return best;
}

/* --------------------------------------------------------------- the loop */
#define FAIL(msg) do { PyErr_SetString(PyExc_RuntimeError, msg); goto fail; } while (0)

static PyObject *fs_run(PyObject *self, PyObject *args)
{
    PyObject *spec, *controller, *ctrl_queue, *input_queue;
    long long max_ticks;
    Ctx x; memset(&x, 0, sizeof(x));
    PyObject *result = NULL;
    PyObject *out_values = NULL, *out_ticks = NULL, *frames = NULL, *frame_ticks = NULL;
    PyObject *m_pop = NULL, *m_out = NULL, *m_frame = NULL;
    Py_ssize_t n;
    const char *error = NULL;
    int crashed = 0;   /* a wall step is pending its one grace tick */
    const char *status = "tick-cap";
    PyObject *verdict = NULL;
    int64_t ticks = 0;

    if (!PyArg_ParseTuple(args, "OOOOL", &spec, &controller, &ctrl_queue,
                          &input_queue, &max_ticks))
        return NULL;

    x.W = (int32_t)PyLong_AsLong(get(spec, "W"));
    x.H = (int32_t)PyLong_AsLong(get(spec, "H"));
    if (PyErr_Occurred()) return NULL;
    x.size = x.W * x.H;
    x.n_cells = (int32_t)PyLong_AsLong(get(spec, "n_cells"));
    if (PyErr_Occurred()) return NULL;

    PyObject *code = get(spec, "code"), *lit = get(spec, "lit");
    if (!code || !lit) return NULL;
    for (int d = 0; d < 4; d++) {
        x.code[d] = list_i32(PyList_GET_ITEM(code, d), NULL);
        x.lit[d] = list_i64(PyList_GET_ITEM(lit, d), NULL);
        if (!x.code[d] || !x.lit[d]) goto fail;
    }
    {
        PyObject *stp = get(spec, "step");
        if (!stp) return NULL;
        for (int d = 0; d < 4; d++) {
            x.step[d] = list_i32(PyList_GET_ITEM(stp, d), NULL);
            if (!x.step[d]) goto fail;
        }
    }
    x.cellpos = list_i32(get(spec, "cellpos"), NULL);
    x.mcell = list_i32(get(spec, "mcell"), &n);
    x.n_men = (int32_t)n;
    x.mdir = list_i32(get(spec, "mdir"), NULL);
    x.mroom = list_i32(get(spec, "mroom"), NULL);
    x.mhalt = list_i32(get(spec, "mhalt"), NULL);
    x.mA = list_i64(get(spec, "mA"), NULL);
    x.mB = list_i64(get(spec, "mB"), NULL);
    x.mBP = list_i64(get(spec, "mBP"), NULL);
    x.room_out_off = list_i32(get(spec, "room_out_off"), NULL);
    x.room_out_idx = list_i32(get(spec, "room_out_idx"), NULL);
    x.room_in_off = list_i32(get(spec, "room_in_off"), NULL);
    x.room_in_idx = list_i32(get(spec, "room_in_idx"), NULL);
    x.room_ins_off = list_i32(get(spec, "room_ins_off"), NULL);
    x.room_ins_idx = list_i32(get(spec, "room_ins_idx"), NULL);
    x.disp_pipes = list_i32(get(spec, "disp_pipes"), &n);
    x.n_disp_pipes = (int32_t)n;
    if (PyErr_Occurred()) goto fail;

    int32_t nm = x.n_men ? x.n_men : 1;
    x.wkind = (int32_t *)PyMem_Calloc(nm, sizeof(int32_t));
    x.wlen = (int32_t *)PyMem_Calloc(nm, sizeof(int32_t));
    x.wptr = (int32_t **)PyMem_Calloc(nm, sizeof(int32_t *));
    x.wsingle = (int32_t *)PyMem_Calloc(nm, sizeof(int32_t));
    x.runflag = (int32_t *)PyMem_Calloc(nm, sizeof(int32_t));
    x.runbuf = (int32_t *)PyMem_Calloc(nm, sizeof(int32_t));
    x.heap = (int32_t *)PyMem_Calloc(nm + 1, sizeof(int32_t));
    x.stamp = (int64_t *)PyMem_Calloc(nm, sizeof(int64_t));
    x.occ = (int32_t *)PyMem_Malloc((x.size ? x.size : 1) * sizeof(int32_t));
    x.near_out = (int32_t *)PyMem_Malloc((x.n_cells ? x.n_cells : 1) * sizeof(int32_t));
    x.near_in = (int32_t *)PyMem_Malloc((x.n_cells ? x.n_cells : 1) * sizeof(int32_t));
    if (!x.occ || !x.near_out || !x.near_in || !x.stamp) FAIL("oom");
    for (int32_t i = 0; i < x.size; i++) x.occ[i] = -1;
    for (int32_t i = 0; i < x.n_cells; i++) { x.near_out[i] = -2; x.near_in[i] = -2; }
    for (int32_t i = 0; i < x.n_men; i++) {
        x.stamp[i] = -1;
        x.occ[x.cellpos[x.mcell[i]]] = i;
        if (!x.mhalt[i]) runnable_add(&x, i);
    }

    PyObject *p_len = get(spec, "p_len"), *p_runs = get(spec, "p_runs");
    PyObject *p_vals = get(spec, "p_vals"), *p_turn = get(spec, "p_turn");
    PyObject *p_src = get(spec, "p_src_pos"), *p_dst = get(spec, "p_dst_pos");
    if (!p_len || !p_runs || !p_vals || !p_turn || !p_src || !p_dst) goto fail;
    x.n_pipes = (int32_t)PyList_Size(p_len);
    x.pipes = (Pipe *)PyMem_Calloc(x.n_pipes ? x.n_pipes : 1, sizeof(Pipe));
    x.act_buf = (int32_t *)PyMem_Calloc(x.n_pipes ? x.n_pipes : 1, sizeof(int32_t));
    x.act_pos = (int32_t *)PyMem_Calloc(x.n_pipes ? x.n_pipes : 1, sizeof(int32_t));
    if (!x.pipes || !x.act_buf || !x.act_pos) FAIL("oom");
    for (int32_t i = 0; i < x.n_pipes; i++) {
        Pipe *p = &x.pipes[i];
        p->len = (int32_t)PyLong_AsLong(PyList_GET_ITEM(p_len, i));
        p->turn = (int32_t)PyLong_AsLong(PyList_GET_ITEM(p_turn, i));
        p->src_pos = (int32_t)PyLong_AsLong(PyList_GET_ITEM(p_src, i));
        p->dst_pos = (int32_t)PyLong_AsLong(PyList_GET_ITEM(p_dst, i));
        p->runs_cap = p->len + 4;
        p->runs = (int32_t *)PyMem_Calloc(p->runs_cap, sizeof(int32_t));
        p->vals = (int64_t *)PyMem_Calloc(p->len ? p->len : 1, sizeof(int64_t));
        if (!p->runs || !p->vals) FAIL("oom");
        PyObject *rl = PyList_GET_ITEM(p_runs, i), *vl = PyList_GET_ITEM(p_vals, i);
        p->nruns = (int32_t)PyList_Size(rl);
        for (int32_t j = 0; j < p->nruns; j++)
            p->runs[j] = (int32_t)PyLong_AsLong(PyList_GET_ITEM(rl, j));
        p->count = (int32_t)PyList_Size(vl);
        for (int32_t j = 0; j < p->count; j++)
            p->vals[j] = (int64_t)PyLong_AsLongLong(PyList_GET_ITEM(vl, j));
        p->head = 0;
        x.act_pos[i] = -1;
        if (p->nruns && (p->nruns > 2 || p->runs[p->nruns - 1] != p->len - 1))
            act_add(&x, i);
    }
    if (PyErr_Occurred()) goto fail;

    PyObject *dlist = get(spec, "disp"), *dcur = get(spec, "disp_cur"),
             *dnext = get(spec, "disp_next");
    if (!dlist || !dcur || !dnext) goto fail;
    x.n_disps = (int32_t)PyList_Size(dlist);
    x.disps = (Disp *)PyMem_Calloc(x.n_disps ? x.n_disps : 1, sizeof(Disp));
    if (!x.disps) FAIL("oom");
    for (int32_t i = 0; i < x.n_disps; i++) {
        PyObject *t = PyList_GET_ITEM(dlist, i);
        Disp *dd = &x.disps[i];
        dd->addr = (int32_t)PyLong_AsLong(PyList_GET_ITEM(t, 0));
        dd->data = (int32_t)PyLong_AsLong(PyList_GET_ITEM(t, 1));
        dd->swap = (int32_t)PyLong_AsLong(PyList_GET_ITEM(t, 2));
        dd->w = (int32_t)PyLong_AsLong(PyList_GET_ITEM(t, 3));
        dd->h = (int32_t)PyLong_AsLong(PyList_GET_ITEM(t, 4));
        dd->cursor = (int32_t)PyLong_AsLong(PyList_GET_ITEM(t, 5));
        int32_t sz = dd->w * dd->h;
        dd->cur = (int8_t *)PyMem_Calloc(sz ? sz : 1, 1);
        dd->nxt = (int8_t *)PyMem_Calloc(sz ? sz : 1, 1);
        if (!dd->cur || !dd->nxt) FAIL("oom");
        PyObject *cl = PyList_GET_ITEM(dcur, i), *nl = PyList_GET_ITEM(dnext, i);
        for (int32_t j = 0; j < sz; j++) {
            dd->cur[j] = (int8_t)PyLong_AsLong(PyList_GET_ITEM(cl, j));
            dd->nxt[j] = (int8_t)PyLong_AsLong(PyList_GET_ITEM(nl, j));
        }
    }
    x.input_pipe = (int32_t)PyLong_AsLong(get(spec, "input_pipe"));
    x.output_pipe = (int32_t)PyLong_AsLong(get(spec, "output_pipe"));
    if (PyErr_Occurred()) goto fail;

    out_values = PyList_New(0); out_ticks = PyList_New(0);
    frames = PyList_New(0); frame_ticks = PyList_New(0);
    if (!out_values || !out_ticks || !frames || !frame_ticks) goto fail;
    if (controller != Py_None) {
        m_pop = PyObject_GetAttrString(controller, "pop_input");
        m_out = PyObject_GetAttrString(controller, "on_output");
        if (!m_pop || !m_out) goto fail;
        m_frame = PyObject_GetAttrString(controller, "on_frame");
        if (!m_frame) PyErr_Clear();
    }

    {
    int32_t *snap = (int32_t *)PyMem_Malloc((x.n_pipes ? x.n_pipes : 1) * sizeof(int32_t));
    int32_t *movers = (int32_t *)PyMem_Malloc(nm * sizeof(int32_t));
    if (!snap || !movers) { PyMem_Free(snap); PyMem_Free(movers); FAIL("oom"); }

    for (int64_t t = 0; t < max_ticks; t++) {
        ticks++;
        x.tick = ticks;
        /* ---------------------------------------------------- 1. pipe shift */
        int32_t nact = x.act_n;
        memcpy(snap, x.act_buf, nact * sizeof(int32_t));
        for (int32_t si = 0; si < nact; si++) {
            int32_t pi = snap[si];
            Pipe *p = &x.pipes[pi];
            int32_t last = p->len - 1, nr = p->nruns;
            int32_t *runs = p->runs;
            int src_was_full = (runs[0] == 0);
            int dst_was_empty = (runs[nr - 1] != last);
            int blocked = (runs[nr - 1] == last);
            int32_t moving = blocked ? nr - 2 : nr;
            for (int32_t i = 0; i < moving; i += 2) { runs[i]++; runs[i + 1]++; }
            if (blocked && moving && runs[moving - 1] + 1 == runs[moving]) {
                runs[moving - 1] = runs[moving + 1];
                memmove(runs + moving, runs + moving + 2,
                        (nr - moving - 2) * sizeof(int32_t));
                p->nruns = nr - 2;
            }
            if (!(p->nruns > 2 || runs[p->nruns - 1] != last)) act_del(&x, pi);
            if (src_was_full && runs[0] != 0) wake_send(&x, pi);
            if (dst_was_empty && runs[p->nruns - 1] == last) wake_recv(&x, pi);
        }
        /* ----------------------------------------------------------- 2. I/O */
        Py_CLEAR(verdict);
        if (x.output_pipe >= 0) {
            Pipe *p = &x.pipes[x.output_pipe];
            if (p->nruns && p->runs[p->nruns - 1] == p->len - 1) {
                int64_t v = take_last(&x, x.output_pipe);
                PyObject *o = PyLong_FromLongLong(v);
                PyObject *o2 = PyLong_FromLongLong(ticks);
                if (!o || !o2) { Py_XDECREF(o); Py_XDECREF(o2); goto loop_fail; }
                PyList_Append(out_values, o); PyList_Append(out_ticks, o2);
                Py_DECREF(o); Py_DECREF(o2);
                if (m_out) {
                    PyObject *r = PyObject_CallFunction(m_out, "LL",
                                    (long long)v, (long long)ticks);
                    if (!r) goto loop_fail;
                    if (PyObject_IsTrue(r)) { verdict = r; break; }
                    Py_DECREF(r);
                }
            }
        }
        if (x.input_pipe >= 0) {
            Pipe *p = &x.pipes[x.input_pipe];
            if (!(p->nruns && p->runs[0] == 0)) {
                if (m_pop) {
                    if (!(ctrl_queue != Py_None && PyList_GET_SIZE(ctrl_queue) == 0)) {
                        PyObject *v = PyObject_CallNoArgs(m_pop);
                        if (!v) goto loop_fail;
                        if (v != Py_None) {
                            int64_t iv = (int64_t)PyLong_AsLongLong(v);
                            if (iv == -1 && PyErr_Occurred()) { Py_DECREF(v); goto loop_fail; }
                            put0(&x, x.input_pipe, iv);
                        }
                        Py_DECREF(v);
                    }
                } else if (PyList_Check(input_queue) && PyList_GET_SIZE(input_queue) > 0) {
                    int64_t iv = (int64_t)PyLong_AsLongLong(PyList_GET_ITEM(input_queue, 0));
                    if (iv == -1 && PyErr_Occurred()) goto loop_fail;
                    if (PySequence_DelItem(input_queue, 0) < 0) goto loop_fail;
                    put0(&x, x.input_pipe, iv);
                }
            }
        }
        /* ------------------------------------------------------- 3. execute */
        /* A crash from the previous tick stops everything before any
           man executes; there is no drain-to-empty. */
        if (crashed) { error = "wall"; goto exec_err; }
        x.heap_n = 0;
        for (int32_t i = 0; i < x.runbuf_n; i++) {
            int32_t mi = x.runbuf[i];
            if (x.runflag[mi]) { x.runflag[mi] = 0; heap_push(&x, mi); }
        }
        x.runbuf_n = 0; x.n_runnable = 0;
        x.in_execute = 1;
        int32_t movers_n = 0;
        while (x.heap_n) {
            int32_t i = heap_pop(&x);
            if (x.stamp[i] == ticks) continue;
            x.stamp[i] = ticks;
            x.cur_index = i;
            if (x.mhalt[i]) continue;
            int32_t cell = x.mcell[i];
            int32_t d = x.mdir[i];
            int32_t op = x.code[d][cell];
            int32_t ri = x.mroom[i];
            switch (op) {
            case 0: break;
            case 1: case 2: case 3: case 4: x.mdir[i] = op - 1; break;
            case OP_LIT: x.mA[i] = x.lit[d][cell]; break;
            case 21: if (x.mA[i] > 0) x.mdir[i] = (d + 1) & 3;
                     else if (x.mA[i] < 0) x.mdir[i] = (d + 3) & 3; break;
            case 8: x.mB[i] = x.mA[i]; break;
            case 9: { int64_t tmp = x.mA[i]; x.mA[i] = x.mB[i]; x.mB[i] = tmp; break; }
            case 10: x.mA[i] = wrap_add(x.mA[i], x.mB[i]); break;
            case 11: x.mA[i] = wrap_sub(x.mA[i], x.mB[i]); break;
            case 12: x.mA[i] = wrap_mul(x.mA[i], x.mB[i]); break;
            case 13: x.mA[i] = (int64_t)(0 - (uint64_t)x.mA[i]); break;
            case 14: if (x.mB[i] == 0) x.mA[i] = 0;
                     else { int64_t q, r; floordivmod(x.mA[i], x.mB[i], &q, &r); x.mA[i] = r; }
                     break;
            case 15: if (x.mB[i] == 0) { x.mB[i] = x.mA[i]; x.mA[i] = 0; }
                     else { int64_t q, r; floordivmod(x.mA[i], x.mB[i], &q, &r);
                            x.mA[i] = q; x.mB[i] = r; }
                     break;
            case 16: x.mA[i] = x.mA[i] & x.mB[i]; break;
            case 17: x.mA[i] = x.mA[i] | x.mB[i]; break;
            case 18: x.mA[i] = x.mA[i] ^ x.mB[i]; break;
            case 19: { int64_t b = x.mB[i];
                       x.mA[i] = (b >= 0 && b <= 63)
                           ? (int64_t)((uint64_t)x.mA[i] << b) : 0; break; }
            case 20: { int64_t b = x.mB[i];
                       if (b < 0) x.mA[i] = 0;
                       else x.mA[i] = x.mA[i] >> (b < 63 ? b : 63); break; }
            case 7: x.mhalt[i] = 1; continue;
            case 22: {   /* s */
                int32_t pi = x.near_out[cell];
                if (pi == -2) {
                    int32_t o = x.room_out_off[ri];
                    pi = nearest_pick(&x, x.room_out_idx + o,
                                      x.room_out_off[ri + 1] - o,
                                      x.cellpos[cell], 1);
                    x.near_out[cell] = pi;
                }
                if (pi < 0) { error = "no-pipe"; goto exec_err; }
                Pipe *p = &x.pipes[pi];
                if (p->nruns && p->runs[0] == 0) {
                    x.wkind[i] = 3; x.wsingle[i] = pi;
                    x.wptr[i] = &x.wsingle[i]; x.wlen[i] = 1; x.n_send_wait++;
                    wlist_add(&p->send_w, &p->send_n, &p->send_cap, i);
                    continue;
                }
                put0(&x, pi, x.mA[i]);
                break; }
            case 24: {   /* r */
                int32_t pi = x.near_in[cell];
                if (pi == -2) {
                    int32_t o = x.room_in_off[ri];
                    pi = nearest_pick(&x, x.room_in_idx + o,
                                      x.room_in_off[ri + 1] - o,
                                      x.cellpos[cell], 0);
                    x.near_in[cell] = pi;
                }
                if (pi < 0) { error = "no-pipe"; goto exec_err; }
                Pipe *p = &x.pipes[pi];
                if (p->nruns && p->runs[p->nruns - 1] == p->len - 1) {
                    x.mA[i] = take_last(&x, pi);
                } else {
                    x.wkind[i] = 1; x.wsingle[i] = pi;
                    x.wptr[i] = &x.wsingle[i]; x.wlen[i] = 1; x.n_recv_wait++;
                    wlist_add(&p->recv_w, &p->recv_n, &p->recv_cap, i);
                    continue;
                }
                break; }
            case 23: {   /* S */
                int32_t o = x.room_out_off[ri], e = x.room_out_off[ri + 1];
                if (o == e) { error = "no-pipe"; goto exec_err; }
                int busy = 0;
                for (int32_t j = o; j < e; j++) {
                    Pipe *p = &x.pipes[x.room_out_idx[j]];
                    if (p->nruns && p->runs[0] == 0) { busy = 1; break; }
                }
                if (busy) {
                    x.wkind[i] = 4; x.wptr[i] = x.room_out_idx + o;
                    x.wlen[i] = e - o; x.n_send_wait++;
                    for (int32_t j = o; j < e; j++) {
                        Pipe *p = &x.pipes[x.room_out_idx[j]];
                        wlist_add(&p->send_w, &p->send_n, &p->send_cap, i);
                    }
                    continue;
                }
                { int64_t a = x.mA[i];
                  for (int32_t j = o; j < e; j++) put0(&x, x.room_out_idx[j], a); }
                break; }
            case 25: case 26: {   /* R / U */
                int32_t o = x.room_in_off[ri], e = x.room_in_off[ri + 1];
                if (o == e) { error = "no-pipe"; goto exec_err; }
                int32_t chosen = -1;
                int32_t so = x.room_ins_off[ri], se = x.room_ins_off[ri + 1];
                for (int32_t j = so; j < se; j++) {
                    int32_t pi = x.room_ins_idx[j];
                    Pipe *p = &x.pipes[pi];
                    if (p->nruns && p->runs[p->nruns - 1] == p->len - 1) {
                        chosen = pi; break;
                    }
                }
                if (chosen < 0) {
                    x.wkind[i] = 2; x.wptr[i] = x.room_in_idx + o;
                    x.wlen[i] = e - o; x.n_recv_wait++;
                    for (int32_t j = o; j < e; j++) {
                        Pipe *p = &x.pipes[x.room_in_idx[j]];
                        wlist_add(&p->recv_w, &p->recv_n, &p->recv_cap, i);
                    }
                    continue;
                }
                x.mA[i] = take_last(&x, chosen);
                if (op == 26) x.mdir[i] = x.pipes[chosen].turn;
                break; }
            case 27: {   /* q */
                int32_t pi = x.near_in[cell];
                if (pi == -2) {
                    int32_t o = x.room_in_off[ri];
                    pi = nearest_pick(&x, x.room_in_idx + o,
                                      x.room_in_off[ri + 1] - o,
                                      x.cellpos[cell], 0);
                    x.near_in[cell] = pi;
                }
                if (pi < 0) { error = "no-pipe"; goto exec_err; }
                x.mBP[i] = x.pipes[pi].count;
                break; }
            case 28: x.mBP[i] = x.mA[i]; break;
            case 29: x.mBP[i] = wrap_sub(x.mBP[i], 1); break;
            case 30: if (x.mBP[i] > 0) x.mdir[i] = (d + 1) & 3; break;
            case 31: if (x.mBP[i] > 0) x.mdir[i] = (d + 3) & 3; break;
            case 32: x.mBP[i] = x.mBP[i] >> 1; break;
            case 33: x.mdir[i] = (x.mBP[i] & 1) ? ((d + 1) & 3) : ((d + 3) & 3); break;
            default: error = "bad-op"; goto exec_err;
            }
            movers[movers_n++] = i;
            runnable_add(&x, i);
        }
        x.in_execute = 0; x.cur_index = -1;
        /* ------------------------------------------------------- 3b. display */
        for (int32_t di = 0; di < x.n_disps; di++) {
            Disp *dd = &x.disps[di];
            int32_t sides[3]; sides[0] = dd->addr; sides[1] = dd->data; sides[2] = dd->swap;
            int32_t sz = dd->w * dd->h;
            for (int32_t sd = 0; sd < 3; sd++) {
                int32_t pi = sides[sd];
                if (pi < 0) continue;
                Pipe *p = &x.pipes[pi];
                if (!(p->nruns && p->runs[p->nruns - 1] == p->len - 1)) continue;
                int64_t v = take_last(&x, pi);
                if (sd == 0) {
                    if (v < 0 || v >= sz) { error = "display"; goto exec_err; }
                    dd->cursor = (int32_t)v;
                } else if (sd == 1) {
                    if (v < 0 || v > 15) { error = "display"; goto exec_err; }
                    dd->nxt[dd->cursor] = (int8_t)v;
                    dd->cursor = (dd->cursor + 1) % sz;
                } else {
                    if (v != 0 && v != 1) { error = "display"; goto exec_err; }
                    memcpy(dd->cur, dd->nxt, sz);
                    PyObject *fr = PyList_New(dd->h);
                    if (!fr) goto loop_fail;
                    for (int32_t rr = 0; rr < dd->h; rr++) {
                        PyObject *row = PyList_New(dd->w);
                        if (!row) { Py_DECREF(fr); goto loop_fail; }
                        for (int32_t cc = 0; cc < dd->w; cc++)
                            PyList_SET_ITEM(row, cc,
                                PyLong_FromLong(dd->cur[rr * dd->w + cc]));
                        PyList_SET_ITEM(fr, rr, row);
                    }
                    PyList_Append(frames, fr);
                    PyObject *ft = PyLong_FromLongLong(ticks);
                    PyList_Append(frame_ticks, ft); Py_DECREF(ft);
                    if (m_frame) {
                        PyObject *r = PyObject_CallFunction(m_frame, "OL", fr,
                                                           (long long)ticks);
                        if (!r) { Py_DECREF(fr); goto loop_fail; }
                        if (PyObject_IsTrue(r)) { Py_XSETREF(verdict, r); }
                        else Py_DECREF(r);
                    }
                    Py_DECREF(fr);
                    if (v == 0) { memset(dd->nxt, 0, sz); dd->cursor = 0; }
                }
            }
        }
        /* ------------------------------------------------------ 4. movement */
        for (int32_t k = 0; k < movers_n; k++) {
            int32_t i = movers[k];
            if (x.mhalt[i]) continue;
            int32_t cell = x.mcell[i];
            int32_t ncell = x.step[x.mdir[i]][cell];
            if (ncell < 0) {
                /* ONE GRACE TICK, mirroring sim.py and fastsim.py. The
                   official engine lets the man enter the wall cell and
                   fires the fatal at the start of the NEXT execute
                   phase, so that tick's pipe shift and output emit
                   still happen. */
                crashed = 1;
                x.mhalt[i] = 1;
                runnable_discard(&x, i);
                continue;
            }
            int32_t np = x.cellpos[ncell];
            int32_t occupant = x.occ[np];
            if (occupant >= 0) {
                x.mhalt[i] = 1; x.mhalt[occupant] = 1;
                runnable_discard(&x, i); runnable_discard(&x, occupant);
                clear_wait(&x, occupant);
                continue;
            }
            x.occ[x.cellpos[cell]] = -1;
            x.mcell[i] = ncell;
            x.occ[np] = i;
        }
        if (verdict) break;
        if (!x.n_runnable && !x.n_recv_wait && !x.n_send_wait) {
            if (x.output_pipe >= 0 && x.pipes[x.output_pipe].count) continue;
            int drained = 0;
            for (int32_t j = 0; j < x.n_disp_pipes; j++)
                if (x.pipes[x.disp_pipes[j]].count) { drained = 1; break; }
            if (drained) continue;
            if (crashed) {
                /* marked halted so it stops moving, but the program did
                   NOT end cleanly; a wall fatal does not drain. */
                error = "wall"; goto exec_err;
            }
            status = "halted";
            break;
        }
    }
    goto finished;
loop_fail:
    PyMem_Free(snap); PyMem_Free(movers);
    goto fail;
exec_err:
    x.in_execute = 0;
finished:
    PyMem_Free(snap); PyMem_Free(movers);
    }

    /* ---------------------------------------------------------- results */
    {
    PyObject *mpos = PyList_New(x.n_men), *mdir = PyList_New(x.n_men);
    /* returned as cell ids */
    PyObject *mA = PyList_New(x.n_men), *mB = PyList_New(x.n_men);
    PyObject *mBP = PyList_New(x.n_men), *mhalt = PyList_New(x.n_men);
    PyObject *mwait = PyList_New(x.n_men);
    if (!mpos || !mdir || !mA || !mB || !mBP || !mhalt || !mwait) goto fail;
    for (int32_t i = 0; i < x.n_men; i++) {
        PyList_SET_ITEM(mpos, i, PyLong_FromLong(x.mcell[i]));
        PyList_SET_ITEM(mdir, i, PyLong_FromLong(x.mdir[i]));
        PyList_SET_ITEM(mA, i, PyLong_FromLongLong(x.mA[i]));
        PyList_SET_ITEM(mB, i, PyLong_FromLongLong(x.mB[i]));
        PyList_SET_ITEM(mBP, i, PyLong_FromLongLong(x.mBP[i]));
        PyList_SET_ITEM(mhalt, i, PyLong_FromLong(x.mhalt[i]));
        PyList_SET_ITEM(mwait, i, PyLong_FromLong(x.wkind[i]));
    }
    PyObject *pruns = PyList_New(x.n_pipes), *pvals = PyList_New(x.n_pipes);
    for (int32_t i = 0; i < x.n_pipes; i++) {
        Pipe *p = &x.pipes[i];
        PyObject *rl = PyList_New(p->nruns);
        for (int32_t j = 0; j < p->nruns; j++)
            PyList_SET_ITEM(rl, j, PyLong_FromLong(p->runs[j]));
        PyObject *vl = PyList_New(p->count);
        for (int32_t j = 0; j < p->count; j++)
            PyList_SET_ITEM(vl, j, PyLong_FromLongLong(p->vals[(p->head + j) % p->len]));
        PyList_SET_ITEM(pruns, i, rl);
        PyList_SET_ITEM(pvals, i, vl);
    }
    PyObject *dcur2 = PyList_New(x.n_disps), *dnext2 = PyList_New(x.n_disps),
             *dcurs = PyList_New(x.n_disps);
    for (int32_t i = 0; i < x.n_disps; i++) {
        Disp *dd = &x.disps[i];
        int32_t sz = dd->w * dd->h;
        PyObject *a = PyList_New(sz), *b = PyList_New(sz);
        for (int32_t j = 0; j < sz; j++) {
            PyList_SET_ITEM(a, j, PyLong_FromLong(dd->cur[j]));
            PyList_SET_ITEM(b, j, PyLong_FromLong(dd->nxt[j]));
        }
        PyList_SET_ITEM(dcur2, i, a);
        PyList_SET_ITEM(dnext2, i, b);
        PyList_SET_ITEM(dcurs, i, PyLong_FromLong(dd->cursor));
    }
    PyObject *verd = verdict ? verdict : Py_None;
    result = Py_BuildValue("(szOLNNNNNNNNNNNNNNNN)",
        status, error, verd, (long long)ticks,
        out_values, out_ticks, frames, frame_ticks,
        mpos, mdir, mA, mB, mBP, mhalt, mwait, pruns, pvals,
        dcur2, dnext2, dcurs);
    out_values = out_ticks = frames = frame_ticks = NULL;
    }
fail:
    Py_XDECREF(verdict);
    Py_XDECREF(m_pop); Py_XDECREF(m_out); Py_XDECREF(m_frame);
    Py_XDECREF(out_values); Py_XDECREF(out_ticks);
    Py_XDECREF(frames); Py_XDECREF(frame_ticks);
    for (int d = 0; d < 4; d++) { PyMem_Free(x.code[d]); PyMem_Free(x.lit[d]); }
    for (int d = 0; d < 4; d++) PyMem_Free(x.step[d]);
    PyMem_Free(x.cellpos); PyMem_Free(x.mcell); PyMem_Free(x.mdir);
    PyMem_Free(x.mroom); PyMem_Free(x.mhalt); PyMem_Free(x.mA);
    PyMem_Free(x.mB); PyMem_Free(x.mBP); PyMem_Free(x.wkind);
    PyMem_Free(x.wlen); PyMem_Free(x.wptr); PyMem_Free(x.wsingle);
    PyMem_Free(x.runflag); PyMem_Free(x.runbuf); PyMem_Free(x.heap);
    PyMem_Free(x.stamp); PyMem_Free(x.occ); PyMem_Free(x.near_out);
    PyMem_Free(x.near_in); PyMem_Free(x.room_out_off); PyMem_Free(x.room_out_idx);
    PyMem_Free(x.room_in_off); PyMem_Free(x.room_in_idx);
    PyMem_Free(x.room_ins_off); PyMem_Free(x.room_ins_idx);
    PyMem_Free(x.disp_pipes); PyMem_Free(x.act_buf); PyMem_Free(x.act_pos);
    if (x.pipes) {
        for (int32_t i = 0; i < x.n_pipes; i++) {
            PyMem_Free(x.pipes[i].runs); PyMem_Free(x.pipes[i].vals);
            PyMem_Free(x.pipes[i].recv_w); PyMem_Free(x.pipes[i].send_w);
        }
        PyMem_Free(x.pipes);
    }
    if (x.disps) {
        for (int32_t i = 0; i < x.n_disps; i++) {
            PyMem_Free(x.disps[i].cur); PyMem_Free(x.disps[i].nxt);
        }
        PyMem_Free(x.disps);
    }
    return result;
}

static PyMethodDef Methods[] = {
    {"run", fs_run, METH_VARARGS, "run a compiled littleman program"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT, "littleman._fastsim_ext", NULL, -1, Methods,
    NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC PyInit__fastsim_ext(void) { return PyModule_Create(&moduledef); }
