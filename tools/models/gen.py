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
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import geometry  # noqa: E402
import glbout  # noqa: E402
import ron_read  # noqa: E402

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


def mottled(rng: random.Random, base_uv, alt_uv, p: float):
    """A per-face palette callable: `alt_uv` with probability `p`, else `base_uv`.
    Deterministic because `rng` is the spec-seeded generator and geometry.py draws it
    exactly once per emitted face in a fixed order."""
    if p <= 0.0:
        return base_uv
    return lambda: alt_uv if rng.random() < p else base_uv


def build_titan(spec: dict, rng: random.Random, pose_name: str) -> tuple[list, dict, dict]:
    """The titan geometry scheme: one faceted capsule per drawn_poses capsule, PLUS the
    rig's neck capsule (the same union `accept.py` and `tools/fleet/verify_caps.py`
    register — src/titan/rig.rs registers pose capsules AND a neck segment, so a body
    without drawn neck flesh would carry 0.24+ units of registering air on it).

    The neck derivation MIRRORS accept.py's (both read the same scale.ron fractions and
    class row — one authoritative source, two readers, per README rule 5):
        fit = cortex_height_m / cortex_y · head_m = H·(1 − leg_f − torso_f)
        neck_r = head_m / 2 / fit · neck from (0, sh_f·H/fit − r, 0) to (0, H/fit − r, 0)

    Style on top, inside the honesty band:
    - Cortex-side band: a darker RECESSED ring on the neck at cortex height. The recess is a
      cut inward (flesh-safe by construction); depth 0.02 u eats into the air budget,
      which the gate measures.
    - eyes: dark cells as tiles a few millimetres proud of the head wall, corners inside
      the flesh band.
    - mottle: per-face second skin tone from the spec's `a..b` palette gradient.

    Returns (parts, envelope, anchors) in the GAME frame (+z backwards, y from ground).
    """
    pose = ron_read.drawn_pose(pose_name)
    size = spec.get("size_class")
    if size is None:
        sys.exit(
            f"gen.py: a titan spec needs `size_class` (a scale.ron class name) — the "
            f"neck capsule and the Cortex-side-band height depend on it, and a silent default "
            f"would be a game value in disguise ({spec['name']})"
        )
    H, CY = ron_read.size_class(size)
    fit = CY / pose["cortex_y"]
    leg_f = ron_read.fraction("leg_fraction")
    torso_f = ron_read.fraction("torso_fraction")
    sh_f = ron_read.fraction("shoulder_height_fraction")
    head_m = H * (1.0 - leg_f - torso_f)
    neck_r = head_m / 2.0 / fit
    neck_a = (0.0, sh_f * H / fit - neck_r, 0.0)
    neck_b = (0.0, H / fit - neck_r, 0.0)

    facets = spec["facets"]
    n_torso = int(facets["torso"])
    n_limb = int(facets["limb"])
    detail = spec.get("detail", {})

    skin_lo, _, skin_hi = spec["palette"]["skin"].partition("..")
    base_uv = glbout.palette_uv(skin_lo)
    alt_uv = glbout.palette_uv(skin_hi) if skin_hi else base_uv
    mottle_p = float(detail.get("mottle", 0.0))
    skin = mottled(rng, base_uv, alt_uv, mottle_p)
    band_uv = glbout.palette_uv(palette_key(spec["palette"].get("nape_band", "roof_slate")))
    eye_uv = glbout.palette_uv(palette_key(spec["palette"].get("eyes", "char_black")))

    parts: list[geometry.Mesh] = []
    head_cap = None
    for c in pose["capsules"]:
        n = n_torso if c["part"] in ("torso", "head") else n_limb
        parts.append(geometry.capsule_between(c["a"], c["b"], c["radius"], n, uv=skin))
        if c["part"] == "head":
            head_cap = c

    # the neck, with the Cortex-side band recessed at the pose's cortex height
    bands = ()
    if detail.get("nape_band", False):
        half_w = float(detail.get("nape_band_half_w", 0.15))
        recess = float(detail.get("nape_band_recess", 0.02))
        neck_len = neck_b[1] - neck_a[1]
        lo = max(0.0, pose["cortex_y"] - half_w - neck_a[1])
        hi = min(neck_len, pose["cortex_y"] + half_w - neck_a[1])
        if lo >= hi:
            sys.exit(
                f"gen.py: Cortex-side band at cortex_y {pose['cortex_y']} misses the neck "
                f"({neck_a[1]:.2f}..{neck_b[1]:.2f}) — the pose or the class is wrong"
            )
        bands = ((lo, hi, 1.0 - recess / neck_r, band_uv),)
    parts.append(
        geometry.capsule_between(neck_a, neck_b, neck_r, n_torso, uv=skin, bands=bands)
    )

    # the painted cortex plate: the aim cue the a-042 Cortex-side carries (an amber rectangle on
    # the back of the neck — the rig's own cortex sphere is hidden once a glb dresses the
    # titan, so a generated body must paint its own). +z is BACKWARDS in the game frame,
    # so azimuth 0 (+z) faces the viewer who stands behind the Cortex-side.
    if detail.get("cortex_plate", True) and bands:
        plate_uv = glbout.palette_uv(palette_key(spec["palette"].get("cortex_plate", "gold_ochre")))
        plate_half_h = float(detail.get("cortex_plate_half_h", 0.30))
        plate_az = float(detail.get("cortex_plate_az_half", 0.42))
        proud_r = neck_r * (1.0 + geometry.mid_radius_band(n_torso)) + 0.004
        parts.append(
            geometry.cylinder_patch(
                0.0,
                pose["cortex_y"] - plate_half_h,
                pose["cortex_y"] + plate_half_h,
                0.0,
                proud_r,
                0.0,
                plate_az,
                plate_uv,
            )
        )

    if detail.get("eyes", True) and head_cap is not None:
        a, b, r = head_cap["a"], head_cap["b"], head_cap["radius"]
        f = tuple(b[i] - a[i] for i in range(3))
        L = math.sqrt(sum(x * x for x in f))
        f = tuple(x / L for x in f)
        right = (-f[2], 0.0, f[0])  # cross(up, forward) for forward mostly -z: +x-ish
        Lr = math.sqrt(sum(x * x for x in right)) or 1.0
        right = tuple(x / Lr for x in right)
        size_u = float(detail.get("eye_size_u", 0.14))
        spread = float(detail.get("eye_spread", 0.45))
        lift = float(detail.get("eye_lift", 0.12))
        for s in (-1.0, 1.0):
            d = tuple(f[i] + s * spread * right[i] + lift * (0.0, 1.0, 0.0)[i] for i in range(3))
            Ld = math.sqrt(sum(x * x for x in d))
            d = tuple(x / Ld for x in d)
            proud = r * geometry.mid_radius_band(n_torso) + 0.004
            center = tuple(b[i] + d[i] * (r + proud) for i in range(3))
            parts.append(geometry.tile(center, d, (0.0, 1.0, 0.0), size_u, size_u * 0.75, eye_uv))

    # the authoritative envelope: the analytic AABB of the registered capsule union
    caps = [(c["a"], c["b"], c["radius"]) for c in pose["capsules"]]
    caps.append((neck_a, neck_b, neck_r))
    lo3 = [min(min(a[i], b[i]) - r for (a, b, r) in caps) for i in range(3)]
    hi3 = [max(max(a[i], b[i]) + r for (a, b, r) in caps) for i in range(3)]
    envelope = {"min": tuple(lo3), "max": tuple(hi3)}

    # the cortex empty: the pose's cortex_y on the model's centre line, at the BACK of
    # the neck (+z is backwards in the game frame; src/titan/rig.rs clamps depth to at
    # least head_m/2 anyway, and holds x to the centre line — F-030)
    anchors = {"cortex": (0.0, pose["cortex_y"], neck_r)}
    return parts, envelope, anchors


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

    rng = random.Random(int(spec["seed"]))  # the ONLY randomness source

    pointer = spec["geometry"]
    anchors: dict = {}
    if pointer.startswith("titan.ron:drawn_poses/"):
        if spec["kind"] != "titan":
            sys.exit(f"gen.py: a drawn_poses geometry is a titan, not {spec['kind']!r}")
        parts, envelope, anchors = build_titan(spec, rng, pointer.split("/", 1)[1])
    elif pointer.startswith("art.ron:"):
        sys.exit(
            f"gen.py: geometry {pointer!r} — the remnant/prop scheme is another lane's "
            "(A4); this generator resolves demo: and titan.ron:drawn_poses/ today."
        )
    elif pointer == "demo:capsule":
        parts, envelope = build_demo_capsule(spec)
    else:
        sys.exit(f"gen.py: unknown geometry scheme {pointer!r}")

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
    for name, xyz in anchors.items():
        writer.add_empty(name, model_turn(*xyz))
    if spec["kind"] == "titan" and "cortex" not in anchors:
        sys.exit("gen.py: a titan without a cortex empty must never be written")

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
