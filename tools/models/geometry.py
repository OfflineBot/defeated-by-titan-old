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
    face normal, winding fixed against `interior` (a point inside the solid)."""
    verts, normals, uvs, indices = mesh
    a, b, c = loop[0], loop[1], loop[2]
    ux, uy, uz = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    vx, vy, vz = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    nx, ny, nz = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length < 1e-12:
        return  # degenerate (a loft ring collapsed to a point) — nothing to draw
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
