#!/usr/bin/env python3
"""gen.py — the CLI of the model generator (tools/models/README.md).

    python3 tools/models/gen.py [--check] tools/models/specs/<name>.json

DETERMINISTIC by contract: the only randomness is `random.Random(spec["seed"])`, there
is no wall clock anywhere, and a re-run with an unchanged spec is byte-identical —
`--check` regenerates in memory and compares against the file on disk, writing nothing.

Every produced file carries the generator version and the sha256 of the spec BYTES in
glTF `asset.extras`, so a stale glb is detectable without opening Blender.

WHAT THIS SKELETON RESOLVES: the `demo:` geometry scheme (a self-contained test body —
capsule loft torso on a chamfered box pedestal with a wedge crest, one combined mesh).
The real schemes `titan.ron:drawn_poses/...` and `art.ron:hulls/...` go through
`ron_read.py` (wave 1 lane A2) and land in wave 2 — asking for one today exits with
that message instead of guessing at numbers (README rule 5: a spec never copies
geometry numbers, the generator READS the authoritative source).

FRAME: geometry is composed in the game frame (+Z forward, feet at y=0, drawn_poses
convention) and then turned into the pack's authoring frame with the inverse
MODEL_FACES turn `(x, y, z) -> (-x, y, -z)` — applied to vertices, normals AND
anchors, so the game's `shared::model_turn` (a pi turn about Y, self-inverse) brings
everything back. `hit.min`/`hit.max` are re-ordered per axis after the turn: the
output contract is an ORDERED AABB (documented divergence from the pack's corner-pair
quirk; model.rs takes both).
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import geometry  # noqa: E402
import glbout  # noqa: E402

VERSION = "0.1.0"
ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "assets" / "3d" / "gen"

REQUIRED_KEYS = ("name", "geometry", "kind", "seed", "facets", "palette")
KINDS = ("titan", "remnant", "prop")


def model_turn(x: float, y: float, z: float) -> tuple[float, float, float]:
    """The inverse of shared::MODEL_FACES (a pi turn about Y — self-inverse)."""
    return (-x, y, -z)


def turn_mesh(mesh: geometry.Mesh) -> geometry.Mesh:
    verts, normals, uvs, indices = mesh
    tv, tn = list(verts), list(normals)
    for i in range(0, len(tv), 3):
        tv[i], tv[i + 1], tv[i + 2] = model_turn(tv[i], tv[i + 1], tv[i + 2])
        tn[i], tn[i + 1], tn[i + 2] = model_turn(tn[i], tn[i + 1], tn[i + 2])
    return (tv, tn, list(uvs), list(indices))


def palette_key(spec_value: str) -> str:
    """A spec palette value is a key or a `a..b` gradient. The skeleton paints the
    FIRST stop flat; the gradient ramp is a wave-2 styling concern, not a geometry one."""
    return spec_value.split("..", 1)[0]


def build_demo_capsule(spec: dict) -> tuple[list[geometry.Mesh], dict]:
    """The self-contained demo body, in the game frame, feet at y = 0.

    Fixed dimensions (a demo is a fixture, not a spec surface): capsule r 0.5 m with a
    1.0 m cylinder, standing on a 0.8 x 0.3 x 0.8 pedestal, a 0.4 x 0.25 x 0.5 wedge
    crest whose slope falls toward +Z — so a wrong MODEL_FACES turn is VISIBLE, not
    just measurable. Returns the parts and the analytic hit envelope (game frame)."""
    n = int(spec["facets"]["torso"])
    edge_break = float(spec.get("detail", {}).get("edge_break_m", 0.0))
    skin = glbout.palette_uv(palette_key(spec["palette"]["skin"]))
    trim = glbout.palette_uv(palette_key(spec["palette"].get("trim", "roof_slate")))

    r, cyl = 0.5, 1.0
    ped = (0.8, 0.3, 0.8)
    crest = (0.4, 0.25, 0.5)

    pedestal = geometry.translate(
        geometry.box(*ped, uv=trim, edge_break_m=edge_break), 0.0, ped[1] / 2.0, 0.0
    )
    torso_y = ped[1] + r + cyl / 2.0
    torso = geometry.translate(geometry.capsule(r, cyl, n, uv=skin), 0.0, torso_y, 0.0)
    crest_y = ped[1] + cyl + 2.0 * r + crest[1] / 2.0
    top = geometry.translate(geometry.wedge(*crest, uv=trim), 0.0, crest_y, 0.0)

    envelope = {
        "min": (-r, 0.0, -r),
        "max": (r, ped[1] + cyl + 2.0 * r + crest[1], r),
    }
    return [pedestal, torso, top], envelope


def generate(spec_path: Path) -> tuple[bytes, Path, str]:
    """The GLB bytes, the output path and the spec sha for one spec file."""
    raw = spec_path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    spec = json.loads(raw)

    missing = [k for k in REQUIRED_KEYS if k not in spec]
    if missing:
        sys.exit(f"gen.py: {spec_path.name} is missing the required key(s) {missing}")
    if spec["kind"] not in KINDS:
        sys.exit(f"gen.py: kind {spec['kind']!r} is not one of {KINDS}")

    rng = random.Random(int(spec["seed"]))  # the ONLY randomness source; style jitter
    _ = rng  # is a wave-2 concern — the handle exists so no one reaches for the clock

    pointer = spec["geometry"]
    if pointer.startswith(("titan.ron:", "art.ron:")):
        sys.exit(
            f"gen.py: geometry {pointer!r} needs ron_read.py (wave 1 lane A2) — "
            "authoritative-geometry resolution lands in wave 2, a spec never copies "
            "those numbers (README rule 5)."
        )
    if pointer != "demo:capsule":
        sys.exit(f"gen.py: unknown geometry scheme {pointer!r}")

    parts, envelope = build_demo_capsule(spec)
    body = turn_mesh(geometry.combine(parts))

    lo = model_turn(*envelope["min"])
    hi = model_turn(*envelope["max"])
    hit_min = tuple(min(a, b) for a, b in zip(lo, hi))  # ordered AABB, per axis
    hit_max = tuple(max(a, b) for a, b in zip(lo, hi))

    writer = glbout.Writer(
        generator=f"dbt-gen {VERSION}",
        extras={"generator_version": VERSION, "spec_sha256": sha},
    )
    writer.add_mesh(spec["name"], *body)
    writer.add_empty("hit.min", hit_min)
    writer.add_empty("hit.max", hit_max)
    if spec["kind"] == "titan":
        sys.exit("gen.py: a titan needs its cortex from titan.ron drawn_poses — wave 2")

    return writer.bytes(), OUT_DIR / f"{spec['name']}.glb", sha


def main(argv: list[str]) -> int:
    check = "--check" in argv
    paths = [Path(a) for a in argv if not a.startswith("--")]
    if len(paths) != 1:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2

    data, out_path, sha = generate(paths[0])
    if check:
        if not out_path.exists():
            print(f"CHECK FAILED: {out_path} does not exist")
            return 1
        on_disk = out_path.read_bytes()
        if on_disk != data:
            print(
                f"CHECK FAILED: {out_path} differs from a regeneration "
                f"({len(on_disk)} vs {len(data)} bytes) — the spec or the generator moved"
            )
            return 1
        print(f"check ok: {out_path} is byte-identical to a regeneration (spec sha {sha[:12]})")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    print(f"wrote {out_path} ({len(data)} bytes, spec sha {sha[:12]}, generator {VERSION})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
