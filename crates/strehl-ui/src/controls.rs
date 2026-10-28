use crate::{
    jobs::{MachineResources, RenderSettings, Resampler},
    theme::{ACCENT, INK, LINE, MUTED},
};
use eframe::egui::{self, RichText};

#[path = "run-review.rs"]
mod run_review;
pub(crate) use run_review::{ReviewFocus, show as show_review};

pub struct Controls {
    pub settings: RenderSettings,
    pub exposure: Option<f32>,
    pub gate: Option<f32>,
    pub workers: usize,
    machine: MachineResources,
}
impl Default for Controls {
    fn default() -> Self {
        Self::for_machine(MachineResources::detect())
    }
}
impl Controls {
    fn for_machine(machine: MachineResources) -> Self {
        Self {
            settings: RenderSettings::default(),
            exposure: None,
            gate: None,
            workers: machine.maximum_workers(),
            machine,
        }
    }
    pub(crate) fn machine_summary(&self) -> String {
        let memory = self
            .machine
            .physical_memory_bytes
            .map_or_else(String::new, |bytes| {
                format!(
                    " · {:.1} GiB RAM",
                    bytes as f64 / (1024.0 * 1024.0 * 1024.0)
                )
            });
        format!(
            "{}/{} CPU threads{memory}",
            self.workers, self.machine.logical_processors
        )
    }

    pub(crate) fn quality_summary(&self) -> &'static str {
        if self.settings.binned {
            "Half-size · 16-bit RGB"
        } else {
            "Full resolution · 16-bit RGB"
        }
    }

    pub fn show(&mut self, ui: &mut egui::Ui, enabled: bool) {
        if self.settings.session.is_some() {
            self.show_session_controls(ui, enabled);
            return;
        }
        ui.add_enabled_ui(enabled, |ui| {
            ui.horizontal(|ui| {
                ui.label(RichText::new("RENDER SETTINGS").monospace().size(9.0).color(MUTED));
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    if ui.add(egui::Button::new(RichText::new("Reset").size(10.0).color(MUTED)).frame(false)).clicked() { *self=Self::default(); }
                });
            });
            section(ui, "01", "Merge", |ui| {
                ui.horizontal(|ui| { ui.label("Method"); right(ui,"Laplacian pyramid"); });
                optional_float(ui,"Noise gate",&mut self.gate,2.0,0.0..=8.0,
                    "A noise/detail tradeoff. Higher values average more coefficients below the sensor noise gate. Click Default to override; drag a number or click to type.");
                ui.checkbox(&mut self.settings.temporal_energy, "Temporal detail smoothing")
                    .on_hover_text("Uses adjacent captures to guide the finest detail layers on the next stack. Compare with this off; this is experimental and is not a post-process filter.");
                note(ui, "Experimental. May remove faint detail visible in only one capture.");
                egui::CollapsingHeader::new("Scale controls").id_salt("pyramid").show(ui, |ui| {
                    ui.horizontal(|ui| {
                        ui.label("Scales");
                        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                            if let Some(value) = &mut self.settings.pyramid_bands {
                                let clear=ui.small_button("Reset").clicked();
                                ui.add(egui::DragValue::new(value).range(1..=12).speed(0.05));
                                if clear { self.settings.pyramid_bands=None; }
                            } else if ui.small_button("Default").on_hover_text("Override the engine's pyramid scale count.").clicked() { self.settings.pyramid_bands=Some(7); }
                        });
                    });
                    optional_float(ui,"Coarse power",&mut self.settings.pyramid_exponent,2.0,0.5..=8.0,
                        "Exponent applied to band weights. Increasing it concentrates selection; it does not promise better detail.");
                    optional_float(ui,"Fine-scale ramp",&mut self.settings.pyramid_sharpen,1.4,1.0..=2.0,
                        "Increase selection exponents toward finer bands. This is not post-process sharpening.");
                });
            });
            section(ui,"02","Develop", |ui| {
                if ui.checkbox(&mut self.settings.auto_exposure,"Automatic exposure").on_hover_text("Place the merged image's 99.9th-percentile linear luminance at 0.90, within ±6 EV. The chosen exposure is recorded in the run. This cannot recover clipped capture detail.").changed() && self.settings.auto_exposure {
                    self.exposure = None;
                }
                ui.add_enabled_ui(!self.settings.auto_exposure, |ui| {
                    optional_float(ui,"Exposure",&mut self.exposure,0.0,-12.0..=12.0,
                        "Exposure in stops for the next TIFF. Click Default to override. Camera JPEG previews retain camera processing.");
                });
                ui.checkbox(&mut self.settings.correct_lateral_ca,"Correct colour fringing").on_hover_text("Use the engine's supported optical profile; unknown profiles follow its normal guard.");
                note(ui,"As-shot WB / sRGB tone");
            });
            section(ui,"03","Geometry", |ui| {
                ui.checkbox(&mut self.settings.crop_to_coverage,"Shared coverage crop").on_hover_text("Use the area covered by placed frames instead of the engine's normal canvas policy.");
                ui.checkbox(&mut self.settings.binned,"Half-size TIFF").on_hover_text("One pixel per 2x2 CFA quad. Changes output sampling; all selected captures still participate.");
                ui.horizontal(|ui| {
                    ui.label("Sampling");
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        egui::ComboBox::from_id_salt("sampler").width(137.0).selected_text(self.settings.resampler.label()).show_ui(ui, |ui| {
                            for item in Resampler::ALL { ui.selectable_value(&mut self.settings.resampler,item,item.label()); }
                        });
                    });
                });
                note(ui,self.quality_summary());
            });
            egui::CollapsingHeader::new("Capture range & evidence").id_salt("capture-evidence").show(ui, |ui| {
                optional_usize(ui,"First captures",&mut self.settings.frame_limit,12,1..=65_536,
                    "Use the first N captures in filename order. All captures remain browsable. Reset includes the entire bracket.");
                ui.checkbox(&mut self.settings.confidence_map,"Save confidence map").on_hover_text("Adds a second decode and warp pass. Saves confidence.tiff beside the photograph: an aligned-observation centrality rank on the plane grid, not a probability or a defect detector. 0–1000 encodes extreme-to-central; 65535 means no observation.");
                if self.settings.confidence_map {
                    note(ui,"Extra pass · confidence.tiff beside the photograph");
                }
                note(ui,"Pyramid uses soft weighting and an averaged tone base.");
                ui.label(RichText::new("Why no focus-operator or photometric controls?").size(9.5).color(MUTED)).on_hover_text("Those controls belong to the alternative estimator backend. The pyramid engine explicitly refuses them. Hard-max selection, weighted tone base, linear measurement output, and research diagnostics remain available through the CLI; they are not hidden desktop settings.");
            });
            egui::CollapsingHeader::new("Execution").id_salt("performance").show(ui, |ui| {
                note(ui, &self.machine_summary());
                ui.horizontal(|ui| {
                    ui.label("CPU thread limit");
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center),|ui| {
                        ui.add(egui::DragValue::new(&mut self.workers).range(1..=self.machine.maximum_workers()).speed(0.05));
                    });
                });
                note(ui,"All available CPU threads by default.");
                note(ui,"CPU stacking · GPU display");
                ui.label(RichText::new("Engine manages memory and task routing.").size(9.5).color(MUTED)).on_hover_text("The normal stacking engine runs on CPU. The graphics card draws this workspace. Thread limits do not change the image settings or canonical merge reduction order; actual active threads depend on the current stage and bracket.");
            });
        });
    }

    fn show_session_controls(&mut self, ui: &mut egui::Ui, enabled: bool) {
        ui.add_enabled_ui(enabled, |ui| {
            section(ui, "01", "Session merge", |ui| {
                optional_float(ui, "Noise gate", &mut self.gate, 2.0, 0.0..=8.0, "Higher values average more coefficients below the calibrated noise gate.");
                optional_usize(ui, "Detail scales", &mut self.settings.pyramid_bands, 7, 1..=12, "Pyramid scale count for this session.");
                optional_float(ui, "Coarse power", &mut self.settings.pyramid_exponent, 2.0, 0.5..=8.0, "Band-weight exponent.");
                optional_float(ui, "Fine-scale ramp", &mut self.settings.pyramid_sharpen, 1.4, 1.0..=2.0, "Selection exponent increase toward finer bands.");
                optional_float(ui, "Exposure", &mut self.exposure, 0.0, -12.0..=12.0, "Manual output exposure in stops; camera previews keep camera processing.");
                note(ui, "Full resolution · 16-bit photograph + linear master");
                note(ui, "Each pass is calibrated independently. Source repairs and temporal smoothing are unavailable in a session.");
                note(ui, "New session renders start from these merge settings. Develop each saved photograph afterwards; previous edits stay with their saved result.");
            });
            section(ui, "02", "Session resources", |ui| {
                note(ui, &self.machine_summary());
                let maximum = self.machine.physical_memory_bytes.map_or(4096.0, |bytes| (bytes as f64 / (1u64 << 30) as f64).max(1.0));
                ui.horizontal(|ui| {
                    ui.label("RAM budget").on_hover_text("Working-memory reservation for the session engine, including cached CFA, guides, direct native pairs and reconstruction. It refuses a budget too small for the required workspace.");
                    let session = self.settings.session.as_mut().expect("session controls");
                    ui.add(egui::DragValue::new(&mut session.memory_limit_gib).range(1.0..=maximum).speed(0.25).suffix(" GiB"));
                });
                ui.horizontal(|ui| { ui.label("CPU thread limit"); ui.add(egui::DragValue::new(&mut self.workers).range(1..=self.machine.maximum_workers()).speed(0.1)); });
                note(ui, "The engine bounds active workers to the RAM reservation. GPU draws this workspace.");
            });
        });
    }
}
fn section(ui: &mut egui::Ui, index: &str, name: &str, contents: impl FnOnce(&mut egui::Ui)) {
    ui.add_space(8.0);
    ui.horizontal(|ui| {
        ui.label(RichText::new(index).monospace().size(8.5).color(MUTED));
        ui.label(RichText::new(name).size(11.5).color(INK));
    });
    let (rule, _) =
        ui.allocate_exact_size(egui::vec2(ui.available_width(), 1.0), egui::Sense::hover());
    crate::theme::rule(ui.painter(), rule.left_center(), rule.right_center(), LINE);
    ui.add_space(3.0);
    contents(ui);
    ui.add_space(5.0);
}
fn optional_float(
    ui: &mut egui::Ui,
    label: &str,
    value: &mut Option<f32>,
    initial: f32,
    range: std::ops::RangeInclusive<f32>,
    help: &str,
) {
    ui.horizontal(|ui| {
        ui.label(label).on_hover_text(help);
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            if let Some(number) = value {
                let clear = ui
                    .add(
                        egui::Button::new(RichText::new("Reset").size(9.0).color(MUTED))
                            .frame(false),
                    )
                    .clicked();
                ui.add(
                    egui::DragValue::new(number)
                        .range(range)
                        .speed(0.02)
                        .max_decimals(2)
                        .suffix(if label == "Exposure" { " EV" } else { "" }),
                )
                .on_hover_text(help);
                if clear {
                    *value = None;
                }
            } else if ui
                .add(
                    egui::Button::new(RichText::new("Default").size(10.0).color(MUTED))
                        .frame(false),
                )
                .on_hover_text(help)
                .clicked()
            {
                *value = Some(initial);
            }
        });
    });
}
fn optional_usize(
    ui: &mut egui::Ui,
    label: &str,
    value: &mut Option<usize>,
    initial: usize,
    range: std::ops::RangeInclusive<usize>,
    help: &str,
) {
    ui.horizontal(|ui| {
        ui.label(label).on_hover_text(help);
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            if let Some(number) = value {
                let reset = ui
                    .small_button("All")
                    .on_hover_text("Use every capture")
                    .clicked();
                ui.add(egui::DragValue::new(number).range(range).speed(0.2))
                    .on_hover_text(help);
                if reset {
                    *value = None;
                }
            } else if ui.small_button("All").on_hover_text(help).clicked() {
                *value = Some(initial);
            }
        });
    });
}
fn note(ui: &mut egui::Ui, text: &str) {
    ui.label(RichText::new(text).size(9.5).color(MUTED));
}
fn right(ui: &mut egui::Ui, text: &str) {
    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
        ui.label(RichText::new(text).size(11.0).color(ACCENT));
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn execution_defaults_use_available_capacity_without_changing_image_settings() {
        // A 32-thread machine rejects the retired four-thread desktop default;
        // single-CPU and API-limit cases independently exercise both bounds.
        for (available, expected) in [(0, 1), (1, 1), (4, 4), (32, 32), (64, 64), (2048, 1024)] {
            let controls = Controls::for_machine(MachineResources {
                logical_processors: available,
                physical_memory_bytes: None,
            });
            assert_eq!(controls.workers, expected);
            assert_eq!(controls.settings, RenderSettings::default());
            assert!(!controls.settings.binned);
            assert_eq!(controls.settings.resampler, Resampler::CatmullRom);
            assert!(controls.settings.correct_lateral_ca);
            assert!(controls.exposure.is_none() && controls.gate.is_none());
        }
    }

    #[test]
    fn action_summaries_follow_manual_limits_and_output_sampling_truthfully() {
        let mut controls = Controls::for_machine(MachineResources {
            logical_processors: 32,
            physical_memory_bytes: Some(64 * 1024 * 1024 * 1024),
        });
        assert_eq!(
            controls.machine_summary(),
            "32/32 CPU threads · 64.0 GiB RAM"
        );
        assert_eq!(controls.quality_summary(), "Full resolution · 16-bit RGB");
        controls.workers = 8;
        controls.settings.binned = true;
        assert_eq!(
            controls.machine_summary(),
            "8/32 CPU threads · 64.0 GiB RAM"
        );
        assert_eq!(controls.quality_summary(), "Half-size · 16-bit RGB");
        controls.machine.physical_memory_bytes = None;
        assert_eq!(
            controls.machine_summary(),
            "8/32 CPU threads",
            "Unavailable RAM must not masquerade as zero capacity"
        );
    }

    #[test]
    fn temporal_energy_checkbox_and_reset_use_the_real_adjust_controls() {
        fn paint(
            controls: &mut Controls,
            ctx: &egui::Context,
            enabled: bool,
            time: f64,
            events: Vec<egui::Event>,
        ) -> egui::FullOutput {
            ctx.run(
                egui::RawInput {
                    screen_rect: Some(egui::Rect::from_min_size(
                        egui::Pos2::ZERO,
                        egui::vec2(300.0, 720.0),
                    )),
                    time: Some(time),
                    events,
                    ..Default::default()
                },
                |ctx| {
                    egui::CentralPanel::default().show(ctx, |ui| controls.show(ui, enabled));
                },
            )
        }
        fn label(output: &egui::FullOutput, name: &str) -> egui::Pos2 {
            output
                .shapes
                .iter()
                .find_map(|shape| match &shape.shape {
                    egui::Shape::Text(text) if text.galley.text() == name => {
                        Some(text.visual_bounding_rect().center())
                    }
                    _ => None,
                })
                .unwrap_or_else(|| panic!("missing rendered control: {name}"))
        }
        fn click(
            controls: &mut Controls,
            ctx: &egui::Context,
            enabled: bool,
            at: egui::Pos2,
            time: f64,
        ) {
            for (offset, pressed) in [(0.0, true), (0.02, false)] {
                paint(
                    controls,
                    ctx,
                    enabled,
                    time + offset,
                    vec![
                        egui::Event::PointerMoved(at),
                        egui::Event::PointerButton {
                            pos: at,
                            button: egui::PointerButton::Primary,
                            pressed,
                            modifiers: egui::Modifiers::NONE,
                        },
                    ],
                );
            }
        }
        let ctx = egui::Context::default();
        crate::theme::install(&ctx);
        let mut controls = Controls::default();
        let first = paint(&mut controls, &ctx, true, 0.0, vec![]);
        assert!(!controls.settings.temporal_energy);
        let toggle = label(&first, "Temporal detail smoothing");
        label(
            &first,
            "Experimental. May remove faint detail visible in only one capture.",
        );
        click(&mut controls, &ctx, true, toggle, 0.1);
        assert!(controls.settings.temporal_energy);
        paint(&mut controls, &ctx, false, 0.2, vec![]);
        click(&mut controls, &ctx, false, toggle, 0.3);
        assert!(
            controls.settings.temporal_energy,
            "disabled controls must not alter a running recipe"
        );
        let enabled = paint(&mut controls, &ctx, true, 0.4, vec![]);
        click(&mut controls, &ctx, true, label(&enabled, "Reset"), 0.5);
        assert_eq!(controls.settings, RenderSettings::default());
        assert!(!controls.settings.temporal_energy);
    }
}
