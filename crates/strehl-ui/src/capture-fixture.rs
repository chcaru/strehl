//! Offscreen fixtures for the Capture station (`--capture-fixture`): a
//! planned stack, a capture in flight and glance mode, from a fabricated
//! host state and synthetic pictures. A fixture connection sends nothing; no
//! camera, light or Pi is reached. For checking the screens against the
//! mockups and for tests.
use std::sync::Arc;
use std::time::{Instant, SystemTime};

use eframe::egui::{Color32, ColorImage};
use serde_json::{Value, json};

use super::follow::{self, Progress};
use super::test_shot::RawLevels;
use crate::capture_aids::{Peaking, PreviewLevels};
use crate::capture_client::{Snapshot, StoredRaws};

/// Which screen a fixture shows.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Fixture {
    Plan,
    Flight,
    Glance,
}

impl Fixture {
    pub fn parse(name: &str) -> Option<Self> {
        match name {
            "plan" => Some(Self::Plan),
            "flight" => Some(Self::Flight),
            "glance" => Some(Self::Glance),
            _ => None,
        }
    }
}

/// The calibration pass's facts for the fixtures (spec 9, S2): a sweep
/// over the fixture's subject (the oval of [`subject_image`] at 960 x 640,
/// in focus from 37,100 at its left to 37,764 at its right), and, once
/// `surveyed`, a survey read from RAW.
pub(crate) fn pass_facts(surveyed: bool) -> super::measure::Facts {
    let (w, h) = (960usize, 640usize);
    let (cols, rows) = (w / super::sweep::TILE, h / super::sweep::TILE);
    let inside = |fx: f64, fy: f64| {
        let (dx, dy) = ((fx - 0.5) / 0.34, (fy - 0.52) / 0.30);
        dx * dx + dy * dy <= 0.92
    };
    let focus_at = |fx: f64| 37_100.0 + 664.0 * ((fx - 0.16) / 0.68).clamp(0.0, 1.0);
    let focus: Vec<Option<f64>> = (0..cols * rows)
        .map(|t| {
            let (fx, fy) = (
                (t % cols) as f64 / cols as f64 + 0.5 / cols as f64,
                (t / cols) as f64 / rows as f64 + 0.5 / rows as f64,
            );
            // A few tiles with no peak, as a real sweep leaves.
            (inside(fx, fy) && (t * 7919) % 23 != 0).then(|| focus_at(fx).round())
        })
        .collect();
    let kept = focus.iter().flatten().count();
    let peaks = super::sweep::Peaks {
        cols,
        rows,
        focus,
        range: Some((37_100.0, 37_764.0)),
        busiest: Some(37_430.0),
        kept,
        at_first: 0,
        at_last: 0,
        prominent: kept + 12,
        window: (34_430.0, 40_430.0),
        offset: 22.5,
    };
    let survey = surveyed.then(|| {
        // 64 px tiles of the 9,504 x 6,336 sensor.
        let (c, r) = (148usize, 99usize);
        let focus: Vec<Value> = (0..c * r)
            .map(|t| {
                let (fx, fy) = (
                    (t % c) as f64 / c as f64 + 0.5 / c as f64,
                    (t / c) as f64 / r as f64 + 0.5 / r as f64,
                );
                if inside(fx, fy) && (t * 104_729) % 31 != 0 {
                    json!(focus_at(fx).round())
                } else {
                    Value::Null
                }
            })
            .collect();
        json!({
            "subject":{"area_share":0.287},
            "depth":{"in_focus_first":37_112.0,"in_focus_last":37_758.0,"reaches_first":false,"reaches_last":false,
                "suggested_start":37_087.0,"suggested_end":37_783.0,
                "per_position":(0..24).map(|i| {
                    let at = 36_980.0 + 45.0 * f64::from(i);
                    // Tiles in focus: none outside the range, a band of the
                    // oval's width inside it.
                    let n = if (37_112.0..=37_758.0).contains(&at) {
                        (420.0 * (1.0 - ((at - 37_435.0) / 400.0).powi(2))).round()
                    } else {
                        0.0
                    };
                    json!([at, n])
                }).collect::<Vec<_>>()},
            "maps":{"cols":c,"rows":r,"tile_px":64,"focus":focus},
            "step":{"width":45.0,"width_p10":35.0,"width_p90":59.0,"suggested_step":6,"positions":25,"spacing":9.0,"width_low":false},
            "body":{"top":0.62,"g":{"p50":0.008}},
            "census":{"top":30.1},
            "shutters":{"long_effective_s":1.0,"short_effective_s":0.03125},
            "positions":{"pairs":13}
        })
    });
    super::measure::Facts {
        peaks: Some(peaks),
        sweep_seconds: Some(36.2),
        sweep_positions: 33,
        // Where the fixture's lens stands: every tile at full colour.
        busiest: Some(37_556),
        test_top: Some(0.48),
        shutters: Some((65_537, 65_568)),
        light_on_seconds: Some(240.0),
        survey,
        preview_size: Some([w, h]),
        revision: 1 + u64::from(surveyed),
    }
}

/// A textured oval on black, as a camera preview of a small subject.
pub(crate) fn subject_image(width: usize, height: usize, sharp: f32) -> ColorImage {
    let mut image = ColorImage::filled([width, height], Color32::BLACK);
    let (cx, cy) = (width as f32 * 0.5, height as f32 * 0.52);
    let (rx, ry) = (width as f32 * 0.34, height as f32 * 0.30);
    for y in 0..height {
        for x in 0..width {
            let (dx, dy) = ((x as f32 - cx) / rx, (y as f32 - cy) / ry);
            let r = dx * dx + dy * dy;
            if r > 1.0 {
                continue;
            }
            let band = ((dx * 9.0).sin() * 0.5 + 0.5) * sharp + 0.5 * (1.0 - sharp);
            let speckle = (((x * 7919 + y * 104_729) % 97) as f32 / 97.0 - 0.5) * 0.25 * sharp;
            let v = (0.25 + 0.55 * band + speckle).clamp(0.0, 1.0) * (1.0 - r * 0.35);
            image.pixels[y * width + x] = Color32::from_rgb(
                (40.0 + 60.0 * v) as u8,
                (90.0 + 150.0 * v) as u8,
                (110.0 + 120.0 * v) as u8,
            );
        }
    }
    image
}

fn plan_state() -> Value {
    let samples: Vec<Value> = (0..33)
        .map(|i| {
            let position = 36_980 + i * 28;
            let inside = (37_100..=37_764).contains(&position);
            let peak = if inside {
                0.45 + 0.4 * ((f64::from(position - 37_100) / 664.0) * 3.0).sin().abs()
            } else {
                0.04
            };
            json!({"position":position,"scores":vec![peak; 24]})
        })
        .collect();
    json!({"camera_revision":4,"plan_revision":3,"sequence_id":2,"phase":"ready","connected":true,
        "busy":false,"editable":true,"message":"Connected · A7CR four-shot pixel shift saves to the PC",
        "demo":false,"camera_model":"ILCE-7CR","usb_speed_mbps":5000,"position":37556,
        "plan":{"start":37100,"end":37764,"step":7,"settle_ms":500,"approach":128,"capture_timeout_s":120},
        "start_set":true,"end_set":true,"planned":96,"initial_seconds":540.0,"shots_per_plane":4,
        "pixel_shift_options":[1,4],"raw_max_bytes":130_000_000u64,"storage_required_bytes":64_700_000_000u64,
        "storage":{"mode":"host-pc","free_bytes":371_000_000_000u64},
        "power":{"light":{"on":true,"watts":41.0},"camera":{"on":true,"watts":2.1},"available":true,
            "can_start_camera":false,"can_stop_camera":true,"can_manage":true,"manage_stack":true,"warmup_seconds":5},
        "exposure":{"iso":100,"shutter":65544,"f_number":560,"iso_options":[100,200,400,800,1600,3200],
            "shutter_options":[65561,65556,65551,65549,65546,65544,65542,65541,65540,65539,262154,65538,393226,524298,65537],"writable":true,"mode":"M","problem":null},
        "preview":{"available":true,"fresh":true,"generation":7,"age_seconds":0.2,"width":960,"height":640},
        "samples":samples,"magnifier_ratios":[0,59,117],"magnifier_current":59,
        "suggestion":{"start":37100,"end":37764,"supported_tiles":20,"clipped":false,"explanation":"Sharp detail from 37,100 to 37,764"},
        "capabilities":{"test_shot":true,"exposure_check":true,"max_retakes":true,"queue_retakes":true,"new_plan":true},
        "retakes":{"max":2,"limit":5,"accepted":false,"queued":[],"run":null,"followup":null},
        "error_correction":false,
        "schedule":{"job":null,"error":null},"pending_control":0,"completed":0,"total":0})
}

/// `plan+survey`: a host that takes a shutter per position and holds a
/// subject outline (plans X1, S1), for the rows and tools they bring.
pub(crate) fn survey_snapshot() -> Snapshot {
    let mut state = plan_state();
    state["capabilities"]["exposure_tiers"] = json!(true);
    state["capabilities"]["subject"] = json!(true);
    state["plan"]["subject"] = json!({"rings":[[[0.18,0.22],[0.62,0.14],[0.83,0.4],[0.74,0.78],
        [0.34,0.86],[0.12,0.6]]],"reference_focus":37500,"rate_ppm":null,
        "provenance":{"kind":"auto"}});
    snapshot_from(Fixture::Plan, state)
}

/// What Calibrate step reports from a two-shutter survey (`strehl survey`
/// on the pronotum, 2026-11-24, the fields the desktop reads).
pub(crate) fn survey_result() -> Value {
    json!({"width":72.3,"suggested_step":10,
        "summary":"Subject found (28.7 % of the frame), sharp from focus 37,100 to 37,764. Suggested: the highlight pass.",
        "survey":{"advice":{"suggested":"highlight_pass",
            "highlight_pass":{"base_code":1310730,"short_code":65561},
            "protect":{"code":65561},
            "accept":{"code":1310730,"pinned_sites_per_plane":9341.7}},
            "census":{"top":2.55}}})
}

/// The host's state, the receiver and the pictures for `fixture`.
pub(crate) fn snapshot(fixture: Fixture) -> Snapshot {
    snapshot_from(fixture, plan_state())
}

fn snapshot_from(fixture: Fixture, mut state: Value) -> Snapshot {
    if fixture != Fixture::Plan {
        let captured = flight_groups() * 4;
        for (key, value) in [
            ("phase", json!("capturing")),
            ("editable", json!(false)),
            ("completed", json!(61)),
            ("total", json!(96)),
            ("position", json!(37520)),
            ("message", json!("Plane 61 of 96 · focus 37520")),
            ("error_correction", json!(true)),
            (
                "timer",
                json!({"elapsed":341.6,"remaining":198.0,"finished":false,"paused":false}),
            ),
            (
                "storage",
                json!({"mode":"host-pc","free_bytes":355_000_000_000u64,"pipelined":true,
                    "captured_frames":captured,"saved_frames":captured - 2,"pending_frames":2,
                    "receipt":{"wire_MB_per_second":38.2}}),
            ),
        ] {
            state[key] = value;
        }
    }
    let image = Arc::new(subject_image(960, 640, 1.0));
    let mut s = Snapshot {
        online: true,
        observed: Some(Instant::now()),
        receiver: json!({"ok":true,"free_bytes":371_000_000_000u64,"compress_raw":true,"archive_format":2,
            "folder":"D:\\Captures"}),
        stored: vec![StoredRaws {
            folder: "stack-fixture".into(),
            model: "ILCE-7CR".into(),
            raw_format: "sony-uncompressed".into(),
            raws: 784,
            original: 125_600_000,
            stored: 65_000_000,
            encoding: "strehl-archive-v2".into(),
        }],
        peaking: Some((7, Arc::new(Peaking::analyze(&image)))),
        levels: Some((7, Arc::new(PreviewLevels::analyze(&image)))),
        preview: Some((7, image)),
        ..Default::default()
    };
    s.set_state(state);
    s
}

/// The engine's reasons as `strehl follow` writes them (`pixel-shift-cmd.rs`
/// `demotion`), for fabricated journals.
pub(crate) const MOTION: &str = "witness tiles disagree locally by 0.86 px at p99 (limit 0.51): motion, a focus slip or a wrong member";
pub(crate) const PATTERN: &str =
    "offsets [(0, -1), (1, -1), (1, 1)] do not cover the four CFA parities";
#[cfg(test)]
pub(crate) const SLIP: &str = "offsets [(0, -1), (1, -2), (1, 0)] do not cover the four CFA parities: a shot slipped by a whole photosite";
pub(crate) const RESIDUAL: &str =
    "witness pairs misregistered by 0.204 photosite after residual compensation";
pub(crate) const MISREGISTERED: &str =
    "witness pairs misregistered by 0.228 photosite after residual compensation";

/// What one fabricated group's check says.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Check {
    Pass,
    /// Demoted, with the engine's reason and whether a retake could help.
    Demote(&'static str, bool),
}

/// A journal line as `strehl follow` writes it (the fields the desktop
/// reads), for a stack starting at focus `start` with a step of 7.
pub(crate) fn journal_line(
    start: u64,
    plane: u64,
    attempt: u32,
    frame: u64,
    check: Check,
) -> Value {
    let target = start + (plane - 1) * 7;
    let group = if attempt == 1 {
        format!("g{plane}")
    } else {
        format!("g{plane}-{attempt}")
    };
    let names: Vec<String> = (0..4)
        .map(|k| format!("frame-{:06}.ARW", frame + k))
        .collect();
    let seconds = 0.26 + (plane % 3) as f64 * 0.01;
    match check {
        Check::Pass => json!({"plane":plane,"target":target,"group_id":group,"verdict":"pass",
            "reason":null,"retake":false,"members":4,"names":names,"seconds":seconds}),
        Check::Demote(reason, retake) => json!({"plane":plane,"target":target,"group_id":group,
            "verdict":"demote","reason":reason,"retake":retake,"members":4,"names":names,
            "seconds":seconds}),
    }
}

/// A fabricated run's journal in the order the checker writes it: a retake
/// is taken after the next plane (the host's deferred retake), so its line
/// follows that plane's. `checks(plane)` gives each try's check, first try
/// first. Returns the lines and the groups captured.
pub(crate) fn journal(
    start: u64,
    planes: u64,
    checks: impl Fn(u64) -> Vec<Check>,
) -> (Vec<Value>, u64) {
    let mut lines = Vec::new();
    let mut frame = 1;
    // Retakes owed: (plane, its remaining tries, the try number).
    let mut owed: Vec<(u64, Vec<Check>, u32)> = Vec::new();
    for plane in 1..=planes {
        let mut tries = checks(plane);
        let first = tries.remove(0);
        lines.push(journal_line(start, plane, 1, frame, first));
        frame += 4;
        for (p, rest, attempt) in std::mem::take(&mut owed) {
            let mut rest = rest;
            let check = rest.remove(0);
            lines.push(journal_line(start, p, attempt, frame, check));
            frame += 4;
            if !rest.is_empty() {
                owed.push((p, rest, attempt + 1));
            }
        }
        if !tries.is_empty() {
            owed.push((plane, tries, 2));
        }
    }
    (lines, (frame - 1) / 4)
}

fn progress_of(lines: &[Value]) -> Progress {
    let text: Vec<String> = lines.iter().map(Value::to_string).collect();
    follow::progress(&text.join("\n"))
}

/// The flight fixture's checks, modelled on the owner's run of 2026-11-21
/// (`stack-1795300522964-6430`): planes retaken and passing, one still
/// failing after two retakes, and failures the checker does not retake.
pub(crate) fn flight_checks(plane: u64) -> Vec<Check> {
    use Check::*;
    match plane {
        3 => vec![Demote(MISREGISTERED, true), Pass],
        24 => vec![Demote(PATTERN, false)],
        27 => vec![Demote(RESIDUAL, false)],
        39 => vec![Demote(MOTION, true), Pass],
        52 => vec![
            Demote(MOTION, true),
            Demote(MOTION, true),
            Demote(MOTION, true),
        ],
        55 => vec![Demote(MOTION, true), Demote(MOTION, true), Pass],
        59 => vec![Demote(PATTERN, false)],
        // Its retake is taken after plane 61 and not checked yet.
        60 => vec![Demote(MOTION, true), Pass],
        _ => vec![Pass],
    }
}

/// The checker's journal for the flight fixture: 61 planes (see
/// [`flight_checks`]); the retake of plane 60 is still being checked.
pub(crate) fn progress() -> Progress {
    let (lines, _) = journal(37_100, 61, flight_checks);
    let lines: Vec<Value> = lines
        .into_iter()
        .filter(|l| !(l["plane"] == 60 && l["verdict"] == "pass"))
        .collect();
    progress_of(&lines)
}

/// The groups the flight fixture's camera has captured: 61 planes and their
/// retakes so far (plane 60's included).
pub(crate) fn flight_groups() -> u64 {
    journal(37_100, 61, flight_checks).1
}

/// The flight fixture's capture once ended (`--capture-fixture
/// flight+done`): all 96 planes and every retake checked; and its groups.
pub(crate) fn finished_progress() -> (Progress, u64) {
    let (lines, groups) = journal(37_100, 96, flight_checks);
    (progress_of(&lines), groups)
}

/// The flight fixture's host state once the capture completed.
pub(crate) fn finish(s: &mut Snapshot) {
    let mut state = s.state.clone();
    let groups = finished_progress().1;
    state["phase"] = json!("complete");
    state["editable"] = json!(true);
    state["completed"] = json!(96);
    state["message"] = json!("Capture complete");
    state["timer"] = json!({"elapsed":602.4,"remaining":0.0,"finished":true,"paused":false});
    state["storage"]["captured_frames"] = json!(groups * 4);
    state["storage"]["saved_frames"] = json!(groups * 4);
    state["storage"]["pending_frames"] = json!(0);
    s.set_state(state);
}

/// The retake fixture's checks (`--capture-fixture flight+retakes`,
/// h-retake): the flight fixture's, and a run of four planes left to one
/// shot (44-47: two the checker does not retake, one that failed every
/// try, one whose shots were out of line after compensation), too long for
/// the calibrated overlap (width 50, step 7).
pub(crate) fn retake_checks(plane: u64) -> Vec<Check> {
    use Check::*;
    match plane {
        44 | 46 => vec![Demote(PATTERN, false)],
        45 => vec![
            Demote(MOTION, true),
            Demote(MOTION, true),
            Demote(MOTION, true),
        ],
        47 => vec![Demote(RESIDUAL, false)],
        _ => flight_checks(plane),
    }
}

/// The retake fixture's journal in flight (as [`progress`]: plane 60's
/// retake still being checked) or, `done`, once all 96 planes ended; and
/// its groups.
pub(crate) fn retake_progress(done: bool) -> (Progress, u64) {
    let planes = if done { 96 } else { 61 };
    let (lines, groups) = journal(37_100, planes, retake_checks);
    let lines: Vec<Value> = lines
        .into_iter()
        .filter(|l| done || !(l["plane"] == 60 && l["verdict"] == "pass"))
        .collect();
    (progress_of(&lines), groups)
}

/// The host's retake state for the retake fixture: the setting, and plane
/// 59 (a shift-pattern failure) asked to be retaken by hand, while it runs.
pub(crate) fn add_retakes(s: &mut Snapshot, done: bool) {
    let mut state = s.state.clone();
    state["capabilities"]["max_retakes"] = json!(true);
    state["capabilities"]["queue_retakes"] = json!(true);
    state["retakes"] = json!({"max":2,"limit":5,"accepted":true,
        "queued": if done { json!([]) } else { json!([59]) },
        "run":"stack-fixture","followup":null});
    s.set_state(state);
}

/// A long run's checks (`--capture-fixture flight+long`): about one plane
/// in 23 retaken once, one in 211 failing after two retakes, one in 97 and
/// one in 151 failing checks the checker does not retake.
pub(crate) fn long_checks(plane: u64) -> Vec<Check> {
    use Check::*;
    if plane % 211 == 7 {
        vec![
            Demote(MOTION, true),
            Demote(MOTION, true),
            Demote(MOTION, true),
        ]
    } else if plane % 97 == 5 {
        vec![Demote(PATTERN, false)]
    } else if plane % 151 == 11 {
        vec![Demote(RESIDUAL, false)]
    } else if plane.is_multiple_of(23) {
        vec![Demote(MOTION, true), Pass]
    } else {
        vec![Pass]
    }
}

/// The long fixture's planes taken so far, and planned, from focus 20,000
/// every 7 units.
pub(crate) const LONG_DONE: u64 = 5_400;
pub(crate) const LONG_TOTAL: u64 = 6_000;
pub(crate) const LONG_START: u64 = 20_000;

/// The long fixture's journal ([`LONG_DONE`] planes) and its groups.
pub(crate) fn long_progress() -> (Progress, u64) {
    let (lines, groups) = journal(LONG_START, LONG_DONE, long_checks);
    (progress_of(&lines), groups)
}

/// The flight fixture's host state for the long run: [`LONG_DONE`] of
/// [`LONG_TOTAL`] planes and `groups` groups captured.
pub(crate) fn lengthen(s: &mut Snapshot, groups: u64) {
    let mut state = s.state.clone();
    let end = LONG_START + (LONG_TOTAL - 1) * 7;
    state["plan"]["start"] = json!(LONG_START);
    state["plan"]["end"] = json!(end);
    state["planned"] = json!(LONG_TOTAL);
    state["completed"] = json!(LONG_DONE);
    state["total"] = json!(LONG_TOTAL);
    state["position"] = json!(LONG_START + (LONG_DONE - 1) * 7);
    state["message"] = json!(format!("Plane {LONG_DONE} of {LONG_TOTAL}"));
    state["timer"] =
        json!({"elapsed":31_150.0,"remaining":3_400.0,"finished":false,"paused":false});
    state["storage"]["captured_frames"] = json!(groups * 4);
    state["storage"]["saved_frames"] = json!(groups * 4 - 2);
    s.set_state(state);
}

/// The test shot the plan fixture shows.
pub(crate) fn test_levels() -> RawLevels {
    RawLevels {
        path: "frame-000001.ARW".into(),
        camera: "ILCE-7CR".into(),
        iso: Some(100.0),
        black: 512.0,
        white: 15360.0,
        samples: 61_000_000,
        clipped_share: 0.0,
        shadow_level: 0.012,
        median_level: 0.21,
        highlight_level: 0.24,
        colours: [crate::capture_workspace::test_shot::ColourLevels {
            highlight_level: 0.24,
            ..Default::default()
        }; 3],
        brightest: 1,
        in_subject: false,
    }
}

/// When the fixture's test shot and calibration happened.
pub(crate) fn earlier(minutes: u64) -> SystemTime {
    SystemTime::now() - std::time::Duration::from_secs(minutes * 60)
}

/// The plan fixture's focus trace before its preview: the lens stepped by
/// 4 from 37,468 through a peak at 37,540, scaled so the fixture's own
/// preview (at 37,556) reads as it would on that curve. Fabricated, like
/// the rest of the fixture.
pub(crate) fn focus_trace(s: &Snapshot) -> Vec<super::live::FocusSample> {
    let curve = |p: f32| 0.25 + 0.75 * (-((p - 37_540.0) / 26.0).powi(2)).exp();
    let roi = s
        .host
        .roi
        .unwrap_or_else(strehl_capture::model::Roi::subject);
    let Some(now) = s
        .peaking
        .as_ref()
        .and_then(|(_, peaks)| peaks.focus.focus_in(roi.x, roi.y, roi.width, roi.height))
    else {
        return Vec::new();
    };
    (37_468..37_556u16)
        .step_by(4)
        .map(|lens| super::live::FocusSample {
            lens: Some(lens),
            value: now / curve(37_556.0) * curve(f32::from(lens)),
        })
        .collect()
}
