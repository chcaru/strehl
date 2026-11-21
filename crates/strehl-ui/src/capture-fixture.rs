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
            "shutter_options":[65546,65544,65541,65539,65538,65537],"writable":true,"mode":"M","problem":null},
        "preview":{"available":true,"fresh":true,"generation":7,"age_seconds":0.2,"width":960,"height":640},
        "samples":samples,"magnifier_ratios":[0,59,117],"magnifier_current":59,
        "suggestion":{"start":37100,"end":37764,"supported_tiles":20,"clipped":false,"explanation":"Sharp detail from 37,100 to 37,764"},
        "capabilities":{"test_shot":true,"exposure_check":true},"error_correction":false,
        "schedule":{"job":null,"error":null},"pending_control":0,"completed":0,"total":0})
}

/// The host's state, the receiver and the pictures for `fixture`.
pub(crate) fn snapshot(fixture: Fixture) -> Snapshot {
    let mut state = plan_state();
    if fixture != Fixture::Plan {
        for (key, value) in [
            ("phase", json!("capturing")),
            ("editable", json!(false)),
            ("completed", json!(61)),
            ("total", json!(96)),
            ("position", json!(37520)),
            ("message", json!("Plane 61 of 96 · focus 37520")),
            (
                "timer",
                json!({"elapsed":341.6,"remaining":198.0,"finished":false,"paused":false}),
            ),
            (
                "storage",
                json!({"mode":"host-pc","free_bytes":355_000_000_000u64,"pipelined":true,"captured_frames":244,
                    "saved_frames":242,"pending_frames":2,"receipt":{"wire_MB_per_second":38.2}}),
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

/// The checker's journal for the flight fixture: 61 planes, plane 39 retaken.
pub(crate) fn progress() -> Progress {
    let mut lines = Vec::new();
    for plane in 1..=61u64 {
        let target = 37_100 + (plane - 1) * 7;
        if plane == 39 {
            lines.push(
                json!({"plane":plane,"target":target,"group_id":"g39","verdict":"demote",
                "reason":"moved between shots","retake":true,"members":4,"seconds":2.0}),
            );
            lines.push(
                json!({"plane":plane,"target":target,"group_id":"g39b","verdict":"pass",
                "retake":false,"members":4,"seconds":2.2}),
            );
        } else {
            let seconds = 1.9 + (plane % 3) as f64 * 0.1;
            lines.push(
                json!({"plane":plane,"target":target,"group_id":format!("g{plane}"),
                "verdict":"pass","retake":false,"members":4,"seconds":seconds}),
            );
        }
    }
    let text: Vec<String> = lines.iter().map(Value::to_string).collect();
    follow::progress(&text.join("\n"))
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
        highlight_level: 0.86,
    }
}

/// When the fixture's test shot and calibration happened.
pub(crate) fn earlier(minutes: u64) -> SystemTime {
    SystemTime::now() - std::time::Duration::from_secs(minutes * 60)
}
