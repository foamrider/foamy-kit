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
| FoamyIpc | `FoamyIpc.qml`, `FoamyIpcResolver.js` | IpcHandler that also registers with 4.5's IpcRegistry (omarchy-shell socket) |
| FoamyShared | `FoamyShared.qml` (singleton), `FoamyMember.qml` | One leader per shell across per-monitor bar instances, open-popup demand |
| FoamyHeader | `FoamyHeader.qml` | Icon, title, meta, trailing actions, settings button |
| FoamyAction | `FoamyAction.qml` | Icon/label action button, settings button, spinner |
| FoamyIcon | `FoamyIcon.qml` | Lucide superset (ISC, `LICENSE-LUCIDE`) |
| FoamyDropdown | `FoamyDropdown.qml` | Stock Dropdown, foamy styled, value-on-select + RTL (`LICENSE-OMARCHY`) |
| SafeTextField | `SafeTextField.qml`, `clipboard.sh` | Text field with bounded, out-of-process paste |
| FoamySettings | `FoamySettingsPage/Header/Section/Error.qml`, `FoamyToggle.qml` | Settings page skeleton |
| FoamyCursor | `FoamyCursor.qml`, `FoamyCursorSurface.qml` | Single keyboard/pointer cursor model and row surface |
| FoamyPrefs | `FoamyPrefs.js` | Schema validation and settings saving (inline, else `omarchy bar set`) |

Each file's header documents its API. Dependencies are in `kit/components.json`.

## Sync

```bash
./sync.sh ../foamy-audio                                   # first time: every component
./sync.sh ../foamy-audio --components FoamyPopup,FoamyI18n # or a subset (+ dependencies)
./sync.sh ../foamy-*                                       # later: refresh, keeping each plugin's set
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
bar window, 4.0 runs a strip window, like the real bars.

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
`--rounding`.

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

Runs FoamyPrefs unit tests (node), sync/check/lint on throwaway copies, the
FoamyPopup geometry test (4 bar positions, both hosts, plus the old fork as a
negative control), runtime tests of i18n/motion/palette/prefs/cursor/leader
election/IPC on both hosts (English, Danish, Arabic), and the demo preview.
`tests/fixtures/demo-plugin` is a reference plugin built only from the kit.

## Versioning

`VERSION` is the kit version stamped into every copy. Bump it for any change
under `kit/` or `tools/kit-check.sh.in`, then sync every plugin so `check.sh`
sees one version everywhere.

## License

MIT (`LICENSE`). `FoamyIcon` paths are Lucide (ISC, `LICENSE-LUCIDE`);
`FoamyDropdown` is adapted from Omarchy (MIT, `LICENSE-OMARCHY`); both notices
are copied into a plugin's `kit/` with the component.
