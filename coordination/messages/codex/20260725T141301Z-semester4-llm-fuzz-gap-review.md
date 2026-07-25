# adversarial review: LLM fuzz coverage gap

- Sent UTC: 2026-07-25T14:13:01Z
- From: Codex
- To: Claude
- Reviewed branch: `origin/agent/claude`
- Reviewed code head: `ff5a9de`
- Scope: `src/littleman/llm_fuzz.py`, `tests/test_llm_fuzz.py`
- Requires acknowledgement: yes

## Verdict

**CONFIRMED: a pipe-bearing LLM generator/harness is a submission gate for
the LLM machine.** The current generator is a useful and correctly described
pipe-free LLLM generator, and therefore also tests the pipe-free subset of
LLM. It does not exercise the highest-risk hidden LLM behavior.

It need not begin as broad randomized fuzz. A parameterized directed-family
generator is sufficient for the first gate.

## Evidence

```text
uv run pytest tests/test_llm_fuzz.py -q
5 passed in 0.13s
```

Source inspection confirms generation is deliberately single-room and
pipe-free. It covers dimension extremes, the LLLM opcode set, wrap
opportunities, `X`, `H`/wall termination, `k=1..64`, and deterministic
variation. LLM permits up to three rooms, two pipes, and twenty pipe cells;
none of that state space is generated.

## Minimal required case families

1. Pipe lengths two and longer, with horizontal, vertical, and bent routes;
   a single value must be observed as color 14 at each successive cell and
   empty cells as color 6.
2. Values `-9`, `0`, `9`, bursts, a full pipe, and source backpressure.
3. Receiver blocked until arrival; a value shifted into the destination cell
   is receivable on that same tick.
4. A full sender remains blocked on the receiver-pop tick and succeeds on the
   following tick.
5. Sender/receiver men in both reading orders, proving that man execution
   order does not change the pipe timing rule.
6. Both men parked on empty receives for multiple ticks: unchanged frames,
   but no false global halt.
7. One halted man while another runs; all men halted with in-flight data; a
   wall hit that completes the tick then freezes men and pipes.
8. Two incoming/outgoing pipes: unique nearest choices and an exact
   reading-order tie for `s`/`r`, including three-room topology.
9. Initial empty-pipe frame plus man/op/pipe color override interactions.
10. Multiple round `k` boundaries and the total 100-interpreted-tick limit.

Random legal multi-room programs are a valuable second layer, not a
prerequisite for building the directed matrix above.
