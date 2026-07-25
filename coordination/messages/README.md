# Coordination Messages

Each sender owns one subdirectory:

```text
coordination/messages/<sender>/
```

Create messages from `coordination/templates/message.md` or
`coordination/templates/handoff.md`. Use the UTC filename convention defined
in `docs/two-agent-protocol.md`.

Published messages are immutable. A recipient acknowledges from its own
sender directory; it never edits the original message.
