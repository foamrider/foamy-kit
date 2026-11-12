#!/usr/bin/env python3
"""kit/clipboard.sh through hostenv.clipboard_fakes(), the stand-ins plugin
clipboard tests share: the paste's bounds (size, NUL, single line, the 2 s
deadline, a producer that ignores SIGTERM) and that a paste which works
still works when the machine is slow. Shell only: no Quickshell or Omarchy
host, so tests/suite.sh --ci runs it too."""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, report  # noqa: E402

sys.path.insert(0, str(KIT_ROOT / "preview"))
import hostenv  # noqa: E402

HELPER = KIT_ROOT / "kit/clipboard.sh"


def paste(env, mode, selection="clipboard"):
    """(result, seconds) of one clipboard.sh run in `mode`."""
    Path(env["TEST_CLIPBOARD_STATE"]).write_text(mode)
    started = time.monotonic()
    deadline = mode in hostenv.CLIPBOARD_DEADLINE_MODES
    result = subprocess.run(
        ["bash", str(HELPER), selection], env=env, capture_output=True, timeout=10 if deadline else 90
    )
    return result, time.monotonic() - started


def stopped(pid):
    """True once `pid` is gone or a zombie (bounded wait)."""
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            if Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] == "Z":
                return True
        except (FileNotFoundError, ProcessLookupError):
            return True
        time.sleep(0.01)
    return False


def main():
    ok = True
    with tempfile.TemporaryDirectory(prefix="foamy-kit-clipboard-") as work:
        env = dict(os.environ, **hostenv.clipboard_fakes(Path(work) / "bin"))
        state = env["TEST_CLIPBOARD_STATE"]

        for mode, expected in (
            ("normal", "folder"),
            ("unicode", "/home/test/Blåbær 📁"),
            ("empty", ""),
            ("limit", "x" * 16384),
            ("delayed", "later"),
            ("lines", "one  two three"),
        ):
            result, _ = paste(env, mode)
            got = json.loads(result.stdout) if result.returncode == 0 and result.stdout else None
            ok &= report(
                f"{mode}: pasted as one bounded line", got == expected, f"exit {result.returncode}, {got!r:.60}"
            )

        result, _ = paste(env, "lines", "primary")
        args = json.loads(Path(state + ".args").read_text())
        ok &= report(
            "primary passes --primary to wl-paste",
            result.returncode == 0 and args == ["--no-newline", "--type", "text", "--primary"],
            str(args),
        )
        for mode in ("large", "nul", "stream"):
            result, _ = paste(env, mode)
            ok &= report(
                f"{mode}: refused, with no output",
                result.returncode != 0 and result.stdout == b"" and result.stderr == b"",
                f"exit {result.returncode}",
            )
        ok &= report("a failing wl-paste fails the paste", paste(env, "failure")[0].returncode != 0)
        ok &= report("an unknown selection is refused", paste(env, "normal", "secondary")[0].returncode == 2)

        # The deadline modes keep clipboard.sh's real 2 s.
        for mode in hostenv.CLIPBOARD_DEADLINE_MODES:
            result, seconds = paste(env, mode)
            pid = Path(state + ".pid").read_text()
            ok &= report(
                f"{mode}: killed at the 2 s deadline, producer included",
                result.returncode == 137 and seconds < 4 and stopped(pid),
                f"exit {result.returncode} after {seconds:.1f}s",
            )

        # Load: a paste that takes 2.5 s (a slow machine) still pastes with
        # the stand-in timeout, and is killed by the real one.
        result, seconds = paste(env, "loaded")
        ok &= report(
            "loaded: a slow paste that works still pastes",
            result.returncode == 0 and json.loads(result.stdout or "null") == "late",
            f"exit {result.returncode} after {seconds:.1f}s",
        )
        (Path(work) / "bin/timeout").unlink()
        result, seconds = paste(env, "loaded")
        ok &= report(
            "loaded, real timeout: the same paste dies at 2 s (why the stand-in exists)",
            result.returncode == 137 and seconds < 4,
            f"exit {result.returncode} after {seconds:.1f}s",
        )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
