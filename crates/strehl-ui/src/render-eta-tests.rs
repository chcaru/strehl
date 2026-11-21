//! Stage timings and time left, on excerpts of real render logs (stage lines
//! and a few progress events; no diagnostics; capture paths neutral).
use super::*;
use std::sync::atomic::AtomicBool;

const CPU_299: &str = include_str!("../fixtures/render-logs/cpu-299.log");
const GPU_1321: &str = include_str!("../fixtures/render-logs/gpu-1321.log");

fn close(a: f64, b: f64) -> bool {
    (a - b).abs() < 1e-6
}

#[test]
fn a_log_with_a_preview_pass_yields_both_passes_and_the_full_one_seeds() {
    let passes = passes(CPU_299);
    assert_eq!(passes.len(), 2);
    assert_eq!(passes[0].folded.map(|f| (f.0, f.1)), Some((38, 299)));
    assert!(
        !passes[0].complete(),
        "the quick preview fold is not a seed"
    );
    let seed = seed_from(CPU_299).unwrap();
    assert_eq!(seed.frames, Some(299));
    assert_eq!(seed.first_decode, Some(0.05));
    assert_eq!(seed.alignment, Some(0.0));
    let (done, of, seconds, per_frame) = seed.folded.unwrap();
    assert_eq!((done, of), (299, 299));
    assert!(close(seconds, 155.3) && close(per_frame, 0.52));
    assert_eq!(seed.collapse_write, Some(1.9));
    assert_eq!(seed.total, Some(157.3));
    assert!(close(seed.per_frame().unwrap(), 155.3 / 299.0));
    assert!(close(seed.estimate(299).unwrap(), 155.3 + 1.9));
    assert!(close(seed.estimate(598).unwrap(), 2.0 * 155.3 + 1.9));
}

#[test]
fn a_gpu_render_seeds_its_long_write_stage() {
    let seed = seed_from(GPU_1321).unwrap();
    assert_eq!(seed.frames, Some(1321));
    assert_eq!(seed.collapse_write, Some(95.0));
    assert_eq!(seed.total, Some(109.2));
    assert!(close(seed.per_frame().unwrap(), 13.9 / 1321.0));
}

#[test]
fn the_seed_is_read_from_the_tail_of_a_large_log() {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("render.log");
    // 2 MiB of progress lines before the summary: only the tail is read.
    let filler = "STREHL_UI_PROGRESS event=merge-step index=1 name=decode state=started level=none total=299\n";
    let mut text = filler.repeat(2 * 1024 * 1024 / filler.len());
    text.push_str(CPU_299);
    std::fs::write(&path, &text).unwrap();
    let seed = read_seed(&path, &AtomicBool::new(false)).unwrap().unwrap();
    assert_eq!(seed.total, Some(157.3));
    // A log without a complete pass seeds nothing; a missing one fails.
    std::fs::write(&path, filler.repeat(10)).unwrap();
    assert!(read_seed(&path, &AtomicBool::new(false)).unwrap().is_none());
    assert!(
        read_seed(
            &directory.path().join("missing.log"),
            &AtomicBool::new(false)
        )
        .is_err()
    );
}

#[test]
fn malformed_stage_lines_are_ignored_rather_than_misread() {
    let mut times = StageTimes::default();
    for line in [
        "folded          : many frames in a while",
        "total           : 12.5 minutes",
        "collapse+write  : -3.0 s",
        "frames          : lots",
    ] {
        times.ingest(line);
    }
    assert_eq!(times, StageTimes::default());
}

/// Feed `text` line by line, one line every `step`.
fn feed(tracker: &mut EtaTracker, text: &str, start: Instant, step: Duration) -> Instant {
    let mut now = start;
    for line in text.lines() {
        tracker.ingest(line, now);
        now += step;
    }
    now
}

#[test]
fn time_left_comes_from_the_seed_until_the_live_rate_is_trustworthy() {
    let seed = seed_from(CPU_299);
    let start = Instant::now();
    let mut tracker = EtaTracker::new(seed);
    tracker.ingest("STREHL_UI_PROGRESS event=stage name=read total=299\nSTREHL_UI_PROGRESS event=stage name=alignment total=299", start);
    assert_eq!(tracker.phase(), Phase::Preparing);
    let before = tracker.eta(start).unwrap().as_secs_f64();
    assert!(close(before, 155.3 + 1.9), "{before}");
    tracker.ingest("STREHL_UI_PROGRESS event=stage name=merge total=299", start);
    // Five frames at 0.25 s: too few for a live rate, so the seed's 0.52 s.
    let mut now = start;
    for processed in 1..=5 {
        now += Duration::from_millis(250);
        tracker.ingest(&format!("STREHL_UI_PROGRESS event=frame-finished index={} processed={processed} accepted={processed} total=299", processed - 1), now);
    }
    assert!(tracker.live_rate().is_none());
    let seeded = tracker.eta(now).unwrap().as_secs_f64();
    assert!(close(seeded, 294.0 * 155.3 / 299.0 + 1.9), "{seeded}");
    // Forty frames at 0.25 s: the live rate takes over.
    for processed in 6..=45 {
        now += Duration::from_millis(250);
        tracker.ingest(&format!("STREHL_UI_PROGRESS event=frame-finished index={} processed={processed} accepted={processed} total=299", processed - 1), now);
    }
    let rate = tracker.live_rate().unwrap();
    assert!((rate - 0.25).abs() < 1e-3, "{rate}");
    let live = tracker.eta(now).unwrap().as_secs_f64();
    assert!((live - (254.0 * 0.25 + 1.9)).abs() < 0.01, "{live}");
    // Time passing without a new frame counts down.
    let later = tracker
        .eta(now + Duration::from_secs(10))
        .unwrap()
        .as_secs_f64();
    assert!((live - later - 10.0).abs() < 0.01);
    // The write stage counts down from the seed's collapse+write.
    tracker.ingest("STREHL_UI_PROGRESS event=stage name=render total=299", now);
    assert_eq!(tracker.phase(), Phase::Writing);
    assert!(close(tracker.eta(now).unwrap().as_secs_f64(), 1.9));
    assert!(tracker.eta(now + Duration::from_secs(5)).unwrap().is_zero());
    tracker.ingest("folded          : 299 / 299 frames in 70.0 s (0.23 s per frame, 32 execution threads)\ncollapse+write  : 1.0 s\ntotal           : 71.0 s", now);
    assert_eq!(tracker.phase(), Phase::Done);
    assert_eq!(tracker.eta(now), Some(Duration::ZERO));
    // A new pass starts over, with the plane count its first stage names.
    tracker.ingest("STREHL_UI_PROGRESS event=stage name=read total=299", now);
    assert_eq!(tracker.phase(), Phase::Preparing);
    assert_eq!(tracker.processed(), (0, Some(299)));
}

#[test]
fn without_a_seed_there_is_no_estimate_until_frames_arrive() {
    let start = Instant::now();
    let mut tracker = EtaTracker::new(None);
    let end = feed(
        &mut tracker,
        CPU_299
            .lines()
            .take(19)
            .collect::<Vec<_>>()
            .join("\n")
            .as_str(),
        start,
        Duration::from_millis(10),
    );
    assert_eq!(tracker.phase(), Phase::Merge);
    assert!(tracker.eta(end).is_none(), "no seed and no frames yet");
    // The fixture's own frame events arrive at 50-frame steps: two give a rate.
    let mut now = end;
    for processed in [50usize, 100, 150] {
        now += Duration::from_secs(25);
        tracker.ingest(&format!("STREHL_UI_PROGRESS event=frame-finished index={} processed={processed} accepted={processed} total=299", processed - 1), now);
    }
    let eta = tracker.eta(now).unwrap().as_secs_f64();
    assert!((eta - 149.0 * 0.5).abs() < 0.01, "{eta}");
}

#[test]
fn durations_read_as_people_say_them() {
    for (seconds, words) in [
        (0, "0 s"),
        (25, "25 s"),
        (60, "1 min"),
        (198, "3 min 18 s"),
        (1260, "21 min"),
        (3840, "1 h 04 min"),
    ] {
        assert_eq!(spoken(Duration::from_secs(seconds)), words);
    }
}

/// A real render log of 1.6 MB put its `frames` line before the seed's 1 MiB
/// tail: the seed then had rates but no plane count, and the resumed stack
/// showed no time left until its merge began (P5 end-to-end run).
#[test]
fn a_seed_without_its_frames_line_still_estimates_before_the_merge() {
    let seed = seed_from(
        "folded          : 3 / 3 frames in 0.6 s (0.21 s per frame, 3 execution threads)\n\
         collapse+write  : 0.6 s\n\
         total           : 1.3 s\n",
    )
    .expect("a complete pass");
    assert_eq!((seed.frames, seed.planes()), (None, Some(3)));
    let now = Instant::now();
    let mut tracker = EtaTracker::new(Some(seed));
    assert_eq!(tracker.phase(), Phase::Preparing);
    let eta = tracker.eta(now).expect("an estimate while aligning");
    assert!(close(eta.as_secs_f64(), 3.0 * 0.2 + 0.6), "{eta:?}");
    // The stages name the plane count of this render: a 299-plane variant.
    tracker.ingest(
        "STREHL_UI_PROGRESS event=stage name=read total=299\n\
         STREHL_UI_PROGRESS event=stage name=alignment total=299\n",
        now,
    );
    assert_eq!(tracker.phase(), Phase::Preparing);
    let eta = tracker.eta(now).unwrap();
    assert!(close(eta.as_secs_f64(), 299.0 * 0.2 + 0.6), "{eta:?}");
    assert_eq!(tracker.processed(), (0, Some(299)));
}
