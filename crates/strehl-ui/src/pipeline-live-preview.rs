//! The latest real live Preview packet retained independently of GUI cadence,
//! recent-packet eviction, or log replay timing. No build gallery is retained.
use super::{DiagnosticKind, DiagnosticSurface};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Scope {
    total: usize,
    extent: Option<[usize; 2]>,
    origin: [usize; 2],
    level: usize,
    samples: [usize; 2],
}

#[derive(Debug, Default)]
pub(crate) struct LivePreview {
    pub(crate) latest: Option<DiagnosticSurface>,
    pub(crate) tone_range: Option<(f32, f32)>,
    pub(crate) generation: u64,
    scope: Option<Scope>,
}
impl LivePreview {
    #[cfg(test)]
    pub(crate) fn is_empty(&self) -> bool {
        self.latest.is_none()
    }

    /// Called only after strict packet validation. Retained packets share their
    /// Arc payload with the diagnostic ring; at most one 512x384 byte image.
    pub(crate) fn observe(
        &mut self,
        packet: &DiagnosticSurface,
        total: usize,
        extent: Option<[usize; 2]>,
        origin: [usize; 2],
    ) {
        if packet.kind != DiagnosticKind::Preview || packet.folded == 0 || packet.folded > total {
            return;
        }
        let scope = Scope {
            total,
            extent,
            origin,
            level: packet.level,
            samples: [packet.width, packet.height],
        };
        if self.scope != Some(scope) {
            self.latest = None;
            self.tone_range = None;
            self.generation = self.generation.wrapping_add(1);
            self.scope = Some(scope);
        }
        if self.tone_range.is_none() && packet.max > packet.min {
            self.tone_range = Some((packet.min, packet.max));
        }
        if self
            .latest
            .as_ref()
            .is_none_or(|old| (packet.folded, packet.sequence) > (old.folded, old.sequence))
        {
            self.latest = Some(packet.clone());
        }
    }
}

#[cfg(test)]
#[path = "pipeline-live-preview-tests.rs"]
mod tests;
