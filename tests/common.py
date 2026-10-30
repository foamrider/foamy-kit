"""Shared helpers for foamy-kit tests."""
import shutil
import sys
import tempfile
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT_ROOT / "tools"))
sys.path.insert(0, str(KIT_ROOT / "preview"))
import foamykit  # noqa: E402
import harness  # noqa: E402

FIXTURES = KIT_ROOT / "tests/fixtures"
PLUGINS = KIT_ROOT.parent


def synced_demo(components=None):
    """A temporary copy of the demo plugin with the kit synced into it."""
    base = Path(tempfile.mkdtemp(prefix="foamy-kit-demo-"))
    plugin = base / "foamy-kit-demo"
    shutil.copytree(FIXTURES / "demo-plugin", plugin)
    foamykit.sync_plugin(plugin, components, out=lambda *_: None)
    return plugin


def report(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'} {name}{': ' + detail if detail else ''}")
    return ok


def read_png(path):
    """(width, height, pixel(x, y) -> (r, g, b, a)) for an 8-bit RGB/RGBA PNG (stdlib only)."""
    import struct
    import zlib
    data = Path(path).read_bytes()
    width, height = struct.unpack(">II", data[16:24])
    colour = data[25]
    channels = {6: 4, 2: 3}[colour]
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
        rows.append(bytes(line))
        previous = line

    def pixel(x, y):
        values = rows[y][x * channels:(x + 1) * channels]
        return tuple(values) + ((255,) if channels == 3 else ())
    return width, height, pixel
