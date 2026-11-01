# P32 QA Automation V0.1 — isolated handoff

Status: `ISOLATED_QA_EXECUTED / PRODUCTION_GATE_BLOCKED`.

## What was actually tested
- Upstream P29 isolated Python package baseline: 14/14 tests passed.
- Independent P32 contract suite: 7 tests, 5 passed, 2 failed.
- Failures are reported as defects, not hidden or patched by P32:
  - P32-DEF-001: repeated `skip_epoch()` emits duplicate cancellation commands.
  - P32-DEF-002: boolean `seq=True` is accepted because Python bool is an int subclass.

## Reproduce
Run from this package root:
```bash
python -m unittest discover -s target_fixture/tests -v
python -m unittest discover -s tests/automated -v
```
The second command is expected to exit non-zero until P29 fixes the two reported defects.

## Boundaries
P13's supplied `actual_path_mapping.json` says `actual_game_repository=null`,
`actual_game_commit=null`, `production_write_authorized=false`. Therefore this package is
an isolated fixture only. It does not write to the production project. Unity import,
Windows build, Anki runtime, dual-client build parity and E2E remain NOT_RUN/BLOCKED.

## Handoff
- Fix owner: P29 for both defects.
- Re-test owner: P32.
- Independent evidence review: P35.
- P32 does not approve release and does not claim cross-module integration.
