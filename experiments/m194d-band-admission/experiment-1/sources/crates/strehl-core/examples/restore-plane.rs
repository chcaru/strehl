//! Apply [`strehl_core::restore`] to image planes, for measurement.
//!
//! This exists so the restoration can be measured **as the shipped Rust code
//! actually computes it**, rather than through a Python reimplementation that
//! would only prove the reimplementation agrees with itself.
//!
//! It deliberately reads and writes a headered raw `f32` format rather than
//! TIFF. `strehl-core` has no image-format dependency and adding one to it, to
//! serve a measurement, would be the wrong trade: the format here is eight
//! bytes of header and a plane of little-endian `f32`, which any driver can
//! write. The driver that does so is
//! `experiments/BUILD-SHARP/src/restore_apply.py`.
//!
//! ```text
//! usage: restore-plane <in.raw> <out.raw> <grid_factor> <sigma2> <gain_cap>
//! ```
//!
//! Layout: `u32 w`, `u32 h`, then `w * h` little-endian `f32`, row major.
//! The report is printed to stdout as JSON.

use std::io::{Read, Write};

use strehl_core::align::Resampler;
use strehl_core::restore::{restore_plane, RestoreConfig};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 6 {
        eprintln!("usage: restore-plane <in.raw> <out.raw> <grid_factor> <sigma2> <gain_cap>");
        std::process::exit(2);
    }
    let cfg = RestoreConfig {
        resampler: Resampler::CatmullRom,
        grid_factor: args[3].parse()?,
        sigma2: args[4].parse()?,
        gain_cap: args[5].parse()?,
    };

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
    let mut plane: Vec<f32> = (0..w * h)
        .map(|i| {
            let o = 8 + i * 4;
            f32::from_le_bytes([bytes[o], bytes[o + 1], bytes[o + 2], bytes[o + 3]])
        })
        .collect();

    let report = restore_plane(&mut plane, w, h, &cfg);

    let mut out = Vec::with_capacity(want);
    out.extend_from_slice(&(w as u32).to_le_bytes());
    out.extend_from_slice(&(h as u32).to_le_bytes());
    for v in &plane {
        out.extend_from_slice(&v.to_le_bytes());
    }
    std::fs::File::create(&args[2])?.write_all(&out)?;

    let taps: Vec<String> = report.taps.iter().map(|t| format!("{t:.9}")).collect();
    println!(
        "{{\"w\":{w},\"h\":{h},\"dc_gain\":{:.12},\"max_gain\":{:.6},\
\"gain_at_nyquist\":{:.6},\"recovered_fraction\":{:.6},\"sigma2\":{:.4},\"taps\":[{}]}}",
        report.dc_gain,
        report.max_gain,
        report.gain_at_nyquist,
        report.recovered_fraction,
        report.sigma2,
        taps.join(",")
    );
    Ok(())
}
