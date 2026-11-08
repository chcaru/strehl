use crate::theme::*;
use eframe::egui::{self, Color32, Rect, RichText, Vec2};
use std::{
    collections::BTreeMap,
    net::SocketAddr,
    path::PathBuf,
    sync::{Arc, Mutex},
    time::{Duration, Instant},
};
use strehl_capture::{
    backend::property,
    model::{Phase, Roi},
    remote::WebServer,
    session::{Controls, Session},
    timing,
    worker::{Action, PAUSE, STOP, Snapshot, Worker},
};

pub struct App {
    pub worker: Arc<Worker>,
    pub controls: Arc<Mutex<Controls>>,
    session: Arc<Session>,
    web: Option<WebServer>,
    pub web_bind: SocketAddr,
    web_visible: bool,
    web_address: usize,
    qr: Option<egui::TextureHandle>,
    qr_url: String,
    pub demo: bool,
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
    close_revision: Option<u64>,
    recovery_ack: bool,
    recovery_message: String,
}
impl App {
    pub fn new(worker: Worker, root: PathBuf, demo: bool) -> Self {
        let worker = Arc::new(worker);
        let controls = Arc::new(Mutex::new(Controls::new(root)));
        let session = Arc::new(Session::new(worker.clone(), controls.clone(), demo));
        Self {
            worker,
            controls,
            session,
            web: None,
            web_bind: "0.0.0.0:8787".parse().unwrap(),
            web_visible: false,
            web_address: 0,
            qr: None,
            qr_url: String::new(),
            demo,
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
            close_revision: None,
            recovery_ack: false,
            recovery_message: String::new(),
        }
    }
    fn send(&mut self, s: &Snapshot, action: Action) {
        self.local_message = None;
        if let Err(e) = self.worker.send(s.revision, action) {
            self.local_message = Some(e.to_string());
        }
    }
    pub fn control_snapshot(&self) -> Controls {
        self.controls.lock().unwrap().clone()
    }
    pub fn web_enabled(&self) -> bool {
        self.web.is_some()
    }
    fn web_panel(&mut self, ctx: &egui::Context) {
        if !self.web_visible {
            return;
        }
        let mut visible = self.web_visible;
        egui::Window::new("Web remote")
            .open(&mut visible).resizable(false).default_width(460.0)
            .show(ctx, |ui| {
                ui.label("Control this capture session from a phone or another computer.");
                ui.small("The camera stays connected to this laptop. Keep Strehl Capture open.");
                ui.add_space(8.0);
                if self.web.is_none() {
                    if self.button(ui,"web-enable","Enable web remote",true) {
                        match WebServer::start(self.session.clone(),self.web_bind) {
                            Ok(server) => {self.web=Some(server);self.web_address=0;self.local_message=None;},
                            Err(e) => self.local_message=Some(format!("{e:#}")),
                        }
                    }
                } else {
                    if self.button(ui,"web-disable","Disable and revoke links",true) {
                        self.web=None;self.qr=None;self.qr_url.clear();return;
                    }
                    let addresses=self.web.as_ref().unwrap().addresses.clone();
                    self.web_address=self.web_address.min(addresses.len()-1);
                    egui::ComboBox::from_id_salt("web-address")
                        .selected_text(&addresses[self.web_address].label)
                        .show_ui(ui,|ui|{for (index,address) in addresses.iter().enumerate() {
                            ui.selectable_value(&mut self.web_address,index,&address.label);
                        }});
                    let address=&addresses[self.web_address];
                    let base=address.url.split('#').next().unwrap();
                    ui.label(RichText::new(base).monospace().color(ACCENT));
                    if self.qr_url!=address.url && let Ok(code)=qrcode::QrCode::new(address.url.as_bytes()) {
                            let width=code.width();let size=width+8;
                            let mut pixels=vec![Color32::WHITE;size*size];
                            for y in 0..width { for x in 0..width {
                                if code[(x,y)]==qrcode::Color::Dark {pixels[(y+4)*size+x+4]=Color32::BLACK;}
                            }}
                            let image=egui::ColorImage::new([size,size],pixels);
                            self.qr=Some(ctx.load_texture("pairing-qr",image,egui::TextureOptions::NEAREST));
                            self.qr_url=address.url.clone();
                    }
                    if let Some(qr)=&self.qr {ui.add(egui::Image::new(qr).fit_to_exact_size(Vec2::splat(220.0)));}
                    ui.horizontal(|ui| {
                        if ui.button("Copy pairing link").clicked(){ctx.copy_text(address.url.clone());}
                        if ui.button("Open on this laptop").clicked(){ctx.open_url(egui::OpenUrl::new_tab(self.web.as_ref().unwrap().local_url()));}
                    });
                    ui.small("Scan the QR or open the copied link. It grants control until web remote is disabled or the app closes.");
                    ui.add_space(8.0);
                    ui.label(RichText::new("Access while away").color(ACCENT));
                    ui.label("Install Tailscale on this laptop and your phone / other computer, and sign in to the same account. Enable it on both devices, then select ‘Away · Tailscale’ above.");
                    if !addresses.iter().any(|a|a.label.contains("Tailscale")) {
                        ui.small("Tailscale is not connected here. After connecting it, disable and re-enable web remote to find its address.");
                    }
                    ui.hyperlink_to("Tailscale setup guide","https://tailscale.com/docs/how-to/quickstart");
                    ui.small("Nearby: use the same Wi-Fi/LAN. If blocked, see START-HERE.md for the narrow Windows firewall rule. Away: no router port forwarding is needed.");
                }
            });
        self.web_visible = visible;
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
        let shared = self.controls.clone();
        let mut settings = shared.lock().unwrap();
        let s = self.worker.snapshot();
        settings.sync_connection(&s);
        let before = settings.clone();
        if ctx.input(|i| i.viewport().close_requested())
            && (s.connected || s.phase.active() || s.command_pending)
        {
            ctx.send_viewport_cmd(egui::ViewportCommand::CancelClose);
            self.closing = true;
            self.worker.request_stop();
        }
        if self.closing {
            if !s.connected && !s.phase.active() && !s.command_pending {
                ctx.send_viewport_cmd(egui::ViewportCommand::Close);
            } else if !s.phase.active()
                && !s.command_pending
                && self.close_revision != Some(s.revision)
            {
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
                            !s.phase.active() && !s.command_pending,
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
                        if self.button(ui, "web-remote", "Web remote", true) {
                            self.web_visible = true;
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
            .exact_height(86.0)
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
                if let Some(timing) = &s.timing {
                    let response = ui.label(
                        RichText::new(timing.label(Instant::now(), s.phase == Phase::Paused))
                            .monospace()
                            .color(ACCENT),
                    );
                    self.widgets.insert("countdown".into(), response.rect);
                } else {
                    ui.small(
                        "Time estimates update from completed captures; paused time is excluded.",
                    );
                }
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
                self.recovery_controls(ui, &s);
                egui::ScrollArea::vertical()
                    .id_salt("capture-controls")
                    .auto_shrink([false, false])
                    .show(ui, |ui| self.controls(ui, &s, &mut settings));
            });
        egui::CentralPanel::default()
            .frame(
                egui::Frame::new()
                    .fill(BG)
                    .inner_margin(egui::Margin::same(16)),
            )
            .show(ctx, |ui| self.viewer(ui, &s, &mut settings));
        if *settings != before {
            settings.revision += 1;
        }
        drop(settings);
        self.web_panel(ctx);
        ctx.request_repaint_after(Duration::from_millis(80));
    }
    fn recovery_controls(&mut self, ui: &mut egui::Ui, s: &Snapshot) {
        if let Some(error) = &s.failure {
            if self.recovery_message != *error {
                self.recovery_message = error.clone();
                self.recovery_ack = false;
            }
            Self::section(ui, "CAMERA NEEDS ATTENTION");
            ui.label(RichText::new(error).color(AMBER));
            ui.small(format!(
                "{} / {} captures confirmed. Existing RAWs and the journal are kept.",
                s.completed, s.total
            ));
            if s.exposure_uncertain {
                ui.small("The last exposure may be on the card. Wait for camera/card activity to finish and inspect the SD card before reconnecting.");
                let response = ui.checkbox(
                    &mut self.recovery_ack,
                    "Camera is idle; I checked the uncertain exposure",
                );
                self.widgets.insert("recovery-ack".into(), response.rect);
            }
            if self.button(
                ui,
                "recover-camera",
                "Reconnect camera",
                matches!(s.phase, Phase::Fault | Phase::Disconnected)
                    && !s.command_pending
                    && (!s.exposure_uncertain || self.recovery_ack),
            ) {
                self.send(
                    s,
                    Action::Recover {
                        acknowledge_uncertain: self.recovery_ack,
                    },
                );
            }
            ui.small("Reconnect does not take a photo. Review both focus marks afterward; Start makes a new stack from A.");
            ui.separator();
        } else {
            self.recovery_ack = false;
            self.recovery_message.clear();
        }
    }
    fn controls(&mut self, ui: &mut egui::Ui, s: &Snapshot, settings: &mut Controls) {
        let editable = s.phase.can_edit() && !s.command_pending;
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
                            settle_ms: settings.plan.settle_ms,
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
                        let set = if start { settings.start_set } else { settings.end_set };
                        let value = if start {
                            settings.plan.start
                        } else {
                            settings.plan.end
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
                            editable && s.connected && s.position.is_some(),
                        ) {
                            if start {
                                settings.plan.start = s.position.unwrap();
                                settings.start_set = true;
                            } else {
                                settings.plan.end = s.position.unwrap();
                                settings.end_set = true;
                            }
                        }
                        let set = if start { settings.start_set } else { settings.end_set };
                        let target = if start {
                            settings.plan.start
                        } else {
                            settings.plan.end
                        };
                        if self.button(
                            ui,
                            if start { "go-start" } else { "go-end" },
                            "Go to mark",
                            editable && set,
                        ) {
                            let from=i32::from(target)-settings.plan.direction()*i32::from(settings.plan.approach);
                            if let Ok(approach_from)=u16::try_from(from) {
                                self.send(s,Action::Inspect{target,approach_from,settle_ms:settings.plan.settle_ms});
                            }else{self.local_message=Some("Shorten Approach to inspect this mark without crossing the lens limit".into());}
                        }
                    });
                });
        }
        if editable && (s.preview_error.is_some() || s.preview_at.is_none()) {
            ui.label(RichText::new("Preview unavailable. Use the camera display to inspect focus; Mark current still records the reported position.").size(11.0).color(AMBER));
        }
        Self::section(ui, "CAPTURE PLAN");
        ui.add_enabled_ui(
            !s.phase.active() && !s.command_pending && s.phase != Phase::Fault,
            |ui| {
                egui::Grid::new("plan-settings")
                    .num_columns(2)
                    .spacing([15.0, 8.0])
                    .show(ui, |ui| {
                        ui.label("Focus step");
                        ui.add(
                            egui::DragValue::new(&mut settings.plan.step)
                                .range(1..=65535)
                                .speed(1.0)
                                .suffix(" units"),
                        );
                        ui.end_row();
                        ui.label("Settle after move");
                        ui.add(
                            egui::DragValue::new(&mut settings.plan.settle_ms)
                                .range(100..=30000)
                                .speed(25.0)
                                .suffix(" ms"),
                        );
                        ui.end_row();
                    });
            },
        );
        ui.label(
            RichText::new(
                "1 is the smallest command. Adjacent positions can repeat the same physical focus.",
            )
            .size(11.0)
            .color(MUTED),
        );
        let positions = if settings.start_set && settings.end_set {
            settings.plan.positions()
        } else {
            Err(anyhow::anyhow!("Mark both focus boundaries"))
        };
        match &positions {
            Ok(p) => {
                ui.label(
                    RichText::new(format!(
                        "{} RAWs · {} sweep",
                        p.len(),
                        if settings.plan.end >= settings.plan.start {
                            "increasing"
                        } else {
                            "decreasing"
                        }
                    ))
                    .color(ACCENT),
                );
                if !s.phase.active()
                    && let Some(cycle) = property(&s.status, "ShutterSpeed")
                        .and_then(|shutter| timing::initial_cycle(shutter, settings.plan.settle_ms))
                {
                    let estimate = cycle.mul_f64(p.len() as f64)
                        + timing::initial_setup(settings.plan.settle_ms);
                    ui.label(RichText::new(format!("Initial estimate ~{}", timing::format_duration(estimate))).size(11.0).color(MUTED))
                        .on_hover_text("Rough shutter + settle + camera/SD allowance. The countdown learns actual cadence during capture.");
                }
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
                        plan: settings.plan.clone(),
                        root: settings.root.clone(),
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
        let fresh_preview = s.preview_error.is_none()
            && s.preview_at
                .is_some_and(|time| time.elapsed() < Duration::from_secs(2));
        ui.horizontal(|ui| {
            if self.button(
                ui,
                "select-roi",
                if self.choose_roi {
                    "Draw a rectangle…"
                } else {
                    "Select subject"
                },
                editable && fresh_preview,
            ) {
                self.choose_roi = !self.choose_roi;
                self.zoom = 1.0;
            }
            if self.button(
                ui,
                "scan",
                "Sweep preview",
                editable
                    && fresh_preview
                    && settings.start_set
                    && settings.end_set
                    && settings.plan.start.abs_diff(settings.plan.end) >= 8,
            ) {
                self.worker.request_resume();
                self.send(
                    s,
                    Action::Scan {
                        plan: settings.plan.clone(),
                        roi: settings.roi,
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
                settings.plan.start = suggestion.start;
                settings.plan.end = suggestion.end;
                settings.start_set = true;
                settings.end_set = true;
            }
        }
        ui.add_space(5.0);
        egui::CollapsingHeader::new("Approach, timeout & storage").show(ui,|ui|{
            ui.add_enabled_ui(!s.phase.active() && !s.command_pending,|ui|{
                ui.horizontal(|ui|{ui.label("Approach");ui.add(egui::DragValue::new(&mut settings.plan.approach).range(1..=4096).suffix(" units"));});
                ui.small("Before capture, move beyond A, then approach A in the sweep direction to reduce hysteresis.");
                ui.horizontal(|ui|{ui.label("Shutter timeout");ui.add(egui::DragValue::new(&mut settings.plan.capture_timeout_s).range(5..=3600).suffix(" s"));});
                if ui.button("Choose journal folder…").clicked()
                    && let Some(path)=rfd::FileDialog::new().set_title("Local capture journals (no photographs)").pick_folder(){settings.root=path;}
            });
            ui.label(RichText::new(settings.root.display().to_string()).size(10.0).color(MUTED));
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
    fn viewer(&mut self, ui: &mut egui::Ui, s: &Snapshot, settings: &mut Controls) {
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
                            settings.roi = roi;
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
                    rect.min
                        + egui::vec2(
                            settings.roi.x * rect.width(),
                            settings.roi.y * rect.height(),
                        ),
                    egui::vec2(
                        settings.roi.width * rect.width(),
                        settings.roi.height * rect.height(),
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
                if s.connected {
                    "Waiting for live preview"
                } else {
                    "Bring the subject into focus"
                },
                egui::FontId::proportional(23.0),
                INK,
            );
            ui.painter().text(
                canvas.center() + egui::vec2(0.0, 18.0),
                egui::Align2::CENTER_CENTER,
                if s.connected {
                    "You can still jog focus and mark both bounds using the camera display."
                } else {
                    "Connect the camera to begin a live preview."
                },
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
