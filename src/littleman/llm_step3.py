"""Lockstep STEP room for full LLM semantics (work order claude_24).

ONE interpreter machine, round-robin over the interpreted men inside each
tick, exactly `littleman.llm_lockstep.LockstepLLM.from_stream`.  This module
is built model-first in the proven `lllm_step.StepModel` style:

* :class:`Step3Model` -- the machine-shaped choreography.  Every ring
  pull/push is literal; in-hand arithmetic is annotated with the opcode
  tape the room will run (A/B/BP legality checked by construction).
* the room builder (landed phase by phase) transcribes it 1:1.

Scratch ring, CANONICAL order (16 slots, head left):

    [C0 A0 I0 B0 | C1 A1 I1 B1 | C2 A2 I2 B2 | MARK SP OVER K]

* per man i (ring order = reading order; absent men lead, frozen, ADDR 0):
  C = CTRL = intent<<3 | frozen<<2 | heading (N0 E1 S2 W3), A = ADDR,
  I = interpreted A, B = interpreted B.
* MARK = -1 forever: every per-man loop pulls the head and exits on sign,
  so no pass needs a man counter.  SP = 0 forever: the collision compare
  reads slot +5/+9/+13 mod 16 (the *other* groups' slot-1) and one of the
  three is always this harmless never-equal dummy.
* OVER = global wall-freeze flag, K = the round's remaining ticks.

World storage is the UNMODIFIED claude_11a FETCH station: intake classifies
each 13-bit scan-v2 record (raw ASCII + wall bit) into the claude_09 record
`colour | class<<4 | value<<8 [| wall<<12]` and feeds FETCH the repacked
words, so op fetch answers `class<<4|value` and `-1` streams true colours.
New classes 9 (`s`) and 10 (`r`) extend claude_09; both colour 13.

Display protocol out is claude_10 deltas (`addr*16+colour`, negative =
commit), one FULL 257..259-pixel repaint per round -- cases outrank score,
and a full repaint deletes the OLD-slot machinery and the round-1/round-N
asymmetry in one move.
"""

from __future__ import annotations

from .llm_lockstep import machine_stream, wrap64
from .lllm_step import ScriptedFetch, frames_from_deltas

MARK = -1
DISPLAY = 16
STEP_DELTA = (-16, 1, 16, -1)          # heading 0..3 = N E S W on a 16-wide
WALL_REC = 4 | (1 << 4) | (1 << 12)    # colour 4, class 1, wall bit

# interior char -> claude_09 record (colour | class<<4 | value<<8)
CHAR_REC = {
    "^": 35, ">": 291, "v": 547, "<": 803,          # class 2, value 0..3
    "M": 76, "+": 90, "-": 106, "X": 115, "H": 131,  # classes 4..8
    "s": 157, "r": 173,                              # classes 9..10
}
for _d in range(10):
    CHAR_REC[str(_d)] = 56 + 256 * _d                # class 3, colour 8


def classify_record(rec: int) -> int:
    """One scan-v2 cell record -> claude_09 record (the intake chain).

    Wall bit first (any bordered cell is wall regardless of glyph), then a
    subtract/X compare chain over the ASCII code; everything unknown --
    space, padding, pipe glyphs outside rooms -- is class 0, colour 0,
    matching ``llm_lockstep._op_color`` on every character.
    """
    if rec & 256:
        return WALL_REC
    return CHAR_REC.get(chr(rec & 255), 0)


class Step3Model:
    """Machine-shaped model of the lockstep STEP room.

    ``self.ring`` is the scratch loop; only :meth:`_pull` / :meth:`_push`
    touch it.  ``A``/``B`` shadow the host registers so every method body
    doubles as the opcode tape (commented where non-obvious).
    """

    def __init__(self, fetch) -> None:
        self.fetch = fetch
        self.ring: list[int] = []
        self.ring2: list[int] = []      # [MARK2, seg0, seg1]; segment =
        self.deltas: list[int] = []     # [-(rawHDR), (addr, pres, val) x L]
        self.A = 0                      # with cell groups TAIL-FIRST
        self.B = 0
        self.msteps = 0

    def _pull2(self) -> int:
        self.A = self.ring2.pop(0)
        self.msteps += 1
        return self.A

    def _push2(self, value: int | None = None) -> None:
        if value is not None:
            self.A = value
        self.ring2.append(self.A)
        self.msteps += 1

    def _relay2(self, n: int) -> None:
        for _ in range(n):
            self._push2(self._pull2())

    # -- scratch-loop primitives ------------------------------------------
    def _pull(self) -> int:
        self.A = self.ring.pop(0)
        self.msteps += 1
        return self.A

    def _push(self, value: int | None = None) -> None:
        if value is not None:
            self.A = value
        self.ring.append(self.A)
        self.msteps += 1

    def _relay(self, n: int) -> None:
        for _ in range(n):
            self._push(self._pull())

    # -- intake: world -> classify -> FETCH -------------------------------
    def _intake_world(self, stream) -> None:
        """256 record laps; ring rides [w, phase, acc, count].

        Lap tape: ``r(w) M `8192` W /`` leaves A=w>>13, B=rec in ONE op;
        ``s`` parks the shifted word, ``W`` recovers rec, the classify
        chain maps it, and the phase staircase (BP = phase via ``b``)
        shifts/accumulates.  Flush arm (phase 3) sends acc to FETCH, pulls
        the next LOAD token, and decrements count -- count==0 ends intake.
        """
        feed = iter(stream[:64])
        self.ring = [next(feed), 0, 0, 64]          # r(LOAD) s `0` s s `64` s
        while True:
            w = self._pull()                        # r(w)
            w, rec = divmod(w, 8192)                # M `8192` W / -> A,B
            self._push(w)                           # s
            crec = classify_record(rec)             # W, then the chain
            phase = self._pull()                    # M(B=crec) r(phase) b
            self._push((phase + 1) & 3)             # arm literal, s
            acc = self._pull()                      # W M `13*phase` W { ...
            acc += crec << (13 * phase)             # ... M r(acc) +
            if phase < 3:
                self._push(acc)                     # s
                self._relay(1)                      # rs(count)
                continue
            self.fetch.send(acc)                    # s -> REQ (world feed)
            self._push(0)                           # `0` s
            count = self._pull() - 1                # r `1` M W - X
            if count == 0:
                for _ in range(3):                  # drop w/phase/acc
                    self._pull()
                return
            self._push(count)                       # s
            self._pull()                            # r(w == 0, drop)
            self._push(next(feed))                  # r(LOAD) s
            self._relay(3)                          # phase, acc, count

    def _man_group(self, addr: int) -> None:
        """Push one 4-slot man group; B-free (X-test on the addr itself)."""
        if addr:                                    # X: addr > 0
            self._push(1)                           # M `1` s   (CTRL: East)
            self._push(addr)                        # W s       (ADDR)
        else:                                       # X: addr == 0 (absent)
            self._push(4)                           # `4` s     (frozen)
            self._push(0)                           # `0` s
        self._push(0)                               # `0` s / s (AI)
        self._push(0)                               # s         (BI)

    def intake(self, stream) -> None:
        """The whole machine_stream: world, three men, pipe count."""
        self._intake_world(stream)
        x, y = stream[64], stream[65]               # r M(B=X) r s(Y) W s(X)
        self.ring = [y, x]                          # (ring was empty)
        self._man_group(stream[66])                 # r(LOAD) -> M0
        self._man_group(self._pull())               # r(Y)    -> M1
        self._man_group(self._pull())               # r(X)    -> M2
        n = sum(1 for a in stream[64:67] if a)      # path-encoded (4 paths)
        self._push(MARK)                            # `1` N s
        self._push(0)                               # `0` s   (SP)
        self._push(2 ** (3 - n))                    # `1|2|4|8` s  (SHIFTM)
        self._push(0)                               # s       (K)
        for p in range(stream[67]):                 # r(LOAD): count, b-loop
            self._intake_pipe(stream[68 + 8 * p : 76 + 8 * p])
        self._push2(MARK)                           # `1` N s2 (canon TAIL)
        self._check_canonical()

    def _intake_pipe(self, desc) -> None:
        """One 8-word descriptor -> one ring2 segment, cells REVERSED.

        The 7 cell words are reversed by insertion into RING1 (step t:
        push w, relay t, relay 16 -- men stay contiguous, statically), so
        the hi-first peel emits addrs tail-first; BP = 21-L skips the
        zero padding, which always leads.  HDR is stored as -raw (raw >= 2
        always: L>=1 and head addr 0 is geometrically impossible), so
        segment starts are the only negative ring2 slots after MARK2.
        """
        raw = desc[0]                               # r(LOAD)
        self._push2(-raw)                           # N s2
        length = raw & 31                           # N M `31` W & ...
        for t, word in enumerate(desc[1:8]):        # ... N M `21` W + b
            self._push(word)                        # r(LOAD) s
            self._relay(t)                          # rev-so-far
            self._relay(16)                         # the men, contiguous
        skip = 21 - length
        for _ in range(7):
            w = self._pull()                        # r (ring1 head)
            for div in (1 << 42, 1 << 21, 1):       # M `2^k` W / hi-first
                field, w = divmod(w, div)
                if skip:                            # d: BP > 0
                    skip -= 1                       # m
                    continue
                self._push2(field)                  # s2 (addr)
                self._push2(0)                      # `0` s2 (pres)
                self._push2(0)                      # s2 (val)

    def _check_canonical(self) -> None:
        assert len(self.ring) == 16
        assert self.ring[12] == MARK and self.ring[13] == 0
        assert not self.ring2 or self.ring2[-1] == MARK

    # -- pipes: the tick's phase 1 (tail-first gap fill, one lap) ----------
    def _pipe_shift(self) -> None:
        """Structural ring2 lap; cells are tail-first so the pulled order
        IS the model's descending-i order, and the pending-gap walk (addr
        pushed early, pres/val deferred, giver's addr held in B) does the
        cascade with two registers.  Only addr-or-sentinel slots are ever
        sign-tested; addrs are >= 0, so values never fake a boundary."""
        x = self._pull2()                           # first sentinel or MARK2
        while x != MARK:
            self._push2(x)                          # s2 (the -raw header)
            gap = False                             # no pending (deferred
            while True:                             # pres/val) cell yet
                x = self._pull2()                   # r2: addr or sentinel
                if x < 0:
                    if gap:
                        self._push2(0)              # pending resolves empty
                        self._push2(0)
                    break
                if not gap:
                    self._push2(x)                  # s2 (addr, A kept)
                    if self._pull2():               # r2(pres) X
                        self._push2(1)              # `1` s2
                        self._push2(self._pull2())  # r2(v) s2
                    else:
                        self._pull2()               # r2: junk v, dropped
                        gap = True                  # this cell now pending
                else:                               # x = giver addr (in B)
                    p = self._pull2()               # r2 X
                    v = self._pull2()               # r2
                    if p:                           # transfer up the pipe
                        self._push2(1)              # pending := (1, v)
                        self._push2(v)
                    else:
                        self._push2(0)              # pending stays empty
                        self._push2(0)
                    self._push2(x)                  # W s2: giver's addr;
                    gap = True                      # giver is now pending
        self._push2(x)                              # MARK2 home: canonical

    # -- FETCH round trip --------------------------------------------------
    def _op_fetch(self, addr: int) -> int:
        (resp,) = self.fetch.send(addr)             # s -> REQ, r <- RESP
        self.msteps += 2
        return resp

    # -- pass 1: round-robin execute (records move intents) ----------------
    def _pass1(self) -> None:
        """Loop: pull head; MARK exits, frozen relays, live dispatches."""
        while True:
            c = self._pull()                        # r
            if c == MARK:                           # X: A < 0
                self._push(c)                       # s
                self._relay(3)                      # SP, OVER, K
                return
            if c >= 4:                              # M `4` W - X: frozen
                self._push(c)                       # + s
                self._relay(3)
                continue
            self._push(c + 8)                       # + M `8` W + s: intent
            addr = self._pull()                     # r(ADDR)
            self._push(addr)                        # s
            resp = self._op_fetch(addr)             # (fetch band)
            cls, val = divmod(resp, 16)             # M `16` W / b(BP=cls)
            self._dispatch(cls, val)                # staircase + arms

    def _dispatch(self, cls: int, val: int) -> None:
        """Arms start head=AI (+2 into the group), end head=next CTRL."""
        if cls == 2:                                # heading: CTRL = 8+val
            self._relay(14)                         # W(B=val) rides in B
            self._pull()                            # r
            self._push(8 + val)                     # W M `8` + s
            self._relay(3)
        elif cls == 3:                              # digit: AI = val
            self._pull()                            # r (old AI)
            self._push(val)                         # W s
            self._relay(1)                          # rs(BI)
        elif cls == 4:                              # M: BI = AI
            ai = self._pull()                       # r s M(B=ai)
            self._push(ai)
            self._pull()                            # r (old BI)
            self._push(ai)                          # W s
        elif cls in (5, 6):                         # add / sub
            ai = self._pull()                       # r M(B=ai)
            bi = self._pull()                       # r
            s = ai + bi if cls == 5 else ai - bi    # +  |  W -
            self._push(wrap64(s))                   # s
            self._push(bi)                          # -  |  W    then s
        elif cls == 7:                              # X: turn by sign(AI)
            ai = self._pull()                       # r s X   (head -> BI)
            self._push(ai)
            if ai:
                self._relay(13)                     # BI .. SP -> own CTRL
                c = self._pull()                    # r: A = 8+h
                turn = 1 if ai > 0 else 3
                self._push(8 + (c - 8 + turn) % 4)  # `8`MW- `t`MW+ M`4`W% ..
                self._relay(3)
            else:
                self._relay(1)                      # rs(BI)
        elif cls == 8:                              # H: freeze, no intent
            self._relay(14)                         # to CTRL
            c = self._pull()                        # r: A = 8+h
            self._push(c - 4)                       # `4` M W - s -> 4+h
            self._relay(3)
        elif cls in (9, 10):                        # s / r: the pipe arms
            self._pipe_arm(outgoing=cls == 9)
        else:                                       # class 0: nop + move
            self._relay(2)

    # -- the s/r arms ------------------------------------------------------
    def _lap_read(self, offset: int) -> int:
        """Full ring1 lap bringing slot ``offset`` through the hand."""
        self._relay(offset)
        value = self._pull()
        self._push(value)
        self._relay(15 - offset)
        return value

    def _lap_write(self, offset: int, value: int) -> None:
        self._relay(offset)
        self._pull()
        self._push(value)
        self._relay(15 - offset)

    def _seg_headers(self) -> list[int]:
        """One structural ring2 lap; returns each segment's raw HDR.

        Machine shape: pull HDR' (push back), N, L-extract, BP=3L relay,
        next sentinel...; raw values ride through MARK/SP parking slots.
        """
        raws = []
        x = self._pull2()
        while x != MARK:
            self._push2(x)                          # s2
            raws.append(-x)                         # N (+ parking dance)
            self._relay2(3 * (-x & 31))             # BP = 3L cell slots
            x = self._pull2()
        self._push2(x)                              # MARK2: canonical
        return raws

    def _pipe_arm(self, outgoing: bool) -> None:
        """head = AI of the executing man; ends at the next man's CTRL.

        Machine: BP count-to-MARK names the man (3 static sub-arms); the
        nearest-pipe pick parks intermediates in the MARK/SP slots and
        re-reads SHIFTM for the mask bit 2^(21|24 + mi)/SHIFTM.
        """
        mi = (10 - self.ring.index(MARK)) // 4      # `3`b + m per group hop
        self._relay(2 + 4 * (2 - mi) + 1)           # AI,BI + hops + rs(MARK)
        self._relay(3)                              # SP, SHIFTM, K: head 0
        shiftm = self.ring[14]                      # r(SHIFTM) en route
        man_addr = self._lap_read(4 * mi + 1)
        raws = self._seg_headers()
        best, key = -1, None
        bit = 2 ** ((21 if outgoing else 24) + mi) // shiftm
        for pi, raw in enumerate(raws):             # <=2: straight-line
            if not raw & bit:                       # W & X (raw stays in B)
                continue
            cell = raw >> (5 if outgoing else 13) & 255
            d = abs(cell // 16 - man_addr // 16) + abs(
                cell % 16 - man_addr % 16
            )
            if key is None or (d, cell) < key:
                best, key = pi, (d, cell)
        blocked = best < 0 or not self._seg_act(best, outgoing, mi)
        if blocked:
            self._lap_write(4 * mi, self._lap_read(4 * mi) - 8)
        self._relay(4 * (mi + 1))                   # -> next man's CTRL

    def _seg_act(self, ci: int, outgoing: bool, mi: int) -> bool:
        """Rotate ring2 to segment ``ci``, act on head/tail cell, rotate
        home structurally.  Returns False when blocked (full/empty)."""
        for _ in range(ci):                         # skip earlier segments
            x = self._pull2()
            self._push2(x)
            self._relay2(3 * (-x & 31))
        length = -self._pull2() & 31                # r2(HDR') s2 N `31`&b
        self._push2()
        if outgoing:                                # head cell = LAST group
            self._relay2(3 * (length - 1))
            a, p, v = self._pull2(), self._pull2(), self._pull2()
            ok = p == 0
            self._push2(a)
            self._push2(1 if ok else p)
            self._push2(self._lap_read(4 * mi + 2) if ok else v)
        else:                                       # tail cell = FIRST group
            a, p, v = self._pull2(), self._pull2(), self._pull2()
            ok = p == 1
            self._push2(a)
            self._push2(0 if ok else p)
            self._push2(0 if ok else v)
            if ok:
                self._lap_write(4 * mi + 2, v)      # AI := taken value
            self._relay2(3 * (length - 1))
        while True:                                 # structural walk home
            x = self._pull2()
            self._push2(x)
            if x == MARK:
                return ok
            self._relay2(3 * (-x & 31))
    def _pass2(self) -> None:
        while True:
            v = self._pull()                        # r
            if v == MARK:                           # X
                self._push(v)
                self._relay(3)
                return
            if v < 8 or v >= 16:                    # no intent, or walled
                self._push(v)                       # `8`MW-X ... s
                self._relay(3)
                continue
            if v >= 12:                             # collision-halted here
                self._push(v - 8)                   # `4`MW- `4`MW+ s: 4+h
                self._relay(3)
                continue
            h = v - 8                               # mover: A = heading
            self._push(h)                           # s (provisional live CTRL)
            addr = self._pull()                     # M`1`W+b then r(ADDR)
            self._push(addr)                        # s (peek)
            target = addr + STEP_DELTA[h]           # staircase arm h -> A=T
            self.B = target                         # M (B=T survives relays)
            for k in (1, 2, 3):
                self._relay(3)
                other = self._pull()                # r: A = other ADDR
                if other == target:                 # - X: A == 0 collision
                    self._push(other)               # + s
                    self._relay(14)                 # -> C_j
                    cj = self._pull()               # r
                    self._push(cj | 4)              # M `4` W | s
                    self._relay(15 - 4 * k)         # -> own CTRL
                    self._pull()                    # r: provisional h
                    self._push(h + 4)               # `4` M W + s: frozen
                    self._relay(3)
                    break
                self._push(other)                   # + s (restore)
            else:
                self._relay(3)                      # OVER/K/own C (mod 16)
                self._pull()                        # r: old ADDR, dropped
                self._push(target)                  # W s: commit the move
                self._relay(2)

    # -- pass 3: wall sweep, AFTER all moves; restartable scan -------------
    def _pass3(self) -> None:
        while True:
            c = self._pull()                        # r
            if c == MARK:
                self._push(c)
                self._relay(3)
                return
            if c >= 4:                              # frozen: skip
                self._push(c)
                self._relay(3)
                continue
            self._push(c)                           # s
            addr = self._pull()                     # r(ADDR)
            self._push(addr)                        # s
            if self._op_fetch(addr) != 16:          # `16` M W - X: not wall
                self._relay(2)
                continue
            self._relay(14)                         # wall: back to own CTRL
            self._pull()                            # r(c)
            self._push(c + 20)                      # `20` M W + s: WALLED
            self._relay(3)                          # -> next man's CTRL

    # -- tick loop top: freeze scan + the K countdown ----------------------
    def _loop_top(self) -> str:
        """head 0 -> head 0; 'tick' / 'idle' / 'emit'.

        The relay over the 12 man slots doubles as a straight-line scan:
        each CTRL branches walled (>=16) / live (<4) / frozen into three
        parallel relay tracks (found-states are idempotent, so tracks
        merge pairwise; ~6 short blocks in the room).
        """
        walled = live = False
        for _ in range(3):                          # r X ... s, relay 3
            c = self._pull()
            self._push(c)
            walled = walled or c >= 16
            live = live or c < 4
            self._relay(3)
        self._relay(3)                              # MARK, SP, SHIFTM
        k = self._pull()                            # r(K)
        if walled:                                  # global freeze: drain
            self._push(0)                           # M - s
            return "emit"
        if k == 0:                                  # X: A == 0
            self._push(0)                           # s
            return "emit"
        self._push(k - 1)                           # M `1` W - s
        return "tick" if live else "idle"

    # -- EMIT: one full-frame repaint + man pixels + commit ----------------
    def _emit(self, token: int) -> None:
        self.deltas.append(token)
        self.msteps += 1

    def emit_frame(self) -> None:
        """head 0 -> head 0.  `1`N s -> REQ asks FETCH for the -1 stream;
        the 256-pixel loop is LLLM round 1's (B = addr*16 accumulator,
        BP = countdown); man pixels are a MARK loop over the ring."""
        colors = self.fetch.send(-1)
        for addr, color in enumerate(colors):       # r(RESP) + s `16` + M ma
            self._emit(addr * 16 + color)
        x = self._pull2()                           # pipes over the grid
        while x != MARK:                            # structural repaint lap
            self._push2(x)
            for _ in range(-x & 31):
                a = self._pull2()                   # r2 s2 (addr, held)
                self._push2(a)
                p = self._pull2()                   # r2 X: 14 full / 6 empty
                self._push2(p)
                self._relay2(1)                     # rs2(val)
                self._emit(a * 16 + (14 if p else 6))
            x = self._pull2()
        self._push2(x)                              # MARK2: ring2 canonical
        while True:
            c = self._pull()                        # r
            if c == MARK:
                self._push(c)                       # s
                self._relay(3)
                break
            self._push(c)                           # s
            addr = self._pull()                     # r(ADDR)
            self._push(addr)                        # s X
            if addr:                                # M `16` W * M `9` W + s
                self._emit(addr * 16 + 9)
            self._relay(2)
        self._emit(-1)                              # `1` N s: commit
        self._check_canonical()

    # -- rounds ------------------------------------------------------------
    def round_in(self, k: int) -> None:
        """r(LOAD) holds k in B across a full lap, stamps K, head 0."""
        self.B = k                                  # r M
        self._relay(15)                             # everything up to K
        self._pull()                                # r: old K, dropped
        self._push(k)                               # W s
        self._check_canonical()

    def round(self, k: int) -> None:
        self.round_in(k)
        while (state := self._loop_top()) != "emit":
            if state == "tick":
                self._pipe_shift()
                self._pass1()
                self._pass2()
                self._pass3()
        self.emit_frame()

    def run(self, stream, ks) -> None:
        self.intake(stream)
        self.emit_frame()                           # round 1: initial frame
        for k in ks:
            self.round(int(k))


# ------------------------------------------------------------------ driver
def run_case3(rows: list[str], ks: list[int]) -> Step3Model:
    model = Step3Model(ScriptedFetch())
    model.run(machine_stream(rows), ks)
    return model


def oracle_frames3(rows: list[str], ks: list[int]) -> list[list[str]]:
    """Frames per round straight from the pinned lockstep oracle."""
    from .llm_lockstep import LockstepLLM

    obj = LockstepLLM.from_stream(machine_stream(rows))
    frames = [obj.render()]
    for k in ks:
        obj.run(int(k))
        frames.append(obj.render())
    return frames


def check_case3(rows: list[str], ks: list[int]) -> Step3Model:
    model = run_case3(rows, ks)
    assert frames_from_deltas(model.deltas) == oracle_frames3(rows, ks)
    return model
