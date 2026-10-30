# Changelog

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
