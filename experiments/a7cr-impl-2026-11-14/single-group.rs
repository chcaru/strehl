//! One recorded four-shot group, three ways, at full resolution, with no stack
//! and no warp: does pixel shift itself deliver on this camera?
//!
//! `cargo run --release -p strehl-cli --example a7cr-single-group -- DIR PLANE OUT_DIR`
//!
//! Arms, all over member 1's active area, white-balanced from member 1
//! (`pixel_shift::balance`), black-subtracted, linear:
//!   * `demosaic1`  member 1 alone, Malvar (the ordinary single exposure);
//!   * `demosaic4`  every member Malvar-demosaiced, read at its measured
//!     integer offset, divided by its measured exposure gain and averaged
//!     (the same photons as pixel shift, colour still interpolated: the
//!     control that separates pixel shift's colour sampling from its 4x light);
//!   * `shift`      `pixel_shift::assemble` (measured red, two greens, blue at
//!     every site; nothing interpolated).
//! Offsets and gains come from `pixel_shift::register` exactly as
//! `strehl pixel-shift` measures them. Crops: the six 384-px tiles with the
//! highest green high-pass energy in `demosaic1`, kept at least two crops
//! apart, written as little-endian f32 RGB (`crop{i}-{arm}.f32`) with
//! `crops.json` recording origins. Read-only over the capture.
use anyhow::{Context, Result, ensure};
use rayon::prelude::*;
use serde_json::json;
use std::path::PathBuf;
use strehl_cli::pixel_shift_cmd::{check_group, recorded_groups, views};
use strehl_core::demosaic::{Mosaic, demosaic_malvar_row};
use strehl_core::pixel_shift::{MemberView, assemble, balance, cfa_colour};

const C: usize = 384;

fn malvar(m: &MemberView<'_>, wb: [f32; 3]) -> Vec<f32> {
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
    let mut out = vec![0f32; w * h * 3];
    out.par_chunks_mut(w * 3)
        .enumerate()
        .for_each(|(y, row)| demosaic_malvar_row(&mm, y, row));
    out
}

fn main() -> Result<()> {
    let a: Vec<String> = std::env::args().skip(1).collect();
    ensure!(a.len() == 3, "usage: DIR PLANE OUT_DIR");
    let (dir, plane, out) = (
        PathBuf::from(&a[0]),
        a[1].parse::<u64>()?,
        PathBuf::from(&a[2]),
    );
    std::fs::create_dir_all(&out)?;
    let g = recorded_groups(&dir)?
        .into_iter()
        .find(|g| g.plane == plane)
        .context("no such plane")?;
    ensure!(
        g.complete && g.files.len() == 4,
        "plane {plane} is not a complete four-shot group"
    );
    let frames: Vec<strehl_raw::Frame> = g
        .files
        .par_iter()
        .map(|f| strehl_raw::decode(&f.path).with_context(|| f.path.display().to_string()))
        .collect::<Result<_>>()?;
    let m = views(&frames);
    let c = check_group(&m);
    ensure!(
        c.parities,
        "offsets {:?} do not cover all parities",
        c.offsets
    );
    let wb = balance(&m[0]);
    eprintln!(
        "offsets {:?} gains {:?} residual {:?} wb {:?}",
        c.offsets, c.gains, c.residual, wb
    );
    let (w, h) = (m[0].active[2], m[0].active[3]);
    let d: Vec<Vec<f32>> = (0..4).map(|k| malvar(&m[k], wb)).collect();
    let shift = assemble(&m, &c.offsets, &c.gains, wb);
    // Crop picks from demosaic1's green high-pass energy.
    let (tw, th) = (w / C, h / C);
    let mut energy: Vec<(f64, usize, usize)> = (0..th * tw)
        .into_par_iter()
        .map(|t| {
            let (ty, tx) = (t / tw, t % tw);
            let mut e = 0f64;
            for y in ty * C + 1..(ty + 1) * C - 1 {
                for x in tx * C + 1..(tx + 1) * C - 1 {
                    let g = |x: usize, y: usize| d[0][3 * (y * w + x) + 1];
                    let l = 4.0 * g(x, y) - g(x - 1, y) - g(x + 1, y) - g(x, y - 1) - g(x, y + 1);
                    e += f64::from(l * l);
                }
            }
            (e, tx * C, ty * C)
        })
        .collect();
    energy.sort_by(|a, b| b.0.total_cmp(&a.0));
    let mut picks: Vec<(usize, usize)> = Vec::new();
    for &(_, x0, y0) in &energy {
        if x0 < 8 || y0 < 8 || x0 + C + 8 > w || y0 + C + 8 > h {
            continue;
        }
        if picks
            .iter()
            .all(|&(px, py)| x0.abs_diff(px) >= 2 * C || y0.abs_diff(py) >= 2 * C)
        {
            picks.push((x0, y0));
        }
        if picks.len() == 6 {
            break;
        }
    }
    for (i, &(x0, y0)) in picks.iter().enumerate() {
        let mut arms: [Vec<f32>; 3] = Default::default();
        for y in y0..y0 + C {
            for x in x0..x0 + C {
                arms[0].extend_from_slice(&d[0][3 * (y * w + x)..][..3]);
                for ch in 0..3 {
                    let mut s = 0f32;
                    for k in 0..4 {
                        let (xx, yy) = (x as isize + c.offsets[k].0, y as isize + c.offsets[k].1);
                        let (xx, yy) = (
                            xx.clamp(0, w as isize - 1) as usize,
                            yy.clamp(0, h as isize - 1) as usize,
                        );
                        s += d[k][3 * (yy * w + xx) + ch] / c.gains[k] as f32;
                    }
                    arms[1].push(s / 4.0);
                }
                for p in &shift {
                    arms[2].push(p[y * w + x]);
                }
            }
        }
        for (name, v) in ["demosaic1", "demosaic4", "shift"].iter().zip(&arms) {
            let bytes: Vec<u8> = v.iter().flat_map(|f| f.to_le_bytes()).collect();
            std::fs::write(out.join(format!("crop{i}-{name}.f32")), bytes)?;
        }
    }
    std::fs::write(
        out.join("crops.json"),
        serde_json::to_string_pretty(&json!({
            "dir": dir, "plane": plane, "files": g.files.iter().map(|f| &f.name).collect::<Vec<_>>(),
            "offsets": c.offsets, "gains": c.gains, "residual_px": c.residual, "structure": c.precision,
            "white_balance": wb, "active": [w, h], "crop": C, "origins": picks,
        }))? + "\n",
    )?;
    eprintln!("wrote {} crops to {}", picks.len(), out.display());
    Ok(())
}
