use super::*;
use crate::{
    learned_asset::{
        FrozenProfileData, FrozenProfileDescriptor, GainDescriptor, ProfileOrigin, ToneDescriptor,
    },
    learned_profile::IDENTITY_MATRIX,
};

fn fixture() -> (FrozenLearnedAsset, ExpectedAsset) {
    let identities = AssetIdentities {
        contract_id: "strehl/store-fixture-v1".into(),
        contract_sha256: [1; 32],
        model_sha256: [2; 32],
        input_sha256: [3; 32],
        source_sha256: [4; 32],
    };
    let asset = FrozenLearnedAsset::freeze(
        FrozenProfileDescriptor {
            identities: identities.clone(),
            origin: ProfileOrigin {
                full_size: [32, 24],
                region: None,
            },
            gain: GainDescriptor {
                dimensions: [1, 1, 1],
                origin_yx: [0.; 2],
                spacing_yx: [1.; 2],
                input_weights: [1., 0., 0., 0., 0.],
                gamma: 1.,
            },
            tables: [None, None, None],
            linear_709_to_rimm: IDENTITY_MATRIX,
            pre_gain_scale: 1.,
            tone_curve: ToneDescriptor::Identity,
            masks: [None, None],
        },
        FrozenProfileData {
            gain: vec![1.25],
            tables: [None, None, None],
            masks: [None, None],
        },
    )
    .unwrap();
    (
        asset,
        ExpectedAsset {
            identities,
            full_size: [32, 24],
        },
    )
}

fn entries(path: &Path) -> Vec<PathBuf> {
    fs::read_dir(path)
        .unwrap()
        .map(|e| e.unwrap().path())
        .collect()
}

#[test]
fn keys_cannot_supply_paths_or_ambiguous_encodings() {
    let key = AssetKey::from_digest([0xab; 32]);
    let encoded = "ab".repeat(32);
    assert_eq!(key.to_string(), encoded);
    assert_eq!(encoded.parse::<AssetKey>().unwrap(), key);
    for value in [
        "",
        "..",
        "../asset",
        "C:\\asset",
        "/asset",
        &"AB".repeat(32),
        &"a".repeat(63),
        &"a".repeat(65),
        &format!("{}\n", "a".repeat(63)),
        &"gg".repeat(32),
    ] {
        assert!(value.parse::<AssetKey>().is_err(), "accepted key {value:?}");
    }
}

#[test]
fn opening_requires_an_existing_absolute_directory() {
    assert!(LearnedAssetStore::open(Path::new("relative-store")).is_err());
    let temporary = tempfile::tempdir().unwrap();
    let missing = temporary.path().join("missing");
    assert!(LearnedAssetStore::open(&missing).is_err());
    assert!(!missing.exists(), "opening must not create a directory");
    let file = temporary.path().join("file");
    fs::write(&file, b"data").unwrap();
    assert!(LearnedAssetStore::open(&file).is_err());
}

#[test]
fn immutable_save_load_and_repeat_use_one_exact_object() {
    let temporary = tempfile::tempdir().unwrap();
    let store = LearnedAssetStore::open(temporary.path()).unwrap();
    let (asset, expected) = fixture();
    let cancel = AtomicBool::new(false);
    let key = store.save(&asset, &expected, &cancel).unwrap();
    let first = fs::read(store.path(key)).unwrap();
    let modified = fs::metadata(store.path(key)).unwrap().modified().unwrap();
    assert_eq!(first, asset.encode().unwrap());
    assert_eq!(store.save(&asset, &expected, &cancel).unwrap(), key);
    assert_eq!(
        modified,
        fs::metadata(store.path(key)).unwrap().modified().unwrap()
    );
    assert_eq!(entries(temporary.path()).len(), 1);
    let reopened = store.load(key, &expected, &cancel).unwrap();
    assert_eq!(reopened.digest(), asset.digest());
    let apply = |profile: &FrozenLearnedAsset| {
        profile
            .prepared()
            .apply_pixel([0.2, 0.4, 1.2], [0.5; 2], [0.; 2], 1.)
            .unwrap()
    };
    assert_eq!(apply(&asset), apply(&reopened));
}

#[test]
fn every_external_identity_is_required_for_read_and_write() {
    let temporary = tempfile::tempdir().unwrap();
    let store = LearnedAssetStore::open(temporary.path()).unwrap();
    let (asset, expected) = fixture();
    let cancel = AtomicBool::new(false);
    let key = store.save(&asset, &expected, &cancel).unwrap();
    let before = fs::read(store.path(key)).unwrap();
    for change in [
        (|e: &mut ExpectedAsset| e.full_size[0] += 1) as fn(&mut ExpectedAsset),
        |e| e.identities.source_sha256[0] ^= 1,
        |e| e.identities.contract_id.push_str("-unknown"),
        |e| e.identities.contract_sha256[0] ^= 1,
        |e| e.identities.model_sha256[0] ^= 1,
        |e| e.identities.input_sha256[0] ^= 1,
    ] {
        let mut wrong = expected.clone();
        change(&mut wrong);
        assert!(store.load(key, &wrong, &cancel).is_err());
        assert!(store.save(&asset, &wrong, &cancel).is_err());
        assert_eq!(fs::read(store.path(key)).unwrap(), before);
    }
}

#[test]
fn missing_wrong_key_and_corrupt_existing_assets_never_fall_back_or_overwrite() {
    let temporary = tempfile::tempdir().unwrap();
    let store = LearnedAssetStore::open(temporary.path()).unwrap();
    let (asset, expected) = fixture();
    let cancel = AtomicBool::new(false);
    let key = AssetKey::from_digest(asset.digest());
    assert!(store.load(key, &expected, &cancel).is_err());
    let mut other_digest = asset.digest();
    other_digest[0] ^= 1;
    let other_key = AssetKey::from_digest(other_digest);
    fs::write(store.path(other_key), asset.encode().unwrap()).unwrap();
    assert!(
        format!(
            "{:#}",
            store.load(other_key, &expected, &cancel).err().unwrap()
        )
        .contains("key")
    );
    fs::write(store.path(key), b"another application's bytes").unwrap();
    assert!(store.save(&asset, &expected, &cancel).is_err());
    assert_eq!(
        fs::read(store.path(key)).unwrap(),
        b"another application's bytes"
    );
}

#[test]
fn oversized_truncated_and_directory_entries_are_rejected() {
    let temporary = tempfile::tempdir().unwrap();
    let store = LearnedAssetStore::open(temporary.path()).unwrap();
    let (asset, expected) = fixture();
    let cancel = AtomicBool::new(false);
    let key = AssetKey::from_digest(asset.digest());
    let path = store.path(key);
    let encoded = asset.encode().unwrap();
    fs::write(&path, &encoded[..encoded.len() - 1]).unwrap();
    assert!(store.load(key, &expected, &cancel).is_err());
    File::create(&path)
        .unwrap()
        .set_len(MAX_ASSET_BYTES as u64 + 1)
        .unwrap();
    assert!(
        format!("{:#}", store.load(key, &expected, &cancel).err().unwrap()).contains("size limit")
    );
    fs::remove_file(&path).unwrap();
    fs::create_dir(&path).unwrap();
    assert!(store.load(key, &expected, &cancel).is_err());
    assert!(store.save(&asset, &expected, &cancel).is_err());
    assert!(path.is_dir());
}

#[test]
fn cancellation_before_and_after_writing_never_publishes_partial_content() {
    let temporary = tempfile::tempdir().unwrap();
    let store = LearnedAssetStore::open(temporary.path()).unwrap();
    let (asset, expected) = fixture();
    let cancel = AtomicBool::new(true);
    assert!(store.save(&asset, &expected, &cancel).is_err());
    assert!(entries(temporary.path()).is_empty());
    cancel.store(false, Ordering::Relaxed);
    let mut reached_complete_temporary = false;
    let result = store.save_before_publish(&asset, &expected, &cancel, || {
        reached_complete_temporary = true;
        let files = entries(temporary.path());
        assert_eq!(files.len(), 1);
        assert_eq!(fs::read(&files[0]).unwrap(), asset.encode().unwrap());
        cancel.store(true, Ordering::Relaxed);
        Ok(())
    });
    assert!(
        reached_complete_temporary,
        "cancellation control must occur after bytes exist"
    );
    assert!(result.is_err());
    assert!(entries(temporary.path()).is_empty());
}

#[test]
fn competing_publishers_only_reuse_valid_identical_content() {
    for valid in [false, true] {
        let temporary = tempfile::tempdir().unwrap();
        let store = LearnedAssetStore::open(temporary.path()).unwrap();
        let (asset, expected) = fixture();
        let cancel = AtomicBool::new(false);
        let key = AssetKey::from_digest(asset.digest());
        let path = store.path(key);
        let competing = if valid {
            asset.encode().unwrap()
        } else {
            b"competing unrelated content".to_vec()
        };
        let result = store.save_before_publish(&asset, &expected, &cancel, || {
            fs::write(&path, &competing)?;
            Ok(())
        });
        assert_eq!(result.is_ok(), valid);
        assert_eq!(fs::read(&path).unwrap(), competing);
        assert_eq!(
            entries(temporary.path()).len(),
            1,
            "owned temporary must be cleaned"
        );
    }
}

#[test]
fn concurrent_saves_publish_one_complete_object() {
    let temporary = tempfile::tempdir().unwrap();
    let store = LearnedAssetStore::open(temporary.path()).unwrap();
    let (asset, expected) = fixture();
    let barrier = std::sync::Barrier::new(4);
    std::thread::scope(|scope| {
        let mut workers = Vec::new();
        for _ in 0..4 {
            let store = &store;
            let asset = &asset;
            let expected = &expected;
            let barrier = &barrier;
            workers.push(scope.spawn(move || {
                barrier.wait();
                store.save(asset, expected, &AtomicBool::new(false))
            }));
        }
        for worker in workers {
            assert_eq!(worker.join().unwrap().unwrap().digest(), asset.digest());
        }
    });
    assert_eq!(entries(temporary.path()).len(), 1);
}

#[test]
fn interrupted_process_temporaries_are_ignored_and_not_deleted() {
    let temporary = tempfile::tempdir().unwrap();
    let orphan = temporary.path().join(".strehl-export-interrupted.tmp");
    fs::write(&orphan, b"partial unrelated bytes").unwrap();
    let store = LearnedAssetStore::open(temporary.path()).unwrap();
    let (asset, expected) = fixture();
    let cancel = AtomicBool::new(false);
    assert!(
        store
            .load(AssetKey::from_digest(asset.digest()), &expected, &cancel)
            .is_err()
    );
    store.save(&asset, &expected, &cancel).unwrap();
    assert_eq!(fs::read(&orphan).unwrap(), b"partial unrelated bytes");
    assert_eq!(entries(temporary.path()).len(), 2);
}

#[test]
fn replacing_the_directory_cannot_redirect_an_open_store() {
    let temporary = tempfile::tempdir().unwrap();
    let directory = temporary.path().join("store");
    fs::create_dir(&directory).unwrap();
    let store = LearnedAssetStore::open(&directory).unwrap();
    fs::rename(&directory, temporary.path().join("original")).unwrap();
    fs::create_dir(&directory).unwrap();
    let (asset, expected) = fixture();
    let cancel = AtomicBool::new(false);
    assert!(store.save(&asset, &expected, &cancel).is_err());
    assert!(
        store
            .load(AssetKey::from_digest(asset.digest()), &expected, &cancel)
            .is_err()
    );
    assert!(entries(&directory).is_empty());
    assert!(entries(&temporary.path().join("original")).is_empty());
}

#[cfg(unix)]
#[test]
fn symlink_directories_and_asset_entries_are_rejected() {
    use std::os::unix::fs::symlink;
    let temporary = tempfile::tempdir().unwrap();
    let directory = temporary.path().join("store");
    fs::create_dir(&directory).unwrap();
    let alias = temporary.path().join("alias");
    symlink(&directory, &alias).unwrap();
    assert!(LearnedAssetStore::open(&alias).is_err());
    let store = LearnedAssetStore::open(&directory).unwrap();
    let (asset, expected) = fixture();
    let cancel = AtomicBool::new(false);
    let outside = temporary.path().join("outside");
    fs::write(&outside, asset.encode().unwrap()).unwrap();
    let key = AssetKey::from_digest(asset.digest());
    symlink(&outside, store.path(key)).unwrap();
    assert!(store.load(key, &expected, &cancel).is_err());
    assert!(store.save(&asset, &expected, &cancel).is_err());
    assert_eq!(fs::read(outside).unwrap(), asset.encode().unwrap());
}
