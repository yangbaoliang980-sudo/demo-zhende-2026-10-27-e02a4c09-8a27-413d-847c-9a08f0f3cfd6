# P29 Battle Animation Player V0.1 — isolated package

## Status

`ISOLATED_IMPLEMENTATION_DELIVERED / PRODUCTION_INTEGRATION_BLOCKED`.

This is executable Python reference code for the presentation-only event consumer. It is not a Unity/Godot production integration and does not claim compatibility with a frozen P14 DTO: the P28 handoff explicitly marks the P02 event contract and P29 player contract blocked. The supplied P13 mapping confirms `actual_game_repository=null`, `actual_game_commit=null`, and `production_write_authorized=false`. Therefore this package is intentionally isolated and does not write any game repository paths.

## Implemented

- Monotonic `seq` consumption; duplicate and stale-epoch rejection.
- Sequence gaps and future epochs return `SYNC_REQUIRED`; no event synthesis or replay.
- Snapshot recovery clears queued decoration and resets HP/shield visual baselines.
- `normal`, `fast`, `reduced`, `none`, mute and idempotent skip semantics.
- Background/resume requires a new authoritative snapshot.
- HP/shield interpolation is presentation-local only.
- Missing P19 anchor rectangles suppress guessed travel/impact coordinates.
- Persistent result-log commands preserve HP loss and shield absorbed as separate facts.

## Run tests

From this directory:

```bash
python -m unittest discover -s tests -v
```

The tests validate the isolated Python module only. They do not establish engine import, P14 contract compatibility, P19 HUD integration, real-time rendering, audio playback, accessibility conformance on target hardware, or end-to-end battle correctness.

## Integration contract required

P13/P14/P19 must provide a frozen versioned event/snapshot DTO and P19 must provide sampled current viewport anchors. The host must implement snapshot request/response, rendering, audio, lifecycle hooks and cancellation token binding. The host must never route presentation commands back into P14 domain mutation.

## Upstream interpretation

- P28 proposed timing values are copied into `contracts/event_to_presentation.json`; they are not treated as frozen.
- P23 reduced-motion semantics are applied: reduced/none suppress motion and retain static result facts; fast collapses decoration; skip cancels only the current visual epoch.
- P27 hit-center coordinates remain `PROPOSAL_NOT_RUNTIME`; this package does not use them as runtime positions.
- Supplied VFX images are visual references only. Their provenance/licence has not been approved for redistribution, so they are not embedded in this source package.

## Ownership boundaries

P29 owns only this isolated player and its tests. P14 owns battle values/events; P19 owns HUD and input; P13 owns internal DTO and production path authorization; P28 owns original FX sources. No cross-module merge was performed.
