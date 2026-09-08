#!/usr/bin/env python3
"""ron_read.py — minimal regex extractors for the authoritative geometry rows.

The generator and the gate READ the authoritative geometry (titan.ron: drawn_poses,
art.ron: hulls) — a spec never copies numbers out of them (tools/models/README.md rule 5,
CLAUDE.md rule 5: do not re-derive another domain's decision, read it).

Pattern precedent: tools/fleet/verify_caps.py reads scale.ron fractions with a bare
`re.search(name + r'\\s*:\\s*([0-9.]+)')`. This file does the same, plus one balanced-paren
scanner for row bodies, because a capsule list is nested one level too deep for a single
regex to stay readable. Python stdlib only.

Frames, so nobody guesses:
- `drawn_poses` rows are in the MODEL FILE's own units, GAME-TURNED frame (+z backwards,
  MODEL_FACES already applied), y from the ground (titan.ron, B-042 header).
- `hulls` rows are in the FILE's own authored metres, authored frame (art.ron header —
  they were read off the glb triangles directly; the quarter turn happens at placement).
- `model_faces_rad()` reads the one composition constant out of src/shared/anchors.rs so
  a checker can apply the turn THROUGH shared's decision instead of trusting a generator.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TITAN_RON = ROOT / "assets" / "data" / "titan.ron"
ART_RON = ROOT / "assets" / "data" / "art.ron"
SCALE_RON = ROOT / "assets" / "data" / "scale.ron"
ANCHORS_RS = ROOT / "src" / "shared" / "anchors.rs"

_NUM = r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?"


def _strip_comments(text: str) -> str:
    """RON line comments removed, so a number in a comment can never be extracted."""
    return re.sub(r"//[^\n]*", "", text)


def _balanced(text: str, start: int) -> str:
    """The body of the parenthesis group opening at `start` (which must be '(')."""
    assert text[start] == "(", f"expected '(' at {start}"
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start + 1 : i]
    raise ValueError("unbalanced parentheses")


def _row_body(text: str, section: str, name: str) -> str:
    """The `( ... )` body of `"name": (` inside `section: { ... }`."""
    sec = re.search(re.escape(section) + r"\s*:\s*\{", text)
    if not sec:
        raise KeyError(f"no section {section!r}")
    row = re.compile(r'"' + re.escape(name) + r'"\s*:\s*\(')
    m = row.search(text, sec.end())
    if not m:
        raise KeyError(f"no row {name!r} in section {section!r}")
    return _balanced(text, m.end() - 1)


def _triple(s: str) -> tuple[float, float, float]:
    xs = re.findall(_NUM, s)
    if len(xs) != 3:
        raise ValueError(f"expected 3 numbers in {s!r}")
    return (float(xs[0]), float(xs[1]), float(xs[2]))


def _pair(s: str) -> tuple[float, float]:
    xs = re.findall(_NUM, s)
    if len(xs) != 2:
        raise ValueError(f"expected 2 numbers in {s!r}")
    return (float(xs[0]), float(xs[1]))


# ---------------------------------------------------------------------------
# titan.ron: drawn_poses
# ---------------------------------------------------------------------------


def drawn_pose(name: str, path: Path = TITAN_RON) -> dict:
    """{'cortex_y': float, 'capsules': [{'part', 'radius', 'a': (x,y,z), 'b': (x,y,z)}]}.

    Units: the model file's own units, game-turned frame (see module header).
    """
    text = _strip_comments(path.read_text())
    body = _row_body(text, "drawn_poses", name)
    m = re.search(r"cortex_y\s*:\s*(" + _NUM + ")", body)
    if not m:
        raise ValueError(f"drawn_poses/{name}: no cortex_y")
    cortex_y = float(m.group(1))
    capsules = []
    cap = re.compile(
        r'part\s*:\s*"([^"]+)"\s*,\s*radius\s*:\s*(' + _NUM + r")"
        r"\s*,\s*a\s*:\s*\(([^)]*)\)\s*,\s*b\s*:\s*\(([^)]*)\)"
    )
    for part, radius, a, b in cap.findall(body):
        capsules.append(
            {"part": part, "radius": float(radius), "a": _triple(a), "b": _triple(b)}
        )
    if not capsules:
        raise ValueError(f"drawn_poses/{name}: no capsules extracted")
    return {"cortex_y": cortex_y, "capsules": capsules}


# ---------------------------------------------------------------------------
# art.ron: hulls, models, cortex_tolerance_m
# ---------------------------------------------------------------------------


def hull(name: str, path: Path = ART_RON) -> dict:
    """{'walls': [(min3, max3)], 'roof_rects': [{'y_m', 'min': (x,z), 'max': (x,z)}]}.

    Authored metres, authored frame (see module header).
    """
    text = _strip_comments(path.read_text())
    body = _row_body(text, "hulls", name)
    walls_m = re.search(r"walls\s*:\s*\[", body)
    if not walls_m:
        raise ValueError(f"hulls/{name}: no walls list")
    walls = []
    box = re.compile(r"min_m\s*:\s*\(([^)]*)\)\s*,\s*max_m\s*:\s*\(([^)]*)\)")
    roof_split = re.search(r"roof_rects\s*:\s*\[", body)
    wall_part = body[: roof_split.start()] if roof_split else body
    roof_part = body[roof_split.start() :] if roof_split else ""
    for lo, hi in box.findall(wall_part):
        walls.append((_triple(lo), _triple(hi)))
    roof_rects = []
    rect = re.compile(
        r"y_m\s*:\s*(" + _NUM + r")\s*,\s*min_m\s*:\s*\(([^)]*)\)\s*,\s*max_m\s*:\s*\(([^)]*)\)"
    )
    for y, lo, hi in rect.findall(roof_part):
        roof_rects.append({"y_m": float(y), "min": _pair(lo), "max": _pair(hi)})
    if not walls:
        raise ValueError(f"hulls/{name}: no wall boxes extracted")
    return {"walls": walls, "roof_rects": roof_rects}


def model_source(name: str, path: Path = ART_RON) -> str:
    """The glb path (relative to assets/) behind `models: { "name": (source: Gltf(..)) }`."""
    text = _strip_comments(path.read_text())
    m = re.search(
        r'"' + re.escape(name) + r'"\s*:\s*\(\s*source\s*:\s*Gltf\("([^"]+)"\)', text
    )
    if not m:
        raise KeyError(f"no model {name!r} in art.ron")
    return m.group(1)


def cortex_tolerance_m(path: Path = ART_RON) -> float:
    text = _strip_comments(path.read_text())
    m = re.search(r"cortex_tolerance_m\s*:\s*(" + _NUM + ")", text)
    if not m:
        raise ValueError("art.ron: no cortex_tolerance_m")
    return float(m.group(1))


# ---------------------------------------------------------------------------
# scale.ron: size classes and rig fractions (the neck capsule's inputs)
# ---------------------------------------------------------------------------


def size_class(name: str, path: Path = SCALE_RON) -> tuple[float, float]:
    """(height_m, cortex_height_m) for a titan size class such as "medium"."""
    text = _strip_comments(path.read_text())
    m = re.search(
        r'"' + re.escape(name) + r'"\s*:\s*\(\s*height_m\s*:\s*(' + _NUM + r")"
        r"\s*,\s*cortex_height_m\s*:\s*(" + _NUM + r")",
        text,
    )
    if not m:
        raise KeyError(f"no size class {name!r} in scale.ron")
    return (float(m.group(1)), float(m.group(2)))


def fraction(name: str, path: Path = SCALE_RON) -> float:
    """One `<name>: <float>` out of scale.ron (verify_caps.py's frac())."""
    text = _strip_comments(path.read_text())
    m = re.search(re.escape(name) + r"\s*:\s*(" + _NUM + ")", text)
    if not m:
        raise KeyError(f"no {name!r} in scale.ron")
    return float(m.group(1))


# ---------------------------------------------------------------------------
# src/shared/anchors.rs: the one facing decision
# ---------------------------------------------------------------------------

_RUST_CONSTS = {
    "std::f32::consts::PI": math.pi,
    "std::f32::consts::FRAC_PI_2": math.pi / 2.0,
    "std::f32::consts::TAU": math.tau,
}


def model_faces_rad(path: Path = ANCHORS_RS) -> float:
    """MODEL_FACES out of src/shared/anchors.rs — the pack's facing flip, radians about +Y.

    Read, not copied: `model_turn(yaw) = Quat::from_rotation_y(MODEL_FACES + yaw)` is the one
    composition (anchors.rs), and a checker that hardcoded pi here would be the second writer
    rule 5 forbids.
    """
    text = path.read_text()
    m = re.search(r"pub const MODEL_FACES\s*:\s*f32\s*=\s*([^;]+);", text)
    if not m:
        raise ValueError("src/shared/anchors.rs: no MODEL_FACES const")
    expr = m.group(1).strip()
    if expr in _RUST_CONSTS:
        return _RUST_CONSTS[expr]
    return float(expr)


if __name__ == "__main__":
    # Smoke print, no arguments: one line per extractor against the live files.
    pose = drawn_pose("titan_husk")
    print(f"drawn_poses/titan_husk: cortex_y {pose['cortex_y']} · {len(pose['capsules'])} capsules")
    h = hull("ruin_wall_corner")
    print(f"hulls/ruin_wall_corner: {len(h['walls'])} walls · {len(h['roof_rects'])} roof_rects")
    print(f"model ruin_wall_corner -> {model_source('ruin_wall_corner')}")
    print(f"cortex_tolerance_m {cortex_tolerance_m()}")
    print(f"medium {size_class('medium')} · small {size_class('small')}")
    print(
        "fractions leg %.2f torso %.2f shoulder %.2f"
        % (fraction("leg_fraction"), fraction("torso_fraction"), fraction("shoulder_height_fraction"))
    )
    print(f"MODEL_FACES {model_faces_rad():.6f} rad")
