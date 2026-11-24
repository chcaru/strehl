use super::*;
use std::sync::Arc;
use strehl_edit::{DevelopmentRecipe, ImageOrigin, LinearImage};

fn library() -> Library {
    Library::default()
}

fn fields() -> NameFields<'static> {
    NameFields {
        subject: "Blue weevil",
        view: "Dorsal",
        preset: "",
        date: "2026-11-21",
    }
}

#[test]
fn preset_lines_match_the_mockup() {
    let lib = library();
    let line =
        |name: &str| preset_summary(&lib.presets.iter().find(|p| p.name == name).unwrap().output);
    assert_eq!(line("Web"), "JPEG · sRGB · 2560 px long edge · quality 90");
    assert_eq!(line("HDR"), "AVIF · Rec.2020 PQ · full size · 10-bit");
    assert_eq!(line("Print"), "TIFF 16-bit · Display P3 · full size");
    assert_eq!(line("Archive"), "Linear master and the develop recipe");
    let web = &lib.presets[0].output;
    assert_eq!(output_size(web, [7032, 4688]), [2560, 1707]);
    assert_eq!(human_bytes(estimate_bytes(web, [7032, 4688])), "1.7 MB");
    assert_eq!(format_seconds(24.6), "25 s");
}

#[test]
fn a_batch_plans_free_names_for_every_ticked_preset() {
    let dir = tempfile::tempdir().unwrap();
    let mut lib = library();
    for preset in &mut lib.presets {
        preset.enabled = true;
    }
    std::fs::write(dir.path().join("Blue weevil-Dorsal-Web.jpg"), b"existing").unwrap();
    let files = plan_batch(
        &lib,
        &lib.template,
        &fields(),
        dir.path(),
        Path::new("master.tiff"),
        &BatchText {
            artist: "Chris".into(),
            copyright: "© 2026".into(),
            description: "Weevil".into(),
        },
        |p| p.exists(),
    )
    .unwrap();
    let names: Vec<String> = files
        .iter()
        .map(|f| f.path.file_name().unwrap().to_string_lossy().into_owned())
        .collect();
    assert_eq!(
        names,
        [
            "Blue weevil-Dorsal-Web (2).jpg",
            "Blue weevil-Dorsal-HDR.avif",
            "Blue weevil-Dorsal-Print.tiff",
            "Blue weevil-Dorsal-Archive.tiff",
        ]
    );
    match &files[3].output {
        BatchOutput::Archive { recipe, .. } => {
            assert!(recipe.ends_with("Blue weevil-Dorsal-Archive.strehl-edits.json"))
        }
        other => panic!("{other:?}"),
    }
    // Text enters only through a preset's switches (all off by default).
    let BatchOutput::Image(web) = &files[0].output else {
        panic!()
    };
    assert!(web.metadata.is_empty());
    for preset in &mut lib.presets {
        preset.enabled = false;
    }
    assert!(
        plan_batch(
            &lib,
            &lib.template,
            &fields(),
            dir.path(),
            Path::new("m"),
            &BatchText::default(),
            |_| false
        )
        .is_err()
    );
}

fn job() -> crate::development_job::DevelopmentJob {
    let image = Arc::new(LinearImage {
        width: 64,
        height: 40,
        pixels: (0..64 * 40)
            .flat_map(|i| [0.02 + (i % 64) as f32 * 0.01, 0.1, 0.2])
            .collect(),
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    });
    crate::development_job::DevelopmentJob::new(image.clone(), image, DevelopmentRecipe::default())
}

#[test]
fn a_batch_writes_every_file_through_one_job_with_a_phase_per_file() {
    let dir = tempfile::tempdir().unwrap();
    let master = dir.path().join("master.tiff");
    strehl_edit::save_linear_tiff(&master, job().image(false)).unwrap();
    let mut lib = library();
    for preset in &mut lib.presets {
        preset.enabled = preset.name != "HDR";
    }
    let files = plan_batch(
        &lib,
        &lib.template,
        &fields(),
        dir.path(),
        &master,
        &BatchText::default(),
        |p| p.exists(),
    )
    .unwrap();
    let progress = BatchProgress::new(&files);
    let start = progress.snapshot();
    assert_eq!(
        (start.file, start.files, start.phase),
        (0, 3, BatchPhase::Preparing)
    );
    assert_eq!(start.caption(), "File 1 of 3 · Web · preparing");
    let context = BatchContext {
        job: job(),
        recipe_json: b"{\"version\":1}".to_vec(),
        um_per_px: None,
        date: None,
        version: None,
    };
    let done = run_batch(files.clone(), &context, &progress);
    assert!(done.failed.is_empty(), "{:?}", done.failed);
    assert_eq!(done.written.len(), 3);
    for file in &files {
        assert!(file.path.is_file(), "{} missing", file.path.display());
    }
    let archive = files.iter().find(|f| f.preset == "Archive").unwrap();
    assert_eq!(
        std::fs::read(&archive.path).unwrap(),
        std::fs::read(&master).unwrap()
    );
    // Every file of the batch names Strehl (h-develop): the Web JPEG in its
    // Exif and XMP, the Print TIFF in its Software tag, and the Archive, a
    // copy of the master, in the master's. `strehl-edit`'s `export-stamp.rs`
    // reads each container properly; here the batch path is checked.
    for (preset, stamp) in [
        ("Web", &b"<xmp:CreatorTool>Strehl</xmp:CreatorTool>"[..]),
        ("Print", b"Strehl development v1\0"),
        ("Archive", b"Strehl scene-linear master v1\0"),
    ] {
        let file = files.iter().find(|f| f.preset == preset).unwrap();
        let bytes = std::fs::read(&file.path).unwrap();
        assert!(
            bytes.windows(stamp.len()).any(|w| w == stamp),
            "{preset} does not name Strehl"
        );
        if preset == "Web" {
            assert!(bytes.windows(6).any(|w| w == b"Exif\0\0"));
        }
    }
    let end = progress.snapshot();
    assert_eq!((end.phase, end.fraction()), (BatchPhase::Done, 1.0));
    // A second run never overwrites: the same plan now fails file by file.
    let again = run_batch(files.clone(), &context, &progress);
    assert_eq!(again.failed.len(), 3);
    // Cancelled before it starts, it writes nothing.
    let fresh = plan_batch(
        &lib,
        &lib.template,
        &fields(),
        dir.path(),
        &master,
        &BatchText::default(),
        |p| p.exists(),
    )
    .unwrap();
    let cancelled = BatchProgress::new(&fresh);
    cancelled.cancelled.store(true, Ordering::Relaxed);
    let none = run_batch(fresh.clone(), &context, &cancelled);
    assert!(none.cancelled && none.written.is_empty());
    assert!(fresh.iter().all(|f| !f.path.exists()));
}

#[test]
fn the_inspector_shows_the_batch_button_and_ticks_presets() {
    let ctx = egui::Context::default();
    let lib = library();
    let palette = StudioPalette::GRAPHITE;
    let mut panel = ExportPanel::default();
    let folder = std::env::temp_dir();
    let run = |events: Vec<egui::Event>, panel: &mut ExportPanel| {
        let mut intents = Vec::new();
        let output = ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(
                    egui::Pos2::ZERO,
                    egui::vec2(348.0, 982.0),
                )),
                events,
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(ctx, |ui| {
                        let view = ExportView {
                            palette: &palette,
                            library: &lib,
                            name: &lib.template,
                            fields: fields(),
                            destination: Some(&folder),
                            size: [7032, 4688],
                            has_scale_bar: true,
                            calibrated: true,
                            hdr_photo: true,
                            history: &[],
                            batch: None,
                            blocker: None,
                            feedback: None,
                            note: None,
                            view_bundle: None,
                            words: Words::default(),
                        };
                        intents = inspector(ui, panel, &view);
                    });
            },
        );
        (output, intents)
    };
    let (output, intents) = run(Vec::new(), &mut panel);
    assert!(intents.is_empty());
    let find = |text: &str| {
        output.shapes.iter().find_map(|s| match &s.shape {
            egui::Shape::Text(t) if t.galley.text() == text => Some(t.pos + t.galley.size() * 0.5),
            _ => None,
        })
    };
    assert!(
        find("Export 2 files").is_some(),
        "Web and HDR are ticked by default"
    );
    assert!(find("Blue weevil-Dorsal-Web.jpg · 1.7 MB").is_some());
    let click = |at: egui::Pos2| {
        vec![
            egui::Event::PointerMoved(at),
            egui::Event::PointerButton {
                pos: at,
                button: egui::PointerButton::Primary,
                pressed: true,
                modifiers: Default::default(),
            },
            egui::Event::PointerButton {
                pos: at,
                button: egui::PointerButton::Primary,
                pressed: false,
                modifiers: Default::default(),
            },
        ]
    };
    let (_, intents) = run(click(find("Export 2 files").unwrap()), &mut panel);
    assert_eq!(intents, vec![ExportIntent::ExportTicked]);
    // The Print row's box sits 13 px below its top, 16 px in.
    let print = find("Print").unwrap();
    let (_, intents) = run(
        click(egui::pos2(16.0 + 7.0, print.y - 18.0 + 20.0)),
        &mut panel,
    );
    assert_eq!(
        intents,
        vec![ExportIntent::Tick(lib.presets[2].id.clone(), true)]
    );
}

#[path = "export-station-actions-tests.rs"]
mod actions;
