#!/usr/bin/env python3
"""gen_static.py — remnant/prop generation from art.ron hulls rows (tools/models/README.md).

    python3 tools/models/gen_static.py [--check] tools/models/specs/<name>.json

The statics lane of the generator: models built FROM their `art.ron: hulls` rows, so the
drawn geometry is centred on the hit pair BY CONSTRUCTION — the mis-centring class (B-043)
cannot exist in a file whose triangles are extruded from the very boxes the game registers.
(A later chore merges this CLI into gen.py; both read glbout/geometry/ron_read only.)

WHAT IT BUILDS, per kind:
- remnant  every hulls wall box becomes a chamfered stone box (geometry.box, chamfer is a
           cut and stays inside), with a seeded inward face jitter — jitter shrinks, never
           grows, so `mesh ⊂ hull ⊂ envelope` holds by construction and the remnant gate's
           "zero samples outside the envelope" cannot be violated by style.
- prop     (banner-long) the hulls boxes are read by role — the full-height box is the
           pole, the rest are bracket bands — and a low-poly CLOTH slab is added filling
           the hulls' plan box, because the pack file draws none (B-043 honest residual,
           art.ron: "banner_long a pole with no cloth", p95 0.44 m iron-only). The cloth's
           front/back planes are placed so EVERY plan-box face keeps a drawn triangle
           within the README prop limit (0.10 m); the sway is silhouette only — hem curve,
           edge inset, a few mm of z-bow — sized to stay inside those margins.

FRAME: hulls rows are in the file's own authored metres, authored frame (art.ron hulls
header — they were read off the glb triangles directly; the quarter turn happens at
placement). So unlike drawn_poses there is NO MODEL_FACES turn here, and accept.py applies
none for remnants/props either.

ANCHORS: `hit.min`/`hit.max` are the ordered AABB of the AUTHORITATIVE hull boxes (not of
the jittered mesh) — the envelope contract. Honest `hook.*` empties sit on real drawn
geometry: the shrunk-and-chamfered top face of the tallest box, never on an analytic corner
the chamfer cut away.

DETERMINISM: the only randomness is `random.Random(spec["seed"])`, drawn in one fixed
order; a re-run with an unchanged spec is byte-identical (`--check` proves it without
writing).
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
KINDS = ("remnant", "prop")

# Cloth slab constants (prop). The README prop gate demands every plan-box face within
# LIMIT_PROP_FACE_M = 0.10 of drawn geometry; these offsets keep the worst perpendicular
# distance at 0.06 (front) / 0.09 (back) INCLUDING the sway amplitude, with the arithmetic
# spelled out at the build site below.
CLOTH_FRONT_OFF = 0.055  # front plane sits this far inside the envelope's -z face
CLOTH_BACK_OFF = 0.085  # back plane sits this far inside the envelope's +z face
CLOTH_SWAY_Z = 0.005  # z-bow amplitude (both planes together — the slab sways as one)
CLOTH_EDGE_INSET = 0.03  # mean edge inset; the edge curve is inset ± this again
CLOTH_HEM_BASE = 0.03  # mean hem height over the envelope floor
CLOTH_HEM_WAVE = 0.02  # hem curve amplitude (hem stays in 0.01..0.05)
CLOTH_COLS = 12
CLOTH_ROWS = 16


def hull_aabb(walls):
    lo = [min(w[0][a] for w in walls) for a in range(3)]
    hi = [max(w[1][a] for w in walls) for a in range(3)]
    return lo, hi


# ---------------------------------------------------------------------------
# remnant: chamfered, inward-jittered extrusions of the hull boxes
# ---------------------------------------------------------------------------


def build_remnant(spec: dict, walls, rng: random.Random):
    """One mesh part per hull box. Jitter is INWARD only (shrink), so the mesh can never
    leave the envelope; the ground face (a box floor at the envelope floor) is never
    jittered — a remnant does not hover."""
    detail = spec.get("detail", {})
    chamfer = float(detail.get("edge_break_m", 0.06))
    jitter = float(detail.get("jitter_m", 0.03))
    env_lo, env_hi = hull_aabb(walls)

    uv_stone = glbout.palette_uv(spec["palette"]["stone"])
    uv_rubble = glbout.palette_uv(spec["palette"].get("rubble", spec["palette"]["stone"]))
    uv_accent = glbout.palette_uv(spec["palette"].get("accent", spec["palette"]["stone"]))

    parts = []
    tallest_top, tallest = -1e9, None
    for lo, hi in walls:
        # fixed rng draw order per box: 6 face jitters, 1 chamfer factor, 1 colour pick
        j = [rng.uniform(0.0, jitter) for _ in range(6)]
        cf = rng.uniform(1.0, 1.5)
        pick = rng.random()
        if abs(lo[1] - env_lo[1]) < 1e-9:
            j[2] = 0.0  # the ground face stays on the ground
        slo = [lo[0] + j[0], lo[1] + j[2], lo[2] + j[4]]
        shi = [hi[0] - j[1], hi[1] - j[3], hi[2] - j[5]]
        size = [shi[a] - slo[a] for a in range(3)]
        # low spill boxes read as rubble; everything that carries height is stone
        low = hi[1] <= env_lo[1] + 1.05
        uv = (uv_rubble if pick < 0.7 else uv_accent) if low else uv_stone
        c = min(chamfer * cf, 0.08)
        part = geometry.box(size[0], size[1], size[2], uv=uv, edge_break_m=c)
        cx, cy, cz = [(slo[a] + shi[a]) / 2.0 for a in range(3)]
        parts.append(geometry.translate(part, cx, cy, cz))
        if shi[1] > tallest_top:
            tallest_top, tallest = shi[1], (slo, shi, c)

    # honest hooks: ON the drawn top face of the tallest (jittered, chamfered) box
    slo, shi, c = tallest
    tcx, tcz = (slo[0] + shi[0]) / 2.0, (slo[2] + shi[2]) / 2.0
    hooks = {
        "hook.crown": (tcx, shi[1], tcz),
        # midpoint of the top face's +x inset edge — on the face boundary the chamfer left
        "hook.crown_edge": (shi[0] - c, shi[1], tcz),
    }
    return parts, hooks


# ---------------------------------------------------------------------------
# prop: the banner — pole + brackets from the hulls, cloth filling the plan box
# ---------------------------------------------------------------------------


def build_banner(spec: dict, walls, rng: random.Random):
    """Pole and bracket boxes drawn exactly at their hull extents; a cloth slab hung from
    the envelope top to just over the floor, spanning the envelope width.

    THE MARGIN ARITHMETIC (against accept.py gate_prop, limit 0.10 m per face):
      -z face:  front plane at z_lo + 0.055, sway ±0.005      -> worst 0.060
      +z face:  back plane at z_hi - 0.085, sway ±0.005       -> worst 0.090
      ±x faces: cloth edge inset <= 0.06; sample z rows sit within 0.025 of the slab
                                                              -> worst ~0.065
      bottom:   hem in 0.01..0.05 over the floor, slab within 0.03 of both sample z rows
                                                              -> worst ~0.058
      top:      the upper bracket box spans the full envelope width to the envelope top.
    """
    detail = spec.get("detail", {})
    chamfer = float(detail.get("edge_break_m", 0.02))
    env_lo, env_hi = hull_aabb(walls)

    uv_cloth = glbout.palette_uv(spec["palette"]["cloth"])
    uv_pole = glbout.palette_uv(spec["palette"]["pole"])
    uv_bracket = glbout.palette_uv(spec["palette"]["bracket"])

    parts = []
    pole = None
    for lo, hi in walls:
        full_height = abs(lo[1] - env_lo[1]) < 1e-9 and abs(hi[1] - env_hi[1]) < 1e-9
        uv = uv_pole if full_height else uv_bracket
        size = [hi[a] - lo[a] for a in range(3)]
        part = geometry.box(size[0], size[1], size[2], uv=uv, edge_break_m=chamfer)
        center = [(lo[a] + hi[a]) / 2.0 for a in range(3)]
        parts.append(geometry.translate(part, *center))
        if full_height:
            pole = (lo, hi)
    if pole is None:
        sys.exit("gen_static.py: no full-height pole box in the hulls row")

    # ---- the cloth slab --------------------------------------------------------------
    z_lo, z_hi = env_lo[2], env_hi[2]
    front_base = z_lo + CLOTH_FRONT_OFF
    back_base = z_hi - CLOTH_BACK_OFF
    thickness = back_base - front_base
    if thickness < 0.03:
        sys.exit(
            f"gen_static.py: envelope depth {z_hi - z_lo:.3f} leaves cloth {thickness:.3f}"
        )
    p1, p2, p3, p4 = (rng.uniform(0.0, 2.0 * math.pi) for _ in range(4))
    y_top = env_hi[1]
    x_lo, x_hi = env_lo[0], env_hi[0]

    def inset(y):  # edge silhouette sway, 0..2*CLOTH_EDGE_INSET
        return CLOTH_EDGE_INSET * (1.0 + math.sin(2.0 * math.pi * y / 1.9 + p2))

    def hem(x):  # bottom hem curve over the envelope floor
        return env_lo[1] + CLOTH_HEM_BASE + CLOTH_HEM_WAVE * math.sin(
            2.0 * math.pi * x / 0.7 + p4
        )

    def z_front(x, y):  # a few mm of bow — silhouette, never a face-gate risk
        return front_base + CLOTH_SWAY_Z * 0.5 * (
            math.sin(2.0 * math.pi * y / 2.8 + p1) + math.sin(2.0 * math.pi * x / 1.1 + p3)
        )

    def corner(col, row, back):
        u = col / CLOTH_COLS
        # rows run hem (row 0) to top; y depends on x only through the hem row
        yl = hem(x_lo + (x_hi - x_lo) * u)
        y = yl + (y_top - yl) * (row / CLOTH_ROWS)
        half_in = inset(y)
        x = (x_lo + half_in) + ((x_hi - half_in) - (x_lo + half_in)) * u
        z = z_front(x, y) + (thickness if back else 0.0)
        return (x, y, z)

    cloth = geometry._new()

    def quad(a, b, c, d):
        cx = sum(p[0] for p in (a, b, c, d)) / 4.0
        cy = sum(p[1] for p in (a, b, c, d)) / 4.0
        cz = sum(p[2] for p in (a, b, c, d)) / 4.0
        # local interior: the slab's own mid-plane behind this face
        mid_z = (z_front(cx, cy) + z_front(cx, cy) + thickness) / 2.0
        geometry._emit(cloth, [a, b, c, d], uv_cloth, (cx, cy, mid_z))

    for col in range(CLOTH_COLS):
        for row in range(CLOTH_ROWS):
            f00, f10 = corner(col, row, False), corner(col + 1, row, False)
            f01, f11 = corner(col, row + 1, False), corner(col + 1, row + 1, False)
            b00, b10 = corner(col, row, True), corner(col + 1, row, True)
            b01, b11 = corner(col, row + 1, True), corner(col + 1, row + 1, True)
            quad(f00, f10, f11, f01)  # front
            quad(b00, b10, b11, b01)  # back
            if row == 0:
                quad(f00, f10, b10, b00)  # hem rim
            if row == CLOTH_ROWS - 1:
                quad(f01, f11, b11, b01)  # top rim
            if col == 0:
                quad(f00, f01, b01, b00)  # left rim
            if col == CLOTH_COLS - 1:
                quad(f10, f11, b11, b10)  # right rim
    parts.append(cloth)

    plo, phi = pole
    hooks = {"hook.top": ((plo[0] + phi[0]) / 2.0, phi[1], (plo[2] + phi[2]) / 2.0)}
    return parts, hooks


# ---------------------------------------------------------------------------
# CLI (gen.py's shape: --check compares a regeneration against the file on disk)
# ---------------------------------------------------------------------------


def generate(spec_path: Path) -> tuple[bytes, Path, str]:
    raw = spec_path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    spec = json.loads(raw)

    missing = [k for k in REQUIRED_KEYS if k not in spec]
    if missing:
        sys.exit(f"gen_static.py: {spec_path.name} is missing the required key(s) {missing}")
    if spec["kind"] not in KINDS:
        sys.exit(f"gen_static.py: kind {spec['kind']!r} is not one of {KINDS} (titans: gen.py)")

    pointer = spec["geometry"]
    if not pointer.startswith("art.ron:hulls/"):
        sys.exit(f"gen_static.py: geometry {pointer!r} — this CLI resolves art.ron:hulls/* only")
    hull_name = pointer.split("/", 1)[1]
    hull = ron_read.hull(hull_name)
    if hull["roof_rects"]:
        sys.exit(f"gen_static.py: hulls/{hull_name} has roof_rects — not a statics shape")
    walls = hull["walls"]

    rng = random.Random(int(spec["seed"]))
    if spec["kind"] == "remnant":
        parts, hooks = build_remnant(spec, walls, rng)
    else:
        parts, hooks = build_banner(spec, walls, rng)

    # the envelope is the AUTHORITATIVE hulls AABB — by construction, not by measurement
    env_lo, env_hi = hull_aabb(walls)

    writer = glbout.Writer(
        generator=f"dbt-gen-static {VERSION}",
        extras={"generator_version": VERSION, "spec_sha256": sha},
    )
    writer.add_mesh(spec["name"], *geometry.combine(parts))
    writer.add_empty("hit.min", tuple(env_lo))
    writer.add_empty("hit.max", tuple(env_hi))
    for name, xyz in hooks.items():
        writer.add_empty(name, xyz)

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
        if out_path.read_bytes() != data:
            print(f"CHECK FAILED: {out_path} differs from a regeneration")
            return 1
        print(f"check ok: {out_path} is byte-identical to a regeneration (spec sha {sha[:12]})")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    print(f"wrote {out_path} ({len(data)} bytes, spec sha {sha[:12]}, generator {VERSION})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
