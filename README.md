# foamy-kit

The canonical source of the components every foamy Omarchy shell plugin shares
(`foamy-audio`, `foamy-bolt`, … `foamy-weather`), plus the tools that keep
them identical: `sync.sh`, `check.sh`, a design lint, an offscreen preview
harness for screenshots, and `tools/build-native.sh` for plugins' bundled
Rust helpers ([Native helpers](#native-helpers)). The look and the rules live in [DESIGN.md](DESIGN.md).

Plugins can't share files at runtime (each is a self-contained directory and
`omarchy-plugin-validate` rejects symlinks), so the kit is **copied** into
each plugin as stamped regular files under `kit/`. A stamped copy is never
edited in a plugin: change it here, then sync.

## Components (`kit/`)

| Component | Files | What |
|---|---|---|
| FoamyStyle | `FoamyStyle.qml` (singleton) | Radius, border, font family and type scale, widths, spacing, control sizes |
| FoamyPalette | `FoamyPalette.qml` (singleton) | Surface tones and theme status colours from colors.toml |
| FoamyWallClock | `FoamyWallClock.qml` | Epoch-aligned seconds/minutes, with `enabled` demand gating; safe across daylight-saving fallback |
| FoamyMotion | `FoamyMotion.qml` (singleton) | Durations through `Style.duration` (4.5), `reduceMotion`, named tokens |
| FoamyI18n | `FoamyI18n.qml` (singleton) | `t()`, `tn()` plurals, `number()`, `formatLocale`, `rightToLeft`; 4.5 Translations, English on 4.0 |
| FoamyPopup | `FoamyPopup.qml` | Stock `qs.Ui.KeyboardPanel` with the foamy surface and a lazy `body` |
| FoamyPopupCard | `FoamyPopupCard.qml` | Stock `qs.Ui.PopupCard` with the foamy surface (menus, tray) |
| FoamyIpc | `FoamyIpc.qml`, `FoamyIpcResolver.js`, `FoamyIpcPreference.qml` | IpcHandler that also registers with 4.5's IpcRegistry (omarchy-shell socket); `prefer/others/call`; keep a shared target |
| FoamyPeerIpc | `FoamyPeerIpc.qml` | Call another plugin's IPC: in-process on 4.5, bounded `omarchy-shell` fallback |
| FoamyShared | `FoamyShared.qml` (singleton), `FoamyMember.qml` | One leader per shell across per-monitor bar instances, open-popup demand |
| FoamyHeader | `FoamyHeader.qml` | Icon, title, meta, trailing actions (at most three buttons; overflow into a ⋯ menu with Settings last), settings button |
| FoamyHeroBand | `FoamyHeroBand.qml` | The tinted full-bleed header band: title row + hero slot, `centered` variant, compact settings form, own picture or scene |
| FoamyMenu | `FoamyMenu.qml`, `FoamyMenuItem.qml` | In-card menu dropping from a button (the ⋯ menu): icons, separators, submenus, single-cursor keys, RTL |
| FoamyAction | `FoamyAction.qml` | Icon/label action button, settings button, spinner |
| FoamyButton | `FoamyButton.qml` | Form button (primary/secondary/destructive, icon, busy, focus ring) |
| FoamyPanelFooter | `FoamyPanelFooter.qml` | Footer: source or leading action, "Updated …", refresh |
| FoamyInfoNote | `FoamyInfoNote.qml` | (i) beside a heading that opens an inline help note (instead of long tooltips) |
| FoamyWheelScroll | `FoamyWheelScroll.qml` | Normal wheel/touchpad scrolling for any Flickable, `ensureVisible(item)` |
| FoamyIcon | `FoamyIcon.qml` | Lucide superset, 108 names (ISC, `LICENSE-LUCIDE`); `tools/update-icons.py` |
| FoamyDropdown | `FoamyDropdown.qml` | Stock Dropdown, foamy styled, RTL, never assigns over the caller's `value` (`LICENSE-OMARCHY`) |
| SafeTextField | `SafeTextField.qml`, `clipboard.sh` | Text field with bounded, out-of-process paste, `maximumLength` |
| FoamyNumberField | `FoamyNumberField.qml`, `FoamyTextSettingField.qml` | Binding-safe numeric and text settings fields: draft, Enter/focus-out commit, Escape restore, step, validation, compact one-row form for short values |
| FoamySettings | `FoamySettingsPage/Header/Section/Error/State.qml`, `FoamyToggle.qml` | Settings page skeleton (wheel scrolling, `ensureVisible`, section `info`), plain toggle rows, open/close state |
| FoamyCursor | `FoamyCursor.qml`, `FoamyCursorSurface.qml` | Single keyboard/pointer cursor model and row surface |
| FoamyPrefs | `FoamyPrefs.js`, `FoamyPrefsQueue.qml`, `node-loader.cjs` | Schema (incl. array/object), queued saving (inline, else the CLI), node loader for unit tests |
| FoamyNative | `FoamyNative.js`, `node-loader.cjs`, `rust/release.toml`, `rust/foamy-helper/**`, `rust-toolchain.toml` (plugin root) | Launch the plugin's bundled helper `bin/<arch>/<name>`, the shared Rust crate `foamy-helper`, the pinned toolchain and release profile. Opt-in: `sync.sh <plugin> --add FoamyNative` ([Native helpers](#native-helpers)) |

Each file's header documents its API. Dependencies are in `kit/components.json`.

## Sync

```bash
./sync.sh ../foamy-audio                                   # first time: every component
./sync.sh ../foamy-audio --components FoamyPopup,FoamyI18n # or a subset (+ dependencies)
./sync.sh ../foamy-*                                       # later: refresh, keeping each plugin's set
./sync.sh ../foamy-lock --add FoamyPeerIpc                 # add a component to the plugin's set
```

Sync writes `kit/` (components, a generated `kit/qmldir` registering the
singletons, license notices), `tests/kit-check.sh`, and `foamy-kit.lock`
(version, components, body hashes). Line 1 of every copied file (line 2 after
`pragma`, `.pragma` or a shebang) is

    // foamy-kit 0.1.0 <sha256 of the body> — do not edit; change foamy-kit and run sync

`.sh`, `.toml` and `qmldir` use `#`. Rust and TOML files always carry the stamp
on line 1 (a Rust `#![…]` attribute is not a shebang), and it is always one
line, so a kit version change never shifts a line number (Rust panic locations
embed them). A component's files may live in subdirectories of `kit/` (glob
patterns such as `rust/foamy-helper/src/**/*.rs` in `kit/components.json`) and
may place files at the plugin root (`rootFiles`, e.g. `rust-toolchain.toml`);
those are stamped, locked and checked like the rest. `optIn` components
(FoamyNative) are left out of a first sync without `--components`.

Sync is idempotent, refuses to overwrite a stamped file that was edited in the
plugin (`--force` discards the edit), refuses unknown files or symlinks in
`kit/`, removes components no longer selected, and runs
`omarchy-plugin-validate` afterwards. Plugins import the kit with
`import "kit"` (`import "../kit"` from a subdirectory) and JS with
`import "kit/FoamyPrefs.js" as Prefs`.

`tests/kit-check.sh` is self-contained (bash, sed, sha256sum): it re-hashes
every stamped file, so a local edit fails the plugin's own test run.

## Check

```bash
./check.sh ../foamy-*              # versions + stamps + design lint
./check.sh --lint-only ../foamy-x  # just the lint
./check.sh --allow-unsynced …      # don't fail plugins that have no lock yet
./check.sh --warn-pua …            # report literal icon-font glyphs as warnings, not errors
```

Fails when plugins are on different kit versions, a stamped file was edited,
or the design lint finds a violation (see DESIGN.md, "Lint"). The lint covers
git-tracked `.qml`/`.js` outside `tests/` and `preview/`.

## Native helpers

A plugin that needs more than QML (atomic state files, locks, child processes
with bounds, protocol parsing) ships **one Rust multi-call binary**,
`foamy-<plugin>-helper <subcommand> …`, committed as static musl executables
for x86_64 and aarch64. Users install the plugin as a plain checkout and need
no Rust; other CPUs get a clear "unavailable" state. The `FoamyNative`
component brings everything the build needs; `tools/build-native.sh` builds
reproducibly and `check.sh` / `tests/kit-check.sh` verify the result.

### Layout in a plugin

```
Cargo.toml                  plugin-owned: the Cargo workspace (exact content below)
Cargo.lock                  committed; every build uses --locked
rust-toolchain.toml         kit (FoamyNative): toolchain 1.99.1, both musl targets, clippy, rustfmt
native/Cargo.toml           package foamy-<plugin>-helper (template below)
native/src/main.rs          the helper; its contract is the doc comment at the top
native/native.pin           written by tools/build-native.sh; never edit
bin/x86_64/foamy-<plugin>-helper    built, mode 0755, static-pie ELF
bin/aarch64/foamy-<plugin>-helper   built, mode 0755, static ELF
kit/FoamyNative.js          kit: command builder for QML
kit/node-loader.cjs         kit: loads FoamyNative.js in node tests
kit/rust/release.toml       kit: the release profile (passed to cargo with --config)
kit/rust/foamy-helper/…     kit: the shared crate, a path dependency
```

`Cargo.toml` at the plugin root, exactly (with `members = ["search"]` for a
crate in `search/`):

```toml
[workspace]
members = ["native"]
exclude = ["kit"]
resolver = "3"
```

The plugin root is the workspace root so that cargo identifies the vendored
`kit/rust/foamy-helper` by its path relative to the plugin, not its absolute
path; without it a worktree and the live checkout build different bytes.
`exclude = ["kit"]` keeps workspace-wide cargo commands off the kit's code.

`native/Cargo.toml`:

```toml
[package]
name = "foamy-<plugin>-helper"
version = "0.1.0"
edition = "2024"
license = "MIT"
publish = false

[dependencies]
foamy-helper = { path = "../kit/rust/foamy-helper" }
serde_json = "1"     # only what the helper needs; justify each one in the PR
```

No `[profile]` (in either manifest) and no `[workspace]` in the crate:
`build-native.sh` refuses them. The release profile is `kit/rust/release.toml`
(opt-level "s", lto "fat", codegen-units 1, panic "abort", strip "symbols"),
which cargo ranks above the manifests. There is no `.cargo/config.toml`;
linker and flags come from the build tool. `rust-toolchain.toml` sits at the
plugin root because rustup reads it from the working directory upwards, so
`cargo` anywhere in the plugin uses 1.99.1.

The binary name defaults to `foamy-<x>-helper` for manifest id `foamy.<x>`
and the crate dir to `native/`. Another layout (foamy-menu: `search/`,
`foamy-menu-search`) is given once, `--crate search --bin foamy-menu-search`,
and `<crate>/native.pin` remembers it.

### Recipe

From the plugin's worktree, with `KIT` the foamy-kit checkout:

```bash
export CARGO_TARGET_DIR=~/.cache/foamy-native/foamy-<plugin>   # before ANY cargo command (see below)
$KIT/sync.sh . --add FoamyNative          # kit/FoamyNative.js, kit/rust/…, rust-toolchain.toml, tests/kit-check.sh
# write Cargo.toml (workspace), native/Cargo.toml, native/src/main.rs
(cd native && cargo generate-lockfile)    # writes ./Cargo.lock (only that file)
$KIT/tools/build-native.sh . --test       # cargo fmt --check, clippy --all-targets -D warnings, cargo test
$KIT/tools/build-native.sh .              # builds both arches, installs bin/<arch>/…, writes native/native.pin
$KIT/tools/build-native.sh . --verify     # clean rebuild in a fresh target dir, byte compare with bin/
bash tests/kit-check.sh                   # kit stamps + native pin, checksums, static ELF, staleness
$KIT/check.sh .                           # the same from the kit, plus the design lint
```

Commit `Cargo.toml`, `Cargo.lock`, `native/`, `bin/x86_64/…`, `bin/aarch64/…`
and the synced kit files together, and add `/target/` to the plugin's
`.gitignore`.

Cargo hygiene:

- **`CARGO_TARGET_DIR` first.** Plain `cargo test`, `cargo clippy` or
  `cargo build` in a plugin would create `target/` inside it, and the shell
  watches (and hot-reloads) plugin folders. Export
  `CARGO_TARGET_DIR=~/.cache/foamy-native/foamy-<plugin>` before any cargo
  command (`build-native.sh` sets it itself). `check.sh` and
  `tests/kit-check.sh` warn when they find a cargo target dir in the plugin.
- **Format only your crate:** `cargo fmt -p foamy-<plugin>-helper`. Never
  `cargo fmt --all`, which would reformat `kit/rust` (then the kit check
  fails: the vendored files are edited). `build-native.sh --test` only checks.
- **The source hash covers the whole crate dir** (every file but
  `native.pin` and `target/`, docs and test data included), so any edit
  there, even a README or a comment, makes the binaries stale: rebuild
  (`build-native.sh .`) and commit the new pin.

**An existing crate** (a helper that already had its own `Cargo.toml`, like
foamy-menu's `search/`): `git mv <crate>/Cargo.lock Cargo.lock` (keep the
lock, don't regenerate it), delete the crate's `[profile]` (the build tool
refuses one) and any `.cargo/config.toml`, add the root workspace and the
`foamy-helper` path dependency, then build with `--crate`/`--bin` once.

**Vendored third-party modules** (code copied from another project into
your crate) stay byte-identical to upstream: never edit or reformat them.
Put the exemptions on the `mod` declaration in your own code:

```rust
#[rustfmt::skip]
#[allow(clippy::all, dead_code, unused)]
mod vendored_parser;
``` After changing dependencies run
`cargo update -p <crate>` (or `cargo generate-lockfile`) in `native/`; after a
kit sync that changed `foamy-helper`'s dependencies, `cargo update -p
foamy-helper`. Never run cargo in `kit/rust/`, and never point
`CARGO_TARGET_DIR` into the plugin.

`build-native.sh` (`tools/foamykit.py native`):

- refuses to build when the kit files are edited or FoamyNative isn't synced,
  when the root workspace, `Cargo.lock` or the crate is missing, or a manifest
  declares `[profile]`;
- runs `cargo build --locked --release --target <x86_64|aarch64>-unknown-linux-musl
  --bin <binary> --config kit/rust/release.toml` with `RUSTUP_TOOLCHAIN` from
  `rust-toolchain.toml`, `CARGO_TARGET_DIR=${FOAMY_NATIVE_CACHE:-~/.cache/foamy-native}/foamy-<x>`
  (never inside the plugin: the shell hot-reloads plugin folders), `rust-lld`
  as the linker, `-C link-self-contained=yes -C link-arg=--build-id=none`, and
  `--remap-path-prefix` for `~/.cargo`, the rustup home, the target dir, the
  plugin, `kit/rust` and the crate; the caller's `RUSTFLAGS`, `CARGO_PROFILE_*`,
  `CARGO_TARGET_*` and wrappers are dropped;
- installs each binary atomically (a temp file in `bin/<arch>/`, then a
  rename) and only when its bytes changed, then writes `native.pin`: crate,
  binary, toolchain, kit version, the **source hash** and a sha256 per arch;
- `--verify` rebuilds in a fresh target dir (removed afterwards) and fails
  unless both binaries are byte-identical to the committed ones and the pin
  is current; `--test` runs fmt, clippy and tests in the same cache.

The source hash covers the crate (without `native.pin` and `target/`),
`kit/rust/`, and `Cargo.toml`, `Cargo.lock` and `rust-toolchain.toml` at the
root, each file hashed without its kit stamp, so a kit version bump that
leaves the Rust code alone keeps the binaries fresh. `check.sh` and
`tests/kit-check.sh` (bash, coreutils, `file`) fail when a pinned binary is
missing, a symlink, not executable, has another checksum, is not a static
64-bit ELF for its arch, or the sources changed since the build ("stale"),
and when FoamyNative is synced without a `native.pin`.

### Launching from QML

```qml
import "kit/FoamyNative.js" as FoamyNative

Process {
  command: ["timeout", "--kill-after=1s", "30s"].concat(FoamyNative.command(
    FoamyNative.localPath(Qt.resolvedUrl(".")), "foamy-power-helper", ["set", profile]))
  onExited: function(exitCode) {
    if (FoamyNative.unavailable(exitCode)) service.error = FoamyI18n.t("This plugin's helper isn't available for this CPU.")
  }
}
```

`command(pluginDir, name, args)` returns
`["bash", "-c", 'exec -- "$1/bin/$HOSTTYPE/$2" "${@:3}"', "foamy-native", pluginDir, name, …args]`:
bash's builtin `$HOSTTYPE` picks `x86_64` or `aarch64` and `exec` replaces bash,
so no extra process remains. A missing binary or an unsupported CPU exits 127
(126: not executable) instead of a Process that never reports an exit.
`unavailable(code)` is true for 126 and 127: show the message above (in the
plugin's catalogs; `FoamyNative.UNAVAILABLE_TEXT` is the English text) and don't
retry in a loop. Keep each call's `timeout --kill-after=…` wrapper, restart and
backoff logic and stdin/stdout handling. `localPath(Qt.resolvedUrl(".."))` from a
subdirectory. Helpers never exit 126 or 127 themselves.

### Panics and arguments

The release profile has `panic = "abort"`, so a panic would end in
`SIGABRT` and a core dump. `json::run` and `json::serve` install the kit's
panic hook (a reply where there is one, then exit 101); **every helper that
runs its own loop or protocol calls `foamy_helper::process::exit_on_panic(101)`
first thing in `main`**. Read argv with `std::env::args_os()` inside the
`json::run` closure (or after the hook), never `std::env::args()` before it:
`args()` panics on a non-UTF-8 argument, before any hook exists. The
fixture's `main` is the pattern:

```rust
fn main() -> ExitCode {
    foamy_helper::process::exit_on_panic(101);
    match std::env::args_os().nth(1).as_deref().and_then(OsStr::to_str) {
        Some("serve") => serve(),                    // its own JSON-lines loop
        _ => json::run(|| main_json(&args()?), json::error_reply), // args(): args_os → Strings, INVALID_ARGUMENT
    }
}
```

### The shared crate (`kit/rust/foamy-helper`)

| Module | What |
|---|---|
| `io` | `read_limited`, `read_stdin_limited`, `LineReader` (max line length; an overlong line is reported and skipped, the next one still reads) |
| `json` | `to_line`/`write_line`/`print_line` (one compact line), `parse`, `serve` (JSON-lines loop: a reply per request, bad lines answered), `run` (one-shot entry point: always one JSON reply, also on failure and panic, which exits 101 instead of aborting), `Failure` (code, message, exit code), `error_reply` |
| `fs` | `write_atomic` (temp file `O_EXCL\|O_NOFOLLOW`, exact mode, fsync, rename, directory fsync; refuses symlinks, foreign-owned targets and directories, and directories that are world-writable without the sticky bit; group-writable own directories, as with umask 002, are fine), `ensure_private_dir` (0700, checked), `read_file_limited` (no symlinks, FIFOs, devices) |
| `lock` | `FileLock::try_exclusive`/`exclusive`/`exclusive_within` (`flock`, 0600, owner checks), `runtime_dir(plugin)` (`$XDG_RUNTIME_DIR/<plugin>`, 0700), `try_runtime_lock` |
| `child` | `Bounded`: deadline, per-stream output cap, kill of the whole process group on either, stdin feeding (all of it, also after the child closed its output), `keep_env`/`env_clear`, `new_session`, rlimits, `inherit_fd` (Python's `pass_fds`), `PR_SET_PDEATHSIG` by default |
| `process` | `exit_on_panic` (exit with a code instead of aborting), `die_with_parent` (`PR_SET_PDEATHSIG`), `new_session` (`setsid`), `limit` (rlimits), `set_umask` |
| `favicon` (feature) | `run` (browser-favicon.py's whole stdin/stdout contract), `resolve`, `lookup`, `Dirs`, `valid_png`, `valid_hostname`, `browser_roots`: favicons from local Chromium-family caches, never a web request; SQLite read by a built-in read-only reader (SQLite's `SHARED` lock on the live file, in-memory snapshot when the browser holds it, WAL frames, structural check) |
| `sandbox` (feature) | `BpfFilter` (seccomp-BPF via `seccompiler`: `decoder()` is artwork.py's filter; `to_bytes`, `memfd` for `bwrap --seccomp`; `Bounded::seccomp`), `ExecOnly` (Landlock: only the given files may execute, applied in `pre_exec`; `probe` = github_status's setpriv probe and fallback; `Bounded::exec_only`, `apply_to(&mut Command)`), `Bwrap` (bubblewrap argv builder, `readonly_host`, fd options, `bounded`, `works`), `elf_interpreter`, `which` |

Enable a feature in the plugin crate, `foamy-helper = { path =
"../kit/rust/foamy-helper", features = ["favicon"] }` (or `["sandbox"]`),
then `cargo update -p foamy-helper` for the lock. Dependencies: `rustix` (fs,
process, event), `serde`, `serde_json`; `favicon` adds `libc`; `sandbox` adds
`libc`, `seccompiler` and `landlock`. No async runtime, no build script, no
C code. qemu-user has neither seccomp nor Landlock: the aarch64 binary
reports them unsupported there (fail closed), so test sandboxing on x86_64. Rules for helper code: std threads and blocking I/O, keep
running the same system tools with the same argv, carry every bound of the
code being replaced over on purpose, and use `json::run` (or `serve`) so every
failure still prints JSON. `tests/fixtures/native-plugin` is a complete
reference plugin (its `native/src/main.rs` documents a contract the way a
plugin helper does).

Requirements for building (developers only): rustup with the toolchain from
`rust-toolchain.toml` (`rustup toolchain install 1.99.1 --profile minimal -c
clippy,rustfmt -t x86_64-unknown-linux-musl,aarch64-unknown-linux-musl`),
`file`, and qemu-user binfmt to run the aarch64 binary in tests.

## Preview

```bash
preview/render.py ../foamy-audio --host both --out /tmp/audio-shots
preview/publish-screenshots.sh ../foamy-audio /tmp/audio-shots/4.5 fix-omarchy-45/audio
```

`render.py` runs Quickshell offscreen (software renderer, temp HOME and XDG
dirs, no Wayland/Hyprland variables) against a host shell: `--host 4.0`
(`/usr/share/omarchy/shell`) or `--host 4.5` (`/tmp/omarchy-ref/v45/shell`;
QML is loaded, no host script or binary is ever run). Offscreen Qt has no
layer shell, so the host's own `Ui/KeyboardPanel.qml` is loaded with its
`PanelWindow` swapped for an item that draws into a simulated 1920x1080
screen; its geometry and motion code is the host's. 4.5 runs use a full-screen
bar window, 4.0 runs a strip window, like the real bars. Each run gets a
private D-Bus session (no service activation: the desktop's MPRIS players
and notifications are invisible), and `qs` dies with the render, even when
the render itself is killed; the temp dir is removed (`--keep` keeps it).
The plugin is loaded over `file://`, like the shell loads it, so plugin
subdirectories need no qmldir.

The plugin provides `preview/Preview.qml` (mock data, no processes):

```qml
import QtQuick
import "../kit"
import ".." as Plugin
Item {
  id: preview
  required property QtObject bar          // mock bar facade (barSize, popout, shell.updateEntryInline)
  required property Item anchorItem       // the bar button on the simulated screen
  property var previewStates: ["default", "empty", "settings"]
  property string previewState: "default" // set by the harness before each capture
  property int settleMs: 600              // optional
  readonly property Item popup: popup
  FoamyPopup {
    id: popup
    anchorItem: preview.anchorItem; bar: preview.bar; open: true
    body: Component { Plugin.MyView { /* mock data by preview.previewState */ } }
  }
}
```

Per state it writes `<state>-screen.png` (bar strip and the popup where
FoamyPopup puts it) and `<state>.png` (the card). Options: `--states`,
`--theme dark|light|<colors.toml>`, `--language da` (4.5), `--position`,
`--rounding`, `--scale 1.25` (display scale: windows get that device pixel
ratio, PNGs are in device pixels, layout stays logical, like a 125 % output),
`--timeout`, `--bus private|none`, `--keep`.

Other preview shapes (examples in `tests/fixtures/demo-plugin/preview/`):

- a **pre-kit fork** (for `--trio` Before): `popup` may be the old
  `<Name>Popup`; the harness finds its card;

- a **FoamyPopupCard** menu: declare `readonly property var popup` (a card is a
  window, not an Item); its card is copied onto the screen at its anchor;
- a **service plugin** (toasts, no bar popup): leave out `bar`/`anchorItem`;
  `popup` is any Item with a `cardItem`, placed in screen coordinates (the
  preview fills the screen); without a `cardItem` only the screen is captured.

MultiEffect, ShaderEffect and layer effects draw nothing under the software
renderer the harness uses (as under Omarchy CPU rendering): gate them so the
content still reads without them (DESIGN.md, "Effects").

Temp dirs: each run owns one PID-tagged dir under `/tmp` and removes only that
one. Never `rm -rf /tmp/foamy-kit-preview-*` — concurrent renders (other
agents') live there. `python3 preview/harness.py --gc` removes only dirs of
runs whose process is gone.

Comparing screenshots: `preview/compare.py old.png new.png` (or two
directories). It compares RGB and alpha; never compare one without the other.

### Before / after trio

```bash
preview/render.py ../foamy-power --trio --url-prefix https://raw.githubusercontent.com/foamrider/foamy-power/pr-assets/fix-omarchy-45/power
```

Renders each view three times: `<view>-before.png` (the `origin/dev` tree,
`--dev-ref`), `<view>-after-4.0.png` and `<view>-after-4.5.png` (the working
tree), and writes `trio.md`, a PR-body table. Before comes from `git archive`
(the plugin repo is not touched), with layer-shell windows (pre-kit popup
forks, overlay windows) swapped for the offscreen stand-in — only the windows
and their own `anchors { }` blocks are rewritten — and bare `Color.` qualified
(Qt 6.12 shadows it), so dev looks as it did. Describe the dev UI in
`preview/Before.qml` in the current tree (or `--before-preview FILE`); else dev's
own `preview/Preview.qml` is used. Before tries `--before-host 4.5,4.0` in order:
when dev doesn't render on 4.5, or its popup fork is clipped there (the 120 px
card the kit fixed), it falls back to the 4.0.6 host and the column header says
so. Card images only; `--states` limits the views.

`publish-screenshots.sh` commits PNGs to the plugin's orphan `pr-assets`
branch through a temporary worktree (the working tree is untouched), prints
`raw.githubusercontent.com` URLs and the `git push` command. It never pushes.

## Compatibility

`dev` plugins target Omarchy 4.5 and must keep loading on 4.0.6. The kit
does that with runtime feature detection only: the stock KeyboardPanel and
PopupCard behave natively on each version, `FoamyI18n`/`FoamyIpc` resolve
4.5-only singletons through `Qt.createQmlObject`, `FoamyMotion` checks
`typeof Style.duration`. No dual code paths beyond that.

## Tests

```bash
tests/run-all.sh
```

Runs FoamyPrefs unit tests (node, through `kit/node-loader.cjs`), sync/check/lint
on throwaway copies, the FoamyPopup geometry test (4 bar positions, both hosts,
max height, menu padding, plus the old fork as a negative control), runtime
tests of i18n/motion/palette/prefs/cursor/leader election/IPC on both hosts
(English, Danish, Arabic), the 0.2 features (icons, tokens, dropdown binding,
prefs queue inline and CLI with fake `omarchy`, IPC preference and peer
calls, settings state, private D-Bus), a `qs ipc` argument probe, harness
leak tests, the demo, menu-card and service previews, and (0.4.0, both hosts,
LTR/RTL, scale 1.0 and 1.25) the header overflow menu (`test_menu.py`), the
centred band, footer, buttons, info note and screen-height popups
(`test_components.py`), and wheel scrolling (`test_wheel.py`, which also
prints how far Qt's own Flickable gets per notch).
`tests/fixtures/demo-plugin` is a reference plugin built only from the kit.
FoamyNative (0.5.0): `native.test.cjs` (command builder and the real `bash
exec` launch: arguments verbatim, exit 126/127) and `test_native.py` (subdirectory
sync and Rust/TOML stamps, `cargo fmt`/`clippy`/`test` of `foamy-helper`, the
fixture plugin `tests/fixtures/native-plugin` built for both arches, `--verify`
and a rebuild at another path byte-identical, check.sh and kit-check.sh on
pins, tampered, dynamic, wrong-arch and stale binaries, the helper's contract
on x86_64 and on aarch64 through qemu, and `FoamyNative.command` from node and
from Quickshell's `Process`).

## Versioning

See [CHANGELOG.md](CHANGELOG.md).


`VERSION` is the kit version stamped into every copy. Bump it for any change
under `kit/` or `tools/kit-check.sh.in`, then sync every plugin so `check.sh`
sees one version everywhere.

## License

MIT (`LICENSE`). `FoamyIcon` paths are Lucide (ISC, `LICENSE-LUCIDE`);
`FoamyDropdown` is adapted from Omarchy (MIT, `LICENSE-OMARCHY`); both notices
are copied into a plugin's `kit/` with the component.
