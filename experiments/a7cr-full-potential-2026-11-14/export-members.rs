//! Export a four-shot run's member mosaics for the full-potential prototype.
//!
//! `cargo run --locked --release -p strehl-cli --example a7cr-export-members -- DIR OUT_DIR [FIRST LAST]`
//!
//! Per recorded complete group (plane), `pNNN.u16`: the four members in
//! member order, each `(height + 2 * PAD) x (width + 2 * PAD)` little-endian
//! u16 raw samples (black level included): the active area plus a `PAD`
//! photosite border taken from the decoded buffer where it exists and
//! edge-replicated where it does not. `members.jsonl` gets one line per plane:
//! integer offsets, sub-photosite residuals, exposure gains and structure from
//! `pixel_shift::register` (as `strehl pixel-shift` measures them), levels,
//! white balance from member 1, focus target and file names. Single-shot
//! planes export their one frame the same way (`members` = 1). Read-only over
//! the capture.
use anyhow::{Context, Result, ensure};
use rayon::prelude::*;
use serde_json::json;
use std::io::Write;
use std::path::PathBuf;
use strehl_cli::pixel_shift_cmd::{check_group, recorded_groups, views};
use strehl_core::pixel_shift::{MemberView, balance};

const PAD: usize = 2;

fn padded(f: &strehl_raw::Frame) -> Vec<u8> {
    let a = f.active;
    let (w, h) = (a.width + 2 * PAD, a.height + 2 * PAD);
    let mut out = vec![0u8; w * h * 2];
    out.par_chunks_mut(w * 2).enumerate().for_each(|(y, row)| {
        let by = (a.y + y).saturating_sub(PAD).min(f.buffer_height - 1);
        let src = &f.data[by * f.stride..][..f.stride];
        for x in 0..w {
            let bx = (a.x + x).saturating_sub(PAD).min(f.stride - 1);
            row[2 * x..2 * x + 2].copy_from_slice(&src[bx].to_le_bytes());
        }
    });
    out
}

fn main() -> Result<()> {
    let a: Vec<String> = std::env::args().skip(1).collect();
    ensure!(
        a.len() == 2 || a.len() == 4,
        "usage: DIR OUT_DIR [FIRST LAST]"
    );
    let (dir, out) = (PathBuf::from(&a[0]), PathBuf::from(&a[1]));
    let range = if a.len() == 4 {
        a[2].parse::<u64>()?..=a[3].parse::<u64>()?
    } else {
        0..=u64::MAX
    };
    std::fs::create_dir_all(&out)?;
    let mut log = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(out.join("members.jsonl"))?;
    for g in recorded_groups(&dir)? {
        if !range.contains(&g.plane) || !g.complete {
            continue;
        }
        let began = std::time::Instant::now();
        let frames: Vec<strehl_raw::Frame> = g
            .files
            .par_iter()
            .map(|f| strehl_raw::decode(&f.path).with_context(|| f.path.display().to_string()))
            .collect::<Result<_>>()?;
        let f0 = &frames[0];
        let one = MemberView {
            data: &f0.data,
            stride: f0.stride,
            buffer_height: f0.buffer_height,
            active: [f0.active.x, f0.active.y, f0.active.width, f0.active.height],
            black: f0.levels.black,
            white: f0.levels.white,
        };
        let wb = balance(&one);
        let check = (frames.len() == 4).then(|| check_group(&views(&frames)));
        let mut file = std::io::BufWriter::with_capacity(
            1 << 24,
            std::fs::File::create(out.join(format!("p{:03}.u16", g.plane)))?,
        );
        for f in &frames {
            file.write_all(&padded(f))?;
        }
        file.flush()?;
        let line = json!({
            "plane": g.plane, "target": g.target, "members": frames.len(),
            "files": g.files.iter().map(|f| &f.name).collect::<Vec<_>>(),
            "width": f0.active.width, "height": f0.active.height, "pad": PAD,
            "black": f0.levels.black, "white": f0.levels.white, "white_balance": wb,
            "offsets": check.as_ref().map(|c| c.offsets),
            "residual_px": check.as_ref().map(|c| c.residual),
            "gains": check.as_ref().map(|c| c.gains),
            "structure": check.as_ref().map(|c| c.precision),
            "parities": check.as_ref().map(|c| c.parities),
        });
        writeln!(log, "{line}")?;
        eprintln!(
            "plane {} in {:.2} s",
            g.plane,
            began.elapsed().as_secs_f64()
        );
    }
    Ok(())
}
