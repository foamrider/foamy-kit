# foamy-kit

The canonical source of the components every foamy Omarchy shell plugin shares
(`foamy-audio`, `foamy-bolt`, … `foamy-weather`), plus the tools that keep
them identical: `sync.sh`, `check.sh`, a design lint, one validation command
with pinned linters and formatters and its CI job ([Tooling](#tooling)), an
offscreen preview harness for screenshots, and a build tool for plugins'
bundled Rust helpers that each plugin carries itself ([Native helpers](#native-helpers)). The look and the rules live in [DESIGN.md](DESIGN.md).
The shared code review standard lives in [REVIEW.md](REVIEW.md): structure,
simplification, linting and dead-code analysis, defensive programming, security
and validation evidence. Read it before reviewing kit or plugin changes.

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
| FoamyMotion | `FoamyMotion.qml` (singleton) | Durations through `Style.duration`, `reduceMotion`, named tokens |
| FoamyI18n | `FoamyI18n.qml` (singleton), `FoamyI18nText.js`, `node-loader.cjs` | `t()`, `tn()` plurals, `number()`, `formatLocale`, `rightToLeft`; the shell's Translations. `FoamyI18nText.js`: its value substitution, and `translator(catalog, english)` for node tests |
| FoamyPopup | `FoamyPopup.qml` | Stock `qs.Ui.KeyboardPanel` with the foamy surface and a lazy `body` |
| FoamyPopupCard | `FoamyPopupCard.qml` | Stock `qs.Ui.PopupCard` with the foamy surface (menus, tray) |
| FoamyIpc | `FoamyIpc.qml`, `FoamyIpcResolver.js`, `FoamyIpcPreference.qml` | IpcHandler that also registers with the shell's IpcRegistry (omarchy-shell socket); `prefer/others/call`; keep a shared target |
| FoamyPeerIpc | `FoamyPeerIpc.qml` | Call another plugin's IPC: in-process, bounded `omarchy-shell` fallback |
| FoamyShared | `FoamyShared.qml` (singleton), `FoamyMember.qml` | One leader per shell across per-monitor bar instances, open-popup demand |
| FoamyHeader | `FoamyHeader.qml` | Icon, title, meta, trailing actions (at most three buttons; overflow into a ⋯ menu with Settings last), settings button |
| FoamyHeroBand | `FoamyHeroBand.qml` | The tinted full-bleed header band: title row + hero slot, `centered` variant, compact settings form, own picture or scene |
| FoamyMenu | `FoamyMenu.qml`, `FoamyMenuItem.qml` | In-card menu dropping from a button (the ⋯ menu): icons, separators, submenus, single-cursor keys, RTL |
| FoamyAction | `FoamyAction.qml` | Icon/label action button, settings button, spinner |
| FoamyButton | `FoamyButton.qml` | Form button (primary/secondary/destructive, icon, busy, focus ring) |
| FoamyPanelFooter | `FoamyPanelFooter.qml` | Footer: source or leading action, "Updated …", refresh |
| FoamyInfoNote | `FoamyInfoNote.qml` | (i) beside a heading that opens an inline help note (instead of long tooltips) |
| FoamyWheelScroll | `FoamyWheelScroll.qml` | Normal wheel/touchpad scrolling for any Flickable, `ensureVisible(item)` |
| FoamyIcon | `FoamyIcon.qml` | Lucide superset, 113 names (ISC, `LICENSE-LUCIDE`); `tools/update-icons.py` |
| FoamyDropdown | `FoamyDropdown.qml` | Stock Dropdown, foamy styled, RTL, never assigns over the caller's `value` (`LICENSE-OMARCHY`) |
| SafeTextField | `SafeTextField.qml`, `clipboard.sh` | Text field with bounded, out-of-process paste, `maximumLength` |
| FoamyNumberField | `FoamyNumberField.qml`, `FoamyTextSettingField.qml` | Binding-safe numeric and text settings fields: draft, Enter/focus-out commit, Escape restore, step, validation, compact one-row form for short values |
| FoamySettings | `FoamySettingsPage/Header/Section/Error/State.qml`, `FoamyToggle.qml` | Settings page skeleton (wheel scrolling, `ensureVisible`, section `info`), plain toggle rows, open/close state |
| FoamyCursor | `FoamyCursor.qml`, `FoamyCursorSurface.qml` | Single keyboard/pointer cursor model and row surface |
| FoamyPrefs | `FoamyPrefs.js`, `FoamyPrefsQueue.qml`, `node-loader.cjs` | Schema (incl. array/object), queued saving (inline, else the CLI), an invalid stored array kept until a forced save (`storedProblems.<key>` says which), node loader for unit tests |
| FoamyText | `FoamyText.js`, `node-loader.cjs` | `cap(text, lines, chars)` and `tooltip(text)`: text for a sink with no size bound of its own (the host bar tooltip), cut with a visible "…", never splitting a surrogate pair |
| FoamySchedule | `FoamySchedule.js`, `FoamyScheduleDay.qml`, `node-loader.cjs` | A weekly on/off schedule (`scheduleMonday`…`scheduleSunday`, overnight ranges) with a snooze/resume override kept in a state file, and its settings row (switch, from/to fields, injectable label component). Opt-in: `sync.sh <plugin> --add FoamySchedule` |
| FoamyNative | `FoamyNative.js`, `node-loader.cjs`, `native/native.py`, `native/build-native.sh`, `rust/release.toml`, `rust/foamy-helper/**`, `rust-toolchain.toml` and `.github/workflows/verify-native.yml` (plugin root) | Launch the plugin's bundled helper `bin/<arch>/<name>`, the shared Rust crate `foamy-helper`, the pinned toolchain and release profile, the build tool, and the CI workflow that rebuilds and attests the binaries. Opt-in: `sync.sh <plugin> --add FoamyNative` ([Native helpers](#native-helpers)) |

Each file's header documents its API. Dependencies are in `kit/components.json`.

## Sync

```bash
./sync.sh ../foamy-audio                                   # first time: every component
./sync.sh ../foamy-audio --components FoamyPopup,FoamyI18n # or a subset (+ dependencies)
./sync.sh ../foamy-*                                       # later: refresh, keeping each plugin's set
./sync.sh ../foamy-lock --add FoamyPeerIpc                 # add a component to the plugin's set
```

Sync writes `kit/` (components, a generated `kit/qmldir` registering the
singletons, license notices), `tests/kit-check.sh`, root `REVIEW.md`, the
[tooling](#tooling) (`tests/validate.sh`, `kit/tooling/validate.py`,
`mise.toml`, `ruff.toml`, `.oxlintrc.json`, `.qmlformat.ini`,
`.github/workflows/checks.yml`), the review block in `AGENTS.md`, and
`foamy-kit.lock`
(version, components, body hashes). Line 1 of every stamped code file (line 2 after
`pragma`, `.pragma` or a shebang) is

    // foamy-kit 0.1.0 <sha256 of the body> — do not edit; change foamy-kit and run sync

`.sh`, `.py`, `.toml`, `.yml`, `.ini` and `qmldir` use `#`. Rust and TOML files always carry the stamp
on line 1 (a Rust `#![…]` attribute is not a shebang), and it is always one
line, so a kit version change never shifts a line number (Rust panic locations
embed them). A component's files may live in subdirectories of `kit/` (glob
patterns such as `rust/foamy-helper/src/**/*.rs` in `kit/components.json`) and
may place files at the plugin root (`rootFiles`, e.g. `rust-toolchain.toml`);
those are stamped, locked and checked like the rest. `optIn` components
(FoamyNative) are left out of a first sync without `--components`.

`REVIEW.md` is always included, even with a component subset. Like license
notices, it is copied verbatim and hashed whole instead of carrying a code
stamp. Sync refuses to overwrite a different unowned guide or a locally edited
copy. Change the canonical guide here; keep plugin-specific instructions in
the plugin's own README or `AGENTS.md`. The guide sets the review standard
and the tooling target; syncing it does not install linters or configure
plugin CI.

Sync also points review agents at the guide (Codex reads `AGENTS.md`, not
`REVIEW.md`). It keeps one marked block in the plugin's `AGENTS.md`, creating
the file when it is absent:

    <!-- foamy-kit review: begin; managed by foamy-kit sync.sh, edit outside this block -->
    ## Code review
    …
    <!-- foamy-kit review: end -->

The rest of `AGENTS.md` belongs to the plugin and is kept byte for byte, with
its file mode; it is not in `foamy-kit.lock`. Sync replaces only the block
between the markers, and refuses (even with `--force`) a symlinked or
non-UTF-8 file or a damaged block: a missing, repeated, reordered or edited
marker. `check.sh` and `tests/kit-check.sh` fail when the block is missing or
differs from the current kit's.

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
./check.sh ../foamy-*              # versions + kit files + design lint
./check.sh --lint-only ../foamy-x  # just the lint
./check.sh --allow-unsynced …      # don't fail plugins that have no lock yet
./check.sh --warn-pua …            # report literal icon-font glyphs as warnings, not errors
```

Fails when plugins are on different kit versions, a stamped file, notice or
`REVIEW.md` was edited, the `AGENTS.md` review block is missing or stale, a
native helper doesn't match its pin ([Native helpers](#native-helpers)), or
the design lint finds a violation (see DESIGN.md, "Lint"). The lint covers
git-tracked `.qml`/`.js` outside `tests/` and `preview/`.

## Tooling

Every repository has one validation command, synced from the kit (foamy-kit
runs the same files on itself):

```bash
mise install                 # once: the tools mise.toml pins (https://mise.jdx.dev)
tests/validate.sh            # everything, on the Omarchy host
tests/validate.sh --ci       # what GitHub's runner can do (checks.yml runs this)
tests/validate.sh --fast     # no native helper tests; tests/suite.sh gets --fast
tests/validate.sh --only qmllint,ruff     # or --skip CHECKS; --list names them
tests/validate.sh --update-baseline qmllint   # rewrite a baseline, then review its diff
```

It prints a PASS, FAIL or SKIP line per check and exits nonzero on any
failure. A pinned tool that is missing or at another version fails with
"run `mise install`"; a check that can't run where you are (the host checks
under `--ci`) is a SKIP with the reason.

| Check | What runs |
|---|---|
| `kit-check` | `bash tests/kit-check.sh` |
| `plugin-validate` | `omarchy-plugin-validate <plugin>` (host) |
| `design-lint` | foamy-kit's `check.sh <plugin>`, when the kit is at `$FOAMY_KIT` or `~/GitHub/Personal/foamy-kit` (else SKIP) |
| `qmllint` | `/usr/lib/qt6/bin/qmllint` with `qs` as the Omarchy shell (`/usr/share/omarchy/shell`, or `FOAMY_HOST_45`) and Qt's QML dir on the import path; every default category, unused imports as errors, Qt Design Studio's categories off (host) |
| `qmlformat` | `/usr/lib/qt6/bin/qmlformat -s .qmlformat.ini`, compared with each file (host; Qt 6.12's output) |
| `oxlint` | `.oxlintrc.json` over every `.js`/`.cjs`/`.mjs`. QML-loaded files are linted from a copy in which `.pragma`/`.import` lines are `//` comments (same line numbers); their top-level functions are QML's API, so an unused one is not reported |
| `ruff`, `ruff-format` | `ruff check` and `ruff format --check` with `ruff.toml` (E, F, W, B, C901 at 15; E402 allowed in `tests/`) |
| `vulture` | `vulture --min-confidence 60` |
| `shellcheck` | `bash -n` and `shellcheck -x` on every `*.sh` and shell-shebang script |
| `shfmt` | `shfmt -i 2 -ci -bn -d` on the same scripts |
| `native` | `kit/native/build-native.sh . --test --crate <crate>` for each `native.pin` (`--fast`: SKIP; `--ci`: SKIP, verify-native.yml runs it) |
| `suite` | `bash tests/suite.sh [--ci] [--fast]`: the repository's own tests |

Kit-owned files (everything `foamy-kit.lock` lists, all of `kit/`) are never
linted or reformatted in a plugin. The checks read git-tracked and untracked,
non-ignored files.

**What a plugin adds** (its own files; sync never touches them):

- `tests/suite.sh`, required: the plugin's node, Python and offscreen runtime
  tests. It gets `--ci` (no Quickshell, no Omarchy host: run only node and
  host-free Python tests) and `--fast` (skip the slow runtime tests), and
  must exit nonzero on any failure. `FOAMY_KIT` is set when the kit was found,
  and the pinned tools (node included) come first on `PATH`.
- `tests/lint/<check>-baseline.txt` (qmllint, oxlint, ruff, vulture,
  shellcheck): the findings that existed when the check was adopted, written
  by `--update-baseline` and reviewed in the commit like code. An entry is
  file, rule, message and the reported line's text (not its number), so
  edits elsewhere don't invalidate it; only findings not in it fail, and a
  baselined C901 function fails again once its score grows. Validate notes
  fixed entries; shrink the file then. Never regenerate it to get a new
  finding through.
- `tests/lint/exclude.txt`: `<glob> [checks]  # reason` lines for paths a check
  must not read, such as test inputs whose exact text is the test, or
  harness scenes whose imports exist only in the harness's staged copy
  (`tests/qml/*  qmllint  # …`). The harness replaces `qs.Ui` with a staged
  copy that adds preview stand-ins, so qmllint's verdict on a harness file's
  imports is not evidence.
- `tests/lint/vulture-ignore.txt`: `<name>  # reason` lines for dynamic entry
  points Vulture can't see (atexit or signal handlers, names called by
  string).
- `.ruff.toml` (`extend = "ruff.toml"` first) and `tests/lint/oxlintrc.json`
  (`"extends": ["../../.oxlintrc.json"]`) for plugin rules or ignores, each
  with a comment saying why. `.mise.toml` adds tools; validate still requires
  the kit's pinned versions.

Adopting it in a plugin: sync, `mise install`, write `tests/suite.sh`, run the
formatters once and commit that migration on its own (`ruff format --config
ruff.toml <files>`, `shfmt -i 2 -ci -bn -w <scripts>`, `qmlformat -s
.qmlformat.ini -i <file>`; qmlformat moves an end-of-line comment after a
JavaScript statement to the next line, so move such comments above their
statement first), then `tests/validate.sh --update-baseline`, review and
commit the baselines.

The pins (`mise.toml`) are exact versions, each the newest release at least
a week old when chosen; `mise install` installs them, and CI installs the
same file through jdx/mise-action. Not pinned there: Python 3.11 or newer
(the system's: the tests use its packages), Qt 6, Quickshell and the Omarchy
shell (the host), and rustup (FoamyNative reads `rust-toolchain.toml`).
There is no JavaScript formatter yet.

`.github/workflows/checks.yml` runs `tests/validate.sh --ci` on ubuntu-24.04
for pushes to main and dev and for pull requests, with read-only contents
permission and no secrets; actions/checkout and jdx/mise-action are pinned by
commit. It sits beside verify-native.yml, which still rebuilds and attests
native helpers.

## Native helpers

A plugin that needs more than QML (atomic state files, locks, child processes
with bounds, protocol parsing) ships **one Rust multi-call binary**,
`foamy-<plugin>-helper <subcommand> …`, committed as static musl executables
for x86_64 and aarch64. Users install the plugin as a plain checkout and need
no Rust; other CPUs get a clear "unavailable" state. The `FoamyNative`
component brings everything the build needs, including the build tool
itself (`kit/native/build-native.sh`), so a plugin's binaries can be rebuilt
and verified from the plugin's repository alone. The build is reproducible,
`check.sh` / `tests/kit-check.sh` verify the result, the plugin's
`verify-native.yml` workflow rebuilds it on GitHub and attests it
([Provenance](#provenance-ci-rebuild-and-attestation)), and the build writes
the licenses of everything linked into it to `THIRD_PARTY_NOTICES.md`
([Third-party notices](#third-party-notices)).

### Layout in a plugin

```
Cargo.toml                  plugin-owned: the Cargo workspace (exact content below)
Cargo.lock                  committed; every build uses --locked
rust-toolchain.toml         kit (FoamyNative): toolchain 1.99.1, both musl targets, clippy, rustfmt
native/Cargo.toml           package foamy-<plugin>-helper (template below)
native/src/main.rs          the helper; its contract is the doc comment at the top
native/native.pin           written by kit/native/build-native.sh; never edit
bin/x86_64/foamy-<plugin>-helper    built, mode 0755, static-pie ELF
bin/aarch64/foamy-<plugin>-helper   built, mode 0755, static ELF
THIRD_PARTY_NOTICES.md      written by kit/native/build-native.sh with the binaries; never edit
kit/FoamyNative.js          kit: command builder for QML
kit/node-loader.cjs         kit: loads FoamyNative.js in node tests
kit/rust/release.toml       kit: the release profile (passed to cargo with --config)
kit/rust/foamy-helper/…     kit: the shared crate, a path dependency
kit/native/build-native.sh  kit: the build tool (runs kit/native/native.py)
.github/workflows/verify-native.yml   kit: CI rebuild, byte compare, attestation
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
which cargo ranks above the manifests. There is no `.cargo/config.toml` (the
build tool refuses one in the plugin or crate dir, and scrubs wrapper and flag
variables from its environment);
linker and flags come from the build tool. `rust-toolchain.toml` sits at the
plugin root because rustup reads it from the working directory upwards, so
`cargo` anywhere in the plugin uses 1.99.1.

The binary name defaults to `foamy-<x>-helper` for manifest id `foamy.<x>`
and the crate dir to `native/`. Another layout (foamy-menu: `search/`,
`foamy-menu-search`) is given once, `--crate search --bin foamy-menu-search`,
and `<crate>/native.pin` remembers it.

### Recipe

From the plugin's worktree, with `KIT` the foamy-kit checkout (only `sync.sh`
and `check.sh` need it; the build tool is the plugin's own copy):

```bash
export CARGO_TARGET_DIR=~/.cache/foamy-native/foamy-<plugin>   # before ANY cargo command (see below)
$KIT/sync.sh . --add FoamyNative          # kit/FoamyNative.js, kit/rust/…, kit/native/…, rust-toolchain.toml,
                                          # .github/workflows/verify-native.yml, tests/kit-check.sh
# write Cargo.toml (workspace), native/Cargo.toml, native/src/main.rs
(cd native && cargo generate-lockfile)    # writes ./Cargo.lock (only that file)
kit/native/build-native.sh . --test       # cargo fmt --check, clippy --all-targets -D warnings, cargo test
kit/native/build-native.sh .              # builds both arches, installs bin/<arch>/…, writes native/native.pin
                                          # and THIRD_PARTY_NOTICES.md
kit/native/build-native.sh . --verify     # clean rebuild in a fresh target dir, byte compare with bin/
bash tests/kit-check.sh                   # kit stamps + native pin, checksums, static ELF, staleness
$KIT/check.sh .                           # the same from the kit, plus the design lint
```

`$KIT/tools/build-native.sh <plugin> …` is a shortcut that runs the plugin's
copy. Commit `Cargo.toml`, `Cargo.lock`, `native/`, `bin/x86_64/…`,
`bin/aarch64/…`, `THIRD_PARTY_NOTICES.md` and the synced kit files together,
and add `/target/` to the plugin's `.gitignore`.

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
refuses one) and any `.cargo/config.toml` (refused too), add the root workspace and the
`foamy-helper` path dependency, then build with `--crate`/`--bin` once.

**Vendored third-party modules** (code copied from another project into
your crate) stay byte-identical to upstream: never edit or reformat them.
Put the exemptions on the `mod` declaration in your own code:

```rust
#[rustfmt::skip]
#[allow(clippy::all, dead_code, unused)]
mod vendored_parser;
```

After changing dependencies run
`cargo update -p <crate>` (or `cargo generate-lockfile`) in `native/`; after a
kit sync that changed `foamy-helper`'s dependencies, `cargo update -p
foamy-helper`. Never run cargo in `kit/rust/`, and never point
`CARGO_TARGET_DIR` into the plugin.

`kit/native/build-native.sh` (`kit/native/native.py`, standard library only;
`check.sh` imports the same module for its native checks):

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
  binary, toolchain, kit version (the plugin's `foamy-kit.lock` version, the
  version of the tool that built it), the **source hash** and a sha256 per arch,
  and `THIRD_PARTY_NOTICES.md` ([Third-party notices](#third-party-notices));
- `--verify` rebuilds in a fresh target dir (removed afterwards) and fails
  unless both binaries are byte-identical to the committed ones, the pin
  is current and `THIRD_PARTY_NOTICES.md` equals a fresh generation;
  `--verify --out DIR` also writes the rebuilt binaries to
  `DIR/<arch>/<binary>` (outside the plugin), which is what CI attests;
  `--test` runs fmt, clippy and tests in the same cache; `--notices` only
  rewrites `THIRD_PARTY_NOTICES.md` (for binaries that are current).

The source hash covers the crate (without `native.pin` and `target/`),
`kit/rust/`, and `Cargo.toml`, `Cargo.lock` and `rust-toolchain.toml` at the
root, each file hashed without its kit stamp, so a kit version bump that
leaves the Rust code alone keeps the binaries fresh. `check.sh` and
`tests/kit-check.sh` (bash, coreutils, `file`) fail when a pinned binary is
missing, a symlink, not executable, has another checksum, is not a static
64-bit ELF for its arch, or the sources changed since the build ("stale"),
when FoamyNative is synced without a `native.pin`, when the pin of fresh
binaries names another kit version than `foamy-kit.lock`, and when
`THIRD_PARTY_NOTICES.md` is missing or doesn't name the pin's source hash
and checksums. The pin's `kit` line is the kit version its binaries match:
the build writes it, and sync refreshes that one line in a pin whose source
hash still matches after the sync (a kit bump that leaves `kit/rust` alone),
never its source hash or checksums; a stale pin keeps the version that built
it until the rebuild.

### Third-party notices

A static binary contains its dependencies' code, so their license texts and
copyright notices ship with it. The marketplace reviewers check this too:
the plugin's own `LICENSE*` files cover the plugin and the projects it ports,
not crates such as rustls-webpki (ISC, "Copyright 2015 Brian Smith") or rustls
(Joseph Birr-Pixton) that the TLS helpers link. `kit/native/build-native.sh`
therefore writes **`THIRD_PARTY_NOTICES.md`** at the plugin root with the
binaries. Per binary it lists:

- the binary checksums and the pin's source hash (what `tests/kit-check.sh`
  matches against `native.pin`);
- every **crate** compiled into it for each musl target: name, version,
  SPDX license from its `Cargo.toml`, the `Cargo.lock` checksum, the arches,
  and links to its notices. The list is `cargo tree --locked --target <triple>
  --edges normal,no-proc-macro` with the build's features and flags.
  Build-dependencies and proc-macro crates (serde_derive, syn, …) only run on
  the build host and are left out; so are crates `Cargo.lock` records for
  other platforms or features the build doesn't enable (windows-*, ring,
  schannel, …), which are never compiled. While generating, the tool checks
  that every crate source path embedded in the binaries (panic locations)
  is in the list, and fails otherwise;
- the **toolchain's code**: the Rust standard library (in-tree notices from
  the pinned toolchain's `share/doc/rust/COPYRIGHT-library.html`) and its
  crates.io dependencies (addr2line, adler2, gimli, hashbrown, miniz_oxide,
  object, …) at the versions and checksums of the toolchain's
  `library/Cargo.lock` (see below), musl libc and the
  C runtime objects of the self-contained musl linking (musl 1.2.5's
  `COPYRIGHT`, embedded in the tool, which checks `libc.a`'s version), and
  LLVM's libunwind and crtbegin/crtend (the toolchain's `COPYRIGHT.html`);
- the first-party crates: the plugin's crate (`LICENSE`) and the vendored
  `kit/rust/foamy-helper` (foamy-kit's MIT license).

Then each distinct notice text once, with the crates that ship it: every
`LICENSE*`, `LICENCE*`, `COPYING*`, `NOTICE*`, `COPYRIGHT*` and `UNLICENSE`
file in the crate (vendored subdirectories included, tests, benches and
examples not) and its `license-file`, plus the copyright lines and SPDX ids
at the top of its source files, which is where vendored code keeps its
notices (graviola's s2n-bignum, mlkem-native and OpenSSL parts). The texts
come from the `.crate` archive in the cargo registry whose SHA-256 is the
`Cargo.lock` checksum (never from cargo's unpacked copy; a missing archive
is fetched once with `cargo fetch --locked`, and one that doesn't match is
refused), including a nonstandard `license-file` the manifest names; for a
crate that ships no license file at all
(graviola) the standard text of each license in its SPDX expression is
reproduced and marked so. Where a crate offers a choice of licenses, all its
texts are kept. The file is a supply-chain record, not a legal opinion.

**The standard library's dependencies** are crates.io crates that cargo
never fetches (they come precompiled in the toolchain). Their versions and
`.crate` checksums are the registry packages of the toolchain's
`library/Cargo.lock`: read from the rust-src component when it is installed,
else from the table `STD_LOCKS` in `native.py`, generated from that file for
each pinned toolchain (the build only needs the minimal profile, and CI
doesn't install rust-src; when both exist they must agree). Each linked one
(the sysroot crates of the musl targets, at the version the binaries name)
gets the notices of the toolchain's `COPYRIGHT-library.html` entry for that
exact version, else those of its `.crate` archive: from cargo's registry
cache, else `${FOAMY_NATIVE_CACHE:-~/.cache/foamy-native}/crates/`, else
downloaded from `static.crates.io` (not with `CARGO_NET_OFFLINE=true`), and
used and cached only when its SHA-256 matches the lock. Generation fails, and
nothing is written, when a dependency the binaries or the sysroot show has no
locked version or no notice text. A toolchain bump needs its `STD_LOCKS`
entry (or rust-src installed); `rust-toolchain.toml` itself stays as it is.

The generation is deterministic (the same plugin commit and toolchain give
the same bytes on any machine) and offline once the crates are fetched
(`cargo fetch --locked`; a build has already fetched them) and the standard
library's few archives are cached (the first generation downloads those
cargo doesn't have, under 1 MB for Rust 1.99.1). The file sits at
the plugin root, next to `LICENSE`, where reviewers look and where it ships
with the plugin; it is not one of the hashed build inputs (the crate dir,
`kit/rust`, the root `Cargo.*` and `rust-toolchain.toml`), so writing it never
makes the binaries stale. `--verify` (and so the CI workflow) regenerates it
and fails when the committed file differs; `tests/kit-check.sh` and
`check.sh`, which run without cargo, fail when it is missing or names other
binaries than `native.pin`. After a kit sync that introduces it, run
`kit/native/build-native.sh .` (the binaries don't change) or
`kit/native/build-native.sh . --notices`, and commit the file.

### Provenance: CI rebuild and attestation

The Omarchy plugin marketplace reports committed ELF files as
`bundled-executable-binary`, and a maintainer accepts that capability only
with evidence they can check themselves that the exact committed bytes were
built from the reviewed source (omacom/omarchy-plugin-marketplace#14501).
`native.pin`, README steps and "I rebuilt it locally" are not enough; a
public rebuild with a signed attestation at the exact commit is.

`.github/workflows/verify-native.yml` (synced, stamped) provides it. On every
push to `main` or `dev`, pull request and manual run, a GitHub-hosted runner
checks out the commit, installs the toolchain `rust-toolchain.toml` pins,
runs `tests/kit-check.sh`, `kit/native/build-native.sh . --test` and
`--verify --out $RUNNER_TEMP/rebuilt`, writes a table of each binary's git
blob and committed and rebuilt SHA-256 to the job summary, and uploads the
rebuilt files. On pushes and manual runs (not pull requests) a second job,
on a fresh runner that never builds (so no build script or dependency can
touch what it signs, and only it gets `id-token: write`), downloads them,
requires each to equal the committed git blob and `native.pin`, and attests
them with `actions/attest-build-provenance`. The attestation therefore
covers the committed files:

```sh
gh attestation verify bin/x86_64/<binary> --repo foamrider/foamy-<plugin> \
  --signer-workflow foamrider/foamy-<plugin>/.github/workflows/verify-native.yml \
  --source-digest <commit> --deny-self-hosted-runners
```

Actions are pinned by commit SHA; update them in `kit/native/verify-native.yml`
and sync. Everything the build reads is in the plugin at that commit, so the
attestation's source commit covers the build tool as well.

**Before filing or updating a marketplace Verify issue** for a plugin that
ships a helper: the target commit is the `main` HEAD, and the workflow run
for that push must be green. Put this in the issue:

- the run link (`gh run list -w verify-native.yml -b main -L 1`);
- a table of each `bin/<arch>/<binary>` with its git blob
  (`git rev-parse <commit>:bin/x86_64/<binary>`) and SHA-256, as in the
  run's summary;
- the `gh attestation verify` commands above, with the commit;
- a link to `THIRD_PARTY_NOTICES.md` at that commit (the notice mapping of
  the code linked into the binaries);
- the local rebuild from the README.

**The plugin README's "Verifying the helper binaries"** section names the
same three checks, all from the plugin's repository alone (no foamy-kit
clone, no hard-coded kit commit):

````markdown
## Verifying the helper binaries

`bin/x86_64/<binary>` and `bin/aarch64/<binary>` are compiled from the Rust
source in this repository: `native/`, the shared crate in `kit/rust/`, the
dependencies locked in `Cargo.lock` and the toolchain pinned in
`rust-toolchain.toml`, with the build tool in `kit/native/`. The build is
reproducible. `native/native.pin` records the toolchain, a hash of every
build input (`source`) and the SHA-256 of each binary.
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) lists the third-party code
linked into the binaries (crates, the Rust standard library, musl, LLVM's
libunwind) with the license texts and copyright notices it ships; the build
writes it and the verification below regenerates and compares it.

**CI.** The [Verify native helpers](https://github.com/foamrider/foamy-<plugin>/actions/workflows/verify-native.yml)
workflow rebuilds both binaries on a GitHub-hosted runner for every push,
compares them byte for byte with `bin/`, and attests the rebuilt files. To
check the committed files against that attestation (GitHub CLI):

```sh
gh attestation verify bin/x86_64/<binary> --repo foamrider/foamy-<plugin> \
  --signer-workflow foamrider/foamy-<plugin>/.github/workflows/verify-native.yml \
  --deny-self-hosted-runners
gh attestation verify bin/aarch64/<binary> --repo foamrider/foamy-<plugin> \
  --signer-workflow foamrider/foamy-<plugin>/.github/workflows/verify-native.yml \
  --deny-self-hosted-runners
```

Add `--source-digest <commit>` to require a particular commit.

**Yourself.** You need `rustup`, Python 3.11 or newer and `file`. From a
checkout of this repository at the commit you want to check:

```sh
rustup toolchain install "$(awk '$1 == "toolchain" { print $2 }' native/native.pin)" \
  --profile minimal --target x86_64-unknown-linux-musl,aarch64-unknown-linux-musl
kit/native/build-native.sh . --verify
```

It builds both binaries from scratch in `~/.cache/foamy-native/` (nothing is
written to the checkout), compares them byte for byte with `bin/`, checks
that the kit files are unmodified, that `native.pin` matches the source and
that `THIRD_PARTY_NOTICES.md` equals a fresh generation, and ends with
`verify OK (<binary>, <toolchain>, both arches reproducible)`.

### Building the helper yourself

To run binaries you built instead of the committed ones, build them in the
installed plugin (`~/.config/omarchy/plugins/foamy.<plugin>`) with the same
toolchain, then run `omarchy restart shell`:

```sh
cd ~/.config/omarchy/plugins/foamy.<plugin>
kit/native/build-native.sh .
```

The build is reproducible, so `git status` shows no change when your
binaries match the release, and `omarchy plugin update` still applies.
````

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
| `hash` | `sha256`, `sha256_hex` (plain Rust, `hashlib.sha256` compatible; cache names and content hashes, not for secrets) |
| `io` | `read_limited`, `read_stdin_limited`, `LineReader` (max line length; an overlong line is reported and skipped, the next one still reads) |
| `json` | `to_line`/`write_line`/`print_line` (one compact line), `parse`, `serve` (JSON-lines loop: a reply per request, bad lines answered), `run` (one-shot entry point: always one JSON reply, also on failure and panic, which exits 101 instead of aborting), `Failure` (code, message, exit code), `error_reply` |
| `fs` | `write_atomic` (temp file `O_EXCL\|O_NOFOLLOW`, exact mode, fsync, rename, directory fsync; refuses symlinks, foreign-owned targets and directories, and directories that are world-writable without the sticky bit; group-writable own directories, as with umask 002, are fine), `ensure_private_dir` (0700, checked), `read_file_limited` (no symlinks, FIFOs, devices) |
| `lock` | `FileLock::try_exclusive`/`exclusive`/`exclusive_within` (`flock`; a missing lock file is created 0600, an existing one keeps its mode; owner checks), `runtime_dir(plugin)` (`$XDG_RUNTIME_DIR/<plugin>`, 0700), `try_runtime_lock` |
| `child` | `Bounded`: deadline, per-stream output cap, kill of the whole process group on either, stdin feeding (all of it, also after the child closed its output), `keep_env`/`env_clear`, `new_session`, rlimits, `inherit_fd` (Python's `pass_fds`), `PR_SET_PDEATHSIG` by default; `stdin_fd` (standard input straight from an open file, still seekable), `nice`, `io_idle`; `pipe_into` → `Pipeline` (one child's standard output into another's input, moved with `splice` and counted: `run`, `run_with_progress`, `PipelineOutput`; see [Two-stage jobs](#two-stage-jobs)) |
| `net` | `DeadlineStream` (wraps a `TcpStream`/`UnixStream`; re-arms the socket timeout to the time left before every read and write, so rustls, an HTTP parser or `read_to_end` on top is bounded as a whole; `DeadlineExceeded`, `is_deadline`), `set_deadline` for long-lived connections. Connecting and name resolution are outside it: use `TcpStream::connect_timeout` with the time left, on a resolved address |
| `process` | `exit_on_panic` (exit with a code instead of aborting), `die_with_parent` (`PR_SET_PDEATHSIG`), `new_session` (`setsid`), `limit` (rlimits), `set_umask`, `set_run_budget`/`run_deadline` (one deadline for the whole run: every `Bounded` child and `Pipeline` ends by then, none starts after it) |
| `favicon` (feature) | `run` (browser-favicon.py's whole stdin/stdout contract), `resolve`, `lookup`, `Dirs`, `valid_png`, `valid_hostname`, `browser_roots`: favicons from local Chromium-family caches, never a web request; SQLite read by a built-in read-only reader (SQLite's `SHARED` lock on the live file, in-memory snapshot when the browser holds it, WAL frames, structural check) |
| `sandbox` (feature) | `BpfFilter` (seccomp-BPF via `seccompiler`: `decoder()` is artwork.py's filter, `threaded_decoder()` the same for a decoder that runs threads; `to_bytes`, `memfd` for `bwrap --seccomp`; `Bounded::seccomp`), `ExecOnly` (Landlock: only the given files may be `execve`d, applied in `pre_exec`; an allowed dynamic loader can still run other binaries passed to it, so it stops a program from running hooks and helpers by path, not code already running in the child; `probe` = github_status's setpriv probe and fallback; `Bounded::exec_only`, `apply_to(&mut Command)`), `Bwrap` (bubblewrap argv builder, `readonly_host`, fd options, `bounded`, `works`), `elf_interpreter`, `which` |
| `tls` (feature) | `provider` (Graviola, the one crypto provider for every helper), `system_roots`/`system_roots_der` (system CA store, loaded once), `client_config` (WebPKI, TLS 1.2+1.3), `cpu_supported`/`ensure_supported`/`UNSUPPORTED` (Graviola needs AES/PCLMUL, SSSE3, AVX, AVX2, BMI1/BMI2 and ADX on x86_64, NEON/AES/PMULL/SHA-2 on aarch64: check before a handshake, report instead of aborting; `UNSUPPORTED` is an i18n catalog key, translate it verbatim). With ureq: `default-features = false, features = ["rustls-no-provider"]` and `unversioned_rustls_crypto_provider(tls::provider())` |

Enable a feature in the plugin crate, `foamy-helper = { path =
"../kit/rust/foamy-helper", features = ["favicon"] }` (or `["sandbox"]`, `["tls"]`),
then `cargo update -p foamy-helper` for the lock. Dependencies: `rustix` (fs,
process, event, pipe), `serde`, `serde_json`; `favicon` adds `libc`; `sandbox` adds
`libc`, `seccompiler` and `landlock`; `tls` adds `rustls`, `rustls-graviola` and
`rustls-native-certs`. No async runtime, no build script, no C code (do not
add ring, aws-lc-rs or any `-sys` crate that compiles C: the bytes would
depend on the build machine's C compiler). qemu-user has neither seccomp nor Landlock: the aarch64 binary
reports them unsupported there (fail closed), so test sandboxing on x86_64. Rules for helper code: std threads and blocking I/O, keep
running the same system tools with the same argv, carry every bound of the
code being replaced over on purpose, and use `json::run` (or `serve`) so every
failure still prints JSON. A helper the QML side wraps in `timeout` (as in
the FoamyNative.js example) calls `process::set_run_budget` with less than
the wrapper's time first thing in `main`: `timeout` signals only the
helper's own process group, not the groups its children lead, so children
whose own timeouts add up to more would outlive it and no reply would be
printed. `tests/fixtures/native-plugin` is a complete
reference plugin (its `native/src/main.rs` documents a contract the way a
plugin helper does).

Requirements for building (developers only): rustup with the toolchain from
`rust-toolchain.toml` (`rustup toolchain install 1.99.1 --profile minimal -c
clippy,rustfmt -t x86_64-unknown-linux-musl,aarch64-unknown-linux-musl`),
`file`, and qemu-user binfmt to run the aarch64 binary in tests.

### Two-stage jobs

A decoder that must run threads (ffmpeg converting a video) gets
`BpfFilter::threaded_decoder()` instead of `decoder()`; everything else
about the sandbox stays as it is.

| Syscall | `decoder()` | `threaded_decoder()` |
|---|---|---|
| `clone` | `EPERM` | allowed only with `CLONE_THREAD` and no `CLONE_NEW*` flag (masked compares on the low 32 bits of argument 0, the bits the kernel reads); otherwise `EPERM` |
| `clone3` | `EPERM` | `ENOSYS` (its flags are in memory, where seccomp can't look), so glibc falls back to `clone` |
| `fork`, `vfork`, `ptrace`, `mount`, `unshare`, `setns`, `bpf` | `EPERM` | `EPERM` |
| `io_uring_setup`, `io_uring_enter`, `io_uring_register`, `add_key`, `request_key`, `keyctl`, `userfaultfd` (0.6.0) | `EPERM` | `EPERM` |
| another architecture, x32 (x86_64) | killed | killed |

So the decoder can start threads but no process and no namespace. The
`decoder()` program changed only by 0.6.0's hardening row (a unit test pins
its bytes, and 0.5.2's list still gives 0.5.2's). Only x86_64
tests it live: unit tests run the test binary under the filter (a thread
starts; fork, `clone` without `CLONE_THREAD` or with `CLONE_NEWUSER`,
`unshare` and the hardening row fail; an x32 call is killed). aarch64 is
covered by the BPF interpreter tests, which check both profiles for every
syscall number on both architectures; qemu-user has no seccomp, so the
aarch64 binary fails closed there.

`Bounded` runs the stages:

- **`stdin_fd(file)`** hands a file the helper opened and checked to the
  child as fd 0, nothing copied, still seekable: `ffmpeg -fd 0 -i fd:`
  reads an MP4 whose index is at the end (`-i pipe:0` would not seek).
- **`nice(19)`** and **`io_idle()`** (`ionice -c 3`) per child; threads and
  children inherit them. `nice` only raises the niceness: a child already
  nicer keeps its own.
- **`a.pipe_into(b)`** is a `Pipeline`: `a`'s standard output into `b`'s
  standard input through the helper, moved with `splice` (no copy) and
  counted. `run_with_progress(|bytes| …)` is called after every transfer
  and at least every 100 ms; `ControlFlow::Break(())` cancels (check a
  flag your signal handler sets there). The deadline is the shorter of the
  two timeouts. A timeout, an output over a stage's `max_output`, a cancel
  or an error kills both process groups, and both children are always
  reaped. `PipelineOutput` has both `Output`s, `piped` (bytes) and
  `cancelled`; the second stage's `stdin` must stay unset.

```rust
let filter_a = BpfFilter::threaded_decoder()?.memfd()?;
let filter_b = BpfFilter::threaded_decoder()?.memfd()?;
let decode = sandbox(&filter_a)          // your Bwrap: --unshare-all, read-only /usr, --seccomp …
    .bounded(["/usr/bin/ffmpeg", "-nostdin", "-protocol_whitelist", "fd", "-fd", "0", "-i", "fd:",
              /* … */ "-f", "rawvideo", "-pix_fmt", "yuv420p", "pipe:1"])
    .env_clear()
    .stdin_fd(input)                     // the File the helper opened
    .nice(19)
    .io_idle()
    .rlimit(Resource::As, limit)
    .timeout(Duration::from_secs(600));
let encode = sandbox(&filter_b)
    .bounded(["/usr/bin/ffmpeg", "-nostdin", "-f", "rawvideo", /* … */ "-i", "pipe:0", /* … */ "pipe:1"])
    .env_clear()
    .nice(19)
    .io_idle()
    .max_output(150 << 20)
    .timeout(Duration::from_secs(600));
let output = decode.pipe_into(encode).run_with_progress(|bytes| {
    report_frames(bytes / frame_bytes);
    if cancel.load(Ordering::Relaxed) { ControlFlow::Break(()) } else { ControlFlow::Continue(()) }
})?;
```

Give each stage its own filter memfd: bubblewrap reads the program from the
fd's shared offset, so with one memfd for both a stage gets a partial or
empty program and bubblewrap refuses to start it (it fails closed).

## Preview

```bash
preview/render.py ../foamy-audio --out /tmp/audio-shots
preview/publish-screenshots.sh ../foamy-audio /tmp/audio-shots fix-omarchy-45/audio
```

`render.py` runs Quickshell offscreen (software renderer, temp HOME and XDG
dirs, no Wayland/Hyprland variables) against a host shell (only its QML is
loaded, no host script or binary is ever run): the installed Omarchy 4.5
shell, `/usr/share/omarchy/shell` (`FOAMY_HOST_45` overrides). Omarchy 4.0 is
not supported since 0.9.0: `--host 4.0` stops with a message, `--host both`
renders 4.5 into `<out>/4.5/` as it used to, `FOAMY_HOST_40` is ignored, and
`harness.available_hosts()` prints a `SKIP … on 4.0` line for a 4.0 a caller
still lists. Offscreen Qt has no
layer shell, so the host's own `Ui/KeyboardPanel.qml` is loaded with its
`PanelWindow` swapped for an item that draws into a simulated 1920x1080
screen; its geometry and motion code is the host's. The bar window spans the
screen, like the real 4.5 bar. Each run gets a
private D-Bus session (no service activation: the desktop's MPRIS players
and notifications are invisible), and `qs` dies with the render, even when
the render itself is killed; the temp dir is removed (`--keep` keeps it).

What a run's processes (qs, the plugin's `Process`es, the host QML) can
reach is isolated by default (0.9.0):

- **No host commands.** Omarchy's bin directories (`/usr/share/omarchy/bin`,
  the host's `../bin`, the caller's `$OMARCHY_PATH/bin`) leave `PATH`, and
  any other `omarchy`/`omarchy-*` still on it (`/usr/bin`, a wrapper in
  `~/.local/bin`) is shadowed by a stub that exits 127 and logs the call to
  `$FOAMY_OUT/host-commands.log` (`Run.host_commands()`). `Run(…,
  fakebin={"omarchy": script})` stand-ins come first. A test that changes
  `run.env["PATH"]` adds its own directories in front of it
  (`f"{folder}:{run.env['PATH']}"`); `Run.start()` stops with the reason
  when the stubs are gone from `PATH`, a directory holding a host
  `omarchy*` command comes before them, or an Omarchy bin directory is back.
- **No AppImage libraries.** Entries under `$APPDIR` (an editor's bundled
  libnotify) leave `LD_LIBRARY_PATH` and `PATH`.
- **No audio server.** `PULSE_SERVER` and `PIPEWIRE_REMOTE` name dead
  sockets; the lookup dirs are the private runtime dir.
- **No system bus.** `DBUS_SYSTEM_BUS_ADDRESS` is a dead address, so
  NetworkManager, logind, UPower and BlueZ are out of reach. A test that
  needs one opts in: `Run(…, system_bus="private")` starts a second private
  daemon (`Run.system_bus_address`) for its fake services, and
  `system_bus="unix:path=…"` uses a bus the test runs itself.
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
`--theme dark|light|<colors.toml>`, `--language da`, `--position`,
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

Temp dirs: each run owns one PID-tagged dir under the temp dir (`$TMPDIR`,
else `/tmp`) and removes only that one. Never `rm -rf /tmp/foamy-kit-preview-*`
— concurrent renders (other agents') live there. `python3 preview/harness.py
--gc` removes only dirs of runs whose process is gone.

Sockets: a unix socket path holds at most 107 bytes, so each run keeps its
runtime dir (`XDG_RUNTIME_DIR`, where qs binds
`quickshell/by-id/<id>/ipc.sock`) and its private buses' sockets in a second,
short dir, `Run.sockets` (`foamy-kit-s-<pid>-<random>`, 0700): in the temp
dir when that fits, else in `/tmp`. A long `$TMPDIR` (an agent sandbox's)
used to leave qs with only "Failed to start IPC server" in its log; that line
is now a failure marker, and `Run.start()` stops with the reason when a
test's `XDG_RUNTIME_DIR` is too long. Read the runtime dir from
`run.env["XDG_RUNTIME_DIR"]`, not from `run.base`.

Comparing screenshots: `preview/compare.py old.png new.png` (or two
directories). It compares RGB and alpha; never compare one without the other.

### Test helpers for plugins

Plugin runtime tests import the harness from the kit checkout (they don't
sync it), and the same goes for these helpers:

```python
KIT = Path(os.environ.get("FOAMY_KIT", Path.home() / "GitHub/Personal/foamy-kit"))
sys.path.insert(0, str(KIT / "preview"))
import harness, hostenv
```

- **`harness/FoamyWait.qml`**, in every run's QML (`import "harness"`): steps
  that wait for a condition instead of a fixed `after(ms)` chain, so they
  neither flake on a loaded machine nor waste time on an idle one.

  ```qml
  FoamyWait { id: wait }
  wait.waitFor(function() { return service.ready }, 10000, function(ok) {
    check(ok, "the service became ready")
    nextStep()
  })
  wait.waitFor(function() { return !proc.running }, 5000, nextStep, "the save ends")  // label: a timeout fails the run
  wait.after(500, nextStep)                                                            // when the step really is time
  ```

  `then(ok)` is called once and always later; a throwing condition counts as
  false; `pending` counts the waits in flight.
- **`harness.wait_for(condition, timeout, interval=0.05, stop=None)`** polls a
  Python condition and returns its value (or None after the timeout);
  **`Run.wait_for_log(text, timeout)`** waits until the running shell logs
  `text` (a `FOAMY READY` line before an IPC call).
- **`preview/hostenv.py`** for what runs outside `harness.Run`, or needs a
  private Omarchy tree:
  - `isolate(env, base)`: the harness's isolation for a process the test
    starts itself (its own `qs`, `notify-send`): no Omarchy bin dir or
    `$APPDIR` on `PATH`/`LD_LIBRARY_PATH`, dead audio and system-bus
    addresses. `library_path()`, `isolated_path()` and `host_bins()` are the
    parts.
  - `make(base, app, env=None, stubs=None, names=())`: environment overrides
    for a private `OMARCHY_PATH` (the host's `shell/` and `default/` only) whose
    `bin/` and `PATH` stubs log every `omarchy-*` call to
    `<base>/omarchy-calls.log` and succeed; `omarchy-shell` reaches the test's
    own shell (`qs ipc -n -p <app>`), never the live one. `stubs` replaces or
    adds scripts; `calls(base)` reads the log.
  - `check(env, *outputs)`: fails when a host bin dir is on `PATH` or a host
    script's path shows up in the outputs.
  - `fake_helper_plugin(plugin, dest, helper, script)`: a copy of the plugin
    whose `bin/<arch>/<helper>` is a script, so `FoamyNative` launches the
    fake.
  - `ProcessGroup(argv, **popen)`: a `qs` (or service) the test starts
    itself, as the leader of its own process group. `stop(grace=2.0)` (or
    leaving the `with` block) sends SIGTERM to the whole group, SIGKILL to
    what is left, and reaps the leader, so the scripts its `Process`es
    started go too; `Popen.terminate()` stopped qs alone and left their
    children running. `wait(timeout)` returns the exit status, or None while
    it runs; wait through it, not `.process.wait()`, so the group id stays
    reserved until `stop()`. A child that makes its own session or group
    (`setsid`, coreutils `timeout`) is outside it.

    ```python
    with hostenv.ProcessGroup(["qs", "-p", str(app), "--no-color"], env=env, stdout=log) as shell:
        shell.wait(60)
    ```

  It replaces the plugin copies (`tests/hostenv.py` in foamy-notifications and
  foamy-notification-center, the `isolate()`s in foamy-audio and foamy-bolt,
  foamy-github's `fake_plugin()`); `tests/test_helpers.py` covers it.
- **`preview/i18n_runtime.py <plugin>`**: the plugin's catalogs through the
  kit's `FoamyI18n` in an isolated shell, switching the language file live
  (the first non-English catalog, Norwegian when there is one, then Arabic,
  then English). Expectations come from the catalogs: a translated string and
  its English fallback, a plural entry's `one` form in the language's digits,
  right-to-left only under Arabic, English-only and unknown strings, values
  substituted once. It replaces the per-plugin `tests/i18n-runtime.py`
  variants; plugin UI under a language switch (foamy-notifications' cards)
  stays in the plugin's own test. `tests/test_i18n_runtime.py` covers it.

### Before / after trio

```bash
preview/render.py ../foamy-power --trio --url-prefix https://raw.githubusercontent.com/foamrider/foamy-power/pr-assets/fix-omarchy-45/power
```

Renders each view: `<view>-before.png` (the `origin/dev` tree,
`--dev-ref`) and `<view>-after-4.5.png` (the working tree), and writes
`trio.md`, a PR-body table. Before comes from `git archive`
(the plugin repo is not touched), with layer-shell windows (pre-kit popup
forks, overlay windows) swapped for the offscreen stand-in — only the windows
and their own `anchors { }` blocks are rewritten — and bare `Color.` qualified
(Qt 6.12 shadows it), so dev looks as it did. Describe the dev UI in
`preview/Before.qml` in the current tree (or `--before-preview FILE`); else dev's
own `preview/Preview.qml` is used. When dev's popup fork is clipped on 4.5
(the 120 px card the kit fixed) or dev doesn't render, the column header says
so. Card images only;
`--states` limits the views.

`publish-screenshots.sh` commits PNGs to the plugin's orphan `pr-assets`
branch through a temporary worktree (the working tree is untouched), prints
`raw.githubusercontent.com` URLs and the `git push` command. It never pushes.

## Compatibility

Plugins and the kit target Omarchy 4.5, the installed shell, and nothing
else: 0.9.0 removed the 4.0 code paths, the `--host 4.0` harness option and
`FOAMY_HOST_40`. The stock KeyboardPanel and PopupCard bring the host's own
behaviour; `FoamyI18n` uses the shell's `Translations`, `FoamyMotion` its
`Style.duration`, and `FoamyIpc` registers with its `IpcRegistry`.

## Tests

```bash
tests/run-all.sh             # every test
tests/validate.sh            # the linters and formatters, then tests/suite.sh (run-all.sh)
tests/validate.sh --ci       # what CI runs: tests/suite.sh --ci is the node, sync/check,
                             # validate and image-compare tests
```

`test_validate.py` runs a synced plugin's own `tests/validate.sh`: QML-loaded
JavaScript linted through its directives, baselines (line shifts, grown
complexity, fixed entries), kit-owned files left alone, reasons required, a
missing pinned tool, the suite hook and `--ci`. It needs `mise install`.

Host-based tests run on 4.5 (`/usr/share/omarchy/shell`, or `FOAMY_HOST_45`).

Runs FoamyPrefs, FoamyText, FoamySchedule and FoamyI18nText unit tests (node, through `kit/node-loader.cjs`), sync/check/lint
on throwaway copies, the FoamyPopup geometry test (4 bar positions, max
height, menu padding, plus the old fork as a negative control), runtime
tests of i18n/motion/palette/prefs/cursor/leader election/IPC
(English, Danish, Arabic), the 0.2 features (icons, tokens, dropdown binding,
prefs queue inline and CLI with fake `omarchy`, IPC preference and peer
calls, settings state, private D-Bus), how a prefs-queue CLI save ends
(`test_lifecycle.py`: exit, failed start, deadline, capped stderr, stopped,
queue destroyed, an array save's stuck child killed with it so it never
writes late; and a peer call that can't start), a `qs ipc` argument probe, harness
leak tests, the demo, menu-card and service previews, and (0.4.0,
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
pins, tampered, dynamic, wrong-arch and stale binaries, `THIRD_PARTY_NOTICES.md`
(linked crates only, checksums, shipped texts, an ISC crate's copyright line,
standard texts for a crate without one, a stale, edited or missing file), the helper's contract
on x86_64 and on aarch64 through qemu, and `FoamyNative.command` from node and
from Quickshell's `Process`).

## Versioning

See [CHANGELOG.md](CHANGELOG.md).


`VERSION` is the kit version stamped into every copy. Bump it for any change
under `kit/`, `tools/kit-check.sh.in`, `REVIEW.md`, the tooling files or the
`AGENTS.md` review block, then sync every plugin so `check.sh`
sees one version everywhere.

## License

MIT (`LICENSE`). `FoamyIcon` paths are Lucide (ISC, `LICENSE-LUCIDE`),
except the Zendesk brand mark from Simple Icons (CC0, source in `FoamyIcon.qml`);
`FoamyDropdown` is adapted from Omarchy (MIT, `LICENSE-OMARCHY`); both notices
are copied into a plugin's `kit/` with the component.
