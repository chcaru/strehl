use super::*;
use strehl_edit::OutputSharpening;

fn directory() -> PathBuf {
    let path = std::env::temp_dir().join(format!(
        "strehl-export-preset-test-{}",
        random_id().unwrap()
    ));
    std::fs::create_dir(&path).unwrap();
    path
}

fn png() -> PresetOutput {
    PresetOutput::Image(ImagePreset {
        settings: ExportSettings {
            format: ExportFormat::Png,
            color_space: OutputColorSpace::DisplayP3,
            hdr: false,
            ..Default::default()
        },
        copyright: true,
        description: false,
    })
}

#[test]
fn defaults_are_the_four_planned_presets_and_a_web_copy_leaves_with_a_full_size_file() {
    let library = Library::default();
    library.validate().unwrap();
    let names: Vec<&str> = library.presets.iter().map(|p| p.name.as_str()).collect();
    assert_eq!(names, ["Web", "HDR", "Print", "Archive"]);
    let image = |name: &str| match &library
        .presets
        .iter()
        .find(|p| p.name == name)
        .unwrap()
        .output
    {
        PresetOutput::Image(image) => image.settings.clone(),
        PresetOutput::Archive => panic!("{name} is not an image"),
    };
    let web = image("Web");
    assert_eq!(
        (web.format, web.color_space, web.hdr, web.quality),
        (ExportFormat::Jpeg, OutputColorSpace::Srgb, false, 90)
    );
    assert_eq!(web.resize.unwrap().long_edge, 2560);
    assert!(
        web.sharpen.is_none(),
        "sharpening waits for the owner's native-crop review"
    );
    let hdr = image("HDR");
    assert_eq!(
        (hdr.format, hdr.color_space, hdr.hdr),
        (ExportFormat::Avif, OutputColorSpace::Rec2020, true)
    );
    assert!(hdr.resize.is_none(), "full size");
    let print = image("Print");
    assert_eq!(
        (print.format, print.color_space, print.hdr),
        (ExportFormat::Tiff, OutputColorSpace::DisplayP3, false)
    );
    assert!(!print.embed_recipe, "recipe switch is off by default");
    assert_eq!(library.presets[3].output, PresetOutput::Archive);
    // One action: the ticked batch holds a web copy and a full-size file.
    let ticked: Vec<&str> = library.ticked().map(|p| p.name.as_str()).collect();
    assert_eq!(ticked, ["Web", "HDR"]);
    assert_eq!(library.template, "{subject}-{view}-{preset}");
}

#[test]
fn presets_carry_switches_not_personal_text() {
    let mut library = Library::default();
    let id = library.add("Proof", png()).unwrap();
    let PresetOutput::Image(preset) = &library.presets.iter().find(|p| p.id == id).unwrap().output
    else {
        panic!()
    };
    let settings = preset
        .resolve(" Chris Caruso ", "© 2026 Chris Caruso", "Weevil")
        .unwrap();
    assert_eq!(settings.metadata.artist, "Chris Caruso");
    assert_eq!(settings.metadata.copyright, "© 2026 Chris Caruso");
    assert!(
        settings.metadata.description.is_empty(),
        "description switch is off"
    );
    let json = serde_json::to_string(&library).unwrap();
    assert!(!json.contains("Chris"), "no personal text is stored");
    let mut bad = png();
    if let PresetOutput::Image(image) = &mut bad {
        image.settings.metadata.artist = "Someone".into();
    }
    assert!(library.add("Leaky", bad).is_err());
    let mut bad = png();
    if let PresetOutput::Image(image) = &mut bad {
        image.settings.sharpen = Some(OutputSharpening {
            amount: 5.0,
            ..Default::default()
        });
    }
    assert!(library.update(&id, bad).is_err(), "settings are validated");
}

#[test]
fn names_are_unique_and_the_library_round_trips_its_edits() {
    let mut library = Library::default();
    assert!(
        library.add("web", png()).is_err(),
        "case-insensitive unique"
    );
    let id = library.add("  Proof sheet  ", png()).unwrap();
    assert_eq!(library.presets.last().unwrap().name, "Proof sheet");
    for name in ["", " \t", "bad\nname", &"a".repeat(97)] {
        assert!(library.add(name, png()).is_err());
    }
    library.rename(&id, "Contact").unwrap();
    assert!(library.rename(&id, "Print").is_err());
    library.set_enabled(&id, false).unwrap();
    let (index, removed) = library.remove(&id).unwrap();
    library.restore(index, removed).unwrap();
    assert!(!library.presets[index].enabled);
    library.validate().unwrap();
    let mut duplicate = library.clone();
    duplicate.presets.push(duplicate.presets[0].clone());
    assert!(duplicate.validate().is_err());
    let mut future = serde_json::to_value(&library).unwrap();
    future["version"] = serde_json::json!(2);
    assert!(
        serde_json::from_value::<Library>(future)
            .unwrap()
            .validate()
            .is_err()
    );
    let mut unknown = serde_json::to_value(&library).unwrap();
    unknown["presets"][0]["copied"] = serde_json::json!(true);
    assert!(serde_json::from_value::<Library>(unknown).is_err());
}

#[test]
fn name_templates_expand_into_safe_file_stems() {
    let fields = NameFields {
        subject: "Weevil: Curculio / nucum",
        view: "Version 2",
        preset: "Web",
        date: "2026-11-21",
    };
    assert_eq!(
        expand_name(DEFAULT_TEMPLATE, &fields).unwrap(),
        "Weevil- Curculio - nucum-Version 2-Web"
    );
    assert_eq!(
        expand_name(
            "{date} {subject}",
            &NameFields {
                subject: "昆虫*?",
                ..fields.clone()
            }
        )
        .unwrap(),
        "2026-11-21 昆虫"
    );
    for bad in ["", "plain", "{nope}", "{subject", "subject}", "a\tb{view}"] {
        assert!(expand_name(bad, &fields).is_err(), "{bad:?}");
    }
    assert_eq!(sanitize_stem("  ..hidden. "), "hidden");
    assert_eq!(sanitize_stem("con"), "con_");
    assert_eq!(sanitize_stem("COM3.final"), "COM3.final_");
    assert_eq!(sanitize_stem("com10"), "com10");
    assert_eq!(sanitize_stem("::"), "untitled");
    assert_eq!(sanitize_stem(&"x".repeat(300)).chars().count(), 120);
    let mut library = Library::default();
    assert!(library.set_template("{nope}").is_err());
    library.set_template("{subject} {preset}").unwrap();
}

#[test]
fn available_paths_never_reuse_an_existing_name() {
    let dir = directory();
    std::fs::write(dir.join("bug-Web.jpg"), b"existing").unwrap();
    std::fs::write(dir.join("bug-Web (2).jpg"), b"existing").unwrap();
    let path = available_path(&dir, "bug-Web", "jpg", |p| p.exists()).unwrap();
    assert_eq!(path, dir.join("bug-Web (3).jpg"));
    assert_eq!(
        available_path(&dir, "bug-HDR", "avif", |p| p.exists()).unwrap(),
        dir.join("bug-HDR.avif")
    );
    assert!(available_path(&dir, "x", "jpg", |_| true).is_err());
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn destinations_are_remembered_per_subject() {
    let mut library = Library::default();
    let folder = std::env::temp_dir().join("strehl-exports");
    assert!(library.destination("subject-a").is_none());
    library.remember_destination("subject-a", &folder).unwrap();
    library
        .remember_destination("subject-b", &folder.join("b"))
        .unwrap();
    assert_eq!(library.destination("subject-a"), Some(folder.as_path()));
    assert!(
        library
            .remember_destination("subject-c", Path::new("relative"))
            .is_err()
    );
    assert!(library.remember_destination("", &folder).is_err());
    assert_eq!(
        library.forget_destination("subject-b"),
        Some(folder.join("b"))
    );
    library.validate().unwrap();
}

#[test]
fn persistence_is_atomic_and_detects_external_changes() {
    let dir = directory();
    let catalog = dir.join("projects.json");
    let path = library_path(&catalog);
    assert_eq!(path, dir.join("export-presets.json"));
    let loaded = load(&path).unwrap();
    assert!(loaded.bytes.is_none());
    assert_eq!(loaded.library, Library::default());
    let mut library = loaded.library;
    library.add("Proof", png()).unwrap();
    let bytes = save(&path, &library, None).unwrap();
    assert_eq!(load(&path).unwrap().library, library);
    library.remember_destination("s", &dir).unwrap();
    let newer = save(&path, &library, Some(&bytes)).unwrap();
    assert!(save(&path, &Library::default(), Some(&bytes)).is_err());
    assert_eq!(
        std::fs::read(&path).unwrap(),
        newer,
        "stale window must not clobber"
    );
    let recovery = save_recovery(&path, &Library::default()).unwrap();
    assert_eq!(load(&recovery).unwrap().library, Library::default());
    // A malformed library is an error, never silently replaced.
    std::fs::write(&path, b"{not json").unwrap();
    assert!(load(&path).is_err());
    let held = std::fs::OpenOptions::new()
        .read(true)
        .write(true)
        .open(path.with_extension("lock"))
        .unwrap();
    held.try_lock().unwrap();
    assert!(
        save(&path, &library, Some(b"{not json")).is_err(),
        "negative control: a held lock blocks publication"
    );
    drop(held);
    save(&path, &library, Some(b"{not json")).unwrap();
    std::fs::remove_dir_all(dir).unwrap();
}
