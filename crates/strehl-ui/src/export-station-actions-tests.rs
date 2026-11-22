//! Owner feedback on the Export station (2026-11-21): no "New" tags, the AVIF
//! encoder's effort back as its own option beside quality, and a footer that
//! always answers a press.
use super::*;

/// One frame of the 348 px inspector (body and foot) for `view`.
fn inspector_frame(
    ctx: &egui::Context,
    panel: &mut ExportPanel,
    view: &ExportView<'_>,
    events: Vec<egui::Event>,
) -> (egui::FullOutput, Vec<ExportIntent>) {
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
                .show(ctx, |ui| intents = inspector(ui, panel, view));
        },
    );
    (output, intents)
}

fn view<'a>(
    palette: &'a StudioPalette,
    lib: &'a Library,
    destination: Option<&'a Path>,
) -> ExportView<'a> {
    ExportView {
        palette,
        library: lib,
        fields: fields(),
        destination,
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
    }
}

fn texts(output: &egui::FullOutput) -> Vec<(String, Rect)> {
    fn walk(shape: &egui::Shape, into: &mut Vec<(String, Rect)>) {
        match shape {
            egui::Shape::Text(text) => {
                into.push((text.galley.text().to_owned(), text.visual_bounding_rect()))
            }
            egui::Shape::Vec(parts) => parts.iter().for_each(|part| walk(part, into)),
            _ => {}
        }
    }
    let mut found = Vec::new();
    for shape in &output.shapes {
        walk(&shape.shape, &mut found);
    }
    found
}

fn find(output: &egui::FullOutput, text: &str) -> Option<Rect> {
    texts(output)
        .into_iter()
        .find(|(t, _)| t == text)
        .map(|(_, rect)| rect)
}

fn click(at: egui::Pos2) -> Vec<egui::Event> {
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
}

#[test]
fn effort_is_ten_minus_speed_and_defaults_to_four() {
    assert_eq!(effort_of(ExportSettings::default().speed), 4);
    for speed in 0..=10 {
        assert_eq!(speed_of(effort_of(speed)), speed);
    }
    assert_eq!((effort_of(10), effort_of(0)), (0, 10));
    // Out-of-range values clamp instead of wrapping.
    assert_eq!((effort_of(200), speed_of(200)), (0, 0));
}

#[test]
fn the_time_estimate_follows_quality_range_and_effort() {
    // MEASURED on the 7032 x 4688 weevil, release build (g-develop note):
    // (quality, HDR, effort, seconds). The last three were held out of the
    // fit and measured after it.
    let measured: [(u8, bool, u8, f64); 22] = [
        // The single q100 curve said 46 s here.
        (50, false, 4, 12.75),
        (70, false, 4, 15.23),
        (85, false, 4, 17.36),
        (90, false, 4, 19.66),
        (95, false, 4, 22.59),
        (100, false, 4, 35.49),
        (50, true, 4, 14.28),
        (70, true, 4, 19.44),
        (85, true, 4, 22.05),
        (90, true, 4, 23.80),
        (95, true, 4, 32.22),
        (100, true, 4, 39.04),
        (100, true, 4, 33.43),
        (100, true, 0, 11.80),
        (100, true, 8, 172.50),
        (85, false, 0, 5.55),
        (85, false, 8, 97.02),
        (85, true, 0, 9.41),
        (85, true, 8, 101.92),
        // Held out.
        (50, false, 0, 4.65),
        (50, false, 8, 74.25),
        (70, true, 6, 47.88),
    ];
    let avif = |quality, hdr, effort| {
        PresetOutput::Image(crate::export_presets::ImagePreset {
            settings: ExportSettings {
                format: ExportFormat::Avif,
                color_space: if hdr {
                    OutputColorSpace::Rec2020
                } else {
                    OutputColorSpace::Srgb
                },
                hdr,
                quality,
                speed: speed_of(effort),
                ..Default::default()
            },
            copyright: false,
            description: false,
        })
    };
    for (quality, hdr, effort, seconds) in measured {
        let estimate = estimate_seconds(&[&avif(quality, hdr, effort)], [7032, 4688]);
        assert!(
            (estimate / seconds - 1.0).abs() < 0.2,
            "q{quality} hdr {hdr} effort {effort}: estimate {estimate:.1} s, measured {seconds} s"
        );
    }
    // Time rises with quality and with effort everywhere.
    for hdr in [false, true] {
        let by_quality: Vec<f64> = (1..=100).map(|q| avif_seconds_per_mp(q, hdr, 4)).collect();
        assert!(by_quality.windows(2).all(|w| w[0] < w[1]));
        let by_effort: Vec<f64> = (0..=10).map(|e| avif_seconds_per_mp(90, hdr, e)).collect();
        assert!(by_effort.windows(2).all(|w| w[0] < w[1]));
    }
}

#[test]
fn the_avif_size_estimate_follows_quality_and_range() {
    // MEASURED at effort 4 on the 7032 x 4688 weevil (g-develop note):
    // (quality, SDR bytes, HDR bytes).
    let measured: [(u8, f64, f64); 6] = [
        (50, 1_962_728.0, 1_704_501.0),
        (70, 3_769_846.0, 5_812_210.0),
        (85, 6_656_658.0, 13_876_666.0),
        (90, 9_236_099.0, 20_899_095.0),
        (95, 15_871_122.0, 33_442_454.0),
        (100, 36_276_821.0, 59_165_477.0),
    ];
    let avif = |quality, hdr| {
        PresetOutput::Image(crate::export_presets::ImagePreset {
            settings: ExportSettings {
                format: ExportFormat::Avif,
                color_space: if hdr {
                    OutputColorSpace::Rec2020
                } else {
                    OutputColorSpace::Srgb
                },
                hdr,
                quality,
                ..Default::default()
            },
            copyright: false,
            description: false,
        })
    };
    let size = [7032, 4688];
    for (quality, sdr, hdr) in measured {
        for (range, bytes) in [(false, sdr), (true, hdr)] {
            let estimate = estimate_bytes(&avif(quality, range), size) as f64;
            assert!(
                (estimate / bytes - 1.0).abs() < 0.01,
                "q{quality} hdr {range}: estimate {estimate}, measured {bytes}"
            );
        }
    }
    // The HDR preset (quality 100) reads about 59 MB, not the 13.8 MB of
    // the old constant.
    let lib = library();
    let hdr = &lib.presets.iter().find(|p| p.name == "HDR").unwrap().output;
    assert_eq!(human_bytes(estimate_bytes(hdr, size)), "59.2 MB");
    // Between and below the measurements the size still rises with quality.
    for range in [false, true] {
        let sizes: Vec<f64> = (1..=100).map(|q| avif_bytes_per_pixel(q, range)).collect();
        assert!(sizes.windows(2).all(|w| w[0] < w[1]), "{sizes:?}");
        assert!(sizes[0] > 0.0);
    }
}

#[test]
fn avif_presets_show_encoder_effort_beside_quality_and_no_new_tags() {
    let ctx = egui::Context::default();
    let lib = library();
    let palette = StudioPalette::GRAPHITE;
    let folder = std::env::temp_dir();
    let hdr = lib.presets.iter().find(|p| p.name == "HDR").unwrap();
    let mut panel = ExportPanel {
        selected: Some(hdr.id.clone()),
        ..Default::default()
    };
    let v = view(&palette, &lib, Some(&folder));
    let (output, intents) = inspector_frame(&ctx, &mut panel, &v, vec![]);
    assert!(intents.is_empty());
    for label in ["Quality", "Encoder effort", "Size", "Sharpen for the size"] {
        assert!(find(&output, label).is_some(), "{label} is not drawn");
    }
    let all = texts(&output);
    assert!(
        !all.iter().any(|(t, _)| t.eq_ignore_ascii_case("new")),
        "a New tag is still drawn"
    );
    assert!(
        all.iter()
            .any(|(t, _)| t.starts_with("About ") && t.contains("Less effort finishes sooner")),
        "the effort's time note is missing"
    );
    // Dragging the effort to the right asks for a slower encode.
    let row = find(&output, "Encoder effort").unwrap();
    let value = all
        .iter()
        .find(|(t, r)| t == "4" && (r.center().y - row.center().y).abs() < 8.0)
        .map(|(_, r)| r.center())
        .expect("the effort value, 4, on its row");
    let drag = vec![
        egui::Event::PointerMoved(value),
        egui::Event::PointerButton {
            pos: value,
            button: egui::PointerButton::Primary,
            pressed: true,
            modifiers: Default::default(),
        },
    ];
    inspector_frame(&ctx, &mut panel, &v, drag);
    let mut asked = Vec::new();
    // Past egui's drag threshold, then on.
    for step in 1..=3 {
        let at = value + egui::vec2(step as f32 * 10.0, 0.0);
        let (_, intents) =
            inspector_frame(&ctx, &mut panel, &v, vec![egui::Event::PointerMoved(at)]);
        asked.extend(intents);
    }
    inspector_frame(
        &ctx,
        &mut panel,
        &v,
        vec![egui::Event::PointerButton {
            pos: value + egui::vec2(30.0, 0.0),
            button: egui::PointerButton::Primary,
            pressed: false,
            modifiers: Default::default(),
        }],
    );
    let speeds: Vec<u8> = asked
        .iter()
        .filter_map(|intent| match intent {
            ExportIntent::Edit(id, PresetOutput::Image(image)) if id == &hdr.id => {
                Some(image.settings.speed)
            }
            _ => None,
        })
        .collect();
    assert!(!speeds.is_empty(), "the drag asked for nothing: {asked:?}");
    assert!(
        speeds.iter().all(|&s| s < 6),
        "more effort is a lower speed: {speeds:?}"
    );
    // Quality is untouched by the effort.
    assert!(asked.iter().all(|intent| match intent {
        ExportIntent::Edit(_, PresetOutput::Image(image)) => image.settings.quality == 100,
        _ => true,
    }));
    // JPEG (Web) has quality but no encoder effort.
    let web = lib.presets.iter().find(|p| p.name == "Web").unwrap();
    panel.selected = Some(web.id.clone());
    let (output, _) = inspector_frame(&ctx, &mut panel, &v, vec![]);
    assert!(find(&output, "Quality").is_some());
    assert!(find(&output, "Encoder effort").is_none());
}

#[test]
fn the_encoder_effort_reaches_the_encoder() {
    let dir = tempfile::tempdir().unwrap();
    let master = dir.path().join("master.tiff");
    std::fs::write(&master, b"linear master bytes").unwrap();
    let mut lib = library();
    for preset in &mut lib.presets {
        preset.enabled = false;
    }
    let sdr = |speed| {
        PresetOutput::Image(crate::export_presets::ImagePreset {
            settings: ExportSettings {
                format: ExportFormat::Avif,
                color_space: OutputColorSpace::Srgb,
                hdr: false,
                quality: 80,
                speed,
                ..Default::default()
            },
            copyright: false,
            description: false,
        })
    };
    lib.add("Fast", sdr(speed_of(0))).unwrap();
    lib.add("Thorough", sdr(speed_of(6))).unwrap();
    let files = plan_batch(
        &lib,
        &fields(),
        dir.path(),
        &master,
        &BatchText::default(),
        |p| p.exists(),
    )
    .unwrap();
    let planned: Vec<u8> = files
        .iter()
        .map(|f| match &f.output {
            BatchOutput::Image(settings) => settings.speed,
            BatchOutput::Archive { .. } => panic!("no archive was ticked"),
        })
        .collect();
    assert_eq!(planned, vec![10, 4]);
    let context = BatchContext {
        job: job(),
        recipe_json: b"{\"version\":1}".to_vec(),
        um_per_px: None,
        date: None,
        version: None,
    };
    let done = run_batch(files.clone(), &context, &BatchProgress::new(&files));
    assert!(done.failed.is_empty(), "{:?}", done.failed);
    let written: Vec<Vec<u8>> = files
        .iter()
        .map(|f| std::fs::read(&f.path).unwrap())
        .collect();
    // Each file is the encoder's output at its preset's speed: the same call
    // made directly gives the same bytes, and the two speeds differ.
    for (file, bytes) in files.iter().zip(&written) {
        let BatchOutput::Image(settings) = &file.output else {
            unreachable!()
        };
        let direct = dir.path().join(format!("direct-{}.avif", settings.speed));
        context
            .job
            .export_with(
                &direct,
                settings,
                None,
                None,
                &std::sync::atomic::AtomicBool::new(false),
            )
            .unwrap();
        assert_eq!(
            &std::fs::read(&direct).unwrap(),
            bytes,
            "speed {} was not the encoder's",
            settings.speed
        );
    }
    assert_ne!(
        written[0], written[1],
        "the two speeds encoded the same bytes"
    );
}

#[test]
fn the_footer_answers_every_press() {
    let ctx = egui::Context::default();
    let lib = library();
    let palette = StudioPalette::GRAPHITE;
    let folder = std::env::temp_dir();
    let mut panel = ExportPanel::default();
    // No folder yet: the button chooses one instead of sitting disabled.
    let v = view(&palette, &lib, None);
    let (output, _) = inspector_frame(&ctx, &mut panel, &v, vec![]);
    let choose = find(&output, "Choose a folder…").expect("the folder button");
    let (_, intents) = inspector_frame(&ctx, &mut panel, &v, click(choose.center()));
    assert_eq!(intents, vec![ExportIntent::ChangeDestination]);
    // Something must finish first: the press still goes through, so the
    // app can say what it waits for.
    let mut v = view(&palette, &lib, Some(&folder));
    v.blocker = Some("Wait for the look to finish calculating");
    let (output, _) = inspector_frame(&ctx, &mut panel, &v, vec![]);
    let export = find(&output, "Export 2 files").unwrap();
    let (_, intents) = inspector_frame(&ctx, &mut panel, &v, click(export.center()));
    assert_eq!(intents, vec![ExportIntent::ExportTicked]);
    // The result heads the inspector with Open folder and Dismiss.
    v.blocker = None;
    v.feedback = Some(Feedback {
        ok: true,
        text: "Wrote 2 files to C:\\exports",
        folder: true,
    });
    let (output, _) = inspector_frame(&ctx, &mut panel, &v, vec![]);
    let said = find(&output, "Wrote 2 files to C:\\exports").expect("the result line");
    let presets = find(&output, "PRESETS").unwrap();
    assert!(
        said.bottom() < presets.top(),
        "the result is not at the head"
    );
    let open = find(&output, "OPEN FOLDER").unwrap();
    let (_, intents) = inspector_frame(&ctx, &mut panel, &v, click(open.center()));
    assert_eq!(intents, vec![ExportIntent::OpenFolder]);
    let dismiss = find(&output, "DISMISS").unwrap();
    let (_, intents) = inspector_frame(&ctx, &mut panel, &v, click(dismiss.center()));
    assert_eq!(intents, vec![ExportIntent::DismissFeedback]);
    // An error is said in words, with Dismiss only.
    v.feedback = Some(Feedback {
        ok: false,
        text: "Choose where this subject's files go",
        folder: false,
    });
    let (output, _) = inspector_frame(&ctx, &mut panel, &v, vec![]);
    assert!(find(&output, "Choose where this subject's files go").is_some());
    assert!(find(&output, "OPEN FOLDER").is_none());
    assert!(find(&output, "DISMISS").is_some());
}
