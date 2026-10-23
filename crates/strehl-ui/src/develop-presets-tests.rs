use super::*;
use strehl_edit::{HdrSettings, RegionAdjustment, RegionShape, SourceRange};

fn settings(exposure: f32) -> PresetSettings {
    PresetSettings {
        adjustments: Adjustments {
            exposure,
            ..Default::default()
        },
        adaptive: None,
    }
}

fn region(id: &str) -> RegionAdjustment {
    RegionAdjustment {
        id: id.into(),
        name: "Reflection".into(),
        note: "Keep original source evidence".into(),
        shape: RegionShape::Ellipse {
            center: [0.23, 0.64],
            radius: [0.12, 0.19],
        },
        feather: 0.35,
        enabled: true,
        adjustments: Adjustments {
            exposure: -1.2,
            ..Default::default()
        },
        source_range: Some(SourceRange { first: 7, last: 13 }),
    }
}

fn directory() -> PathBuf {
    let path = std::env::temp_dir().join(format!("strehl-preset-test-{}", random_id().unwrap()));
    std::fs::create_dir(&path).unwrap();
    path
}

#[test]
fn capture_is_portable_and_application_preserves_destination_evidence() {
    let mut source = DevelopmentRecipe::default();
    source.global.exposure = 1.8;
    source.regions.push(region("original"));
    let preset = PresetSettings::capture(&source, Some("original")).unwrap();
    let json = serde_json::to_string(&preset).unwrap();
    for forbidden in [
        "original",
        "source_range",
        "shape",
        "feather",
        "hdr",
        "Reflection",
    ] {
        assert!(
            !json.contains(forbidden),
            "preset must not copy {forbidden}"
        );
    }
    let mut destination = DevelopmentRecipe::default();
    destination.global.exposure = 0.45;
    destination.hdr = HdrSettings {
        peak_nits: 1600.0,
        quality: 98,
        ..Default::default()
    };
    destination.regions = vec![region("target"), region("other")];
    destination.regions[0].adjustments.exposure = 0.2;
    let applied = preset.apply_controls(&destination, Some("target")).unwrap();
    let mut expected = destination.clone();
    expected.regions[0].adjustments = preset.adjustments;
    assert_eq!(applied, expected);
    assert_ne!(
        applied.regions[0].adjustments, destination.regions[0].adjustments,
        "fixture must exercise a real scoped change"
    );
    let global = preset.apply_controls(&destination, None).unwrap();
    assert_eq!(global.regions, destination.regions);
    assert_eq!(global.hdr, destination.hdr);
    assert!(
        preset
            .apply_controls(&destination, Some("missing"))
            .is_err()
    );
    destination.regions[0].enabled = false;
    assert!(preset.apply_controls(&destination, Some("target")).is_err());
}

#[test]
fn names_are_utf8_bounded_unique_and_never_interpreted_as_paths() {
    let mut library = Library::default();
    let id = library
        .add("  昆虫 / Warm look ✨  ", settings(0.3))
        .unwrap();
    assert_eq!(library.presets[0].name, "昆虫 / Warm look ✨");
    assert_eq!(library.presets[0].id, id);
    let before = library.clone();
    for name in ["", " \t", "bad\nname", &"🦋".repeat(49), &"a".repeat(97)] {
        assert!(library.add(name, settings(0.0)).is_err());
        assert_eq!(library, before);
    }
    let second = library.add("SECOND", settings(0.4)).unwrap();
    assert!(library.add("second", settings(0.0)).is_err());
    assert!(library.rename(&id, "second").is_err());
    library.rename(&second, "New name").unwrap();
    let (index, deleted) = library.remove(&id).unwrap();
    library.restore(index, deleted).unwrap();
    assert_eq!(library.presets[0].id, id);
    library.validate().unwrap();
}

#[test]
fn malformed_or_image_specific_payloads_cannot_enter_library() {
    let mut library = Library::default();
    library.add("Test", settings(0.5)).unwrap();
    let valid = serde_json::to_value(&library).unwrap();
    for field in ["source_range", "shape", "path", "spatial"] {
        let mut bad = valid.clone();
        bad["presets"][0]["settings"][field] = serde_json::json!({"copied":true});
        assert!(serde_json::from_value::<Library>(bad).is_err());
    }
    let mut bad = library.clone();
    bad.presets[0].settings.adjustments.exposure = f32::NAN;
    assert!(bad.validate().is_err());
    bad = library.clone();
    bad.version = 999;
    assert!(bad.validate().is_err());
    bad = library.clone();
    bad.presets.push(bad.presets[0].clone());
    assert!(bad.validate().is_err());
    bad = library.clone();
    bad.presets[0].settings.adaptive = Some(AdaptivePreset {
        intent: AdaptiveIntent::Balance,
        amount: 1.01,
        parameters: Default::default(),
    });
    assert!(bad.validate().is_err());
}

#[test]
fn persistence_is_atomic_and_detects_external_changes_without_overwriting_them() {
    let dir = directory();
    let path = dir.join("looks.json");
    let loaded = load(&path).unwrap();
    assert!(loaded.bytes.is_none() && loaded.library.presets.is_empty());
    let mut library = loaded.library;
    let id = library.add("First", settings(0.8)).unwrap();
    let bytes = save(&path, &library, None).unwrap();
    assert_eq!(load(&path).unwrap().library, library);
    library.rename(&id, "Renamed").unwrap();
    let newer = save(&path, &library, Some(&bytes)).unwrap();
    assert_eq!(std::fs::read(&path).unwrap(), newer);
    assert!(save(&path, &Library::default(), Some(&bytes)).is_err());
    assert_eq!(
        std::fs::read(&path).unwrap(),
        newer,
        "stale window must not clobber newer saved presets"
    );
    assert_eq!(
        std::fs::read_dir(&dir).unwrap().count(),
        2,
        "only the library and stable OS-lock file should remain"
    );
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn concurrent_writers_cannot_both_publish_from_the_same_saved_revision() {
    use std::sync::{Arc, Barrier};
    let dir = directory();
    let path = dir.join("looks.json");
    let empty = save(&path, &Library::default(), None).unwrap();
    let held = std::fs::OpenOptions::new()
        .read(true)
        .write(true)
        .open(path.with_extension("lock"))
        .unwrap();
    held.try_lock().unwrap();
    let mut blocked = Library::default();
    blocked.add("Must not publish", settings(1.0)).unwrap();
    assert!(
        save(&path, &blocked, Some(&empty)).is_err(),
        "negative control: ignoring the held lock would incorrectly publish"
    );
    assert_eq!(std::fs::read(&path).unwrap(), empty);
    drop(held);
    let barrier = Arc::new(Barrier::new(2));
    let handles = (0..2)
        .map(|i| {
            let path = path.clone();
            let expected = empty.clone();
            let barrier = barrier.clone();
            std::thread::spawn(move || {
                let mut library = Library::default();
                library
                    .add(&format!("Window {i}"), settings(i as f32))
                    .unwrap();
                barrier.wait();
                save(&path, &library, Some(&expected)).map(|_| library)
            })
        })
        .collect::<Vec<_>>();
    let results = handles
        .into_iter()
        .map(|h| h.join().unwrap())
        .collect::<Vec<_>>();
    assert_eq!(results.iter().filter(|r| r.is_ok()).count(), 1);
    let winner = results.into_iter().find_map(Result::ok).unwrap();
    assert_eq!(load(&path).unwrap().library, winner);
    // An abandoned lock file is harmless; releasing the handle releases the
    // actual lock and the next save can succeed without deleting any sentinel.
    let current = std::fs::read(&path).unwrap();
    save(&path, &winner, Some(&current)).unwrap();
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn corrupt_oversized_and_future_libraries_stay_unchanged() {
    let dir = directory();
    let path = dir.join("looks.json");
    for bytes in [
        b"{broken".to_vec(),
        vec![b' '; MAX_BYTES + 1],
        br#"{"version":999,"presets":[]}"#.to_vec(),
    ] {
        std::fs::write(&path, &bytes).unwrap();
        assert!(load(&path).is_err());
        assert!(save(&path, &Library::default(), None).is_err());
        assert_eq!(std::fs::read(&path).unwrap(), bytes);
    }
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn rejected_restore_and_full_library_do_not_change_saved_looks() {
    let mut library = Library::default();
    for i in 0..MAX_PRESETS {
        library.add(&format!("Look {i}"), settings(0.0)).unwrap();
    }
    let before = library.clone();
    assert!(library.add("Overflow", settings(0.0)).is_err());
    assert_eq!(library, before);
    let (index, preset) = library.remove(&before.presets[0].id).unwrap();
    library.add(&preset.name, settings(1.0)).unwrap();
    let current = library.clone();
    assert!(library.restore(index, preset).is_err());
    assert_eq!(library, current);
}
