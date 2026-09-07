use super::*;

const ADMISSION_ENV: &str = "STREHL_M194D_ADMISSION";

fn parse_admission(value: &str) -> Result<AdmissionMode> {
    match value {
        "hard-floor" => Ok(AdmissionMode::HardFloor),
        "floor-pedestal-v1" => Ok(AdmissionMode::FloorPedestalV1),
        _ => bail!("{ADMISSION_ENV}: unsupported admission mode {value:?}"),
    }
}

#[test]
#[ignore = "explicit generated fixture manifest and external hash bindings required"]
fn m194d_known_scene_consumer() -> Result<()> {
    let value = std::env::var(ADMISSION_ENV).context("missing STREHL_M194D_ADMISSION")?;
    let mode = parse_admission(&value)?;
    ensure!(
        std::env::var(format!("{PREFIX}DIAGNOSTIC")).is_err(),
        "M194d requires the registered measured floor without diagnostics"
    );
    run_known_scene_consumer(Some(mode))
}

#[test]
fn m194d_defaults_and_explicit_option() {
    assert_eq!(MergeConfig::default().admission, AdmissionMode::HardFloor);
    assert_eq!(
        options(PathBuf::new()).pyramid.admission,
        AdmissionMode::HardFloor
    );
    assert_eq!(
        parse_admission("hard-floor").unwrap(),
        AdmissionMode::HardFloor
    );
    assert_eq!(
        parse_admission("floor-pedestal-v1").unwrap(),
        AdmissionMode::FloorPedestalV1
    );
    for bad in ["", "HardFloor", "floor-pedestal", " floor-pedestal-v1", "1"] {
        assert!(parse_admission(bad).is_err(), "accepted {bad:?}");
    }
    let opts = options_with_admission(PathBuf::new(), Some(AdmissionMode::FloorPedestalV1));
    assert_eq!(opts.pyramid.admission, AdmissionMode::FloorPedestalV1);
    assert_eq!(opts.pyramid.gate, 2.0);
    assert_eq!(opts.pyramid.bands, 3);
}

mod m194d_independent_consumer_tests {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/m194d-band-admission/independent-consumer-tests.rs"
    ));
}
