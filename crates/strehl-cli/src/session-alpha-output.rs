//! Explicit transparency for optional union canvases. Ordinary output never
//! calls this module. RGB values and color metadata survive the alpha addition.
use super::*;
use anyhow::ensure;
use std::fs::OpenOptions;
use std::io::{BufReader, Write};
use strehl_core::plane::PlaneGeometry;
use tiff::decoder::{Decoder, DecodingResult};

pub(super) fn tone_from_supported_mosaic(m: &Mosaic, dev: &Develop, mask: &[bool]) -> Tone {
    let mut luminance = Vec::new();
    // Same sample grid and arithmetic as ordinary development, excluding only
    // missing quads. A thin supported strip may miss this grid: then sample all
    // supported quads rather than assigning tone from the union's storage zeros.
    for stride in [TONE_STRIDE, 1] {
        for y in (0..m.height - 1).step_by(2 * stride) {
            for x in (0..m.width - 1).step_by(2 * stride) {
                if !mask[(y / 2) * (m.width / 2) + x / 2] {
                    continue;
                }
                let i = y * m.width + x;
                let v = [
                    m.data[i],
                    0.5 * (m.data[i + 1] + m.data[i + m.width]),
                    m.data[i + m.width + 1],
                ];
                let v = match &dev.matrix {
                    Some(r) => r.develop(v),
                    None => v,
                };
                luminance.push(luma709(v));
            }
        }
        if !luminance.is_empty() {
            break;
        }
    }
    Tone::from_luminance(&mut luminance)
}

/// Coverage is conservative across both Malvar's radius-two sensor stencil and
/// the optional directional radius-three stencil: every quad within radius two
/// must exist. Canvas exterior is unknown. Sidecar samples are 0 or 255; alpha
/// is unassociated (straight), so supported RGB is never multiplied or changed.
pub(crate) fn apply_mosaic_coverage(
    photograph: &Path,
    coverage_output: &Path,
    quad_geometry: PlaneGeometry,
    quad_coverage: &[bool],
) -> Result<()> {
    ensure!(
        quad_coverage.len() == quad_geometry.pixels(),
        "mosaic coverage size differs"
    );
    let width = quad_geometry
        .width
        .checked_mul(2)
        .context("mosaic width overflow")?;
    let height = quad_geometry
        .height
        .checked_mul(2)
        .context("mosaic height overflow")?;
    let pixels = width.checked_mul(height).context("mosaic size overflow")?;
    let mut decoder = Decoder::new(BufReader::new(File::open(photograph)?))?;
    ensure!(
        decoder.dimensions()? == (width.try_into()?, height.try_into()?),
        "mosaic photograph dimensions differ"
    );
    ensure!(
        decoder.colortype()? == tiff::ColorType::RGB(16),
        "mosaic photograph must be RGB16"
    );
    let mut limits = tiff::decoder::Limits::default();
    limits.decoding_buffer_size = pixels.checked_mul(6).context("mosaic decode overflow")?;
    decoder = decoder.with_limits(limits);
    let description = decoder.get_tag_ascii_string(Tag::ImageDescription).ok();
    let software = decoder.get_tag_ascii_string(Tag::Software).ok();
    let profile = decoder.get_tag_u8_vec(Tag::IccProfile).ok();
    let resolution = [Tag::XResolution, Tag::YResolution].map(|tag| decoder.get_tag(tag).ok());
    let unit = decoder
        .get_tag(Tag::ResolutionUnit)
        .ok()
        .and_then(|v| match v {
            tiff::decoder::ifd::Value::Short(v) => Some(v),
            _ => None,
        });
    let DecodingResult::U16(rgb) = decoder.read_image()? else {
        anyhow::bail!("mosaic RGB storage differs");
    };
    ensure!(
        rgb.len() == pixels.checked_mul(3).context("mosaic RGB overflow")?,
        "mosaic RGB count differs"
    );
    drop(decoder);
    let mut scratch = vec![0; quad_geometry.pixels()];
    let mut supported = vec![false; quad_geometry.pixels()];
    crate::session_focus::complete_support(
        quad_coverage,
        quad_geometry,
        2,
        &mut scratch,
        &mut supported,
    )?;
    let mut rgba = Vec::with_capacity(pixels.checked_mul(4).context("mosaic RGBA overflow")?);
    let mut coverage = Vec::with_capacity(pixels);
    for (i, pixel) in rgb.as_chunks::<3>().0.iter().enumerate() {
        let ok = supported[(i / width / 2) * quad_geometry.width + (i % width) / 2];
        rgba.extend_from_slice(pixel);
        rgba.push(if ok { u16::MAX } else { 0 });
        coverage.push(if ok { 255 } else { 0 });
    }
    let temporary = photograph.with_extension("alpha-pending.tiff");
    let backup = photograph.with_extension("rgb-pending.tiff");
    ensure!(!backup.exists(), "mosaic temporary backup already exists");
    let mut output = BufWriter::new(
        OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temporary)?,
    );
    {
        let mut encoder = TiffEncoder::new(&mut output)?;
        let mut img =
            encoder.new_image::<colortype::RGBA16>(width.try_into()?, height.try_into()?)?;
        img.encoder().write_tag(Tag::ExtraSamples, &[2_u16][..])?;
        if let Some(description) = description {
            img.encoder()
                .write_tag(Tag::ImageDescription, description.as_str())?;
        }
        if let Some(software) = software {
            img.encoder().write_tag(Tag::Software, software.as_str())?;
        }
        if let Some(profile) = profile {
            img.encoder()
                .write_tag(Tag::IccProfile, IccBytes(&profile))?;
        }
        for (tag, value) in [Tag::XResolution, Tag::YResolution]
            .into_iter()
            .zip(resolution)
        {
            if let Some(tiff::decoder::ifd::Value::Rational(n, d)) = value {
                img.encoder().write_tag(tag, Rational { n, d })?;
            }
        }
        if let Some(unit) = unit {
            img.encoder().write_tag(Tag::ResolutionUnit, unit)?;
        }
        img.write_data(&rgba)?;
    }
    output.flush()?;
    output.get_ref().sync_all()?;
    drop(output);
    let mut mask = BufWriter::new(
        OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(coverage_output)?,
    );
    TiffEncoder::new(&mut mask)?.write_image::<colortype::Gray8>(
        width.try_into()?,
        height.try_into()?,
        &coverage,
    )?;
    mask.flush()?;
    mask.get_ref().sync_all()?;
    drop(mask);
    std::fs::rename(photograph, &backup)?;
    if let Err(error) = std::fs::rename(&temporary, photograph) {
        std::fs::rename(&backup, photograph)?;
        return Err(error.into());
    }
    std::fs::remove_file(backup)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn missing_union_storage_cannot_change_tone_and_all_valid_matches_ordinary() {
        let (w, h) = (84, 84);
        let mut data = vec![0.; w * h];
        for y in 0..h {
            for x in 0..w {
                data[y * w + x] = 0.05 + 0.5 * ((x / 2 + y / 2) % 29) as f32 / 28.;
            }
        }
        let dev = OutputSpace::from_flags(true, false).unwrap().develop(None);
        let mask = vec![true; w * h / 4];
        let m = Mosaic {
            data: &data,
            width: w,
            height: h,
        };
        let a = tone_from_mosaic(&m, &dev);
        let b = tone_from_supported_mosaic(&m, &dev, &mask);
        assert_eq!(
            [a.black, a.white, a.contrast],
            [b.black, b.white, b.contrast]
        );
        let mut mask = mask;
        for y in 0..h / 2 {
            for x in 0..w / 4 {
                mask[y * w / 2 + x] = false;
            }
        }
        let expected = tone_from_supported_mosaic(&m, &dev, &mask);
        for y in 0..h {
            for x in 0..w / 2 {
                data[y * w + x] = 100000.;
            }
        }
        let actual = tone_from_supported_mosaic(
            &Mosaic {
                data: &data,
                width: w,
                height: h,
            },
            &dev,
            &mask,
        );
        assert_eq!(
            [expected.black, expected.white, expected.contrast],
            [actual.black, actual.white, actual.contrast]
        );
        let contaminated = tone_from_mosaic(
            &Mosaic {
                data: &data,
                width: w,
                height: h,
            },
            &dev,
        );
        assert!(contaminated.white > actual.white * 100.);
    }
    #[test]
    fn rgba_preserves_rgb_metadata_and_refuses_missing_demosaic_support() {
        let root = std::env::temp_dir().join(format!(
            "strehl-alpha-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir(&root).unwrap();
        let photo = root.join("photo.tiff");
        let mask = root.join("coverage.tiff");
        let g = PlaneGeometry {
            width: 12,
            height: 11,
        };
        let (w, h) = (24_u32, 22_u32);
        let rgb: Vec<u16> = (0..w * h * 3).map(|i| (i * 31 % 65536) as u16).collect();
        let mut file = BufWriter::new(File::create(&photo).unwrap());
        {
            let mut encoder = TiffEncoder::new(&mut file).unwrap();
            let mut img = encoder.new_image::<colortype::RGB16>(w, h).unwrap();
            img.encoder()
                .write_tag(Tag::ImageDescription, "alpha fixture")
                .unwrap();
            img.encoder()
                .write_tag(Tag::IccProfile, IccBytes(&[1, 2, 3, 4]))
                .unwrap();
            img.resolution(ResolutionUnit::Inch, Rational { n: 300, d: 1 });
            img.write_data(&rgb).unwrap();
        }
        file.flush().unwrap();
        drop(file);
        let mut valid = vec![true; g.pixels()];
        valid[g.index(6, 5)] = false;
        apply_mosaic_coverage(&photo, &mask, g, &valid).unwrap();
        let mut dec = Decoder::new(BufReader::new(File::open(&photo).unwrap())).unwrap();
        assert_eq!(
            dec.get_tag_ascii_string(Tag::ImageDescription).unwrap(),
            "alpha fixture"
        );
        assert_eq!(dec.get_tag_u8_vec(Tag::IccProfile).unwrap(), [1, 2, 3, 4]);
        assert_eq!(dec.get_tag_u16_vec(Tag::ExtraSamples).unwrap(), [2]);
        assert_eq!(
            dec.get_tag(Tag::XResolution).unwrap(),
            tiff::decoder::ifd::Value::Rational(300, 1)
        );
        let DecodingResult::U16(rgba) = dec.read_image().unwrap() else {
            panic!()
        };
        let mut dec = Decoder::new(BufReader::new(File::open(&mask).unwrap())).unwrap();
        let DecodingResult::U8(mask) = dec.read_image().unwrap() else {
            panic!()
        };
        for (i, pixel) in rgba.as_chunks::<4>().0.iter().enumerate() {
            assert_eq!(&pixel[..3], &rgb[i * 3..i * 3 + 3]);
            let (x, y) = ((i % 24) / 2, (i / 24) / 2);
            let expected =
                (2..10).contains(&x) && (2..9).contains(&y) && !(x.abs_diff(6) <= 2 && y.abs_diff(5) <= 2);
            assert_eq!(pixel[3], if expected { 65535 } else { 0 });
            assert_eq!(mask[i], if expected { 255 } else { 0 });
        }
        drop(dec);
        std::fs::remove_dir_all(root).unwrap();
    }
}
