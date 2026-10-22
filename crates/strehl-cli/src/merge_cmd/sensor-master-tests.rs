use super::*;

fn geometry() -> Geometry {
    Geometry {
        full_quad_width: 11,
        full_quad_height: 9,
        crop_quad: [3, 5, 2, 2],
    }
}

fn planes() -> Vec<Vec<f32>> {
    // Asymmetric channels/rows detect transposition and the CfaPlane::ALL trap.
    vec![
        vec![-3.5, -0.0, 7.0, 90000.0],
        vec![11.0, 12.0, 13.0, 14.0],
        vec![21.0, 22.0, 23.0, 24.0],
        vec![31.0, 32.0, 33.0, 34.0],
    ]
}

fn tag(bytes: &[u8], sought: u16) -> (u16, u32, u32) {
    assert_eq!(&bytes[..8], b"II\x2a\x00\x08\x00\x00\x00");
    let count = u16::from_le_bytes(bytes[8..10].try_into().unwrap()) as usize;
    for entry in bytes[10..10 + count * 12].chunks_exact(12) {
        if u16::from_le_bytes(entry[..2].try_into().unwrap()) == sought {
            return (
                u16::from_le_bytes(entry[2..4].try_into().unwrap()),
                u32::from_le_bytes(entry[4..8].try_into().unwrap()),
                u32::from_le_bytes(entry[8..12].try_into().unwrap()),
            );
        }
    }
    panic!("missing TIFF tag {sought}")
}

#[test]
fn signed_cfa_bits_order_and_crop_are_exact() {
    let mut bytes = Vec::new();
    let result = encode(&mut bytes, geometry(), &planes(), 1000.0).unwrap();
    assert_eq!(tag(&bytes, 256), (4, 1, 4));
    assert_eq!(tag(&bytes, 257), (4, 1, 4));
    assert_eq!(tag(&bytes, 258), (3, 1, 32));
    assert_eq!(tag(&bytes, 339), (3, 1, 3));
    assert_eq!(tag(&bytes, 262), (3, 1, 32803));
    assert_eq!(tag(&bytes, 33421), (3, 2, 0x0002_0002));
    assert_eq!(tag(&bytes, 33422), (1, 4, 0x0201_0100));
    let offset = tag(&bytes, 273).2 as usize;
    let decoded: Vec<u32> = bytes[offset..]
        .chunks_exact(4)
        .map(|b| u32::from_le_bytes(b.try_into().unwrap()))
        .collect();
    let expected: [f32; 16] = [
        -3.5, 11.0, -0.0, 12.0, 21.0, 31.0, 22.0, 32.0, 7.0, 13.0, 90000.0, 14.0, 23.0, 33.0, 24.0,
        34.0,
    ];
    assert_eq!(decoded, expected.map(f32::to_bits));
    assert_eq!(result.planes[0].negative_samples, 1);
    assert_eq!(result.planes[0].above_usable_white_samples, 1);
    assert_eq!(result.planes[0].minimum, -3.5);
    assert_eq!(result.planes[0].maximum, 90000.0);
    assert_eq!(
        result.payload_sha256,
        hex(&Sha256::digest(&bytes[offset..]))
    );
    assert_eq!(result.tiff_sha256, hex(&Sha256::digest(&bytes)));
    assert_eq!(result.tiff_bytes, bytes.len() as u64);
    // Crop is already compact. Applying x/y again would overrun these 4 samples.
    assert_eq!(geometry().crop_quad, [3, 5, 2, 2]);
}

#[test]
fn placebo_uses_identical_serialized_bytes_and_statistics() {
    let file = encode(&mut Vec::new(), geometry(), &planes(), 1000.0).unwrap();
    let placebo = encode(&mut std::io::sink(), geometry(), &planes(), 1000.0).unwrap();
    assert_eq!(
        serde_json::to_value(file).unwrap(),
        serde_json::to_value(placebo).unwrap()
    );
    let mut changed = planes();
    changed[2][1] += 1.0;
    let altered = encode(&mut std::io::sink(), geometry(), &changed, 1000.0).unwrap();
    let original = encode(&mut std::io::sink(), geometry(), &planes(), 1000.0).unwrap();
    assert_ne!(original.payload_sha256, altered.payload_sha256);
    assert_ne!(original.tiff_sha256, altered.tiff_sha256);
}

#[test]
fn invalid_samples_and_shapes_are_refused_without_normalization() {
    for invalid in [f32::NAN, f32::INFINITY, f32::NEG_INFINITY] {
        let mut p = planes();
        p[2][3] = invalid;
        let error = encode(&mut Vec::new(), geometry(), &p, 1000.0)
            .unwrap_err()
            .to_string();
        assert!(error.contains("G2 plane at compact index 3"), "{error}");
    }
    let mut wrong = planes();
    wrong[1].pop();
    assert!(encode(&mut Vec::new(), geometry(), &wrong, 1000.0).is_err());
    assert!(encode(&mut Vec::new(), geometry(), &planes()[..3], 1000.0).is_err());
    for white in [0.0, -1.0, f32::NAN, f32::INFINITY] {
        assert!(encode(&mut Vec::new(), geometry(), &planes(), white).is_err());
    }
    for crop in [[0, 0, 0, 2], [10, 8, 2, 2], [usize::MAX, 0, 2, 2]] {
        assert!(
            Geometry {
                crop_quad: crop,
                ..geometry()
            }
            .dimensions()
            .is_err()
        );
    }
    assert!(header(u32::MAX, 2).is_err());
}

#[test]
fn extreme_tiff_dimensions_fail_before_arithmetic_wrap_or_allocation() {
    let error = header(u32::MAX, u32::MAX).unwrap_err().to_string();
    assert!(error.contains("byte count overflow"), "{error}");
    let error = header(u32::MAX, 1).unwrap_err().to_string();
    assert!(error.contains("classic TIFF size limit"), "{error}");
    for dimensions in [(0, 1), (1, 0), (0, 0)] {
        assert!(
            header(dimensions.0, dimensions.1)
                .unwrap_err()
                .to_string()
                .contains("dimensions must be positive")
        );
    }
}

#[test]
fn tiny_crop_with_overflowing_reference_origin_is_rejected_before_writing() {
    for g in [
        Geometry {
            full_quad_width: usize::MAX,
            full_quad_height: 1,
            crop_quad: [usize::MAX - 1, 0, 1, 1],
        },
        Geometry {
            full_quad_width: 1,
            full_quad_height: usize::MAX,
            crop_quad: [0, usize::MAX - 1, 1, 1],
        },
    ] {
        assert!(g.dimensions().is_err());
        let mut written = Vec::new();
        let planes: [Vec<f32>; 4] = std::array::from_fn(|_| vec![1.0]);
        assert!(encode(&mut written, g, &planes, 1000.0).is_err());
        assert!(written.is_empty());
    }
}

#[test]
fn serializer_does_not_mutate_the_collapsed_planes() {
    let planes = planes();
    let before: Vec<_> = planes.iter().flatten().map(|v| v.to_bits()).collect();
    encode(&mut std::io::sink(), geometry(), &planes, 1000.0).unwrap();
    assert_eq!(
        before,
        planes
            .iter()
            .flatten()
            .map(|v| v.to_bits())
            .collect::<Vec<_>>()
    );
}

struct TestDir(PathBuf);
impl TestDir {
    fn new() -> Self {
        let p = std::env::temp_dir().join(format!(
            "strehl-sensor-test-{}-{}",
            std::process::id(),
            TEMP_ID.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&p).unwrap();
        Self(p)
    }
}
impl Drop for TestDir {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

#[test]
fn atomic_publication_cannot_replace_an_existing_file_and_cleans_temporaries() {
    let dir = TestDir::new();
    let destination = dir.0.join("sensor.tiff");
    let mut temp = Temporary::new(&destination).unwrap();
    let receipt = encode(temp.file.as_mut().unwrap(), geometry(), &planes(), 1000.0).unwrap();
    temp.sync_close().unwrap();
    assert!(!destination.exists());
    temp.publish(&destination).unwrap();
    assert_eq!(
        digest_file(&destination).unwrap().sha256,
        receipt.tiff_sha256
    );
    assert!(temp.publish(&destination).is_err());
    assert!(require_absent(&destination).is_err());
    drop(temp);
    assert_eq!(fs::read_dir(&dir.0).unwrap().count(), 1);
    let mut conflicting = Temporary::new(&destination).unwrap();
    conflicting
        .file
        .as_mut()
        .unwrap()
        .write_all(b"replacement")
        .unwrap();
    conflicting.sync_close().unwrap();
    assert!(conflicting.publish(&destination).is_err());
    assert_eq!(
        digest_file(&destination).unwrap().sha256,
        receipt.tiff_sha256
    );
}

#[test]
fn normalized_paths_find_dot_and_parent_aliases() {
    let dir = TestDir::new();
    fs::create_dir(dir.0.join("nested")).unwrap();
    let p = dir.0.join("output.tiff");
    assert_eq!(
        normalized(&p).unwrap(),
        normalized(&dir.0.join("nested/.././output.tiff")).unwrap()
    );
    assert_eq!(sidecar(&p), dir.0.join("output.tiff.json"));
    #[cfg(windows)]
    assert_eq!(
        normalized(&p).unwrap(),
        normalized(&dir.0.join("OUTPUT.TIFF")).unwrap()
    );
}

fn options(dir: &Path) -> MergeOptions {
    use super::super::{
        MergeConfig, PhotometricMode, Resampler, SettingSource, align_cmd, image_out,
    };
    MergeOptions {
        dir: dir.to_path_buf(),
        out: Some(dir.join("primary.tiff")),
        linear_master: None,
        region_recipe: None,
        sensor_master: Request::File(dir.join("sensor.tiff")),
        limit: None,
        srgb: false,
        space: image_out::OutputSpace::CameraLinear,
        demosaic: true,
        exposure: 0.0,
        auto_exposure: false,
        gates: vec![2.0],
        focus: None,
        flat_roi: None,
        detail_roi: None,
        index_map: None,
        n_eff_map: None,
        confidence_map: None,
        photometric: PhotometricMode::Off,
        photometric_source: SettingSource::Default,
        target_n_eff: None,
        stats: false,
        stats_placebo: false,
        confidence_tail: 0.05,
        resampler: Resampler::CatmullRom,
        backend: MergeBackend::Pyramid,
        cover: align_cmd::CoverMode::Scale,
        cover_source: SettingSource::Default,
        pyramid: MergeConfig::default(),
    }
}

fn provenance(dir: &Path) -> Provenance {
    let source = dir.join("test-input.bin");
    if !source.exists() {
        fs::write(&source, b"frozen synthetic source binding").unwrap();
    }
    Provenance {
        sources: vec![digest_file(&source).unwrap()],
        auxiliary_files: vec![],
        binary: digest_file(&source).unwrap(),
        environment: BTreeMap::new(),
        first_source: json!({"test_fixture":true,"ordered_source_index":0}),
    }
}

#[test]
fn preflight_rejects_all_output_aliases_and_unsupported_routes_before_work() {
    let dir = TestDir::new();
    let mut opts = options(&dir.0);
    preflight(&opts, &[]).unwrap();
    for field in [
        "primary",
        "master",
        "recipe",
        "confidence",
        "index",
        "neff",
        "source",
        "sidecar",
    ] {
        opts = options(&dir.0);
        let collision = dir.0.join("./sensor.tiff");
        let mut sources = vec![];
        match field {
            "primary" => opts.out = Some(collision),
            "master" => opts.linear_master = Some(collision),
            "recipe" => opts.region_recipe = Some(collision),
            "confidence" => opts.confidence_map = Some(collision),
            "index" => opts.index_map = Some(collision),
            "neff" => opts.n_eff_map = Some(collision),
            "source" => sources.push(collision),
            "sidecar" => opts.out = Some(dir.0.join("sensor.tiff.json")),
            _ => unreachable!(),
        }
        assert!(preflight(&opts, &sources).is_err(), "unprotected {field}");
    }
    opts = options(&dir.0);
    opts.backend = MergeBackend::Estimator;
    assert!(
        preflight(&opts, &[])
            .unwrap_err()
            .to_string()
            .contains("pyramid")
    );
    opts = options(&dir.0);
    opts.out = None;
    assert!(preflight(&opts, &[]).is_err());
    // Disabled bypasses even invalid destinations/backend and never reads inputs.
    opts.sensor_master = Request::Disabled;
    assert!(preflight(&opts, &[dir.0.join("does-not-exist")]).is_ok());
}

#[test]
fn complete_pair_hashes_match_placebo_and_failed_exports_preserve_primary() {
    let dir = TestDir::new();
    let mut opts = options(&dir.0);
    fs::write(opts.out.as_ref().unwrap(), b"completed primary image").unwrap();
    let primary_before = digest_file(opts.out.as_ref().unwrap()).unwrap().sha256;
    let source = provenance(&dir.0);
    finish(
        &opts,
        source,
        geometry(),
        &planes(),
        1000.0,
        json!({"fixture":true}),
    )
    .unwrap();
    let path = dir.0.join("sensor.tiff");
    let metadata: Value = serde_json::from_slice(&fs::read(sidecar(&path)).unwrap()).unwrap();
    let placebo = encode(&mut std::io::sink(), geometry(), &planes(), 1000.0).unwrap();
    assert_eq!(metadata["encoded"], serde_json::to_value(placebo).unwrap());
    assert_eq!(
        metadata["encoded"]["tiff_sha256"],
        digest_file(&path).unwrap().sha256
    );
    assert_eq!(
        metadata["mosaic_origin_in_reference_active_pixels"],
        json!([6, 10])
    );
    opts.sensor_master = Request::Placebo;
    let count = fs::read_dir(&dir.0).unwrap().count();
    finish(
        &opts,
        provenance(&dir.0),
        geometry(),
        &planes(),
        1000.0,
        Value::Null,
    )
    .unwrap();
    assert_eq!(fs::read_dir(&dir.0).unwrap().count(), count);
    opts.sensor_master = Request::File(dir.0.join("bad.tiff"));
    let mut bad = planes();
    bad[3][2] = f32::NAN;
    assert!(
        finish(
            &opts,
            provenance(&dir.0),
            geometry(),
            &bad,
            1000.0,
            Value::Null
        )
        .is_err()
    );
    assert!(!dir.0.join("bad.tiff").exists());
    assert!(!dir.0.join("bad.tiff.json").exists());
    assert_eq!(fs::read_dir(&dir.0).unwrap().count(), count);
    assert_eq!(
        digest_file(opts.out.as_ref().unwrap()).unwrap().sha256,
        primary_before
    );
}

#[test]
fn changed_or_missing_source_refuses_export_without_fallback() {
    let dir = TestDir::new();
    let opts = options(&dir.0);
    let captured = provenance(&dir.0);
    fs::write(dir.0.join("test-input.bin"), b"changed after capture").unwrap();
    assert!(
        finish(&opts, captured, geometry(), &planes(), 1000.0, Value::Null)
            .unwrap_err()
            .to_string()
            .contains("changed during stack")
    );
    let captured = provenance(&dir.0);
    fs::remove_file(dir.0.join("test-input.bin")).unwrap();
    assert!(finish(&opts, captured, geometry(), &planes(), 1000.0, Value::Null).is_err());
    assert!(!dir.0.join("sensor.tiff").exists());
}

#[test]
fn clap_exposes_two_explicit_mutually_exclusive_observer_modes() {
    use clap::Parser;
    assert!(
        crate::Cli::try_parse_from([
            "strehl",
            "stack",
            "input",
            "--out",
            "primary.tiff",
            "--sensor-master",
            "master.tiff"
        ])
        .is_ok()
    );
    assert!(
        crate::Cli::try_parse_from([
            "strehl",
            "stack",
            "input",
            "--out",
            "primary.tiff",
            "--sensor-master-placebo"
        ])
        .is_ok()
    );
    assert!(
        crate::Cli::try_parse_from([
            "strehl",
            "stack",
            "input",
            "--out",
            "primary.tiff",
            "--sensor-master",
            "master.tiff",
            "--sensor-master-placebo"
        ])
        .is_err()
    );
    assert!(
        crate::Cli::try_parse_from(["strehl", "stack", "input", "--sensor-master-placebo"])
            .is_err()
    );
}
