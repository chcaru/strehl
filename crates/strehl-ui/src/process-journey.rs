//! A persistent map of the work, with counters only where the engine supplies them.
//! The phase anchor follows the pipeline, while quiet work lanes show overlapping
//! reads, scale separation and folds. Kernel events never move the phase anchor.
//! A received sample is evidence, not a whole-phase completion estimate.
use crate::{
    pipeline::{AlignmentPhase, DiagnosticKind, PipelineProgress, RenderStep, Stage, WorkState},
    theme::{ACCENT, AMBER, GREEN, INK, LINE, MUTED},
};
use eframe::egui::{self, Align2, FontId, Rect, Sense, Stroke, Ui};

pub(crate) const HEIGHT: f32 = 80.0;
const TITLES: [&str; 6] = [
    "READ",
    "REGISTER",
    "SEPARATE",
    "COMBINE",
    "RECONSTRUCT",
    "DEVELOP + SAVE",
];

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
enum State {
    #[default]
    Waiting,
    Observed,
    Active,
    Finished,
    Bypassed,
    Stopped,
}

#[derive(Clone, Debug)]
struct Node {
    title: Option<&'static str>,
    state: State,
    value: String,
    unit: &'static str,
    detail: String,
    work: String,
    fraction: Option<f32>,
    help: String,
}
impl Default for Node {
    fn default() -> Self {
        Self {
            title: None,
            state: State::Waiting,
            value: "—".into(),
            unit: "awaiting observation",
            detail: String::new(),
            work: String::new(),
            fraction: None,
            help: "No observation received for this operation yet.".into(),
        }
    }
}
impl Node {
    fn count(&mut self, done: usize, total: usize, unit: &'static str) {
        self.value = format!("{done} / {total}");
        self.unit = unit;
        self.fraction = (total > 0).then(|| (done as f32 / total as f32).clamp(0.0, 1.0));
        self.state = State::Observed;
    }
}

#[derive(Default)]
pub(crate) struct ProcessJourney {
    epoch: Option<u64>,
    reconstruction_seen: bool,
    reconstruction_finished: bool,
    develop_seen: bool,
    write_seen: bool,
    write_finished: bool,
    active: Option<usize>,
}

impl ProcessJourney {
    pub(crate) fn show(
        &mut self,
        ui: &mut Ui,
        rect: Rect,
        epoch: u64,
        progress: &PipelineProgress,
    ) {
        let nodes = self.observe(epoch, progress);
        let width = rect.width() / nodes.len() as f32;
        for (index, node) in nodes.iter().enumerate() {
            let title = node.title.unwrap_or(TITLES[index]);
            let cell = Rect::from_min_size(
                rect.min + egui::vec2(index as f32 * width, 0.0),
                egui::vec2(width, rect.height().min(HEIGHT)),
            );
            let painter = ui.painter_at(cell.shrink2(egui::vec2(3.0, 0.0)));
            if node.state == State::Active {
                painter.rect_filled(
                    cell.shrink2(egui::vec2(3.0, 2.0)),
                    0.0,
                    crate::theme::RAISED,
                );
                painter.text(
                    cell.right_top() + egui::vec2(-8.0, 11.0),
                    Align2::RIGHT_CENTER,
                    "LIVE",
                    FontId::monospace(6.8),
                    ACCENT,
                );
            }
            let colour = match node.state {
                State::Active => ACCENT,
                State::Finished | State::Observed => GREEN,
                State::Stopped | State::Bypassed => AMBER,
                State::Waiting => MUTED,
            };
            let origin = cell.min + egui::vec2(7.0, 0.0);
            let centre = origin + egui::vec2(5.0, 11.0);
            painter.circle_stroke(centre, 4.0, Stroke::new(1.0_f32, colour));
            if matches!(
                node.state,
                State::Finished | State::Observed | State::Active
            ) {
                painter.circle_filled(centre, 2.0, colour);
            }
            if index < nodes.len() - 1 {
                painter.line_segment(
                    [
                        origin + egui::vec2(17.0, 21.0),
                        egui::pos2(cell.right() - 5.0, origin.y + 21.0),
                    ],
                    Stroke::new(0.6_f32, LINE),
                );
                let tip = egui::pos2(cell.right() - 5.0, origin.y + 21.0);
                painter.line_segment(
                    [tip - egui::vec2(3.0, 2.0), tip],
                    Stroke::new(0.6_f32, LINE),
                );
            }
            painter.text(
                origin + egui::vec2(16.0, 11.0),
                Align2::LEFT_CENTER,
                title,
                FontId::proportional(if width < 118.0 { 7.5 } else { 9.5 }),
                if node.state == State::Waiting {
                    MUTED
                } else {
                    colour
                },
            );
            painter.text(
                origin + egui::vec2(0.0, 26.0),
                Align2::LEFT_TOP,
                &node.value,
                FontId::monospace(if width < 118.0 { 10.0 } else { 12.0 }),
                if node.state == State::Waiting {
                    MUTED
                } else {
                    INK
                },
            );
            for (text, y, size, color) in [
                (node.unit, 40.0, 9.0, MUTED),
                (node.detail.as_str(), 52.0, 9.0, colour),
                (node.work.as_str(), 64.0, 8.0, MUTED),
            ] {
                let line = Rect::from_min_max(
                    origin + egui::vec2(0.0, y),
                    egui::pos2(cell.right() - 7.0, origin.y + y + 12.0),
                );
                if !text.is_empty() && line.is_positive() {
                    let mut job = egui::text::LayoutJob::simple(
                        text.to_owned(),
                        FontId::proportional(size),
                        color,
                        line.width(),
                    );
                    job.wrap.max_rows = 1;
                    job.wrap.break_anywhere = true;
                    job.wrap.overflow_character = Some('…');
                    let galley = painter.layout_job(job);
                    let position = line.min - galley.rect.min.to_vec2();
                    painter
                        .with_clip_rect(line.intersect(painter.clip_rect()))
                        .galley(position, galley, color);
                }
            }
            if let Some(fraction) = node.fraction {
                let start = origin + egui::vec2(0.0, 75.0);
                let end = egui::pos2(cell.right() - 10.0, start.y);
                painter.line_segment([start, end], Stroke::new(1.0_f32, LINE));
                if fraction > 0.0 {
                    painter.line_segment(
                        [start, start + (end - start) * fraction],
                        Stroke::new(1.5_f32, colour),
                    );
                }
            }
            ui.interact(
                cell,
                ui.id().with(("process-journey", index)),
                Sense::hover(),
            )
            .on_hover_text(format!(
                "{}\n{}\n\n{}",
                title,
                [
                    node.value.as_str(),
                    node.unit,
                    node.detail.as_str(),
                    node.work.as_str()
                ]
                .into_iter()
                .filter(|line| !line.is_empty())
                .collect::<Vec<_>>()
                .join("\n"),
                node.help,
            ));
        }
    }

    fn observe(&mut self, epoch: u64, p: &PipelineProgress) -> [Node; 6] {
        if self.epoch != Some(epoch) {
            *self = Self {
                epoch: Some(epoch),
                ..Self::default()
            };
        }
        if p.diagnostic_surfaces
            .iter()
            .any(|s| s.kind == DiagnosticKind::Reconstructed)
        {
            self.reconstruction_seen = true;
            self.reconstruction_finished = true;
        }
        match p.render_step {
            Some(RenderStep::Reconstruct) => {
                self.reconstruction_seen = true;
                self.reconstruction_finished |= p.render_step_state == Some(WorkState::Finished);
            }
            Some(RenderStep::Develop) => self.develop_seen = true,
            Some(RenderStep::Write) => {
                self.write_seen = true;
                self.write_finished |= p.render_step_state == Some(WorkState::Finished);
            }
            None => (),
        }
        let mut nodes = std::array::from_fn(|_| Node::default());
        let decoded = p
            .merge_frame_observations
            .values()
            .filter(|frame| frame.decode == Some(WorkState::Finished))
            .count();
        let pyramids = p
            .merge_frame_observations
            .values()
            .filter(|frame| frame.pyramid == Some(WorkState::Finished))
            .count();

        let read = &mut nodes[0];
        if let Some((done, total)) = p.alignment_planes {
            read.count(done, total, "alignment frames read");
            read.help = format!(
                "{done} of {total} alignment input reads completed. The separate merge decode observer has reported {decoded} finished RAW reads; those identities are sampled, not a total."
            );
        } else if decoded > 0 {
            read.value = format!("{decoded} observed");
            read.unit = "merge RAW reads";
            read.state = State::Observed;
            read.help = "Finished RAW decode events actually received. These frame events are sampled, so this is not a whole-stack fraction.".into();
        } else if let Some(total) = p.frames_total {
            read.value = format!("{total} RAW");
            read.unit = "capture inputs";
            read.help = "Number of input frames, not the number already decoded.".into();
        }
        read.detail = if decoded > 0 {
            format!("{decoded} merge reads observed")
        } else {
            String::new()
        };

        let register = &mut nodes[1];
        if let Some((done, accepted, total)) = p.alignment_pairs {
            register.count(done, total, "pair comparisons");
            register.detail = format!("{accepted} direct fits");
            register.help = format!(
                "{done} of {total} planned pair comparisons completed, including refused fits. {accepted} comparisons produced accepted direct fits. This bar measures comparisons, not placement accuracy."
            );
        }
        if let Some(placed) = p.placed {
            if p.alignment_pairs.is_none() {
                register.value = p
                    .frames_total
                    .map_or_else(|| placed.to_string(), |total| format!("{placed} / {total}"));
                register.unit = "frames placed";
                register.help = "Frames placed by the reported alignment result. No pair-work fraction is invented for a cached or externally supplied solution.".into();
            }
            register.detail = format!("{placed} placed · {} refused", p.refused.unwrap_or(0));
            register.state = State::Finished;
        }
        if p.alignment_phase == Some(AlignmentPhase::Bypassed) {
            register.state = State::Bypassed;
            register.value = "BYPASSED".into();
            register.unit = "no fitted placement";
            register.detail = String::new();
            register.fraction = None;
            register.help = "The engine explicitly bypassed alignment. This does not imply a solved or validated placement.".into();
        }

        let separate = &mut nodes[2];
        if pyramids > 0 {
            separate.state = State::Observed;
            separate.value = format!("{pyramids} observed");
            separate.unit = "frame pyramids";
            separate.help = "Completed merge pyramid events actually received. Per-frame kernel events are sampled; no all-frames percentage is inferred from them.".into();
        }
        if let Some(bands) = p.bands {
            separate.detail = format!("{} image scales", bands + 1);
            if pyramids == 0 {
                separate.value = (bands + 1).to_string();
                separate.unit = "planned image scales";
                separate.help = "Configured detail bands plus the coarse base. A scale plan does not claim any frame has finished its pyramid.".into();
            }
        }

        let combine = &mut nodes[3];
        if let (Some(done), Some(total)) = (p.frames_processed, p.frames_total) {
            combine.count(done, total, "frames processed");
            combine.detail = p
                .frames_accepted
                .map(|n| format!("{n} accepted into stack"))
                .unwrap_or_default();
            combine.help = "Engine cumulative processed-frame count, including refused frames. Accepted frames are shown separately. Per-scale fold counts remain in the scale ledger; a completed frame is not a completed photograph.".into();
        } else if let Some((done, total)) = p.folded {
            combine.count(done, total, "frames in fold summary");
            combine.help = "Engine terminal fold summary. Refused frames may be included; it does not establish that reconstruction or saving has started.".into();
        }
        if let Some((done, total)) = p.frames_processed.zip(p.frames_total)
            && done == total
        {
            combine.state = State::Finished;
        }

        let reconstruct = &mut nodes[4];
        if self.reconstruction_seen {
            reconstruct.value = if self.reconstruction_finished {
                "PLANES READY"
            } else {
                "REBUILDING"
            }
            .into();
            reconstruct.unit = "merged sensor planes";
            reconstruct.state = if self.reconstruction_finished {
                State::Finished
            } else {
                State::Observed
            };
            reconstruct.detail = "scales → sensor image".into();
            reconstruct.help = "Actual reconstruction event or measured reconstructed-green packet. There is no reported within-reconstruction denominator.".into();
        }

        let save = &mut nodes[5];
        let confidence_active = p
            .confidence
            .as_ref()
            .is_some_and(|pass| pass.state == WorkState::Started)
            && !self.develop_seen
            && !self.write_seen;
        if let Some(pass) = &p.confidence {
            save.work = format!(
                "{} compared · {} refused",
                pass.compared,
                pass.completed - pass.compared
            );
            if !self.develop_seen && !self.write_seen {
                save.title = Some("CONFIDENCE");
                save.count(pass.completed, pass.total, "source attempts");
                save.detail = save.work.clone();
                save.work = pass.last_frame.map_or_else(
                    || "green observations → merge".into(),
                    |(frame, mapped)| {
                        format!(
                            "F{:03} {}",
                            frame + 1,
                            if mapped {
                                "→ merged green"
                            } else {
                                "refused"
                            }
                        )
                    },
                );
                save.help = format!(
                    "{} of {} source attempts completed in the confidence pass. {} mapped frames were compared with reconstructed green luma; {} attempts were refused before comparison. This measures the observation-balance map, not photographic quality or pixel coverage. A complete pass is not a saved photograph.",
                    pass.completed,
                    pass.total,
                    pass.compared,
                    pass.completed - pass.compared
                );
            }
        }
        if self.develop_seen || self.write_seen {
            save.value = if self.write_finished {
                "TIFF WRITTEN"
            } else if self.write_seen {
                "COLOUR + TIFF"
            } else {
                "PREPARING"
            }
            .into();
            save.unit = if self.write_finished {
                "awaiting output check"
            } else {
                "colour development"
            };
            save.state = State::Observed;
            save.fraction = None;
            save.detail = "sensor image → photograph".into();
            save.help = "The write operation includes colour development and TIFF output. No separate pixel, byte or within-write percentage is reported. Saved completion waits for the owned job's terminal success.".into();
        }
        if p.stage == Stage::Complete {
            save.value = "SAVED".into();
            save.unit = "finished photograph";
            save.detail = "TIFF checked + saved".into();
            save.state = State::Finished;
        }

        if p.stage == Stage::Merge {
            merge_work_lanes(&mut nodes, p);
        }

        let active = match p.stage {
            Stage::Preparing if p.observed_stages.contains(&Stage::Preparing) => Some(0),
            Stage::Alignment => match p.alignment_phase {
                Some(AlignmentPhase::Planes) => Some(0),
                Some(AlignmentPhase::Complete | AlignmentPhase::Bypassed) => None,
                Some(_) => Some(1),
                None => None,
            },
            // Merge workers overlap: a read or focus event is not a return to
            // an earlier phase. Keep this anchor through started/finished gaps
            // and through the final fold, until reconstruction really begins.
            Stage::Merge => Some(3),
            Stage::Rendering if confidence_active => Some(5),
            Stage::Rendering
                if p.confidence.is_some() && !self.develop_seen && !self.write_seen =>
            {
                None
            }
            Stage::Rendering if p.render_step_state == Some(WorkState::Started) => {
                p.render_step.map(|step| match step {
                    RenderStep::Reconstruct => 4,
                    RenderStep::Develop | RenderStep::Write => 5,
                })
            }
            _ => None,
        };
        if let Some(index) = active {
            nodes[index].state = State::Active;
            nodes[index].detail = match p.stage {
                Stage::Preparing => "reading sensor profile".into(),
                Stage::Alignment => {
                    if p.alignment_phase == Some(AlignmentPhase::Pairs) {
                        p.alignment_pairs
                            .map(|(_, accepted, _)| format!("{accepted} direct fits"))
                            .unwrap_or_default()
                    } else {
                        p.alignment_phase
                            .map(|phase| phase.title().to_owned())
                            .unwrap_or_default()
                    }
                }
                // Preserve the accepted count. Actual sampled kernel work has
                // its own quiet line and never replaces accumulated progress.
                Stage::Merge => nodes[index].detail.clone(),
                Stage::Rendering => {
                    if confidence_active {
                        nodes[index].detail.clone()
                    } else if index == 4 {
                        "reconstructing planes".into()
                    } else if p.render_step == Some(RenderStep::Write) {
                        "developing + writing".into()
                    } else {
                        "preparing colour".into()
                    }
                }
                _ => String::new(),
            };
        }
        if matches!(p.stage, Stage::Failed | Stage::Cancelled) {
            if let Some(index) = self.active {
                nodes[index].state = State::Stopped;
                nodes[index].detail = if p.stage == Stage::Failed {
                    "stopped with error"
                } else {
                    "cancelled"
                }
                .into();
            }
        } else if active.is_some() {
            self.active = active;
        }
        nodes
    }
}

/// In-flight *observations*, not a census of workers. A single capture can be
/// read while another has a scale measured or folded. Focus has no finish event;
/// its observed lane ends when that same capture and scale starts/finishes fold.
fn merge_work_lanes(nodes: &mut [Node; 6], p: &PipelineProgress) {
    let mut counts = [0usize; 6];
    for frame in p.merge_frame_observations.values() {
        counts[0] += usize::from(frame.decode == Some(WorkState::Started));
        counts[1] += usize::from(frame.gather == Some(WorkState::Started));
        counts[2] += usize::from(frame.extract == Some(WorkState::Started));
        counts[3] += usize::from(frame.pyramid == Some(WorkState::Started));
        counts[4] += (frame.focus_started & !(frame.fold_started | frame.fold_finished))
            .count_ones() as usize;
        counts[5] += (frame.fold_started & !frame.fold_finished).count_ones() as usize;
    }
    let preparation = match (counts[2] > 0, counts[3] > 0) {
        (true, false) => "planes",
        (false, true) => "scales",
        _ => "prepare",
    };
    for (index, work) in [
        (0, &[("decode", counts[0]), ("gather", counts[1])][..]),
        (
            2,
            &[(preparation, counts[2] + counts[3]), ("measure", counts[4])][..],
        ),
        (3, &[("fold", counts[5])][..]),
    ] {
        nodes[index].work = work
            .iter()
            .filter(|(_, count)| *count > 0)
            .map(|(name, count)| format!("{name} ×{count}"))
            .collect::<Vec<_>>()
            .join(" · ");
        nodes[index].help.push_str(
            " The quiet work line shows received in-flight frame or scale observations, which may overlap across lanes. They are sampled, not a count of all workers; a missing finish observation can leave a sample open until the phase ends.",
        );
    }
}

#[cfg(test)]
#[path = "process-journey-tests.rs"]
mod tests;
