# reverse triple extraction — working notes

Base: reverse_07 (13x13, live 84,922, `src/littleman/alexey_reverse7.py`).
Pump interior (7w x 6h), ring protocol: frame [k, v1..vk] circulates
relay->pump; per pass the send-then-read loop `> s U d m ^` (enter A=k-2,
BP=k-2) relays k-2 and exits holding v_{k-1}; tail prints v_k then v_{k-1}.

GOAL: extract THREE per pass. Loop entered with A=k-3, BP=k-3 relays k-3,
exits holding v_{k-2}; stash v_{k-2} (send to a 1-value side room or park in
BP via b? BP write-only -- must be a stash ROOM), read v_{k-1} (hold in B via
M), read v_k, print v_k, W print v_{k-1}, recall v_{k-2} from stash, print.
Branches: k==1 spur (A=-2), k==2 (A=-1), k==3 (A=0 straight onto U), k>3
(A>0 cw). X three-way is sign-based: need k==1 and k==2 BOTH on the A<0 arm
-- disambiguate with a second X after adding 1, or handle k<=2 on one spur
lane (read+print up to 2 values directly; ring empty in both cases).
Stash room: 4x4 with @ relay man (r then s, like the main relay) OR
stash via the OUTPUT pipe order?? NO -- output order must be v_k first.
Stash cost: ~+1 col/row somewhere; 13x13 -> likely 14x14 (fp 196).
Payoff: relays n^2/6 vs n^2/4; est avg ~340-360; 196x350 ~ 68k vs 84.9k.
If box stays 13: 169x350 ~ 59k.

Steps: (1) simulate protocol on paper for k=1..5; (2) build in a lab.py like
experiments/alexey-reverse06/lab.py (copy check/save/stress); (3) audit
resolution (stash room adds 2 pipes to pump: nearest-pipe re-audit ALL);
(4) fuzz every length 1..16 x3 patterns + 250 multi-round; (5) submit if
< 84,922 local-equivalent.

## step 1 DONE: protocol verified in python
round_sim: relay k-3, emit [v_k, v_{k-1}, v_{k-2}]; k<=2 -> emit reversed
remainder directly. Correct for all n=1..16. n=16: 35 relays (was 64),
6 passes (was 8).

## steps 2-3 RESULT: triple extraction is NOT worth building -- proven during layout

**1. The third slot cannot be free.** Print order v_k, v_{k-1}, v_{k-2}
forces holding TWO values while reading the third. Registers give A+B only
(BP is write-only). Every alternative stash was eliminated:
- ring-as-stash: the deferred value lands BEHIND the next frame; re-deriving
  the protocol shows "defer one into the ring" collapses into EXACTLY the
  reverse_07 protocol (send head+k-2, hold v_{k-1}) -- reverse_07 is already
  the optimum for 2 registers. n^2/4 is the 2-register floor.
- output-pipe-as-stash: O admits one pipe; FIFO order wrong.
- relay-as-stash: relay man's R reads any-ready -> would forward stash into
  the ring; a routing relay needs a bigger program and its own resolution
  audit -- a second room in disguise.

**2. A stash ROOM forces the box past the profit line.** The tail becomes
`M r W s' r s W s r'' s` (10 work cells vs 6) and the k<=2 spur needs its
own x-branch (+ b m m r x + two arms) -- pump interior 7x6 -> at least
9-10 wide even before the stash. The stash room itself (4x6 minimal relay)
needs 2-row pipe gaps on both ports. Every packing attempt lands at 15x15+:
fp 225 x ~340 avg = ~76k vs live 84,922 = 1.11x -- for hours of high-risk
walk-graph work. 14x14 does not fit the stash at all; 13x13 has zero free
4x6 regions.

**3. The register-count law (worth keeping):** with s spare slots the ring
family costs ~n^2/(2s). reverse_01 was s=1 (n^2/2 -> 5n^2 with overhead),
reverse_07 is s=2 (n^2/4), triple needs s=3 and the 3rd slot costs more fp
than it saves ticks at n<=16. The 15.3k leader is NOT in this family --
that is linear time, i.e. Theta(n) storage slots, i.e. an architecture with
~n cells of addressable state in <=13x13, which no bound I have covers.

Step 1's protocol sim remains valid if anyone finds a free third slot.
