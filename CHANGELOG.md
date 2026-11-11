# Changelog

## 0.9.0 — unreleased (dev)

### Added
- `REVIEW.md`: the shared Foamy review standard (blocking checklist,
  severity, review order, deterministic checks, boundary and process
  lifecycle rules, security at the sink, tests, review record). `sync.sh`
  copies it verbatim to each plugin root and records its hash in
  `foamy-kit.lock`; `tests/kit-check.sh`, `check.sh` and the bundled build
  tool fail when it is edited.
- `AGENTS.md`: sync keeps one marked "Code review" block in each plugin's
  `AGENTS.md` (created when missing) that points review agents at
  `REVIEW.md`. Text outside the block and the file's mode are preserved;
  sync refuses a symlink, non-UTF-8 file or broken markers, even with
  `--force`. `tests/kit-check.sh` and `check.sh` fail when the block is
  missing or stale. foamy-kit has its own `AGENTS.md`.
- Shared test helpers that plugins import from the kit checkout, like the
  harness, instead of copying them (three plugins had): `harness/FoamyWait.qml`
  in every run (`waitFor(condition, timeoutMs, then[, label])`, `after(ms,
  then)`: condition-driven steps instead of fixed delays, which flaked under
  load in vitals, bolt and zendesk), `harness.wait_for()` and
  `Run.wait_for_log()` on the Python side, and `preview/hostenv.py`
  (`isolate`, `make` with an `omarchy-shell` that reaches only the test's
  own shell, `calls`, `check`, `fake_helper_plugin`). See README, "Test
  helpers for plugins".
- `FoamyText` (`kit/FoamyText.js`, a new component): `cap(text, maxLines,
  maxChars)` and `tooltip(text)` (6 lines of 100 characters) bound text for
  a sink with no size limit of its own. The host bar tooltip is a PlainText
  label sized to its text (no width, wrap or line limit), so a long or
  many-line app-controlled title made a window as large as the text (foamy-tray
  review; Omarchy's own tray has the same issue). Cut lines and dropped lines
  end in a visible "…"; characters are code points, so a surrogate pair is
  never split; `\r\n`, `\r`, U+2028 and U+2029 count as line breaks. Node
  tests in `tests/text.test.cjs`, engine parity in `tests/qml/Runtime.qml`.
  After syncing, pass app-controlled text through `FoamyText.tooltip()` at
  every `bar.showTooltip` call.
- REVIEW.md section 5: plain text alone doesn't bound a host tooltip's size,
  and a line-mode `SplitParser` or a `StdioCollector` is not a memory bound.
- `FoamySchedule` (opt-in component): `kit/FoamySchedule.js` and
  `kit/FoamyScheduleDay.qml`, moved from foamy-train's `Schedule.js` and
  `ScheduleDay.qml`. foamy-zendesk carried byte-identical copies ("keep the
  two in step until it moves into foamy-kit"); the JS is unchanged apart from
  `.pragma library`, a null-safe `week()` and more exports (`dayKeys`,
  `minutes`, `validOverride`, `nextScheduled`). The row's weekday label is
  injectable (`labelComponent`: any Component whose root has `text`; train
  passes `TrainText`, zendesk `PlainText`; default a plain-text body label;
  `labelItem`). Node tests (`tests/schedule.test.cjs`, train's and zendesk's
  schedule cases) and a row test (`tests/test_schedule.py`).

  After syncing (train, zendesk): `sync.sh <plugin> --add FoamySchedule`,
  delete `Schedule.js` and `ScheduleDay.qml`, import
  `"kit/FoamySchedule.js" as Schedule` (Panel, the service/store), use
  `FoamyScheduleDay { labelComponent: Component { TrainText { } } … }` in the
  settings page, and point the schedule unit tests at the kit (or drop them:
  the kit tests cover them).

### Changed
- `preview/harness.py` isolates every run by default (render.py and every
  plugin runtime test that uses `harness.Run`). Reviews found runtime tests
  running the real host tools (`omarchy-audio-*`, `pactl`, `omarchy bar
  set`) and reaching the machine's system bus (foamy-train's test called the
  real Entur API through NetworkManager's online state). Now Omarchy's bin
  directories and an AppImage's `$APPDIR` entries leave `PATH`, every other
  `omarchy`/`omarchy-*` on `PATH` is a stub that exits 127 and logs to
  `$FOAMY_OUT/host-commands.log` (`Run.host_commands()`), `$APPDIR` entries
  leave `LD_LIBRARY_PATH`, `PULSE_SERVER`/`PIPEWIRE_REMOTE` name dead
  sockets, and `DBUS_SYSTEM_BUS_ADDRESS` is a dead address. The private
  session bus is unchanged. `Run(…, system_bus="private")` gives a test its
  own system bus (`Run.system_bus_address`); `system_bus="unix:path=…"`
  uses one the test provides. `tests/test_isolation.py` checks each from
  inside qs.

  After syncing: a plugin test whose QML runs a host command now gets exit
  127 and a `host-commands.log` line; give it a `fakebin` stand-in (or `hostenv.make()` stubs).
  Plugin-local `isolate()`/`library_path()` copies are redundant.

- `FoamyPrefs`/`FoamyPrefsQueue` (behaviour change, kit-wide): an invalid
  stored array is no longer replaced by the next save of that key. An array
  setting holds user data (accounts, folders); one invalid item (a hand edit,
  an older shape) makes the whole value read as the default, so a save built
  from what the panel showed wiped every other entry (foamy-teams D1,
  REVIEW item 7). Now `save(key, value)` refuses when the stored array
  (present, not null) fails the schema: `FoamyPrefs.save()` returns
  `storedInvalid: true` with `STORED_INVALID` ("The saved list in shell.json
  isn't valid, so it wasn't replaced."), nothing is written, `failed()` fires
  and it isn't retryable. `save(key, value, true)` (and `FoamyPrefs.save(…,
  pending, true)`) replaces it on purpose. `storedProblem(key)` and
  `storedProblems` (queue), `FoamyPrefs.storedProblem()/storedProblems()`
  say which stored value is invalid. Other keys still save and carry the
  stored array over verbatim; invalid scalars and objects, absent and null
  values, reads and the inline/CLI paths are unchanged.

  After syncing: a plugin whose array settings hold user data should show
  `storedProblem(key)` (and block the editor, or offer a confirmed "start
  over" that saves with force), and add the new message to its catalogs if
  it shows `prefs.error`. foamy-teams will (accounts).

### Removed
- Omarchy 4.0 support, which the README no longer promised. The kit
  components lose their 4.0 branches: `FoamyI18n` uses the shell's
  `Translations` and `I18n` directly (no English-only fallback; its
  `translationsAvailable` is always true and kept only for plugins that read
  it), `FoamyMotion` calls `Style.duration`, `FoamyCursor.emitTextKey` always
  passes modifiers, `FoamyPopup` leaves RTL mirroring to the host panel, and
  the IPC, popup and prefs comments describe 4.5 alone. The harness knows
  only 4.5: `FOAMY_HOST_40` is ignored, `harness.Run("4.0", …)` and
  `render.py --host 4.0` stop with "Omarchy 4.0 is no longer supported …",
  `harness.available_hosts()` prints a `SKIP … on 4.0` line for a 4.0 a
  caller still lists (so its 4.5 cases keep running), `--host both` renders
  4.5 into `<out>/4.5/`, and the preview shell, `ScreenSim` (its
  `fullScreenBar` property is gone) and the kit tests drop the 4.0 strip bar
  window. `--trio` renders Before on 4.5 only (`--before-host` and
  `trio(before_hosts=…)` are gone) and labels a clipped fork or a dev tree
  that won't render.

  After syncing: drop each plugin test's 4.0 cases (`--host 4.0|both`
  choices, `FOAMY_HOST_40` checks, `("4.0", …)` case lists,
  `harness.HOSTS["4.0"]`); until then a listed 4.0 prints SKIP, and a test
  that calls `harness.Run("4.0")` itself stops with the message above.

## 0.8.1 — 2026-11-10

### Fixed
- `THIRD_PARTY_NOTICES.md` covers every crates.io dependency of the Rust
  standard library linked into the helpers. 0.8.0 named addr2line, adler2,
  miniz_oxide and object as omissions (the toolchain's
  `COPYRIGHT-library.html` has no entry for them) and `--verify` accepted
  that. Their versions and `.crate` checksums now come from the toolchain's
  `library/Cargo.lock` (rust-src's copy when installed, else the `STD_LOCKS`
  table in `native.py`, generated for 1.99.1 from rust-src; both must
  agree), and each gets the notice file's entry for that exact version or
  the texts of its checksum-verified archive (cargo's cache, the
  foamy-native cache, or a download from static.crates.io, cached; not with
  `CARGO_NET_OFFLINE`). Generation fails when a dependency the binaries or
  the sysroot show has no locked version or no notice text. Versions are now
  exact (libc 0.2.189, memchr 2.8.3, hashbrown 0.17.1).

  After syncing, run `kit/native/build-native.sh . --notices` (or a build;
  the binaries and `native.pin` source hash don't change) and commit the
  file; until then `--verify` and CI fail on the stale notices.

## 0.8.0 — 2026-11-10

Answers two marketplace review findings that apply to every plugin
(omacom/omarchy-plugin-marketplace#14501).

### Fixed
- `FoamyPrefsQueue`: a CLI-fallback save always ends. A command that can't
  start (Quickshell emits no `exited` then), hangs past `saveTimeoutMs`
  (default 20 s; then SIGKILL) or is cancelled goes through one completion
  path that rolls back, reports the error and keeps retry, so `inFlight` can
  no longer stick and later saves are never blocked. The next save waits until
  the previous process has really exited. stderr is read in chunks and only
  the first 4096 characters are kept. Every CLI save runs under coreutils
  `timeout --signal=KILL` (`FoamyPrefs.bounded()`), which leads its own
  process group and kills the whole group at the deadline, so a child of the
  array-save `sh -c` wrapper can't write a rolled-back value later; a save
  stopped by a signal or a queue destroyed mid-save also kills what is left
  of the group (`FoamyPrefs.killGroupCommand()`), and the next save waits
  for it. The queue's own deadline is a backstop at `saveTimeoutMs` + 2 s.
  The inline save path is unchanged.
- `FoamyPeerIpc`: a call whose `omarchy-shell` can't start calls
  `done(false, "")` instead of never finishing; the unread stderr collector
  is gone.

### Added
- Native helpers ship `THIRD_PARTY_NOTICES.md` at the plugin root: per
  binary and arch, every crate linked into it (`cargo tree --edges
  normal,no-proc-macro` per musl target, cross-checked against registry paths
  in the ELF), with its version, SPDX expression and Cargo.lock checksum, and
  each distinct license and notice text, read from the checksum-verified
  `.crate`. Also the Rust standard library (from the toolchain's
  COPYRIGHT-library.html), musl 1.2.5, LLVM libunwind and crtbegin/crtend.
  `build-native.sh .` writes it, `--notices` rewrites only it, `--verify`
  fails when it differs from a fresh generation, and `tests/kit-check.sh` /
  `check.sh` fail when it is missing or doesn't match `native.pin`. Not a
  hashed build input, so binaries and pins are unchanged. Texts come only
  from the `.crate` whose SHA-256 matches Cargo.lock (one `cargo fetch
  --locked` if it's missing), a manifest `license-file` is included in full,
  and a plugin with several helpers can rebuild them one at a time after a
  shared dependency changes (a stale sibling binary skips the ELF
  cross-check and stays reported stale until rebuilt).
- `tests/test_lifecycle.py`: failed start, deadline, bounded stderr, cancel
  and destruction for the queue, and failed start for peer calls.

### Upgrading
After syncing, run `kit/native/build-native.sh . --notices` (or a normal
build) once in each plugin with a helper and commit `THIRD_PARTY_NOTICES.md`;
until then kit-check and CI fail.

## 0.7.0 — 2026-11-10

A plugin's helper binaries can now be rebuilt, verified and attested from the
plugin's own repository. The marketplace accepts `bundled-executable-binary`
only with independently checkable source-to-binary evidence at the exact
commit (omacom/omarchy-plugin-marketplace#14501); README.md "Provenance"
is the recipe.

### Added
- FoamyNative vendors the build tool: `kit/native/native.py` (the former
  `tools/foamykit.py native`, standard library only) and its wrapper
  `kit/native/build-native.sh`. Building, `--verify` and `--test` need only
  the plugin, rustup and Python 3.11+; no foamy-kit clone, so plugin READMEs
  no longer name a kit commit.
- `--verify --out DIR`: also writes the rebuilt binaries to
  `DIR/<arch>/<binary>` (refused inside the plugin).
- FoamyNative syncs `.github/workflows/verify-native.yml`: on pushes,
  pull requests and manual runs a GitHub-hosted runner runs kit-check,
  `--test` and `--verify --out`, reports each binary's git blob and SHA-256,
  uploads the rebuilt files. On pushes and manual runs a separate job on a
  fresh runner (no build, the only one with `id-token: write`) requires each
  rebuilt file to equal the committed git blob and `native.pin`, then attests
  it with `actions/attest-build-provenance`, so `gh attestation verify
  bin/<arch>/<binary>` passes for the committed files. Actions are pinned by
  commit SHA.
- README.md: the Verify issue evidence and the plugin README's "Verifying the
  helper binaries" section.

### Changed
- `tools/build-native.sh <plugin>` runs the plugin's own
  `kit/native/build-native.sh`; sync first if the plugin has none.
- `native.pin`'s `kit` is the plugin's `foamy-kit.lock` version (the vendored
  tool's), and its header names `kit/native/build-native.sh .`. Pins change
  on the next build; the binaries don't.
- Sync stamps `.py` and `.yml` files with `#`, keeps a shebang on line 1, and
  removes a dropped root file's empty directories (`.github/workflows`).
- `tests/kit-check.sh` accepts `.github/workflows/verify-native.yml` in the
  lock.

## 0.6.0 — 2026-11-08

For foamy-lock's video wallpapers: a sandboxed, multithreaded ffmpeg
conversion in two stages, and stricter decoder filters (a deliberate
hardening, below). Otherwise everything is additive; `Bounded` calls behave
as before. README.md "Two-stage jobs" is the recipe.

### Added
- `foamy-helper::sandbox::BpfFilter::threaded_decoder()` (feature
  `sandbox`), with `threaded_decoder_denied(arch)`: the image decoder's
  filter for a decoder that runs threads. `clone` is allowed only with
  `CLONE_THREAD` and no `CLONE_NEW*` flag (masked compares on the low 32
  bits of argument 0), `clone3` returns `ENOSYS` so glibc falls back to
  `clone`, and `fork`, `vfork`, `ptrace`, `mount`, `unshare`, `setns` and
  `bpf` stay `EPERM` (and the hardening below). Foreign architectures and
  x32 are killed as before.
- `Bounded::stdin_fd(fd)`: standard input straight from an open file, as
  fd 0 and still seekable (`ffmpeg -fd 0 -i fd:`).
- `Bounded::nice(n)` and `Bounded::io_idle()`: niceness (only ever raised)
  and the idle I/O class for one child, inherited by its threads and
  children.
- `Bounded::pipe_into(next)` → `child::Pipeline` (`run`,
  `run_with_progress`) → `child::PipelineOutput` (`first`, `second`,
  `piped`, `cancelled`, `success()`): the first child's standard output
  into the second one's input through the helper, moved with `splice` and
  counted. The progress callback runs after every transfer and at least
  every 100 ms and can cancel. The deadline is the shorter of the two
  timeouts. A timeout, an overflow, a cancel or an error kills both process
  groups, and both children are always reaped.
- Tests: the threaded profile against an independent reference for every
  syscall and many `clone` flags on both arches, and live in a child (a
  thread starts; fork, `clone` without `CLONE_THREAD` or with
  `CLONE_NEWUSER`, `unshare`, `setns` and `bpf` fail; x32 is killed); the
  decoder program's bytes pinned; `stdin_fd`, `nice`, `io_idle`, and
  pipelines (counting, progress, both ends closing, deadline, cancel,
  overflow, spawn failure, no zombies).

### Changed (security hardening: the image decoder's filter is new)
- Both decoder profiles, `BpfFilter::decoder()` and `threaded_decoder()`,
  are denylists, so they now also deny (`EPERM`) kernel interfaces a
  decoder never needs and that have a history of privilege-escalation
  bugs: io_uring (`io_uring_setup`, `io_uring_enter`, `io_uring_register`),
  the kernel key store (`add_key`, `request_key`, `keyctl`) and
  `userfaultfd`. `decoder_denied(arch)` and `threaded_decoder_denied(arch)`
  list them too. This deliberately changes the `decoder()` program that
  0.5.2 and artwork.py built (x86_64: 53 → 88 instructions, aarch64: 40 →
  75): the unit test that pinned its bytes to 0.5.2's now pins the new
  bytes and also checks that 0.5.2's list still compiles to 0.5.2's bytes,
  so the list is the only change. ImageMagick and ffmpeg use none of these
  calls (foamy-lock's image and video tests run under the new filters).
- Tests for each new denial: the BPF interpreter (both profiles, both
  arches, every syscall against the references) and, on x86_64, live in a
  child: each call is `EPERM` under the threaded profile (installed before
  exec) and under the image decoder profile (installed by the probe on its
  own thread, since the test harness needs a thread first), while without
  a filter the kernel answers otherwise (`EBADF`, `EFAULT`, `EINVAL`,
  `EOPNOTSUPP`). 92 unit tests.

### Changed
- `foamy-helper` is 0.1.1 (new public API) and enables rustix's `pipe`
  feature; its dependencies are unchanged. A plugin that syncs 0.6.0 runs
  `cargo update -p foamy-helper` (in `native/`, or its crate dir) and,
  being FoamyNative, rebuilds: `kit/rust` changed, so `native.pin`'s
  source hash changes too.
- `Bounded::run` now also reaps a child it killed after an error, instead
  of leaving a zombie.

## 0.5.2 — 2026-11-07

Omarchy 4.5.0 is the installed shell now: the kit is previewed and tested on it,
and 4.0 is opt-in.

### Changed (on resync, native plugins must rebuild)
- `foamy-helper::tls::UNSUPPORTED` named only AES and carry-less multiply,
  but `cpu_supported()` also needs SSSE3, AVX, AVX2, BMI1, BMI2 and ADX on
  x86_64 and NEON, AES, PMULL and SHA-2 on aarch64. It is now exactly
  `HTTPS isn't supported on this CPU (foamy helpers need AES, carry-less
  multiply, AVX2, BMI2 and ADX on x86-64, or the crypto extensions on ARMv8)`.
  Plugins use this text as an i18n catalog key: update the catalogs to the
  new key. A unit test pins it; the module docs list every checked feature.
- **The message is in `kit/rust`, so it changes `native.pin`'s source hash:
  after syncing 0.5.2, every plugin with FoamyNative must run
  `tools/build-native.sh <plugin>` and commit the new `bin/<arch>/` binaries
  and `native.pin`**, or `check.sh` and `tests/kit-check.sh` report them stale.

### Tooling
- Hosts: `preview/harness.py` defaults `HOSTS["4.5"]` to the installed shell,
  `/usr/share/omarchy/shell` (`FOAMY_HOST_45` still overrides). 4.0 has no
  default: `HOSTS["4.0"]` exists only when `FOAMY_HOST_40` points at a 4.0
  shell directory (its code paths in the harness and kit stay). Before, 4.0
  defaulted to `/usr/share/omarchy/shell` and 4.5 to
  `/tmp/omarchy-ref/v45/shell`, which on a 4.5 machine ran "4.0" against the
  4.5 shell.
- `harness.available_hosts()` (and `host_problem()`): the usable hosts, with
  a `SKIP … on 4.0: host 4.0 is opt-in: set FOAMY_HOST_40 …` line for the
  others, and an error when none is usable. `render.py --host both`, `--trio`
  and `--before-host` and every kit test that loops over hosts use it;
  `--host 4.0` without `FOAMY_HOST_40` fails with that message. `--host both`
  always writes `<out>/<host>/`.
- `render.py --trio`: one After column per available host; labels say "4.0",
  not "4.0.6". A pre-kit fork clipped on 4.5 with no other host to try is
  labelled `Before (dev, 4.5 host; popup fork clipped)`.
- `test_ipc_cli.py` and `test_harness.py` run on 4.5; `test_harness.py`
  checks the host defaults. README, `tests/run-all.sh` and test docstrings no
  longer describe `/usr/share/omarchy/shell` as 4.0.6 or 4.5 at
  `/tmp/omarchy-ref`.

## 0.5.1 — 2026-11-06

### Added
- `FoamyIcon`: the Zendesk brand mark (Simple Icons, CC0, drawn filled), plus
  `undo-2`, `undo-dot` and `check-check` (Lucide 1.65.0); both undo icons
  mirror in RTL. 113 names.

## 0.5.0 — 2026-11-06

Native helpers: plugins replace their Python and Bash helpers with one Rust
binary each, committed as static musl executables for x86_64 and aarch64, so
an install stays a plain checkout and needs no Rust. README.md "Native
helpers" is the recipe.

### Added
- **`FoamyNative`** (opt-in: `sync.sh <plugin> --add FoamyNative`):
  `FoamyNative.js` (`command(pluginDir, name, args)` builds
  `bash -c 'exec -- "$1/bin/$HOSTTYPE/$2" "${@:3}"'`, so a missing binary or an
  unsupported CPU is a normal exit 127/126 instead of a Process without an exit;
  `unavailable(exitCode)`, `localPath(url)`, `UNAVAILABLE_TEXT`), the shared
  crate `kit/rust/foamy-helper`, the release profile `kit/rust/release.toml`
  and `rust-toolchain.toml` (1.99.1, both musl targets) at the plugin root.
- **`foamy-helper`** 0.1.0 (rustix, serde, serde_json): bounded reads and a
  line reader with a maximum line length (`io`); JSON-lines helpers, a serve
  loop and `json::run`, which prints one JSON reply for every outcome and turns
  a panic into a JSON reply and exit 101 instead of an abort (`json`); atomic
  writes with owner, type and mode checks, private directories, bounded file
  reads without symlinks or special files (`fs`); `flock` locks and
  `$XDG_RUNTIME_DIR/<plugin>` (`lock`); bounded child processes with a
  deadline, an output cap, a process-group kill, environment control, rlimits,
  sessions and `PR_SET_PDEATHSIG` (`child`); `PR_SET_PDEATHSIG`, `setsid`,
  rlimits and umask for the helper itself (`process`). 35 unit tests.
- **`foamy-helper::favicon`** (cargo feature `favicon`): a port of
  foamy-notifications' and foamy-notification-center's `bin/browser-favicon.py`
  with the same stdin/stdout contract (`favicon::run`, reply lines in Python's
  `json.dumps` format), browser roots, `Default/` plus at most fifteen
  `Profile *` databases, 2 s deadline, no web request, PNG and hostname bounds,
  the 0600 cache of at most 256 icons reused for 24 hours. A live database is
  read under SQLite's own `SHARED` lock with a 100 ms busy timeout (a hot
  journal fails like a read-only SQLite connection); a database the browser
  holds exclusively is copied into memory with every Python check (32 MiB,
  no transaction sidecars, unchanged during the copy, rollback header) and
  checked structurally before it is queried. Nothing is ever written next to
  the browser's files.
- **`foamy-helper::sandbox`** (cargo feature `sandbox`): `BpfFilter`
  (seccomp-BPF generated with `seccompiler`; `decoder()` is foamy-lock's
  `decoder_filter`, proven equal for every syscall number on both arches,
  including the x32 kill on x86_64; `memfd()` for `bwrap --seccomp`,
  `Bounded::seccomp`), `ExecOnly` (a Landlock ruleset handling only
  "execute", applied in `pre_exec`; `probe` is foamy-github's setpriv probe:
  the program from `PATH` and its ELF interpreter, works and bites or `None`
  for the unrestricted fallback; `Bounded::exec_only`), `Bwrap` (bubblewrap
  argv for artwork.py's decoder and github_status's pinned namespace,
  `readonly_host`, fd options inherited by the child, `works`), and
  `elf_interpreter`/`which` as in github_status. 30 more unit tests.
- `process::exit_on_panic(code)`: a panic exits with `code` instead of
  aborting (the message still goes to stderr, nothing to stdout);
  `json::run` and `json::serve` install it, and helpers with their own loop
  call it first in `main`.
- `Bounded::inherit_fd` (Python's `pass_fds`).
- `check.sh` and `tests/kit-check.sh` warn about a cargo target dir inside a
  plugin.
- **`tools/build-native.sh <plugin> [--verify | --test] [--crate DIR] [--bin NAME]`**:
  both arches with `--locked --release`, the pinned toolchain, `rust-lld`
  self-contained, `--build-id=none` and path remapping, cargo output in
  `~/.cache/foamy-native/foamy-<x>` (`FOAMY_NATIVE_CACHE`), never in the plugin;
  atomic installs into `bin/<arch>/`; `<crate>/native.pin` with toolchain, kit
  version, source hash and per-arch sha256. `--verify` rebuilds in a fresh
  target dir and compares bytes; `--test` runs fmt, clippy `-D warnings` and tests.
  Defaults: crate `native/`, binary `foamy-<x>-helper` (manifest id `foamy.<x>`);
  another layout is remembered in its `native.pin`.
- `check.sh` and the generated `tests/kit-check.sh` verify native binaries
  against `native.pin` (regular file, executable, checksum, static ELF of the
  right arch) and report them stale when the crate, `kit/rust`, the root
  `Cargo.toml`/`Cargo.lock` or `rust-toolchain.toml` changed; a synced
  FoamyNative without a pin fails.
- Sync: components may have files in subdirectories of `kit/` (glob patterns)
  and at the plugin root (`rootFiles`); `optIn` components stay out of a first
  sync; emptied directories are removed when a component is dropped.
- Tests: `native.test.cjs`, `test_native.py` with the fixture plugin
  `tests/fixtures/native-plugin` (built for both arches, byte-identical on a
  clean rebuild and from another checkout path, run on aarch64 through qemu),
  `tests/qml/Native.qml` (FoamyNative.command in Quickshell's Process).

### Changed
- `fs::write_atomic` refuses a directory only when it is foreign-owned or
  world-writable without the sticky bit; a group-writable directory of the
  user's own (umask 002) is accepted. `ensure_private_dir` stays 0700-strict.
- The fixture helper (the template for plugin helpers) installs the panic
  hook first and reads argv with `args_os()` inside `json::run`, so a
  non-UTF-8 argument is an `INVALID_ARGUMENT` reply instead of an abort; it
  builds with both features on both arches.
- README "Native helpers": `CARGO_TARGET_DIR` before any cargo command,
  `/target/` in `.gitignore`, `cargo fmt -p <crate>` only, the recipe for an
  existing crate, vendored third-party modules, re-pin after any edit in the
  crate dir, panics and arguments.

### Fixed
- `build-native.sh` refuses symlinks among the build inputs (crate dir,
  `kit/rust`, root Cargo files): the source hash skips them, so a link
  target could change without the pin noticing.
- **Security:** `build-native.sh` wrote `bin/<arch>/<binary>` and `native.pin`
  through their parent paths, so a symlinked `bin/` or `bin/<arch>` in a
  contributor's checkout redirected the built ELF outside the plugin. Every
  directory is now opened component by component without following symlinks,
  and files are created and renamed relative to that directory.
- **Security:** `build-native.sh` refuses a `.cargo/config(.toml)` in the plugin
  root or the crate dir (or between): Cargo would load it, it isn't in
  `native.pin`, and a `rustc-wrapper` there could alter both the build and
  `--verify` while the pin still looked fresh.
- `build-native.sh` refuses `path` dependencies outside the crate dir and
  `kit/rust` (in any dependency, patch or workspace table): their sources are
  not in `native.pin`'s hash, so an edit there would go unnoticed.
- `build-native.sh` hashed the sources after building, so an edit while cargo
  ran (or between the two arches) was pinned to binaries built from the old
  source. It now hashes before and after, and installs nothing (and `--verify`
  fails) when they differ.
- **Security:** `sync.sh` trusted every path in a plugin's `foamy-kit.lock`, so
  a crafted lock (`../x`, an absolute path, `kit/../../x`) could make a sync,
  `--force` or not, delete or overwrite a file outside the plugin. Lock paths
  must now be normalised relative paths under `kit/`, `tests/kit-check.sh` or a
  component's root file, or sync and check refuse the plugin; sync also refuses
  any path whose parent directory resolves outside the plugin (a symlinked
  `tests/`). The generated `tests/kit-check.sh` rejects the same lock paths.
- `Bounded::run` kept feeding standard input only while stdout or stderr was
  open: a child that closed or redirected its output before reading its input
  got it silently truncated. It now writes all of it (until the child stops
  reading: `EPIPE`), within the deadline.
- Stamps: `.toml` files use `#`; Rust and TOML files carry the stamp on line 1
  always (a `#![…]` attribute is not a shebang), so version changes never
  shift line numbers that panic locations embed.

### Decisions
- The plugin root is the Cargo workspace root (a plugin-owned four-line
  `Cargo.toml`, `Cargo.lock` next to it): cargo hashes a path dependency
  outside the workspace by its absolute path, so with the workspace at
  `native/` a worktree and the live checkout built different x86_64 binaries.
- The release profile is passed with `--config kit/rust/release.toml` (it ranks
  above the manifests) instead of a stamped `.cargo/config.toml`, and plugin
  manifests may not declare `[profile]`, so committed binaries depend only on
  the sources, the vendored kit and the toolchain.
- **`foamy-helper::hash`**: `sha256`/`sha256_hex` in plain Rust (the favicon
  module's, now public), so helpers need neither `sha2` nor ring for cache names.
- **`foamy-helper::net`**: `DeadlineStream`, socket I/O bounded by one
  absolute deadline. A socket timeout bounds each blocking call, so a peer
  trickling bytes (or rustls making several reads per record) could stretch a
  request far past its budget; the stream re-arms the timeout to the time left
  before every read and write and fails with `DeadlineExceeded` after it.
- **`foamy-helper::tls`** (cargo feature `tls`): the one crypto provider and
  trust store for HTTPS in every helper: `provider()` (Graviola through
  `rustls-graviola`), `system_roots()`/`system_roots_der()` (the system CA
  store, loaded once), `client_config()` (WebPKI, TLS 1.2 and 1.3),
  `cpu_supported()`/`ensure_supported()` and `UNSUPPORTED`, so a CPU without
  the instructions Graviola needs reports an error instead of aborting.
- `rust-toolchain.toml` goes to the plugin root, not the crate dir: rustup
  looks upwards from the working directory, so one file covers any crate dir.
- **HTTPS crypto: Graviola for every helper, not ring or aws-lc-rs.** Both of
  those compile C, so cross-building them needs a C compiler and musl
  sysroot per target, and the committed bytes would depend on the build
  machine's clang version (the same problem as `rusqlite` below). Graviola is
  Rust and assembly only and builds byte-identically with rustc alone. The
  cost: it needs AES, carry-less multiply, and on x86_64 AVX2, BMI2 and ADX
  (Intel Broadwell / AMD Zen or newer), on aarch64 the ARMv8 crypto
  extensions (Apple Silicon, Raspberry Pi 5, not a Pi 4). On other CPUs HTTPS
  features report `UNSUPPORTED`; everything else in the helper still works.
- **SQLite for `favicon`: a built-in read-only reader, not `rusqlite`.**
  `rusqlite` with `bundled` does cross-build for aarch64-musl with clang and
  rust-lld, byte-identically on one machine (tried: about 1.5 MB per arch for
  "hello world"), but only with a musl sysroot that isn't packaged here (musl's
  headers downloaded and installed by hand) and C flags the build tool would
  have to inject, and the committed bytes would then depend on the host's
  clang version: the next clang upgrade, or another developer's machine, would
  fail `--verify` with no source change, and the pin records only the Rust
  toolchain. The reader (`favicon/sqlite.rs`, about 1,200 lines with its tests) covers
  what the Python query reads: rollback and WAL databases (committed frames,
  checksums and salts as SQLite's recovery), table b-trees, records with
  overflow pages, `CREATE TABLE` column lists, SQLite's lock protocol, and a
  structural check of every b-tree for the snapshot (the part of `PRAGMA
  quick_check` that matters here). UTF-8 databases only (Chromium's).

## 0.4.7 — 2026-11-05

### Changed
- `FoamyPanelFooter`: the bottom padding is `spacing` (was `gapSmall`), so the row sits as far
  above the popup's bottom edge as below the hairline (live check: clock's footer had 12 px over
  the row and 4 px under it).

## 0.4.6 — 2026-11-04

### Added
- `FoamyWallClock`: epoch-aligned second/minute ticks avoid negative timer delays during daylight-saving fallback. Disabled clocks stop and refresh immediately when enabled again.

## 0.4.5 — 2026-11-02

### Changed
- FoamyIcon `arrow-down-to-line` (Lucide 1.65.0) replaces `chevrons-down` (0.4.3), which only
  GitHub's "Pull all" used; 109 names.

## 0.4.4 — 2026-11-02

### Added
- **`FoamyI18n.updatedAgo(updatedMs, nowMs)`**: a footer's freshness, "Updated just now", then
  minutes, hours and days (live check: the clock footer read "Updated 1283 minutes ago"). Plugins
  carry the plural entries "Updated %1 minutes ago", "Updated %1 hours ago" and "Updated %1 days
  ago" plus "Updated just now". DESIGN.md "Footer" names it, and "Updating…" while a refresh
  replaces stale data.

## 0.4.3 — 2026-11-02

### Added
- FoamyIcon `chevrons-down` (Lucide 1.65.0), for GitHub's "Pull all"; 109 names.

## 0.4.2 — 2026-10-31

Settings pages read as one list (live check: media, GitHub, notification-center mixed full-width
dropdowns/fields with compact rows).

### Added
- **`FoamyDropdown { compact: true }`**, the row form of FoamyNumberField compact: label (subtitle,
  normal weight) and optional `description` on the reading start, the dropdown on the end, sized
  to its widest option plus the chevron (`compactNaturalWidth`; `compactWidth` overrides, e.g. for
  a `labelDelegate`), at most `compactMaxFraction` (0.5) of the row, eliding beyond. The open list
  may be wider than a capped trigger (up to the row) and grows toward the label; RTL mirrors.
  Row height `rowHeight + gapSmall` (taller when the text wraps), as FoamyToggle rows. New:
  `triggerItem`; the trigger reports `Accessible.ComboBox` with the label/description. The
  full-width form is unchanged.
- `FoamyNumberField.description` (compact form): under the label, as in toggle rows.
- `FoamyStyle.unitWidthCompact` (18).
- DESIGN.md "Short values use the row form": numbers, enum choices and intervals in settings are
  rows; full width with the label above only for free text, paths, URLs, commands, long option
  labels and composite rows; with a checklist for the plugin sweep.

### Changed
- **Compact FoamyNumberField rows are as tall as toggle rows** (`rowHeight + gapSmall`, was
  `controlHeight`) and their unit column is narrow and end-aligned (`unitWidthCompact`), so the
  unit ends on the row's trailing edge like a switch or a compact dropdown. Stacked fields still
  line up (units up to 18 px; wider units widen the column, as before). Full-width fields are
  unchanged.

### Fixed
- **FoamySettingsSection with `info`** (GitHub "Git LFS (i)"): the title line was as tall as the
  (i) button, so its description sat ~5 px further down (and the section ~5 px lower) than under a
  plain title. The heading line is now as tall as the title text and the (i) overhangs it; the
  open note keeps clear of the button. Section title/description Texts have objectNames
  (`foamySectionTitle`, `foamySectionDescription`).

### Tests
- `test_rows.py` (Rows.qml; 4.0.6 and 4.5-rc2, LTR/RTL, scale 1.0/1.25): shared row height and
  trailing edge for toggle, compact number and compact dropdown rows; dropdown natural width, the
  half-row cap and elision; the open list's width and edge; keyboard pick keeps `value`; full-width
  dropdown unchanged; equal title → description gap with and without (i).

## 0.4.1 — 2026-10-31

### Added
- `FoamyHeader.iconGlyph` / `iconFamily` (forwarded by FoamyHeroBand): a font glyph instead of a
  Lucide `iconName` for brand marks Lucide doesn't have, e.g. the Teams logo
  (`iconGlyph: "\u{f02bb}"`, nf-md-microsoft_teams, in the Omarchy mono font by default). Same
  18 px box and tint as the Lucide icon; hidden by `centered` bands; not mirrored in RTL.
  (foamy-teams, user #7)

## 0.4.0 — 2026-10-31

Round 6 of the live UI review (user feedback at 125 % scaling). New components and two
behaviour changes every plugin gets on resync. Existing APIs are unchanged.

### Changed (on resync, no code change needed)
- **Popups grow to the screen, not to 640 px.** `FoamyPopup.maxHeight` defaults to 0: the card
  fits its content up to the host's `availableCardHeight` (screen minus the bar, the gap and a
  margin; measured from the 4.0 strip window or the 4.5 bar thickness), and scrolls only beyond.
  `FoamyPopupCard` gained the same `maxHeight` (default 0). Set `maxHeight:
  FoamyStyle.popupMaxHeight` to keep the old cap. (vitals, monitor: "taller so content fits")
- **Header: at most three buttons top right.** FoamyHeader/FoamyHeroBand move the least important
  trailing actions (declared in priority order) and Settings into a ⋯ menu when actions + Settings
  (+ a menu) exceed `maxButtons` (3). Of today's plugins only foamy-notification-center's header
  overflows (search, clear, its own ⋯, Settings); see the 0.4.0 handoff for its migration.
- **Settings pages scroll normally with the wheel.** Root cause, measured offscreen with synthetic
  WheelEvents on Qt 6.12: Flickable turns every wheel event into a short smoothing animation that
  starts from the current position. A high-resolution wheel (the user's Logitech G502 X; most
  current mice) sends one notch as several small events (8 × 15 instead of 1 × 120), each
  restarting the animation, so a notch moved 9–28 px instead of 72. FoamySettingsPage now scrolls
  with FoamyWheelScroll: one notch = `wheelScrollLines` × `rowHeight` (108 px) however it is split,
  notches add up (animated by FoamyMotion.slider, instant under reduced motion), touchpad pixel
  deltas 1:1.

- **FoamyToggle rows are plain rows, not boxed cards** (user: notification-center settings). The
  row is the kit's own now (the stock `ToggleSwitch` on the end): label in subtitle size and
  normal weight, optional description in bodySmall/secondary, height `rowHeight + gapSmall` (taller
  when the text wraps), a soft fill under the cursor/pointer, an accent ring on Tab focus, optional
  `divider` hairline. Same API (label, description, checked, hasCursor, clicked(), hovered(bool),
  rounded, foreground, accent, fontFamily, titleSize, descriptionSize); `switchItem`, `hot` added.
- **FoamyHeroBand `hasHero` counts only shown hero items** (round6-train): a hero whose items
  are all hidden is no hero (no gap under the title row). The hero slot stays "visible" outside
  the compact form, at zero height when empty.

### Fixed
- FoamyHeader queued its relayout with `Qt.callLater`; a header destroyed before it ran (popup
  opened and closed in one frame, a bar removed: foamy-monitor's runtime test) threw a TypeError.
  It uses a child Timer now; so does FoamyInfoNote's scroll-into-view.

### Added
- **FoamyNumberField `compact`** for short values (vitals' % thresholds and °C margins): the
  label on the reading start, a narrow field sized to the longest value (`compactDigits`, from
  `from`/`to`/`decimals`; `compactFieldWidth`), the unit after it, one row; right-aligned digits;
  stacked compact fields line up at the unit; the error line stays under the row.
- **FoamyMenu / FoamyMenuItem**: in-card menu dropping from a button (the ⋯ menu; usable for row
  menus too). An overlay inside the popup card, trailing edge on the button's trailing edge,
  mirrored in RTL, kept inside the card (above the button when there is no room below, scrolls when
  long). Every entry has an icon; separators; `checked`; `destructive`; submenus open in place with
  a Back row. Keys while open: Up/Down/j/k/Home/End, Enter/Space/Right (Left in RTL) activate or
  open a submenu, Left/h/Backspace back, Esc back or close, Tab closes; a press outside closes;
  focus returns. Closes when the header is hidden.
- **FoamyHeader/FoamyHeroBand overflow API**: `menuItems`, `maxButtons`, `menuHasCursor`,
  `menuHovered(bool)`, `menuOpen`, `openMenu(keyboard)`, `closeMenu()`, `toggleMenu()`,
  `overflowing`, `settingsInMenu`, `shownTrailing`, `menuButton`, `menu`; FoamyHeader `showTitle`,
  `buttonsWidth`. Moved actions keep working through their own `clicked`; their menu entry uses
  their `iconName` and tooltip text. `trailing` is now a `list<Item>` laid out by the header
  (declaring actions as children or `trailing: [...]` both still work).
- **FoamyHeroBand `centered: true`**: no title icon; hero first and centred; title (title size)
  and meta centred under it; the buttons pinned to the trailing top corner; centred content keeps
  clear of them on both sides. For clock and weather.
- **FoamyPanelFooter**: hairline, the source (`source`) or leading items (an action like clock's
  "Calendar"), the status ("Updated 3 minutes ago", `statusError`, `statusClickable`, short
  `statusTooltip`) and a refresh FoamyAction (`refreshing` spins and makes it inert,
  `refreshHasCursor`, `refreshHovered`, `refreshClicked`).
- **FoamyInfoNote** and **FoamySettingsSection `info`**: an (i) beside a heading opens an inline
  note under it (bodySmall, secondary, wrapped, subtle rounded surface, the column's width)
  instead of a tooltip; it scrolls itself into view in a settings page. (github's Git LFS help
  spanned the whole screen as a tooltip.)
- **FoamyButton**: a form button that reads as a button: `secondary` (field fill + border),
  `primary` (accent fill, `FoamyPalette.onAccent` text), `destructive` (urgent tint + border);
  optional icon, `busy` (spinning, inert), `hasCursor`/`hovered` for the panel cursor,
  `focusable` with a 2 px focus ring. (audio Verify/Apply/Remove)
- **FoamyWheelScroll** `{ target: flickable }` for plugin lists and pages, with `ensureVisible(item
  [, margin])` (follows a growing section for `followMs`), `scrollBy`, `scrollTo`, `wheel(event)`.
  FoamySettingsPage exposes `ensureVisible(item)`, `flickable`, `wheel`.
- FoamyPalette `menuFill`, `noteFill`, `onAccent`. FoamyIcon: `clock`, `alarm-clock`, `bell-ring`,
  `timer`, `circle-help`, `ellipsis-vertical` (Lucide 1.65.0); 108 names.
- DESIGN.md: header button rule (≤ 3, priority order, Settings last in the ⋯ menu, icons on every
  entry), menus, centred band, footer, buttons, help notes, "tooltips only for short labels",
  sliders ("the cursor highlights thumb and track, never a filled row"), scrolling, popup heights.

### Tooling
- `preview/render.py --scale 1.25` and `harness.Run(scale=…)`: render at a display scale
  (`QT_SCALE_FACTOR`; windows get the device pixel ratio, PNGs are in device pixels, the simulated
  screen stays 1920×1080 logical). Inherited Qt scale variables no longer leak into runs.
- Tests (4.0.6 and 4.5-rc2, LTR/RTL, scale 1.0 and 1.25): `test_menu.py` (overflow rule, menu
  placement in the card and against the ⋯ button in both directions, keys, submenu, press outside,
  focus restore, a re-shown action is drawn), `test_components.py` (centred band, footer, buttons,
  info note, plain toggle rows, compact number fields, `hasHero`, popup heights), `test_wheel.py` (Qt baseline printed as NOTE, split notches, adding
  notches, pixel deltas, horizontal and inner wheel users, bounds, settings page, ensureVisible, info
  note). Geometry: the default popup now fills the available height; an explicit cap still caps.
  `run_shell` fails a run that logs a `polish()` loop (a layout that never settles).

## 0.3.5 — 2026-10-31

### Fixed
- **SafeTextField text inset doubled when sized with `width:`** (live UI check: clock "Calendar
  app", train From/To; also FoamyTextSettingField, which places its field in a Column). The
  attached TextArea resizes the Flickable's contentWidth to the text's own width, and a field with
  an explicit width ended up scrolled to `contentX = -leftPadding`, so the text started one padding
  too far in (22 px instead of 11). The horizontal scroll is now clamped to the text whenever the
  geometry or scroll changes; long text still scrolls to the cursor.
- **SafeTextField didn't mirror in RTL panels** unless the caller set an alignment: it now defaults to
  an explicit `horizontalAlignment: TextEdit.AlignLeft`, which LayoutMirroring flips.
- `editorItem` exposes the editor (tests, glyph geometry).
- Tests (both hosts): the first/last glyph sits at the same x for a `width:`-sized field, a
  RowLayout `fillWidth` field, FoamyTextSettingField and FoamyNumberField, in LTR (padding + border)
  and RTL (against the right padding); long text still scrolls to keep the cursor visible.

### Tooling (also in this release)
- `check.sh` / `foamykit.py lint`: `pua-literal` (an icon-font character written literally) is an
  error by default; `--warn-pua` reports it as a warning instead. `--strict` is accepted and ignored.

## 0.3.4 — 2026-10-30

Fixes from the 0.3.3 resync (kit-issues: foamy-lock, foamy-media, foamy-vitals,
foamy-notification-center, foamy-train).

### Security
- **FoamyIpcPreference could lose the lock route (regression in 0.3.2).** 0.3.2 made it poll only
  while a rival was present at its last check, so a handler registered or moved ahead *after* that
  check (another "lock" service) kept the route: `omarchy-shell lock …` (and the pre-suspend status
  poll) reached the wrong lock. IpcRegistry keeps handlers in a plain array mutated in place and has
  no change signal, so the preference polls again for as long as it is active on 4.5 (one short array
  scan every `interval`, 5 s). Regression test: the rival arrives after the check settled. foamy-lock's
  own runtime test (registry re-claim) passes against this build on 4.5 and 4.0.

### Fixed
- **FoamyPrefsQueue on 4.5 kept a synchronously reflected inline save pending** (foamy-media): 4.5's
  `updateEntryInline` updates `settings` inside the call, before the value became pending, so it stayed
  pending for 10 s, hid outside changes, and the next save wrote it back. The queue settles right after
  registering it. Tested with a host that reflects synchronously, plus an outside change in between.
- **SafeTextField TypeError ("Math" undefined) on settings state switches** (foamy-train):
  `onMaximumLengthChanged` could run while a page was built or torn down. It now waits for completion
  and uses no JS globals (also in the length clamp). Not reproduced in isolation; covered by a test
  that switches settings pages (sync and async Loader, a Repeater of `maximumLength` fields) 12 times
  with the log checked for TypeErrors.
- **FoamyNumberField/FoamyTextSettingField couldn't retry a failed save with the same value**
  (foamy-notification-center): the commit guard is cleared when a new edit starts, and `saveFailed()`
  shows the saved value again and allows the same input to commit (wire it to the save's failure, e.g.
  FoamyPrefsQueue `onFailed`).
- **A refused paste was silent in the settings fields** (foamy-vitals): SafeTextField's `pasteError` is
  shown in the field's error line and emitted as `pasteFailed(message)`.

### Added
- `preview/compare.py`: screenshot comparison (files or directories) on RGB *and* alpha, treating fully
  transparent pixels as equal whatever their hidden RGB; `--tolerance`; exit 0/1/2. Use it instead of
  ad-hoc PIL scripts (one compared in a way that reported every image identical).

## 0.3.3 — 2026-10-30

### Fixed
- **Stacked FoamyNumberFields didn't line up with mixed units** (foamy-vitals): the unit label's
  width set the field width, so "%" and "°C" fields ended a few pixels apart. The unit now sits in a
  fixed column (`unitWidth`, default `FoamyStyle.unitWidth` 32), so stacked fields share x and width
  in LTR and RTL. A unitless field among them sets `reserveUnit: true`. Units wider than the column
  widen it: use short symbols, or the same larger `unitWidth` across a section.

## 0.3.2 — 2026-10-30

From the Codex review of the plugin PRs (/tmp/foamy-fix/reviews/unanswered.md).

### Fixed
- **FoamyHeroBand kept every artwork decoded** (foamy-media#2): each distinct `imageSource` was
  loaded into the band's Canvas and never unloaded, and popup bodies are retained, so covers piled
  up for the shell's lifetime. The band now holds at most one picture: the previous one is unloaded
  on change, and the current one while the band is hidden (popup closed) or the source clears; it
  reloads when shown. `loadedImage` reports what is held. Tested by cycling 50 covers.
- **FoamyIpcPreference polled forever**: it re-claimed every 5 s for the shell's lifetime; it now
  polls only while another handler shares the target (a later handler queues behind it anyway).

### Added
- **FoamyNumberField** (also pulled in by FoamySettings): a numeric settings field that never
  assigns over its `value` binding. Shows `value` (following external changes) when not editing,
  keeps a draft while editing, Enter/focus-out commit once only a valid changed number
  (`committed(v)`), Escape restores and is consumed (the page stays), Up/Down step by `stepSize`
  within `from`..`to`, `decimals`, invalid-input message (`invalidText`, AlertMessage), language
  digits and decimal mark accepted, RTL row, `hasCursor`. Replaces hand-rolled numeric rows that did
  `text = …` (bolt, vitals, media, notification center: see KIT-0.3.2-HANDOFF).
- **FoamyTextSettingField** (component FoamyNumberField): the same draft/commit/Escape rules for
  free-text settings, with `validate(text)` (true, or false / a message) and `trim`. Replaces
  media's hand-rolled text rows.
- Demo plugin settings use FoamyNumberField.

### Checked, nothing to change
- Kit-wide sweep for assignments over caller bindings, Canvas/Image resources never released and
  timers running while hidden: FoamyDropdown (0.2.0 fix holds), FoamyToggle, SafeTextField (internal
  edits only), settings skeleton, FoamyPopup (radius/colour bound on the host card), FoamyAction
  (spinner only while visible), FoamyPrefsQueue (expiry timer only while values are pending),
  FoamyIcon (data-URL images, pixmap-cache bounded).

## 0.3.1 — 2026-10-30

Round-5 feedback on 0.3.0 (kit-issues newer than the 0.3.0 release).

### Fixed
- **FoamyHeroBand over the card's rounded bottom** (foamy-train #4): a band that ends the card
  (empty states, outside-schedule, band-only popups) painted its square bottom over the card's
  rounded corners and border. The band finds its popup card and, when its bottom meets the card's,
  rounds its bottom corners like the top and drops the hairline (`endsCard`, `roundBottom`; set
  `roundBottom` to override). Plugins need no spacer.
- **`render.py --trio` rewrote ordinary `anchors { }` blocks in dev trees** (foamy-monitor): a file
  with any `PanelWindow` (monitor's Identify overlay in Panel.qml) got every block-form `anchors { }`
  renamed, breaking normal items. The rewrite (`harness.transform_panel_windows`) is now
  brace-scoped: it swaps `PanelWindow {` for the offscreen stand-in, drops `WlrLayershell.*`, and
  renames `anchors { }` only when it is a direct property of such a window. Dev files outside `Ui/`
  get the stand-in through their own `import qs.Ui as FoamyFakeUi`, so files that don't import
  `qs.Ui` render too. Regression fixture: `tests/fixtures/old-monitor/` (reduced monitor dev Panel).
- **Preview temp-dir hygiene**: every run owns `<prefix><pid>-<random>` (mkdtemp, 0700) and removes
  only its own dir; trio/dev work dirs are PID-tagged too. `python3 preview/harness.py --gc
  [--dry-run]` removes only dirs whose owner PID is gone and that no live process uses. Never
  `rm -rf /tmp/foamy-kit-preview-*`: other agents' renders live there.

### Not changed
- **Fake MPRIS helper**: foamy-media's `preview/Before.qml` has no fake player yet (dev shows its
  "not running" view), so there is nothing to generalise; revisit when one exists.
- foamy-lock's registry item was resolved in 0.2.0 (FoamyIpcPreference, adopted in foamy-lock 80368b4).

## 0.3.0 — 2026-10-30

The foamy header band is back, as part of the design language: the tinted,
full-bleed header area many plugins had on `dev` (power, audio, github,
vitals, syncthing, notification center, weather), with the compact 4.5
header layout on it.

### Added
- **FoamyHeroBand**: the band. Title row (FoamyHeader: icon, title, meta,
  trailing actions, settings button) and a hero slot (a ColumnLayout, so it
  mirrors in RTL) on the popup surface tinted toward the accent: a diagonal
  wash with a soft glow at the trailing top corner (`FoamyPalette.bandFill`,
  `bandFillEnd`, `bandGlow`; dark and light), a hairline into the body
  (`bandEdge`). Full bleed; top corners at the popup radius minus the border
  (`FoamyStyle.bandRadius`). Compact paddings (`bandPaddingTop/Bottom` 16,
  `bandGap` 14). Drawn with Canvas: identical under the software renderer,
  static (nothing for reduced motion to stop), mirrored in RTL.
  `imageSource` (artwork, cover-fitted and clipped by the band) and
  `background: Component` (a scene such as a sky) keep the geometry and text
  treatment under a readability scrim (`bandScrimTop/Bottom`). `compact: true`
  is the settings form (back, "Settings", "Saving…").
- FoamySettingsPage shows the compact band instead of a plain header row.
- FoamyHeader and FoamySettingsHeader: `horizontalPadding`, `topPadding`,
  `bottomPadding` (the band sets them).
- `render.py --trio`: Before (`origin/dev`, via `git archive`) / After 4.0.6 /
  After 4.5 per view, `<view>-before.png` / `-after-4.0.png` / `-after-4.5.png`
  and a `trio.md` PR table (`--url-prefix`). Pre-kit popup forks are swapped for
  the offscreen window and bare `Color.` is qualified in the dev copy, so dev
  renders as it looked; Before falls back from 4.5 to the 4.0.6 host (labelled)
  when dev doesn't render or its fork is clipped there. `preview/Before.qml` or
  `--before-preview` describes the dev UI.
- Previews can capture pre-kit fork popups (no `cardItem`): the harness finds the card.
- Tests: test_band.py (both hosts × dark/light × LTR/RTL: geometry in a real
  FoamyPopup card, rounded transparent corners, tint vs body, hairline, glow side,
  hero alignment, clipped picture), test_trio.py (dev fork on a throwaway repo,
  clipped-fork and failure fallbacks, missing ref, untouched repo, no leaks);
  the demo plugin uses the band with a hero, an artwork state and the compact
  settings band.

### Not changed
- **Exact dev recipes per plugin** (power's flat 0.075 tint, NC's 58 px band):
  one band for all; plugins keep their own picture through `imageSource` /
  `background`, not their own tint.
- **MultiEffect blur under artwork** (dev media): optional per plugin, gated on the
  renderer; the base band never depends on it.

## 0.2.0 — 2026-10-30

Triage of the kit issues filed while migrating the 18 plugins to 0.1.0
(`/tmp/foamy-fix/kit-issues/*.md`) and the Codex review of the plugin PRs.
Resync with `sync.sh ../foamy-*`; add new components with `--add`.

### Fixed
- **FoamyDropdown no longer assigns `value` on select** (foamy-clock, Codex review). Upstream's
  `root.value = v` destroyed the caller's `value:` binding; popup bodies are kept between opens,
  so later changes to the setting (CLI, bar cycling) stopped showing. Selection now only emits
  `changed(v)`; the pick shows through `shownValue` until `value` changes, the list reopens, or
  `pickHoldMs` (10 s) passes. New `select(v)` does what the list does. No other kit control assigns
  over a caller binding (checked: FoamyToggle/stock Toggle, SafeTextField, settings skeleton, popups).
- **FoamyIcon `info` was Lucide `megaphone`** (foamy-weather); it is now Lucide `info`. The old
  path is available as `megaphone` (foamy-train used `info` for its notice megaphone).
- **Settings reset on open** (foamy-syncthing observation): the `onOpenedChanged: if (opened)
  editingSettings = false` pattern breaks `openSettings()` on a closed popup, because `Ui.Panel.open()`
  flips `opened` synchronously. New **FoamySettingsState** (`show()`/`hide()`, resets on close only,
  `holdOnClose`). The demo fixture uses it. Affected plugin: foamy-github (see KIT-0.2-HANDOFF).
- **Preview harness leaks** (coordinator): `qs` and the private bus get a parent-death signal and
  their own process group; `stop()` kills the group; every live run is stopped at exit; renders
  clean their temp dir (`--keep` to keep it); SIGTERM/SIGHUP run the cleanup. Five orphaned
  `qs -p /tmp/foamy-kit-preview-*` processes from earlier renders were terminated.
- **Preview harness used the desktop's D-Bus** (foamy-media): each run gets a private
  `dbus-daemon` without service activation (`--bus none` for a dead address), so live MPRIS players
  and notifications never reach tests or screenshots.
- **Preview harness loaded plugins as `qs:@` URLs** (foamy-syncthing, foamy-notifications), so
  same-directory types in plugin subdirectories failed without a hand-written qmldir. Previews now
  load the plugin over `file://`, like the shell does.

### Added
- FoamyIcon: `github` (Lucide 0.577.0: Lucide 1.x dropped brand icons), and from Lucide 1.65.0
  `git-branch`, `arrow-up`, `arrow-down`, `arrow-right`, `eye`, `chevron-left`, `calendar`,
  `bell`, `bell-off`, `search`, `x`, `ellipsis`, `mouse`, `keyboard`, `message-square` (aliases
  `message`, `chat`), `users`, `battery`, `battery-low`, `battery-medium`, `battery-full`,
  `battery-charging`, `battery-warning`, `zap`, `skip-back`, `skip-forward`, `shuffle`, `repeat`,
  `repeat-1`, `music`, `megaphone`; `play`, `pause` and `plug` refreshed to Lucide 1.65.0.
  `chevron-left` mirrors in RTL. `tools/update-icons.py` regenerates entries from lucide-static.
- FoamyPrefs: `array` (`maxItems`) and `object` field types with `validate(value)` (true, or false /
  a message); `problem()`; `equal()` (key-order-insensitive); `overlay()`/`settle()`; `save(…,
  pending)` merges over saved-but-unreflected values, never over a stale entry. Array values take
  `sh -c 'omarchy-shell shell setBarWidget … " [json]" "{}"'` on the CLI path: `qs ipc call` (4.0, or
  4.5 without the socket) splits a `[…]` argument into a list (verified, tests/test_ipc_cli.py).
- **FoamyPrefsQueue** (from teams/power): one queue per panel — inline or CLI saves, one process at
  a time, newest value per key, `effectiveSettings`, `value(key)`, `saving`, `busy`, `error`,
  `canRetry`, `retry()`, `saved`/`failed` signals; a failed CLI save restores the previous value.
- `kit/node-loader.cjs`: `require("../kit/node-loader.cjs").load("FoamyPrefs")` for node tests.
- FoamyIpcResolver: `handlersFor()`, `others()`, `prefer()`, `call()`. **FoamyIpcPreference** keeps a
  FoamyIpc first for a shared target (foamy-lock vs stock `lock`), no registry splicing in plugins.
- **FoamyPeerIpc** (from foamy-notifications' PeerIpc): in-process IpcRegistry call on 4.5,
  bounded `omarchy-shell` fallback. New component: `sync.sh <plugin> --add FoamyPeerIpc`.
- FoamyStyle: `font.numeral` (56) and `font.numeralCompact` (40) for hero numbers; `menuPadding` (8).
- FoamyPopup `maxHeight` (default `popupMaxHeight`; 0 = screen limit only).
- FoamyPopupCard padding = `FoamyStyle.menuPadding`.
- FoamyCursorSurface `cursorShape` (pointing hand by default).
- FoamyCursor `plain(modifiers)` and `emitTextKey(catcher, text, modifiers)`: `PanelKeyCatcher.textKey`
  is `(text)` on 4.0 and `(text, modifiers)` on 4.5.
- SafeTextField `maximumLength`.
- `sync.sh --add`.
- Lint (coordinator, after Codex found Nerd Font glyphs silently dropped in audio and bolt):
  `empty-glyph` fails on `*Glyph { text: "" }`; `pua-literal` warns on literal private-use
  characters (use `"\u{f0e7}"`, verified to work in QML); `check.sh --strict` fails on warnings.
- Preview: `popup` may be a FoamyPopupCard (declared `var`; its card is copied onto the screen at its
  anchor) or, for service plugins, any Item with a `cardItem`; previews may omit `bar`/`anchorItem`;
  `--timeout`, `--bus`. Harness `fakebin` for CLI stand-ins in tests.
- Tests: test_features.py (all of the above on both hosts), test_ipc_cli.py, test_harness.py (no
  leaks on timeout, killed parent, context manager), FoamyPopup maxHeight and card padding in the
  geometry test, node tests for the new prefs API, the old fork vendored as the negative control.

### Not changed
- **Existing FoamyIcon paths** stay the plugins' approved 0.1.0 shapes (only `info`, `play`, `pause`,
  `plug` were replaced): refreshing all of them to Lucide 1.65 would change every plugin's look
  without a request.
- **`FoamyStyle.effectsAvailable`** (media, weather): a singleton can't read `GraphicsInfo`, which is
  attached per item. DESIGN.md documents gating with `layer.enabled: GraphicsInfo.api !==
  GraphicsInfo.Software` instead.
- **Notification-only shared files** (BrowserIdentity.js, BrowserIcons.qml, browser-favicon.py…) stay
  in the two notification plugins, as their issue proposed; shipping them would put browser-cache and
  ImageMagick code into 16 plugins that never use it.
- **A `preferred` property on FoamyIpc** (lock): IpcHandler would expose it to IPC callers; the
  resolver functions and FoamyIpcPreference do it from outside.
- **Automatic leading space for `[`-arguments in FoamyPeerIpc**: it would change the string the peer
  receives on the in-process path; documented instead.
- **Tab bar / PanelSlider cursor** (monitor notes): no second plugin needs them yet.
- **4.5 plugin facade has no `barSizeFor`** (notch floor): host behaviour for every third-party widget.
- **Shell-literal command check** (foamy-github #5): plugin-specific validation of repository-supplied
  commands; not a shared component yet.

## 0.1.0 — 2026-10-30

First release: tokens, palette, motion, i18n, FoamyPopup/FoamyPopupCard wrapping the stock panels,
FoamyIpc, FoamyShared, header/action/icon/dropdown/text field/settings/cursor/prefs, sync/check/lint,
offscreen preview harness, tests on 4.0.6 and 4.5-rc2.
