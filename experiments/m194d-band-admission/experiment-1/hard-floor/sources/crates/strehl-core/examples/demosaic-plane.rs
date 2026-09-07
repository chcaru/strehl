//! Run [`strehl_core::demosaic`] on a mosaic, for measurement.
//!
//! The shipped render is **not** a quad collapse: it re-interleaves the merge's
//! four per-quad CFA estimates into a Bayer mosaic and demosaics it to full
//! sensor resolution. That step has never been priced, and it is the last
//! resampling-like operation the delivered pixels pass through.
//!
//! This exists so it can be measured **as the shipped Rust actually computes
//! it**, not through a Python transcription that would only prove the
//! transcription agrees with itself. That is the gap BUILD-SHARP left in the
//! pyramid measurement of section 21 and it is not left again here.
//!
//! Both arms are exposed, because a headline needs a different rule on
//! identical data rather than a better measurement of the same rule:
//! `malvar` is the shipping path, `bilinear` is `demosaic.rs`'s own reference.
//!
//! ```text
//! usage: demosaic-plane <in.raw> <out.raw> <malvar|bilinear>
//! ```
//!
//! Input layout: `u32 w`, `u32 h`, then `w * h` little-endian `f32`, row major,
//! interpreted as an **RGGB** mosaic. Output is the same header followed by
//! `w * h * 3` little-endian `f32`, interleaved RGB.

use std::io::{Read, Write};

use strehl_core::demosaic::{demosaic, demosaic_bilinear_row, Mosaic};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 4 {
        eprintln!("usage: demosaic-plane <in.raw> <out.raw> <malvar|bilinear>");
        std::process::exit(2);
    }

    let mut bytes = Vec::new();
    std::fs::File::open(&args[1])?.read_to_end(&mut bytes)?;
    if bytes.len() < 8 {
        return Err("input shorter than its header".into());
    }
    let w = u32::from_le_bytes(bytes[0..4].try_into()?) as usize;
    let h = u32::from_le_bytes(bytes[4..8].try_into()?) as usize;
    let want = 8 + w * h * 4;
    if bytes.len() != want {
        return Err(format!("{w}x{h} needs {want} bytes, file has {}", bytes.len()).into());
    }
    let data: Vec<f32> = (0..w * h)
        .map(|i| {
            let o = 8 + i * 4;
            f32::from_le_bytes([bytes[o], bytes[o + 1], bytes[o + 2], bytes[o + 3]])
        })
        .collect();

    let m = Mosaic { data: &data, width: w, height: h };
    let mut out = vec![0.0f32; w * h * 3];
    match args[3].as_str() {
        "malvar" => demosaic(&m, &mut out),
        "bilinear" => {
            for y in 0..h {
                demosaic_bilinear_row(&m, y, &mut out[y * w * 3..(y + 1) * w * 3]);
            }
        }
        other => return Err(format!("unknown arm {other:?}, want malvar or bilinear").into()),
    }

    let mut buf = Vec::with_capacity(8 + out.len() * 4);
    buf.extend_from_slice(&(w as u32).to_le_bytes());
    buf.extend_from_slice(&(h as u32).to_le_bytes());
    for v in &out {
        buf.extend_from_slice(&v.to_le_bytes());
    }
    std::fs::File::create(&args[2])?.write_all(&buf)?;
    println!("{{\"w\":{w},\"h\":{h},\"arm\":\"{}\"}}", args[3]);
    Ok(())
}
