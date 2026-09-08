#!/usr/bin/env python3
"""geometry.py — the faceted primitives of the model generator (tools/models/README.md).

THE MID-RADIUS RULE LIVES HERE. A faceted ring approximating an analytic circle of
radius r must STRADDLE it symmetrically: its vertices are authored at

    r' = r * 2 / (1 + cos(pi / n))

so that the vertex overshoot (r' - r) equals the face-center undershoot
(r - r' * cos(pi/n)); both are r * (1 - cos(pi/n)) / (1 + cos(pi/n)). That expression
is the EXACT symmetric band of the rule: 0.0396*r at n=8, 0.0173*r at n=12. (The
README's table rounds these to 0.038/0.022 — `mid_radius_band()` below is the
authoritative number, the sampler in the evidence measures against it.)

The caps of a capsule facet in the polar direction too, so their loft rings get a
second, independent mid-radius factor for the polar chord — `capsule()` documents it
inline.

FLAT SHADING: every face duplicates its vertices and carries one face normal — no
vertex is shared between faces, which is what makes the low-poly look read as facets
instead of smooth blobs.

All functions return `(verts, normals, uvs, indices)` in the glbout.add_mesh shape and
take a single flat `uv` (a palette-cell center from glbout.palette_uv). Everything is
pure: no clock, no randomness, no file — determinism is the caller's to keep.

WINDING: faces are emitted counter-clockwise seen from OUTSIDE (the glTF front face).
Instead of hand-arguing 26 face orientations per shape, every face is checked against
an interior point and flipped if it looks inward — a convex shape cannot fool that.
"""

from __future__ import annotations

import math

Mesh = tuple[list, list, list, list]


def mid_radius(r: float, n: int) -> float:
    """The authored ring radius that straddles the analytic radius `r` with `n` facets."""
    return r * 2.0 / (1.0 + math.cos(math.pi / n))


def mid_radius_band(n: int) -> float:
    """The exact symmetric surface-error band of the rule, as a FRACTION of r:
    max |faceted - analytic| = r * (1 - cos(pi/n)) / (1 + cos(pi/n))."""
    c = math.cos(math.pi / n)
    return (1.0 - c) / (1.0 + c)


# ---------------------------------------------------------------------------
# face assembly
# ---------------------------------------------------------------------------


def _emit(mesh: Mesh, loop: list, uv, interior) -> None:
    """One flat convex face from a vertex loop (3 or 4 points), duplicated verts, one
    face normal, winding fixed against `interior` (a point inside the solid).

    `uv` is a flat (u, v) tuple OR a zero-argument callable returning one — the callable
    is drawn ONCE PER FACE (after the degeneracy check), which is how per-face palette
    mottling stays deterministic: the caller seeds the RNG, the face order is fixed."""
    verts, normals, uvs, indices = mesh
    a, b, c = loop[0], loop[1], loop[2]
    ux, uy, uz = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    vx, vy, vz = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    nx, ny, nz = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length < 1e-12:
        return  # degenerate (a loft ring collapsed to a point) — nothing to draw
    if callable(uv):
        uv = uv()
    nx, ny, nz = nx / length, ny / length, nz / length
    cx = sum(p[0] for p in loop) / len(loop)
    cy = sum(p[1] for p in loop) / len(loop)
    cz = sum(p[2] for p in loop) / len(loop)
    out = (cx - interior[0]) * nx + (cy - interior[1]) * ny + (cz - interior[2]) * nz
    if out < 0.0:
        loop = list(reversed(loop))
        nx, ny, nz = -nx, -ny, -nz
    base = len(verts) // 3
    for p in loop:
        verts.extend(p)
        normals.extend((nx, ny, nz))
        uvs.extend(uv)
    for i in range(1, len(loop) - 1):  # fan: (0,1,2) and, for a quad, (0,2,3)
        indices.extend((base, base + i, base + i + 1))


def _new() -> Mesh:
    return ([], [], [], [])


def combine(parts: list[Mesh]) -> Mesh:
    """Several parts as ONE mesh — the generator ships one primitive per material so
    that glb_merge finds nothing left to merge (FIND-105: node count is the cost)."""
    verts, normals, uvs, indices = _new()
    for pv, pn, pu, pi in parts:
        base = len(verts) // 3
        verts.extend(pv)
        normals.extend(pn)
        uvs.extend(pu)
        indices.extend(base + i for i in pi)
    return (verts, normals, uvs, indices)


def translate(mesh: Mesh, dx: float, dy: float, dz: float) -> Mesh:
    verts, normals, uvs, indices = mesh
    moved = list(verts)
    for v in range(0, len(moved), 3):
        moved[v] += dx
        moved[v + 1] += dy
        moved[v + 2] += dz
    return (moved, list(normals), list(uvs), list(indices))


# ---------------------------------------------------------------------------
# capsule loft
# ---------------------------------------------------------------------------


def capsule(radius: float, height: float, n: int, uv, cap_rings: int = 8) -> Mesh:
    """A vertical capsule: a cylinder of `height` between two hemispherical caps of
    `radius`, centered at the origin, `n` facets around, `cap_rings` loft rings per cap.

    Mid-radius, applied twice and independently:
    - AZIMUTHAL: every ring is authored at `mid_radius(analytic_r, n)` — the flat wall
      between two ring vertices straddles the analytic circle.
    - POLAR (caps only): the chord between two cap rings cuts inside the sphere arc by
      the same cosine geometry, so intermediate cap rings scale the SPHERE radius by
      `2 / (1 + cos(half_polar_step))` as well. The equator ring is shared with the
      cylinder and gets the azimuthal factor only — a polar factor there would open a
      radial step at the seam.

    The polar factor eats into the band, so the total error exceeds the pure ring band
    `mid_radius_band(n) * radius` slightly; with the default 8 cap rings the vertex
    worst case is `mid_radius(r,n)/r * (2/(1+cos(pi/(4*cap_rings)))) - 1` — the
    evidence sampler measures the real mesh instead of trusting this comment.
    """
    if height < 0.0 or radius <= 0.0 or n < 3 or cap_rings < 1:
        raise ValueError(f"capsule(radius={radius}, height={height}, n={n}, cap_rings={cap_rings})")
    s_az = mid_radius(1.0, n)
    half_step = (math.pi / 2.0) / cap_rings / 2.0
    s_pol = 2.0 / (1.0 + math.cos(half_step))
    h2 = height / 2.0

    # The profile, bottom pole to top pole: (y, ring radius). Poles are rings of radius 0.
    profile: list[tuple[float, float]] = [(-(h2 + s_pol * radius), 0.0)]
    for j in range(cap_rings - 1, 0, -1):  # bottom cap, pole side toward equator
        a = (math.pi / 2.0) * j / cap_rings
        profile.append((-(h2 + s_pol * radius * math.sin(a)), s_az * s_pol * radius * math.cos(a)))
    profile.append((-h2, s_az * radius))  # cylinder bottom (shared equator)
    profile.append((h2, s_az * radius))  # cylinder top (shared equator)
    for j in range(1, cap_rings):  # top cap, equator toward pole
        a = (math.pi / 2.0) * j / cap_rings
        profile.append((h2 + s_pol * radius * math.sin(a), s_az * s_pol * radius * math.cos(a)))
    profile.append((h2 + s_pol * radius, 0.0))

    mesh = _new()
    interior = (0.0, 0.0, 0.0)
    for (y0, r0), (y1, r1) in zip(profile, profile[1:]):
        if r0 == 0.0 and r1 == 0.0:
            continue
        for k in range(n):
            t0, t1 = 2.0 * math.pi * k / n, 2.0 * math.pi * (k + 1) / n
            c0, s0 = math.cos(t0), math.sin(t0)
            c1, s1 = math.cos(t1), math.sin(t1)
            lower = [(r0 * c0, y0, r0 * s0), (r0 * c1, y0, r0 * s1)]
            upper = [(r1 * c1, y1, r1 * s1), (r1 * c0, y1, r1 * s0)]
            if r0 == 0.0:
                _emit(mesh, [lower[0]] + upper, uv, interior)  # bottom pole fan
            elif r1 == 0.0:
                _emit(mesh, lower + [upper[0]], uv, interior)  # top pole fan
            else:
                _emit(mesh, lower + upper, uv, interior)
    return mesh


# ---------------------------------------------------------------------------
# box extrusion with edge break, and the wedge
# ---------------------------------------------------------------------------


def box(sx: float, sy: float, sz: float, uv, edge_break_m: float = 0.0) -> Mesh:
    """An axis-aligned box centered at the origin. With `edge_break_m > 0` every edge
    is chamfered by that width: 6 inset faces, 12 edge strips, 8 corner triangles —
    the cheap detail that keeps a low-poly silhouette from reading as a primitive.
    The chamfer stays INSIDE the analytic box (a chamfer is a cut, not a bulge), so
    the box's authored extents are exactly its hit extents."""
    h = (sx / 2.0, sy / 2.0, sz / 2.0)
    c = min(edge_break_m, min(h) * 0.99) if edge_break_m > 0.0 else 0.0
    if c <= 0.0:
        mesh = _new()
        for axis in range(3):
            for sign in (-1.0, 1.0):
                loop = []
                for da, db in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                    p = [0.0, 0.0, 0.0]
                    p[axis] = h[axis] * sign
                    p[(axis + 1) % 3] = h[(axis + 1) % 3] * da
                    p[(axis + 2) % 3] = h[(axis + 2) % 3] * db
                    loop.append(tuple(p))
                _emit(mesh, loop, uv, (0.0, 0.0, 0.0))
        return mesh

    def corner_point(sgn: tuple, face_axis: int) -> tuple:
        """The chamfered-cube vertex near corner `sgn` that lies ON the face of
        `face_axis` — full extent on that axis, pulled in by `c` on the other two."""
        return tuple(
            h[a] * sgn[a] if a == face_axis else (h[a] - c) * sgn[a] for a in range(3)
        )

    mesh = _new()
    interior = (0.0, 0.0, 0.0)
    signs = [(sa, sb, sc_) for sa in (-1, 1) for sb in (-1, 1) for sc_ in (-1, 1)]

    for axis in range(3):  # 6 inset faces
        for sign in (-1, 1):
            loop = []
            for da, db in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                sgn = [0, 0, 0]
                sgn[axis] = sign
                sgn[(axis + 1) % 3] = da
                sgn[(axis + 2) % 3] = db
                loop.append(corner_point(tuple(sgn), axis))
            _emit(mesh, loop, uv, interior)

    for a in range(3):  # 12 edge strips, edge along axis d between faces a and b
        for b in range(a + 1, 3):
            d = 3 - a - b
            for sa in (-1, 1):
                for sb in (-1, 1):
                    lo, hi_ = [0, 0, 0], [0, 0, 0]
                    lo[a], lo[b], lo[d] = sa, sb, -1
                    hi_[a], hi_[b], hi_[d] = sa, sb, 1
                    loop = [
                        corner_point(tuple(lo), a),
                        corner_point(tuple(lo), b),
                        corner_point(tuple(hi_), b),
                        corner_point(tuple(hi_), a),
                    ]
                    _emit(mesh, loop, uv, interior)

    for sgn in signs:  # 8 corner triangles
        _emit(mesh, [corner_point(sgn, a) for a in range(3)], uv, interior)
    return mesh


# ---------------------------------------------------------------------------
# oriented capsules — the titan scheme's primitive (a drawn_poses row is capsules)
# ---------------------------------------------------------------------------


def _align_y(axis: tuple[float, float, float]) -> list[list[float]]:
    """The rotation matrix (rows) taking +Y onto the unit vector `axis` (Rodrigues)."""
    dx, dy, dz = axis
    if dy > 1.0 - 1e-12:
        return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    if dy < -1.0 + 1e-12:
        return [[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, -1.0]]
    # v = y × d = (dz, 0, -dx), c = dy; R = I + [v]x + [v]x^2 * (1-c)/|v|^2
    vx, vy, vz = dz, 0.0, -dx
    k = (1.0 - dy) / (vx * vx + vz * vz)
    return [
        [1.0 - k * vz * vz, -vz, k * vx * vz],
        [vz, 1.0 - k * (vx * vx + vz * vz), -vx],
        [k * vx * vz, vx, 1.0 - k * vx * vx],
    ]


def _apply(R: list[list[float]], p: tuple) -> tuple:
    return (
        R[0][0] * p[0] + R[0][1] * p[1] + R[0][2] * p[2],
        R[1][0] * p[0] + R[1][1] * p[1] + R[1][2] * p[2],
        R[2][0] * p[0] + R[2][1] * p[1] + R[2][2] * p[2],
    )


def rotate(mesh: Mesh, R: list[list[float]]) -> Mesh:
    """Rotate a mesh by a 3x3 matrix — vertices AND normals (pure rotation, so the
    inverse-transpose is the matrix itself)."""
    verts, normals, uvs, indices = mesh
    tv, tn = list(verts), list(normals)
    for i in range(0, len(tv), 3):
        tv[i], tv[i + 1], tv[i + 2] = _apply(R, (tv[i], tv[i + 1], tv[i + 2]))
        tn[i], tn[i + 1], tn[i + 2] = _apply(R, (tn[i], tn[i + 1], tn[i + 2]))
    return (tv, tn, list(uvs), list(indices))


def capsule_between(
    a: tuple,
    b: tuple,
    radius: float,
    n: int,
    uv,
    cap_rings: int = 6,
    max_span: float = 0.12,
    bands: tuple = (),
) -> Mesh:
    """A faceted capsule from `a` to `b` (sphere caps beyond both ends), mid-radius rule
    as in `capsule()`. Two additions over the vertical primitive:

    - SUBDIVISION: the cylinder wall is split into spans of at most `max_span` — not for
      looks (flat shading hides it) but for the gate's instrument: `accept.py` measures
      registering air against nearest MESH SAMPLES, 10 per triangle, and one 3-unit-tall
      quad would leave sample gaps wider than the whole air budget.
    - BANDS: `(lo, hi, r_scale, band_uv)` in LOCAL axis coordinates (0 at `a`, |b-a| at
      `b`): the wall between lo and hi is authored at `mid_radius * r_scale` with its own
      uv — the recessed Cortex-side band. A recess is a cut inward, so it can only eat air
      budget, never flesh budget; the caller keeps `1 - r_scale` small enough for the
      gate. Step rings (horizontal annuli) close the recess at both edges.
    """
    ax, ay, az = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    length = math.sqrt(ax * ax + ay * ay + az * az)
    if length < 1e-9:
        raise ValueError(f"capsule_between: a == b at {a}")
    axis = (ax / length, ay / length, az / length)
    s_az = mid_radius(1.0, n)
    # cap ring count scales with the radius so cap sample density matches the walls'
    cap_rings = max(cap_rings, int(math.ceil((math.pi / 2.0) * radius / max_span)))
    half_step = (math.pi / 2.0) / cap_rings / 2.0
    s_pol = 2.0 / (1.0 + math.cos(half_step))
    h2 = length / 2.0

    def wall_r(y: float) -> tuple[float, object]:
        """(authored radius, uv) of the cylinder wall at local height y (centered)."""
        t = y + h2  # 0 at `a`
        for lo, hi, scale, band_uv in bands:
            if lo - 1e-9 <= t <= hi + 1e-9:
                return (s_az * radius * scale, band_uv)
        return (s_az * radius, uv)

    # profile: (y, r, uv) — poles and caps first, then the subdivided/banded cylinder.
    profile: list[tuple[float, float, object]] = [(-(h2 + s_pol * radius), 0.0, uv)]
    for j in range(cap_rings - 1, 0, -1):
        ang = (math.pi / 2.0) * j / cap_rings
        profile.append(
            (-(h2 + s_pol * radius * math.sin(ang)), s_az * s_pol * radius * math.cos(ang), uv)
        )
    cuts = {-h2, h2}  # band lo/hi are t in [0, length]; local y is t - h2
    for lo, hi, _scale, _buv in bands:
        cuts.add(max(-h2, min(h2, lo - h2)))
        cuts.add(max(-h2, min(h2, hi - h2)))
    edges = sorted(cuts)
    ys: list[float] = []
    for y0, y1 in zip(edges, edges[1:]):
        spans = max(1, int(math.ceil((y1 - y0) / max_span)))
        for s in range(spans):
            ys.append(y0 + (y1 - y0) * s / spans)
    ys.append(h2)
    prev_r = None
    for y in ys:
        r_here, uv_here = wall_r(y + 1e-6 if y < h2 else y - 1e-6)
        if prev_r is not None and abs(prev_r - r_here) > 1e-9:
            # a band edge: close the step with a ring at the SAME height (the horizontal
            # annulus gets the deeper side's uv via the span rule below)
            below_r, below_uv = wall_r(y - 1e-6)
            profile.append((y, below_r, below_uv))
            profile.append((y, r_here, uv_here))
        else:
            profile.append((y, r_here, uv_here))
        prev_r = r_here
    for j in range(1, cap_rings):
        ang = (math.pi / 2.0) * j / cap_rings
        profile.append(
            (h2 + s_pol * radius * math.sin(ang), s_az * s_pol * radius * math.cos(ang), uv)
        )
    profile.append((h2 + s_pol * radius, 0.0, uv))

    mesh = _new()
    interior = (0.0, 0.0, 0.0)

    def lerp(p, q, t):
        return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t, p[2] + (q[2] - p[2]) * t)

    for (y0, r0, uv0), (y1, r1, uv1) in zip(profile, profile[1:]):
        if r0 == 0.0 and r1 == 0.0:
            continue
        if abs(y1 - y0) < 1e-9 and abs(r1 - r0) < 1e-9:
            continue
        span_uv = uv1 if r1 < r0 or y1 > y0 else uv0
        # A step ring (same height, radius jump) is where the solid stops being convex:
        # the bottom edge of a recess is exposed UPWARD, the top edge DOWNWARD. The
        # convex interior at the origin would orient the top edge wrong, so step rings
        # get an interior on the correct side instead.
        span_interior = interior
        if abs(y1 - y0) < 1e-9:
            span_interior = (0.0, y0 - 1.0, 0.0) if r1 < r0 else (0.0, y0 + 1.0, 0.0)
        # azimuthal COPLANAR subdivision: the gate measures registering air against
        # nearest mesh samples (10 per triangle), so a wide facet is cut into sub-quads
        # in the SAME plane — silhouette and shading unchanged, sample density not.
        chord = max(r0, r1) * 2.0 * math.sin(math.pi / n)
        m = max(1, int(math.ceil(chord / max_span)))
        for k in range(n):
            t0, t1 = 2.0 * math.pi * k / n, 2.0 * math.pi * (k + 1) / n
            c0, s0 = math.cos(t0), math.sin(t0)
            c1, s1 = math.cos(t1), math.sin(t1)
            L0, L1 = (r0 * c0, y0, r0 * s0), (r0 * c1, y0, r0 * s1)
            U0, U1 = (r1 * c0, y1, r1 * s0), (r1 * c1, y1, r1 * s1)
            face_uv = span_uv() if callable(span_uv) else span_uv  # one color per FACET
            for j in range(m):
                f0, f1 = j / m, (j + 1) / m
                l0, l1 = lerp(L0, L1, f0), lerp(L0, L1, f1)
                u0, u1 = lerp(U0, U1, f0), lerp(U0, U1, f1)
                if r0 == 0.0:
                    _emit(mesh, [L0, u1, u0], face_uv, span_interior)
                elif r1 == 0.0:
                    _emit(mesh, [l0, l1, U0], face_uv, span_interior)
                else:
                    _emit(mesh, [l0, l1, u1, u0], face_uv, span_interior)

    mesh = rotate(mesh, _align_y(axis))
    mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0, (a[2] + b[2]) / 2.0)
    return translate(mesh, *mid)


def cylinder_patch(
    axis_x: float,
    y_lo: float,
    y_hi: float,
    axis_z: float,
    radius: float,
    az_center: float,
    az_half: float,
    uv,
    n_az: int = 6,
    n_y: int = 3,
) -> Mesh:
    """A curved rectangular patch hugging a vertical cylinder (axis at `axis_x`/`axis_z`,
    azimuth 0 at +Z): the painted cortex plate on the Cortex-side. Emitted as an `n_az` x `n_y`
    grid of small outward quads, so each flat sub-quad stays within a whisker of the
    cylinder — the caller budgets `radius` against the flesh band, the grid keeps the
    corner error out of it."""
    mesh = _new()
    for j in range(n_y):
        ya = y_lo + (y_hi - y_lo) * j / n_y
        yb = y_lo + (y_hi - y_lo) * (j + 1) / n_y
        for i in range(n_az):
            ta = az_center - az_half + 2.0 * az_half * i / n_az
            tb = az_center - az_half + 2.0 * az_half * (i + 1) / n_az
            xa, za = axis_x + radius * math.sin(ta), axis_z + radius * math.cos(ta)
            xb, zb = axis_x + radius * math.sin(tb), axis_z + radius * math.cos(tb)
            loop = [(xa, ya, za), (xb, ya, zb), (xb, yb, zb), (xa, yb, za)]
            _emit(mesh, loop, uv, (axis_x, (ya + yb) / 2.0, axis_z))
    return mesh


def tile(center: tuple, out_dir: tuple, up_hint: tuple, w: float, h: float, uv) -> Mesh:
    """One outward-facing quad — an eye cell. `center` is the tile's middle, `out_dir`
    the exterior direction (normalized here), `up_hint` roughly the tile's up. The tile
    is flat, so its corners sit slightly further from a curved surface than its center —
    the caller budgets that against the flesh band."""
    ox, oy, oz = out_dir
    L = math.sqrt(ox * ox + oy * oy + oz * oz)
    ox, oy, oz = ox / L, oy / L, oz / L
    ux, uy, uz = up_hint
    d = ux * ox + uy * oy + uz * oz
    ux, uy, uz = ux - d * ox, uy - d * oy, uz - d * oz
    L = math.sqrt(ux * ux + uy * uy + uz * uz)
    ux, uy, uz = ux / L, uy / L, uz / L
    rx, ry, rz = (uy * oz - uz * oy, uz * ox - ux * oz, ux * oy - uy * ox)
    hw, hh = w / 2.0, h / 2.0
    corners = [
        (center[0] - rx * hw - ux * hh, center[1] - ry * hw - uy * hh, center[2] - rz * hw - uz * hh),
        (center[0] + rx * hw - ux * hh, center[1] + ry * hw - uy * hh, center[2] + rz * hw - uz * hh),
        (center[0] + rx * hw + ux * hh, center[1] + ry * hw + uy * hh, center[2] + rz * hw + uz * hh),
        (center[0] - rx * hw + ux * hh, center[1] - ry * hw + uy * hh, center[2] - rz * hw + uz * hh),
    ]
    mesh = _new()
    interior = (center[0] - ox, center[1] - oy, center[2] - oz)
    _emit(mesh, corners, uv, interior)
    return mesh


def wedge(sx: float, sy: float, sz: float, uv) -> Mesh:
    """A right triangular prism: the box `sx*sy*sz` cut along one diagonal. The base
    is the full x-z rectangle at y = -sy/2, the vertical back face stands at z = -sz/2,
    and the slope runs from the back's top edge down to the front's base edge."""
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
    b00, b01 = (-hx, -hy, -hz), (-hx, -hy, hz)
    b10, b11 = (hx, -hy, -hz), (hx, -hy, hz)
    t0, t1 = (-hx, hy, -hz), (hx, hy, -hz)
    interior = (0.0, -hy / 2.0, -hz / 2.0)
    mesh = _new()
    _emit(mesh, [b00, b10, b11, b01], uv, interior)  # base
    _emit(mesh, [b00, b10, t1, t0], uv, interior)  # back
    _emit(mesh, [b01, b11, t1, t0], uv, interior)  # slope
    _emit(mesh, [b00, b01, t0], uv, interior)  # left side
    _emit(mesh, [b10, b11, t1], uv, interior)  # right side
    return mesh
