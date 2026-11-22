#!/usr/bin/env python3
"""preview/compare.py: RGB and alpha both count; invisible RGB under full
transparency doesn't; RGB vs RGBA files; sizes; directories; exit codes."""

import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, report  # noqa: E402

sys.path.insert(0, str(KIT_ROOT / "preview"))
import compare  # noqa: E402


def paeth(a, b, c):
    """The PNG specification's Paeth predictor, with its tie order (a, b, c)."""
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def write_png(path, pixels, alpha=True, filters=None, split=False):
    """An 8-bit RGBA (or RGB) PNG. `filters` gives one PNG filter type
    (0-4) per row, encoded as the specification says (default: all 0);
    `split` writes the image data as two IDAT chunks. Qt and other encoders
    pick filters per row, so a reader must undo all five types."""
    height, width = len(pixels), len(pixels[0])
    channels = 4 if alpha else 3
    filters = filters or [0] * height
    raw, previous = b"", bytes(width * channels)
    for row, kind in zip(pixels, filters, strict=True):
        line = b"".join(bytes(p[:channels]) for p in row)
        encoded = bytearray()
        for i, x in enumerate(line):
            a = line[i - channels] if i >= channels else 0
            b = previous[i]
            c = previous[i - channels] if i >= channels else 0
            encoded.append((x - (0, a, b, (a + b) // 2, paeth(a, b, c))[kind]) & 255)
        raw += bytes([kind]) + encoded
        previous = line

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width, height, 8, 6 if alpha else 2, 0, 0, 0)
    data = zlib.compress(raw)
    cut = len(data) // 2 if split else len(data)
    idat = chunk(b"IDAT", data[:cut]) + (chunk(b"IDAT", data[cut:]) if split else b"")
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + idat + chunk(b"IEND", b""))


def grid(colour, w=8, h=6):
    return [[colour for _ in range(w)] for _ in range(h)]


def main():
    ok = True
    base = Path(tempfile.mkdtemp(prefix="foamy-kit-compare-"))
    try:

        def p(name):
            return base / name

        write_png(p("a.png"), grid((10, 20, 30, 255)))
        write_png(p("same.png"), grid((10, 20, 30, 255)))
        rgb = grid((10, 20, 30, 255))
        rgb[2][3] = (10, 20, 31, 255)
        write_png(p("rgb.png"), rgb)
        alpha = grid((10, 20, 30, 255))
        alpha[1][1] = (10, 20, 30, 128)
        write_png(p("alpha.png"), alpha)
        write_png(p("clear1.png"), grid((0, 0, 0, 0)))
        write_png(p("clear2.png"), grid((200, 100, 50, 0)))
        write_png(p("opaque-rgb.png"), grid((10, 20, 30, 255)), alpha=False)
        write_png(p("small.png"), grid((10, 20, 30, 255), 4, 4))

        ok &= report("identical images are identical", compare.compare(p("a.png"), p("same.png"))["identical"])
        r = compare.compare(p("a.png"), p("rgb.png"))
        ok &= report(
            "an RGB-only change is a difference",
            not r["identical"] and r["pixels"] == 1 and r["bbox"] == (3, 2, 3, 2),
            str(r),
        )
        r = compare.compare(p("a.png"), p("alpha.png"))
        ok &= report("an alpha-only change is a difference", not r["identical"] and r["pixels"] == 1, str(r))
        ok &= report(
            "fully transparent pixels compare equal whatever their hidden RGB",
            compare.compare(p("clear1.png"), p("clear2.png"))["identical"],
        )
        ok &= report(
            "transparent vs opaque is a difference", not compare.compare(p("clear1.png"), p("a.png"))["identical"]
        )
        ok &= report(
            "RGB and RGBA files with the same visible pixels are identical",
            compare.compare(p("a.png"), p("opaque-rgb.png"))["identical"],
        )
        ok &= report("different sizes differ", not compare.compare(p("a.png"), p("small.png"))["identical"])
        ok &= report(
            "--tolerance absorbs small channel noise",
            compare.compare(p("a.png"), p("rgb.png"), tolerance=1)["identical"],
        )
        ok &= report(
            "--tolerance 1 still sees a larger change",
            not compare.compare(p("a.png"), p("alpha.png"), tolerance=1)["identical"],
        )

        # Every PNG filter type, the image data in two chunks: a reader that
        # undoes one filter wrongly sees a different picture.
        varied = [[(x * 30, y * 40 + x, (x + y) * 15, 255 - x * 10) for x in range(8)] for y in range(6)]
        # Paeth ties in the red channel of row 4 (a Paeth row): at x = 1 the
        # up and upper-left guesses tie (the specification picks up), at
        # x = 3 the left and upper-left guesses tie (it picks left).
        for x, y, red in ((0, 3, 100), (1, 3, 80), (2, 3, 100), (3, 3, 110), (0, 4, 110), (2, 4, 80)):
            varied[y][x] = (red, *varied[y][x][1:])
        changed = [row[:] for row in varied]
        changed[4][5] = (1, 2, 3, 255)
        for alpha in (True, False):
            kind = "RGBA" if alpha else "RGB"
            write_png(p("plain.png"), varied, alpha=alpha)
            write_png(p("filtered.png"), varied, alpha=alpha, filters=[0, 1, 2, 3, 4, 4], split=True)
            write_png(p("filtered-changed.png"), changed, alpha=alpha, filters=[0, 1, 2, 3, 4, 4], split=True)
            r = compare.compare(p("plain.png"), p("filtered.png"))
            ok &= report(
                f"{kind}: filters Sub, Up, Average and Paeth decode to the same pixels", r["identical"], str(r)
            )
            r = compare.compare(p("plain.png"), p("filtered-changed.png"))
            ok &= report(
                f"{kind}: one changed pixel in a filtered image is found",
                not r["identical"] and r["pixels"] == 1 and r["bbox"] == (5, 4, 5, 4),
                str(r),
            )

        old, new = base / "old", base / "new"
        old.mkdir()
        new.mkdir()
        for name in ("a.png", "rgb.png"):
            shutil.copyfile(p("a.png"), old / name)
        shutil.copyfile(p("a.png"), new / "a.png")
        shutil.copyfile(p("rgb.png"), new / "rgb.png")
        shutil.copyfile(p("a.png"), new / "extra.png")

        def run(*args):
            return subprocess.run(
                [sys.executable, "-I", str(KIT_ROOT / "preview/compare.py"), *map(str, args)],
                capture_output=True,
                text=True,
            )

        same = run(p("a.png"), p("same.png"))
        diff = run(old, new)
        ok &= report(
            "CLI: identical files exit 0", same.returncode == 0 and "identical" in same.stdout, same.stdout.strip()
        )
        ok &= report(
            "CLI: directories report each file and exit 1 on any difference",
            diff.returncode == 1
            and "a.png: identical" in diff.stdout
            and "rgb.png: 1 pixel(s) differ" in diff.stdout
            and "extra.png: only in new" in diff.stdout,
            diff.stdout.strip().replace("\n", "; "),
        )
        (base / "bad.png").write_bytes(b"nope")
        bad = run(p("a.png"), base / "bad.png")
        ok &= report("CLI: unreadable input exits 2", bad.returncode == 2)
        # A damaged PNG is unreadable (exit 2 with the reason), never a
        # traceback (exit 1, "different") or a guessed picture.
        header = (8).to_bytes(4, "big") + (6).to_bytes(4, "big") + bytes([8, 6, 0, 0, 0])
        signature = b"\x89PNG\r\n\x1a\n"

        def chunk(kind, data):
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

        whole = b"".join(b"\x00" + bytes(8 * 4) for _ in range(6))
        for name, data, reason in (
            ("image data shorter than its rows", whole[:-10], "image data"),
            ("an unknown filter type", b"\x05" + whole[1:], "filter type 5"),
            ("a header cut short", b"", "truncated"),
        ):
            png = signature + chunk(b"IHDR", header)
            png = png[:20] if reason == "truncated" else png + chunk(b"IDAT", zlib.compress(data)) + chunk(b"IEND", b"")
            (base / "damaged.png").write_bytes(png)
            damaged = run(p("a.png"), base / "damaged.png")
            ok &= report(
                f"CLI: a PNG with {name} exits 2 and says why",
                damaged.returncode == 2 and "unreadable" in damaged.stderr and reason in damaged.stderr,
                f"exit {damaged.returncode}: {(damaged.stdout + damaged.stderr).strip()[-200:]}",
            )
        for name, tail in (
            ("cut inside a chunk's length", b"\x00\x00"),
            ("with a chunk longer than the file", chunk(b"IDAT", zlib.compress(whole))[:-8]),
        ):
            (base / "damaged.png").write_bytes(signature + chunk(b"IHDR", header) + tail)
            damaged = run(p("a.png"), base / "damaged.png")
            ok &= report(
                f"CLI: a PNG {name} exits 2 and says why",
                damaged.returncode == 2 and "truncated chunk" in damaged.stderr,
                f"exit {damaged.returncode}: {(damaged.stdout + damaged.stderr).strip()[-200:]}",
            )
    finally:
        shutil.rmtree(base, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
