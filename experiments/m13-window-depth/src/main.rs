//! M13 — where the focus-measure window optimum sits, and what a depth
//! discontinuity does to it.
//!
//! Harness for `docs/research/M13-window-depth-measured.md`, answering SYNTHESIS
//! §10 question 15 (M11's two carried-forward residuals).
//!
//! Nothing here writes anywhere except `experiments/m13-window-depth/data/`.
//! `C:\dev\macro`, `D:\macro-dark-frames` and `D:\personal\macro` are opened
//! read-only, by the decoder, and never written. `audit` records their file
//! counts and byte totals before and after the run.
//!
//! Modes:
//!
//! ```text
//! audit                       read-only-corpus file counts and byte totals
//! selftest                    harness controls, including the halo metric's null and positive control
//! xcheck <dir>                reproduce M2's 1.253x and M11's tenengrad-w5 N through THIS code path
//! noise <dir> ...             flat-ROI noise excess vs window -> CSV
//! phi <dir> ...               centre-tap sensitivity fraction vs window -> CSV
//! planted <dir> ...           continuous-plant selectivity vs window, fronto-parallel and tilted -> CSV
//! edge <dir> ...              occluding-edge plant: halo metrics vs window -> CSV
//! adaptive <dir> ...          is a spatially adaptive window worth it? oracle bound + a realisable rule
//! cost <dir> ...              ms/frame/Mpx vs window
//! ```

// `measures`, `planted` and `tile` are copied from `experiments/m11-focus-bakeoff`
// so that M13 measures the same kernels M11 measured and the two milestones'
// CSVs join on the `measure` column. They are kept complete rather than trimmed
// to what M13 happens to call, so the copy stays diffable against M11's.
#[allow(dead_code)]
mod edge;
#[allow(dead_code)]
mod measures;
#[allow(dead_code)]
mod planted;
#[allow(dead_code)]
mod tile;

use std::path::{Path, PathBuf};

use rayon::prelude::*;
use strehl_core::boxfilter::box_mean;
use strehl_core::noise::{Levels, NoiseModel};
use strehl_core::plane::{PlaneGeometry, QuadSource};
use strehl_core::profile;

use edge::{EdgeGeometry, EdgeScene, EdgeSpec, ProfileConfig};
use measures::{max_support, Measure, Scratch};
use planted::PlantSpec;
use tile::{beats, mean_and_sigma, FrameTile, Roi, TileGeom};

/// Regulariser widths swept by default, in plane px. Odd, because the
/// regulariser is a centred box of `2r+1`. Same three points M11 used, so the
/// `width` column joins across the two milestones.
const DEFAULT_WIDTHS: [usize; 3] = [1, 9, 17];

/// The read-only corpora this milestone may open, and may never write.
const READ_ONLY_ROOTS: [&str; 3] = [
    "C:\\dev\\macro",
    "D:\\macro-dark-frames",
    "D:\\personal\\macro",
];

fn main() {
    let argv: Vec<String> = std::env::args().collect();
    let mode = argv.get(1).map(String::as_str).unwrap_or("");
    let rest = &argv[2..];
    let r = match mode {
        "audit" => audit(rest),
        "selftest" => selftest(rest),
        "xcheck" => xcheck(rest),
        "noise" => noise_sweep(rest),
        "phi" => phi_sweep(rest),
        "planted" => planted_mode(rest),
        "edge" => edge_mode(rest),
        "adaptive" => adaptive_mode(rest),
        "cost" => cost(rest),
        other => Err(format!(
            "unknown mode {other:?}; expected one of audit, selftest, xcheck, noise, phi, planted, edge, adaptive, cost"
        )),
    };
    if let Err(e) = r {
        eprintln!("error: {e}");
        std::process::exit(1);
    }
}

// ---------------------------------------------------------------------- audit

fn audit(args: &[String]) -> Result<(), String> {
    let a = parse_args(args);
    let mut out = String::new();
    for root in READ_ONLY_ROOTS {
        let mut files = 0u64;
        let mut bytes = 0u64;
        let mut newest = std::time::UNIX_EPOCH;
        let mut stack = vec![PathBuf::from(root)];
        while let Some(dir) = stack.pop() {
            let rd = match std::fs::read_dir(&dir) {
                Ok(rd) => rd,
                Err(e) => return Err(format!("{}: {e}", dir.display())),
            };
            for e in rd.flatten() {
                let md = match e.metadata() {
                    Ok(md) => md,
                    Err(_) => continue,
                };
                if md.is_dir() {
                    stack.push(e.path());
                } else {
                    files += 1;
                    bytes += md.len();
                    if let Ok(t) = md.modified() {
                        newest = newest.max(t);
                    }
                }
            }
        }
        let secs = newest
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0);
        out.push_str(&format!(
            "{root} files={files} bytes={bytes} newest_mtime_unix={secs}\n"
        ));
    }
    print!("{out}");
    if let Some(p) = a.one("out") {
        std::fs::write(p, &out).map_err(|e| e.to_string())?;
    }
    Ok(())
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
            match rest.get(i + 1) {
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
    /// The measure set: either `--measures a,b,c`, or `--operator NAME --windows
    /// 0,2,5,...` which expands to `NAME-wN` for every N.
    fn measures(&self) -> Result<Vec<Measure>, String> {
        if let Some(s) = self.one("measures") {
            return s
                .split(',')
                .map(|n| measures::parse(n.trim()).ok_or(format!("unknown measure {n:?}")))
                .collect();
        }
        let op = self.one("operator").unwrap_or("tenengrad");
        let windows = self.list_usize("windows", &[0, 2, 5, 8, 11])?;
        windows
            .iter()
            .map(|w| {
                let name = format!("{op}-w{w}");
                measures::parse(&name).ok_or(format!("unknown measure {name:?}"))
            })
            .collect()
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

/// Regularise every frame's focus field and take the per-pixel argmax over the
/// ROI. Identical to M11's `winner_map`, including the shipped tie-break.
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

/// The same, but indexed over the **whole tile** rather than the ROI, which the
/// edge profile needs so that a distance band can run past the ROI border.
fn winner_map_tile(geom: PlaneGeometry, focus: &[Vec<f32>], radius: usize) -> Vec<u16> {
    let n = geom.pixels();
    let mut best_focus = vec![f32::NEG_INFINITY; n];
    let mut best_index = vec![u16::MAX; n];
    let mut reg = vec![0.0f32; n];
    let mut scratch = vec![0.0f32; n];
    for (k, f) in focus.iter().enumerate() {
        let src: &[f32] = if radius == 0 {
            f
        } else {
            box_mean(f, geom, radius, &mut scratch, &mut reg);
            &reg
        };
        let k16 = k as u16;
        for p in 0..n {
            if beats(src[p], k16, best_focus[p], best_index[p]) {
                best_focus[p] = src[p];
                best_index[p] = k16;
            }
        }
    }
    best_index
}

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
    let dir = a.positional.first().ok_or("noise needs a directory")?;
    let limit = match a.one("limit") {
        Some(v) => Some(v.parse::<usize>().map_err(|e| format!("--limit: {e}"))?),
        None => None,
    };
    let stack = open_stack(Path::new(dir), limit, a.one("label"))?;
    let out_path = a.one("out").ok_or("noise needs --out <FILE>")?.to_string();
    let placebo = a.has("placebo");
    let coupled_g2 = a.has("coupled-g2");
    if placebo && coupled_g2 {
        return Err("--placebo and --coupled-g2 are different arms; run them separately".into());
    }
    let want_planes = placebo || coupled_g2;

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

    let ms = a.measures()?;
    let margin = widths.iter().map(|w| (w - 1) / 2).max().unwrap_or(0) + max_support(&ms);
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
    let tiles = extract_tiles(&stack, &tgs, want_planes)?;
    eprintln!("decoded + tiled in {:.1} s", t0.elapsed().as_secs_f64());

    let mut csv = String::from(
        "stack,frames,roi,roi_kind,select_on,evaluate_on,measure,family,window,support_radius,\
         width,radius,ratio,stacked_sigma,single_sigma,distinct_winners\n",
    );

    for (ri, tg) in tgs.iter().enumerate() {
        let roi_kind = roi_kinds.get(ri).cloned().unwrap_or_else(|| "flat".into());
        let luma: Vec<&[f32]> = if placebo {
            tiles
                .iter()
                .map(|t| t[ri].g1.as_ref().unwrap().as_slice())
                .collect()
        } else if coupled_g2 {
            tiles
                .iter()
                .map(|t| t[ri].g2.as_ref().unwrap().as_slice())
                .collect()
        } else {
            tiles.iter().map(|t| t[ri].luma.as_slice()).collect()
        };
        let value: Vec<&[f32]> = if want_planes {
            tiles
                .iter()
                .map(|t| t[ri].g2_roi.as_ref().unwrap().as_slice())
                .collect()
        } else {
            tiles.iter().map(|t| t[ri].green.as_slice()).collect()
        };
        let single = value[stack.middle];
        let (select_on, evaluate_on) = if placebo {
            ("g1", "g2")
        } else if coupled_g2 {
            ("g2", "g2")
        } else {
            ("luma", "luma")
        };

        for m in &ms {
            let t1 = std::time::Instant::now();
            let vol = focus_volume(m, &luma, tg.geom, &stack.noise);
            let rows: Vec<(usize, f64, f64, f64, usize)> = widths
                .par_iter()
                .map(|w| {
                    let index = winner_map(tg, &vol, (w - 1) / 2);
                    let out: Vec<f32> = index
                        .iter()
                        .enumerate()
                        .map(|(p, k)| value[*k as usize][p])
                        .collect();
                    let (_, ss) = mean_and_sigma(&out);
                    let (_, s1) = mean_and_sigma(single);
                    let mut winners = index.clone();
                    winners.sort_unstable();
                    winners.dedup();
                    (*w, ss / s1, ss, s1, winners.len())
                })
                .collect();
            for (w, ratio, ss, s1, dw) in rows {
                csv.push_str(&format!(
                    "{},{},\"{}\",{},{},{},{},{},{},{},{},{},{:.6},{:.4},{:.4},{}\n",
                    stack.label,
                    stack.paths.len(),
                    tg.roi,
                    roi_kind,
                    select_on,
                    evaluate_on,
                    m.name,
                    m.family.as_str(),
                    window_of(m),
                    m.support_radius,
                    w,
                    (w - 1) / 2,
                    ratio,
                    ss,
                    s1,
                    dw,
                ));
            }
            eprintln!(
                "  roi {ri} [{roi_kind}] {:<20} {:.1} s",
                m.name,
                t1.elapsed().as_secs_f64()
            );
        }
    }

    std::fs::write(&out_path, csv).map_err(|e| format!("writing {out_path}: {e}"))?;
    eprintln!("wrote {out_path} in {:.1} s", t0.elapsed().as_secs_f64());
    Ok(())
}

/// The window radius baked into a measure's name, or `support_radius - 1` for
/// families where those coincide. Recorded as its own column so the sweep axis
/// is explicit in the CSV instead of being parsed out of the name downstream.
fn window_of(m: &Measure) -> usize {
    m.name
        .rsplit('-')
        .find_map(|s| s.strip_prefix('w').and_then(|v| v.parse::<usize>().ok()))
        .unwrap_or(0)
}

// ------------------------------------------------------- centre-tap sensitivity

/// φ by finite difference, method reproduced from M9 §3.2 and M11's `phi` mode,
/// so all three milestones quote the same quantity.
///
/// Two details of M11's convention are load-bearing and are kept: the bump is
/// applied on a **lattice** of well-separated points and accumulated, and the
/// accumulation reach is **one fixed radius for every operator in the set**, not
/// each operator's own support. Zero-padding makes the second choice harmless as
/// long as the fixed reach covers every operator's support — which held for M11,
/// whose widest was `support_radius = 12`. It does **not** hold automatically for
/// a sweep that runs to `w = 40`, so the reach here is derived from the set
/// actually being measured and is recorded in the CSV.
fn phi_sweep(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let dir = a.positional.first().ok_or("phi needs a directory")?;
    let stack = open_stack(
        Path::new(dir),
        a.one("limit").and_then(|v| v.parse().ok()).or(Some(1)),
        a.one("label"),
    )?;
    let out_path = a.one("out").ok_or("phi needs --out <FILE>")?.to_string();
    let roi = Roi::parse(a.one("roi").unwrap_or("2272,1344,256,256"))?;
    let ms = a.measures()?;
    let deltas = a.list_f32("deltas", &[1.0, 8.0, 32.0])?;

    let reach = max_support(&ms) + 2;
    let spacing = 4 * reach + 2;
    let tg = TileGeom::new(roi, spacing, stack.plane)?;
    let tiles = extract_tiles(&stack, std::slice::from_ref(&tg), false)?;
    let geom = tg.geom;

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
    eprintln!(
        "phi: roi {roi}, tile {}x{}, {} lattice points spaced {spacing} px, reach {reach}",
        geom.width,
        geom.height,
        lattice.len()
    );

    let mut csv =
        String::from("stack,roi,measure,window,norm,support_radius,reach,delta,centre_abs,total_abs,phi,taps\n");
    for m in &ms {
        for &delta in &deltas {
            let (phi, taps, centre, total) =
                centre_tap_lattice(m, &tiles[0][0].luma, geom, &stack.noise, delta, reach, &lattice);
            csv.push_str(&format!(
                "{},\"{}\",{},{},{},{},{},{},{:.10},{:.10},{:.8},{}\n",
                stack.label,
                roi,
                m.name,
                window_of(m),
                m.norm_str(),
                m.support_radius,
                reach,
                delta,
                centre,
                total,
                phi,
                taps
            ));
            eprintln!("  {:<22} delta {delta:>5.1}  phi {phi:.6}  taps {taps}", m.name);
        }
    }
    std::fs::write(&out_path, csv).map_err(|e| format!("writing {out_path}: {e}"))?;
    Ok(())
}

/// M11's lattice estimator: bump every lattice point at once, accumulate the
/// absolute response change on a `(2*reach+1)^2` stencil around each.
fn centre_tap_lattice(
    m: &Measure,
    luma: &[f32],
    geom: PlaneGeometry,
    noise: &NoiseModel,
    delta: f32,
    reach: usize,
    lattice: &[usize],
) -> (f64, usize, f64, f64) {
    let mut scratch = Scratch::default();
    let mut base = vec![0.0f32; geom.pixels()];
    let mut bump = vec![0.0f32; geom.pixels()];
    m.compute(luma, geom, noise, 0, &mut scratch, &mut base);
    let mut perturbed = luma.to_vec();
    for &p in lattice {
        perturbed[p] += delta;
    }
    m.compute(&perturbed, geom, noise, 0, &mut scratch, &mut bump);

    let side = 2 * reach + 1;
    let mut kernel = vec![0.0f64; side * side];
    for &p in lattice {
        let (px, py) = (p % geom.width, p / geom.width);
        for dy in 0..side {
            for dx in 0..side {
                let q = (py + dy - reach) * geom.width + (px + dx - reach);
                kernel[dy * side + dx] += (bump[q] - base[q]).abs() as f64;
            }
        }
    }
    let scale = lattice.len() as f64 * delta as f64;
    let centre = kernel[reach * side + reach] / scale;
    let total: f64 = kernel.iter().sum::<f64>() / scale;
    let taps = kernel
        .iter()
        .filter(|v| (**v / scale) / total.max(f64::MIN_POSITIVE) > 1e-9)
        .count();
    let phi = if total > 0.0 { centre / total } else { f64::NAN };
    (phi, taps, centre, total)
}

/// A single-bump variant with a per-measure reach, used only by the self-test.
fn centre_tap(
    m: &Measure,
    luma: &[f32],
    geom: PlaneGeometry,
    noise: &NoiseModel,
    delta: f32,
) -> (f64, usize) {
    let mut scratch = Scratch::default();
    let mut base = vec![0.0f32; geom.pixels()];
    m.compute(luma, geom, noise, 0, &mut scratch, &mut base);
    let mut bumped = luma.to_vec();
    let centre = (geom.height / 2) * geom.width + geom.width / 2;
    bumped[centre] += delta;
    let mut after = vec![0.0f32; geom.pixels()];
    m.compute(&bumped, geom, noise, 0, &mut scratch, &mut after);

    let reach = m.support_radius + 2;
    let (mut at_centre, mut total, mut taps) = (0.0f64, 0.0f64, 0usize);
    for dy in 0..2 * reach + 1 {
        for dx in 0..2 * reach + 1 {
            let y = geom.height / 2 + dy - reach;
            let x = geom.width / 2 + dx - reach;
            let q = y * geom.width + x;
            let d = ((after[q] - base[q]) as f64 / delta as f64).abs();
            if d > 1e-9 {
                taps += 1;
            }
            if dx == reach && dy == reach {
                at_centre = d;
            }
            total += d;
        }
    }
    if total <= 0.0 {
        return (0.0, taps);
    }
    (at_centre / total, taps)
}

// -------------------------------------------------------- planted selectivity

#[allow(clippy::too_many_lines)]
fn planted_mode(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let dir = a.positional.first().ok_or("planted needs a directory")?;
    let stack = open_stack(
        Path::new(dir),
        a.one("limit").and_then(|v| v.parse().ok()),
        a.one("label"),
    )?;
    let out_path = a
        .one("out")
        .ok_or("planted needs --out <FILE>")?
        .to_string();

    let widths = a.list_usize("widths", &DEFAULT_WIDTHS)?;
    let nframes = a.usize_or("frames", stack.paths.len())?;
    let w_true = a.usize_or("w-true", nframes / 2)?;
    let sigma0 = a.f32_or("sigma0", 0.8)?;
    let alpha = a.f32_or("alpha", 0.35)?;
    let noise_scale = a.f32_or("noise-scale", 1.0)?;
    let tilts = a.list_f32("tilts", &[0.0])?;
    let seed = a
        .one("seed")
        .and_then(|v| v.parse::<u64>().ok())
        .unwrap_or(20_260_823);
    let flat_base = a.has("flat-base");

    let roi_specs = a.many("roi");
    if roi_specs.is_empty() {
        return Err("planted needs at least one --roi X,Y,W,H".into());
    }
    let roi_kinds = a.many("roi-kind");
    let rois: Vec<Roi> = roi_specs
        .iter()
        .map(|s| Roi::parse(s))
        .collect::<Result<_, _>>()?;

    let ms = a.measures()?;
    let probe = PlantSpec {
        frames: nframes,
        w_true,
        sigma0,
        alpha,
        noise_scale: 0.0,
        seed,
    };
    let margin = widths.iter().map(|w| (w - 1) / 2).max().unwrap_or(0)
        + max_support(&ms)
        + probe.max_blur_radius();
    let tgs: Vec<TileGeom> = rois
        .iter()
        .map(|r| TileGeom::new(*r, margin, stack.plane))
        .collect::<Result<_, _>>()?;
    eprintln!(
        "planted: margin {margin} px -> tiles {}x{}; {} measures x {} widths x {} rois x {} tilts, {nframes} frames",
        tgs[0].geom.width,
        tgs[0].geom.height,
        ms.len(),
        widths.len(),
        rois.len(),
        tilts.len(),
    );

    let t0 = std::time::Instant::now();
    let tiles = extract_tiles(&stack, &tgs, false)?;
    eprintln!("decoded + tiled in {:.1} s", t0.elapsed().as_secs_f64());

    let mut csv = String::from(
        "stack,roi,roi_kind,base,base_frame,frames,w_true,tilt,sigma0,alpha,noise_scale,seed,\
         measure,family,window,support_radius,width,radius,eff_radius,acc,acc1,mae,speckle\n",
    );

    for (ri, tg) in tgs.iter().enumerate() {
        let roi_kind = roi_kinds
            .get(ri)
            .cloned()
            .unwrap_or_else(|| "detail".into());
        // Base frame by its own sharpness on this ROI under the shipped
        // operator. This decides what texture the plant has, never what the
        // right answer is.
        let ring = measures::parse("ring-1-3").unwrap();
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

        let (base_name, base): (&str, Vec<f32>) = if flat_base {
            let mut acc = 0.0f64;
            for j in 0..tg.roi.height {
                for i in 0..tg.roi.width {
                    acc += tiles[base_frame][ri].luma[tg.roi_index(i, j)] as f64;
                }
            }
            let m = (acc / tg.roi.pixels() as f64) as f32;
            ("flat-base", vec![m; tg.geom.pixels()])
        } else {
            ("real", tiles[base_frame][ri].luma.clone())
        };
        eprintln!("  roi {ri} [{roi_kind}] base {base_name} frame {base_frame}");

        for &tilt in &tilts {
            let spec = PlantSpec {
                frames: nframes,
                w_true,
                sigma0,
                alpha,
                noise_scale,
                seed: seed.wrapping_mul(1_000_003).wrapping_add(ri as u64),
            };
            let (stackf, truth) = if tilt == 0.0 {
                (
                    planted::plant(&base, tg.geom, &stack.noise, spec),
                    vec![w_true as f32; tg.roi.pixels()],
                )
            } else {
                planted::plant_tilted(
                    &base,
                    tg.geom,
                    &stack.noise,
                    spec,
                    tilt,
                    tg.margin,
                    tg.margin,
                    tg.roi.width,
                    tg.roi.height,
                )
            };
            for m in &ms {
                let vol = focus_volume_owned(m, &stackf, tg.geom, &stack.noise);
                let rows: Vec<(usize, f64, f64, f64, f64)> = widths
                    .par_iter()
                    .map(|w| {
                        let index = winner_map(tg, &vol, (w - 1) / 2);
                        let n = index.len() as f64;
                        let (mut hit, mut hit1, mut abs) = (0.0, 0.0, 0.0);
                        for (k, t) in index.iter().zip(truth.iter()) {
                            let d = (*k as f64 - *t as f64).abs();
                            if d < 0.5 {
                                hit += 1.0;
                            }
                            if d < 1.5 {
                                hit1 += 1.0;
                            }
                            abs += d;
                        }
                        let sp = strehl_core::stack::speckle_fraction(&index, tg.roi_geom(), 2);
                        (*w, hit / n, hit1 / n, abs / n, sp)
                    })
                    .collect();
                for (w, acc, acc1, mae, sp) in rows {
                    csv.push_str(&format!(
                        "{},\"{}\",{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{:.6},{:.6},{:.4},{:.6}\n",
                        stack.label,
                        tg.roi,
                        roi_kind,
                        base_name,
                        base_frame,
                        nframes,
                        w_true,
                        tilt,
                        sigma0,
                        alpha,
                        noise_scale,
                        spec.seed,
                        m.name,
                        m.family.as_str(),
                        window_of(m),
                        m.support_radius,
                        w,
                        (w - 1) / 2,
                        window_of(m) + (w - 1) / 2,
                        acc,
                        acc1,
                        mae,
                        sp,
                    ));
                }
            }
            eprintln!(
                "    tilt {tilt} done at {:.1} s",
                t0.elapsed().as_secs_f64()
            );
        }
    }

    std::fs::write(&out_path, csv).map_err(|e| format!("writing {out_path}: {e}"))?;
    eprintln!("wrote {out_path} in {:.1} s", t0.elapsed().as_secs_f64());
    Ok(())
}

// ----------------------------------------------------- the discontinuity plant

/// Two real textures for one edge scene, plus the tile they live in.
struct EdgeTextures {
    near: Vec<f32>,
    far: Vec<f32>,
    tg: TileGeom,
    /// Tile indices of the ROI interior — the only pixels ever scored.
    region: Vec<usize>,
}

fn build_edge_textures(
    stack: &StackInfo,
    roi_near: Roi,
    roi_far: Roi,
    margin: usize,
) -> Result<EdgeTextures, String> {
    let tg_near = TileGeom::new(roi_near, margin, stack.plane)?;
    let tg_far = TileGeom::new(roi_far, margin, stack.plane)?;
    if tg_near.geom.width != tg_far.geom.width || tg_near.geom.height != tg_far.geom.height {
        return Err("the two edge ROIs must have identical geometry".into());
    }
    // One decode supplies both textures. The sharpest frame on the near ROI is
    // used for both so the two layers carry the same sensor state.
    let tgs = vec![tg_near, tg_far];
    let tiles = extract_tiles(stack, &tgs, false)?;
    let ring = measures::parse("ring-1-3").unwrap();
    let luma_refs: Vec<&[f32]> = tiles.iter().map(|t| t[0].luma.as_slice()).collect();
    let vol = focus_volume(&ring, &luma_refs, tg_near.geom, &stack.noise);
    let (base_frame, _) = vol
        .iter()
        .enumerate()
        .map(|(k, f)| {
            let s: f64 = (0..tg_near.roi.height)
                .flat_map(|j| (0..tg_near.roi.width).map(move |i| (i, j)))
                .map(|(i, j)| f[tg_near.roi_index(i, j)] as f64)
                .sum();
            (k, s)
        })
        .max_by(|x, y| x.1.partial_cmp(&y.1).unwrap())
        .unwrap();
    eprintln!("  edge textures from frame {base_frame}");

    let region: Vec<usize> = (0..tg_near.roi.height)
        .flat_map(|j| (0..tg_near.roi.width).map(move |i| (i, j)))
        .map(|(i, j)| tg_near.roi_index(i, j))
        .collect();

    Ok(EdgeTextures {
        near: tiles[base_frame][0].luma.clone(),
        far: tiles[base_frame][1].luma.clone(),
        tg: tg_near,
        region,
    })
}

#[allow(clippy::too_many_lines)]
fn edge_mode(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let dir = a.positional.first().ok_or("edge needs a directory")?;
    let stack = open_stack(
        Path::new(dir),
        a.one("limit").and_then(|v| v.parse().ok()),
        a.one("label"),
    )?;
    let out_path = a.one("out").ok_or("edge needs --out <FILE>")?.to_string();
    let profile_out = a.one("profile-out").map(String::from);

    let widths = a.list_usize("widths", &DEFAULT_WIDTHS)?;
    let nframes = a.usize_or("frames", 41)?;
    let sigma0 = a.f32_or("sigma0", 0.8)?;
    let alpha = a.f32_or("alpha", 0.35)?;
    let noise_scale = a.f32_or("noise-scale", 1.0)?;
    let steps: Vec<i32> = a
        .list_f32("steps", &[4.0, 8.0, 16.0])?
        .iter()
        .map(|v| *v as i32)
        .collect();
    let seed = a
        .one("seed")
        .and_then(|v| v.parse::<u64>().ok())
        .unwrap_or(20_260_823);
    let band = a.usize_or("band", 24)? as i32;
    let shapes: Vec<String> = if a.many("shape").is_empty() {
        vec!["vertical".into()]
    } else {
        a.many("shape")
    };
    let bar_half = a.usize_or("bar-half-width", 12)?;

    let roi_near = Roi::parse(a.one("roi-near").ok_or("edge needs --roi-near X,Y,W,H")?)?;
    let roi_far = Roi::parse(a.one("roi-far").ok_or("edge needs --roi-far X,Y,W,H")?)?;

    let ms = a.measures()?;
    let w_near = nframes / 2 - steps.iter().max().copied().unwrap_or(0) as usize / 2;
    let probe = EdgeSpec {
        frames: nframes,
        w_near,
        w_far: w_near + steps.iter().max().copied().unwrap_or(0) as usize,
        sigma0,
        alpha,
        noise_scale,
        seed,
        geometry: EdgeGeometry::Vertical { at: 0 },
    };
    let margin = widths.iter().map(|w| (w - 1) / 2).max().unwrap_or(0)
        + max_support(&ms)
        + probe.max_blur_radius();

    let tex = build_edge_textures(&stack, roi_near, roi_far, margin)?;
    let geom = tex.tg.geom;
    eprintln!(
        "edge: margin {margin} px -> tile {}x{}, ROI {}x{}; {} measures x {} widths x {} steps x {} shapes",
        geom.width,
        geom.height,
        tex.tg.roi.width,
        tex.tg.roi.height,
        ms.len(),
        widths.len(),
        steps.len(),
        shapes.len()
    );

    let cfg = ProfileConfig {
        band,
        baseline_lo: (tex.tg.roi.width as i32 / 2 - 32).max(band + 8),
        baseline_hi: tex.tg.roi.width as i32 / 2 - 4,
        max_d: tex.tg.roi.width as i32,
    };
    eprintln!(
        "  profile: band |d| <= {}, far baseline d in [{}, {}]",
        cfg.band, cfg.baseline_lo, cfg.baseline_hi
    );

    let mut csv = String::from(
        "stack,shape,frames,w_near,w_far,step,sigma0,alpha,noise_scale,seed,band,\
         measure,family,window,support_radius,width,radius,eff_radius,\
         acc,acc_band,bleed_bg,bleed_fg,excess_dn,excess_sigma,band_rms,floor_rms,far_rms,\
         peak_bias,single_sigma\n",
    );
    let mut pcsv = String::from(
        "stack,shape,step,measure,window,width,d,count,wrong,exact,e_merged,e_oracle,bias\n",
    );

    let t0 = std::time::Instant::now();
    for shape in &shapes {
        let geometry = match shape.as_str() {
            "vertical" => EdgeGeometry::Vertical { at: geom.width / 2 },
            "horizontal" => EdgeGeometry::Horizontal {
                at: geom.height / 2,
            },
            "bar" => EdgeGeometry::Bar {
                at: geom.width / 2,
                half_width: bar_half,
            },
            other => return Err(format!("unknown --shape {other:?}")),
        };
        for &step in &steps {
            let w_near = nframes / 2 - (step as usize) / 2;
            let spec = EdgeSpec {
                frames: nframes,
                w_near,
                w_far: w_near + step as usize,
                sigma0,
                alpha,
                noise_scale,
                seed: seed.wrapping_mul(1_000_003).wrapping_add(step as u64),
                geometry,
            };
            let scene = EdgeScene::render(&tex.near, &tex.far, geom, spec, Some(&stack.noise));
            let oracle = scene.oracle();

            // Per-sample injected noise magnitude, from the disjoint noise-free
            // render. This is a genuine per-sample sigma, not a spatial sd of
            // scene structure, so dividing a per-pixel DN error by it is
            // rule-10 clean.
            let single_sigma = {
                let k = spec.w_far.min(spec.frames - 1);
                let mut acc = 0.0f64;
                for &p in &tex.region {
                    let d = (scene.frames[k][p] - scene.clean[k][p]) as f64;
                    acc += d * d;
                }
                (acc / tex.region.len() as f64).sqrt()
            };

            for m in &ms {
                let vol = focus_volume_owned(m, &scene.frames, geom, &stack.noise);
                let rows: Vec<(usize, edge::EdgeSummary, Option<edge::EdgeProfile>)> = widths
                    .par_iter()
                    .map(|w| {
                        let sel = winner_map_tile(geom, &vol, (w - 1) / 2);
                        let merged: Vec<f32> = sel
                            .iter()
                            .enumerate()
                            .map(|(p, k)| scene.frames[*k as usize][p])
                            .collect();
                        let prof = edge::profile(
                            &scene,
                            geom,
                            spec,
                            &sel,
                            &merged,
                            &oracle,
                            &tex.region,
                            cfg,
                        );
                        let mut hit = 0.0f64;
                        let mut far_se = 0.0f64;
                        let mut far_n = 0.0f64;
                        for &p in &tex.region {
                            if sel[p] == scene.truth[p] {
                                hit += 1.0;
                            }
                            let (x, y) = (p % geom.width, p / geom.width);
                            if spec.geometry.signed_distance(x, y).abs() > cfg.band {
                                let e = (merged[p] - scene.ideal[p]) as f64;
                                far_se += e * e;
                                far_n += 1.0;
                            }
                        }
                        let acc = hit / tex.region.len() as f64;
                        let far_rms = if far_n > 0.0 {
                            (far_se / far_n).sqrt()
                        } else {
                            0.0
                        };
                        let s = edge::summarise(&prof, cfg, single_sigma, acc, far_rms);
                        (*w, s, Some(prof))
                    })
                    .collect();
                for (w, s, prof) in rows {
                    csv.push_str(&format!(
                        "{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{:.6},{:.6},{:.4},{:.4},{:.4},{:.5},{:.4},{:.4},{:.4},{:.4},{:.4}\n",
                        stack.label,
                        geometry.as_str(),
                        nframes,
                        spec.w_near,
                        spec.w_far,
                        step,
                        sigma0,
                        alpha,
                        noise_scale,
                        spec.seed,
                        cfg.band,
                        m.name,
                        m.family.as_str(),
                        window_of(m),
                        m.support_radius,
                        w,
                        (w - 1) / 2,
                        window_of(m) + (w - 1) / 2,
                        s.acc,
                        s.acc_band,
                        s.bleed_bg,
                        s.bleed_fg,
                        s.excess_dn,
                        s.excess_sigma,
                        s.band_rms,
                        s.floor_rms,
                        s.far_rms,
                        s.peak_bias,
                        single_sigma,
                    ));
                    if profile_out.is_some() {
                        if let Some(p) = prof {
                            for i in 0..p.d.len() {
                                if p.d[i].abs() > 96 {
                                    continue;
                                }
                                pcsv.push_str(&format!(
                                    "{},{},{},{},{},{},{},{},{:.6},{:.6},{:.4},{:.4},{:.4}\n",
                                    stack.label,
                                    geometry.as_str(),
                                    step,
                                    m.name,
                                    window_of(m),
                                    w,
                                    p.d[i],
                                    p.count[i],
                                    p.wrong[i],
                                    p.exact[i],
                                    p.e_merged[i],
                                    p.e_oracle[i],
                                    p.bias[i],
                                ));
                            }
                        }
                    }
                }
            }
            eprintln!(
                "  {shape} step {step}: done at {:.1} s",
                t0.elapsed().as_secs_f64()
            );
        }
    }

    std::fs::write(&out_path, csv).map_err(|e| format!("writing {out_path}: {e}"))?;
    if let Some(p) = profile_out {
        std::fs::write(&p, pcsv).map_err(|e| format!("writing {p}: {e}"))?;
        eprintln!("wrote {p}");
    }
    eprintln!("wrote {out_path} in {:.1} s", t0.elapsed().as_secs_f64());
    Ok(())
}

// ------------------------------------------------------------ adaptive windows

/// Is a spatially adaptive window worth building?
///
/// Three arms on identical data, all scored by `RMS(merged - ideal)` over the
/// whole ROI:
///
/// - each fixed window on its own — the incumbent answer, "one number";
/// - an **oracle** that picks, per pixel, whichever of two windows lands closer
///   to the ideal. This is not realisable — it reads the answer — and is
///   therefore a strict **upper bound** on what any adaptive rule can win;
/// - a **realisable** rule that needs no ground truth: use the wide window
///   everywhere except where the two windows' elected frames disagree by more
///   than `tau`, and fall back to the narrow window there.
///
/// If the oracle bound is small, the recommendation is a single global window
/// and no amount of cleverness changes that. Measuring the bound *before*
/// designing a rule is the point.
#[allow(clippy::too_many_lines)]
fn adaptive_mode(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let dir = a.positional.first().ok_or("adaptive needs a directory")?;
    let stack = open_stack(
        Path::new(dir),
        a.one("limit").and_then(|v| v.parse().ok()),
        a.one("label"),
    )?;
    let out_path = a
        .one("out")
        .ok_or("adaptive needs --out <FILE>")?
        .to_string();

    let width = a.usize_or("width", 1)?;
    let nframes = a.usize_or("frames", 41)?;
    let sigma0 = a.f32_or("sigma0", 0.8)?;
    let alpha = a.f32_or("alpha", 0.35)?;
    let noise_scale = a.f32_or("noise-scale", 1.0)?;
    let steps: Vec<i32> = a
        .list_f32("steps", &[8.0, 16.0])?
        .iter()
        .map(|v| *v as i32)
        .collect();
    let seed = a
        .one("seed")
        .and_then(|v| v.parse::<u64>().ok())
        .unwrap_or(20_260_823);
    let band = a.usize_or("band", 24)? as i32;
    let taus = a.list_usize("taus", &[1, 2, 4, 8])?;
    let narrow = a.one("narrow").unwrap_or("tenengrad-w2").to_string();
    let wide = a.one("wide").unwrap_or("tenengrad-w11").to_string();

    let roi_near = Roi::parse(a.one("roi-near").ok_or("adaptive needs --roi-near")?)?;
    let roi_far = Roi::parse(a.one("roi-far").ok_or("adaptive needs --roi-far")?)?;

    let m_narrow = measures::parse(&narrow).ok_or(format!("unknown measure {narrow:?}"))?;
    let m_wide = measures::parse(&wide).ok_or(format!("unknown measure {wide:?}"))?;
    let ms = vec![m_narrow.clone(), m_wide.clone()];

    let w_near = nframes / 2 - steps.iter().max().copied().unwrap_or(0) as usize / 2;
    let probe = EdgeSpec {
        frames: nframes,
        w_near,
        w_far: w_near + steps.iter().max().copied().unwrap_or(0) as usize,
        sigma0,
        alpha,
        noise_scale,
        seed,
        geometry: EdgeGeometry::Vertical { at: 0 },
    };
    let margin = (width - 1) / 2 + max_support(&ms) + probe.max_blur_radius();
    let tex = build_edge_textures(&stack, roi_near, roi_far, margin)?;
    let geom = tex.tg.geom;

    let mut csv = String::from(
        "stack,step,width,narrow,wide,arm,tau,rms_all,rms_band,rms_far,acc,bleed_bg\n",
    );
    let cfg = ProfileConfig {
        band,
        baseline_lo: (tex.tg.roi.width as i32 / 2 - 32).max(band + 8),
        baseline_hi: tex.tg.roi.width as i32 / 2 - 4,
        max_d: tex.tg.roi.width as i32,
    };

    for &step in &steps {
        let w_near = nframes / 2 - (step as usize) / 2;
        let spec = EdgeSpec {
            frames: nframes,
            w_near,
            w_far: w_near + step as usize,
            sigma0,
            alpha,
            noise_scale,
            seed: seed.wrapping_mul(1_000_003).wrapping_add(step as u64),
            geometry: EdgeGeometry::Vertical { at: geom.width / 2 },
        };
        let scene = EdgeScene::render(&tex.near, &tex.far, geom, spec, Some(&stack.noise));
        let oracle_out = scene.oracle();
        let radius = (width - 1) / 2;

        let sel_n = winner_map_tile(
            geom,
            &focus_volume_owned(&m_narrow, &scene.frames, geom, &stack.noise),
            radius,
        );
        let sel_w = winner_map_tile(
            geom,
            &focus_volume_owned(&m_wide, &scene.frames, geom, &stack.noise),
            radius,
        );
        let merged_of = |sel: &[u16]| -> Vec<f32> {
            sel.iter()
                .enumerate()
                .map(|(p, k)| scene.frames[*k as usize][p])
                .collect()
        };
        let m_n = merged_of(&sel_n);
        let m_w = merged_of(&sel_w);

        let mut arms: Vec<(String, i64, Vec<u16>)> = vec![
            (format!("fixed:{narrow}"), -1, sel_n.clone()),
            (format!("fixed:{wide}"), -1, sel_w.clone()),
        ];

        // Oracle: per pixel, whichever window's *output* is closer to ideal.
        // Reads the answer; a strict upper bound, never a proposal.
        let mut sel_oracle = sel_w.clone();
        for &p in &tex.region {
            let dn = (m_n[p] - scene.ideal[p]).abs();
            let dw = (m_w[p] - scene.ideal[p]).abs();
            if dn < dw {
                sel_oracle[p] = sel_n[p];
            }
        }
        arms.push(("oracle:min-error".into(), -1, sel_oracle));

        // Realisable: disagreement gate. No ground truth is read.
        for &tau in &taus {
            let mut sel = sel_w.clone();
            for &p in &tex.region {
                if (sel_w[p] as i32 - sel_n[p] as i32).unsigned_abs() as usize > tau {
                    sel[p] = sel_n[p];
                }
            }
            arms.push(("rule:disagree".into(), tau as i64, sel));
        }

        for (arm, tau, sel) in arms {
            let merged = merged_of(&sel);
            let (mut se_all, mut se_band, mut se_far, mut hit) = (0.0f64, 0.0f64, 0.0f64, 0.0f64);
            let (mut n_band, mut n_far) = (0.0f64, 0.0f64);
            for &p in &tex.region {
                let e = (merged[p] - scene.ideal[p]) as f64;
                se_all += e * e;
                let (x, y) = (p % geom.width, p / geom.width);
                if spec.geometry.signed_distance(x, y).abs() <= cfg.band {
                    se_band += e * e;
                    n_band += 1.0;
                } else {
                    se_far += e * e;
                    n_far += 1.0;
                }
                if sel[p] == scene.truth[p] {
                    hit += 1.0;
                }
            }
            let n = tex.region.len() as f64;
            let prof = edge::profile(
                &scene,
                geom,
                spec,
                &sel,
                &merged,
                &oracle_out,
                &tex.region,
                cfg,
            );
            csv.push_str(&format!(
                "{},{},{},{},{},{},{},{:.4},{:.4},{:.4},{:.6},{:.4}\n",
                stack.label,
                step,
                width,
                narrow,
                wide,
                arm,
                tau,
                (se_all / n).sqrt(),
                (se_band / n_band.max(1.0)).sqrt(),
                (se_far / n_far.max(1.0)).sqrt(),
                hit / n,
                edge::bleed_width(&prof, cfg, 1),
            ));
        }
        eprintln!("  step {step} done");
    }

    std::fs::write(&out_path, csv).map_err(|e| format!("writing {out_path}: {e}"))?;
    Ok(())
}

// --------------------------------------------------------------- the crosscheck

/// Reproduce M2's published `1.2527x` / `1.0737x` and M11's `tenengrad-w5`
/// noise ratio through **this** harness's code path.
///
/// SYNTHESIS §5 item 15: a cross-check against a known published figure is the
/// cheapest guard against misreading a schema or a kernel, and it must be the
/// first thing a re-analysis prints. `m13_reproduce_m11.py` does the same job
/// for the CSV *reader*; this does it for the *harness*.
fn xcheck(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let dir = a.positional.first().ok_or("xcheck needs a directory")?;
    let stack = open_stack(Path::new(dir), None, a.one("label"))?;
    let roi = Roi::parse(a.one("roi").unwrap_or("2272,1344,256,256"))?;
    let mut out = String::new();
    let ms: Vec<Measure> = ["ring-1-3", "tenengrad-w5", "tenengrad-w11"]
        .iter()
        .map(|n| measures::parse(n).unwrap())
        .collect();
    let margin = 8 + max_support(&ms);
    let tg = TileGeom::new(roi, margin, stack.plane)?;
    let tiles = extract_tiles(&stack, std::slice::from_ref(&tg), false)?;
    let luma: Vec<&[f32]> = tiles.iter().map(|t| t[0].luma.as_slice()).collect();
    let value: Vec<&[f32]> = tiles.iter().map(|t| t[0].green.as_slice()).collect();
    let single = value[stack.middle];

    out.push_str(&format!("stack {} roi {}\n", stack.label, roi));
    for m in &ms {
        let vol = focus_volume(m, &luma, tg.geom, &stack.noise);
        for w in [1usize, 17] {
            let index = winner_map(&tg, &vol, (w - 1) / 2);
            let merged: Vec<f32> = index
                .iter()
                .enumerate()
                .map(|(p, k)| value[*k as usize][p])
                .collect();
            let (_, ss) = mean_and_sigma(&merged);
            let (_, s1) = mean_and_sigma(single);
            out.push_str(&format!(
                "  {:<16} width {:>2}: N = {:.4}x\n",
                m.name,
                w,
                ss / s1
            ));
        }
    }
    out.push_str(
        "\nM2 published ring-1-3 at width 1 = 1.2527x and width 17 = 1.0737x on this ROI\n\
         (reproduced by M11's harness to 4 dp). M11's cross-stack aggregate for\n\
         tenengrad-w5 is 1.1324x and for tenengrad-w11 1.0908x; those are medians over\n\
         four flat ROIs and a mean over two stacks, so a single-ROI figure here is only\n\
         required to be of the same magnitude, not identical.\n",
    );
    print!("{out}");
    if let Some(p) = a.one("out") {
        std::fs::write(p, &out).map_err(|e| e.to_string())?;
    }
    Ok(())
}

// ------------------------------------------------------------------------ cost

fn cost(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let dir = a.positional.first().ok_or("cost needs a directory")?;
    let stack = open_stack(Path::new(dir), Some(1), a.one("label"))?;
    let out_path = a.one("out").ok_or("cost needs --out <FILE>")?.to_string();
    let roi = Roi::parse(a.one("roi").unwrap_or("2272,1344,512,512"))?;
    let reps = a.usize_or("reps", 5)?;
    let ms = a.measures()?;
    let margin = max_support(&ms);
    let tg = TileGeom::new(roi, margin, stack.plane)?;
    let tiles = extract_tiles(&stack, std::slice::from_ref(&tg), false)?;
    let luma = &tiles[0][0].luma;
    let mpx = tg.geom.pixels() as f64 / 1.0e6;

    let mut csv =
        String::from("stack,measure,window,support_radius,mpx,reps,ms_per_frame_per_mpx\n");
    for m in &ms {
        let mut scratch = Scratch::default();
        let mut out = vec![0.0f32; tg.geom.pixels()];
        m.compute(luma, tg.geom, &stack.noise, 0, &mut scratch, &mut out);
        let t = std::time::Instant::now();
        for k in 0..reps {
            m.compute(luma, tg.geom, &stack.noise, k, &mut scratch, &mut out);
        }
        let ms_each = t.elapsed().as_secs_f64() * 1000.0 / reps as f64;
        csv.push_str(&format!(
            "{},{},{},{},{:.4},{},{:.4}\n",
            stack.label,
            m.name,
            window_of(m),
            m.support_radius,
            mpx,
            reps,
            ms_each / mpx
        ));
        eprintln!("  {:<20} {:.3} ms/frame/Mpx", m.name, ms_each / mpx);
    }
    std::fs::write(&out_path, csv).map_err(|e| format!("writing {out_path}: {e}"))?;
    Ok(())
}

// ------------------------------------------------------------------ self-tests

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

struct Checks {
    out: String,
    pass: usize,
    fail: usize,
}

impl Checks {
    fn new() -> Self {
        Self {
            out: String::new(),
            pass: 0,
            fail: 0,
        }
    }
    fn check(&mut self, ok: bool, what: &str, detail: String) {
        if ok {
            self.pass += 1;
            self.out.push_str(&format!("  PASS  {what}  {detail}\n"));
        } else {
            self.fail += 1;
            self.out.push_str(&format!("  FAIL  {what}  {detail}\n"));
        }
    }
    fn group(&mut self, name: &str) {
        self.out.push_str(&format!("\n{name}\n"));
    }
}

#[allow(clippy::too_many_lines)]
fn selftest(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let mut c = Checks::new();
    let noise = flat_noise();

    // ---- group A: the measure parser and the window axis -------------------
    c.group("A. the window axis is what the name says it is");
    for w in [0usize, 2, 5, 11, 20, 40] {
        let m = measures::parse(&format!("tenengrad-w{w}")).unwrap();
        c.check(
            m.support_radius == 1 + w,
            "support radius tracks the window",
            format!("tenengrad-w{w} -> radius {}", m.support_radius),
        );
    }
    {
        // A wider window must strictly widen the sensitivity kernel: the tap
        // count of a Tenengrad at window w is (2(w+1)+1)^2.
        let g = PlaneGeometry {
            width: 129,
            height: 129,
        };
        let luma: Vec<f32> = (0..g.pixels())
            .map(|i| {
                let (x, y) = ((i % g.width) as f32, (i / g.width) as f32);
                3000.0 + 120.0 * (x * 1.31).sin() * (y * 1.07).cos()
            })
            .collect();
        for w in [0usize, 2, 5, 11] {
            let m = measures::parse(&format!("tenengrad-w{w}")).unwrap();
            let (_, taps) = centre_tap(&m, &luma, g, &noise, 8.0);
            let want = (2 * (w + 1) + 1) * (2 * (w + 1) + 1);
            c.check(
                taps == want,
                "tap count is the analytic support",
                format!("w{w}: {taps} taps, analytic {want}"),
            );
        }
    }

    // ---- group B: what the window does to the centre tap ------------------
    //
    // M11 A1 reports φ *rising* with the window on real corpus texture
    // (w0 0.0335 -> w2 0.0612 -> w5 0.0728 -> w8 0.0872 -> w11 0.1089). That is
    // not a property of the kernel alone: with `Norm::None` the window can only
    // *spread* a centre bump over (2w+1)^2 output pixels, so the centre's share
    // of the total must fall once w >= 1. The rise M11 sees is the pointwise
    // normaliser's own 1-px centre tap becoming a larger fraction of a shrinking
    // window term. The kernel half of that is asserted here; the texture half is
    // measured on real corpus texture by the `phi` mode, not asserted.
    c.group("B. the window's effect on the centre tap, decomposed");
    {
        let g = PlaneGeometry {
            width: 257,
            height: 257,
        };
        let luma: Vec<f32> = (0..g.pixels())
            .map(|i| {
                let (x, y) = ((i % g.width) as f32, (i / g.width) as f32);
                3000.0
                    + 120.0 * (x * 1.31).sin() * (y * 1.07).cos()
                    + 60.0 * (x * 0.37 + y * 0.29).sin()
            })
            .collect();
        let mut prev = f64::INFINITY;
        let mut mono = true;
        let mut trace = String::new();
        for w in [1usize, 2, 5, 8, 11, 15, 20] {
            let m = measures::parse(&format!("tenengrad-w{w}-nonorm")).unwrap();
            let (phi, _) = centre_tap(&m, &luma, g, &noise, 8.0);
            trace.push_str(&format!("w{w}={phi:.4} "));
            if phi > prev + 1e-9 {
                mono = false;
            }
            prev = phi;
        }
        c.check(
            mono,
            "un-normalised: phi is non-increasing in window for w >= 1",
            trace,
        );
        let m0 = measures::parse("tenengrad-w0-nonorm").unwrap();
        let (phi0, _) = centre_tap(&m0, &luma, g, &noise, 8.0);
        c.check(
            phi0 < 1e-9,
            "the zero-centre-tap configuration is exactly zero",
            format!("phi = {phi0:.9}"),
        );
        let mut trace = String::new();
        for w in [0usize, 2, 5, 8, 11, 20] {
            let m = measures::parse(&format!("tenengrad-w{w}")).unwrap();
            let (phi, _) = centre_tap(&m, &luma, g, &noise, 8.0);
            trace.push_str(&format!("w{w}={phi:.4} "));
        }
        c.check(
            true,
            "OBSERVED (not asserted): pointwise-normalised phi on SYNTHETIC texture",
            format!("{trace}— compare M11 A1 on real texture in phi mode"),
        );
    }

    // ---- group C: the edge plant -------------------------------------------
    c.group("C. the occluding-edge plant");
    let g = PlaneGeometry {
        width: 384,
        height: 128,
    };
    let tex_near: Vec<f32> = (0..g.pixels())
        .map(|i| {
            let (x, y) = ((i % g.width) as f32, (i / g.width) as f32);
            1600.0 + 260.0 * (x * 0.91).sin() * (y * 0.53).cos()
        })
        .collect();
    let tex_far: Vec<f32> = (0..g.pixels())
        .map(|i| {
            let (x, y) = ((i % g.width) as f32, (i / g.width) as f32);
            2600.0 + 300.0 * (x * 0.23 + y * 0.61).sin()
        })
        .collect();
    let mk = |step: i32, ns: f32| EdgeSpec {
        frames: 41,
        w_near: 12,
        w_far: (12 + step) as usize,
        sigma0: 0.8,
        alpha: 0.35,
        noise_scale: ns,
        seed: 99,
        geometry: EdgeGeometry::Vertical { at: g.width / 2 },
    };
    {
        let s = mk(0, 0.0);
        let scene = EdgeScene::render(&tex_near, &tex_far, g, s, None);
        let worst = scene.clean[s.w_near]
            .iter()
            .zip(scene.ideal.iter())
            .map(|(a, b)| (a - b).abs())
            .fold(0.0f32, f32::max);
        c.check(
            worst < 1e-2,
            "a zero depth step renders the ideal image exactly",
            format!("max |frame[w] - ideal| = {worst:.2e} DN"),
        );
    }
    {
        // Far from the boundary the composite is just the layer that is there.
        let s = mk(8, 0.0);
        let scene = EdgeScene::render(&tex_near, &tex_far, g, s, None);
        let p = 64 * g.width + 8; // deep inside the occluder
        let q = 64 * g.width + g.width - 8; // deep inside the background
        let e1 = (scene.clean[s.w_near][p] - scene.ideal[p]).abs();
        let e2 = (scene.clean[s.w_far][q] - scene.ideal[q]).abs();
        c.check(
            e1 < 1e-2 && e2 < 1e-2,
            "far from the boundary each layer's own frame is ideal",
            format!("occluder {e1:.2e}, background {e2:.2e}"),
        );
    }
    {
        // And near the boundary it is not: that difference IS the physical halo.
        let s = mk(16, 0.0);
        let scene = EdgeScene::render(&tex_near, &tex_far, g, s, None);
        let oracle = scene.oracle();
        let mut near_edge = 0.0f64;
        let mut n = 0.0f64;
        for y in 0..g.height {
            for x in (g.width / 2)..(g.width / 2 + 6) {
                let p = y * g.width + x;
                let e = (oracle[p] - scene.ideal[p]) as f64;
                near_edge += e * e;
                n += 1.0;
            }
        }
        let rms = (near_edge / n).sqrt();
        c.check(
            rms > 1.0,
            "the oracle CANNOT reconstruct the ideal at the boundary",
            format!("oracle RMS at d in [0,6) = {rms:.2} DN — the irreducible floor"),
        );
    }

    // ---- group D: the halo metric's controls -------------------------------
    c.group("D. the halo metric: null, positive control, and chance");
    let cfg = ProfileConfig {
        band: 24,
        baseline_lo: 96,
        baseline_hi: 150,
        max_d: 192,
    };
    let region: Vec<usize> = (0..g.pixels()).collect();
    {
        let s = mk(16, 0.0);
        let scene = EdgeScene::render(&tex_near, &tex_far, g, s, None);
        let oracle = scene.oracle();
        let p = edge::profile(&scene, g, s, &scene.truth, &oracle, &oracle, &region, cfg);
        let bg = edge::bleed_width(&p, cfg, 1);
        let fg = edge::bleed_width(&p, cfg, -1);
        c.check(
            bg.abs() < 1e-12 && fg.abs() < 1e-12,
            "NULL 1: ground-truth selection has zero bleed",
            format!("bleed_bg = {bg:.3e} px, bleed_fg = {fg:.3e} px"),
        );
        let s0 = edge::summarise(&p, cfg, 1.0, 1.0, 0.0);
        c.check(
            s0.excess_dn.abs() < 1e-6,
            "NULL 1: ground-truth selection has zero excess error",
            format!("excess = {:.3e} DN", s0.excess_dn),
        );
    }
    {
        // NULL 2 — the strong one. Keep the intensity edge, the two textures,
        // the compositing and the noise; remove ONLY the depth step. A real
        // operator now runs on it and the metric must still read ~zero.
        let s = mk(0, 1.0);
        let scene = EdgeScene::render(&tex_near, &tex_far, g, s, Some(&noise));
        let oracle = scene.oracle();
        let m = measures::parse("tenengrad-w11").unwrap();
        let vol = focus_volume_owned(&m, &scene.frames, g, &noise);
        let sel = winner_map_tile(g, &vol, 0);
        let merged: Vec<f32> = sel
            .iter()
            .enumerate()
            .map(|(p, k)| scene.frames[*k as usize][p])
            .collect();
        let p = edge::profile(&scene, g, s, &sel, &merged, &oracle, &region, cfg);
        let bg = edge::bleed_width(&p, cfg, 1);
        c.check(
            bg.abs() < 1e-12,
            "NULL 2: a real operator on a zero-step scene has zero bleed",
            format!(
                "tenengrad-w11 bleed_bg = {bg:.3e} px (intensity edge present, depth step absent)"
            ),
        );
    }
    {
        let s = mk(16, 0.0);
        let scene = EdgeScene::render(&tex_near, &tex_far, g, s, None);
        let oracle = scene.oracle();
        let mut trace = String::new();
        let mut all_ok = true;
        for r in [1i32, 3, 8, 17, 32, 64] {
            let sel = edge::halo_positive_control(&scene, g, s, r);
            let merged: Vec<f32> = sel
                .iter()
                .enumerate()
                .map(|(p, k)| scene.frames[*k as usize][p])
                .collect();
            let p = edge::profile(&scene, g, s, &sel, &merged, &oracle, &region, cfg);
            let got = edge::bleed_width(&p, cfg, 1);
            let want = (r - 1) as f64;
            all_ok &= (got - want).abs() < 1e-9;
            trace.push_str(&format!("{r}->{got:.1} "));
        }
        c.check(
            all_ok,
            "POSITIVE: a planted halo of known width is recovered exactly",
            format!("planted->recovered (convention: d starts at 1): {trace}"),
        );
    }
    {
        // A uniformly random selector: the metric must NOT report a wide halo,
        // because there is no distance structure. This is the limitation the
        // report has to disclose, so it is asserted rather than described.
        let s = mk(16, 1.0);
        let scene = EdgeScene::render(&tex_near, &tex_far, g, s, Some(&noise));
        let oracle = scene.oracle();
        let m = measures::parse("ctl-random").unwrap();
        let vol = focus_volume_owned(&m, &scene.frames, g, &noise);
        let sel = winner_map_tile(g, &vol, 0);
        let merged: Vec<f32> = sel
            .iter()
            .enumerate()
            .map(|(p, k)| scene.frames[*k as usize][p])
            .collect();
        let p = edge::profile(&scene, g, s, &sel, &merged, &oracle, &region, cfg);
        let bg = edge::bleed_width(&p, cfg, 1);
        let sm = edge::summarise(&p, cfg, 1.0, 0.0, 0.0);
        c.check(
            bg < 4.0 && sm.excess_dn > 10.0,
            "CHANCE: a random selector shows no bleed WIDTH but large excess error",
            format!(
                "bleed_bg = {bg:.2} px, excess = {:.1} DN — the two metrics see different damage",
                sm.excess_dn
            ),
        );
    }

    // ---- group E: tile exactness at the widest window -----------------------
    c.group("E. tile exactness at the widest window in the sweep (rule 7 corollary)");
    {
        let base: Vec<f32> = (0..(160 * 160))
            .map(|i| {
                let (x, y) = ((i % 160) as f32, (i / 160) as f32);
                2400.0 + 180.0 * (x * 0.41).sin() * (y * 0.23).cos()
            })
            .collect();
        let gg = PlaneGeometry {
            width: 160,
            height: 160,
        };
        let spec = PlantSpec {
            frames: 9,
            w_true: 4,
            sigma0: 0.8,
            alpha: 0.35,
            noise_scale: 1.0,
            seed: 5,
        };
        let frames = planted::plant(&base, gg, &noise, spec);
        for wsz in [5usize, 11, 20] {
            let m = measures::parse(&format!("tenengrad-w{wsz}")).unwrap();
            let vol = focus_volume_owned(&m, &frames, gg, &noise);
            let margin = m.support_radius + 4;
            let tg = TileGeom::identity(gg, margin);
            let full = winner_map(&tg, &vol, 4);
            // The same computation on a wider margin must agree on the inset.
            let tg2 = TileGeom::identity(gg, margin + 8);
            let inner = winner_map(&tg2, &vol, 4);
            let mut agree = true;
            for j in 0..tg2.roi.height {
                for i in 0..tg2.roi.width {
                    let a = full[(j + 8) * tg.roi.width + (i + 8)];
                    let b = inner[j * tg2.roi.width + i];
                    if a != b {
                        agree = false;
                    }
                }
            }
            c.check(
                agree,
                "winner map is margin-independent on the inset",
                format!("tenengrad-w{wsz}, reg width 9"),
            );
        }
    }

    let head = format!("M13 self-test — {} passed, {} failed\n", c.pass, c.fail);
    let body = format!("{head}{}", c.out);
    print!("{body}");
    if let Some(p) = a.one("out") {
        std::fs::write(p, &body).map_err(|e| e.to_string())?;
    }
    if c.fail > 0 {
        return Err(format!("{} self-test assertions failed", c.fail));
    }
    Ok(())
}
