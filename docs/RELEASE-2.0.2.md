# Future Crash + LOOK 2.0.2

LO had become more capable than its original runtime ceilings allowed. Complex but ordinary tasks could consume most of a 1,400–2,000-token generation budget in reasoning/tool work and reach the answer only on a follow-up turn.

2.0.2 makes runtime capacity adaptive:

| Tier | Context | Output ceiling | Tool rounds |
|---|---:|---:|---:|
| FAST | 8,192 | 1,500 | 4 |
| STANDARD | 16,384 | 3,500 | 8 |
| DEEP | 24,576 | 6,000 | 12 |

These are ceilings, not quotas. A weather lookup or short file action still stops as soon as it is done.

STANDARD is intended for tasks such as counting files, inspecting a directory, comparing several selected files, explaining code, or searching a workspace. DEEP is selected for larger multi-file analysis, debugging, architecture/refactoring work, or explicit deep-thinking mode.

Use `lk budget <example request>` to inspect which tier LOOK would choose while benchmarking different local models.

LOOK is 4.0.2. Future Crash remains 1.1.7.
