# Architecture

Future Crash and LOOK are one distributed environment with two modules.

- LOOK owns shell/navigation/system/file/AI tooling.
- Future Crash owns the ambient workstation/front-end experience.
- The installer owns composition.

Public commands:
- `future-crash` / `rst` / `fc` — front end
- `lk` / `lo` — underlying terminal tools

Future Crash's launcher reads LOOK's selected Ollama model and host, so there is one AI configuration rather than two competing configurations.
