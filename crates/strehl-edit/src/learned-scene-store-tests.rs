use super::*;
use crate::learned_scene_asset::tests::{fixture, legacy_wire_fixture};

fn scene() -> (FrozenSceneAsset, ExpectedAsset) {
    let (d, data) = fixture();
    let expected = ExpectedAsset {
        identities: d.identities.clone(),
        full_size: d.origin.full_size,
    };
    (FrozenSceneAsset::freeze(d, data).unwrap(), expected)
}
fn entries(path: &Path) -> Vec<PathBuf> {
    fs::read_dir(path)
        .unwrap()
        .map(|e| e.unwrap().path())
        .collect()
}

#[test]
fn scene_and_legacy_storage_coexist_idempotently_without_cross_codec_fallback() {
    let temporary = tempfile::tempdir().unwrap();
    let store = LearnedAssetStore::open(temporary.path()).unwrap();
    let (asset, expected) = scene();
    let cancel = AtomicBool::new(false);
    let key = store.save_scene(&asset, &expected, &cancel).unwrap();
    let path = store.path(key);
    let modified = fs::metadata(&path).unwrap().modified().unwrap();
    assert_eq!(fs::read(&path).unwrap(), asset.encode().unwrap());
    assert_eq!(store.save_scene(&asset, &expected, &cancel).unwrap(), key);
    assert_eq!(fs::metadata(&path).unwrap().modified().unwrap(), modified);
    let loaded = store.load_scene(key, &expected, &cancel).unwrap();
    assert_eq!(loaded.encode().unwrap(), asset.encode().unwrap());
    assert_eq!(
        loaded
            .prepared()
            .develop_pixel([0.1, 0.4, 1.2], [0.3, 0.6])
            .unwrap()
            .map(f32::to_bits),
        asset
            .prepared()
            .develop_pixel([0.1, 0.4, 1.2], [0.3, 0.6])
            .unwrap()
            .map(f32::to_bits)
    );
    assert!(store.load(key, &expected, &cancel).is_err());
    let legacy = legacy_wire_fixture();
    let old = FrozenLearnedAsset::decode(&legacy).unwrap();
    let old_expected = ExpectedAsset {
        identities: old.descriptor().identities.clone(),
        full_size: old.descriptor().origin.full_size,
    };
    let old_key = store.save(&old, &old_expected, &cancel).unwrap();
    assert_eq!(fs::read(store.path(old_key)).unwrap(), legacy);
    assert_eq!(
        store
            .load(old_key, &old_expected, &cancel)
            .unwrap()
            .encode()
            .unwrap(),
        legacy
    );
    assert!(store.load_scene(old_key, &old_expected, &cancel).is_err());
    assert_eq!(entries(temporary.path()).len(), 2);
}

#[test]
fn scene_requires_every_external_identity_for_both_read_and_write() {
    let temporary = tempfile::tempdir().unwrap();
    let store = LearnedAssetStore::open(temporary.path()).unwrap();
    let (asset, expected) = scene();
    let cancel = AtomicBool::new(false);
    let key = store.save_scene(&asset, &expected, &cancel).unwrap();
    let before = fs::read(store.path(key)).unwrap();
    for change in [
        (|e: &mut ExpectedAsset| e.full_size[1] += 1) as fn(&mut ExpectedAsset),
        |e| e.identities.source_sha256[0] ^= 1,
        |e| e.identities.contract_id.push_str("-wrong"),
        |e| e.identities.contract_sha256[0] ^= 1,
        |e| e.identities.model_sha256[0] ^= 1,
        |e| e.identities.input_sha256[0] ^= 1,
    ] {
        let mut wrong = expected.clone();
        change(&mut wrong);
        assert!(store.load_scene(key, &wrong, &cancel).is_err());
        assert!(store.save_scene(&asset, &wrong, &cancel).is_err());
        assert_eq!(fs::read(store.path(key)).unwrap(), before);
    }
}

#[test]
fn scene_missing_corrupt_wrong_key_oversized_and_directory_objects_never_fall_back() {
    let temporary = tempfile::tempdir().unwrap();
    let store = LearnedAssetStore::open(temporary.path()).unwrap();
    let (asset, expected) = scene();
    let cancel = AtomicBool::new(false);
    let key = AssetKey::from_digest(asset.digest());
    let path = store.path(key);
    assert!(store.load_scene(key, &expected, &cancel).is_err());
    let mut digest = asset.digest();
    digest[0] ^= 1;
    let wrong = AssetKey::from_digest(digest);
    fs::write(store.path(wrong), asset.encode().unwrap()).unwrap();
    assert!(store.load_scene(wrong, &expected, &cancel).is_err());
    fs::write(&path, b"existing unrelated content").unwrap();
    assert!(store.save_scene(&asset, &expected, &cancel).is_err());
    assert_eq!(fs::read(&path).unwrap(), b"existing unrelated content");
    let bytes = asset.encode().unwrap();
    fs::write(&path, &bytes[..bytes.len() - 1]).unwrap();
    assert!(store.load_scene(key, &expected, &cancel).is_err());
    File::create(&path)
        .unwrap()
        .set_len(MAX_ASSET_BYTES as u64 + 1)
        .unwrap();
    assert!(
        format!(
            "{:#}",
            store.load_scene(key, &expected, &cancel).err().unwrap()
        )
        .contains("size limit")
    );
    fs::remove_file(&path).unwrap();
    fs::create_dir(&path).unwrap();
    assert!(store.load_scene(key, &expected, &cancel).is_err());
    assert!(store.save_scene(&asset, &expected, &cancel).is_err());
    assert!(path.is_dir());
}

#[test]
fn scene_cancellation_before_and_after_complete_write_never_publishes() {
    let temporary = tempfile::tempdir().unwrap();
    let store = LearnedAssetStore::open(temporary.path()).unwrap();
    let (asset, expected) = scene();
    let cancel = AtomicBool::new(true);
    assert!(store.save_scene(&asset, &expected, &cancel).is_err());
    assert!(entries(temporary.path()).is_empty());
    cancel.store(false, Ordering::Relaxed);
    let mut exercised = false;
    assert!(
        store
            .save_scene_before_publish(&asset, &expected, &cancel, || {
                let files = entries(temporary.path());
                assert_eq!(files.len(), 1);
                assert_eq!(fs::read(&files[0]).unwrap(), asset.encode().unwrap());
                exercised = true;
                cancel.store(true, Ordering::Relaxed);
                Ok(())
            })
            .is_err()
    );
    assert!(exercised);
    assert!(entries(temporary.path()).is_empty());
    cancel.store(false, Ordering::Relaxed);
    let key = store.save_scene(&asset, &expected, &cancel).unwrap();
    cancel.store(true, Ordering::Relaxed);
    assert!(store.load_scene(key, &expected, &cancel).is_err());
    assert_eq!(fs::read(store.path(key)).unwrap(), asset.encode().unwrap());
}

#[test]
fn scene_concurrent_and_competing_publication_only_reuses_exact_valid_content() {
    for valid in [false, true] {
        let temporary = tempfile::tempdir().unwrap();
        let store = LearnedAssetStore::open(temporary.path()).unwrap();
        let (asset, expected) = scene();
        let cancel = AtomicBool::new(false);
        let key = AssetKey::from_digest(asset.digest());
        let path = store.path(key);
        let competing = if valid {
            asset.encode().unwrap()
        } else {
            b"other bytes".to_vec()
        };
        let result = store.save_scene_before_publish(&asset, &expected, &cancel, || {
            fs::write(&path, &competing)?;
            Ok(())
        });
        assert_eq!(result.is_ok(), valid);
        assert_eq!(fs::read(&path).unwrap(), competing);
        assert_eq!(entries(temporary.path()).len(), 1);
    }
    let temporary = tempfile::tempdir().unwrap();
    let store = LearnedAssetStore::open(temporary.path()).unwrap();
    let (asset, expected) = scene();
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
                store.save_scene(asset, expected, &AtomicBool::new(false))
            }));
        }
        for worker in workers {
            assert_eq!(worker.join().unwrap().unwrap().digest(), asset.digest());
        }
    });
    assert_eq!(entries(temporary.path()).len(), 1);
}

#[test]
fn scene_replaced_store_and_orphan_temporaries_are_not_adopted() {
    let temporary = tempfile::tempdir().unwrap();
    let directory = temporary.path().join("store");
    fs::create_dir(&directory).unwrap();
    let store = LearnedAssetStore::open(&directory).unwrap();
    let (asset, expected) = scene();
    let cancel = AtomicBool::new(false);
    let key = AssetKey::from_digest(asset.digest());
    let orphan = directory.join(".strehl-export-interrupted.tmp");
    fs::write(&orphan, b"orphan").unwrap();
    assert!(store.load_scene(key, &expected, &cancel).is_err());
    store.save_scene(&asset, &expected, &cancel).unwrap();
    assert_eq!(fs::read(&orphan).unwrap(), b"orphan");
    fs::rename(&directory, temporary.path().join("original")).unwrap();
    fs::create_dir(&directory).unwrap();
    assert!(store.load_scene(key, &expected, &cancel).is_err());
    assert!(store.save_scene(&asset, &expected, &cancel).is_err());
    assert!(entries(&directory).is_empty());
    assert_eq!(
        fs::read(
            temporary
                .path()
                .join("original")
                .join(".strehl-export-interrupted.tmp")
        )
        .unwrap(),
        b"orphan"
    );
}

#[cfg(unix)]
#[test]
fn scene_symlink_entry_is_refused_without_overwriting_target() {
    let temporary = tempfile::tempdir().unwrap();
    let directory = temporary.path().join("store");
    fs::create_dir(&directory).unwrap();
    let store = LearnedAssetStore::open(&directory).unwrap();
    let (asset, expected) = scene();
    let cancel = AtomicBool::new(false);
    let key = AssetKey::from_digest(asset.digest());
    let target = temporary.path().join("outside");
    fs::write(&target, asset.encode().unwrap()).unwrap();
    std::os::unix::fs::symlink(&target, store.path(key)).unwrap();
    assert!(store.load_scene(key, &expected, &cancel).is_err());
    assert!(store.save_scene(&asset, &expected, &cancel).is_err());
    assert_eq!(fs::read(target).unwrap(), asset.encode().unwrap());
}
