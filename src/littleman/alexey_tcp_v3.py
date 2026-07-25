"""tcp_04 -- marker-free ring, packed to 38x38. Live 20/20, score 5,981,626.

Progression from this line: tcp_00 20,028,106 -> tcp_02 8,554,029 ->
tcp_03 7,693,504 -> tcp_04 5,981,626 (3.35x).

ALGORITHM (unchanged since tcp_02). Slot w0 -- the next expected sequence
number -- is ALWAYS empty at packet start, because every packet drains to
completion. So it need not be stored: the ring holds w1..w15 only, 15
values with no sentinel, and the marker-realign that ate 46% of the v2
machine's ring ops simply does not exist.

  d >= 1 : rotate d-1, pop the stale slot, push val, relay 15-d.
           Constant 16 ops and no drain -- an off-head insert cannot fill w0.
  d == 0 : emit val straight to the forwarder, then pop-and-emit while the
           head is positive. The forwarder's 0 refill lands at the tail,
           which is exactly where the freed window slot belongs, so the
           invariant restores itself. An in-order packet costs TWO ring ops.

REGISTERS. exp lives in B permanently. The two loop counts would need a
second counter nobody has, so the SPLITTER supplies the constant instead:
it sends seq down the S pipe and (15-seq, val) down the V pipe. The pump
gets d from one `-` and 15-d from one `+`. tcp_03 moved 15-seq from the S
pipe to the V pipe so both of the pump's mid-packet reads sit in the same
zone -- that alone removed ~25 ticks/packet of walking.

LAYOUT RULE worth reusing. All three of the pump's incoming pipes enter
the SAME wall (the bottom). The row term of the Manhattan distance is then
identical for all of them, so the zone is decided purely by column and a
read cell's pipe no longer depends on how deep in the room it sits. All
nine `r` cells resolved correctly on the first audit.

TRAPS, one debug round each:
  * a counted relay loop needs `m` inside it -- `d` only tests the
    backpack, it does not decrement, so a loop without `m` spins forever;
  * RIN must be able to park the WHOLE ring (>= 16 cells). When the pump
    idles between packets the forwarder keeps pushing; a short RIN blocks
    it and any tag queued behind those values is never decoded;
  * mirroring a room vertically must swap v<->^, and is only safe when the
    room has no handed op (X, d, a, x), since a mirror flips CW into CCW;
  * a pipe cell whose backward neighbour is a room wall starts a NEW pipe
    there -- keep routed cells one column clear of foreign rooms.

Validated: 6/6 public, 46/46 boundary stress (n=48, full window, instant
loss, fully reversed), 20/20 live.
"""

import sys

def build():
    from littleman.canvas import Canvas
    P={}
    def C(r,c,ch):
        assert 1<=r<=21 and 1<=c<=22, ('oob',r,c,ch)
        assert (r,c) not in P, ('collide',r,c,P[(r,c)],ch); P[(r,c)]=ch
    def W(r,c,s):
        for i,ch in enumerate(s): C(r,c+i,ch)
    # ---- INIT: BP=15, A=0, B=0 ; seed 15 zeros -------------------------
    W(1,1,'@`15`b0M'); C(1,9,'v')
    C(2,9,'v'); C(3,9,'d'); C(3,8,'s'); C(3,7,'m'); C(3,6,'^'); C(2,6,'>')
    C(4,9,'<'); C(4,4,'v')
    # ---- PROLOGUE row 5 : r(S)=seq, d=seq-exp, loss test, 3-way branch --
    C(5,4,'>'); C(5,5,'r'); C(5,6,'-'); C(5,7,'b'); W(5,8,']]]]')
    C(5,12,'a'); C(5,13,'X')
    # ---- LOSS (d>=16): north, then east on row 2 -----------------------
    C(4,12,'^'); C(3,12,'^'); C(2,12,'>'); W(2,13,'`2000`'); C(2,19,'N'); C(2,20,'s'); C(2,21,'H')
    C(4,13,'H')                                   # d<0 cannot occur
    # ---- DPOS (d>=1) ---------------------------------------------------
    C(6,13,'b'); C(7,13,'m'); C(8,13,'v')
    C(9,13,'v'); C(10,13,'d'); C(10,12,'r'); C(10,11,'s'); C(10,10,'^'); C(9,10,'>'); C(9,12,'m')
    C(11,13,'r')                                  # pop stale slot
    C(12,13,'>'); C(12,17,'r'); C(12,18,'+'); C(12,19,'b')     # 15-seq from V -> BP=15-d
    C(12,20,'r'); C(12,21,'s'); C(12,22,'v')                   # val from V -> ring
    C(13,22,'<'); C(13,12,'v'); C(14,12,'v')
    C(15,12,'v'); C(16,12,'d'); C(16,11,'r'); C(16,10,'s'); C(16,9,'^'); C(15,9,'>'); C(15,11,'m')
    C(17,12,'<'); C(17,4,'^')                     # shared return lane, col 4
    # ---- D0 (d==0) -----------------------------------------------------
    C(5,17,'r')                                   # discard 15-seq
    C(5,20,'r'); C(5,21,'N'); C(5,22,'v')         # val -> tag
    C(6,22,'<'); C(6,21,'s'); C(6,20,'1'); C(6,19,'+'); C(6,18,'M'); C(6,14,'v')
    C(18,14,'v'); C(19,14,'r'); C(20,14,'X')
    C(20,13,'N'); C(20,12,'s'); C(20,10,'^'); C(19,10,'^'); C(18,10,'>'); W(18,11,'1+M')
    C(21,14,'<'); C(21,4,'^')                     # shared return lane

    PUMP=[''.join(P.get((r,c),' ') for c in range(1,23)) for r in range(1,22)]
    SPL={}
    def c1(r,c,ch):
        assert (r,c) not in SPL,(r,c); SPL[(r,c)]=ch
    c1(1,1,'@'); c1(1,2,'r'); c1(1,11,'v')
    c1(2,11,'<'); c1(2,10,'r'); c1(2,9,'s'); c1(2,8,'M')
    for c,ch in zip(range(4,8),'`51`'): c1(2,c,ch)
    c1(2,3,'-'); c1(2,2,'v')
    c1(3,2,'v'); c1(3,11,'^')
    c1(4,2,'>'); c1(4,3,'s'); c1(4,4,'r'); c1(4,5,'s'); c1(4,11,'^')
    SPLIT=[''.join(SPL.get((r,c),' ') for c in range(1,12)) for r in range(1,5)]

    sw={'v':'^','V':'^','^':'v'}
    SPLIT_F=[''.join(sw.get(ch,ch) for ch in r) for r in SPLIT[::-1]]
    # ---------- compact forwarder: fast path 8-9 cells ----------
    F={}
    def c2(r,c,ch): assert (r,c) not in F,('collide',r,c); F[(r,c)]=ch
    c2(1,3,'>'); c2(1,4,'M')
    for c,ch in zip(range(5,11),'`2000`'): c2(1,c,ch)
    c2(1,11,'+'); c2(1,12,'X'); c2(1,13,'1'); c2(1,14,'N'); c2(1,15,'s'); c2(1,16,'H')   # loss
    c2(2,1,'>'); c2(2,2,'r'); c2(2,3,'X'); c2(2,4,'v')                                   # hot loop
    c2(2,12,'>'); c2(2,13,'W'); c2(2,14,'N'); c2(2,15,'s'); c2(2,16,'v')                 # data -> OUT
    c2(3,1,'^'); c2(3,3,'s'); c2(3,4,'<'); c2(3,16,'v')                                  # s -> RIN
    c2(4,1,'^'); c2(4,3,'<'); c2(4,5,'s'); c2(4,6,'0'); c2(4,16,'<')                     # refill -> RIN
    c2(5,2,'@'); c2(5,3,'^')                                                             # one-time entry
    FWD=[''.join(F.get((r,c),' ') for c in range(1,17)) for r in range(1,6)]
    def box(i):
        w=len(i[0]); return ['+'+'-'*w+'+']+['|'+r+'|' for r in i]+['+'+'-'*w+'+']
    cv=Canvas()
    cv.put(0,0,box(PUMP))                # pump rows0-22 cols0-23
    cv.put(28,6,box(FWD))                # forwarder rows28-34 cols6-23; RIN top rel c3=abs9, OUT right rel r3=abs31
    cv.put(29,25,box(SPLIT_F))           # splitter rows29-34 cols25-37; S/V col 27
    cv.put(24,33,["+-+","|I|","+-+"]); cv.pipe([(27,34),(28,34)])
    cv.put(23,17,["+-+","|O|","+-+"]); cv.pipe([(27,18),(26,18)])
    cv.pipe([(23,3),(31,3),(31,5)])                                                   # ROUT down west side
    cv.pipe([(27,9),(26,9),(26,4),(25,4),(25,14),(24,14),(24,11),(23,11)]); cv.cells[(23,11)]='^'  # RIN
    cv.pipe([(28,27),(24,27),(24,20),(23,20)]); cv.cells[(23,20)]='^'                 # V
    cv.pipe([(35,27),(37,27),(37,2),(23,2)]); cv.cells[(23,2)]='^'                    # S

    return cv.render()

if __name__=='__main__':
    sys.stdout.write(build())
