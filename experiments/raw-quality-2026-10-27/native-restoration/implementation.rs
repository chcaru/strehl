// Test-only fixed sensor-space contrast hypothesis; no optical inverse claim.
use super::*;
use serde_json::{Value, json};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Correction {
    Off,
    Bounded,
    Unbounded,
}

// Reflect around the outermost sample: -1 -> 1, n -> n-2.
fn reflect(i: isize, n: usize) -> usize {
    if i < 0 {
        (-i) as usize
    } else if i >= n as isize {
        (2 * n as isize - 2 - i) as usize
    } else {
        i as usize
    }
}

fn binomial(x: &[f32], width: usize, height: usize) -> Vec<f32> {
    let mut tmp = vec![0.; x.len()];
    tmp.par_chunks_mut(width).enumerate().for_each(|(y, row)| {
        for (j, v) in row.iter_mut().enumerate() {
            *v = (x[y * width + reflect(j as isize - 1, width)] * 0.25 + x[y * width + j] * 0.5)
                + x[y * width + reflect(j as isize + 1, width)] * 0.25;
        }
    });
    let mut out = vec![0.; x.len()];
    out.par_chunks_mut(width).enumerate().for_each(|(y, row)| {
        let a = reflect(y as isize - 1, height) * width;
        let b = reflect(y as isize + 1, height) * width;
        for (j, v) in row.iter_mut().enumerate() {
            *v = (tmp[a + j] * 0.25 + tmp[y * width + j] * 0.5) + tmp[b + j] * 0.25;
        }
    });
    out
}

pub(crate) fn apply(
    planes: &[Vec<f32>],
    width: usize,
    height: usize,
    mode: Correction,
) -> Result<Vec<Vec<f32>>> {
    ensure!(
        width >= 3
            && height >= 3
            && width <= 4096
            && height <= 4096
            && planes.len() == 4
            && planes
                .iter()
                .all(|p| p.len() == width * height && p.iter().all(|v| v.is_finite())),
        "bounded finite CFA geometry"
    );
    if mode == Correction::Off {
        return Ok(planes.to_vec());
    }
    let mut output = Vec::with_capacity(4);
    // Process one phase at a time: four input/output planes, no source volume.
    for x in planes {
        let b = binomial(x, width, height);
        let bb = binomial(&b, width, height);
        ensure!(
            b.iter().chain(&bb).all(|v| v.is_finite()),
            "nonfinite filter intermediates"
        );
        let mut out = vec![0.; x.len()];
        out.par_chunks_mut(width).enumerate().for_each(|(y, row)| {
            for (j, v) in row.iter_mut().enumerate() {
                let i = y * width + j;
                let d = 2.0 * (b[i] - bb[i]);
                if !d.is_finite() {
                    *v = f32::NAN;
                    continue;
                }
                if mode == Correction::Unbounded {
                    *v = x[i] + d;
                    continue;
                }
                let mut lo = x[i];
                let mut hi = x[i];
                for dy in -1..=1 {
                    for dx in -1..=1 {
                        let s = x[reflect(y as isize + dy, height) * width
                            + reflect(j as isize + dx, width)];
                        lo = lo.min(s);
                        hi = hi.max(s);
                    }
                }
                // Frozen correction clamp, followed by its exact support cap
                // solely to prevent a final f32 addition rounding outside it.
                *v = (x[i] + d.clamp(lo - x[i], hi - x[i])).clamp(lo, hi);
            }
        });
        ensure!(out.iter().all(|v| v.is_finite()), "nonfinite correction");
        output.push(out);
    }
    Ok(output)
}

pub(crate) fn camera_rgb(
    planes: &[Vec<f32>],
    width: usize,
    height: usize,
    levels: Levels,
    wb: [f32; 4],
) -> Result<Vec<f32>> {
    super::phase_packed_rgb::camera_rgb(planes, width, height, levels, wb)
}

mod controls {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/raw-quality-2026-10-27/native-restoration/controls.rs"
    ));
}
mod replay {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/raw-quality-2026-10-27/native-restoration/writer-adapter.rs"
    ));
}

#[test]
#[ignore = "root-scheduled fixed generated controls"]
fn generated_controls() -> Result<()> {
    controls::run()
}
#[test]
#[ignore = "root-scheduled complete saved-CFA weevil replay"]
fn replay_weevil() -> Result<()> {
    replay::run(false)
}
#[test]
#[ignore = "root-scheduled complete saved-CFA flat replay"]
fn replay_flat() -> Result<()> {
    replay::run(true)
}
