// Unit tests for kit/FoamySchedule.js (moved here with the schedule from
// foamy-train's and foamy-zendesk's model tests), loaded through
// kit/node-loader.cjs the way plugins load it.
const assert = require("assert");
const Schedule = require("../kit/node-loader.cjs").load("FoamySchedule");

let passed = 0;
function test(name, fn) {
  try {
    fn();
    passed++;
  } catch (error) {
    error.message = `${name}: ${error.message}`;
    throw error;
  }
}
const plain = (value) => JSON.parse(JSON.stringify(value));

test("ranges: HH:MM-HH:MM, 24:00 only as an end, '' is a day off", () => {
  for (const value of ["", "08:00-16:00", "22:00-02:00", "00:00-24:00", "23:00-24:00"]) assert.ok(Schedule.validRange(value), value);
  for (const value of ["8:00-16:00", "24:00-01:00", "08:00", "09:80-10:00", "08:00-16:00-18:00", null, 7])
    assert.ok(!Schedule.validRange(value), String(value));
  assert.strictEqual(Schedule.minutes("24:00", true), 1440);
  assert.strictEqual(Schedule.minutes("24:00", false), -1);
});

test("week(): seven ranges, Monday first; invalid or missing ones are days off", () => {
  assert.deepStrictEqual(plain(Schedule.week({})), ["", "", "", "", "", "", ""]);
  assert.deepStrictEqual(plain(Schedule.week(null)), ["", "", "", "", "", "", ""]);
  assert.deepStrictEqual(plain(Schedule.week({ scheduleMonday: "08:00-16:00", scheduleSunday: "bad" })),
    ["08:00-16:00", "", "", "", "", "", ""]);
  assert.strictEqual(Schedule.dayKeys.length, 7);
});

test("overnight ranges carry into the next day; off means always within", () => {
  const week = ["22:00-02:00", "", "", "", "", "", ""]; // Monday night into Tuesday
  assert.strictEqual(Schedule.withinWeek(new Date(2026, 10, 2, 23), true, week), true);
  assert.strictEqual(Schedule.withinWeek(new Date(2026, 10, 3, 1), true, week), true);
  assert.strictEqual(Schedule.withinWeek(new Date(2026, 10, 3, 2), true, week), false);
  assert.strictEqual(Schedule.withinWeek(new Date(2026, 10, 3, 2), false, week), true);
  assert.strictEqual(Schedule.withinWeek(new Date(2026, 8, 29, 1), false, []), true);
  assert.strictEqual(Schedule.withinWeek(new Date(2026, 10, 4, 12), true, ["", "", "00:00-24:00", "", "", "", ""]), true);
});

test("snoozing and resuming override the schedule until the next day", () => {
  const at = (day, hour, minute) => new Date(2026, 10, day, hour, minute || 0);
  const week = ["08:00-16:00", "22:00-06:00", "", "", "", "", ""]; // Monday, Tuesday night
  // Within the hours: a snooze lasts until they end, then the schedule rules again.
  const snooze = Schedule.toggled(at(2, 10), true, week, null);
  assert.deepStrictEqual(plain(snooze), { on: false, until: at(2, 16).getTime() });
  assert.strictEqual(Schedule.effective(at(2, 15, 59), true, week, snooze), false);
  assert.strictEqual(Schedule.effective(at(3, 8), true, week, snooze), false);
  // Pressing again goes back to the schedule: no override.
  assert.strictEqual(Schedule.toggled(at(2, 11), true, week, snooze), null);
  // Outside the hours: resuming lasts until midnight...
  const evening = Schedule.toggled(at(2, 19), true, week, null);
  assert.deepStrictEqual(plain(evening), { on: true, until: at(3, 0).getTime() });
  assert.strictEqual(Schedule.effective(at(2, 23, 59), true, week, evening), true);
  assert.strictEqual(Schedule.effective(at(3, 0), true, week, evening), false);
  // ...or until the schedule starts, if that is sooner.
  assert.deepStrictEqual(plain(Schedule.toggled(at(2, 6), true, week, null)), { on: true, until: at(2, 8).getTime() });
  // An overnight range: the snooze runs on past midnight to its end.
  assert.deepStrictEqual(plain(Schedule.toggled(at(3, 23), true, week, null)), { on: false, until: at(4, 6).getTime() });
  // No schedule: snoozed until midnight.
  assert.deepStrictEqual(plain(Schedule.toggled(at(4, 12), false, [], null)), { on: false, until: at(5, 0).getTime() });
  // The state file: expired or malformed overrides are dropped.
  const text = Schedule.serializeOverride(snooze);
  assert.deepStrictEqual(plain(Schedule.parseOverride(text, at(2, 12).getTime())), plain(snooze));
  assert.strictEqual(Schedule.parseOverride(text, at(2, 16).getTime()), null);
  assert.strictEqual(Schedule.parseOverride('{"version":1,"override":{"on":"no","until":1}}', 0), null);
  assert.strictEqual(Schedule.parseOverride("not json", 0), null);
  assert.strictEqual(Schedule.serializeOverride(null), '{"version":1,"override":null}\n');
  assert.strictEqual(Schedule.serializeOverride({ on: true, until: Infinity }), '{"version":1,"override":null}\n');
});

console.log(`PASS FoamySchedule: ${passed} tests`);
