#!/usr/bin/env python3
"""Runtime checks under both hosts: FoamyI18n (English on 4.0; Danish and
Arabic on 4.5), FoamyMotion, FoamyPalette, FoamyStyle, FoamyPrefs, FoamyCursor,
FoamyShared leader election across three bar instances, and FoamyIpc over
both the 4.5 IpcRegistry socket path and `qs ipc` (both versions)."""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, report, synced_demo  # noqa: E402


def qs_ipc(run, *call):
    by_id = Path(run.env["XDG_RUNTIME_DIR"]) / "quickshell/by-id"
    for _ in range(80):
        ids = [p.name for p in by_id.iterdir()] if by_id.is_dir() else []
        if ids and "FOAMY READY" in (run.base / "qs.log").read_text(errors="replace"):
            break
        time.sleep(0.1)
    else:
        return None
    result = subprocess.run(["qs", "ipc", "-i", ids[0], "call", *call], env=run.env, capture_output=True, text=True, timeout=10)
    return result.stdout.strip() if result.returncode == 0 else None


def run(host, lang):
    plugin = synced_demo()
    shell = (KIT_ROOT / "tests/qml/Runtime.qml").read_text()
    r = harness.Run(host, shell, plugin=plugin, language=lang, prefix=f"foamy-kit-runtime-{host}-{lang}-")
    r.env["FOAMY_LANG"] = lang
    r.env["FOAMY_HOLD_MS"] = "4000"
    log_path = r.base / "qs.log"
    process = subprocess.Popen(["qs", "-p", str(r.root), "--no-color"], env=r.env, stdout=log_path.open("w"),
                               stderr=subprocess.STDOUT, start_new_session=True)
    try:
        status = qs_ipc(r, "foamy.kit-demo", "status")
        process.wait(timeout=60)
    finally:
        if process.poll() is None:
            process.kill()
    r.log = log_path.read_text(errors="replace")
    ok_ipc = False
    try:
        ok_ipc = status is not None and json.loads(status).get("leader") is True
    except ValueError:
        pass
    r.ok = "FOAMY DONE" in r.log and "FOAMY FAIL" not in r.log and not any(m in r.log for m in harness.FAILURE_MARKERS)
    detail = next((l.split("qml: ", 1)[-1] for l in r.log.splitlines() if "FOAMY RESULT" in l), "no result")
    ok = report(f"runtime {host} {lang}", r.ok, detail)
    ok = report(f"qs ipc call foamy.kit-demo status ({host})", ok_ipc, status or "no reply") and ok
    if not ok:
        print("\n".join("    " + l for l in (r.failures() or r.log.splitlines()[-30:])))
    else:
        r.cleanup()
        shutil.rmtree(plugin.parent, ignore_errors=True)
    return ok


def main():
    results = [run("4.0", "en"), run("4.5", "en"), run("4.5", "da"), run("4.5", "ar")]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
