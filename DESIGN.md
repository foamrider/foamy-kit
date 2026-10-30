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
| Body font | `FoamyStyle.fontFamily` | `"sans-serif"`; never the literal *(lint)*. `monoFamily` (the Omarchy font) for numbers, code, glyphs |
| Type scale | `FoamyStyle.font.*` | caption 10, bodySmall 11, body 12, subtitle 13, title 14, heading 16, iconLarge 18, display 24, displayLarge 28 (all `Style.space(n)`). Hero numbers (clock face, temperature, volume, countdown): `numeral` 56, `numeralCompact` 40, their unit in `display`. No other sizes |
| Widths | `popupWidth` / `popupWidthWide` | 420 standard; 560 for data-dense panels (vitals, weather, monitor). The settings page uses the same width. Height cap `popupMaxHeight` 640 (FoamyPopup `maxHeight`; 0 for panels that compact themselves by screen height). Menus: `menuWidth` 232, `menuPadding` 8 |
| Spacing | `padding` 20, `gapTiny` 2, `gapSmall` 4, `gap` 8, `gapLarge` 12, `sectionGap` 14, `rowPadding` 10, `rowHeight` 36 | Popup card padding is 0; content insets by `padding` so lists scroll edge to edge |
| Controls | `controlHeight` 32, `actionSize` 28, `iconSize` 15, `settingsButtonSize` 32, `settingsIconSize` 16, `iconStroke` 1.7 | |
| Colours | `Commons.Color.*` | Always qualified *(lint)*: on Qt 6.12 (installed) a bare `Color.popups` is `undefined` |
| Text tones | `FoamyPalette.text`, `secondaryText` (tint .72), `mutedText` (tint .55) | Meta/section labels secondary; hints and empty states muted |
| Fills | `hoverFill` .08, `fieldFill` .055, `selectedFill` accent .18, `divider` .12 | |
| Status | `FoamyPalette.warning/success/error/info` | Theme `yellow/green/red/cyan` from colors.toml, falling back to `urgent`/`accent`. No hex literals outside FoamyPalette *(lint)*. For text on the surface use `onSurface(c)` |
| Disabled | `FoamyStyle.disabledOpacity` .45 | |
| Motion | `FoamyMotion.hover` 100, `press` 160, `toggle` 120, `slider` 140, `fadeIn` 180, `fadeOut` 120, `grow` 200, `morph` 220, `slow` 300; `duration(ms)` | Every `duration:` goes through FoamyMotion *(lint)*. 0 under reduced motion on 4.5 |

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
    actions, settings button (tooltip "Settings").
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
    `FoamySettingsPage` does it.
  - No band on menus (`FoamyPopupCard`) or toasts.
- **Header row only** (`FoamyHeader`): inside the band; standalone only where a
  band can't sit (a sub-view header inside the body).
- **Rows**: `FoamyCursorSurface` (stock CursorSurface, foamy radius), insets
  `gapLarge`, icon `iconSize`, name `body`, detail `caption` secondary.
- **Actions**: `FoamyAction` (28, icon 15, hover fill, tooltip). Settings button =
  `settings: true` (32/16). Destructive: `destructive: true`. Spinners only via
  `spinning`.
- **Icons**: `FoamyIcon` (Lucide superset, 102 names). Add icons to the kit
  (tools/update-icons.py), not to plugins; no Nerd-font glyphs in popups.
- **Inputs**: `SafeTextField` (never Qt's TextField: it reads the whole clipboard).
  Callers set size/alignment, never `background`.
- **Choices**: `FoamyDropdown`, with `value` bound to the setting and the save in
  `onChanged`; it never assigns `value` itself. **Toggles**: `FoamyToggle`
  (`checked` bound, save in `onClicked`).
- **Numbers and text in settings**: `FoamyNumberField` / `FoamyTextSettingField`
  (bound `value`, save in `onCommitted`). Never hand-roll a row that assigns `text`.
- **Controlled values**: kit controls never assign over a caller's binding.
  Bind `value`/`checked`/`open` to state and change the state in handlers.
  (Text fields are the exception every toolkit has: typing edits `text`;
  write back in `onTextEdited`, reset by assigning.)
- **Settings page**: `FoamySettingsPage` (back, "Settings", "Saving…", error +
  Retry, sections). Sections: `FoamySettingsSection`, sentence-case titles.
  Whether it shows: `FoamySettingsState` (`show()` opens the popup on
  Settings; resets on close, never on open).
- **Empty / loading / error**: one line, bodySmall, `mutedText`, word-wrapped; no
  period for short states ("No devices", "Scanning…"); errors in `Commons.Color.urgent`
  with `Accessible.AlertMessage`, plus "Retry" when the action can be retried.

## UX rules (4.5, mandatory)

- **Motion**: durations through FoamyMotion. Every looping animation runs only
  while shown and `!FoamyMotion.reduceMotion` *(lint)*. Nothing over 300 ms
  except loop periods.
- **Keyboard**: one cursor. Wrap popup content in `PanelKeyCatcher`; keep the
  cursor in `FoamyCursor`; arrows/hjkl move, Enter/Space activate, Esc closes
  (or leaves Settings), Tab/Shift-Tab call `switchPanel(direction)`, `s` opens
  Settings, `r` refreshes where there is a refresh. Pointer hover moves the same
  cursor (one highlight on screen). Focus rings only on form controls in
  Settings (`focusable: true`); set `blocked` on the key catcher while a form
  or editor owns keys.
- **RTL**: FoamyPopup/FoamyPopupCard/FoamySettingsPage mirror; place things
  with anchors/rows, not `x` arithmetic; directional icons mirror via FoamyIcon.
- **Lazy content**: popup content in `body`; nothing polls or ticks for the UI
  while hidden. Data that must exist while closed lives outside the body.
- **Once per shell**: 4.5 draws a bar per monitor. Pollers, helpers and IPC
  run in the leader only (`FoamyMember`), state lives in a plugin `pragma
  Singleton`; open popups raise demand.
- **IPC**: `FoamyIpc` only *(lint: no raw `IpcHandler`/`ShellIpc`)*, `enabled:
  member.isLeader`.
  A target shared with another service: `FoamyIpcPreference`. Calling another
  plugin: `FoamyPeerIpc` (never read its files or run its scripts).
- **Settings**: save through `FoamyPrefsQueue` (inline `updateEntryInline`,
  else the CLI; serialised, newest value per key, never merging over a stale
  entry). Arrays/objects are schema types (`array`, `object` + `validate`).
  Never a hand-built `setBarWidget` call or a plugin-local save queue.
- **Letter shortcuts**: `onTextKey: function(text, modifiers)` and skip unless
  `cursor.plain(modifiers)` (`modifiers` is undefined on 4.0, which has
  `textKey(text)`). Tests emit with `cursor.emitTextKey(catcher, text)`.
- **Effects**: MultiEffect, ShaderEffect and layer effects draw nothing under
  the software renderer (Omarchy CPU rendering, the preview harness). Gate them
  with `layer.enabled: GraphicsInfo.api !== GraphicsInfo.Software` and keep the
  content readable without them.

## Copy

Sentence case everywhere. Fixed words: "Settings" (never "Plugin settings"),
"Back", "Retry", "Refresh", "Saving…". Intervals: "Refresh every" with options
like "30 seconds", "5 minutes". Bar options: "Show … in the bar". Counts:
`FoamyI18n.tn("%1 devices", n)` with a plural catalog entry, never
`n + " " + t("devices")`. Numbers through `FoamyI18n.number()` or `%1` holes.
Dates with `Qt.locale(FoamyI18n.formatLocale)`.

## Lint

`check.sh` fails on: `unqualified-color`, `bare-duration`, `sans-serif`,
`radius-x2`, `hex-colour`, `unguarded-loop`, `raw-ipc`, `empty-glyph` (a
`*Glyph { text: "" }`: an icon character was lost). It warns on `pua-literal`
(an icon-font character written literally; editors and tools strip them, so
write `"\u{f0e7}"`); `--strict` fails on warnings too. Kit files that own a
rule are exempt by name. A justified exception (art surface, shader clock)
carries a reasoned opt-out on the line or the line above:

```qml
property color glass: "#0b1d2a" // foamy-lint: allow hex-colour — lock-screen art surface
```

An opt-out without a reason is itself an error (`opt-out-reason`).
