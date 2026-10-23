//! Structured access to the same certified Gray16 evidence used by the lens.
//! This is called only by background workers, after the caller binds the result.
use super::*;
use serde_json::{Value, json};
use strehl_edit::RegionShape;

pub(crate) struct BalanceEvidence {
    size: [usize; 2],
    values: Vec<u16>,
}

pub(crate) fn read_evidence(
    path: &Path,
    expected: [usize; 2],
    cancelled: &AtomicBool,
) -> Result<BalanceEvidence> {
    let decoded = decode(path, expected, cancelled, &AtomicBool::new(false))?;
    Ok(BalanceEvidence {
        size: decoded.size,
        values: decoded.values,
    })
}

impl BalanceEvidence {
    /// Spatially stratified bounded samples. Missing evidence is never zero.
    pub(crate) fn probe(&self, region: &RegionShape) -> Value {
        let (min, max) = region.bounds();
        let aperture = Rect::from_min_max(egui::pos2(min[0], min[1]), egui::pos2(max[0], max[1]));
        let window = PixelWindow::enclosing(self.size, aperture);
        let sampled = sampled_size(window.extent(), 256);
        let mut histogram = [0u32; BINS];
        let (mut missing, mut observed, mut sum) = (0u32, 0u32, 0u64);
        let (mut lowest, mut highest) = (1000u16, 0u16);
        for y in 0..sampled[1] {
            let sy = window.min[1] + sample_index(y, sampled[1], window.extent()[1]);
            for x in 0..sampled[0] {
                let sx = window.min[0] + sample_index(x, sampled[0], window.extent()[0]);
                let uv = [
                    (sx as f32 + 0.5) / self.size[0] as f32,
                    (sy as f32 + 0.5) / self.size[1] as f32,
                ];
                if !region.contains(uv) {
                    continue;
                }
                let value = self.values[sy * self.size[0] + sx];
                if value == MISSING {
                    missing += 1;
                    continue;
                }
                observed += 1;
                sum += u64::from(value);
                lowest = lowest.min(value);
                highest = highest.max(value);
                histogram[(usize::from(value) * BINS / 1000).min(BINS - 1)] += 1;
            }
        }
        json!({
            "available":true,"analysis_size":self.size,"sampling":"stratified grid, at most 256 pixels per side",
            "observed":observed,"missing":missing,"histogram":histogram,"histogram_domain":[0,1000],
            "mean_rank":(observed>0).then(||sum as f64/f64::from(observed)),
            "minimum_rank":(observed>0).then_some(lowest),"maximum_rank":(observed>0).then_some(highest),
            "meaning":"0 one-sided, 1000 balanced; ties also read 0. Neither end is a quality grade.",
            "limitations":"Folded rank omits direction, distance, source identity and observation count; not a clipping or sharpness probability."
        })
    }

    pub(crate) fn preview(&self, region: Option<&RegionShape>, max_side: u32) -> image::RgbaImage {
        let (min, max) = region
            .map(RegionShape::bounds)
            .unwrap_or(([0.0, 0.0], [1.0, 1.0]));
        let window = PixelWindow::enclosing(
            self.size,
            Rect::from_min_max(egui::pos2(min[0], min[1]), egui::pos2(max[0], max[1])),
        );
        let extent = window.extent();
        let sampled = sampled_size(extent, max_side.clamp(1, 1024) as usize);
        image::RgbaImage::from_fn(sampled[0] as u32, sampled[1] as u32, |x, y| {
            let sx = window.min[0] + sample_index(x as usize, sampled[0], extent[0]);
            let sy = window.min[1] + sample_index(y as usize, sampled[1], extent[1]);
            let uv = [
                (sx as f32 + 0.5) / self.size[0] as f32,
                (sy as f32 + 0.5) / self.size[1] as f32,
            ];
            if region.is_some_and(|region| !region.contains(uv)) {
                return image::Rgba([0, 0, 0, 0]);
            }
            let color = palette(self.values[sy * self.size[0] + sx]);
            image::Rgba(color.to_array())
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn centrality_extremes_and_missing_evidence_remain_distinct() {
        let evidence = BalanceEvidence {
            size: [4, 1],
            values: vec![0, 1000, MISSING, 500],
        };
        let full = RegionShape::Rectangle {
            min: [0.0, 0.0],
            max: [1.0, 1.0],
        };
        let probe = evidence.probe(&full);
        assert_eq!(probe["observed"], 3);
        assert_eq!(probe["missing"], 1);
        assert_eq!(probe["mean_rank"], 500.0);
        assert_eq!(probe["minimum_rank"], 0);
        assert_eq!(probe["maximum_rank"], 1000);
        let preview = evidence.preview(None, 64);
        assert_eq!(preview.get_pixel(2, 0).0, [0, 0, 0, 0]);
        assert_ne!(preview.get_pixel(0, 0), preview.get_pixel(1, 0));
        assert_eq!(preview.get_pixel(0, 0).0[3], 255);
        let missing = RegionShape::Rectangle {
            min: [0.5, 0.0],
            max: [0.75, 1.0],
        };
        let probe = evidence.probe(&missing);
        assert_eq!(probe["observed"], 0);
        assert_eq!(probe["missing"], 1);
        assert!(probe["mean_rank"].is_null());
    }
}
