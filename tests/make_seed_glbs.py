"""Build deterministic seed GLBs for gate unit tests.

Three fixtures, all committed artifacts of the repo:
  ok_cube.glb            — 12-face box, no texture (trimesh)
  broken_watertight.glb  — box with one face removed (non-watertight)
  textured_tetra.glb     — hand-built GLB with an embedded PNG texture
                           (proves the stdlib JSON-chunk parser reads
                           accessors, bounds and texture refs correctly)
"""
from __future__ import annotations

import json
import os
import struct
import zlib

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def _png_bytes() -> bytes:
    def chunk(typ: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 2, 2, 8, 6, 0, 0, 0)
    row = b"\x00" + b"\xff\x00\x00\xff" * 2 + b"\x00" + b"\x00\xff\x00\xff" * 2
    idat = zlib.compress(row, 9)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def _pad(data: bytes, char: bytes) -> bytes:
    pad = (4 - len(data) % 4) % 4
    return data + char * pad


def build_textured_tetra(path: str) -> None:
    positions = [
        (1.0, 1.0, 1.0), (1.0, -1.0, -1.0), (-1.0, 1.0, -1.0), (-1.0, -1.0, 1.0),
    ]
    indices = [0, 1, 2, 0, 3, 1, 0, 2, 3, 1, 3, 2]
    pos_bytes = b"".join(struct.pack("<fff", *p) for p in positions)
    idx_bytes = b"".join(struct.pack("<H", i) for i in indices)
    png = _png_bytes()

    buf = pos_bytes + idx_bytes + png
    pos_len, idx_len = len(pos_bytes), len(idx_bytes)

    gltf = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "tetra"}],
        "meshes": [{"primitives": [{
            "attributes": {"POSITION": 0}, "indices": 1, "material": 0}]}],
        "materials": [{"pbrMetallicRoughness": {"baseColorTexture": {"index": 0}}}],
        "textures": [{"sampler": 0, "source": 0}],
        "images": [{"bufferView": 2, "mimeType": "image/png"}],
        "samplers": [{"magFilter": 9729, "minFilter": 9729}],
        "accessors": [
            {
                "bufferView": 0, "componentType": 5126, "count": 4, "type": "VEC3",
                "min": [-1.0, -1.0, -1.0], "max": [1.0, 1.0, 1.0],
            },
            {
                "bufferView": 1, "componentType": 5123, "count": 12, "type": "SCALAR",
            },
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": pos_len},
            {"buffer": 0, "byteOffset": pos_len, "byteLength": idx_len},
            {"buffer": 0, "byteOffset": pos_len + idx_len, "byteLength": len(png)},
        ],
        "buffers": [{"byteLength": len(buf)}],
    }

    js = _pad(json.dumps(gltf).encode("utf-8"), b" ")
    bn = _pad(buf, b"\x00")
    total = 12 + 8 + len(js) + 8 + len(bn)
    out = struct.pack("<III", 0x46546C67, 2, total)
    out += struct.pack("<II", len(js), 0x4E4F534A) + js
    out += struct.pack("<II", len(bn), 0x004E4942) + bn
    with open(path, "wb") as fh:
        fh.write(out)


def main() -> None:
    os.makedirs(FIXTURES, exist_ok=True)
    import trimesh

    box = trimesh.creation.box(extents=(1.0, 1.0, 1.0))
    box.export(os.path.join(FIXTURES, "ok_cube.glb"))

    broken = trimesh.creation.box(extents=(1.0, 1.0, 1.0))
    broken.update_faces([i != 0 for i in range(len(broken.faces))])
    broken.export(os.path.join(FIXTURES, "broken_watertight.glb"))

    build_textured_tetra(os.path.join(FIXTURES, "textured_tetra.glb"))
    print(f"fixtures written to {FIXTURES}")


if __name__ == "__main__":
    main()
