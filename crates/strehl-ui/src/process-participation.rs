//! Completed-stack spatial admission, in capture order. The linked traces measure
//! sampled area, never a share of the final photograph or coefficient magnitude.
use std::collections::BTreeMap;

use crate::{
    pipeline::Stage,
    process_provenance::{AdmissionArchive, AdmissionMeta},
    process_region_probe::SampleWindow,
    process_space::Input,
    theme::{ACCENT, BG, GREEN, LINE, MUTED},
};
use eframe::egui::{self, Align2, Color32, FontId, Pos2, Rect, Sense, Stroke, TextureHandle, Ui};

pub(crate) const HEIGHT: f32 = 224.0;
const MAX_CONTACTS: usize = 48;
const CONTACT_WIDTH: f32 = 144.0;
const MIN_CONTACT_WIDTH: f32 = 88.0;
const CONTACT_GAP: f32 = 6.0;
const CONTACT_REFINEMENT_BYTES: usize = 32 * 1024 * 1024;

/// An inclusive capture interval. Colour belongs to the interval's identity,
/// so extending it or adding another interval never recolours an older trace.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct SelectionSpan {
    pub start: usize,
    pub end: usize,
    pub id: usize,
}
impl SelectionSpan {
    pub(crate) fn contains(self, frame: usize) -> bool {
        (self.start..=self.end).contains(&frame)
    }
    pub(crate) fn len(self) -> usize {
        self.end.saturating_sub(self.start).saturating_add(1)
    }
    pub(crate) fn color(self) -> Color32 {
        if self.id == usize::MAX {
            return Color32::from_rgb(220, 228, 237);
        }
        const COLORS: [Color32; 8] = [
            GREEN,
            Color32::from_rgb(116, 183, 243),
            Color32::from_rgb(224, 153, 217),
            Color32::from_rgb(234, 189, 109),
            Color32::from_rgb(123, 214, 222),
            Color32::from_rgb(242, 146, 138),
            Color32::from_rgb(177, 167, 243),
            Color32::from_rgb(203, 218, 134),
        ];
        if let Some(&color) = COLORS.get(self.id) {
            return color;
        }
        // Keep the familiar first eight colours, then spread new identities
        // around the hue circle instead of recycling an active range's colour.
        // Saturation/value vary gently so larger selections remain readable.
        let index = self.id - COLORS.len();
        egui::ecolor::Hsva::new(
            ((index as f64 * 0.618_033_988_749_894_9 + 0.04).fract()) as f32,
            0.50 + (index / 8 % 3) as f32 * 0.10,
            0.95 - (index / 24 % 3) as f32 * 0.05,
            1.0,
        )
        .into()
    }
    pub(crate) fn label(self) -> String {
        if self.start == self.end {
            format!("{:03}", self.start + 1)
        } else {
            format!("{:03}–{:03}", self.start + 1, self.end + 1)
        }
    }
}

struct SpanDrag {
    from: usize,
    append: bool,
    before: Vec<SelectionSpan>,
    id: usize,
}

/// Deliberate selection only: never retain textures, hovering or engine work in
/// the exploration journal.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct SelectionState {
    held: Option<usize>,
    spans: Vec<SelectionSpan>,
    anchor: Option<usize>,
    active_span: Option<usize>,
    next_span: usize,
}

#[derive(Default, Debug, PartialEq, Eq)]
pub(crate) struct ParticipationResponse {
    /// Transient hover takes precedence over a deliberately held capture.
    pub frame: Option<usize>,
    pub held: bool,
    /// A deliberate selection requests the real camera pixels. At completion
    /// these appear beside the final photograph, never in its coordinate grid.
    pub open_source: Option<usize>,
    /// A source exploration update. The workspace retains the last source until
    /// an explicit return action; this does not edit contribution spans.
    pub hover_source: Option<usize>,
    pub return_photo: bool,
    pub reset_view: bool,
    pub level: Option<usize>,
    pub spans: Vec<SelectionSpan>,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
struct Area {
    observed: usize,
    admitted: usize,
}
impl Area {
    fn fraction(self) -> Option<f32> {
        (self.observed > 0).then(|| self.admitted as f32 / self.observed as f32)
    }
    fn label(self) -> String {
        self.fraction()
            .map_or_else(|| "—".into(), |value| format!("{:.0}%", value * 100.0))
    }
}

struct Evidence {
    meta: AdmissionMeta,
    scene: Area,
    window: Area,
    window_key: Option<SampleWindow>,
}

#[derive(Clone, Copy, PartialEq)]
struct EvidenceKey {
    revision: u64,
    level: usize,
    frames: usize,
    extent: Option<[usize; 2]>,
    window: Option<SampleWindow>,
}
#[derive(PartialEq)]
struct BandKey {
    revision: u64,
    extent: Option<[usize; 2]>,
    frames: Vec<usize>,
}

struct ContactRefinement {
    texture: TextureHandle,
    started: f64,
    bytes: usize,
}

#[derive(Clone, Copy)]
struct HoverSweep {
    frame: usize,
    inside_at: f64,
}

#[derive(Default)]
pub(crate) struct CaptureParticipation {
    domain: Option<(u64, u64)>,
    layout_key: Option<(usize, u32, u32)>,
    level: Option<usize>,
    aperture: Option<Rect>,
    held: Option<usize>,
    spans: Vec<SelectionSpan>,
    anchor: Option<usize>,
    active_span: Option<usize>,
    next_span: usize,
    span_drag: Option<SpanDrag>,
    /// A keyboard step or explicit clear remains visible until the pointer
    /// actually moves; a stationary hover must not undo either action.
    suppressed_hover: Option<Pos2>,
    anchors: Vec<usize>,
    contacts: BTreeMap<usize, TextureHandle>,
    // A requested capture may still be decoding. Each slot retains its last
    // actual photo and identity until a replacement is ready; requests never
    // turn an already painted card into an empty rectangle.
    presented_contacts: Vec<usize>,
    // One chosen, already cached canonical tier per visible contact, under a
    // strict byte budget. It cannot disappear when the browser evicts its copy
    // or keep changing tier while the user scrubs elsewhere.
    refinements: BTreeMap<usize, ContactRefinement>,
    evidence: BTreeMap<usize, Evidence>,
    evidence_key: Option<EvidenceKey>,
    band_key: Option<BandKey>,
    plot_cache: Vec<[Area; 2]>,
    plot_key: Option<(usize, usize)>,
    plot_dirty: bool,
    #[cfg(test)]
    evidence_refreshes: usize,
    #[cfg(test)]
    band_count_reads: usize,
    #[cfg(test)]
    plot_builds: usize,
    #[cfg(test)]
    tooltip_builds: usize,
    band_evidence: BTreeMap<(usize, usize), (AdmissionMeta, Area)>,
    signature_levels: Vec<usize>,
    active_source: Option<usize>,
    source_mode: bool,
    source_drag: bool,
    hover_sweep: Option<HoverSweep>,
    hover_suppressed: bool,
    hover_suppressed_at: Option<Pos2>,
    last_pointer: Option<Pos2>,
    wheel_frame: Option<usize>,
    wheel_origin: Option<Pos2>,
    wheel_remainder: f32,
}
impl CaptureParticipation {
    pub(crate) fn selection(&self) -> SelectionState {
        SelectionState {
            held: self.held,
            spans: self.spans.clone(),
            anchor: self.anchor,
            active_span: self.active_span,
            next_span: self.next_span,
        }
    }

    pub(crate) fn restore_selection(&mut self, state: &SelectionState) {
        self.held = state.held;
        self.spans = state.spans.clone();
        self.anchor = state.anchor;
        self.active_span = state.active_span;
        self.next_span = state.next_span;
        self.span_drag = None;
        self.source_drag = false;
        self.suppress_hover_until_motion();
    }
    pub(crate) fn indices(&self) -> Vec<usize> {
        let mut indices = self.anchors.clone();
        if let Some(frame) = self.active_source
            && !indices.contains(&frame)
        {
            indices.push(frame);
        }
        indices
    }

    pub(crate) fn set_active_source(&mut self, frame: Option<usize>) {
        self.active_source = frame;
    }

    fn contact_frames(&self, active: Option<usize>) -> Vec<usize> {
        let mut frames = self.anchors.clone();
        if let Some(active) = active
            && !frames.contains(&active)
            && !frames.is_empty()
        {
            // Use the same slot mapping as contact(), including rounded anchor
            // intervals. Nearest-anchor distances can choose a different slot.
            let last = frames.last().copied().unwrap_or(0).max(1);
            let slot = contact_slot(active, last + 1, frames.len());
            if slot < frames.len() {
                frames[slot] = active;
            }
        }
        frames
    }

    pub(crate) fn set_source_mode(&mut self, enabled: bool) {
        self.source_mode = enabled;
    }
    pub(crate) fn suppress_hover_until_motion(&mut self) {
        self.hover_sweep = None;
        self.hover_suppressed = true;
        self.hover_suppressed_at = self.last_pointer;
        self.wheel_frame = None;
        self.wheel_origin = None;
        self.wheel_remainder = 0.0;
    }
    pub(crate) fn select_frame(&mut self, frame: usize) {
        self.inspect_frame(frame);
        self.suppress_hover_until_motion();
    }

    pub(crate) fn has_ranges(&self) -> bool {
        self.spans.len() > 1 || self.spans.iter().any(|span| span.len() > 1)
    }

    /// Screenshot diagnostics use the normal selection state after its domain
    /// is initialized. Reject the entire preset before changing any selection.
    pub(crate) fn screenshot_ranges(
        &mut self,
        domain: (u64, u64),
        frame_count: usize,
        ranges: &[[usize; 2]],
    ) -> Result<bool, &'static str> {
        if ranges.is_empty()
            || ranges.len() > 8
            || ranges
                .iter()
                .any(|&[start, end]| start > end || end >= frame_count)
        {
            return Err(
                "capture ranges must contain 1 to 8 valid intervals within the completed stack",
            );
        }
        if self.domain != Some(domain) {
            return Ok(false);
        }
        self.clear();
        for &[start, end] in ranges {
            let span = self.new_span(start, end);
            self.active_span = Some(span.id);
            self.anchor = Some(start);
            self.held = Some(end);
            self.spans.push(span);
        }
        Ok(true)
    }

    /// Source inspection moves the comparison without rewriting saved ranges
    /// or the anchor used by the next explicit Shift extension.
    fn inspect_frame(&mut self, frame: usize) {
        if self.has_ranges() {
            self.held = Some(frame);
        } else {
            self.select(frame, false, false);
        }
    }

    pub(crate) fn clear(&mut self) {
        self.active_source = None;
        self.held = None;
        self.spans.clear();
        self.anchor = None;
        self.active_span = None;
        self.next_span = 0;
        self.span_drag = None;
        self.source_drag = false;
        self.suppressed_hover = None;
        self.suppress_hover_until_motion();
    }

    pub(crate) fn spans(&self) -> &[SelectionSpan] {
        &self.spans
    }

    fn next_span_id(&self) -> usize {
        let mut id = self.next_span;
        loop {
            // RGB quantization can eventually make generated colours equal.
            // Keep colours unique among live identities, including fragments
            // left when a capture is removed from the middle of a range.
            let color = SelectionSpan {
                start: 0,
                end: 0,
                id,
            }
            .color();
            if id != usize::MAX && !self.spans.iter().any(|span| span.color() == color) {
                return id;
            }
            id = id.wrapping_add(1);
        }
    }

    fn new_span(&mut self, from: usize, to: usize) -> SelectionSpan {
        let span = SelectionSpan {
            start: from.min(to),
            end: from.max(to),
            id: self.next_span_id(),
        };
        self.next_span = span.id.wrapping_add(1);
        span
    }

    fn select(&mut self, frame: usize, extend: bool, append: bool) {
        if extend {
            let anchor = self.anchor.or(self.held).unwrap_or(frame);
            if !append
                && let Some(span) = self
                    .spans
                    .iter_mut()
                    .find(|span| Some(span.id) == self.active_span && span.contains(anchor))
            {
                span.start = anchor.min(frame);
                span.end = anchor.max(frame);
            } else {
                let span = self.new_span(anchor, frame);
                self.active_span = Some(span.id);
                self.spans.push(span);
            }
            self.anchor = Some(anchor);
        } else if append {
            // Ctrl-click removes exactly this capture from an existing span,
            // splitting it when necessary, or adds an independent colour.
            if self.spans.iter().any(|span| span.contains(frame)) {
                let mut remainder = Vec::new();
                for span in self.spans.drain(..) {
                    if !span.contains(frame) {
                        remainder.push(span);
                    } else {
                        if span.start < frame {
                            remainder.push(SelectionSpan {
                                end: frame - 1,
                                ..span
                            });
                        }
                        if frame < span.end {
                            remainder.push(SelectionSpan {
                                start: frame + 1,
                                ..span
                            });
                        }
                    }
                }
                self.spans = remainder;
                self.held = self.spans.last().map(|span| span.end);
                self.active_span = self.spans.last().map(|span| span.id);
                self.anchor = self.spans.last().map(|span| span.start);
                return;
            }
            let span = self.new_span(frame, frame);
            self.active_span = Some(span.id);
            self.spans.push(span);
            self.anchor = Some(frame);
        } else {
            self.next_span = 0;
            self.spans.clear();
            let span = self.new_span(frame, frame);
            self.spans = vec![span];
            self.active_span = Some(span.id);
            self.anchor = Some(frame);
        }
        self.held = Some(frame);
    }

    fn update(
        &mut self,
        input: &Input<'_>,
        archive: &AdmissionArchive,
        level: usize,
        aperture: Rect,
        width: f32,
        height: f32,
    ) {
        let domain = (input.epoch, input.progress.diagnostic_epoch);
        if self.domain != Some(domain) {
            *self = Self {
                domain: Some(domain),
                source_mode: self.source_mode,
                active_source: self
                    .domain
                    .is_none()
                    .then_some(self.active_source)
                    .flatten(),
                ..Default::default()
            };
        }
        let layout_key = (input.frame_count, width.to_bits(), height.to_bits());
        if self.layout_key != Some(layout_key) {
            self.anchors = anchors_at_height(input.frame_count, width, height);
            self.held = self.held.filter(|&frame| frame < input.frame_count);
            self.spans.retain(|span| span.start < input.frame_count);
            for span in &mut self.spans {
                span.end = span.end.min(input.frame_count.saturating_sub(1));
            }
            self.layout_key = Some(layout_key);
        }
        self.active_source = self
            .active_source
            .filter(|&frame| frame < input.frame_count);
        let extent = input.progress.analysis_size.or(input.progress.plane_size);
        let revision = archive.revision();
        let same_receipts = self.evidence_key.is_some_and(|key| {
            key.revision == revision
                && key.level == level
                && key.frames == input.frame_count
                && key.extent == extent
        });
        if same_receipts && self.aperture == Some(aperture) {
            return;
        }
        self.aperture = Some(aperture);
        let window = archive
            .frames(level)
            .next()
            .and_then(|frame| archive.metadata(level, frame))
            .filter(|meta| extent.is_none_or(|extent| extent == meta.extent))
            .and_then(|meta| SampleWindow::new(level, meta, aperture));
        let key = EvidenceKey {
            revision,
            level,
            frames: input.frame_count,
            extent,
            window,
        };
        if self.evidence_key == Some(key) {
            return;
        }
        self.evidence_key = Some(key);
        self.plot_dirty = true;
        #[cfg(test)]
        {
            self.evidence_refreshes += 1;
        }
        if self.level != Some(level) {
            self.evidence.clear();
            self.level = Some(level);
        }
        self.evidence.retain(|&frame, item| {
            frame < input.frame_count && archive.metadata(level, frame) == Some(item.meta)
        });
        let whole = aperture.contains_rect(Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)));
        for frame in archive
            .frames(level)
            .filter(|&frame| frame < input.frame_count)
        {
            if let Some(evidence) = self.evidence.get_mut(&frame) {
                if evidence.window_key != window {
                    evidence.window = if whole && window.is_some() {
                        evidence.scene
                    } else {
                        window
                            .map(|window| window.archive_counts(archive, level, frame))
                            .map_or_else(Area::default, |count| Area {
                                observed: count.observed,
                                admitted: count.admitted,
                            })
                    };
                    evidence.window_key = window;
                }
                continue;
            }
            if let Some(meta) = archive.metadata(level, frame)
                && let Some((admitted, observed)) = archive.counts(level, frame)
            {
                let scene = Area { admitted, observed };
                let local = if whole && window.is_some() {
                    scene
                } else {
                    window
                        .map(|window| window.archive_counts(archive, level, frame))
                        .map_or_else(Area::default, |count| Area {
                            observed: count.observed,
                            admitted: count.admitted,
                        })
                };
                self.evidence.insert(
                    frame,
                    Evidence {
                        meta,
                        scene,
                        window: local,
                        window_key: window,
                    },
                );
            }
        }
    }

    pub(crate) fn show(
        &mut self,
        ui: &mut Ui,
        rect: Rect,
        input: &Input<'_>,
        archive: &AdmissionArchive,
        level: usize,
        aperture: Rect,
    ) -> ParticipationResponse {
        self.update(input, archive, level, aperture, rect.width(), rect.height());
        let mut result = ParticipationResponse::default();
        let Some(mut layout) = Layout::new(rect, input.frame_count, self.anchors.len()) else {
            return result;
        };
        layout.source_mode = self.source_mode;
        let hit = ui.interact(
            layout.hit,
            ui.id().with("capture-participation"),
            Sense::click_and_drag(),
        );
        // Physical clicks address the identity that was actually painted,
        // even if a newly decoded source becomes available this same frame.
        let clicked_contacts = if self.presented_contacts.len() == self.anchors.len() {
            self.presented_contacts.clone()
        } else {
            self.contact_frames(self.active_source)
        };
        let enabled = ui.is_enabled()
            && ui
                .ctx()
                .memory(|memory| memory.is_above_modal_layer(ui.layer_id()));
        let hover_point = enabled.then(|| hit.hover_pos()).flatten();
        if hover_point != self.suppressed_hover {
            self.suppressed_hover = None;
        }
        let hovered = hover_point
            .filter(|at| Some(*at) != self.suppressed_hover)
            .map(|at| layout.index(at.x));
        let scrubbed = (enabled && hit.dragged())
            .then(|| hit.interact_pointer_pos())
            .flatten()
            .filter(|at| Some(*at) != self.suppressed_hover)
            .map(|at| layout.index(at.x));
        let mut pointer_frame = scrubbed.or(hovered);
        let modifiers = ui.input(|state| {
            state
                .events
                .iter()
                .rev()
                .find_map(|event| {
                    if let egui::Event::PointerButton {
                        button: egui::PointerButton::Primary,
                        modifiers,
                        ..
                    } = event
                    {
                        Some(*modifiers)
                    } else {
                        None
                    }
                })
                .unwrap_or(state.modifiers)
        });
        let complete = input.progress.stage == crate::pipeline::Stage::Complete;
        let span_modifier = modifiers.shift || modifiers.ctrl || modifiers.command;
        if enabled && hit.is_pointer_button_down_on() && ui.input(|s| s.pointer.primary_pressed()) {
            self.source_drag = !span_modifier
                && hit
                    .interact_pointer_pos()
                    .is_some_and(|at| complete || self.source_mode || at.y >= layout.contact_top());
        }
        let source_interaction =
            self.source_drag || (self.source_mode && !span_modifier && !complete);
        if source_interaction {
            let mut extended_by_key = false;
            // The same capture lane becomes a direct source sweep. A hover
            // never displaces the developing image; a press or drag does.
            let pointer_active = enabled
                && (!complete || !modifiers.alt || ui.input(|s| s.pointer.primary_down()))
                && (hit.clicked()
                    || hit.dragged()
                    || (hit.is_pointer_button_down_on()
                        && ui.input(|s| s.pointer.primary_pressed())));
            if pointer_active && let Some(at) = hit.interact_pointer_pos() {
                result.open_source = Some(if hit.dragged() {
                    layout.index(at.x)
                } else {
                    // A deliberate card click chooses the named photograph;
                    // a sweep addresses every capture along the continuous axis.
                    layout.index_at(at, &clicked_contacts)
                });
                hit.request_focus();
            }
            if complete && hit.double_clicked() {
                self.clear();
                result.open_source = None;
                result.return_photo = true;
                result.reset_view = true;
                self.suppressed_hover = hover_point;
            }
            if enabled && hit.has_focus() {
                let current = self
                    .held
                    .filter(|_| complete)
                    .or(self.active_source)
                    .unwrap_or(input.selected)
                    .min(input.frame_count - 1);
                let selected = ui.input(|state| {
                    state.events.iter().find_map(|event| {
                        let egui::Event::Key {
                            key,
                            pressed: true,
                            modifiers,
                            ..
                        } = event
                        else {
                            return None;
                        };
                        let frame = match key {
                            egui::Key::ArrowLeft => Some(current.saturating_sub(1)),
                            egui::Key::ArrowRight => Some((current + 1).min(input.frame_count - 1)),
                            egui::Key::Home => Some(0),
                            egui::Key::End => Some(input.frame_count - 1),
                            _ => None,
                        }?;
                        Some((frame, modifiers.shift))
                    })
                });
                if let Some((frame, extend)) = selected {
                    result.open_source = Some(frame);
                    if complete && extend {
                        self.select(frame, true, false);
                        extended_by_key = true;
                    }
                }
            }
            if complete
                && let Some(frame) = result.open_source
                && !modifiers.alt
                && !extended_by_key
            {
                self.inspect_frame(frame);
            }
            result.frame = (!result.reset_view).then_some(
                result
                    .open_source
                    .or(self.held.filter(|_| complete))
                    .or(self.active_source)
                    .unwrap_or(input.selected)
                    .min(input.frame_count - 1),
            );
            result.held = !result.reset_view;
        } else {
            let append = modifiers.ctrl || modifiers.command;
            if enabled
                && hit.is_pointer_button_down_on()
                && ui.input(|state| state.pointer.primary_pressed())
                && (modifiers.shift || append)
                && let Some(at) = hit.interact_pointer_pos()
            {
                let from = layout.index(at.x);
                let id = self.next_span_id();
                self.span_drag = Some(SpanDrag {
                    from,
                    append,
                    before: self.spans.clone(),
                    id,
                });
            }
            if enabled
                && hit.dragged()
                && let (Some(drag), Some(frame)) = (&self.span_drag, scrubbed)
            {
                let span = SelectionSpan {
                    start: drag.from.min(frame),
                    end: drag.from.max(frame),
                    id: drag.id,
                };
                self.spans = if drag.append {
                    drag.before.clone()
                } else {
                    Vec::new()
                };
                self.spans.push(span);
                self.next_span = span.id.wrapping_add(1);
                self.held = Some(frame);
                self.anchor = Some(drag.from);
                self.active_span = Some(span.id);
                result.return_photo = !complete;
                result.open_source = complete.then_some(frame);
                hit.request_focus();
            }
            if enabled
                && hit.dragged()
                && self.span_drag.is_none()
                && let Some(frame) = scrubbed
            {
                self.inspect_frame(frame);
                result.return_photo = !complete;
                result.open_source = complete.then_some(frame);
                hit.request_focus();
            }
            // egui also synthesizes clicked() from Space/Enter for a focused
            // widget. Space is the photograph's temporary clean peek, so only a
            // real primary-button release may change a held capture or open it.
            let pointer_release =
                ui.input(|state| state.pointer.button_released(egui::PointerButton::Primary));
            if enabled && pointer_release && hit.double_clicked() && !modifiers.shift && !append {
                if complete {
                    result.return_photo = true;
                    result.reset_view = true;
                } else {
                    result.open_source =
                        hover_point.map(|at| layout.index_at(at, &clicked_contacts));
                }
                self.clear();
                self.suppressed_hover = hover_point;
                pointer_frame = None;
            } else if enabled && pointer_release && hit.clicked() {
                hit.request_focus();
                if let Some(frame) = hover_point.map(|at| layout.index_at(at, &clicked_contacts)) {
                    let removing = append
                        && !modifiers.shift
                        && self.spans.iter().any(|span| span.contains(frame));
                    if !modifiers.shift
                        && !append
                        && self.held == Some(frame)
                        && self.spans.len() <= 1
                        && self.spans.first().is_none_or(|span| span.len() == 1)
                    {
                        self.clear();
                        result.return_photo = true;
                        self.suppressed_hover = hover_point;
                        pointer_frame = None;
                    } else {
                        if modifiers.shift || append {
                            self.select(frame, modifiers.shift, append);
                        } else {
                            self.inspect_frame(frame);
                        }
                        pointer_frame = (!removing).then_some(frame);
                        result.return_photo = !complete;
                        if complete && !removing {
                            result.open_source = Some(frame);
                        }
                        self.suppressed_hover = removing.then_some(hover_point).flatten();
                        if removing {
                            pointer_frame = None;
                        }
                    }
                }
            }
            if !enabled || !ui.input(|state| state.pointer.primary_down()) {
                self.span_drag = None;
            }
            if enabled && hit.has_focus() {
                let current = self.held.or(pointer_frame).unwrap_or(0);
                let selected = ui.input(|state| {
                    // A complete key chord can arrive between two paints. Its
                    // pressed event owns Shift; the frame's final modifier state
                    // may already report the released key.
                    state.events.iter().find_map(|event| {
                        let egui::Event::Key {
                            key,
                            pressed: true,
                            modifiers,
                            ..
                        } = event
                        else {
                            return None;
                        };
                        let frame = match key {
                            egui::Key::ArrowLeft => current.saturating_sub(1),
                            egui::Key::ArrowRight => (current + 1).min(input.frame_count - 1),
                            egui::Key::Home => 0,
                            egui::Key::End => input.frame_count - 1,
                            _ => return None,
                        };
                        Some((frame, modifiers.shift))
                    })
                });
                if let Some((frame, extend)) = selected {
                    if extend {
                        self.select(frame, true, false);
                    } else {
                        self.inspect_frame(frame);
                    }
                    if complete {
                        result.open_source = Some(frame);
                    }
                    self.suppressed_hover = hover_point;
                    pointer_frame = None;
                }
            }
            if enabled {
                result.frame = pointer_frame.or(self.held);
                result.held = result.frame.is_some() && result.frame == self.held;
            }
        }
        if enabled && ui.input(|state| state.key_pressed(egui::Key::Escape)) {
            self.clear();
            result.frame = None;
            result.open_source = None;
            result.held = false;
            result.return_photo = true;
            self.suppressed_hover = hover_point;
            pointer_frame = None;
        }
        if enabled {
            result.spans = self.spans.clone();
        }
        if !ui.input(|state| state.pointer.primary_down()) {
            self.source_drag = false;
        }
        hit.context_menu(|ui| {
            if ui
                .button(if complete {
                    "Compare source beside photograph"
                } else {
                    "View source in photograph"
                })
                .clicked()
            {
                result.open_source = pointer_frame.or(self.held).or(Some(input.selected));
                ui.close();
            }
            if ui.button("Clear selected contributions").clicked() {
                self.clear();
                result.frame = None;
                result.spans.clear();
                result.return_photo = true;
                self.suppressed_hover = hover_point;
                ui.close();
            }
            ui.separator();
            ui.label(if complete {
                "Hover / drag: source + final · Photograph returns"
            } else {
                "Drag thumbnails: source sweep"
            });
            ui.label("Drag lanes: footprint · Shift: span · Ctrl: add");
        });
        let changed_by_key = ui.input(|state| {
            state.events.iter().any(|event| {
                matches!(
                    event,
                    egui::Event::Key {
                        key: egui::Key::ArrowLeft
                            | egui::Key::ArrowRight
                            | egui::Key::Home
                            | egui::Key::End
                            | egui::Key::Escape,
                        pressed: true,
                        ..
                    }
                )
            })
        });
        result.hover_source = self.hover_source(
            ui,
            &hit,
            &layout,
            enabled,
            result.open_source.is_some()
                || result.return_photo
                || result.reset_view
                || changed_by_key,
        );
        if let Some(frame) = result.hover_source {
            result.frame = Some(frame);
            result.held = false;
        }
        if result.return_photo || result.reset_view {
            self.active_source = None;
        } else {
            self.active_source = result
                .open_source
                .or(complete.then_some(result.hover_source).flatten())
                .or(self.active_source)
                .or(self.source_mode.then_some(input.selected))
                .filter(|&frame| frame < input.frame_count);
        }
        if enabled && !result.return_photo && !result.reset_view {
            result.frame = result.frame.or(self.active_source);
        }
        self.sync_contacts(input, ui.input(|state| state.time));
        let contacts = self.presented_contacts.clone();
        self.update_bands(input, archive, &contacts);
        if !self.source_mode {
            self.update_plot(input.frame_count, layout.columns);
        }

        let painter = ui.painter_at(rect);
        painter.text(
            rect.min,
            Align2::LEFT_TOP,
            if self.source_mode {
                "CAPTURES / SOURCES"
            } else if rect.width() < 700.0 {
                "CAPTURES"
            } else {
                "CAPTURE / ADMITTED SAMPLES"
            },
            FontId::proportional(9.0),
            ACCENT,
        );
        let is_base = input.progress.bands == Some(level);
        let mean_base = is_base
            && input
                .progress
                .base
                .as_deref()
                .is_some_and(|mode| mode.starts_with("plain mean"));
        let scale = if mean_base {
            "broad tone · fallback average".into()
        } else {
            scale_name(level, is_base, input.progress.output_geometry)
        };
        let multi = self.has_ranges();
        let caption = if self.source_mode {
            format!(
                "{:03} / {} · hover to explore · wheel / arrows step",
                result.frame.unwrap_or(0) + 1,
                input.frame_count
            )
        } else if multi {
            let captures = (0..input.frame_count)
                .filter(|&frame| self.spans.iter().any(|span| span.contains(frame)))
                .count();
            let observed = self
                .evidence
                .keys()
                .filter(|&&frame| self.spans.iter().any(|span| span.contains(frame)))
                .count();
            if rect.width() < 640.0 {
                format!("{} spans · {observed}/{captures} sampled", self.spans.len())
            } else {
                format!(
                    "{} spans · {captures} captures · {observed}/{captures} sampled{}",
                    self.spans.len(),
                    if rect.width() >= 900.0 {
                        " · shared sample marks"
                    } else {
                        ""
                    }
                )
            }
        } else if mean_base {
            if rect.width() < 420.0 {
                "tone · fallback average".into()
            } else if let Some(frame) = result.frame {
                format!(
                    "{:03}  ·  {scale}{}",
                    frame + 1,
                    if result.held { "  ·  held" } else { "" }
                )
            } else {
                scale.clone()
            }
        } else if rect.width() < 420.0 {
            result.frame.map_or_else(
                || scale.clone(),
                |frame| {
                    let area = self.evidence.get(&frame);
                    format!(
                        "{:03} · {} / {}",
                        frame + 1,
                        area.map_or_else(|| "—".into(), |item| item.scene.label()),
                        area.map_or_else(|| "—".into(), |item| item.window.label())
                    )
                },
            )
        } else if let Some(frame) = result.frame {
            let area = self.evidence.get(&frame);
            format!(
                "{:03}  ·  {} full image  /  {} region{}{}",
                frame + 1,
                area.map_or_else(|| "—".into(), |item| item.scene.label()),
                area.map_or_else(|| "—".into(), |item| item.window.label()),
                if rect.width() >= 640.0 {
                    format!("  ·  {scale}")
                } else {
                    String::new()
                },
                if result.held { "  ·  held" } else { "" },
            )
        } else {
            format!(
                "{scale}  ·  sampled area{}",
                if rect.width() >= 640.0 {
                    "  ·  Shift span / Ctrl-drag add"
                } else {
                    ""
                }
            )
        };
        painter.text(
            rect.right_top(),
            Align2::RIGHT_TOP,
            caption,
            FontId::proportional(10.0),
            MUTED,
        );
        let lanes: &[(&str, Color32)] = if self.source_mode {
            &[("read", GREEN), ("scales", ACCENT), ("folded", GREEN)]
        } else {
            &[("Full image", GREEN), ("Current region", ACCENT)]
        };
        for (row, &(name, colour)) in lanes.iter().enumerate() {
            let lane = layout.lane(row);
            painter.text(
                egui::pos2(
                    rect.left() + 4.0 + row as f32 * if self.source_mode { 74.0 } else { 112.0 },
                    rect.top() + 16.0,
                ),
                Align2::LEFT_TOP,
                name,
                FontId::proportional(9.0),
                colour,
            );
            if !self.source_mode && row == 0 {
                painter.line_segment(
                    [lane.left_top(), lane.right_top()],
                    Stroke::new(0.5_f32, LINE.gamma_multiply(0.55)),
                );
                painter.line_segment(
                    [lane.left_center(), lane.right_center()],
                    Stroke::new(0.5_f32, LINE.gamma_multiply(0.30)),
                );
            }
            if self.source_mode || row == 0 {
                painter.line_segment(
                    [lane.left_bottom(), lane.right_bottom()],
                    Stroke::new(0.5_f32, LINE),
                );
            }
            let mut previous: Option<Pos2> = None;
            for column in 0..layout.columns {
                let range = layout.range(column);
                let cell = layout.cell(row, column);
                let pooled = if self.source_mode {
                    Area::default()
                } else {
                    self.plot_cache[column][row]
                };
                let fraction = if self.source_mode {
                    // These are observed processing milestones, not estimated
                    // percentages. All three tracks accrue independently;
                    // alignment scales stay visible when folding begins.
                    let done = range
                        .clone()
                        .filter(|frame| {
                            if row == 0 {
                                input.progress.alignment_plane_observations.contains(frame)
                            } else if row == 1 {
                                input
                                    .progress
                                    .alignment_pyramid_observations
                                    .contains(frame)
                            } else {
                                input.progress.frame_observations.get(frame)
                                    == Some(&crate::pipeline::FrameObservation::Processed)
                            }
                        })
                        .count();
                    (done > 0).then_some(done as f32 / range.len().max(1) as f32)
                } else {
                    pooled.fraction()
                };
                if let Some(fraction) = fraction {
                    let bar = Rect::from_min_max(
                        egui::pos2(
                            cell.left(),
                            cell.bottom() - 1.0 - fraction * (cell.height() - 1.0),
                        ),
                        cell.right_bottom(),
                    );
                    if self.source_mode || row == 0 {
                        painter.rect_filled(
                            bar,
                            0.0,
                            colour.gamma_multiply(if self.source_mode {
                                0.85
                            } else if fraction > 0.0 {
                                0.14
                            } else {
                                0.3
                            }),
                        );
                    }
                    if !self.source_mode {
                        let at = egui::pos2(layout.column_x(column), bar.top());
                        if let Some(before) = previous {
                            if row == 0 {
                                painter.line_segment([before, at], Stroke::new(1.0_f32, colour));
                            } else {
                                dashed_line(&painter, before, at, Stroke::new(1.2_f32, colour));
                            }
                        }
                        painter.circle_filled(
                            at,
                            if result.frame.is_some_and(|frame| range.contains(&frame)) {
                                3.0
                            } else {
                                1.1
                            },
                            colour,
                        );
                        previous = Some(at);
                        if row == 0 && result.frame.is_some_and(|frame| range.contains(&frame)) {
                            painter.line_segment(
                                [
                                    egui::pos2(at.x, lane.top()),
                                    egui::pos2(at.x, lane.bottom()),
                                ],
                                Stroke::new(0.7_f32, colour.gamma_multiply(0.65)),
                            );
                        }
                    }
                } else {
                    previous = None;
                }
            }
        }
        if self.source_mode
            && let Some(pair) = input
                .inspected_pair
                .or(input.progress.alignment_current_pair)
                .filter(|pair| pair.iter().all(|&frame| frame < input.frame_count))
        {
            let y = layout.contact_top() - 7.0;
            let a = layout.x(pair[0]);
            let b = layout.x(pair[1]);
            painter.line_segment(
                [egui::pos2(a, y), egui::pos2(b, y)],
                Stroke::new(1.2_f32, ACCENT),
            );
            for x in [a, b] {
                painter.circle_filled(egui::pos2(x, y), 2.0, ACCENT);
            }
        }
        for &frame in &contacts {
            let image = layout.contact(frame);
            if (layout.x(frame) - image.center().x).abs() > 1.0 {
                // Sparse contacts form an even filmstrip while these short
                // stems preserve their exact location on the capture axis.
                painter.line_segment(
                    [
                        egui::pos2(layout.x(frame), image.top() - 7.0),
                        image.center_top(),
                    ],
                    Stroke::new(0.6_f32, LINE),
                );
            }
            painter.rect_filled(image, 0.0, BG);
            if let Some(texture) = self
                .contacts
                .get(&frame)
                .or_else(|| self.refinements.get(&frame).map(|chosen| &chosen.texture))
            {
                let base_id = texture.id();
                painter.image(base_id, image, contact_uv(texture, image), Color32::WHITE);
                if !self.refinements.contains_key(&frame)
                    && let Some(photo) = input.inspection_photos.iter().find(|photo| {
                        photo.epoch == input.epoch
                            && photo.index == frame
                            && contact_refinement_fits(
                                texture,
                                photo,
                                image,
                                ui.ctx().pixels_per_point(),
                            )
                    })
                {
                    let bytes = photo.texture.size()[0]
                        .checked_mul(photo.texture.size()[1])
                        .and_then(|pixels| pixels.checked_mul(4));
                    let used: usize = self.refinements.values().map(|item| item.bytes).sum();
                    if let Some(bytes) = bytes
                        .filter(|bytes| *bytes <= CONTACT_REFINEMENT_BYTES.saturating_sub(used))
                    {
                        self.refinements.insert(
                            frame,
                            ContactRefinement {
                                texture: photo.texture.clone(),
                                started: ui.input(|i| i.time),
                                bytes,
                            },
                        );
                    }
                }
                if let Some(chosen) = self.refinements.get(&frame)
                    && chosen.texture.id() != base_id
                {
                    let now = ui.input(|i| i.time);
                    let t = ((now - chosen.started) / 0.20).clamp(0.0, 1.0) as f32;
                    let blend = t * t * (3.0 - 2.0 * t);
                    painter.image(
                        chosen.texture.id(),
                        image,
                        contact_uv(&chosen.texture, image),
                        Color32::from_white_alpha((blend * 255.0).round() as u8),
                    );
                    if t < 1.0 {
                        ui.ctx().request_repaint();
                    }
                }
            }
            let pending = self.active_source.filter(|&requested| {
                requested != frame
                    && contact_slot(requested, input.frame_count, contacts.len())
                        == contact_slot(frame, input.frame_count, contacts.len())
            });
            if let Some(requested) = pending {
                let label = format!("Waiting {:03}", requested + 1);
                let font = FontId::monospace(9.0);
                let galley = painter.layout_no_wrap(label, font, ACCENT);
                let badge = Rect::from_min_size(
                    image.min + egui::vec2(4.0, 4.0),
                    galley.size() + egui::vec2(6.0, 4.0),
                );
                painter.rect_filled(badge, 0.0, BG.gamma_multiply(0.94));
                painter.galley(badge.min + egui::vec2(3.0, 2.0), galley, ACCENT);
            }
            painter.rect_stroke(
                image,
                0.0,
                Stroke::new(
                    0.9_f32,
                    self.spans.iter().find(|span| span.contains(frame)).map_or(
                        if self.active_source == Some(frame) || pending.is_some() {
                            ACCENT
                        } else {
                            LINE
                        },
                        |span| span.color(),
                    ),
                ),
                egui::StrokeKind::Inside,
            );
            painter.text(
                egui::pos2(image.center().x, image.bottom() + 5.0),
                Align2::CENTER_CENTER,
                if self.active_source == Some(frame) {
                    format!("{:03} · SOURCE", frame + 1)
                } else if pending.is_some() {
                    format!("{:03} · SHOWN", frame + 1)
                } else {
                    format!("{:03}", frame + 1)
                },
                FontId::monospace(9.0),
                if self.active_source == Some(frame) {
                    ACCENT
                } else {
                    MUTED
                },
            );
            self.band_signature(ui, image, frame, level, input, &mut result);
        }
        for (index, span) in self.spans.iter().filter(|_| !self.source_mode).enumerate() {
            let y = layout.contact_top() - 8.0 + (index % 3) as f32 * 1.8;
            let a = layout.x(span.start);
            let b = layout.x(span.end);
            painter.line_segment(
                [egui::pos2(a - 3.0, y), egui::pos2(b + 3.0, y)],
                Stroke::new(1.4_f32, span.color()),
            );
            for x in [a, b] {
                painter.line_segment(
                    [egui::pos2(x, y - 2.0), egui::pos2(x, y + 2.0)],
                    Stroke::new(1.0_f32, span.color()),
                );
            }
            if multi {
                let known = self.evidence.range(span.start..=span.end).count();
                let span_hit = Rect::from_min_max(
                    egui::pos2(a - 4.0, layout.contact_top() - 11.0),
                    egui::pos2(b + 4.0, layout.contact_top() - 2.0),
                );
                ui.interact(span_hit, ui.id().with(("capture-span", span.id, span.start)), Sense::hover())
                    .on_hover_text(format!("{} · {known}/{} captures sampled\nColour marks their combined admitted area. Stripes mark shared area. Missing masks remain unknown.\nShift-click extends · Ctrl-click adds/removes · Ctrl-drag adds a span · Esc clears", span.label(), span.len()));
            }
        }
        if let Some(frame) = result.frame {
            // The cursor follows physical motion continuously; the requested
            // photograph remains one real integer capture. Wheel/held states
            // use their exact capture location until pointer motion resumes.
            let pointer_cursor = (result.hover_source.is_some() && self.wheel_frame.is_none())
                .then(|| ui.input(|state| state.pointer.hover_pos()))
                .flatten()
                .or_else(|| hit.dragged().then(|| hit.interact_pointer_pos()).flatten());
            let x = pointer_cursor.map_or_else(
                || layout.x(frame),
                |at| at.x.clamp(layout.left, layout.right),
            );
            painter.line_segment(
                [
                    egui::pos2(x, layout.lane(0).top() - 2.0),
                    egui::pos2(x, rect.bottom() - 1.0),
                ],
                Stroke::new(1.0_f32, ACCENT),
            );
            painter.add(egui::Shape::convex_polygon(
                vec![
                    egui::pos2(x - 3.0, layout.lane(0).top() - 3.0),
                    egui::pos2(x + 3.0, layout.lane(0).top() - 3.0),
                    egui::pos2(x, layout.lane(0).top()),
                ],
                ACCENT,
                Stroke::NONE,
            ));
            if !hit.hovered() {
                // A held source still paints its cursor while the pointer is
                // in the photograph. Do not build its off-screen tooltip.
            } else if self.source_mode {
                hit.clone().on_hover_text(format!("Source {:03} · press and sweep to inspect in the primary viewer\nNo registration is applied to camera previews. Return photograph restores the aligned diagnostics view.", frame + 1));
            } else if let Some(item) = self.evidence.get(&frame) {
                let body = format!(
                    "{:03} · {} / {} scene samples · {} / {} window samples admitted\n{}",
                    frame + 1,
                    item.scene.admitted,
                    item.scene.observed,
                    item.window.admitted,
                    item.window.observed,
                    if mean_base {
                        "Fallback average bypasses this gate; zero admission is not zero final contribution."
                    } else {
                        "Click holds · Shift extends · Ctrl-click toggles · Ctrl-drag adds span · Esc clears"
                    },
                );
                hit.clone().on_hover_text(body);
            } else {
                hit.clone().on_hover_text(format!(
                    "{:03} · no retained samples\n{}",
                    frame + 1,
                    if complete {
                        "Double-click clears · Drag compares a source · Photograph returns"
                    } else {
                        "Double-click opens source"
                    }
                ));
            }
        }
        hit.on_hover_cursor(egui::CursorIcon::Crosshair);
        let info = Rect::from_min_size(rect.min, egui::vec2(190.0, 14.0));
        if !self.source_mode {
            ui.interact(info, ui.id().with("participation-scope"), Sense::hover()).on_hover_ui(|ui| { ui.label(format!(
            "Green: admitted samples across the scene. Amber: admitted samples inside the linked detail window. Each capture is independent; areas need not add to 100%. Shift-click extends a span; Shift-drag draws one; Ctrl-drag adds another colour; Ctrl-click adds/removes a capture. Shared admitted cells are striped on the photograph. Gaps have no retained samples; a mark on the baseline means observed zero admission. Heights measure sampled area, not contribution weight or image quality. Zero gate admission is not zero final contribution: fallback averaging can still use a capture, and the plain-mean tone base bypasses the gate entirely. {} retained masks; {} packets omitted at the archive limit.{}",
            archive.len(), archive.dropped(), if layout.columns < input.frame_count { " Dense lanes pool adjacent captures; the pointer still selects each individual capture." } else { "" }
        )); });
        }
        result
    }

    fn sync_contacts(&mut self, input: &Input<'_>, now: f64) {
        let desired = self.contact_frames(self.active_source);
        let mut keep = self.anchors.clone();
        keep.extend(
            self.presented_contacts
                .iter()
                .copied()
                .filter(|frame| *frame < input.frame_count),
        );
        keep.extend(self.active_source);
        keep.sort_unstable();
        keep.dedup();
        self.contacts
            .retain(|frame, _| keep.binary_search(frame).is_ok());
        self.refinements
            .retain(|frame, _| keep.binary_search(frame).is_ok());
        for photo in input
            .photos
            .iter()
            .filter(|photo| photo.epoch == input.epoch && keep.binary_search(&photo.index).is_ok())
        {
            self.contacts
                .entry(photo.index)
                .or_insert_with(|| photo.texture.clone());
        }
        // A canonical tier can bridge the one-frame handoff before its native
        // derivative reaches the contact input. Retain the real handle under
        // the same strict budget as all other contact refinements.
        let mut used: usize = self.refinements.values().map(|item| item.bytes).sum();
        for &frame in &desired {
            if self.contacts.contains_key(&frame) || self.refinements.contains_key(&frame) {
                continue;
            }
            if let Some(photo) = input
                .inspection_photos
                .iter()
                .find(|photo| photo.epoch == input.epoch && photo.index == frame)
            {
                let bytes = photo.texture.size()[0]
                    .checked_mul(photo.texture.size()[1])
                    .and_then(|pixels| pixels.checked_mul(4));
                // The old picture in this same slot is disposable only once
                // the actual replacement is ready. Count the transaction's
                // final retained bytes, so a full cache cannot strand a ready
                // canonical source behind an obsolete shown card.
                let replaced = self.presented_contacts.iter().copied().find(|&old| {
                    old != frame
                        && contact_slot(old, input.frame_count, desired.len())
                            == contact_slot(frame, input.frame_count, desired.len())
                        && self.refinements.contains_key(&old)
                });
                let retired_bytes = replaced
                    .and_then(|old| self.refinements.get(&old))
                    .map_or(0, |old| old.bytes);
                let retained = used.saturating_sub(retired_bytes);
                if let Some(bytes) = bytes
                    .filter(|bytes| *bytes <= CONTACT_REFINEMENT_BYTES.saturating_sub(retained))
                {
                    if let Some(old) = replaced {
                        self.refinements.remove(&old);
                    }
                    self.refinements.insert(
                        frame,
                        ContactRefinement {
                            texture: photo.texture.clone(),
                            started: now - 0.20,
                            bytes,
                        },
                    );
                    used = retained + bytes;
                }
            }
        }
        let ready = |frame: usize| {
            self.contacts.contains_key(&frame) || self.refinements.contains_key(&frame)
        };
        let mut presented = Vec::with_capacity(desired.len());
        for (slot, &wanted) in desired.iter().enumerate() {
            let fallback = self.presented_contacts.iter().copied().find(|&frame| {
                frame < input.frame_count
                    && contact_slot(frame, input.frame_count, desired.len()) == slot
                    && ready(frame)
            });
            presented.push(if ready(wanted) {
                wanted
            } else {
                fallback.unwrap_or(wanted)
            });
        }
        self.presented_contacts = presented;
        self.contacts.retain(|frame, _| {
            self.anchors.contains(frame) || self.presented_contacts.contains(frame)
        });
        self.refinements
            .retain(|frame, _| self.presented_contacts.contains(frame));
    }

    fn update_plot(&mut self, frames: usize, columns: usize) {
        if !self.plot_dirty && self.plot_key == Some((frames, columns)) {
            return;
        }
        self.plot_key = Some((frames, columns));
        self.plot_dirty = false;
        self.plot_cache.clear();
        #[cfg(test)]
        {
            self.plot_builds += 1;
        }
        for column in 0..columns {
            let range = column * frames / columns..(column + 1) * frames / columns;
            let mut areas = [Area::default(); 2];
            for (_, evidence) in self.evidence.range(range) {
                for (row, value) in [evidence.scene, evidence.window].into_iter().enumerate() {
                    areas[row].admitted += value.admitted;
                    areas[row].observed += value.observed;
                }
            }
            self.plot_cache.push(areas);
        }
    }

    fn update_bands(&mut self, input: &Input<'_>, archive: &AdmissionArchive, frames: &[usize]) {
        let extent = input.progress.analysis_size.or(input.progress.plane_size);
        if self.band_key.as_ref().is_some_and(|key| {
            key.revision == archive.revision() && key.extent == extent && key.frames == frames
        }) {
            return;
        }
        self.band_key = Some(BandKey {
            revision: archive.revision(),
            extent,
            frames: frames.to_vec(),
        });
        self.signature_levels.clear();
        self.signature_levels.extend(archive.levels().take(16));
        self.band_evidence.retain(|&(frame, level), (meta, _)| {
            frames.contains(&frame)
                && self.signature_levels.contains(&level)
                && archive.metadata(level, frame) == Some(*meta)
                && extent.is_none_or(|extent| extent == meta.extent)
        });
        for &frame in frames {
            for &level in &self.signature_levels {
                if self.band_evidence.contains_key(&(frame, level)) {
                    continue;
                }
                if let Some(meta) = archive.metadata(level, frame)
                    && extent.is_none_or(|extent| extent == meta.extent)
                    && let Some((admitted, observed)) = archive.counts(level, frame)
                {
                    #[cfg(test)]
                    {
                        self.band_count_reads += 1;
                    }
                    self.band_evidence
                        .insert((frame, level), (meta, Area { admitted, observed }));
                }
            }
        }
    }

    fn band_signature(
        &mut self,
        ui: &mut Ui,
        image: Rect,
        frame: usize,
        active: usize,
        input: &Input<'_>,
        result: &mut ParticipationResponse,
    ) {
        let count = self.signature_levels.len();
        if count == 0 {
            return;
        }
        let pitch = ((image.width() - 4.0) / count as f32).min(14.0);
        let left = image.center().x - pitch * count as f32 * 0.5;
        for slot in 0..count {
            let level = self.signature_levels[slot];
            let rect = Rect::from_min_size(
                egui::pos2(left + slot as f32 * pitch, image.bottom() + 12.0),
                egui::vec2(pitch - 2.0, 9.0),
            );
            let color = crate::process_sample_glyphs::level_color(level);
            ui.painter().line_segment(
                [rect.left_bottom(), rect.right_bottom()],
                Stroke::new(0.7_f32, LINE),
            );
            let area = self
                .band_evidence
                .get(&(frame, level))
                .map(|(_, area)| *area);
            if let Some(fraction) = area.and_then(Area::fraction) {
                let bar = Rect::from_min_max(
                    egui::pos2(rect.left(), rect.bottom() - 1.0 - fraction * 7.0),
                    rect.right_bottom(),
                );
                ui.painter()
                    .rect_filled(bar, 0.0, color.gamma_multiply(0.8));
            }
            if level == active {
                ui.painter().line_segment(
                    [rect.left_top(), rect.right_top()],
                    Stroke::new(1.0_f32, ACCENT),
                );
            }
            let hit = ui.interact(
                rect.expand2(egui::vec2(0.5, 2.0)),
                ui.id().with(("capture-band", frame, level)),
                Sense::click(),
            );
            if hit.clicked() {
                result.level = Some(level);
                result.open_source = Some(frame);
                result.frame = Some(frame);
                result.hover_source = None;
                self.active_source = Some(frame);
                if input.progress.stage == Stage::Complete {
                    self.inspect_frame(frame);
                    result.spans = self.spans.clone();
                    result.held = true;
                }
                self.suppress_hover_until_motion();
            }
            if hit.hovered() {
                #[cfg(test)]
                {
                    self.tooltip_builds += 1;
                }
                hit.on_hover_text(format!("Capture {:03} · {}\n{}\n{}\nClick: compare this source at this detail size. These are recorded gate samples, not blend weights.", frame + 1, scale_name(level, input.progress.bands == Some(level), input.progress.output_geometry), area.map_or_else(|| "No retained samples".into(), |area| format!("{} / {} admitted samples · {}", area.admitted, area.observed, area.label())), crate::process_output_space::detail_tooltip(level, input.progress.output_geometry)));
            }
        }
    }

    fn hover_source(
        &mut self,
        ui: &mut Ui,
        hit: &egui::Response,
        layout: &Layout,
        enabled: bool,
        changed: bool,
    ) -> Option<usize> {
        let (pointer, now, down, focused) = ui.input(|state| {
            (
                state.pointer.hover_pos(),
                state.time,
                state.pointer.any_down(),
                state.focused
                    && state.viewport().focused != Some(false)
                    && state.viewport().minimized != Some(true),
            )
        });
        let moved = self
            .wheel_origin
            .zip(pointer)
            .is_some_and(|(a, b)| a.distance(b) > 2.0);
        let moved_since_suppression = pointer.is_some_and(|pointer| {
            self.hover_suppressed_at
                .is_none_or(|origin| origin.distance(pointer) > 2.0)
        });
        if moved_since_suppression {
            self.hover_suppressed = false;
        }
        if moved {
            self.wheel_frame = None;
            self.wheel_origin = None;
            self.wheel_remainder = 0.0;
        }
        self.last_pointer = pointer;
        if changed {
            self.suppress_hover_until_motion();
            return None;
        }
        if !enabled || !focused || egui::Popup::is_any_open(ui.ctx()) {
            self.suppress_hover_until_motion();
            return None;
        }
        if down {
            if !hit.is_pointer_button_down_on() {
                self.suppress_hover_until_motion();
            }
            self.hover_sweep = None;
            return None;
        }
        let Some(pointer) = pointer else {
            self.hover_sweep = None;
            self.wheel_frame = None;
            self.wheel_origin = None;
            return None;
        };
        let inside = hit.hovered() && layout.hit.contains(pointer);
        let delta = if inside {
            ui.input(|state| {
                if state.modifiers.ctrl || state.modifiers.command {
                    0.0
                } else if state.raw_scroll_delta.x.abs() > state.raw_scroll_delta.y.abs() {
                    state.raw_scroll_delta.x
                } else {
                    -state.raw_scroll_delta.y
                }
            })
        } else {
            0.0
        };
        if delta != 0.0 {
            self.hover_suppressed = false;
            self.wheel_origin.get_or_insert(pointer);
            self.wheel_remainder += delta;
            let steps = (self.wheel_remainder / 48.0).trunc() as isize;
            if steps != 0 {
                let frame = self
                    .wheel_frame
                    .or(self.hover_sweep.map(|hover| hover.frame))
                    .unwrap_or_else(|| layout.index(pointer.x));
                self.wheel_frame = Some(
                    frame
                        .saturating_add_signed(steps.clamp(-8, 8))
                        .min(layout.count - 1),
                );
                self.wheel_remainder -= steps as f32 * 48.0;
            }
            ui.input_mut(|state| {
                state.raw_scroll_delta = egui::Vec2::ZERO;
                state.smooth_scroll_delta = egui::Vec2::ZERO;
            });
        }
        if self.hover_suppressed || self.suppressed_hover == Some(pointer) {
            self.hover_sweep = None;
            return None;
        }
        if inside {
            let frame = self.wheel_frame.unwrap_or_else(|| layout.index(pointer.x));
            self.hover_sweep = Some(HoverSweep {
                frame,
                inside_at: now,
            });
            return Some(frame);
        }
        if let Some(mut hover) = self.hover_sweep {
            let grace = layout.hit.expand2(egui::vec2(0.0, 40.0));
            if grace.contains(pointer) && now - hover.inside_at <= 0.30 {
                hover.frame = layout.index(pointer.x);
                self.hover_sweep = Some(hover);
                ui.ctx()
                    .request_repaint_after(std::time::Duration::from_millis(20));
                return Some(hover.frame);
            }
        }
        self.hover_sweep = None;
        self.wheel_frame = None;
        self.wheel_origin = None;
        None
    }
}

#[cfg(test)]
fn areas(
    meta: AdmissionMeta,
    level: usize,
    cells: impl Iterator<Item = bool>,
    aperture: Rect,
) -> [Area; 2] {
    let mut scene = Area::default();
    let mut window = Area::default();
    let membership = SampleWindow::new(level, meta, aperture);
    for (index, admitted) in cells.enumerate() {
        scene.observed += 1;
        scene.admitted += usize::from(admitted);
        // Half-open windows partition the transmitted grid without double-
        // counting a boundary sample when adjacent regions are compared.
        if membership.is_some_and(|window| window.contains(index)) {
            window.observed += 1;
            window.admitted += usize::from(admitted);
        }
    }
    [scene, window]
}

fn scale_name(
    level: usize,
    base: bool,
    geometry: Option<crate::process_output_space::OutputGeometry>,
) -> String {
    if base {
        "broad tone".into()
    } else {
        crate::process_output_space::detail_label(level, geometry)
    }
}

#[cfg(test)]
fn anchors(count: usize, width: f32) -> Vec<usize> {
    anchors_at_height(count, width, HEIGHT)
}
fn anchors_at_height(count: usize, width: f32, height: f32) -> Vec<usize> {
    if count == 0 || !width.is_finite() || width < 240.0 {
        return Vec::new();
    }
    if count == 1 {
        return vec![0];
    }
    // Contacts have legible image area at every size. The capture axis remains
    // continuous even when a long bracket needs evenly sampled contact slots.
    let minimum_width = MIN_CONTACT_WIDTH.max(contact_height(height) * 1.35);
    let slots = (((width - 12.0) / (minimum_width + CONTACT_GAP)).floor() as usize)
        .clamp(2, MAX_CONTACTS)
        .min(count);
    (0..slots)
        .map(|slot| {
            ((slot as u128 * (count - 1) as u128 + (slots - 1) as u128 / 2) / (slots - 1) as u128)
                as usize
        })
        .collect()
}

struct Layout {
    rect: Rect,
    hit: Rect,
    count: usize,
    columns: usize,
    contacts: usize,
    left: f32,
    right: f32,
    contact_width: f32,
    contact_height: f32,
    source_mode: bool,
}
impl Layout {
    fn new(rect: Rect, count: usize, contacts: usize) -> Option<Self> {
        if count == 0 || contacts == 0 || rect.width() < 240.0 || rect.height() < 72.0 {
            return None;
        }
        let desired_height = contact_height(rect.height());
        let contact_width = ((rect.width() - 12.0) / contacts as f32 - CONTACT_GAP)
            .clamp(0.0, CONTACT_WIDTH.max(desired_height * 1.8));
        // The evidence axis occupies the filmstrip's complete outer bounds.
        // Photograph centers are inset independently so edge cards remain
        // fully visible without shortening the capture coordinate system.
        let left = rect.left() + 6.0;
        let right = rect.right() - 6.0;
        Some(Self {
            rect,
            hit: Rect::from_min_max(
                egui::pos2(left, rect.top() + 28.0),
                egui::pos2(right, rect.bottom()),
            ),
            count,
            columns: count.min(((right - left) / 2.0).floor().max(1.0) as usize),
            contacts,
            left,
            right,
            contact_width,
            contact_height: desired_height.min(contact_width / 1.2),
            source_mode: false,
        })
    }
    fn x(&self, frame: usize) -> f32 {
        if self.count == 1 {
            (self.left + self.right) * 0.5
        } else {
            egui::lerp(
                self.left..=self.right,
                frame as f32 / (self.count - 1) as f32,
            )
        }
    }
    fn index(&self, x: f32) -> usize {
        if self.count == 1 {
            0
        } else {
            (((x - self.left) / (self.right - self.left)).clamp(0.0, 1.0) * (self.count - 1) as f32)
                .round() as usize
        }
    }
    fn index_at(&self, at: Pos2, contacts: &[usize]) -> usize {
        // Exact card identity is for deliberate clicks only. Hovering and
        // dragging anywhere across the row always use the continuous axis.
        contacts
            .iter()
            .copied()
            .find(|&frame| {
                let image = self.contact(frame);
                Rect::from_min_max(image.min, egui::pos2(image.right(), self.rect.bottom()))
                    .contains(at)
            })
            .unwrap_or_else(|| self.index(at.x))
    }
    fn lane(&self, row: usize) -> Rect {
        let count = if self.source_mode { 3.0 } else { 1.0 };
        let gap = 6.0;
        let height = (graph_height(self.rect.height()) - gap * (count - 1.0)) / count;
        let (top, pitch) = (if self.source_mode { 28.0 } else { 32.0 }, height + gap);
        let row = if self.source_mode { row } else { 0 };
        Rect::from_min_max(
            egui::pos2(self.left, self.rect.top() + top + row as f32 * pitch),
            egui::pos2(
                self.right,
                self.rect.top() + top + height + row as f32 * pitch,
            ),
        )
    }
    fn range(&self, column: usize) -> std::ops::Range<usize> {
        column * self.count / self.columns..(column + 1) * self.count / self.columns
    }
    fn column_x(&self, column: usize) -> f32 {
        let range = self.range(column);
        (self.x(range.start) + self.x(range.end - 1)) * 0.5
    }
    fn cell(&self, row: usize, column: usize) -> Rect {
        let lane = self.lane(row);
        let range = self.range(column);
        let half_step = if self.count == 1 {
            8.0
        } else {
            (self.right - self.left) / (self.count - 1) as f32 * 0.5
        };
        Rect::from_min_max(
            egui::pos2(
                if range.start == 0 {
                    self.left
                } else {
                    self.x(range.start) - half_step + 0.35
                },
                lane.top(),
            ),
            egui::pos2(
                if range.end == self.count {
                    self.right
                } else {
                    self.x(range.end - 1) + half_step - 0.35
                },
                lane.bottom(),
            ),
        )
    }
    fn contact(&self, frame: usize) -> Rect {
        // Rounded capture indices have uneven intervals. Placing large cards
        // directly on those intervals creates holes (and, near a sampling
        // boundary, overlaps). The contact row has even slots; lane x() above
        // remains the true capture coordinate, and index_at() reads the exact
        // identity of the photograph under the pointer.
        let x = if self.contacts <= 1 {
            (self.left + self.right) * 0.5
        } else {
            let slot = contact_slot(frame, self.count, self.contacts);
            egui::lerp(
                (self.left + self.contact_width * 0.5)..=(self.right - self.contact_width * 0.5),
                slot as f32 / (self.contacts - 1) as f32,
            )
        };
        Rect::from_center_size(
            egui::pos2(x, self.contact_top() + self.contact_height * 0.5),
            egui::vec2(self.contact_width, self.contact_height),
        )
    }
    fn contact_top(&self) -> f32 {
        self.rect.top() + 38.0 + graph_height(self.rect.height())
    }
}

fn contact_slot(frame: usize, count: usize, contacts: usize) -> usize {
    if contacts <= 1 {
        return 0;
    }
    (frame as f32 * (contacts - 1) as f32 / count.saturating_sub(1).max(1) as f32).round() as usize
}

fn contact_height(height: f32) -> f32 {
    (height - 64.0 - graph_height(height)).clamp(8.0, 240.0)
}

fn dashed_line(painter: &egui::Painter, a: Pos2, b: Pos2, stroke: Stroke) {
    let delta = b - a;
    let length = delta.length();
    if length <= f32::EPSILON {
        return;
    }
    let direction = delta / length;
    let mut start = 0.0;
    while start < length {
        painter.line_segment(
            [
                a + direction * start,
                a + direction * (start + 3.0).min(length),
            ],
            stroke,
        );
        start += 6.0;
    }
}

fn graph_height(height: f32) -> f32 {
    (height * 0.24 + 4.0)
        .clamp(54.0, 84.0)
        .min((height - 60.0).max(12.0))
}

fn contact_refinement_fits(
    native: &TextureHandle,
    canonical: &crate::workbench::SourcePhoto,
    image: Rect,
    pixels_per_point: f32,
) -> bool {
    let native_size = native.size_vec2();
    let canonical_size = canonical.texture.size_vec2();
    let aperture = egui::vec2(canonical.aperture[0] as f32, canonical.aperture[1] as f32);
    if aperture.min_elem() <= 0.0 || canonical_size.min_elem() <= 0.0 {
        return false;
    }
    let native_aspect = native_size.x / native_size.y;
    let aperture_aspect = aperture.x / aperture.y;
    let canonical_aspect = canonical_size.x / canonical_size.y;
    // Native letterboxed contacts can have a different crop. Their low tier
    // cannot be treated as a canonical preview, even inside a fixed card.
    let compatible = (native_aspect / aperture_aspect - 1.0).abs() <= 0.01
        && (canonical_aspect / aperture_aspect - 1.0).abs() <= 0.01;
    let native_pixels = native_size * contact_uv(native, image).size();
    let required = image.size() * pixels_per_point;
    compatible
        && canonical_size.x > native_size.x
        && canonical_size.y > native_size.y
        && (required.x > native_pixels.x * 1.10 || required.y > native_pixels.y * 1.10)
}

fn contact_uv(texture: &TextureHandle, image: Rect) -> Rect {
    let [width, height] = texture.size();
    let source = width as f32 / height.max(1) as f32;
    let target = image.width() / image.height().max(f32::EPSILON);
    let extent = if source > target {
        egui::vec2(target / source, 1.0)
    } else {
        egui::vec2(1.0, source / target)
    };
    Rect::from_center_size(egui::pos2(0.5, 0.5), extent)
}

#[cfg(test)]
#[path = "process-participation-tests.rs"]
mod tests;

#[cfg(test)]
#[path = "process-participation-interaction-tests.rs"]
mod interaction_tests;

#[cfg(test)]
#[path = "process-participation-selection-tests.rs"]
mod selection_tests;

#[cfg(test)]
#[path = "process-participation-coordinate-review-tests.rs"]
mod coordinate_review_tests;

#[cfg(test)]
#[path = "process-participation-hover-tests.rs"]
mod hover_tests;

#[cfg(test)]
#[path = "process-participation-scrub-tests.rs"]
mod scrub_tests;

#[cfg(test)]
#[path = "process-participation-v24-tests.rs"]
mod v24_tests;

#[cfg(test)]
#[path = "process-participation-v25-tests.rs"]
mod v25_tests;

#[cfg(test)]
#[path = "process-participation-v26-tests.rs"]
mod v26_tests;
