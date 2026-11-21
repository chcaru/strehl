use super::*;
use crate::jobs::tests::TestDirectory;

fn source(directory: &Path, name: &str, bytes: &[u8], age: Duration) -> PathBuf {
    let path = directory.join(name);
    fs::write(&path, bytes).unwrap();
    let file = OpenOptions::new().write(true).open(&path).unwrap();
    file.set_modified(SystemTime::now() - age).unwrap();
    path
}

fn picture(path: &Path, side: usize) -> PreviewImage {
    PreviewImage {
        path: path.to_path_buf(),
        source_size: [7008, 4672],
        size: [side, side * 2 / 3],
        rgba: (0..side * (side * 2 / 3) * 4)
            .map(|index| (index % 251) as u8)
            .collect(),
        is_overview: true,
    }
}

#[test]
fn derivatives_round_trip_and_any_identity_change_misses() {
    let directory = TestDirectory::new("source-preview-disk-round-trip");
    let cache = directory.path().join("cache");
    let raw = source(
        directory.path(),
        "a.arw",
        b"raw bytes",
        Duration::from_secs(60),
    );
    // The round trip goes through the real folder lookup.
    set_root(Some(cache.clone()));
    let image = picture(&raw, 304);
    store(&raw, 304, "p3-test", &image);
    let loaded = load(&raw, 304, "p3-test").expect("stored derivative");
    assert_eq!(loaded.rgba, image.rgba);
    assert_eq!(loaded.size, image.size);
    assert_eq!(loaded.source_size, image.source_size);
    assert_eq!(loaded.path, raw);
    assert!(
        load(&raw, 160, "p3-test").is_none(),
        "another tier never shares it"
    );
    assert!(
        load(&raw, 304, "p3-other").is_none(),
        "another policy never shares it"
    );
    // A replaced source (new length and time) misses.
    let replaced = source(
        directory.path(),
        "a.arw",
        b"other raw bytes",
        Duration::from_secs(30),
    );
    assert!(load(&replaced, 304, "p3-test").is_none());
    // A source inside the write window is neither stored nor read.
    let fresh = source(directory.path(), "b.arw", b"new", Duration::ZERO);
    store(&fresh, 304, "p3-test", &picture(&fresh, 304));
    assert!(load(&fresh, 304, "p3-test").is_none());
    // Corrupt entries are ignored, never returned.
    let identity = identity(&replaced, 304, "p3-test").unwrap();
    fs::write(
        cache.join(format!("{identity}.scrub")),
        b"\x10\x00\x00\x00{}",
    )
    .unwrap();
    assert!(load(&replaced, 304, "p3-test").is_none());
    set_root(None);
    assert!(
        load(&raw, 304, "p3-test").is_none(),
        "disabled reads nothing"
    );
}

#[test]
fn pruning_keeps_the_entry_bound_and_drops_the_oldest() {
    let directory = TestDirectory::new("source-preview-disk-prune");
    let root = directory.path();
    for index in 0..DISK_ENTRIES + 6 {
        let path = root.join(format!("{index:05}.scrub"));
        fs::write(&path, [0u8; 16]).unwrap();
        let file = OpenOptions::new().write(true).open(&path).unwrap();
        file.set_modified(UNIX_EPOCH + Duration::from_secs(1_000_000 + index as u64))
            .unwrap();
    }
    fs::write(root.join("keep.txt"), b"unrelated").unwrap();
    prune(root);
    let left: Vec<String> = fs::read_dir(root)
        .unwrap()
        .flatten()
        .map(|entry| entry.file_name().to_string_lossy().into_owned())
        .collect();
    assert_eq!(
        left.iter().filter(|name| name.ends_with(".scrub")).count(),
        DISK_ENTRIES
    );
    for oldest in 0..6 {
        assert!(!left.contains(&format!("{oldest:05}.scrub")));
    }
    assert!(
        left.contains(&"keep.txt".to_owned()),
        "only derivatives are pruned"
    );
}
