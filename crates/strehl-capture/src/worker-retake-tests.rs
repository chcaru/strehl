//! h-retake: the run's own retake limit, manual retakes during a capture
//! and after it, on the simulated PC camera (`backend::sim::PcSim`).
use super::*;
use crate::backend::sim::{Fail, PcSim};

/// A capture of `planes` planes (step 1 from 60000) with error correction
/// on and `max` retakes, into a fresh folder.
struct Bench {
    temp: tempfile::TempDir,
    shared: Shared,
    control: Arc<AtomicU8>,
    plan: Plan,
}

impl Bench {
    fn new(planes: u16, max: usize) -> Self {
        Self {
            temp: tempfile::tempdir().unwrap(),
            shared: Arc::new(Mutex::new(Snapshot {
                error_correction: true,
                max_retakes: max,
                ..Snapshot::default()
            })),
            control: Arc::new(AtomicU8::new(RUN)),
            plan: Plan {
                start: 60000,
                end: 60000 + planes - 1,
                step: 1,
                ..Plan::default()
            },
        }
    }
    fn capture(&self, camera: &mut PcSim) {
        capture(
            camera,
            &self.shared,
            &self.control,
            self.plan.clone(),
            self.temp.path().into(),
            None,
            None,
        )
        .unwrap();
    }
    fn followup(&self, camera: &mut PcSim, planes: Vec<u64>) -> Result<()> {
        self.control.store(RUN, Ordering::SeqCst);
        followup(camera, &self.shared, &self.control, planes, None)
    }
    fn run(&self) -> PathBuf {
        self.shared.lock().unwrap().journal.clone().unwrap()
    }
    fn events(&self) -> Vec<Value> {
        std::fs::read_to_string(self.run().join("events.jsonl"))
            .unwrap()
            .lines()
            .map(|l| serde_json::from_str(l).unwrap())
            .collect()
    }
    fn named(&self, event: &str) -> Vec<Value> {
        self.events()
            .into_iter()
            .filter(|e| e["event"] == event)
            .map(|e| e["data"].clone())
            .collect()
    }
    fn snapshot(&self) -> Snapshot {
        self.shared.lock().unwrap().clone()
    }
}

/// Plane 2 fails every try. The run's own setting decides how often it is
/// taken again, 0 included, and the journal says the setting.
#[test]
fn the_runs_max_retakes_decides_how_often_a_plane_is_taken_again() {
    for max in [0usize, 1, 2, 3] {
        let bench = Bench::new(4, max);
        let fail = (1..=6).map(|t| ((2, t), Fail::Retake)).collect();
        let mut camera = PcSim::new(fail);
        bench.capture(&mut camera);
        assert_eq!(camera.tries(2), max + 1, "max {max}");
        assert_eq!(camera.groups.len(), 4 + max, "max {max}");
        assert_eq!(bench.named("retake_intent").len(), max);
        let exhausted = bench.named("retake_exhausted");
        assert_eq!(exhausted.len(), 1, "max {max}");
        assert_eq!(exhausted[0]["retakes"], max);
        assert_eq!(exhausted[0]["max_retakes"], max);
        assert_eq!(exhausted[0]["manual"], false);
        let setting = bench.named("error_correction");
        assert_eq!(setting, [json!({"enabled":true,"max_retakes":max})]);
        assert_eq!(bench.snapshot().phase, Phase::Complete);
    }
    // Above the limit is held to it.
    let bench = Bench::new(2, 99);
    let mut camera = PcSim::new((1..=9).map(|t| ((1, t), Fail::Retake)).collect());
    bench.capture(&mut camera);
    assert_eq!(camera.tries(1), MAX_RETAKES_LIMIT + 1);
}

/// A retake queued while the capture runs is taken between planes, through
/// the approach move, recorded as the user's, and never followed by error
/// correction's own retakes even when it fails again.
#[test]
fn a_retake_queued_mid_run_is_taken_between_planes() {
    let bench = Bench::new(5, 2);
    // Plane 1 fails a check the checker does not retake; plane 3 likewise,
    // and fails its manual retake too.
    let mut camera = PcSim::new(vec![
        ((1, 1), Fail::Kept),
        ((3, 1), Fail::Kept),
        ((3, 2), Fail::Retake),
    ]);
    camera.inject = vec![
        (3, vec![1], bench.shared.clone()),
        (4, vec![3], bench.shared.clone()),
    ];
    bench.capture(&mut camera);
    assert_eq!(camera.tries(1), 2);
    assert_eq!(camera.tries(3), 2, "a failed manual retake is not retaken");
    assert_eq!(camera.groups.len(), 7);
    let intents = bench.named("retake_intent");
    assert_eq!(intents.len(), 2);
    assert!(intents.iter().all(|i| i["manual"] == true));
    assert_eq!(intents[0]["plane"], 1);
    assert_eq!(intents[1]["plane"], 3);
    // Plane 1's retake came after plane 3 was taken (it was asked for then),
    // through the approach: below 60000 first.
    let order: Vec<u64> = camera.groups.iter().map(|(p, _)| *p).collect();
    assert_eq!(&order[..4], [1, 2, 3, 1]);
    assert!(camera.focuses.contains(&(60000 - 128)));
    let exhausted = bench.named("retake_exhausted");
    assert_eq!(exhausted.len(), 1);
    assert_eq!(exhausted[0]["manual"], true);
    // The retake is filed under its plane's number.
    let buffered = bench.named("capture_buffered");
    assert_eq!(buffered[3]["response"]["files"][0]["plane"], 1);
    assert!(bench.snapshot().retake_queue.is_empty());
}

/// A plane error correction gave up on, then retaken by hand: the manual
/// retake is one more try beyond the limit, and its pass is the plane's
/// newest group (the one the stack uses).
#[test]
fn an_exhausted_plane_can_be_retaken_by_hand() {
    let bench = Bench::new(5, 2);
    let fail = (1..=3).map(|t| ((2, t), Fail::Retake)).collect();
    let mut camera = PcSim::new(fail);
    // Asked for once the last plane is taken, after the plane was given up.
    camera.inject = vec![(7, vec![2], bench.shared.clone())];
    bench.capture(&mut camera);
    assert_eq!(bench.named("retake_exhausted").len(), 1);
    assert_eq!(camera.tries(2), 4);
    let last = camera
        .groups
        .iter()
        .rev()
        .find(|(p, _)| *p == 2)
        .unwrap()
        .1
        .clone();
    assert_eq!(camera.groups.last().unwrap().1, last, "the newest group");
    assert_eq!(camera.verdict(&last).unwrap().unwrap()["verdict"], "pass");
    let intents = bench.named("retake_intent");
    assert_eq!(intents.len(), 3);
    assert_eq!(intents[2]["manual"], true);
    assert_eq!(intents[2]["retake"], 3);
}

/// A plane that passed, or that error correction is about to retake, is not
/// taken again by hand; a plane not taken yet is refused. Each is said.
#[test]
fn a_manual_retake_never_replaces_a_pass() {
    let bench = Bench::new(4, 2);
    let mut camera = PcSim::new(vec![((2, 1), Fail::Retake)]);
    camera.inject = vec![(2, vec![1, 4], bench.shared.clone())];
    bench.capture(&mut camera);
    assert_eq!(camera.tries(1), 1);
    assert_eq!(camera.tries(2), 2, "error correction's retake only");
    let skipped = bench.named("manual_retake_skipped");
    let reasons: Vec<_> = skipped
        .iter()
        .map(|s| (s["plane"].clone(), s["reason"].clone()))
        .collect();
    assert!(
        reasons.contains(&(json!(1), json!("its newest try passed"))),
        "{reasons:?}"
    );
    assert!(
        reasons.contains(&(json!(4), json!("not taken yet"))),
        "{reasons:?}"
    );
    assert!(
        bench
            .named("retake_intent")
            .iter()
            .all(|i| i["manual"].is_null())
    );
}

/// After the capture: the planes asked for are taken into the same run,
/// under their own numbers, the RAWs continuing the run's names, the
/// journal marking the start and end; the result file is untouched.
#[test]
fn retakes_after_the_capture_go_into_the_same_run() {
    let bench = Bench::new(4, 2);
    let mut camera = PcSim::new(vec![
        ((3, 1), Fail::Kept),
        ((3, 2), Fail::Kept),
        ((4, 1), Fail::Kept),
    ]);
    bench.capture(&mut camera);
    let result = std::fs::read(bench.run().join("result.json")).unwrap();
    assert_eq!(bench.snapshot().phase, Phase::Complete);
    let s = bench.snapshot();
    assert!(s.retakes_accepted && s.capture_run);
    // A span: planes 3-4, with plane 1 (which passed) asked for too.
    bench.followup(&mut camera, vec![4, 1, 3]).unwrap();
    assert_eq!(camera.tries(3), 2);
    assert_eq!(camera.tries(4), 2);
    assert_eq!(camera.tries(1), 1, "a passed plane is skipped");
    let started = bench.named("followup_started");
    assert_eq!(started, [json!({"planes":[1,3,4],"manual":true})]);
    let finished = bench.named("followup_finished");
    assert_eq!(
        finished,
        [json!({"outcome":"complete","taken":2,"skipped":1})]
    );
    let buffered = bench.named("capture_buffered");
    let tail: Vec<_> = buffered[4..]
        .iter()
        .map(|b| {
            (
                b["response"]["files"][0]["plane"].clone(),
                b["response"]["files"][0]["name"].clone(),
            )
        })
        .collect();
    assert_eq!(
        tail,
        [
            (json!(3), json!("frame-000017.ARW")),
            (json!(4), json!("frame-000021.ARW"))
        ]
    );
    // Each through the approach, in the capture's order.
    let below: Vec<u16> = camera
        .focuses
        .iter()
        .copied()
        .filter(|f| *f < 60000)
        .collect();
    assert_eq!(below.len(), 3, "the capture's approach and one a retake");
    assert_eq!(
        std::fs::read(bench.run().join("result.json")).unwrap(),
        result
    );
    let events = bench.events();
    let sequences: Vec<u64> = events
        .iter()
        .map(|e| e["sequence"].as_u64().unwrap())
        .collect();
    assert!(
        sequences.windows(2).all(|w| w[1] == w[0] + 1),
        "{sequences:?}"
    );
    let s = bench.snapshot();
    assert_eq!((s.phase, s.followup), (Phase::Complete, None));
    // A second round continues after the first.
    bench.followup(&mut camera, vec![3]).unwrap();
    assert_eq!(camera.tries(3), 3);
    let last = bench.named("capture_buffered").pop().unwrap();
    assert_eq!(last["response"]["files"][0]["name"], "frame-000025.ARW");
}

/// Stopped part-way: what was taken stays, the end says stopped, and the
/// run is as it was before (complete). During the capture, retakes still
/// queued when it stops are dropped, and said.
#[test]
fn a_stop_part_way_keeps_what_was_taken() {
    let bench = Bench::new(4, 2);
    let mut camera = PcSim::new((1..=4).map(|p| ((p, 1), Fail::Kept)).collect());
    bench.capture(&mut camera);
    camera.stop_at = Some((6, bench.control.clone()));
    bench.followup(&mut camera, vec![1, 2, 3, 4]).unwrap();
    assert_eq!(camera.groups.len(), 6);
    let finished = bench.named("followup_finished");
    assert_eq!(
        finished,
        [json!({"outcome":"stopped","taken":2,"skipped":0})]
    );
    assert_eq!(bench.snapshot().phase, Phase::Complete);

    let bench = Bench::new(6, 2);
    let mut camera = PcSim::new(vec![((1, 1), Fail::Kept)]);
    camera.late = 1000;
    camera.inject = vec![(2, vec![1], bench.shared.clone())];
    camera.stop_at = Some((3, bench.control.clone()));
    bench.capture(&mut camera);
    assert_eq!(bench.snapshot().phase, Phase::Stopped);
    let dropped = bench.named("manual_retakes_dropped");
    assert_eq!(dropped.len(), 1);
    assert_eq!(dropped[0]["planes"], json!([1]));
    assert!(bench.snapshot().retake_queue.is_empty());
}

/// A retake afterwards takes the plane as the capture did: a changed
/// exposure or mode refuses it before any focus move or exposure.
#[test]
fn retakes_after_the_capture_need_the_captures_exposure() {
    let bench = Bench::new(3, 2);
    let mut camera = PcSim::new(vec![((2, 1), Fail::Kept)]);
    bench.capture(&mut camera);
    let (groups, focuses) = (camera.groups.len(), camera.focuses.len());
    camera.demo.iso = 400;
    let e = bench.followup(&mut camera, vec![2]).unwrap_err();
    assert!(e.to_string().contains("IsoSensitivity differs"), "{e:#}");
    camera.demo.iso = 100;
    camera.demo.shots = 1;
    let e = bench.followup(&mut camera, vec![2]).unwrap_err();
    assert!(e.to_string().contains("4 RAWs a plane"), "{e:#}");
    camera.demo.shots = 4;
    let e = bench.followup(&mut camera, vec![7]).unwrap_err();
    assert!(e.to_string().contains("Choose planes 1-3"), "{e:#}");
    assert_eq!(
        (camera.groups.len(), camera.focuses.len()),
        (groups, focuses)
    );
    assert!(bench.named("followup_started").is_empty());
    bench.followup(&mut camera, vec![2]).unwrap();
    assert_eq!(camera.tries(2), 2);
}

/// The run's record read back from its journal: RAWs, planes, tries and
/// each plane's newest group.
#[test]
fn an_ended_run_is_read_back_from_its_journal() {
    let bench = Bench::new(3, 2);
    let mut camera = PcSim::new(vec![((2, 1), Fail::Retake)]);
    bench.capture(&mut camera);
    let record = RunRecord::read(&bench.run()).unwrap();
    assert_eq!((record.frames, record.planes, record.shots), (16, 3, 4));
    assert_eq!(record.tries[&2], (2, "ptp-sim-3".to_owned()));
    assert_eq!(record.positions, [60000, 60001, 60002]);
}

/// A capture that kept its RAWs on the card takes no manual retakes: the
/// PC has no plane records to bind them to.
#[test]
fn a_card_capture_takes_no_manual_retakes() {
    let bench = Bench::new(2, 2);
    let mut demo = Demo {
        delay_ms: 1,
        ..Demo::default()
    };
    capture(
        &mut demo,
        &bench.shared,
        &bench.control,
        bench.plan.clone(),
        bench.temp.path().into(),
        None,
        None,
    )
    .unwrap();
    let s = bench.snapshot();
    assert_eq!(s.phase, Phase::Complete);
    assert!(!s.retakes_accepted);
    let e = followup(&mut demo, &bench.shared, &bench.control, vec![1], None).unwrap_err();
    assert!(e.to_string().contains("on the card"), "{e:#}");
}

/// Retakes asked for while those after the capture run join them, in turn;
/// a plane the capture never took is refused, and said.
#[test]
fn a_retake_asked_during_the_retakes_after_joins_them() {
    let bench = Bench::new(4, 2);
    let mut camera = PcSim::new((1..=4).map(|p| ((p, 1), Fail::Kept)).collect());
    bench.capture(&mut camera);
    // At the first retake's capture (the fifth group): plane 1 and a
    // plane beyond the capture.
    camera.inject = vec![(5, vec![1, 9], bench.shared.clone())];
    bench.followup(&mut camera, vec![3]).unwrap();
    let order: Vec<u64> = camera.groups[4..].iter().map(|(p, _)| *p).collect();
    assert_eq!(order, [3, 1]);
    assert_eq!(
        bench.named("followup_finished"),
        [json!({"outcome":"complete","taken":2,"skipped":0})]
    );
    let skipped = bench.named("manual_retake_skipped");
    assert_eq!(
        skipped,
        [json!({"plane":9,"reason":"not taken by the capture"})]
    );
}
