//! Studio 2 lettering (implementation plan 6.5). The faces are read from the
//! operating system's font folder at run time; font files are never
//! redistributed. egui 0.33 cannot choose a weight inside a variable font, so
//! Bahnschrift supplies its default (Regular) instance and Segoe UI Semibold
//! and Light supply the strong and light weights.
use eframe::egui::{self, FontData, FontDefinitions, FontFamily, FontId, text::LayoutJob};
use std::sync::OnceLock;

/// Labels, tracked capitals, figures and body text.
pub(crate) const DIN: &str = "din";
/// Titles and statements.
pub(crate) const DIN_STRONG: &str = "din-strong";
/// Large figures, 64 px and up.
pub(crate) const DIN_LIGHT: &str = "din-light";

#[allow(dead_code)] // Part of the Studio 2 API for the station agents (P3 to P7).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Face {
    Regular,
    Strong,
    Light,
}

const BAHNSCHRIFT: &str = "bahnschrift";
const SEGOE_SEMIBOLD: &str = "segoe-ui-semibold";
const SEGOE_LIGHT: &str = "segoe-ui-light";
const SEGOE: &str = "segoe-ui";

/// The four Windows faces and where they are installed.
const SYSTEM_FACES: [(&str, &str); 4] = [
    (BAHNSCHRIFT, "C:/Windows/Fonts/bahnschrift.ttf"),
    (SEGOE_SEMIBOLD, "C:/Windows/Fonts/seguisb.ttf"),
    (SEGOE_LIGHT, "C:/Windows/Fonts/segoeuil.ttf"),
    (SEGOE, "C:/Windows/Fonts/segoeui.ttf"),
];

/// Read each installed face once per process. Every context then shares the
/// same bytes instead of rereading a megabyte of TrueType per window or test.
fn system_face(key: &str) -> Option<&'static [u8]> {
    type Faces = Vec<(&'static str, Option<&'static [u8]>)>;
    static FACES: OnceLock<Faces> = OnceLock::new();
    FACES
        .get_or_init(|| {
            SYSTEM_FACES
                .iter()
                .map(|(name, path)| {
                    let bytes = if cfg!(windows) {
                        std::fs::read(path).ok()
                    } else {
                        None
                    };
                    (*name, bytes.map(|b| &*Box::leak(b.into_boxed_slice())))
                })
                .collect()
        })
        .iter()
        .find(|(name, _)| *name == key)
        .and_then(|(_, bytes)| *bytes)
}

/// Font definitions with the Studio families. `load` returns a face's bytes,
/// or `None` when it is not installed; every family then falls back to Segoe
/// UI and finally egui's bundled fonts, so nothing is ever missing a glyph.
pub(crate) fn definitions_with(load: impl Fn(&str) -> Option<&'static [u8]>) -> FontDefinitions {
    let mut fonts = FontDefinitions::default();
    let defaults = fonts
        .families
        .get(&FontFamily::Proportional)
        .cloned()
        .unwrap_or_default();
    let mut present = Vec::new();
    for (name, _) in SYSTEM_FACES {
        if let Some(bytes) = load(name) {
            fonts
                .font_data
                .insert(name.into(), FontData::from_static(bytes).into());
            present.push(name);
        }
    }
    let chain = |first: &str| -> Vec<String> {
        let mut chain: Vec<String> = Vec::new();
        let system = [first, SEGOE, BAHNSCHRIFT];
        let names = system
            .iter()
            .filter(|name| present.contains(name))
            .map(|name| (*name).to_owned())
            .chain(defaults.iter().cloned());
        for name in names {
            if !chain.contains(&name) {
                chain.push(name);
            }
        }
        chain
    };
    let regular = chain(BAHNSCHRIFT);
    fonts
        .families
        .insert(FontFamily::Proportional, regular.clone());
    fonts.families.insert(FontFamily::Name(DIN.into()), regular);
    fonts
        .families
        .insert(FontFamily::Name(DIN_STRONG.into()), chain(SEGOE_SEMIBOLD));
    fonts
        .families
        .insert(FontFamily::Name(DIN_LIGHT.into()), chain(SEGOE_LIGHT));
    fonts
}

pub(crate) fn definitions() -> FontDefinitions {
    definitions_with(system_face)
}

fn installed_id() -> egui::Id {
    egui::Id::new("studio-fonts-installed")
}

pub(crate) fn install(ctx: &egui::Context) {
    ctx.set_fonts(definitions());
    ctx.data_mut(|data| data.insert_temp(installed_id(), true));
}

/// The family for a face. Before `install`, the named families do not exist
/// and egui would panic on them, so every face is the default family then.
pub(crate) fn family(ctx: &egui::Context, face: Face) -> FontFamily {
    let installed = ctx
        .data(|data| data.get_temp::<bool>(installed_id()))
        .unwrap_or(false);
    match face {
        _ if !installed => FontFamily::Proportional,
        Face::Regular => FontFamily::Name(DIN.into()),
        Face::Strong => FontFamily::Name(DIN_STRONG.into()),
        Face::Light => FontFamily::Name(DIN_LIGHT.into()),
    }
}

pub(crate) fn font(ctx: &egui::Context, face: Face, size: f32) -> FontId {
    FontId::new(size, family(ctx, face))
}

/// Tracked capitals: the text upper-cased and spaced by `tracking` em.
pub(crate) fn tracked(text: &str, font: FontId, color: egui::Color32, tracking: f32) -> LayoutJob {
    let mut job = LayoutJob::default();
    append_tracked(&mut job, text, font, color, tracking);
    job
}

pub(crate) fn append_tracked(
    job: &mut LayoutJob,
    text: &str,
    font: FontId,
    color: egui::Color32,
    tracking: f32,
) {
    let spacing = font.size * tracking;
    job.append(
        &text.to_uppercase(),
        0.0,
        egui::TextFormat {
            font_id: font,
            color,
            extra_letter_spacing: spacing,
            ..Default::default()
        },
    );
}

#[cfg(test)]
#[path = "studio-fonts-tests.rs"]
mod tests;
