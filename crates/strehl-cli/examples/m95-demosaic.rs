//! M95 arm 6: expose the shipped demosaic so an external instrument can be
//! certified against it.
//!
//! The measurement for this arm is written in Python, because that is where the
//! FFT band analysis and the ground-truth construction live. A Python
//! reimplementation of `strehl_core::demosaic` is only admissible evidence
//! about the *shipped* demosaic if it is shown to agree with the shipped
//! demosaic. This binary is the reference the port is checked against.
//!
//! It does nothing clever: read `f32` samples, run the real
//! [`strehl_core::demosaic::demosaic`] (or the bilinear reference arm), write
//! `f32` samples. No colour, no exposure, no tone curve, no resampling — any of
//! those would put a second stage between the thing under test and the file.
//!
//!     m95-demosaic <in.f32> <width> <height> <out.f32> [mhc|bilinear]
//!
//! `in.f32` is `width * height` little-endian `f32`, row-major, RGGB phase at
//! (0, 0). `out.f32` is `width * height * 3` little-endian `f32`, interleaved
//! RGB.
//!
//! This writes only to the path it is given and reads only the path it is
//! given. It is a test fixture, not a pipeline stage.

use std::fs;
use std::io::Write;

use strehl_core::demosaic::{demosaic, demosaic_bilinear_row, Mosaic};

fn main() -> anyhow::Result<()> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 5 {
        anyhow::bail!("usage: m95-demosaic <in.f32> <width> <height> <out.f32> [mhc|bilinear]");
    }
    let width: usize = args[2].parse()?;
    let height: usize = args[3].parse()?;
    let kind = args.get(5).map(String::as_str).unwrap_or("mhc");

    let bytes = fs::read(&args[1])?;
    let want = width * height * 4;
    anyhow::ensure!(
        bytes.len() == want,
        "input is {} bytes, expected {want} for {width}x{height} f32",
        bytes.len()
    );
    let data: Vec<f32> = bytes
        .as_chunks::<4>()
        .0
        .iter()
        .map(|c| f32::from_le_bytes(*c))
        .collect();

    let m = Mosaic {
        data: &data,
        width,
        height,
    };
    let mut out = vec![0.0f32; width * height * 3];
    match kind {
        "mhc" => demosaic(&m, &mut out),
        "bilinear" => {
            for y in 0..height {
                demosaic_bilinear_row(&m, y, &mut out[y * width * 3..(y + 1) * width * 3]);
            }
        }
        other => anyhow::bail!("unknown demosaic {other:?}, want mhc or bilinear"),
    }

    let mut f = std::io::BufWriter::new(fs::File::create(&args[4])?);
    for v in &out {
        f.write_all(&v.to_le_bytes())?;
    }
    f.flush()?;
    eprintln!("m95-demosaic: {kind} {width}x{height} -> {}", args[4]);
    Ok(())
}
