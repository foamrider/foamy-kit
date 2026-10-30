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


def write_png(path, pixels, alpha=True):
    height, width = len(pixels), len(pixels[0])
    raw = b"".join(b"\x00" + b"".join(bytes(p if alpha else p[:3]) for p in row) for row in pixels)
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    header = struct.pack(">IIBBBBB", width, height, 8, 6 if alpha else 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def grid(colour, w=8, h=6):
    return [[colour for _ in range(w)] for _ in range(h)]


def main():
    ok = True
    base = Path(tempfile.mkdtemp(prefix="foamy-kit-compare-"))
    try:
        p = lambda name: base / name
        write_png(p("a.png"), grid((10, 20, 30, 255)))
        write_png(p("same.png"), grid((10, 20, 30, 255)))
        rgb = grid((10, 20, 30, 255)); rgb[2][3] = (10, 20, 31, 255); write_png(p("rgb.png"), rgb)
        alpha = grid((10, 20, 30, 255)); alpha[1][1] = (10, 20, 30, 128); write_png(p("alpha.png"), alpha)
        write_png(p("clear1.png"), grid((0, 0, 0, 0)))
        write_png(p("clear2.png"), grid((200, 100, 50, 0)))
        write_png(p("opaque-rgb.png"), grid((10, 20, 30, 255)), alpha=False)
        write_png(p("small.png"), grid((10, 20, 30, 255), 4, 4))

        ok &= report("identical images are identical", compare.compare(p("a.png"), p("same.png"))["identical"])
        r = compare.compare(p("a.png"), p("rgb.png"))
        ok &= report("an RGB-only change is a difference", not r["identical"] and r["pixels"] == 1 and r["bbox"] == (3, 2, 3, 2), str(r))
        r = compare.compare(p("a.png"), p("alpha.png"))
        ok &= report("an alpha-only change is a difference", not r["identical"] and r["pixels"] == 1, str(r))
        ok &= report("fully transparent pixels compare equal whatever their hidden RGB",
                     compare.compare(p("clear1.png"), p("clear2.png"))["identical"])
        ok &= report("transparent vs opaque is a difference", not compare.compare(p("clear1.png"), p("a.png"))["identical"])
        ok &= report("RGB and RGBA files with the same visible pixels are identical",
                     compare.compare(p("a.png"), p("opaque-rgb.png"))["identical"])
        ok &= report("different sizes differ", not compare.compare(p("a.png"), p("small.png"))["identical"])
        ok &= report("--tolerance absorbs small channel noise", compare.compare(p("a.png"), p("rgb.png"), tolerance=1)["identical"])

        old, new = base / "old", base / "new"
        old.mkdir(); new.mkdir()
        for name in ("a.png", "rgb.png"):
            shutil.copyfile(p("a.png"), old / name)
        shutil.copyfile(p("a.png"), new / "a.png"); shutil.copyfile(p("rgb.png"), new / "rgb.png"); shutil.copyfile(p("a.png"), new / "extra.png")
        run = lambda *args: subprocess.run([sys.executable, "-I", str(KIT_ROOT / "preview/compare.py"), *map(str, args)],
                                           capture_output=True, text=True)
        same = run(p("a.png"), p("same.png"))
        diff = run(old, new)
        ok &= report("CLI: identical files exit 0", same.returncode == 0 and "identical" in same.stdout, same.stdout.strip())
        ok &= report("CLI: directories report each file and exit 1 on any difference",
                     diff.returncode == 1 and "a.png: identical" in diff.stdout and "rgb.png: 1 pixel(s) differ" in diff.stdout
                     and "extra.png: only in new" in diff.stdout, diff.stdout.strip().replace("\n", "; "))
        (base / "bad.png").write_bytes(b"nope")
        bad = run(p("a.png"), base / "bad.png")
        ok &= report("CLI: unreadable input exits 2", bad.returncode == 2)
        # A real render: the demo card vs itself and vs its screen shot.
        out = KIT_ROOT / "tests/out/preview/4.5"
        if (out / "devices.png").exists() and (out / "empty.png").exists():
            ok &= report("real renders: a card equals itself, differs from another state",
                         compare.compare(out / "devices.png", out / "devices.png")["identical"]
                         and not compare.compare(out / "devices.png", out / "settings.png")["identical"])
    finally:
        shutil.rmtree(base, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
