// Production scheduler commissioning, nested under the frozen generated d adapter.
// Source regeneration retains u16 CFA only. No merge/filter implementation lives here.
use super::*;
use crate::merge_cmd::temporal_cpu;
use std::collections::BTreeMap;
use std::sync::Arc;
use strehl_core::warpmap::{Provenance, StackIdentity};

struct Source {
    case: Case,
    noisy: bool,
    reverse: bool,
    corrupt_second: bool,
    calls: Mutex<Vec<usize>>,
    hashes: Mutex<Vec<Option<String>>>,
}
impl Source {
    fn new(case: &Case, noisy: bool, reverse: bool) -> Self {
        Self {
            case: case.clone(),
            noisy,
            reverse,
            corrupt_second: false,
            calls: Mutex::new(vec![0; case.n]),
            hashes: Mutex::new(vec![None; case.n]),
        }
    }
    fn original(&self, i: usize) -> usize {
        if self.reverse { self.case.n - 1 - i } else { i }
    }
    fn map(&self, domain: PyramidDomain, refused: Option<usize>) -> WarpMap {
        let entries: Vec<_> = (0..self.case.n)
            .map(|i| (format!("generated-{i}.ARW"), (SIDE * SIDE * 2) as u64))
            .collect();
        WarpMap::new(
            Provenance {
                stack: StackIdentity::from_entries(self.case.name, &entries),
                strategy: "generated-known-placement".into(),
                heldout_px: None,
                cycle_floor_px: None,
                reference: 0,
                note: "Analytic source planted through inverse gather; not a fitted calibration"
                    .into(),
            },
            domain.full,
            Resampler::CatmullRom,
            (0..self.case.n)
                .map(|i| {
                    if refused == Some(i) {
                        FrameWarp::Refused("commissioned refusal".into())
                    } else {
                        FrameWarp::Placed(transform(&self.case, self.original(i)))
                    }
                })
                .collect(),
        )
    }
    fn counts(&self) -> Vec<usize> {
        self.calls.lock().unwrap().clone()
    }
}
impl PyramidFrameSource for Source {
    fn len(&self) -> usize {
        self.case.n
    }
    fn decode(&self, index: usize) -> Result<Frame> {
        let ordinal = {
            let mut calls = self.calls.lock().unwrap();
            calls[index] += 1;
            calls[index]
        };
        let original = self.original(index);
        let clean = temporal_source(&self.case, Some(original), true);
        let mut frame = if self.noisy {
            let seed = SEED
                .wrapping_add(self.case.seed)
                .wrapping_add(original as u64 * 0x10001);
            let (frame, _, clipped) = noisy_frame(&clean, &noise(false), &mut Rng(seed));
            ensure!(clipped == 0, "synthetic source clipped");
            frame
        } else {
            clean
        };
        let bytes: Vec<_> = frame.data.iter().flat_map(|x| x.to_le_bytes()).collect();
        let hash = digest(&bytes);
        let mut hashes = self.hashes.lock().unwrap();
        if let Some(first) = &hashes[index] {
            assert_eq!(first, &hash, "regeneration changed u16 source");
        } else {
            hashes[index] = Some(hash);
        }
        // Deliberately mutate one consumed G1 site AFTER reproducibility check.
        // This must be caught by the core's guide/center binding, not by this source.
        if self.corrupt_second && index == 0 && ordinal == 2 {
            frame.data[64 * SIDE + 65] += 100;
        }
        Ok(frame)
    }
}
fn levels() -> Levels {
    Levels {
        black: 512.0,
        white: 15_360.0,
    }
}
fn domain() -> Result<PyramidDomain> {
    PyramidDomain::cropped(
        PlaneGeometry {
            width: SIDE / 2,
            height: SIDE / 2,
        },
        align_cmd::CropRect {
            x: 4,
            y: 4,
            width: ANALYSIS_SIDE,
            height: ANALYSIS_SIDE,
        },
    )
}
fn float_hash(values: &[f32]) -> String {
    digest(
        &values
            .iter()
            .flat_map(|v| v.to_bits().to_le_bytes())
            .collect::<Vec<_>>(),
    )
}
fn image_hash(image: &[Vec<f32>]) -> String {
    digest(
        &image
            .iter()
            .flatten()
            .flat_map(|v| v.to_bits().to_le_bytes())
            .collect::<Vec<_>>(),
    )
}
fn coarse_view(merge: &BandMerge) -> Vec<(usize, String, Vec<bool>)> {
    let mut result = Vec::new();
    merge.observe_accumulator(|o| {
        if o.level >= 2 {
            let values: Vec<_> = (0..o.size.pixels()).map(|i| o.coefficient(i)).collect();
            result.push((
                o.level,
                float_hash(&values),
                (0..o.size.pixels()).map(|i| o.averaging(i)).collect(),
            ));
        }
    });
    result
}
fn finish(merge: &BandMerge) -> Vec<Vec<f32>> {
    merge.finish(&mut Workspace::new(merge.sizes()))
}

struct Legacy {
    merge: BandMerge,
    beta: Vec<Vec<f32>>,
    beta_sum: Vec<f64>,
    beta_n: usize,
}
// Only scheduling is reproduced: every frame uses production BandWorker::fold,
// every chunk uses production BandMerge::absorb, and finish is unchanged core.
fn legacy(source: &Source, domain: PyramidDomain, per_chunk: usize) -> Result<Legacy> {
    let cfg = config(&source.case);
    let map = source.map(domain, None);
    let mut worker = BandWorker::new(domain, cfg);
    worker.fws.set_spatial_noise_floor_mode(Mode::Off);
    let mut merged: Option<BandMerge> = None;
    let mut beta = Vec::new();
    let mut beta_sum = Vec::<f64>::new();
    let mut beta_n = 0;
    for start in (0..source.len()).step_by(per_chunk) {
        let end = (start + per_chunk).min(source.len());
        for index in start..end {
            ensure!(
                worker.fold(source, index, levels(), &noise(false), Some(&map), None)?,
                "placed synthetic source refused"
            );
            ensure!(
                worker.beta.len() >= 2,
                "two changed bands require measured beta"
            );
            beta.push(worker.beta.clone());
        }
        if beta_sum.len() < worker.beta_sum.len() {
            beta_sum.resize(worker.beta_sum.len(), 0.0);
        }
        for (sum, value) in beta_sum.iter_mut().zip(&worker.beta_sum) {
            *sum += value;
        }
        beta_n += worker.beta_n;
        match merged.as_mut() {
            Some(acc) => acc.absorb(&worker.merge),
            None => {
                let geom = domain.analysis();
                merged = Some(std::mem::replace(
                    &mut worker.merge,
                    BandMerge::new(geom.width, geom.height, BAND_PLANES, cfg),
                ));
            }
        }
        if end < source.len() {
            worker.reset_chunk();
        }
    }
    assert_eq!(source.counts(), vec![1; source.len()]);
    Ok(Legacy {
        merge: merged.unwrap(),
        beta,
        beta_sum,
        beta_n,
    })
}
#[derive(Default)]
struct TraceState {
    active: usize,
    beta: Vec<Vec<f32>>,
    ready: Vec<(usize, usize, bool, Option<[usize; 2]>)>,
    folded: Vec<usize>,
    chunks: Vec<usize>,
    coarse_weights: Vec<(usize, usize, String)>,
    coarse_fold: Vec<Vec<(usize, String, Vec<bool>)>>,
    coarse_chunk: Vec<Vec<(usize, String, Vec<bool>)>>,
    absolute_floors: usize,
}
struct Trace {
    state: Mutex<TraceState>,
    expected_progress: crate::ui_progress::Progress,
    expected_events: Arc<Mutex<Vec<String>>>,
    level_count: usize,
    total: usize,
}
impl Trace {
    fn new(total: usize, level_count: usize) -> Self {
        let (expected_progress, expected_events) = crate::ui_progress::Progress::captured(total);
        Self {
            state: Mutex::new(TraceState::default()),
            expected_progress,
            expected_events,
            level_count,
            total,
        }
    }
}
impl MergeObserver for Trace {
    fn supports_absolute_floor(&self) -> bool {
        true
    }
    fn phase(&self, _: FoldPhase) {}
    fn band(&self, b: BandObservation<'_>) {
        let mut state = self.state.lock().unwrap();
        let index = state.active;
        if b.absolute_floor.is_some() {
            assert!(b.level < 2 && !state.ready.last().unwrap().2);
            assert!(b.variance.is_none());
            assert_eq!(b.floor_multiplier, 1.0);
            state.absolute_floors += 1;
        }
        if b.level >= 2 {
            state
                .coarse_weights
                .push((index, b.level, float_hash(b.weights)));
        }
        let first_absolute = b.absolute_floor.is_some() && state.absolute_floors == 1;
        drop(state);
        assert!(b.level < self.level_count);
        // Commission FrameTap's choice of array and scaling independently:
        // expected input goes directly from the consumer observation to surface.
        // No FrameTap call participates in this expected gate-floor payload.
        if let Some(floor) = b.absolute_floor {
            self.expected_progress.surface(
                index,
                b.level,
                "gate-floor",
                "frame",
                "log",
                1,
                b.size,
                |i| floor[i],
                None,
            );
            if first_absolute {
                let correct = floor_surfaces(&self.expected_events.lock().unwrap())
                    .pop()
                    .unwrap();
                let (foil, events) = crate::ui_progress::Progress::captured(self.total);
                let energy = b.energy.expect("temporal AC band has energy");
                foil.surface(
                    index,
                    b.level,
                    "gate-floor",
                    "frame",
                    "log",
                    1,
                    b.size,
                    |i| energy[i],
                    None,
                );
                foil.surface(
                    index,
                    b.level,
                    "gate-floor",
                    "frame",
                    "log",
                    1,
                    b.size,
                    |i| 2.0 * floor[i],
                    None,
                );
                let wrong = floor_surfaces(&events.lock().unwrap());
                assert_ne!(
                    correct, wrong[0],
                    "wrong-array payload foil is not detected"
                );
                assert_ne!(
                    correct, wrong[1],
                    "double-scaled full-F payload foil is not detected"
                );
            }
        } else if let Some(variance) = b.variance {
            self.expected_progress.surface(
                index,
                b.level,
                "gate-floor",
                "frame",
                "log",
                1,
                b.size,
                |i| b.floor_multiplier * variance[i].max(0.0),
                None,
            );
        }
    }
}
impl temporal_cpu::Observer for Trace {
    fn guide(&self, index: usize, beta: &[f32]) {
        let mut s = self.state.lock().unwrap();
        assert_eq!(index, s.beta.len());
        s.beta.push(beta.to_vec());
    }
    fn ready(&self, index: usize, chunk: usize, original: bool, neighbors: Option<[usize; 2]>) {
        let mut s = self.state.lock().unwrap();
        s.active = index;
        s.ready.push((index, chunk, original, neighbors));
    }
    fn folded(&self, index: usize, merge: &BandMerge) {
        let mut s = self.state.lock().unwrap();
        s.folded.push(index);
        s.coarse_fold.push(coarse_view(merge));
    }
    fn chunk(&self, chunk: usize, merge: &BandMerge) {
        let mut s = self.state.lock().unwrap();
        s.chunks.push(chunk);
        s.coarse_chunk.push(coarse_view(merge));
    }
}
fn fields(line: &str) -> BTreeMap<String, String> {
    line.split_whitespace()
        .filter_map(|part| part.split_once('='))
        .map(|(k, v)| (k.to_string(), v.to_string()))
        .collect()
}
fn floor_surfaces(events: &[String]) -> Vec<BTreeMap<String, String>> {
    events
        .iter()
        .filter_map(|line| {
            let mut f = fields(line);
            if f.get("kind").map(String::as_str) == Some("gate-floor")
                && f.get("scope").map(String::as_str) == Some("frame")
            {
                f.remove("seq");
                Some(f)
            } else {
                None
            }
        })
        .collect()
}
fn verify_events(events: &[String], expected: &[String], n: usize, bands: usize) {
    let starts: Vec<_> = events
        .iter()
        .map(|s| fields(s))
        .filter(|f| f.get("event").map(String::as_str) == Some("frame-started"))
        .collect();
    let ends: Vec<_> = events
        .iter()
        .map(|s| fields(s))
        .filter(|f| f.get("event").map(String::as_str) == Some("frame-finished"))
        .collect();
    assert_eq!(starts.len(), n);
    assert_eq!(ends.len(), n);
    for i in 0..n {
        assert_eq!(starts[i]["index"], i.to_string());
        assert_eq!(ends[i]["index"], i.to_string());
        assert_eq!(ends[i]["processed"], (i + 1).to_string());
        assert_eq!(ends[i]["accepted"], (i + 1).to_string());
    }
    let actual = floor_surfaces(events);
    let expected = floor_surfaces(expected);
    assert_eq!(
        actual.len(),
        n * bands,
        "missing or duplicated complete-floor surface"
    );
    assert_eq!(
        actual, expected,
        "actual scheduler surface differs from consumed full F"
    );
}
struct Run {
    result: temporal_cpu::FoldResult,
    image: Vec<Vec<f32>>,
    state: TraceState,
    events: Vec<String>,
    hashes: Vec<Option<String>>,
}
fn production(
    case: &Case,
    noisy: bool,
    reverse: bool,
    per_chunk: usize,
    mode: TemporalMode,
    domain: PyramidDomain,
) -> Result<Run> {
    let source = Source::new(case, noisy, reverse);
    let map = source.map(domain, None);
    let mut worker = BandWorker::new(domain, config(case));
    worker.fws.set_spatial_noise_floor_mode(Mode::Off);
    let levels_count = worker.merge.sizes().len();
    let trace = Trace::new(case.n, levels_count);
    let (progress, events) = crate::ui_progress::Progress::captured(case.n);
    let result = temporal_cpu::fold(
        &source,
        &mut worker,
        levels(),
        &noise(false),
        Some(&map),
        None,
        Some(&progress),
        case.n,
        per_chunk,
        mode,
        Some(&trace),
    )?;
    let events = events.lock().unwrap().clone();
    verify_events(
        &events,
        &trace.expected_events.lock().unwrap(),
        case.n,
        levels_count - 1,
    );
    let state = trace.state.into_inner().unwrap();
    assert_eq!(
        source.counts(),
        vec![2; case.n],
        "each source is generated once per guide and once per center"
    );
    assert_eq!(state.folded, (0..case.n).collect::<Vec<_>>());
    assert_eq!(result.folded_total, case.n);
    assert_eq!(result.merge.frames() as usize, case.n);
    assert_eq!(
        state.chunks,
        (0..case.n.div_ceil(per_chunk)).collect::<Vec<_>>()
    );
    for &(index, chunk, original, neighbors) in &state.ready {
        assert_eq!(chunk, index / per_chunk);
        let unchanged =
            mode == TemporalMode::Off || case.n < 3 || index == 0 || index + 1 == case.n;
        assert_eq!(original, unchanged);
        assert_eq!(
            neighbors,
            (!unchanged).then_some([index.wrapping_sub(1), index + 1])
        );
    }
    assert_eq!(
        state.absolute_floors,
        if mode == TemporalMode::Off {
            0
        } else {
            case.n.saturating_sub(2) * 2
        }
    );
    let image = finish(&result.merge);
    assert!(image.iter().flatten().all(|v| v.is_finite()));
    let hashes = source.hashes.into_inner().unwrap();
    Ok(Run {
        result,
        image,
        state,
        events,
        hashes,
    })
}
fn negatives(domain: PyramidDomain) -> Result<Value> {
    let mut c = case("negative-controls", 5, "broad", 120.0, 94);
    c.geometry = "identity";
    let source = Source::new(&c, true, false);
    let refused = source.map(domain, Some(2));
    let cfg = config(&c);
    let mut worker = BandWorker::new(domain, cfg);
    let err = temporal_cpu::fold(
        &source,
        &mut worker,
        levels(),
        &noise(false),
        Some(&refused),
        None,
        None,
        c.n,
        2,
        TemporalMode::On,
        None,
    )
    .err()
    .context("refused placement accepted")?;
    assert!(err.to_string().contains("refused"));
    assert_eq!(source.counts(), vec![0; c.n]);
    let good = source.map(domain, None);
    assert!(temporal_cpu::preflight(cfg, c.n, Some(&good), true).is_err());
    assert_eq!(source.counts(), vec![0; c.n]);
    struct Unaware;
    impl MergeObserver for Unaware {
        fn phase(&self, _: FoldPhase) {}
        fn band(&self, _: BandObservation<'_>) {}
    }
    impl temporal_cpu::Observer for Unaware {}
    assert!(
        temporal_cpu::fold(
            &source,
            &mut worker,
            levels(),
            &noise(false),
            Some(&good),
            None,
            None,
            c.n,
            2,
            TemporalMode::On,
            Some(&Unaware)
        )
        .is_err()
    );
    assert_eq!(source.counts(), vec![0; c.n]);
    assert!(preflight_temporal_dispatch(MergeBackend::Estimator, Some("on"), true).is_err());
    assert!(preflight_temporal_dispatch(MergeBackend::Pyramid, Some("on"), false).is_err());
    assert!(preflight_temporal_dispatch(MergeBackend::Pyramid, Some("typo"), true).is_err());
    preflight_temporal_dispatch(MergeBackend::Estimator, None, false)?;
    preflight_temporal_dispatch(MergeBackend::Estimator, Some("off"), false)?;
    preflight_temporal_dispatch(MergeBackend::Pyramid, Some("on"), true)?;
    assert!(temporal_cpu::parse_mode(Some("unknown")).is_err());
    assert_eq!(temporal_cpu::parse_mode(None)?, TemporalMode::Off);
    assert_eq!(temporal_cpu::parse_mode(Some("on"))?, TemporalMode::On);
    assert_eq!(
        temporal_cpu::parse_mode(Some("shift"))?,
        TemporalMode::ShiftNeighbors
    );
    assert!(temporal_cpu::memory_preflight(usize::MAX, 1, worker.merge.sizes()).is_err());
    assert!(temporal_cpu::memory_preflight(MEMORY_BUDGET_BYTES, 1, worker.merge.sizes()).is_err());
    assert!(temporal_cpu::memory_preflight(0, 0, worker.merge.sizes())? > 0);
    let mut changed = Source::new(&c, true, false);
    changed.corrupt_second = true;
    let mut worker = BandWorker::new(domain, cfg);
    let failed = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        temporal_cpu::fold(
            &changed,
            &mut worker,
            levels(),
            &noise(false),
            Some(&good),
            None,
            None,
            c.n,
            2,
            TemporalMode::On,
            None,
        )
    }));
    assert!(
        failed.is_err(),
        "guide/center source mutation escaped binding"
    );
    assert_eq!(worker.merge.frames(), 0, "binding rejection mutated merge");
    assert_eq!(changed.counts()[0], 2);
    Ok(
        json!({"refused_before_decode":true,"region_recipe_rejected":true,"unaware_observer_before_decode":true,
        "invalid_mode_rejected":true,"memory_overflow_and_budget_rejected":true,"source_binding_mutation_rejected_before_fold":true}),
    )
}

fn defect_accounting(domain: PyramidDomain) -> Result<Value> {
    use strehl_core::defect_map::{CoordSpace, Correction, DefectMap, HotFloor, HotSite};
    let c = case("defect-accounting", 5, "broad", 120.0, 97);
    let plan = crate::stack::DefectPlan {
        map: DefectMap {
            sensor_w: SIDE,
            sensor_h: SIDE,
            covered_w: SIDE,
            covered_h: SIDE,
            coords: CoordSpace::Active,
            camera: "generated-fixture".into(),
            aperture_f: None,
            hot: vec![HotSite {
                x: 65,
                y: 64,
                excess_e: 40.0,
            }],
            dust: vec![],
            provenance: vec![],
        },
        correction: Correction::HOT,
        floor: HotFloor::CENSUS,
        gain_dn_per_e: 0.5,
    };
    let source = Source::new(&c, true, false);
    let map = source.map(domain, None);
    let tally = crate::stack::DefectTally::default();
    let mut worker = BandWorker::new(domain, config(&c));
    worker.fws.set_spatial_noise_floor_mode(Mode::Off);
    let mut beta = Vec::new();
    for i in 0..c.n {
        ensure!(worker.fold(
            &source,
            i,
            levels(),
            &noise(false),
            Some(&map),
            Some((&plan, &tally))
        )?);
        beta.push(worker.beta.clone());
    }
    let original = finish(&worker.merge);
    let expected = tally.report();
    assert_eq!(tally.frames(), c.n);
    assert_eq!(expected.hot_examined, c.n);
    assert_eq!(expected.hot_corrected, c.n);
    assert_eq!(expected.samples_changed, c.n);
    for mode in [
        TemporalMode::Off,
        TemporalMode::On,
        TemporalMode::ShiftNeighbors,
    ] {
        let source = Source::new(&c, true, false);
        let tally = crate::stack::DefectTally::default();
        let mut worker = BandWorker::new(domain, config(&c));
        worker.fws.set_spatial_noise_floor_mode(Mode::Off);
        let trace = Trace::new(c.n, worker.merge.sizes().len());
        let result = temporal_cpu::fold(
            &source,
            &mut worker,
            levels(),
            &noise(false),
            Some(&map),
            Some((&plan, &tally)),
            None,
            c.n,
            c.n,
            mode,
            Some(&trace),
        )?;
        assert_eq!(
            tally.frames(),
            c.n,
            "guide pass double-counted defect frames"
        );
        assert_eq!(
            tally.report(),
            expected,
            "guide pass double-counted defect corrections"
        );
        assert_eq!(
            trace.state.lock().unwrap().beta,
            beta,
            "corrected guide beta changed"
        );
        if mode == TemporalMode::Off {
            assert_eq!(finish(&result.merge), original);
        }
    }
    Ok(
        json!({"frames":c.n,"hot_examined":expected.hot_examined,"hot_corrected":expected.hot_corrected,
        "samples_changed":expected.samples_changed,"all_modes_exactly_once":true,"guide_center_correction_binding":true}),
    )
}

#[test]
#[ignore = "root schedules production scheduler commissioning; new absolute output required"]
fn temporal_normal_cpu_falsifier() -> Result<()> {
    let out = PathBuf::from(
        std::env::var_os("STREHL_TEMPORAL_CPU_OUT").context("set STREHL_TEMPORAL_CPU_OUT")?,
    );
    ensure!(
        out.is_absolute() && !out.exists(),
        "fresh absolute output required"
    );
    ensure!(
        std::env::var("STREHL_FIX_CA").as_deref() == Ok("0"),
        "synthetic CA must be off"
    );
    ensure!(
        align_cmd::fullres_gather_enabled(),
        "normal fullres gather required"
    );
    ensure!(gatefloor::enabled(), "actual measured gate floor required");
    ensure!(
        std::env::var("STREHL_GATE_FLOOR_SCALE").is_err(),
        "unset floor override"
    );
    ensure!(
        std::env::var("STREHL_SPATIAL_NOISE_FLOOR").as_deref() == Ok("off"),
        "explicit spatial Off required"
    );
    ensure!(
        std::env::var("STREHL_DEMOSAIC").is_err(),
        "unset demosaic override"
    );
    let domain = domain()?;
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let sources = [
        "experiments/rea-a7c2-2026-10-24-d/normal-cpu-fixture.rs",
        "experiments/rea-a7c2-2026-10-24-d/temporal-finish.rs",
        "crates/strehl-cli/src/merge_cmd/temporal-cpu.rs",
        "crates/strehl-cli/src/merge_cmd.rs",
        "crates/strehl-core/src/temporal-energy.rs",
        "crates/strehl-core/src/pyramid.rs",
        "crates/strehl-cli/src/ui-diagnostics.rs",
        "crates/strehl-cli/src/merge_cmd/gatefloor.rs",
    ];
    for (name, expected) in [
        (
            "noise-floor-gather.rs",
            "59d82721432978bfd60324a5a832ad0ee4b6434257ac909501ce2be0bf3a45cd",
        ),
        (
            "noise-floor-reconstruction.rs",
            "bb7515c9ead0902b5c02217b0fea9ce112d5fb3ec167140240d62850bf9b9f48",
        ),
    ] {
        let file = root.join("experiments/rea-a7c2-2026-10-24-c").join(name);
        ensure!(
            digest(&fs::read(file)?) == expected,
            "frozen c helper changed: {name}"
        );
    }
    let source_hashes: Vec<_> = sources
        .iter()
        .map(|s| -> Result<Value> {
            Ok(json!({"path":s,"sha256":digest(&fs::read(root.join(s))?)}))
        })
        .collect::<Result<_>>()?;
    let exe = std::env::current_exe()?;
    let environment: BTreeMap<_, _> = std::env::vars()
        .filter(|(k, _)| k.starts_with("STREHL_") || k == "RAYON_NUM_THREADS")
        .collect();
    fs::create_dir(&out)?;
    fs::write(
        out.join("plan.json"),
        serde_json::to_vec_pretty(
            &json!({"status":"RUNNING until summary.json", "source_hashes":source_hashes,
        "executable":exe,"executable_sha256":digest(&fs::read(&exe)?),"environment":environment,"workers":rayon::current_num_threads(),
        "measurement":"production scheduler commissioning, not photographic quality", "source_native":[SIDE,SIDE], "analysis_quad":[ANALYSIS_SIDE,ANALYSIS_SIDE],
        "stored_inputs":"regenerated u16 CFA, no aligned frame volume", "floor_probe_seed":"actual processing ordinal; no private calibration",
        "coarse_observable":"exact shared weights, resolved green coefficient and fallback state per fold/chunk; core unit tests own raw all-plane accumulator invariants",
        "partition_comparison":"Off exact legacy within each partition; cross-partition arithmetic grouping is not required bitwise equal"}),
        )?,
    )?;
    let negative = negatives(domain)?;
    let defect_accounting = defect_accounting(domain)?;
    let mut flat = case("flat-first", 5, "flat", 0.0, 90);
    flat.geometry = "identity";
    let weak = case("weak-phase", 9, "one", 55.0, 91);
    let mut curved = case("mixed-curved", 9, "fine-coarse", 120.0, 92);
    curved.geometry = "curved";
    let mut short1 = case("short-one", 1, "broad", 120.0, 93);
    short1.geometry = "identity";
    let short2 = case("short-two", 2, "broad", 120.0, 93);
    let mut constant = case("constant-noiseless", 5, "broad", 120.0, 95);
    constant.constant = true;
    let jobs = [
        (flat, vec![2], true, false),
        (weak.clone(), vec![1, 4, 9], true, false),
        (curved, vec![4, 9], true, false),
        (short1, vec![1], true, false),
        (short2, vec![1], true, false),
        (constant, vec![2], false, false),
        (weak, vec![4, 9], true, true),
    ];
    let mut reports = Vec::new();
    for (c, chunks, noisy, reverse) in jobs {
        for chunk in chunks {
            let label = format!(
                "{}-chunk{chunk}-{}",
                c.name,
                if reverse { "reverse" } else { "forward" }
            );
            let legacy_source = Source::new(&c, noisy, reverse);
            let legacy = legacy(&legacy_source, domain, chunk)?;
            let legacy_image = finish(&legacy.merge);
            let mut runs = Vec::new();
            for mode in [
                TemporalMode::Off,
                TemporalMode::On,
                TemporalMode::ShiftNeighbors,
            ] {
                let run = production(&c, noisy, reverse, chunk, mode, domain)?;
                assert_eq!(
                    run.state.beta, legacy.beta,
                    "guide beta differs from actual original scheduler"
                );
                assert_eq!(
                    run.result.beta_sum, legacy.beta_sum,
                    "beta accounted twice or changed"
                );
                assert_eq!(run.result.beta_n, legacy.beta_n);
                assert_eq!(run.hashes, *legacy_source.hashes.lock().unwrap());
                assert_eq!(coarse_view(&run.result.merge), coarse_view(&legacy.merge));
                if mode == TemporalMode::Off {
                    assert_eq!(
                        image_hash(&run.image),
                        image_hash(&legacy_image),
                        "Off output bits changed"
                    );
                    assert_eq!(
                        run.image, legacy_image,
                        "Off changed original canonical scheduler output"
                    );
                }
                if c.n < 3 {
                    assert_eq!(run.image, legacy_image, "short stack must remain original");
                }
                if c.constant {
                    assert!(
                        max_difference(&run.image, &legacy_image) <= 0.001,
                        "constant noiseless source changed"
                    );
                }
                runs.push(run);
            }
            for arm in 1..3 {
                assert_eq!(runs[arm].state.coarse_weights, runs[0].state.coarse_weights);
                assert_eq!(runs[arm].state.coarse_fold, runs[0].state.coarse_fold);
                assert_eq!(runs[arm].state.coarse_chunk, runs[0].state.coarse_chunk);
            }
            // One complete production chunk must match the independently staged
            // d core adapter using the production-measured source-attached beta.
            let mut core_match = false;
            if chunk == c.n && !c.constant {
                let mut beta_by_original = legacy.beta.clone();
                if reverse {
                    beta_by_original.reverse();
                }
                let reference = stack(
                    &c,
                    0,
                    noisy,
                    true,
                    reverse,
                    &[3, 2, 4],
                    domain,
                    &beta_by_original,
                )?;
                for (a, expected) in [1usize, 2, 3].into_iter().enumerate() {
                    assert_eq!(
                        runs[a].image, reference.outputs[expected],
                        "production/core consumer mismatch"
                    );
                }
                core_match = true;
            }
            let dir = out.join(&label);
            fs::create_dir(&dir)?;
            let mut arm_reports = Vec::new();
            for (i, run) in runs.iter().enumerate() {
                let name = ["off", "on", "shift"][i];
                let saved = save_output(
                    &dir,
                    name,
                    &run.image,
                    LevelSize {
                        width: ANALYSIS_SIDE,
                        height: ANALYSIS_SIDE,
                    },
                )?;
                fs::write(
                    dir.join(format!("{name}-events.txt")),
                    run.events.join("\n") + "\n",
                )?;
                arm_reports.push(json!({"arm":name,"output":saved,"image_sha256":image_hash(&run.image),"beta_sum":run.result.beta_sum,
                    "beta_n":run.result.beta_n,"ready":run.state.ready,"absolute_floor_observations":run.state.absolute_floors,
                    "folded":run.state.folded,"chunks":run.state.chunks}));
            }
            reports.push(json!({"case":label,"n":c.n,"per_chunk":chunk,"noisy":noisy,"reversed":reverse,"geometry":c.geometry,
                "legacy_off_exact":true,"global_neighbor_indices_exact":true,"coarse_observables_exact":true,"beta_accounting_exact":true,
                "actual_floor_surfaces_exact":true,"core_adapter_match":core_match,"source_sha256":runs[0].hashes,"arms":arm_reports}));
            fs::write(
                out.join("completed.json"),
                serde_json::to_vec_pretty(&reports)?,
            )?;
            eprintln!("normal CPU completed {label}");
        }
    }
    fs::write(
        out.join("summary.json"),
        serde_json::to_vec_pretty(
            &json!({"status":"COMPLETE","negative_controls":negative,"defect_accounting":defect_accounting,"cases":reports}),
        )?,
    )?;
    Ok(())
}
