use super::*;

/// egui's bundled proportional face stands in for every system face, so the
/// family wiring is tested without depending on what this machine installed.
fn stand_in() -> &'static [u8] {
    static BYTES: OnceLock<&'static [u8]> = OnceLock::new();
    BYTES.get_or_init(|| {
        let fonts = FontDefinitions::default();
        let name = &fonts.families[&FontFamily::Proportional][0];
        let bytes = fonts.font_data[name].font.to_vec();
        Box::leak(bytes.into_boxed_slice())
    })
}

fn chain_of(fonts: &FontDefinitions, name: &str) -> Vec<String> {
    fonts.families[&FontFamily::Name(name.into())].clone()
}

#[test]
fn every_family_starts_with_its_system_face_and_ends_with_egui_fallbacks() {
    let fonts = definitions_with(|_| Some(stand_in()));
    let defaults = FontDefinitions::default().families[&FontFamily::Proportional].clone();
    assert_eq!(
        fonts.families[&FontFamily::Proportional][..2],
        [BAHNSCHRIFT.to_owned(), SEGOE.to_owned()]
    );
    assert_eq!(
        chain_of(&fonts, DIN),
        fonts.families[&FontFamily::Proportional]
    );
    assert_eq!(chain_of(&fonts, DIN_STRONG)[0], SEGOE_SEMIBOLD);
    assert_eq!(chain_of(&fonts, DIN_LIGHT)[0], SEGOE_LIGHT);
    for name in [DIN, DIN_STRONG, DIN_LIGHT] {
        let chain = chain_of(&fonts, name);
        assert!(chain.ends_with(&defaults), "{name}: {chain:?}");
        let mut unique = chain.clone();
        unique.sort();
        unique.dedup();
        assert_eq!(unique.len(), chain.len(), "{name} repeats a face");
        for face in &chain {
            assert!(fonts.font_data.contains_key(face), "{name} names {face}");
        }
    }
    // Monospace is untouched: the plan names no monospaced system face.
    assert_eq!(
        fonts.families[&FontFamily::Monospace],
        FontDefinitions::default().families[&FontFamily::Monospace]
    );
}

#[test]
fn missing_system_faces_fall_back_without_naming_absent_font_data() {
    let fonts = definitions_with(|_| None);
    let defaults = FontDefinitions::default().families[&FontFamily::Proportional].clone();
    for name in [DIN, DIN_STRONG, DIN_LIGHT] {
        assert_eq!(chain_of(&fonts, name), defaults, "{name}");
    }
    assert_eq!(fonts.families[&FontFamily::Proportional], defaults);
    // Only one face present: the others reuse it before egui's fonts.
    let fonts = definitions_with(|name| (name == SEGOE).then(stand_in));
    assert_eq!(chain_of(&fonts, DIN_STRONG)[0], SEGOE);
    assert_eq!(chain_of(&fonts, DIN_LIGHT)[0], SEGOE);
}

#[test]
fn named_faces_are_used_only_after_install() {
    let ctx = egui::Context::default();
    assert_eq!(family(&ctx, Face::Strong), FontFamily::Proportional);
    install(&ctx);
    assert_eq!(family(&ctx, Face::Regular), FontFamily::Name(DIN.into()));
    assert_eq!(
        family(&ctx, Face::Strong),
        FontFamily::Name(DIN_STRONG.into())
    );
    assert_eq!(
        family(&ctx, Face::Light),
        FontFamily::Name(DIN_LIGHT.into())
    );
    // The installed families really resolve: laying out with them must not panic.
    let _ = ctx.run(egui::RawInput::default(), |ctx| {
        egui::CentralPanel::default().show(ctx, |ui| {
            for face in [Face::Regular, Face::Strong, Face::Light] {
                ui.label(egui::RichText::new("Render 3 · 41 s").font(font(ctx, face, 13.0)));
            }
        });
    });
}

#[test]
fn tracked_capitals_are_upper_case_and_spaced_by_the_em_fraction() {
    let job = tracked(
        "Depth rail",
        FontId::proportional(10.5),
        egui::Color32::WHITE,
        crate::studio_theme::scale::CAPS_TRACKING,
    );
    assert_eq!(job.text, "DEPTH RAIL");
    assert_eq!(job.sections.len(), 1);
    let spacing = job.sections[0].format.extra_letter_spacing;
    assert!((spacing - 10.5 * 0.13).abs() < 1e-6);
    let ctx = egui::Context::default();
    let _ = ctx.run(egui::RawInput::default(), |ctx| {
        let plain = ctx.fonts_mut(|fonts| {
            fonts
                .layout_no_wrap(
                    "DEPTH RAIL".into(),
                    FontId::proportional(10.5),
                    egui::Color32::WHITE,
                )
                .size()
                .x
        });
        let spaced = ctx.fonts_mut(|fonts| fonts.layout_job(job.clone()).size().x);
        assert!(
            spaced > plain + 8.0 * spacing,
            "tracking must widen the label: {plain} -> {spaced}"
        );
    });
}

#[cfg(windows)]
#[test]
fn installed_windows_faces_are_read_from_the_system_folder() {
    let fonts = definitions();
    for (name, path) in SYSTEM_FACES {
        assert_eq!(
            fonts.font_data.contains_key(name),
            std::path::Path::new(path).is_file(),
            "{name} must be read exactly when {path} exists"
        );
    }
}
