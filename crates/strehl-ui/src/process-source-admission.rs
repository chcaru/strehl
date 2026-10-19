//! Source companion mini-maps use fixed final-domain coordinates. Pan, zoom,
//! and pointer motion change only their viewport outline, not these samples.
use crate::{process_provenance::AdmissionArchive, process_sample_glyphs::SampleGeometry};
use eframe::egui::Pos2;

#[derive(Clone, Copy, PartialEq, Eq)]
struct Key {
    domain: [u64; 2],
    revision: u64,
    frame: usize,
    extent: [usize; 2],
    levels: usize,
}
#[derive(Default)]
pub(super) struct Band {
    pub counts: Option<(usize, usize)>,
    pub points: Vec<Pos2>,
}
#[derive(Default)]
pub(super) struct SourceAdmissionCache {
    key: Option<Key>,
    bands: Vec<Band>,
    #[cfg(test)]
    bit_reads: usize,
}
impl SourceAdmissionCache {
    pub(super) fn bands(
        &mut self,
        archive: &AdmissionArchive,
        domain: [u64; 2],
        frame: usize,
        extent: [usize; 2],
        levels: usize,
    ) -> &[Band] {
        let key = Key {
            domain,
            revision: archive.revision(),
            frame,
            extent,
            levels: levels.min(16),
        };
        if self.key == Some(key) {
            return &self.bands;
        }
        self.key = Some(key);
        self.bands.clear();
        for level in 0..key.levels {
            let mut band = Band::default();
            if let Some((meta, mut cells)) = archive.cells(level, frame)
                && meta.extent == extent
                && let Some(geometry) = SampleGeometry::new(level, meta)
            {
                let total = cells.len();
                let stride = total.div_ceil(192).max(1);
                let mut admitted = 0;
                for (index, yes) in cells.by_ref().enumerate() {
                    admitted += usize::from(yes);
                    if yes
                        && (admitted - 1) % stride == 0
                        && let Some(glyph) = geometry.at(index)
                    {
                        band.points.push(glyph.center);
                    }
                }
                #[cfg(test)]
                {
                    self.bit_reads += cells.bit_reads();
                }
                band.counts = Some((admitted, total));
            }
            self.bands.push(band);
        }
        &self.bands
    }
}

#[cfg(test)]
#[path = "process-source-admission-tests.rs"]
mod tests;
