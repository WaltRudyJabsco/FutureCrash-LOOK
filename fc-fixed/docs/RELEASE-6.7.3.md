# 6.7.3 · LET GO

6.7.3 hardens the persistent working-state architecture introduced by STAY AWAKE. A pending slot now means exactly one thing: LO is waiting for operator input. It does not grant an old goal ownership of arbitrary future utterances.

When a weather location is supplied, LO clears the operator-input obligation before touching the WEATHER edge and marks the goal running. A failed provider invocation retires that run as failed instead of leaving a zombie clarification that can hijack later turns or a fresh LO process.

Continuation recognition is structural rather than an expanding capability blacklist. Bare places still satisfy a pending location; explicit weather restatements contribute only their extracted place; new questions and commands such as `what is the time`, `lo what is the date`, or `open the browser` remain new intent.

Regression coverage includes the exact cross-intent failure observed on the M4 Air. Full suite: 377 tests.
