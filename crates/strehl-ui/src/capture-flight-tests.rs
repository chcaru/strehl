use super::super::{fixture, follow};
use super::*;
use eframe::egui::{Event, FullOutput, PointerButton, Pos2, RawInput};
use serde_json::{Value, json};
use std::time::{Duration, Instant};

fn snapshot(state: Value) -> Snapshot {
    let mut s = Snapshot {
        online: true,
        observed: Some(Instant::now()),
        receiver: json!({"ok":true,"free_bytes":355_000_000_000u64}),
        ..Default::default()
    };
    s.set_state(state);
    s
}

fn capturing() -> Value {
    json!({"camera_revision":4,"plan_revision":3,"sequence_id":2,"phase":"capturing","connected":true,
        "busy":false,"editable":false,"completed":61,"total":96,"shots_per_plane":4,"position":37520,
        "timer":{"elapsed":341.6,"remaining":198.0},"camera_model":"ILCE-7CR","error_correction":true,
        "storage":{"mode":"host-pc","captured_frames":268,"saved_frames":266,"pending_frames":2,
            "receipt":{"wire_MB_per_second":38.2}}})
}

/// The flight fixture's journal: 61 planes with retakes and failures.
fn journal() -> Progress {
    fixture::progress()
}

/// The owner's capture of 2026-11-21 (`stack-1795300522964-6430`, 211
/// planes, four-shot, error correction on), its checker's 260 journal lines
/// in order: the plane, then `.` (passed) or the failure (M: witness tiles
/// disagree; W: witness pairs misregistered; P: offsets do not cover the CFA
/// parities) and whether the checker asked for a retake (+ or -).
const OWNER_RUN: &str = "1. 2. 3W+ 4. 3. 5. 6. 7. 8. 9. 10. 11. 12. 13. 14. 15. 16. 17. 18. 19. 20. 21. 22. 23. 24P- 25. 26. 27W- 28. 29. 30P- 31P- 32P- 33P- 34. 35. 36. 37. 38. 39. 40. 41W- 42. 43. 44. 45. 46. 47. 48. 49. 50. 51W- 52. 53P- 54P- 55. 56. 57. 58. 59. 60. 61. 62. 63. 64. 65. 66. 67P- 68. 69. 70. 71. 72. 73. 74. 75. 76. 77. 78. 79W+ 80. 79. 81. 82. 83. 84. 85P- 86. 87. 88. 89. 90. 91. 92. 93. 94. 95. 96. 97P- 98. 99. 100. 101P- 102. 103. 104. 105. 106. 107. 108. 109. 110. 111. 112. 113. 114. 115. 116. 117P- 118. 119. 120. 121. 122. 123M+ 124. 123. 125. 126M+ 127M+ 126. 128M+ 127. 129. 128. 130M+ 131. 130M+ 132. 130. 133. 134M+ 135P- 134M+ 136. 134. 137. 138M+ 139M+ 138M+ 140M+ 139M+ 138M+ 141M+ 140P- 139. 142. 141. 143M+ 144M+ 143. 145M+ 144M+ 146M+ 145M+ 144M+ 147M+ 146M+ 145M+ 148M+ 147M+ 146P- 149M+ 148. 147M+ 150M+ 149M+ 151. 150M+ 149M+ 152. 150. 153. 154. 155M+ 156M+ 155M+ 157M+ 156M+ 155M+ 158M+ 157. 156. 159M+ 158. 160. 159. 161. 162M+ 163M+ 162. 164. 163. 165M+ 166. 165M+ 167M+ 165. 168M+ 167. 169M+ 168. 170. 169. 171. 172M+ 173. 172. 174. 175M+ 176. 175M+ 177. 175. 178M+ 179. 178M+ 180. 178M+ 181. 182. 183. 184. 185. 186. 187P- 188. 189. 190. 191. 192. 193. 194. 195. 196. 197. 198. 199. 200. 201. 202. 203P- 204. 205. 206. 207. 208. 209. 210. 211.";

/// The journal [`OWNER_RUN`] encodes, with the engine's own reasons.
fn owner_lines() -> Vec<String> {
    let mut tries = std::collections::HashMap::new();
    OWNER_RUN
        .split_whitespace()
        .map(|token| {
            let digits: String = token.chars().take_while(char::is_ascii_digit).collect();
            let plane: u64 = digits.parse().unwrap();
            let rest = &token[digits.len()..];
            let n = tries.entry(plane).or_insert(0u32);
            *n += 1;
            let group = format!("ptp-{plane}-{n}");
            let names = [format!("plane-{plane}-try-{n}.ARW")];
            if rest == "." {
                json!({"plane":plane,"target":31_000 + plane * 7,"group_id":group,"verdict":"pass",
                    "reason":null,"retake":false,"members":4,"names":names,"seconds":0.26})
            } else {
                let reason = match &rest[..1] {
                    "M" => fixture::MOTION,
                    "W" => fixture::RESIDUAL,
                    _ => fixture::PATTERN,
                };
                json!({"plane":plane,"target":31_000 + plane * 7,"group_id":group,"verdict":"demote",
                    "reason":reason,"retake":rest.ends_with('+'),"members":4,"names":names,"seconds":0.28})
            }
            .to_string()
        })
        .collect()
}

fn owner_progress() -> Progress {
    follow::progress(&owner_lines().join("\n"))
}

/// The feed's items of `plane`, with their rows.
fn rows_of(p: &Progress, plane: u64, cx: FeedContext) -> Vec<FeedRow> {
    p.feed
        .iter()
        .enumerate()
        .filter(|(_, item)| item.plane == plane)
        .map(|(i, item)| {
            let next = item.next.and_then(|n| p.feed.get(i + n as usize));
            feed_row(item, next, cx)
        })
        .collect()
}

const ENDED: FeedContext = FeedContext {
    error_correction: true,
    ended: true,
    max_retakes: 2,
    manual: false,
};

/// The owner's run as the feed tells it: every try its own item in the
/// checker's order, the counts the activity and the stack reported (34
/// retaken, 27 stacked from one shot: the render demoted exactly 27 frames),
/// each failure's status and the end summary in words.
#[test]
fn the_owners_run_is_told_try_by_try() {
    let p = owner_progress();
    assert_eq!(p.feed.len(), 260);
    assert_eq!((p.retakes, p.retaken), (49, 34));
    // planes, first try, retake passed, retake failed, not retaken, asked,
    // incomplete
    assert_eq!(p.tally.counts(), [211, 159, 25, 9, 18, 0, 0]);
    assert_eq!(p.tally.single_shot(), 27);
    // Plane 3's retake is its own item, after plane 4 (as it was taken).
    let order: Vec<(u64, u32)> = p.feed[..5].iter().map(|i| (i.plane, i.attempt)).collect();
    assert_eq!(order, [(1, 1), (2, 1), (3, 1), (4, 1), (3, 2)]);
    let three = rows_of(&p, 3, ENDED);
    assert_eq!(
        (three[0].status, three[0].mark, three[0].detail.as_str()),
        (
            "retaken",
            Mark::Warn,
            "The four shots do not line up. Retaken: try 2 passed."
        )
    );
    assert_eq!(
        (three[1].status, three[1].title.as_str()),
        ("passed", "Retake passed · try 2")
    );
    // Not retaken: a wrong shift pattern, and the scene's own correction.
    let pattern = &rows_of(&p, 24, ENDED)[0];
    assert_eq!((pattern.status, pattern.mark), ("one shot", Mark::Bad));
    assert!(
        pattern
            .detail
            .ends_with("Not retaken, by the checker's rule.")
    );
    assert!(
        pattern
            .tip
            .contains("expects a retake to fail the same way")
    );
    assert!(pattern.tip.contains("do not cover the four CFA parities"));
    let correction = &rows_of(&p, 27, ENDED)[0];
    assert_eq!(correction.title, "Shift correction off");
    assert!(correction.detail.ends_with("the shots are not at fault."));
    // Two retakes, then no more: the stack uses the last try's first shot.
    let exhausted = rows_of(&p, 138, ENDED);
    let statuses: Vec<&str> = exhausted.iter().map(|r| r.status).collect();
    assert_eq!(statuses, ["retaken", "retaken", "one shot"]);
    assert!(exhausted[1].detail.ends_with("Retaken: try 3 failed too."));
    assert_eq!(exhausted[2].title, "Shots differ in places · try 3");
    assert!(
        exhausted[2]
            .detail
            .ends_with("Failed 3 tries; no retakes left.")
    );
    // A retake that failed a check the checker does not retake.
    let switched = rows_of(&p, 140, ENDED);
    assert_eq!(switched[1].title, "Shift pattern off · try 2");
    assert_eq!(switched[1].status, "one shot");
    assert_eq!(
        summary_sentence(&p.tally, true),
        "211 planes checked: 159 passed on the first try. 34 planes were taken again: 25 then passed, 9 failed every try. 18 planes failed a check the checker does not retake. The stack uses the first shot of those 27 planes (one shot's detail there, not four); every plane is in the stack."
    );
    // The kinds, most tries first, and the planes each left at one shot.
    let kinds = failure_kinds(&p.feed);
    assert_eq!(
        kinds,
        [
            (Failure::Motion, 54, 7),
            (Failure::Pattern, 17, 17),
            (Failure::Correction, 3, 3),
            (Failure::OutOfLine, 2, 0),
        ]
    );
}

/// While the capture runs, a failed try asking for a retake is "retaking"
/// until its retake is checked; without error correction, or once the
/// capture ended, it is not retaken and the stack uses its first shot.
#[test]
fn a_retake_asked_for_is_pending_until_it_comes() {
    let line = json!({"plane":7,"group_id":"g7","verdict":"demote","reason":fixture::MOTION,
        "retake":true,"members":4,"names":["frame-000025.ARW"]});
    let p = follow::progress(&line.to_string());
    let item = &p.feed[0];
    let running = FeedContext {
        error_correction: true,
        ended: false,
        ..FeedContext::default()
    };
    let row = feed_row(item, None, running);
    assert_eq!((row.status, row.mark), ("retaking", Mark::Warn));
    assert!(row.detail.ends_with("Taking it again (try 2 of 3)."));
    assert_eq!(p.tally.asked, 1);
    let off = feed_row(item, None, FeedContext::default());
    assert_eq!(off.status, "one shot");
    assert!(off.detail.ends_with("error correction is off."));
    let ended = feed_row(item, None, ENDED);
    assert!(ended.detail.ends_with("the capture ended."));
    assert_eq!(
        summary_sentence(&p.tally, false),
        "1 plane checked so far: 0 passed on the first try. 1 plane is being taken again."
    );
    assert!(summary_sentence(&p.tally, true).contains("asked for a retake that was not taken"));
}

/// Every row's words fit their lines at the narrowest feed (340 px) in the
/// studio face: the title beside its status on one line, the detail on two.
#[test]
fn feed_rows_fit_their_lines_at_the_narrowest() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let mut items = Vec::new();
    for reason in [
        fixture::MOTION,
        fixture::MISREGISTERED,
        fixture::PATTERN,
        "offsets unmeasurable (too little scene structure)",
        "shifted photosites leave the sensor buffer",
        "members disagree in black or white level",
    ] {
        for retake in [true, false] {
            for attempt in [1, 2, 3] {
                items.push(FeedItem {
                    plane: 6000,
                    attempt,
                    verdict: Verdict::Demote,
                    retake,
                    reason: Some(reason.into()),
                    members: 4,
                    ..Default::default()
                });
            }
        }
    }
    items.push(FeedItem {
        plane: 6000,
        verdict: Verdict::Incomplete,
        ..Default::default()
    });
    let passed = FeedItem {
        plane: 6000,
        attempt: 3,
        verdict: Verdict::Pass,
        members: 4,
        ..Default::default()
    };
    let failed = FeedItem {
        verdict: Verdict::Demote,
        ..passed.clone()
    };
    let running = FeedContext {
        error_correction: true,
        ended: false,
        ..FeedContext::default()
    };
    let mut checked = 0;
    let _ = ctx.run(RawInput::default(), |ctx| {
        let painter = ctx.layer_painter(egui::LayerId::background());
        // The row's text column in the narrowest side column.
        let width = 340.0 - 58.0 - FEED_GUTTER;
        for item in items.iter().chain([&passed]) {
            for next in [None, Some(&passed), Some(&failed)] {
                for cx in [ENDED, FeedContext::default(), running] {
                    let row = feed_row(item, next, cx);
                    let mut detail = style::job(&row.detail, 12.0, egui::Color32::WHITE, 0.0);
                    detail.wrap.max_width = width;
                    let rows = painter.layout_job(detail).rows.len();
                    assert!(rows <= 2, "{rows} rows: {}", row.detail);
                    let title = style::job(&row.title, 12.5, egui::Color32::WHITE, 0.0);
                    let status = style::caps_job(row.status, 10.0, egui::Color32::WHITE);
                    let room = width - painter.layout_job(status).size().x - 8.0;
                    assert!(
                        painter.layout_job(title).size().x <= room,
                        "title too long: {}",
                        row.title
                    );
                    checked += 1;
                }
            }
        }
    });
    assert!(checked > 300, "{checked}");
}

#[test]
fn the_health_column_reads_transfer_checks_disk_and_rig() {
    let s = snapshot(capturing());
    let p = journal();
    let lines = health(&s, Some(&p), true);
    assert_eq!(lines[0].title, "Transfer");
    assert_eq!(
        lines[0].text,
        "266 of 268 RAWs on this PC · 2 behind · 38 MB/s on Wi-Fi"
    );
    assert_eq!(lines[0].mark, Mark::Ok);
    assert!((lines[0].fraction.unwrap() - 266.0 / 268.0).abs() < 1e-6);
    assert_eq!(
        lines[1].text,
        "61 planes checked · 53 passed first time · 4 retaken (3 then passed) · 1 being retaken · 4 stacked from one shot"
    );
    assert_eq!(lines[1].mark, Mark::Warn);
    assert!(lines[2].text.ends_with("355 GB free"));
    // Written never passes the whole: the retakes' RAWs are expected too.
    let disk = lines[2].fraction.unwrap();
    let expected = 96.0 * 4.0 + p.retakes as f32 * 4.0;
    assert!(disk < 1.0 && (disk - 266.0 / expected).abs() < 1e-6);
    assert_eq!(lines[3].title, "Rig");
    let off = health(&s, None, false);
    assert!(off[1].text.starts_with("Off"));
    let (mark, word) = needs_you(&s, &lines);
    assert_eq!((mark, word), (Mark::Warn, "Worth a look"));
}

/// The headline counts planes once and RAWs with their retakes; it never
/// says "X of Y RAWs" (the owner saw 1,040 of 844).
#[test]
fn the_headline_counts_planes_once_and_retakes_apart() {
    let mut state = capturing();
    state["completed"] = json!(211);
    state["total"] = json!(211);
    state["storage"]["captured_frames"] = json!(1040);
    let s = snapshot(state);
    let p = owner_progress();
    let h = headline(&s, Some(&p));
    assert_eq!((h.plane, h.total, h.fraction), (211, 211, 1.0));
    assert_eq!((h.raws_taken, h.raws_for_retakes), (1040, 196));
    assert_eq!((h.retakes, h.retaken_planes), (49, 34));
}

#[test]
fn the_rail_ticks_follow_the_planes() {
    let s = snapshot(capturing());
    let p = journal();
    let positions: Vec<u16> = (0..96).map(|i| 37100 + i * 7).collect();
    let ticks = flight_ticks(positions, &s, Some(&p));
    assert_eq!(ticks.states.len(), 96);
    assert_eq!(ticks.states[38], TickState::Retaken, "plane 39");
    assert_eq!(
        ticks.states[23],
        TickState::Attention,
        "plane 24 not retaken"
    );
    assert_eq!(
        ticks.states[60],
        TickState::Checked,
        "plane 61 passed its check"
    );
    assert_eq!(ticks.states[0], TickState::Checked);
    assert_eq!(ticks.states[61], TickState::ToCome);
    // Without the checker: 242 of 244 RAWs here, so plane 61 is on the host.
    let mut state = capturing();
    state["storage"]["captured_frames"] = json!(244);
    state["storage"]["saved_frames"] = json!(242);
    let s = snapshot(state);
    let positions: Vec<u16> = (0..96).map(|i| 37100 + i * 7).collect();
    let plain = flight_ticks(positions, &s, None);
    assert_eq!(plain.states[59], TickState::Checked);
    assert_eq!(plain.states[60], TickState::OnHost);
}

fn host_at(completed: u64, groups: u64, elapsed: f64, total: u64) -> Snapshot {
    let mut state = capturing();
    state["completed"] = json!(completed);
    state["total"] = json!(total);
    state["storage"]["captured_frames"] = json!(groups * 4);
    state["timer"] = json!({"elapsed":elapsed,"remaining":100.0});
    snapshot(state)
}

/// The retakes' cost is the time between planes beyond the plain pace,
/// from the host's counts. Paced as the owner's run (5.7 s a plane, about
/// 10.2 s a retake in its `events.jsonl`): 10.2 s a retake.
#[test]
fn the_retake_clock_times_what_retakes_add() {
    let mut clock = RetakeClock::default();
    let (mut done, mut groups, mut t) = (0, 0, 0.0);
    clock.observe(&host_at(done, groups, t, 211));
    let mut retakes = 0;
    for plane in 1..=40u64 {
        // A retake every tenth plane, taken before the next plane.
        let retake = plane % 10 == 0 && plane > 10;
        t += 5.7 + if retake { 10.2 } else { 0.0 };
        groups += 1 + u64::from(retake);
        retakes += u64::from(retake);
        done += 1;
        // A poll between, with the group taken and the plane not counted.
        clock.observe(&host_at(done - 1, groups, t - 1.0, 211));
        clock.observe(&host_at(done, groups, t, 211));
    }
    assert_eq!(retakes, 3);
    assert!((clock.plain_pace().unwrap() - 5.7).abs() < 1e-9);
    assert_eq!(clock.timed, 3);
    let cost = clock.cost(retakes).unwrap();
    assert!((cost - 30.6).abs() < 1e-6, "{cost}");
    // Retakes not seen (the desktop started mid-run) at the timed average.
    assert!((clock.cost(5).unwrap() - 51.0).abs() < 1e-6);
    assert_eq!(clock.cost(0), None);
    // After the last plane, the final retakes' time is all theirs.
    let mut end = RetakeClock::default();
    end.observe(&host_at(211, 300, 2000.0, 211));
    end.observe(&host_at(211, 301, 2011.0, 211));
    assert!((end.seconds - 11.0).abs() < 1e-6 && end.timed == 1);
    // A new capture starts again.
    let mut state = capturing();
    state["sequence_id"] = json!(3);
    clock.observe(&snapshot(state));
    assert_eq!((clock.timed, clock.plain_pace()), (0, None));
}

/// The time left counts down by the second and eases to the host's
/// estimate, so a retake's jump does not shake it; a large change (a new
/// estimate far off) is taken at once.
#[test]
fn the_time_left_counts_down_smoothly() {
    let mut clock = LeftClock::default();
    let start = Instant::now();
    let at = |s: f64| start + Duration::from_secs_f64(s);
    assert_eq!(
        clock.update(Some(600.0), Some(2), true, at(0.0)),
        Some(600.0)
    );
    // Five polls a second with the host's estimate jumping by 12 s (as a
    // plane's pace changes): the shown time only falls, about a second a
    // second.
    let mut last = 600.0;
    for i in 1..=300 {
        let t = i as f64 * 0.2;
        let jitter = if i % 28 < 14 { 6.0 } else { -6.0 };
        let shown = clock
            .update(Some(600.0 - t + jitter), Some(2), true, at(t))
            .unwrap();
        assert!(shown <= last + 1e-9, "at {t}: {shown} after {last}");
        assert!((shown - (600.0 - t)).abs() < 7.0);
        last = shown;
    }
    // A retake adds 10 s to the estimate: eased in, not jumped.
    let before = clock.update(Some(530.0), Some(2), true, at(60.2)).unwrap();
    let after = clock.update(Some(540.0), Some(2), true, at(60.4)).unwrap();
    assert!((after - before).abs() < 1.0, "{before} -> {after}");
    // Paused: it does not count down.
    let held = clock.update(Some(540.0), Some(2), false, at(70.0)).unwrap();
    let still = clock.update(Some(540.0), Some(2), false, at(75.0)).unwrap();
    assert!(still >= held);
    assert_eq!(
        clock.update(Some(1500.0), Some(2), true, at(75.2)),
        Some(1500.0)
    );
    assert_eq!(clock.update(None, Some(2), true, at(75.4)), None);
}

thread_local! {
    static CLOCK: std::cell::Cell<f64> = const { std::cell::Cell::new(0.0) };
}
/// Frame times only move forward within a context.
fn tick() -> f64 {
    CLOCK.with(|c| {
        c.set(c.get() + 0.05);
        c.get()
    })
}

fn inputs<'a>(s: &'a Snapshot, p: Option<&'a Progress>) -> FlightInputs<'a> {
    FlightInputs {
        s,
        progress: p,
        checking: true,
        stack_when_done: true,
        power_down: Some(true),
        confirm_stop: false,
        left: Some(198.0),
        retake_cost: Some(61.2),
        plain_pace: Some(5.6),
        ended: false,
        ended_at: None,
        stack_stopped: None,
        retakes: RetakeInputs::default(),
    }
}

fn frame(
    ctx: &egui::Context,
    input: &FlightInputs<'_>,
    events: Vec<Event>,
) -> (FullOutput, Vec<FlightIntent>) {
    let time = tick();
    let mut intents = Vec::new();
    let palette = CapturePalette::default();
    let out = ctx.run(
        RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(348.0, 982.0))),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| intents = inspector(ui, input, &palette));
        },
    );
    (out, intents)
}

fn click(ctx: &egui::Context, input: &FlightInputs<'_>, label: &str) -> Vec<FlightIntent> {
    let (out, _) = frame(ctx, input, vec![]);
    let at = texts(&out)
        .into_iter()
        .find(|t| t.0 == label)
        .map(|t| t.1.center())
        .unwrap_or_else(|| panic!("{label} is not drawn"));
    let press = |pressed| Event::PointerButton {
        pos: at,
        button: PointerButton::Primary,
        pressed,
        modifiers: Default::default(),
    };
    let mut all = frame(ctx, input, vec![Event::PointerMoved(at), press(true)]).1;
    all.extend(frame(ctx, input, vec![press(false)]).1);
    all
}

/// Stop asks first; the confirmation stops; Glance opens glance. Once the
/// capture ended, the foot offers New capture and Back to the plan.
#[test]
fn stop_asks_first_and_glance_opens() {
    let ctx = egui::Context::default();
    let s = snapshot(capturing());
    let p = journal();
    let mut input = inputs(&s, Some(&p));
    assert_eq!(click(&ctx, &input, "Stop…"), [FlightIntent::AskStop]);
    assert_eq!(click(&ctx, &input, "Pause"), [FlightIntent::Pause]);
    assert_eq!(click(&ctx, &input, "Glance"), [FlightIntent::Glance]);
    input.confirm_stop = true;
    assert_eq!(click(&ctx, &input, "Stop now"), [FlightIntent::Stop]);
    assert_eq!(click(&ctx, &input, "Keep going"), [FlightIntent::KeepGoing]);
    input.confirm_stop = false;
    input.ended = true;
    assert_eq!(
        click(&ctx, &input, "Back to the plan"),
        [FlightIntent::Done]
    );
    assert_eq!(
        click(&ctx, &input, "New capture"),
        [FlightIntent::NewCapture]
    );
    // Plan Q6: a capture stopped with planes taken offers to stack them.
    input.stack_stopped = Some(24);
    assert_eq!(
        click(&ctx, &input, "Stack 24 planes"),
        [FlightIntent::StackStopped]
    );
    assert_eq!(
        click(&ctx, &input, "New capture"),
        [FlightIntent::NewCapture]
    );
}

/// Draws the canvas at `size` and returns its output and intents.
fn canvas_frame(
    ctx: &egui::Context,
    input: &FlightInputs<'_>,
    view: &mut FlightView,
    size: egui::Vec2,
    events: Vec<Event>,
) -> (FullOutput, Vec<FlightIntent>) {
    let palette = CapturePalette::default();
    let mut intents = Vec::new();
    let out = ctx.run(
        RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, size)),
            time: Some(tick()),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| intents = canvas(ui, input, view, &palette));
        },
    );
    (out, intents)
}

/// Every text drawn, with its rectangle.
fn texts(out: &FullOutput) -> Vec<(String, Rect)> {
    fn walk(shape: &egui::Shape, out: &mut Vec<(String, Rect)>) {
        match shape {
            egui::Shape::Text(t) => {
                out.push((t.galley.text().to_owned(), t.visual_bounding_rect()))
            }
            egui::Shape::Vec(parts) => parts.iter().for_each(|p| walk(p, out)),
            _ => {}
        }
    }
    let mut v = Vec::new();
    for s in &out.shapes {
        walk(&s.shape, &mut v);
    }
    v
}

/// A text shape's first baseline, in screen points.
fn baseline_of(out: &FullOutput, text: &str) -> f32 {
    out.shapes
        .iter()
        .find_map(|s| match &s.shape {
            egui::Shape::Text(t) if t.galley.text() == text => {
                Some(t.pos.y + style::baseline(&t.galley))
            }
            _ => None,
        })
        .unwrap_or_else(|| panic!("{text} is not drawn"))
}

/// The canvas: G opens glance; the headline says plane, total, time left,
/// RAWs with their retakes and the retakes' cost; the plane and its total
/// share one baseline.
#[test]
fn the_canvas_reads_the_headline_and_g_opens_glance() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let s = snapshot(capturing());
    let p = journal();
    let input = inputs(&s, Some(&p));
    let mut view = FlightView::default();
    let g = Event::Key {
        key: egui::Key::G,
        physical_key: None,
        pressed: true,
        repeat: false,
        modifiers: Default::default(),
    };
    let size = egui::vec2(1332.0, 855.0);
    let (out, intents) = canvas_frame(&ctx, &input, &mut view, size, vec![g]);
    assert_eq!(intents, [FlightIntent::Glance]);
    let all: Vec<String> = texts(&out).into_iter().map(|t| t.0).collect();
    for want in [
        "61",
        "of 96",
        "3:18",
        "On track",
        "5.6 s a plane",
        "268 RAWs taken · 24 for retakes",
        "6 retakes of 4 planes · +61 s",
        "Four shots agree",
        "PLANES · 61 CHECKED",
    ] {
        assert!(all.iter().any(|t| t == want), "{want}: {all:?}");
    }
    assert!(
        !all.iter()
            .any(|t| t.contains("RAWs taken") && t.contains(" of "))
    );
    // The big number and the small "of 96" stand on one line.
    let a = baseline_of(&out, "61");
    let b = baseline_of(&out, "of 96");
    assert!((a - b).abs() < 0.6, "plane {a}, total {b}");
}

/// Nothing in the headline moves as the time left changes: its figures sit
/// in fixed cells, and the bar between is laid out from fixed slots.
#[test]
fn the_headline_does_not_shift_as_the_time_left_ticks() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let s = snapshot(capturing());
    let p = journal();
    let mut view = FlightView::default();
    let mut edges = Vec::new();
    for left in [198.0, 111.0, 171.0, 199.4, 1.0] {
        let mut input = inputs(&s, Some(&p));
        input.left = Some(left);
        let size = egui::vec2(1332.0, 855.0);
        let (out, _) = canvas_frame(&ctx, &input, &mut view, size, vec![]);
        let texts = texts(&out);
        let started = texts
            .iter()
            .find(|t| t.0.starts_with("started "))
            .expect("started")
            .1;
        let of = texts.iter().find(|t| t.0 == "of 96").expect("of 96").1;
        edges.push((started.right(), of.left()));
    }
    for w in edges.windows(2) {
        assert!((w[0].0 - w[1].0).abs() < 0.01, "{edges:?}");
        assert!((w[0].1 - w[1].1).abs() < 0.01, "{edges:?}");
    }
}

/// A feed row's plane number (the column left of the titles).
fn is_plane_number(t: &(String, Rect)) -> bool {
    t.0.parse::<u64>().is_ok() && t.1.left() > 980.0 && t.1.left() < 1000.0
}

/// The feed fills its column and scrolls; with 5,400 planes it lays out
/// only the rows in view, newest at the top and followed; scrolled away it
/// stays where it is; "Show" on a failed try asks for that try's RAW.
#[test]
fn the_feed_scrolls_follows_the_newest_and_shows_a_try() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let (p, groups) = fixture::long_progress();
    let mut s = snapshot(capturing());
    fixture::lengthen(&mut s, groups);
    let input = inputs(&s, Some(&p));
    let mut view = FlightView::default();
    let size = egui::vec2(1332.0, 855.0);
    let mut out = None;
    for _ in 0..3 {
        out = Some(canvas_frame(&ctx, &input, &mut view, size, vec![]).0);
    }
    let out = out.unwrap();
    assert!(p.feed.len() > 5_600, "{}", p.feed.len());
    assert!(
        view.rows_drawn > 3 && view.rows_drawn < 30,
        "{}",
        view.rows_drawn
    );
    // The newest item is the first row.
    let newest = p.feed.last().unwrap().plane.to_string();

    let first_row = texts(&out)
        .into_iter()
        .filter(is_plane_number)
        .min_by(|a, b| a.1.top().total_cmp(&b.1.top()))
        .unwrap();
    assert_eq!(first_row.0, newest);
    // Scrolling down leaves the newest behind.
    let over = egui::pos2(1150.0, 700.0);
    let wheel = |dy: f32| Event::MouseWheel {
        unit: egui::MouseWheelUnit::Point,
        delta: egui::vec2(0.0, dy),
        modifiers: Default::default(),
    };
    for _ in 0..6 {
        canvas_frame(
            &ctx,
            &input,
            &mut view,
            size,
            vec![Event::PointerMoved(over), wheel(-400.0)],
        );
    }
    let mut show = None;
    for _ in 0..60 {
        // Smooth scrolling runs over several frames: let it settle.
        for _ in 0..30 {
            canvas_frame(&ctx, &input, &mut view, size, vec![]);
        }
        let (out, _) = canvas_frame(&ctx, &input, &mut view, size, vec![]);
        assert!(!texts(&out).iter().any(|t| t.0 == newest));
        show = texts(&out)
            .into_iter()
            .find(|t| t.0 == "SHOW" && t.1.top() > 520.0 && t.1.bottom() < 820.0)
            .map(|t| t.1.center());
        if show.is_some() {
            break;
        }
        canvas_frame(
            &ctx,
            &input,
            &mut view,
            size,
            vec![Event::PointerMoved(over), wheel(-60.0)],
        );
    }
    // Show on a failed try in view.
    let at = show.expect("a failed try in view");
    let press = |pressed| Event::PointerButton {
        pos: at,
        button: PointerButton::Primary,
        pressed,
        modifiers: Default::default(),
    };
    // The pointer comes to rest on it, then presses.
    for _ in 0..10 {
        canvas_frame(&ctx, &input, &mut view, size, vec![Event::PointerMoved(at)]);
    }
    canvas_frame(&ctx, &input, &mut view, size, vec![press(true)]);
    let (_, intents) = canvas_frame(&ctx, &input, &mut view, size, vec![press(false)]);
    match intents.as_slice() {
        [
            FlightIntent::ShowPlane {
                plane,
                raw: Some(raw),
            },
        ] => {
            assert!(raw.starts_with("frame-"), "{raw}");
            let item = p
                .feed
                .iter()
                .find(|i| i.first.as_deref() == Some(&**raw))
                .unwrap();
            assert_eq!(item.plane, *plane);
            assert!(!item.verdict.passed() || item.attempt > 1);
        }
        other => panic!("{other:?}"),
    }
}

/// New tries arriving while the feed is scrolled away from the newest do
/// not move the rows in view; at the top, the newest is shown.
#[test]
fn a_scrolled_feed_stays_put_as_it_grows() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let (lines, _) = fixture::journal(20_000, 400, fixture::long_checks);
    let text = |n: usize| {
        lines[..n]
            .iter()
            .map(|l| l.to_string())
            .collect::<Vec<_>>()
            .join("\n")
    };
    let before = follow::progress(&text(380));
    let after = follow::progress(&text(395));
    let s = snapshot(capturing());
    let size = egui::vec2(1332.0, 855.0);
    let mut view = FlightView::default();
    let over = egui::pos2(1150.0, 700.0);
    let wheel = Event::MouseWheel {
        unit: egui::MouseWheelUnit::Point,
        delta: egui::vec2(0.0, -600.0),
        modifiers: Default::default(),
    };
    let input = inputs(&s, Some(&before));
    canvas_frame(
        &ctx,
        &input,
        &mut view,
        size,
        vec![Event::PointerMoved(over), wheel],
    );
    let mut out = None;
    for _ in 0..40 {
        out = Some(canvas_frame(&ctx, &input, &mut view, size, vec![]).0);
    }
    let rows = |out: &FullOutput| -> Vec<(String, f32)> {
        texts(out)
            .into_iter()
            .filter(is_plane_number)
            .map(|t| (t.0, t.1.top()))
            .collect()
    };
    let held = rows(&out.unwrap());
    assert!(!held.is_empty());
    let grown = inputs(&s, Some(&after));
    let (out, _) = canvas_frame(&ctx, &grown, &mut view, size, vec![]);
    let (out2, _) = canvas_frame(&ctx, &grown, &mut view, size, vec![]);
    for out in [&out, &out2] {
        let now = rows(out);
        for (plane, top) in &held {
            let moved = now.iter().find(|(p, _)| p == plane).map(|(_, t)| *t);
            assert_eq!(moved, Some(*top), "plane {plane} moved");
        }
    }
    // Back at the top, the newest try is the first row.
    let up = Event::MouseWheel {
        unit: egui::MouseWheelUnit::Point,
        delta: egui::vec2(0.0, 100_000.0),
        modifiers: Default::default(),
    };
    canvas_frame(
        &ctx,
        &grown,
        &mut view,
        size,
        vec![Event::PointerMoved(over), up],
    );
    let mut out = None;
    for _ in 0..60 {
        out = Some(canvas_frame(&ctx, &grown, &mut view, size, vec![]).0);
    }
    let newest = after.feed.last().unwrap().plane.to_string();
    let top_row = texts(&out.unwrap())
        .into_iter()
        .filter(is_plane_number)
        .min_by(|a, b| a.1.top().total_cmp(&b.1.top()))
        .unwrap();
    assert_eq!(top_row.0, newest);
}

/// The rows' positions grow only at the end as the feed grows, and are
/// rebuilt when its oldest items were dropped.
#[test]
fn feed_rows_are_positioned_once() {
    let p = owner_progress();
    let mut view = FlightView::default();
    let (tops, height) = view.tops(&p.feed[..100]);
    assert_eq!(tops.len(), 100);
    let first = (tops.to_vec(), height);
    let (tops, _) = view.tops(&p.feed);
    assert_eq!(&tops[..100], &first.0[..]);
    assert_eq!(tops[100], first.1);
    let (tops, _) = view.tops(&p.feed[10..]);
    assert_eq!((tops.len(), tops[0]), (250, 0.0));
}

/// The plane view's place fills the canvas beside the side column, under
/// the headline; the feed starts at the same height (no picture above it).
#[test]
fn the_plane_view_has_the_space_beside_the_feed() {
    let ctx = egui::Context::default();
    let s = snapshot(capturing());
    let p = journal();
    let input = inputs(&s, Some(&p));
    let mut view = FlightView::default();
    for ((w, h), side) in [
        ((1332.0, 855.0), 340.0),
        ((940.0, 600.0), 340.0),
        ((2212.0, 1229.0), 460.0),
    ] {
        let size = egui::vec2(w, h);
        let (out, _) = canvas_frame(&ctx, &input, &mut view, size, vec![]);
        let plane = view.plane.expect("the canvas places the plane view");
        // Head (20 + 108 + 20 above), 16 below; 24 + 14 + side + 24 across.
        assert_eq!(plane.width(), w - 48.0 - 14.0 - side, "{plane:?}");
        assert_eq!(plane.height(), h - 148.0 - 16.0, "{plane:?}");
        let planes = texts(&out)
            .into_iter()
            .find(|t| t.0.starts_with("PLANES ·"))
            .expect("the feed's head");
        assert!(
            (planes.1.top() - plane.top()).abs() < 4.0 && planes.1.left() > plane.right(),
            "{planes:?} beside {plane:?}"
        );
    }
}

/// Once the capture ended the feed opens with what happened in words and
/// why each kind of failure was or was not retaken.
#[test]
fn the_review_says_what_happened_and_why() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let mut state = capturing();
    state["phase"] = json!("complete");
    let s = snapshot(state);
    let p = owner_progress();
    let mut input = inputs(&s, Some(&p));
    input.ended = true;
    let mut view = FlightView::default();
    let size = egui::vec2(1332.0, 1100.0);
    let (out, _) = canvas_frame(&ctx, &input, &mut view, size, vec![]);
    let all: Vec<String> = texts(&out).into_iter().map(|t| t.0).collect();
    assert!(
        all.iter()
            .any(|t| t.starts_with("211 planes checked: 159 passed"))
    );
    assert!(
        all.iter()
            .any(|t| t.starts_with("Shift pattern off · 17 tries"))
    );
    assert!(
        all.iter()
            .any(|t| t.contains("expects a retake to fail the same way"))
    );
    assert!(all.iter().any(|t| t == "Finished"));
}

/// The start of a capture says what it is doing (owner feedback,
/// 2026-11-23: it "just sits there"): the light's warm-up with its seconds
/// and a share of the bar, the approach move, and from an older host its
/// message until the first RAW. Once planes are taken it is gone.
#[test]
fn the_start_says_warm_up_and_approach() {
    let mut state = capturing();
    state["completed"] = json!(0);
    state["storage"]["captured_frames"] = json!(0);
    state["starting"] = json!({"stage":"light","elapsed":12.4,"seconds":60.0});
    let h = headline(&snapshot(state.clone()), None);
    let (text, fraction) = h.starting.unwrap();
    assert_eq!(text, "Warming the light: 12 of 60 s");
    assert!((fraction.unwrap() - 12.4 / 60.0).abs() < 1e-4);
    state["starting"] = json!({"stage":"light","elapsed":0.1,"seconds":0.0});
    assert_eq!(
        headline(&snapshot(state.clone()), None).starting.unwrap().0,
        "The light is warm"
    );
    state["starting"] = json!({"stage":"approach","elapsed":2.2});
    let (text, fraction) = headline(&snapshot(state.clone()), None).starting.unwrap();
    assert!(text.starts_with("Moving to the start"), "{text}");
    assert!(fraction.is_none());
    // An older host: its message, until the first RAW.
    state.as_object_mut().unwrap().remove("starting");
    state["message"] = json!("Studio light on · warming for 60 s");
    assert_eq!(
        headline(&snapshot(state.clone()), None).starting.unwrap().0,
        "Studio light on · warming for 60 s"
    );
    assert!(headline(&snapshot(capturing()), None).starting.is_none());
}
