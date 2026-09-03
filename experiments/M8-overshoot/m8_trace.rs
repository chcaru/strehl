use std::fs::{self, OpenOptions};
use std::io::{BufWriter, Write};
use std::path::PathBuf;
use std::process::Command;

use anyhow::{Context, Result, bail, ensure};
use strehl_core::align::{Resampler, Similarity};
use strehl_core::plane::PlaneGeometry;

const MAGIC: &[u8; 8] = b"M8SITE01";
const VERSION: u32 = 2;

fn write_u32(w: &mut impl Write, v: usize) -> Result<()> {
    w.write_all(
        &u32::try_from(v)
            .context("M8 trace dimension exceeds u32")?
            .to_le_bytes(),
    )?;
    Ok(())
}

fn f32_bytes(values: &[f32]) -> &[u8] {
    assert!(
        cfg!(target_endian = "little"),
        "M8 trace protocol is little-endian"
    );
    // SAFETY: f32 has no invalid bit patterns, the byte length is exact, and
    // the returned slice cannot outlive `values`.
    unsafe {
        std::slice::from_raw_parts(values.as_ptr().cast::<u8>(), std::mem::size_of_val(values))
    }
}

#[allow(clippy::too_many_arguments)]
pub fn trace_site(
    frame: &strehl_raw::Frame,
    site_x: usize,
    site_y: usize,
    geom: PlaneGeometry,
    transform: Similarity,
    cx: f64,
    cy: f64,
    channel: usize,
    site_gain: f32,
    resampler: Resampler,
    source: &[f32],
    trace: &[f32],
) -> Result<()> {
    let Some(root) = std::env::var_os("STREHL_M8_TRACE_DIR") else {
        return Ok(());
    };
    let checker = std::env::var_os("STREHL_M8_CHECKER")
        .context("STREHL_M8_TRACE_DIR requires STREHL_M8_CHECKER")?;
    let capture = std::env::var("STREHL_M8_CAPTURE")
        .context("STREHL_M8_TRACE_DIR requires STREHL_M8_CAPTURE")?;
    let kernel = match resampler {
        Resampler::CatmullRom => 0u32,
        Resampler::Bilinear => 1u32,
        other => bail!("M8 trace supports Catmull-Rom and bilinear, got {other:?}"),
    };
    let root = PathBuf::from(root);
    let blocks = root.join("blocks");
    let seen = root.join("seen");
    fs::create_dir_all(&blocks)?;
    fs::create_dir_all(&seen)?;
    let stem = frame
        .path
        .file_stem()
        .and_then(|s| s.to_str())
        .context("M8 trace frame name is not UTF-8")?;
    let marker = seen.join(format!("{stem}-{site_x}{site_y}"));
    if marker.exists() {
        return Ok(());
    }
    let block = blocks.join(format!("{stem}-{site_x}{site_y}.m8site"));
    let file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&block)
        .with_context(|| format!("creating unique M8 block {}", block.display()))?;
    let mut w = BufWriter::new(file);
    let src_w = 2 * geom.width;
    let src_h = 2 * geom.height;
    ensure!(
        source.len() == src_w * src_h,
        "M8 source is not full-resolution"
    );
    ensure!(
        trace.len() == geom.pixels(),
        "M8 trace is not destination-sized"
    );
    w.write_all(MAGIC)?;
    w.write_all(&VERSION.to_le_bytes())?;
    w.write_all(&kernel.to_le_bytes())?;
    for v in [
        src_w,
        src_h,
        geom.width,
        geom.height,
        site_x,
        site_y,
        channel,
    ] {
        write_u32(&mut w, v)?;
    }
    for v in [
        transform.a.re,
        transform.a.im,
        transform.b.re,
        transform.b.im,
        cx,
        cy,
    ] {
        w.write_all(&v.to_le_bytes())?;
    }
    w.write_all(&frame.levels.range().to_le_bytes())?;
    w.write_all(&site_gain.to_le_bytes())?;
    let frame_path = frame.path.to_string_lossy();
    write_u32(&mut w, frame_path.len())?;
    w.write_all(frame_path.as_bytes())?;
    w.write_all(f32_bytes(source))?;
    w.write_all(f32_bytes(trace))?;
    w.flush()?;
    drop(w);

    let status = Command::new("python")
        .arg("-B")
        .arg(checker)
        .arg("consume")
        .arg("--block")
        .arg(&block)
        .arg("--state")
        .arg(&root)
        .arg("--capture")
        .arg(&capture)
        .env("PYTHONIOENCODING", "utf-8")
        .status()
        .context("launching independent M8 checker")?;
    if !status.success() {
        bail!(
            "independent M8 checker failed on {}; block retained",
            block.display()
        );
    }
    OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&marker)
        .with_context(|| format!("creating unique M8 seen marker {}", marker.display()))?;
    fs::remove_file(&block)
        .with_context(|| format!("removing consumed M8 block {}", block.display()))?;
    Ok(())
}
