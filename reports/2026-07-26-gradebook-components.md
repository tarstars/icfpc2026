# Grade Book component optimization

Date: 2026-07-26

## Baseline

The frozen source is `submissions/gradebook/gradebook_04.man`, SHA-256
`94dbbc88658be87b0021cf24a9745ed41e844989fa37642d6401b46b05e1555d`.
Local judging passes 7/7 public cases. The preserved platform record says
20/20 with score `54,422,867,494.2`.

The 16 rooms now have stable component names:

- `input_port`
- `command_frontend`
- `subject_engine[1..4]`
- `scratch_circulator[1..4]`
- `record_circulator[1..4]`
- `result_arbiter`
- `output_port`

`tests/test_gradebook_components.py` freezes their parser order, dimensions,
port counts, and all 30 directed topology edges.

## Completed component checks

### FIFO circulator

The eight 5×5 relay rooms are the same FIFO component under two protocols.
The existing square layout and a 6×4 layout both relay the directed signed
and boundary values. The 6×4 form has smaller area (24 rather than 25), but
a worse maximum dimension (6 rather than 5), so it is retained as an
alternative rather than selected blindly.

### Result arbiter

A compact 6×4 room accepts each of the four inputs independently and drains
four simultaneous values in simulator reading order `[1, 3, 4, 2]`.

Substitution into the full program was valid but not beneficial:

| metric | `gradebook_04` | compact arbiter prototype |
|---|---:|---:|
| dimensions | 386×313 | 386×314 |
| footprint | 148,996 | 148,996 |
| public cases | 7/7 | 7/7 |
| local score | 16,097,634,265.7 | 16,115,535,070.9 |

The prototype is 0.1112% worse because the existing acknowledgement routing
forces an extra row and the changed result-pipe travel increases ticks.
It was therefore not preserved as a solution version or submitted.

### Command frontend

`frontend_reference()` specifies the semantic boundary:

- one roster burst: `N`, then `id,g1,g2,g3,g4` per student, zero-padding
  subjects absent from the input;
- one four-token burst per operation;
- GET → `1,id,subject,0`;
- SET → `2,id,subject,value`;
- AVG → `3,0,subject,0`;
- TOP → `4,0,subject,0`;
- one acknowledgement barrier after the roster and after every operation.

An isolated physical trace runs only the live frontend man, replaces all
four worker inputs with lossless trace sinks, and injects acknowledgements
only at the actual ack receive. On every public case, every output pipe
matches the reference at every barrier.

The 385×115 room is wide primarily because its border spans the four-worker
bank. Its live instructions occupy only the left control region. Cropping
the border alone will not improve the current 386-square footprint; its
value is enabling a later 2×2 worker recomposition.

## Subject engines and `gradebook_05`

Each live subject engine is now tested independently with software-backed
record and scratch circulators. The directed test covers roster loading,
matched GET, SET followed by GET, AVG, TOP, a mismatched subject, result
emission, and acknowledgement chaining for subjects 1–4.

The width-dominating cells were three 80-cell `.` runs per worker. They were
fixed travel delays before blocking record-ring receives. Removing them
preserves correctness because the receive supplies the synchronization.
The raw no-delay machine passed 7/7 before any geometric transformation.

Blindly folding every new worker was unsafe. Whole-program judging selected
merge prefixes 24, 25, 25, and 26 for engines 1–4; the next merge breaks one
public case in engines 2–4. The frontend retains its known-safe prefix 34;
merge 35 still drops to 5/7.

| metric | `gradebook_04` | `gradebook_05` | change |
|---|---:|---:|---:|
| dimensions | 386×313 | 382×307 | max −1.04% |
| footprint | 148,996 | 145,924 | −2.06% |
| average public ticks | 108,040.714 | 95,493.143 | −11.61% |
| local score | 16,097,634,265.7 | 13,934,741,378.3 | **−13.44%** |
| public cases | 7/7 | 7/7 | unchanged |

Preflight reports 16 rooms, 30 pipes, 14 men, valid layout, and pipe lengths
from 2 to 696. The exact artifact SHA-256 is
`315a41d54ffc7ed64b097dd2ffb83ca04f9ba579a15d3d1cb26c70542a8c825e`.

The mandatory live freshness read at 2026-07-26T14:26:56Z found the team at
20/20, score `54,422,867,494.2`, rank 50 before `gradebook_05`.

Submission `010701d6-3d29-41e1-a09f-dae700e2f9ec` completed at
2026-07-26T14:34:13Z: 20/20, 382×307, average ticks `322,878.9`, score
`47,115,780,603.6`. This is a 13.43% live improvement. The full terminal
response is preserved in `submissions/gradebook/gradebook_05-submit.json`.

## Remaining experiments

1. Try a cropped frontend plus 2×2 worker recomposition.
2. Search safe column relocations inside subject-engine pipe-selection zones.
3. Integrate compact relays and arbiter only when the recomposed whole machine
   proves a score reduction.

Whole-program public judging remains mandatory after every substitution:
pipe length changes affect both capacity and timing even when room behavior
is unchanged.
