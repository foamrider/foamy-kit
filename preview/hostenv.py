"""Host-environment helpers for plugin tests: load the host's shell QML and
data, never its scripts, the machine's audio server or its system bus.

Shared from the foamy-kit checkout; plugins import it the way they import the
harness (it is not synced into plugins):

  KIT = Path(os.environ.get("FOAMY_KIT", Path.home() / "GitHub/Personal/foamy-kit"))
  sys.path.insert(0, str(KIT / "preview"))
  import harness, hostenv

harness.Run already applies isolate() to every run. Use these for what runs
outside it, or for more than it does:

  env = hostenv.isolate(dict(os.environ), base)      # a qs, notify-send… a test starts itself
                                                     # (session_bus=… for its own bus)
  env.update(hostenv.make(base, app))                # private OMARCHY_PATH, logging omarchy-* stubs
  …
  hostenv.check(env, log_text, *hostenv.calls(base)) # no host script could run, and none did
  plugin = hostenv.fake_helper_plugin(PLUGIN, work / "plugin", "foamy-x-helper", script)
  with hostenv.ProcessGroup(["qs", "-p", str(app)], env=env) as shell:  # its own qs, killed with
      shell.wait(60)                                 # everything its Processes started

The Omarchy tree is the installed /usr/share/omarchy (its shell/ is 4.5):
OMARCHY_TEST_ROOT (a tree with shell/ and default/) selects another one;
FOAMY_HOST_45 or OMARCHY_SHELL_PATH (a shell/ directory) select its parent.
Standard library only.
"""

import ctypes
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

INSTALLED_BIN = "/usr/share/omarchy/bin"
ARCHES = ("x86_64", "aarch64")
CALLS_LOG = "omarchy-calls.log"
# What fake_helper_plugin() leaves out of the copy by default.
COPY_IGNORE = (".git", "bin", "target", "tests", "__pycache__", "preview.png")
try:
    _LIBC = ctypes.CDLL(None, use_errno=True)
except OSError:
    _LIBC = None
PR_SET_PDEATHSIG = 1


def root():
    """The Omarchy tree the tests load (shell/, default/)."""
    explicit = os.environ.get("OMARCHY_TEST_ROOT") or ""
    for shell in (os.environ.get("FOAMY_HOST_45"), os.environ.get("OMARCHY_SHELL_PATH")):
        if not explicit and shell:
            explicit = str(Path(shell).parent)
    return Path(explicit or "/usr/share/omarchy")


def host_bins(*extra):
    """Real paths of Omarchy's bin directories: the installed one, the test
    tree's, the caller's $OMARCHY_PATH/bin and any `extra`."""
    bins = [INSTALLED_BIN, root() / "bin", *extra]
    if os.environ.get("OMARCHY_PATH"):
        bins.append(Path(os.environ["OMARCHY_PATH"]) / "bin")
    return {os.path.realpath(b) for b in bins}


def in_appdir(path):
    """True for a path inside the running AppImage ($APPDIR)."""
    appdir = (os.environ.get("APPDIR") or "").rstrip("/")
    return bool(appdir) and (path == appdir or path.startswith(appdir + "/"))


def library_path(value=None):
    """LD_LIBRARY_PATH (or `value`) without an AppImage's bundled libraries."""
    value = os.environ.get("LD_LIBRARY_PATH", "") if value is None else value
    return ":".join(p for p in value.split(":") if p and not in_appdir(p))


def isolated_path(value=None, *extra_bins):
    """PATH (or `value`) without Omarchy's bin directories and $APPDIR."""
    value = os.environ.get("PATH", "/usr/bin:/bin") if value is None else value
    bins = host_bins(*extra_bins)
    return ":".join(p for p in value.split(":") if p and os.path.realpath(p) not in bins and not in_appdir(p))


# What isolate() drops unless display=True: the live compositor, Hyprland
# and X11.
DISPLAY_VARIABLES = ("WAYLAND_DISPLAY", "HYPRLAND_INSTANCE_SIGNATURE", "DISPLAY")
# Tests never show anything on the live desktop unless the user sets this to
# 1 for the run: a validate run used to put test surfaces on the user's screen.
DESKTOP_OPT_IN = "FOAMY_TEST_DESKTOP"


def desktop_problem(env, what):
    """Why `what` must not run with `env`: it keeps a variable that reaches the
    live desktop (DISPLAY_VARIABLES) and the user has not set
    FOAMY_TEST_DESKTOP=1 in this process's environment. None when it may."""
    kept = [name for name in DISPLAY_VARIABLES if env.get(name)]
    if not kept or os.environ.get(DESKTOP_OPT_IN) == "1":
        return None
    return (
        f"{what} keeps {', '.join(kept)}, which reach the live desktop; tests never show anything there "
        f"unless the user opts in: set {DESKTOP_OPT_IN}=1 to run it on purpose"
    )


def isolate(env, base, session_bus=None, display=False):
    """`env` (a dict, changed in place and returned) for a process a test
    starts itself: no Omarchy bin directory or AppImage entry on PATH or
    LD_LIBRARY_PATH, no audio server, no system bus, and, like harness.Run,
    not the desktop's session bus or display. `base` is the test's temp
    dir; the dead sockets are named inside it.

    The session bus is a dead address unless `session_bus` names the test's
    own (a unix: address, e.g. `os.environ["DBUS_SESSION_BUS_ADDRESS"]`
    inside dbus-run-session): the caller's address is the desktop's in a
    terminal, where a test's qs would reach the live notification daemon and
    media players. WAYLAND_DISPLAY, HYPRLAND_INSTANCE_SIGNATURE and DISPLAY
    leave unless `display=True` (a test that runs on the live compositor
    on purpose), which raises RuntimeError unless FOAMY_TEST_DESKTOP=1 is
    set."""
    if session_bus is not None and not str(session_bus).startswith("unix:"):
        raise ValueError(f"session_bus must be a unix: address, not {session_bus!r}")
    if display:
        problem = desktop_problem(env, "hostenv.isolate(display=True)")
        if problem:
            raise RuntimeError(problem)
    env["PATH"] = isolated_path(env.get("PATH", "/usr/bin:/bin"))
    libraries = library_path(env.get("LD_LIBRARY_PATH", ""))
    if libraries:
        env["LD_LIBRARY_PATH"] = libraries
    else:
        env.pop("LD_LIBRARY_PATH", None)
    env.update(
        {
            "PULSE_SERVER": f"unix:{base}/no-pulse",
            "PIPEWIRE_REMOTE": f"{base}/no-pipewire",
            "DBUS_SYSTEM_BUS_ADDRESS": f"unix:path={base}/no-system-bus",
            # Set even when the caller had none: an unset address falls back
            # to $XDG_RUNTIME_DIR/bus, the login session's.
            "DBUS_SESSION_BUS_ADDRESS": str(session_bus) if session_bus else f"unix:path={base}/no-session-bus",
        }
    )
    for name in ("PULSE_RUNTIME_PATH", "PIPEWIRE_RUNTIME_DIR", "PULSE_COOKIE"):
        env.pop(name, None)
    if not display:
        for name in DISPLAY_VARIABLES:
            env.pop(name, None)
    return env


def write_commands(folder, commands):
    """Executable scripts {name: text} in `folder` (created)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in commands.items():
        (folder / name).write_text(text)
        (folder / name).chmod(0o755)
    return folder


def logging_stub(log):
    """A command that logs "$0 $*" to `log` and succeeds."""
    return f'#!/bin/sh\nprintf "%s\\n" "$0 $*" >> "{log}"\nexit 0\n'


def make(base, app, env=None, stubs=None, names=()):
    """A private Omarchy tree and logging stubs; returns the environment
    overrides (OMARCHY_PATH, OMARCHY_SHELL_PATH, PATH, LD_LIBRARY_PATH).

    Only `shell/` and `default/` of root() are exposed through OMARCHY_PATH;
    its `bin/` and every `omarchy-*` name of the host's bin directories (plus
    `names`) are stubs that log to <base>/omarchy-calls.log and succeed.
    `omarchy-shell` reaches this test's own shell only (`qs ipc -n -p APP`,
    APP being the shell root the test runs), never the live session. `stubs`
    ({name: script}) replaces or adds commands. PATH is `env`'s (default the
    caller's) with the stubs first and the host's bin directories gone."""
    base, host = Path(base), root()
    tree = base / "omarchy-host"
    (tree / "bin").mkdir(parents=True)
    (tree / "shell").symlink_to(host / "shell", target_is_directory=True)
    if (host / "default").is_dir():
        (tree / "default").symlink_to(host / "default", target_is_directory=True)
    log = base / CALLS_LOG
    found = {n for b in host_bins() if os.path.isdir(b) for n in os.listdir(b) if n.startswith("omarchy-")}
    commands = {name: logging_stub(log) for name in found | set(names) | {"omarchy-shell"}}
    commands["omarchy-shell"] = (
        f'#!/bin/sh\nprintf "%s\\n" "$0 $*" >> "{log}"\n[ "$1" = -q ] && shift\nexec qs ipc -n -p "{app}" call "$@"\n'
    )
    commands.update(stubs or {})
    stub_dir = write_commands(base / "stub-bin", commands)
    write_commands(tree / "bin", commands)
    source = env if env is not None else os.environ
    path = [str(stub_dir)] + isolated_path(source.get("PATH", "/usr/bin:/bin")).split(":")
    return {
        "OMARCHY_PATH": str(tree),
        "OMARCHY_SHELL_PATH": str(tree / "shell"),
        "PATH": ":".join(p for p in path if p),
        "LD_LIBRARY_PATH": library_path(source.get("LD_LIBRARY_PATH", "")),
    }


def calls(base):
    """Lines the make() stubs logged ("<path> <args>")."""
    log = Path(base) / CALLS_LOG
    return log.read_text(errors="replace").splitlines() if log.exists() else []


def check(env, *outputs):
    """Fails (AssertionError) when a host script could run (the host's bin
    directories on PATH, OMARCHY_PATH/bin not the stubs) or did (its path in
    one of `outputs`)."""
    bins = host_bins()
    assert not any(os.path.realpath(p) in bins for p in env["PATH"].split(":") if p), env["PATH"]
    if env.get("OMARCHY_PATH"):
        tree = Path(env["OMARCHY_PATH"])
        assert os.path.realpath(tree / "bin").startswith(os.path.realpath(tree.parent)), (
            "OMARCHY_PATH/bin must be the stub directory"
        )
    named = bins | {str(root() / "bin"), INSTALLED_BIN}
    for text in outputs:
        assert not any(b + "/" in str(text) for b in named), "a host script ran"


# kit/clipboard.sh stand-ins (clipboard_fakes()). wl-paste and
# clipboard-fixture are this one script: bash builtins only, so it starts in
# milliseconds (clipboard.sh gives a paste 2 s in all, and a Python stand-in's
# start-up alone took longer than that on a loaded machine).
CLIPBOARD_STAND_IN = r"""#!/bin/bash
state=$TEST_CLIPBOARD_STATE
if [[ ${0##*/} == clipboard-fixture ]]; then
  printf '%s' "$1" >"$state"
  exit 0
fi
mode=$(<"$state")
printf '%s' "$$" >"$state.pid"
args=$(printf ',"%s"' "$@")
printf '[%s]' "${args#,}" >"$state.args"
xs() { local s; printf -v s '%*s' "$1" ''; printf '%s' "${s// /x}"; }
case $mode in
  failure) exit 1 ;;
  ignore) trap '' TERM; exec sleep 30 ;;
  stall) exec sleep 30 ;;
  stream) while :; do xs 4096; done ;;
  slow) while :; do printf x; sleep 0.1; done ;;
  delayed) sleep 0.4; printf later ;;
  loaded) sleep 2.5; printf late ;;
  unicode) printf '%s' "/home/test/Blåbær 📁" ;;
  empty) ;;
  limit) xs 16384 ;;
  large) xs 16385 ;;
  nul) printf 'a\0b' ;;
  lines) printf 'one\r\ntwo\xe2\x80\xa8three' ;;
  long) xs 400 ;;
  *) printf folder ;;
esac
"""
# Modes whose outcome is clipboard.sh's own 2 s deadline.
CLIPBOARD_DEADLINE_MODES = ("stall", "slow", "ignore")
# timeout(1) in front of clipboard.sh: the deadline modes keep the real 2 s,
# every other mode (it ends by itself) gets 60 s.
CLIPBOARD_TIMEOUT = r"""#!/bin/bash
case $(<"$TEST_CLIPBOARD_STATE") in
  stall | slow | ignore) ;;
  *) [[ $1 == --signal=KILL && $2 == 2s ]] && set -- "$1" 60s "${@:3}" ;;
esac
exec @TIMEOUT@ "$@"
"""


def clipboard_fakes(folder, env=None):
    """Stand-ins for a test of kit/clipboard.sh (run directly, or through
    SafeTextField in a qs) in `folder` (created): `wl-paste`,
    `clipboard-fixture MODE` (what the next paste does) and `timeout`.
    Returns the environment overrides: TEST_CLIPBOARD_STATE (the mode file,
    "normal" to start) and PATH, `env`'s (default the caller's) with
    `folder` first.

    Modes: normal ("folder"), unicode, empty, limit (16384 bytes), large
    (16385), nul, lines (CR LF and U+2028), long (400 bytes), delayed (0.4
    s), loaded (2.5 s: a paste on a loaded machine), failure (exit 1),
    stream (endless), and the deadline modes stall, slow (a byte per 0.1 s)
    and ignore (ignores SIGTERM). Each paste writes its argv to
    <state>.args (JSON) and its pid to <state>.pid.

    The stand-in timeout keeps clipboard.sh's 2 s for the deadline modes,
    whose outcome is that deadline, and gives every other mode 60 s, so a
    loaded machine (the paste is six processes) can't turn a paste that
    works into a timeout. clipboard.sh itself is unchanged."""
    folder = Path(folder)
    path = (env if env is not None else os.environ).get("PATH", "/usr/bin:/bin")
    real = shutil.which("timeout", path=path)
    if not real:
        raise FileNotFoundError(f"timeout(1) is not on PATH ({path})")
    write_commands(
        folder,
        {
            "wl-paste": CLIPBOARD_STAND_IN,
            "clipboard-fixture": CLIPBOARD_STAND_IN,
            "timeout": CLIPBOARD_TIMEOUT.replace("@TIMEOUT@", real),
        },
    )
    state = folder / "clipboard-mode"
    state.write_text("normal")
    return {"TEST_CLIPBOARD_STATE": str(state), "PATH": f"{folder}:{path}"}


def die_with_parent():
    """preexec_fn: SIGKILL this child when the Python process dies."""
    if _LIBC is not None:
        _LIBC.prctl(PR_SET_PDEATHSIG, signal.SIGKILL)


class ProcessGroup:
    """`argv` (a qs or service a test starts itself) as the leader of its own
    process group; `popen` goes to subprocess.Popen. stop() signals the
    whole group, so the scripts a shell's `Process`es started go with it:
    Popen.terminate() reaches qs alone, and a `sh -c` child's own children
    outlived it. The leader also dies with the Python process (its children
    then don't). A child that makes its own group or session (setsid,
    coreutils timeout) leaves this one. Wait through wait(), not
    `.process.wait()`: the leader stays unreaped until stop(), so its pid,
    the group id, can't name another group while stop() signals it.

      with hostenv.ProcessGroup(["qs", "-p", str(app), "--no-color"], env=env, stdout=log) as shell:
          shell.wait(60)       # None while it still runs
    """

    def __init__(self, argv, **popen):
        self.process = subprocess.Popen(argv, start_new_session=True, preexec_fn=die_with_parent, **popen)
        self.pid = self.process.pid
        self.returncode = None

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.stop()
        return False

    def exit_status(self):
        """The leader's exit status (negative: killed by that signal) once
        it has exited, else None. It is not reaped."""
        if self.returncode is not None:
            return self.returncode
        info = os.waitid(os.P_PID, self.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        if info is None:
            return None
        return info.si_status if info.si_code == os.CLD_EXITED else -info.si_status

    def wait(self, timeout=None):
        """Wait up to `timeout` seconds (None: as long as it takes) for the
        leader to exit; its exit_status(), or None when it still runs."""
        deadline = None if timeout is None else time.monotonic() + timeout
        while (status := self.exit_status()) is None:
            if deadline is not None and time.monotonic() >= deadline:
                return None
            time.sleep(0.02)
        return status

    def _signal(self, sig):
        # Only while the leader is unreaped (running or a zombie): then no
        # other process group can have its id.
        if self.returncode is None:
            try:
                os.killpg(self.pid, sig)
            except ProcessLookupError:
                pass

    def stop(self, grace=2.0):
        """SIGTERM the group, SIGKILL what is left once the leader has exited
        or `grace` seconds have passed, then reap the leader. Returns its exit
        status; later calls return the same."""
        if self.returncode is not None:
            return self.returncode
        self._signal(signal.SIGTERM)
        self.wait(grace)
        # Members that ignored SIGTERM, and children the leader left behind.
        self._signal(signal.SIGKILL)
        self.returncode = self.process.wait()
        return self.returncode


def fake_helper_plugin(plugin, dest, helper, script, ignore=COPY_IGNORE):
    """A copy of `plugin` at `dest` (must not exist) whose bundled helper
    bin/<arch>/<helper> is `script` for both arches, so FoamyNative runs the
    fake. `ignore` names what the copy leaves out (shutil.ignore_patterns)."""
    dest = Path(dest)
    shutil.copytree(plugin, dest, ignore=shutil.ignore_patterns(*ignore))
    for arch in ARCHES:
        write_commands(dest / "bin" / arch, {helper: script})
    return dest
