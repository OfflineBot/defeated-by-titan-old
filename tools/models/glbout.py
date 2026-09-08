#!/usr/bin/env python3
"""glbout.py — the GLB writer of the in-repo model generator (tools/models/README.md).

FROZEN API (README, 2026-09-08):

    w = Writer(generator="dbt-gen 0.1.0", extras={...})
    w.add_mesh(name, verts, normals, uvs, indices)
    w.add_empty(name, xyz)
    w.write(path)                # returns the bytes it wrote

The output is shaped exactly like the a-* pack so that every existing consumer keeps
working unchanged: one scene, one untransformed root node, every other node a direct
child of it — mesh nodes without any transform (vertices are authored in model space),
empty nodes with a translation only — one primitive per mesh, mode 4 (TRIANGLES),
attributes exactly POSITION/NORMAL/TEXCOORD_0, indexed, one buffer. That is precisely
the set `tools/glb_merge.py preconditions()` asserts, and satisfying it is part of the
output contract.

THE ONE DIVERGENCE FROM THE PACK: the material's palette texture is EMBEDDED in the BIN
chunk (an image with a bufferView and mimeType image/png) instead of a
`../../texturen/TEX-*.png` URI. A generated file must not couple to a folder it did not
come from (README: "no ../../texturen coupling"). The PNG is built here with zlib from
the stdlib — same byte-pattern precedent as tools/glb_merge.py, python stdlib ONLY.

DETERMINISM: nothing in this module reads a clock, the environment or any file. The same
calls in the same order produce byte-identical output (dict insertion order is the JSON
order, zlib compression at a fixed level is deterministic).
"""

from __future__ import annotations

import array
import json
import struct
import sys
import zlib
from pathlib import Path

GLB_MAGIC = 0x46546C67  # 'glTF'
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942

FLOAT = 5126
USHORT = 5123
UINT = 5125
TRIANGLES = 4
ARRAY_BUFFER = 34962
ELEMENT_ARRAY_BUFFER = 34963
NEAREST = 9728
CLAMP_TO_EDGE = 33071

USHORT_MAX = 65535

# ---------------------------------------------------------------------------
# The palette — one fixed table, one fixed texture, forever.
#
# A spec names colors by KEY ("sand_brown", "roof_slate"); geometry gets a flat UV at the
# center of that key's cell. The table is ordered and append-only: a new color goes at
# the END, because the cell position of every existing key is baked into every generated
# file already on disk.
# ---------------------------------------------------------------------------

PALETTE: dict[str, tuple[int, int, int]] = {
    "sand_brown": (194, 154, 108),
    "brick_red": (156, 74, 60),
    "roof_slate": (84, 90, 102),
    "bone_white": (226, 220, 205),
    "moss_green": (110, 124, 70),
    "iron_grey": (120, 120, 126),
    "timber_dark": (94, 70, 48),
    "blood_red": (138, 34, 34),
    "leaf_green": (86, 142, 74),
    "night_blue": (44, 52, 86),
    "cloth_teal": (70, 120, 120),
    "stone_light": (168, 164, 152),
    "skin_pale": (222, 188, 158),
    "gold_ochre": (198, 152, 64),
    "char_black": (38, 36, 34),
    "snow_white": (240, 240, 240),
}

_GRID = 4  # 4x4 cells of 4x4 px each -> a 16x16 px texture, 16 color slots
_CELL_PX = 4
_TEX_PX = _GRID * _CELL_PX


def palette_uv(key: str) -> tuple[float, float]:
    """The UV of the CENTER of `key`'s cell — safe under both nearest and linear
    filtering, because the cell is 4 px wide and the sample point is 2 px from
    every neighbouring color."""
    try:
        slot = list(PALETTE).index(key)
    except ValueError:
        raise KeyError(
            f"palette key {key!r} is not in glbout.PALETTE ({sorted(PALETTE)})"
        ) from None
    col, row = slot % _GRID, slot // _GRID
    return (
        (col * _CELL_PX + _CELL_PX / 2) / _TEX_PX,
        (row * _CELL_PX + _CELL_PX / 2) / _TEX_PX,
    )


def _palette_png() -> bytes:
    """The palette as a minimal RGB PNG, stdlib only, byte-deterministic."""

    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))

    raw = bytearray()
    keys = list(PALETTE)
    for py in range(_TEX_PX):
        raw.append(0)  # filter: none
        for px in range(_TEX_PX):
            slot = (py // _CELL_PX) * _GRID + (px // _CELL_PX)
            rgb = PALETTE[keys[slot]] if slot < len(keys) else (255, 0, 255)
            raw += bytes(rgb)
    ihdr = struct.pack(">IIBBBBB", _TEX_PX, _TEX_PX, 8, 2, 0, 0, 0)  # 8-bit RGB
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


# ---------------------------------------------------------------------------
# The container — same shape as tools/glb_merge.py write_glb (glTF 2.0 section 4.4.3)
# ---------------------------------------------------------------------------


def write_glb_bytes(doc: dict, binary: bytes) -> bytes:
    """GLB bytes. JSON padded with spaces, BIN with zeros, both to 4."""
    text = json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    text += b" " * (-len(text) % 4)
    binary += b"\0" * (-len(binary) % 4)
    total = 12 + 8 + len(text) + (8 + len(binary) if binary else 0)
    out = struct.pack("<III", GLB_MAGIC, 2, total)
    out += struct.pack("<II", len(text), CHUNK_JSON) + text
    if binary:
        out += struct.pack("<II", len(binary), CHUNK_BIN) + binary
    return out


class _Bin:
    """The output BIN chunk: one accessor per bufferView, every view 4-aligned."""

    def __init__(self) -> None:
        self.blob = bytearray()
        self.views: list[dict] = []
        self.accessors: list[dict] = []

    def _view(self, payload: bytes, target: int | None) -> int:
        self.blob += b"\0" * (-len(self.blob) % 4)
        view = {"buffer": 0, "byteOffset": len(self.blob), "byteLength": len(payload)}
        if target is not None:
            view["target"] = target
        self.blob += payload
        self.views.append(view)
        return len(self.views) - 1

    def add(self, values, component: int, kind: str, target: int, minmax=None) -> int:
        fmt = {FLOAT: "f", USHORT: "H", UINT: "I"}[component]
        comp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}[kind]
        buf = array.array(fmt, values)
        if sys.byteorder != "little":
            buf.byteswap()
        acc = {
            "bufferView": self._view(buf.tobytes(), target),
            "byteOffset": 0,
            "componentType": component,
            "count": len(buf) // comp,
            "type": kind,
        }
        if minmax:
            acc["min"], acc["max"] = minmax
        self.accessors.append(acc)
        return len(self.accessors) - 1


class Writer:
    """Collects meshes and empties, writes one pack-shaped GLB."""

    def __init__(self, generator: str, extras: dict | None = None) -> None:
        self.generator = generator
        self.extras = extras or {}
        self._meshes: list[tuple[str, list, list, list, list]] = []
        self._empties: list[tuple[str, tuple[float, float, float]]] = []

    def add_mesh(self, name, verts, normals, uvs, indices) -> None:
        """One mesh node. `verts`/`normals` are flat [x,y,z,...], `uvs` flat [u,v,...],
        `indices` a flat triangle list. Lengths are checked here, because a wrong length
        would otherwise surface as garbage triangles three tools later."""
        if len(verts) % 3 or len(verts) != len(normals):
            raise ValueError(f"mesh {name!r}: verts {len(verts)} vs normals {len(normals)}")
        if len(uvs) * 3 != len(verts) * 2:
            raise ValueError(f"mesh {name!r}: {len(verts)//3} verts vs {len(uvs)//2} uvs")
        if len(indices) % 3:
            raise ValueError(f"mesh {name!r}: {len(indices)} indices is not whole triangles")
        n = len(verts) // 3
        if indices and (min(indices) < 0 or max(indices) >= n):
            raise ValueError(f"mesh {name!r}: an index is outside 0..{n - 1}")
        self._meshes.append((name, list(verts), list(normals), list(uvs), list(indices)))

    def add_empty(self, name, xyz) -> None:
        """One named empty — a hit corner, a cortex, a hook point — as a mesh-less node
        with a translation only, exactly the shape src/shared/anchors.rs reads."""
        x, y, z = xyz
        self._empties.append((name, (float(x), float(y), float(z))))

    def document(self) -> tuple[dict, bytes]:
        """The glTF JSON and BIN chunk, without touching disk."""
        out = _Bin()
        meshes: list[dict] = []
        nodes: list[dict] = []

        for name, verts, normals, uvs, indices in self._meshes:
            # Positions go through float32 BEFORE min/max, or the declared bounds can sit
            # a ulp inside the data (the glb_merge lesson, kept on purpose).
            pos = list(array.array("f", verts))
            lo = [min(pos[a::3]) for a in range(3)]
            hi = [max(pos[a::3]) for a in range(3)]
            component = USHORT if (len(pos) // 3) - 1 <= USHORT_MAX else UINT
            prim = {
                "attributes": {
                    "POSITION": out.add(pos, FLOAT, "VEC3", ARRAY_BUFFER, (lo, hi)),
                    "NORMAL": out.add(normals, FLOAT, "VEC3", ARRAY_BUFFER),
                    "TEXCOORD_0": out.add(uvs, FLOAT, "VEC2", ARRAY_BUFFER),
                },
                "indices": out.add(indices, component, "SCALAR", ELEMENT_ARRAY_BUFFER),
                "mode": TRIANGLES,
                "material": 0,
            }
            meshes.append({"name": name, "primitives": [prim]})
            nodes.append({"name": name, "mesh": len(meshes) - 1})

        for name, xyz in self._empties:
            nodes.append({"name": name, "translation": list(xyz)})

        image_view = out._view(_palette_png(), None)
        nodes.append({"name": "root", "children": list(range(len(nodes)))})

        doc = {
            "asset": {"version": "2.0", "generator": self.generator, "extras": dict(self.extras)},
            "scene": 0,
            "scenes": [{"name": "scene", "nodes": [len(nodes) - 1]}],
            "nodes": nodes,
            "meshes": meshes,
            "materials": [
                {
                    "name": "palette",
                    "pbrMetallicRoughness": {
                        "baseColorTexture": {"index": 0},
                        "metallicFactor": 0.0,
                        "roughnessFactor": 0.9,
                    },
                }
            ],
            "textures": [{"name": "palette", "sampler": 0, "source": 0}],
            "images": [{"name": "palette", "mimeType": "image/png", "bufferView": image_view}],
            "samplers": [
                {
                    "magFilter": NEAREST,
                    "minFilter": NEAREST,
                    "wrapS": CLAMP_TO_EDGE,
                    "wrapT": CLAMP_TO_EDGE,
                }
            ],
            "accessors": out.accessors,
            "bufferViews": out.views,
            "buffers": [{"byteLength": len(out.blob) + (-len(out.blob) % 4)}],
        }
        return doc, bytes(out.blob)

    def bytes(self) -> bytes:
        doc, blob = self.document()
        return write_glb_bytes(doc, blob)

    def write(self, path) -> bytes:
        data = self.bytes()
        Path(path).write_bytes(data)
        return data
