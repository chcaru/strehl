use super::*;

fn rgb(color: Color32) -> u32 {
    (u32::from(color.r()) << 16) | (u32::from(color.g()) << 8) | u32::from(color.b())
}

/// Appendix A, row by row: bg panel raised control line line2 ink ink2 ink3
/// accent accent_ink ok warn bad info plane surround.
#[test]
fn every_theme_matches_appendix_a() {
    let table: [(ThemeName, [u32; 17]); 3] = [
        (
            ThemeName::Graphite,
            [
                0x0b0b0c, 0x111112, 0x171718, 0x1e1e20, 0x232326, 0x37373c, 0xe9e6de, 0xa19f98,
                0x807e77, 0xe6b450, 0x171204, 0xa9c779, 0xf08a4b, 0xe5604c, 0x8ab4e8, 0x55d6c4,
                0x0e0e0f,
            ],
        ),
        (
            ThemeName::Instrument,
            [
                0x10141c, 0x141821, 0x1a1f29, 0x212835, 0x272e3a, 0x3a4353, 0xe2e0d8, 0x99a2ae,
                0x7c8799, 0xe6b450, 0x171204, 0xa9c779, 0xf08a4b, 0xe5604c, 0x8ab4e8, 0x55d6c4,
                0x0c0f15,
            ],
        ),
        (
            ThemeName::Lightbox,
            [
                0xe7e6e1, 0xf3f2ee, 0xfaf9f6, 0xe9e7e1, 0xd8d5cd, 0xb9b5ab, 0x19191b, 0x55544f,
                0x6f6d66, 0xa46300, 0xffffff, 0x4f7d2c, 0xb9520c, 0xb83224, 0x2a66ad, 0x0c8a7c,
                0x2a2a2b,
            ],
        ),
    ];
    for (theme, expected) in table {
        let t = theme.tokens();
        let actual = [
            t.bg,
            t.panel,
            t.raised,
            t.control,
            t.line,
            t.line2,
            t.ink,
            t.ink2,
            t.ink3,
            t.accent,
            t.accent_ink,
            t.ok,
            t.warn,
            t.bad,
            t.info,
            t.plane,
            t.surround,
        ]
        .map(rgb);
        assert_eq!(actual, expected, "{theme:?}");
        assert_eq!(t.light, theme == ThemeName::Lightbox);
        assert_eq!(
            t.spectrum,
            if t.light {
                SPECTRUM_LIGHT
            } else {
                SPECTRUM_DARK
            }
        );
        // The soft accent is the accent at 12 % (10 % on paper), premultiplied.
        let alpha = f32::from(t.accent_soft.a()) / 255.0;
        assert!((alpha - if t.light { 0.10 } else { 0.12 }).abs() < 0.005);
        assert!((f32::from(t.accent_soft.r()) - f32::from(t.accent.r()) * alpha).abs() <= 1.0);
    }
    // On Lightbox, text over the dark surround keeps light inks.
    assert_eq!(LIGHTBOX.canvas_ink.map(rgb), [0xe9e6de, 0xa19f98, 0x96948d]);
    assert_eq!(LIGHTBOX.canvas_line.map(rgb), [0x3a3a3d, 0x57575c]);
    assert_eq!(
        DETAIL_SIZES,
        [2, 4, 8, 16, 32, 64, 128, 256],
        "the spectrum is indexed by detail size"
    );
}

fn luminance(color: Color32) -> f32 {
    let linear = |c: u8| {
        let c = f32::from(c) / 255.0;
        if c <= 0.04045 {
            c / 12.92
        } else {
            ((c + 0.055) / 1.055).powf(2.4)
        }
    };
    0.2126 * linear(color.r()) + 0.7152 * linear(color.g()) + 0.0722 * linear(color.b())
}
fn contrast(a: Color32, b: Color32) -> f32 {
    let (x, y) = (luminance(a), luminance(b));
    (x.max(y) + 0.05) / (x.min(y) + 0.05)
}

#[test]
fn the_faintest_ink_stays_readable_on_panels_and_the_surround_inks_on_the_surround() {
    for theme in ThemeName::ALL {
        let t = theme.tokens();
        // Appendix A states the 4.5:1 floor on panels. MEASURED: Lightbox ink3
        // on its darker bg is 4.14:1, so faint text belongs on panels there.
        assert!(
            contrast(t.ink3, t.panel) >= 4.5,
            "{theme:?} ink3 {:.2}:1",
            contrast(t.ink3, t.panel)
        );
        assert!(contrast(t.ink, t.panel) >= 12.0, "{theme:?} ink");
        assert!(
            contrast(t.canvas_ink[2], t.surround) >= 4.5,
            "{theme:?} canvas ink {:.2}:1",
            contrast(t.canvas_ink[2], t.surround)
        );
        // A failure must not read as a warning or as the accent.
        assert_ne!(t.bad, t.warn);
        assert_ne!(t.bad, t.accent);
    }
}

#[test]
fn names_round_trip_and_unknown_names_are_rejected() {
    for theme in ThemeName::ALL {
        assert_eq!(ThemeName::parse(theme.key()), Some(theme));
        assert_eq!(ThemeName::parse(&theme.label().to_uppercase()), Some(theme));
        let json = serde_json::to_string(&theme).unwrap();
        assert_eq!(json, format!("\"{}\"", theme.key()));
    }
    assert_eq!(ThemeName::parse("navy"), None);
    assert_eq!(ThemeName::default(), ThemeName::Graphite);
    assert_eq!(Surround::Theme.color(GRAPHITE.surround), GRAPHITE.surround);
    assert_eq!(Surround::Black.color(GRAPHITE.surround), Color32::BLACK);
}

#[test]
fn applying_a_theme_sets_context_tokens_and_the_real_egui_style() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    assert_eq!(theme_name(&ctx), ThemeName::Graphite);
    assert_eq!(tokens(&ctx), GRAPHITE);
    assert_eq!(ctx.style().visuals.panel_fill, GRAPHITE.panel);
    apply(&ctx, ThemeName::Lightbox, Surround::Black, true);
    let t = tokens(&ctx);
    assert_eq!(t.panel, LIGHTBOX.panel);
    assert_eq!(t.surround, Color32::BLACK, "the surround preference wins");
    assert!(reduced_motion(&ctx));
    let style = ctx.style();
    assert_eq!(style.visuals.panel_fill, LIGHTBOX.panel);
    assert_eq!(style.visuals.override_text_color, Some(LIGHTBOX.ink));
    assert_eq!(
        style.animation_time, 0.0,
        "reduced motion removes animation"
    );
    // The theme survives a second install, as on a display-scale change.
    crate::theme::install(&ctx);
    assert_eq!(theme_name(&ctx), ThemeName::Lightbox);
    assert_eq!(ctx.style().visuals.panel_fill, LIGHTBOX.panel);
}

#[test]
fn a_scoped_theme_draws_its_content_and_then_restores_the_current_one() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    apply(&ctx, ThemeName::Lightbox, Surround::Theme, false);
    let mut inside = None;
    let output = ctx.run(egui::RawInput::default(), |ctx| {
        scoped(ctx, ThemeName::Graphite, || {
            inside = Some((tokens(ctx), ctx.style().visuals.panel_fill));
            egui::CentralPanel::default().show(ctx, |ui| {
                ui.label("Legacy pane");
            });
        });
    });
    let (scoped_tokens, scoped_fill) = inside.unwrap();
    assert_eq!(scoped_tokens.panel, GRAPHITE.panel);
    assert_eq!(scoped_fill, GRAPHITE.panel);
    assert_eq!(tokens(&ctx).panel, LIGHTBOX.panel);
    assert_eq!(ctx.style().visuals.panel_fill, LIGHTBOX.panel);
    let label = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if text.galley.text() == "Legacy pane" => {
                Some(text.fallback_color)
            }
            _ => None,
        })
        .expect("the scoped panel must paint");
    assert_eq!(label, GRAPHITE.ink, "legacy text keeps its light ink");
}

#[test]
fn styles_are_built_once_per_theme_and_scale() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let first = style(&ctx, ThemeName::Instrument, false);
    let second = style(&ctx, ThemeName::Instrument, false);
    assert!(Arc::ptr_eq(&first, &second));
    assert!(!Arc::ptr_eq(
        &first,
        &style(&ctx, ThemeName::Graphite, false)
    ));
}
