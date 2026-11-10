#!/usr/bin/env python3
"""How the kit's Process users end, on 4.5 and, with FOAMY_HOST_40, 4.0
(tests/qml/Lifecycle.qml): every way a FoamyPrefsQueue CLI save ends (exit
0, exit 1, can't start, hangs past the deadline, stopped, queue destroyed)
clears `saving`, rolls back and stays retryable, and its stderr is capped;
a FoamyPeerIpc call that can't start still calls done(). Fake omarchy and
omarchy-shell on PATH, never the real ones."""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, report, synced_demo  # noqa: E402

# The value is the last-but-one argument, JSON-quoted: "hang", "boom"...
FAKE_OMARCHY = """#!/bin/bash
printf '%s\\n' "omarchy $*" >> "$FOAMY_CALLS"
case "$*" in
  *'"hang'*) echo partial >&2; trap '' TERM; echo $$ >> "$FOAMY_BASE/hang.pids"; exec sleep 600 ;;
  *'"bigerr"'*) head -c 1000000 /dev/zero | tr '\\0' e >&2; exit 1 ;;
  *'"boom"'*) echo "fake failure" >&2; exit 1 ;;
  *'"slow"'*) sleep 30; exit 0 ;;
esac
sleep 0.1
exit 0
"""

# Executable, but exec fails (no such interpreter): a failed start that can
# never fall through to a real omarchy-shell later on PATH.
UNSTARTABLE = "#!/nonexistent/foamy-kit-interpreter\n"


def run(host):
    plugin = synced_demo()
    shell = (KIT_ROOT / "tests/qml/Lifecycle.qml").read_text()
    r = harness.Run(host, shell, plugin=plugin, prefix=f"foamy-kit-lifecycle-{host}-", fakebin={"omarchy": FAKE_OMARCHY, "omarchy-shell": UNSTARTABLE})
    calls = r.base / "calls.log"
    calls.write_text("")
    r.env.update({"FOAMY_CALLS": str(calls), "FOAMY_BASE": str(r.base), "QML_XHR_ALLOW_FILE_READ": "1"})
    r.run(timeout=60)
    detail = next((l.split("qml: ", 1)[-1] for l in r.log.splitlines() if "FOAMY RESULT" in l), "no result")
    ok = report(f"lifecycle {host}", r.ok, detail)
    if not ok:
        print("\n".join("    " + l for l in (r.failures() or r.log.splitlines()[-30:])))
    # The warning names the cause and carries at most stderrLimit characters.
    warnings = [l for l in r.log.splitlines() if "foamy-kit: saving" in l]
    causes = ["(exit 1): fake failure", "(the command couldn't start)", "(no exit after 1500 ms): partial",
              "(exit 1): eeee", "(stopped by signal 15)"]
    missing = [c for c in causes if not any(c in w for w in warnings)]
    ok &= report(f"lifecycle {host}: failure causes logged", not missing, f"missing {missing}" if missing else "")
    longest = max((len(w) for w in warnings), default=0)
    ok &= report(f"lifecycle {host}: logged stderr is bounded", 4096 < longest < 4096 + 200, f"longest line {longest}")
    r.cleanup()
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return ok


def main():
    harness.install_signal_cleanup()
    results = [run(host) for host in harness.available_hosts(what="lifecycle")]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
