# Changelog

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
