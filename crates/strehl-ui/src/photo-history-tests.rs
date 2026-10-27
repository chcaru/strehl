use super::*;
use std::sync::{Arc, Barrier};

struct Fixture {
    root: PathBuf,
    owner: PhotoOwner,
    image: Arc<LinearImage>,
}
impl Fixture {
    fn new() -> Self {
        let root = std::env::temp_dir().join(format!("strehl-photo-history-{}", new_id().unwrap()));
        fs::create_dir_all(&root).unwrap();
        let output = root.join("result.tiff");
        fs::write(&output, b"original TIFF evidence").unwrap();
        Self {
            root,
            owner: PhotoOwner {
                stack: None,
                run: None,
                output,
            },
            image: Arc::new(LinearImage {
                width: 3,
                height: 2,
                pixels: vec![0.25; 18],
                origin: strehl_edit::ImageOrigin::SceneLinear,
                baseline: None,
                baked_recipe: None,
            }),
        }
    }
    fn save(&self, name: &str, recipe: DevelopmentRecipe) -> PhotoVersion {
        save_version(
            &self.root,
            self.owner.clone(),
            name,
            recipe,
            &self.image,
            &self.owner.output,
            &AtomicBool::new(false),
        )
        .unwrap()
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.root);
    }
}

#[test]
fn immutable_version_roundtrip_rejects_wrong_owner_pixels_master_and_file() {
    let mut f = Fixture::new();
    let mut recipe = DevelopmentRecipe::default();
    recipe.global.exposure = 1.25;
    let mut record = f.save("Éclat · first", recipe.clone());
    record.name = "Renamed display name".into();
    let read = |f: &Fixture, v: &PhotoVersion| {
        read_version(
            &f.root,
            v,
            &f.owner,
            &f.image,
            &f.owner.output,
            &AtomicBool::new(false),
        )
    };
    assert_eq!(read(&f, &record).unwrap(), recipe);
    let bytes = fs::read(payload_path(&f.root, &record.id).unwrap()).unwrap();
    let mut different = f.owner.clone();
    different.stack = Some(5);
    different.run = Some("another-run".into());
    assert!(
        read_version(
            &f.root,
            &record,
            &different,
            &f.image,
            &f.owner.output,
            &AtomicBool::new(false)
        )
        .is_err()
    );
    Arc::make_mut(&mut f.image).pixels[7] = 0.8;
    assert!(
        read(&f, &record)
            .unwrap_err()
            .to_string()
            .contains("loaded photograph")
    );
    Arc::make_mut(&mut f.image).pixels[7] = 0.25;
    let master = f.root.join("master.tiff");
    fs::write(&master, b"master").unwrap();
    assert!(
        read_version(
            &f.root,
            &record,
            &f.owner,
            &f.image,
            &master,
            &AtomicBool::new(false)
        )
        .is_err()
    );
    fs::write(&f.owner.output, b"replaced TIFF evidence").unwrap();
    assert!(read(&f, &record).is_err());
    assert_eq!(
        fs::read(payload_path(&f.root, &record.id).unwrap()).unwrap(),
        bytes
    );
}

#[test]
fn cancelled_invalid_and_oversized_versions_never_publish() {
    let f = Fixture::new();
    for name in ["", "\n", "bad\0name", &"x".repeat(121)] {
        assert!(
            save_version(
                &f.root,
                f.owner.clone(),
                name,
                DevelopmentRecipe::default(),
                &f.image,
                &f.owner.output,
                &AtomicBool::new(false)
            )
            .is_err()
        );
    }
    assert!(
        save_version(
            &f.root,
            f.owner.clone(),
            "Cancelled",
            DevelopmentRecipe::default(),
            &f.image,
            &f.owner.output,
            &AtomicBool::new(true)
        )
        .is_err()
    );
    assert!(payload_path(&f.root, "../escape").is_err());
    let record = f.save("Valid", DevelopmentRecipe::default());
    fs::write(
        payload_path(&f.root, &record.id).unwrap(),
        vec![b' '; MAX_VERSION_BYTES + 1],
    )
    .unwrap();
    assert!(
        read_version(
            &f.root,
            &record,
            &f.owner,
            &f.image,
            &f.owner.output,
            &AtomicBool::new(false)
        )
        .is_err()
    );
    assert_eq!(
        fs::read_dir(&f.root)
            .unwrap()
            .filter_map(|entry| entry.ok())
            .filter(|e| e.path().extension().is_some_and(|s| s == "pending"))
            .count(),
        0
    );
}

#[test]
fn export_evidence_retains_format_and_detects_replaced_delivery() {
    let f = Fixture::new();
    let version = f.save("Delivery", DevelopmentRecipe::default());
    let settings = ExportSettings {
        format: strehl_edit::ExportFormat::Png,
        hdr: false,
        color_space: strehl_edit::OutputColorSpace::DisplayP3,
        ..Default::default()
    };
    assert!(
        record_export(
            &version,
            f.owner.output.clone(),
            settings.clone(),
            &AtomicBool::new(false)
        )
        .is_err()
    );
    let path = f.root.join("delivered.png");
    fs::write(&path, b"export pixels").unwrap();
    let record = record_export(
        &version,
        path.clone(),
        settings.clone(),
        &AtomicBool::new(false),
    )
    .unwrap();
    assert_eq!(record.settings, settings);
    assert_eq!(record.version, version.id);
    verify_export(&record, &AtomicBool::new(false)).unwrap();
    fs::write(path, b"replaced data").unwrap();
    assert!(verify_export(&record, &AtomicBool::new(false)).is_err());
}

#[test]
fn competing_catalog_writers_preserve_winner_and_recover_loser_without_replacing_it() {
    let f = Fixture::new();
    let path = f.root.join("projects.json");
    let mut first = super::super::Catalog::load(Some(path.clone()));
    first.create_project("Base").unwrap();
    first.save().unwrap();
    let mut a = super::super::Catalog::load(Some(path.clone()));
    let mut b = super::super::Catalog::load(Some(path.clone()));
    a.create_project("A").unwrap();
    b.create_project("B").unwrap();
    let gate = Arc::new(Barrier::new(2));
    let peer = gate.clone();
    let thread = std::thread::spawn(move || {
        peer.wait();
        let saved = a.save();
        (a, saved)
    });
    gate.wait();
    let b_saved = b.save();
    let (mut a, a_saved) = thread.join().unwrap();
    assert_ne!(
        a_saved.is_ok(),
        b_saved.is_ok(),
        "Exactly one writer may publish against the same expected bytes"
    );
    let loser = if a_saved.is_ok() { &mut b } else { &mut a };
    let winner = fs::read(&path).unwrap();
    let recovery = loser.recover_and_reload().unwrap();
    assert_eq!(fs::read(&path).unwrap(), winner);
    assert_ne!(fs::read(recovery).unwrap(), winner);
    loser.save().unwrap(); // loaded expected bytes must permit a no-op save
    assert!(path.with_extension("lock").is_file());
}

fn write_pending(path: &Path, bytes: &[u8]) {
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .unwrap();
    file.write_all(bytes).unwrap();
    file.sync_all().unwrap();
}

#[test]
fn immutable_publication_preserves_an_existing_destination_and_pending_payload() {
    let f = Fixture::new();
    let pending = f.root.join("candidate.pending");
    let destination = f.root.join("version.json");
    write_pending(&pending, b"complete candidate");
    fs::write(&destination, b"existing immutable version").unwrap();

    assert!(publish_version(&pending, &destination).is_err());
    assert_eq!(
        fs::read(&destination).unwrap(),
        b"existing immutable version"
    );
    assert_eq!(fs::read(&pending).unwrap(), b"complete candidate");
}

#[test]
fn competing_immutable_publishers_have_one_complete_winner_without_overwriting() {
    let f = Fixture::new();
    for round in 0..8 {
        let a = f.root.join(format!("a-{round}.pending"));
        let b = f.root.join(format!("b-{round}.pending"));
        let destination = f.root.join(format!("version-{round}.json"));
        let a_bytes = vec![b'a'; 128 * 1024 + round];
        let b_bytes = vec![b'b'; 96 * 1024 + round];
        write_pending(&a, &a_bytes);
        write_pending(&b, &b_bytes);
        let gate = Arc::new(Barrier::new(2));
        let peer = gate.clone();
        let peer_a = a.clone();
        let peer_destination = destination.clone();
        let thread = std::thread::spawn(move || {
            peer.wait();
            publish_version(&peer_a, &peer_destination)
        });
        gate.wait();
        let b_saved = publish_version(&b, &destination);
        let a_saved = thread.join().unwrap();
        assert_ne!(
            a_saved.is_ok(),
            b_saved.is_ok(),
            "Exactly one publisher wins"
        );
        let (winner, loser, loser_bytes) = if a_saved.is_ok() {
            (&a_bytes, &b, &b_bytes)
        } else {
            (&b_bytes, &a, &a_bytes)
        };
        assert_eq!(&fs::read(&destination).unwrap(), winner);
        assert_eq!(&fs::read(loser).unwrap(), loser_bytes);
        // Retrying the loser must still preserve the complete winning bytes.
        assert!(publish_version(loser, &destination).is_err());
        assert_eq!(&fs::read(&destination).unwrap(), winner);
        assert_eq!(&fs::read(loser).unwrap(), loser_bytes);
    }
}

#[cfg(windows)]
#[test]
fn immutable_publication_preserves_wide_unicode_paths() {
    let f = Fixture::new();
    let pending = f.root.join("\u{e9}clat-\u{753b}-\u{1f4f7}.pending");
    let destination = f.root.join("\u{e9}clat-\u{753b}-\u{1f4f7}.json");
    write_pending(&pending, b"complete Unicode payload");
    publish_version(&pending, &destination).unwrap();
    assert_eq!(fs::read(&destination).unwrap(), b"complete Unicode payload");
    assert!(!pending.exists());
}

#[cfg(windows)]
#[test]
fn immutable_publication_rejects_nul_in_either_path_without_truncating() {
    let f = Fixture::new();
    let pending = f.root.join("candidate.pending");
    let destination = f.root.join("version.json");
    write_pending(&pending, b"complete candidate");
    for corrupt_source in [true, false] {
        let mut source = pending.clone().into_os_string();
        let mut target = destination.clone().into_os_string();
        if corrupt_source {
            source.push("\0ignored");
        } else {
            target.push("\0ignored");
        }
        let error = publish_version(Path::new(&source), Path::new(&target)).unwrap_err();
        assert_eq!(error.kind(), std::io::ErrorKind::InvalidInput);
        assert_eq!(fs::read(&pending).unwrap(), b"complete candidate");
        assert!(!destination.exists());
    }
}

#[test]
fn cancelled_staged_version_cleans_owned_pending_without_publishing() {
    let f = Fixture::new();
    let pending = f.root.join("cancelled.pending");
    let destination = f.root.join("cancelled.json");
    let error = write_version_payload(
        &pending,
        &destination,
        b"complete but cancelled version",
        &AtomicBool::new(true),
    )
    .unwrap_err();
    assert!(error.to_string().contains("Photograph history cancelled"));
    assert!(!pending.exists());
    assert!(!destination.exists());
}

#[test]
fn staged_version_collision_never_removes_another_writers_pending_file() {
    let f = Fixture::new();
    let pending = f.root.join("collision.pending");
    let destination = f.root.join("collision.json");
    write_pending(&pending, b"another writer owns this pending payload");
    assert!(
        write_version_payload(
            &pending,
            &destination,
            b"must not replace or remove it",
            &AtomicBool::new(false),
        )
        .is_err()
    );
    assert_eq!(
        fs::read(&pending).unwrap(),
        b"another writer owns this pending payload"
    );
    assert!(!destination.exists());
}

#[test]
fn staged_version_publication_collision_cleans_only_owned_pending() {
    let f = Fixture::new();
    let pending = f.root.join("candidate.pending");
    let destination = f.root.join("version.json");
    fs::write(&destination, b"existing immutable version").unwrap();
    assert!(
        write_version_payload(
            &pending,
            &destination,
            b"new candidate",
            &AtomicBool::new(false),
        )
        .is_err()
    );
    assert_eq!(
        fs::read(&destination).unwrap(),
        b"existing immutable version"
    );
    assert!(!pending.exists());
}

#[cfg(windows)]
#[test]
fn immutable_publication_supports_paths_longer_than_win32_max_path() {
    use std::os::windows::ffi::OsStrExt;

    let f = Fixture::new();
    let mut directory = f.root.clone();
    while directory.as_os_str().encode_wide().count() <= 280 {
        directory.push("long-photograph-history-directory");
    }
    fs::create_dir_all(&directory).unwrap();
    let pending = directory.join("candidate.pending");
    let destination = directory.join("version.json");
    assert!(pending.as_os_str().encode_wide().count() > 260);
    assert!(destination.as_os_str().encode_wide().count() > 260);
    write_version_payload(
        &pending,
        &destination,
        b"complete version beyond MAX_PATH",
        &AtomicBool::new(false),
    )
    .unwrap();
    assert_eq!(
        fs::read(&destination).unwrap(),
        b"complete version beyond MAX_PATH"
    );
    assert!(!pending.exists());
    write_pending(&pending, b"must not overwrite the long-path version");
    assert!(publish_version(&pending, &destination).is_err());
    assert_eq!(
        fs::read(&destination).unwrap(),
        b"complete version beyond MAX_PATH"
    );
    assert_eq!(
        fs::read(&pending).unwrap(),
        b"must not overwrite the long-path version"
    );
}

#[cfg(windows)]
#[test]
fn immutable_publication_rejects_a_different_destination_directory() {
    let f = Fixture::new();
    let pending = f.root.join("candidate.pending");
    let other = f.root.join("other");
    fs::create_dir(&other).unwrap();
    let destination = other.join("version.json");
    write_pending(&pending, b"complete candidate");
    let error = publish_version(&pending, &destination).unwrap_err();
    assert_eq!(error.kind(), std::io::ErrorKind::InvalidInput);
    assert_eq!(fs::read(&pending).unwrap(), b"complete candidate");
    assert!(!destination.exists());
}
