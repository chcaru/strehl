//! The Export station (implementation plan 7.6; mockup `screens/export.html`)
//! as self-contained parts for the Studio 2 shell: the presets list with its
//! check boxes, the selected preset's editor, the "In every file" switches,
//! name and place, the export history under the photograph, and the batch
//! that writes every ticked preset through one job, a phase per file.
//!
//! Files are never overwritten: names come from `available_path` before the
//! batch starts, and every encoder publishes with `new_file_checked`.
#![allow(
    dead_code,
    reason = "the Studio 2 shell (P1) composes these parts; tests use them until then"
)]
use crate::develop_station::style::{self, ButtonKind, Mark, StudioPalette};
use crate::export_presets::{
    ExportPreset, ImagePreset, Library, NameFields, PresetOutput, available_path, expand_name,
};
use anyhow::{Context, Result, ensure};
use eframe::egui::{self, Align2, CornerRadius, Rect, Sense, Ui};
use std::{
    io::Write,
    path::{Path, PathBuf},
    sync::{
        Arc,
        atomic::{AtomicBool, AtomicU8, AtomicUsize, Ordering},
    },
};
use strehl_edit::{
    ExportDateTime, ExportFormat, ExportSettings, OutputColorSpace, OutputSharpening, Resize,
    ResizeFilter,
};

// ------------------------------------------------------------------ summaries

fn format_name(format: ExportFormat) -> &'static str {
    match format {
        ExportFormat::Avif => "AVIF",
        ExportFormat::Tiff => "TIFF",
        ExportFormat::Png => "PNG",
        ExportFormat::Jpeg => "JPEG",
    }
}

fn space_name(space: OutputColorSpace, hdr: bool) -> &'static str {
    match (space, hdr) {
        (OutputColorSpace::Srgb, _) => "sRGB",
        (OutputColorSpace::DisplayP3, _) => "Display P3",
        (OutputColorSpace::Rec2020, true) => "Rec.2020 PQ",
        (OutputColorSpace::Rec2020, false) => "Rec.2020",
    }
}

/// The preset's one line, for example `JPEG · sRGB · 2560 px long edge · quality 90`.
pub(crate) fn preset_summary(output: &PresetOutput) -> String {
    match output {
        PresetOutput::Archive => "Linear master and the develop recipe".into(),
        PresetOutput::Image(image) => {
            let s = &image.settings;
            let mut parts = vec![
                match s.format {
                    ExportFormat::Tiff => "TIFF 16-bit".into(),
                    format => format_name(format).to_owned(),
                },
                space_name(s.color_space, s.hdr).to_owned(),
                s.resize.map_or("full size".into(), |r| {
                    format!("{} px long edge", r.long_edge)
                }),
            ];
            match s.format {
                ExportFormat::Jpeg => parts.push(format!("quality {}", s.quality)),
                ExportFormat::Avif => parts.push("10-bit".into()),
                _ => {}
            }
            parts.join(" · ")
        }
    }
}

/// Output size in pixels for a photograph of `size` (after its crop).
pub(crate) fn output_size(output: &PresetOutput, size: [u32; 2]) -> [u32; 2] {
    match output {
        PresetOutput::Image(image) => image
            .settings
            .resize
            .and_then(|r| r.target(size))
            .unwrap_or(size),
        PresetOutput::Archive => size,
    }
}

/// AVIF bytes per pixel against quality: (quality, SDR sRGB, HDR Rec.2020
/// PQ), measured at encoder effort 4 on the 7032 x 4688 weevil with its own
/// recipe (g-develop note). Other efforts measured -6 % to +17 % of these
/// (effort 0 largest); the estimate leaves effort out.
const AVIF_BYTES_PER_PIXEL: [(u8, f64, f64); 6] = [
    (50, 0.0595, 0.0517),
    (70, 0.1144, 0.1763),
    (85, 0.2019, 0.4209),
    (90, 0.2802, 0.6340),
    (95, 0.4814, 1.0145),
    (100, 1.1004, 1.7947),
];

/// AVIF encode (with development) seconds per megapixel at encoder effort
/// 4: (quality, SDR, HDR), measured with the sizes above. HDR quality 100 is
/// the mean of two runs (39.04 s and 33.43 s).
const AVIF_SECONDS_PER_MP: [(u8, f64, f64); 6] = [
    (50, 0.3868, 0.4332),
    (70, 0.4620, 0.5897),
    (85, 0.5266, 0.6689),
    (90, 0.5964, 0.7220),
    (95, 0.6853, 0.9774),
    (100, 1.0766, 1.0992),
];

/// Encode time against effort, relative to effort 4: geometric means of the
/// ratios measured at SDR quality 85, HDR quality 85 and HDR quality 100.
const AVIF_EFFORT_TIME: [(u8, f64); 3] = [(0, 0.3455), (4, 1.0), (8, 4.851)];

/// Straight lines through `points` in log value, continued past either end
/// with the nearest segment's slope.
fn log_interpolate(points: &[(f64, f64)], x: f64) -> f64 {
    let i = (1..points.len())
        .find(|&i| x <= points[i].0)
        .unwrap_or(points.len() - 1);
    let ((x0, y0), (x1, y1)) = (points[i - 1], points[i]);
    let (l0, l1) = (y0.ln(), y1.ln());
    (l0 + (x - x0) * (l1 - l0) / (x1 - x0)).exp()
}

/// Bytes per pixel of an AVIF at `quality`: straight lines between the
/// measurements in log size (size grows geometrically as the quantizer
/// falls), the first segment's slope below quality 50.
pub(crate) fn avif_bytes_per_pixel(quality: u8, hdr: bool) -> f64 {
    let points =
        AVIF_BYTES_PER_PIXEL.map(|(q, sdr, high)| (f64::from(q), if hdr { high } else { sdr }));
    log_interpolate(&points, f64::from(quality.clamp(1, 100)))
}

/// Seconds per megapixel to develop and encode an AVIF: the quality table
/// at effort 4 times the effort factor (both interpolated in log time).
pub(crate) fn avif_seconds_per_mp(quality: u8, hdr: bool, effort: u8) -> f64 {
    let quality_points =
        AVIF_SECONDS_PER_MP.map(|(q, sdr, high)| (f64::from(q), if hdr { high } else { sdr }));
    let effort_points = AVIF_EFFORT_TIME.map(|(e, factor)| (f64::from(e), factor));
    log_interpolate(&quality_points, f64::from(quality.clamp(1, 100)))
        * log_interpolate(&effort_points, f64::from(effort.min(10)))
}

/// A rough file size: bytes per pixel measured on the owner's 33 MP weevil
/// (P7 model note: JPEG q90 0.39, PNG 16-bit P3 4.2, TIFF 16-bit 6.0; the
/// master 12; AVIF from `AVIF_BYTES_PER_PIXEL`).
pub(crate) fn estimate_bytes(output: &PresetOutput, size: [u32; 2]) -> u64 {
    let [w, h] = output_size(output, size);
    let pixels = f64::from(w) * f64::from(h);
    let per_pixel = match output {
        PresetOutput::Archive => 12.0,
        PresetOutput::Image(image) => match image.settings.format {
            ExportFormat::Jpeg => 0.39 * f64::from(image.settings.quality) / 90.0,
            ExportFormat::Avif => avif_bytes_per_pixel(image.settings.quality, image.settings.hdr),
            ExportFormat::Png => 4.2,
            ExportFormat::Tiff => 6.0,
        },
    };
    (pixels * per_pixel) as u64
}

pub(crate) fn human_bytes(bytes: u64) -> String {
    let b = bytes as f64;
    if b >= 1e9 {
        format!("{:.1} GB", b / 1e9)
    } else if b >= 1e6 {
        format!("{:.1} MB", b / 1e6).replace(".0 MB", " MB")
    } else {
        format!("{:.0} KB", (b / 1e3).max(1.0))
    }
}

/// Seconds for a batch, from encoder times measured on the 33 MP master
/// (the SDR formats under 2 s). AVIF time depends on quality, range and
/// encoder effort (`avif_seconds_per_mp`; g-develop note).
pub(crate) fn estimate_seconds(outputs: &[&PresetOutput], size: [u32; 2]) -> f64 {
    outputs
        .iter()
        .map(|output| {
            let [w, h] = output_size(output, size);
            let mp = f64::from(w) * f64::from(h) / 1e6;
            match output {
                PresetOutput::Archive => 0.02 * mp,
                PresetOutput::Image(image) => match image.settings.format {
                    ExportFormat::Avif => {
                        let s = &image.settings;
                        mp * avif_seconds_per_mp(s.quality, s.hdr, effort_of(s.speed))
                    }
                    _ => 0.05 * mp + 0.2,
                },
            }
        })
        .sum()
}

/// Encoder effort as the Export station shows it: 0 fastest, 10 slowest.
/// The settings keep the AV1 speed (10 fastest), so effort is `10 - speed`;
/// the default speed 6 is effort 4 (the export pane's "Encoder effort").
pub(crate) fn effort_of(speed: u8) -> u8 {
    10 - speed.min(10)
}

pub(crate) fn speed_of(effort: u8) -> u8 {
    10 - effort.min(10)
}

// ------------------------------------------------------------------- history

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum HistoryStatus {
    Checking,
    Unchanged,
    /// The file is still there but its bytes are not the ones written.
    Changed,
    Missing,
    /// Written from a version older than the current edit.
    Older,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct HistoryRow {
    pub id: String,
    pub path: PathBuf,
    pub preset: String,
    pub size: String,
    pub version: String,
    pub when: String,
    pub status: HistoryStatus,
}

// ---------------------------------------------------------------------- view

/// What the Export parts read; built by the caller from state it holds.
pub(crate) struct ExportView<'a> {
    pub palette: &'a StudioPalette,
    pub library: &'a Library,
    /// The open photograph's file name: its own, else the template.
    pub name: &'a str,
    pub fields: NameFields<'a>,
    pub destination: Option<&'a Path>,
    /// Size of the developed photograph after its crop.
    pub size: [u32; 2],
    pub has_scale_bar: bool,
    pub calibrated: bool,
    pub hdr_photo: bool,
    pub history: &'a [HistoryRow],
    pub batch: Option<BatchSnapshot>,
    /// Why an export cannot start now (a look still calculating, a version
    /// being saved); the press then says so instead of doing nothing.
    pub blocker: Option<&'a str>,
    /// What the last action came to, at the head of the inspector.
    pub feedback: Option<Feedback<'a>>,
    /// For example: a depth repair is pending; files use the last finished pixels.
    pub note: Option<&'a str>,
    /// An independent-views session can leave as a view bundle; `true`
    /// while one is being written.
    pub view_bundle: Option<bool>,
    /// What "Copyright and description" writes.
    pub words: Words<'a>,
}

/// The text "Copyright and description" writes: the owner's artist and
/// copyright (Preferences, `studio.json`) and this photograph's description
/// (the catalog). Presets carry only the switch.
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub(crate) struct Words<'a> {
    pub artist: &'a str,
    pub copyright: &'a str,
    pub description: &'a str,
}

/// One of the three texts, as edited in Export.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum WordsField {
    Artist,
    Copyright,
    Description,
}

/// The last batch's result or an error, in words.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct Feedback<'a> {
    pub ok: bool,
    pub text: &'a str,
    /// Offer Open folder (the files went to this subject's folder).
    pub folder: bool,
}

/// Panel state that is not the library itself.
#[derive(Clone, Debug, Default)]
pub(crate) struct ExportPanel {
    /// The preset shown in the editor (and in the canvas preview).
    pub selected: Option<String>,
    pub template_draft: Option<String>,
    /// A words field's text while it has the keyboard; `None` otherwise, so
    /// the field always shows the current text (another photograph's
    /// description never lingers).
    pub words_draft: Option<(WordsField, String)>,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) enum ExportIntent {
    Tick(String, bool),
    Select(String),
    Edit(String, PresetOutput),
    NewPreset,
    SetTemplate(String),
    /// This photograph's own file name; `None` goes back to the template.
    SetName(Option<String>),
    ChangeDestination,
    OpenFolder,
    ExportTicked,
    CancelBatch,
    Reveal(PathBuf),
    CopyPath(PathBuf),
    ExportAgain(String),
    /// Copy every bound photograph, master, focus map and receipt.
    ExportViewBundle,
    CancelViewBundle,
    DismissFeedback,
    /// Artist or copyright (into Preferences) or this photograph's
    /// description (into the catalog), as typed.
    SetWords(WordsField, String),
}

/// Sharpening choices "for the size". `Screen` is the conservative default
/// measured against the flat-ROI control (engineering ledger rule 9).
pub(crate) fn sharpen_choices() -> [(&'static str, Option<OutputSharpening>); 3] {
    [
        ("Off", None),
        ("Screen", Some(OutputSharpening::default())),
        (
            "Print",
            Some(OutputSharpening {
                amount: 0.4,
                radius_px: 1.2,
                ..OutputSharpening::default()
            }),
        ),
    ]
}

/// The inspector's body (presets, the selected preset, "In every file",
/// name and place), padded and scrolling, for the shell's inspector body.
pub(crate) fn inspector_body(
    ui: &mut Ui,
    panel: &mut ExportPanel,
    view: &ExportView<'_>,
) -> Vec<ExportIntent> {
    let mut intents = Vec::new();
    let rect = ui.max_rect();
    let body = Rect::from_min_max(
        egui::pos2(rect.left() + 16.0, rect.top() + 14.0),
        egui::pos2(rect.right() - 16.0, rect.bottom() - 8.0),
    );
    if panel
        .selected
        .as_ref()
        .is_none_or(|id| !view.library.presets.iter().any(|p| &p.id == id))
    {
        panel.selected = view.library.ticked().next().map(|p| p.id.clone());
    }
    let mut body_ui = ui.new_child(
        egui::UiBuilder::new()
            .max_rect(body)
            .layout(egui::Layout::top_down(egui::Align::Min)),
    );
    egui::ScrollArea::vertical()
        .id_salt("export-inspector")
        .auto_shrink([false, false])
        .show(&mut body_ui, |ui| {
            ui.spacing_mut().item_spacing.y = 8.0;
            if let Some(feedback) = view.feedback {
                feedback_line(ui, view.palette, feedback, &mut intents);
            }
            presets_list(ui, panel, view, &mut intents);
            if let Some(preset) = panel
                .selected
                .as_ref()
                .and_then(|id| view.library.presets.iter().find(|p| &p.id == id))
            {
                preset_editor(ui, view, preset, &mut intents);
            }
            every_file(ui, panel, view, &mut intents);
            name_and_place(ui, panel, view, &mut intents);
            if let Some(running) = view.view_bundle {
                view_bundle(ui, view.palette, running, &mut intents);
            }
        });
    intents
}

/// The foot, into the shell's footer row: "Export N files" with the time it
/// will take, or the running batch with Cancel. Ctrl+E exports the ticked.
pub(crate) fn inspector_footer(ui: &mut Ui, view: &ExportView<'_>) -> Vec<ExportIntent> {
    let pal = view.palette;
    let mut intents = Vec::new();
    let ticked: Vec<&PresetOutput> = view.library.ticked().map(|p| &p.output).collect();
    if let Some(batch) = &view.batch {
        let text = batch.caption();
        let width = (ui.available_width() - 80.0).max(80.0);
        let (rect, _) = ui.allocate_exact_size(egui::vec2(width, 28.0), Sense::hover());
        style::paint_text(
            ui.painter(),
            rect.left_center(),
            Align2::LEFT_CENTER,
            &text,
            12.5,
            pal.ink,
        );
        let bar = Rect::from_min_max(
            egui::pos2(rect.left(), rect.bottom() - 2.0),
            rect.right_bottom(),
        );
        ui.painter()
            .rect_filled(bar, CornerRadius::ZERO, pal.line_2);
        ui.painter().rect_filled(
            Rect::from_min_size(bar.min, egui::vec2(bar.width() * batch.fraction(), 2.0)),
            CornerRadius::ZERO,
            pal.accent,
        );
        if style::button(
            ui,
            pal,
            "Cancel",
            ButtonKind::Plain,
            egui::vec2(72.0, 28.0),
            !batch.cancelling,
        )
        .clicked()
        {
            intents.push(ExportIntent::CancelBatch);
        }
    } else {
        // Every press answers: it starts the batch, opens the folder dialog,
        // or (when something must finish first) says what in the inspector.
        let count = ticked.len();
        let no_folder = view.destination.is_none() && count > 0;
        let label = match count {
            0 => "Tick a preset to export".to_owned(),
            _ if no_folder => "Choose a folder…".to_owned(),
            1 => "Export 1 file".to_owned(),
            n => format!("Export {n} files"),
        };
        let estimate = format!(
            "about {}",
            format_seconds(estimate_seconds(&ticked, view.size))
        );
        let estimate_width = 64.0;
        let width = (ui.available_width() - estimate_width - 8.0).max(80.0);
        let hover = if no_folder {
            "Choose where this subject's files go, then export"
        } else {
            view.blocker
                .unwrap_or("Ctrl+E · existing files are never overwritten")
        };
        if style::button(
            ui,
            pal,
            &label,
            ButtonKind::Primary,
            egui::vec2(width, 28.0),
            count > 0,
        )
        .on_hover_text(hover)
        .clicked()
        {
            intents.push(if no_folder {
                ExportIntent::ChangeDestination
            } else {
                ExportIntent::ExportTicked
            });
        }
        style::text(ui, &estimate, style::SMALL, pal.ink_3);
    }
    if ui.input(|i| i.modifiers.command && i.key_pressed(egui::Key::E))
        && view.batch.is_none()
        && view.destination.is_some()
    {
        intents.push(ExportIntent::ExportTicked);
    }
    intents
}

/// The last batch's result (with Open folder) or an error, with Dismiss.
fn feedback_line(
    ui: &mut Ui,
    pal: &StudioPalette,
    feedback: Feedback<'_>,
    intents: &mut Vec<ExportIntent>,
) {
    let links: &[&str] = if feedback.folder {
        &["Open folder", "Dismiss"]
    } else {
        &["Dismiss"]
    };
    let kind = if feedback.ok { Mark::Ok } else { Mark::Warn };
    match style::notice_line(ui, pal, kind, feedback.text, links) {
        Some(0) if feedback.folder => intents.push(ExportIntent::OpenFolder),
        Some(_) => intents.push(ExportIntent::DismissFeedback),
        None => {}
    }
}

/// Body and foot together, for callers without the shell (tests).
pub(crate) fn inspector(
    ui: &mut Ui,
    panel: &mut ExportPanel,
    view: &ExportView<'_>,
) -> Vec<ExportIntent> {
    let pal = view.palette;
    let full = ui.available_rect_before_wrap();
    ui.painter()
        .rect_filled(full, CornerRadius::ZERO, pal.panel);
    let foot_height = 53.0;
    let body = Rect::from_min_max(
        full.min,
        egui::pos2(full.right(), full.bottom() - foot_height),
    );
    let mut body_ui = ui.new_child(egui::UiBuilder::new().max_rect(body));
    let mut intents = inspector_body(&mut body_ui, panel, view);
    let foot = Rect::from_min_max(
        egui::pos2(full.left(), full.bottom() - foot_height),
        full.max,
    );
    style::hairline(ui.painter(), foot.left_top(), foot.right_top(), pal.line);
    let mut foot_ui = ui.new_child(
        egui::UiBuilder::new()
            .max_rect(foot.shrink2(egui::vec2(16.0, 12.0)))
            .layout(egui::Layout::left_to_right(egui::Align::Center)),
    );
    foot_ui.spacing_mut().item_spacing.x = 8.0;
    intents.extend(inspector_footer(&mut foot_ui, view));
    ui.advance_cursor_after_rect(full);
    intents
}

pub(crate) fn format_seconds(seconds: f64) -> String {
    if seconds < 60.0 {
        format!("{} s", (seconds.round() as u64).max(1))
    } else {
        format!("{} min", (seconds / 60.0).round() as u64)
    }
}

fn presets_list(
    ui: &mut Ui,
    panel: &mut ExportPanel,
    view: &ExportView<'_>,
    intents: &mut Vec<ExportIntent>,
) {
    let pal = view.palette;
    ui.horizontal(|ui| {
        style::caps(ui, "Presets", style::CAPS, pal.ink_3);
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            if style::link(ui, pal, "New preset…", false).clicked() {
                intents.push(ExportIntent::NewPreset);
            }
        });
    });
    for preset in &view.library.presets {
        let width = ui.available_width();
        let (rect, response) = ui.allocate_exact_size(egui::vec2(width, 66.0), Sense::click());
        let on = panel.selected.as_ref() == Some(&preset.id);
        let painter = ui.painter();
        if on {
            painter.rect_filled(
                Rect::from_min_size(rect.min, egui::vec2(2.0, rect.height())),
                CornerRadius::ZERO,
                pal.accent,
            );
        } else if response.hovered() {
            painter.rect_filled(rect, CornerRadius::ZERO, pal.raised);
        }
        style::hairline(painter, rect.left_bottom(), rect.right_bottom(), pal.line);
        let left = rect.left() + if on { 10.0 } else { 0.0 };
        let check =
            Rect::from_min_size(egui::pos2(left, rect.top() + 13.0), egui::vec2(14.0, 14.0));
        style::paint_checkbox(painter, check, pal, preset.enabled);
        let text = left + 28.0;
        style::paint_text(
            painter,
            egui::pos2(text, rect.top() + 18.0),
            Align2::LEFT_CENTER,
            &preset.name,
            style::BODY,
            pal.ink,
        );
        style::paint_text(
            painter,
            egui::pos2(text, rect.top() + 36.0),
            Align2::LEFT_CENTER,
            &preset_summary(&preset.output),
            style::SMALL,
            pal.ink_2,
        );
        let file = expand_name(
            view.name,
            &NameFields {
                preset: &preset.name,
                ..view.fields.clone()
            },
        )
        .map(|stem| {
            format!(
                "{stem}.{} · {}",
                preset.output.extension(),
                human_bytes(estimate_bytes(&preset.output, view.size))
            )
        })
        .unwrap_or_else(|_| "the name template needs attention".into());
        painter.text(
            egui::pos2(text, rect.top() + 53.0),
            Align2::LEFT_CENTER,
            file,
            egui::FontId::monospace(11.0),
            pal.ink_3,
        );
        let check_hit = ui.interact(
            check.expand(6.0),
            ui.id().with(("tick", &preset.id)),
            Sense::click(),
        );
        if check_hit.clicked() {
            intents.push(ExportIntent::Tick(preset.id.clone(), !preset.enabled));
        } else if response.clicked() {
            panel.selected = Some(preset.id.clone());
            intents.push(ExportIntent::Select(preset.id.clone()));
        }
    }
}

fn row(ui: &mut Ui, pal: &StudioPalette, label: &str, add: impl FnOnce(&mut Ui)) {
    ui.horizontal(|ui| {
        ui.set_min_height(24.0);
        style::text(ui, label, style::BODY, pal.ink_2);
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), add);
    });
}

fn preset_editor(
    ui: &mut Ui,
    view: &ExportView<'_>,
    preset: &ExportPreset,
    intents: &mut Vec<ExportIntent>,
) {
    let pal = view.palette;
    style::sect(
        ui,
        pal,
        &format!("{} preset", preset.name),
        Some("changes are saved to the preset"),
    );
    let PresetOutput::Image(image) = &preset.output else {
        style::text(
            ui,
            "Copies the scene-linear master and the develop recipe beside each other.",
            style::SMALL,
            pal.ink_2,
        );
        return;
    };
    let mut next = image.clone();
    let s = &mut next.settings;
    let formats = [
        ExportFormat::Avif,
        ExportFormat::Tiff,
        ExportFormat::Png,
        ExportFormat::Jpeg,
    ];
    row(ui, pal, "Format", |ui| {
        // Right-to-left: list in reverse so AVIF stays first on screen.
        if let Some(i) = style::seg(
            ui,
            pal,
            &["AVIF", "TIFF", "PNG", "JPEG"],
            formats.iter().position(|f| *f == s.format),
        ) {
            s.format = formats[i];
            s.hdr = s.format == ExportFormat::Avif && s.hdr && view.hdr_photo;
            if s.format != ExportFormat::Tiff {
                s.embed_recipe = false;
            }
        }
    });
    let spaces = [
        OutputColorSpace::Srgb,
        OutputColorSpace::DisplayP3,
        OutputColorSpace::Rec2020,
    ];
    row(ui, pal, "Colour space", |ui| {
        if let Some(i) = style::seg(
            ui,
            pal,
            &["sRGB", "P3", "Rec.2020"],
            spaces.iter().position(|c| *c == s.color_space),
        ) {
            s.color_space = spaces[i];
        }
    });
    if s.format == ExportFormat::Avif && view.hdr_photo {
        row(ui, pal, "Range", |ui| {
            if let Some(i) = style::seg(ui, pal, &["HDR", "SDR"], Some(usize::from(!s.hdr))) {
                s.hdr = i == 0;
            }
        });
    }
    row(ui, pal, "Size", |ui| {
        let mut long = s.resize.map(|r| r.long_edge).unwrap_or(0);
        let response = ui.add(
            egui::DragValue::new(&mut long)
                .range(0..=65_535)
                .custom_formatter(|v, _| {
                    if v < 16.0 {
                        "Full size".into()
                    } else {
                        format!("Long edge {v:.0} px")
                    }
                }),
        );
        if response.changed() {
            s.resize = (long >= 16).then_some(Resize {
                long_edge: long,
                filter: s.resize.map_or(ResizeFilter::Mitchell, |r| r.filter),
            });
        }
    });
    let choices = sharpen_choices();
    row(ui, pal, "Sharpen for the size", |ui| {
        let current = choices.iter().position(|(_, c)| *c == s.sharpen);
        if let Some(i) = style::seg(ui, pal, &["Off", "Screen", "Print"], current) {
            s.sharpen = choices[i].1;
        }
    });
    if matches!(s.format, ExportFormat::Jpeg | ExportFormat::Avif) {
        row(ui, pal, "Quality", |ui| {
            let mut q = s.quality;
            if ui
                .add(egui::DragValue::new(&mut q).range(1..=100))
                .changed()
            {
                s.quality = q;
            }
        });
    }
    if s.format == ExportFormat::Avif {
        // The AV1 encoder's time against compression, separate from quality:
        // effort is 10 - speed, as in the export pane before Studio 2.
        row(ui, pal, "Encoder effort", |ui| {
            let mut effort = effort_of(s.speed);
            if ui
                .add(egui::DragValue::new(&mut effort).range(0..=10).speed(0.05))
                .on_hover_text(
                    "0 is the fastest encode, 10 the slowest. Quality is set separately.",
                )
                .changed()
            {
                s.speed = speed_of(effort);
            }
        });
        let seconds = estimate_seconds(&[&PresetOutput::Image(next.clone())], view.size);
        style::text(
            ui,
            &format!(
                "About {} for this photograph. Less effort finishes sooner; more searches longer and can compress better.",
                format_seconds(seconds)
            ),
            style::SMALL,
            pal.ink_3,
        );
    }
    if next != *image {
        intents.push(ExportIntent::Edit(
            preset.id.clone(),
            PresetOutput::Image(next),
        ));
    }
}

fn every_file(
    ui: &mut Ui,
    panel: &mut ExportPanel,
    view: &ExportView<'_>,
    intents: &mut Vec<ExportIntent>,
) {
    let pal = view.palette;
    style::sect(ui, pal, "In every file", None);
    let images: Vec<(&ExportPreset, &ImagePreset)> = view
        .library
        .ticked()
        .filter_map(|p| match &p.output {
            PresetOutput::Image(image) => Some((p, image)),
            PresetOutput::Archive => None,
        })
        .collect();
    let all =
        |f: &dyn Fn(&ImagePreset) -> bool| !images.is_empty() && images.iter().all(|(_, i)| f(i));
    let mut set = |f: &dyn Fn(&mut ImagePreset, bool), on: bool| {
        for (preset, image) in &images {
            let mut next = (*image).clone();
            f(&mut next, on);
            if &next != *image {
                intents.push(ExportIntent::Edit(
                    preset.id.clone(),
                    PresetOutput::Image(next),
                ));
            }
        }
    };
    let bar_on = all(&|i| i.settings.scale_bar);
    let option = |ui: &mut Ui, on: bool, enabled: bool, label: &str, aside: &str| -> bool {
        let mut clicked = false;
        ui.horizontal(|ui| {
            ui.set_min_height(26.0);
            ui.add_enabled_ui(enabled, |ui| {
                clicked = style::toggle(ui, pal, on).clicked();
            });
            style::text(
                ui,
                label,
                style::BODY,
                if enabled { pal.ink } else { pal.ink_3 },
            );
            if !aside.is_empty() {
                style::text(ui, aside, style::SMALL, pal.ink_3);
            }
        });
        clicked
    };
    let bar_possible = view.has_scale_bar && view.calibrated;
    if option(
        ui,
        bar_on,
        bar_possible,
        "Scale bar",
        if !view.has_scale_bar {
            "add one in Develop"
        } else if !view.calibrated {
            "the subject has no scale calibration"
        } else {
            ""
        },
    ) {
        set(&|i, on| i.settings.scale_bar = on, !bar_on);
    }
    let words_on = all(&|i| i.copyright && i.description);
    if option(ui, words_on, true, "Copyright and description", "") {
        set(
            &|i, on| {
                i.copyright = on;
                i.description = on;
            },
            !words_on,
        );
    }
    words_lines(ui, panel, view, words_on, intents);
    let tiffs: Vec<_> = images
        .iter()
        .filter(|(_, i)| i.settings.format == ExportFormat::Tiff)
        .collect();
    let recipe_on = !tiffs.is_empty() && tiffs.iter().all(|(_, i)| i.settings.embed_recipe);
    if option(
        ui,
        recipe_on,
        !tiffs.is_empty(),
        "Develop recipe and region notes",
        "TIFF only",
    ) {
        for (preset, image) in tiffs {
            let mut next = (*image).clone();
            next.settings.embed_recipe = !recipe_on;
            intents.push(ExportIntent::Edit(
                preset.id.clone(),
                PresetOutput::Image(next),
            ));
        }
    }
    if let Some(note) = view.note {
        ui.horizontal(|ui| {
            let (rect, _) = ui.allocate_exact_size(egui::vec2(10.0, 16.0), Sense::hover());
            style::mark(ui.painter(), rect.center(), Mark::Warn, pal);
            style::text(ui, note, style::SMALL, pal.ink_2);
        });
    }
}

/// Under "Copyright and description": exactly what it writes, each line
/// editable in place. Artist and copyright are the owner's (kept in
/// Preferences, for every photograph), the description this photograph's
/// (kept in the catalog). Then the Strehl stamp, which every file carries.
fn words_lines(
    ui: &mut Ui,
    panel: &mut ExportPanel,
    view: &ExportView<'_>,
    on: bool,
    intents: &mut Vec<ExportIntent>,
) {
    let pal = view.palette;
    let ink = if on { pal.ink } else { pal.ink_3 };
    let fields = [
        (
            WordsField::Artist,
            "Artist",
            view.words.artist,
            "Not set · your name",
            crate::studio_preferences::MAX_ARTIST_BYTES,
        ),
        (
            WordsField::Copyright,
            "Copyright",
            view.words.copyright,
            "Not set · © 2026 Your name",
            crate::studio_preferences::MAX_COPYRIGHT_BYTES,
        ),
        (
            WordsField::Description,
            "Description",
            view.words.description,
            "Not set · what it shows",
            2048,
        ),
    ];
    for (field, label, value, hint, limit) in fields {
        ui.horizontal_top(|ui| {
            ui.spacing_mut().item_spacing.x = 8.0;
            words_label(ui, label, pal);
            let mut text = match panel.words_draft.take() {
                Some((f, text)) if f == field => text,
                other => {
                    panel.words_draft = other;
                    value.to_owned()
                }
            };
            let edit = if field == WordsField::Description {
                egui::TextEdit::multiline(&mut text).desired_rows(1)
            } else {
                egui::TextEdit::singleline(&mut text)
            };
            let response = ui.add(
                edit.id_salt(("export-words", label))
                    .hint_text(egui::RichText::new(hint).color(pal.ink_3))
                    .char_limit(limit)
                    .font(egui::FontId::proportional(style::BODY))
                    .text_color(ink)
                    .frame(false)
                    .margin(egui::Margin::symmetric(0, 3))
                    .desired_width(f32::INFINITY),
            );
            style::hairline(
                ui.painter(),
                response.rect.left_bottom(),
                response.rect.right_bottom(),
                if response.has_focus() {
                    pal.accent
                } else {
                    pal.line
                },
            );
            if response.has_focus() {
                panel.words_draft = Some((field, text));
            } else if response.lost_focus() && text.trim() != value.trim() {
                intents.push(ExportIntent::SetWords(field, text));
            }
        });
    }
    style::text(
        ui,
        if on {
            "Written into every ticked image. Artist and copyright are yours, for every photograph (also under Strehl › Preferences); the description is this photograph's. An empty field writes nothing."
        } else {
            "Off: none of these is written. Artist and copyright are kept under Strehl › Preferences; the description with this photograph."
        },
        style::SMALL,
        pal.ink_3,
    );
    ui.horizontal(|ui| {
        ui.spacing_mut().item_spacing.x = 8.0;
        words_label(ui, "Software", pal);
        style::text(ui, strehl_edit::CREATOR_TOOL, style::BODY, pal.ink);
        style::text(ui, "every file, always", style::SMALL, pal.ink_3);
    });
}

/// A words line's tracked caption in its fixed column.
fn words_label(ui: &mut Ui, label: &str, pal: &StudioPalette) {
    let (rect, _) = ui.allocate_exact_size(egui::vec2(82.0, 22.0), Sense::hover());
    let galley = ui
        .painter()
        .layout_job(style::caps_job(label, style::CAPS, pal.ink_3));
    let at = egui::pos2(rect.left(), rect.center().y - galley.size().y * 0.5);
    ui.painter().galley(at, galley, pal.ink_3);
}

fn name_and_place(
    ui: &mut Ui,
    panel: &mut ExportPanel,
    view: &ExportView<'_>,
    intents: &mut Vec<ExportIntent>,
) {
    let pal = view.palette;
    style::sect(ui, pal, "Name and place", None);
    // The name is this photograph's (owner feedback, 2026-11-23: a name
    // typed for one export came back on the next photograph). The template
    // is the default every other photograph starts from.
    let draft = panel
        .template_draft
        .get_or_insert_with(|| view.name.to_owned());
    let edit = ui.add(
        egui::TextEdit::singleline(draft)
            .id_salt("export-name")
            .font(egui::FontId::monospace(12.0))
            .frame(false)
            .desired_width(f32::INFINITY),
    );
    if edit.lost_focus() {
        if draft.trim() != view.name {
            intents.push(ExportIntent::SetName(Some(draft.trim().to_owned())));
        }
        panel.template_draft = None;
    }
    let own = view.name != view.library.template;
    style::text(
        ui,
        &if own {
            format!(
                "This photograph's name. Others use {}.",
                view.library.template
            )
        } else {
            "The default name; editing it here names this photograph only. Tokens: {subject} {view} {preset} {date}.".into()
        },
        style::SMALL,
        pal.ink_3,
    );
    if !own && view.library.template != crate::export_presets::DEFAULT_TEMPLATE {
        // A default edited before names were per photograph.
        if style::link(ui, pal, "Restore Strehl's default name", false)
            .on_hover_text(crate::export_presets::DEFAULT_TEMPLATE)
            .clicked()
        {
            intents.push(ExportIntent::SetTemplate(
                crate::export_presets::DEFAULT_TEMPLATE.into(),
            ));
        }
    }
    if own {
        ui.horizontal(|ui| {
            ui.spacing_mut().item_spacing.x = 14.0;
            if style::link(ui, pal, "Back to the default", false).clicked() {
                intents.push(ExportIntent::SetName(None));
            }
            // Only a name with a token can name every photograph apart.
            let tokens = view.name.contains('{');
            if tokens
                && style::link(ui, pal, "Make it the default", false)
                    .on_hover_text("Every photograph without its own name takes this one")
                    .clicked()
            {
                intents.push(ExportIntent::SetTemplate(view.name.to_owned()));
                intents.push(ExportIntent::SetName(None));
            }
        });
    }
    ui.horizontal(|ui| {
        let place = view
            .destination
            .map_or("No folder chosen for this subject".into(), |p| {
                crate::display_path::display_path(p)
            });
        style::text(ui, &place, 12.5, pal.ink_2);
        if style::link(ui, pal, "Change…", false).clicked() {
            intents.push(ExportIntent::ChangeDestination);
        }
    });
}

fn view_bundle(ui: &mut Ui, pal: &StudioPalette, running: bool, intents: &mut Vec<ExportIntent>) {
    style::sect(ui, pal, "View bundle", Some("every view of this session"));
    style::text(
        ui,
        "Copies every bound photograph, linear master, focus map and receipt to a new folder. Original RAWs and unsaved edits are not copied.",
        style::SMALL,
        pal.ink_2,
    );
    let width = ui.available_width();
    if running {
        style::text(ui, "Writing the view bundle…", style::SMALL, pal.ink);
        if style::button(
            ui,
            pal,
            "Cancel",
            ButtonKind::Plain,
            egui::vec2(72.0, 24.0),
            true,
        )
        .clicked()
        {
            intents.push(ExportIntent::CancelViewBundle);
        }
    } else if style::button(
        ui,
        pal,
        "Export view bundle…",
        ButtonKind::Plain,
        egui::vec2(width.min(180.0), 24.0),
        true,
    )
    .clicked()
    {
        intents.push(ExportIntent::ExportViewBundle);
    }
}

/// "Preview of" and the selected preset's output, above the canvas.
pub(crate) fn control_strip(
    ui: &mut Ui,
    panel: &mut ExportPanel,
    view: &ExportView<'_>,
) -> Vec<ExportIntent> {
    // Drawn into the shell's row: a left-to-right layout already inset.
    let pal = view.palette;
    let mut intents = Vec::new();
    ui.spacing_mut().item_spacing.x = 14.0;
    style::caps(ui, "Preview of", style::CAPS, pal.ink_3);
    let ticked: Vec<&ExportPreset> = view.library.ticked().collect();
    let names: Vec<&str> = ticked.iter().map(|p| p.name.as_str()).collect();
    let current = ticked
        .iter()
        .position(|p| Some(&p.id) == panel.selected.as_ref());
    if !names.is_empty()
        && let Some(i) = style::seg(ui, pal, &names, current)
    {
        panel.selected = Some(ticked[i].id.clone());
        intents.push(ExportIntent::Select(ticked[i].id.clone()));
    }
    if let Some(preset) = panel
        .selected
        .as_ref()
        .and_then(|id| view.library.presets.iter().find(|p| &p.id == id))
    {
        let [w, h] = output_size(&preset.output, view.size);
        let space = match &preset.output {
            PresetOutput::Image(i) => space_name(i.settings.color_space, i.settings.hdr),
            PresetOutput::Archive => "linear BT.709",
        };
        style::text(
            ui,
            &format!(
                "{w} × {h} · {space} · about {}",
                human_bytes(estimate_bytes(&preset.output, view.size))
            ),
            12.5,
            pal.ink_2,
        );
    }
    intents
}

/// The exports of this photograph, under the canvas (152 px in the mockup).
pub(crate) fn history_table(ui: &mut Ui, view: &ExportView<'_>) -> Vec<ExportIntent> {
    let pal = view.palette;
    let mut intents = Vec::new();
    let rect = ui.available_rect_before_wrap();
    ui.painter()
        .rect_filled(rect, CornerRadius::ZERO, pal.panel);
    style::hairline(ui.painter(), rect.left_top(), rect.right_top(), pal.line);
    let mut child =
        ui.new_child(egui::UiBuilder::new().max_rect(rect.shrink2(egui::vec2(14.0, 8.0))));
    let ui = &mut child;
    ui.horizontal(|ui| {
        style::caps(ui, "Exports of this photograph", style::CAPS, pal.ink_3);
        let unchanged = view
            .history
            .iter()
            .filter(|r| r.status == HistoryStatus::Unchanged)
            .count();
        let summary = match view.history.len() {
            0 => "none yet".to_owned(),
            n if unchanged == n => format!(
                "{n} file{} · all still where they were written",
                if n == 1 { "" } else { "s" }
            ),
            n => format!("{n} file{}", if n == 1 { "" } else { "s" }),
        };
        style::text(ui, &summary, style::SMALL, pal.ink_3);
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            if view.destination.is_some()
                && style::link(ui, pal, "Open the folder", false).clicked()
            {
                intents.push(ExportIntent::OpenFolder);
            }
        });
    });
    let columns = [0.0, 228.0, 407.0, 593.0, 812.0, 925.0];
    let headers = ["File", "Preset", "Size", "From version", "When", ""];
    let top = ui.cursor().top() + 4.0;
    let painter = ui.painter().clone();
    for (x, header) in columns.iter().zip(headers) {
        painter.galley(
            egui::pos2(rect.left() + 14.0 + x, top),
            painter.layout_job(style::caps_job(header, 9.5, pal.ink_3)),
            pal.ink_3,
        );
    }
    let mut y = top + 18.0;
    egui::ScrollArea::vertical()
        .id_salt("export-history")
        .show(ui, |ui| {
            for row in view.history {
                let line = Rect::from_min_max(
                    egui::pos2(rect.left(), y),
                    egui::pos2(rect.right(), y + 32.0),
                );
                style::hairline(&painter, line.left_top(), line.right_top(), pal.line);
                let cy = line.center().y;
                let x = |i: usize| rect.left() + 14.0 + columns[i];
                let name = row.path.file_name().unwrap_or_default().to_string_lossy();
                painter.text(
                    egui::pos2(x(0), cy),
                    Align2::LEFT_CENTER,
                    name,
                    egui::FontId::monospace(11.5),
                    pal.ink,
                );
                for (i, text) in [
                    (1, &row.preset),
                    (2, &row.size),
                    (3, &row.version),
                    (4, &row.when),
                ] {
                    style::paint_text(
                        &painter,
                        egui::pos2(x(i), cy),
                        Align2::LEFT_CENTER,
                        text,
                        12.5,
                        pal.ink_2,
                    );
                }
                let (mark, words) = match row.status {
                    HistoryStatus::Checking => (Mark::Idle, "checking"),
                    HistoryStatus::Unchanged => (Mark::Ok, "unchanged"),
                    HistoryStatus::Changed => (Mark::Bad, "changed since it was written"),
                    HistoryStatus::Missing => (Mark::Bad, "missing"),
                    HistoryStatus::Older => (Mark::Warn, "older than the current version"),
                };
                style::mark(&painter, egui::pos2(x(5) + 4.0, cy), mark, pal);
                let after = style::paint_text(
                    &painter,
                    egui::pos2(x(5) + 12.0, cy),
                    Align2::LEFT_CENTER,
                    words,
                    12.5,
                    pal.ink_2,
                );
                let mut at = after.right() + 10.0;
                let mut action = |label: &str, intent: ExportIntent, available: bool| {
                    if !available {
                        return;
                    }
                    let galley = painter.layout_job(style::caps_job(label, style::CAPS, pal.ink_2));
                    let hit = Rect::from_min_size(egui::pos2(at, cy - 7.0), galley.size());
                    let response = ui.interact(hit, ui.id().with((&row.id, label)), Sense::click());
                    painter.galley_with_override_text_color(
                        hit.min,
                        galley,
                        if response.hovered() {
                            pal.ink
                        } else {
                            pal.ink_2
                        },
                    );
                    if response.clicked() {
                        intents.push(intent);
                    }
                    at = hit.right() + 12.0;
                };
                let present = row.status != HistoryStatus::Missing;
                action("Reveal", ExportIntent::Reveal(row.path.clone()), present);
                action(
                    "Copy path",
                    ExportIntent::CopyPath(row.path.clone()),
                    present,
                );
                action(
                    "Export again",
                    ExportIntent::ExportAgain(row.id.clone()),
                    true,
                );
                y += 32.0;
            }
            ui.allocate_space(egui::vec2(1.0, (y - top).max(0.0)));
        });
    intents
}

// --------------------------------------------------------------------- batch

/// One file of a batch, with its name chosen before the batch starts.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct BatchFile {
    pub preset: String,
    pub path: PathBuf,
    pub output: BatchOutput,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) enum BatchOutput {
    Image(ExportSettings),
    /// Copy of the master, with the recipe written beside it.
    Archive {
        master: PathBuf,
        recipe: PathBuf,
    },
}

/// Who wrote the file and what it says, filled in per batch.
#[derive(Clone, Debug, Default)]
pub(crate) struct BatchText {
    pub artist: String,
    pub copyright: String,
    pub description: String,
}

/// Plan every ticked preset into a file with a free name in `folder`.
pub(crate) fn plan_batch(
    library: &Library,
    name: &str,
    fields: &NameFields<'_>,
    folder: &Path,
    master: &Path,
    text: &BatchText,
    exists: impl Fn(&Path) -> bool,
) -> Result<Vec<BatchFile>> {
    library.validate()?;
    ensure!(folder.is_absolute(), "Choose where the files go");
    let mut files: Vec<BatchFile> = Vec::new();
    for preset in library.ticked() {
        let stem = expand_name(
            name,
            &NameFields {
                preset: &preset.name,
                ..fields.clone()
            },
        )?;
        let taken = |path: &Path| exists(path) || files.iter().any(|f| f.path == path);
        let path = available_path(folder, &stem, preset.output.extension(), taken)?;
        let output = match &preset.output {
            PresetOutput::Image(image) => BatchOutput::Image(image.resolve(
                &text.artist,
                &text.copyright,
                &text.description,
            )?),
            PresetOutput::Archive => BatchOutput::Archive {
                master: master.to_path_buf(),
                recipe: path.with_extension("strehl-edits.json"),
            },
        };
        files.push(BatchFile {
            preset: preset.name.clone(),
            path,
            output,
        });
    }
    ensure!(!files.is_empty(), "Tick at least one preset");
    Ok(files)
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub(crate) enum BatchPhase {
    Preparing = 0,
    Encoding = 1,
    Recording = 2,
    Done = 3,
}

/// Shared progress of one batch: which file, which phase.
#[derive(Debug)]
pub(crate) struct BatchProgress {
    files: Vec<String>,
    current: AtomicUsize,
    phase: AtomicU8,
    pub cancelled: AtomicBool,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct BatchSnapshot {
    pub file: usize,
    pub files: usize,
    pub name: String,
    pub phase: BatchPhase,
    pub cancelling: bool,
}

impl BatchSnapshot {
    pub(crate) fn fraction(&self) -> f32 {
        if self.phase == BatchPhase::Done {
            return 1.0;
        }
        let step = match self.phase {
            BatchPhase::Preparing => 0.0,
            BatchPhase::Encoding => 0.3,
            BatchPhase::Recording => 0.9,
            BatchPhase::Done => 1.0,
        };
        ((self.file as f32 + step) / self.files.max(1) as f32).clamp(0.0, 1.0)
    }

    pub(crate) fn caption(&self) -> String {
        let phase = match self.phase {
            BatchPhase::Preparing => "preparing",
            BatchPhase::Encoding => "encoding",
            BatchPhase::Recording => "recording",
            BatchPhase::Done => "done",
        };
        if self.cancelling {
            "Cancelling after this file…".into()
        } else {
            format!(
                "File {} of {} · {} · {phase}",
                (self.file + 1).min(self.files),
                self.files,
                self.name
            )
        }
    }
}

impl BatchProgress {
    pub(crate) fn new(files: &[BatchFile]) -> Arc<Self> {
        Arc::new(Self {
            files: files.iter().map(|f| f.preset.clone()).collect(),
            current: AtomicUsize::new(0),
            phase: AtomicU8::new(BatchPhase::Preparing as u8),
            cancelled: AtomicBool::new(false),
        })
    }

    fn set(&self, file: usize, phase: BatchPhase) {
        self.current.store(file, Ordering::Relaxed);
        self.phase.store(phase as u8, Ordering::Relaxed);
    }

    pub(crate) fn snapshot(&self) -> BatchSnapshot {
        let file = self.current.load(Ordering::Relaxed);
        let phase = match self.phase.load(Ordering::Relaxed) {
            1 => BatchPhase::Encoding,
            2 => BatchPhase::Recording,
            3 => BatchPhase::Done,
            _ => BatchPhase::Preparing,
        };
        BatchSnapshot {
            file,
            files: self.files.len(),
            name: self.files.get(file).cloned().unwrap_or_default(),
            phase,
            cancelling: self.cancelled.load(Ordering::Relaxed),
        }
    }
}

/// What a finished batch wrote.
#[derive(Debug, Default)]
pub(crate) struct BatchDone {
    pub written: Vec<(BatchFile, Option<crate::workspace_history::PhotoExport>)>,
    pub failed: Vec<(PathBuf, String)>,
    pub cancelled: bool,
}

/// The batch's inputs beyond its files.
pub(crate) struct BatchContext {
    pub job: crate::development_job::DevelopmentJob,
    pub recipe_json: Vec<u8>,
    pub um_per_px: Option<f64>,
    pub date: Option<ExportDateTime>,
    /// The version every image file is recorded against.
    pub version: Option<crate::workspace_history::PhotoVersion>,
}

/// Run a batch on a worker: one file at a time, never overwriting. A failed
/// file is reported and the batch goes on; cancellation stops after the
/// current codec call and removes nothing that was published.
pub(crate) fn run_batch(
    files: Vec<BatchFile>,
    context: &BatchContext,
    progress: &BatchProgress,
) -> BatchDone {
    let mut done = BatchDone::default();
    for (index, file) in files.into_iter().enumerate() {
        if progress.cancelled.load(Ordering::Relaxed) {
            done.cancelled = true;
            break;
        }
        progress.set(index, BatchPhase::Encoding);
        let result = (|| -> Result<Option<crate::workspace_history::PhotoExport>> {
            match &file.output {
                BatchOutput::Image(settings) => {
                    context.job.export_with(
                        &file.path,
                        settings,
                        context.um_per_px,
                        context.date,
                        &progress.cancelled,
                    )?;
                    progress.set(index, BatchPhase::Recording);
                    context
                        .version
                        .as_ref()
                        .map(|version| {
                            crate::workspace_history::photographs::record_export(
                                version,
                                file.path.clone(),
                                settings.clone(),
                                &progress.cancelled,
                            )
                        })
                        .transpose()
                }
                BatchOutput::Archive { master, recipe } => {
                    copy_new(master, &file.path, &progress.cancelled)?;
                    let mut out = std::fs::OpenOptions::new()
                        .write(true)
                        .create_new(true)
                        .open(recipe)
                        .with_context(|| {
                            format!("writing {}", crate::display_path::display_path(recipe))
                        })?;
                    out.write_all(&context.recipe_json)?;
                    out.sync_all()?;
                    Ok(None)
                }
            }
        })();
        match result {
            Ok(record) => done.written.push((file, record)),
            Err(error) => done.failed.push((file.path, format!("{error:#}"))),
        }
    }
    progress.set(progress.files.len().saturating_sub(1), BatchPhase::Done);
    done
}

/// Copy a file to a new name, never replacing one.
fn copy_new(from: &Path, to: &Path, cancelled: &AtomicBool) -> Result<()> {
    let mut source = std::fs::File::open(from)
        .with_context(|| format!("reading {}", crate::display_path::display_path(from)))?;
    let mut target = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(to)
        .with_context(|| {
            format!(
                "{} already exists or cannot be written",
                crate::display_path::display_path(to)
            )
        })?;
    let result = (|| -> Result<()> {
        let mut buffer = vec![0u8; 4 << 20];
        loop {
            ensure!(!cancelled.load(Ordering::Relaxed), "export cancelled");
            let n = std::io::Read::read(&mut source, &mut buffer)?;
            if n == 0 {
                break;
            }
            target.write_all(&buffer[..n])?;
        }
        target.sync_all()?;
        Ok(())
    })();
    if result.is_err() {
        drop(target);
        let _ = std::fs::remove_file(to);
    }
    result
}

#[cfg(test)]
#[path = "export-station-tests.rs"]
mod tests;
