//! M16 — orientation asymmetry and fixed-pattern noise.
//!
//! Answers SYNTHESIS §10 question 20: why edge orientation sets the direction
//! the merge regulariser moves the focus-window optimum (fact 83), and whether
//! that is a defect biasing every window number M13 and M15 produced.
//!
//! The science lives in M13's modules and is **included by path, unmodified**:
//! the same layered-occlusion render, the same `E_excess`, the same Sobel and
//! box window, the same green-luma extraction. This crate adds only a sweep
//! driver plus five treatment knobs, so that any movement it measures is
//! attributable to a knob and not to a reimplementation.
//!
//! The treatments touch **only the focus operator's input**. `merged` is still
//! taken from the untreated frames, and `ideal`, `oracle` and `single_sigma`
//! are untouched, so `E_excess` is measured on the same physical quantity in
//! every arm and "you changed the metric" is not available as an explanation.
//!
//! Pre-registered in `PREREGISTRATION.md`, committed before any result here was
//! computed.

#[allow(dead_code)]
#[path = "../../m13-window-depth/src/edge.rs"]
mod edge;
#[allow(dead_code)]
#[path = "../../m13-window-depth/src/measures.rs"]
mod measures;
#[allow(dead_code)]
#[path = "../../m13-window-depth/src/planted.rs"]
mod planted;
#[allow(dead_code)]
#[path = "../../m13-window-depth/src/tile.rs"]
mod tile;

mod fpn;

use std::path::{Path, PathBuf};

use rayon::prelude::*;
use strehl_core::boxfilter::box_mean;
use strehl_core::noise::{Levels, NoiseModel};
use strehl_core::plane::{PlaneGeometry, QuadSource};
use strehl_core::profile;

use edge::{EdgeGeometry, EdgeScene, EdgeSpec, ProfileConfig};
use fpn::{Destripe, FpnPlant, FpnStage};
use measures::{max_support, Measure, Scratch};
use tile::{beats, FrameTile, Roi, TileGeom};

/// The read-only corpora this milestone may open, and may never write.
const READ_ONLY_ROOTS: [&str; 3] = [
    "C:\\dev\\macro",
    "D:\\macro-dark-frames",
    "D:\\personal\\macro",
];

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mode = args.first().map(String::as_str).unwrap_or("help");
    let rest = if args.is_empty() {
        &args[..]
    } else {
        &args[1..]
    };
    let r = match mode {
        "edge" => edge_mode(rest),
        "fpnscan" => fpnscan_mode(rest),
        "anisoscan" => anisoscan_mode(rest),
        "darkfpn" => darkfpn_mode(rest),
        "audit" => audit(rest),
        "selftest" => selftest(),
        _ => {
            eprintln!(
                "usage:\n  \
                 m16 edge <DIR> --out F --roi-near X,Y,W,H --roi-far X,Y,W,H [knobs]\n  \
                 m16 fpnscan <DIR> --out F --roi X,Y,W,H [--roi ...] [--limit N]\n  \
                 m16 audit [--out F]\n  \
                 m16 selftest\n\
                 \n\
                 edge knobs beyond M13's:\n  \
                 --seeds a,b,c        run several base seeds in one decode\n  \
                 --texture real|synth real tiles, or an isotropic 1/f field\n  \
                 --destripe none|mean|hp|oracle   operator-input treatment\n  \
                 --hp-sigma S         profile blur for --destripe hp (default 4)\n  \
                 --fpn-sd DN          plant a row/column offset pattern\n  \
                 --fpn-axis row|col|both\n  \
                 --fpn-stage sensor|texture  post-blur fixed pattern, or in the texture\n  \
                 --fpn-seed N\n  \
                 --transpose          transpose both textures (square tiles only)\n  \
                 --score-region W,H   centred crop of the scored ROI interior\n  \
                 --arm LABEL          written into the CSV\n"
            );
            Ok(())
        }
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
    fn u64_or(&self, key: &str, default: u64) -> Result<u64, String> {
        match self.one(key) {
            Some(v) => v.parse::<u64>().map_err(|e| format!("--{key}: {e}")),
            None => Ok(default),
        }
    }
    fn list_u64(&self, key: &str, default: &[u64]) -> Result<Vec<u64>, String> {
        match self.one(key) {
            Some(s) => s
                .split(',')
                .map(|v| v.trim().parse::<u64>().map_err(|e| format!("--{key}: {e}")))
                .collect(),
            None => Ok(default.to_vec()),
        }
    }
    fn list_i32(&self, key: &str, default: &[i32]) -> Result<Vec<i32>, String> {
        match self.one(key) {
            Some(s) => s
                .split(',')
                .map(|v| v.trim().parse::<i32>().map_err(|e| format!("--{key}: {e}")))
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
    /// The measure set, identical in spelling to M13's so the `measure` column
    /// joins across milestones.
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

fn window_of(m: &Measure) -> usize {
    m.name
        .rsplit('-')
        .find_map(|s| s.strip_prefix('w').and_then(|v| v.parse::<usize>().ok()))
        .unwrap_or(0)
}

// ---------------------------------------------------------------------- audit

/// File count and byte total of the read-only corpora, so the report can show
/// the milestone took nothing and left nothing. Counts hidden entries, which
/// `Get-ChildItem` without `-Force` does not (project rule 14).
fn audit(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let mut out = String::new();
    for root in READ_ONLY_ROOTS {
        let mut files = 0u64;
        let mut bytes = 0u64;
        let mut newest = std::time::UNIX_EPOCH;
        let mut stack = vec![PathBuf::from(root)];
        while let Some(dir) = stack.pop() {
            let Ok(rd) = std::fs::read_dir(&dir) else {
                continue;
            };
            for e in rd.flatten() {
                let p = e.path();
                if p.is_dir() {
                    stack.push(p);
                } else if let Ok(md) = e.metadata() {
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

// ---------------------------------------------------------------------- stack

struct StackInfo {
    label: String,
    paths: Vec<PathBuf>,
    plane: PlaneGeometry,
    levels: Levels,
    noise: NoiseModel,
    iso: Option<f32>,
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
        paths,
        plane,
        levels,
        noise,
        iso: first.iso,
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
/// whole tile. Copied verbatim from M13's `winner_map_tile`, including the
/// shipped tie-break, so the election is the shipped election.
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

// ------------------------------------------------------------------- fpn scan

/// Descriptive plant characterisation: how much row and column structure the
/// real texture tiles actually carry, and how isotropic they are. Measured
/// before the arms, reported as a property of the plant, not as a test.
/// Measures gradient anisotropy **before and after** each destripe treatment.
///
/// Answers a question the arms alone cannot: the A1 treatment removes most of
/// the row-marginal variance, yet leaves the orientation asymmetry unchanged.
/// If `aniso` is still far from 1 after `destripe_mean`, the corpus tiles are
/// anisotropic in two dimensions, not merely in their row marginal — and a
/// row/column mean subtraction was never going to touch that.
fn anisoscan_mode(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let dir = a.positional.first().ok_or("anisoscan needs a directory")?;
    let stack = open_stack(
        Path::new(dir),
        a.one("limit").and_then(|v| v.parse().ok()),
        a.one("label"),
    )?;
    let out_path = a
        .one("out")
        .ok_or("anisoscan needs --out <FILE>")?
        .to_string();
    let hp_sigma = a.f32_or("hp-sigma", 4.0)?;
    let rois: Vec<Roi> = a
        .many("roi")
        .iter()
        .map(|s| Roi::parse(s))
        .collect::<Result<_, _>>()?;
    if rois.is_empty() {
        return Err("anisoscan needs at least one --roi X,Y,W,H".into());
    }
    let tgs: Vec<TileGeom> = rois
        .iter()
        .map(|r| TileGeom::new(*r, 0, stack.plane))
        .collect::<Result<_, _>>()?;
    let tiles = extract_tiles(&stack, &tgs, false)?;

    let mut csv = String::from(
        "stack,iso,roi,frame,variant,width,height,mean_dn,sd_dn,\
         row_sd_raw,col_sd_raw,gx2,gy2,aniso,row_share,col_share\n",
    );
    for (ri, tg) in tgs.iter().enumerate() {
        for (fi, ft) in tiles.iter().enumerate() {
            for variant in [Destripe::None, Destripe::Mean, Destripe::Hp] {
                let mut luma = ft[ri].luma.clone();
                match variant {
                    Destripe::None => {}
                    Destripe::Mean => fpn::destripe_mean(&mut luma, tg.geom),
                    Destripe::Hp => fpn::destripe_hp(&mut luma, tg.geom, hp_sigma),
                    Destripe::Oracle => {}
                }
                let s = fpn::scan(&luma, tg.geom, hp_sigma);
                csv.push_str(&format!(
                    "{},{},{},{},{},{},{},{:.4},{:.4},{:.5},{:.5},{:.6},{:.6},{:.5},{:.6},{:.6}\n",
                    stack.label,
                    stack.iso.unwrap_or(0.0),
                    format_args!(
                        "{}x{}+{}+{}",
                        tg.roi.width, tg.roi.height, tg.roi.x, tg.roi.y
                    ),
                    fi,
                    variant.as_str(),
                    tg.geom.width,
                    tg.geom.height,
                    s.mean,
                    s.sd,
                    s.row_sd_raw,
                    s.col_sd_raw,
                    s.gx2,
                    s.gy2,
                    s.aniso,
                    s.row_share,
                    s.col_share,
                ));
            }
        }
    }
    std::fs::write(&out_path, csv).map_err(|e| format!("write {out_path}: {e}"))?;
    eprintln!("anisoscan -> {out_path}");
    Ok(())
}

fn fpnscan_mode(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let dir = a.positional.first().ok_or("fpnscan needs a directory")?;
    let stack = open_stack(
        Path::new(dir),
        a.one("limit").and_then(|v| v.parse().ok()),
        a.one("label"),
    )?;
    let out_path = a
        .one("out")
        .ok_or("fpnscan needs --out <FILE>")?
        .to_string();
    let hp_sigma = a.f32_or("hp-sigma", 4.0)?;
    let rois: Vec<Roi> = a
        .many("roi")
        .iter()
        .map(|s| Roi::parse(s))
        .collect::<Result<_, _>>()?;
    if rois.is_empty() {
        return Err("fpnscan needs at least one --roi X,Y,W,H".into());
    }
    let tgs: Vec<TileGeom> = rois
        .iter()
        .map(|r| TileGeom::new(*r, 0, stack.plane))
        .collect::<Result<_, _>>()?;
    let tiles = extract_tiles(&stack, &tgs, false)?;

    let mut csv = String::from(
        "stack,iso,roi,frame,width,height,mean_dn,sd_dn,\
         row_sd_raw,col_sd_raw,row_sd_hp,col_sd_hp,resid_sd,\
         gx2,gy2,aniso,row_share,col_share\n",
    );
    // Every frame of the stack for the first ROI (so the across-frame constancy
    // of the row profile is visible), first frame only for the rest.
    for (ri, tg) in tgs.iter().enumerate() {
        let nf = if ri == 0 { tiles.len() } else { 1 };
        for (fi, ft) in tiles.iter().enumerate().take(nf) {
            let luma = &ft[ri].luma;
            let s = fpn::scan(luma, tg.geom, hp_sigma);
            csv.push_str(&format!(
                "{},{},{},{},{},{},{:.4},{:.4},{:.5},{:.5},{:.5},{:.5},{:.5},{:.6},{:.6},{:.5},{:.6},{:.6}\n",
                stack.label,
                stack.iso.unwrap_or(0.0),
                format_args!(
                    "{}x{}+{}+{}",
                    rois[ri].width, rois[ri].height, rois[ri].x, rois[ri].y
                ),
                fi,
                tg.geom.width,
                tg.geom.height,
                s.mean,
                s.sd,
                s.row_sd_raw,
                s.col_sd_raw,
                s.row_sd_hp,
                s.col_sd_hp,
                s.resid_sd,
                s.gx2,
                s.gy2,
                s.aniso,
                s.row_share,
                s.col_share,
            ));
        }
    }
    // The synthetic field, for the same readout, at the tile size the arms use
    // and at a square tile — because a rectangular tile makes even an isotropic
    // generator read anisotropic (the clamped blur border is proportionally
    // larger on the short axis), and the control has to be honest about that.
    let g0 = tgs[0].geom;
    let square = PlaneGeometry {
        width: g0.height,
        height: g0.height,
    };
    for g in [g0, square] {
        for seed in [0x5EED_0F0Cu64, 0x5EED_0F0C ^ 0x9E37_79B9] {
            let f = fpn::synthetic_texture_seeded(g, 2000.0, 300.0, seed);
            let s = fpn::scan(&f, g, hp_sigma);
            csv.push_str(&format!(
                "synthetic,0,seed{seed:#x},0,{},{},{:.4},{:.4},{:.5},{:.5},{:.5},{:.5},{:.5},{:.6},{:.6},{:.5},{:.6},{:.6}\n",
                g.width, g.height,
                s.mean, s.sd, s.row_sd_raw, s.col_sd_raw, s.row_sd_hp, s.col_sd_hp,
                s.resid_sd, s.gx2, s.gy2, s.aniso, s.row_share, s.col_share,
            ));
        }
    }
    std::fs::write(&out_path, csv).map_err(|e| format!("writing {out_path}: {e}"))?;
    eprintln!("wrote {out_path}");
    Ok(())
}

// ----------------------------------------------------------------- dark FPN

/// Decompose a dark stack's fixed-pattern noise into **row**, **column** and
/// **residual** parts.
///
/// H3's premise is that the sensor's fixed pattern is row/column structured, so
/// Sobel-x and Sobel-y see it asymmetrically. M4 measured the *total* per-pixel
/// FPN sigma and never decomposed it; M5 §3.1 asserts a row/column form as an
/// argued root cause. This mode measures the split directly.
///
/// Method. Average `M` frames of a dark folder into a master bias — which
/// suppresses temporal noise by `sqrt(M)` and leaves the fixed pattern intact
/// (M4 §6) — then take the row and column marginals of the master. The same
/// marginals of a **split-half difference** of the same frames give the
/// temporal floor those marginals would show with no fixed pattern at all, so
/// the excess over that floor is the fixed part. The difference is the null
/// control: it contains no fixed pattern by construction.
fn darkfpn_mode(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let root = a
        .positional
        .first()
        .ok_or("darkfpn needs the dark-frame root")?;
    let out_path = a
        .one("out")
        .ok_or("darkfpn needs --out <FILE>")?
        .to_string();
    let roi = Roi::parse(a.one("roi").unwrap_or("1600,1000,512,512"))?;
    let hp_sigma = a.f32_or("hp-sigma", 4.0)?;
    let take = a.usize_or("take", 20)?;

    let mut dirs: Vec<PathBuf> = std::fs::read_dir(Path::new(root))
        .map_err(|e| format!("reading {root}: {e}"))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.is_dir())
        .collect();
    dirs.sort();

    let mut csv = String::from(
        "folder,iso,frames_used,width,height,\
         master_sd,master_row_sd,master_col_sd,master_resid_sd,master_aniso,\
         diff_sd,diff_row_sd,diff_col_sd,diff_aniso,\
         fpn_row_sd,fpn_col_sd,fpn_total_sd\n",
    );
    for dir in &dirs {
        let stack = match open_stack(dir, None, None) {
            Ok(s) => s,
            Err(e) => {
                eprintln!("  skipping {}: {e}", dir.display());
                continue;
            }
        };
        // M4 discards the first two frames of every dark group.
        let paths: Vec<PathBuf> = stack.paths.iter().skip(2).take(take).cloned().collect();
        if paths.len() < 8 {
            eprintln!(
                "  skipping {}: only {} usable frames",
                dir.display(),
                paths.len()
            );
            continue;
        }
        let tg = TileGeom::new(roi, 0, stack.plane)?;
        let sub = StackInfo {
            label: stack.label.clone(),
            paths,
            plane: stack.plane,
            levels: stack.levels,
            noise: stack.noise.clone(),
            iso: stack.iso,
        };
        let tiles = extract_tiles(&sub, std::slice::from_ref(&tg), false)?;
        let n = tiles.len();
        let px = tg.geom.pixels();

        let mut master = vec![0.0f32; px];
        // Split-half difference: the null. Fixed pattern cancels exactly.
        let mut diff = vec![0.0f32; px];
        let half = n / 2;
        for (k, t) in tiles.iter().enumerate() {
            let l = &t[0].luma;
            for i in 0..px {
                master[i] += l[i] / n as f32;
                if k < half {
                    diff[i] += l[i] / half as f32;
                } else {
                    diff[i] -= l[i] / (n - half) as f32;
                }
            }
        }
        // The difference of two half-means has sqrt(1/half + 1/(n-half)) times
        // the single-frame temporal sd; the master has sqrt(1/n). Scale the
        // difference down to the master's temporal level so the two marginals
        // are directly comparable.
        let scale = ((1.0 / n as f64) / (1.0 / half as f64 + 1.0 / (n - half) as f64)).sqrt();
        for v in diff.iter_mut() {
            *v *= scale as f32;
        }

        let ms = fpn::scan(&master, tg.geom, hp_sigma);
        let ds = fpn::scan(&diff, tg.geom, hp_sigma);
        // Everything below is a per-frame amplitude: the master's marginals are
        // sqrt(n) quieter in the temporal term but carry the fixed pattern at
        // full strength, so the fixed part is the excess over the difference.
        let fpn_row = (ms.row_sd_hp.powi(2) - ds.row_sd_hp.powi(2))
            .max(0.0)
            .sqrt();
        let fpn_col = (ms.col_sd_hp.powi(2) - ds.col_sd_hp.powi(2))
            .max(0.0)
            .sqrt();
        let fpn_tot = (ms.sd.powi(2) - ds.sd.powi(2)).max(0.0).sqrt();
        eprintln!(
            "  {} iso {:?}: master row {:.4} col {:.4}; null row {:.4} col {:.4}; \
             fixed row {:.4} col {:.4} total {:.4} DN",
            stack.label,
            stack.iso,
            ms.row_sd_hp,
            ms.col_sd_hp,
            ds.row_sd_hp,
            ds.col_sd_hp,
            fpn_row,
            fpn_col,
            fpn_tot
        );
        csv.push_str(&format!(
            "{},{},{},{},{},{:.5},{:.5},{:.5},{:.5},{:.5},{:.5},{:.5},{:.5},{:.5},{:.5},{:.5},{:.5}\n",
            stack.label,
            stack.iso.unwrap_or(0.0),
            n,
            tg.geom.width,
            tg.geom.height,
            ms.sd, ms.row_sd_hp, ms.col_sd_hp, ms.resid_sd, ms.aniso,
            ds.sd, ds.row_sd_hp, ds.col_sd_hp, ds.aniso,
            fpn_row, fpn_col, fpn_tot,
        ));
    }
    std::fs::write(&out_path, csv).map_err(|e| format!("writing {out_path}: {e}"))?;
    eprintln!("wrote {out_path}");
    Ok(())
}

// ----------------------------------------------------- the discontinuity plant

struct EdgeTextures {
    near: Vec<f32>,
    far: Vec<f32>,
    tg: TileGeom,
    /// Tile indices of the scored region.
    region: Vec<usize>,
    /// Which frame of the stack the textures came from, for provenance.
    base_frame: usize,
}

/// Identical to M13's `build_edge_textures`: the sharpest frame on the near ROI
/// supplies both layers, so the two layers carry the same sensor state.
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
        base_frame,
    })
}

/// Restrict the scored region to a centred `w x h` window of the ROI. This is
/// the H2a probe: it changes the shape and pixel count of the scored band
/// without touching the plant.
fn crop_region(tg: &TileGeom, w: usize, h: usize) -> Result<Vec<usize>, String> {
    if w > tg.roi.width || h > tg.roi.height {
        return Err(format!(
            "--score-region {w},{h} does not fit in ROI {}x{}",
            tg.roi.width, tg.roi.height
        ));
    }
    let x0 = (tg.roi.width - w) / 2;
    let y0 = (tg.roi.height - h) / 2;
    Ok((y0..y0 + h)
        .flat_map(|j| (x0..x0 + w).map(move |i| (i, j)))
        .map(|(i, j)| tg.roi_index(i, j))
        .collect())
}

fn transpose(src: &[f32], geom: PlaneGeometry) -> Vec<f32> {
    let mut out = vec![0.0f32; src.len()];
    for y in 0..geom.height {
        for x in 0..geom.width {
            out[x * geom.width + y] = src[y * geom.width + x];
        }
    }
    out
}

/// `T <- (T + T_transpose) / 2` on a square tile.
///
/// The sharpest available test of H2. The result is **exactly** invariant under
/// transposition, so it carries the real corpus's contrast, intensity step and
/// spatial spectrum while having, by construction, no preferred axis at all.
/// Any orientation asymmetry that survives this treatment is therefore in the
/// machinery, not in the scene — no synthetic-texture regime mismatch to argue
/// about, because the texture is still the corpus's own.
fn symmetrise(src: &[f32], geom: PlaneGeometry) -> Vec<f32> {
    let t = transpose(src, geom);
    src.iter().zip(&t).map(|(a, b)| 0.5 * (a + b)).collect()
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

    let widths = a.list_usize("widths", &[1, 9, 17])?;
    let nframes = a.usize_or("frames", 41)?;
    let sigma0 = a.f32_or("sigma0", 0.8)?;
    let alpha = a.f32_or("alpha", 0.35)?;
    let noise_scale = a.f32_or("noise-scale", 1.0)?;
    let steps = a.list_i32("steps", &[4, 8, 16])?;
    let seeds = a.list_u64("seeds", &[20_260_823])?;
    let band = a.usize_or("band", 24)? as i32;
    let shapes: Vec<String> = if a.many("shape").is_empty() {
        vec!["vertical".into()]
    } else {
        a.many("shape")
    };
    let bar_half = a.usize_or("bar-half-width", 12)?;
    let arm = a.one("arm").unwrap_or("unlabelled").to_string();

    // --- the M16 knobs -----------------------------------------------------
    let texture_kind = a.one("texture").unwrap_or("real").to_string();
    let destripe = Destripe::parse(a.one("destripe").unwrap_or("none"))?;
    let hp_sigma = a.f32_or("hp-sigma", 4.0)?;
    let fpn_sd = a.f32_or("fpn-sd", 0.0)?;
    let fpn_axis = a.one("fpn-axis").unwrap_or("row").to_string();
    let fpn_stage = FpnStage::parse(a.one("fpn-stage").unwrap_or("sensor"))?;
    let fpn_seed = a.u64_or("fpn-seed", 0x0F1E_2D3C)?;
    let do_transpose = a.has("transpose");
    let do_symmetrise = a.has("symmetrise");
    let score_region = a.one("score-region").map(String::from);
    let synth_seed = a.u64_or("synth-seed", 0x5EED_0F0C)?;
    let synth_base = a.f32_or("synth-base", 2000.0)?;
    let synth_amp = a.f32_or("synth-amp", 300.0)?;

    let roi_near = Roi::parse(a.one("roi-near").ok_or("edge needs --roi-near X,Y,W,H")?)?;
    let roi_far = Roi::parse(a.one("roi-far").ok_or("edge needs --roi-far X,Y,W,H")?)?;

    let ms = a.measures()?;
    let max_step = steps.iter().max().copied().unwrap_or(0) as usize;
    let w_near0 = nframes / 2 - max_step / 2;
    let probe = EdgeSpec {
        frames: nframes,
        w_near: w_near0,
        w_far: w_near0 + max_step,
        sigma0,
        alpha,
        noise_scale,
        seed: seeds[0],
        geometry: EdgeGeometry::Vertical { at: 0 },
    };
    let margin = match a.one("margin") {
        Some(v) => v.parse::<usize>().map_err(|e| format!("--margin: {e}"))?,
        None => {
            widths.iter().map(|w| (w - 1) / 2).max().unwrap_or(0)
                + max_support(&ms)
                + probe.max_blur_radius()
        }
    };
    // A margin override exists so an arm can sweep a subset of M15's widths
    // while keeping M15's tile, and therefore M15's *scene*: the edge sits at
    // `tile_width / 2`, so shrinking the margin would move the boundary
    // relative to the texture and silently make a different experiment. Gate 2
    // checks the override reproduces M15 field for field.
    let auto = widths.iter().map(|w| (w - 1) / 2).max().unwrap_or(0)
        + max_support(&ms)
        + probe.max_blur_radius();
    if margin < auto {
        return Err(format!(
            "--margin {margin} is below the {auto} px this ladder needs; \
             scored pixels would have a clamped operator window"
        ));
    }

    let mut tex = build_edge_textures(&stack, roi_near, roi_far, margin)?;
    let geom = tex.tg.geom;

    // --- apply the texture-level knobs, in a fixed order -------------------
    if texture_kind == "synth" {
        // Two independent isotropic fields, so the two layers are as unrelated
        // as the two real ROIs are.
        tex.near = fpn::synthetic_texture_seeded(geom, synth_base, synth_amp, synth_seed);
        tex.far =
            fpn::synthetic_texture_seeded(geom, synth_base, synth_amp, synth_seed ^ 0x9E37_79B9);
    } else if texture_kind != "real" {
        return Err(format!("unknown --texture {texture_kind:?}"));
    }
    if do_transpose {
        if geom.width != geom.height {
            return Err(format!(
                "--transpose needs a square tile; this one is {}x{}. Use a square ROI.",
                geom.width, geom.height
            ));
        }
        tex.near = transpose(&tex.near, geom);
        tex.far = transpose(&tex.far, geom);
    }
    if do_symmetrise {
        if geom.width != geom.height {
            return Err(format!(
                "--symmetrise needs a square tile; this one is {}x{}. Use a square ROI.",
                geom.width, geom.height
            ));
        }
        tex.near = symmetrise(&tex.near, geom);
        tex.far = symmetrise(&tex.far, geom);
    }
    let plant = FpnPlant::new(fpn_sd, &fpn_axis, fpn_stage, fpn_seed, geom)?;
    if plant.active() && fpn_stage == FpnStage::Texture {
        plant.apply(&mut tex.near, geom);
        plant.apply(&mut tex.far, geom);
    }
    let (score_w, score_h) = match &score_region {
        Some(s) => {
            let p: Vec<usize> = s
                .split(',')
                .map(|v| v.trim().parse::<usize>().map_err(|e| e.to_string()))
                .collect::<Result<_, _>>()?;
            if p.len() != 2 {
                return Err("--score-region wants W,H".into());
            }
            tex.region = crop_region(&tex.tg, p[0], p[1])?;
            (p[0], p[1])
        }
        None => (tex.tg.roi.width, tex.tg.roi.height),
    };

    eprintln!(
        "edge[{arm}]: margin {margin} px -> tile {}x{}, ROI {}x{}, scored {}x{}; \
         texture={texture_kind} destripe={} fpn={:.4}DN/{fpn_axis}/{} transpose={do_transpose} symmetrise={do_symmetrise}",
        geom.width,
        geom.height,
        tex.tg.roi.width,
        tex.tg.roi.height,
        score_w,
        score_h,
        destripe.as_str(),
        fpn_sd,
        fpn_stage.as_str(),
    );
    eprintln!(
        "  {} measures x {} widths x {} steps x {} shapes x {} seeds = {} rows",
        ms.len(),
        widths.len(),
        steps.len(),
        shapes.len(),
        seeds.len(),
        ms.len() * widths.len() * steps.len() * shapes.len() * seeds.len()
    );

    let cfg = ProfileConfig {
        band,
        baseline_lo: (tex.tg.roi.width as i32 / 2 - 32).max(band + 8),
        baseline_hi: tex.tg.roi.width as i32 / 2 - 4,
        max_d: tex.tg.roi.width as i32,
        mis_tol: 2,
    };
    eprintln!(
        "  profile: band |d| <= {}, far baseline d in [{}, {}], max_d {}",
        cfg.band, cfg.baseline_lo, cfg.baseline_hi, cfg.max_d
    );

    // The first 33 columns are M15's, in M15's order, so a shared-column
    // comparison against `experiments/m15-regulariser-window/data/edge-*.csv`
    // is a field-by-field string comparison (Gate 2). M16's provenance columns
    // come after.
    let mut csv = String::from(
        "stack,shape,frames,w_near,w_far,step,sigma0,alpha,noise_scale,seed,band,\
         measure,family,window,support_radius,width,radius,eff_radius,\
         acc,acc_band,bleed_bg,bleed_fg,mis_bg,mis_fg,dmae_band,dmae_far,\
         excess_dn,excess_sigma,band_rms,floor_rms,far_rms,peak_bias,single_sigma,\
         arm,texture,destripe,fpn_sd,fpn_axis,fpn_stage,transpose,score_w,score_h,base_frame\n",
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
            for &base_seed in &seeds {
                let w_near = nframes / 2 - (step as usize) / 2;
                let spec = EdgeSpec {
                    frames: nframes,
                    w_near,
                    w_far: w_near + step as usize,
                    sigma0,
                    alpha,
                    noise_scale,
                    seed: base_seed.wrapping_mul(1_000_003).wrapping_add(step as u64),
                    geometry,
                };
                let scene = EdgeScene::render(&tex.near, &tex.far, geom, spec, Some(&stack.noise));
                let oracle = scene.oracle();

                let single_sigma = {
                    let k = spec.w_far.min(spec.frames - 1);
                    let mut acc = 0.0f64;
                    for &p in &tex.region {
                        let d = (scene.frames[k][p] - scene.clean[k][p]) as f64;
                        acc += d * d;
                    }
                    (acc / tex.region.len() as f64).sqrt()
                };

                // The treated operator input. `None` means "byte-identically
                // M15's path" — the no-op arm cannot differ by construction.
                let treated: Option<Vec<Vec<f32>>> = if destripe == Destripe::None
                    && !(plant.active() && fpn_stage == FpnStage::Sensor)
                {
                    None
                } else {
                    Some(
                        scene
                            .frames
                            .par_iter()
                            .map(|f| {
                                let mut g = f.clone();
                                if plant.active() && fpn_stage == FpnStage::Sensor {
                                    plant.apply(&mut g, geom);
                                }
                                match destripe {
                                    Destripe::None => {}
                                    Destripe::Mean => fpn::destripe_mean(&mut g, geom),
                                    Destripe::Hp => fpn::destripe_hp(&mut g, geom, hp_sigma),
                                    Destripe::Oracle => plant.remove(&mut g, geom),
                                }
                                g
                            })
                            .collect(),
                    )
                };
                let op_frames: &[Vec<f32>] = treated.as_deref().unwrap_or(&scene.frames);

                for m in &ms {
                    let vol = focus_volume_owned(m, op_frames, geom, &stack.noise);
                    let rows: Vec<(usize, edge::EdgeSummary)> = widths
                        .par_iter()
                        .map(|w| {
                            let sel = winner_map_tile(geom, &vol, (w - 1) / 2);
                            // The merge output is taken from the UNTREATED
                            // frames, so the treatment changes only which frame
                            // is elected, never what is delivered.
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
                            (*w, edge::summarise(&prof, cfg, single_sigma, acc, far_rms))
                        })
                        .collect();
                    for (w, s) in rows {
                        csv.push_str(&format!(
                            "{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{:.6},{:.6},{:.4},{:.4},{:.4},{:.4},{:.4},{:.4},{:.4},{:.5},{:.4},{:.4},{:.4},{:.4},{:.4},\
                             {},{},{},{:.5},{},{},{},{},{},{}\n",
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
                            s.mis_bg,
                            s.mis_fg,
                            s.dmae_band,
                            s.dmae_far,
                            s.excess_dn,
                            s.excess_sigma,
                            s.band_rms,
                            s.floor_rms,
                            s.far_rms,
                            s.peak_bias,
                            single_sigma,
                            arm,
                            texture_kind,
                            destripe.as_str(),
                            fpn_sd,
                            fpn_axis,
                            fpn_stage.as_str(),
                            u8::from(do_transpose),
                            score_w,
                            score_h,
                            tex.base_frame,
                        ));
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
    eprintln!("wrote {out_path} in {:.1} s", t0.elapsed().as_secs_f64());
    Ok(())
}

// -------------------------------------------------------------------- selftest

fn selftest() -> Result<(), String> {
    let g = PlaneGeometry {
        width: 96,
        height: 64,
    };

    // G3: the re-seeded synthetic texture reproduces M13's at M13's seed.
    let a = planted::synthetic_texture(g, 2000.0, 300.0);
    let b = fpn::synthetic_texture_seeded(g, 2000.0, 300.0, 0x5EED_0F0C);
    if a != b {
        return Err("G3 FAIL: synthetic_texture_seeded != planted::synthetic_texture".into());
    }
    println!("G3 ok: synthetic_texture_seeded is bit-identical at seed 0x5EED0F0C");

    // A different seed must give a different field, or the seed is ignored.
    let c = fpn::synthetic_texture_seeded(g, 2000.0, 300.0, 0xA11C_E5EE);
    if a == c {
        return Err("G3 FAIL: the seed does nothing".into());
    }
    println!("G3 ok: a different seed gives a different field");

    // destripe_mean removes an exactly-planted row+column pattern and preserves
    // the plane mean.
    let mut f = fpn::synthetic_texture_seeded(g, 2000.0, 300.0, 7);
    let before = f.iter().map(|v| *v as f64).sum::<f64>() / f.len() as f64;
    let plant = FpnPlant::new(25.0, "both", FpnStage::Sensor, 99, g)?;
    let clean = f.clone();
    plant.apply(&mut f, g);
    let planted_delta = f
        .iter()
        .zip(&clean)
        .map(|(a, b)| (a - b).abs() as f64)
        .fold(0.0f64, f64::max);
    if planted_delta < 1.0 {
        return Err(format!("plant did nothing: max delta {planted_delta}"));
    }
    let mut d1 = f.clone();
    fpn::destripe_mean(&mut d1, g);
    let mut d0 = clean.clone();
    fpn::destripe_mean(&mut d0, g);
    let resid = d1
        .iter()
        .zip(&d0)
        .map(|(a, b)| (a - b).abs() as f64)
        .fold(0.0f64, f64::max);
    if resid > 1e-2 {
        return Err(format!(
            "destripe_mean did not remove a planted row+col pattern: residual {resid:.4} DN"
        ));
    }
    println!("positive control ok: destripe_mean removes a {planted_delta:.2} DN plant to {resid:.2e} DN");

    let after = d0.iter().map(|v| *v as f64).sum::<f64>() / d0.len() as f64;
    if (after - before).abs() > 1e-2 {
        return Err(format!(
            "destripe_mean changed the plane mean: {before:.4} -> {after:.4}"
        ));
    }
    println!("level control ok: plane mean preserved, {before:.4} -> {after:.4} DN");

    // Null: destriping a field that has already been destriped is a near no-op.
    let mut d2 = d0.clone();
    fpn::destripe_mean(&mut d2, g);
    let idem = d2
        .iter()
        .zip(&d0)
        .map(|(a, b)| (a - b).abs() as f64)
        .fold(0.0f64, f64::max);
    println!("null control ok: destripe_mean is idempotent to {idem:.2e} DN");

    // Isotropy readout of the synthetic field, and the anisotropy a pure row
    // pattern produces — the positive control for the anisotropy statistic.
    let s = fpn::scan(&clean, g, 4.0);
    println!(
        "synthetic field: gx2 {:.4} gy2 {:.4} aniso {:.4} row_share {:.4} col_share {:.4}",
        s.gx2, s.gy2, s.aniso, s.row_share, s.col_share
    );
    let mut rowonly = clean.clone();
    FpnPlant::new(60.0, "row", FpnStage::Sensor, 3, g)?.apply(&mut rowonly, g);
    let sr = fpn::scan(&rowonly, g, 4.0);
    println!(
        "  + 60 DN row plant: gx2 {:.4} gy2 {:.4} aniso {:.4} row_share {:.4}",
        sr.gx2, sr.gy2, sr.aniso, sr.row_share
    );
    if sr.aniso >= s.aniso * 0.9 {
        return Err("positive control FAIL: a pure row plant did not lower gx2/gy2".into());
    }
    println!("positive control ok: a pure row plant drives the anisotropy statistic down");

    println!("\nselftest PASS");
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn selftest_passes() {
        selftest().unwrap();
    }

    #[test]
    fn transpose_is_an_involution() {
        let g = PlaneGeometry {
            width: 48,
            height: 48,
        };
        let f = fpn::synthetic_texture_seeded(g, 100.0, 10.0, 11);
        assert_eq!(f, transpose(&transpose(&f, g), g));
    }

    #[test]
    fn transpose_swaps_the_gradient_axes() {
        let g = PlaneGeometry {
            width: 48,
            height: 48,
        };
        let mut f = fpn::synthetic_texture_seeded(g, 100.0, 10.0, 12);
        FpnPlant::new(30.0, "row", FpnStage::Sensor, 5, g)
            .unwrap()
            .apply(&mut f, g);
        let a = fpn::scan(&f, g, 4.0);
        let b = fpn::scan(&transpose(&f, g), g, 4.0);
        assert!(
            (a.gx2 - b.gy2).abs() / a.gx2.max(b.gy2) < 1e-4,
            "{a:?} {b:?}"
        );
        assert!(
            (a.gy2 - b.gx2).abs() / a.gy2.max(b.gx2) < 1e-4,
            "{a:?} {b:?}"
        );
    }
}
