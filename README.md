# foamy-kit

The canonical source of the components every foamy Omarchy shell plugin shares
(`foamy-audio`, `foamy-bolt`, … `foamy-weather`), plus the tools that keep
them identical: `sync.sh`, `check.sh`, a design lint, and an offscreen preview
harness for screenshots. The look and the rules live in [DESIGN.md](DESIGN.md).

Plugins can't share files at runtime (each is a self-contained directory and
`omarchy-plugin-validate` rejects symlinks), so the kit is **copied** into
each plugin as stamped regular files under `kit/`. A stamped copy is never
edited in a plugin: change it here, then sync.

## Components (`kit/`)

| Component | Files | What |
|---|---|---|
| FoamyStyle | `FoamyStyle.qml` (singleton) | Radius, border, font family and type scale, widths, spacing, control sizes |
| FoamyPalette | `FoamyPalette.qml` (singleton) | Surface tones and theme status colours from colors.toml |
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
| FoamyNumberField | `FoamyNumberField.qml`, `FoamyTextSettingField.qml` | Binding-safe numeric and text settings fields: draft, Enter/focus-out commit, Escape restore, step, validation |
| FoamySettings | `FoamySettingsPage/Header/Section/Error/State.qml`, `FoamyToggle.qml` | Settings page skeleton (wheel scrolling, `ensureVisible`, section `info`) and open/close state |
| FoamyCursor | `FoamyCursor.qml`, `FoamyCursorSurface.qml` | Single keyboard/pointer cursor model and row surface |
| FoamyPrefs | `FoamyPrefs.js`, `FoamyPrefsQueue.qml`, `node-loader.cjs` | Schema (incl. array/object), queued saving (inline, else the CLI), node loader for unit tests |

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

## Versioning

See [CHANGELOG.md](CHANGELOG.md).


`VERSION` is the kit version stamped into every copy. Bump it for any change
under `kit/` or `tools/kit-check.sh.in`, then sync every plugin so `check.sh`
sees one version everywhere.

## License

MIT (`LICENSE`). `FoamyIcon` paths are Lucide (ISC, `LICENSE-LUCIDE`);
`FoamyDropdown` is adapted from Omarchy (MIT, `LICENSE-OMARCHY`); both notices
are copied into a plugin's `kit/` with the component.
