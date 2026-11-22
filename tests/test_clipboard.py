#!/usr/bin/env python3
"""kit/clipboard.sh through hostenv.clipboard_fakes(), the stand-ins plugin
clipboard tests share: the paste's bounds (size, NUL, single line or
`multiline` with its line breaks kept, the 2 s deadline, a producer that
ignores SIGTERM), the exit codes FoamyClipboard maps to its messages, that
a stopped or killed read ends whole, and that a paste which works still
works when the machine is slow. Shell only: no Quickshell or Omarchy host,
so tests/suite.sh --ci runs it too."""

import contextlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, report  # noqa: E402

sys.path.insert(0, str(KIT_ROOT / "preview"))
import hostenv  # noqa: E402

HELPER = KIT_ROOT / "kit/clipboard.sh"


def paste(env, mode, selection="clipboard", *extra):
    """(result, seconds) of one clipboard.sh run in `mode`; `extra` follows
    the selection (multiline)."""
    Path(env["TEST_CLIPBOARD_STATE"]).write_text(mode)
    started = time.monotonic()
    deadline = mode in hostenv.CLIPBOARD_DEADLINE_MODES
    result = subprocess.run(
        ["bash", str(HELPER), selection, *extra], env=env, capture_output=True, timeout=10 if deadline else 90
    )
    return result, time.monotonic() - started


def stopped(pid, within=2.0):
    """True once `pid` is gone or a zombie, waiting at most `within` seconds."""
    deadline = time.monotonic() + within
    while time.monotonic() < deadline:
        try:
            if Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] == "Z":
                return True
        except (FileNotFoundError, ProcessLookupError):
            return True
        time.sleep(0.01)
    return False


def catches_term(pid):
    """True when `pid` has a handler for SIGTERM: clipboard.sh's trap is set.
    The trap sets TERM, INT and HUP in one command, and only the trap
    catches TERM (bash may hold its own INT handler before that)."""
    try:
        status = Path(f"/proc/{pid}/status").read_text()
    except FileNotFoundError:
        return False
    caught = next(int(line.split()[1], 16) for line in status.splitlines() if line.startswith("SigCgt:"))
    return bool(caught & 1 << (signal.SIGTERM - 1))


def signalled(env, signum):
    """(exit code or the reason no signal was sent, stdout, stderr, producer
    pid, producer stopped within 1 s) for a `loaded` paste whose
    clipboard.sh gets `signum` once its trap is set. The stand-in timeout gives `loaded` 60 s and its producer runs
    2.5 s, so only clipboard.sh's own kill of the whole read ends it within
    1 s."""
    state = Path(env["TEST_CLIPBOARD_STATE"])
    state.write_text("loaded")
    Path(f"{state}.pid").unlink(missing_ok=True)
    # Files, not pipes: a producer that outlives clipboard.sh would hold a
    # pipe open, and the wait below must still end with clipboard.sh.
    out, err = Path(f"{state}.out"), Path(f"{state}.err")
    with out.open("wb") as stdout, err.open("wb") as stderr:
        proc = subprocess.Popen(["bash", str(HELPER), "clipboard"], env=env, stdout=stdout, stderr=stderr)
    pid_file = Path(f"{state}.pid")
    try:
        deadline = time.monotonic() + 5
        # The stand-in empties the pid file before it writes its pid.
        producer = ""
        while not (producer and catches_term(proc.pid)):
            if proc.poll() is not None:
                return f"clipboard.sh exited first with {proc.returncode}", b"", b"", producer or None, False
            if time.monotonic() > deadline:
                return "the trap and the producer pid not seen within 5 s", b"", b"", producer or None, False
            time.sleep(0.01)
            producer = pid_file.read_text().strip() if pid_file.exists() else ""
        os.kill(proc.pid, signum)
        try:
            code = proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            code = "none within 2 s"
        return code, out.read_bytes(), err.read_bytes(), producer, stopped(producer, within=1.0)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()


def read_processes(marker):
    """Pids of the live processes whose environment holds `marker`: the
    clipboard.sh run that got it and every process it started."""
    pids = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            # A zombie's environ reads empty, so only live processes count.
            if marker in (entry / "environ").read_bytes().split(b"\0"):
                pids.append(int(entry.name))
        except OSError:
            continue
    return pids


def killed(env, early, group_signal=None):
    """The pids of a `loaded` paste's processes still alive 1 s after its
    clipboard.sh got SIGKILL (no trap runs: Quickshell kills it so when its
    Process is destroyed), or the reason no kill was sent. With `early`, the
    kill comes as soon as clipboard.sh has started a child, else once the
    producer runs. With `group_signal`, clipboard.sh leads its own process
    group and that signal goes to the whole group instead (a closed
    terminal, a session that ends), which also reaches the processes
    clipboard.sh started in its group. The stand-in timeout gives `loaded`
    60 s and its producer runs 2.5 s, so only clipboard.sh's own kill of the
    read ends it within 1 s."""
    state = Path(env["TEST_CLIPBOARD_STATE"])
    state.write_text("loaded")
    pid_file = Path(f"{state}.pid")
    pid_file.unlink(missing_ok=True)
    tag = uuid.uuid4().hex
    marker = f"FOAMY_TEST_READ={tag}".encode()
    proc = subprocess.Popen(
        ["bash", str(HELPER), "clipboard"],
        env=dict(env, FOAMY_TEST_READ=tag),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=group_signal is not None,
    )
    children = Path(f"/proc/{proc.pid}/task/{proc.pid}/children")
    try:
        deadline = time.monotonic() + 5
        while not (children.read_text().strip() if early else pid_file.exists() and pid_file.read_text().strip()):
            if proc.poll() is not None:
                return f"clipboard.sh exited first with {proc.returncode}"
            if time.monotonic() > deadline:
                return "no child or producer seen within 5 s"
            # Early: poll without a pause, to kill as close to the start as possible.
            if not early:
                time.sleep(0.01)
        if group_signal is None:
            proc.kill()
        else:
            os.killpg(proc.pid, group_signal)
        proc.wait()
        deadline = time.monotonic() + 1
        while (left := read_processes(marker)) and time.monotonic() < deadline:
            time.sleep(0.01)
        return left
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        for pid in read_processes(marker):
            with contextlib.suppress(ProcessLookupError):
                os.kill(pid, signal.SIGKILL)


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
        # Exit 5 is what FoamyClipboard shows as "too large"; with an
        # endless stream, pipefail reports jq's 5 as the last failure.
        for mode in ("large", "nul", "stream"):
            result, _ = paste(env, mode)
            ok &= report(
                f"{mode}: refused with exit 5, with no output",
                result.returncode == 5 and result.stdout == b"" and result.stderr == b"",
                f"exit {result.returncode}",
            )
        # Not 5, 124 or 137, which FoamyClipboard shows as "too large" or
        # "timed out": a failing wl-paste is "Could not paste".
        code = paste(env, "failure")[0].returncode
        ok &= report("a failing wl-paste fails the paste", code not in (0, 5, 124, 137), f"exit {code}")

        # multiline (SafeTextArea): the same bounds, line breaks kept as "\n".
        for mode, selection, expected in (
            ("lines", "clipboard", "one\ntwo\nthree"),
            ("breaks", "primary", "a\nb\n\nc\nd\n"),
            ("unicode", "clipboard", "/home/test/Blåbær 📁"),
            ("limit", "clipboard", "x" * 16384),
        ):
            result, _ = paste(env, mode, selection, "multiline")
            got = json.loads(result.stdout) if result.returncode == 0 and result.stdout else None
            ok &= report(
                f"multiline {mode}: line breaks kept as \\n", got == expected, f"exit {result.returncode}, {got!r:.60}"
            )
        args = json.loads(Path(state + ".args").read_text())
        ok &= report(
            "multiline passes the same wl-paste options", args == ["--no-newline", "--type", "text"], str(args)
        )
        result, _ = paste(env, "breaks")
        ok &= report(
            "without multiline, the same breaks are spaces",
            result.returncode == 0 and json.loads(result.stdout) == "a b  c d  ",
            result.stdout.decode(errors="replace").strip(),
        )
        for mode in ("large", "nul", "stream"):
            result, _ = paste(env, mode, "clipboard", "multiline")
            ok &= report(
                f"multiline {mode}: refused with exit 5, with no output",
                result.returncode == 5 and result.stdout == b"" and result.stderr == b"",
                f"exit {result.returncode}",
            )
        for extra in (["lines"], ["multiline", "multiline"], ["", "multiline"]):
            ok &= report(
                f"clipboard {' '.join(map(repr, extra))} is refused",
                paste(env, "normal", "clipboard", *extra)[0].returncode == 2,
            )
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

        # The stand-in stretches only clipboard.sh's own read: another command
        # under the same deadline (a plugin's probe, `bash -lc …`) keeps 2 s.
        # At its deadline `timeout --signal=KILL` kills its whole group,
        # itself included, so it ends by SIGKILL.
        Path(state).write_text("normal")
        started = time.monotonic()
        other = subprocess.run(
            ["timeout", "--signal=KILL", "2s", "bash", "-c", "sleep 3"], env=env, capture_output=True, timeout=90
        )
        seconds = time.monotonic() - started
        ok &= report(
            "the stand-in timeout keeps another command's 2 s deadline",
            other.returncode == -signal.SIGKILL,
            f"exit {other.returncode} after {seconds:.1f}s",
        )

        # The caller stops a read (Quickshell sends TERM): the whole read
        # ends at once, producer included, with exit 143 and no output.
        for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            code, out, err, producer, gone = signalled(env, signum)
            ok &= report(
                f"{signum.name} to clipboard.sh kills the whole read",
                code == 143 and out == b"" and err == b"" and gone,
                f"exit {code}, output {out + err!r:.40}, producer {producer} stopped within 1 s: {gone}",
            )

        # clipboard.sh itself killed (SIGKILL: a destroyed Process), right
        # after it starts or in the middle of the read: no part of the read
        # outlives it by more than a moment.
        for early, when in ((True, "at its start"), (False, "mid-read")):
            left = killed(env, early)
            ok &= report(f"SIGKILL to clipboard.sh {when} kills the whole read", left == [], f"still running: {left}")

        # A stop sent to clipboard.sh's whole process group mid-read: the
        # processes of that group end together, and the read still ends.
        for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            left = killed(env, False, signum)
            ok &= report(
                f"{signum.name} to clipboard.sh's process group kills the whole read",
                left == [],
                f"still running: {left}",
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
