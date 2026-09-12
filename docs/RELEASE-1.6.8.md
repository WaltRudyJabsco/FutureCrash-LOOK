# Future Crash + LOOK 1.6.8

This release makes LO's model-resource policy explicit.

- LOOK 3.8.1
- Future Crash 1.1.7
- LO working context: 8192 tokens
- LO output ceilings: light 800, adaptive 1400, deep 2000
- Recent chat history is bounded by both message count and approximate serialized size.
- Thinking depth now controls the Ollama `think` field when the selected model reports thinking capability.
- Background memory, summary, and skill extraction run with small explicit no-thinking budgets.

The design goal is consistent behavior across a modest local laptop and a fast remote GPU: ceilings provide headroom, while short answers still stop naturally.
