# foamy-kit: notes for coding agents

foamy-kit is the canonical source of the components, tools and guides every
Foamy plugin carries. README.md describes sync, check, the validation command
(`tests/validate.sh`, "Tooling") and the native helper workflow; DESIGN.md
holds the UI rules. Run `tests/validate.sh` before proposing a change. Change shared files here, never in a
plugin's copy.

<!-- foamy-kit review: begin; managed by foamy-kit sync.sh, edit outside this block -->
## Code review

Follow [REVIEW.md](REVIEW.md) when reviewing or preparing a change. It is the
shared Foamy review standard, synced from foamy-kit. The rest of this file
adds repository-specific rules.

Before you add or change a test, read its section 6, "Test the behavior": a
test must fail when something a user or another component relies on breaks,
and you must have seen it fail.
<!-- foamy-kit review: end -->

## Working across plugins

foamy-kit is also the home repository for the plugins: start a session here
when a task spans plugins, and open or clone each plugin from the list below.
Read a plugin's own `AGENTS.md` before changing it; its rules apply inside
that repository. Change a kit file here and run `./sync.sh ../foamy-*`, then
`./check.sh ../foamy-*`. Each repository has its own history, branches and
pull requests. Shared Foamy workflows are skills in `.agents/skills/`
(`.claude/skills/` links to them).

## Plugins

`check.sh` fails for a published plugin that this list leaves out. Keep one
line per plugin, in alphabetical order, in the format below.

- foamy-audio (audio outputs, microphones, per-app volume and AirPlay): ~/GitHub/Personal/foamy-audio. Clone from https://github.com/foamrider/foamy-audio.git if missing.
- foamy-bolt (Logitech receiver and battery status): ~/GitHub/Personal/foamy-bolt. Clone from https://github.com/foamrider/foamy-bolt.git if missing.
- foamy-clock (clock, calendar and local Evolution agenda): ~/GitHub/Personal/foamy-clock. Clone from https://github.com/foamrider/foamy-clock.git if missing.
- foamy-github (local Git repository status and actions): ~/GitHub/Personal/foamy-github. Clone from https://github.com/foamrider/foamy-github.git if missing.
- foamy-idle-suspend (idle sleep policy for battery and AC power): ~/GitHub/Personal/foamy-idle-suspend. Clone from https://github.com/foamrider/foamy-idle-suspend.git if missing.
- foamy-lock (lock screen with password or fingerprint authentication): ~/GitHub/Personal/foamy-lock. Clone from https://github.com/foamrider/foamy-lock.git if missing.
- foamy-media (Spotify and YouTube media controls): ~/GitHub/Personal/foamy-media. Clone from https://github.com/foamrider/foamy-media.git if missing.
- foamy-menu (launcher and Omarchy menu): ~/GitHub/Personal/foamy-menu. Clone from https://github.com/foamrider/foamy-menu.git if missing.
- foamy-monitor (display arrangement, safe trials and wireless casting): ~/GitHub/Personal/foamy-monitor. Clone from https://github.com/foamrider/foamy-monitor.git if missing.
- foamy-notification-center (notification history, search and do not disturb): ~/GitHub/Personal/foamy-notification-center. Clone from https://github.com/foamrider/foamy-notification-center.git if missing.
- foamy-notifications (notification popups): ~/GitHub/Personal/foamy-notifications. Clone from https://github.com/foamrider/foamy-notifications.git if missing.
- foamy-power (battery status and AC/battery power profiles): ~/GitHub/Personal/foamy-power. Clone from https://github.com/foamrider/foamy-power.git if missing.
- foamy-syncthing (Syncthing folders and devices, Rust native core): ~/GitHub/Personal/foamy-syncthing. Clone from https://github.com/foamrider/foamy-syncthing.git if missing.
- foamy-teams (Microsoft Teams account launcher and unread status): ~/GitHub/Personal/foamy-teams. Clone from https://github.com/foamrider/foamy-teams.git if missing.
- foamy-todoist (Todoist tasks with quick add): ~/GitHub/Personal/foamy-todoist. Clone from https://github.com/foamrider/foamy-todoist.git if missing.
- foamy-train (direct trains in Norway with live departures): ~/GitHub/Personal/foamy-train. Clone from https://github.com/foamrider/foamy-train.git if missing.
- foamy-tray (always-visible system tray): ~/GitHub/Personal/foamy-tray. Clone from https://github.com/foamrider/foamy-tray.git if missing.
- foamy-vitals (system activity, memory, graphics and temperatures): ~/GitHub/Personal/foamy-vitals. Clone from https://github.com/foamrider/foamy-vitals.git if missing.
- foamy-weather (MET Norway weather and forecast): ~/GitHub/Personal/foamy-weather. Clone from https://github.com/foamrider/foamy-weather.git if missing.
- foamy-zendesk (Zendesk tickets with OAuth sign-in): ~/GitHub/Personal/foamy-zendesk. Clone from https://github.com/foamrider/foamy-zendesk.git if missing.
