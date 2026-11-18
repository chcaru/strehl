//! The device's own check before a render trusts it (round-2 plan stage Q0):
//! a small fold of synthetic frames through the device and through the CPU's
//! `BandMerge`, every accumulator and the collapsed output compared bit for
//! bit, four and twelve planes, two chunks each. What it guards against is a
//! driver or device whose arithmetic differs from the CPU's (flushed
//! subnormals, a fused multiply-add, an inexact division); the fold's other
//! kernels are covered by the device tests of this crate.
//!
//! The verdict is kept beside the pipeline cache, keyed by adapter, driver
//! and the shader's words: a new driver or a changed shader is tested again.
use std::path::{Path, PathBuf};

use strehl_core::pyramid::{BandMerge, FrameWorkspace, MergeConfig, Workspace, level_sizes};

use crate::GpuFold;

struct Rng(u64);

impl Rng {
    fn next(&mut self) -> f32 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        (self.0 >> 40) as f32 / (1u64 << 24) as f32
    }
}

/// `planes` integer-valued planes as `(u16 - black).max(0)` gives them: a
/// scene whose sharp region moves with `f`, noise, and a flat third where the
/// soft-power numerator is subnormal (the case a flushing device gets wrong).
fn frame_of(planes: usize, w: usize, h: usize, f: usize, rng: &mut Rng) -> Vec<Vec<f32>> {
    (0..planes)
        .map(|c| {
            (0..w * h)
                .map(|i| {
                    let (x, y) = ((i % w) as f32, (i / w) as f32);
                    let sharp = if (x as usize * 6 / w + f).is_multiple_of(6) {
                        1.0
                    } else {
                        0.15
                    };
                    let flat = x < w as f32 / 3.0;
                    let detail = if flat { 0.0 } else { 1.0 }
                        * 900.0
                        * sharp
                        * ((x * 0.71 + c as f32).sin() * (y * 0.43).cos());
                    let base = 300.0 + 40.0 * c as f32 + 200.0 * (x / w as f32);
                    let noise = (rng.next() - 0.5) * if flat { 60.0 } else { 30.0 };
                    (base + detail + noise).round().max(0.0)
                })
                .collect()
        })
        .collect()
}

fn bits(v: &[Vec<f32>]) -> Vec<Vec<u32>> {
    v.iter()
        .map(|l| l.iter().map(|x| x.to_bits()).collect())
        .collect()
}

fn snapshot(m: &mut BandMerge) -> Vec<Vec<Vec<u32>>> {
    let t = m.totals_mut();
    vec![
        bits(t.num),
        bits(t.usum),
        bits(t.den),
        bits(t.zmax),
        bits(t.zsum),
        bits(t.lsum),
        bits(t.esum),
        bits(t.lo),
        bits(t.hi),
    ]
}

/// One comparison: `planes` planes of `w x h`, `frames` frames per chunk.
fn compare(planes: usize, w: usize, h: usize, bands: usize, frames: usize) -> Result<(), String> {
    let cfg = MergeConfig {
        bands,
        ..Default::default()
    };
    let sizes = level_sizes(w, h, cfg.bands);
    let mut rng = Rng(0x9E37_79B9_7F4A_7C15 ^ (w * 31 + planes) as u64);
    let data: Vec<Vec<Vec<f32>>> = (0..2 * frames)
        .map(|f| frame_of(planes, w, h, f, &mut rng))
        .collect();
    let beta: Vec<f32> = vec![0.41, 0.093, 0.021, 0.006];
    let mut cpu = BandMerge::new(w, h, planes, cfg);
    let mut gpu_merge = BandMerge::new(w, h, planes, cfg);
    let mut gpu = GpuFold::new(&gpu_merge)?;
    let mut fws = FrameWorkspace::new(&sizes, planes);
    for chunk in 0..2 {
        if chunk > 0 {
            cpu.reset_for_reuse();
            gpu_merge.reset_for_reuse();
        }
        for frame in &data[chunk * frames..(chunk + 1) * frames] {
            let luma: Vec<f32> = frame[1]
                .iter()
                .zip(&frame[2])
                .map(|(a, b)| 0.5 * (a + b))
                .collect();
            let var: Vec<f32> = luma.iter().map(|l| 0.3 * l.max(0.0) + 7.0).collect();
            let refs: Vec<&[f32]> = frame.iter().map(Vec::as_slice).collect();
            fws.next_frame();
            cpu.add_frame_with_gain(&refs, &luma, &var, Some(&beta), &mut fws);
            gpu.add_frame(&mut gpu_merge, &refs, &var, Some(&beta));
        }
        gpu.finish_chunk(&mut gpu_merge);
        if cpu.frames() != gpu_merge.frames() {
            return Err("frame counts differ".into());
        }
        let names = [
            "num", "usum", "den", "zmax", "zsum", "lsum", "esum", "lo", "hi",
        ];
        for ((x, y), name) in snapshot(&mut cpu)
            .iter()
            .zip(&snapshot(&mut gpu_merge))
            .zip(names)
        {
            if x != y {
                return Err(format!(
                    "{planes} planes {w}x{h}, chunk {chunk}: the device's {name} differs from the CPU's"
                ));
            }
        }
        let mut ws = Workspace::new(&sizes);
        if bits(&cpu.finish(&mut ws)) != bits(&gpu_merge.finish(&mut ws)) {
            return Err(format!(
                "{planes} planes {w}x{h}, chunk {chunk}: the collapsed output differs"
            ));
        }
    }
    Ok(())
}

/// The verdict file for this adapter, driver and shader under `dir`.
fn verdict_file(dir: &Path) -> Option<PathBuf> {
    let key = crate::context::self_test_key()?;
    Some(dir.join(format!("selftest-{key}.ok")))
}

/// Whether the device folds exactly as the CPU does, tested now or recorded
/// under `dir` for this adapter, driver and shader. `Err` says why not (no
/// device, or the first difference found). About a tenth of a second when it
/// runs.
pub fn self_test(dir: Option<&Path>) -> Result<(), String> {
    let file = dir.and_then(verdict_file);
    if file.as_ref().is_some_and(|f| f.exists()) {
        return Ok(());
    }
    compare(4, 193, 131, 5, 4)?;
    compare(12, 97, 71, 4, 3)?;
    if let Some(f) = file {
        if let Some(parent) = f.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        let _ = std::fs::write(&f, b"bit-identical\n");
        crate::context::remove_siblings(&f);
    }
    Ok(())
}
