//! Optional saved evidence overlays. Photograph pixels and edit recipes stay separate.
use crate::jobs::{Task, spawn_task};
use eframe::egui::{self, Color32, Rect};
use std::path::{Path, PathBuf};
#[path = "session-diagnostics-data.rs"]
mod data;
use data::{Catalog, LoadedMap};

enum Work {
    Catalog(PathBuf, Task<Catalog>),
    Map(PathBuf, usize, Task<LoadedMap>),
}
pub(crate) struct SavedDiagnostics {
    output: Option<PathBuf>,
    catalog: Option<Catalog>,
    work: Option<Work>,
    selected: Option<usize>,
    loaded: Option<(usize, LoadedMap, egui::TextureHandle)>,
    opacity: f32,
    probe: Option<usize>,
    error: Option<String>,
}
impl Default for SavedDiagnostics {
    fn default() -> Self {
        Self {
            output: None,
            catalog: None,
            work: None,
            selected: None,
            loaded: None,
            opacity: 0.55,
            probe: None,
            error: None,
        }
    }
}
impl SavedDiagnostics {
    fn cancel_work(&self) {
        match &self.work {
            Some(Work::Catalog(_, task)) => task.cancel(),
            Some(Work::Map(_, _, task)) => task.cancel(),
            None => {}
        }
    }
    pub fn is_loading(&self) -> bool {
        self.work.is_some()
    }
    pub fn set_output(&mut self, path: Option<&Path>) {
        if self.output.as_deref() != path {
            self.cancel_work();
            self.output = path.map(Path::to_path_buf);
            self.catalog = None;
            self.selected = None;
            self.loaded = None;
            self.probe = None;
            self.error = None;
        }
    }
    pub(crate) fn poll(&mut self, ctx: &egui::Context) {
        match &self.work {
            Some(Work::Catalog(path, task)) => match task.receiver.try_recv() {
                Ok(result) => {
                    let current = self.output.as_ref() == Some(path) && !task.is_cancelled();
                    self.work = None;
                    if current {
                        match result {
                            Ok(catalog) => self.catalog = Some(catalog),
                            Err(error) => self.error = Some(error),
                        }
                    }
                }
                Err(std::sync::mpsc::TryRecvError::Disconnected) => self.work = None,
                Err(std::sync::mpsc::TryRecvError::Empty) => {}
            },
            Some(Work::Map(path, index, task)) => match task.receiver.try_recv() {
                Ok(result) => {
                    let index = *index;
                    let current = self.output.as_ref() == Some(path)
                        && self.selected == Some(index)
                        && !task.is_cancelled();
                    self.work = None;
                    if current {
                        match result {
                            Ok(map) => {
                                let texture = ctx.load_texture(
                                    "saved-session-diagnostic",
                                    map.image.clone(),
                                    egui::TextureOptions::NEAREST,
                                );
                                self.loaded = Some((index, map, texture));
                            }
                            Err(error) => self.error = Some(error),
                        }
                    }
                }
                Err(std::sync::mpsc::TryRecvError::Disconnected) => self.work = None,
                Err(std::sync::mpsc::TryRecvError::Empty) => {}
            },
            None => {}
        }
        if self.work.is_none()
            && self.error.is_none()
            && let Some(path) = self.output.clone()
        {
            if self.catalog.is_none() {
                let input = path.clone();
                self.work = Some(Work::Catalog(
                    path,
                    spawn_task("strehl-saved-diagnostics", move |_| data::catalog(&input)),
                ));
            } else if let Some(index) = self.selected
                && self.loaded.as_ref().is_none_or(|(old, _, _)| *old != index)
                && let Some(map) = self
                    .catalog
                    .as_ref()
                    .and_then(|c| c.maps.get(index))
                    .cloned()
            {
                self.work = Some(Work::Map(
                    path,
                    index,
                    spawn_task("strehl-saved-map", move |cancelled| {
                        data::load(&map, &cancelled)
                    }),
                ));
            }
        }
        if self.work.is_some() {
            ctx.request_repaint_after(std::time::Duration::from_millis(60));
        }
    }
    pub fn select(
        &mut self,
        label: Option<&str>,
        opacity: Option<f32>,
        uv: Option<[f32; 2]>,
    ) -> anyhow::Result<()> {
        let index = if let Some(label) = label {
            Some(
                self.catalog
                    .as_ref()
                    .and_then(|c| c.maps.iter().position(|m| m.label == label))
                    .ok_or_else(|| {
                        anyhow::anyhow!(
                            "Saved diagnostic map is unavailable; inspect available map names first"
                        )
                    })?,
            )
        } else {
            None
        };
        anyhow::ensure!(
            opacity.is_none_or(|v| v.is_finite() && (0.0..=1.0).contains(&v)),
            "Overlay opacity must be 0..1"
        );
        anyhow::ensure!(
            uv.is_none_or(|p| p.iter().all(|v| v.is_finite() && (0.0..=1.0).contains(v))),
            "Probe coordinates must be 0..1"
        );
        if self.selected != index {
            self.cancel_work();
            self.loaded = None;
            self.error = None;
            self.probe = None;
            self.selected = index;
        }
        if let Some(opacity) = opacity {
            self.opacity = opacity;
        }
        if let (Some(index), Some(uv)) = (index, uv) {
            self.probe = self.catalog.as_ref().unwrap().maps[index].index(uv);
        }
        Ok(())
    }
    pub fn capture_ready(
        &mut self,
        map: &str,
        opacity: Option<f32>,
        uv: Option<[f32; 2]>,
    ) -> anyhow::Result<bool> {
        if let Some(error) = &self.error {
            anyhow::bail!("Saved evidence: {error}");
        }
        if self.catalog.is_none() {
            return Ok(false);
        }
        self.select(Some(map), opacity, uv)?;
        Ok(self.work.is_none()
            && self
                .loaded
                .as_ref()
                .is_some_and(|(i, _, _)| Some(*i) == self.selected))
    }
    pub fn snapshot(&self) -> serde_json::Value {
        let map = self
            .selected
            .and_then(|i| self.catalog.as_ref()?.maps.get(i));
        let value = self
            .probe
            .and_then(|i| self.loaded.as_ref()?.1.values.get(i).copied());
        serde_json::json!({"available":self.catalog.as_ref().map(|c|c.maps.iter().map(|m|&m.label).collect::<Vec<_>>()).unwrap_or_default(),
            "selected":map.map(|m|&m.label),"loading":self.work.is_some(),"opacity":self.opacity,
            "sample":self.probe,"value":value.filter(|v|v.is_finite()),
            "interpretation":map.zip(value).map(|(m,v)|m.value_label(v)),"reconstruction":self.catalog.as_ref().and_then(|c|c.reconstruction.as_ref()),"error":self.error})
    }
    pub fn controls(&mut self, ui: &mut egui::Ui, path: Option<&Path>) {
        self.set_output(path);
        self.poll(ui.ctx());
        ui.add_space(12.0);
        ui.label(
            egui::RichText::new("SAVED EVIDENCE")
                .monospace()
                .size(10.0)
                .color(crate::theme::ACCENT),
        );
        let before = self.selected;
        if let Some(catalog) = &self.catalog {
            if catalog.maps.is_empty() {
                ui.small("No optional evidence maps were saved.");
            } else {
                egui::ComboBox::from_id_salt("saved-session-map")
                    .selected_text(
                        self.selected
                            .and_then(|i| catalog.maps.get(i))
                            .map_or("Photograph only", |m| m.label.as_str()),
                    )
                    .width(ui.available_width())
                    .show_ui(ui, |ui| {
                        ui.selectable_value(&mut self.selected, None, "Photograph only");
                        for (i, map) in catalog.maps.iter().enumerate() {
                            ui.selectable_value(&mut self.selected, Some(i), &map.label);
                        }
                    });
            }
            if let Some(outcome) = &catalog.reconstruction {
                ui.small(if outcome.enabled {
                    "Original-CFA reconstruction · conditional support"
                } else {
                    "Original-CFA reconstruction · native fallback"
                });
                ui.small(format!(
                    "{} / {} RGB pixels reconstructed · {} native fallback",
                    outcome.replaced_rgb_pixels,
                    outcome.total_rgb_pixels,
                    outcome.native_fallback_pixels
                ));
                ui.small(format!(
                    "{} registration-supported tiles",
                    outcome.registration_supported_tiles
                ));
                ui.small("Same output dimensions; support is not a measured resolution increase.")
                    .on_hover_text(outcome.limitations.join("\n"));
            }
            for warning in &catalog.warnings {
                ui.small(
                    egui::RichText::new("Saved evidence unavailable").color(crate::theme::ACCENT),
                )
                .on_hover_text(warning);
            }
        }
        if before != self.selected {
            self.cancel_work();
            self.loaded = None;
            self.error = None;
            self.probe = None;
        }
        if self.work.is_some() {
            ui.small("Reading saved evidence…");
        }
        if let Some(error) = &self.error {
            ui.small(
                egui::RichText::new("Could not open saved evidence").color(crate::theme::ACCENT),
            )
            .on_hover_text(error);
            if ui.small_button("Retry evidence").clicked() {
                self.error = None;
            }
        }
        if let Some(index) = self.selected
            && let Some(map) = self.catalog.as_ref().and_then(|c| c.maps.get(index))
        {
            ui.add(
                egui::Slider::new(&mut self.opacity, 0.0..=1.0)
                    .text("Overlay")
                    .fixed_decimals(2),
            );
            ui.small(&map.scope);
            if let Some((_, loaded, _)) = &self.loaded {
                ui.small(format!(
                    "{} × {} saved cells · display {:.3}–{:.3}",
                    map.size[0], map.size[1], loaded.range[0], loaded.range[1]
                ));
                legend(ui, map, loaded.range);
                ui.small("Overlay colors are sampled for display; hover or click reads the exact saved cell. Missing values are transparent.");
                if let Some(i) = self.probe {
                    let x = i % map.size[0] as usize;
                    let y = i / map.size[0] as usize;
                    ui.label(format!("Cell {x}, {y}"));
                    if let Some(&v) = loaded.values.get(i) {
                        ui.label(map.value_label(v));
                    }
                    if let Some(repro) = &map.repro
                        && let Some(tile) = repro.tiles.get(i)
                    {
                        ui.small(data::qualification(tile.qualification));
                        let metric =
                            |v: Option<f32>| v.map_or("unavailable".into(), |v| format!("{v:.4}"));
                        ui.small(format!(
                            "Correlation {}\nRelative difference {}\nAmplitude ratio {}",
                            metric(tile.band_correlation),
                            metric(tile.relative_rms_difference),
                            metric(tile.band_amplitude_ratio)
                        ));
                        curves(ui, tile);
                    }
                }
            }
        }
    }
    pub fn overlay(
        &mut self,
        ui: &mut egui::Ui,
        mapping: Option<(Rect, Rect)>,
        clip: Rect,
        exclusion: Option<Rect>,
    ) {
        let (Some((destination, aperture)), Some(index), Some((loaded_index, loaded, texture))) =
            (mapping, self.selected, &self.loaded)
        else {
            return;
        };
        if *loaded_index != index || !destination.is_positive() || !aperture.is_positive() {
            return;
        }
        let Some(map) = self.catalog.as_ref().and_then(|c| c.maps.get(index)) else {
            return;
        };
        // ProcessSpace maps the full normalized photograph to `destination`;
        // both rectangles are in screen coordinates. The second is its visible
        // screen aperture, not a normalized UV rectangle.
        let visible = clip.intersect(aperture).intersect(destination);
        let rect = Rect::from_min_size(
            destination.min,
            destination.size() * egui::vec2(map.extent[0], map.extent[1]),
        );
        for paint_clip in overlay_clips(visible.intersect(rect), exclusion) {
            ui.painter().with_clip_rect(paint_clip).image(
                texture.id(),
                rect,
                Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(1.0, 1.0)),
                Color32::WHITE.gamma_multiply(self.opacity),
            );
        }
        if let Some(pointer) = ui
            .ctx()
            .pointer_hover_pos()
            .filter(|p| visible.contains(*p) && exclusion.is_none_or(|rect| !rect.contains(*p)))
        {
            let uv = (pointer - destination.min) / destination.size();
            self.probe = map.index([uv.x, uv.y]);
            if let Some(i) = self.probe
                && let Some(&v) = loaded.values.get(i)
            {
                let text = format!("{} · {}", map.name, map.value_label(v));
                let box_rect = Rect::from_min_size(
                    clip.left_bottom() + egui::vec2(8.0, -26.0),
                    egui::vec2((clip.width() - 16.0).max(1.0), 22.0),
                );
                ui.painter().with_clip_rect(clip).rect_filled(
                    box_rect,
                    3.0,
                    Color32::from_black_alpha(190),
                );
                ui.painter().with_clip_rect(box_rect).text(
                    box_rect.left_center() + egui::vec2(5., 0.),
                    egui::Align2::LEFT_CENTER,
                    text,
                    egui::FontId::proportional(10.),
                    Color32::WHITE,
                );
            }
        }
    }
}
const FIRST_POWER: Color32 = Color32::from_rgb(75, 210, 225);
const SECOND_POWER: Color32 = Color32::from_rgb(230, 165, 90);

fn legend(ui: &mut egui::Ui, map: &data::Map, range: [f32; 2]) {
    if let Some(labels) = &map.value_labels {
        egui::ScrollArea::vertical()
            .id_salt(("saved-map-categories", &map.label))
            .max_height(95.)
            .show(ui, |ui| {
                for (code, label) in labels.iter() {
                    ui.horizontal(|ui| {
                        let (rect, _) =
                            ui.allocate_exact_size(egui::vec2(10., 10.), egui::Sense::hover());
                        ui.painter().rect_filled(
                            rect,
                            0.,
                            data::color(*code as f32, map.scale, range),
                        );
                        ui.small(format!("{code} · {label}"));
                    });
                }
            });
        return;
    }
    let discrete = matches!(map.scale, data::Scale::Category | data::Scale::Flags);
    let (rect, _) = ui.allocate_exact_size(
        egui::vec2(ui.available_width().max(40.), 10.),
        egui::Sense::hover(),
    );
    let steps = if discrete { 8 } else { 32 };
    for i in 0..steps {
        let value = if discrete {
            i as f32
        } else {
            range[0] + (range[1] - range[0]) * i as f32 / (steps - 1) as f32
        };
        let piece = Rect::from_min_max(
            rect.min + egui::vec2(rect.width() * i as f32 / steps as f32, 0.),
            egui::pos2(
                rect.left() + rect.width() * (i + 1) as f32 / steps as f32,
                rect.bottom(),
            ),
        );
        ui.painter()
            .rect_filled(piece, 0., data::color(value, map.scale, range));
    }
    if discrete {
        ui.small("Category colors repeat; inspect the exact value.");
    } else {
        ui.horizontal(|ui| {
            ui.small(format!("Low {:.3}", range[0]));
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                ui.small(format!("High {:.3}", range[1]));
            });
        });
    }
}

fn curves(ui: &mut egui::Ui, tile: &data::Tile) {
    ui.small("Ring correlation · cycles/sensor pixel");
    let (rect, _) = ui.allocate_exact_size(
        egui::vec2(ui.available_width().max(40.), 74.),
        egui::Sense::hover(),
    );
    ui.painter().rect_filled(rect, 2., crate::theme::PANEL);
    let point = |f: f32, v: f32| {
        egui::pos2(
            rect.left() + f.clamp(0., 0.5) * 2. * rect.width(),
            rect.bottom() - (v + 1.).clamp(0., 2.) * 0.5 * rect.height(),
        )
    };
    ui.painter().line_segment(
        [point(0., 0.), point(0.5, 0.)],
        egui::Stroke::new(0.5_f32, crate::theme::MUTED),
    );
    let mut previous = None;
    for ring in &tile.rings {
        if let Some(v) = ring.correlation {
            let p = point(ring.frequency, v);
            if let Some(q) = previous {
                ui.painter()
                    .line_segment([q, p], egui::Stroke::new(1_f32, crate::theme::ACCENT));
            }
            previous = Some(p);
        } else {
            previous = None;
        }
    }
    ui.horizontal(|ui| {
        ui.small("Power · log scale");
        ui.colored_label(FIRST_POWER, "First");
        ui.colored_label(SECOND_POWER, "Second");
    });
    let (rect, _) = ui.allocate_exact_size(
        egui::vec2(ui.available_width().max(40.), 65.),
        egui::Sense::hover(),
    );
    ui.painter().rect_filled(rect, 2., crate::theme::PANEL);
    let positive: Vec<_> = tile
        .rings
        .iter()
        .flat_map(|r| [r.power_first, r.power_second])
        .filter(|v| *v > 0.)
        .map(f32::log10)
        .collect();
    let lo = positive.iter().copied().fold(f32::INFINITY, f32::min);
    let hi = positive.iter().copied().fold(f32::NEG_INFINITY, f32::max);
    if !lo.is_finite() || !hi.is_finite() {
        return;
    }
    for (second, color) in [(false, FIRST_POWER), (true, SECOND_POWER)] {
        let mut previous = None;
        for ring in &tile.rings {
            let v = if second {
                ring.power_second
            } else {
                ring.power_first
            };
            if v > 0. {
                let p = egui::pos2(
                    rect.left() + ring.frequency.clamp(0., 0.5) * 2. * rect.width(),
                    rect.bottom() - (v.log10() - lo) / (hi - lo).max(1e-6) * rect.height(),
                );
                if let Some(q) = previous {
                    ui.painter()
                        .line_segment([q, p], egui::Stroke::new(1_f32, color));
                }
                previous = Some(p);
            } else {
                previous = None;
            }
        }
    }
    ui.small(format!(
        "Power range 10^{lo:.1}–10^{hi:.1}; no inferred cutoff"
    ));
}

// A saved map belongs to the main photograph, not the inset overview. Split
// the clip instead of drawing an incorrectly registered map over that widget.
fn overlay_clips(visible: Rect, exclusion: Option<Rect>) -> Vec<Rect> {
    if !visible.is_positive() {
        return Vec::new();
    }
    let Some(hole) = exclusion
        .map(|r| r.intersect(visible))
        .filter(Rect::is_positive)
    else {
        return vec![visible];
    };
    [
        Rect::from_min_max(visible.min, egui::pos2(visible.right(), hole.top())),
        Rect::from_min_max(egui::pos2(visible.left(), hole.bottom()), visible.max),
        Rect::from_min_max(egui::pos2(visible.left(), hole.top()), hole.left_bottom()),
        Rect::from_min_max(hole.right_top(), egui::pos2(visible.right(), hole.bottom())),
    ]
    .into_iter()
    .filter(Rect::is_positive)
    .collect()
}

/// Import checks each declared map, preserving unsupported report warnings.
pub(crate) struct ImportArtifact {
    pub path: PathBuf,
    pub size: [u32; 2],
    pub sha256: Option<String>,
}
pub(crate) fn import_artifacts(
    output: &Path,
    warnings: &mut Vec<String>,
) -> anyhow::Result<Vec<ImportArtifact>> {
    let catalog = data::catalog(output)?;
    warnings.extend(catalog.warnings);
    Ok(catalog
        .maps
        .into_iter()
        .map(|m| ImportArtifact {
            path: m.path,
            size: m.size,
            sha256: m.sha256,
        })
        .collect())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn saved_overlay_uses_screen_destination_and_clips_partial_map_at_any_zoom() {
        let ctx = egui::Context::default();
        let image = egui::ColorImage::filled([2, 2], Color32::RED);
        let texture = ctx.load_texture("map-control", image.clone(), Default::default());
        let mut state = SavedDiagnostics {
            catalog: Some(Catalog {
                maps: vec![data::Map {
                    path: "unused".into(),
                    label: "test".into(),
                    name: "test".into(),
                    size: [2, 2],
                    extent: [0.75, 0.5],
                    sha256: None,
                    scale: data::Scale::Unit,
                    scope: String::new(),
                    repro: None,
                    value_labels: None,
                }],
                warnings: vec![],
                reconstruction: None,
            }),
            selected: Some(0),
            loaded: Some((
                0,
                LoadedMap {
                    values: vec![0., 1., 2., 3.],
                    range: [0., 3.],
                    image,
                },
                texture.clone(),
            )),
            opacity: 0.6,
            ..Default::default()
        };
        for (origin, size) in [
            (egui::pos2(100., 200.), egui::vec2(400., 400.)),
            (egui::pos2(-500., -200.), egui::vec2(1600., 1200.)),
        ] {
            let destination = Rect::from_min_size(origin, size);
            let aperture = Rect::from_min_max(egui::pos2(150., 250.), egui::pos2(450., 550.));
            let pointer = destination.min + destination.size() * egui::vec2(0.5, 0.25);
            let aperture = aperture.union(Rect::from_center_size(pointer, egui::vec2(2., 2.)));
            let output = ctx.run(
                egui::RawInput {
                    screen_rect: Some(Rect::from_min_max(
                        egui::Pos2::ZERO,
                        egui::pos2(1000., 900.),
                    )),
                    events: vec![egui::Event::PointerMoved(pointer)],
                    ..Default::default()
                },
                |ctx| {
                    egui::CentralPanel::default().show(ctx, |ui| {
                        state.overlay(ui, Some((destination, aperture)), aperture, None);
                    });
                },
            );
            let mesh = output
                .shapes
                .iter()
                .find_map(|s| match &s.shape {
                    egui::Shape::Mesh(m) if m.texture_id == texture.id() => Some((s.clip_rect, m)),
                    _ => None,
                })
                .expect("actual overlay mesh must be painted at nonzero screen origin");
            assert_eq!(
                mesh.0,
                aperture
                    .intersect(destination)
                    .intersect(Rect::from_min_size(origin, size * egui::vec2(0.75, 0.5)))
            );
            assert_eq!(
                mesh.1.calc_bounds(),
                Rect::from_min_size(origin, size * egui::vec2(0.75, 0.5))
            );
            assert_eq!(
                state.probe,
                Some(3),
                "hover samples normalized full-photo coordinates"
            );
            assert!(
                mesh.1
                    .vertices
                    .iter()
                    .all(|v| v.color == Color32::WHITE.gamma_multiply(0.6))
            );
        }
        let destination = Rect::from_min_size(egui::pos2(100., 100.), egui::vec2(400., 400.));
        let _ = ctx.run(
            egui::RawInput {
                events: vec![egui::Event::PointerMoved(egui::pos2(450., 250.))],
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default().show(ctx, |ui| {
                    state.overlay(ui, Some((destination, destination)), destination, None)
                });
            },
        );
        assert_eq!(
            state.probe, None,
            "incomplete map margin must not retain a stale value"
        );
        let hole = Rect::from_min_size(egui::pos2(220., 180.), egui::vec2(70., 50.));
        state.probe = Some(2);
        let output = ctx.run(
            egui::RawInput {
                events: vec![egui::Event::PointerMoved(hole.center())],
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default().show(ctx, |ui| {
                    state.overlay(
                        ui,
                        Some((destination, destination)),
                        destination,
                        Some(hole),
                    );
                });
            },
        );
        let clips = output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Mesh(mesh) if mesh.texture_id == texture.id() => Some(shape.clip_rect),
                _ => None,
            })
            .collect::<Vec<_>>();
        assert_eq!(clips.len(), 4);
        assert!(clips.iter().all(|clip| !clip.intersect(hole).is_positive()));
        let area: f32 = clips.iter().map(|clip| clip.area()).sum();
        assert_eq!(area, 300. * 200. - hole.area());
        assert_eq!(
            state.probe,
            Some(2),
            "navigator hover must not sample the main photograph"
        );
    }

    #[test]
    fn saved_power_curves_and_labels_use_identical_cyan_orange_colors() {
        let ctx = egui::Context::default();
        let tile = data::Tile {
            tile: [0, 0],
            origin_sensor: [0, 0],
            qualification: 3,
            band_correlation: None,
            relative_rms_difference: None,
            band_amplitude_ratio: None,
            rings: vec![
                data::Ring {
                    frequency: 0.1,
                    power_first: 16.,
                    power_second: 4.,
                    correlation: Some(0.9),
                },
                data::Ring {
                    frequency: 0.2,
                    power_first: 8.,
                    power_second: 2.,
                    correlation: Some(0.8),
                },
            ],
        };
        let output = ctx.run(egui::RawInput::default(), |ctx| {
            egui::CentralPanel::default().show(ctx, |ui| curves(ui, &tile));
        });
        for expected in [FIRST_POWER, SECOND_POWER] {
            assert!(output.shapes.iter().any(|s| matches!(&s.shape, egui::Shape::LineSegment { stroke, .. } if stroke.color == expected)));
            assert!(output.shapes.iter().any(|s| matches!(&s.shape, egui::Shape::Text(text) if text.galley.job.sections.iter().any(|section| section.format.color == expected))));
        }
        assert_ne!(FIRST_POWER, crate::theme::ACCENT);
    }

    #[test]
    fn unavailable_selection_is_noop_and_normalized_agent_input_is_required() {
        let mut state = SavedDiagnostics::default();
        let before = state.snapshot();
        assert!(
            state
                .select(Some("../outside.tiff"), Some(0.3), Some([0.5, 0.5]))
                .is_err()
        );
        assert_eq!(state.snapshot(), before);
        let command =
            |opacity, sample_uv| crate::agent_interface::AgentCommand::InspectSessionDiagnostic {
                map: None,
                opacity,
                sample_uv,
            };
        assert!(command(Some(f32::NAN), None).validate().is_err());
        assert!(command(None, Some([1.1, 0.5])).validate().is_err());
        assert!(command(Some(0.5), Some([0., 1.])).validate().is_ok());
    }
}
