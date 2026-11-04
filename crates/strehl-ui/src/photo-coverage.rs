//! Final saved coverage is presentation support, never a new physical erosion.
use anyhow::{Context, Result, ensure};
use std::{path::Path, sync::Arc};

#[derive(Clone)]
pub(crate) struct Coverage {
    pub size: [u32; 2],
    pub values: Arc<[u8]>,
}

impl Coverage {
    /// Only an explicit mosaic completion attaches a coverage sidecar. Merely
    /// finding a similarly named file beside an ordinary photograph is insufficient.
    pub fn load(path: &Path, size: [u32; 2]) -> Result<Option<Arc<Self>>> {
        let directory = path.parent().context("Photograph directory missing")?;
        let completion = directory.join("completed.json");
        if !completion.is_file() {
            return Ok(None);
        }
        ensure!(
            completion.metadata()?.len() <= 1024 * 1024,
            "Completion receipt exceeds 1 MiB"
        );
        let receipt: serde_json::Value = serde_json::from_reader(std::fs::File::open(completion)?)?;
        if receipt["mode"].as_str() != Some("mosaic") {
            return Ok(None);
        }
        ensure!(
            receipt["schema"] == "strehl.session-completion.v1"
                && receipt["coverage"] == "coverage.tiff",
            "Mosaic completion has no supported coverage contract"
        );
        ensure!(
            size[0] > 0 && size[1] > 0 && u64::from(size[0]) * u64::from(size[1]) <= 80_000_000,
            "Coverage exceeds the photograph allocation limit"
        );
        let mask_path = directory.join("coverage.tiff");
        let checksum = receipt["coverage_sha256"]
            .as_str()
            .context("Mosaic coverage checksum missing")?;
        let scalar = strehl_edit::read_scalar_tiff(&mask_path, size, 80_000_000, Some(checksum))?;
        let strehl_edit::ScalarSamples::U8(values) = scalar.samples else {
            anyhow::bail!("Coverage must contain one exact Gray8 channel");
        };
        ensure!(
            values.iter().all(|&v| v == 0 || v == 255),
            "Coverage must contain binary 0/255 support"
        );
        Ok(Some(Arc::new(Self {
            size,
            values: values.into(),
        })))
    }

    /// A display sample is shown as missing if any original support in its
    /// footprint is missing. No checker color becomes photographic/export data.
    pub fn supported(&self, source: [u32; 2], min: [u32; 2], max: [u32; 2]) -> bool {
        let lo = [0, 1]
            .map(|c| (u64::from(min[c]) * u64::from(self.size[c]) / u64::from(source[c])) as u32);
        let hi = [0, 1].map(|c| {
            (u64::from(max[c]) * u64::from(self.size[c]))
                .div_ceil(u64::from(source[c]))
                .min(u64::from(self.size[c])) as u32
        });
        (lo[1]..hi[1])
            .all(|y| (lo[0]..hi[0]).all(|x| self.values[(y * self.size[0] + x) as usize] == 255))
    }

    pub fn checker_rgb(&self, source: [u32; 2], min: [u32; 2]) -> u8 {
        let sensor =
            [0, 1].map(|c| u64::from(min[c]) * u64::from(self.size[c]) / u64::from(source[c]));
        if (sensor[0] / 32 + sensor[1] / 32).is_multiple_of(2) {
            58
        } else {
            82
        }
    }

    pub fn apply_rgb(&self, size: [u32; 2], rgb: &mut [u8]) {
        for y in 0..size[1] {
            for x in 0..size[0] {
                if !self.supported(size, [x, y], [x + 1, y + 1]) {
                    let v = self.checker_rgb(size, [x, y]);
                    rgb[((y * size[0] + x) * 3) as usize..((y * size[0] + x) * 3 + 3) as usize]
                        .fill(v);
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn final_coverage_is_not_reeroded_and_display_bins_never_invent_support() {
        let coverage = Coverage {
            size: [4, 2],
            values: vec![255, 255, 0, 255, 255, 255, 255, 255].into(),
        };
        assert!(coverage.supported([4, 2], [1, 0], [2, 1]));
        assert!(!coverage.supported([4, 2], [2, 0], [3, 1]));
        assert!(!coverage.supported([2, 1], [1, 0], [2, 1]));
        let mut rgb = vec![123; 24];
        coverage.apply_rgb([4, 2], &mut rgb);
        assert_eq!(&rgb[..6], &[123; 6]);
        assert_eq!(&rgb[9..], &[123; 15]);
        assert_eq!(&rgb[6..9], &[58; 3]);
    }
    #[test]
    fn coverage_receipt_shape_type_and_binary_values_are_required() {
        let root = tempfile::tempdir().unwrap();
        let path = root.path().join("photograph.tiff");
        image::GrayImage::from_raw(2, 1, vec![255, 0])
            .unwrap()
            .save(root.path().join("coverage.tiff"))
            .unwrap();
        assert!(Coverage::load(&path, [2, 1]).unwrap().is_none());
        let receipt = root.path().join("completed.json");
        use sha2::{Digest, Sha256};
        let hash = Sha256::digest(std::fs::read(root.path().join("coverage.tiff")).unwrap())
            .iter()
            .map(|v| format!("{v:02x}"))
            .collect::<String>();
        std::fs::write(&receipt,serde_json::to_vec(&serde_json::json!({"schema":"strehl.session-completion.v1","mode":"mosaic","coverage":"coverage.tiff","coverage_sha256":hash})).unwrap()).unwrap();
        let c = Coverage::load(&path, [2, 1]).unwrap().unwrap();
        assert_eq!(c.values.as_ref(), &[255, 0]);
        assert!(Coverage::load(&path, [1, 2]).is_err());
        image::GrayImage::from_raw(2, 1, vec![255, 1])
            .unwrap()
            .save(root.path().join("coverage.tiff"))
            .unwrap();
        assert!(Coverage::load(&path, [2, 1]).is_err());
        image::RgbImage::new(2, 1)
            .save(root.path().join("coverage.tiff"))
            .unwrap();
        assert!(Coverage::load(&path, [2, 1]).is_err());
    }

    #[test]
    fn coverage_native_and_overview_preserve_supported_rgb_and_checkers_are_display_only() {
        use crate::development_job::DevelopmentJob;
        let image = Arc::new(strehl_edit::LinearImage {
            width: 8,
            height: 4,
            pixels: (0..96).map(|i| 0.02 + i as f32 * 0.004).collect(),
            origin: strehl_edit::ImageOrigin::DisplayReferred,
            baseline: None,
            baked_recipe: None,
        });
        let mut values = vec![255; 32];
        values[2] = 0;
        let coverage = Arc::new(Coverage {
            size: [8, 4],
            values: values.into(),
        });
        let ordinary = DevelopmentJob::native(image.clone(), Default::default());
        let covered = DevelopmentJob::native(image.clone(), Default::default())
            .with_coverage(Some(coverage.clone()));
        let cancel = std::sync::atomic::AtomicBool::new(false);
        for stride in [1, 2] {
            let request = strehl_edit::DisplayRegionRequest {
                min: [0, 0],
                max: [8, 4],
                stride,
            };
            let plain = crate::photo_viewport::prepare_job(
                &ordinary, false, request, &cancel, None, false, true,
            )
            .unwrap()
            .sdr
            .unwrap();
            let checked = crate::photo_viewport::prepare_job(
                &covered, false, request, &cancel, None, false, true,
            )
            .unwrap()
            .sdr
            .unwrap();
            for y in 0..checked.size[1] {
                for x in 0..checked.size[0] {
                    let min = [x as u32 * stride, y as u32 * stride];
                    let max = [min[0] + stride, min[1] + stride];
                    let i = y * checked.size[0] + x;
                    if coverage.supported([8, 4], min, max) {
                        assert_eq!(checked.pixels[i], plain.pixels[i]);
                    } else {
                        assert_eq!(checked.pixels[i], eframe::egui::Color32::from_gray(58));
                    }
                }
            }
        }
        assert!(Arc::ptr_eq(covered.image(false), &image));
        assert_eq!(covered.image(false).pixels, ordinary.image(false).pixels);
        let root = tempfile::tempdir().unwrap();
        let path = root.path().join("covered.png");
        covered
            .export(
                &path,
                &strehl_edit::ExportSettings {
                    format: strehl_edit::ExportFormat::Png,
                    hdr: false,
                    ..Default::default()
                },
                &cancel,
            )
            .unwrap();
        let rgba = image::open(path).unwrap().into_rgba16();
        assert_eq!(rgba.get_pixel(2, 0)[3], 0);
        assert_eq!(rgba.get_pixel(1, 0)[3], 65535);
        assert_ne!(
            rgba.get_pixel(2, 0)[0],
            58 * 257,
            "Checker must never become exported image data"
        );
    }
}
