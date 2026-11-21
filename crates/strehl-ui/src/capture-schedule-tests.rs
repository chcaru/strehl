//! The schedule dialog: local times resolved through daylight saving, the
//! relative mode, the wheels, and what the dialog sends.
use super::*;
use chrono::{FixedOffset, MappedLocalTime, NaiveDate, Offset};
use eframe::egui::{Event, FullOutput, PointerButton, Pos2, RawInput};
use serde_json::{Value, json};
use std::time::Instant;

/// US Pacific in 2026, by rule: PDT (UTC-7) from 2026-03-08 02:00 PST to
/// 2026-11-01 02:00 PDT, PST (UTC-8) otherwise. Enough of a zone to test a
/// skipped and a repeated hour without the machine's own zone.
#[derive(Clone, Copy, Debug)]
struct Pacific;

const PST: i32 = -8 * 3600;
const PDT: i32 = -7 * 3600;

fn utc(y: i32, m: u32, d: u32, h: u32, min: u32) -> NaiveDateTime {
    NaiveDate::from_ymd_opt(y, m, d)
        .unwrap()
        .and_hms_opt(h, min, 0)
        .unwrap()
}

impl TimeZone for Pacific {
    type Offset = FixedOffset;
    fn from_offset(_: &FixedOffset) -> Self {
        Pacific
    }
    fn offset_from_local_date(&self, local: &NaiveDate) -> MappedLocalTime<FixedOffset> {
        self.offset_from_local_datetime(&local.and_hms_opt(12, 0, 0).unwrap())
    }
    fn offset_from_local_datetime(&self, local: &NaiveDateTime) -> MappedLocalTime<FixedOffset> {
        let pst = FixedOffset::east_opt(PST).unwrap();
        let pdt = FixedOffset::east_opt(PDT).unwrap();
        // The local wall-clock hours of the two changes.
        let spring = utc(2026, 3, 8, 2, 0);
        let fall = utc(2026, 11, 1, 1, 0);
        if *local >= spring && *local < spring + Duration::hours(1) {
            MappedLocalTime::None
        } else if *local >= fall && *local < fall + Duration::hours(1) {
            MappedLocalTime::Ambiguous(pdt, pst)
        } else if *local >= spring + Duration::hours(1) && *local < fall {
            MappedLocalTime::Single(pdt)
        } else {
            MappedLocalTime::Single(pst)
        }
    }
    fn offset_from_utc_date(&self, utc: &NaiveDate) -> FixedOffset {
        self.offset_from_utc_datetime(&utc.and_hms_opt(12, 0, 0).unwrap())
    }
    fn offset_from_utc_datetime(&self, at: &NaiveDateTime) -> FixedOffset {
        let dst = *at >= utc(2026, 3, 8, 10, 0) && *at < utc(2026, 11, 1, 9, 0);
        FixedOffset::east_opt(if dst { PDT } else { PST }).unwrap()
    }
}

fn unix(at: NaiveDateTime) -> i64 {
    at.and_utc().timestamp()
}

/// A local time resolves by the zone's rules: winter and summer offsets, a
/// skipped hour refused, a repeated hour the earlier of the two.
#[test]
fn local_times_resolve_through_daylight_saving() {
    // Winter: 12:00 PST is 20:00 UTC; summer: 12:00 PDT is 19:00 UTC.
    assert_eq!(
        resolve(&Pacific, utc(2026, 1, 15, 12, 0)),
        Ok(Start {
            unix: unix(utc(2026, 1, 15, 20, 0)),
            repeated: false
        })
    );
    assert_eq!(
        resolve(&Pacific, utc(2026, 7, 1, 12, 0)).unwrap().unix,
        unix(utc(2026, 7, 1, 19, 0))
    );
    // 02:30 on 8 March does not exist.
    let gap = resolve(&Pacific, utc(2026, 3, 8, 2, 30)).unwrap_err();
    assert!(
        gap.contains("02:30") && gap.contains("clocks go forward"),
        "{gap}"
    );
    // 01:30 on 1 November happens twice: the first (PDT) is 08:30 UTC.
    assert_eq!(
        resolve(&Pacific, utc(2026, 11, 1, 1, 30)),
        Ok(Start {
            unix: unix(utc(2026, 11, 1, 8, 30)),
            repeated: true
        })
    );
    // Just after each change.
    assert_eq!(
        resolve(&Pacific, utc(2026, 3, 8, 3, 0)).unwrap().unix,
        unix(utc(2026, 3, 8, 10, 0))
    );
    assert_eq!(
        resolve(&Pacific, utc(2026, 11, 1, 2, 0)).unwrap().unix,
        unix(utc(2026, 11, 1, 10, 0))
    );
    // The labels read back in the zone.
    let now = unix(utc(2026, 7, 1, 16, 0)); // 09:00 PDT
    assert_eq!(
        when_label(&Pacific, unix(utc(2026, 7, 1, 19, 0)), now),
        "Today · 12:00"
    );
    assert_eq!(
        when_label(&Pacific, unix(utc(2026, 7, 2, 13, 5)), now),
        "Tomorrow · 06:05"
    );
    assert_eq!(
        when_label(&Pacific, unix(utc(2026, 7, 6, 19, 0)), now),
        "Mon Jul 6 · 12:00"
    );
    let summer = Pacific
        .offset_from_utc_datetime(&utc(2026, 7, 1, 0, 0))
        .fix()
        .local_minus_utc();
    assert_eq!(offset_label(summer), "UTC-07:00");
}

/// The machine's own zone: a resolved local time reads back unchanged, in
/// winter and in summer, with the offset of that date.
#[test]
fn the_machine_zone_round_trips() {
    for (m, d) in [(1, 15), (4, 10), (7, 1), (10, 20), (12, 24)] {
        let at = utc(2027, m, d, 14, 35);
        let start = resolve(&Local, at).expect("an ordinary afternoon exists");
        assert!(!start.repeated);
        let back = Local.timestamp_opt(start.unix, 0).single().unwrap();
        assert_eq!(back.naive_local(), at);
        assert_eq!(
            local_offset(start.unix),
            Some(back.offset().local_minus_utc())
        );
    }
}

#[test]
fn spans_offsets_and_defaults_read_as_the_dialog_says_them() {
    assert_eq!(offset_label(-8 * 3600), "UTC-08:00");
    assert_eq!(offset_label(5 * 3600 + 1800), "UTC+05:30");
    assert_eq!(offset_label(0), "UTC+00:00");
    assert_eq!(span_label(45 * 60), "45 m");
    assert_eq!(span_label(3600), "1 h");
    assert_eq!(span_label(90 * 60), "1 h 30 m");
    assert_eq!(span_label(51 * 3600), "2 d 3 h");
    assert_eq!(span_label(59), "1 m");
    let now = unix(utc(2026, 7, 1, 16, 2)) + 17; // 09:02:17 PDT
    assert_eq!(
        default_start(&Pacific, now),
        utc(2026, 7, 1, 9, 35),
        "half an hour on, on the next five minutes"
    );
    assert!(check_future(now + 30, now).is_err());
    assert!(check_future(now + MIN_LEAD, now).is_ok());
}

#[test]
fn wheels_wrap_and_minutes_carry() {
    let minutes = (0, 55, 5);
    assert_eq!(shift(55, 1, minutes, true), 0);
    assert_eq!(shift(0, -1, minutes, true), 55);
    assert_eq!(shift(20, 2, minutes, true), 30);
    assert_eq!(shift(23, 1, (0, 23, 1), true), 0);
    assert_eq!(shift(0, -1, (0, 72, 1), false), 0);
    assert_eq!(shift(72, 1, (0, 72, 1), false), 72);
    // 1 h 55 m up a step is 2 h; 2 h down a step is 1 h 55 m.
    assert_eq!(carry(115, 0), 120);
    assert_eq!(carry(120, 55), 115);
    assert_eq!(carry(125, 10), 130);
}

fn snapshot(state: Value) -> Snapshot {
    let mut s = Snapshot {
        online: true,
        observed: Some(Instant::now()),
        ..Default::default()
    };
    s.set_state(state);
    s
}

fn ready() -> Value {
    json!({"camera_revision":4,"plan_revision":3,"sequence_id":2,"phase":"ready","connected":true,
        "busy":false,"editable":true,
        "plan":{"start":37100,"end":37764,"step":7,"settle_ms":500,"approach":128,"capture_timeout_s":120},
        "start_set":true,"end_set":true,"shots_per_plane":4,
        "power":{"light":{"on":true},"camera":{"on":true},"available":true,"can_manage":true,
            "manage_stack":true,"warmup_seconds":17},
        "schedule":{"job":null,"error":null}})
}

thread_local! {
    static CLOCK: std::cell::Cell<f64> = const { std::cell::Cell::new(0.0) };
}

struct Dialog {
    ctx: egui::Context,
    ui: ScheduleUi,
    s: Snapshot,
}

impl Dialog {
    fn new(state: Value) -> Self {
        let ctx = egui::Context::default();
        crate::theme::install(&ctx);
        let s = snapshot(state);
        let mut ui = ScheduleUi::default();
        ui.open(&s);
        Self { ctx, ui, s }
    }
    fn frame(&mut self, events: Vec<Event>) -> (FullOutput, Option<Command>) {
        let time = CLOCK.with(|c| {
            c.set(c.get() + 0.05);
            c.get()
        });
        let mut command = None;
        let timing = Some(StackTiming {
            seconds: 540.0,
            planes: 96,
            raws: 384,
        });
        let out = self.ctx.run(
            RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1280.0, 900.0))),
                time: Some(time),
                events,
                ..Default::default()
            },
            |ctx| {
                command = self
                    .ui
                    .show(ctx, &self.s, true, timing, &CapturePalette::default());
            },
        );
        (out, command)
    }
    fn texts(out: &FullOutput) -> Vec<(String, Rect)> {
        out.shapes
            .iter()
            .filter_map(|s| match &s.shape {
                egui::Shape::Text(t) => {
                    Some((t.galley.text().to_owned(), t.visual_bounding_rect()))
                }
                _ => None,
            })
            .collect()
    }
    fn click(&mut self, label: &str) -> Option<Command> {
        let (out, _) = self.frame(vec![]);
        let at = Self::texts(&out)
            .into_iter()
            .find(|(t, _)| t == label)
            .unwrap_or_else(|| panic!("{label} is not drawn"))
            .1
            .center();
        self.click_at(at)
    }
    fn click_at(&mut self, at: Pos2) -> Option<Command> {
        let press = |pressed| Event::PointerButton {
            pos: at,
            button: PointerButton::Primary,
            pressed,
            modifiers: Default::default(),
        };
        let a = self.frame(vec![Event::PointerMoved(at), press(true)]).1;
        let b = self.frame(vec![press(false)]).1;
        a.or(b)
    }
}

/// The dialog says its title once (it used to sit in a window inside a
/// window of the same name).
#[test]
fn the_title_is_drawn_once() {
    let mut d = Dialog::new(ready());
    d.frame(vec![]);
    let (out, _) = d.frame(vec![]);
    let texts = Dialog::texts(&out);
    let titles = texts
        .iter()
        .filter(|(t, _)| t.eq_ignore_ascii_case("Schedule this stack"))
        .count();
    assert_eq!(titles, 1);
    assert!(
        !texts.iter().any(|(t, _)| t == "Schedule stack"),
        "no window title of its own"
    );
}

/// "In a while": a chip sets the span, and the stack is scheduled that far
/// from now, with the host's warm-up and every outlet action.
#[test]
fn a_span_from_now_schedules_that_far_ahead() {
    let mut d = Dialog::new(ready());
    d.frame(vec![]);
    d.click("In a while");
    assert_eq!(d.ui.mode, Mode::In);
    d.click("+2 h");
    assert_eq!(d.ui.in_minutes, 120);
    let before = Utc::now().timestamp();
    let label = Dialog::texts(&d.frame(vec![]).0)
        .into_iter()
        .map(|(t, _)| t)
        .find(|t| t.starts_with("Schedule for "))
        .expect("the button names the local start");
    let command = d.click(&label).expect("scheduled");
    let after = Utc::now().timestamp();
    let Command::ScheduleStack {
        start_at,
        power,
        warmup_seconds,
    } = command
    else {
        panic!("not a schedule: {command:?}")
    };
    let start_at = start_at as i64;
    assert!(
        (before + 7200..=after + 7200).contains(&start_at),
        "{start_at} two hours after {before}..{after}"
    );
    assert_eq!(power, StackPower::managed());
    assert_eq!(warmup_seconds, Some(17));
    assert!(!d.ui.editing(), "the dialog closes once sent");
}

/// "At a time": a day on the calendar and the wheels' time are sent as that
/// local time's Unix seconds.
#[test]
fn a_calendar_day_schedules_that_local_time() {
    let mut d = Dialog::new(ready());
    d.frame(vec![]);
    // Next month, the 3rd.
    d.click("\u{203a}");
    let (out, _) = d.frame(vec![]);
    let three = Dialog::texts(&out)
        .into_iter()
        .find(|(t, _)| t == "3")
        .expect("day 3 drawn")
        .1
        .center();
    d.click_at(three);
    let today = Local::now().date_naive();
    let next = if today.month() == 12 {
        NaiveDate::from_ymd_opt(today.year() + 1, 1, 3)
    } else {
        NaiveDate::from_ymd_opt(today.year(), today.month() + 1, 3)
    }
    .unwrap();
    assert_eq!(d.ui.date, Some(next));
    // A click on the hour under the wheel's value steps it on by one.
    let expected_hour = (d.ui.hour + 1) % 24;
    let (out, _) = d.frame(vec![]);
    let caption = Dialog::texts(&out)
        .into_iter()
        .find(|(t, _)| t == "TIME")
        .map(|(_, r)| r)
        .expect("the time wheels' caption");
    // Under the caption and right of the calendar.
    let below = Dialog::texts(&out)
        .into_iter()
        .filter(|(_, r)| r.top() > caption.bottom() && r.left() > caption.left() - 4.0)
        .find(|(t, _)| *t == format!("{expected_hour:02}"))
        .expect("the next hour is drawn under the wheel")
        .1
        .center();
    d.click_at(below);
    assert_eq!(d.ui.hour, expected_hour);
    let local = next.and_hms_opt(d.ui.hour, d.ui.minute, 0).unwrap();
    let label = Dialog::texts(&d.frame(vec![]).0)
        .into_iter()
        .map(|(t, _)| t)
        .find(|t| t.starts_with("Schedule for "))
        .unwrap();
    let Some(Command::ScheduleStack { start_at, .. }) = d.click(&label) else {
        panic!("not scheduled")
    };
    assert_eq!(start_at as i64, resolve(&Local, local).unwrap().unix);
}

/// Switching mode carries the start across.
#[test]
fn switching_mode_keeps_the_start() {
    let mut ui = ScheduleUi::default();
    let s = snapshot(ready());
    ui.open(&s);
    let now = Utc::now().timestamp();
    ui.mode = Mode::In;
    ui.in_minutes = 95;
    ui.switch(Mode::At, now);
    let at = ui.start(now).unwrap().unix;
    assert!(
        (at - (now + 95 * 60)).abs() < 5 * 60,
        "rounded to five minutes"
    );
    ui.switch(Mode::In, now);
    assert_eq!(ui.in_minutes % 5, 0);
    assert!((i64::from(ui.in_minutes) * 60 - (at - now)).abs() < 5 * 60);
}

/// An armed schedule shows when it starts and only cancels: no second form.
#[test]
fn an_armed_schedule_shows_and_cancels() {
    let mut state = ready();
    let start = Utc::now().timestamp() + 3600;
    state["schedule"] = json!({"job":{"id":"job-1","start_at":start,"stage":"armed",
        "message":"Armed","recipe":{"plan":{"start":37100,"end":37764,"step":7},"shots":4}},"error":null});
    let mut d = Dialog::new(state);
    d.frame(vec![]);
    let (out, _) = d.frame(vec![]);
    let texts: Vec<String> = Dialog::texts(&out).into_iter().map(|(t, _)| t).collect();
    assert!(texts.iter().any(|t| t == "Cancel schedule"));
    assert!(
        !texts.iter().any(|t| t.starts_with("Schedule for")),
        "{texts:?}"
    );
    assert!(texts.iter().any(|t| t.contains("local, UTC")));
    assert!(matches!(
        d.click("Cancel schedule"),
        Some(Command::CancelSchedule { id }) if id == "job-1"
    ));
    assert!(armed_label(&d.s).unwrap().starts_with("Scheduled · "));
}
