//! Control arm for the full-potential prototype: member 1 of every group,
//! demosaiced (Malvar-He-Cutler, the shipped default), in the prototype's
//! assembled-plane format. Running the same fusion on it prices what the four
//! shots add over one exposure per plane.
//!
//! `cargo run --locked --release -p strehl-cli --example a7cr-export-demosaic1 -- DIR OUT_DIR`
//!
//! Per recorded group, `OUT_DIR/pNNN.u16`: `[3, height, width]` little-endian
//! u16 = round(4 * (value + 64)), value in black-subtracted raw DN per
//! channel. The mosaic is white-balanced before the demosaic, as the merge
//! does, and each output channel is divided by its balance gain again so that
//! the units match the measured-colour planes. Read-only over the capture.
use anyhow::{Context, Result, ensure};
use rayon::prelude::*;
use std::io::Write;
use std::path::PathBuf;
use strehl_cli::pixel_shift_cmd::recorded_groups;
use strehl_core::demosaic::{Mosaic, demosaic_malvar_row};
use strehl_core::pixel_shift::{MemberView, balance, cfa_colour};

fn main() -> Result<()> {
    let a: Vec<String> = std::env::args().skip(1).collect();
    ensure!(a.len() == 2, "usage: DIR OUT_DIR");
    let (dir, out) = (PathBuf::from(&a[0]), PathBuf::from(&a[1]));
    std::fs::create_dir_all(&out)?;
    for g in recorded_groups(&dir)? {
        let Some(first) = g.files.first() else {
            continue;
        };
        let target = out.join(format!("p{:03}.u16", g.plane));
        if target.exists() {
            continue;
        }
        let f =
            strehl_raw::decode(&first.path).with_context(|| first.path.display().to_string())?;
        let m = MemberView {
            data: &f.data,
            stride: f.stride,
            buffer_height: f.buffer_height,
            active: [f.active.x, f.active.y, f.active.width, f.active.height],
            black: f.levels.black,
            white: f.levels.white,
        };
        let wb = balance(&m);
        let [ax, ay, w, h] = m.active;
        let mut mosaic = vec![0f32; w * h];
        mosaic.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
            let src = &m.data[(ay + y) * m.stride + ax..][..w];
            for (x, o) in row.iter_mut().enumerate() {
                *o = (f32::from(src[x]) - m.black) * wb[cfa_colour(x as isize, y as isize)];
            }
        });
        let mm = Mosaic {
            data: &mosaic,
            width: w,
            height: h,
        };
        let mut planes = vec![0u16; 3 * w * h];
        let (r, rest) = planes.split_at_mut(w * h);
        let (gr, b) = rest.split_at_mut(w * h);
        r.par_chunks_mut(w)
            .zip(gr.par_chunks_mut(w))
            .zip(b.par_chunks_mut(w))
            .enumerate()
            .for_each(|(y, ((rr, gg), bb))| {
                let mut row = vec![0f32; w * 3];
                demosaic_malvar_row(&mm, y, &mut row);
                let enc = |v: f32, gain: f32| {
                    ((v / gain + 64.0) * 4.0).round().clamp(0.0, 65535.0) as u16
                };
                for x in 0..w {
                    rr[x] = enc(row[3 * x], wb[0]);
                    gg[x] = enc(row[3 * x + 1], wb[1]);
                    bb[x] = enc(row[3 * x + 2], wb[2]);
                }
            });
        let bytes: Vec<u8> = planes.iter().flat_map(|v| v.to_le_bytes()).collect();
        std::fs::File::create(&target)?.write_all(&bytes)?;
        eprintln!("plane {}", g.plane);
    }
    Ok(())
}
