#!/usr/bin/env python3
"""accept.py — the acceptance gate for generated models (tools/models/README.md).

    python3 tools/models/accept.py FILE.glb --geometry titan.ron:drawn_poses/titan_husk \
        [--kind titan|remnant|prop] [--class medium] [--samples 20000] [--spec spec.json]

Nonzero exit on ANY breach of the README acceptance table; one table row per metric.

WHAT IT MEASURES, per class (all at class scale, >= 20 000 surface samples):
- titan:   flesh outside the nearest registered capsule (max, p99) — the capsule set is the
           titan.ron drawn_poses row PLUS the rig's neck segment (src/titan/rig.rs registers
           both; tools/fleet/verify_caps.py measured the recorded numbers against exactly
           that union) · registering air over every capsule surface (worst) · cortex empty
           EXISTS (render::model::fit_to_class silently falls back to hit-pair fit without
           it) and sits at the pose's cortex_y · stand height within art.ron's
           cortex_tolerance_m (the same yardstick src/render/model.rs holds a loaded body
           against) · facing sign THROUGH shared::model_turn.
- remnant: mesh samples outside the authored hit envelope (must be ZERO) · compound hull
           surface to nearest drawn triangle (median, worst).
- prop:    every hit-envelope (plan box) face's worst distance to drawn geometry.
All classes: glb_merge preconditions() pass · spec sha256 in asset.extras matches disk
(when --spec names the spec).

FRAMES (tools/models/README.md, titan.ron B-042 header, art.ron hulls header):
- drawn_poses rows are GAME-TURNED; a glb is authored pack-style facing +Z. This gate turns
  the authored mesh into the game frame itself, by the angle it READS out of
  src/shared/anchors.rs (ron_read.model_faces_rad) — it never trusts a generator's own
  composition, because a sign error there is exactly the bug nothing else would catch.
  The turn arithmetic is tools/fleet/glb_slice.py's: rotation about +Y, game z = -authored z
  at MODEL_FACES = pi.
- hulls rows are in the file's own authored metres and authored frame (the placement turn
  is world::map's, not the file's) — no turn for remnants and props.

INSTRUMENT LINEAGE — why two different distance instruments:
- "registering air" uses nearest-MESH-SAMPLE distance on a 0.4-cell grid, the verbatim
  tools/fleet/verify_caps.py instrument that produced the recorded a-042 numbers
  (0.52 units / 1.04 m worst); same instrument, so the known-bad proof is a reproduction,
  not a coincidence. Mesh sampling is fit_caps.py's fixed 10-barycentric-points-per-triangle
  pattern, topped up area-weighted (seeded) to the sample floor.
- hull-to-mesh and plan-box-to-mesh use EXACT point-to-triangle distance (a hull face can
  sit far from any mesh vertex, and a sample-to-sample distance would flatter it).

Worst case of the instrument (docs/lessons/fixtures.md rule 6): a glb with no triangles or
no cortex FAILS loudly with the counts printed — it is never a silent pass. Python stdlib
only (tools/glb_merge.py precedent).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import random
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import ron_read  # noqa: E402

_spec = importlib.util.spec_from_file_location("glb_merge", ROOT / "tools" / "glb_merge.py")
glb_merge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(glb_merge)

MIN_SAMPLES = 20_000
# The acceptance table, tools/models/README.md (metres at class scale).
LIMIT_TITAN_FLESH_M = 0.05
LIMIT_TITAN_AIR_M = 0.10
LIMIT_REMNANT_OUTSIDE = 0  # samples
LIMIT_REMNANT_MEDIAN_M = 0.05
LIMIT_REMNANT_WORST_M = 0.15
LIMIT_PROP_FACE_M = 0.10
FACING_SLACK_U = 0.02  # units; the wrong sign must not be measurably better

# fit_caps.py's fixed barycentric pattern — the instrument the recorded numbers used.
BARY = [(1, 0), (0, 1), (0, 0), (1 / 3, 1 / 3), (0.5, 0.5), (0.5, 0), (0, 0.5),
        (0.25, 0.25), (0.25, 0.5), (0.5, 0.25)]


# ---------------------------------------------------------------------------
# vectors
# ---------------------------------------------------------------------------

def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def mul(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def norm(a): return math.sqrt(dot(a, a))


def seg_dist(p, a, b):
    ab = sub(b, a)
    t = dot(sub(p, a), ab) / max(dot(ab, ab), 1e-12)
    t = max(0.0, min(1.0, t))
    return norm(sub(p, add(a, mul(ab, t))))


def tri_dist(p, a, b, c):
    """Exact distance from point to triangle (Ericson, Real-Time Collision Detection)."""
    ab = sub(b, a); ac = sub(c, a); ap = sub(p, a)
    d1 = dot(ab, ap); d2 = dot(ac, ap)
    if d1 <= 0 and d2 <= 0:
        return norm(ap)
    bp = sub(p, b); d3 = dot(ab, bp); d4 = dot(ac, bp)
    if d3 >= 0 and d4 <= d3:
        return norm(bp)
    vc = d1 * d4 - d3 * d2
    if vc <= 0 <= d1 and d3 <= 0:
        v = d1 / (d1 - d3)
        return norm(sub(p, add(a, mul(ab, v))))
    cp = sub(p, c); d5 = dot(ab, cp); d6 = dot(ac, cp)
    if d6 >= 0 and d5 <= d6:
        return norm(cp)
    vb = d5 * d2 - d1 * d6
    if vb <= 0 <= d2 and d6 <= 0:
        w = d2 / (d2 - d6)
        return norm(sub(p, add(a, mul(ac, w))))
    va = d3 * d6 - d5 * d4
    if va <= 0 and d4 - d3 >= 0 and d5 - d6 >= 0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return norm(sub(p, add(b, mul(sub(c, b), w))))
    den = 1.0 / (va + vb + vc)
    v = vb * den; w = vc * den
    q = add(a, add(mul(ab, v), mul(ac, w)))
    return norm(sub(p, q))


# ---------------------------------------------------------------------------
# glb -> world-space triangles + anchors (tools/fleet/glb_slice.py walker)
# ---------------------------------------------------------------------------

def _read_accessor(g, binchunk, idx):
    acc = g['accessors'][idx]
    bv = g['bufferViews'][acc['bufferView']]
    ncomp = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[acc['type']]
    fmt = {5126: 'f', 5123: 'H', 5125: 'I', 5121: 'B', 5122: 'h', 5120: 'b'}[acc['componentType']]
    size = struct.calcsize(fmt)
    start = bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
    stride = bv.get('byteStride', ncomp * size)
    return [struct.unpack_from('<' + fmt * ncomp, binchunk, start + i * stride)
            for i in range(acc['count'])]


def _node_matrix(n):
    if 'matrix' in n:
        m = n['matrix']
        return [[m[0], m[4], m[8], m[12]], [m[1], m[5], m[9], m[13]],
                [m[2], m[6], m[10], m[14]], [m[3], m[7], m[11], m[15]]]
    t = n.get('translation', [0, 0, 0]); r = n.get('rotation', [0, 0, 0, 1]); s = n.get('scale', [1, 1, 1])
    x, y, z, w = r
    R = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    M = [[R[i][j] * s[j] for j in range(3)] + [t[i]] for i in range(3)]
    M.append([0, 0, 0, 1])
    return M


def _matmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def _xform(m, v):
    return tuple(m[i][0] * v[0] + m[i][1] * v[1] + m[i][2] * v[2] + m[i][3] for i in range(3))


def collect(path: Path):
    """(doc, verts, tris, anchors) — verts world-space authored frame, tris index triples."""
    doc, binary = glb_merge.read_glb(path.read_bytes())
    verts, tris, anchors = [], [], {}
    ident = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    nodes = doc.get('nodes', [])

    def walk(idx, parent_m):
        n = nodes[idx]
        m = _matmul(parent_m, _node_matrix(n))
        if 'mesh' not in n and n.get('name'):
            anchors[n['name']] = (m[0][3], m[1][3], m[2][3])
        if 'mesh' in n:
            for prim in doc['meshes'][n['mesh']]['primitives']:
                if 'POSITION' not in prim['attributes']:
                    continue
                base = len(verts)
                for v in _read_accessor(doc, binary, prim['attributes']['POSITION']):
                    verts.append(_xform(m, v))
                if 'indices' in prim:
                    idxs = [i[0] for i in _read_accessor(doc, binary, prim['indices'])]
                else:
                    idxs = list(range(len(verts) - base))
                tris.extend((base + idxs[k], base + idxs[k + 1], base + idxs[k + 2])
                            for k in range(0, len(idxs) - 2, 3))
        for c in n.get('children', []):
            walk(c, m)

    if doc.get('scenes'):
        for root in doc['scenes'][doc.get('scene', 0)].get('nodes', []):
            walk(root, ident)
    return doc, verts, tris, anchors


def surface_samples(verts, tris, floor=MIN_SAMPLES):
    """fit_caps.py's fixed 10-per-triangle pattern, topped up area-weighted to `floor`."""
    samples = []
    areas = []
    for (i, j, k) in tris:
        A, B, C = verts[i], verts[j], verts[k]
        for (u, v) in BARY:
            w = 1 - u - v
            samples.append((A[0] * u + B[0] * v + C[0] * w,
                            A[1] * u + B[1] * v + C[1] * w,
                            A[2] * u + B[2] * v + C[2] * w))
        ab, ac = sub(B, A), sub(C, A)
        cx = (ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2],
              ab[0] * ac[1] - ab[1] * ac[0])
        areas.append(0.5 * norm(cx))
    total = sum(areas)
    if samples and total > 0 and len(samples) < floor:
        rng = random.Random(1)  # deterministic — re-run is identical
        acc, cum = 0.0, []
        for a in areas:
            acc += a
            cum.append(acc)
        for _ in range(floor - len(samples)):
            r = rng.random() * total
            lo, hi = 0, len(cum) - 1
            while lo < hi:
                mid = (lo + hi) // 2
                if cum[mid] < r: lo = mid + 1
                else: hi = mid
            i, j, k = tris[lo]
            A, B, C = verts[i], verts[j], verts[k]
            u, v = rng.random(), rng.random()
            if u + v > 1: u, v = 1 - u, 1 - v
            w = 1 - u - v
            samples.append((A[0] * u + B[0] * v + C[0] * w,
                            A[1] * u + B[1] * v + C[1] * w,
                            A[2] * u + B[2] * v + C[2] * w))
    return samples


# ---------------------------------------------------------------------------
# spatial grids
# ---------------------------------------------------------------------------

class PointGrid:
    """verify_caps.py's nearest-mesh-sample grid, cell 0.4 (the recorded instrument)."""

    def __init__(self, points, cell=0.4):
        self.cell = cell
        self.grid = {}
        for s in points:
            self.grid.setdefault((int(s[0] // cell), int(s[1] // cell), int(s[2] // cell)),
                                 []).append(s)

    def nearest(self, p, max_rad=12):
        best = 9e9
        c = self.cell
        ci, cj, ck = int(p[0] // c), int(p[1] // c), int(p[2] // c)
        for rad in range(1, max_rad):
            for i in range(ci - rad, ci + rad + 1):
                for j in range(cj - rad, cj + rad + 1):
                    for k in range(ck - rad, ck + rad + 1):
                        for s in self.grid.get((i, j, k), []):
                            d = norm(sub(p, s))
                            if d < best: best = d
            if best < (rad - 1) * c:
                break
        return best


class TriGrid:
    """Exact point-to-triangle nearest distance, triangles binned by their AABB."""

    def __init__(self, verts, tris, cell=0.5):
        self.cell = cell
        self.verts = verts
        self.tris = tris
        self.grid = {}
        for t, (i, j, k) in enumerate(tris):
            ps = (verts[i], verts[j], verts[k])
            lo = [min(p[a] for p in ps) for a in range(3)]
            hi = [max(p[a] for p in ps) for a in range(3)]
            for x in range(int(lo[0] // cell), int(hi[0] // cell) + 1):
                for y in range(int(lo[1] // cell), int(hi[1] // cell) + 1):
                    for z in range(int(lo[2] // cell), int(hi[2] // cell) + 1):
                        self.grid.setdefault((x, y, z), []).append(t)

    def nearest(self, p, max_rad=24):
        best = 9e9
        c = self.cell
        ci, cj, ck = int(p[0] // c), int(p[1] // c), int(p[2] // c)
        seen = set()
        for rad in range(1, max_rad):
            for i in range(ci - rad, ci + rad + 1):
                for j in range(cj - rad, cj + rad + 1):
                    for k in range(ck - rad, ck + rad + 1):
                        for t in self.grid.get((i, j, k), []):
                            if t in seen: continue
                            seen.add(t)
                            a, b, cc = (self.verts[v] for v in self.tris[t])
                            d = tri_dist(p, a, b, cc)
                            if d < best: best = d
            if best < (rad - 1) * c:
                break
        return best


# ---------------------------------------------------------------------------
# the report
# ---------------------------------------------------------------------------

class Report:
    def __init__(self):
        self.failed = False
        print(f"{'metric':44s} {'value':>12s} {'limit':>12s}  verdict")

    def row(self, metric, value, limit, ok, note=""):
        if not ok:
            self.failed = True
        v = value if isinstance(value, str) else f"{value:.3f}"
        print(f"{metric:44s} {v:>12s} {str(limit):>12s}  {'PASS' if ok else 'FAIL'}"
              + (f"  {note}" if note else ""))

    def fail(self, metric, why):
        self.failed = True
        print(f"{metric:44s} {'—':>12s} {'—':>12s}  FAIL  {why}")


def model_turned(points, theta):
    """Rotation about +Y by theta — glb_slice.py's turn arithmetic, angle READ from shared."""
    c, s = math.cos(theta), math.sin(theta)
    return [(p[0] * c + p[2] * s, p[1], -p[0] * s + p[2] * c) for p in points]


# ---------------------------------------------------------------------------
# per-class gates
# ---------------------------------------------------------------------------

def flesh_outside(samples, caps):
    """Sorted list of (min over capsules of surface distance) per mesh sample."""
    outs = []
    for s in samples:
        outs.append(min(seg_dist(s, a, b) - r for (a, b, r) in caps))
    outs.sort()
    return outs


def capsule_surface_points(a, b, r, rings=12, spokes=16):
    """verify_caps.py's ring sampling of one capsule's lateral surface."""
    ax = sub(b, a)
    L = norm(ax)
    ax = mul(ax, 1 / max(L, 1e-9))
    up = (0, 1, 0) if abs(ax[1]) < 0.9 else (1, 0, 0)
    u = (ax[1] * up[2] - ax[2] * up[1], ax[2] * up[0] - ax[0] * up[2], ax[0] * up[1] - ax[1] * up[0])
    u = mul(u, 1 / norm(u))
    v = (ax[1] * u[2] - ax[2] * u[1], ax[2] * u[0] - ax[0] * u[2], ax[0] * u[1] - ax[1] * u[0])
    pts = []
    for ti in range(rings):
        t = ti / (rings - 1)
        c = add(a, mul(sub(b, a), t))
        for gi in range(spokes):
            ang = gi / spokes * 2 * math.pi
            pts.append(add(c, add(mul(u, r * math.cos(ang)), mul(v, r * math.sin(ang)))))
    return pts


def gate_titan(rep, samples, anchors, pose_name, size_name):
    pose = ron_read.drawn_pose(pose_name)
    H, CY = ron_read.size_class(size_name)
    tol_m = ron_read.cortex_tolerance_m()
    theta = ron_read.model_faces_rad()

    cortex = anchors.get('cortex')
    if cortex is None:
        rep.fail("cortex empty exists",
                 "MISSING — fit_to_class silently falls back to hit-pair fit")
        return
    rep.row("cortex empty exists", "yes", "required", True)

    # into the game frame, through shared's turn — never the generator's own composition
    game = model_turned(samples, theta)
    cg = model_turned([cortex], theta)[0]
    fit = CY / cg[1]
    print(f"# class {size_name}: height {H} m, cortex {CY} m; cortex anchor y {cg[1]:.4f} u "
          f"-> fit {fit:.4f} m/u; turn {theta:.4f} rad (src/shared/anchors.rs)")

    caps = [(c['a'], c['b'], c['radius']) for c in pose['capsules']]
    # the rig's neck segment stays registered (verify_caps.py derivation, scale.ron numbers)
    leg_f = ron_read.fraction('leg_fraction')
    torso_f = ron_read.fraction('torso_fraction')
    sh_f = ron_read.fraction('shoulder_height_fraction')
    head_m = H - leg_f * H - torso_f * H
    neck_r = head_m / 2 / fit
    caps.append(((0, sh_f * H / fit - neck_r, 0), (0, H / fit - neck_r, 0), neck_r))
    names = [c['part'] for c in pose['capsules']] + ['neck(rig)']

    rep.row("cortex y vs pose cortex_y [m]", abs(cg[1] - pose['cortex_y']) * fit, tol_m,
            abs(cg[1] - pose['cortex_y']) * fit <= tol_m)

    ys = [p[1] for p in game]
    stand = (max(ys) - min(ys)) * fit
    rep.row("stand height [m]", stand, f"{H}±{tol_m}", abs(stand - H) <= tol_m)

    outs = flesh_outside(game, caps)
    p99 = outs[int(len(outs) * 0.99)]
    rep.row("flesh outside nearest capsule max [m]", outs[-1] * fit, LIMIT_TITAN_FLESH_M,
            outs[-1] * fit <= LIMIT_TITAN_FLESH_M,
            f"({outs[-1]:.3f} u, p99 {p99:.3f} u = {p99 * fit:.2f} m)")

    # facing: the wrong sign must not fit the pose better (mirror = turn + pi)
    mirrored = model_turned(samples, theta + math.pi)
    outs_m = flesh_outside(mirrored, caps)
    rep.row("facing via model_turn (max u, turned/mirror)",
            f"{outs[-1]:.3f}/{outs_m[-1]:.3f}", "turned<=mirr",
            outs[-1] <= outs_m[-1] + FACING_SLACK_U)

    mesh = PointGrid(game, cell=0.4)
    worst = 0.0
    worst_part = ""
    for name, (a, b, r) in zip(names, caps):
        w = 0.0
        wp = None
        for p in capsule_surface_points(a, b, r):
            d = mesh.nearest(p)
            if d > w: w, wp = d, p
        print(f"# air {name:16s}: up to {w:.3f} u = {w * fit:.2f} m at "
              f"({wp[0]:.2f},{wp[1]:.2f},{wp[2]:.2f})")
        if w > worst: worst, worst_part = w, name
    rep.row("registering air worst [m]", worst * fit, LIMIT_TITAN_AIR_M,
            worst * fit <= LIMIT_TITAN_AIR_M, f"({worst:.3f} u, {worst_part})")


def _hull_surface_points(hull, step=0.20):
    """Grid samples of the compound's EXPOSED surface: a face point is kept iff nudging it
    outward along the face normal lands in air (not inside any wall box)."""
    boxes = hull['walls']

    def inside_any(p, eps=1e-6):
        for lo, hi in boxes:
            if all(lo[a] - eps <= p[a] <= hi[a] + eps for a in range(3)):
                return True
        return False

    def grid1(lo, hi):
        n = max(1, int(round((hi - lo) / step)))
        return [lo + (hi - lo) * (i + 0.5) / n for i in range(n)]

    pts = []
    for lo, hi in boxes:
        for axis in range(3):
            for side, val, nrm in ((0, lo[axis], -1.0), (1, hi[axis], 1.0)):
                o1, o2 = [a for a in range(3) if a != axis]
                for c1 in grid1(lo[o1], hi[o1]):
                    for c2 in grid1(lo[o2], hi[o2]):
                        p = [0.0, 0.0, 0.0]
                        p[axis] = val; p[o1] = c1; p[o2] = c2
                        q = list(p)
                        q[axis] += nrm * 1e-3
                        if not inside_any(tuple(q)):
                            pts.append(tuple(p))
    # roof bands: linear frustum between consecutive rects, plus the top rect's lid
    rects = hull['roof_rects']
    for i in range(len(rects)):
        r0 = rects[i]
        r1 = rects[i + 1] if i + 1 < len(rects) else None
        if r1 is None:
            for cx in grid1(r0['min'][0], r0['max'][0]):
                for cz in grid1(r0['min'][1], r0['max'][1]):
                    pts.append((cx, r0['y_m'], cz))
            break
        for t in grid1(0.0, 1.0):
            y = r0['y_m'] + (r1['y_m'] - r0['y_m']) * t
            x0 = r0['min'][0] + (r1['min'][0] - r0['min'][0]) * t
            x1 = r0['max'][0] + (r1['max'][0] - r0['max'][0]) * t
            z0 = r0['min'][1] + (r1['min'][1] - r0['min'][1]) * t
            z1 = r0['max'][1] + (r1['max'][1] - r0['max'][1]) * t
            for cz in grid1(z0, z1):
                pts.append((x0, y, cz)); pts.append((x1, y, cz))
            for cx in grid1(x0, x1):
                pts.append((cx, y, z0)); pts.append((cx, y, z1))
    return pts


def _envelope(anchors):
    a, b = anchors.get('hit.min'), anchors.get('hit.max')
    if a is None or b is None:
        return None
    # the pack's corner-pair quirk: order the pair ourselves, like model.rs takes both
    return ([min(a[i], b[i]) for i in range(3)], [max(a[i], b[i]) for i in range(3)])


def gate_remnant(rep, samples, verts, tris, anchors, hull_name):
    hull = ron_read.hull(hull_name)
    env = _envelope(anchors)
    if env is None:
        rep.fail("hit envelope exists", "hit.min/hit.max empty missing")
        return
    lo, hi = env
    eps = 1e-3
    out_n, out_max = 0, 0.0
    for s in samples:
        exc = max(max(lo[a] - s[a], s[a] - hi[a]) for a in range(3))
        if exc > eps:
            out_n += 1
            if exc > out_max: out_max = exc
    rep.row("mesh samples outside hit envelope", f"{out_n}/{len(samples)}",
            LIMIT_REMNANT_OUTSIDE, out_n == 0,
            f"max excursion {out_max:.2f} m" if out_n else "")

    tg = TriGrid(verts, tris, cell=0.5)
    ds = sorted(tg.nearest(p) for p in _hull_surface_points(hull))
    if not ds:
        rep.fail("hull surface to mesh", "no hull surface samples")
        return
    med = ds[len(ds) // 2]
    rep.row("hull surface to mesh median [m]", med, LIMIT_REMNANT_MEDIAN_M,
            med <= LIMIT_REMNANT_MEDIAN_M, f"({len(ds)} hull samples)")
    rep.row("hull surface to mesh worst [m]", ds[-1], LIMIT_REMNANT_WORST_M,
            ds[-1] <= LIMIT_REMNANT_WORST_M)


def gate_prop(rep, verts, tris, anchors):
    env = _envelope(anchors)
    if env is None:
        rep.fail("hit envelope exists", "hit.min/hit.max empty missing")
        return
    lo, hi = env
    tg = TriGrid(verts, tris, cell=0.5)
    step = 0.10
    worst_face, worst = "", 0.0
    for axis, ax_name in ((0, 'x'), (1, 'y'), (2, 'z')):
        for val, side in ((lo[axis], '-'), (hi[axis], '+')):
            o1, o2 = [a for a in range(3) if a != axis]
            n1 = max(1, int(round((hi[o1] - lo[o1]) / step)))
            n2 = max(1, int(round((hi[o2] - lo[o2]) / step)))
            w = 0.0
            for i in range(n1):
                for j in range(n2):
                    p = [0.0, 0.0, 0.0]
                    p[axis] = val
                    p[o1] = lo[o1] + (hi[o1] - lo[o1]) * (i + 0.5) / n1
                    p[o2] = lo[o2] + (hi[o2] - lo[o2]) * (j + 0.5) / n2
                    d = tg.nearest(tuple(p))
                    if d > w: w = d
            print(f"# face {side}{ax_name}: worst {w:.3f} m")
            if w > worst: worst, worst_face = w, side + ax_name
    rep.row("plan-box face to drawn worst [m]", worst, LIMIT_PROP_FACE_M,
            worst <= LIMIT_PROP_FACE_M, f"(face {worst_face})")


# ---------------------------------------------------------------------------

def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('glb', type=Path)
    ap.add_argument('--geometry', required=True,
                    help='titan.ron:drawn_poses/<name> or art.ron:hulls/<name> or "-" (prop)')
    ap.add_argument('--kind', choices=['titan', 'remnant', 'prop'])
    ap.add_argument('--class', dest='size', default='medium',
                    help='scale.ron size class for titans (default medium)')
    ap.add_argument('--samples', type=int, default=MIN_SAMPLES)
    ap.add_argument('--spec', type=Path, help='spec json; its sha256 must be in asset.extras')
    args = ap.parse_args(argv)

    geo_name = None
    kind = args.kind
    if args.geometry != '-':
        try:
            _file, rest = args.geometry.split(':', 1)
            section, geo_name = rest.split('/', 1)
        except ValueError:
            print(f"bad geometry pointer {args.geometry!r}", file=sys.stderr)
            return 2
        inferred = {'drawn_poses': 'titan', 'hulls': 'remnant'}.get(section)
        kind = kind or inferred
    if kind is None:
        print("cannot infer --kind from the geometry pointer; pass it", file=sys.stderr)
        return 2

    doc, verts, tris, anchors = collect(args.glb)
    print(f"file: {args.glb}")
    print(f"kind: {kind} · geometry: {args.geometry} · verts {len(verts)} · tris {len(tris)}"
          f" · anchors {sorted(anchors)}")

    rep = Report()

    why = glb_merge.preconditions(doc)
    rep.row("glb_merge preconditions", "ok" if why is None else "violated", "pass",
            why is None, why or "")

    if args.spec:
        want = hashlib.sha256(args.spec.read_bytes()).hexdigest()
        got = doc.get('asset', {}).get('extras', {}).get('spec_sha256')
        rep.row("spec sha256 in asset.extras", (got or "MISSING")[:12], want[:12], got == want)

    samples = surface_samples(verts, tris, floor=args.samples)
    rep.row("surface samples", f"{len(samples)}", f">={args.samples}",
            len(samples) >= args.samples,
            "ZERO GEOMETRY — an empty file must never pass" if not samples else "")
    if not samples:
        # still run the class gate so the missing-cortex/envelope failures are printed too
        if kind == 'titan' and 'cortex' not in anchors:
            rep.fail("cortex empty exists",
                     "MISSING — fit_to_class silently falls back to hit-pair fit")
        if kind in ('remnant', 'prop') and _envelope(anchors) is None:
            rep.fail("hit envelope exists", "hit.min/hit.max empty missing")
    elif kind == 'titan':
        gate_titan(rep, samples, anchors, geo_name, args.size)
    elif kind == 'remnant':
        gate_remnant(rep, samples, verts, tris, anchors, geo_name)
    else:
        gate_prop(rep, verts, tris, anchors)

    print("ACCEPT" if not rep.failed else "REJECT")
    return 1 if rep.failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
