//! Bound output receipts and a streamed native-merge CFA master shared by simple
//! sessions and mosaics. One merged image, never an aligned source volume.
use anyhow::{Context, Result, ensure};
use sha2::{Digest, Sha256};
use std::io::{BufWriter, Read, Seek, Write};
use std::path::Path;
use strehl_core::plane::PlaneGeometry;

pub(super) fn sha256(path: &Path) -> Result<String> {
    let mut file = std::fs::File::open(path)
        .with_context(|| format!("hashing mosaic output {}", path.display()))?;
    let before = file.metadata()?;
    let mut hash = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let n = file.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        hash.update(&buffer[..n]);
    }
    let after = file.metadata()?;
    ensure!(
        before.len() == after.len() && before.modified().ok() == after.modified().ok(),
        "mosaic output changed while hashing"
    );
    Ok(crate::session_input::hex(&hash.finalize()))
}
pub(super) fn save_sensor(
    path: &Path,
    geometry: PlaneGeometry,
    planes: &[Vec<f32>; 4],
    metadata: &serde_json::Value,
) -> Result<()> {
    workspace_bytes(geometry)?;
    let file = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)?;
    let mut writer = BufWriter::new(file);
    write_sensor(&mut writer, geometry, planes, metadata)?;
    writer.flush()?;
    writer.get_ref().sync_all()?;
    Ok(())
}
/// Two bounded stripe buffers plus TIFF strip tables and small encoder state.
pub(super) fn workspace_bytes(geometry: PlaneGeometry) -> Result<usize> {
    let pixels = geometry
        .width
        .checked_mul(geometry.height)
        .context("sensor dimensions overflow")?;
    ensure!(
        pixels > 0 && pixels <= 33_000_000,
        "sensor dimensions exceed TIFF bounds"
    );
    let width = geometry
        .width
        .checked_mul(2)
        .context("sensor width overflow")?;
    let height = geometry
        .height
        .checked_mul(2)
        .context("sensor height overflow")?;
    width
        .checked_mul(height.min(32))
        .and_then(|n| n.checked_mul(8))
        .and_then(|n| n.checked_add(height.div_ceil(32).checked_mul(16)?))
        .and_then(|n| n.checked_add(64 << 10))
        .context("sensor writer reservation overflow")
}
fn write_sensor<W: Write + Seek>(
    writer: &mut W,
    geometry: PlaneGeometry,
    planes: &[Vec<f32>; 4],
    metadata: &serde_json::Value,
) -> Result<()> {
    let n = geometry
        .width
        .checked_mul(geometry.height)
        .context("sensor mosaic dimensions overflow")?;
    ensure!(
        n > 0 && n <= 33_000_000 && planes.iter().all(|p| p.len() == n),
        "sensor mosaic plane dimensions differ or exceed TIFF bounds"
    );
    let width = geometry
        .width
        .checked_mul(2)
        .context("sensor width overflow")?;
    let height = geometry
        .height
        .checked_mul(2)
        .context("sensor height overflow")?;
    let mut encoder = tiff::encoder::TiffEncoder::new(writer)?;
    let mut image = encoder.new_image::<tiff::encoder::colortype::Gray32Float>(
        width.try_into()?,
        height.try_into()?,
    )?;
    image.rows_per_strip(32)?;
    let description = serde_json::to_string(metadata)?;
    image
        .encoder()
        .write_tag(tiff::tags::Tag::ImageDescription, description.as_str())?;
    let mut rows = vec![0.0_f32; width * height.min(32)];
    let mut start = 0;
    while start < height {
        let count = (height - start).min(32);
        for y in 0..count {
            let sy = start + y;
            for x in 0..width {
                let channel = match (sy % 2, x % 2) {
                    (0, 0) => 0,
                    (0, 1) => 1,
                    (1, 0) => 3,
                    (1, 1) => 2,
                    _ => unreachable!(),
                };
                let value = planes[channel][(sy / 2) * geometry.width + x / 2];
                ensure!(value.is_finite(), "nonfinite final CFA sample");
                rows[y * width + x] = value;
            }
        }
        image.write_strip(&rows[..count * width])?;
        start += count;
    }
    image.finish()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn sensor_master_preserves_native_site_order_signed_values_and_schema() {
        let g = PlaneGeometry {
            width: 3,
            height: 2,
        };
        let planes = [vec![-2.0; 6], vec![3.0; 6], vec![7.0; 6], vec![5.0; 6]];
        let mut bytes = std::io::Cursor::new(Vec::new());
        let metadata = serde_json::json!({"schema":"strehl.mosaic-cfa-master.v1","cfa":"RGGB","coverage":"coverage.tiff"});
        write_sensor(&mut bytes, g, &planes, &metadata).unwrap();
        bytes.set_position(0);
        let mut decoder = tiff::decoder::Decoder::new(bytes).unwrap();
        assert_eq!(decoder.dimensions().unwrap(), (6, 4));
        assert_eq!(
            serde_json::from_str::<serde_json::Value>(
                &decoder
                    .get_tag_ascii_string(tiff::tags::Tag::ImageDescription)
                    .unwrap()
            )
            .unwrap(),
            metadata
        );
        let tiff::decoder::DecodingResult::F32(pixels) = decoder.read_image().unwrap() else {
            panic!("float CFA master")
        };
        assert_eq!(&pixels[0..6], &[-2.0, 3.0, -2.0, 3.0, -2.0, 3.0]);
        assert_eq!(&pixels[6..12], &[5.0, 7.0, 5.0, 7.0, 5.0, 7.0]);
    }
    #[test]
    fn native_master_preserves_every_site_and_partial_final_strip_without_mutation() {
        let g = PlaneGeometry {
            width: 5,
            height: 17,
        };
        let planes: [Vec<f32>; 4] = std::array::from_fn(|c| {
            (0..g.pixels())
                .map(|i| ((c * 1024 + i) as f32 - 1536.0) / 8.0)
                .collect()
        });
        let original = planes.clone();
        let mut bytes = std::io::Cursor::new(Vec::new());
        write_sensor(
            &mut bytes,
            g,
            &planes,
            &serde_json::json!({"stage":"native-merge-before-demosaic"}),
        )
        .unwrap();
        assert_eq!(planes, original);
        bytes.set_position(0);
        let mut decoder = tiff::decoder::Decoder::new(bytes).unwrap();
        assert_eq!(decoder.dimensions().unwrap(), (10, 34));
        let tiff::decoder::DecodingResult::F32(pixels) = decoder.read_image().unwrap() else {
            panic!("signed f32")
        };
        for y in 0..34 {
            for x in 0..10 {
                let c = [[0, 1], [3, 2]][y % 2][x % 2];
                assert_eq!(
                    pixels[y * 10 + x].to_bits(),
                    original[c][y / 2 * 5 + x / 2].to_bits()
                );
            }
        }
        assert!(workspace_bytes(g).unwrap() >= 2 * 10 * 32 * 4);
        assert!(
            workspace_bytes(PlaneGeometry {
                width: usize::MAX,
                height: 2
            })
            .is_err()
        );
        assert!(
            workspace_bytes(PlaneGeometry {
                width: 1,
                height: 0
            })
            .is_err()
        );
    }
}
