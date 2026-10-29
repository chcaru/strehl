//! Additive camera-RGB seam for optional original-CFA reconstruction.
//!
//! The ordinary writer never calls this module. Its native mosaic is already
//! normalized and white-balanced before MHC; moving those operations after MHC
//! would change cross-channel interpolation and is deliberately not done here.
use super::*;

pub(crate) struct NativeCameraImage {
    pub width: usize,
    pub height: usize,
    /// Interleaved normalized, white-balanced camera RGB, before matrix,
    /// highlight treatment or display tone. Rejected pixels retain exact bits.
    pub pixels: Vec<f32>,
    /// Tone frozen from the unchanged native CFA mosaic, never the candidate.
    pub develop: Develop,
}

/// Exact radiometric expression used before the existing MHC interpolation.
/// Exposing the operands avoids silently changing multiply/divide ordering.
#[derive(Clone, Copy)]
pub(crate) struct NativeNormalization {
    pub white_balance: [f32; 3],
    pub exposure_gain: f32,
    pub range: f32,
}
impl NativeNormalization {
    pub fn normalize(self, value: f32, channel: usize) -> f32 {
        value * self.white_balance[channel] * self.exposure_gain / self.range
    }

    /// Express the WB-aware native interpolation in camera DN for bookkeeping.
    /// This is never used to round-trip a retained native output pixel.
    pub fn camera_units(self, value: f32, channel: usize) -> f32 {
        value * self.range / (self.white_balance[channel] * self.exposure_gain)
    }
}

pub(crate) type NativeTransform<'a> =
    dyn FnMut(&mut NativeCameraImage, NativeNormalization) -> Result<()> + 'a;

pub(crate) struct NativeReconstruction<'a> {
    pub output_memory_budget: usize,
    pub transform: &'a mut NativeTransform<'a>,
}

pub(crate) fn reservation_bytes(width: usize, height: usize) -> Result<usize> {
    anyhow::ensure!(
        width >= 2 && height >= 2 && u32::try_from(width).is_ok() && u32::try_from(height).is_ok(),
        "invalid reconstruction output dimensions"
    );
    width
        .checked_mul(height)
        .and_then(|n| n.checked_mul(18))
        .and_then(|n| n.checked_add(1 << 20))
        .filter(|&n| n <= isize::MAX as usize)
        .context("reconstruction output reservation overflow")
}

pub(crate) fn prepare_native_camera_image(
    width: usize,
    height: usize,
    normalized_mosaic: &[f32],
    develop: &Develop,
    memory_budget: usize,
) -> Result<NativeCameraImage> {
    let reserved = reservation_bytes(width, height)?;
    anyhow::ensure!(
        reserved <= memory_budget,
        "reconstruction output exceeds its reserved memory budget"
    );
    anyhow::ensure!(
        normalized_mosaic.len() == width * height
            && normalized_mosaic.iter().all(|v| v.is_finite()),
        "invalid native reconstruction mosaic"
    );
    let mosaic = Mosaic {
        data: normalized_mosaic,
        width,
        height,
    };
    let develop = resolve_tone(develop, || tone_from_mosaic(&mosaic, develop));
    let mut pixels = Vec::new();
    pixels.try_reserve_exact(width * height * 3)?;
    pixels.resize(width * height * 3, 0.);
    pixels
        .par_chunks_mut(width * 3)
        .enumerate()
        .for_each(|(y, row)| demosaic_row(&mosaic, y, row));
    Ok(NativeCameraImage {
        width,
        height,
        pixels,
        develop,
    })
}

/// Consume the single final camera image. SDR is developed before reusing its
/// float buffer for the linear master, so no second full float image or second
/// demosaic is allocated. Candidates and fallback use exactly the same matrix,
/// highlight and display operations as the existing row writer.
pub(crate) fn write_reconstructed_camera_image(
    path: &Path,
    mut image: NativeCameraImage,
    linear_master: Option<&Path>,
    baked_recipe: Option<&strehl_edit::DevelopmentRecipe>,
) -> Result<()> {
    let (width, height) = (image.width, image.height);
    reservation_bytes(width, height)?;
    anyhow::ensure!(
        image.pixels.len() == width * height * 3 && image.pixels.iter().all(|v| v.is_finite()),
        "invalid reconstructed camera RGB"
    );
    anyhow::ensure!(
        !image.develop.wants_tone || image.develop.tone.is_some(),
        "reconstruction display tone was not frozen"
    );
    let matrix = if linear_master.is_some() {
        Some(
            image
                .develop
                .matrix
                .context("scene-linear master requires a camera color matrix")?,
        )
    } else {
        None
    };
    let mut rgb = Vec::new();
    rgb.try_reserve_exact(width * height * 3)?;
    rgb.resize(width * height * 3, 0_u16);
    rgb.par_chunks_exact_mut(3)
        .zip(image.pixels.par_chunks_exact(3))
        .for_each(|(dst, src)| {
            dst.copy_from_slice(&develop_pixel([src[0], src[1], src[2]], &image.develop));
        });
    if let (Some(master), Some(matrix)) = (linear_master, matrix) {
        image.pixels.par_chunks_exact_mut(3).for_each(|p| {
            let value = matrix.develop([p[0], p[1], p[2]]);
            p.copy_from_slice(&value);
        });
        let master_image = strehl_edit::LinearImage {
            width: width as u32,
            height: height as u32,
            pixels: image.pixels,
            origin: strehl_edit::ImageOrigin::SceneLinear,
            baseline: image.develop.tone.map(|tone| strehl_edit::DisplayBaseline {
                black: tone.black,
                white: tone.white,
                contrast: tone.contrast,
                exposure_gain: image.develop.exposure_gain,
            }),
            baked_recipe: baked_recipe.cloned(),
        };
        if let Some(parent) = master.parent().filter(|p| !p.as_os_str().is_empty()) {
            std::fs::create_dir_all(parent)?;
        }
        strehl_edit::save_linear_tiff(master, &master_image)?;
        eprintln!(
            "linear master   : {} ({width} x {height}, RGB32-float, BT.709/D65, pre-tone, direct-CFA reconstruction with native fallback)",
            master.display()
        );
    }
    write_rgb16_described(path, width as u32, height as u32, &rgb, &image.develop)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn session_reconstruction_output_unavailable_is_exact_native_and_candidate_is_not_demosaiced_twice()
     {
        let root = std::env::temp_dir().join(format!(
            "strehl-reconstruction-output-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir(&root).unwrap();
        let (w, h) = (80, 68);
        let mosaic: Vec<_> = (0..w * h)
            .map(|i| {
                let x = (i % w) as f32;
                let y = (i / w) as f32;
                let wb = match (i / w % 2, i % w % 2) {
                    (0, 0) => 2.7,
                    (1, 1) => 1.6,
                    _ => 1.0,
                };
                (0.18
                    + 0.2 * (x * 0.3).sin()
                    + 0.12 * (y * 0.17).cos()
                    + if x > 40. && y > 30. { 1.1 } else { 0. })
                    * wb
            })
            .collect();
        let dev = Develop {
            matrix: Some(
                color::Render::new([[1.4, -0.3, -0.1], [-0.2, 1.3, -0.1], [-0.1, -0.2, 1.3]])
                    .with_ceiling([2.7, 1., 1.6]),
            ),
            srgb: true,
            wants_tone: true,
            exposure_gain: 1.2,
            ..Develop::default()
        };
        let a = root.join("native.tiff");
        let am = root.join("native-master.tiff");
        write_demosaiced_with_master(&a, w, h, &mosaic, &dev, Some(&am), None).unwrap();
        let prepared =
            prepare_native_camera_image(w, h, &mosaic, &dev, reservation_bytes(w, h).unwrap())
                .unwrap();
        let expected = prepared.pixels.clone();
        let frozen = prepared.develop;
        let b = root.join("fallback.tiff");
        let bm = root.join("fallback-master.tiff");
        write_reconstructed_camera_image(&b, prepared, Some(&bm), None).unwrap();
        assert_eq!(std::fs::read(a).unwrap(), std::fs::read(b).unwrap());
        assert_eq!(std::fs::read(am).unwrap(), std::fs::read(bm).unwrap());
        let mut changed =
            prepare_native_camera_image(w, h, &mosaic, &dev, reservation_bytes(w, h).unwrap())
                .unwrap();
        let i = 3 * (31 * w + 37);
        changed.pixels[i..i + 3].copy_from_slice(&[0.12, 0.27, 0.44]);
        let c = root.join("candidate.tiff");
        let cm = root.join("candidate-master.tiff");
        write_reconstructed_camera_image(&c, changed, Some(&cm), None).unwrap();
        let mut decoder =
            tiff::decoder::Decoder::new(std::io::BufReader::new(std::fs::File::open(cm).unwrap()))
                .unwrap();
        let tiff::decoder::DecodingResult::F32(values) = decoder.read_image().unwrap() else {
            panic!("wrong master type")
        };
        for (pixel, p) in expected.as_chunks::<3>().0.iter().enumerate() {
            let input = if pixel == i / 3 {
                [0.12, 0.27, 0.44]
            } else {
                [p[0], p[1], p[2]]
            };
            assert_eq!(
                values[pixel * 3..pixel * 3 + 3]
                    .iter()
                    .map(|v| v.to_bits())
                    .collect::<Vec<_>>(),
                frozen.matrix.unwrap().develop(input).map(f32::to_bits)
            );
        }
        assert!(prepare_native_camera_image(w, h, &mosaic, &dev, 1).is_err());
        assert!(reservation_bytes(usize::MAX, 2).is_err());
        std::fs::remove_dir_all(root).unwrap();
    }
}
