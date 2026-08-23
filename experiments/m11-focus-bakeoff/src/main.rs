//! M11 — the focus-measure bake-off: what is the measured trade-off between
//! focus selectivity and argmax's noise excess, and what should the default be?
//!
//! Harness for `docs/research/M11-focus-bakeoff-measured.md`, closing SYNTHESIS
//! risk 2 and running SYNTHESIS §8 experiment 3.
//!
//! Nothing here writes anywhere except `experiments/m11-focus-bakeoff/data/`.
//! `C:\dev\macro` and `D:\macro-dark-frames` are opened read-only, by the
//! decoder, and never written.
//!
//! Modes:
//!
//! ```text
//! selftest                    harness controls; nothing downstream is worth reading if these fail
//! rois <dir>                  flatness / detail search -- picks ROIs by scene structure, never by outcome
//! xcheck <dir>                reproduce M2's published 1.253x and 1.075x through this code path
//! noise <dir> ...             flat-ROI noise excess: measures x regulariser widths -> CSV
//! phi <dir> ...               centre-tap sensitivity fraction per measure -> CSV
//! planted <dir> ...           ground-truth selectivity on a planted focus surface -> CSV
//! stability <dir> ...         real-data winner stability under an independent noise draw -> CSV
//! cost <dir> ...              wall-clock cost per measure -> CSV
//! ```

mod measures;
mod planted;
mod tile;

use std::path::{Path, PathBuf};

use rayon::prelude::*;
use strehl_core::boxfilter::box_mean;
use strehl_core::noise::{Levels, NoiseModel};
use strehl_core::plane::{PlaneGeometry, QuadSource};
use strehl_core::profile;
use strehl_core::stack::speckle_fraction;

use measures::{design, max_support, Measure, Scratch};
use planted::{PlantSpec, Rng};
use tile::{beats, mean_and_sigma, mean_gradient, FrameTile, Roi, TileGeom};

/// Regulariser widths swept by default, in plane px. Odd, because the
/// regulariser is a centred box of `2r+1`.
///
/// M9 established (fact 36) that the noise objective is monotone-then-flat in
/// this variable with no interior optimum, so M11 does not sweep it finely: it
/// samples "none", "the shipped 17x17 reference", and one point between, and
/// pairs every width with a **selectivity** number so the objective is
/// two-sided.
const DEFAULT_WIDTHS: [usize; 3] = [1, 9, 17];

fn main() {
    let argv: Vec<String> = std::env::args().collect();
    let mode = argv.get(1).map(String::as_str).unwrap_or("");
    let rest = &argv[2..];
    let r = match mode {
        "selftest" => selftest(),
        "rois" => rois(rest),
        "xcheck" => xcheck(rest),
        "noise" => noise_sweep(rest),
        "phi" => phi(rest),
        "planted" => planted_mode(rest),
        "stability" => stability(rest),
        "cost" => cost(rest),
        other => Err(format!(
            "unknown mode {other:?}; expected one of selftest, rois, xcheck, noise, phi, planted, stability, cost"
        )),
    };
    if let Err(e) = r {
        eprintln!("error: {e}");
        std::process::exit(1);
    }
}

// ------------------------------------------------------------------ arguments

struct Args {
    positional: Vec<String>,
    flags: Vec<(String, Option<String>)>,
}

fn parse_args(rest: &[String]) -> Args {
    let mut positional = Vec::new();
    let mut flags: Vec<(String, Option<String>)> = Vec::new();
    let mut i = 0;
    while i < rest.len() {
        let a = &rest[i];
        if let Some(name) = a.strip_prefix("--") {
            let next = rest.get(i + 1);
            match next {
                Some(v) if !v.starts_with("--") => {
                    flags.push((name.to_string(), Some(v.clone())));
                    i += 2;
                }
                _ => {
                    flags.push((name.to_string(), None));
                    i += 1;
                }
            }
        } else {
            positional.push(a.clone());
            i += 1;
        }
    }
    Args { positional, flags }
}

impl Args {
    fn one(&self, key: &str) -> Option<&str> {
        self.flags
            .iter()
            .find(|(k, _)| k == key)
            .and_then(|(_, v)| v.as_deref())
    }
    fn many(&self, key: &str) -> Vec<String> {
        self.flags
            .iter()
            .filter(|(k, v)| k == key && v.is_some())
            .map(|(_, v)| v.clone().unwrap())
            .collect()
    }
    fn has(&self, key: &str) -> bool {
        self.flags.iter().any(|(k, _)| k == key)
    }
    fn usize_or(&self, key: &str, default: usize) -> Result<usize, String> {
        match self.one(key) {
            Some(v) => v.parse::<usize>().map_err(|e| format!("--{key}: {e}")),
            None => Ok(default),
        }
    }
    fn f32_or(&self, key: &str, default: f32) -> Result<f32, String> {
        match self.one(key) {
            Some(v) => v.parse::<f32>().map_err(|e| format!("--{key}: {e}")),
            None => Ok(default),
        }
    }
    fn list_f32(&self, key: &str, default: &[f32]) -> Result<Vec<f32>, String> {
        match self.one(key) {
            Some(s) => s
                .split(',')
                .map(|v| v.trim().parse::<f32>().map_err(|e| format!("--{key}: {e}")))
                .collect(),
            None => Ok(default.to_vec()),
        }
    }
    fn list_usize(&self, key: &str, default: &[usize]) -> Result<Vec<usize>, String> {
        match self.one(key) {
            Some(s) => s
                .split(',')
                .map(|v| {
                    v.trim()
                        .parse::<usize>()
                        .map_err(|e| format!("--{key}: {e}"))
                })
                .collect(),
            None => Ok(default.to_vec()),
        }
    }
}

// ---------------------------------------------------------------------- stack

struct StackInfo {
    label: String,
    paths: Vec<PathBuf>,
    plane: PlaneGeometry,
    levels: Levels,
    noise: NoiseModel,
    middle: usize,
}

fn raw_paths(dir: &Path, limit: Option<usize>) -> Result<Vec<PathBuf>, String> {
    let mut paths: Vec<PathBuf> = std::fs::read_dir(dir)
        .map_err(|e| format!("reading {}: {e}", dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| {
            p.extension()
                .and_then(|e| e.to_str())
                .map(|e| e.eq_ignore_ascii_case("arw"))
                .unwrap_or(false)
        })
        .collect();
    paths.sort();
    if let Some(n) = limit {
        paths.truncate(n);
    }
    if paths.is_empty() {
        return Err(format!("no RAW files in {}", dir.display()));
    }
    Ok(paths)
}

fn open_stack(dir: &Path, limit: Option<usize>, label: Option<&str>) -> Result<StackInfo, String> {
    let paths = raw_paths(dir, limit)?;
    let first = strehl_raw::decode(&paths[0]).map_err(|e| format!("{e}"))?;
    let plane = first.geometry();
    let levels = first.levels;
    let noise = profile::noise_model_for(&first.camera, first.iso, levels);
    let label = label
        .map(str::to_string)
        .unwrap_or_else(|| dir.file_name().unwrap_or_default().to_string_lossy().into());
    eprintln!(
        "stack {label}: {} frames, plane {}x{}, black {} white {}, iso {:?}, noise {:?}",
        paths.len(),
        plane.width,
        plane.height,
        levels.black,
        levels.white,
        first.iso,
        noise.provenance
    );
    Ok(StackInfo {
        label,
        middle: paths.len() / 2,
        paths,
        plane,
        levels,
        noise,
    })
}

/// Decode every frame once and cut the tiles it contributes to each ROI.
fn extract_tiles(
    stack: &StackInfo,
    tgs: &[TileGeom],
    with_planes: bool,
) -> Result<Vec<Vec<FrameTile>>, String> {
    stack
        .paths
        .par_iter()
        .map(|p| {
            let frame = strehl_raw::decode(p).map_err(|e| format!("{e}"))?;
            let out: Vec<FrameTile> = tgs
                .iter()
                .map(|tg| tg.extract(&frame, stack.levels.black, with_planes))
                .collect();
            drop(frame);
            Ok(out)
        })
        .collect()
}

fn selected_measures(a: &Args) -> Result<Vec<Measure>, String> {
    match a.one("measures") {
        Some(s) => {
            let want: Vec<&str> = s.split(',').map(|v| v.trim()).collect();
            let all = design();
            for w in &want {
                if !all.iter().any(|m| m.name == *w) {
                    return Err(format!("--measures: no measure named {w}"));
                }
            }
            Ok(all
                .into_iter()
                .filter(|m| want.contains(&m.name.as_str()))
                .collect())
        }
        None => Ok(design()),
    }
}

// ------------------------------------------------------------------ the merge

/// What one `(measure, width)` cell produces on one ROI.
struct Cell {
    stacked_sigma: f64,
    single_sigma: f64,
    stacked_mean: f64,
    ratio: f64,
    distinct_winners: usize,
    speckle: f64,
    grad_stacked: f64,
    grad_single: f64,
}

/// Regularise every frame's focus field and take the per-pixel argmax over the
/// ROI, returning the winner index map. This is the shipped selector.
fn winner_map(tg: &TileGeom, focus: &[Vec<f32>], radius: usize) -> Vec<u16> {
    let n = tg.roi.pixels();
    let mut best_focus = vec![f32::NEG_INFINITY; n];
    let mut best_index = vec![u16::MAX; n];
    let mut reg = vec![0.0f32; tg.geom.pixels()];
    let mut scratch = vec![0.0f32; tg.geom.pixels()];
    for (k, f) in focus.iter().enumerate() {
        let src: &[f32] = if radius == 0 {
            f
        } else {
            box_mean(f, tg.geom, radius, &mut scratch, &mut reg);
            &reg
        };
        let k16 = k as u16;
        for j in 0..tg.roi.height {
            for i in 0..tg.roi.width {
                let p = j * tg.roi.width + i;
                let v = src[tg.roi_index(i, j)];
                if beats(v, k16, best_focus[p], best_index[p]) {
                    best_focus[p] = v;
                    best_index[p] = k16;
                }
            }
        }
    }
    best_index
}

/// Per-pixel argmax over the regularised focus fields, then the flat-ROI
/// statistics of the merged green.
///
/// `focus` is one padded tile per frame; `value` is the ROI-sized channel the
/// winner's pixel is taken from; `single` is the same channel from the middle
/// frame. Keeping selection and evaluation as separate arguments is what makes
/// the decoupled placebo possible.
fn merge_cell(
    tg: &TileGeom,
    focus: &[Vec<f32>],
    value: &[&[f32]],
    single: &[f32],
    radius: usize,
) -> Cell {
    let index = winner_map(tg, focus, radius);
    let out: Vec<f32> = index
        .iter()
        .enumerate()
        .map(|(p, k)| value[*k as usize][p])
        .collect();

    let (stacked_mean, stacked_sigma) = mean_and_sigma(&out);
    let (_, single_sigma) = mean_and_sigma(single);
    let mut winners = index.clone();
    winners.sort_unstable();
    winners.dedup();
    let roi_geom = tg.roi_geom();
    Cell {
        stacked_sigma,
        single_sigma,
        stacked_mean,
        ratio: stacked_sigma / single_sigma,
        distinct_winners: winners.len(),
        speckle: speckle_fraction(&index, roi_geom, 2),
        grad_stacked: mean_gradient(&out, roi_geom),
        grad_single: mean_gradient(single, roi_geom),
    }
}

/// Focus fields for one measure over every frame, one padded tile each.
fn focus_volume(
    m: &Measure,
    luma: &[&[f32]],
    geom: PlaneGeometry,
    noise: &NoiseModel,
) -> Vec<Vec<f32>> {
    luma.par_iter()
        .enumerate()
        .map(|(k, l)| {
            let mut scratch = Scratch::default();
            let mut out = vec![0.0f32; geom.pixels()];
            m.compute(l, geom, noise, k, &mut scratch, &mut out);
            out
        })
        .collect()
}

fn focus_volume_owned(
    m: &Measure,
    frames: &[Vec<f32>],
    geom: PlaneGeometry,
    noise: &NoiseModel,
) -> Vec<Vec<f32>> {
    let refs: Vec<&[f32]> = frames.iter().map(|f| f.as_slice()).collect();
    focus_volume(m, &refs, geom, noise)
}

// ------------------------------------------------------------- the noise sweep

#[allow(clippy::too_many_lines)]
fn noise_sweep(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let dir = a
        .positional
        .first()
        .ok_or("noise needs a directory of RAW files")?;
    let limit = match a.one("limit") {
        Some(v) => Some(v.parse::<usize>().map_err(|e| format!("--limit: {e}"))?),
        None => None,
    };
    let stack = open_stack(Path::new(dir), limit, a.one("label"))?;
    let out_path = a.one("out").ok_or("noise needs --out <FILE>")?.to_string();
    let placebo = a.has("placebo");

    let widths = a.list_usize("widths", &DEFAULT_WIDTHS)?;
    for w in &widths {
        if w % 2 == 0 {
            return Err(format!(
                "regulariser width {w} is even; a centred box is 2r+1"
            ));
        }
    }

    let roi_specs = a.many("roi");
    if roi_specs.is_empty() {
        return Err("noise needs at least one --roi X,Y,W,H".into());
    }
    let roi_kinds = a.many("roi-kind");
    let rois: Vec<Roi> = roi_specs
        .iter()
        .map(|s| Roi::parse(s))
        .collect::<Result<_, _>>()?;

    let ms = selected_measures(&a)?;
    // Margin is sized from the whole design even when `--measures` filters it,
    // so a filtered run reads exactly the same tile as the full run.
    let margin = widths.iter().map(|w| (w - 1) / 2).max().unwrap_or(0) + max_support(&design());
    let tgs: Vec<TileGeom> = rois
        .iter()
        .map(|r| TileGeom::new(*r, margin, stack.plane))
        .collect::<Result<_, _>>()?;
    eprintln!(
        "margin {margin} px -> tiles {}x{}; {} measures x {} widths x {} rois",
        tgs[0].geom.width,
        tgs[0].geom.height,
        ms.len(),
        widths.len(),
        rois.len()
    );

    let t0 = std::time::Instant::now();
    let tiles = extract_tiles(&stack, &tgs, placebo)?;
    eprintln!("decoded + tiled in {:.1} s", t0.elapsed().as_secs_f64());

    let mut csv = String::from(
        "stack,frames,roi,roi_kind,select_on,evaluate_on,measure,family,role,norm,degree,\
         support_radius,support_px,width,radius,\
         ratio,stacked_sigma,single_sigma,stacked_mean,distinct_winners,speckle,\
         grad_stacked,grad_single\n",
    );

    for (ri, tg) in tgs.iter().enumerate() {
        let roi_kind = roi_kinds.get(ri).cloned().unwrap_or_else(|| "flat".into());
        let luma: Vec<&[f32]> = if placebo {
            tiles
                .iter()
                .map(|t| t[ri].g1.as_ref().expect("--placebo needs the planes").as_slice())
                .collect()
        } else {
            tiles.iter().map(|t| t[ri].luma.as_slice()).collect()
        };
        let value: Vec<&[f32]> = if placebo {
            tiles
                .iter()
                .map(|t| {
                    t[ri]
                        .g2_roi
                        .as_ref()
                        .expect("--placebo needs the planes")
                        .as_slice()
                })
                .collect()
        } else {
            tiles.iter().map(|t| t[ri].green.as_slice()).collect()
        };
        let single = value[stack.middle];
        let (select_on, evaluate_on) = if placebo { ("g1", "g2") } else { ("luma", "luma") };

        for m in &ms {
            let t1 = std::time::Instant::now();
            let vol = focus_volume(m, &luma, tg.geom, &stack.noise);
            let rows: Vec<(usize, Cell)> = widths
                .par_iter()
                .map(|w| (*w, merge_cell(tg, &vol, &value, single, (w - 1) / 2)))
                .collect();
            for (w, c) in rows {
                csv.push_str(&format!(
                    "{},{},\"{}\",{},{},{},{},{},{},{},{},{},{},{},{},{:.6},{:.4},{:.4},{:.3},{},{:.6},{:.5},{:.5}\n",
                    stack.label,
                    stack.paths.len(),
                    tg.roi,
                    roi_kind,
                    select_on,
                    evaluate_on,
                    m.name,
                    m.family.as_str(),
                    m.role.as_str(),
                    m.norm_str(),
                    m.kind.degree(),
                    m.support_radius,
                    m.support_px(),
                    w,
                    (w - 1) / 2,
                    c.ratio,
                    c.stacked_sigma,
                    c.single_sigma,
                    c.stacked_mean,
                    c.distinct_winners,
                    c.speckle,
                    c.grad_stacked,
                    c.grad_single,
                ));
            }
            eprintln!(
                "  roi {ri} [{roi_kind}] {:<22} {:.1} s",
                m.name,
                t1.elapsed().as_secs_f64()
            );
        }
    }

    std::fs::write(&out_path, csv).map_err(|e| format!("writing {out_path}: {e}"))?;
    eprintln!(
        "wrote {out_path} in {:.1} s total",
        t0.elapsed().as_secs_f64()
    );
    Ok(())
}

// ------------------------------------------------------- centre-tap sensitivity

/// How much of a measure's response at a pixel comes from **that pixel's own
/// value**, measured on real sensor data by finite difference.
///
/// Method reproduced from M9 (`docs/research/M9-support-coupling-measured.md`
/// §3.2), because M11's whole trade-off is stated in terms of phi and the two
/// milestones must be quoting the same quantity. Every measure here is shift
/// invariant away from the border, so `d r(q) / d L(p)` depends only on
/// `q - p`; perturbing a sparse lattice with spacing wider than twice the
/// largest support yields the whole kernel in one pass.
fn phi(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let dir = a.positional.first().ok_or("phi needs a directory")?;
    let stack = open_stack(
        Path::new(dir),
        a.one("limit").and_then(|v| v.parse().ok()),
        a.one("label"),
    )?;
    let roi = Roi::parse(a.one("roi").unwrap_or("2272,1344,256,256"))?;
    let out_path = a.one("out").map(String::from);
    let deltas = a.list_f32("deltas", &[1.0, 8.0, 32.0])?;

    let ms = selected_measures(&a)?;
    let reach = max_support(&design());
    let spacing = 4 * reach + 2;
    let tg = TileGeom::new(roi, spacing, stack.plane)?;
    let tiles = extract_tiles(&stack, std::slice::from_ref(&tg), false)?;
    let geom = tg.geom;
    let noise = &stack.noise;

    let mut lattice: Vec<usize> = Vec::new();
    let mut y = spacing;
    while y + spacing < geom.height {
        let mut x = spacing;
        while x + spacing < geom.width {
            lattice.push(y * geom.width + x);
            x += spacing;
        }
        y += spacing;
    }
    if lattice.is_empty() {
        return Err("tile too small for the sensitivity lattice".into());
    }

    let mut csv = String::from(
        "stack,roi,measure,family,role,norm,degree,support_radius,support_px,delta,\
         centre_abs,total_abs,phi,taps\n",
    );
    println!(
        "phi: {} frames, roi {roi}, tile {}x{}, {} lattice points spaced {spacing} px, reach {reach}",
        stack.paths.len(),
        geom.width,
        geom.height,
        lattice.len()
    );
    println!(
        "{:<22} {:>7} {:>13} {:>13} {:>9} {:>6}",
        "measure", "delta", "centre |dr|", "total |dr|", "phi", "taps"
    );
    for m in &ms {
        for &delta in &deltas {
            let mut scratch = Scratch::default();
            let mut base = vec![0.0f32; geom.pixels()];
            let mut bump = vec![0.0f32; geom.pixels()];
            let n = (2 * reach + 1) * (2 * reach + 1);
            let mut kernel = vec![0.0f64; n];
            let mut samples = 0usize;
            for (k, t) in tiles.iter().enumerate() {
                let luma = &t[0].luma;
                m.compute(luma, geom, noise, k, &mut scratch, &mut base);
                let mut perturbed = luma.clone();
                for &p in &lattice {
                    perturbed[p] += delta;
                }
                m.compute(&perturbed, geom, noise, k, &mut scratch, &mut bump);
                for &p in &lattice {
                    let (px, py) = (p % geom.width, p / geom.width);
                    for dy in 0..2 * reach + 1 {
                        for dx in 0..2 * reach + 1 {
                            let (qx, qy) = (px + dx - reach, py + dy - reach);
                            let q = qy * geom.width + qx;
                            kernel[dy * (2 * reach + 1) + dx] += (bump[q] - base[q]).abs() as f64;
                        }
                    }
                    samples += 1;
                }
            }
            let scale = samples as f64 * delta as f64;
            let centre = kernel[reach * (2 * reach + 1) + reach] / scale;
            let total: f64 = kernel.iter().sum::<f64>() / scale;
            let rel = |v: f64| (v / scale) / total.max(f64::MIN_POSITIVE);
            let taps = kernel.iter().filter(|v| rel(**v) > 1e-9).count();
            let phi = if total > 0.0 { centre / total } else { f64::NAN };
            println!(
                "{:<22} {delta:>7.1} {centre:>13.6} {total:>13.6} {phi:>9.6} {taps:>6}",
                m.name
            );
            csv.push_str(&format!(
                "{},\"{}\",{},{},{},{},{},{},{},{},{:.10},{:.10},{:.8},{}\n",
                stack.label,
                roi,
                m.name,
                m.family.as_str(),
                m.role.as_str(),
                m.norm_str(),
                m.kind.degree(),
                m.support_radius,
                m.support_px(),
                delta,
                centre,
                total,
                phi,
                taps
            ));
        }
    }
    if let Some(p) = out_path {
        std::fs::write(&p, csv).map_err(|e| format!("{p}: {e}"))?;
        println!("wrote {p}");
    }
    Ok(())
}

// -------------------------------------------------------- planted selectivity

struct PlantedCell {
    acc: f64,
    acc1: f64,
    mae: f64,
    mean_winner: f64,
    distinct_winners: usize,
    speckle: f64,
}

fn planted_cell(tg: &TileGeom, focus: &[Vec<f32>], radius: usize, w_true: usize) -> PlantedCell {
    let index = winner_map(tg, focus, radius);
    let n = index.len() as f64;
    let mut hit = 0usize;
    let mut hit1 = 0usize;
    let mut abs = 0.0f64;
    let mut sum = 0.0f64;
    for k in &index {
        let d = (*k as isize - w_true as isize).abs();
        if d == 0 {
            hit += 1;
        }
        if d <= 1 {
            hit1 += 1;
        }
        abs += d as f64;
        sum += *k as f64;
    }
    let mut winners = index.clone();
    winners.sort_unstable();
    winners.dedup();
    PlantedCell {
        acc: hit as f64 / n,
        acc1: hit1 as f64 / n,
        mae: abs / n,
        mean_winner: sum / n,
        distinct_winners: winners.len(),
        speckle: speckle_fraction(&index, tg.roi_geom(), 2),
    }
}

/// High-passed spatial sd of a tile's ROI, as a per-frame noise readout.
///
/// **Rule 10.** This is a spatial sd and is only ever compared against another
/// spatial sd of the same ROI. It exists to disclose the planted stack's
/// realised noise ladder, not to stand in for a temporal sigma.
fn highpass_sd(tg: &TileGeom, plane: &[f32], radius: usize) -> f64 {
    let mut scratch = vec![0.0f32; tg.geom.pixels()];
    let mut mean = vec![0.0f32; tg.geom.pixels()];
    box_mean(plane, tg.geom, radius, &mut scratch, &mut mean);
    let hp: Vec<f32> = (0..tg.roi.height)
        .flat_map(|j| (0..tg.roi.width).map(move |i| (i, j)))
        .map(|(i, j)| {
            let q = tg.roi_index(i, j);
            plane[q] - mean[q]
        })
        .collect();
    mean_and_sigma(&hp).1
}

#[allow(clippy::too_many_lines)]
fn planted_mode(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let dir = a.positional.first().ok_or("planted needs a directory")?;
    let stack = open_stack(
        Path::new(dir),
        a.one("limit").and_then(|v| v.parse().ok()),
        a.one("label"),
    )?;
    let out_path = a.one("out").ok_or("planted needs --out <FILE>")?.to_string();
    let frames_out = a.one("frames-out").map(String::from);

    let widths = a.list_usize("widths", &DEFAULT_WIDTHS)?;
    let w_trues = a.list_usize("w-true", &[5, 11, 16])?;
    let noise_scales = a.list_f32("noise-scales", &[1.0])?;
    let sigma0 = a.f32_or("sigma0", 0.8)?;
    let alpha = a.f32_or("alpha", 0.35)?;
    let seed = a.one("seed").and_then(|v| v.parse::<u64>().ok()).unwrap_or(20261101);
    let synthetic = a.has("synthetic");
    let null = a.has("null");
    let alpha = if null { 0.0 } else { alpha };

    let roi_specs = a.many("roi");
    if roi_specs.is_empty() {
        return Err("planted needs at least one --roi X,Y,W,H".into());
    }
    let roi_kinds = a.many("roi-kind");
    let rois: Vec<Roi> = roi_specs
        .iter()
        .map(|s| Roi::parse(s))
        .collect::<Result<_, _>>()?;

    let ms = selected_measures(&a)?;
    let nframes = stack.paths.len();
    let probe = PlantSpec {
        frames: nframes,
        w_true: *w_trues.iter().max().unwrap_or(&0),
        sigma0,
        alpha,
        noise_scale: 0.0,
        seed,
    };
    let margin = widths.iter().map(|w| (w - 1) / 2).max().unwrap_or(0)
        + max_support(&design())
        + probe.max_blur_radius();
    let tgs: Vec<TileGeom> = rois
        .iter()
        .map(|r| TileGeom::new(*r, margin, stack.plane))
        .collect::<Result<_, _>>()?;
    eprintln!(
        "planted: margin {margin} px -> tiles {}x{}; {} measures x {} widths x {} rois x {} w_true x {} noise scales",
        tgs[0].geom.width,
        tgs[0].geom.height,
        ms.len(),
        widths.len(),
        rois.len(),
        w_trues.len(),
        noise_scales.len(),
    );

    let t0 = std::time::Instant::now();
    let tiles = extract_tiles(&stack, &tgs, false)?;
    eprintln!("decoded + tiled in {:.1} s", t0.elapsed().as_secs_f64());

    let mut csv = String::from(
        "stack,roi,roi_kind,base,base_frame,w_true,sigma0,alpha,noise_scale,seed,frames,\
         measure,family,role,norm,support_radius,width,radius,\
         acc,acc1,mae,mean_winner,distinct_winners,speckle\n",
    );
    let mut fcsv = String::from(
        "stack,roi,roi_kind,base,base_frame,w_true,sigma0,alpha,noise_scale,frame,\
         blur_sigma,hp_sd,roi_mean\n",
    );

    for (ri, tg) in tgs.iter().enumerate() {
        let roi_kind = roi_kinds.get(ri).cloned().unwrap_or_else(|| "detail".into());

        // Pick the base frame by its own sharpness on this ROI, using the
        // shipped operator. This decides *what texture the planted stack has*,
        // never what the right answer is: ground truth is `w_true`, which is
        // chosen independently.
        let ring = design()
            .into_iter()
            .find(|m| m.name == "ring-1-3")
            .ok_or("ring-1-3 missing from the design")?;
        let luma_refs: Vec<&[f32]> = tiles.iter().map(|t| t[ri].luma.as_slice()).collect();
        let vol = focus_volume(&ring, &luma_refs, tg.geom, &stack.noise);
        let (base_frame, _) = vol
            .iter()
            .enumerate()
            .map(|(k, f)| {
                let s: f64 = (0..tg.roi.height)
                    .flat_map(|j| (0..tg.roi.width).map(move |i| (i, j)))
                    .map(|(i, j)| f[tg.roi_index(i, j)] as f64)
                    .sum();
                (k, s)
            })
            .max_by(|x, y| x.1.partial_cmp(&y.1).unwrap())
            .unwrap();
        drop(vol);

        let (base_name, base): (&str, Vec<f32>) = if synthetic {
            (
                "synthetic",
                planted::synthetic_texture(tg.geom, 2000.0, 240.0),
            )
        } else {
            ("real", tiles[base_frame][ri].luma.clone())
        };
        eprintln!(
            "  roi {ri} [{roi_kind}] base {base_name} frame {base_frame}, {} measures",
            ms.len()
        );

        for &w_true in &w_trues {
            for &noise_scale in &noise_scales {
                let spec = PlantSpec {
                    frames: nframes,
                    w_true,
                    sigma0,
                    alpha,
                    noise_scale,
                    seed: seed
                        .wrapping_mul(1_000_003)
                        .wrapping_add((ri * 97 + w_true) as u64),
                };
                let stackf = planted::plant(&base, tg.geom, &stack.noise, spec);
                for (k, f) in stackf.iter().enumerate() {
                    let (m, _) = mean_and_sigma(f);
                    fcsv.push_str(&format!(
                        "{},\"{}\",{},{},{},{},{},{},{},{},{:.4},{:.5},{:.3}\n",
                        stack.label,
                        tg.roi,
                        roi_kind,
                        base_name,
                        base_frame,
                        w_true,
                        sigma0,
                        alpha,
                        noise_scale,
                        k,
                        spec.blur_sigma(k),
                        highpass_sd(tg, f, 2),
                        m,
                    ));
                }

                for m in &ms {
                    let vol = focus_volume_owned(m, &stackf, tg.geom, &stack.noise);
                    let rows: Vec<(usize, PlantedCell)> = widths
                        .par_iter()
                        .map(|w| (*w, planted_cell(tg, &vol, (w - 1) / 2, w_true)))
                        .collect();
                    for (w, c) in rows {
                        csv.push_str(&format!(
                            "{},\"{}\",{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{:.6},{:.6},{:.4},{:.3},{},{:.6}\n",
                            stack.label,
                            tg.roi,
                            roi_kind,
                            base_name,
                            base_frame,
                            w_true,
                            sigma0,
                            alpha,
                            noise_scale,
                            spec.seed,
                            nframes,
                            m.name,
                            m.family.as_str(),
                            m.role.as_str(),
                            m.norm_str(),
                            m.support_radius,
                            w,
                            (w - 1) / 2,
                            c.acc,
                            c.acc1,
                            c.mae,
                            c.mean_winner,
                            c.distinct_winners,
                            c.speckle,
                        ));
                    }
                }
            }
        }
    }

    std::fs::write(&out_path, csv).map_err(|e| format!("writing {out_path}: {e}"))?;
    if let Some(p) = frames_out {
        std::fs::write(&p, fcsv).map_err(|e| format!("writing {p}: {e}"))?;
        eprintln!("wrote {p}");
    }
    eprintln!(
        "wrote {out_path} in {:.1} s total",
        t0.elapsed().as_secs_f64()
    );
    Ok(())
}

// ------------------------------------------------- real-data winner stability

fn median(v: &mut [f64]) -> f64 {
    if v.is_empty() {
        return f64::NAN;
    }
    v.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let n = v.len();
    if n % 2 == 1 {
        v[n / 2]
    } else {
        0.5 * (v[n / 2 - 1] + v[n / 2])
    }
}

struct StabilityCell {
    agree: f64,
    chance: f64,
    kappa: f64,
    mad: f64,
    prominence: f64,
    margin: f64,
}

/// Two independent noise draws, one winner map each. Cohen's kappa against the
/// chance level implied by the observed winner histogram, so an operator that
/// concentrates on one frame cannot look stable for free.
fn stability_cell(
    tg: &TileGeom,
    va: &[Vec<f32>],
    vb: &[Vec<f32>],
    radius: usize,
) -> StabilityCell {
    let wa = winner_map(tg, va, radius);
    let wb = winner_map(tg, vb, radius);
    let n = wa.len();
    let nframes = va.len();
    let mut agree = 0usize;
    let mut mad = 0.0f64;
    let mut hist_a = vec![0usize; nframes];
    let mut hist_b = vec![0usize; nframes];
    for i in 0..n {
        if wa[i] == wb[i] {
            agree += 1;
        }
        mad += (wa[i] as f64 - wb[i] as f64).abs();
        hist_a[wa[i] as usize] += 1;
        hist_b[wb[i] as usize] += 1;
    }
    let agree = agree as f64 / n as f64;
    let chance: f64 = (0..nframes)
        .map(|k| (hist_a[k] as f64 / n as f64) * (hist_b[k] as f64 / n as f64))
        .sum();
    let kappa = if (1.0 - chance).abs() < 1e-12 {
        f64::NAN
    } else {
        (agree - chance) / (1.0 - chance)
    };

    // Discrimination SNR: the peak's height above the curve's own body, in
    // units of the measure's own response noise, estimated from the paired
    // draws. This is SYNTHESIS §8 experiment 3's "winner-margin versus sigma",
    // made concrete.
    let mut proms = Vec::with_capacity(n);
    let mut margins = Vec::with_capacity(n);
    let mut curve = vec![0.0f64; nframes];
    let mut diffs = vec![0.0f64; nframes];
    for j in 0..tg.roi.height {
        for i in 0..tg.roi.width {
            let q = tg.roi_index(i, j);
            for k in 0..nframes {
                let (x, y) = (va[k][q] as f64, vb[k][q] as f64);
                curve[k] = 0.5 * (x + y);
                diffs[k] = x - y;
            }
            // sd of one draw's response, from the paired difference.
            let s1 = (diffs.iter().map(|d| d * d).sum::<f64>() / (2.0 * nframes as f64)).sqrt();
            // the averaged curve carries sd s1/sqrt(2).
            let s = s1 / std::f64::consts::SQRT_2;
            if !(s > 0.0) {
                continue;
            }
            let mut sorted = curve.clone();
            sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
            let med = if nframes % 2 == 1 {
                sorted[nframes / 2]
            } else {
                0.5 * (sorted[nframes / 2 - 1] + sorted[nframes / 2])
            };
            let top = sorted[nframes - 1];
            let second = sorted[nframes - 2];
            proms.push((top - med) / s);
            margins.push((top - second) / s);
        }
    }
    StabilityCell {
        agree,
        chance,
        kappa,
        mad: mad / n as f64,
        prominence: median(&mut proms),
        margin: median(&mut margins),
    }
}

#[allow(clippy::too_many_lines)]
fn stability(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let dir = a.positional.first().ok_or("stability needs a directory")?;
    let stack = open_stack(
        Path::new(dir),
        a.one("limit").and_then(|v| v.parse().ok()),
        a.one("label"),
    )?;
    let out_path = a.one("out").ok_or("stability needs --out <FILE>")?.to_string();
    let widths = a.list_usize("widths", &DEFAULT_WIDTHS)?;
    let betas = a.list_f32("betas", &[1.0])?;
    let seed = a
        .one("seed")
        .and_then(|v| v.parse::<u64>().ok())
        .unwrap_or(20261102);

    let roi_specs = a.many("roi");
    if roi_specs.is_empty() {
        return Err("stability needs at least one --roi X,Y,W,H".into());
    }
    let roi_kinds = a.many("roi-kind");
    let rois: Vec<Roi> = roi_specs
        .iter()
        .map(|s| Roi::parse(s))
        .collect::<Result<_, _>>()?;

    let ms = selected_measures(&a)?;
    let use_planes = a.has("planes");
    let margin = widths.iter().map(|w| (w - 1) / 2).max().unwrap_or(0) + max_support(&design());
    let tgs: Vec<TileGeom> = rois
        .iter()
        .map(|r| TileGeom::new(*r, margin, stack.plane))
        .collect::<Result<_, _>>()?;

    let t0 = std::time::Instant::now();
    let tiles = extract_tiles(&stack, &tgs, use_planes)?;
    eprintln!("decoded + tiled in {:.1} s", t0.elapsed().as_secs_f64());

    let mut csv = String::from(
        "stack,frames,roi,roi_kind,source,beta,measure,family,role,norm,support_radius,width,radius,\
         agree,chance,kappa,mad,prominence,margin\n",
    );

    for (ri, tg) in tgs.iter().enumerate() {
        let roi_kind = roi_kinds.get(ri).cloned().unwrap_or_else(|| "detail".into());
        for &beta in &betas {
            // The two draws are built once and shared by every measure, so the
            // comparison across measures is paired on identical data.
            //
            // `--planes` uses the two physical green photosites as the two
            // independent realisations: no synthetic noise anywhere, at the
            // cost that G1 and G2 sample lattices offset by half a plane pixel
            // diagonally, so their disagreement is an **upper bound** on
            // noise-driven instability. Injection is the controlled version of
            // the same probe and the two are reported side by side.
            let (source, copy_a, copy_b): (&str, Vec<Vec<f32>>, Vec<Vec<f32>>) = if use_planes {
                (
                    "g1-g2",
                    tiles
                        .iter()
                        .map(|t| t[ri].g1.clone().expect("--planes needs the planes"))
                        .collect(),
                    tiles
                        .iter()
                        .map(|t| t[ri].g2.clone().expect("--planes needs the planes"))
                        .collect(),
                )
            } else {
                let mut ca_all = Vec::with_capacity(tiles.len());
                let mut cb_all = Vec::with_capacity(tiles.len());
                for (k, t) in tiles.iter().enumerate() {
                    let src = &t[ri].luma;
                    let mut ca = vec![0.0f32; src.len()];
                    let mut cb = vec![0.0f32; src.len()];
                    let base = seed
                        .wrapping_mul(7_919)
                        .wrapping_add((ri as u64) << 32)
                        .wrapping_add(k as u64);
                    planted::add_noise(src, &stack.noise, beta, base ^ 0xA5A5_A5A5, &mut ca);
                    planted::add_noise(src, &stack.noise, beta, base ^ 0x5A5A_5A5A, &mut cb);
                    ca_all.push(ca);
                    cb_all.push(cb);
                }
                ("inject", ca_all, cb_all)
            };

            for m in &ms {
                let va = focus_volume_owned(m, &copy_a, tg.geom, &stack.noise);
                let vb = focus_volume_owned(m, &copy_b, tg.geom, &stack.noise);
                for &w in &widths {
                    let c = stability_cell(tg, &va, &vb, (w - 1) / 2);
                    csv.push_str(&format!(
                        "{},{},\"{}\",{},{},{},{},{},{},{},{},{},{},{:.6},{:.6},{:.6},{:.4},{:.4},{:.4}\n",
                        stack.label,
                        tiles.len(),
                        tg.roi,
                        roi_kind,
                        source,
                        beta,
                        m.name,
                        m.family.as_str(),
                        m.role.as_str(),
                        m.norm_str(),
                        m.support_radius,
                        w,
                        (w - 1) / 2,
                        c.agree,
                        c.chance,
                        c.kappa,
                        c.mad,
                        c.prominence,
                        c.margin,
                    ));
                }
                eprintln!("  roi {ri} [{roi_kind}] {source} beta {beta} {:<22} done", m.name);
            }
            if use_planes {
                break;
            }
        }
    }

    std::fs::write(&out_path, csv).map_err(|e| format!("writing {out_path}: {e}"))?;
    eprintln!("wrote {out_path} in {:.1} s", t0.elapsed().as_secs_f64());
    Ok(())
}

// ------------------------------------------------------------------ ROI search

/// Rank plane blocks by residual scene structure (flat) and by full-resolution
/// mean gradient (detail).
///
/// M2's procedure, restated, as reproduced by M9: the green plane is
/// box-downsampled 16x to suppress per-pixel noise and blocks are ranked by the
/// sd of the downsampled block, i.e. **by scene structure, deliberately not by
/// stacked noise**, which would bias the ratio downward.
fn rois(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let dir = a.positional.first().ok_or("rois needs a directory")?;
    let stack = open_stack(Path::new(dir), None, a.one("label"))?;
    let size = a.usize_or("size", 256)?;
    let stride = a.usize_or("stride", 16)?;
    let margin = a.usize_or("margin", 64)?;
    let top = a.usize_or("top", 6)?;

    let frame = strehl_raw::decode(&stack.paths[stack.middle]).map_err(|e| format!("{e}"))?;
    let (w, h) = (stack.plane.width, stack.plane.height);
    let mut green = vec![0.0f32; stack.plane.pixels()];
    strehl_core::plane::green_luma(&frame, stack.levels.black, &mut green);
    drop(frame);

    let (dw, dh) = (w / 16, h / 16);
    let mut down = vec![0.0f32; dw * dh];
    for dy in 0..dh {
        for dx in 0..dw {
            let mut s = 0.0f64;
            for y in dy * 16..dy * 16 + 16 {
                for x in dx * 16..dx * 16 + 16 {
                    s += green[y * w + x] as f64;
                }
            }
            down[dy * dw + dx] = (s / 256.0) as f32;
        }
    }

    let cells = size / 16;
    let mut gcell = vec![0.0f32; dw * dh];
    for dy in 0..dh {
        for dx in 0..dw {
            let mut s = 0.0f64;
            let mut n = 0usize;
            for y in (dy * 16).max(1)..(dy * 16 + 16).min(h - 1) {
                for x in (dx * 16).max(1)..(dx * 16 + 16).min(w - 1) {
                    let gx = 0.5 * (green[y * w + x + 1] - green[y * w + x - 1]) as f64;
                    let gy = 0.5 * (green[(y + 1) * w + x] - green[(y - 1) * w + x]) as f64;
                    s += (gx * gx + gy * gy).sqrt();
                    n += 1;
                }
            }
            gcell[dy * dw + dx] = if n == 0 { 0.0 } else { (s / n as f64) as f32 };
        }
    }

    let block_stats = |x: usize, y: usize| -> (f64, f64) {
        let (bx, by) = (x / 16, y / 16);
        let vals: Vec<f32> = (0..cells)
            .flat_map(|j| (0..cells).map(move |i| (i, j)))
            .map(|(i, j)| down[(by + j) * dw + bx + i])
            .collect();
        let (_, sd) = mean_and_sigma(&vals);
        let g: f64 = (0..cells)
            .flat_map(|j| (0..cells).map(move |i| (i, j)))
            .map(|(i, j)| gcell[(by + j) * dw + bx + i] as f64)
            .sum::<f64>()
            / (cells * cells) as f64;
        (sd, g)
    };

    let mut blocks: Vec<Block> = Vec::new();
    let mut y = margin;
    while y + size + margin <= h {
        let mut x = margin;
        while x + size + margin <= w {
            let (sd, grad) = block_stats(x, y);
            blocks.push(Block { sd, grad, x, y });
            x += stride;
        }
        y += stride;
    }
    println!(
        "{} candidate blocks of {size}x{size} at stride {stride}, margin {margin}",
        blocks.len()
    );

    let disjoint = |picked: &[&Block], b: &Block| {
        picked
            .iter()
            .all(|p| p.x.abs_diff(b.x) >= size || p.y.abs_diff(b.y) >= size)
    };

    let mut by_sd: Vec<&Block> = blocks.iter().collect();
    by_sd.sort_by(|a, b| a.sd.partial_cmp(&b.sd).unwrap());
    println!("flattest, non-overlapping (ranked by downsampled structure sd):");
    let mut picked: Vec<&Block> = Vec::new();
    for b in &by_sd {
        if picked.len() >= top {
            break;
        }
        if disjoint(&picked, b) {
            println!(
                "  {},{},{size},{size}   structure sd {:8.3} DN   mean |grad| {:7.3} DN/px",
                b.x, b.y, b.sd, b.grad
            );
            picked.push(b);
        }
    }

    let mut by_grad: Vec<&Block> = blocks.iter().collect();
    by_grad.sort_by(|a, b| b.grad.partial_cmp(&a.grad).unwrap());
    println!("most detailed, non-overlapping (ranked by full-resolution mean |grad|):");
    let mut picked: Vec<&Block> = Vec::new();
    for b in &by_grad {
        if picked.len() >= top {
            break;
        }
        if disjoint(&picked, b) {
            println!(
                "  {},{},{size},{size}   structure sd {:8.3} DN   mean |grad| {:7.3} DN/px",
                b.x, b.y, b.sd, b.grad
            );
            picked.push(b);
        }
    }

    for spec in a.many("rank") {
        let r = Roi::parse(&spec)?;
        if r.width != size || r.height != size {
            println!("rank of {r}: skipped, not {size}x{size}");
            continue;
        }
        let (sd, grad) = block_stats(r.x - r.x % 16, r.y - r.y % 16);
        let flatter = blocks.iter().filter(|b| b.sd < sd).count();
        let sharper = blocks.iter().filter(|b| b.grad > grad).count();
        println!(
            "rank of {r} (snapped to {},{}): structure sd {sd:.3} DN, mean |grad| {grad:.3} DN/px, {} of {} blocks flatter, {} sharper",
            r.x - r.x % 16,
            r.y - r.y % 16,
            flatter,
            blocks.len(),
            sharper,
        );
    }
    Ok(())
}

struct Block {
    sd: f64,
    grad: f64,
    x: usize,
    y: usize,
}

// --------------------------------------------------------------- the crosscheck

/// Reproduce M2's two published numbers through this harness.
///
/// SYNTHESIS §5 item 15: when re-analysing or re-implementing someone else's
/// measurement, reproduce one of their published numbers **first**. M2 published
/// **1.253x** at width 1 and **1.075x** at width 17 on `109MSDCF`, ROI
/// `2272,1344,256,256`; M9 reproduced 1.2527x and 1.0737x.
fn xcheck(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let dir = a.positional.first().ok_or("xcheck needs a directory")?;
    let limit = match a.one("limit") {
        Some(v) => Some(v.parse::<usize>().map_err(|e| format!("--limit: {e}"))?),
        None => None,
    };
    let stack = open_stack(Path::new(dir), limit, a.one("label"))?;
    let roi = Roi::parse(a.one("roi").unwrap_or("2272,1344,256,256"))?;
    let widths = a.list_usize("widths", &[1, 17])?;

    let ms = design();
    let m = ms
        .iter()
        .find(|m| m.name == "ring-1-3")
        .ok_or("ring-1-3 is missing from the design")?;

    println!(
        "xcheck: {} frames, roi {roi}, measure {}",
        stack.paths.len(),
        m.name
    );
    println!("  M2 published 1.253x at width 1 and 1.075x at width 17; M9 reproduced 1.2527 / 1.0737");

    // Two margins, to prove the tile answer is margin independent.
    for margin_extra in [0usize, 64] {
        let margin = widths.iter().map(|w| (w - 1) / 2).max().unwrap_or(0)
            + m.support_radius
            + margin_extra;
        let tg = TileGeom::new(roi, margin, stack.plane)?;
        let tiles = extract_tiles(&stack, std::slice::from_ref(&tg), false)?;
        let luma: Vec<&[f32]> = tiles.iter().map(|t| t[0].luma.as_slice()).collect();
        let value: Vec<&[f32]> = tiles.iter().map(|t| t[0].green.as_slice()).collect();
        let vol = focus_volume(m, &luma, tg.geom, &stack.noise);
        for &w in &widths {
            let c = merge_cell(&tg, &vol, &value, value[stack.middle], (w - 1) / 2);
            println!(
                "  margin {margin:>3}  width {w:>3}: ratio {:.4}x  stacked sd {:.3} DN  single sd {:.3} DN  winners {}  speckle {:.3}%",
                c.ratio,
                c.stacked_sigma,
                c.single_sigma,
                c.distinct_winners,
                100.0 * c.speckle
            );
        }
    }
    Ok(())
}

// ------------------------------------------------------------------------ cost

fn cost(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let dir = a.positional.first().ok_or("cost needs a directory")?;
    let stack = open_stack(Path::new(dir), Some(a.usize_or("limit", 4)?), a.one("label"))?;
    let roi = Roi::parse(a.one("roi").unwrap_or("2272,1344,256,256"))?;
    let reps = a.usize_or("reps", 3)?;
    let out_path = a.one("out").map(String::from);

    let ms = selected_measures(&a)?;
    let margin = max_support(&design());
    let tg = TileGeom::new(roi, margin, stack.plane)?;
    let tiles = extract_tiles(&stack, std::slice::from_ref(&tg), false)?;
    let luma: Vec<&[f32]> = tiles.iter().map(|t| t[0].luma.as_slice()).collect();
    let mpx = tg.geom.pixels() as f64 / 1.0e6;

    let mut csv = String::from("stack,roi,measure,family,support_radius,megapixels,frames,ms_per_frame_mpx\n");
    println!("cost: tile {}x{} = {:.3} Mpx, {reps} reps, single-threaded per frame", tg.geom.width, tg.geom.height, mpx);
    for m in &ms {
        let mut best = f64::INFINITY;
        for _ in 0..reps {
            let t = std::time::Instant::now();
            let mut scratch = Scratch::default();
            let mut out = vec![0.0f32; tg.geom.pixels()];
            for (k, l) in luma.iter().enumerate() {
                m.compute(l, tg.geom, &stack.noise, k, &mut scratch, &mut out);
            }
            let per = t.elapsed().as_secs_f64() * 1000.0 / (luma.len() as f64 * mpx);
            best = best.min(per);
        }
        println!("  {:<22} {best:8.3} ms / frame / Mpx", m.name);
        csv.push_str(&format!(
            "{},\"{}\",{},{},{},{:.4},{},{:.4}\n",
            stack.label,
            roi,
            m.name,
            m.family.as_str(),
            m.support_radius,
            mpx,
            luma.len(),
            best
        ));
    }
    if let Some(p) = out_path {
        std::fs::write(&p, csv).map_err(|e| format!("{p}: {e}"))?;
        println!("wrote {p}");
    }
    Ok(())
}

// ---------------------------------------------------------------- self-tests

macro_rules! check {
    ($ok:expr, $failed:expr, $cond:expr, $($arg:tt)*) => {{
        if $cond {
            println!("  PASS  {}", format!($($arg)*));
            $ok += 1;
        } else {
            println!("  FAIL  {}", format!($($arg)*));
            $failed += 1;
        }
    }};
}

fn flat_noise() -> NoiseModel {
    use strehl_core::noise::{PlaneNoise, Provenance};
    let p = PlaneNoise {
        gain_dn_per_e: 0.229,
        read_noise_e: 1.47,
        levels: Levels {
            black: 512.0,
            white: 15360.0,
        },
    };
    NoiseModel::new([p; 4], 100.0, Provenance::Profile)
}

#[allow(clippy::too_many_lines)]
fn selftest() -> Result<(), String> {
    let mut ok = 0usize;
    let mut failed = 0usize;
    let noise = flat_noise();
    let ms = design();

    // ---------------------------------------------------------------- group A
    println!("group A -- the operators themselves");
    let geom = PlaneGeometry {
        width: 129,
        height: 129,
    };
    let flat = vec![3000.0f32; geom.pixels()];
    for m in &ms {
        let mut s = Scratch::default();
        let mut out = vec![0.0f32; geom.pixels()];
        m.compute(&flat, geom, &noise, 0, &mut s, &mut out);
        let inset = 20;
        let interior: Vec<f32> = (inset..geom.height - inset)
            .flat_map(|y| (inset..geom.width - inset).map(move |x| (x, y)))
            .map(|(x, y)| out[y * geom.width + x])
            .collect();
        let finite = interior.iter().all(|v| v.is_finite());
        let expect_zero = !matches!(
            m.kind,
            measures::Kind::CtlLuma | measures::Kind::CtlRandom
        );
        let flat_zero = interior.iter().all(|v| v.abs() < 1e-3);
        check!(
            ok,
            failed,
            finite && (!expect_zero || flat_zero),
            "{:<22} finite on a flat field, and zero where it should be",
            m.name
        );
    }

    let texture = planted::synthetic_texture(geom, 3000.0, 200.0);
    let mut blurred = vec![0.0f32; geom.pixels()];
    planted::gaussian_blur(&texture, geom, 2.5, &mut blurred);
    for m in &ms {
        if m.role != measures::Role::Treatment {
            continue;
        }
        let mut s = Scratch::default();
        let (mut a, mut b) = (vec![0.0f32; geom.pixels()], vec![0.0f32; geom.pixels()]);
        m.compute(&texture, geom, &noise, 0, &mut s, &mut a);
        m.compute(&blurred, geom, &noise, 0, &mut s, &mut b);
        let inset = 20;
        let mean = |v: &[f32]| -> f64 {
            let mut t = 0.0f64;
            let mut n = 0usize;
            for y in inset..geom.height - inset {
                for x in inset..geom.width - inset {
                    t += v[y * geom.width + x] as f64;
                    n += 1;
                }
            }
            t / n as f64
        };
        check!(
            ok,
            failed,
            mean(&a) > mean(&b),
            "{:<22} scores sharp above blurred ({:.4} vs {:.4})",
            m.name,
            mean(&a),
            mean(&b)
        );
    }

    // ---------------------------------------------------------------- group B
    println!("group B -- the planted stack builder");
    let spec = PlantSpec {
        frames: 9,
        w_true: 4,
        sigma0: 0.8,
        alpha: 0.35,
        noise_scale: 0.0,
        seed: 1,
    };
    check!(
        ok,
        failed,
        (spec.blur_sigma(4) - 0.8).abs() < 1e-6 && (spec.blur_sigma(0) - 2.2).abs() < 1e-5,
        "blur ladder is minimal at w_true and symmetric ({:.3} at 4, {:.3} at 0, {:.3} at 8)",
        spec.blur_sigma(4),
        spec.blur_sigma(0),
        spec.blur_sigma(8)
    );
    let stackf = planted::plant(&texture, geom, &noise, spec);
    let ring = ms.iter().find(|m| m.name == "ring-1-3").unwrap();
    let vol = focus_volume_owned(ring, &stackf, geom, &noise);
    let inset = 24;
    let mut wrong = 0usize;
    let mut total = 0usize;
    for y in inset..geom.height - inset {
        for x in inset..geom.width - inset {
            let q = y * geom.width + x;
            let mut best = (0usize, f32::NEG_INFINITY);
            for (k, f) in vol.iter().enumerate() {
                if beats(f[q], k as u16, best.1, best.0 as u16) {
                    best = (k, f[q]);
                }
            }
            if best.0 != spec.w_true {
                wrong += 1;
            }
            total += 1;
        }
    }
    check!(
        ok,
        failed,
        wrong == 0,
        "noiseless planted stack is recovered exactly by ring-1-3 ({wrong} of {total} wrong)"
    );

    // ---------------------------------------------------------------- group C
    println!("group C -- the RNG and the noise injection");
    let mut rng = Rng::new(42);
    let draws: Vec<f64> = (0..200_000).map(|_| rng.normal() as f64).collect();
    let m = draws.iter().sum::<f64>() / draws.len() as f64;
    let v = draws.iter().map(|x| (x - m) * (x - m)).sum::<f64>() / draws.len() as f64;
    check!(
        ok,
        failed,
        m.abs() < 0.01 && (v - 1.0).abs() < 0.02,
        "normal draws have mean {m:.4} (want 0) and variance {v:.4} (want 1)"
    );
    let mut ra = Rng::new(7);
    let mut rb = Rng::new(7);
    check!(
        ok,
        failed,
        (0..1000).all(|_| ra.normal() == rb.normal()),
        "the RNG is reproducible from its seed"
    );
    let level = vec![3000.0f32; 400_000];
    let mut noisy = vec![0.0f32; level.len()];
    planted::add_noise(&level, &noise, 1.0, 99, &mut noisy);
    let (_, sd) = mean_and_sigma(&noisy);
    let want = noise.green_luma_sigma(3000.0) as f64;
    check!(
        ok,
        failed,
        (sd / want - 1.0).abs() < 0.01,
        "injected noise sd is the model sigma ({sd:.4} vs {want:.4} DN)"
    );

    // ---------------------------------------------------------------- group D
    println!("group D -- the selectivity statistics, on planted answers");
    let tgeom = PlaneGeometry {
        width: 200,
        height: 200,
    };
    let roi = Roi {
        x: 40,
        y: 40,
        width: 120,
        height: 120,
    };
    let tg = TileGeom {
        roi,
        margin: 40,
        geom: tgeom,
        x0: 0,
        y0: 0,
    };
    // A volume whose argmax is exactly frame 3 everywhere.
    let exact: Vec<Vec<f32>> = (0..7)
        .map(|k| vec![-(k as f32 - 3.0).abs(); tgeom.pixels()])
        .collect();
    let c = planted_cell(&tg, &exact, 0, 3);
    check!(
        ok,
        failed,
        (c.acc - 1.0).abs() < 1e-12 && c.mae == 0.0,
        "planted_cell scores a perfect volume at acc {:.4}, mae {:.4}",
        c.acc,
        c.mae
    );
    // A volume that is pure independent noise: accuracy must sit at chance.
    let mut rng = Rng::new(5);
    let rnd: Vec<Vec<f32>> = (0..7)
        .map(|_| (0..tgeom.pixels()).map(|_| rng.normal()).collect())
        .collect();
    let c = planted_cell(&tg, &rnd, 0, 3);
    check!(
        ok,
        failed,
        (c.acc - 1.0 / 7.0).abs() < 0.02,
        "planted_cell on pure noise sits at chance: {:.4} vs 1/7 = {:.4}",
        c.acc,
        1.0 / 7.0
    );
    // Cohen's kappa: identical volumes give 1, independent volumes give ~0.
    let s = stability_cell(&tg, &rnd, &rnd, 0);
    check!(
        ok,
        failed,
        (s.kappa - 1.0).abs() < 1e-9 && (s.agree - 1.0).abs() < 1e-12,
        "kappa is 1 for identical draws ({:.6})",
        s.kappa
    );
    let mut rng2 = Rng::new(6);
    let rnd2: Vec<Vec<f32>> = (0..7)
        .map(|_| (0..tgeom.pixels()).map(|_| rng2.normal()).collect())
        .collect();
    let s = stability_cell(&tg, &rnd, &rnd2, 0);
    check!(
        ok,
        failed,
        s.kappa.abs() < 0.02,
        "kappa is 0 for independent draws ({:.6}), against agreement {:.4} and chance {:.4}",
        s.kappa,
        s.agree,
        s.chance
    );

    // ---------------------------------------------------------------- group E
    println!("group E -- centre taps that are supposed to be exactly zero");
    let probe_geom = PlaneGeometry {
        width: 129,
        height: 129,
    };
    let probe = planted::synthetic_texture(probe_geom, 3000.0, 150.0);
    let centre = (probe_geom.height / 2) * probe_geom.width + probe_geom.width / 2;
    for name in [
        "tenengrad-w2-nonorm",
        "brenner-sym-s2-w2",
        "stensor-w2",
        "tenengrad-w0",
        "ring-1-3",
        "ctl-luma",
    ] {
        let m = ms.iter().find(|m| m.name == name).unwrap();
        let mut s = Scratch::default();
        let (mut a, mut b) = (
            vec![0.0f32; probe_geom.pixels()],
            vec![0.0f32; probe_geom.pixels()],
        );
        m.compute(&probe, probe_geom, &noise, 0, &mut s, &mut a);
        let mut bumped = probe.clone();
        bumped[centre] += 8.0;
        m.compute(&bumped, probe_geom, &noise, 0, &mut s, &mut b);
        let d = ((b[centre] - a[centre]) as f64 / 8.0).abs();
        let want_zero = matches!(
            name,
            "tenengrad-w2-nonorm" | "brenner-sym-s2-w2" | "stensor-w2"
        );
        let cond = if want_zero { d < 1e-9 } else { d > 1e-9 };
        check!(
            ok,
            failed,
            cond,
            "{name:<22} centre sensitivity {d:.3e} ({} zero)",
            if want_zero { "must be" } else { "must not be" }
        );
    }

    // ---------------------------------------------------------------- group F
    println!("group F -- Parseval, and the DCT band");
    let dgeom = PlaneGeometry {
        width: 64,
        height: 64,
    };
    let dc = vec![1500.0f32; dgeom.pixels()];
    let m = ms.iter().find(|m| m.name == "dct8-hi").unwrap();
    let mut s = Scratch::default();
    let mut out = vec![0.0f32; dgeom.pixels()];
    m.compute(&dc, dgeom, &noise, 0, &mut s, &mut out);
    let interior_max = (16..48)
        .flat_map(|y| (16..48).map(move |x| (x, y)))
        .map(|(x, y)| out[y * dgeom.width + x])
        .fold(0.0f32, f32::max);
    check!(
        ok,
        failed,
        interior_max < 1e-2,
        "dct8-hi has no band energy on a constant field (max {interior_max:.3e})"
    );

    // ---------------------------------------------------------------- group G
    println!("group G -- the merge path");
    let value: Vec<Vec<f32>> = (0..5).map(|k| vec![100.0 * k as f32; roi.pixels()]).collect();
    let vrefs: Vec<&[f32]> = value.iter().map(|v| v.as_slice()).collect();
    let ties: Vec<Vec<f32>> = (0..5).map(|_| vec![1.0f32; tgeom.pixels()]).collect();
    let c = merge_cell(&tg, &ties, &vrefs, vrefs[2], 0);
    check!(
        ok,
        failed,
        (c.stacked_mean - 0.0).abs() < 1e-9 && c.distinct_winners == 1,
        "an all-ties focus volume elects frame 0 (mean {:.3}, winners {})",
        c.stacked_mean,
        c.distinct_winners
    );

    println!("\n{ok} passed, {failed} failed");
    if failed > 0 {
        return Err(format!("{failed} self-tests failed"));
    }
    Ok(())
}
