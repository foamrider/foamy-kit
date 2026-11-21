#!/usr/bin/env python3
"""Runtime checks on 4.5: FoamyI18n (English, Danish and Arabic), FoamyMotion,
FoamyPalette (and a live theme switch), FoamyStyle, FoamyCursor, FoamyShared
leader election and leader takeover across three bar instances, and FoamyIpc
over both the IpcRegistry socket path and `qs ipc`."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, report, synced_demo  # noqa: E402


def qs_ipc(run, *call):
    """`qs ipc call` to the run's own instance; None when it fails."""
    by_id = Path(run.env["XDG_RUNTIME_DIR"]) / "quickshell/by-id"
    ids = [p.name for p in by_id.iterdir()] if by_id.is_dir() else []
    if not ids:
        return None
    result = subprocess.run(
        ["qs", "ipc", "-i", ids[0], "call", *call], env=run.env, capture_output=True, text=True, timeout=10
    )
    return result.stdout.strip() if result.returncode == 0 else None


def run(host, lang):
    plugin = synced_demo()
    shell = (KIT_ROOT / "tests/qml/Runtime.qml").read_text()
    r = harness.Run(host, shell, plugin=plugin, language=lang, prefix=f"foamy-kit-runtime-{host}-{lang}-")
    r.env["FOAMY_LANG"] = lang
    # Only a bound: the scene holds after READY until the finish call below.
    r.env["FOAMY_HOLD_MS"] = "15000"
    r.start()
    status = None
    try:
        if r.wait_for_log("FOAMY READY", 20):
            status = qs_ipc(r, "foamy.kit-demo", "status")
            qs_ipc(r, "foamy.test-runtime", "finish")
        r.wait(60)
    finally:
        r.stop()
    ok_ipc = False
    try:
        ok_ipc = status is not None and json.loads(status).get("leader") is True
    except ValueError:
        pass
    r.ok = "FOAMY DONE" in r.log and "FOAMY FAIL" not in r.log and not any(m in r.log for m in harness.FAILURE_MARKERS)
    detail = next((line.split("qml: ", 1)[-1] for line in r.log.splitlines() if "FOAMY RESULT" in line), "no result")
    ok = report(f"runtime {host} {lang}", r.ok, detail)
    ok = report(f"qs ipc call foamy.kit-demo status ({host})", ok_ipc, status or "no reply") and ok
    # qs ipc exits 0 for a missing target, so the scene says what ended it.
    # Without the call it would only end at the FOAMY_HOLD_MS bound.
    ended = next((line.split("FOAMY END ", 1)[1] for line in r.log.splitlines() if "FOAMY END " in line), "nothing")
    ok = report(f"the scene ends on the finish call ({host} {lang})", ended == "by the finish call", ended) and ok
    if not ok:
        print("\n".join("    " + line for line in (r.failures() or r.log.splitlines()[-30:])))
    else:
        r.cleanup()
        shutil.rmtree(plugin.parent, ignore_errors=True)
    return ok


def main():
    results = [run(host, lang) for host in harness.available_hosts(what="runtime") for lang in ("en", "da", "ar")]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
