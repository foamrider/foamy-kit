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
  env.update(hostenv.make(base, app))                # private OMARCHY_PATH, logging omarchy-* stubs
  …
  hostenv.check(env, log_text, *hostenv.calls(base)) # no host script could run, and none did
  plugin = hostenv.fake_helper_plugin(PLUGIN, work / "plugin", "foamy-x-helper", script)

The Omarchy tree is the installed /usr/share/omarchy (its shell/ is 4.5):
OMARCHY_TEST_ROOT (a tree with shell/ and default/) selects another one;
FOAMY_HOST_45 or OMARCHY_SHELL_PATH (a shell/ directory) select its parent.
Standard library only.
"""
import os
import shutil
from pathlib import Path

INSTALLED_BIN = "/usr/share/omarchy/bin"
ARCHES = ("x86_64", "aarch64")
CALLS_LOG = "omarchy-calls.log"
# What fake_helper_plugin() leaves out of the copy by default.
COPY_IGNORE = (".git", "bin", "target", "tests", "__pycache__", "preview.png")


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


def isolate(env, base):
    """`env` (a dict, changed in place and returned) for a process a test
    starts itself: no Omarchy bin directory or AppImage entry on PATH or
    LD_LIBRARY_PATH, no audio server, no system bus. `base` is the test's
    temp dir; the dead sockets are named inside it."""
    env["PATH"] = isolated_path(env.get("PATH", "/usr/bin:/bin"))
    libraries = library_path(env.get("LD_LIBRARY_PATH", ""))
    if libraries:
        env["LD_LIBRARY_PATH"] = libraries
    else:
        env.pop("LD_LIBRARY_PATH", None)
    env.update({
        "PULSE_SERVER": f"unix:{base}/no-pulse",
        "PIPEWIRE_REMOTE": f"{base}/no-pipewire",
        "DBUS_SYSTEM_BUS_ADDRESS": f"unix:path={base}/no-system-bus",
    })
    for name in ("PULSE_RUNTIME_PATH", "PIPEWIRE_RUNTIME_DIR", "PULSE_COOKIE"):
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
    commands["omarchy-shell"] = (f'#!/bin/sh\nprintf "%s\\n" "$0 $*" >> "{log}"\n'
                                 f'[ "$1" = -q ] && shift\nexec qs ipc -n -p "{app}" call "$@"\n')
    commands.update(stubs or {})
    stub_dir = write_commands(base / "stub-bin", commands)
    write_commands(tree / "bin", commands)
    source = env if env is not None else os.environ
    path = [str(stub_dir)] + isolated_path(source.get("PATH", "/usr/bin:/bin")).split(":")
    return {"OMARCHY_PATH": str(tree), "OMARCHY_SHELL_PATH": str(tree / "shell"), "PATH": ":".join(p for p in path if p),
            "LD_LIBRARY_PATH": library_path(source.get("LD_LIBRARY_PATH", ""))}


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
        assert os.path.realpath(tree / "bin").startswith(os.path.realpath(tree.parent)), "OMARCHY_PATH/bin must be the stub directory"
    named = bins | {str(root() / "bin"), INSTALLED_BIN}
    for text in outputs:
        assert not any(b + "/" in str(text) for b in named), "a host script ran"


def fake_helper_plugin(plugin, dest, helper, script, ignore=COPY_IGNORE):
    """A copy of `plugin` at `dest` (must not exist) whose bundled helper
    bin/<arch>/<helper> is `script` for both arches, so FoamyNative runs the
    fake. `ignore` names what the copy leaves out (shutil.ignore_patterns)."""
    dest = Path(dest)
    shutil.copytree(plugin, dest, ignore=shutil.ignore_patterns(*ignore))
    for arch in ARCHES:
        write_commands(dest / "bin" / arch, {helper: script})
    return dest
