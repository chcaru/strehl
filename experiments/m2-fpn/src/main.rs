// Experiment M4: does frame averaging actually buy sqrt(N) on this sensor?
//
// This is the go/no-go on the project's central design pillar. `strehl` claims
// that averaging N frames below the noise floor buys ~sqrt(N). That is true
// only for noise that differs every frame. A per-pixel fixed offset -- FPN --
// is identical in every frame and does not average away at all; it is a floor.
// Dark frames separate the two because they contain nothing else.
//
// Three rules this code exists to obey, all of them project rules that have
// already been broken once somewhere:
//   1. Active area only. rawler returns 7168x5120 and fills 7032x4688; the
//      rest is synthetic zeros that drag every statistic toward zero.
//   2. Spatial and temporal sd are different quantities and are never named
//      the same thing. A prior claim was retracted for exactly that confusion.
//   3. Black level is ~512 and half of every deviation is negative. Nothing is
//      clamped and black is never subtracted before a variance is taken.
//
// Modes:
//   --map <root>        folder -> ISO/exposure, metadata only, no pixel decode
//   --synthetic         estimator negative control; run this before believing
//                       anything the measurement prints
//   <root> [folders..]  the measurement

mod stats;

use rawler::decoders::RawDecodeParams;
use rawler::rawsource::RawSource;
use rayon::prelude::*;
use std::collections::{BTreeMap, HashSet};
use std::path::{Path, PathBuf};
use std::time::Instant;

use stats::*;

/// RGGB: within each 2x2 quad, R is at (0,0), G1 at (1,0), G2 at (0,1),
/// B at (1,1). Offsets are (dx, dy).
const PLANES: [(&str, usize, usize); 4] = [("R", 0, 0), ("G1", 1, 0), ("G2", 0, 1), ("B", 1, 1)];

/// Frames held in memory at once during decode. 20 planes-sets are ~63 MB each
/// (1.26 GB for a folder); each in-flight decode adds a 73 MB rawler buffer on
/// top. Eight keeps the peak near 2.5 GB, well under the 8 GB ratchet.
const DECODE_CONCURRENCY: usize = 8;

/// Frames the owner shot for stabilisation before each run, discarded on the
/// owner's explicit instruction.
const WARMUP_FRAMES: usize = 2;

#[derive(Clone, PartialEq, Eq, PartialOrd, Ord, Debug)]
struct Setting {
    iso: u32,
    /// Exposure time as the raw rational, so 1/100 stays 1/100.
    exp_n: u32,
    exp_d: u32,
}

impl std::fmt::Display for Setting {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "ISO {:<6} {}/{}s", self.iso, self.exp_n, self.exp_d)
    }
}

fn read_setting(path: &Path) -> Result<(Setting, String), String> {
    let rs = RawSource::new(path).map_err(|e| format!("{e}"))?;
    let dec = rawler::get_decoder(&rs).map_err(|e| format!("{e}"))?;
    let md = dec
        .raw_metadata(&rs, &RawDecodeParams::default())
        .map_err(|e| format!("{e}"))?;
    let iso = md
        .exif
        .iso_speed_ratings
        .map(u32::from)
        .or(md.exif.iso_speed)
        .ok_or_else(|| "no ISO tag".to_string())?;
    let (exp_n, exp_d) = md
        .exif
        .exposure_time
        .map(|r| (r.n, r.d))
        .ok_or_else(|| "no exposure time".to_string())?;
    Ok((Setting { iso, exp_n, exp_d }, md.model.clone()))
}

struct Geometry {
    pw: usize,
    ph: usize,
    active: (usize, usize, usize, usize),
    buffer: (usize, usize),
    black: [f64; 4],
}

/// One frame reduced to its four CFA planes over the active area only.
struct Frame {
    planes: [Vec<u16>; 4],
}

fn decode_planes(path: &Path) -> Result<(Frame, Geometry), String> {
    let img = rawler::decode_file(path).map_err(|e| format!("{e:?}"))?;
    let data = match img.data {
        rawler::RawImageData::Integer(d) => d,
        rawler::RawImageData::Float(_) => return Err("float raw".into()),
    };
    let stride = img.width;
    let (ax, ay, aw, ah) = img
        .active_area
        .map(|r| (r.p.x, r.p.y, r.d.w, r.d.h))
        .ok_or_else(|| "no active area".to_string())?;
    if ax % 2 != 0 || ay % 2 != 0 {
        // An odd origin would rotate the CFA phase and silently swap the plane
        // labels; refuse rather than mislabel R as G1.
        return Err(format!(
            "active origin ({ax},{ay}) is not even; CFA phase would shift"
        ));
    }
    let mut black = [0.0f64; 4];
    for (i, b) in black.iter_mut().enumerate() {
        *b = img
            .blacklevel
            .levels
            .get(i)
            .or(img.blacklevel.levels.first())
            .map(|r| r.n as f64 / r.d as f64)
            .unwrap_or(0.0);
    }

    let (pw, ph) = (aw / 2, ah / 2);
    let mut planes: [Vec<u16>; 4] = std::array::from_fn(|_| vec![0u16; pw * ph]);
    for (c, (_, dx, dy)) in PLANES.iter().enumerate() {
        let out = &mut planes[c];
        for py in 0..ph {
            let row = (ay + 2 * py + dy) * stride + ax + dx;
            let dst = &mut out[py * pw..py * pw + pw];
            for (px, o) in dst.iter_mut().enumerate() {
                *o = data[row + 2 * px];
            }
        }
    }
    Ok((
        Frame { planes },
        Geometry {
            pw,
            ph,
            active: (ax, ay, aw, ah),
            buffer: (img.width, img.height),
            black,
        },
    ))
}

fn arw_files(dir: &Path) -> Vec<PathBuf> {
    let mut v: Vec<PathBuf> = std::fs::read_dir(dir)
        .map(|rd| {
            rd.filter_map(|e| e.ok())
                .map(|e| e.path())
                .filter(|p| {
                    p.extension()
                        .and_then(|e| e.to_str())
                        .map(|e| e.eq_ignore_ascii_case("arw"))
                        .unwrap_or(false)
                })
                .collect()
        })
        .unwrap_or_default();
    v.sort();
    v
}

// ---------------------------------------------------------------- mode: map

/// One file's EXIF read: the path, and either its settings plus camera model,
/// or the reason the read failed.
type SettingRead = (PathBuf, Result<(Setting, String), String>);

fn mode_map(root: &Path) -> Vec<(String, Setting, usize)> {
    let dirs: Vec<PathBuf> = {
        let mut d: Vec<PathBuf> = std::fs::read_dir(root)
            .expect("read root")
            .filter_map(|e| e.ok())
            .map(|e| e.path())
            .filter(|p| p.is_dir())
            .collect();
        d.sort();
        d
    };

    println!(
        "folder -> setting map (MEASURED from EXIF, {} folders)",
        dirs.len()
    );
    println!(
        "{:<10} {:>5} {:>5} {:>10} {:>12}  consistency",
        "folder", "files", "used", "ISO", "exposure"
    );

    let mut out = Vec::new();
    for d in &dirs {
        let name = d.file_name().unwrap().to_string_lossy().to_string();
        let files = arw_files(d);
        let used: Vec<PathBuf> = files.iter().skip(WARMUP_FRAMES).cloned().collect();

        let settings: Vec<SettingRead> = used
            .par_iter()
            .map(|p| (p.clone(), read_setting(p)))
            .collect();

        let mut groups: BTreeMap<Setting, Vec<String>> = BTreeMap::new();
        let mut errs = Vec::new();
        for (p, r) in &settings {
            let fname = p.file_name().unwrap().to_string_lossy().to_string();
            match r {
                Ok((s, _)) => groups.entry(s.clone()).or_default().push(fname),
                Err(e) => errs.push(format!("{fname}: {e}")),
            }
        }

        // Also read the two discarded warm-up frames, to confirm they are the
        // same setting and were only stabilisation rather than a different run.
        let warm: Vec<String> = files
            .iter()
            .take(WARMUP_FRAMES)
            .map(|p| match read_setting(p) {
                Ok((s, _)) => format!("{}", s.iso),
                Err(e) => format!("ERR {e}"),
            })
            .collect();

        if groups.len() == 1 && errs.is_empty() {
            let (s, fs) = groups.iter().next().unwrap();
            let note = if warm.iter().all(|w| w == &format!("{}", s.iso)) {
                "uniform (warm-up frames match)".to_string()
            } else {
                format!("uniform; warm-up frames at ISO {warm:?}")
            };
            println!(
                "{:<10} {:>5} {:>5} {:>10} {:>10}/{:<1}  {}",
                name,
                files.len(),
                fs.len(),
                s.iso,
                s.exp_n,
                s.exp_d,
                note
            );
            out.push((name, s.clone(), fs.len()));
        } else {
            println!(
                "{:<10} {:>5} {:>5} {:>10} {:>12}  MIXED -- {} distinct settings, {} errors",
                name,
                files.len(),
                used.len(),
                "-",
                "-",
                groups.len(),
                errs.len()
            );
            for (s, fs) in &groups {
                println!("             group {s} : {} frames", fs.len());
            }
            for e in &errs {
                println!("             error {e}");
            }
            if let Some((s, fs)) = groups.iter().max_by_key(|(_, f)| f.len()) {
                out.push((name, s.clone(), fs.len()));
            }
        }
    }
    out
}

// ------------------------------------------------------------- sanity gate

struct Sanity {
    mean: f64,
    median: u16,
    min: u16,
    max: u16,
    p9999: u16,
    /// Max minus min of the 3x3 grid of cell means over the temporal mean
    /// image. A light leak or an amp glow shows up here as a gradient long
    /// before it moves the global mean.
    grid_spread: f64,
    grid: Vec<f64>,
    /// Number of samples actually accumulated. Cross-checked against
    /// `4 * pw * ph * frames` so that a geometry slip that silently let the
    /// synthetic zero padding into the statistics cannot go unnoticed.
    samples: u64,
    samples_expected: u64,
}

fn sanity(frames: &[Frame], means: &[&[f64]], g: &Geometry) -> Sanity {
    let hist = frames
        .par_iter()
        .map(|f| {
            let mut h = U16Histogram::new();
            for p in &f.planes {
                h.extend(p);
            }
            h
        })
        .reduce(U16Histogram::new, |mut a, b| {
            a.merge(&b);
            a
        });

    // 3x3 cell means of the temporal-mean image, pooled over all four planes.
    let (cw, ch) = (g.pw / 3, g.ph / 3);
    let mut grid = vec![0.0f64; 9];
    for cy in 0..3 {
        for cx in 0..3 {
            let mut s = 0.0f64;
            let mut n = 0usize;
            for m in means.iter() {
                for y in cy * ch..(cy + 1) * ch {
                    let row = &m[y * g.pw + cx * cw..y * g.pw + (cx + 1) * cw];
                    s += row.iter().sum::<f64>();
                    n += row.len();
                }
            }
            grid[cy * 3 + cx] = s / n as f64;
        }
    }
    let gmax = grid.iter().cloned().fold(f64::MIN, f64::max);
    let gmin = grid.iter().cloned().fold(f64::MAX, f64::min);

    Sanity {
        mean: hist.mean(),
        median: hist.quantile(0.5),
        min: hist.min(),
        max: hist.max(),
        p9999: hist.quantile(0.9999),
        grid_spread: gmax - gmin,
        grid,
        samples: hist.count(),
        samples_expected: 4 * (g.pw * g.ph * frames.len()) as u64,
    }
}

// ------------------------------------------------------------ per-plane run

struct PlaneResult {
    name: &'static str,
    plane_pixels: usize,
    black_meta: f64,
    mean_dn: f64,
    sigma_temporal: f64,
    sigma_temporal_mean_of_sd: f64,
    fpn: FpnEstimate,
    curve: Vec<CurvePoint>,
    slope_all: f64,
    slope_low: f64,
    departure_n: Option<usize>,
    /// spatial sd of mean(frames 10..20), and of that minus master bias 0..10
    half_plain: f64,
    half_corrected: f64,
    half_pure_temporal_prediction: f64,
    residual_fpn: Option<f64>,
    corrected_curve: Vec<CurvePoint>,
    slope_corrected: f64,
    hot: Vec<u32>,
    hot_counts: Vec<(String, usize)>,
}

fn analyse_plane(
    name: &'static str,
    frames: &[&[u16]],
    black_meta: f64,
    seed: u64,
    t: &TemporalStats,
) -> PlaneResult {
    let n = frames.len();
    assert_eq!(
        t.frames, n,
        "temporal stats were computed over a different frame count than this plane"
    );
    let fpn = fpn_bias_corrected(&t.means, t.var_pooled, n);
    let (mean_dn, _) = spatial_mean_sd(&t.means);

    let mut rng = Rng::new(seed);
    let ns: Vec<usize> = [1usize, 2, 3, 4, 6, 8, 12, 16, 20]
        .into_iter()
        .filter(|&k| k <= n)
        .collect();
    let curve = sigma_vs_n_curve(frames, &ns, &mut rng);

    let pts: Vec<(f64, f64)> = curve.iter().map(|c| (c.n as f64, c.sd)).collect();
    let (slope_all, _) = loglog_fit(&pts);
    let low: Vec<(f64, f64)> = pts.iter().cloned().filter(|p| p.0 <= 4.0).collect();
    let (slope_low, _) = loglog_fit(&low);

    // Departure: first N where the measured sd sits above the pure -0.5
    // extrapolation from N=1 by more than that point's own subset scatter.
    let sd1 = curve[0].sd;
    let departure_n = curve
        .iter()
        .skip(1)
        .find(|c| {
            let ideal = sd1 / (c.n as f64).sqrt();
            c.sd - ideal > c.scatter.max(1e-12)
        })
        .map(|c| c.n);

    // Split-half. Master bias from the first half, applied to the *disjoint*
    // second half. Correcting a half with itself would subtract that half's
    // own temporal noise and manufacture a spectacular fake result.
    let h = n / 2;
    let first: Vec<usize> = (0..h).collect();
    let second: Vec<usize> = (h..n).collect();
    let master = average_subset(frames, &first);
    let target = average_subset(frames, &second);
    let residual = subtract(&target, &master);
    let half_plain = spatial_mean_sd(&target).1;
    let half_corrected = spatial_mean_sd(&residual).1;
    // Subtracting one h-frame average from another leaves 2 * sigma_t^2 / h of
    // temporal noise even if every scrap of FPN is removed.
    let half_pure_temporal_prediction = (2.0 * t.var_pooled / h as f64).sqrt();
    let resid_var = half_corrected * half_corrected - half_pure_temporal_prediction.powi(2);
    let residual_fpn = if resid_var > 0.0 {
        Some(resid_var.sqrt())
    } else {
        None
    };

    // The same sigma-vs-N curve, but with the master bias subtracted from every
    // average. Subsets are drawn only from the second half so they never share
    // a frame with the master. This is the measurement that says whether a
    // shipped dark-frame subtraction would restore the -0.5 slope, which is the
    // whole practical question.
    let corrected_curve = sigma_vs_n_bias_subtracted(frames, &ns, &master, h);
    // The master carries sigma_t^2/h of its own noise into every point, which
    // is a constant offset, not FPN. Removing it in quadrature recovers the
    // curve a *noise-free* master would have produced.
    let master_noise_var = t.var_pooled / h as f64;
    let corrected_deconvolved: Vec<(f64, f64)> = corrected_curve
        .iter()
        .map(|c| {
            let v = c.sd * c.sd - master_noise_var;
            (c.n as f64, if v > 0.0 { v.sqrt() } else { f64::NAN })
        })
        .filter(|(_, v)| v.is_finite())
        .collect();
    let (slope_corrected, _) = loglog_fit(&corrected_deconvolved);

    // Hot pixels. The threshold must come from a robust estimator: hot pixels
    // are precisely the outliers that would drag a mean-and-sd threshold up
    // behind them. Over 8.24 M pixels a Gaussian puts <1 sample beyond 5.17
    // sigma, so 6 sigma is the smallest defensible cut.
    let (med, rsd) = median_and_robust_sd(&t.means);
    let mut hot_counts = Vec::new();
    for k in [6.0f64, 8.0, 10.0, 20.0] {
        let thr = med + k * rsd;
        let c = t.means.iter().filter(|&&m| m > thr).count();
        hot_counts.push((format!("{k:.0} sigma_robust (>{thr:.1} DN)"), c));
    }
    for d in [50.0f64, 100.0, 200.0, 500.0] {
        let thr = med + d;
        let c = t.means.iter().filter(|&&m| m > thr).count();
        hot_counts.push((format!("median+{d:.0} DN (>{thr:.1} DN)"), c));
    }
    let thr6 = med + 6.0 * rsd;
    let hot: Vec<u32> = t
        .means
        .iter()
        .enumerate()
        .filter(|(_, &m)| m > thr6)
        .map(|(i, _)| i as u32)
        .collect();

    PlaneResult {
        name,
        plane_pixels: frames[0].len(),
        black_meta,
        mean_dn,
        sigma_temporal: t.sigma(),
        sigma_temporal_mean_of_sd: t.mean_of_sd,
        fpn,
        curve,
        slope_all,
        slope_low,
        departure_n,
        half_plain,
        half_corrected,
        half_pure_temporal_prediction,
        residual_fpn,
        corrected_curve,
        slope_corrected,
        hot,
        hot_counts,
    }
}

// ---------------------------------------------------------------- reporting

fn report_plane(p: &PlaneResult, n: usize) {
    println!(
        "\n  plane {} -----------------------------------------------",
        p.name
    );
    println!(
        "    black level     : {:.1} DN measured mean, {:.1} DN declared by metadata, delta {:+.3}",
        p.mean_dn,
        p.black_meta,
        p.mean_dn - p.black_meta
    );
    println!(
        "    sigma_temporal  : {:.4} DN  (pooled sqrt of mean per-pixel variance, N={n})",
        p.sigma_temporal
    );
    println!(
        "                      {:.4} DN  (mean of per-pixel sd; biased low, not the number to quote)",
        p.sigma_temporal_mean_of_sd
    );
    print!("    sigma_FPN       : ");
    match p.fpn.sigma_fpn {
        Some(s) => println!(
            "{:.4} DN  (raw {:.4}, minus bias sigma_t^2/N = {:.4})",
            s,
            p.fpn.raw_var.sqrt(),
            p.fpn.bias
        ),
        None => println!(
            "BELOW RESOLUTION (raw var {:.4} < bias {:.4}; corrected var {:+.4})",
            p.fpn.raw_var, p.fpn.bias, p.fpn.corrected_var
        ),
    }
    if let Some(s) = p.fpn.sigma_fpn {
        println!(
            "    FPN / temporal  : {:.3}  -- averaging can remove at most a factor {:.2} before hitting the floor",
            s / p.sigma_temporal,
            p.sigma_temporal / s
        );
    }

    println!("\n    sigma vs N (spatial sd of the N-frame average):");
    println!(
        "      {:>3} {:>10} {:>9} {:>8} {:>10} {:>9}  subsets disjoint",
        "N", "sd (DN)", "scatter", "subsets", "ideal-0.5", "excess"
    );
    let sd1 = p.curve[0].sd;
    for c in &p.curve {
        let ideal = sd1 / (c.n as f64).sqrt();
        println!(
            "      {:>3} {:>10.4} {:>9.4} {:>8} {:>10.4} {:>+9.4}  {}",
            c.n,
            c.sd,
            c.scatter,
            c.subsets,
            ideal,
            c.sd - ideal,
            if c.disjoint {
                "yes"
            } else {
                "no (overlapping draws)"
            }
        );
    }
    println!(
        "    fitted slope    : {:+.4} over all N, {:+.4} over N<=4   (-0.5 == pure independent noise)",
        p.slope_all, p.slope_low
    );
    match p.departure_n {
        Some(k) => println!(
            "    departs -0.5 at : N = {k} (first N whose excess exceeds its own subset scatter)"
        ),
        None => println!("    departs -0.5 at : never, out to N = {n}"),
    }

    println!(
        "\n    split-half bias subtraction (master from frames 0..{}, applied to {}..{}):",
        n / 2,
        n / 2,
        n
    );
    println!("      un-subtracted : {:.4} DN spatial sd", p.half_plain);
    println!(
        "      bias-corrected: {:.4} DN spatial sd",
        p.half_corrected
    );
    println!(
        "      floor if all FPN were removed: {:.4} DN  (2*sigma_t^2/{} is unavoidable)",
        p.half_pure_temporal_prediction,
        n / 2
    );
    match p.residual_fpn {
        Some(r) => println!("      residual FPN  : {r:.4} DN still present after correction"),
        None => println!(
            "      residual FPN  : none resolvable -- correction reached the temporal floor"
        ),
    }
    let removed = 1.0 - p.half_corrected / p.half_plain;
    println!("      spatial sd reduction: {:.1}%", removed * 100.0);

    println!("\n    sigma vs N with that master bias subtracted (subsets from the disjoint half):");
    println!(
        "        {:>2} {:>10} {:>9} {:>8} {:>12} {:>12}",
        "N", "sd (DN)", "scatter", "subsets", "master-free", "ideal-0.5"
    );
    let master_noise = (p.sigma_temporal * p.sigma_temporal / (n / 2) as f64).sqrt();
    let first = p.corrected_curve.first().map(|c| c.sd).unwrap_or(f64::NAN);
    let first_free = (first * first - master_noise * master_noise)
        .max(0.0)
        .sqrt();
    for c in &p.corrected_curve {
        let free = (c.sd * c.sd - master_noise * master_noise).max(0.0).sqrt();
        println!(
            "        {:>2} {:>10.4} {:>9.4} {:>8} {:>12.4} {:>12.4}",
            c.n,
            c.sd,
            c.scatter,
            c.subsets,
            free,
            first_free / (c.n as f64).sqrt()
        );
    }
    println!(
        "      fitted slope after correction: {:.4}  (master's own {:.4} DN removed in quadrature)",
        p.slope_corrected, master_noise
    );

    println!("\n    hot / stuck pixel census (temporal mean above the plane's own black level):");
    let px = p.plane_pixels as f64;
    for (label, c) in &p.hot_counts {
        println!(
            "      {:<34} {:>9}  ({:.5}% of plane)",
            label,
            c,
            *c as f64 * 100.0 / px
        );
    }
}

// ------------------------------------------------------------------- driver

struct FolderResult {
    name: String,
    setting: Setting,
    frames: usize,
    sanity: Sanity,
    planes: Vec<PlaneResult>,
}

fn analyse_folder(dir: &Path, pool: &rayon::ThreadPool) -> Result<FolderResult, String> {
    let name = dir.file_name().unwrap().to_string_lossy().to_string();
    let files = arw_files(dir);
    if files.len() <= WARMUP_FRAMES {
        return Err(format!("{name}: only {} files", files.len()));
    }
    let used: Vec<PathBuf> = files.into_iter().skip(WARMUP_FRAMES).collect();

    let settings: Vec<Setting> = used
        .par_iter()
        .map(|p| read_setting(p).map(|(s, _)| s))
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| format!("{name}: {e}"))?;
    let mut groups: BTreeMap<Setting, Vec<usize>> = BTreeMap::new();
    for (i, s) in settings.iter().enumerate() {
        groups.entry(s.clone()).or_default().push(i);
    }
    if groups.len() != 1 {
        eprintln!(
            "WARNING {name}: {} distinct settings in one folder; using the largest group only",
            groups.len()
        );
        for (s, v) in &groups {
            eprintln!("  {s} : {} frames", v.len());
        }
    }
    let (setting, idx) = groups
        .into_iter()
        .max_by_key(|(_, v)| v.len())
        .ok_or_else(|| format!("{name}: no usable frames"))?;
    let chosen: Vec<PathBuf> = idx.iter().map(|&i| used[i].clone()).collect();

    let t0 = Instant::now();
    let mut geom: Option<Geometry> = None;
    let mut frames: Vec<Frame> = Vec::with_capacity(chosen.len());
    for chunk in chosen.chunks(DECODE_CONCURRENCY) {
        let decoded: Vec<(Frame, Geometry)> = pool.install(|| {
            chunk
                .par_iter()
                .map(|p| decode_planes(p).map_err(|e| format!("{}: {e}", p.display())))
                .collect::<Result<Vec<_>, _>>()
        })?;
        for (f, g) in decoded {
            if geom.is_none() {
                geom = Some(g);
            }
            frames.push(f);
        }
    }
    let g = geom.unwrap();
    let decode_s = t0.elapsed().as_secs_f64();

    let refs_for =
        |c: usize| -> Vec<&[u16]> { frames.iter().map(|f| f.planes[c].as_slice()).collect() };

    let ts = Instant::now();
    let stats: Vec<TemporalStats> = (0..4).map(|c| temporal_stats(&refs_for(c))).collect();
    eprintln!(
        "  [t] temporal_stats x4: {:.2} s",
        ts.elapsed().as_secs_f64()
    );
    let ts = Instant::now();
    let means: Vec<&[f64]> = stats.iter().map(|s| s.means.as_slice()).collect();
    let san = sanity(&frames, &means, &g);
    eprintln!("  [t] sanity: {:.2} s", ts.elapsed().as_secs_f64());

    let planes: Vec<PlaneResult> = (0..4)
        .map(|c| {
            let r = refs_for(c);
            let ts = Instant::now();
            let out = analyse_plane(
                PLANES[c].0,
                &r,
                g.black[c],
                0x4D34_5350 ^ (c as u64),
                &stats[c],
            );
            eprintln!(
                "  [t] plane {}: {:.2} s",
                PLANES[c].0,
                ts.elapsed().as_secs_f64()
            );
            out
        })
        .collect();

    println!("\n================================================================");
    println!(
        "folder {name}   {setting}   {} frames   (decode {decode_s:.1} s)",
        frames.len()
    );
    println!("================================================================");
    println!(
        "  buffer {}x{}, active {}x{} at ({},{}), plane {}x{}",
        g.buffer.0, g.buffer.1, g.active.2, g.active.3, g.active.0, g.active.1, g.pw, g.ph
    );
    println!(
        "\n  SANITY GATE (active area only, all four planes, all {} frames)",
        frames.len()
    );
    println!(
        "    mean {:.3}   median {}   min {}   max {}   p99.99 {}",
        san.mean, san.median, san.min, san.max, san.p9999
    );
    println!(
        "    {} samples counted, {} expected ({})",
        san.samples,
        san.samples_expected,
        if san.samples == san.samples_expected {
            "active area only, no zero padding"
        } else {
            "MISMATCH -- geometry is wrong, distrust everything below"
        }
    );
    println!(
        "    3x3 grid of cell means (temporal mean image), spread {:.4} DN:",
        san.grid_spread
    );
    for r in 0..3 {
        println!(
            "      {:9.3} {:9.3} {:9.3}",
            san.grid[r * 3],
            san.grid[r * 3 + 1],
            san.grid[r * 3 + 2]
        );
    }

    for p in &planes {
        report_plane(p, frames.len());
    }

    Ok(FolderResult {
        name,
        setting,
        frames: frames.len(),
        sanity: san,
        planes,
    })
}

fn mode_synthetic() {
    println!("negative control: estimators against planted parameters");
    println!("if these do not recover the plants, no number from the real data means anything\n");
    println!(
        "{:>10} {:>10} {:>4} {:>14} {:>14} {:>12} {:>12}",
        "sigma_FPN", "sigma_t", "N", "recovered FPN", "recovered t", "uncorrected", "verdict"
    );
    let px = 400_000;
    for &(sf, st, n) in &[
        (3.0f64, 8.0f64, 20usize),
        (0.5, 8.0, 20),
        (0.0, 8.0, 20),
        (10.0, 2.0, 20),
        (2.0, 20.0, 20),
        (1.0, 5.0, 10),
    ] {
        let mut rng = Rng::new(0xBEEF ^ ((sf * 1000.0) as u64) ^ ((st * 7.0) as u64));
        let fpn: Vec<f64> = (0..px).map(|_| sf * rng.normal()).collect();
        let frames: Vec<Vec<u16>> = (0..n)
            .map(|_| {
                fpn.iter()
                    .map(|f| (512.0 + f + st * rng.normal()).round().clamp(0.0, 65535.0) as u16)
                    .collect()
            })
            .collect();
        let r: Vec<&[u16]> = frames.iter().map(|f| f.as_slice()).collect();
        let t = temporal_stats(&r);
        let f = fpn_bias_corrected(&t.means, t.var_pooled, n);
        let got = f
            .sigma_fpn
            .map(|s| format!("{s:.4}"))
            .unwrap_or_else(|| "below res".into());
        let ok = match f.sigma_fpn {
            Some(s) => (s - sf).abs() < 0.15_f64.max(0.05 * sf),
            None => sf < 0.4,
        };
        println!(
            "{sf:>10.2} {st:>10.2} {n:>4} {got:>14} {:>14.4} {:>12.4} {:>12}",
            t.sigma(),
            f.raw_var.sqrt(),
            if ok { "PASS" } else { "FAIL" }
        );
    }
    println!("\n'uncorrected' is what you get by forgetting the sigma_t^2/N term.");
    println!("Note how it never returns the planted value and never returns zero.");
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() {
        eprintln!("usage:");
        eprintln!("  m2-fpn --synthetic            estimator negative control");
        eprintln!("  m2-fpn --map <root>           folder -> ISO map, metadata only");
        eprintln!("  m2-fpn <root> [folder ...]    the measurement");
        std::process::exit(2);
    }
    if args[0] == "--synthetic" {
        mode_synthetic();
        return;
    }
    if args[0] == "--map" {
        mode_map(Path::new(&args[1]));
        return;
    }

    let root = PathBuf::from(&args[0]);
    let mut dirs: Vec<PathBuf> = if args.len() > 1 {
        args[1..].iter().map(|a| root.join(a)).collect()
    } else {
        let mut d: Vec<PathBuf> = std::fs::read_dir(&root)
            .expect("read root")
            .filter_map(|e| e.ok())
            .map(|e| e.path())
            .filter(|p| p.is_dir())
            .collect();
        d.sort();
        d
    };
    dirs.sort();

    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(DECODE_CONCURRENCY)
        .build()
        .expect("thread pool");

    let t0 = Instant::now();
    let mut results = Vec::new();
    for d in &dirs {
        match analyse_folder(d, &pool) {
            Ok(r) => results.push(r),
            Err(e) => eprintln!("SKIP {e}"),
        }
    }

    summarise(&results, t0.elapsed().as_secs_f64());
}

fn summarise(unsorted: &[FolderResult], wall: f64) {
    // Sorted by ISO, not by folder. The dual-gain discontinuity is a feature of
    // the ISO axis and is invisible in capture order.
    let mut sorted: Vec<&FolderResult> = unsorted.iter().collect();
    sorted.sort_by_key(|r| r.setting.iso);
    let results = &sorted[..];

    println!("\n\n================================================================");
    println!("CROSS-ISO SUMMARY");
    println!("================================================================");

    println!("\n-- read noise vs ISO (MEASURED, DN) --");
    println!(
        "{:<10} {:>8} {:>10} {:>9} {:>9} {:>9} {:>9} {:>10}",
        "folder", "ISO", "exposure", "R", "G1", "G2", "B", "mean"
    );
    for r in results {
        let s: Vec<f64> = r.planes.iter().map(|p| p.sigma_temporal).collect();
        println!(
            "{:<10} {:>8} {:>8}/{:<1} {:>9.4} {:>9.4} {:>9.4} {:>9.4} {:>10.4}",
            r.name,
            r.setting.iso,
            r.setting.exp_n,
            r.setting.exp_d,
            s[0],
            s[1],
            s[2],
            s[3],
            s.iter().sum::<f64>() / 4.0
        );
    }

    println!("\n-- read noise in electrons, using the ASSUMED g = ISO/436.8 DN/e- (DERIVED, not measured) --");
    println!(
        "{:>8} {:>12} {:>12} {:>12}",
        "ISO", "g (DN/e-)", "sigma (DN)", "RN (e-)"
    );
    for r in results {
        let g = r.setting.iso as f64 / 436.8;
        let s: f64 = r.planes.iter().map(|p| p.sigma_temporal).sum::<f64>() / 4.0;
        println!(
            "{:>8} {:>12.5} {:>12.4} {:>12.4}",
            r.setting.iso,
            g,
            s,
            s / g
        );
    }

    println!("\n-- black level vs ISO (MEASURED mean DN per plane; metadata declares 512) --");
    println!(
        "{:>8} {:>9} {:>9} {:>9} {:>9} {:>10} {:>10}",
        "ISO", "R", "G1", "G2", "B", "declared", "max delta"
    );
    for r in results {
        let m: Vec<f64> = r.planes.iter().map(|p| p.mean_dn).collect();
        let d = m
            .iter()
            .zip(r.planes.iter())
            .map(|(x, p)| (x - p.black_meta).abs())
            .fold(0.0, f64::max);
        println!(
            "{:>8} {:>9.3} {:>9.3} {:>9.3} {:>9.3} {:>10.1} {:>10.3}",
            r.setting.iso, m[0], m[1], m[2], m[3], r.planes[0].black_meta, d
        );
    }

    println!("\n-- FPN vs ISO (MEASURED, DN; bias-corrected) --");
    println!(
        "{:>8} {:>9} {:>9} {:>9} {:>9} {:>14} {:>12} {:>14}",
        "ISO", "R", "G1", "G2", "B", "FPN/temporal", "slope(all N)", "slope(bias-sub)"
    );
    for r in results {
        let f: Vec<String> = r
            .planes
            .iter()
            .map(|p| {
                p.fpn
                    .sigma_fpn
                    .map(|s| format!("{s:.4}"))
                    .unwrap_or_else(|| "<res".into())
            })
            .collect();
        let ratio: Vec<f64> = r
            .planes
            .iter()
            .filter_map(|p| p.fpn.sigma_fpn.map(|s| s / p.sigma_temporal))
            .collect();
        let rm = if ratio.is_empty() {
            "n/a".to_string()
        } else {
            format!("{:.4}", ratio.iter().sum::<f64>() / ratio.len() as f64)
        };
        let sl = r.planes.iter().map(|p| p.slope_all).sum::<f64>() / 4.0;
        let slc = r.planes.iter().map(|p| p.slope_corrected).sum::<f64>() / 4.0;
        println!(
            "{:>8} {:>9} {:>9} {:>9} {:>9} {:>14} {:>12.4} {:>14.4}",
            r.setting.iso, f[0], f[1], f[2], f[3], rm, sl, slc
        );
    }

    println!(
        "\n-- split-half bias subtraction: how much of the floor is calibratable (MEASURED) --"
    );
    println!(
        "{:>8} {:>12} {:>12} {:>12} {:>12} {:>10}",
        "ISO", "plain sd", "corrected", "temporal floor", "resid FPN", "reduction"
    );
    for r in results {
        let pl: f64 = r.planes.iter().map(|p| p.half_plain).sum::<f64>() / 4.0;
        let co: f64 = r.planes.iter().map(|p| p.half_corrected).sum::<f64>() / 4.0;
        let fl: f64 = r
            .planes
            .iter()
            .map(|p| p.half_pure_temporal_prediction)
            .sum::<f64>()
            / 4.0;
        let rf: Vec<f64> = r.planes.iter().filter_map(|p| p.residual_fpn).collect();
        let rfs = if rf.is_empty() {
            "<res".to_string()
        } else {
            format!("{:.4}", rf.iter().sum::<f64>() / rf.len() as f64)
        };
        println!(
            "{:>8} {:>12.4} {:>12.4} {:>12.4} {:>12} {:>9.1}%",
            r.setting.iso,
            pl,
            co,
            fl,
            rfs,
            (1.0 - co / pl) * 100.0
        );
    }

    println!("\n-- hot pixels at 6 sigma_robust, and their stability across ISO (MEASURED) --");
    println!(
        "{:>8} {:>10} {:>10} {:>10} {:>10} {:>12} {:>10} {:>14}",
        "ISO", "R", "G1", "G2", "B", "total", "of ISO100", "of this ISO"
    );
    // Reference set is base ISO 100, not capture order: that is the ISO the
    // product actually shoots at.
    let base: Vec<HashSet<u32>> = results
        .iter()
        .find(|r| r.setting.iso == 100)
        .map(|r| {
            r.planes
                .iter()
                .map(|p| p.hot.iter().cloned().collect())
                .collect()
        })
        .unwrap_or_default();
    let base_total: usize = base.iter().map(|b| b.len()).sum();
    for r in results {
        let counts: Vec<usize> = r.planes.iter().map(|p| p.hot.len()).collect();
        let total: usize = counts.iter().sum();
        let shared: usize = r
            .planes
            .iter()
            .enumerate()
            .map(|(c, p)| {
                base.get(c)
                    .map(|b| p.hot.iter().filter(|i| b.contains(i)).count())
                    .unwrap_or(0)
            })
            .sum();
        println!(
            "{:>8} {:>10} {:>10} {:>10} {:>10} {:>12} {:>9.1}% {:>13.1}%",
            r.setting.iso,
            counts[0],
            counts[1],
            counts[2],
            counts[3],
            total,
            if base_total == 0 {
                0.0
            } else {
                shared as f64 * 100.0 / base_total as f64
            },
            if total == 0 {
                0.0
            } else {
                shared as f64 * 100.0 / total as f64
            }
        );
    }

    println!("\n-- sanity gate summary --");
    println!(
        "{:>8} {:>10} {:>8} {:>8} {:>8} {:>10} {:>14}",
        "ISO", "mean", "median", "min", "max", "p99.99", "3x3 spread"
    );
    for r in results {
        println!(
            "{:>8} {:>10.3} {:>8} {:>8} {:>8} {:>10} {:>14.4}",
            r.setting.iso,
            r.sanity.mean,
            r.sanity.median,
            r.sanity.min,
            r.sanity.max,
            r.sanity.p9999,
            r.sanity.grid_spread
        );
    }

    println!(
        "\n{} folders, {} frames analysed, {wall:.1} s wall",
        results.len(),
        results.iter().map(|r| r.frames).sum::<usize>()
    );
}
