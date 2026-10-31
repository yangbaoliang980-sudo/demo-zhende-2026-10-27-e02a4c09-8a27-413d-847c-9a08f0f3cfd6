# P27 visual composition and anchor specification

Version: `P27-ENEMY-VISUAL/0.1.0-isolated`

## Composition rules

1. Enemy artwork is delivered as a transparent image layer. HP, shield, intent, name, status, damage numbers and targeting indicators remain independent UI/data layers owned by P19/P14/P16.
2. No business text, HP bar, intent icon, phase label or numeric value is baked into any SVG/PNG.
3. The PNG artwork is a 1024×1024 visual canvas, not a runtime hitbox. Transparent canvas margins are preserved; no auto-trim is performed.
4. Candidate face-focus and visual-center points are recorded in `enemy_anchors.tsv` as normalized coordinates. They are composition guides only.
5. P23's anchor contract states a 24 logical-pixel design safe margin, viewport logical coordinates, and re-sampling on layout/scroll/resize/text-scale/locale/modal/snapshot changes. P19 owns runtime rectangle sampling. Therefore P27 does not freeze screen-space rectangles or UI overlay coordinates.
6. For card composition, place P19's text/HP/intent in independent UI regions outside the illustration's essential silhouette. If the approved card viewport cannot preserve this separation, P23/P19 must request and approve a crop/window change before artwork is reframed.

## Visual tier proposal (not game balance)

- COMMON: low and broad silhouette; one primary shell motif; warm eye/core accent.
- ELITE: upright silhouette; increased vertical span; split crown and paired shoulder forms.
- BOSS: large axial silhouette; halo/crown/core hierarchy; phase variants intentionally absent until P06 is available.

The tier language is designed to remain legible in grayscale and at 78×92 small-window scale as a hypothesis; actual 78×92 readability has not been tested in the target engine and is NOT_RUN.

## Anchor semantics

`candidate_hit_center` means a proposed center of the visible mass for future P28 visual alignment. It is not a collider, hitbox, hit event, damage origin, or runtime geometry source. `face_focus` means a visual recognition focus. P19/P23/P28 must remeasure and accept any runtime anchor before use.
