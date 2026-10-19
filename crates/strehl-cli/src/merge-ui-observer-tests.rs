use super::*;

struct GeneratedSource(Vec<Frame>);

impl PyramidFrameSource for GeneratedSource {
    fn len(&self) -> usize {
        self.0.len()
    }
    fn decode(&self, index: usize) -> Result<Frame> {
        Ok(self.0[index].clone())
    }
}

#[test]
fn actual_worker_refusal_has_no_fold_and_observer_preserves_output() {
    // A decoded, constant frame rejects all detail weights; the next frame
    // supplies real signal. A third alignment-refused frame must decode but
    // must never reach extraction or a band fold. No RAW decoder is used.
    let levels = Levels {
        black: 64.0,
        white: 16_000.0,
    };
    let full = PlaneGeometry {
        width: 48,
        height: 40,
    };
    let source = GeneratedSource(
        (0..3)
            .map(|frame| Frame {
                data: (0..96 * 80)
                    .map(|i| {
                        if frame == 0 {
                            1064
                        } else {
                            let x = i % 96 / 2;
                            let y = i / 96 / 2;
                            if (x / 3 + y / 4) % 2 == 0 { 1864 } else { 264 }
                        }
                    })
                    .collect(),
                stride: 96,
                buffer_height: 80,
                active: strehl_raw::Region {
                    x: 0,
                    y: 0,
                    width: 96,
                    height: 80,
                },
                levels,
                iso: Some(100.0),
                wb_coeffs: [1.0; 4],
                xyz_to_cam_rgbe: [[0.0; 3]; 4],
                color_matrices: Vec::new(),
                camera: "GENERATED".into(),
                path: PathBuf::from(format!("generated-observer-{frame}.arw")),
            })
            .collect(),
    );
    let entries: Vec<_> = source
        .0
        .iter()
        .map(|frame| (frame.path.to_string_lossy(), frame.allocated_bytes() as u64))
        .collect();
    let warps = WarpMap::new(
        strehl_core::warpmap::Provenance {
            stack: StackIdentity::from_entries("generated observer refusal", &entries),
            strategy: "fixed generated identity".into(),
            heldout_px: None,
            cycle_floor_px: None,
            reference: 0,
            note: "observer control, no alignment accuracy claim".into(),
        },
        full,
        Resampler::CatmullRom,
        vec![
            FrameWarp::Placed(strehl_core::align::Similarity::IDENTITY),
            FrameWarp::Placed(strehl_core::align::Similarity::IDENTITY),
            FrameWarp::Refused("generated refusal".into()),
        ],
    );
    let cfg = MergeConfig {
        bands: 3,
        ..MergeConfig::default()
    };
    let noise = profile::noise_model_for("GENERATED", Some(100.0), levels);
    let (progress, lines) = crate::ui_progress::Progress::captured(source.len());
    // Full-field gather marks unsupported boundary samples black. Crop to a
    // genuinely constant interior so that this is a flat-field control rather
    // than an artificial edge at the gather's coverage boundary.
    let domain = PyramidDomain::cropped(
        full,
        align_cmd::CropRect {
            x: 6,
            y: 6,
            width: 36,
            height: 28,
        },
    )
    .unwrap();
    let mut plain = BandWorker::new(domain, cfg);
    let mut observed = BandWorker::new(domain, cfg);
    // Calibration is injected and identical. The measured-floor experiment is
    // outside this small observer fixture, rather than fitted to its own plant.
    plain.floor = None;
    observed.floor = None;
    for index in 0..source.len() {
        let expected = index != 2;
        assert_eq!(
            plain
                .fold(&source, index, levels, &noise, Some(&warps), None)
                .unwrap(),
            expected
        );
        assert_eq!(
            observed
                .fold_observed(
                    &source,
                    index,
                    levels,
                    &noise,
                    Some(&warps),
                    None,
                    Some(&progress)
                )
                .unwrap(),
            expected
        );
        if index == 0 {
            assert!(
                observed.luma.iter().all(|value| *value == 1000.0),
                "the alleged flat control must actually stay flat after gather"
            );
        }
    }
    let lines = lines.lock().unwrap();
    assert!(
        lines
            .iter()
            .any(|line| line.contains("event=merge-step index=2 name=decode state=finished"))
    );
    assert!(
        lines
            .iter()
            .any(|line| line.contains("event=merge-step index=2 name=gather state=skipped"))
    );
    assert!(!lines.iter().any(
        |line| line.contains("event=merge-step index=2 name=extract")
            || line.contains("event=band-work index=2 ")
    ));
    let size = domain.analysis();
    let sizes = level_sizes(size.width, size.height, cfg.bands);
    for level in 0..sizes.len() {
        assert!(lines.iter().any(|line| line.contains(&format!(
            "event=band-work index=1 level={level} completed=2 total=3"
        ))));
    }
    let support: Vec<_> = lines
        .iter()
        .filter(|line| line.contains("kind=gate-support "))
        .collect();
    assert!(
        support.iter().any(|line| line.contains("frame=0 ")),
        "flat control was not observed"
    );
    assert!(
        support
            .iter()
            .filter(|line| line.contains("frame=0 "))
            .all(|line| line
                .split("data=")
                .nth(1)
                .unwrap()
                .bytes()
                .all(|v| v == b'0')),
        "flat control claimed selected detail"
    );
    assert!(
        support
            .iter()
            .any(|line| line.contains("frame=1 ")
                && line.split("data=").nth(1).unwrap().contains("ff")),
        "positive control did not reach real weighted bands"
    );
    let finish = |worker: &BandWorker| {
        worker
            .merge
            .finish(&mut Workspace::new(&sizes))
            .into_iter()
            .flatten()
            .map(f32::to_bits)
            .collect::<Vec<_>>()
    };
    assert_eq!(finish(&plain), finish(&observed));

    // The production confidence pass must observe real refused loads and real
    // comparisons. Equal arithmetic from a hand-written mock would not test
    // these boundaries. Compare its actual arrays with the observer absent.
    let paths: Vec<_> = source.0.iter().map(|frame| frame.path.clone()).collect();
    let merged_luma = vec![1000.0; domain.analysis().pixels()];
    let baseline = confidence_pass(
        &source,
        &paths,
        domain,
        levels,
        Some(&warps),
        None,
        &merged_luma,
        1,
    )
    .unwrap();
    let (confidence, receipts) = crate::ui_progress::Progress::captured(source.len());
    let measured = confidence_pass_observed(
        &source,
        &paths,
        domain,
        levels,
        Some(&warps),
        None,
        &merged_luma,
        1,
        Some(&confidence),
    )
    .unwrap();
    assert_eq!(baseline.below, measured.below);
    assert_eq!(baseline.seen, measured.seen);
    assert!(
        measured.seen.iter().all(|&seen| seen == 2),
        "refused frame must not enter the arithmetic"
    );
    assert!(
        measured.below.contains(&0) && measured.below.contains(&1),
        "fixture must actually exercise both sides of the merged-luma comparison"
    );
    let receipts = receipts.lock().unwrap();
    assert!(
        receipts
            .first()
            .unwrap()
            .contains("event=confidence-pass state=started completed=0 compared=0 total=3")
    );
    assert!(
        receipts
            .last()
            .unwrap()
            .contains("event=confidence-pass state=finished completed=3 compared=2 total=3")
    );
    assert_eq!(receipts.len(), 5);
    let mut completed = 0;
    let mut compared = 0;
    let mut identities = std::collections::BTreeSet::new();
    for line in &receipts[1..4] {
        let fields: std::collections::BTreeMap<_, _> = line
            .split_whitespace()
            .filter_map(|part| part.split_once('='))
            .collect();
        let index: usize = fields["index"].parse().unwrap();
        let mapped = fields["mapped"] == "true";
        assert_eq!(mapped, index != 2);
        assert!(identities.insert(index));
        completed += 1;
        compared += usize::from(mapped);
        assert_eq!(fields["completed"].parse::<usize>().unwrap(), completed);
        assert_eq!(fields["compared"].parse::<usize>().unwrap(), compared);
    }
}
