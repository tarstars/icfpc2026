"""tcp_02 -- marker-free ring. Live 20/20, score 8,554,029 (tcp_00 was 20,028,106).

The v2 machine kept a resident marker in the ring and paid a 15-relay
realign after every packet to put it back where the drain had displaced
it -- 46% of all ring ops. This design deletes the marker outright.

Key idea: slot w0 (the next expected sequence number) is ALWAYS empty at
packet start, because every packet drains to completion. So w0 need not
be stored at all. The ring holds only w1..w15 -- 15 values, no sentinel:

  d >= 1: rotate d-1, pop the stale slot, push val, relay 15-d.
          Total 16 ops, and no drain: inserting off-head cannot fill w0.
  d == 0: emit val straight to the forwarder, then pop-and-emit while the
          head is positive. The forwarder's 0 refill lands at the tail,
          which is exactly where the freed window slot belongs, so the
          invariant restores itself with no fixup. An in-order packet
          costs TWO ring ops (v2 charged ~36).

Both loop counts come from one subtraction each because the SPLITTER
sends seq and 15-seq: the pump holds exp in B, so `-` yields d and `+`
yields 15-d. That frees B permanently and removes the need to stash a
second counter anywhere.

Measured: 1075 ring ops over the 6 public cases vs v2's 3204 (2.98x),
and the forwarder's fast path is 8 cells vs v2's 28, so the pump never
starves. 6/6 public, 46/46 boundary stress, 20/20 live.

Traps that cost a debug round each, in case this gets rebuilt:
  * a counted relay loop needs `m` in it -- `d` only tests, it does not
    decrement, so a loop without `m` spins forever;
  * RIN must be able to park the WHOLE ring (>= 16 cells). When the pump
    idles between packets the forwarder keeps pushing; a short RIN blocks
    it and any tag still behind those values never gets decoded;
  * mirroring a room vertically must swap v<->^ (and is only safe when
    the room has no handed op: X, d, a, x).
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
    # ---- INIT: BP=15, A=0, B=0 ------------------------------------------
    W(1,1,'@`15`b0M'); C(1,9,'v')
    # seed loop rows 2-3 cols 6-9 (8-cell: entry col 9 heading south)
    C(2,9,'v'); C(3,9,'d'); C(3,8,'s'); C(3,7,'m'); C(3,6,'^'); C(2,6,'>')
    C(4,9,'<'); C(4,4,'v')                       # seed exit -> prologue
    # ---- PROLOGUE row 5 --------------------------------------------------
    C(5,4,'>'); C(5,5,'r'); C(5,6,'-'); C(5,7,'b')
    W(5,8,']]]]'); C(5,12,'a'); C(5,13,'X')      # a: BP>0 (d>=16) -> CCW = north = LOSS
    C(5,1,'>')                                   # return-lane merge into prologue
    # ---- LOSS: north up col 12 to row 2, east ----------------------------
    C(4,12,'^'); C(3,12,'^'); C(2,12,'>'); W(2,13,'`2000`'); C(2,19,'N'); C(2,20,'s'); C(2,21,'H')
    # ---- d<0 impossible: halt --------------------------------------------
    C(4,13,'H')
    # ---- DPOS (d>=1): south from X ---------------------------------------
    C(6,13,'b'); C(7,13,'m'); C(8,13,'v')
    C(9,13,'v'); C(10,13,'d'); C(10,12,'r'); C(10,11,'s'); C(10,10,'^'); C(9,10,'>'); C(9,12,'m')   # rotate loop
    C(11,13,'r')                                  # pop w_d (RIN)
    C(12,13,'>'); C(12,20,'r'); C(12,21,'s'); C(12,22,'v')                             # val from V, push
    C(13,22,'<'); C(13,5,'r'); C(13,4,'+'); C(13,3,'b'); C(13,2,'v')                   # 15-seq from S
    C(14,2,'>'); C(14,12,'v')
    C(15,12,'v'); C(16,12,'d'); C(16,11,'r'); C(16,10,'s'); C(16,9,'^'); C(15,9,'>'); C(15,11,'m')   # relay loop
    C(17,12,'<'); C(17,1,'^')                                                          # return north col 1
    # ---- D0 (d==0): straight east from X ---------------------------------
    C(5,20,'r'); C(5,21,'N'); C(5,22,'v')                                              # val, tag
    C(6,22,'<'); C(6,21,'s'); C(6,20,'1'); C(6,19,'+'); C(6,18,'M'); C(6,14,'v')       # emit, exp++
    C(18,14,'v'); C(19,14,'r'); C(20,14,'X')                                           # drain loop
    C(20,13,'N'); C(20,12,'s'); C(20,10,'^'); C(19,10,'^'); C(18,10,'>')
    W(18,11,'1+M')
    C(21,14,'<'); C(21,5,'r'); C(21,1,'^')                                             # discard 15-seq, return

    PUMP=[''.join(P.get((r,c),' ') for c in range(1,23)) for r in range(1,22)]
    SPL={}
    def c1(r,c,ch): SPL[(r,c)]=ch
    c1(1,1,'@'); c1(1,2,'r'); c1(1,11,'v')
    c1(2,11,'<'); c1(2,10,'r'); c1(2,9,'s'); c1(2,8,'M')
    for c,ch in zip(range(4,8),'`51`'): c1(2,c,ch)
    c1(2,3,'-'); c1(2,2,'s'); c1(2,1,'v')
    c1(3,1,'v'); c1(3,11,'^')
    c1(4,1,'>'); c1(4,2,'r'); c1(4,3,'s'); c1(4,11,'^')
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
    cv.put(29,30,box(SPLIT_F))           # splitter rows29-34 cols30-42; S/V col 32
    cv.put(24,36,["+-+","|I|","+-+"]); cv.pipe([(27,37),(28,37)])
    cv.put(30,26,["+-+","|O|","+-+"]); cv.pipe([(31,24),(31,25)])
    cv.pipe([(23,3),(31,3),(31,5)])                                                   # ROUT down west side
    cv.pipe([(27,9),(26,9),(26,4),(25,4),(25,16),(24,16),(24,11),(23,11)]); cv.cells[(23,11)]='^'  # RIN
    cv.pipe([(28,32),(24,32),(24,20),(23,20)]); cv.cells[(23,20)]='^'                 # V
    cv.pipe([(35,32),(37,32),(37,2),(23,2)]); cv.cells[(23,2)]='^'                    # S

    return cv.render()

if __name__=='__main__':
    sys.stdout.write(build())
