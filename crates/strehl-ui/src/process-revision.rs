//! Conservative spatial revisions of observed coarse green estimates.
//!
//! This compares the physical intervals represented by the producer's rounded
//! 8-bit linear samples, not display colours or independently normalised bytes.
//! Zero means the two intervals overlap: change is unresolved, not absent.
//! A revision is activity between two observed accepted prefixes, never a
//! sharpness, quality, noise estimate, or isolated per-frame contribution.

use crate::pipeline::{DiagnosticKind, DiagnosticScale, DiagnosticScope, DiagnosticSurface};
use std::collections::VecDeque;

const WIDTH: usize = 64;
const HEIGHT: usize = 48;
// Tiny summaries retain the full trace of a deep bracket without recycling its
// early marks. Pixel payloads still retain only the current comparison.
const HISTORY: usize = 4096;

#[derive(Clone, Debug)]
pub(crate) struct RevisionSummary {
    pub sequence: u64,
    /// Exact accepted-prefix counts, which need not be consecutive.
    pub from: usize,
    pub to: usize,
    /// Zero-based capture identities, distinct from accepted-prefix counts.
    pub from_frame: usize,
    pub to_frame: usize,
    pub changed_samples: usize,
    pub total_samples: usize,
    /// Minimum and maximum signed interval separation in linear green DN.
    pub range_dn: [f32; 2],
}

#[derive(Clone, Debug)]
pub(crate) struct Revision {
    pub sequence: u64,
    pub from: usize,
    pub to: usize,
    pub from_frame: usize,
    pub to_frame: usize,
    pub width: usize,
    pub height: usize,
    pub extent: [usize; 2],
    /// Signed distance between disjoint quantization intervals in green DN.
    /// Positive is an increased estimate, negative a decreased estimate.
    /// Magnitude is a conservative resolvable movement, not the exact delta.
    /// Zero is unresolved; it must never be labelled "unchanged".
    pub signed_dn: Vec<f32>,
    pub changed_samples: usize,
    pub total_samples: usize,
    pub range_dn: [f32; 2],
}

#[derive(Debug)]
struct Baseline {
    packet: DiagnosticSurface,
    extent: [usize; 2],
}

#[derive(Debug, Default)]
pub(crate) struct RevisionField {
    baseline: Option<Baseline>,
    latest: Option<Revision>,
    history: VecDeque<RevisionSummary>,
}

impl RevisionField {
    /// Observe every incoming valid Preview packet before texture coalescing.
    /// Repeated or older sequences/prefixes do not replace retained evidence.
    /// A changed spatial domain seeds a new comparison and clears its history.
    pub(crate) fn observe(&mut self, packet: &DiagnosticSurface, extent: [usize; 2]) {
        if !valid(packet, extent) {
            return;
        }
        if let Some(previous) = &self.baseline {
            if packet.sequence <= previous.packet.sequence
                || packet.folded <= previous.packet.folded
            {
                return;
            }
            if previous.extent == extent
                && previous.packet.level == packet.level
                && previous.packet.width == packet.width
                && previous.packet.height == packet.height
            {
                let Some(revision) = compare(&previous.packet, packet, extent) else {
                    return;
                };
                if self.history.len() == HISTORY {
                    self.history.pop_front();
                }
                self.history.push_back(RevisionSummary {
                    sequence: revision.sequence,
                    from: revision.from,
                    to: revision.to,
                    from_frame: revision.from_frame,
                    to_frame: revision.to_frame,
                    changed_samples: revision.changed_samples,
                    total_samples: revision.total_samples,
                    range_dn: revision.range_dn,
                });
                self.latest = Some(revision);
            } else {
                self.latest = None;
                self.history.clear();
            }
        }
        self.baseline = Some(Baseline {
            packet: packet.clone(),
            extent,
        });
    }

    pub(crate) fn latest(&self) -> Option<&Revision> {
        self.latest.as_ref()
    }

    pub(crate) fn history(&self) -> &VecDeque<RevisionSummary> {
        &self.history
    }
}

fn valid(packet: &DiagnosticSurface, extent: [usize; 2]) -> bool {
    packet.kind == DiagnosticKind::Preview
        && packet.scope == DiagnosticScope::Stack
        && packet.scale == DiagnosticScale::Linear
        && packet.sequence > 0
        && packet.folded > 0
        && packet.level < 64
        && packet.width > 0
        && packet.width <= 512
        && packet.height > 0
        && packet.height <= 384
        && packet.pixels.len() == packet.width * packet.height
        && packet.min.is_finite()
        && packet.max.is_finite()
        && packet.min <= packet.max
        && f64::from(packet.max) - f64::from(packet.min) <= f64::from(f32::MAX)
        && !extent.contains(&0)
}

fn interval(packet: &DiagnosticSurface, index: usize) -> [f64; 2] {
    let sample = f64::from(packet.pixels[index]);
    let low = f64::from(packet.min);
    let span = f64::from(packet.max) - low;
    // The producer normalizes, multiplies and rounds in f32. Pad the nominal
    // half-bin endpoints outward to cover those operation-rounding errors;
    // a tiny arithmetic discrepancy is not resolved image movement. Extrema
    // are exact supplied f32 values, so a genuinely flat range stays exact.
    let pad = if span == 0.0 {
        0.0
    } else {
        4.0 * f64::from(f32::EPSILON) * (span + low.abs() + f64::from(packet.max).abs())
    };
    [
        (low + ((sample - 0.5) / 255.0).max(0.0) * span - pad).max(low),
        (low + ((sample + 0.5) / 255.0).min(1.0) * span + pad).min(f64::from(packet.max)),
    ]
}

fn separation(before: [f64; 2], after: [f64; 2]) -> Option<f32> {
    let gap = if after[0] > before[1] {
        after[0] - before[1]
    } else if after[1] < before[0] {
        after[1] - before[0]
    } else {
        0.0
    };
    let mut result = gap as f32;
    if !result.is_finite() {
        return None;
    }
    // Casting can round away from zero. Move one ULP toward zero rather than
    // overstate the lower bound on physical separation.
    if f64::from(result).abs() > gap.abs() {
        result = f32::from_bits(result.to_bits() - 1);
    }
    Some(result)
}

fn compare(
    before: &DiagnosticSurface,
    after: &DiagnosticSurface,
    extent: [usize; 2],
) -> Option<Revision> {
    let scale = (WIDTH as f64 / after.width as f64)
        .min(HEIGHT as f64 / after.height as f64)
        .min(1.0);
    let width = (after.width as f64 * scale).floor().max(1.0) as usize;
    let height = (after.height as f64 * scale).floor().max(1.0) as usize;
    let mut signed_dn = Vec::with_capacity(width * height);
    for y in 0..height {
        let source_y = ((2 * y + 1) * after.height / (2 * height)).min(after.height - 1);
        for x in 0..width {
            let source_x = ((2 * x + 1) * after.width / (2 * width)).min(after.width - 1);
            let index = source_y * after.width + source_x;
            signed_dn.push(separation(interval(before, index), interval(after, index))?);
        }
    }
    let changed_samples = signed_dn.iter().filter(|&&value| value != 0.0).count();
    let range_dn = [
        signed_dn.iter().copied().fold(f32::INFINITY, f32::min),
        signed_dn.iter().copied().fold(f32::NEG_INFINITY, f32::max),
    ];
    Some(Revision {
        sequence: after.sequence,
        from: before.folded,
        to: after.folded,
        from_frame: before.frame,
        to_frame: after.frame,
        width,
        height,
        extent,
        total_samples: signed_dn.len(),
        signed_dn,
        changed_samples,
        range_dn,
    })
}

#[cfg(test)]
#[path = "process-revision-tests.rs"]
mod tests;
