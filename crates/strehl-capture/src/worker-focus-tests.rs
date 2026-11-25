//! Focus moves that do not arrive (owner, 2026-11-24): the lens's ends,
//! learned when a manual move stops there, and a capture's moves tried once
//! more through the approach.
use super::*;
use crate::backend::sim::{Fail, PcSim};

fn until(w: &Worker, predicate: impl Fn(&Snapshot) -> bool) -> Snapshot {
    let end = Instant::now() + Duration::from_secs(8);
    loop {
        let s = w.snapshot();
        if predicate(&s) {
            return s;
        }
        assert!(Instant::now() < end, "Timeout: {:?} {}", s.phase, s.message);
        thread::sleep(Duration::from_millis(5));
    }
}

/// A demo camera whose lens travels 1509 to 63487, as the owner's does.
fn worker_with_ends() -> Worker {
    Worker::with_factory(Box::new(|| {
        Ok(Box::new(Demo {
            delay_ms: 0,
            travel: (1509, 63487),
            ..Demo::default()
        }))
    }))
}

/// A move past the far end stops there: the controller stays ready, says
/// where the end is, and keeps it (in the file too); a later move back
/// lands as before. Before the fix the same move faulted the controller.
#[test]
fn a_move_past_the_lens_end_stops_there_and_is_kept() {
    let temp = tempfile::tempdir().unwrap();
    let file = temp.path().join("lens-travel.json");
    let w = worker_with_ends();
    w.keep_lens_travel(file.clone());
    w.send(0, Action::Connect).unwrap();
    let s = until(&w, |s| s.phase == Phase::Ready && !s.command_pending);
    w.send(
        s.revision,
        Action::Move {
            target: 63568,
            settle_ms: 100,
        },
    )
    .unwrap();
    let s = until(&w, |s| !s.command_pending && s.phase != Phase::Moving);
    assert_eq!(s.phase, Phase::Ready, "{}", s.message);
    assert_eq!(s.position, Some(63487));
    assert!(s.message.contains("far end is 63487"), "{}", s.message);
    assert_eq!(s.lens_travel.far, Some(63487));
    assert_eq!(s.lens_travel.near, None);
    assert_eq!(LensTravel::load(&file).far, Some(63487));
    // A fresh controller reads it back.
    let again = worker_with_ends();
    again.keep_lens_travel(file.clone());
    assert_eq!(again.snapshot().lens_travel.far, Some(63487));
    // Back inside the travel: the move lands.
    w.send(
        s.revision,
        Action::Move {
            target: 61000,
            settle_ms: 100,
        },
    )
    .unwrap();
    let s = until(&w, |s| !s.command_pending && s.position == Some(61000));
    assert_eq!(s.phase, Phase::Ready);
    assert_eq!(s.message, "Focus settled");
    // The near end the same way, from a mark's approach.
    w.send(
        s.revision,
        Action::Inspect {
            target: 1600,
            approach_from: 1472,
            settle_ms: 100,
        },
    )
    .unwrap();
    let s = until(&w, |s| !s.command_pending && s.position == Some(1600));
    assert_eq!(s.phase, Phase::Ready, "{}", s.message);
    assert!(s.message.contains("near end is 1509"), "{}", s.message);
    assert_eq!(s.lens_travel.near, Some(1509));
}

/// A plan of `planes` planes, step 1 from 60000, on the PC simulator.
fn bench(planes: u16) -> (tempfile::TempDir, Shared, Plan) {
    (
        tempfile::tempdir().unwrap(),
        Arc::new(Mutex::new(Snapshot {
            error_correction: true,
            max_retakes: 2,
            ..Snapshot::default()
        })),
        Plan {
            start: 60000,
            end: 60000 + planes - 1,
            step: 1,
            ..Plan::default()
        },
    )
}

fn events(shared: &Shared, name: &str) -> Vec<Value> {
    let run = shared.lock().unwrap().journal.clone().unwrap();
    std::fs::read_to_string(run.join("events.jsonl"))
        .unwrap()
        .lines()
        .map(|l| serde_json::from_str::<Value>(l).unwrap())
        .filter(|e| e["event"] == name)
        .map(|e| e["data"].clone())
        .collect()
}

/// A plane the lens stalls short of once is reached on the second try,
/// through the approach, and the run completes; twice, and the run stops
/// with both tries said.
#[test]
fn a_plane_the_lens_misses_once_is_tried_again_through_the_approach() {
    let (temp, shared, plan) = bench(4);
    let mut camera = PcSim::new(Vec::new());
    camera.demo.stalls = vec![60002];
    let control = AtomicU8::new(RUN);
    capture(
        &mut camera,
        &shared,
        &control,
        plan.clone(),
        temp.path().into(),
        None,
        None,
    )
    .unwrap();
    let retry = events(&shared, "focus_retry");
    assert_eq!(retry.len(), 1);
    assert_eq!(retry[0]["target"], 60002);
    assert!(
        retry[0]["error"]
            .as_str()
            .unwrap()
            .contains("stopped at 60001"),
        "{}",
        retry[0]
    );
    assert_eq!(shared.lock().unwrap().completed, 4);
    // The retry came from below, through the approach.
    let at = camera.focuses.iter().rposition(|&f| f == 60002).unwrap();
    assert_eq!(camera.focuses[at - 1], 60002 - plan.approach);

    let (temp, shared, plan) = bench(4);
    let mut camera = PcSim::new(Vec::new());
    camera.demo.stalls = vec![60002, 60002];
    let error = capture(
        &mut camera,
        &shared,
        &control,
        plan,
        temp.path().into(),
        None,
        None,
    )
    .unwrap_err();
    let text = format!("{error:#}");
    assert!(text.contains("Focus failed twice at 60002"), "{text}");
}

/// A retake whose focus move fails keeps the plane's last group, and the
/// capture goes on to its end (owner, 2026-11-24: it stopped half way).
#[test]
fn a_retake_that_cannot_reach_focus_keeps_the_plane_and_the_run_goes_on() {
    let (temp, shared, plan) = bench(5);
    // Plane 2 asks for a retake; the retake's approach move stalls, and so
    // does its retry's.
    let mut camera = PcSim::new(vec![((2, 1), Fail::Retake)]);
    let below = 60001 - plan.approach;
    camera.demo.stalls = vec![below];
    let control = AtomicU8::new(RUN);
    capture(
        &mut camera,
        &shared,
        &control,
        plan,
        temp.path().into(),
        None,
        None,
    )
    .unwrap();
    let abandoned = events(&shared, "retake_abandoned");
    assert_eq!(abandoned.len(), 1, "{abandoned:?}");
    assert_eq!(abandoned[0]["target"], 60001);
    assert_eq!(shared.lock().unwrap().completed, 5);
    assert_eq!(camera.tries(2), 1, "the plane keeps its first group");
}

/// The lens's ends: a manual move is kept at an end it would cross from
/// inside; from the end itself it goes on (another lens may travel further,
/// and landing beyond moves the end out).
#[test]
fn lens_travel_keeps_moves_inside_and_widens_when_passed() {
    let mut t = LensTravel::default();
    assert_eq!(t.keep_inside(60000, 65000), 65000, "no end known");
    assert!(t.stopped(true, 63487));
    assert!(!t.stopped(true, 63487));
    assert_eq!(t.keep_inside(60000, 65000), 63487);
    assert_eq!(t.keep_inside(63487, 63600), 63600, "from the end: as asked");
    assert!(t.stopped(false, 1509));
    assert_eq!(t.keep_inside(2000, 0), 1509);
    assert_eq!(t.outside([2000, 63500]), Some((63500, "far", 63487)));
    assert_eq!(t.outside([1500]), Some((1500, "near", 1509)));
    assert_eq!(t.outside([1509, 63487]), None);
    assert!(t.landed(63600));
    assert_eq!(t.far, Some(63600));
    assert!(!t.landed(30000));
}
