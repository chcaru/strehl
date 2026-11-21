//! A capture in flight (Studio 2, 7.4; mockup `flight.html`): the headline
//! (plane, bar, time left, finishing time), the proof, the latest plane with
//! its verdict, the last planes from the checker's journal, and the health
//! column with the "when it finishes" switches, Pause, Stop and Glance.
//!
//! The view takes [`FlightInputs`] and returns [`FlightIntent`]s. The
//! numbers are computed by the pure functions here ([`headline`],
//! [`health`], [`recent_planes`], [`flight_ticks`]), which the glance mode
//! shares.
use eframe::egui::{self, Align2, Rect, Sense, TextureId, Ui};
use serde_json::Value;

use super::follow::Progress;
use super::rail::{FlightTicks, TickState};
use super::style::{self, ButtonKind, CapturePalette, Mark};
use crate::capture_client::{Snapshot, host::HostPhase};

/// The headline's numbers.
#[derive(Clone, Debug, Default, PartialEq)]
pub(crate) struct Headline {
    /// Planes done, and planned.
    pub plane: u64,
    pub total: u64,
    pub fraction: f32,
    pub per_plane: Option<f64>,
    pub raws_taken: u64,
    pub raws_total: u64,
    pub elapsed: Option<f64>,
    pub left: Option<f64>,
    pub paused: bool,
}

/// The headline from the host's state.
pub(crate) fn headline(s: &Snapshot) -> Headline {
    let host = &s.host;
    let shots = host.shots();
    let total = host.total.max(host.completed);
    let timer = host.timer.as_ref();
    let elapsed = timer.and_then(|t| t.elapsed);
    let taken = host
        .storage
        .captured_frames
        .unwrap_or(host.completed * shots);
    Headline {
        plane: host.completed,
        total,
        fraction: if total > 0 {
            host.completed as f32 / total as f32
        } else {
            0.0
        },
        per_plane: elapsed
            .filter(|_| host.completed > 0)
            .map(|e| e / host.completed as f64),
        raws_taken: taken,
        raws_total: total * shots,
        elapsed,
        left: timer.and_then(|t| t.remaining),
        paused: host.phase == HostPhase::Paused,
    }
}

/// One line of the health column.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct HealthLine {
    pub title: &'static str,
    pub mark: Mark,
    pub text: String,
    /// The line's bar, when it has one.
    pub fraction: Option<f32>,
}

/// Transfer, checks, disk and rig.
pub(crate) fn health(s: &Snapshot, progress: Option<&Progress>, checking: bool) -> [HealthLine; 4] {
    let host = &s.host;
    let shots = host.shots();
    let storage = &host.storage;
    let taken = storage.captured_frames.unwrap_or(host.completed * shots);
    let saved = storage.saved_frames.unwrap_or(0);
    let behind = storage
        .pending_frames
        .unwrap_or(taken.saturating_sub(saved));
    let rate = storage
        .receipt
        .as_ref()
        .and_then(|r| r.wire_mb_per_second)
        .map(|r| format!(" · {r:.0} MB/s on Wi-Fi"))
        .unwrap_or_default();
    let on_pc = storage.mode.as_deref() == Some("host-pc");
    let transfer = if on_pc {
        HealthLine {
            title: "Transfer",
            mark: if behind > 2 * shots.max(1) * 2 {
                Mark::Warn
            } else {
                Mark::Ok
            },
            text: format!("{saved} of {taken} RAWs on this PC · {behind} behind{rate}"),
            fraction: (taken > 0).then(|| saved as f32 / taken as f32),
        }
    } else {
        HealthLine {
            title: "Transfer",
            mark: Mark::Idle,
            text: format!("{taken} RAWs kept on the camera's card"),
            fraction: None,
        }
    };
    let checks = match (progress, checking) {
        (Some(p), _) => {
            let first = p.passed.saturating_sub(p.retaken);
            let mut text = format!("{} planes checked", p.checked);
            if p.passed > 0 {
                text.push_str(&format!(" · {first} passed first time"));
            }
            if p.retaken > 0 {
                text.push_str(&format!(" · {} retaken", p.retaken));
            }
            if p.attention > 0 {
                text.push_str(&format!(" · {} need attention", p.attention));
            }
            HealthLine {
                title: "Checks",
                mark: if p.attention > 0 {
                    Mark::Warn
                } else {
                    Mark::Ok
                },
                text,
                fraction: (host.completed > 0).then(|| p.checked as f32 / host.completed as f32),
            }
        }
        (None, true) => HealthLine {
            title: "Checks",
            mark: Mark::Idle,
            text: "Starts with the first plane saved on this PC".into(),
            fraction: None,
        },
        (None, false) => HealthLine {
            title: "Checks",
            mark: Mark::Idle,
            text: "Off: the stack is checked when it is opened".into(),
            fraction: None,
        },
    };
    let per_raw = super::plan::expected_per_raw(s);
    let free = s.receiver["free_bytes"].as_u64();
    let disk = if !on_pc {
        HealthLine {
            title: "Disk",
            mark: Mark::Idle,
            text: host.card_remaining.map_or("The camera's card".into(), |n| {
                format!("The camera's card: room for {n} more RAWs")
            }),
            fraction: None,
        }
    } else {
        HealthLine {
            title: "Disk",
            mark: if host.storage_error.is_some() {
                Mark::Warn
            } else {
                Mark::Ok
            },
            text: match (per_raw, free) {
                (Some(b), Some(f)) => format!(
                    "{:.1} of about {} written · {:.0} GB free",
                    (saved * b) as f64 / 1e9,
                    style::gigabytes(host.total * shots * b),
                    f as f64 / 1e9
                ),
                (None, Some(f)) => format!("{saved} RAWs written · {:.0} GB free", f as f64 / 1e9),
                _ => format!("{saved} RAWs written"),
            },
            fraction: (host.total > 0).then(|| saved as f32 / (host.total * shots).max(1) as f32),
        }
    };
    let rig = HealthLine {
        title: "Rig",
        mark: if host.failure.is_some() {
            Mark::Bad
        } else if host.connected {
            Mark::Ok
        } else {
            Mark::Warn
        },
        text: super::plan::rig_summary(s),
        fraction: None,
    };
    [transfer, checks, disk, rig]
}

/// A plane's journal line as the "last planes" list says it: its mark, a
/// sentence and the time its check took.
pub(crate) fn plane_sentence(v: &Value, retaken: bool) -> (Mark, String, Option<String>) {
    let verdict = v["verdict"].as_str().unwrap_or("");
    let members = v["members"].as_u64();
    let (mark, text) = match verdict {
        "pass" if retaken => (Mark::Warn, "retaken, the second try passed".to_owned()),
        "pass" => (
            Mark::Ok,
            format!("{} shots agree", spell(members.unwrap_or(4))),
        ),
        "decoded" => (Mark::Ok, "decoded and aligned".to_owned()),
        "demote" => (
            Mark::Warn,
            v["reason"].as_str().map_or(
                "the stack will use its first shot".to_owned(),
                str::to_owned,
            ),
        ),
        "failed" => (
            Mark::Bad,
            v["reason"]
                .as_str()
                .unwrap_or("could not be read")
                .to_owned(),
        ),
        "incomplete" => (Mark::Idle, "its RAWs did not all arrive".to_owned()),
        other => (Mark::Info, other.to_owned()),
    };
    let seconds = v["seconds"].as_f64().map(|s| format!("{s:.1} s"));
    (mark, text, seconds)
}

fn spell(n: u64) -> String {
    match n {
        1 => "one".into(),
        2 => "two".into(),
        3 => "three".into(),
        4 => "four".into(),
        n => n.to_string(),
    }
}

/// The last `n` planes, newest first: plane number, mark, sentence, timing.
pub(crate) fn recent_planes(p: &Progress, n: usize) -> Vec<(u64, Mark, String, Option<String>)> {
    p.latest(n)
        .map(|(plane, v)| {
            let (mark, text, seconds) = plane_sentence(v, p.retaken_planes.contains(plane));
            (*plane, mark, text, seconds)
        })
        .collect()
}

/// The rail's ticks in flight: each planned plane checked, retaken, needing
/// attention, on the camera host or to come.
pub(crate) fn flight_ticks(
    positions: Vec<u16>,
    s: &Snapshot,
    progress: Option<&Progress>,
) -> FlightTicks {
    let host = &s.host;
    let shots = host.shots().max(1);
    let saved_planes = host
        .storage
        .saved_frames
        .map_or(host.completed, |f| f / shots)
        .min(host.completed);
    let states = (0..positions.len() as u64)
        .map(|i| {
            let plane = i + 1;
            let line = progress.and_then(|p| p.plane(plane));
            if i >= host.completed {
                TickState::ToCome
            } else if progress.is_some_and(|p| p.retaken_planes.contains(&plane)) {
                TickState::Retaken
            } else if let Some(v) = line {
                match v["verdict"].as_str() {
                    Some("pass" | "decoded") => TickState::Checked,
                    Some("incomplete") => TickState::OnHost,
                    _ => TickState::Attention,
                }
            } else if i >= saved_planes {
                TickState::OnHost
            } else {
                TickState::Checked
            }
        })
        .collect();
    FlightTicks {
        positions,
        states,
        revision: 0,
    }
}

/// The overall state in one word, for the inspector's chip.
pub(crate) fn needs_you(s: &Snapshot, health: &[HealthLine; 4]) -> (Mark, &'static str) {
    let host = &s.host;
    if host.failure.is_some() || host.phase == HostPhase::Fault {
        (Mark::Bad, "Needs you")
    } else if host.phase == HostPhase::Paused {
        (Mark::Warn, "Paused")
    } else if health.iter().any(|h| h.mark == Mark::Warn) {
        (Mark::Warn, "Worth a look")
    } else {
        (Mark::Ok, "Nothing needs you")
    }
}

/// Everything the in-flight view shows.
pub(crate) struct FlightInputs<'a> {
    pub s: &'a Snapshot,
    pub progress: Option<&'a Progress>,
    /// The checker is on.
    pub checking: bool,
    /// The proof's texture and what it stands for ("planes 1–61").
    pub proof: Option<(TextureId, egui::Vec2, String)>,
    /// The live preview, as the latest plane's picture.
    pub latest: Option<(TextureId, egui::Vec2)>,
    pub stack_when_done: bool,
    /// "Manage power"; `None` without studio outlets.
    pub power_down: Option<bool>,
    /// Stop was clicked once and waits for its confirmation.
    pub confirm_stop: bool,
}

/// What the user asked of the in-flight view.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum FlightIntent {
    Pause,
    Resume,
    /// The first click on Stop…: ask.
    AskStop,
    /// The confirming click.
    Stop,
    KeepGoing,
    Glance,
    SetStackWhenDone(bool),
    SetPowerDown(bool),
    /// Show a plane (a retaken one) in the stack station.
    ShowPlane(u64),
}

/// The canvas part: headline, proof, latest plane, last planes.
pub(crate) fn canvas(
    ui: &mut Ui,
    inputs: &FlightInputs<'_>,
    palette: &CapturePalette,
) -> Vec<FlightIntent> {
    let mut out = Vec::new();
    let r = ui.max_rect();
    let p = ui.painter().clone();
    p.rect_filled(r, 0.0, palette.surround);
    let h = headline(inputs.s);
    // Headline (24 px margins, 108 high, a hairline beneath).
    let head = Rect::from_min_size(
        r.min + egui::vec2(24.0, 20.0),
        egui::vec2(r.width() - 48.0, 108.0),
    );
    style::hairline(&p, head.left_bottom(), head.right_bottom(), palette.line);
    let base = head.bottom() - 14.0;
    style::paint_job(
        &p,
        egui::pos2(head.left(), base - 64.0 - 8.0),
        Align2::LEFT_BOTTOM,
        style::caps_job("Plane", 10.5, palette.ink3),
    );
    let plane = style::paint_job(
        &p,
        egui::pos2(head.left(), base),
        Align2::LEFT_BOTTOM,
        style::job(&h.plane.to_string(), 64.0, palette.ink, -0.6),
    );
    let of = style::paint_job(
        &p,
        egui::pos2(plane.right() + 10.0, base - 4.0),
        Align2::LEFT_BOTTOM,
        style::job(&format!("of {}", h.total), 20.0, palette.ink3, 0.0),
    );
    let ends_text = h
        .left
        .map(style::local_time_in)
        .unwrap_or_else(|| "—".into());
    let ends = style::paint_job(
        &p,
        egui::pos2(head.right(), base),
        Align2::RIGHT_BOTTOM,
        style::job(&ends_text, 64.0, palette.ink3, -0.6),
    );
    style::paint_job(
        &p,
        egui::pos2(head.right(), base - 72.0),
        Align2::RIGHT_BOTTOM,
        style::caps_job("Ends", 10.5, palette.ink3),
    );
    let left_text = h.left.map(style::clock).unwrap_or_else(|| "—".into());
    let left = style::paint_job(
        &p,
        egui::pos2(ends.left() - 34.0, base),
        Align2::RIGHT_BOTTOM,
        style::job(&left_text, 64.0, palette.ink, -0.6),
    );
    style::paint_job(
        &p,
        egui::pos2(left.right(), base - 72.0),
        Align2::RIGHT_BOTTOM,
        style::caps_job("Left", 10.5, palette.ink3),
    );
    let grow = Rect::from_min_max(
        egui::pos2(of.right() + 34.0, base - 40.0),
        egui::pos2(left.left() - 34.0, base),
    );
    style::bar(
        &p,
        Rect::from_min_size(grow.min, egui::vec2(grow.width(), 8.0)),
        h.fraction,
        palette.ok,
        palette,
    );
    let (mark, state) = if h.paused {
        (Mark::Warn, "Paused")
    } else {
        (Mark::Ok, "On track")
    };
    let row_y = grow.min.y + 8.0 + 8.0 + 8.0;
    style::mark(&p, egui::pos2(grow.left() + 3.5, row_y), mark, 7.0, palette);
    let mut x = grow.left() + 13.0;
    for (text, color) in [
        (state.to_owned(), palette.ink),
        (
            h.per_plane
                .map(|s| format!("{s:.1} s per plane"))
                .unwrap_or_default(),
            palette.ink2,
        ),
        (
            format!("{} of {} RAWs taken", h.raws_taken, h.raws_total),
            palette.ink2,
        ),
    ] {
        if text.is_empty() {
            continue;
        }
        let rr = style::paint_job(
            &p,
            egui::pos2(x, row_y),
            Align2::LEFT_CENTER,
            style::job(&text, 12.5, color, 0.0),
        );
        x = rr.right() + 8.0;
    }
    if let Some(e) = h.elapsed {
        style::paint_job(
            &p,
            egui::pos2(grow.right(), row_y),
            Align2::RIGHT_CENTER,
            style::job(
                &format!("started {}", style::local_time_in(-e)),
                12.5,
                palette.ink2,
                0.0,
            ),
        );
    }
    // The proof and the latest plane.
    let top = head.bottom() + 20.0;
    let side_w = 340.0;
    let proof = Rect::from_min_max(
        egui::pos2(r.left() + 24.0, top),
        egui::pos2(
            r.right() - 24.0 - side_w - 14.0,
            (top + 620.0).min(r.bottom() - 16.0),
        ),
    );
    picture(
        &p,
        proof,
        inputs.proof.as_ref().map(|(t, s, _)| (*t, *s)),
        palette,
    );
    let proof_label = inputs
        .proof
        .as_ref()
        .map(|(_, _, what)| format!("{what} · from the camera previews, not the RAW stack"))
        .unwrap_or_else(|| {
            "appears after the first planes · from the camera previews, not the RAW stack".into()
        });
    label(&p, proof, "Proof so far", &proof_label, palette);
    let side = egui::pos2(proof.right() + 14.0, top);
    let latest = Rect::from_min_size(side, egui::vec2(side_w, 227.0));
    picture(&p, latest, inputs.latest, palette);
    let progress = inputs.progress;
    let newest = progress.and_then(|p| p.latest(1).next());
    let latest_text = match newest {
        Some((plane, v)) => {
            let (_, text, _) = plane_sentence(
                v,
                progress.is_some_and(|p| p.retaken_planes.contains(plane)),
            );
            let focus = v["target"]
                .as_u64()
                .map(|t| format!("focus {} · ", style::focus_units(t as u16)))
                .unwrap_or_default();
            (format!("Plane {plane}"), format!("{focus}{text}"))
        }
        None => (format!("Plane {}", h.plane), "live view".into()),
    };
    label(&p, latest, &latest_text.0, &latest_text.1, palette);
    // The last planes.
    let list = Rect::from_min_max(
        egui::pos2(side.x, latest.bottom() + 17.0),
        egui::pos2(side.x + side_w, r.bottom()),
    );
    style::paint_job(
        &p,
        list.left_top(),
        Align2::LEFT_TOP,
        style::caps_job("Last planes", 10.5, palette.ink3),
    );
    let mut y = list.top() + 22.0;
    style::hairline(
        &p,
        egui::pos2(list.left(), y),
        egui::pos2(list.right(), y),
        palette.line,
    );
    if let Some(progress) = progress {
        for (plane, mark, text, seconds) in recent_planes(progress, 5) {
            let row = Rect::from_min_size(egui::pos2(list.left(), y), egui::vec2(side_w, 34.0));
            style::mark(
                &p,
                egui::pos2(row.left() + 4.0, row.center().y),
                mark,
                7.0,
                palette,
            );
            style::paint_job(
                &p,
                egui::pos2(row.left() + 18.0, row.center().y),
                Align2::LEFT_CENTER,
                style::job(&plane.to_string(), 12.5, palette.ink, 0.2),
            );
            let mut job = style::job(&text, 12.5, palette.ink2, 0.0);
            job.wrap.max_width = side_w - 46.0 - 60.0;
            job.wrap.max_rows = 1;
            style::paint_job(
                &p,
                egui::pos2(row.left() + 52.0, row.center().y),
                Align2::LEFT_CENTER,
                job,
            );
            if mark == Mark::Warn && progress.retaken_planes.contains(&plane) {
                let link = Rect::from_min_size(
                    egui::pos2(row.right() - 40.0, row.top()),
                    egui::vec2(40.0, row.height()),
                );
                let resp = ui.interact(link, ui.id().with(("flight-show", plane)), Sense::click());
                style::paint_job(
                    &p,
                    link.right_center(),
                    Align2::RIGHT_CENTER,
                    style::caps_job(
                        "Show",
                        10.5,
                        if resp.hovered() {
                            palette.ink
                        } else {
                            palette.ink2
                        },
                    ),
                );
                if resp.clicked() {
                    out.push(FlightIntent::ShowPlane(plane));
                }
            } else if let Some(seconds) = seconds {
                style::paint_job(
                    &p,
                    egui::pos2(row.right(), row.center().y),
                    Align2::RIGHT_CENTER,
                    style::job(&seconds, 12.5, palette.ink3, 0.0),
                );
            }
            y = row.bottom();
            style::hairline(
                &p,
                egui::pos2(list.left(), y),
                egui::pos2(list.right(), y),
                palette.line,
            );
        }
    } else {
        style::paint_job(
            &p,
            egui::pos2(list.left(), y + 17.0),
            Align2::LEFT_CENTER,
            style::job("Checking is off", 12.5, palette.ink3, 0.0),
        );
    }
    // G opens glance; Space pauses (the shell may route them elsewhere).
    if !ui.ctx().wants_keyboard_input() {
        ui.input(|i| {
            if i.key_pressed(egui::Key::G) {
                out.push(FlightIntent::Glance);
            }
            if i.key_pressed(egui::Key::Space) {
                out.push(if h.paused {
                    FlightIntent::Resume
                } else {
                    FlightIntent::Pause
                });
            }
        });
    }
    out
}

/// A picture fitted (cover) into `rect`, or an empty frame.
fn picture(
    p: &egui::Painter,
    rect: Rect,
    texture: Option<(TextureId, egui::Vec2)>,
    palette: &CapturePalette,
) {
    p.rect_filled(rect, 0.0, palette.bg);
    if let Some((id, size)) = texture
        && size.x > 0.0
        && size.y > 0.0
    {
        let scale = (rect.width() / size.x).max(rect.height() / size.y);
        let shown = size * scale;
        let uv_w = rect.width() / shown.x;
        let uv_h = rect.height() / shown.y;
        let uv = Rect::from_min_max(
            egui::pos2((1.0 - uv_w) / 2.0, (1.0 - uv_h) / 2.0),
            egui::pos2((1.0 + uv_w) / 2.0, (1.0 + uv_h) / 2.0),
        );
        p.image(id, rect, uv, egui::Color32::WHITE);
    }
    p.rect_stroke(
        rect,
        0.0,
        egui::Stroke::new(1.0_f32, egui::Color32::from_white_alpha(15)),
        egui::StrokeKind::Inside,
    );
}

/// The caption at the foot of a picture (`.lbl`).
fn label(p: &egui::Painter, rect: Rect, name: &str, text: &str, palette: &CapturePalette) {
    let band = Rect::from_min_max(egui::pos2(rect.left(), rect.bottom() - 30.0), rect.max);
    let mut mesh = egui::Mesh::default();
    let clear = egui::Color32::TRANSPARENT;
    let dark = egui::Color32::from_black_alpha(178);
    let i = mesh.vertices.len() as u32;
    for (pos, c) in [
        (band.left_top(), clear),
        (band.right_top(), clear),
        (band.right_bottom(), dark),
        (band.left_bottom(), dark),
    ] {
        mesh.colored_vertex(pos, c);
    }
    mesh.add_triangle(i, i + 1, i + 2);
    mesh.add_triangle(i, i + 2, i + 3);
    p.add(egui::Shape::mesh(mesh));
    let name_rect = style::paint_job(
        p,
        egui::pos2(band.left() + 10.0, band.bottom() - 9.0),
        Align2::LEFT_BOTTOM,
        style::caps_job(name, 10.5, palette.ink),
    );
    style::paint_job(
        p,
        egui::pos2(name_rect.right() + 10.0, band.bottom() - 9.0),
        Align2::LEFT_BOTTOM,
        style::job(text, 12.0, palette.ink.gamma_multiply(0.65), 0.0),
    );
}

/// The inspector part: the health column, the switches and the foot.
pub(crate) fn inspector(
    ui: &mut Ui,
    inputs: &FlightInputs<'_>,
    palette: &CapturePalette,
) -> Vec<FlightIntent> {
    let mut out = Vec::new();
    let full = ui.max_rect();
    ui.painter().rect_filled(full, 0.0, palette.panel);
    style::hairline(
        ui.painter(),
        full.left_top() + egui::vec2(0.5, 0.0),
        full.left_bottom() + egui::vec2(0.5, 0.0),
        palette.line,
    );
    let foot = Rect::from_min_max(egui::pos2(full.left(), full.bottom() - 53.0), full.max);
    let body = Rect::from_min_max(full.min, egui::pos2(full.right(), foot.top()));
    let lines = health(inputs.s, inputs.progress, inputs.checking);
    let (state_mark, state) = needs_you(inputs.s, &lines);
    ui.scope_builder(egui::UiBuilder::new().max_rect(body.shrink2(egui::vec2(16.0, 14.0))), |ui| {
        ui.spacing_mut().item_spacing.y = 0.0;
        section(ui, "In flight", Some((state_mark, state)), palette);
        for line in &lines {
            health_row(ui, line, palette);
        }
        ui.add_space(14.0);
        section(ui, "When it finishes", None, palette);
        ui.add_space(6.0);
        if style::option(ui, inputs.stack_when_done, "Stack it, then show the checks", None, inputs.checking, palette) {
            out.push(FlightIntent::SetStackWhenDone(!inputs.stack_when_done));
        }
        if let Some(down) = inputs.power_down
            && style::option(ui, down, "Power the rig down", Some("after the last RAW is saved"), false, palette)
        {
            out.push(FlightIntent::SetPowerDown(!down));
        }
        ui.add_space(14.0);
        let mut job = style::job("You can leave this page. ", 12.5, palette.ink, 0.0);
        job.append(
            "The capture keeps its place in the bar at the top right while you develop another photograph.",
            0.0,
            egui::TextFormat {
                font_id: egui::FontId::proportional(12.5),
                color: palette.ink2,
                ..Default::default()
            },
        );
        job.wrap.max_width = ui.available_width();
        ui.label(job);
    });
    style::hairline(
        ui.painter(),
        foot.left_top() + egui::vec2(0.0, 0.5),
        foot.right_top() + egui::vec2(0.0, 0.5),
        palette.line,
    );
    let s = inputs.s;
    let host = &s.host;
    let fresh = s.fresh() && !s.pending;
    ui.scope_builder(
        egui::UiBuilder::new()
            .max_rect(foot.shrink2(egui::vec2(16.0, 12.0)))
            .layout(egui::Layout::left_to_right(egui::Align::Center)),
        |ui| {
            ui.spacing_mut().item_spacing.x = 8.0;
            if inputs.confirm_stop {
                let w = ui.available_width() - 100.0 - 8.0;
                if style::button_sized(
                    ui,
                    "Stop now",
                    ButtonKind::Danger,
                    egui::vec2(w, 28.0),
                    fresh && host.phase.active(),
                    palette,
                )
                .clicked()
                {
                    out.push(FlightIntent::Stop);
                }
                if style::button_sized(
                    ui,
                    "Keep going",
                    ButtonKind::Plain,
                    egui::vec2(100.0, 28.0),
                    true,
                    palette,
                )
                .clicked()
                {
                    out.push(FlightIntent::KeepGoing);
                }
                return;
            }
            let paused = host.phase == HostPhase::Paused;
            let w = ui.available_width() - 56.0 - 72.0 - 16.0;
            let pause = style::button_sized(
                ui,
                if paused { "Resume" } else { "Pause" },
                ButtonKind::Plain,
                egui::vec2(w, 28.0),
                fresh
                    && (paused
                        || (host.phase == HostPhase::Capturing && host.pending_control != 1)),
                palette,
            );
            if pause.clicked() {
                out.push(if paused {
                    FlightIntent::Resume
                } else {
                    FlightIntent::Pause
                });
            }
            if style::button_sized(
                ui,
                "Stop…",
                ButtonKind::Danger,
                egui::vec2(56.0, 28.0),
                fresh && host.phase.active() && host.pending_control != 2,
                palette,
            )
            .on_hover_text("Asks first, and keeps the planes already taken")
            .clicked()
            {
                out.push(FlightIntent::AskStop);
            }
            if style::button_sized(
                ui,
                "Glance",
                ButtonKind::Plain,
                egui::vec2(72.0, 28.0),
                true,
                palette,
            )
            .clicked()
            {
                out.push(FlightIntent::Glance);
            }
        },
    );
    out
}

fn section(ui: &mut Ui, title: &str, state: Option<(Mark, &str)>, palette: &CapturePalette) {
    let w = ui.available_width();
    let (r, _) = ui.allocate_exact_size(egui::vec2(w, 24.0), Sense::hover());
    let p = ui.painter();
    style::paint_job(
        p,
        r.left_center(),
        Align2::LEFT_CENTER,
        style::caps_job(title, 10.5, palette.ink3),
    );
    if let Some((mark, text)) = state {
        let t = style::paint_job(
            p,
            r.right_center(),
            Align2::RIGHT_CENTER,
            style::job(text, 12.0, palette.ink, 0.0),
        );
        style::mark(
            p,
            egui::pos2(t.left() - 9.0, r.center().y),
            mark,
            7.0,
            palette,
        );
    }
    style::hairline(p, r.left_bottom(), r.right_bottom(), palette.line);
}

fn health_row(ui: &mut Ui, line: &HealthLine, palette: &CapturePalette) {
    let w = ui.available_width();
    let mut job = style::job(&line.text, 12.5, palette.ink2, 0.0);
    job.wrap.max_width = w - 28.0;
    let galley = ui.painter().layout_job(job);
    let h = 11.0 + 18.0 + galley.size().y + if line.fraction.is_some() { 10.0 } else { 0.0 } + 11.0;
    let (r, _) = ui.allocate_exact_size(egui::vec2(w, h), Sense::hover());
    let p = ui.painter();
    style::mark(
        p,
        egui::pos2(r.left() + 5.0, r.top() + 11.0 + 9.0),
        line.mark,
        7.0,
        palette,
    );
    style::paint_job(
        p,
        egui::pos2(r.left() + 28.0, r.top() + 11.0),
        Align2::LEFT_TOP,
        style::job(line.title, 13.0, palette.ink, 0.2),
    );
    p.galley(
        egui::pos2(r.left() + 28.0, r.top() + 29.0),
        galley.clone(),
        palette.ink2,
    );
    if let Some(f) = line.fraction {
        let y = r.top() + 29.0 + galley.size().y + 8.0;
        style::bar(
            p,
            Rect::from_min_size(egui::pos2(r.left() + 28.0, y), egui::vec2(w - 28.0, 2.0)),
            f,
            if line.mark == Mark::Warn {
                palette.warn
            } else {
                palette.ok
            },
            palette,
        );
    }
    style::hairline(p, r.left_bottom(), r.right_bottom(), palette.line);
}

#[cfg(test)]
#[path = "capture-flight-tests.rs"]
mod tests;
