# tools/models — the in-repo model generator (frozen interface, 2026-09-08)

Updated: 2026-09-08

Models authored AROUND their hit geometry, so drawn == registered by construction instead
of by measurement. Sanctioned by the user 2026-09-08 (*"falls nötig erstelle eigene modelle
nochmal … wenn du sagst es hilft gerade bei richtigen hitboxen. dann mach das!"*). Design
scouted the same day; the full design report is condensed here — this file IS the interface
contract for the build round, frozen by the main head before the fan-out.

## The one honesty rule

A faceted surface must straddle its analytic hit surface symmetrically: capsule rings are
authored at the **mid-radius** `r' = r·2/(1+cos(π/n))`. **The authoritative band is
`geometry.mid_radius_band(n)` = `(1−cos(π/n))/(1+cos(π/n))·r`** — exactly 0.0396·r at n=8
and 0.0173·r at n=12 (wave 1 measured the first README rounding of 0.038 as too tight for
n=8: a sampler hitting a ring vertex exceeds it by construction; the measured whole-body
max at n=12 incl. cap polar chords is 0.0208·r). All style jitter stays inside the same
band. The demo proof artifacts live at `specs/demo-body.json` →
`assets/3d/gen/demo-body.glb` (33 460 B, deterministic sha a45f6523…). The generator READS the authoritative geometry (`titan.ron:
drawn_poses`, `art.ron: hulls`) — a spec never copies numbers out of them (rule 5).

## Files (python stdlib ONLY, same byte-pattern as tools/glb_merge.py)

- `glbout.py` — the glb writer. FROZEN API:
  `add_mesh(name, verts, normals, uvs, indices)` · `add_empty(name, xyz)` · `write(path)`.
  One scene, one untransformed root, mesh nodes with translation only, POSITION/NORMAL/
  TEXCOORD_0, mode 4, one material with a small palette texture EMBEDDED in the BIN chunk
  (no ../../texturen coupling). Output must satisfy `glb_merge.py` `preconditions()`.
- `geometry.py` — capsule loft (flat shading via per-face duplicated verts), box extrusion
  with edge-break detail, wedge. Mid-radius rule lives here.
- `ron_read.py` — minimal regex extractors for drawn_poses and hulls rows (the
  fleet's verify_caps.py pattern).
- `gen.py` — CLI `python3 tools/models/gen.py [--check] specs/<name>.json`. DETERMINISTIC:
  fixed seed from the spec, no wall clock; re-run with an unchanged spec is byte-identical.
  Writes generator version + spec sha256 into glTF `asset.extras`.
- `accept.py` — the gate, run after every generation, nonzero on breach. Ported from
  tools/fleet/verify_caps.py + validate.py. **Proven on a known-bad input first**: it must
  reproduce a-042's 0.44 m / ~0.52 u numbers before it may judge a generated file.
- `specs/*.json` — STYLE ONLY per model: palette keys, facet counts, detail toggles, seed,
  plus a pointer naming the authoritative geometry (`"titan.ron:drawn_poses/titan_husk"`
  or `"art.ron:hulls/ruin_wall_corner"`).

## Spec schema (frozen)

```json
{
  "name": "titan-husk",
  "geometry": "titan.ron:drawn_poses/titan_husk",
  "kind": "titan | remnant | prop",
  "seed": 12345,
  "facets": { "torso": 12, "limb": 8 },
  "palette": { "skin": "sand_brown..brick_red", "nape_band": "roof_slate" },
  "detail": { "nape_band": true, "eyes": true, "edge_break_m": 0.06 }
}
```

## Output contract

`assets/3d/gen/<name>.glb`, CHECKED IN beside its spec. Every file carries: `hit.min`/
`hit.max` exactly at the authoritative envelope (ordered AABB — documented divergence from
the pack's corner-pair quirk, model.rs takes both); `cortex` empty exactly at the pose's
cortex_y (titans — accept.py asserts it EXISTS, because fit_to_class silently falls back
to hit-pair fit without it); honest `hook.*` empties on real drawn edges (remnants).
FRAME: drawn_poses are in the game-turned frame; a glb is authored pack-style facing +Z —
gen.py applies the inverse MODEL_FACES turn `(x,y,z) → (−x,y,−z)` to vertices AND anchors,
and accept.py verifies THROUGH `shared::model_turn`, never trusting the generator's own
composition (the one sign error nothing else would catch).

## Acceptance numbers (per class, at CLASS scale, ≥20 000 surface samples)

| class | flesh outside hit surface | registering air | extra |
|---|---|---|---|
| titan | ≤ 0.05 m (today 0.44) | ≤ 0.10 m (today ~0.52 u) | cortex within art.ron cortex_tolerance_m; stand height within class tolerance; facing via model_turn |
| remnant | zero samples outside envelope | hull-to-mesh median ≤ 0.05, worst ≤ 0.15 | centred on hit pair by construction |
| banner/prop | — | every plan-box face ≤ 0.10 m from drawn geometry | — |

All classes: glb_merge `preconditions()` pass · determinism (second run byte-identical) ·
spec sha in extras matches disk. Small-kind scale 0.4157 shrinks absolute error — check
tolerances at BOTH class scales for shared models.

## Sequencing

Wave 1 (parallel): A1 `glbout.py`+`geometry.py`+`gen.py` skeleton (evidence: a cube glb
that glb_merge --check accepts AND Bevy loads headless) · A2 `accept.py`+`ron_read.py`
(evidence: reproduces a-042's known-bad numbers). Wave 2: titan specs+bodies, then
banner+remnants. **Main head only**: art.ron source flips, titan.ron drawn_poses rows,
catalogue-test updates — one atomic swap per class (glb + art.ron + tests in ONE commit).
**Animations stay `{}`** — generated titans are static striding poses like today; clips
are a designed later round, not a promise of this one.
