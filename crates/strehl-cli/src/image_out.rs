//! 16-bit TIFF output.
//!
//! `tiff` 0.11 has a strips-only encoder — there is no tiled writer — and no
//! BigTIFF is needed at this size: the binned 3516x2344 RGB image is 49 MB and
//! the index map 16 MB, both far inside the 4 GB classic-TIFF limit. Tiled
//! float BigTIFF is a v1 requirement (SYNTHESIS §9), not a skeleton one.

use std::fs::File;
use std::io::BufWriter;
use std::path::Path;

use anyhow::{Context, Result};
use tiff::encoder::{TiffEncoder, colortype};

fn writer(path: &Path) -> Result<TiffEncoder<BufWriter<File>>> {
    if let Some(parent) = path.parent()
        && !parent.as_os_str().is_empty()
    {
        std::fs::create_dir_all(parent)
            .with_context(|| format!("creating {}", parent.display()))?;
    }
    let file = File::create(path).with_context(|| format!("creating {}", path.display()))?;
    TiffEncoder::new(BufWriter::new(file))
        .with_context(|| format!("starting TIFF {}", path.display()))
}

/// Interleaved RGB, 16 bits per channel.
pub fn write_rgb16(path: &Path, width: u32, height: u32, data: &[u16]) -> Result<()> {
    assert_eq!(data.len(), width as usize * height as usize * 3);
    writer(path)?
        .write_image::<colortype::RGB16>(width, height, data)
        .with_context(|| format!("writing {}", path.display()))
}

/// Single-channel 16-bit grayscale.
pub fn write_gray16(path: &Path, width: u32, height: u32, data: &[u16]) -> Result<()> {
    assert_eq!(data.len(), width as usize * height as usize);
    writer(path)?
        .write_image::<colortype::Gray16>(width, height, data)
        .with_context(|| format!("writing {}", path.display()))
}
