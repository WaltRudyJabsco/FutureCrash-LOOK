# Future Crash + LOOK 1.9.0

This release tightens four interaction layers at once.

1. **Path completion everywhere:** filer copy/move destinations now complete paths with Tab, and shell file-action helpers use repeated native path completion for every operand.
2. **LOOK-native global find:** `f` and `fznv` keep their fast global retrieval behavior but use LOOK's own visual/action language.
3. **Temporal memory:** recent exchanges and semantic candidates carry age, creation, and reinforcement information. Memory is explicitly historical context, never a pending task queue.
4. **Background LO message passing:** `lo bg REQUEST` queues one-shot LO work. Jobs emit durable completion/failure events, which the shell surfaces at the next prompt. `lk jobs` and `lk events` expose the state.

The background layer is deliberately queue/event based rather than a resident daemon. It establishes a stable local messaging contract that Future Crash, the shell, or a future Unix-socket/HTTP broker can all use.

LOOK is 3.13.0. Future Crash remains 1.1.7.
