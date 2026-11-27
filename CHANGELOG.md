# Changelog

## 0.16.0 — 2026-11-27

From the foamy-todoist UI review. New optional interfaces; with them off
nothing changes: the demo plugin's preview states render the same as with
0.15.1, pixel for pixel, dark and light. No plugin must change.

### Added
- The compact band's title as a control, for a sub-view whose title is
  something the user changes (foamy-todoist's editor page: the task's
  place opens the move menu, and the Project row it repeated goes).
  `FoamySettingsHeader.titleAction` (off by default), `titleIconName`,
  `titleIconColor`, `titleAccessibleName` (default: the title),
  `titleButton`, `titleMenuAnchor` and `titleActivated(keyboard)`;
  `FoamyHeroBand` passes them as `compactTitleAction`,
  `compactTitleIconName`, `compactTitleIconColor`,
  `compactTitleAccessibleName`, `compactTitleButton`,
  `compactTitleMenuAnchor` and `compactTitleActivated(keyboard)`. On, the
  title shows a leading mark, the title and a chevron on a hover fill,
  with the keys' accent ring; it is the next Tab stop after Back; a click
  emits `false`, Enter or Space `true` (for `FoamyMenu.open(keyboard)`); it
  is a Button for assistive technology. A title too long for the room
  ends with "…" ("Saving…" and the trailing actions stay) and shows whole
  in a tooltip on hover, wrapped, at most the header's width.
  `titleMenuAnchor` is a menu's width at the control's start, so a
  FoamyMenu anchored to it hangs under the control from its start (the
  trailing edge in RTL). DESIGN.md: Hero band.
  `tests/test_settings_header.py` (new; LTR and RTL, scale 1.0 and 1.25):
  off, no control and Tab from Back to the trailing action, and the band
  with the other title properties set draws the same pixels; on, the
  mark, title and chevron, click/Return/Enter/Space and the accessible
  press with their `keyboard` argument, the Tab order, ring and fill, role
  and name, the menu's place, Esc giving the keys back, elide and the
  tooltip. Seen failing with Space not handled, no ring, the title as the
  accessible name, no chevron and a click reported as keys (7 checks);
  with the control shown and on the Tab path while off (3 checks and 110
  pixels); with the anchor as wide as the control (the menu's place); and
  with the off title taking the icon colour (592 pixels).
- `FoamySettingsPage.columnWidth` (default: the page's width less its
  side paddings) and `columnInset`, for a page wider than the settings
  width (foamy-todoist's Wide page, 880 with a settings-wide column): Back
  and the title start at the column's edge, the error line with Retry and
  the sections keep to the column, centred; the band's surface still runs
  to the card's edges. `FoamyHeroBand.compactPadding` (default
  `FoamyStyle.padding`) is the compact row's side padding the page sets.
  A page of the settings width is unchanged (the demo's settings and
  settings-error states, and foamy-todoist's Small settings, pixel for
  pixel). DESIGN.md: Settings page. `tests/test_settings_header.py`: on
  an 880 page with a 400 column, the band to the edges, Back and the error
  at the column's start, the title and Retry inside its end, the section
  filling it; a 420 page at the padding; a column wider than the page
  keeps the padding. Seen failing with the page's paddings back at
  `FoamyStyle.padding` (5 checks: Back at 20 instead of 240, the error and
  Retry across the card, the section 840 wide).

## 0.15.1 — 2026-11-26

### Fixed
- Dark themes: `FoamyPalette.onSurface(c, surface)` returned the colour
  unchanged (since 0.1.0, where it came in light-only), so a destructive
  `FoamyButton` label on its strongest (pressed) tint drew 4.30:1 in the preview's dark theme, under the 4.5:1
  the kit promises for text. In a dark theme it now lightens
  (`Qt.lighter`) in the steps the light path darkens in, only until it
  reads at 4.5:1 on `surface` as drawn, at most 1.7 times; the hue stays
  (preview dark #f38ba8 -> #ff92b0, 4.73:1; Nord #bf616a, 3.05:1 on its
  background -> #ef7984, 4.60:1, and 2.32:1 on the pressed tint ->
  #ff97a1, 4.61:1). Light themes are unchanged. Plugins' dark looks change at their
  next sync only where a status colour did not read: the destructive
  label, a destructive menu row under the cursor, the urgent tab count and
  error or status text in themes with a dim red or yellow (Nord, Kanagawa,
  Miasma, Solitude and others). `tests/test_tabs.py` (the destructive
  label check now runs in the dark cases, which failed at 4.30:1 before;
  a status colour that already reads comes back unchanged; seen failing
  when the loop always takes one step), `tests/test_runtime.py` (a live
  switch to Nord: the red reaches 4.5:1 and changes; seen failing at
  3.05:1 with the dark branch removed). DESIGN.md: Tokens.
- Status text that still drew the raw red: `FoamySettingsError` (since
  0.1.0), the `FoamyPanelFooter` status error (since 0.4.0) and the icon of
  a destructive `FoamyAction` under the pointer or cursor (since 0.1.0).
  In a dark theme with a dim red they stayed far under 4.5:1 (Nord 3.05:1
  on the background, 2.67:1 on the action's tint), and a settings page
  showed two reds: the raw one in `FoamySettingsError` beside the readable
  one under a field. They now use `onSurface` (the action on its red tint,
  as `FoamyButton` and `FoamyMenu` do), and `FoamySettingsError` and the
  footer take the theme's red (`FoamyPalette.error`), as the field errors
  do. The urgent `FoamyTabs` count (since 0.12.0) was measured on the
  background but drawn on the cursor's fill under the cursor or pointer
  (Nord 3.72:1, the preview's light red 4.27:1): it is now measured on
  that fill, its strongest surface, so it keeps one colour in both states.
  A colour that already reads there is unchanged: the preview's dark theme
  renders the same, pixel for pixel. Light: the urgent count (#d20f39 ->
  #c80e36, 4.62:1 on the cursor's fill) and the destructive action's icon
  (3.79:1 -> #b70d32, 4.71:1) darken a little. Nord: the settings and
  footer errors #bf616a -> #ef7984 (4.60:1), the action icon -> #ff8490
  (4.65:1), the urgent count -> #ff8e99 (4.60:1 on the cursor's fill).
  `tests/test_components.py` (now also in the light theme and a dark
  theme with a dim red, `tests/fixtures/themes/dim-red.toml`: the pressed
  destructive label on the real button's fill, the action's icon under
  the pointer and the cursor, the footer status error, the settings error
  matching the field error; each seen failing with the raw colour) and
  `tests/test_tabs.py` (the count on the hovered tab, also with the dim
  red; seen failing at 4.27:1 light and 3.93:1 dim red). Plugins see the
  change at their next sync, only in themes whose red did not read there.
  Known limit: a destructive `FoamyAction` is measured with the popup
  surface under its tint; in a hero band or on a selected row the fill
  under it differs and the icon can stay under 4.5:1 (still more than the
  raw red gave). Plugin change: a plugin's own error line should use
  `FoamyPalette.onSurface(FoamyPalette.error)` instead of
  `Commons.Color.urgent` (DESIGN.md: Empty / loading / error), or it shows
  a second red beside the kit's.

## 0.15.0 — 2026-11-26

From the foamy-todoist UI review. Every plugin's look changes at its next
sync (selected rows, tab counts, light themes): render each plugin's
preview in dark and light and look at it.

### Fixed
- `FoamyPalette.onAccent` (since 0.1.0) is now `accentInk`. QML reads a
  property named `on` + a capital letter as a signal handler, so it never
  had a colour, and every primary `FoamyButton` label was black (#000000)
  on the accent. `accentInk` is the popup's text or background, whichever
  has more contrast on the accent (measured, so a mid-tone accent such as
  Ethereal's or Solitude's gets the readable one). Plugin change: foamy-lock (studio/StudioButton.qml) reads
  `FoamyPalette.onAccent`; it must read `accentInk` at its next sync.
  `tests/test_components.py`.
- `FoamyMenu` (since 0.4.0) anchored inside a row's `FoamyCursorSurface`
  (or any other bordered surface) took that surface for the card and drew
  nothing usable: the host is now the first bordered surface above the
  popup's body (the item with `foamyMenuReserve`). Outside a FoamyPopup or
  FoamyPopupCard it is found as before. Plugin change: a `host` set by hand
  only for this can go. `tests/test_menu.py`.
- `FoamyMenu.open(true)` (from the keys), and a submenu, start on the
  checked entry when exactly one is checked (the current choice), else on
  the first. Before, they always started on the first, so Enter twice on a
  property (a priority, a project) picked the first option. With several
  checked (toggles, labels) Enter would turn one off, so those start on
  the first as before. `tests/test_menu.py`.

### Changed
- `FoamyMenu` grows its card only when the shown level (laid out first)
  fits neither below nor above its button and growing helps, and by at
  most `maxGrowHeight` of menu (9 rows, a new property); past it the menu
  scrolls. A submenu, the way back, or a card still shrinking from an
  earlier open decides again; once grown, the card keeps the largest size
  it took while the menu is open (a shorter submenu doesn't shrink it), and
  the entry the keys are on stays in view as the card grows. Before, every menu reserved room
  below its button, so a long one (labels, projects) grew the card up to
  the whole screen, also where it fit above. `tests/test_menu.py`.
- The selected look (`FoamyCursorSurface.current`) is
  `FoamyPalette.selectedFill` (the accent, faint) instead of the host's
  grey, also under the cursor. New: `byKeys` draws the keys' cursor with
  a 1 px accent border, and `currentBar` adds a 3 px accent bar at the
  reading start of a selected row whose details show in a pane.
  `FoamyCursor.byKeys` (true after `move()`, false after `hover()`; set it
  when a key handler sets `index` itself), `FoamyAction.cursorByKeys` and
  `FoamyTabs.cursorByKeys` carry it; the buttons inside FoamyHeader,
  FoamyHeroBand, FoamyPanelFooter and FoamyInfoNote keep the plain look.
  Plugin change, to show the keys' border: bind `byKeys`/`cursorByKeys` to
  `cursor.byKeys`, and set `cursor.byKeys = true` where a key handler
  moves the cursor without `move()` (FoamyTabs.moveCursor, a stop set by
  index). Without it the pointer's look stays, as before. DESIGN.md:
  Keyboard. `tests/test_tabs.py`, `tests/test_components.py`.
- Light themes: `onSurface()` darkens a status colour only until it reads
  at 4.5:1 on the popup background (`contrastRatio()`, from 0.14.2),
  measured as drawn (8 bits a channel), at most 1.7 times darker; it was a
  fixed `Qt.darker(c, 1.35)`, which made a red that already read darker
  than the body text. It also takes a colour given as text, and an
  optional `surface` for a colour drawn on a tinted fill: the destructive
  `FoamyButton` label (on its strongest tint) and a destructive menu row
  under the cursor use it. Menus in a light theme: `menuFill` lighter than
  the card and a new `menuBorder` (text .40; dark: `border`), which
  `FoamyMenu` uses (a visual change, checked in the light preview renders;
  no test measures it). DESIGN.md: Tokens. `tests/test_tabs.py` (light
  runs), `tests/test_runtime.py`.
- `FoamyTabs` counts are `bodySmall` and, on a closed tab, `secondaryText`
  (were `caption` and `mutedText`, the faintest text in the row).
  DESIGN.md: Tab row. `tests/test_tabs.py`.

### Added
- `FoamyIcon`: `tag` (Lucide).

## 0.14.2 — 2026-11-26

### Added
- FoamyIcon: `mail` and `mail-open` (Lucide 1.65.0, lucide-static), 124
  names, for foamy-zendesk. No other icon changed.
- `FoamyPalette.contrastRatio(a, b)`, the WCAG 2 contrast ratio of two
  opaque colours, and `FoamyPalette.readableTint(alpha, ratio, limit)`,
  the lightest tint of `text` over `background` from `alpha` up to `limit`
  (steps of .01) with at least `ratio` contrast on `background`.

### Changed
- `FoamyPalette.mutedText` (hints, empty states) reaches 4.5:1 (WCAG AA
  for small text) on the popup surface in light themes. Before, tint .55
  gave 2.47:1 in Rosé Pine, 2.53:1 in Catppuccin Latte, 3.65:1 in Lupine
  and 4.20:1 in Flexoki Light. Now a light theme uses the lightest tint
  from .55 up that reaches 4.5:1: .55 in White (4.76:1), .58 in Flexoki
  Light, .62 in Lupine, .82 in Catppuccin Latte and .84 in Rosé Pine.
  Dark themes keep tint .55.
- `FoamyPalette.secondaryText` (meta, section labels) reaches 5.5:1 in
  light themes, so it stays darker than the muted tone: tint .72 gave
  3.62:1 in Catppuccin Latte and 3.49:1 in Rosé Pine, which now use .90
  and .93. White, Flexoki Light and Lupine keep .72 (9.23, 7.67 and
  6.24:1). Dark themes keep .72. Both stop at a ceiling (muted .84,
  secondary .95 of the way to the text), so a light theme with weak text
  keeps three tones and a field's placeholder stays below .85; such a
  theme stays under the ratios. Muted text on `fieldFill`,
  `hoverFill` or `noteFill` stays below 4.5:1 (3.87:1 to 4.31:1 in the
  light themes). DESIGN.md: Tokens, Text tones. Plugin change: none
  needed; plugins get it with their next sync. `tests/test_runtime.py`.

### Upgrading
- The sync changes `FoamyIcon.qml` and `FoamyPalette.qml`.
  `kit/i18n-texts.json` did not change. No plugin needs a code change.

## 0.14.1 — 2026-11-26

### Fixed
- `FoamyDropdown.select()` (since 0.1.0): a pick of the value in use ends
  the hold of an older pick, so the last pick shows. Before, only a pick
  of another value was held, so with `value` "c" the picks "a" and then
  "c" kept "a" on show (`shownValue` "a", `pickHeld` true) until `value`
  changed, "a" was refused or `pickHoldMs` (10 s) passed; in foamy-monitor,
  with GTK scale 2 in use, the picks 3 and then 2 showed 3 until the
  request for 3 ended. Code that picks with `select()` met it; a pick from
  the list did not, as opening the list ends a hold. The pick of the value
  in use still emits `changed()` with a serial of its own, and a refusal
  of the older pick after it (`saveFailed(serial)`) changes nothing.
  Plugin change: none needed. `tests/test_features.py`.
- `FoamyDropdown`'s queue link (`queue`, `queueKey`, since 0.14.0) ends
  a pick whose save is refused as it runs also when `onChanged` saves
  another value than the option. Before, after `changed()` the link ended
  the pick only when `failed()` named the option's value, so foamy-teams'
  "When all accounts are closed" pick "hide", saved as
  `hideWhenClosed: true`, stayed on show for 10 s beside the error when
  it waited behind a running CLI save and the widget lost its bar entry
  meanwhile. Now a refusal or failure of the key ends the held pick,
  whatever value it names, when the queue runs no other save and keeps no
  save of the key waiting. So a failed older save of the key leaves a
  newer pick whose save still waits, even one of the same value (a
  dropdown bound to the stored settings lost it before), and such a
  dropdown gives way when its own CLI save fails, mapped value or not, as
  the failure rolls back nothing it shows. Another object linked as the
  queue, with only a `failed(key, value, error)` signal, has no such
  state: there the failure must name the option's value, as before, so an
  older pick's failure leaves a newer pick on show. FoamyScheduleDay's
  link is unchanged and matches a later refusal by the range it sent; its
  header and README.md said it works "as FoamyDropdown does" and now say
  that. Plugin change: none needed; foamy-teams' dropdown works as it is.
  DESIGN.md: Choices. `tests/test_features.py`.
- `FoamyTextSettingField` and `FoamyNumberField` (`saveFailed()`, since
  0.3.4) show the saved value again when `saveFailed()` is called inside
  their own `committed()`, and the same input can be sent again. Before,
  a commit emitted `committed()` before the field settled its draft, and
  `saveFailed()` shows `value` only in a settled field, so a save that
  FoamyPrefsQueue refuses at once (a widget with no bar entry, a value the
  schema refuses, a kept invalid stored list), whose `failed()` comes
  inside the caller's `onCommitted`, left the refused text on show beside
  the error. Now the field settles first (no draft, its text the committed
  value) and then emits `committed()` with the same value, so the wiring
  DESIGN.md gives (the queue's `failed()` calls the field's
  `saveFailed()`) works as written; inside `committed()` the field is no
  longer `editing`. Plugin change: none needed; foamy-todoist
  (TodoSettings.qml, the Open command) and foamy-lock
  (studio/ScenePage.qml, the colour field) can drop their
  `Qt.callLater(… .saveFailed)` at their next sync.
  `tests/test_features.py`.
- `FoamySettingsPage.focusBack()` (since 0.1.0) gives a hidden page no
  keys. foamy-github, foamy-syncthing, foamy-todoist,
  foamy-train, foamy-vitals and foamy-zendesk call
  `Qt.callLater(settingsPage.focusBack)` when Settings shows. Qt delivers
  queued input events before deferred calls, so when Settings showed and
  hid again in one event-loop turn (two quick inputs while the shell was
  busy, or a settings IPC call and then a close), the call ran on the
  hidden page and gave the keys to its hidden Back button: Esc went to
  the hidden page and did nothing, also after the popup closed and
  opened again. FoamyPopup gives the keys back only when the item that
  has them hides, so it could not see this; the plugins' own refocus,
  which they dropped at the 0.14.0 sync, used to cover it. Now a call
  while the page does not show tries once more after the current
  event-loop turn and gives the keys only if the page shows then: a call
  that runs after Settings hid again leaves the keys where they are, and
  one made at once before the page's `visible` follows the settings state
  (a handler of `editing` that runs first) still gives the page the keys.
  Plugins may rely on this: call `focusBack()` at once or deferred, when
  or after Settings shows; a call after Settings hid does nothing. Every
  plugin's call on its dev branch already runs deferred after Settings
  shows (foamy-audio, foamy-bolt, foamy-clock, foamy-github, foamy-media,
  foamy-notification-center, foamy-power, foamy-syncthing, foamy-teams,
  foamy-todoist, foamy-train, foamy-vitals, foamy-weather, foamy-zendesk)
  or from the page's own account editor (foamy-teams' `leaveEditor()`,
  which after a save that ends with the popup closed now leaves the keys
  alone). Plugin change: none needed. `tests/test_popup_keys.py`.
- The 0.14.0 notes below and the docs said three things that are not so
  for every plugin; the 0.14.0 text is corrected (0.14.0 was not merged
  to main or tagged). (1) The pick serial entry said a handler
  that takes only `value` needs no change, which is true, but code that
  emits `FoamyDropdown.changed()` itself with one argument throws
  "Insufficient arguments" since 0.14.0 (foamy-lock's studio test, the
  runtime tests of foamy-teams and foamy-lock); 0.14.0's Upgrading now
  says to pick with `select()` instead. (2) The queue link entry said
  foamy-power, foamy-monitor and foamy-notification-center adopt the
  link, but none of them saves a dropdown through FoamyPrefsQueue
  (foamy-power saves through its helper, with a failure signal of its
  own; foamy-notification-center through its own queue; foamy-monitor
  through its own requests). They are now named under the pick serial
  entry, as their own failure paths compare picks, and the link entry
  names the eleven plugins that link a dropdown. (3) FoamyPopup's key
  return (0.14.0) learns the item with the keys from the window's
  `activeFocusItem`, which Qt keeps only in the active window; a test
  that runs the popup in a window that is not active, or in none, sees no
  key return (foamy-bolt, foamy-vitals and foamy-github had to activate
  the window, or put the popup in one, before dropping their refocus).
  README.md (Components), the FoamyPopup header and 0.14.0's Upgrading
  now say so. No kit code changed. Plugin change: none needed. No test:
  only documentation changed.
- `preview/render.py` (`PreviewShell.qml.in`, since 0.1.0) writes every
  card picture (`<state>.png`) with its alpha channel, the corners outside
  a rounded card transparent. Before, a card that held a fully opaque
  rectangle without radius (FoamyTabs' open-tab underline) or an opaque
  image came out RGB with black corners: under the software renderer
  `grabToImage()` leaves out its transparent fill as soon as one node is
  opaque, as Qt tests the opaque area with `QRegion::contains()`, which
  means "overlaps". The card is now captured through a
  ShaderEffectSource whose layer keeps an alpha channel, sized to the
  direct grab's whole device pixels, so a display scale where the card
  covers part of a pixel (`--scale 1.25`, 382 px high) resamples nothing.
  Every pixel the card fully covers is the one the old capture gave, its
  rounded edge fades out instead of into black, and a picture that had
  transparent corners before is the same to the pixel (foamy-syncthing
  and foamy-todoist, dark and light, compared state by state;
  foamy-syncthing also at scale 1.25). A FoamyPopupCard's copy on the
  screen picture has the screen in its corners. A capture that
  `grabToImage()` refuses (a card under a pixel wide) fails the render at
  once with "FOAMY FAIL the card capture did not start", where the old
  grab waited out the render's timeout. Plugin change: none
  needed; foamy-media, foamy-syncthing and foamy-todoist, whose committed
  `preview.png` has black corners, may render it again. README.md:
  Preview. `tests/test_preview.py`.
- `foamy-helper`'s tests (`kit/rust/foamy-helper`) run the scripts that
  need bash with bash. Five ran with `/bin/sh` and bash syntax or wording,
  which dash, `/bin/sh` on Debian and Ubuntu, does not take. Four redirect
  from a descriptor above 9 (`cat <&12`), which dash refuses with "Bad fd
  number":
  `child::tests::inherited_fds_reach_the_child_under_their_number` and,
  through the fake bubblewrap,
  `sandbox::tests::a_seccomp_memfd_serves_more_than_one_run`,
  `bwrap_names_each_temporary_fd_by_its_own_duplicate` and
  `bwrap_keeps_its_own_copy_of_the_fds_it_names`.
  `bwrap_runs_with_the_seccomp_filter_and_inherited_fds` reads bash's
  message for a fork that fails, which dash words otherwise. foamy-kit's
  "foamy-helper crate" job (new in 0.14.0) on ubuntu-24.04 failed the
  first three (116 passed, 3 failed): the descriptor numbers decide, and
  the job skips the bubblewrap test. They now run `/bin/bash -c`,
  `#!/bin/bash` scripts and `/usr/bin/bash` in the sandbox; only test code
  changed, and the crate builds the same helper. Plugin change: a plugin
  with a native helper rebuilds it (see Upgrading).
  `kit/rust/foamy-helper/src/child.rs` and
  `kit/rust/foamy-helper/src/sandbox/tests.rs`.

### Upgrading
- The sync changes `FoamyDropdown.qml`, `FoamyNumberField.qml`,
  `FoamyTextSettingField.qml`, `FoamySettingsPage.qml` and, in comments
  only, `FoamyPopup.qml` and `FoamyScheduleDay.qml`. `kit/i18n-texts.json`
  did not change: `check.sh` asks the catalogs for no new text.
- `kit/rust` changed in its tests only, but `native.pin` hashes the whole
  vendored `kit/rust`: foamy-audio, foamy-github, foamy-lock, foamy-media,
  foamy-monitor, foamy-notification-center, foamy-notifications,
  foamy-power, foamy-syncthing, foamy-todoist, foamy-train, foamy-vitals,
  foamy-weather and foamy-zendesk rebuild their helper after the sync
  (`kit/native/build-native.sh .`) and commit the new binaries and
  `native.pin`; until then `check.sh`, `tests/kit-check.sh` and `--verify`
  report the binaries stale. `foamy-helper`'s version stays 0.1.2.
- No plugin needs a code change. foamy-todoist (TodoSettings.qml) and
  foamy-lock (studio/ScenePage.qml) can call `saveFailed()` at once
  instead of through `Qt.callLater`. A plugin test that reads a settings
  field's `editing` or text inside its own `onCommitted` sees the field
  settled now.
- A plugin still on 0.13.1 reads 0.14.0's Upgrading too: it now says
  that code emitting `FoamyDropdown.changed()` itself picks with
  `select()`, and that a test runs FoamyPopup in an active window.
- foamy-media, foamy-syncthing and foamy-todoist may render their
  `preview.png` again with `preview/render.py` for rounded corners.
  foamy-menu's black-cornered `preview.png` comes from its own
  `tests/launcher.py --shots`, which this does not change.

## 0.14.0 — 2026-11-22

### Added
- `foamy_helper::json::run_bytes(main, render)`: `json::run` for a
  one-shot helper that encodes its reply line itself (foamy-vitals' sample
  line). `main` returns the finished bytes, which go to standard output
  under `run`'s reply lock and panic hook: a panic in another thread waits
  until the whole line is out, a later one prints no second reply, one
  before it prints `render` of an `INTERNAL` failure, and the process ends
  in 101 for a panic. An `Err` from `main` prints `render(&failure)` with
  its exit code, as `run` does. Every existing function keeps its meaning.
  Plugin change: foamy-vitals passes its sample line to `run_bytes` and
  drops its own panic hook. README.md: The shared crate, Panics and
  arguments. `kit/rust/foamy-helper/src/json.rs` (tests
  `run_bytes_prints_the_line_or_one_reply`,
  `a_panic_while_run_bytes_writes_its_line_waits_for_it`).
- `.github/workflows/foamy-helper.yml`, foamy-kit's own CI job for the
  shared crate: `cargo fmt --check`, Clippy with warnings as errors for
  each feature set and `cargo test --all-features` of
  `kit/rust/foamy-helper`, with the toolchain `kit/rust/rust-toolchain.toml`
  pins and read-only contents permission. Before, the crate's tests ran
  only locally (`tests/test_native.py`). Sync never copies this file:
  `checks.yml` is the workflow plugins get, so the job is not in it. No
  plugin change. README.md: Tooling. `tests/test_sync_check.py` now checks
  this workflow too (actions pinned by commit, read-only by default) and
  fails any write permission outside verify-native.yml's attest job.
- `kit/i18n-texts.json`: one list of the English texts kit components hand
  a plugin to translate, each with the component that hands it out and
  where it shows up: FoamyClipboard's three paste failures (also
  `SafeTextField.pasteError` and `SafeTextArea.pasteError`), FoamyNative's
  `UNAVAILABLE_TEXT`, and FoamyPrefs' four save errors
  (`FoamyPrefsQueue.error`). Sync copies it into every plugin as it is
  (hashed whole, like `REVIEW.md`), so a plugin's catalog test reads it
  instead of keeping its own copy of the texts. `check.sh` (and so the
  `design-lint` check of `tests/validate.sh`) now fails a plugin whose
  catalog (`i18n/*.json`) lacks a text of a component the plugin carries,
  or has it empty, naming the catalog, the text and the component
  (`i18n/no.json lacks "…", which FoamyClipboard hands the plugin to
  translate (kit/i18n-texts.json)`). A plural entry counts as empty
  without a non-empty `other` form, the form `FoamyI18n.t()` shows, and
  the message then adds `(a plural entry needs a non-empty "other")`.
  `--lint-only` skips the check, and a plugin without catalogs needs none.
  The kit's own labels (Settings, Back, Retry…) and the context-menu
  labels a field passes to `translate` are not in the list. Plugin change:
  add the missing texts to every catalog (see Upgrading); foamy-zendesk
  (`tests/i18n.test.cjs`), foamy-teams and foamy-github
  (`tests/runtime-panel.py`) can read the list instead of their copies.
  README.md: Sync, Check; DESIGN.md: Copy. `tests/test_sync_check.py`;
  the list is tied to the kit's texts in `tests/i18n.test.cjs`,
  `tests/qml/Clipboard.qml` and `tests/qml/Lifecycle.qml`.
- `FoamyBoundedCollector` (new component, `kit/FoamyBoundedCollector.qml`):
  a Process's stdout or stderr with a memory bound, in place of
  StdioCollector, which keeps the whole stream however much the child
  prints. It keeps the start of the stream, at most `limit` characters
  (default 65536), drops the rest as it arrives (a chunk-mode SplitParser,
  as FoamyPrefsQueue's stderr), and sets `truncated` when it cut; `text`
  is read in the Process's `exited` handler, and `clear()` in its
  `started` handler begins each run. A cut never keeps half of a surrogate
  pair, and after a cut the collector keeps no later output until
  `clear()`, so `text` is always the start of the stream, even when the
  cut backed off a pair and left room. Quickshell decodes each pipe read
  on its own, so a character whose
  UTF-8 bytes arrive in two reads shows as U+FFFD (StdioCollector decodes
  the whole stream at once); ASCII and a stream that arrives in one read
  are exact. Plugin change: none needed; a plugin adopts it when it
  touches a collector (foamy-idle-suspend's probes first), after `sync.sh
  <plugin> --add FoamyBoundedCollector`, and treats a `truncated` reply as
  a failure, never as the whole reply. README.md: Components.
  `tests/test_collector.py`.
- `FoamyDropdown` pick serials: `changed(value, serial)` gives each pick a
  new serial, and `saveFailed(serial)` drops the pick on show only when it
  is that pick. Before, `saveFailed()` named no pick, so after quick picks
  a caller whose saves end one by one could not drop only the one that
  failed: a refusal of the first of the picks A, B, A dropped the second
  A, and comparing values (foamy-power, foamy-monitor and
  foamy-notification-center check `pickedValue`) takes a repeated value
  for the refused one. `saveFailed()` without a serial works as before,
  and a handler that takes only `value` needs no change; code that emits
  `changed()` itself must pass a serial now (see Upgrading). Plugin
  change: none needed; a plugin that ends a pick on its own failed save
  may pass the serial instead of comparing `pickedValue`: foamy-power
  (its helper's own failure signal), foamy-monitor (its own requests) and
  foamy-notification-center (its own save queue) at their next sync.
  DESIGN.md: Choices. `tests/test_features.py`.
- `FoamyDropdown.queue` and `queueKey`: a dropdown linked to the
  FoamyPrefsQueue it saves through and its key ends its pick by itself
  when the queue refuses that key: at once when `save()` refuses the pick
  (a value the schema rejects, a kept invalid stored array, a widget with
  no bar entry; `save()` returns false), and when a pick that waited
  behind a running CLI save is refused as it runs, which only `failed()`
  reports. Before, such a pick stayed on show next to the error for up to
  `pickHoldMs` (10 s) unless the plugin called `saveFailed()` on
  `save()`'s false return, and the later refusal reached only `failed()`.
  A refusal of another key leaves the pick; a dropdown without the link
  works as before. Plugin change: none needed; a plugin that saves a
  dropdown through FoamyPrefsQueue sets `queue` and `queueKey` and drops
  its own `saveFailed()` call at its next sync (foamy-bolt, foamy-clock,
  foamy-github, foamy-media, foamy-syncthing, foamy-teams, foamy-todoist,
  foamy-train, foamy-vitals, foamy-weather and foamy-zendesk have such
  dropdowns). DESIGN.md: Choices. `tests/test_features.py`.
- `FoamyScheduleDay.saveFailed()`, and the same `queue`/`queueKey` link
  as FoamyDropdown. Before, after a save that failed without changing
  `value`, the time fields kept the unsaved range and Enter did not send
  it again (the row had sent it already). `saveFailed()` shows `value`
  again and lets the same range be sent again, as
  `FoamyNumberField.saveFailed()` does; a time field edited since the
  range was sent keeps its newer draft. A row linked to the
  FoamyPrefsQueue it saves through calls it itself when the queue refuses
  its key: at once when `save()` refuses the range, or later for a range
  the row sent that the queue refuses as it runs. Plugin change: none
  needed; foamy-train and foamy-zendesk may link their rows
  (`queue: prefs; queueKey: modelData`). `tests/test_schedule.py`.

### Changed
- DESIGN.md, Tab row: names the one tab row that is not `FoamyTabs`: a
  footer row that switches the popup's source and shows each source's
  brand glyph (foamy-media's Spotify and YouTube tabs, with the glyph and
  the equalizer, which FoamyTabs cannot draw). Such a row is an
  `Accessible.PageTabList`, each tab an `Accessible.PageTab` with
  `Accessible.selected` on the open one, and each tab is one stop of the
  panel cursor. Plugin change: foamy-media gives its footer row the
  `PageTabList` role (its tabs are `PageTab`s already); foamy-syncthing's
  Folders / Devices row and foamy-monitor's Display / Advanced / Wireless
  row move to `FoamyTabs`. No kit code changes.
- `FoamyText.cap()` and `tooltip()` cut a line where a reader sees a
  character end. Before, they cut by code point (as documented), so the
  letter at the cut could lose its accent or vowel sign (an Arabic letter
  kept without its fatha), an emoji its skin tone, a ZWJ sequence could
  end in a joiner, and a flag show half (one regional indicator). The cut
  now drops the whole cluster before the "…", with foamy-media's rules: the
  Unicode 16 combining marks, Hangul jamo, the Thai and Lao vowel sign AM,
  the halfwidth kana voiced sound marks, joiners, variation selectors,
  skin tones, tags and flag pairs (Unicode's other grapheme rules, a
  conjunct across a virama or a prepended sign, are not followed). The
  functions, their arguments and the code-point count of `maxChars` are
  unchanged; a cut line can come out shorter. It reaches the bar tooltips
  of every plugin and the `FoamyAction`, `FoamyButton` and
  `FoamyPanelFooter` tooltips. Plugin change: foamy-media can drop its own
  copy of the rules (Model.js `scriptMarks`, `isScriptMark`,
  `continuesCluster`, `splitsFlag`). `tests/text.test.cjs`.

### Fixed
- The preview's mock bar (`preview/qml/MockBar.qml`, since 0.1.0) has the
  theme's bar colours, as the host's bar binds them: `foreground` and
  `barForeground` the bar text, `background` the bar background, `urgent`
  the bar's active colour. Before, it was white on black whatever the
  theme, so a host part a popup draws in the bar's colours showed wrong:
  in a light picture foamy-monitor's brightness slider had a white fill on
  a faint white track. Renders of the demo plugin are unchanged;
  foamy-monitor's display and trial pictures now show the slider as the
  host does, in both themes. No plugin change is needed; a plugin test
  that renders or reads the mock bar's colours sees the theme's. README.md:
  Preview. `tests/test_preview.py`.
- `SafeTextField` and `SafeTextArea` (since 0.13.1) give the keys of a
  focused field that hides to the nearest key home that shows
  (FoamyClickAway's `foamyKeyHome`: FoamyPopup's key catcher, a settings
  page), as a click-away does, else to the nearest focus scope as before.
  Before, the keys always went to the nearest focus scope, so the panel's
  keys (Esc, arrows) did nothing after a focused field hid until the
  plugin moved the focus itself. A key home that hides with the field (a
  settings page closing) passes the search on. Plugin change: none needed;
  a plugin that moves the focus after a field hides (foamy-notification-
  center's search) can drop that at its next sync. DESIGN.md: Click-away.
  `tests/test_text_area.py`.
- `FoamyPopup` (since 0.1.0) gives the keys back to its body when the item
  in the body that has them hides: a settings page left with Back, or
  reset when the popup closes on it (FoamySettingsState). Before, Qt kept
  the keys on the hidden page, and the host's focus on the next open went
  back to it: the first Esc after reopening, or after Back, went to the
  hidden page instead of closing the popup, unless the plugin refocused
  its list in `onHidden`. Now, once the item has hidden, the keys go to
  the nearest key home that shows: the settings page while it still shows
  (a focused Retry that hides as its retry starts leaves Esc on the page,
  which goes back), else the body's key home (`focusTarget`, the body
  item by default). A plugin's own refocus, at once or later, still wins.
  Plugin change: none needed; foamy-bolt's `onHidden` refocus can go at
  its next sync. README.md: Components; DESIGN.md: Click-away.
  `tests/test_popup_keys.py`.
- `foamy_helper::favicon` cache (since 0.13.1): a cache on a file system
  whose clock runs a little ahead of this one (NFS, SMB) reuses its icons
  again. 0.13.1 made every file time in the future stale, so there each
  new icon looked stale at once and every request looked it up and wrote
  it again (up to 2 s). A time up to 60 s ahead now counts as age 0; one
  further ahead (the clock was set back) is still stale. No source change
  is needed. `kit/rust/foamy-helper/src/favicon/tests.rs` (test
  `only_a_cached_icon_younger_than_a_day_is_reused`).

### Upgrading
- `kit/rust` changed (`json::run_bytes`, the favicon cache): a plugin with
  a native helper rebuilds it after the sync (`kit/native/build-native.sh
  .`) and commits the new binaries and `native.pin`; until then `check.sh`,
  `tests/kit-check.sh` and `--verify` report the binaries stale.
  `foamy-helper`'s version stays 0.1.2, so no plugin `Cargo.lock` changes.
- `check.sh` asks each catalog for the texts in `kit/i18n-texts.json` of
  the components a plugin carries (see Added). On the plugins' dev
  branches (kit 0.13.1) it fails 13 plugins until they add them to
  `en.json` and `no.json`: "The saved list in shell.json isn't valid, so it
  wasn't replaced." (audio, bolt, clock, media, menu, monitor,
  notification-center, power, syncthing, train, vitals, weather); the
  three paste failures (audio, monitor, power, which carry the text field
  through FoamySettings without showing one); "Settings can't be saved:
  this widget has no bar entry." (menu, monitor, notification-center);
  "That value isn't allowed." and "Couldn't save the setting." (monitor,
  notification-center); FoamyNative's "This plugin's helper isn't
  available for this CPU." (lock).
- `FoamyDropdown.changed()` has a second argument, the pick's serial (see
  Added). A handler that takes only `value` works as before, but code
  that emits `changed()` itself with one argument now throws
  "Insufficient arguments" (foamy-lock's studio test and the runtime
  tests of foamy-teams and foamy-lock did): a test or caller that emits
  `changed()` itself picks with `select(value)` instead, which shows the
  pick as the list does and emits `changed(value, serial)`.
- FoamyPopup's key return (see Fixed) learns the item with the keys from
  its window's `activeFocusItem`, which Qt keeps only in the active
  window. On the desktop the popup's window is active; a plugin test that
  runs the popup in a window that is not active, or in none, sees no key
  return, so before it drops its own refocus it puts the popup in a
  window and activates it (foamy-bolt, foamy-vitals and foamy-github had
  to).
- `tests/test_text_field.py` (new, `tests/qml/TextField.qml`) tests a
  plain SafeTextField through real keys, the mouse and real pastes: the
  13 cases foamy-bolt's and foamy-weather's `tests/tst_clipboard.qml`
  kept because the kit had no such test (a paste dropped when the field
  hides or is disabled, a late result after a caret move or typing, undo
  and redo of a paste, the caret in a 34 px field, a long paste's scroll,
  middle-click, maximumLength across pastes, refused pastes keeping the
  selection, a second Ctrl+V, Shift+Insert of an empty clipboard, typing
  after a paste as its own undo step, Tab, Shift+Tab and Return). No kit
  code changed. Plugin change: foamy-bolt and foamy-weather delete
  `tests/tst_clipboard.qml`, `tests/test_clipboard.py` and their suite and
  README lines at their next sync.

## 0.13.1 — 2026-11-22

### Added
- `FoamyDropdown.saveFailed()`: tells the dropdown that its last pick was
  not saved, so it shows `value` again at once, as
  `FoamyNumberField.saveFailed()` does for a field. Call it when a save
  fails without changing `value`. With `FoamyPrefsQueue` that is a save
  that `save()` refuses before any value is pending: it returns false (a
  value the schema rejects, a kept invalid stored array, a widget with no
  bar entry), e.g. `onChanged: function (v) { if (!prefs.save("mode", v))
  modeDropdown.saveFailed() }`. A CLI save that fails later rolls `value`
  back, which ends the pick by itself. A queue caller whose dropdown
  offers only valid values of a non-array field, in a widget with its bar
  entry, cannot get such a refusal and needs no change. Plugin change:
  foamy-power's default profile dropdowns (a failed
  `PowerService.setDefault()` leaves `value` as it was) call `saveFailed()`
  on the dropdown whose save failed, and only when the failed value equals
  its `pickedValue`: the function takes no argument, so after two quick
  picks a failure of the first must not drop the second. DESIGN.md:
  Choices. `tests/test_features.py`.

### Fixed
- `FoamyNumberField` and `FoamyTextSettingField` commit on focus-out
  (broken since they came in, 0.3.2). Moving the focus away (Tab, a click
  on another field) left a valid draft uncommitted and an invalid one on
  screen: only Enter saved. The fields commit on `editingFinished` only
  when the editor has lost the focus, and `SafeTextField.inputActiveFocus`
  was a binding that still read true inside that handler. It is now an
  alias of the editor's `activeFocus` (same name, type and change signal),
  so a focus move commits a valid changed draft once and restores `value`
  with the error for an invalid one. A field that hides (a settings page
  that closes while kept alive) ends its edit the same way, since
  `SafeTextField` now gives up the focus when it hides: a valid changed
  draft is committed and an invalid one is put back. When the field shows
  again it shows `value` with no error line, also after a focus-out left
  one, so a page the user comes back to shows no error for text that is
  gone. `SafeTextArea.inputActiveFocus` had the same lag and is an alias
  too. No plugin change is needed; a plugin
  that reads `inputActiveFocus` in its own `onEditingFinished` now gets
  false there. `tests/test_features.py`, `tests/test_text_area.py`.
- `SafeTextField` (since 0.2.0) and `SafeTextArea` (since 0.13.0) never
  keep half of a surrogate pair at `maximumLength`. A normal
  `SafeTextField` cut a paste, a longer `text` and a lowered
  `maximumLength` by UTF-16 unit, so an emoji at the limit left a lone
  high surrogate at the end (maximumLength 5 and "abcd😀" gave five units
  ending in 0xD83D). `SafeTextArea` did so for a longer `text` and a
  lowered `maximumLength` (its paste was already cut by code point). Every
  cut now drops the whole pair, as the masked field already did. No plugin
  change is needed. `tests/test_features.py`, `tests/test_masked.py`,
  `tests/test_text_area.py`.
- `SafeTextArea` (since 0.13.0) shows its text inside its paddings. The
  attached `TextArea` left the field scrolled one padding to the side
  (`contentX` at minus `leftPadding`), so the text sat one padding too far
  in, and in a right-to-left layout the ends of the lines were cut at the
  field's edge ("line" showed as "lir", a quiet area's "In place" as "In
  plac"). It now keeps the horizontal scroll inside the text, as
  `SafeTextField` does. No plugin change is needed.
  `tests/test_text_area.py`.
- `SafeTextField` (since 0.2.0) drops a key typed at `maximumLength`,
  wherever the caret is, as Qt's `TextInput` and `SafeTextArea` do.
  Before, the key was kept and the end of the text was cut: typing 8
  after the first 0 of a full `09:00` time field gave `089:0`, and in a
  long field the lost end could be out of view. A longer `text` from the
  caller or an input method is still cut at its end; a masked field
  already dropped the key. No plugin change is needed.
  `tests/test_features.py`.
- `SafeTextField` (since 0.2.0) cuts its text to a `maximumLength` that is
  lowered while the page is created. A bound `maximumLength` lowered after
  the editor took its text and before the field's own
  `Component.onCompleted` (Qt completes in reverse creation order, so a
  root's or a later sibling's handler runs first) left the whole text,
  since the field reacts to `maximumLength` changes only once it is
  complete. `SafeTextArea` already cut the text then. No plugin change is
  needed. `tests/test_features.py`.
- `SafeTextField` with `masked: true` (since 0.12.0) tells a screen
  reader its label. Qt reports no accessible name for a password edit
  (Qt 6.12 drops `Accessible.name` there), so an "API token" field was
  announced as an unnamed password field. The masked editor now also gives
  the field's `Accessible.name` as its description, which Qt keeps. The
  editors of `SafeTextField` and `SafeTextArea` also pass the field's
  `Accessible.description` on (it never reached them, so
  `FoamyNumberField`'s `description` was not read out); a masked field
  uses its description for the name instead. A field or area with no
  `Accessible.description` gives its `placeholderText` as the description,
  as Qt does while nothing sets one, so a screen reader still reads out a
  placeholder hint (a search field labelled only "Search"). No plugin
  change is needed. DESIGN.md: Inputs. `tests/test_masked.py`,
  `tests/test_text_area.py`.
- `SafeTextField` (since 0.1.0) and `SafeTextArea` (since 0.13.0) give up
  the keyboard focus when they hide (their own `visible` or a parent's).
  Qt keeps the active focus on a hidden item, so keys typed after a
  focused field was hidden still edited text the user could not see. A
  field hidden while its context menu is open closes the menu, so Esc or
  the menu's Paste no longer gives the hidden field the focus back.
  Losing the focus ends the edit as any focus loss does: `editingFinished`
  comes once, when the field hides, instead of at the next focus move. A
  plugin that saves on `editingFinished` now saves a hidden field's draft
  at once (foamy-clock's custom value already ignores a hidden field
  there); a plugin that shows the field again focuses it again
  (`focusInput()`). The focus goes to the field's nearest focus scope, not
  to a `PanelKeyCatcher` in it: a plugin whose panel keys (Esc, arrows)
  must work right after a field hides moves the focus itself, as
  foamy-notification-center's search does. `tests/test_text_area.py`.
- `clipboard.sh` (`FoamyClipboard`, `SafeTextField`, `SafeTextArea`): a
  read ends at once however its wrapper ends. Before (since 0.1.0), a
  `FoamyClipboard` destroyed during a read (a closed field, a reload) left
  `wl-paste` and its pipeline running until the 2 s deadline: Quickshell
  kills the script with SIGKILL then, which its trap never saw. A TERM in
  the moment between the start of the read and the trap did the same.
  Now a small guard process kills the read when the script ends without
  finishing it, SIGKILL included, also when a stop goes to the script's
  whole process group, and the TERM, INT and HUP trap is set before the
  read starts. The exit codes and the output are unchanged; the 2 s
  deadline stays. No plugin change is needed. `tests/test_clipboard.py`
  (SIGKILL at the start and mid-read, a stop to the process group),
  `tests/test_clipboard_reader.py` (a destroyed reader).
- `FoamyScheduleDay`: a time range is sent once per commit. Before (since
  0.9.0, when the row moved into the kit), Enter emitted `changed(range)`
  and the focus loss after it (Tab, a click elsewhere, the other field)
  emitted the same range again whenever the caller's `value` had not yet
  caught up. Now the same range is sent again only after an edit of a
  time field or a change of `value`. Callers that reflect the value at
  once (`FoamyPrefsQueue`) see no change. No plugin change is needed.
  `tests/test_schedule.py`.
- `FoamyNumberField` and `FoamyTextSettingField` (since 0.3.4): a
  refused paste (too large, timed out, not plain text) replaces the error
  the line shows for the draft. Before, a field that already showed its
  draft's error (a number out of range, a `validate` message, after Enter
  or a focus-out) kept it, so the refused paste said nothing:
  `SafeTextField` sets `pasteError` without a text change, and the line
  put the draft's error first. Enter with the draft still invalid shows
  that error again. `FoamyTextSettingField.pasteFailed`, documented since
  0.3.4 but never emitted, now comes as `FoamyNumberField`'s does. No
  plugin change is needed. `tests/test_features.py`.
- `FoamyScheduleDay` (since 0.9.0) says why a paste into a From or To
  field was refused (too large, timed out, not plain text: the field's
  `pasteError`), through `FoamyI18n.t`, in an error line under the row,
  as `FoamyNumberField` does. The newest refused paste shows, until that
  field's next edit. Before, the paste just did nothing. The row's root
  is now a `ColumnLayout` (the row, then the line), so its `spacing` is
  the gap above the line; no plugin sets it. No plugin change is needed:
  foamy-train and foamy-zendesk have the three messages in both
  catalogs. `tests/test_schedule.py`.
- `FoamyWheelScroll.ensureVisible` (and `FoamySettingsPage.ensureVisible`)
  shows all of a section that unfolds at the end of the content. Before
  (since 0.4.0), it placed the section when the section's height changed,
  before the Flickable's content had grown, so the scroll stopped at the
  old end of the content: the last pixels of an animated section, or
  almost all of one that unfolds at once (reduced motion), stayed below
  the fold. Now it places the section again when the content height
  changes while it follows. A scroll that is still gliding when the bounds
  shrink (a popup body that grows to fit its content does so after the
  content grew) is aimed inside the new bounds again, so the view never
  ends past the end of its content; the glide's end used to be clamped
  only when it started, which in foamy-train's settings left the page
  337 px past its end after "Use a weekly schedule" was switched on. This
  also holds for a wheel notch. No plugin change is needed.
  `tests/test_wheel.py`.
- `FoamyDropdown`: a failed save that does not change `value` no longer
  leaves the unsaved pick on show. Before (since 0.2.0), the trigger kept
  showing the pick (`shownValue`) for up to `pickHoldMs` (10 s) next to
  the save's error, and the caller had no way to drop it. A caller whose
  failed save does not change `value` (foamy-power's default profiles, a
  `FoamyPrefsQueue` save that `save()` refuses) calls the new
  `saveFailed()` on the failure (see Added).
  `tests/test_features.py`.
- `FoamyDropdown` (since 0.1.0) closes its list when it is disabled (its
  own `enabled` or a parent's), and `open()` and `toggle()` open no list
  while it is disabled. The list lives in the window's overlay, outside
  the disabled tree, so a list left open when the dropdown was disabled (a
  settings page that starts saving, a panel busy with a drag) still took
  Enter and a click, and the pick reached `onChanged`; a panel's `open()`
  on a disabled dropdown opened a working list too. No plugin change is
  needed; a plugin that refuses such a pick itself (foamy-monitor) can
  drop that once it syncs. `tests/test_features.py`.
- `FoamyAction`, `FoamyButton` and `FoamyPanelFooter` tooltips (the
  footer's `statusTooltip`): at most `Style.space(320)` wide, as the host
  caps its own long tooltips, and a few lines high. Before (since 0.1.0
  for `FoamyAction`, 0.4.0 for the other two), the host's `PanelToolTip`
  was as wide as its text and wrapped only under a cap, so a long
  `tooltipText` or `statusTooltip` (a folder path, an app's name, an
  error's detail) spread over the whole popup. Now a long text wraps in
  a tooltip-sized box, a word with no break (a name typed without spaces)
  breaks anywhere, and the shown text is cut to 3 lines of 200 characters
  with a visible "…" (`FoamyText.cap()`), so a 4096-byte path no longer
  fills the popup's height. Short labels keep their own width and text.
  Where the tooltip names the control, its `Accessible.name` keeps the
  whole text: a `FoamyAction`, and a `FoamyButton` without text. A
  `FoamyButton` with text is named by its text and the footer's status
  by `status`, so a screen reader reads neither tooltip, as before. The
  three components now depend on `FoamyText`, so a plugin's next sync
  adds `kit/FoamyText.js` where it was not selected yet; no plugin change
  is needed.
  `tests/test_features.py`.
- `foamy_helper::fs::read_file_limited` (since 0.5.0): the error for a file
  over the limit lost its `io::TooLarge` payload when the path was added to
  the message, so `io::is_over_limit` was false for it and a helper could
  not tell "too large" from other read errors. The error now keeps the
  payload as its source and `io::is_over_limit` also looks at the source,
  so it is true; the message (`cannot read <path>: input is larger than N
  bytes`) and the kind (`InvalidData`) are unchanged. No source change is
  needed; a helper may now use `is_over_limit` on `read_file_limited`'s
  error. `kit/rust/foamy-helper/src/fs.rs` (test
  `bounded_file_reads_refuse_links_and_special_files`).
- `foamy_helper::lock::runtime_dir` (since 0.5.0) treats a shared
  `XDG_RUNTIME_DIR` as unset. Before, only `<base>/<plugin>` was checked:
  with `XDG_RUNTIME_DIR` set to `/tmp` or another directory other users
  can write (a session without pam_systemd), another local user could
  create `<base>/<plugin>` first, and `runtime_dir` then failed with
  `PermissionDenied` or `InvalidInput` instead of the documented
  `NotFound`, so a caller could not tell it from a broken directory. Now
  the base must be the user's own directory, closed to everyone else and
  not a symlink, as the XDG Base Directory spec requires, or `runtime_dir`
  (and `try_runtime_lock`) returns `NotFound` before it creates anything,
  so a caller can fall back. No source change is needed. foamy-todoist
  and foamy-zendesk do not fall back: in such a session they now answer
  `LOCK_UNAVAILABLE` for every locked operation, as they did before only
  once another user had taken the directory; foamy-power, which checks
  its own base this way, falls back to its cache directory.
  `kit/rust/foamy-helper/src/lock.rs` (test
  `a_shared_runtime_base_counts_as_unset`).
- `foamy_helper::json::run` (since 0.9.0): the reply was marked as printed
  before it was written. A panic in another thread at that moment made the
  panic hook print nothing and exit 101 while the reply was still being
  written, so the caller got no JSON or a cut-off line. The mark and the
  write now share one lock with the panic hook: a panic during the write
  waits until the whole line is out, and `run` then returns 101 too, so
  the helper exits 101 without a second reply whether the hook or `main`
  ends the process. No source change is needed.
  `kit/rust/foamy-helper/src/json.rs` (test
  `a_panic_while_the_reply_is_written_waits_for_it`).
- `foamy_helper::favicon` (since 0.5.2): a set but empty or relative
  `XDG_CACHE_HOME` was used as a relative cache directory, so the helper
  copied the browser's icon into `foamy/browser-favicons/` under its
  working directory and then replied `error` (a relative path has no
  `file://` URI); an empty or relative `XDG_CONFIG_HOME` made it look for
  browser profiles relative to the working directory. `Dirs::from_env` now
  treats an empty or relative XDG variable as unset, as the XDG Base
  Directory spec says (`~/.cache`, `~/.config`), and `resolve` refuses a
  relative cache or browser profile directory (a relative `HOME`, or a
  caller's `Dirs`) with the same `error` reply before it reads or writes
  anything. No source change is needed.
  `kit/rust/foamy-helper/src/favicon/tests.rs` (test
  `xdg_dirs_must_be_absolute`).
- `foamy_helper::favicon` cache (since 0.5.2): a cached icon with a
  modification time in the future counted as fresh, so after the clock was
  set back an old icon stayed in use until the clock passed its time plus
  24 hours. Such a file is now stale and the icon is looked up again.
  When the cache is full, such files are removed first and the icon just
  written is always kept; before, a cache full of them made the helper
  remove each new icon at once and reply `found` with a file that no
  longer existed. No source change is needed.
  `kit/rust/foamy-helper/src/favicon/tests.rs` (tests
  `only_a_cached_icon_younger_than_a_day_is_reused`,
  `a_new_icon_outlives_a_full_cache_of_files_from_the_future`,
  `prune_keeps_the_icon_just_written`).
- `tests/kit-check.sh` (generated from `tools/kit-check.sh.in`) names a
  `native.pin` checksum line for a file other than `bin/x86_64/<binary>`
  and `bin/aarch64/<binary>`: "`<crate>/native.pin lists unexpected file
  <path>`", the message `check.sh` has given since 0.5.0. Before, it
  ignored such a line and failed the pin only through the notices check,
  without the reason. Plugins get the new check at their next sync.
  `tests/test_native.py`.
- `tests/validate.sh` qmllint check (since 0.9.0): when qmllint leaves no
  readable report, the failure gives qmllint's exit code and the read
  error ("`qmllint wrote no JSON report (exit 5): [Errno 2] No such file
  or directory: …`"). Before, a full `/tmp` or a crashed qmllint looked
  like a plain lint failure. The oxlint, ruff and shellcheck checks give
  the tool's exit code the same way when it prints no JSON report
  ("`oxlint produced no JSON report (exit 9)`"). No plugin change is
  needed. `tests/test_validate.py`.
- `tests/validate.sh` oxlint check (since 0.9.0): a local
  `tests/lint/oxlintrc.json` must list `"../../.oxlintrc.json"` in its
  `"extends"` array. Before, the name anywhere in the file passed (a
  comment, `ignorePatterns`, an `extends` string), and such a file replaced
  the kit's rules. The file is read as oxlint reads it (comments and
  trailing commas allowed); one that does not parse fails with "is not
  JSON" and the parse error. No plugin carries a local oxlintrc.json today.
  `tests/test_validate.py`.
- `preview/render.py --trio` (since 0.5.2) keeps each render's log in the
  output dir: `render-before.log` and `render-after-<host>.log`. Before,
  a failed render printed the path of a `render.log` inside the trio's
  temporary work dir, which the trio then removed. `render.render()` takes
  a new optional `log` path (default `<out>/render.log`, as before).
  README.md: Before / after trio. `tests/test_trio.py`.
- `preview/harness.py` (since 0.5.2): a private dbus-daemon that exits, or
  that does not create its socket within 2 s, now stops `Run.start()` and
  `Run.start_buses()` with `SystemExit` naming the cause, and the daemon is
  stopped. Before, the run went on with a dead bus address and a later
  D-Bus step failed with an unrelated error. A missing `dbus-daemon` still
  leaves the dead address, as documented. `tests/test_harness.py`.
- `preview/harness.py` `Run.stop()` (since 0.1.0) and
  `hostenv.ProcessGroup.stop()` (since 0.9.0) also end a helper that leads
  a process group of its own. A helper that a plugin runs under coreutils
  `timeout` (FoamyNative's documented call) is outside qs's group, and
  Quickshell does not end it when qs stops, so it ran on after the test
  until its own deadline (30 s in FoamyNative's example). Now `stop()`
  also kills every process left in qs's session (the leader's, for
  `ProcessGroup`) and returns once none is left; only a child that makes
  its own session (`setsid`) is outside it. No plugin change is needed.
  README.md: Preview, Test helpers for plugins. `tests/test_harness.py`,
  `tests/test_helpers.py`.
- `preview/hostenv.py` `check()` (since 0.9.0) fails when `OMARCHY_PATH/bin`
  resolves outside the private tree's parent as a path. Before, a string
  prefix let `/tmp/xy/bin` pass for `/tmp/x`. No plugin change is needed.
  `tests/test_helpers.py`.
- `preview/hostenv.py` `isolate()` (since 0.9.0): a test that isolates
  its environment with `isolate()` alone can no longer run a host
  command. It kept the caller's `OMARCHY_PATH` (the installed
  `/usr/share/omarchy` in an Omarchy session) and the `omarchy-*` commands
  in `/usr/bin`, so a host script reached through `OMARCHY_PATH` or by
  name ran for real (`/usr/bin/omarchy-shell` finds the live shell from
  `OMARCHY_PATH` and `XDG_RUNTIME_DIR`), and `check()` passed such an env
  although it is documented to fail when `OMARCHY_PATH/bin` is not the
  stubs. Now `OMARCHY_PATH` is a private tree in `base` (the host's
  `shell/` and `default/` only, as `make()`'s), every `omarchy`/`omarchy-*`
  command on `PATH` or in Omarchy's bin dirs is a stub in its `bin/`,
  first on `PATH`, that logs the call to `<base>/host-commands.log` and
  exits 127, and `check()` fails for an env whose `OMARCHY_PATH` is a host
  tree. A test that needs a host command gives it a stand-in (`make()`, or
  its own directory in front of `PATH`). No plugin change is needed.
  README.md: Test helpers for plugins. `tests/test_helpers.py`.
- `preview/hostenv.py` `clipboard_fakes()` (since 0.9.0): the stand-in
  `timeout` changes only clipboard.sh's read. Before, it turned every
  `timeout --signal=KILL 2s …` on the test's `PATH` into 60 s, so a
  plugin command with the same deadline (foamy-menu's launcher probe,
  `timeout --signal=KILL 2s bash -lc …`) passed when it was too slow, and
  a test of that deadline waited 60 s. Now only `timeout --signal=KILL 2s
  bash <clipboard.sh> _read …` gets 60 s (outside the deadline modes);
  every other call keeps its own deadline. A plugin test that works
  around it (foamy-menu's guard probe uses 3 s) can use 2 s again.
  README.md: Test helpers for plugins. `tests/test_clipboard.py`.
- `preview/compare.py` (since 0.5.2) exits 2 ("unreadable") with the reason
  for a damaged PNG: a header cut short, a chunk that runs past the end of
  the file, image data shorter than its rows, or a row filter type above 4.
  Before, these ended in a traceback with exit 1 ("different"), or a filter
  type 5-255 was decoded as no filter. Bytes after the `IEND` chunk are
  ignored, as before. No plugin change is needed. `tests/test_compare.py`.
- `preview/compare.py` (since 0.5.2) inflates no more image data than the
  picture's rows need. Before, it inflated all of it before it checked
  the length, and it trusted any width and height in the header, so a PNG
  of a few hundred KiB could take gigabytes of memory. Now a PNG whose
  image data runs on past its rows, or whose header declares more than a
  4096 x 4096 RGBA picture (the kit's largest render, a 1920x1080 screen
  at scale 2, is 3840 x 2160), is unreadable (exit 2) before the rest is
  inflated; before, data past the rows was ignored. A stream that does
  not end after the rows is unreadable, as before. No plugin change is
  needed. README.md: Preview. `tests/test_compare.py`.

### Changed
- `REVIEW.md`, section 6 "Test the behavior": it now says what a test must
  protect, asks that every new or changed test is seen failing with the
  behavior broken, lists the tests not to add (source text as a stand-in
  for behavior, a mirror of the implementation, a repeat of a kit test in a
  plugin, a test that cannot fail), and says that a new test file runs in
  `tests/suite.sh` in the same change. The review block that sync keeps in
  each plugin's `AGENTS.md` gains one sentence that sends an agent to that
  section before it adds or changes a test. `check.sh` and
  `tests/kit-check.sh` expect the new block after the next sync. No plugin
  code changes.
- README.md, Preview: reads of the preview's scope inside the `body`
  Component lint clean when `preview/Preview.qml` starts with `pragma
  ComponentBehavior: Bound`: `preview.…` and `preview.popup.…` do, a bare
  `popup.…` stays `unqualified`. README said no form was clean there. The
  demo plugin's preview, with the pragma, has no `unqualified` finding
  left and renders the same. No plugin change is needed; a preview that
  adds the pragma drops the baseline entries it ends
  (`tests/validate.sh --update-baseline qmllint`).

### Upgrading
- `kit/rust` changed (the five `foamy_helper` items above): a plugin with a
  native helper rebuilds it after the sync (`kit/native/build-native.sh .`)
  and commits the new binaries and `native.pin`; until then `check.sh`,
  `tests/kit-check.sh` and `--verify` report the binaries stale. No call
  site changes, and `foamy-helper`'s version stays the same.
- foamy-power calls `FoamyDropdown.saveFailed()` when a default profile
  save fails (see Added). The text field items above ask a plugin to act
  only in the cases they name (a hidden field shown again, panel keys
  right after a field hides).
- The sync replaces `REVIEW.md` and the review block in `AGENTS.md` (see
  Changed). Nothing else in a plugin changes for it.

## 0.13.0 — 2026-11-19

### Added
- Click-away (`FoamyClickAway`): a click on space that does nothing in a
  Foamy popup takes the keys from a focused text field (`SafeTextField`,
  `SafeTextArea`, any `TextInput` or `TextEdit`), which ends its edit
  (`editingFinished`), and gives them to its key home: the nearest
  ancestor's `foamyKeyHome` (FoamyPopup's body: `focusTarget`, the body
  item while that is the default; `FoamySettingsPage`: the page, so Esc
  still goes back). It lies under the content, so rows, buttons and fields
  keep their clicks, a drag on empty space still flicks and the wheel
  still scrolls. FoamyPopup puts one under its body; `FoamyWheelScroll`
  one in its Flickable's content item, covering the view (`clickAway`,
  default true; `SafeTextArea`'s own is off) and says `spaceClicked` on
  each click there. No plugin change is needed. DESIGN.md: Click-away.
  `tests/test_click_away.py`.
- `FoamyHeroBand` field mode: `field` (a caller's item, normally a
  `SafeTextField`), `fieldOrigin` (the header action it grows from) and
  `fieldOpen`. Opening, the field grows from the action's rectangle to the
  full width between the side paddings, in the title row's slot, and the
  title row and the buttons fade out; closing reverses it
  (`FoamyMotion.grow`, `fadeOut`, `fadeIn`; instant under reduced motion;
  mirrored in RTL). The band's height never changes, and a hero stays in
  place. The band sets the field's text to `FoamyStyle.font.title`, the
  size of the title it covers.
  While the field is open, `buttonsActive` is false: the buttons take no
  pointer input or focus, `settingsHasCursor`/`menuHasCursor` light
  nothing and the ⋯ menu closes and won't open. `fieldShown` and
  `fieldProgress` expose the state and the animation; keys stay the
  caller's. `menuHasCursor` is now a property of the band instead of an
  alias (same use). The field takes pointer input and focus only while
  `fieldOpen`: closing, it is inert at once and drops the active focus,
  so a click on the fading field can't take the focus back and no key
  edits the hidden text. Field mode is for bands with a title row: a
  `centered` band ignores `fieldOpen` (its title is under the hero).
  DESIGN.md: one field at a time, the band height is fixed, "+" sits left
  of Search. `tests/test_band_field.py`.
- `SafeTextField.runs`: an array of `{text, color}` whose texts join to the
  field's text. The field then draws each run in its colour over its own
  glyphs (same font, each run placed where the editor puts its first
  character and on the editor's baseline, so a Latin run next to CJK text
  doesn't jump up; clipped where the editor clips), aligned while the field
  scrolls, with the caret still drawn. A run whose colour is missing or
  not one Qt can read ("bogus") takes the field's `color`. Runs that don't
  match the text (also during an edit, before the caller updates them),
  that the editor lays out other than as one piece (mixed directions,
  letters joined across runs), while text is selected (a run cut at the
  selection would lose its shaping) or while an input method composes (its
  preedit shows only in the editor) give the plain field (`runsShown` says
  which); no position past the text's end is ever asked for. A masked
  field ignores them. The field's `color` is now its own property (same
  use). `tests/test_text_runs.py` compares the styled field's pixels with a
  plain field's, in Arabic, mixed Latin and CJK and during a composition
  too (with `tests/fixtures/fake-ime`, a test-only QML module it builds
  with moc and g++), and fails on Qt's "out of range" warning.
- `SafeTextArea`: the multi-line sibling of `SafeTextField`. Paste goes
  through `FoamyClipboard` with line breaks kept (16 KiB, no NUL, 2 s
  deadline, a late result dropped); `maximumLength` (typing at the limit
  drops the key, a paste is cut to fit), word wrap, `minimumHeight` and
  `maximumHeight` (it scrolls past it, following the caret, wheel through
  `FoamyWheelScroll`), `placeholderText`, `translate`, the accessible name,
  `textEdited`, `editingFinished` on focus loss, and the `keyPressed` hook.
  Enter and Shift+Enter insert a newline. `tests/test_text_area.py`.
- `FoamyStyle.controlPaddingY` (6): the padding above and below the text
  of a multi-line field.
- `clipboard.sh clipboard|primary multiline` and
  `FoamyClipboard.multiline`: line breaks are kept as `\n` (CR LF, CR,
  U+2028 and U+2029 each become one) instead of turning into spaces. The
  same bounds; any other extra argument is refused (exit 2).
  `hostenv.clipboard_fakes()` has a `breaks` mode.
- FoamyIcon: `calendar-range`, `flag`, `target` and `text` (Lucide
  1.65.0, lucide-static), 122 names.
- `FoamyHeroBand.compactTrailing` (`FoamySettingsHeader.trailing`): icon
  actions at the compact band's trailing end, after "Saving…", for a
  sub-view built like the settings page (an editor page's "Open in …").
  The band keeps its height. `tests/test_band.py`.
- `SafeTextField.quiet` and `SafeTextArea.quiet`: text edited in place (an
  editor's title or description that reads as text). At rest the field
  has no fill and no border; hover, the cursor (`hasCursor`) and the focus
  show the usual field. The border keeps its width, so the text doesn't
  move. DESIGN.md, "Inputs". `tests/test_text_area.py`.

### Fixed
- `SafeTextField` placeholder colour (since 0.1.0) and `SafeTextArea`'s:
  `FoamyPalette.mutedText` instead of `Qt.darker(foreground, 1.6)`, which
  in a light theme came out darker than the text itself. The placeholder
  now reads as a hint in light and dark themes.
- `FoamySettingsPage` focus follow with a `SafeTextArea`: the page now
  scrolls to the area's box. Before, it measured the area's inner editor,
  which is as tall as the whole text, and scrolled a field that already
  showed. The area says so with its new read-only `scrollsItself`, so the
  page needs no `SafeTextArea` in its sync set. `tests/test_wheel.py`, and
  `tests/test_sync_check.py` now fails a component that names a kit type
  its deps don't sync.
- `SafeTextField` and `SafeTextArea`: opening the field's own context menu
  (a right-click) no longer emits `editingFinished`. The menu takes the
  focus, so a caller that saves and hides the field on `editingFinished`
  (an editor's date field) hid it under the menu, and the menu's Paste
  was refused because the field was hidden. Now the edit goes on while the
  menu is open; `editingFinished` comes when the menu closes without
  giving the focus back (a press elsewhere), once, and not at all when
  the focus returns to the field (Esc, Paste). `tests/test_text_area.py`.
- `FoamyMenu` keeps the keyboard's entry in view: in a menu taller than
  its room, Up, Down, Home, End, opening from the keyboard and leaving or
  entering a submenu scroll the least that shows the entry, so Enter never
  picks an entry the user can't see. The wheel scrolls as before. Only a
  pointer that moved takes the highlight: rows scrolling under a resting
  pointer no longer replace the keys' entry. `tests/test_menu.py`.

## 0.12.1 — 2026-11-19

### Fixed
- `foamy_helper::io::read_stdin_limited` ends at the helper's run budget
  (`process::set_run_budget`): a caller that wrote its request but never
  closed standard input kept the helper waiting with no end. The read now
  waits in `poll` for at most the time left and fails with kind `TimedOut`.
  Without a run budget it reads as before.

### Added
- foamy-kit is the home repository for agent work across the plugins.
  `AGENTS.md` lists every plugin under `## Plugins` with its local path and
  clone URL. `CLAUDE.md` imports `AGENTS.md`.
- `check.sh` fails for a published plugin (a checkout whose `origin` is a
  `github.com/foamrider` repository) that the list leaves out, and when the
  list is missing or malformed. `--lint-only` skips it. Plain copies, forks
  and plugins that were never pushed are not checked.
- The `omarchy-marketplace-plugin-update` skill, in `.agents/skills/` with a
  `.claude/skills/` link. Submissions target the `main` merge commit.

### Changed
- `REVIEW.md`, section 5 "Review security at the actual sink": never ship
  an editable `TextInput`, or a `TextField` built on it. Qt reads the
  whole clipboard text on the UI thread, with no byte cap or deadline, on
  every clipboard change to update `canPaste`, with no paste gesture, so
  a bounded paste alone does not protect the shell (the marketplace
  review of Foamy Lock, cited in the guide's evidence table). Use
  `SafeTextField`, or a read-only `TextInput` that the plugin edits
  itself (foamy-lock's password field), and paste through
  `FoamyClipboard`. The sync replaces `REVIEW.md` in each plugin; a
  plugin that ships an editable Qt text input changes it.

## 0.12.0 — 2026-11-16

### Added
- `FoamyTabs`: a tab row (underline tabs, each with a label and an optional
  icon and count, one open), for a view switch at the top of the popup
  body, directly under the hero band. Full width, height `controlHeight +
  gap`; tabs as wide as their content from the reading start, inset
  `gapLarge` and padded `rowPadding`, so the first icon lines up with the
  rows' content. The open tab has a DemiBold label, an accent icon and
  count and a 2px accent underline on the row's 1px `divider` hairline,
  which the row draws itself; an urgent count is in the error colour. When
  the tabs don't fit, labels elide from the last tab inward; icons and
  counts never clip, and the row never scrolls. It never assigns `value`:
  a press or Enter/Space emits `activated(value)`. One cursor stop in the
  panel's FoamyCursor: `hasCursor`, `cursorIndex`, `moveCursor(dx)` (dx
  from PanelKeyCatcher, already in reading order), `activateCursor()`,
  `hovered()`. Mirrors with LayoutMirroring; tab-list and page-tab
  accessibility. `tests/test_tabs.py` (LTR/RTL, the standard and wide
  popup, scale 1.0 and 1.25, dark and light).
- FoamyIcon: `inbox`, `calendar-days`, `hash` and `user` (Lucide 1.65.0,
  lucide-static), and the Todoist brand mark (Simple Icons, CC0, drawn
  filled like `zendesk`; brand marks are listed in `filled`), 118 names.
- `SafeTextField.masked`: a password-style field for secrets such as API
  tokens. The editor holds only the mask (one • per code point), so Qt still
  places the caret, selection and clicks; the value is in the read-only
  `secretText`, and `text` is the mask. Typing, Backspace/Delete (word
  variants delete to the start/end), arrows, Home/End, Shift and mouse
  selection, Ctrl+A, Enter and paste (Ctrl+V, Shift+Insert, the menu,
  middle-click; still through `clipboard.sh`) work, within `maximumLength`;
  `textEdited` fires on each change of the value. Copy, cut, undo and redo do
  nothing, and nothing is written to the clipboard or the primary selection;
  input methods are off and accessibility reports a password edit. New
  `clear()` empties text and value. Set `masked` at creation: assigning
  `text`, or changing `masked` later, clears the field.
  `tests/test_masked.py` (LTR/RTL, dark and light).

### Fixed
- The kit's qmllint baseline drops the 32 `FoamyStyle.font` entries
  that 0.11.0's typed `TypeScale` fixed.
- `tools/update-icons.py` works again on the qmlformat-formatted
  `FoamyIcon.qml`: it finds the table's end and keeps the entries' indent
  whatever the indentation, instead of assuming two and four spaces.

## 0.11.0 — 2026-11-16

### Added
- `FoamyClipboard.qml`: the QML side of `FoamyClipboard`, from foamy-menu's
  launcher, for a second plugin that needs it (foamy-lock's password
  field). `start(primary)` runs `clipboard.sh` for the clipboard or the
  primary selection; `read(text)` or `failed(message)` (English) follows
  exactly once, on exit or a failed start, and never after `cancel()`.
  It stays busy until a stopped read has exited, so a new read can't
  take the old one's exit. `tests/test_clipboard_reader.py` runs it
  against the `hostenv.clipboard_fakes()` stand-ins.

- `tests/lint/qmllint-links.txt` (plugin-owned, optional): links qmllint's
  staged copy adds for QML that runs from a root assembled at run time
  (Lock Studio imports `kit`, `elements` and the lock's view beside its
  own files). `validate.sh` lints a copy with those links, so those imports
  resolve instead of filling the baseline; each link must be a new
  relative path and its target an existing path in the repository or
  `@shell/<path>`, with a reason.

### Fixed
- `SafeTextField`: its editor, the tab stop, has the editable-text
  accessible role next to the field's name (it had no role).
- `FoamyStyle.font` is a named type (`TypeScale`), so qmllint knows its
  members: `FoamyStyle.font.body` and the rest no longer report a missing
  property. The values are unchanged. A plugin's qmllint baseline may then
  list fixed entries; shrink it.

## 0.10.0 — 2026-11-16

### Added
- `FoamyClipboard`: `kit/clipboard.sh` as a component of its own, for a
  plugin that draws its own text input and must paste without Qt (Qt's
  `paste()` reads the whole clipboard on the UI thread, with no byte cap or
  total deadline). `SafeTextField` now depends on it and ships the same
  files as before; a plugin's next sync adds `FoamyClipboard` to its lock.
  The script's header documents its arguments, output and exit codes.

## 0.9.0 — 2026-11-12

### Added
- `tests/validate.sh`: one validation command for foamy-kit and every
  plugin (README "Tooling", REVIEW.md section 3). It runs kit-check,
  omarchy-plugin-validate, the kit's `check.sh`, Qt 6 qmllint (with the
  Omarchy shell as `qs`, unused imports as errors), qmlformat, Oxlint (over
  QML-loaded files too, their `.pragma`/`.import` read as comments), Ruff
  lint and format, Vulture, `bash -n` with ShellCheck, shfmt,
  `build-native.sh --test` and then the plugin's own `tests/suite.sh`; it
  exits nonzero on any failure. `--ci` skips the host checks with a reason,
  `--fast` the native tests. Existing findings live in reviewed
  `tests/lint/<check>-baseline.txt` files that match on file, rule, message
  and source text; only new findings (or a baselined function grown more
  complex) fail. `--update-baseline` rewrites them. Kit-owned files are never
  linted or reformatted in a plugin.
- Pinned tools and shared configuration: `mise.toml` (node 26.13.0, ruff
  0.17.3, oxlint 1.91.0, vulture 2.16, shfmt 3.14.1, shellcheck 0.11.0;
  `mise install`), `ruff.toml` (E, F, W, B, C901 at 15), `.oxlintrc.json`,
  `.qmlformat.ini` (2-space indent, no reordering). A missing or other
  version fails validate.
- `.github/workflows/checks.yml`: `tests/validate.sh --ci` on ubuntu-24.04
  for pushes and pull requests (actions pinned by commit, read-only, no
  secrets). foamy-kit runs it too.
- Sync writes all of these into every plugin, whatever its component set:
  stamped, locked and checked like kit code (INI files take a `#` stamp).
  `kit/native/native.py` and `tests/kit-check.sh` accept the new lock paths.
  A plugin adds `tests/suite.sh` and, when adopting, its baselines.
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
- `process::set_run_budget(budget)` and `process::run_deadline()`: one
  deadline for a helper's whole run. Every `Bounded` child and `Pipeline`
  started afterwards ends by then (each with the shorter of its own timeout
  and the time left); one that would start later is not started and reports
  `timed_out` (status `SIGKILL`, no output). Without a call nothing changes.
  A helper the QML side wraps in `timeout` (FoamyNative.js's example: 30 s)
  sets a budget below it first thing in `main`, as foamy-power did locally:
  `timeout` signals only the helper's own process group, so children whose
  own deadlines added up to more than the wrapper outlived it, grandchildren
  included, and the widget got no reply. Documented in FoamyNative.js,
  `json::run` and the README.

### Changed
- foamy-kit's own Python, QML and shell scripts are formatted with ruff
  format, qmlformat and shfmt (separate commits, no behaviour change);
  qmlformat-displaced end-of-line comments sit above their statement. The
  four unused QML imports qmllint found in kit components are gone
  (FoamyAction, FoamyPopup, FoamyPopupCard, FoamyStyle), as are native.py's unused
  `WORKFLOW` and foamykit.py's unused `verify_file`. Plugins get the
  reformatted kit files on their next sync; their stamped copies change,
  nothing else does.
- `test_sync_check.py` prints a SKIP line instead of failing when
  omarchy-plugin-validate is not installed (CI).
- `foamy-helper` is 0.1.2 (new public API). A plugin that syncs 0.9.0 runs
  `cargo update -p foamy-helper` (in `native/`, or its crate dir) and
  rebuilds; no call site changes.

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
  `storedProblems.<key>` (and block the editor, or offer a confirmed "start
  over" that saves with force), and add the new message to its catalogs if
  it shows `prefs.error`. foamy-teams will (accounts).

- `sync.sh` refreshes the `kit <version>` line of each `native.pin` whose
  binaries are still fresh after the sync (the pin's source hash matches),
  and changes nothing else in it; a stale pin keeps the version that built
  it until the rebuild. `tests/kit-check.sh`, `check.sh` and `--verify` fail
  when a fresh pin names another kit version than `foamy-kit.lock`. Before,
  sync left `kit 0.8.1` in foamy-notification-center's pin after the 0.9.0
  sync, and nothing noticed. After syncing, commit the refreshed pins.

### Fixed
- `Bwrap`'s fd options (`ro_bind_fd`, `bind_fd`, `seccomp`) name the
  builder's retained duplicate, not the caller's fd number. Two temporary
  fds passed one after the other get the same number once the first is
  dropped, so both options named it and the child got only the second file
  (both binds showed it). `Bounded` refuses two inherited fds for one number
  (`InvalidInput`) instead of passing only one. foamy-lock and foamy-github,
  the only users, rebuild their helpers. Found by Codex review on #10.
- `process::exit_on_panic` (and `json::run`, `json::serve`, `favicon::run`,
  which install it) kills the process group of every `Bounded` child still
  running before it exits 101. The hook exits without unwinding (the
  release profile aborts on panic), so no drop killed them, and
  `PR_SET_PDEATHSIG` reaches only the child: a panic mid-run (in a
  `run_with_progress` callback or another thread) left grandchildren
  running. The kit keeps a list of unreaped children for this; a child
  leaves it in the same critical section that reaps it, so a recycled pid is
  never killed.
- `child::Bounded::inherit_fd` and `sandbox::Bwrap`'s fd options
  (`seccomp`, `ro_bind_fd`, `bind_fd`) keep their own duplicate of the fd
  instead of its number, and the child gets the duplicate under the
  original number (`dup2` before exec). Before, an fd closed before the run
  (`.seccomp(BpfFilter::decoder()?.memfd()?)` compiled and closed the memfd
  at once) handed bubblewrap whatever fd took the number next. The calls
  are unchanged (`&OwnedFd` still works). Inheriting fd 0-2 is now
  `InvalidInput` (it used to be a silent no-op), and a duplicate that can't
  be made (`EMFILE`) fails the run.
- `sandbox::Bwrap::seccomp`: the filter memfd is sought back to its start
  in the child before every exec. Bubblewrap reads it from the offset all
  copies share, so a second run with the same memfd or builder (`works()`
  and then the real run) found it at the end and failed closed with a
  misleading "requires a kernel configured with CONFIG_SECCOMP". Runs that
  overlap in time still need a memfd each. The live bubblewrap test now
  checks its second run really ran under the filter.
- `json::run`: a panic in another thread after the reply no longer prints
  a second, `INTERNAL` reply; the helper still exits 101.
- `favicon`: a crafted record header whose column sizes add up past 2^64
  is a broken record instead of a debug-build overflow panic (release
  builds wrapped and rejected it later).
- `lock::FileLock::exclusive_within(path, Duration::MAX)` waits as long as
  it takes instead of panicking on `Instant` overflow.
- Docs: `ExecOnly` says what Landlock's execute right covers (an allowed
  dynamic loader can still run other binaries handed to it); the decoder
  filters deny the classic `mount` call only (not the new mount API, which
  needs privileges the decoder lacks without namespaces); the `net` example
  bounds the connect too and says that DNS and connect are outside
  `DeadlineStream`; a lock file is 0600 only when the lock creates it.
- `child`: `Bounded::timeout(Duration::MAX)` (or a pipeline stage's) no
  longer panics on `Instant` overflow; it means no deadline of its own.
- `favicon` (foamy-notifications, foamy-notification-center): a host's
  icon is now the one its root page (`https://<host>/`) maps to, else the
  one most of its pages map to; size closeness to 32 px and recency only
  break ties. Before, the newest 32 px bitmap of any page won, so one
  hidden sign-out frame (`outlook.office.com/mail/logoutFrame.html`, mapped
  to the Microsoft sign-in logo) replaced Outlook's icon. Checked on copies
  of real Vivaldi caches: outlook.office.com, entra.microsoft.com and
  m365.cloud.microsoft now get their own icons, www.google.com the Google
  G; teams.microsoft.com and github.com are unchanged. Cached icons in
  `~/.cache/foamy/browser-favicons` refresh within a day.
- Shared test helpers that plugins import from the kit checkout, like the
  harness, instead of copying them (three plugins had): `harness/FoamyWait.qml`
  in every run (`waitFor(condition, timeoutMs, then[, label])`, `after(ms,
  then)`: condition-driven steps instead of fixed delays, which flaked under
  load in vitals, bolt and zendesk), `harness.wait_for()` and
  `Run.wait_for_log()` on the Python side, and `preview/hostenv.py`
  (`isolate`, `make` with an `omarchy-shell` that reaches only the test's
  own shell, `calls`, `check`, `fake_helper_plugin`). See README, "Test
  helpers for plugins".
- `hostenv.ProcessGroup(argv, **popen)`: a qs (or service) a test starts
  itself runs as the leader of its own process group; `stop()` (or the end
  of its `with` block) signals the whole group and reaps the leader, so the
  scripts its `Process`es started stop with it. Tests that started qs with
  `subprocess.Popen` and stopped it with `terminate()` left those scripts
  running (foamy-power). `hostenv.die_with_parent()` is the parent-death
  `preexec_fn` the harness uses too.

  Plugins (hostenv comes from the kit checkout, not the sync): a test that
  starts its own qs (power's `integration.py`, the clipboard QML runs,
  notifications' and notification-center's dbus-run-session tests) should
  start it through `hostenv.ProcessGroup`.
- `hostenv.isolate(env, base, session_bus=None, display=False)` no longer
  hands the caller's session bus and display to the test's process. It
  kept `DBUS_SESSION_BUS_ADDRESS`, `WAYLAND_DISPLAY`,
  `HYPRLAND_INSTANCE_SIGNATURE` and `DISPLAY`, so a test run from a
  terminal gave its own qs or `notify-send` the desktop's notification
  daemon and media players, unlike `harness.Run` (its documented model).
  The session bus is now a dead address (also when none was set: an unset
  address falls back to the login bus) unless `session_bus` names the
  test's own, and the display variables leave unless `display=True`.

  Plugins (hostenv comes from the kit checkout): a test that calls
  `isolate()` inside `dbus-run-session` passes
  `session_bus=os.environ["DBUS_SESSION_BUS_ADDRESS"]`: notifications'
  `tests/testhost.py`, notification-center's `stock-runtime.py`,
  `settings-ui.py`, `browser-ui.py`, `motion.py` and `images-ui.py`. One that
  sets `WAYLAND_DISPLAY` before the call to use the live compositor
  (notifications' `features-runtime.py` wayland mode, through `testhost.make`)
  passes `display=True`; github's and bolt's clipboard wayland mode set it
  after the call and need no change. Tests that used the caller's session
  bus (bolt and syncthing clipboard, idle-suspend runtime,
  notification-center `scrolling.py`, `rtl-rows.py`, `settings-number.py`)
  now get a dead one; one that needs a bus runs under `dbus-run-session`.
  An offscreen qs needs `QT_QPA_PLATFORMTHEME` set (`basic`): without a
  display the desktop's `gtk3` theme stops it.
- Live-desktop use in tests is the user's opt-in: `hostenv.isolate(display=True)`
  raises RuntimeError, and `harness.Run.start()` refuses a `run.env` with
  `WAYLAND_DISPLAY`, `HYPRLAND_INSTANCE_SIGNATURE` or `DISPLAY` put back,
  unless `FOAMY_TEST_DESKTOP=1` is set. Plugin tests put real surfaces on
  the user's desktop during validate runs. `hostenv.desktop_problem(env,
  what)` gives the same verdict for a test's own checks. README "Test
  helpers" and REVIEW.md section 6 state the rule: tests never show anything
  on the live desktop unless the user opts in.

  Plugins (hostenv comes from the kit checkout): the clipboard wayland modes
  of bolt, github and weather (`display=True`) now need
  `FOAMY_TEST_DESKTOP=1` as well as their platform switch. A test that puts
  `WAYLAND_DISPLAY` into its environment itself after `isolate()`
  (syncthing's clipboard wayland mode) checks
  `hostenv.desktop_problem(env, …)` before it starts qs, or passes
  `display=True` instead. notifications' own `desktop_opt_in()` gate can
  rely on the kit's.
- `preview/fake_nm.py`: a shared stand-in NetworkManager for the run's
  private system bus (from foamy-github's `tests/fake_nm.py`): no devices,
  the connectivity a state file names (`set_connectivity(file, value)`,
  written atomically), PropertiesChanged on a change. `fake_nm.start(address,
  state)` returns its `hostenv.ProcessGroup` once it owns the name, or raises
  with its output. `harness.Run.start_buses()` brings the private buses up
  before qs: Quickshell looks for NetworkManager only once, when it starts,
  so a fake started after qs (as github's `runtime-lifecycle.py` does) leaves
  `Networking` with "Could not find an available backend".

  Plugins: github replaces `tests/fake_nm.py` with the kit's and starts it
  between `run.start_buses()` and `run.start()`; weather and train, whose
  runtime tests assume offline because the system bus is dead, can test the
  online and offline paths with it.
- `fake_nm`: an empty, unreadable or invalid state file keeps the
  connectivity the service reports; only a missing file means full. It read
  all of them as full, so a test that wrote the file in place (truncate, then
  write) could look online for a moment (the weather sync). `connectivity()`
  takes the last value as a second argument. `set_connectivity()` writes a
  unique temporary file and renames it (it used a fixed `.partial` name).

  Plugins: write the state file with `fake_nm.set_connectivity()`.
- Docs: README "Test helpers": the fake NetworkManager changes only what
  the shell sees; it does not cut a helper off from the Internet. Plugins
  point their helpers at a loopback stand-in and fail a test on any outside
  request (found in the weather sync).
- `hostenv.clipboard_fakes(folder)`: the load-proof stand-ins for
  `kit/clipboard.sh` tests, from foamy-media's f7de0ac: a bash-builtin
  `wl-paste`/`clipboard-fixture` and a `timeout` that keeps the real 2 s for
  the deadline modes and gives a paste that ends by itself 60 s.
  clipboard.sh's fixed 2 s for the whole six-process paste made every
  plugin's copied clipboard tests fail under load (media: 6 of 12 runs at
  load 36-50); its runtime behaviour is unchanged and it has no test switch.
  `tests/test_clipboard.py` is the kit's first test of clipboard.sh (shell
  only, so `tests/suite.sh --ci` runs it).

  Plugins (hostenv comes from the kit checkout): bolt, github, media,
  syncthing and weather replace the wl-paste mock in their
  `tests/test_clipboard.py` with `hostenv.clipboard_fakes()` (media already
  has the same stand-ins) and wait as long as a working paste may take
  (media's `pasteWait`, 60 s) in their QML case.
- `foamy-kit.lock`'s `source` line is the full id of the kit commit sync
  copied from (it was a 12-character abbreviation), and sync rewrites it
  whenever the kit commit changed, even when every file is already current
  (it used to keep the old line then, so `source` could name an older kit
  than the one the plugin was last synced from). `+dirty` still marks
  uncommitted kit changes.
- `checks.yml` checks foamy-kit out at the lock's `source` commit and exports
  `FOAMY_KIT` for `tests/validate.sh --ci`. The kit's test helpers
  (`hostenv.clipboard_fakes()`) and design lint are not synced, and the
  runner had no kit checkout: since bolt, github, media, syncthing and
  weather moved their clipboard mocks to hostenv, their clipboard shell cases
  skipped in CI, and design-lint always skipped there. The step fetches over
  public https into `$RUNNER_TEMP` (outside the checkout), keeps the job
  read-only and fails, before validate, when `source` is not a full commit
  id or github.com does not have that commit yet. Under `--ci`, design-lint's
  SKIP now says `FOAMY_KIT is unset` (it said "no foamy-kit checkout"), and
  a `FOAMY_KIT` that is not a kit checkout fails instead of skipping.

  Plugins: re-sync (`./sync.sh ../foamy-*`) from a committed foamy-kit that
  is pushed to github.com, and commit `checks.yml` and `foamy-kit.lock`
  together; push the kit before the plugin, or the job fails at the kit
  checkout. Until the re-sync, the old `checks.yml` keeps skipping those
  cases. Later kit commits change `source` on the next sync: commit the lock
  with it. The design lint now runs in CI, so `check.sh <plugin>` must pass
  there too.
- Docs: `FoamyText.tooltip()`'s comment asks for one item per line (a
  list joined into one line loses whole items past 100 characters). README:
  the preview contract is `readonly property var popup: previewPopup` with
  `id: previewPopup` (qmllint types FoamyPopup as the host's PanelWindow, and
  the id `popup` shadowed the property: id-shadows-member twice and
  incompatible-type in every plugin's Preview.qml; the render is the same);
  `FileView.setText()` writes asynchronously, so a test waits for the file;
  a `tests/suite.sh` example runs a clipboard test's shell cases under
  `--ci`, where only its QML case needs skipping.

  After syncing: rename the FoamyPopup id in `preview/Preview.qml` and type
  `popup` `var`, then shrink the qmllint baseline (`tests/validate.sh
  --update-baseline qmllint`, review the diff). Reads of `popup.…` then
  reach the root property: in a child object (a Timer) qualify them as
  `preview.popup.…` (unqualified, they are new `unqualified` entries); on
  the root's own bindings either form is clean; inside the `body` Component
  leave them as they are, since qmllint reports every outer read there and
  the baselined line still matches (README, "Preview").
- `render.py --language` names a catalog the plugin has. `--language nb` on
  a plugin whose catalog is `no.json` (Omarchy's Norwegian code; there is
  no `nb`) rendered English without a word; it now renders `no` and says
  so. A language with no catalog (nor its base language's) stops the render
  with the catalogs it has, before qs starts.
- `preview/i18n_runtime.py <plugin>`: one catalog check for every plugin,
  replacing the 13 `tests/i18n-runtime.py` copies (12 different variants of
  the same template: a translated key switching no → da/ar → en live, the
  English fallback, literal values, one plugin-specific plural). It derives
  every expectation from the plugin's own catalogs (a translated string, a
  plural entry's `one` form, right-to-left under Arabic), runs under the
  isolated harness and waits on conditions, not fixed ticks. After syncing,
  replace `tests/i18n-runtime.py` with `python3 "$FOAMY_KIT/preview/i18n_runtime.py" .`
  (foamy-notifications keeps its card checks).
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
- `kit/FoamyI18nText.js` (part of FoamyI18n, with `node-loader.cjs`):
  FoamyI18n's value substitution, which the singleton now calls, and
  `translator(catalog, english, number)` (`t`/`tn` over plain catalogs:
  the language, English, the key) for node tests. Thirteen plugins'
  `tests/i18n.cjs` evaluated slices of `FoamyI18n.qml`'s source in a vm, eight
  of them through the 4.0 English fallback removed below. After syncing,
  replace that slicing with
  `require("../kit/node-loader.cjs").load("FoamyI18nText").translator(no, en)`
  (or `.substitute(text, values)`); until then those node tests fail.
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
- `FoamyPrefsQueue` reads `settings` through a plain JSON copy
  (`storedSettings`, `FoamyPrefs.plain()`). A list that reaches the queue
  as a QML sequence wrapper (settings passed through `createObject`, as the
  bar and plugin tests do) fails `Array.isArray`, so it read as an invalid
  stored array: the setting showed its default, `storedProblem()` named it
  and, with the stored-array rule above, every save of it was refused
  (foamy-github). A reflected wrapper also never settled its pending value.
  An invalid stored array is still refused. Code that calls `FoamyPrefs.js`
  directly passes `Prefs.plain(settings)` the same way.

  After syncing: a plugin's own JSON copy in front of the queue
  (foamy-github's `settings: JSON.parse(JSON.stringify(root.settings || {}))`)
  is redundant and can go.
- `preview/harness.py`: each run's runtime dir (`XDG_RUNTIME_DIR`) and its
  private bus sockets live in a short socket dir, `Run.sockets`
  (`foamy-kit-s-<pid>-<random>`, in the temp dir when it fits, else
  `/tmp`), removed with the run and found by `--gc`. A long `TMPDIR` plus
  the run prefix put qs's IPC socket past the 107-byte unix limit: qs only
  logged "Failed to start IPC server", `qs ipc` found no instance and the
  private bus never came up (six plugins' agents hit it).
  "Failed to start IPC server" is a `FAILURE_MARKERS` entry, and
  `Run.start()` stops with the reason when a test's `XDG_RUNTIME_DIR` would
  still be too long. Plugin tests that read `run.env["XDG_RUNTIME_DIR"]`
  need no change; one that built `run.base / "runtime"` or
  `run.base / "bus"` reads `run.sockets` (or the env) instead.
- `harness.Run.start()` stops with the reason when a test's
  `run.env["PATH"]` would let a host command run: the harness's
  `host-bin` stubs are gone (PATH rebuilt from `os.environ`), a directory
  holding a host `omarchy*` command (`/usr/bin` has `omarchy-shell`,
  `~/.local/bin` a wrapper) comes before them, or an Omarchy bin directory is
  back. The isolation only held while the stubs came first, and nothing
  said when a test dropped them (tray and monitor reviews).

  After syncing: foamy-menu's `tests/runtime.py` sets
  `PATH=f"{stubs}:{os.environ['PATH']}"`, which `start()` now refuses;
  it puts its stubs in front of `run.env['PATH']` instead.

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
  `fullScreenBar` property is now ignored, kept so tests that set it load) and the kit tests drop the 4.0 strip bar
  window. `--trio` renders Before on 4.5 only (`--before-host` and
  `trio(before_hosts=…)` are gone) and labels a clipped fork or a dev tree
  that won't render.

  After syncing: drop each plugin test's 4.0 cases (`--host 4.0|both`
  choices, `FOAMY_HOST_40` checks, `("4.0", …)` case lists,
  `harness.HOSTS["4.0"]`); until then a listed 4.0 prints SKIP, and a test
  that calls `harness.Run("4.0")` itself stops with the message above. A
  node test that evaluated `FoamyI18n.qml`'s source (`tests/i18n.cjs`) moves
  to `FoamyI18nText.js` (see Added).

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
