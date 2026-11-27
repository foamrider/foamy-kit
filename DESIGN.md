# Foamy design spec

Foamy plugins match **each other**, not stock Omarchy: one foamy look across all
of them. They follow the Omarchy 4.5 **UX rules** (motion, keyboard, RTL, lazy
content, IPC). Everything below is implemented in `kit/`; a plugin uses the kit
component instead of restating the rule. `check.sh` lints the rules marked *(lint)*.

## Tokens (`FoamyStyle`, `FoamyPalette`, `FoamyMotion`)

| Area | Token | Value |
|---|---|---|
| Radius | `FoamyStyle.radius` | `Style.cornerRadius * 2` on surfaces, rows, inputs, buttons. `radiusSmall` (= Hyprland rounding) for nested chips. Pills via `pillRadius(h)`, only when `rounded`. Never write `cornerRadius * 2` yourself *(lint)* |
| Popup border | `FoamyStyle.popupBorderSpec` | 1px `alpha(popups.text, 0.15)` (`FoamyPalette.border`) |
| Body font | `FoamyStyle.fontFamily` | `"Adwaita Sans"` (package `adwaita-fonts`) when installed, for its real semi-bold: `Font.DemiBold` draws at 600, not Bold; without it the system `"sans-serif"`. Never a literal family *(lint: `"sans-serif"`)*. `monoFamily` (the Omarchy font) for numbers, code, glyphs |
| Type scale | `FoamyStyle.font.*` | caption 10, bodySmall 11, body 12, subtitle 13, title 14, heading 16, iconLarge 18, display 24, displayLarge 28 (all `Style.space(n)`). Hero numbers (clock face, temperature, volume, countdown): `numeral` 56, `numeralCompact` 40, their unit in `display`. No other sizes |
| Widths | `popupWidth` / `popupWidthWide` | 420 standard; 560 for data-dense panels (vitals, weather, monitor). The settings page uses the same width. Menus: `menuWidth` 232, `menuPadding` 8 |
| Heights | FoamyPopup / FoamyPopupCard | The card fits its content up to the screen's **available height** (screen minus the bar, the gap and a margin; the host measures it from the bar thickness), so content fits where the screen allows and scrolls only beyond. `maxHeight` caps it lower when a panel wants that (`popupMaxHeight` 640 is the old cap). Never a fixed height |
| Spacing | `padding` 20, `gapTiny` 2, `gapSmall` 4, `gap` 8, `gapLarge` 12, `sectionGap` 14, `rowPadding` 10, `rowHeight` 36 | Popup card padding is 0; content insets by `padding` so lists scroll edge to edge |
| Controls | `controlHeight` 32, `actionSize` 28, `iconSize` 15, `settingsButtonSize` 32, `settingsIconSize` 16, `iconStroke` 1.7 | |
| Colours | `Commons.Color.*` | Always qualified *(lint)*: on Qt 6.12 (installed) a bare `Color.popups` is `undefined` |
| Text tones | `FoamyPalette.text`, `secondaryText` (tint .72; in a light theme the lightest tint from .72 up with 5.5:1 on the surface, at most .95), `mutedText` (tint .55; in a light theme the lightest from .55 up with 4.5:1, at most .84) | Meta/section labels secondary; hints and empty states muted |
| Fills | `hoverFill` .08, `fieldFill` .055, `selectedFill` accent .18, `divider` .12 | |
| Status | `FoamyPalette.warning/success/error/info` | Theme `yellow/green/red/cyan` from colors.toml, falling back to `urgent`/`accent`. No hex literals outside FoamyPalette *(lint)*. For text and thin marks (rings, icons) on the surface use `onSurface(c)` (`onSurface(c, fill)` on a tinted fill; with a fill that comes and goes, such as hover or press, the strongest one, so the colour stays the same in every state): it darkens on a light surface or lightens on a dark one (the end, black or white, with more contrast on that surface, whatever the theme) in the smallest step that reaches 4.5:1, keeping the hue as long as it can (a colour near black on a dark surface, or one on a mid grey, mixes toward that end), so it always reads at 4.5:1; a colour that already reads is unchanged. Large fills (bars) keep the raw colour. Menus: `menuFill`, `menuBorder` (light: a lighter fill and a text .40 edge); raised menus `raisedMenuFill` |
| Disabled | `FoamyStyle.disabledOpacity` .45 | `FoamyButton` does not fade: inert and disabled draw the kind's fill at .7 and .45 of its alpha (still see-through), with a label that reads at 4.5:1 (inert) and 3:1 (disabled) on it over the popup background |
| Motion | `FoamyMotion.hover` 100, `press` 160, `toggle` 120, `slider` 140, `fadeIn` 180, `fadeOut` 120, `grow` 200, `morph` 220, `slow` 300; `duration(ms)` | Every `duration:` goes through FoamyMotion *(lint)*. 0 under reduced motion |

## Components

- **Popup**: `FoamyPopup` (stock `KeyboardPanel` + foamy surface) for bar-widget
  panels; `FoamyPopupCard` (stock `PopupCard`) for menus. Content goes in
  `body: Component { … }` (built on first open). Never fork KeyboardPanel, never
  override `borderSpec`/`padding`/radius per plugin. Layer namespace stays
  `omarchy-keyboard-panel`. Always set `owner: root` so closing goes through
  the panel (without it the stock close() assigns over your `open:` binding).
- **Hero band** (`FoamyHeroBand`): every foamy popup starts with one band — the
  foamy header area. Rules:
  - First item of the popup body, x 0, full body width: it bleeds to the card
    border and its top corners follow the popup radius (`FoamyStyle.bandRadius`).
  - Surface: the popup background tinted toward the accent, a diagonal wash
    (`FoamyPalette.bandFill` → `bandFillEnd`) with a soft glow at the trailing
    top corner (`bandGlow`), drawn by the kit in any renderer, dark and light.
    No hex, no MultiEffect, no motion. Bottom: a hairline (`bandEdge`) into the
    body, which continues on the plain popup surface. When the band ends the
    card (empty states, band-only popups) it rounds its bottom corners and
    drops the hairline by itself; never add spacers under it.
  - Compact: padding top/bottom 16 (`bandPaddingTop/Bottom`), 20 at the sides,
    14 between the title row and the hero. The title row is FoamyHeader's:
    icon 18, title (title, DemiBold), meta (bodySmall, secondary), trailing
    actions, settings button (tooltip "Settings"). A brand mark with no Lucide
    icon (Teams) uses `iconGlyph` (a Nerd Font glyph written as an escape, in the
    mono font by default) instead of `iconName`, same size and tint.
  - **Hero slot**: use it when the panel is about one state or value the user
    opens it for — a ring and status (power), the volume (audio), the next
    departure (train), sky and temperature (weather), artwork (media), the
    clock face (clock), a host line (vitals), a sync summary (syncthing), the
    unread count (notification center), a repository summary (github). Keep it
    compact: numerals in `font.numeral`/`numeralCompact`, rings ≤ 96 px, one or
    two lines of context. Full-width hero items set `Layout.fillWidth: true`.
  - **Title only**: list and manager panels where every row is equal (bolt,
    monitor, teams): the band holds just the title row.
  - **Own picture**: `imageSource` for artwork (cover-fitted and clipped by the
    band; it holds one picture at a time and drops it while the popup is
    closed — clear the source when the artwork goes away) or `background: Component` for a scene (weather sky; it must keep to
    the rounded top using `topRadius`). Same geometry and text treatment; a
    readability scrim is drawn over pictures.
  - Settings pages show the compact band (back, "Settings", "Saving…");
    `FoamySettingsPage` does it. A sub-view built like a settings page (an
    editor page) uses the same band, with its icon actions at the end
    (`compactTrailing`). When its title is something the user changes (an
    editor page's place), the title is the control: `compactTitleAction`
    (a FoamyTitleAction: a mark, the title, a chevron; a click, Enter or
    Space opens its menu, hung from `compactTitleMenuAnchor`), not a second
    row saying the same.
  - No band on menus (`FoamyPopupCard`) or toasts.
  - **Field mode** (search, quick add): a text field grows out of the header
    action that opens it, across the title row (`field`, `fieldOrigin`,
    `fieldOpen`), while the title row and the buttons fade out; closing
    reverses it. One field at a time: search and quick add share the band's
    one field. The band's height is fixed: the field lies over the title
    row, and the hero and the list under the band never move. "+" sits
    left of Search (declare it first in `trailing`; RTL mirrors it). While
    the field is open the buttons are inert and out of the cursor
    (`buttonsActive`); the panel owns the keys (Esc closes, the focus goes
    back to the key catcher). Closing, the field is inert at once and drops
    the focus. Field mode is for bands with a title row: a centred band
    ignores `fieldOpen`. A wide panel whose columns make a full-width field
    a slab (a rail, a list, a pane) gives it a slot (`fieldX`,
    `fieldWidth`: the list column): the title stays over the rail, cut
    before the field, and the buttons stay over the pane, usable while the
    field is open (+ gives the keys back to the field). What hangs from
    the field places itself by `fieldRect`.
  - **Centred** (`centered: true`): for a panel about one big value read at a
    glance (clock: the time; weather: the temperature and sky). No title icon;
    the hero comes first, centred (give hero items `Layout.alignment:
    Qt.AlignHCenter`), the title and meta centred under it; the buttons stay
    pinned to the trailing top corner and the centred content keeps the same
    distance from both sides, clear of them.
- **Header row only** (`FoamyHeader`): inside the band; standalone only where a
  band can't sit (a sub-view header inside the body).
- **Header buttons: at most three on the top right** (FoamyHeader/FoamyHeroBand
  do it). Declare `trailing` actions in priority order, most important first;
  extra entries go in `menuItems` (FoamyMenuItem). When the actions, Settings
  and a menu don't fit in three, a ⋯ button ("More options") takes the last
  slot and its menu holds the actions that didn't fit, then `menuItems`, then a
  separator and **Settings, always last**. With menu items and room to spare,
  ⋯ sits beside Settings. Every menu entry has an icon.
  - **Settings in the menu**: a panel whose header keeps one action plus a
    state toggle that is not an everyday action (Snooze in train and zendesk)
    puts the toggle in `menuItems` and sets `maxButtons: 2`, so Settings moves
    into the ⋯ menu and the row shows the action and ⋯. The toggle is one
    entry whose text and icon say what it will do now (moon "Snooze until
    tomorrow"; sun "Stop snoozing" / "Resume now"), not a checked state.
    Settings stays reachable with `s` and right-click; the ⋯ button is the
    Settings cursor stop (`settingsHasCursor` and `menuHasCursor` on the same
    stop, Enter calls `openMenu(true)` while `settingsInMenu`), and the key
    catcher is `blocked` while `menuOpen`.
- **Menus** (`FoamyMenu`, the ⋯ menu): an overlay inside the popup card, never a
  separate window or a Controls.Menu positioned by hand. It drops from the
  button, its trailing edge on the button's trailing edge (mirrored in RTL),
  stays inside the card (opens above when there is no room below, scrolls
  when long). Only when it fits neither below nor above does the card grow
  while it is open, by at most `maxGrowHeight` (9 rows) of menu. From the
  keys it starts on the one checked entry (the current choice of a set:
  `checked` means that), else on the first. Text on a tinted fill:
  `onSurface(c, fill)`. Entries: icon `iconSize`, label `body`, row `rowHeight`;
  destructive entries tint urgent under the cursor; a submenu opens in place
  with a Back row. While open it has the keys and the pointer (one cursor:
  arrows/jk, Enter/Space/→ activate, ←/Backspace back, Esc back or close, a
  press outside closes); focus returns where it was. A menu or list that
  hangs over busy content (rows, a tab row) is **raised**: `FoamyMenu.raised`,
  or for a list of your own `FoamyPalette.raisedMenuFill` with `menuBorder`
  over a `FoamyShadow` (the shadow is drawn without effects, so it shows
  under the software renderer too). A list that hangs from a field (Quick
  Add suggestions, the field's error) starts `gapSmall` under it.
- **Rows**: `FoamyCursorSurface` (stock CursorSurface, foamy radius), insets
  `gapLarge`, icon `iconSize`, name `body`, detail `caption` secondary.
- **Actions**: `FoamyAction` (28, icon 15, hover fill, tooltip). Settings button =
  `settings: true` (32/16). Destructive: `destructive: true`. Spinners only via
  `spinning`. Icon actions are for toolbars (header, footer, rows).
- **Title actions**: `FoamyTitleAction` where a title names what the user
  changes from a menu (an editor's place, in the compact band or a pane's
  header): mark, text, chevron, hover fill, the keys' ring; Enter or Space
  opens the menu from its start (`menuAnchor`). It gives way first: the
  header's fixed actions keep their room, its text ends with "…" and shows
  on hover in a tooltip (up to 3 lines of 200 characters, cut with "…"),
  and the mark and chevron stay inside its box.
- **Buttons**: `FoamyButton` for form actions (Verify, Apply, Remove, Add): a
  filled or bordered surface that reads as a button — `secondary` (default,
  field fill + border), `primary` (accent fill, at most one per form),
  `destructive` (urgent tint + border); label `body`, optional icon, height
  `controlHeight`, `busy` spins. Never a bare text or a FoamyAction label for a
  form action. Not active, a button stays readable: inert (`actionEnabled:
  false`) at 4.5:1, disabled (`enabled: false`) at 3:1, each weaker than the
  one before. A dark-ink primary in a dark theme keeps its ink when inert
  (the fill steps up to at most .8 for it) and mostly takes the text's ink
  when disabled; a primary in a light theme, or with an accent that reads
  weakly on the background, turns to a pale accent with the text's ink. A
  change between active, inert and disabled shows its fill and label at
  once; hover, press and a change to or from busy animate. Nothing inside a button fades with it: content a button draws
  itself takes `foreground`.
- **Footer**: `FoamyPanelFooter` when a panel shows where its data comes from or
  how fresh it is: hairline, the source or a leading action ("Calendar") on the
  reading start, "Updated …" (bodySmall, secondary) and the refresh action on
  the end, spinning while loading. Freshness and refresh live there, not in the
  header. The row is centred between the hairline and the popup's bottom edge
  (the same gap above and below; the footer is last, with no padding under it).
  foamy-clock's footer is the reference. The age is
  `FoamyI18n.updatedAgo(ms, now)` (just now, minutes, hours, days); while a
  refresh replaces data older than its interval, the status reads "Updating…".
- **Help**: a short label may have a tooltip; anything longer is a
  `FoamyInfoNote` — an (i) beside the heading that opens an inline note under
  it (bodySmall, secondary, wrapped, subtle rounded surface, the column's
  width). In settings: `FoamySettingsSection { info: … }`; with the note closed
  the title line is as tall as a plain section title (the (i) overhangs it),
  so the title → description gap is the same in every section.
- **Icons**: `FoamyIcon` (Lucide superset, 125 names). Add icons to the kit
  (tools/update-icons.py), not to plugins; no Nerd-font glyphs in popups.
- **Inputs**: `SafeTextField` (never Qt's TextField: it reads the whole clipboard).
  Callers set size/alignment, never `background`. Text edited in place, where
  it reads as text (an editor's task title or description), sets `quiet:
  true`: no fill or border at rest, the usual field on hover, under the
  cursor and with the focus. Secrets (API tokens,
  passwords) use `masked: true` and read `secretText`, never `text`. Label
  the field with visible text and set its `Accessible.name`: Qt gives a
  password edit no accessible name, so the field passes the name on as the
  editor's description.
  Coloured tokens in a field (Quick Add) use its `runs`. Multi-line text
  (a description) is `SafeTextArea`, for the same clipboard reason.
- **Choices**: `FoamyDropdown`, with `value` bound to the setting and the save in
  `onChanged`; it never assigns `value` itself. When a save fails without
  changing `value`, call its `saveFailed()` so it shows the saved choice
  again at once; when saves end one by one, pass the pick's serial from
  `changed(value, serial)` (`saveFailed(serial)`), so a newer pick stays
  on show. With `FoamyPrefsQueue`, link the dropdown instead (`queue:
  prefs; queueKey: "mode"`): it then gives way by itself when the queue
  refuses the pick's save, whatever value `onChanged` saves for the option,
  whether `save()` refuses the pick (it returns false: a
  value the schema rejects, a kept invalid stored array, a widget with no
  bar entry) or a queued pick is refused as it runs (`failed()`); a CLI
  save that fails later rolls `value` back and needs nothing. **Toggles**: `FoamyToggle`
  (`checked` bound, save in `onClicked`).
- **Tab row** (`FoamyTabs`): a few views of one panel (Inbox / Today /
  Upcoming), at the top of the popup body directly under the hero band, the
  body's full width (never in the hero slot). Height `controlHeight + gap`;
  tabs as wide as their content from the reading start, inset `gapLarge`
  and padded `rowPadding`, so the first icon lines up with the rows'
  content below. Each tab: icon `iconSize`, label `body`, optional count
  (mono `bodySmall`). Open: label `text` DemiBold, icon and count in the
  accent, a 2px accent underline across the tab on the row's 1px `divider`
  hairline (the row draws the hairline). Others: `secondaryText`, counts
  too; an urgent count is `error`, readable on the cursor's fill. The cursor is a
  `hoverFill` with `radius` behind the tab; nothing moves. Labels elide from
  the last tab inward; icons and counts never clip; it never scrolls and
  has no overflow menu, so keep the labels short. Bind `value`, change it
  in `onActivated`. One cursor stop: ←/→ move between tabs, Enter activates
  (the file header shows the key catcher wiring). Settings choices stay
  `FoamyDropdown`. One exception: a footer row that switches the popup's
  source and shows each source's brand glyph (foamy-media's Spotify and
  YouTube tabs, with the glyph and the equalizer, which FoamyTabs cannot
  draw). It keeps the rules screen readers and the keyboard need: the row
  is an `Accessible.PageTabList`, each tab an `Accessible.PageTab` with
  `Accessible.selected` on the open one, and each tab is one stop of the
  panel cursor (←/→ along the row, Enter activates). Every other tab row is
  `FoamyTabs`.
- **Short values use the row form** (settings): any control whose value is
  short (a number, an enum choice, an interval, a count, a percentage) is one
  row: label (subtitle, normal weight) and an optional `description`
  (bodySmall, secondary) on the reading start, a small control on the end.
  `FoamyToggle`, `FoamyNumberField { compact: true }` and
  `FoamyDropdown { compact: true }` share the row height
  (`rowHeight + gapSmall`, taller only when the text wraps) and the trailing
  edge (the switch, the dropdown, the number field's end-aligned unit), so a
  page mixing them reads as one list. The compact dropdown is as wide as its
  widest option plus the chevron, at most half the row (it elides beyond; the
  open list may be wider). Full width with the label above is **only** for
  free text (`FoamyTextSettingField`), paths, URLs, commands and choices whose
  option labels don't fit in half the row (window app IDs, "Accept {folder}
  from {device}"), and for controls inside a composite row (a folder row's
  depth dropdown, a weekday's time fields). Never hand-roll a label + control
  RowLayout for this. Where it applies — a sweep checklist:
  - every `FoamyDropdown` in a settings page whose options are a short enum or
    interval ("Refresh every", "Fetch remotes every", "Mouse wheel", "Accent",
    "Layout", "Time format", "Week starts on", "Group … by", power profiles,
    "Outside the schedule", "Show in the bar") → `compact: true`;
  - every `FoamyNumberField` in a settings page (days, counts, seconds, %,
    px, °C) → `compact: true`; put the unit in `unit` ("days", "s", "%"),
    not in the label ("Keep notifications (days)" → label "Keep
    notifications", `unit: FoamyI18n.t("days")`);
  - every plugin-local RowLayout of a label `Text` and a `showLabel: false`
    dropdown or a narrow field → the kit row form;
  - leave full width: `FoamyTextSettingField` / `SafeTextField` for free text,
    paths, URLs, commands, search boxes; dropdowns with long option labels.
- **Settings rows are plain rows, never boxed cards**: a toggle row is the label
  (subtitle, normal weight) and an optional description (bodySmall, secondary)
  on the reading start, the switch on the end, at least `rowHeight + gapSmall`
  tall; hover/cursor shows a soft fill, Tab focus an accent ring. At most a
  hairline between rows (`divider: true`), no border around each row.
- **Numbers and text in settings**: `FoamyNumberField` / `FoamyTextSettingField`
  (bound `value`, save in `onCommitted`). Never hand-roll a row that assigns `text`.
  When a save fails, call the field's `saveFailed()` (from FoamyPrefsQueue
  `onFailed`) so it shows the saved value and the same input can be retried.
  Units are short symbols ("%", "°C", "ms") in the fixed unit column, so a
  section's fields line up; a unitless field among them sets `reserveUnit`.
  Short values (a 2–3 digit percentage, a °C margin) use the **compact** form
  (`compact: true`): label on the reading start, a narrow field sized to the
  longest value, the unit after it, end-aligned in a narrow column
  (`unitWidthCompact`), one row; never a full-width input for two digits.
- **Controlled values**: kit controls never assign over a caller's binding.
  Bind `value`/`checked`/`open` to state and change the state in handlers.
  (Text fields are the exception every toolkit has: typing edits `text`;
  write back in `onTextEdited`, reset by assigning.)
- **Settings page**: `FoamySettingsPage` (back, "Settings", "Saving…", error +
  Retry, sections). Sections: `FoamySettingsSection`, sentence-case titles.
  A page wider than the settings width (a Wide popup's) reads as one
  column: set `columnWidth`; Back and the title, the error line and the
  sections keep to the centred column, the band still runs to the card's
  edges.
- **Scrolling**: every scrolling list or page takes a wheel notch as a normal
  step (~3 rows: `wheelScrollLines` × `rowHeight`), however the mouse splits it,
  and touchpad pixel deltas 1:1. FoamySettingsPage does it; a plugin Flickable
  or ListView adds `FoamyWheelScroll { target: list }`. Qt's own Flickable
  loses most of a high-resolution notch (a few px per notch). When a section
  expands, call `ensureVisible(section)` (the page's or the FoamyWheelScroll's)
  so the new content scrolls into view.
- **Click-away**: a click on space that does nothing (the popup body's empty
  area, a list's space below or between its rows, a settings page's empty
  space) takes the keys from a focused text field, which ends its edit, and
  gives them back to the panel's key catcher (FoamyPopup's `focusTarget`;
  a settings page or an editor page keeps them: `foamyKeyHome`).
  `FoamyClickAway` does it; FoamyPopup and FoamyWheelScroll put it in by
  themselves, so a plugin adds nothing. A focused text field that hides
  gives the keys to the same key home (the nearest one that shows). A list that reacts to a click on
  its empty space (clearing a selection) uses `FoamyWheelScroll.spaceClicked`.
  Whether it shows: `FoamySettingsState` (`show()` opens the popup on
  Settings; resets on close, never on open). When Settings hides (Back, or
  the reset on close), FoamyPopup gives the keys the page had back to the
  body's key home, so Esc and the arrows work at once and after the next
  open; a plugin needs no `onHidden` refocus, and its own still wins. An
  item on the page that hides while the page shows (Retry, as the retry
  starts) leaves the keys with the page, so Esc still goes back.
- **Empty / loading / error**: one line, bodySmall, `mutedText`, word-wrapped; no
  period for short states ("No devices", "Scanning…"); errors in
  `FoamyPalette.onSurface(FoamyPalette.error)` (the raw red does not read in
  every theme) with `Accessible.AlertMessage`, plus "Retry" when the action can be retried.

## UX rules (4.5, mandatory)

- **Motion**: durations through FoamyMotion. Every looping animation runs only
  while shown and `!FoamyMotion.reduceMotion` *(lint)*. Nothing over 300 ms
  except loop periods.
- **Sliders**: the cursor on a slider highlights its thumb and track (a ring on
  the thumb, the accent track), never a filled row background behind it.
- **Tooltips**: only for short labels (an icon's name, a shortcut, a value
  that doesn't fit). A sentence of help or more goes in a FoamyInfoNote; a
  tooltip never wraps a paragraph or spans the screen.
- **Keyboard**: one cursor. Wrap popup content in `PanelKeyCatcher`; keep the
  cursor in `FoamyCursor`; arrows/hjkl move, Enter/Space activate, Esc closes
  (or leaves Settings), Tab/Shift-Tab call `switchPanel(direction)`, `s` opens
  Settings, `r` refreshes where there is a refresh. Pointer hover moves the same
  cursor (one highlight on screen). Where the keys moved it, it has a 1 px
  accent border (`FoamyCursor.byKeys` into `FoamyCursorSurface.byKeys` and
  the `cursorByKeys` of every other control that takes the cursor:
  FoamyAction, FoamyButton, FoamyTabs, FoamyToggle, FoamyDropdown, the text
  and number fields; set `byKeys` when a key handler sets `index` itself);
  on a primary button the border is the text or the background colour,
  whichever reads better on the fill inside it (at least 3:1). It
  is the control's own outline and never changes its size, and an inert or
  disabled control shows it too (with no hover fill). FoamyHeader,
  FoamyHeroBand, FoamyPanelFooter and FoamyInfoNote pass their
  `cursorByKeys` on to their own buttons (⋯, Settings, refresh, the (i));
  bind it once on each. While the look is on, a real pointer move inside
  a control reports the pointer again, as entering does, so the same
  hover wiring takes the cursor back; items moving under a still pointer
  (a keys-driven scroll) are no move. The selected row or view (`current`)
  has `selectedFill`, with `currentBar` when its details show in a pane.
  Focus rings only on form controls in
  Settings (`focusable: true`); a primary button's ring is, as its keys'
  border, the text or the background colour, whichever reads better on
  the fill inside it; set `blocked` on the key catcher while a form
  or editor owns keys, and while a menu is open (`band.menuOpen`). The ⋯
  button is a cursor stop (`menuHasCursor`, `menuHovered`); Enter opens the
  menu with `openMenu(true)`.
- **RTL**: FoamyPopup/FoamyPopupCard/FoamySettingsPage mirror; place things
  with anchors/rows, not `x` arithmetic; directional icons mirror via FoamyIcon.
- **Lazy content**: popup content in `body`; nothing polls or ticks for the UI
  while hidden. Data that must exist while closed lives outside the body.
- **Once per shell**: 4.5 draws a bar per monitor. Pollers, helpers and IPC
  run in the leader only (`FoamyMember`), state lives in a plugin `pragma
  Singleton`; open popups raise demand.
- **IPC**: `FoamyIpc` only *(lint: no raw `IpcHandler`/`ShellIpc`)*, `enabled:
  member.isLeader`.
  A target shared with another service: `FoamyIpcPreference` (keep its poll
  on; it is the only guard against a later service taking the route). Calling another
  plugin: `FoamyPeerIpc` (never read its files or run its scripts).
- **Settings**: save through `FoamyPrefsQueue` (inline `updateEntryInline`,
  else the CLI; serialised, newest value per key, never merging over a stale
  entry). Arrays/objects are schema types (`array`, `object` + `validate`).
  Never a hand-built `setBarWidget` call or a plugin-local save queue.
- **Letter shortcuts**: `onTextKey: function(text, modifiers)` and skip unless
  `cursor.plain(modifiers)`. Tests emit with `cursor.emitTextKey(catcher, text)`.
- **Native helpers**: a helper process is the plugin's bundled binary,
  launched with `FoamyNative.command(pluginDir, name, args)` (never a
  hand-built path, never `python3`). When `FoamyNative.unavailable(exitCode)`
  (126/127: no binary for this CPU) the view says "This plugin's helper isn't
  available for this CPU." in the plugin's language, keeps whatever works
  without it, and does not retry in a loop. Helpers answer in JSON, also on
  failure. Layout, build and checks: README.md, "Native helpers".
  One exception: a helper whose job is a library that only has a working
  Python binding stays Python, and its README says why. Today that is
  foamy-clock (Evolution's libecal through GObject introspection: the
  Evolution D-Bus API is private, versioned and doesn't expand recurring
  events) and foamy-bolt (Solaar's receiver library, years of device
  quirks). Anything else is Rust.
- **Effects**: MultiEffect, ShaderEffect and layer effects draw nothing under
  the software renderer (Omarchy CPU rendering, the preview harness). Gate them
  with `layer.enabled: GraphicsInfo.api !== GraphicsInfo.Software` and keep the
  content readable without them.

## Copy

Sentence case everywhere. Fixed words: "Settings" (never "Plugin settings"),
"Back", "Retry", "Refresh", "Saving…", "More options" (the ⋯ button), "More
information" (the (i) button), "Updated …" in footers. Intervals: "Refresh every" with options
like "30 seconds", "5 minutes". Bar options: "Show … in the bar". Counts:
`FoamyI18n.tn("%1 devices", n)` with a plural catalog entry, never
`n + " " + t("devices")`. Numbers through `FoamyI18n.number()` or `%1` holes.
Dates with `Qt.locale(FoamyI18n.formatLocale)`. The English texts kit
components hand the plugin to translate (paste failures, the helper's
unavailable text, settings save errors) are listed in `kit/i18n-texts.json`;
every catalog holds those of the components the plugin carries (`check.sh`
fails without them).

## Lint

`check.sh` fails on: `unqualified-color`, `bare-duration`, `sans-serif`,
`radius-x2`, `hex-colour`, `unguarded-loop`, `raw-ipc`, `empty-glyph` (a
`*Glyph { text: "" }`: an icon character was lost) and `pua-literal` (an
icon-font character written literally; editors and tools strip them, so write
`"\u{f0e7}"`). `--warn-pua` downgrades `pua-literal` to a warning. Kit files that own a
rule are exempt by name. A justified exception (art surface, shader clock)
carries a reasoned opt-out on the line or the line above:

```qml
property color glass: "#0b1d2a" // foamy-lint: allow hex-colour — lock-screen art surface
```

An opt-out without a reason is itself an error (`opt-out-reason`).
