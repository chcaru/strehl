//! M9 — is the focus measure / merge-regulariser coupling severe enough to
//! belong on the plugin interface?
//!
//! Harness for `docs/research/M9-support-coupling-measured.md`, answering
//! SYNTHESIS §10 open question 9 and ruling on §3.4.1 **B3**.
//!
//! Nothing here writes anywhere except `experiments/m9-support/data/`.
//! `C:\dev\macro` and `D:\macro-dark-frames` are opened read-only, by the
//! decoder, and never written.
//!
//! Modes:
//!
//! ```text
//! selftest                    harness controls; nothing downstream is worth reading if these fail
//! rois <dir>                  flatness search -- picks ROIs by scene structure, never by outcome
//! xcheck <dir>                reproduce M2's published 1.253x and 1.075x through both code paths
//! sweep <dir> ...             the measurement: measures x regulariser widths -> CSV
//! acf <dir> ...               spatial autocorrelation of each measure's focus-field noise
//! ```

mod measures;
mod tile;

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use rayon::prelude::*;
use strehl_core::boxfilter::box_mean;
use strehl_core::noise::{Levels, NoiseModel};
use strehl_core::plane::PlaneGeometry;
use strehl_core::profile;
use strehl_core::stack::speckle_fraction;

use measures::{design, max_support, Measure, Scratch};
use tile::{beats, mean_and_sigma, FrameTile, Roi, TileGeom};

/// The regulariser widths swept by default, in plane px. Odd, because the
/// regulariser is a centred box of `2r+1`.
const DEFAULT_WIDTHS: [usize; 16] = [
    1, 3, 5, 7, 9, 13, 17, 21, 25, 33, 41, 49, 65, 81, 97, 129,
];

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mode = args.first().map(String::as_str).unwrap_or("");
    let rest = &args[args.len().min(1)..];
    let r = match mode {
        "selftest" => selftest(),
        "rois" => rois(rest),
        "xcheck" => xcheck(rest),
        "sweep" => sweep(rest),
        "acf" => acf(rest),
        _ => Err(format!(
            "usage: m9-support <selftest|rois|xcheck|sweep|acf> [args]\n{}",
            "see experiments/m9-support/README.md"
        )),
    };
    if let Err(e) = r {
        eprintln!("ERROR: {e}");
        std::process::exit(1);
    }
}

// ---------------------------------------------------------------- arg parsing

struct Args {
    positional: Vec<String>,
    flags: BTreeMap<String, Vec<String>>,
}

fn parse_args(rest: &[String]) -> Args {
    let mut positional = Vec::new();
    let mut flags: BTreeMap<String, Vec<String>> = BTreeMap::new();
    let mut i = 0;
    while i < rest.len() {
        let a = &rest[i];
        if let Some(name) = a.strip_prefix("--") {
            let takes_value = !matches!(name, "placebo" | "planes");
            if takes_value && i + 1 < rest.len() {
                flags.entry(name.to_string()).or_default().push(rest[i + 1].clone());
                i += 2;
            } else {
                flags.entry(name.to_string()).or_default().push(String::new());
                i += 1;
            }
        } else {
            positional.push(a.clone());
            i += 1;
        }
    }
    Args { positional, flags }
}

impl Args {
    fn one(&self, name: &str) -> Option<&str> {
        self.flags.get(name).and_then(|v| v.first()).map(String::as_str)
    }
    fn many(&self, name: &str) -> Vec<String> {
        self.flags.get(name).cloned().unwrap_or_default()
    }
    fn has(&self, name: &str) -> bool {
        self.flags.contains_key(name)
    }
    fn usize_or(&self, name: &str, default: usize) -> Result<usize, String> {
        match self.one(name) {
            None => Ok(default),
            Some(v) => v.parse().map_err(|e| format!("--{name} {v:?}: {e}")),
        }
    }
}

// ------------------------------------------------------------------ the stack

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
    let plane = {
        use strehl_core::plane::QuadSource;
        first.geometry()
    };
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
///
/// Returns `[frame][roi]`. The frame is dropped before the next decode on that
/// worker, exactly as the stacker does, so peak memory is O(threads).
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
    let n = tg.roi.pixels();
    let mut best_focus = vec![f32::NEG_INFINITY; n];
    let mut best_index = vec![u16::MAX; n];
    let mut out = vec![0.0f32; n];
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
                    out[p] = value[k][p];
                }
            }
        }
    }

    let (stacked_mean, stacked_sigma) = mean_and_sigma(&out);
    let (_, single_sigma) = mean_and_sigma(single);
    let mut winners = best_index.clone();
    winners.sort_unstable();
    winners.dedup();
    let roi_geom = PlaneGeometry {
        width: tg.roi.width,
        height: tg.roi.height,
    };
    Cell {
        stacked_sigma,
        single_sigma,
        stacked_mean,
        ratio: stacked_sigma / single_sigma,
        distinct_winners: winners.len(),
        speckle: speckle_fraction(&best_index, roi_geom, 2),
        grad_stacked: mean_gradient(&out, roi_geom),
        grad_single: mean_gradient(single, roi_geom),
    }
}

/// Mean central-difference gradient magnitude over the interior.
///
/// `AGENTS.md` rule 9: a sharpness metric never travels alone. This is the
/// detail-side control for the flat-ROI ratio, and it is the same quantity
/// SYNTHESIS fact 24 used to show that a mean's sigma looks harmless while its
/// gradient collapses.
fn mean_gradient(v: &[f32], geom: PlaneGeometry) -> f64 {
    let (w, h) = (geom.width, geom.height);
    if w < 3 || h < 3 {
        return 0.0;
    }
    let mut sum = 0.0f64;
    for y in 1..h - 1 {
        for x in 1..w - 1 {
            let dx = 0.5 * (v[y * w + x + 1] - v[y * w + x - 1]) as f64;
            let dy = 0.5 * (v[(y + 1) * w + x] - v[(y - 1) * w + x]) as f64;
            sum += (dx * dx + dy * dy).sqrt();
        }
    }
    sum / ((w - 2) * (h - 2)) as f64
}

/// Focus fields for one measure over every frame, one padded tile each.
fn focus_volume(m: &Measure, luma: &[&[f32]], geom: PlaneGeometry, noise: &NoiseModel) -> Vec<Vec<f32>> {
    luma.par_iter()
        .map(|l| {
            let mut scratch = Scratch::default();
            let mut out = vec![0.0f32; geom.pixels()];
            m.compute(l, geom, noise, &mut scratch, &mut out);
            out
        })
        .collect()
}

// ------------------------------------------------------------------ the sweep

#[allow(clippy::too_many_lines)]
fn sweep(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let dir = a
        .positional
        .first()
        .ok_or("sweep needs a directory of RAW files")?;
    let limit = match a.one("limit") {
        Some(v) => Some(v.parse::<usize>().map_err(|e| format!("--limit: {e}"))?),
        None => None,
    };
    let stack = open_stack(Path::new(dir), limit, a.one("label"))?;
    let out_path = a.one("out").ok_or("sweep needs --out <FILE>")?.to_string();
    let placebo = a.has("placebo");

    let widths: Vec<usize> = match a.one("widths") {
        Some(s) => s
            .split(',')
            .map(|v| v.trim().parse::<usize>().map_err(|e| format!("--widths: {e}")))
            .collect::<Result<_, _>>()?,
        None => DEFAULT_WIDTHS.to_vec(),
    };
    for w in &widths {
        if w % 2 == 0 {
            return Err(format!("regulariser width {w} is even; a centred box is 2r+1"));
        }
    }

    let roi_specs = a.many("roi");
    if roi_specs.is_empty() {
        return Err("sweep needs at least one --roi X,Y,W,H".into());
    }
    let roi_kinds = a.many("roi-kind");
    let rois: Vec<Roi> = roi_specs
        .iter()
        .map(|s| Roi::parse(s))
        .collect::<Result<_, _>>()?;

    let ms: Vec<Measure> = match a.one("measures") {
        Some(s) => {
            let want: Vec<&str> = s.split(',').map(|v| v.trim()).collect();
            let all = design();
            for w in &want {
                if !all.iter().any(|m| m.name == *w) {
                    return Err(format!("--measures: no measure named {w}"));
                }
            }
            all.into_iter().filter(|m| want.contains(&m.name.as_str())).collect()
        }
        None => design(),
    };
    // Margin is sized from the whole design even when `--measures` filters it,
    // so a filtered run reads exactly the same tile as the full run and its
    // rows are identical rather than merely similar.
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
        "stack,frames,roi,roi_kind,select_on,evaluate_on,measure,family,role,\
         support_radius,support_px,declared_radius,declared_px,width,radius,\
         ratio,stacked_sigma,single_sigma,stacked_mean,distinct_winners,speckle,\
         grad_stacked,grad_single\n",
    );

    for (ri, tg) in tgs.iter().enumerate() {
        let roi_kind = roi_kinds.get(ri).cloned().unwrap_or_else(|| "flat".into());
        // Selection reads one channel, evaluation another. Coupled: both are
        // the green luma the stacker actually uses. Placebo: selection reads
        // G1 and evaluation reads G2 -- two physically separate photosites, so
        // the noise that drove the choice is not the noise being measured.
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
                .map(|t| t[ri].g2.as_ref().expect("--placebo needs the planes").as_slice())
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
                    m.support_radius,
                    m.support_px(),
                    m.declared_radius,
                    m.declared_px(),
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
                "  roi {} [{}] {:<14} {:.1} s",
                ri,
                roi_kind,
                m.name,
                t1.elapsed().as_secs_f64()
            );
        }
    }

    std::fs::write(&out_path, csv).map_err(|e| format!("writing {out_path}: {e}"))?;
    eprintln!("wrote {out_path} in {:.1} s total", t0.elapsed().as_secs_f64());
    Ok(())
}

// --------------------------------------------------------------------- the ACF

/// Spatial autocorrelation of each measure's focus field on a flat ROI.
///
/// This is the *mechanism* half of the question. B3's premise (fact 25) is that
/// the merge is coupled to the measure because the measure's own support sets
/// the correlation length of the focus field the merge has to regularise. That
/// premise is measurable directly, without reference to any merge at all.
///
/// **Rule 10 note.** Everything here is spatial. This is the autocorrelation of
/// one frame's focus field across space, with the local mean removed so that
/// scene structure larger than `--highpass` px does not masquerade as
/// correlation length. It is never compared against a temporal sigma.
fn acf(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let dir = a.positional.first().ok_or("acf needs a directory")?;
    let stack = open_stack(Path::new(dir), None, a.one("label"))?;
    let out_path = a.one("out").ok_or("acf needs --out <FILE>")?.to_string();
    let roi = Roi::parse(a.one("roi").ok_or("acf needs --roi")?)?;
    let hp = a.usize_or("highpass", 16)?;
    let max_lag = a.usize_or("maxlag", 40)?;

    let ms = design();
    let margin = max_support(&ms) + hp + 2;
    let tg = TileGeom::new(roi, margin, stack.plane)?;
    let frame = strehl_raw::decode(&stack.paths[stack.middle]).map_err(|e| format!("{e}"))?;
    let t = tg.extract(&frame, stack.levels.black, false);
    drop(frame);

    let mut csv = String::from("stack,measure,family,role,support_radius,lag,acf\n");
    for m in &ms {
        let mut scratch = Scratch::default();
        let mut focus = vec![0.0f32; tg.geom.pixels()];
        m.compute(&t.luma, tg.geom, &stack.noise, &mut scratch, &mut focus);

        // Remove the local mean so slow scene structure cannot be read as
        // correlation length.
        let mut smooth = vec![0.0f32; tg.geom.pixels()];
        let mut tmp = vec![0.0f32; tg.geom.pixels()];
        box_mean(&focus, tg.geom, hp, &mut tmp, &mut smooth);
        let hi: Vec<f32> = focus.iter().zip(&smooth).map(|(f, s)| f - s).collect();

        // Over the ROI only, so every sample is inset from the tile edge.
        let w = tg.roi.width;
        let h = tg.roi.height;
        let roi_vals: Vec<f32> = (0..h)
            .flat_map(|j| (0..w).map(move |i| (i, j)))
            .map(|(i, j)| hi[tg.roi_index(i, j)])
            .collect();
        let (mean, sd) = mean_and_sigma(&roi_vals);
        let var = sd * sd;
        for lag in 0..=max_lag {
            let mut sum = 0.0f64;
            let mut n = 0u64;
            for j in 0..h {
                for i in 0..w - lag {
                    sum += (roi_vals[j * w + i] as f64 - mean)
                        * (roi_vals[j * w + i + lag] as f64 - mean);
                    n += 1;
                }
            }
            for j in 0..h - lag {
                for i in 0..w {
                    sum += (roi_vals[j * w + i] as f64 - mean)
                        * (roi_vals[(j + lag) * w + i] as f64 - mean);
                    n += 1;
                }
            }
            let r = if var > 0.0 { sum / n as f64 / var } else { 0.0 };
            csv.push_str(&format!(
                "{},{},{},{},{},{},{:.6}\n",
                stack.label,
                m.name,
                m.family.as_str(),
                m.role.as_str(),
                m.support_radius,
                lag,
                r
            ));
        }
        eprintln!("  acf {}", m.name);
    }
    std::fs::write(&out_path, csv).map_err(|e| format!("writing {out_path}: {e}"))?;
    eprintln!("wrote {out_path}");
    Ok(())
}

// ------------------------------------------------------------------- ROI search

/// Rank 256x256 plane blocks by residual scene structure, ascending.
///
/// This is M2's own procedure, restated: the green plane is box-downsampled
/// 16x to suppress per-pixel noise and blocks are ranked by the standard
/// deviation of the downsampled block, i.e. **by scene structure, deliberately
/// not by stacked noise**, which would bias the ratio downward. A 16x
/// downsample cannot see pixel-scale fibre (M2 §3.2.2 corrects a structure
/// estimate for exactly that), which is fine: it is used only to *choose*
/// where to point, never to correct a number.
fn rois(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let dir = a.positional.first().ok_or("rois needs a directory")?;
    let stack = open_stack(Path::new(dir), None, a.one("label"))?;
    let size = a.usize_or("size", 256)?;
    let stride = a.usize_or("stride", 16)?;
    let margin = a.usize_or("margin", 105)?;
    let top = a.usize_or("top", 12)?;

    let frame = strehl_raw::decode(&stack.paths[stack.middle]).map_err(|e| format!("{e}"))?;
    let (w, h) = (stack.plane.width, stack.plane.height);
    let mut green = vec![0.0f32; stack.plane.pixels()];
    strehl_core::plane::green_luma(&frame, stack.levels.black, &mut green);
    drop(frame);

    // 16x box downsample.
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
    // Full-resolution gradient magnitude, downsampled to the same 16x grid.
    // Flatness and detail are ranked by different statistics on purpose:
    // downsampled sd finds regions with no structure at any scale, while mean
    // |grad| finds regions with fine structure specifically, which is what the
    // detail-side control needs to have something to lose.
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
    let (cx, cy) = (w as f64 / 2.0, h as f64 / 2.0);
    println!("{} candidate blocks of {size}x{size} at stride {stride}, margin {margin}", blocks.len());

    // Non-overlapping picks only: eight shifts of one flat patch are one flat
    // patch, and reporting them as eight ROIs would fake independence.
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
            let r = (((b.x + size / 2) as f64 - cx).powi(2) + ((b.y + size / 2) as f64 - cy).powi(2)).sqrt();
            println!(
                "  {},{},{size},{size}   structure sd {:8.3} DN   mean |grad| {:7.3} DN/px   radius {r:7.1} px",
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
            let r = (((b.x + size / 2) as f64 - cx).powi(2) + ((b.y + size / 2) as f64 - cy).powi(2)).sqrt();
            println!(
                "  {},{},{size},{size}   structure sd {:8.3} DN   mean |grad| {:7.3} DN/px   radius {r:7.1} px",
                b.x, b.y, b.sd, b.grad
            );
            picked.push(b);
        }
    }

    // Where a named ROI ranks, so a claim that it was not cherry-picked is
    // checkable. Blocks off the search grid are ranked by recomputing their
    // statistic and counting how many grid blocks beat it.
    for spec in a.many("rank") {
        let r = Roi::parse(&spec)?;
        if r.width != size || r.height != size {
            println!("rank of {r}: skipped, not {size}x{size}");
            continue;
        }
        if r.x < margin || r.y < margin || r.x + size + margin > w || r.y + size + margin > h {
            println!("rank of {r}: outside the margin the search uses");
            continue;
        }
        let (sd, grad) = block_stats(r.x - r.x % 16, r.y - r.y % 16);
        let flatter = blocks.iter().filter(|b| b.sd < sd).count();
        println!(
            "rank of {r} (snapped to {},{}): structure sd {sd:.3} DN, mean |grad| {grad:.3} DN/px, {} of {} grid blocks are flatter",
            r.x - r.x % 16,
            r.y - r.y % 16,
            flatter,
            blocks.len()
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

// ---------------------------------------------------------------- the crosscheck

/// Reproduce M2's two published numbers through this harness.
///
/// The tile path is only worth trusting if it lands on figures that were
/// established independently of it: **1.253x** at width 1 (M2 §3.2, reproduced
/// digit-for-digit by `M2-verification.md`) and **1.075x** at width 17
/// (`M2-verification.md` §2, a 17x17-smoothed focus field).
fn xcheck(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let dir = a.positional.first().ok_or("xcheck needs a directory")?;
    let limit = match a.one("limit") {
        Some(v) => Some(v.parse::<usize>().map_err(|e| format!("--limit: {e}"))?),
        None => None,
    };
    let stack = open_stack(Path::new(dir), limit, a.one("label"))?;
    let roi = Roi::parse(a.one("roi").unwrap_or("2272,1344,256,256"))?;
    let widths: Vec<usize> = match a.one("widths") {
        Some(s) => s
            .split(',')
            .map(|v| v.trim().parse::<usize>().map_err(|e| format!("{e}")))
            .collect::<Result<_, _>>()?,
        None => vec![1, 17],
    };

    let ms = design();
    let m = ms
        .iter()
        .find(|m| m.name == "ring-1-3")
        .ok_or("ring-1-3 is missing from the design")?;
    let margin = widths.iter().map(|w| (w - 1) / 2).max().unwrap_or(0) + m.support_radius;
    let tg = TileGeom::new(roi, margin, stack.plane)?;
    let tiles = extract_tiles(&stack, std::slice::from_ref(&tg), false)?;
    let luma: Vec<&[f32]> = tiles.iter().map(|t| t[0].luma.as_slice()).collect();
    let value: Vec<&[f32]> = tiles.iter().map(|t| t[0].green.as_slice()).collect();
    let vol = focus_volume(m, &luma, tg.geom, &stack.noise);

    println!("xcheck: {} frames, roi {roi}, measure {}", stack.paths.len(), m.name);
    println!("  M2 published 1.253x at width 1 and 1.075x at width 17 (17x17-smoothed focus field)");
    for w in widths {
        let c = merge_cell(&tg, &vol, &value, value[stack.middle], (w - 1) / 2);
        println!(
            "  width {w:>3}: ratio {:.4}x  stacked sd {:.3} DN  single sd {:.3} DN  winners {}  speckle {:.3}%",
            c.ratio,
            c.stacked_sigma,
            c.single_sigma,
            c.distinct_winners,
            100.0 * c.speckle
        );
    }
    Ok(())
}

// ------------------------------------------------------------------- self-tests

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

#[allow(clippy::too_many_lines)]
fn selftest() -> Result<(), String> {
    let mut ok = 0usize;
    let mut failed = 0usize;

    println!("group A -- the measures do what their names say (synthetic)");
    {
        // Wide enough that the largest support radius in the design (41 px,
        // the widest positive control) still leaves an interior to average.
        let geom = PlaneGeometry {
            width: 161,
            height: 161,
        };
        let noise = flat_noise();
        let mut scratch = Scratch::default();
        let mut out = vec![0.0f32; geom.pixels()];

        // A flat field must give exactly zero response for every family.
        let flat = vec![3000.0f32; geom.pixels()];
        for m in design() {
            m.compute(&flat, geom, &noise, &mut scratch, &mut out);
            let peak = out.iter().cloned().fold(0.0f32, f32::max);
            check!(ok, failed, peak < 1e-3, "{:<14} is zero on a flat field ({peak:.2e})", m.name);
        }

        // A sharper texture must score higher than a blurred copy of itself,
        // for every family. A single step edge will not do: the integral of
        // |grad| across a step is the step height whatever its width, so a
        // measure with a wide summation window scores a soft edge and a sharp
        // edge identically. Multi-scale texture is the honest test.
        let sharp = texture(geom);
        let soft = blurred(&sharp, geom, 3);
        for m in design() {
            m.compute(&sharp, geom, &noise, &mut scratch, &mut out);
            let a = interior_mean(&out, geom, 45);
            m.compute(&soft, geom, &noise, &mut scratch, &mut out);
            let b = interior_mean(&out, geom, 45);
            check!(ok, failed, a > b, "{:<14} prefers the sharp texture ({a:.2} > {b:.2})", m.name);
        }
    }

    println!("group B -- support radius is the real read extent");
    {
        // A single bright pixel at the tile centre must move the response at
        // exactly `support_radius` away and nowhere further. This is the check
        // that `support_px()` would not be lying.
        let geom = PlaneGeometry {
            width: 129,
            height: 129,
        };
        let noise = flat_noise();
        let mut scratch = Scratch::default();
        let (mut base, mut bump) = (vec![0.0f32; geom.pixels()], vec![0.0f32; geom.pixels()]);
        let flat = vec![2000.0f32; geom.pixels()];
        let mut spike = flat.clone();
        spike[64 * 129 + 64] = 6000.0;
        for m in design() {
            m.compute(&flat, geom, &noise, &mut scratch, &mut base);
            m.compute(&spike, geom, &noise, &mut scratch, &mut bump);
            let reach = (0..129)
                .filter(|x| (bump[64 * 129 + x] - base[64 * 129 + x]).abs() > 1e-4)
                .map(|x| (x as isize - 64).unsigned_abs())
                .max()
                .unwrap_or(0);
            check!(
                ok,
                failed,
                reach == m.support_radius,
                "{:<14} reach {reach} == declared support radius {}",
                m.name,
                m.support_radius
            );
        }
    }

    println!("group C -- the design is actually crossed, and the controls are what they claim");
    {
        let ms = design();
        let t: Vec<&Measure> = ms.iter().filter(|m| m.role == measures::Role::Treatment).collect();
        let supports: Vec<usize> = {
            let mut v: Vec<usize> = t.iter().map(|m| m.support_radius).collect();
            v.sort_unstable();
            v.dedup();
            v
        };
        let families: Vec<&str> = {
            let mut v: Vec<&str> = t.iter().map(|m| m.family.as_str()).collect();
            v.sort_unstable();
            v.dedup();
            v
        };
        check!(ok, failed, supports.len() >= 4, "at least 4 support radii: {supports:?}");
        check!(ok, failed, families.len() >= 4, "at least 4 families: {families:?}");
        let full = supports
            .iter()
            .all(|s| families.iter().all(|f| t.iter().any(|m| m.support_radius == *s && m.family.as_str() == *f)));
        check!(ok, failed, full, "every family appears at every support radius");
        let nulls: Vec<&Measure> = ms.iter().filter(|m| m.role == measures::Role::NullControl).collect();
        let declared: Vec<usize> = nulls.iter().map(|m| m.declared_radius).collect();
        let real: Vec<usize> = nulls.iter().map(|m| m.support_radius).collect();
        check!(ok, failed, declared.len() >= 4 && declared.iter().collect::<std::collections::BTreeSet<_>>().len() == declared.len(),
            "null control declares {declared:?} -- all different");
        check!(ok, failed, real.iter().all(|r| *r == real[0]),
            "null control is one operator at {real:?} -- all the same");
    }

    println!("group D -- the knee statistic fires when the knee moves, and not otherwise");
    {
        // Synthetic monotone-decreasing curves with a planted decay scale. The
        // statistic the whole report rests on is exercised against curves whose
        // answer is known by construction before it is pointed at data.
        //
        // The check is a property, not a re-derivation of the formula: the
        // reported width must be the FIRST grid width at or below the 10%
        // target, i.e. it must be under target and its grid predecessor must be
        // over it. A re-implementation of `knee_width` here would only test
        // that I can type the same expression twice.
        let widths: Vec<usize> = DEFAULT_WIDTHS.to_vec();
        let mut knees: Vec<usize> = Vec::new();
        for planted in [3.0f64, 9.0, 25.0, 60.0] {
            let curve: Vec<f64> = widths
                .iter()
                .map(|w| 1.0 + 0.25 * (-(*w as f64) / planted).exp())
                .collect();
            let knee = knee_width(&widths, &curve, 0.10);
            let top = curve[0];
            let floor = curve.iter().cloned().fold(f64::INFINITY, f64::min);
            let target = floor + 0.10 * (top - floor);
            let idx = knee.and_then(|k| widths.iter().position(|w| *w == k));
            let first_crossing = idx.is_some_and(|i| curve[i] <= target && (i == 0 || curve[i - 1] > target));
            check!(ok, failed, first_crossing,
                "planted decay {planted}: knee {knee:?} is the first grid width under the 10% target");
            if let Some(k) = knee {
                knees.push(k);
            }
        }
        check!(ok, failed, knees.len() == 4 && knees.windows(2).all(|p| p[0] < p[1]),
            "knee increases strictly with the planted decay scale: {knees:?}");
        // Two curves with knees an octave apart must not report the same knee.
        let c1: Vec<f64> = widths.iter().map(|w| 1.0 + 0.25 * (-(*w as f64) / 4.0).exp()).collect();
        let c2: Vec<f64> = widths.iter().map(|w| 1.0 + 0.25 * (-(*w as f64) / 32.0).exp()).collect();
        check!(ok, failed, knee_width(&widths, &c1, 0.10) < knee_width(&widths, &c2, 0.10),
            "knee separates a 8x change in decay scale");
        // A flat curve has no knee to find.
        let flat: Vec<f64> = widths.iter().map(|_| 1.1).collect();
        check!(ok, failed, knee_width(&widths, &flat, 0.10) == Some(widths[0]),
            "a flat curve reports the first width, not a spurious one");
        // A curve that only improves at the very last width must say so
        // instead of reporting an early knee.
        let late: Vec<f64> = widths.iter().map(|w| if *w == *widths.last().unwrap() { 1.0 } else { 1.5 }).collect();
        check!(ok, failed, knee_width(&widths, &late, 0.10) == Some(*widths.last().unwrap()),
            "a knee at the sweep edge is reported at the edge, not earlier");
    }

    println!("group E -- the merge reproduces the arithmetic it is supposed to");
    {
        // A one-frame stack must give a ratio of exactly 1.000: the two sides
        // of the ratio are produced by different code walking different data.
        // This mirrors `strehl-cli`'s own identity test.
        let roi = Roi {
            x: 8,
            y: 8,
            width: 16,
            height: 16,
        };
        let tg = TileGeom::new(
            roi,
            8,
            PlaneGeometry {
                width: 32,
                height: 32,
            },
        )?;
        let value: Vec<f32> = (0..roi.pixels()).map(|i| ((i * 37) % 101) as f32).collect();
        let focus = vec![vec![1.0f32; tg.geom.pixels()]];
        let vals: Vec<&[f32]> = vec![&value];
        for radius in [0usize, 1, 3] {
            let c = merge_cell(&tg, &focus, &vals, &value, radius);
            check!(ok, failed, (c.ratio - 1.0).abs() < 1e-12,
                "one-frame stack has ratio exactly 1 at radius {radius} ({:.15})", c.ratio);
        }
        // A winner exactly 3x noisier must report exactly 3.000.
        let noisy: Vec<f32> = value.iter().map(|v| 3.0 * v).collect();
        let focus2 = vec![vec![0.0f32; tg.geom.pixels()], vec![1.0f32; tg.geom.pixels()]];
        let vals2: Vec<&[f32]> = vec![&value, &noisy];
        let c = merge_cell(&tg, &focus2, &vals2, &value, 0);
        check!(ok, failed, (c.ratio - 3.0).abs() < 1e-6, "a 3x noisier winner reports 3.000 ({:.6})", c.ratio);
        check!(ok, failed, c.distinct_winners == 1, "and exactly one distinct winner ({})", c.distinct_winners);
    }

    println!("group F -- ties go to the lower frame index, as the shipped selector does");
    {
        check!(ok, failed, beats(1.0, 0, 1.0, 1), "equal focus, lower index wins");
        check!(ok, failed, !beats(1.0, 1, 1.0, 0), "equal focus, higher index loses");
        check!(ok, failed, !beats(f32::NAN, 0, f32::NEG_INFINITY, u16::MAX), "NaN never wins");
        check!(ok, failed, beats(0.5, 5, f32::NEG_INFINITY, u16::MAX), "anything beats the sentinel");
    }

    println!("group G -- the gradient control moves in the direction it must");
    {
        let geom = PlaneGeometry {
            width: 161,
            height: 161,
        };
        let sharp = texture(geom);
        let soft = blurred(&sharp, geom, 3);
        check!(ok, failed, mean_gradient(&sharp, geom) > mean_gradient(&soft, geom),
            "mean |grad| is higher on unblurred texture ({:.3} > {:.3})",
            mean_gradient(&sharp, geom), mean_gradient(&soft, geom));
        let flat = vec![1000.0f32; geom.pixels()];
        check!(ok, failed, mean_gradient(&flat, geom) == 0.0, "and exactly zero on a flat field");
    }

    println!();
    println!("{ok} passed, {failed} failed");
    if failed > 0 {
        return Err(format!("{failed} self-tests failed"));
    }
    Ok(())
}

fn flat_noise() -> NoiseModel {
    profile::noise_model_for(
        "ILCE-7CM2",
        Some(160.0),
        Levels {
            black: 512.0,
            white: 15360.0,
        },
    )
}

/// Deterministic multi-scale texture, for the sharp-vs-blurred tests.
///
/// Energy at several spatial scales so that a wide-support bandpass measure has
/// something to see. No resampling is involved anywhere in its construction, so
/// the interpolation-phase artefact that AGENTS.md warns about cannot enter.
fn texture(geom: PlaneGeometry) -> Vec<f32> {
    let (w, h) = (geom.width, geom.height);
    let mut v = Vec::with_capacity(geom.pixels());
    for y in 0..h {
        for x in 0..w {
            let (fx, fy) = (x as f32, y as f32);
            let a = 400.0 * (fx * 1.698).sin() * (fy * 1.461).cos();
            let b = 300.0 * (fx * 0.571).sin() * (fy * 0.483).sin();
            let c = 200.0 * (fx * 0.203 + fy * 0.217).sin();
            v.push(2500.0 + a + b + c);
        }
    }
    v
}

/// A box-blurred copy, using the shipped filter so the border policy matches.
fn blurred(src: &[f32], geom: PlaneGeometry, radius: usize) -> Vec<f32> {
    let mut scratch = vec![0.0f32; geom.pixels()];
    let mut dst = vec![0.0f32; geom.pixels()];
    box_mean(src, geom, radius, &mut scratch, &mut dst);
    dst
}

/// Mean over the interior only, so a measure's clamped border never enters a
/// comparison.
fn interior_mean(v: &[f32], geom: PlaneGeometry, inset: usize) -> f64 {
    let mut sum = 0.0f64;
    let mut n = 0usize;
    for y in inset..geom.height - inset {
        for x in inset..geom.width - inset {
            sum += v[y * geom.width + x] as f64;
            n += 1;
        }
    }
    if n == 0 { 0.0 } else { sum / n as f64 }
}

/// The pre-registered knee: the smallest swept width at which the curve has
/// realised `1 - tol` of the total improvement it achieves anywhere in the
/// sweep.
///
/// Defined on the *observed* range so it is well posed whether or not the curve
/// has an interior minimum — which matters, because a pure noise objective need
/// not have one.
pub fn knee_width(widths: &[usize], curve: &[f64], tol: f64) -> Option<usize> {
    if widths.len() != curve.len() || widths.is_empty() {
        return None;
    }
    let top = curve[0];
    let floor = curve.iter().cloned().fold(f64::INFINITY, f64::min);
    let target = floor + tol * (top - floor);
    widths
        .iter()
        .zip(curve)
        .find(|(_, c)| **c <= target)
        .map(|(w, _)| *w)
}
