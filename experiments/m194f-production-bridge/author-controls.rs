// M194f author checks; independent TIFF readout is owned by the verifier.
use super::*;

fn require_private_environment() -> Result<()> {
    let required = [
        ("STREHL_DEFECT", "off"),
        ("STREHL_FIX_CA", "off"),
        ("STREHL_FULLRES_GATHER", "1"),
        ("STREHL_PYRAMID_WORKERS", "2"),
    ];
    for (k, v) in required {
        ensure!(
            std::env::var(k).as_deref() == Ok(v),
            "private control requires {k}={v}"
        );
    }
    ensure!(
        std::env::var("RAYON_NUM_THREADS").as_deref() == Ok("2"),
        "private control requires two Rayon threads"
    );
    for (k, _) in std::env::vars() {
        if k.to_ascii_uppercase().starts_with("STREHL_") {
            ensure!(
                k == "STREHL_M194F_PRIVATE_OUTPUT" || required.iter().any(|(key, _)| k == *key),
                "unexpected private override {k}"
            );
        }
    }
    Ok(())
}
fn private_rgb_files(root: &Path, label: &str) -> Result<(Vec<PathBuf>, Vec<String>)> {
    let mut data = Vec::with_capacity(64 * 48);
    for y in 0..48 {
        for x in 0..64 {
            let (r, g, b) = if label == "constant" {
                (2000, 3000, 2500)
            } else {
                (2000 + 80 * x, 3000 + 100 * y, 2500 + 40 * x + 60 * y)
            };
            let mut value = match (y % 2, x % 2) {
                (0, 0) => r * 3 / 4,
                (1, 1) => b * 3 / 5,
                _ => g,
            };
            if label == "mutation" && (x, y) == (29, 26) {
                value += 64;
            }
            data.push((512 + value) as u16);
        }
    }
    let bytes: Vec<_> = data.iter().flat_map(|v| v.to_le_bytes()).collect();
    let mut paths = Vec::new();
    let mut hashes = Vec::new();
    for i in 0..5 {
        let path = root.join(format!("{label}-{i}.cfa"));
        fs::write(&path, &bytes)?;
        paths.push(path);
        hashes.push(digest(&bytes));
    }
    Ok((paths, hashes))
}
struct RankSource {
    calls: Vec<AtomicUsize>,
}
impl PyramidFrameSource for RankSource {
    fn len(&self) -> usize {
        5
    }
    fn decode(&self, index: usize) -> Result<Frame> {
        let green = *([100, 200, 200, 400, 500]
            .get(index)
            .context("rank frame index")?);
        let mut data = Vec::with_capacity(32 * 16);
        for y in 0..16 {
            for x in 0..32 {
                data.push(
                    512 + match (y % 2, x % 2) {
                        (0, 0) => 700,
                        (1, 1) => 900,
                        _ => green,
                    },
                );
            }
        }
        let frame = bridge_frame(data, 32, 16, index);
        self.calls[index].fetch_add(1, Ordering::SeqCst);
        Ok(frame)
    }
}
#[test]
fn m194f_author_default_and_configuration_controls() -> Result<()> {
    let full = PlaneGeometry::from_active(64, 48);
    let cfg = options(PathBuf::new()).pyramid;
    ensure!(
        cfg.admission == AdmissionMode::HardFloor
            && MergeConfig::default().admission == AdmissionMode::HardFloor,
        "default admission"
    );
    let levels = level_sizes(full.width, full.height, cfg.bands);
    ensure!(
        levels.len() == 2 && levels[0].width == 32 && levels[0].height == 24,
        "tiny fixture pyramid support"
    );
    let noise = bridge_noise();
    let green = noise.plane(CfaPlane::G1);
    ensure!(
        green.gain_dn_per_e == 0.25
            && green.read_noise_e == 4.0
            && green.levels.black == 512.0
            && green.levels.white == 15360.0
            && (green.variance(3000.0) - 751.0).abs() < 1e-6,
        "explicit injected noise coefficients"
    );
    let identity = identity_map(full);
    ensure!(
        identity.warps().len() == 5
            && identity
                .warps()
                .iter()
                .all(|w| matches!(w,FrameWarp::Placed(t) if *t==Similarity::IDENTITY)),
        "identity input map"
    );
    let bad = BridgeSettings {
        observer: ObserverMode::Count,
        confidence: false,
        exposure: 2,
        wb_mode: WbMode::Baseline,
    };
    ensure!(bad.validate().is_err(), "unsupported exposure must refuse");
    ensure!(
        BridgeSettings { exposure: 1, ..bad }.validate().is_err()
            && Exposure::resolve(false, 1.0, false).is_err()
            && matches!(Exposure::resolve(false, 0.0, false), Ok(Exposure::None)),
        "original exposure1 refusal and exposure0 companion"
    );
    let baseline = WbMode::Baseline.gains();
    let red_double = WbMode::RedDouble.gains();
    ensure!(
        WbMode::parse("baseline")? == WbMode::Baseline
            && WbMode::parse("red-double")? == WbMode::RedDouble
            && WbMode::parse("unknown").is_err()
            && red_double == [2.0 * baseline[0], baseline[1], baseline[2]]
            && bridge_frame(vec![512; CFA_BYTES / 2], 64, 48, 0).wb_gains() == Some(baseline),
        "registered writer WB modes and unchanged frame WB"
    );
    let mut shifted =
        json!({"schema":"m194f-consumer-plan-v1","crop_quad":{"x":3,"y":5,"width":24,"height":16}});
    let original = shifted.clone();
    shifted["crop_quad"]["x"] = json!(4);
    ensure!(
        validate_plan(&original, &original).is_ok() && validate_plan(&shifted, &original).is_err(),
        "same-size shifted plan refusal"
    );
    Ok(())
}
#[test]
#[ignore = "M194f private intended five-TIFF component population, explicit fresh output"]
fn m194f_private_coordinate_and_rank_controls() -> Result<()> {
    require_private_environment()?;
    let root = PathBuf::from(
        std::env::var("STREHL_M194F_PRIVATE_OUTPUT").context("private output required")?,
    );
    ensure!(!root.exists(), "private output already exists");
    fs::create_dir_all(&root)?;
    let crop = align_cmd::CropRect {
        x: 3,
        y: 5,
        width: 24,
        height: 16,
    };
    let domain = PyramidDomain::cropped(PlaneGeometry::from_active(64, 48), crop)?;
    let fit = align_cmd::CoverFit::Cropped { k: 1.0, rect: crop };
    let settings = BridgeSettings {
        observer: ObserverMode::Count,
        confidence: false,
        exposure: 0,
        wb_mode: WbMode::Baseline,
    };
    let mut rgb = serde_json::Map::new();
    let mut rgb_counts = serde_json::Map::new();
    for label in ["constant", "affine", "mutation"] {
        let (paths, hashes) = private_rgb_files(&root, label)?;
        let source = BridgeSource::new(paths, hashes, ObserverMode::Count)?;
        let output = root.join(format!("{label}.tif"));
        let opts = bridge_options(output.clone(), settings, None)?;
        run_bridge_source(&opts, &source, domain, fit)?;
        ensure!(
            source.success_counts() == vec![1; 5] && source.hook_calls() == 5,
            "private RGB source reads"
        );
        rgb.insert(label.into(), tiff_receipt(&output, 3)?);
        rgb_counts.insert(label.into(), json!(source.success_counts()));
    }
    let rank_source = RankSource {
        calls: (0..5).map(|_| AtomicUsize::new(0)).collect(),
    };
    let rank_full = PlaneGeometry::from_active(32, 16);
    let rank_domain = PyramidDomain::whole(rank_full);
    let paths: Vec<_> = (0..5)
        .map(|i| PathBuf::from(format!("M194F-RANK-NO-SUCH-RAW-{i}.ARW")))
        .collect();
    ensure!(
        paths.iter().all(|p| !p.exists()),
        "rank RAW sentinel exists"
    );
    let row = [99.0, 100.0, 200.0, 201.0, 300.0, 400.0, 500.0, 501.0];
    let merged: Vec<f32> = (0..rank_full.pixels()).map(|i| row[i % 8]).collect();
    let c = confidence_pass(
        &rank_source,
        &paths,
        rank_domain,
        bridge_levels(),
        None,
        None,
        &merged,
        2,
    )?;
    let expected = [0, 0, 1, 3, 3, 3, 4, 5];
    ensure!(
        c.below
            .iter()
            .enumerate()
            .all(|(i, &b)| b == expected[i % 8])
            && c.seen == vec![5; 128],
        "actual centrality counts"
    );
    let counts: Vec<_> = rank_source
        .calls
        .iter()
        .map(|n| n.load(Ordering::SeqCst))
        .collect();
    ensure!(counts == vec![1; 5], "rank component decode counts");
    let rank = root.join("rank.tif");
    write_confidence_map(&rank, &c, rank_full)?;
    let mut sentinel = Centrality {
        below: c.below.clone(),
        seen: c.seen.clone(),
    };
    sentinel.below[0] = 0;
    sentinel.seen[0] = 0;
    let sentinel_path = root.join("rank-sentinel.tif");
    write_confidence_map(&sentinel_path, &sentinel, rank_full)?;
    write_json_new(
        &root.join("private-controls.json"),
        &json!({"schema":"m194f-private-controls-v1","status":"complete","fixture_only":true,
        "rgb":rgb,"rgb_successful_decode_counts":rgb_counts,"gray":{"rank":tiff_receipt(&rank,1)?,"sentinel":tiff_receipt(&sentinel_path,1)?},
        "crop_quad":{"x":3,"y":5,"width":24,"height":16},"canonical_native_offset":[6,10],"oracle_output_window":[14,14,34,18],
        "confidence_component":{"native":[32,16],"quad":[16,8],"input_green_dn":[100,200,200,400,500],"merged_luma_dn":merged,
            "below":c.below,"seen":c.seen,"sentinel_below":sentinel.below,"sentinel_seen":sentinel.seen,
            "successful_decode_counts":counts,"sentinel_index":0,"reached_zero_index":1}}),
    )?;
    Ok(())
}
