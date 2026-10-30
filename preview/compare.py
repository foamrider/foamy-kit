#!/usr/bin/env python3
"""Compare screenshots: are two PNGs (or two directories of PNGs) the same picture?

  preview/compare.py old.png new.png
  preview/compare.py old-dir/ new-dir/          # pairs files by name
  preview/compare.py a.png b.png --tolerance 2  # per-channel slack (antialiasing)

Pixels are compared on all four channels, RGB and alpha. Two fully
transparent pixels are equal whatever RGB they carry (it isn't visible);
otherwise any channel differing by more than --tolerance is a difference.
RGB and RGBA files compare as opaque vs. their alpha. Never compare alpha
alone, and never drop alpha before comparing: a transparent corner and an
opaque one are different pictures.

Exit status: 0 identical, 1 different (or sizes differ, or a file is
missing on one side), 2 unreadable input. Standard library only.
"""
import argparse
import struct
import sys
import zlib
from pathlib import Path


def read_png(path):
    """(width, height, rows) for an 8-bit RGB/RGBA/grey/grey-alpha PNG; rows
    are lists of (r, g, b, a) tuples. Raises ValueError for anything else."""
    data = Path(path).read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path}: not a PNG")
    width, height, depth, colour, _, _, interlace = struct.unpack(">IIBBBBB", data[16:29])
    if depth != 8 or interlace != 0 or colour not in (0, 2, 4, 6):
        raise ValueError(f"{path}: only 8-bit non-interlaced grey/RGB(A) PNGs are supported")
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[colour]
    offset, chunks = 8, b""
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        if data[offset + 4:offset + 8] == b"IDAT":
            chunks += data[offset + 8:offset + 8 + length]
        offset += 12 + length
    raw = zlib.decompress(chunks)
    stride = width * channels
    rows, previous = [], bytearray(stride)
    for row in range(height):
        start = row * (stride + 1)
        kind, line = raw[start], bytearray(raw[start + 1:start + 1 + stride])
        for i in range(stride):
            left = line[i - channels] if i >= channels else 0
            up = previous[i]
            corner = previous[i - channels] if i >= channels else 0
            if kind == 1:
                line[i] = (line[i] + left) & 255
            elif kind == 2:
                line[i] = (line[i] + up) & 255
            elif kind == 3:
                line[i] = (line[i] + (left + up) // 2) & 255
            elif kind == 4:
                p = left + up - corner
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - corner)
                line[i] = (line[i] + (left if pa <= pb and pa <= pc else up if pb <= pc else corner)) & 255
        previous = line
        pixels = []
        for x in range(width):
            v = line[x * channels:(x + 1) * channels]
            if channels == 1:
                pixels.append((v[0], v[0], v[0], 255))
            elif channels == 2:
                pixels.append((v[0], v[0], v[0], v[1]))
            elif channels == 3:
                pixels.append((v[0], v[1], v[2], 255))
            else:
                pixels.append((v[0], v[1], v[2], v[3]))
        rows.append(pixels)
    return width, height, rows


def same_pixel(a, b, tolerance=0):
    if a[3] == 0 and b[3] == 0:
        return True
    return all(abs(x - y) <= tolerance for x, y in zip(a, b))


def compare(a, b, tolerance=0):
    """{'identical': bool, 'reason': str, 'pixels': n, 'bbox': (x0, y0, x1, y1) | None}."""
    wa, ha, ra = read_png(a)
    wb, hb, rb = read_png(b)
    if (wa, ha) != (wb, hb):
        return {"identical": False, "reason": f"size {wa}x{ha} vs {wb}x{hb}", "pixels": None, "bbox": None}
    count, x0, y0, x1, y1 = 0, wa, ha, -1, -1
    for y in range(ha):
        for x in range(wa):
            if not same_pixel(ra[y][x], rb[y][x], tolerance):
                count += 1
                x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)
    if count == 0:
        return {"identical": True, "reason": "identical", "pixels": 0, "bbox": None}
    return {"identical": False, "reason": f"{count} pixel(s) differ", "pixels": count, "bbox": (x0, y0, x1, y1)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("a")
    parser.add_argument("b")
    parser.add_argument("--tolerance", type=int, default=0)
    args = parser.parse_args(argv)
    a, b = Path(args.a), Path(args.b)
    if a.is_dir() != b.is_dir():
        print("compare two files or two directories", file=sys.stderr)
        return 2
    pairs = [(a, b)] if not a.is_dir() else [
        (a / name, b / name) for name in sorted({p.name for p in a.glob("*.png")} | {p.name for p in b.glob("*.png")})]
    status = 0
    for left, right in pairs:
        if not left.exists() or not right.exists():
            print(f"{left.name}: only in {'new' if not left.exists() else 'old'}")
            status = max(status, 1)
            continue
        try:
            result = compare(left, right, args.tolerance)
        except (OSError, ValueError, zlib.error) as error:
            print(f"{left.name}: unreadable: {error}", file=sys.stderr)
            status = 2
            continue
        bbox = f" in {result['bbox']}" if result["bbox"] else ""
        print(f"{left.name}: {result['reason']}{bbox}")
        if not result["identical"]:
            status = max(status, 1)
    return status


if __name__ == "__main__":
    sys.exit(main())
