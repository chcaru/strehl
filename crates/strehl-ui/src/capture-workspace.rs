//! Native Capture workspace: camera controls, preview and PC storage in one tab.
use crate::{
    capture_client::{Config, Connection, Snapshot},
    theme::{ACCENT, AMBER, BG, GREEN, INK, MUTED, PANEL},
};
use eframe::egui::{self, RichText};
use serde_json::{Value, json};
use std::{path::PathBuf, sync::mpsc};
use strehl_capture::{
    model::{Plan, Roi},
    session::{Command, CommandRequest},
};

pub(crate) struct CaptureWorkspace {
    config: Config,
    path: PathBuf,
    connection: Option<Connection>,
    pub error: Option<String>,
    texture: Option<(u64, egui::TextureHandle)>,
    draft: Plan,
    draft_revision: u64,
    draft_dirty: bool,
    acknowledge_uncertain: bool,
    zoom: f32,
    select_roi: bool,
    roi_start: Option<egui::Pos2>,
    folder_picker: Option<mpsc::Receiver<Option<PathBuf>>>,
    folder_draft: String,
    folder_dirty: bool,
    selected_stack: usize,
}
impl CaptureWorkspace {
    pub fn new(path: Option<PathBuf>) -> Self {
        let path = path.unwrap_or_else(crate::capture_client::default_path);
        let loaded = Config::load(&path);
        let error = loaded.as_ref().err().map(|e| format!("{e:#}"));
        Self {
            config: loaded.unwrap_or_default(),
            path,
            connection: None,
            error,
            texture: None,
            draft: Plan::default(),
            draft_revision: 0,
            draft_dirty: false,
            acknowledge_uncertain: false,
            zoom: 1.0,
            select_roi: false,
            roi_start: None,
            folder_picker: None,
            folder_draft: String::new(),
            folder_dirty: false,
            selected_stack: 0,
        }
    }
    pub fn activate(&mut self, ctx: &egui::Context) {
        if self.connection.is_none() {
            match Connection::start(self.config.clone(), self.path.clone(), ctx.clone()) {
                Ok(connection) => self.connection = Some(connection),
                Err(e) => self.error = Some(format!("{e:#}")),
            }
        }
    }
    pub fn snapshot(&self) -> Value {
        self.connection
            .as_ref()
            .map_or(json!({"online":false,"initialized":false}), |c| {
                c.snapshot().public()
            })
    }
    pub fn ready_for_screenshot(&self) -> bool {
        self.connection.as_ref().is_some_and(|c| {
            let s = c.snapshot();
            let receiver_checked = !s.receiver.is_null() || s.receiver_error.is_some();
            receiver_checked
                && ((s.observed.is_some()
                    && (s.preview.is_some() || s.state["preview"]["available"] != true))
                    || s.connection_error.is_some()
                    || self.config.controller.is_empty())
        })
    }
    pub fn submit(&mut self, request: CommandRequest) -> anyhow::Result<()> {
        self.connection
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("Open Capture first"))?
            .command(request)
    }
    pub fn import_completed(&mut self, index: usize) -> anyhow::Result<()> {
        let c = self
            .connection
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("Open Capture first"))?;
        let s = c.snapshot();
        let stack = s
            .completed
            .get(index)
            .ok_or_else(|| anyhow::anyhow!("Completed stack unavailable"))?;
        c.handoff(stack.folder.clone())
    }
    pub fn take_handoff(&self) -> Option<PathBuf> {
        self.connection.as_ref()?.take_handoff()
    }
    pub fn start_receiver(&self) -> anyhow::Result<()> {
        self.connection
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("Open Capture first"))?
            .start_receiver()
    }
    pub fn set_compression(&self, compressed: bool) -> anyhow::Result<()> {
        let c = self
            .connection
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("Open Capture first"))?;
        let s = c.snapshot();
        let folder = s.receiver["folder"]
            .as_str()
            .ok_or_else(|| anyhow::anyhow!("Receiver unavailable"))?;
        c.storage(folder.into(), compressed)
    }
    fn command(&mut self, s: &Snapshot, command: Command) {
        let result = s.request(command).and_then(|r| self.submit(r));
        self.record(result);
    }
    fn record(&mut self, result: anyhow::Result<()>) {
        self.error = result.err().map(|e| format!("{e:#}"));
    }
    pub fn show(&mut self, ctx: &egui::Context, can_import: bool) {
        self.activate(ctx);
        let s = self
            .connection
            .as_ref()
            .map(Connection::snapshot)
            .unwrap_or_default();
        if !self.draft_dirty
            && let Ok(plan) = serde_json::from_value(s.state["plan"].clone())
        {
            self.draft = plan;
            self.draft_revision = s.state["plan_revision"].as_u64().unwrap_or(0);
        }
        if !self.folder_dirty {
            self.folder_draft = s.receiver["folder"].as_str().unwrap_or_default().into();
        }
        if let Some(result) = self
            .folder_picker
            .as_ref()
            .and_then(|rx| rx.try_recv().ok())
        {
            self.folder_picker = None;
            if let Some(path) = result {
                self.folder_draft = path.display().to_string();
                self.folder_dirty = true;
            }
        }
        if let Some((generation, image)) = &s.preview
            && self.texture.as_ref().is_none_or(|(g, _)| g != generation)
        {
            let image = image.as_ref().clone();
            match &mut self.texture {
                Some((g, texture)) => {
                    texture.set(image, egui::TextureOptions::LINEAR);
                    *g = *generation;
                }
                None => {
                    self.texture = Some((
                        *generation,
                        ctx.load_texture(
                            "capture-live-preview",
                            image,
                            egui::TextureOptions::LINEAR,
                        ),
                    ))
                }
            }
        }
        egui::SidePanel::left("capture-controls")
            .default_width(310.0)
            .width_range(290.0..=430.0)
            .frame(egui::Frame::new().fill(PANEL).inner_margin(16))
            .show(ctx, |ui| {
                egui::ScrollArea::vertical()
                    .id_salt("capture-controls-scroll")
                    .show(ui, |ui| {
                        ui.label(RichText::new("CAPTURE").color(ACCENT).size(12.0).strong());
                        ui.add_space(12.0);
                        self.connection_ui(ui, &s);
                        ui.add_space(12.0);
                        ui.separator();
                        ui.add_space(10.0);
                        self.focus_ui(ui, &s);
                        ui.add_space(12.0);
                        ui.separator();
                        ui.add_space(10.0);
                        self.storage_ui(ui, &s);
                        ui.add_space(12.0);
                        ui.separator();
                        ui.add_space(10.0);
                        self.completed_ui(ui, &s, can_import);
                    });
            });
        egui::CentralPanel::default()
            .frame(egui::Frame::new().fill(BG).inner_margin(20))
            .show(ctx, |ui| {
                self.sequence_ui(ui, &s);
                ui.add_space(12.0);
                ui.horizontal(|ui| {
                    ui.label(RichText::new("LIVE VIEW").color(MUTED).size(11.0));
                    if ui.selectable_label(self.zoom == 1.0, "Fit").clicked() {
                        self.zoom = 1.0;
                    }
                    ui.add(
                        egui::Slider::new(&mut self.zoom, 1.0..=4.0)
                            .suffix("×")
                            .show_value(true),
                    );
                    ui.add_enabled_ui(
                        s.fresh() && s.state["editable"] == true && !s.pending,
                        |ui| {
                            ui.toggle_value(&mut self.select_roi, "Select subject");
                        },
                    );
                });
                self.preview_ui(ui, &s);
            });
    }
    fn connection_ui(&mut self, ui: &mut egui::Ui, s: &Snapshot) {
        let connected = s.state["connected"] == true;
        ui.horizontal(|ui| {
            ui.colored_label(
                if s.fresh() { GREEN } else { AMBER },
                if s.fresh() {
                    "●  Pi online"
                } else {
                    "○  Pi offline"
                },
            );
            if s.state["demo"] == true {
                ui.label(RichText::new("SIMULATOR").color(AMBER));
            }
        });
        ui.label(
            RichText::new(s.state["camera_model"].as_str().unwrap_or(if connected {
                "Camera connected"
            } else {
                "Camera not connected"
            }))
            .strong()
            .size(18.0),
        );
        ui.horizontal(|ui| {
            if ui
                .add_enabled(
                    s.fresh() && !connected && !s.pending,
                    egui::Button::new("Connect camera"),
                )
                .clicked()
            {
                self.command(s, Command::Connect {});
            }
            if ui
                .add_enabled(
                    s.fresh() && connected && s.state["editable"] == true && !s.pending,
                    egui::Button::new("Disconnect"),
                )
                .clicked()
            {
                self.command(s, Command::Disconnect {});
            }
        });
        egui::CollapsingHeader::new("Connection settings").default_open(self.config.controller.is_empty()).show(ui,|ui| {
            ui.label("Pi address or pairing link");
            ui.add(egui::TextEdit::singleline(&mut self.config.controller).desired_width(f32::INFINITY).hint_text("http://10.0.0.178:8787"));
            ui.label("Pairing key");
            ui.add(egui::TextEdit::singleline(&mut self.config.pairing_key).password(true).desired_width(f32::INFINITY));
            ui.label("Local subnet");ui.text_edit_singleline(&mut self.config.lan);
            ui.label("Receiver configuration on this PC");
            let mut receiver_path=self.config.receiver_config.display().to_string();
            if ui.add(egui::TextEdit::singleline(&mut receiver_path).desired_width(f32::INFINITY)).changed(){self.config.receiver_config=receiver_path.into();}
            if ui.add_enabled(!s.pending,egui::Button::new("Save connection")).clicked() {
                let result=self.config.normalize().and_then(|()|self.connection.as_ref().unwrap().configure(self.config.clone()));
                self.record(result); self.texture=None;
            }
            ui.small("LAN only. Use the same pairing key as your phone. Closing Strehl leaves the Pi's sequence running.");
        });
        if let Some(error) = &s.connection_error {
            ui.colored_label(AMBER, error);
        }
    }
    fn focus_ui(&mut self, ui: &mut egui::Ui, s: &Snapshot) {
        ui.label(RichText::new("Focus bounds").strong());
        ui.label(format!(
            "Position  {}",
            s.state["position"]
                .as_u64()
                .map_or("—".into(), |p| p.to_string())
        ));
        let editable = s.fresh() && s.state["editable"] == true && !s.pending;
        ui.add_enabled_ui(editable,|ui| {
            ui.horizontal(|ui| {
                for (label,delta) in [("−128",-128),("−16",-16),("−1",-1),("+1",1),("+16",16),("+128",128)] {
                    if ui.small_button(label).clicked(){self.command(s,Command::Jog{delta});}
                }
            });
            for (start,label,key) in [(true,"Start","start_set"),(false,"End","end_set")] {
                ui.horizontal(|ui| {
                    let position=if start{self.draft.start}else{self.draft.end};
                    ui.label(format!("{label}  {}",if s.state[key]==true{position.to_string()}else{"not set".into()}));
                    if ui.button(format!("Mark {label}")).clicked(){self.command(s,Command::Mark{start});}
                    if ui.add_enabled(s.state[key]==true,egui::Button::new("Go")).clicked(){self.command(s,Command::Go{start});}
                });
            }
            ui.small("Move focus until the first and last details are sharp, then mark each bound.");
            ui.add_space(8.0);
            egui::Grid::new("capture-plan").num_columns(2).spacing([10.0,8.0]).show(ui,|ui| {
                ui.label("Step size");self.draft_dirty|=ui.add(egui::DragValue::new(&mut self.draft.step).range(1..=65535)).changed();ui.end_row();
                ui.label("Settle time");self.draft_dirty|=ui.add(egui::DragValue::new(&mut self.draft.settle_ms).range(100..=30000).suffix(" ms")).changed();ui.end_row();
            });
            ui.small("1 is the smallest normalized camera step. Lens response is not a calibrated distance.");
            egui::CollapsingHeader::new("Sequence settings").show(ui,|ui| {
                ui.horizontal(|ui|{ui.label("Approach"); self.draft_dirty|=ui.add(egui::DragValue::new(&mut self.draft.approach).range(1..=4096)).changed();});
                ui.horizontal(|ui|{ui.label("Capture timeout");self.draft_dirty|=ui.add(egui::DragValue::new(&mut self.draft.capture_timeout_s).range(5..=3600).suffix(" s")).changed();});
            });
            if self.draft_dirty {
                ui.horizontal(|ui| {
                    if ui.button("Apply settings").clicked(){
                        let command=Command::Settings{step:self.draft.step,settle_ms:self.draft.settle_ms,approach:self.draft.approach,capture_timeout_s:self.draft.capture_timeout_s};
                        let result=s.request(command).and_then(|mut r|{r.plan_revision=self.draft_revision;self.submit(r)});
                        if result.is_ok(){self.draft_dirty=false;} self.record(result);
                    }
                    if ui.button("Discard edits").clicked(){self.draft_dirty=false;}
                });
            }
            let bounds=s.state["start_set"]==true && s.state["end_set"]==true;
            if ui.add_enabled(bounds && s.state["preview"]["fresh"]==true,egui::Button::new("Survey focus within these bounds")).clicked(){self.command(s,Command::Survey{});}
            ui.small("Survey uses the selected subject region to suggest tighter bounds. Set a broad range first.");
            if let Some(suggestion)=s.state["suggestion"].as_object() {
                ui.label(suggestion.get("explanation").and_then(Value::as_str).unwrap_or("Focus survey finished"));
                if ui.add_enabled(s.state["suggestion"]["clipped"]!=true,egui::Button::new("Use suggested bounds")).clicked(){self.command(s,Command::ApplyBounds{});}
            }
            if let Some(ratios)=s.state["magnifier_ratios"].as_array().filter(|r|!r.is_empty()) {
                egui::CollapsingHeader::new("Camera magnifier").show(ui,|ui| {
                    ui.horizontal_wrapped(|ui| {for ratio in ratios.iter().filter_map(Value::as_u64) {
                        if ui.button(if ratio==0{"Off".into()}else{format!("{:.1}×",ratio as f32/10.0)}).clicked(){
                            let roi: Roi=serde_json::from_value(s.state["roi"].clone()).unwrap_or_default();
                            self.command(s,Command::Magnify{ratio:ratio as u32,x:((roi.x+roi.width/2.0)*639.0).round() as u16,y:((roi.y+roi.height/2.0)*479.0).round() as u16});
                        }
                    }});
                });
            }
        });
    }
    fn storage_ui(&mut self, ui: &mut egui::Ui, s: &Snapshot) {
        ui.label(RichText::new("Storage on this PC").strong());
        let available = s.receiver["ok"] == true;
        let checking = s.receiver.is_null() && s.receiver_error.is_none();
        ui.colored_label(
            if available {
                GREEN
            } else if checking {
                MUTED
            } else {
                AMBER
            },
            if available {
                "Receiver ready · runs in background"
            } else if checking {
                "Checking receiver…"
            } else {
                "Receiver unavailable"
            },
        );
        if !available
            && !checking
            && ui
                .add_enabled(!s.pending, egui::Button::new("Start receiver"))
                .clicked()
        {
            let result = self.connection.as_ref().unwrap().start_receiver();
            self.record(result);
        }
        if !available && let Some(error) = &s.receiver_error {
            ui.small(error);
        }
        ui.small("RAWs go directly to this PC. Keep this PC awake and connected while capturing.");
        let free = s.receiver["free_bytes"].as_u64().unwrap_or(0);
        if available {
            ui.label(format!("{:.1} GB free", free as f64 / 1e9));
        }
        ui.add_enabled_ui(available && !s.pending, |ui| {
            self.folder_dirty |= ui
                .add(
                    egui::TextEdit::singleline(&mut self.folder_draft).desired_width(f32::INFINITY),
                )
                .changed();
            ui.horizontal(|ui| {
                if ui
                    .add_enabled(
                        self.folder_picker.is_none(),
                        egui::Button::new("Choose folder…"),
                    )
                    .clicked()
                {
                    let (tx, rx) = mpsc::channel();
                    self.folder_picker = Some(rx);
                    std::thread::spawn(move || {
                        let _ = tx.send(
                            rfd::FileDialog::new()
                                .set_title("Save new captures here")
                                .pick_folder(),
                        );
                    });
                }
                if ui
                    .add_enabled(self.folder_dirty, egui::Button::new("Save folder"))
                    .clicked()
                {
                    let result = self.connection.as_ref().unwrap().storage(
                        PathBuf::from(&self.folder_draft),
                        s.receiver["compress_raw"] != false,
                    );
                    if result.is_ok() {
                        self.folder_dirty = false;
                    }
                    self.record(result);
                }
            });
            let mut compressed = s.receiver["compress_raw"] != false;
            if ui
                .checkbox(&mut compressed, "Keep RAWs losslessly compressed")
                .changed()
                && let Some(folder) = s.receiver["folder"].as_str()
            {
                let result = self
                    .connection
                    .as_ref()
                    .unwrap()
                    .storage(folder.into(), compressed);
                self.record(result);
            }
        });
        ui.small("Strehl opens .ARW.straw directly. Changes apply to new stacks.");
        if let Some(receipt) = s.state["storage"]["receipt"].as_object() {
            if let Some(rate) = receipt.get("wire_MB_per_second").and_then(Value::as_f64) {
                ui.label(format!("Last transfer  {rate:.1} MB/s on Wi-Fi"));
            }
            if let (Some(raw), Some(stored)) = (
                receipt.get("bytes").and_then(Value::as_f64),
                receipt.get("storage_bytes").and_then(Value::as_f64),
            ) && raw > 0.0
            {
                ui.label(format!("Space saved  {:.0}%", 100.0 * (1.0 - stored / raw)));
            }
        }
    }
    fn completed_ui(&mut self, ui: &mut egui::Ui, s: &Snapshot, can_import: bool) {
        ui.label(RichText::new("Completed captures").strong());
        if s.completed.is_empty() {
            ui.small("Completed, durably saved stacks will appear here.");
            return;
        }
        self.selected_stack = self.selected_stack.min(s.completed.len() - 1);
        egui::ComboBox::from_id_salt("capture-completed")
            .width(ui.available_width() - 15.0)
            .selected_text(
                s.completed[self.selected_stack]
                    .folder
                    .file_name()
                    .unwrap_or_default()
                    .to_string_lossy(),
            )
            .show_ui(ui, |ui| {
                for (i, stack) in s.completed.iter().enumerate() {
                    ui.selectable_value(
                        &mut self.selected_stack,
                        i,
                        stack
                            .folder
                            .file_name()
                            .unwrap_or_default()
                            .to_string_lossy(),
                    );
                }
            });
        let stack = &s.completed[self.selected_stack];
        ui.small(format!(
            "{} focal planes · {} RAWs · {} per plane",
            stack.planes, stack.frames, stack.shots_per_plane
        ));
        if ui
            .add_enabled(
                can_import && !s.pending,
                egui::Button::new("Open in Projects"),
            )
            .clicked()
        {
            let result = self.import_completed(self.selected_stack);
            self.record(result);
        }
        ui.small("Open the complete bracket for processing. Streaming reconstruction comes next.");
    }
    fn sequence_ui(&mut self, ui: &mut egui::Ui, s: &Snapshot) {
        let phase = s.state["phase"].as_str().unwrap_or("disconnected");
        let total = s.state["total"]
            .as_u64()
            .filter(|v| *v > 0)
            .or_else(|| s.state["planned"].as_u64())
            .unwrap_or(0);
        let complete = s.state["completed"].as_u64().unwrap_or(0);
        let shots = s.state["shots_per_plane"].as_u64().unwrap_or(1);
        ui.horizontal(|ui| {
            ui.heading("Capture studio");
            ui.label(
                RichText::new(if shots > 1 {
                    format!("{shots}-shot pixel shift")
                } else {
                    "Single RAW per plane".into()
                })
                .color(ACCENT),
            );
            ui.colored_label(if s.fresh() { GREEN } else { AMBER }, phase.to_uppercase());
        });
        ui.label(
            s.state["message"]
                .as_str()
                .unwrap_or("Connect the Pi to begin"),
        );
        if let Some(error) = self.error.as_ref().or(s.command_error.as_ref()) {
            ui.colored_label(AMBER, error);
        }
        let failure = &s.state["failure"];
        if failure.is_object() {
            ui.colored_label(
                AMBER,
                failure["message"]
                    .as_str()
                    .unwrap_or("Capture needs attention"),
            );
            let uncertain = failure["exposure_uncertain"] == true;
            if uncertain {
                ui.checkbox(
                    &mut self.acknowledge_uncertain,
                    "I checked the last exposure; recover without replaying it",
                );
            }
            if ui
                .add_enabled(
                    s.fresh() && !s.pending && (!uncertain || self.acknowledge_uncertain),
                    egui::Button::new("Recover camera"),
                )
                .clicked()
            {
                self.command(
                    s,
                    Command::Recover {
                        acknowledge_uncertain: self.acknowledge_uncertain,
                    },
                );
                self.acknowledge_uncertain = false;
            }
        }
        let active = matches!(phase, "capturing" | "paused" | "scanning");
        ui.horizontal(|ui| {
            let start = s.fresh()
                && s.state["editable"] == true
                && s.state["start_set"] == true
                && s.state["end_set"] == true
                && s.state["plan_error"].is_null()
                && !self.draft_dirty
                && (s.receiver["ok"] == true || s.state["demo"] == true);
            if ui
                .add_enabled(
                    start && !s.pending,
                    egui::Button::new(RichText::new("Start stack").color(BG)).fill(ACCENT),
                )
                .clicked()
            {
                self.command(s, Command::Start {});
            }
            if phase == "paused" {
                if ui
                    .add_enabled(s.fresh() && !s.pending, egui::Button::new("Resume"))
                    .clicked()
                {
                    self.command(s, Command::Resume {});
                }
            } else if ui
                .add_enabled(
                    s.fresh()
                        && phase == "capturing"
                        && !s.pending
                        && s.state["pending_control"] != 1,
                    egui::Button::new("Pause"),
                )
                .clicked()
            {
                self.command(s, Command::Pause {});
            }
            if ui
                .add_enabled(
                    s.fresh() && active && !s.pending && s.state["pending_control"] != 2,
                    egui::Button::new("Stop"),
                )
                .clicked()
            {
                self.command(s, Command::Stop {});
            }
            if s.pending {
                ui.spinner();
                ui.label("Sending…");
            }
            ui.label(format!(
                "{} / {} planes · {} RAWs saved",
                complete,
                total,
                s.state["storage"]["saved_frames"].as_u64().unwrap_or(0)
            ));
        });
        if let Some(error) = s.state["plan_error"].as_str() {
            ui.colored_label(AMBER, error);
        }
        let percent = if total > 0 {
            complete as f32 / total as f32
        } else {
            0.0
        };
        ui.add(egui::ProgressBar::new(percent.clamp(0.0, 1.0)).desired_height(4.0));
        ui.horizontal_wrapped(|ui| {
            ui.label(format!(
                "Elapsed {}",
                duration(s.state["timer"]["elapsed"].as_f64())
            ));
            let remaining = s.state["timer"]["remaining"]
                .as_f64()
                .or_else(|| s.state["initial_seconds"].as_f64());
            ui.label(format!("Estimated remaining {}", duration(remaining)));
            if let Some(queued) = s.state["storage"]["pending_frames"].as_u64() {
                ui.label(format!("{queued} RAWs awaiting PC"));
            }
            if shots > 1 && active {
                ui.small("Pause / stop finishes the current pixel-shift group.");
            }
        });
    }
    fn preview_ui(&mut self, ui: &mut egui::Ui, s: &Snapshot) {
        if let Some(error) = s
            .preview_error
            .as_deref()
            .or_else(|| s.state["preview"]["error"].as_str())
        {
            // Decoder errors are independent of focus controls.
            if !error.is_empty() {
                ui.colored_label(AMBER, error);
            }
        }
        if s.state["preview"]["fresh"] != true && self.texture.is_some() {
            ui.colored_label(AMBER, "Last preview · waiting for a fresh camera frame");
        }
        let Some((_, texture)) = &self.texture else {
            ui.centered_and_justified(|ui|{ui.label(RichText::new("Live preview appears here\nFocus controls remain available if preview is interrupted.").color(MUTED));});
            return;
        };
        let texture = texture.clone();
        let available = ui.available_size();
        let fit = (available.x / texture.size_vec2().x)
            .min((available.y - 22.0).max(50.0) / texture.size_vec2().y);
        let size = texture.size_vec2() * fit * self.zoom;
        egui::ScrollArea::both()
            .id_salt("capture-preview-scroll")
            .auto_shrink([false, false])
            .show(ui, |ui| {
                let response = ui.add(
                    egui::Image::new((texture.id(), size)).sense(egui::Sense::click_and_drag()),
                );
                let r = response.rect;
                let roi: Roi = serde_json::from_value(s.state["roi"].clone()).unwrap_or_default();
                let region = egui::Rect::from_min_size(
                    r.min + egui::vec2(roi.x * r.width(), roi.y * r.height()),
                    egui::vec2(roi.width * r.width(), roi.height * r.height()),
                );
                ui.painter().rect_stroke(
                    region,
                    0.0,
                    egui::Stroke::new(1.0_f32, ACCENT),
                    egui::StrokeKind::Inside,
                );
                if self.select_roi && s.fresh() && s.state["editable"] == true && !s.pending {
                    if response.drag_started() {
                        self.roi_start = response.interact_pointer_pos();
                    }
                    if let (Some(start), Some(end)) =
                        (self.roi_start, response.interact_pointer_pos())
                    {
                        let region = egui::Rect::from_two_pos(start, end).intersect(r);
                        ui.painter().rect_stroke(
                            region,
                            0.0,
                            egui::Stroke::new(2.0_f32, INK),
                            egui::StrokeKind::Inside,
                        );
                        if response.drag_stopped() {
                            let roi = Roi {
                                x: (region.left() - r.left()) / r.width(),
                                y: (region.top() - r.top()) / r.height(),
                                width: region.width() / r.width(),
                                height: region.height() / r.height(),
                            };
                            if roi.width >= 0.05 && roi.height >= 0.05 {
                                self.command(s, Command::Roi { roi });
                                self.select_roi = false;
                            }
                            self.roi_start = None;
                        }
                    }
                }
            });
    }
}
fn duration(seconds: Option<f64>) -> String {
    let Some(seconds) = seconds.filter(|s| s.is_finite() && *s >= 0.0) else {
        return "—".into();
    };
    let n = seconds.round() as u64;
    format!("{:02}:{:02}:{:02}", n / 3600, n / 60 % 60, n % 60)
}
