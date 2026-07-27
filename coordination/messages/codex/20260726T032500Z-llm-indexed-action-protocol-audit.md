# LLM indexed-action protocol audit

Status: read-only audit of the next implementation boundary; no code or
contest mutation.

Confirmed from the frozen LLM problem description and the physical leaf
contracts:

1. A no-eligible-pipe action is unreachable. The problem explicitly
   guarantees that `s` and `r` execute only in rooms with a pipe in the
   required direction. Therefore absent table slots may be encoded as
   ineligible and SELECTELIGIBLE may retain its assertion that at least one
   slot is eligible.
2. `bindscore = Manhattan distance * 256 + endpoint_address` is the exact
   distance/read-order key on a 16x16 display. Endpoint addresses are
   row-major, so no separate slot-order tie breaker is semantically needed.
3. The negative event token is a safe source-room identity. It is
   `-(man_addr + 1)`; well-formed disjoint rooms have distinct man addresses.
   Room order remains input/creation order.
4. Receive ownership uses the stored destination-wall address and the
   destination room rectangle. The address is already known to be on a room
   wall, so BORDERCHECK's rectangle containment is sufficient.

Critical record-layout warning:

- an indexed pipe begins `(start_candidate, source_event, ...)`;
- `start_candidate` is a packed geometry-discovery token, **not** the send
  endpoint;
- send target = the first body cell after `source_event`;
- receive target = the last body cell before `PIPE_DEST_STATE`;
- destination ownership address = the word after `PIPE_DEST_STATE`.

Mutation ordering:

- MASKMAP advances all pipes first;
- rooms then act in preserved creation order;
- each successful PIPEAPPLY update must replace the mutable pipe table before
  the next room acts;
- blocked send/receive changes neither address nor A;
- successful send/receive advances address by the room control heading;
- successful receive also replaces A with PIPEAPPLY's result.

This is the minimum complete contract for the next physical coordinator.
