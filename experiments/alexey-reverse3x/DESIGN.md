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
