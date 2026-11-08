use crate::theme::*;
use eframe::egui::{self, Color32, Rect, RichText, Vec2};
use std::{collections::BTreeMap, path::PathBuf, time::Duration};
use strehl_capture::{
    backend::property,
    model::{Phase, Plan, Roi},
    worker::{Action, PAUSE, STOP, Snapshot, Worker},
};

pub struct App {
    pub worker: Worker,
    pub plan: Plan,
    pub start_set: bool,
    pub end_set: bool,
    pub root: PathBuf,
    pub demo: bool,
    pub roi: Roi,
    pub widgets: BTreeMap<String, Rect>,
    pub local_message: Option<String>,
    texture: Option<egui::TextureHandle>,
    texture_generation: u64,
    zoom: f32,
    center: egui::Pos2,
    peaking: bool,
    choose_roi: bool,
    roi_drag: Option<egui::Pos2>,
    closing: bool,
    was_connected: bool,
    close_revision: Option<u64>,
}
impl App {
    pub fn new(worker: Worker, root: PathBuf, demo: bool) -> Self {
        Self {
            worker,
            plan: Plan::default(),
            start_set: false,
            end_set: false,
            root,
            demo,
            roi: Roi::subject(),
            widgets: BTreeMap::new(),
            local_message: None,
            texture: None,
            texture_generation: 0,
            zoom: 1.0,
            center: egui::pos2(0.5, 0.5),
            peaking: false,
            choose_roi: false,
            roi_drag: None,
            closing: false,
            was_connected: false,
            close_revision: None,
        }
    }
    fn send(&mut self, s: &Snapshot, action: Action) {
        self.local_message = None;
        if let Err(e) = self.worker.send(s.revision, action) {
            self.local_message = Some(e.to_string());
        }
    }
    fn button(&mut self, ui: &mut egui::Ui, key: &str, label: &str, enabled: bool) -> bool {
        let response = ui.add_enabled(enabled, egui::Button::new(label));
        self.widgets.insert(key.into(), response.rect);
        response.clicked()
    }
    fn section(ui: &mut egui::Ui, label: &str) {
        ui.add_space(5.0);
        ui.label(RichText::new(label).size(10.0).color(MUTED).strong());
    }
    pub fn draw(&mut self, ctx: &egui::Context) {
        self.widgets.clear();
        let s = self.worker.snapshot();
        if s.connected != self.was_connected {
            self.start_set = false;
            self.end_set = false;
            self.roi = Roi::subject();
            self.was_connected = s.connected;
        }
        if ctx.input(|i| i.viewport().close_requested()) && (s.connected || s.phase.active()) {
            ctx.send_viewport_cmd(egui::ViewportCommand::CancelClose);
            self.closing = true;
            self.worker.request_stop();
        }
        if self.closing {
            if !s.connected && !s.phase.active() {
                ctx.send_viewport_cmd(egui::ViewportCommand::Close);
            } else if !s.phase.active() && self.close_revision != Some(s.revision) {
                self.close_revision = Some(s.revision);
                self.send(&s, Action::Disconnect);
            }
        }
        self.update_texture(ctx, &s);
        egui::TopBottomPanel::top("top")
            .exact_height(58.0)
            .frame(
                egui::Frame::new()
                    .fill(PANEL)
                    .inner_margin(egui::Margin::symmetric(18, 12)),
            )
            .show(ctx, |ui| {
                ui.horizontal(|ui| {
                    ui.label(RichText::new("Strehl").size(25.0).color(INK));
                    ui.label(RichText::new(" /  CAPTURE").size(11.0).color(MUTED));
                    if self.demo {
                        ui.label(RichText::new("DEMO · NO CAMERA").size(10.0).color(AMBER));
                    }
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if self.button(
                            ui,
                            "connection",
                            if s.connected {
                                "Disconnect"
                            } else {
                                "Connect camera"
                            },
                            !s.phase.active(),
                        ) {
                            self.send(
                                &s,
                                if s.connected {
                                    Action::Disconnect
                                } else {
                                    Action::Connect
                                },
                            );
                        }
                        ui.label(
                            RichText::new(if s.connected {
                                "● USB · A7C II"
                            } else {
                                "○ Camera offline"
                            })
                            .color(if s.connected {
                                GREEN
                            } else {
                                MUTED
                            }),
                        );
                    });
                });
            });
        egui::TopBottomPanel::bottom("status")
            .exact_height(64.0)
            .frame(
                egui::Frame::new()
                    .fill(PANEL)
                    .inner_margin(egui::Margin::symmetric(18, 8)),
            )
            .show(ctx, |ui| {
                let pending = self.worker.pending();
                let message = if self.closing {
                    "Closing after the active camera operation…"
                } else if s.phase.active() && pending == STOP {
                    "Stopping after the active camera operation…"
                } else if s.phase.active() && pending == PAUSE && s.phase != Phase::Paused {
                    "Pausing after the active camera operation…"
                } else {
                    self.local_message.as_deref().unwrap_or(&s.message)
                };
                ui.label(RichText::new(message).color(if s.phase == Phase::Fault {
                    AMBER
                } else {
                    INK
                }));
                ui.horizontal(|ui| {
                    ui.small("RAW → SD card");
                    ui.colored_label(MUTED, "  •  Live view stays in memory  •  Journal → laptop");
                    if s.total > 0 {
                        ui.add(
                            egui::ProgressBar::new(s.completed as f32 / s.total as f32)
                                .desired_width(180.0)
                                .text(format!("{} / {}", s.completed, s.total)),
                        );
                    }
                });
            });
        egui::SidePanel::left("controls")
            .exact_width(320.0)
            .resizable(false)
            .frame(
                egui::Frame::new()
                    .fill(PANEL)
                    .inner_margin(egui::Margin::symmetric(18, 10)),
            )
            .show(ctx, |ui| {
                egui::ScrollArea::vertical()
                    .id_salt("capture-controls")
                    .auto_shrink([false, false])
                    .show(ui, |ui| self.controls(ui, &s));
            });
        egui::CentralPanel::default()
            .frame(
                egui::Frame::new()
                    .fill(BG)
                    .inner_margin(egui::Margin::same(16)),
            )
            .show(ctx, |ui| self.viewer(ui, &s));
        ctx.request_repaint_after(Duration::from_millis(80));
    }
    fn controls(&mut self, ui: &mut egui::Ui, s: &Snapshot) {
        let editable = s.phase.can_edit();
        Self::section(ui, "FOCUS POSITION");
        ui.horizontal(|ui| {
            ui.label(
                RichText::new(
                    s.position
                        .map(|p| p.to_string())
                        .unwrap_or_else(|| "—".into()),
                )
                .monospace()
                .size(30.0),
            );
            ui.label(RichText::new("command units").size(11.0).color(MUTED));
        });
        ui.horizontal(|ui| {
            for delta in [-128, -16, -1, 1, 16, 128] {
                let target = s
                    .position
                    .and_then(|p| u16::try_from(i32::from(p) + delta).ok());
                let label = format!("{delta:+}");
                if self.button(
                    ui,
                    &format!("jog-{delta}"),
                    &label,
                    editable && target.is_some(),
                ) {
                    self.send(
                        s,
                        Action::Move {
                            target: target.unwrap(),
                            settle_ms: self.plan.settle_ms,
                        },
                    );
                }
            }
        });
        ui.small("Jog to each boundary using the live preview.");
        ui.add_space(5.0);
        for start in [true, false] {
            egui::Frame::new()
                .fill(RAISED)
                .inner_margin(10)
                .show(ui, |ui| {
                    ui.horizontal(|ui| {
                        ui.label(
                            RichText::new(if start { "A  START" } else { "B  END" })
                                .color(ACCENT)
                                .size(11.0),
                        );
                        let set = if start { self.start_set } else { self.end_set };
                        let value = if start {
                            self.plan.start
                        } else {
                            self.plan.end
                        };
                        ui.label(
                            RichText::new(if set {
                                value.to_string()
                            } else {
                                "Not marked".into()
                            })
                            .monospace(),
                        );
                    });
                    ui.horizontal(|ui| {
                        if self.button(
                            ui,
                            if start { "mark-start" } else { "mark-end" },
                            "Mark current",
                            editable && s.position.is_some() && s.preview_at.is_some_and(|t|t.elapsed()<Duration::from_secs(2)),
                        ) {
                            if start {
                                self.plan.start = s.position.unwrap();
                                self.start_set = true;
                            } else {
                                self.plan.end = s.position.unwrap();
                                self.end_set = true;
                            }
                        }
                        let set = if start { self.start_set } else { self.end_set };
                        let target = if start {
                            self.plan.start
                        } else {
                            self.plan.end
                        };
                        if self.button(
                            ui,
                            if start { "go-start" } else { "go-end" },
                            "Go to mark",
                            editable && set,
                        ) {
                            let from=i32::from(target)-self.plan.direction()*i32::from(self.plan.approach);
                            if let Ok(approach_from)=u16::try_from(from) {
                                self.send(s,Action::Inspect{target,approach_from,settle_ms:self.plan.settle_ms});
                            }else{self.local_message=Some("Shorten Approach to inspect this mark without crossing the lens limit".into());}
                        }
                    });
                });
        }
        Self::section(ui, "CAPTURE PLAN");
        ui.add_enabled_ui(!s.phase.active() && s.phase != Phase::Fault, |ui| {
            egui::Grid::new("plan-settings")
                .num_columns(2)
                .spacing([15.0, 8.0])
                .show(ui, |ui| {
                    ui.label("Focus step");
                    ui.add(
                        egui::DragValue::new(&mut self.plan.step)
                            .range(1..=65535)
                            .speed(1.0)
                            .suffix(" units"),
                    );
                    ui.end_row();
                    ui.label("Settle after move");
                    ui.add(
                        egui::DragValue::new(&mut self.plan.settle_ms)
                            .range(100..=30000)
                            .speed(25.0)
                            .suffix(" ms"),
                    );
                    ui.end_row();
                });
        });
        ui.label(
            RichText::new(
                "1 is the smallest command. Adjacent positions can repeat the same physical focus.",
            )
            .size(11.0)
            .color(MUTED),
        );
        let positions = if self.start_set && self.end_set {
            self.plan.positions()
        } else {
            Err(anyhow::anyhow!("Mark both focus boundaries"))
        };
        match &positions {
            Ok(p) => {
                ui.label(
                    RichText::new(format!(
                        "{} RAWs · {} sweep",
                        p.len(),
                        if self.plan.end >= self.plan.start {
                            "increasing"
                        } else {
                            "decreasing"
                        }
                    ))
                    .color(ACCENT),
                );
            }
            Err(e) => {
                ui.label(RichText::new(e.to_string()).size(11.0).color(MUTED));
            }
        }
        ui.horizontal(|ui| {
            if self.button(ui, "start", "Start stack", editable && positions.is_ok()) {
                self.worker.request_resume();
                self.send(
                    s,
                    Action::Capture {
                        plan: self.plan.clone(),
                        root: self.root.clone(),
                    },
                );
            }
            if self.button(
                ui,
                "pause",
                if s.phase == Phase::Paused {
                    "Resume"
                } else {
                    "Pause"
                },
                matches!(s.phase, Phase::Capturing | Phase::Scanning | Phase::Paused),
            ) {
                if s.phase == Phase::Paused {
                    self.worker.request_resume();
                } else {
                    self.worker.request_pause();
                }
            }
            if self.button(
                ui,
                "stop",
                "Stop",
                matches!(s.phase, Phase::Capturing | Phase::Scanning | Phase::Paused),
            ) {
                self.worker.request_stop();
            }
        });
        ui.small("Pause / Stop finish the active operation.");
        Self::section(ui, "FIND BOUNDS · PREVIEW SURVEY");
        ui.label(RichText::new("Mark rough limits first. Select the subject in the preview, then sweep without taking RAWs.").size(11.0).color(MUTED));
        ui.horizontal(|ui| {
            if self.button(
                ui,
                "select-roi",
                if self.choose_roi {
                    "Draw a rectangle…"
                } else {
                    "Select subject"
                },
                editable,
            ) {
                self.choose_roi = !self.choose_roi;
                self.zoom = 1.0;
            }
            if self.button(
                ui,
                "scan",
                "Sweep preview",
                editable
                    && self.start_set
                    && self.end_set
                    && self.plan.start.abs_diff(self.plan.end) >= 8,
            ) {
                self.worker.request_resume();
                self.send(
                    s,
                    Action::Scan {
                        plan: self.plan.clone(),
                        roi: self.roi,
                    },
                );
            }
        });
        if let Some(suggestion) = &s.suggestion {
            ui.label(
                RichText::new(format!(
                    "Suggested: {} → {}",
                    suggestion.start, suggestion.end
                ))
                .color(GREEN),
            );
            ui.small(&suggestion.explanation);
            if self.button(
                ui,
                "apply-bounds",
                "Apply suggested bounds",
                editable && !suggestion.clipped,
            ) {
                self.plan.start = suggestion.start;
                self.plan.end = suggestion.end;
                self.start_set = true;
                self.end_set = true;
            }
        }
        ui.add_space(5.0);
        egui::CollapsingHeader::new("Approach, timeout & storage").show(ui,|ui|{
            ui.add_enabled_ui(!s.phase.active(),|ui|{
                ui.horizontal(|ui|{ui.label("Approach");ui.add(egui::DragValue::new(&mut self.plan.approach).range(1..=4096).suffix(" units"));});
                ui.small("Before capture, move beyond A, then approach A in the sweep direction to reduce hysteresis.");
                ui.horizontal(|ui|{ui.label("Shutter timeout");ui.add(egui::DragValue::new(&mut self.plan.capture_timeout_s).range(5..=3600).suffix(" s"));});
                if ui.button("Choose journal folder…").clicked()
                    && let Some(path)=rfd::FileDialog::new().set_title("Local capture journals (no photographs)").pick_folder(){self.root=path;}
            });
            ui.label(RichText::new(self.root.display().to_string()).size(10.0).color(MUTED));
            if self.button(ui,"export","Copy metadata to SD…",!s.phase.active()&&s.journal.as_ref().is_some_and(|p|p.join("result.json").exists()))
                && let Some(folder)=rfd::FileDialog::new().set_title("Choose the mounted SD card or RAW folder").pick_folder(){self.send(s,Action::Export{folder});
            }
            ui.small("Use a card reader after disconnecting. A new STREHL folder receives metadata only.");
        });
        Self::section(ui, "CAMERA");
        ui.horizontal_wrapped(|ui| {
            if let Some(b) = property(&s.status, "BatteryRemain").filter(|v| *v <= 100) {
                ui.small(format!("Battery {b}%"));
            }
            if let Some(n) = property(&s.status, "MediaSLOT1_RemainingNumber") {
                ui.small(format!("Card ~{n} remaining"));
            }
        });
        ui.label(
            RichText::new("A7C II · single RAW per plane")
                .size(11.0)
                .color(MUTED),
        );
        ui.label(
            RichText::new("Pixel shift is unavailable on this camera.")
                .size(11.0)
                .color(MUTED),
        );
        if !s.connected {
            ui.small("If discovery says found 0: close other camera apps, use Remote Shoot (PC Remote), and install the included Sony USB driver.");
        }
    }
    fn update_texture(&mut self, ctx: &egui::Context, s: &Snapshot) {
        if s.preview.is_none() || !s.connected {
            self.texture = None;
            self.texture_generation = u64::MAX;
            return;
        }
        if self.texture_generation == s.preview_generation {
            return;
        }
        let Some(preview) = &s.preview else {
            return;
        };
        let rgb = &preview.rgb;
        let mut data = rgb.as_raw().clone();
        if self.peaking && rgb.width() > 4 && rgb.height() > 4 {
            let luma = |x: u32, y: u32| {
                let p = rgb.get_pixel(x, y);
                (u16::from(p[0]) + 2 * u16::from(p[1]) + u16::from(p[2])) / 4
            };
            for y in 2..rgb.height() - 2 {
                for x in 2..rgb.width() - 2 {
                    let d = luma(x - 1, y).abs_diff(luma(x + 1, y))
                        + luma(x, y - 1).abs_diff(luma(x, y + 1));
                    if d > 55 {
                        let at = ((y * rgb.width() + x) * 3) as usize;
                        data[at..at + 3].copy_from_slice(&[230, 180, 80]);
                    }
                }
            }
        }
        let image =
            egui::ColorImage::from_rgb([rgb.width() as usize, rgb.height() as usize], &data);
        if let Some(texture) = &mut self.texture {
            texture.set(image, egui::TextureOptions::LINEAR);
        } else {
            self.texture =
                Some(ctx.load_texture("live-camera-preview", image, egui::TextureOptions::LINEAR));
        }
        self.texture_generation = s.preview_generation;
    }
    fn viewer(&mut self, ui: &mut egui::Ui, s: &Snapshot) {
        ui.horizontal(|ui| {
            ui.label(RichText::new("LIVE VIEW").size(10.0).color(MUTED));
            if self.button(ui, "fit", "Fit", true) {
                self.zoom = 1.0;
                self.center = egui::pos2(0.5, 0.5);
            }
            ui.add(
                egui::Slider::new(&mut self.zoom, 1.0..=8.0)
                    .suffix("× preview")
                    .show_value(true),
            );
            let peak = ui.checkbox(&mut self.peaking, "Preview edges");
            self.widgets.insert("peaking".into(), peak.rect);
            if peak.changed() {
                self.texture_generation = u64::MAX;
            }
        });
        ui.horizontal_wrapped(|ui| {
            if let Some(preview) = &s.preview {
                let age = s
                    .preview_at
                    .map(|t| t.elapsed().as_secs_f32())
                    .unwrap_or(f32::INFINITY);
                ui.label(
                    RichText::new(format!(
                        "{} × {} · {}",
                        preview.rgb.width(),
                        preview.rgb.height(),
                        if age < 1.0 {
                            "live".into()
                        } else {
                            format!("last frame {age:.0}s ago")
                        }
                    ))
                    .size(11.0)
                    .color(if age < 2.0 { GREEN } else { AMBER }),
                );
            }
            if let Some(error) = &s.preview_error {
                ui.label(RichText::new(error).size(11.0).color(AMBER));
            }
        });
        let magnifier = &s.status["properties"]["Focus_Magnifier_Setting"];
        if magnifier["writable"] == true
            && let Some(allowed) = magnifier["allowed"].as_array()
        {
            ui.horizontal_wrapped(|ui| {
                ui.small("Camera magnifier:");
                for ratio in allowed
                    .iter()
                    .filter_map(|v| v.as_u64().map(|n| (n >> 32) as u32))
                    .take(8)
                {
                    if self.button(
                        ui,
                        &format!("mag-{ratio}"),
                        &format!("{:.1}×", ratio as f32 / 10.0),
                        s.phase.can_edit(),
                    ) {
                        self.send(
                            s,
                            Action::Magnify {
                                ratio,
                                x: (self.center.x * 639.0).round() as u16,
                                y: (self.center.y * 479.0).round() as u16,
                            },
                        );
                    }
                }
            });
        }
        let space =
            ui.available_size() - egui::vec2(0.0, if s.samples.is_empty() { 28.0 } else { 104.0 });
        let (canvas, _) =
            ui.allocate_exact_size(space.max(Vec2::splat(10.0)), egui::Sense::hover());
        ui.painter()
            .rect_filled(canvas, 0.0, Color32::from_rgb(10, 13, 19));
        if let Some(texture) = &self.texture {
            let aspect = texture.size_vec2().x / texture.size_vec2().y;
            let size = if canvas.width() / canvas.height() > aspect {
                egui::vec2(canvas.height() * aspect, canvas.height())
            } else {
                egui::vec2(canvas.width(), canvas.width() / aspect)
            };
            let rect = Rect::from_center_size(canvas.center(), size);
            let half = 0.5 / self.zoom;
            self.center.x = self.center.x.clamp(half, 1.0 - half);
            self.center.y = self.center.y.clamp(half, 1.0 - half);
            let uv = Rect::from_center_size(self.center, Vec2::splat(1.0 / self.zoom));
            ui.painter().image(texture.id(), rect, uv, Color32::WHITE);
            let response =
                ui.interact(rect, ui.id().with("preview"), egui::Sense::click_and_drag());
            self.widgets.insert("preview".into(), rect);
            let select = self.choose_roi || ui.input(|i| i.modifiers.shift);
            if response.drag_started() && select && self.zoom == 1.0 {
                self.roi_drag = response.interact_pointer_pos();
            }
            if select && self.zoom == 1.0 {
                if let (Some(a), Some(b)) = (self.roi_drag, response.interact_pointer_pos()) {
                    let selection = Rect::from_two_pos(a, b).intersect(rect);
                    ui.painter().rect_stroke(
                        selection,
                        0.0,
                        egui::Stroke::new(1.0_f32, ACCENT),
                        egui::StrokeKind::Inside,
                    );
                    if response.drag_stopped() {
                        let roi = Roi {
                            x: (selection.left() - rect.left()) / rect.width(),
                            y: (selection.top() - rect.top()) / rect.height(),
                            width: selection.width() / rect.width(),
                            height: selection.height() / rect.height(),
                        };
                        if roi.valid() {
                            self.roi = roi;
                        }
                        self.roi_drag = None;
                        self.choose_roi = false;
                    }
                }
            } else if response.dragged() {
                let d = response.drag_delta();
                self.center -= egui::vec2(
                    d.x / rect.width() / self.zoom,
                    d.y / rect.height() / self.zoom,
                );
            }
            if response.double_clicked() {
                self.zoom = 1.0;
                self.center = egui::pos2(0.5, 0.5);
            }
            if self.zoom == 1.0 {
                let region = Rect::from_min_size(
                    rect.min + egui::vec2(self.roi.x * rect.width(), self.roi.y * rect.height()),
                    egui::vec2(
                        self.roi.width * rect.width(),
                        self.roi.height * rect.height(),
                    ),
                );
                ui.painter().rect_stroke(
                    region,
                    0.0,
                    egui::Stroke::new(1.0_f32, ACCENT.linear_multiply(0.6)),
                    egui::StrokeKind::Inside,
                );
            }
            if self.demo {
                ui.painter().text(
                    rect.left_bottom() + egui::vec2(12.0, -12.0),
                    egui::Align2::LEFT_BOTTOM,
                    "SIMULATED PREVIEW",
                    egui::FontId::monospace(11.0),
                    ACCENT,
                );
            }
        } else {
            ui.painter().text(
                canvas.center() - egui::vec2(0.0, 18.0),
                egui::Align2::CENTER_CENTER,
                "Bring the subject into focus",
                egui::FontId::proportional(23.0),
                INK,
            );
            ui.painter().text(
                canvas.center() + egui::vec2(0.0, 18.0),
                egui::Align2::CENTER_CENTER,
                "Connect the camera to begin a live preview.",
                egui::FontId::proportional(13.0),
                MUTED,
            );
        }
        ui.label(RichText::new("Drag to pan when enlarged · Shift-drag a subject region at Fit · Double-click to fit").size(10.0).color(MUTED));
        if !s.samples.is_empty() {
            self.curves(ui, s);
        }
    }
    fn curves(&self, ui: &mut egui::Ui, s: &Snapshot) {
        ui.label(
            RichText::new("THROUGH-FOCUS PREVIEW · local texture, not measured resolution")
                .size(10.0)
                .color(MUTED),
        );
        let (rect, _) =
            ui.allocate_exact_size(egui::vec2(ui.available_width(), 58.0), egui::Sense::hover());
        let max = s
            .samples
            .iter()
            .flat_map(|v| v.scores.iter())
            .copied()
            .fold(0.00001_f32, f32::max);
        for tile in 0..strehl_capture::bounds::TILES {
            let points: Vec<_> = s
                .samples
                .iter()
                .enumerate()
                .map(|(i, sample)| {
                    egui::pos2(
                        rect.left() + i as f32 / (s.samples.len() - 1).max(1) as f32 * rect.width(),
                        rect.bottom() - sample.scores[tile] / max * rect.height(),
                    )
                })
                .collect();
            ui.painter().add(egui::Shape::line(
                points,
                egui::Stroke::new(1.0_f32, ACCENT.linear_multiply(0.25)),
            ));
        }
    }
}
impl eframe::App for App {
    fn update(&mut self, ctx: &egui::Context, _: &mut eframe::Frame) {
        self.draw(ctx);
    }
}
