//! M23 — per-edge response calibration ("metacalibration") of short alignment
//! edges. Rust half copied **verbatim** from `experiments/m12-shrinkage`
//! (itself a verbatim copy of `experiments/m10-deep-align`); neither M10's nor
//! M12's directory is modified. The only delta is the added `metacal` mode
//! (`run_metacal`) and its `main` dispatch arm — every other line, including
//! the estimator in `align.rs`, is byte-identical to M12's.
//!
//! Reusing the estimator unmodified is a **consistency check, not independent
//! evidence** (SYNTHESIS §5 discipline 34): if M23 reproduces M10 fact 45's
//! numbers it shows the two analyses agree about one harness, not that the
//! harness is right.
//!
//! M12 — short-baseline magnification shrinkage. Rust half copied verbatim
//! from `experiments/m10-deep-align` (crate renamed only); M10 is not modified.
//!
//! M10 — deep-stack alignment. The Rust half: it produces a **sparse pairwise
//! edge set** over a stack, and nothing else.
//!
//! Every edge is a similarity fitted **directly** between the two frames of its
//! own pair. Nothing here composes one measurement into another, so AGENTS.md
//! rule 6 is untouched by the measurement itself; the strategies that *do*
//! compose (chain, ladder, bundle adjustment) live in the Python half and are
//! scored against these edges.
//!
//! ```text
//!   m12-shrinkage synthetic  <dir-of-ARW>
//!   m12-shrinkage edges      <dir-of-ARW> <out-prefix> --case NAME [opts]
//!   m12-shrinkage synth      <dir-of-ARW> <out-prefix> --case NAME [opts]
//! ```

mod align;
mod field;
mod plane;
mod synth;

use align::{align_with, build_pyramid, compose, tile_grid_m, AlignCfg, Fit, Pyramid, Stage};
use plane::{green_plane, Plane};
use rayon::prelude::*;
use std::collections::BTreeSet;
use std::io::Write;
use std::path::PathBuf;
use std::time::Instant;

fn arg_val(args: &[String], key: &str) -> Option<String> {
    args.iter()
        .position(|a| a == key)
        .and_then(|i| args.get(i + 1))
        .cloned()
}

fn has_flag(args: &[String], key: &str) -> bool {
    args.iter().any(|a| a == key)
}

fn parse_list(s: &str) -> Vec<usize> {
    s.split(',')
        .filter_map(|t| t.trim().parse::<usize>().ok())
        .filter(|d| *d > 0)
        .collect()
}

fn cfg_by_name(name: &str) -> AlignCfg {
    match name {
        "m3" => AlignCfg::m3(),
        "wide" => AlignCfg::wide(),
        "wide64" => AlignCfg::wide64(),
        _ => AlignCfg::m10(),
    }
}

fn load_planes(dir: &str, limit: usize) -> Vec<Plane> {
    let mut paths: Vec<PathBuf> = std::fs::read_dir(dir)
        .unwrap_or_else(|e| panic!("read_dir {dir}: {e}"))
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| {
            p.extension()
                .map(|e| e.eq_ignore_ascii_case("arw"))
                .unwrap_or(false)
        })
        .collect();
    paths.sort();
    paths.truncate(limit);
    assert!(!paths.is_empty(), "no ARW files in {dir}");
    let t0 = Instant::now();
    let planes: Vec<Plane> = paths
        .par_iter()
        .map(|p| green_plane(p).unwrap_or_else(|e| panic!("{}: {e}", p.display())))
        .collect();
    let ms = t0.elapsed().as_secs_f64() * 1e3;
    eprintln!(
        "decoded {} frames to {}x{} green planes in {:.0} ms ({:.1} ms/frame)",
        planes.len(),
        planes[0].w,
        planes[0].h,
        ms,
        ms / planes.len() as f64
    );
    planes
}

fn pair_set(n: usize, spans: &[usize], direct0: bool) -> Vec<(usize, usize)> {
    let mut set: BTreeSet<(usize, usize)> = BTreeSet::new();
    for &s in spans {
        if s >= n {
            continue;
        }
        for i in 0..n - s {
            set.insert((i, i + s));
        }
    }
    if direct0 {
        for j in 1..n {
            set.insert((0, j));
        }
    }
    set.into_iter().collect()
}

const EDGE_HEADER: &str = "case,cfg,ref,mov,span,status,g,rot,ax,ay,rms,used,raw_n,total,lever_rms,peak_mean,plane_w,plane_h";

fn edge_row(
    case: &str,
    cfgname: &str,
    i: usize,
    j: usize,
    st: &Option<Stage>,
    pw: usize,
    ph: usize,
) -> String {
    match st {
        Some(s) => format!(
            "{case},{cfgname},{i},{j},{},ok,{:.9},{:.9},{:.6},{:.6},{:.6},{},{},{},{:.2},{:.5},{pw},{ph}",
            j - i,
            s.fit.g,
            s.fit.r,
            s.fit.ax,
            s.fit.ay,
            s.rms,
            s.used,
            s.raw_n,
            s.total,
            s.lever_rms,
            s.peak_mean
        ),
        None => format!(
            "{case},{cfgname},{i},{j},{},nofit,,,,,,0,0,0,,,{pw},{ph}",
            j - i
        ),
    }
}

/// Measure every requested pair and write one row each, failures included.
#[allow(clippy::too_many_arguments)]
fn measure_edges(
    case: &str,
    cfgname: &str,
    cfg: &AlignCfg,
    planes: &[Plane],
    pairs: &[(usize, usize)],
    out: &mut std::io::BufWriter<std::fs::File>,
) {
    let n = planes.len();
    let (pw, ph) = (planes[0].w, planes[0].h);
    eprintln!(
        "[{case}/{cfgname}] building pyramids at {:?} for {n} frames",
        cfg.coarse_factors
    );
    let t0 = Instant::now();
    let pyr: Vec<Pyramid> = planes.par_iter().map(|p| build_pyramid(p, cfg)).collect();
    eprintln!(
        "[{case}/{cfgname}] pyramids in {:.2} s",
        t0.elapsed().as_secs_f64()
    );

    let spots = tile_grid_m(
        &planes[0],
        cfg.fine_tile,
        cfg.fine_grid.0,
        cfg.fine_grid.1,
        cfg.margin,
    )
    .expect("plane too small for the anchor grid");
    eprintln!(
        "[{case}/{cfgname}] anchor grid {}x{} tile {} margin {} -> {} spots",
        cfg.fine_grid.0,
        cfg.fine_grid.1,
        cfg.fine_tile,
        cfg.margin,
        spots.len()
    );

    let t1 = Instant::now();
    let done = std::sync::atomic::AtomicUsize::new(0);
    let total = pairs.len();
    let rows: Vec<String> = pairs
        .par_iter()
        .map(|&(i, j)| {
            let st = align_with(&pyr[i], &pyr[j], &planes[i], &planes[j], &spots, cfg);
            let k = done.fetch_add(1, std::sync::atomic::Ordering::Relaxed) + 1;
            if k.is_multiple_of(100) {
                eprintln!(
                    "[{case}/{cfgname}] {k}/{total} pairs, {:.1} s elapsed",
                    t1.elapsed().as_secs_f64()
                );
            }
            edge_row(case, cfgname, i, j, &st, pw, ph)
        })
        .collect();
    let secs = t1.elapsed().as_secs_f64();
    let nofit = rows.iter().filter(|r| r.contains(",nofit,")).count();
    eprintln!(
        "[{case}/{cfgname}] {total} pairs in {secs:.1} s ({:.1} ms/pair); {nofit} no-fit",
        secs / total as f64 * 1e3
    );
    for r in rows {
        let _ = writeln!(out, "{r}");
    }
}

/// `P1`: the estimator control. M3 §0's four known warps, through this crate's
/// ported estimator. SYNTHESIS §5 item 15 -- reproduce a published number before
/// trusting a re-implementation.
fn run_synthetic(dir: &str) {
    let planes = load_planes(dir, 1);
    let base = &planes[0];

    let step = Fit {
        ax: 0.0,
        ay: 0.0,
        g: -0.001,
        r: 0.0,
    };
    let n = 21;
    let got = compose(&vec![step; n]).g as f64;
    let want = (1.0f64 - 0.001).powi(n as i32) - 1.0;
    println!(
        "compose() self-check: {got:.9} vs closed form {want:.9} (err {:.2e})",
        (got - want).abs()
    );

    let cases = [
        (
            "pure translation",
            Fit {
                ax: 3.7,
                ay: -2.4,
                g: 0.0,
                r: 0.0,
            },
        ),
        (
            "scale only -1.0%",
            Fit {
                ax: 0.0,
                ay: 0.0,
                g: -0.0100,
                r: 0.0,
            },
        ),
        (
            "scale+trans+rot",
            Fit {
                ax: -5.25,
                ay: 1.75,
                g: -0.00512,
                r: 0.00031,
            },
        ),
        (
            "tiny scale -0.05%",
            Fit {
                ax: 0.0,
                ay: 0.0,
                g: -0.0005,
                r: 0.0,
            },
        ),
    ];

    let radius = base.corner_radius();
    for cfgname in ["m3", "m10"] {
        let cfg = cfg_by_name(cfgname);
        let spots = tile_grid_m(
            base,
            cfg.fine_tile,
            cfg.fine_grid.0,
            cfg.fine_grid.1,
            cfg.margin,
        )
        .expect("grid");
        let bp = build_pyramid(base, &cfg);
        println!(
            "\n=== synthetic control, cfg={cfgname} (margin {}) ===",
            cfg.margin
        );
        let mut worst_g = 0f64;
        for (name, truth) in cases {
            let m = warp_known(base, truth);
            let mp = build_pyramid(&m, &cfg);
            match align_with(&bp, &mp, base, &m, &spots, &cfg) {
                Some(s) => {
                    let f = s.fit;
                    let eg = (f.g - truth.g) as f64;
                    worst_g = worst_g.max(eg.abs());
                    println!(
                        "{name:>18}: ax {:+8.3} (err {:+.3})  ay {:+8.3} (err {:+.3})  \
                         g {:+.6} (err {:+.6})  r {:+.6} (err {:+.6})  rms {:.3} px  {}/{} tiles",
                        f.ax,
                        f.ax - truth.ax,
                        f.ay,
                        f.ay - truth.ay,
                        f.g,
                        eg,
                        f.r,
                        f.r - truth.r,
                        s.rms,
                        s.used,
                        s.total
                    );
                }
                None => println!("{name:>18}: FAILED"),
            }
        }
        println!(
            "worst scale error {:.2e} = {:.3} px at the plane corner (radius {:.0} px)",
            worst_g,
            worst_g * radius,
            radius
        );
    }
}

fn warp_known(rf: &Plane, truth: Fit) -> Plane {
    let (cx, cy) = (rf.w as f32 * 0.5, rf.h as f32 * 0.5);
    let mut out = vec![0f32; rf.w * rf.h];
    let w = rf.w;
    out.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
        for (x, o) in row.iter_mut().enumerate() {
            let (sx, sy) = truth.inv_at(x as f32, y as f32, cx, cy);
            *o = plane::bilinear(rf, sx, sy);
        }
    });
    Plane {
        d: out,
        w: rf.w,
        h: rf.h,
    }
}

/// `P1b`: the estimator's **corner-error floor**, as a distribution rather than
/// as four hand-picked cases, and as a function of the anchor margin.
///
/// This is the yardstick every held-out number in M10 is compared against, and
/// it is also how the anchor margin is chosen: on a 105-frame stack the corner
/// drift reaches 89 plane px (M6 fact 32), so a 10 px margin loses its corner
/// tiles to the search window falling off the plane, while a large margin
/// shortens the lever arm the scale estimate rests on. The trade is measured,
/// not guessed.
///
/// **Resampler disclosure**: the planted warps are bilinear, so this floor
/// includes whatever the resampler contributes. It is a recovery control.
fn run_floor(args: &[String]) {
    let dir = &args[2];
    let prefix = &args[3];
    let case = arg_val(args, "--case").unwrap_or_else(|| "floor".into());
    let margins = parse_list(&arg_val(args, "--margins").unwrap_or_else(|| "10,32,64,96".into()));
    let cfgnames: Vec<String> = arg_val(args, "--cfgs")
        .unwrap_or_else(|| "m10".into())
        .split(',')
        .map(|s| s.trim().to_string())
        .collect();
    let frames: Vec<usize> = arg_val(args, "--frames")
        .unwrap_or_else(|| "0".into())
        .split(',')
        .filter_map(|s| s.trim().parse().ok())
        .collect();
    let nwarp: usize = arg_val(args, "--n")
        .and_then(|s| s.parse().ok())
        .unwrap_or(24);

    let want = frames.iter().copied().max().unwrap_or(0) + 1;
    let planes = load_planes(dir, want);

    // Planted warps covering the real inter-frame range: g from 0 to -5%,
    // translation to +/-3 px, rotation to +/-1e-4 (M3 §2's measured bound).
    let mut rng = synth::Rng(0x4D31_3046_4C4F_4F52);
    let warps: Vec<Fit> = (0..nwarp)
        .map(|i| {
            let t = (i as f32 + 0.5) / nwarp as f32;
            Fit {
                ax: 3.0 * rng.normal().clamp(-1.0, 1.0),
                ay: 3.0 * rng.normal().clamp(-1.0, 1.0),
                g: -0.05 * t,
                r: 1.0e-4 * rng.normal().clamp(-1.0, 1.0),
            }
        })
        .collect();

    let path = format!("data/{prefix}-floor.csv");
    let mut out = std::io::BufWriter::new(std::fs::File::create(&path).expect("create floor csv"));
    let _ = writeln!(
        out,
        "case,cfg,base_frame,warp_id,margin,g_true,rot_true,ax_true,ay_true,g,rot,ax,ay,corner_err,rms,used,total"
    );

    for &fi in &frames {
        let base = &planes[fi];
        let (pw, ph) = (base.w, base.h);
        let warped: Vec<Plane> = warps.iter().map(|t| warp_known(base, *t)).collect();
        for cfgname in &cfgnames {
            for &margin in &margins {
                let mut cfg = cfg_by_name(cfgname);
                cfg.margin = margin;
                let spots = tile_grid_m(
                    base,
                    cfg.fine_tile,
                    cfg.fine_grid.0,
                    cfg.fine_grid.1,
                    margin,
                )
                .expect("grid");
                let bp = build_pyramid(base, &cfg);
                let rows: Vec<String> = warped
                    .par_iter()
                    .enumerate()
                    .map(|(wi, m)| {
                        let mp = build_pyramid(m, &cfg);
                        let t = warps[wi];
                        match align_with(&bp, &mp, base, m, &spots, &cfg) {
                            Some(s) => format!(
                                "{case},{cfgname},{fi},{wi},{margin},{:.9},{:.9},{:.6},{:.6},{:.9},{:.9},{:.6},{:.6},{:.6},{:.6},{},{}",
                                t.g, t.r, t.ax, t.ay,
                                s.fit.g, s.fit.r, s.fit.ax, s.fit.ay,
                                align::corner_err(&s.fit, &t, pw, ph), s.rms, s.used, s.total
                            ),
                            None => format!(
                                "{case},{cfgname},{fi},{wi},{margin},{:.9},{:.9},{:.6},{:.6},,,,,,,0,0",
                                t.g, t.r, t.ax, t.ay
                            ),
                        }
                    })
                    .collect();
                eprintln!(
                    "[{case}] base {fi} cfg {cfgname} margin {margin}: {} warps done",
                    rows.len()
                );
                for r in rows {
                    let _ = writeln!(out, "{r}");
                }
            }
        }
    }
    let _ = out.flush();
    eprintln!("wrote {path}");
}

fn run_edges(args: &[String]) {
    let dir = &args[2];
    let prefix = &args[3];
    let case = arg_val(args, "--case").unwrap_or_else(|| "case".into());
    let cfgnames: Vec<String> = arg_val(args, "--cfg")
        .unwrap_or_else(|| "m10".into())
        .split(',')
        .map(|s| s.trim().to_string())
        .collect();
    let spans = parse_list(&arg_val(args, "--spans").unwrap_or_else(|| "1,2,4,8,16,32".into()));
    let direct0 = has_flag(args, "--direct0");
    let limit: usize = arg_val(args, "--limit")
        .and_then(|s| s.parse().ok())
        .unwrap_or(usize::MAX);

    let planes = load_planes(dir, limit);
    let pairs = pair_set(planes.len(), &spans, direct0);
    eprintln!(
        "[{case}] {} frames, spans {:?}, direct0 {}, {} pairs",
        planes.len(),
        spans,
        direct0,
        pairs.len()
    );

    let path = format!("data/{prefix}-edges.csv");
    let mut out = std::io::BufWriter::new(std::fs::File::create(&path).expect("create edges csv"));
    let _ = writeln!(out, "{EDGE_HEADER}");
    for cfgname in &cfgnames {
        let cfg = cfg_by_name(cfgname);
        measure_edges(&case, cfgname, &cfg, &planes, &pairs, &mut out);
    }
    let _ = out.flush();
    eprintln!("wrote {path}");
}

fn run_synth(args: &[String]) {
    let dir = &args[2];
    let prefix = &args[3];
    let case = arg_val(args, "--case").unwrap_or_else(|| "synth".into());
    let n: usize = arg_val(args, "--n")
        .and_then(|s| s.parse().ok())
        .unwrap_or(105);
    let flavour = match arg_val(args, "--flavour")
        .unwrap_or_else(|| "warp".into())
        .as_str()
    {
        "integer" => synth::Flavour::IntegerShift,
        _ => synth::Flavour::Warp,
    };
    let spans = parse_list(&arg_val(args, "--spans").unwrap_or_else(|| "1,2,4,8,16,32".into()));
    let direct0 = has_flag(args, "--direct0");
    let cfgname = arg_val(args, "--cfg").unwrap_or_else(|| "m10".into());

    let base = load_planes(dir, 1);
    let g_total: f32 = arg_val(args, "--g-total")
        .and_then(|s| s.parse().ok())
        .unwrap_or(-0.04575);
    let curve: f32 = arg_val(args, "--curve")
        .and_then(|s| s.parse().ok())
        .unwrap_or(1.6);
    let spec = synth::SynthSpec {
        n,
        flavour,
        // Default matches coffee-bean's measured total drift (M6 fact 32:
        // -4.575%). M12 overrides it with the *measured* total of whichever
        // real stack the null is standing in for, so that the planted
        // per-frame differential displacement matches the real one and the
        // control is not answering an easier question than the treatment.
        g_total,
        curve,
        g_wobble: 2.0e-5,
        t_wobble: 0.05,
        // M3 §5's measured scale centre, in plane px from the plane centre.
        centre: (-11.0, -56.0),
        rot_total: 6.0e-5,
        blur_per_frame: 0.11,
        gain: 1.0,
        rn_e: 4.2,
        seed: 0x5354_5245_484C_4D31,
    };
    eprintln!("[{case}] building depth field and {n} synthetic frames");
    let t0 = Instant::now();
    let depth = synth::depth_field(base[0].w, base[0].h, n);
    let planes = synth::synth_stack(&base[0], &depth, &spec);
    eprintln!(
        "[{case}] synthesised in {:.1} s",
        t0.elapsed().as_secs_f64()
    );

    let tpath = format!("data/{prefix}-truth.csv");
    let mut tf = std::io::BufWriter::new(std::fs::File::create(&tpath).expect("create truth csv"));
    let _ = writeln!(tf, "case,frame,g,rot,ax,ay");
    for k in 0..n {
        let f = synth::truth_fit(&spec, k);
        let _ = writeln!(
            tf,
            "{case},{k},{:.9},{:.9},{:.6},{:.6}",
            f.g, f.r, f.ax, f.ay
        );
    }
    let _ = tf.flush();
    eprintln!("wrote {tpath}");

    let pairs = pair_set(n, &spans, direct0);
    let path = format!("data/{prefix}-edges.csv");
    let mut out = std::io::BufWriter::new(std::fs::File::create(&path).expect("create edges csv"));
    let _ = writeln!(out, "{EDGE_HEADER}");
    let cfg = cfg_by_name(&cfgname);
    measure_edges(&case, &cfgname, &cfg, &planes, &pairs, &mut out);
    let _ = out.flush();
    eprintln!("wrote {path}");
}

/// `P6`: is a **small** scale change recovered without shrinkage?
///
/// The scale-rate ladder measured on real stacks says a span-1 edge reports a
/// per-frame magnification rate 3.3x smaller than a span-32 edge does. Two very
/// different mechanisms could produce that, and they have opposite engineering
/// consequences:
///
/// * the **estimator** shrinks any sub-pixel differential displacement toward
///   zero (pixel locking, M3 fact 12), in which case no short-edge strategy can
///   ever work and the fix must be to use long edges; or
/// * the **content** differs — consecutive frames differ by a small defocus
///   step, and M6 showed defocus biases correlation — in which case the fix is
///   a better estimator, not a different graph.
///
/// This separates them. Both frames are point samples of the same continuous
/// band-limited field, so there is no defocus difference, no interpolator, and
/// no resampling anywhere: any shrinkage found here is the estimator's own.
///
/// Two arms are run. `field` is the resampler-free arm. `resample` plants the
/// same warps by bilinearly resampling a real frame, and exists only to show
/// what the trap looks like when you do fall into it.
fn run_lock(args: &[String]) {
    let prefix = &args[2];
    let cfgnames: Vec<String> = arg_val(args, "--cfgs")
        .unwrap_or_else(|| "m10,wide64".into())
        .split(',')
        .map(|s| s.trim().to_string())
        .collect();
    let reps: usize = arg_val(args, "--reps")
        .and_then(|s| s.parse().ok())
        .unwrap_or(12);
    let noise: f32 = arg_val(args, "--noise")
        .and_then(|s| s.parse().ok())
        .unwrap_or(4.2);
    let real_dir = arg_val(args, "--resample-from");

    let (w, h) = (3516usize, 2344usize);
    let mags: Vec<f32> = vec![
        -1.0e-4, -2.0e-4, -4.0e-4, -8.0e-4, -1.6e-3, -3.2e-3, -6.4e-3, -1.28e-2, -2.56e-2, -5.12e-2,
    ];

    let path = format!("data/{prefix}-lock.csv");
    let mut out = std::io::BufWriter::new(std::fs::File::create(&path).expect("create lock csv"));
    let _ = writeln!(
        out,
        "arm,cfg,rep,g_true,ax_true,ay_true,g,rot,ax,ay,ratio,corner_err,rms,used,total"
    );

    let real: Option<Plane> = real_dir.as_ref().map(|d| {
        let p = load_planes(d, 1);
        p.into_iter().next().expect("no frame to resample")
    });

    for cfgname in &cfgnames {
        let cfg = cfg_by_name(cfgname);
        let spots = tile_grid_m(
            &Plane { d: vec![], w, h },
            cfg.fine_tile,
            cfg.fine_grid.0,
            cfg.fine_grid.1,
            cfg.margin,
        )
        .expect("grid");
        for rep in 0..reps {
            let fld = field::Field::new(384, 1.0 / 220.0, 1.0 / 2.6, 0xF1E1D0 ^ (rep as u64));
            let rf = fld.render(w, h, None, 900.0, 3000.0, noise, 0x51_u64 ^ (rep as u64));
            let rp = build_pyramid(&rf, &cfg);
            let rows: Vec<String> = mags
                .par_iter()
                .map(|&g| {
                    let mut r2 = synth::Rng(0xB0B ^ ((rep as u64) << 8) ^ g.to_bits() as u64);
                    let t = Fit {
                        g,
                        r: 0.0,
                        ax: 2.0 * r2.normal(),
                        ay: 2.0 * r2.normal(),
                    };
                    let mut lines = Vec::new();
                    let mv = fld.render(w, h, Some(t), 900.0, 3000.0, noise, 0x52_u64 ^ (rep as u64));
                    let mp = build_pyramid(&mv, &cfg);
                    lines.push(match align_with(&rp, &mp, &rf, &mv, &spots, &cfg) {
                        Some(s) => format!(
                            "field,{cfgname},{rep},{:.9},{:.6},{:.6},{:.9},{:.9},{:.6},{:.6},{:.6},{:.6},{:.6},{},{}",
                            t.g, t.ax, t.ay, s.fit.g, s.fit.r, s.fit.ax, s.fit.ay,
                            s.fit.g / t.g, align::corner_err(&s.fit, &t, w, h), s.rms, s.used, s.total
                        ),
                        None => format!(
                            "field,{cfgname},{rep},{:.9},{:.6},{:.6},,,,,,,,0,0",
                            t.g, t.ax, t.ay
                        ),
                    });
                    if let Some(rr) = real.as_ref() {
                        let mv2 = warp_known(rr, t);
                        let rp2 = build_pyramid(rr, &cfg);
                        let mp2 = build_pyramid(&mv2, &cfg);
                        lines.push(match align_with(&rp2, &mp2, rr, &mv2, &spots, &cfg) {
                            Some(s) => format!(
                                "resample,{cfgname},{rep},{:.9},{:.6},{:.6},{:.9},{:.9},{:.6},{:.6},{:.6},{:.6},{:.6},{},{}",
                                t.g, t.ax, t.ay, s.fit.g, s.fit.r, s.fit.ax, s.fit.ay,
                                s.fit.g / t.g, align::corner_err(&s.fit, &t, rr.w, rr.h), s.rms, s.used, s.total
                            ),
                            None => format!(
                                "resample,{cfgname},{rep},{:.9},{:.6},{:.6},,,,,,,,0,0",
                                t.g, t.ax, t.ay
                            ),
                        });
                    }
                    lines.join("\n")
                })
                .collect();
            eprintln!("[lock/{cfgname}] rep {rep} done");
            for r in rows {
                let _ = writeln!(out, "{r}");
            }
        }
    }
    let _ = out.flush();
    eprintln!("wrote {path}");
}

/// `P7`: the mechanism test — does the estimator shrink a **known increment**
/// on a **real, defocus-mismatched** pair?
///
/// The conservation test shows that telescoping span-1 edges across
/// `coffee-bean` accounts for only about a third of the magnification change
/// that span-16 and longer edges agree on. Something is shrinking the short
/// edges. This isolates where.
///
/// For a real pair `(i, i+s)`, fit it to get `F0`. Then plant a known extra
/// similarity `W` on the moving frame and fit again to get `F1`. The recovered
/// increment is `F1 o F0^-1`, and it should equal `W` whatever `s` is. The
/// defocus mismatch, the tile dropout and the content overlap are all *held
/// fixed* between the two fits, so they cancel: only the estimator's response
/// to a small geometric change survives.
///
/// If the recovered increment is faithful at every span, the estimator is
/// locally unbiased on real defocus-mismatched content, and the ladder is not
/// an estimator artefact. If the increment is shrunk at short span, it is.
fn run_increment(args: &[String]) {
    let dir = &args[2];
    let prefix = &args[3];
    let cfgnames: Vec<String> = arg_val(args, "--cfgs")
        .unwrap_or_else(|| "m10,wide64".into())
        .split(',')
        .map(|s| s.trim().to_string())
        .collect();
    let spans = parse_list(&arg_val(args, "--spans").unwrap_or_else(|| "1,2,4,8,16,32".into()));
    let bases = parse_list(&arg_val(args, "--frames").unwrap_or_else(|| "0,20,40,60".into()));
    let mags: Vec<f32> = arg_val(args, "--mags")
        .unwrap_or_else(|| "0.0002,-0.0002,0.001,-0.001,0.004,-0.004".into())
        .split(',')
        .filter_map(|s| s.trim().parse().ok())
        .collect();

    let need = spans.iter().max().copied().unwrap_or(1) + bases.iter().max().copied().unwrap_or(0);
    let planes = load_planes(dir, need + 1);

    let path = format!("data/{prefix}-increment.csv");
    let mut out = std::io::BufWriter::new(std::fs::File::create(&path).expect("create csv"));
    let _ = writeln!(
        out,
        "cfg,base,span,g_plant,g_inc,ratio,rot_inc,ax_inc,ay_inc,rms0,used0,rms1,used1"
    );

    for cfgname in &cfgnames {
        let cfg = cfg_by_name(cfgname);
        let spots = tile_grid_m(
            &planes[0],
            cfg.fine_tile,
            cfg.fine_grid.0,
            cfg.fine_grid.1,
            cfg.margin,
        )
        .expect("grid");
        for &b in &bases {
            for &s in &spans {
                if b + s >= planes.len() {
                    continue;
                }
                let rf = &planes[b];
                let mv = &planes[b + s];
                let rp = build_pyramid(rf, &cfg);
                let mp = build_pyramid(mv, &cfg);
                let f0 = match align_with(&rp, &mp, rf, mv, &spots, &cfg) {
                    Some(s) => s,
                    None => continue,
                };
                let rows: Vec<String> = mags
                    .par_iter()
                    .map(|&gp| {
                        let w = Fit {
                            g: gp,
                            r: 0.0,
                            ax: 0.0,
                            ay: 0.0,
                        };
                        let mv2 = warp_known(mv, w);
                        let mp2 = build_pyramid(&mv2, &cfg);
                        match align_with(&rp, &mp2, rf, &mv2, &spots, &cfg) {
                            Some(s1) => {
                                // increment = F1 o F0^-1, in the (a, b) algebra
                                let (a0, a1) = (
                                    (1.0 + f0.fit.g, f0.fit.r),
                                    (1.0 + s1.fit.g, s1.fit.r),
                                );
                                let den = a0.0 * a0.0 + a0.1 * a0.1;
                                let inc = (
                                    (a1.0 * a0.0 + a1.1 * a0.1) / den,
                                    (a1.1 * a0.0 - a1.0 * a0.1) / den,
                                );
                                let g_inc = inc.0 - 1.0;
                                format!(
                                    "{cfgname},{b},{s},{gp:.9},{g_inc:.9},{:.6},{:.9},{:.6},{:.6},{:.4},{},{:.4},{}",
                                    g_inc / gp, inc.1,
                                    s1.fit.ax - f0.fit.ax, s1.fit.ay - f0.fit.ay,
                                    f0.rms, f0.used, s1.rms, s1.used
                                )
                            }
                            None => format!(
                                "{cfgname},{b},{s},{gp:.9},,,,,,{:.4},{},,0",
                                f0.rms, f0.used
                            ),
                        }
                    })
                    .collect();
                for r in rows {
                    let _ = writeln!(out, "{r}");
                }
                eprintln!("[inc/{cfgname}] base {b} span {s} done ({} tiles)", f0.used);
            }
        }
    }
    let _ = out.flush();
    eprintln!("wrote {path}");
}

/// `M12-F`: where the in-focus band sits, per frame, measured from the pixels.
///
/// The briefing's "the physical step differs by ~78/62" was retracted as an
/// arithmetic identity (`span/(n−1)`), and M12 §4.1's refutation of fact 49
/// rests on **magnification**, which is only a *proxy* for focus position. This
/// mode supplies an independent observable that needs no metadata, no
/// `span/(n−1)`, and no assumption about the magnification-vs-distance map:
/// the frame index at which each scene tile is sharpest.
///
/// Regressing tile-wise `p_112` on `p_113` separates the two hypotheses
/// cleanly — slope `78/62 = 1.2581` if the two sweeps cover one interval at two
/// densities, slope `1.0000` if they share a per-frame step and 112 simply runs
/// further. The depth→focus map is a property of the subject and cancels,
/// including a nonlinear motor-unit-to-distance map.
///
/// **The `(0,j)` fits are book-keeping, not statistic.** They keep a tile on the
/// same scene content as the frame drifts (~78 plane px over a full sweep,
/// against a 96 px window). `--frozen` repeats the whole measurement with the
/// grid nailed down, as the registered F5 arm.
///
/// **No resampling anywhere**: the mapped tile centre is rounded to the nearest
/// integer pixel. A sub-pixel placement error is irrelevant to a sharpness
/// integral over 96×96 and would otherwise import the resampler this project
/// spent M10 fact 45 ruling out.
fn run_focus(args: &[String]) {
    let dir = &args[2];
    let prefix = &args[3];
    let case = arg_val(args, "--case").unwrap_or_else(|| "case".into());
    let cfg = cfg_by_name(&arg_val(args, "--cfg").unwrap_or_else(|| "m10".into()));
    let tile: usize = arg_val(args, "--tile")
        .and_then(|s| s.parse().ok())
        .unwrap_or(96);
    let stride: usize = arg_val(args, "--stride")
        .and_then(|s| s.parse().ok())
        .unwrap_or(96);
    let margin: usize = arg_val(args, "--fmargin")
        .and_then(|s| s.parse().ok())
        .unwrap_or(160);
    let frozen = has_flag(args, "--frozen");
    let step: usize = arg_val(args, "--step")
        .and_then(|s| s.parse().ok())
        .unwrap_or(1);
    let phase: usize = arg_val(args, "--phase")
        .and_then(|s| s.parse().ok())
        .unwrap_or(0);
    let limit: usize = arg_val(args, "--limit")
        .and_then(|s| s.parse().ok())
        .unwrap_or(usize::MAX);

    let all = load_planes(dir, limit);
    let synth_g: Option<f32> = arg_val(args, "--synth-scale").and_then(|s| s.parse().ok());
    let synth_n: usize = arg_val(args, "--synth-n")
        .and_then(|s| s.parse().ok())
        .unwrap_or(79);

    // F1, the registered null: replace the stack with `synth_n` warped copies of
    // its own first frame, carrying the *same* total magnification drift as the
    // real sweep but no focus change whatever. If the sharpness peak is reading
    // focus, almost no tile should survive the acceptance rules here; if it is
    // reading scale or drift, this stack will look like a real one.
    let synth: Vec<Plane> = match synth_g {
        Some(g) => {
            let base = &all[0];
            (0..synth_n)
                .map(|j| {
                    let f = j as f32 / (synth_n - 1) as f32;
                    warp_known(
                        base,
                        Fit {
                            ax: 0.0,
                            ay: 0.0,
                            g: g * f,
                            r: 0.0,
                        },
                    )
                })
                .collect()
        }
        None => Vec::new(),
    };
    let source: Vec<&Plane> = if synth.is_empty() {
        all.iter().collect()
    } else {
        eprintln!(
            "[{case}] SYNTH NULL: {synth_n} warped copies of frame 0, g_total {}",
            synth_g.unwrap()
        );
        synth.iter().collect()
    };
    let planes: Vec<&Plane> = source.into_iter().skip(phase).step_by(step).collect();
    let n = planes.len();
    let (pw, ph) = (planes[0].w, planes[0].h);
    eprintln!("[{case}] {n} frames (step {step} phase {phase}), frozen {frozen}");

    // Direct (0,j) similarities, so a tile centre can follow its scene content.
    let fits: Vec<Fit> = if frozen {
        vec![Fit::default(); n]
    } else {
        let pyr: Vec<Pyramid> = planes.par_iter().map(|p| build_pyramid(p, &cfg)).collect();
        let spots = tile_grid_m(
            planes[0],
            cfg.fine_tile,
            cfg.fine_grid.0,
            cfg.fine_grid.1,
            cfg.margin,
        )
        .expect("plane too small for the anchor grid");
        let t0 = Instant::now();
        let v: Vec<Fit> = (0..n)
            .into_par_iter()
            .map(|j| {
                if j == 0 {
                    return Fit::default();
                }
                align_with(&pyr[0], &pyr[j], planes[0], planes[j], &spots, &cfg)
                    .map(|s| s.fit)
                    .unwrap_or_default()
            })
            .collect();
        eprintln!(
            "[{case}] {} direct (0,j) fits in {:.1} s",
            n - 1,
            t0.elapsed().as_secs_f64()
        );
        v
    };

    // Scene-anchored tile centres, in frame-0 coordinates.
    let half = tile / 2;
    let mut centres: Vec<(usize, usize)> = Vec::new();
    let mut y = margin + half;
    while y + half + margin <= ph {
        let mut x = margin + half;
        while x + half + margin <= pw {
            centres.push((x, y));
            x += stride;
        }
        y += stride;
    }
    eprintln!(
        "[{case}] {} tiles, {tile} px, stride {stride}",
        centres.len()
    );

    let (cx, cy) = (pw as f32 * 0.5, ph as f32 * 0.5);
    let path = format!("data/{prefix}-focus.csv");
    let mut out = std::io::BufWriter::new(std::fs::File::create(&path).expect("create focus csv"));
    let _ = writeln!(out, "case,frame,tile,x0,y0,x,y,mean,tenengrad,modlap");

    let t1 = Instant::now();
    let rows: Vec<String> = (0..n)
        .into_par_iter()
        .flat_map(|j| {
            let p = planes[j];
            let f = fits[j];
            centres
                .iter()
                .enumerate()
                .map(|(ti, &(x0, y0))| {
                    let (dx, dy) = f.at(x0 as f32, y0 as f32, cx, cy);
                    let xf = (x0 as f32 + dx).round();
                    let yf = (y0 as f32 + dy).round();
                    if xf < half as f32
                        || yf < half as f32
                        || xf + half as f32 >= pw as f32
                        || yf + half as f32 >= ph as f32
                    {
                        return format!("{case},{j},{ti},{x0},{y0},,,,,");
                    }
                    let (xi, yi) = (xf as usize - half, yf as usize - half);
                    let (mu, ten, lap) = sharpness(p, xi, yi, tile);
                    format!("{case},{j},{ti},{x0},{y0},{xi},{yi},{mu:.4},{ten:.8},{lap:.8}")
                })
                .collect::<Vec<String>>()
        })
        .collect();
    for r in rows {
        let _ = writeln!(out, "{r}");
    }
    let _ = out.flush();
    eprintln!(
        "[{case}] wrote {path} in {:.1} s",
        t1.elapsed().as_secs_f64()
    );
}

/// Two mean-normalised focus measures over one `t`x`t` window.
///
/// Normalisation by the window mean is mandatory rather than cosmetic: 112 was
/// shot at 1/60 s and 113 at 1/30 s, a full stop apart, and an unnormalised
/// gradient energy would compare a brighter stack against a darker one.
/// Returning both Tenengrad and the modified Laplacian gives the registered F4
/// arm — the verdict must not depend on which focus measure is used.
fn sharpness(p: &Plane, x0: usize, y0: usize, t: usize) -> (f32, f32, f32) {
    let mut sum = 0f64;
    for y in y0..y0 + t {
        let row = &p.d[y * p.w + x0..y * p.w + x0 + t];
        sum += row.iter().map(|v| *v as f64).sum::<f64>();
    }
    let mu = (sum / (t * t) as f64) as f32;
    if mu.is_nan() || mu <= 0.0 {
        return (mu, 0.0, 0.0);
    }
    let mut ten = 0f64;
    let mut lap = 0f64;
    for y in y0 + 1..y0 + t - 1 {
        for x in x0 + 1..x0 + t - 1 {
            let i = y * p.w + x;
            let (l, r) = (p.d[i - 1], p.d[i + 1]);
            let (u, d) = (p.d[i - p.w], p.d[i + p.w]);
            let gx = (r - l) as f64;
            let gy = (d - u) as f64;
            ten += gx * gx + gy * gy;
            let c = p.d[i] as f64 * 2.0;
            lap += ((c - l as f64 - r as f64).abs() + (c - u as f64 - d as f64).abs()).powi(2);
        }
    }
    let m = ((t - 2) * (t - 2)) as f64;
    let mu2 = (mu as f64) * (mu as f64);
    (mu, (ten / m / mu2) as f32, (lap / m / mu2) as f32)
}

/// `M12-F3`: fit the similarity between the first frames of two *different*
/// stacks, so the two tile grids can be shown to address the same scene points.
///
/// Needed because the focus regression matches tiles between `112MSDCF` and
/// `113MSDCF` by scene position, and "the preview NCC is +0.9961" is not a
/// registration. This reports the actual displacement in plane px.
fn run_pairfit(args: &[String]) {
    let cfg = cfg_by_name(&arg_val(args, "--cfg").unwrap_or_else(|| "m10".into()));
    let a = load_planes(&args[2], 1);
    let b = load_planes(&args[3], 1);
    let (pa, pb) = (&a[0], &b[0]);
    let spots = tile_grid_m(
        pa,
        cfg.fine_tile,
        cfg.fine_grid.0,
        cfg.fine_grid.1,
        cfg.margin,
    )
    .expect("plane too small for the anchor grid");
    let (ya, yb) = (build_pyramid(pa, &cfg), build_pyramid(pb, &cfg));
    match align_with(&ya, &yb, pa, pb, &spots, &cfg) {
        Some(s) => {
            let (cx, cy) = (pa.w as f32 * 0.5, pa.h as f32 * 0.5);
            let (dx, dy) = s.fit.at(0.0, 0.0, cx, cy);
            println!(
                "fit ok: ax {:.4} ay {:.4} g {:.8} rot {:.8}",
                s.fit.ax, s.fit.ay, s.fit.g, s.fit.r
            );
            println!(
                "rms {:.4} used {} of {} peak_mean {:.5}",
                s.rms, s.used, s.total, s.peak_mean
            );
            println!(
                "corner displacement {:.3} plane px",
                (dx * dx + dy * dy).sqrt()
            );
            println!(
                "centre displacement {:.3} plane px",
                (s.fit.ax.powi(2) + s.fit.ay.powi(2)).sqrt()
            );
        }
        None => println!("fit FAILED"),
    }
}

/// `M23`: the **per-edge response** `R`, measured on the very pair it will
/// correct.
///
/// This is M10's P7 increment probe (`run_increment`) turned into a two-sided
/// estimator and run over a whole edge set instead of a handful of base frames.
/// The difference matters for three reasons:
///
/// 1. **Two-sided cancels the resampler to first order.** The plant goes
///    through `warp_known`, which is bilinear, and bilinear's phase-dependent
///    blur has variance `phi*(1-phi)` in the fractional pixel offset `phi`.
///    That is invariant under `phi -> 1-phi`, i.e. **even** in the sign of the
///    plant, while the response is **odd**. The one-sided ratio M10 published
///    carries the resampler term; the two-sided difference does not, to first
///    order. `--self` measures the residual directly.
/// 2. **Per-edge, not per-stack.** M12 refuted a scalar `k = 1/S_W(1)` fitted
///    on one scene and transferred to another. Nothing is transferred here:
///    each edge is divided by a number measured on its own two frames.
/// 3. **The response is a derivative, so it needs a `delta` ladder.** If `R`
///    depends materially on the size of the probe, the estimator is not locally
///    linear and the metacalibration identity `L_true = L_meas / R` does not
///    hold at any `delta`. The ladder is the test of the premise, not a tuning
///    sweep, and no argmin over it is reported as an optimum (rule 13).
///
/// For each pair `(i, j)` and each plant magnitude `d`:
///
/// ```text
///   F0  = fit(i, j)
///   F+  = fit(i, warp(j, +d))          I+ = F+ o F0^-1     l+ = log|a(I+)|
///   F-  = fit(i, warp(j, -d))          I- = F- o F0^-1     l- = log|a(I-)|
///   R   = (l+ - l-) / (log(1+d) - log(1-d))
/// ```
///
/// The pair, its defocus mismatch, its tile dropout and its content overlap are
/// held fixed across all three fits, so they cancel: only the estimator's
/// response to a small geometric change survives.
///
/// `--self` replaces `j` with `i`, giving a pair of **real content with zero
/// defocus difference** carrying the identical resampler and the identical
/// plant. Its true `R` is 1 by construction, so it is the registered N3 null.
///
/// **Added after N3 fired (disclosed, not backfilled).** N3 read `R = 0.372` at
/// `delta = 1e-4` on frames that differ by *nothing*, which is lower than any
/// real pair. Two diagnostics were then added to find out why:
///
/// * `--pedestal P` warps the moving frame by a single bilinear pass at
///   `(1+P)(1±d) − 1` instead of `1±d`, so the pair carries a large
///   pre-existing differential displacement (tiles at varied sub-pixel phase)
///   with **one** resampling pass and no extra blur. It moves the operating
///   point, which is the confound to state when reading it.
/// * `--field` renders reference and both plants as point samples of one
///   continuous band-limited function at the composed transforms, so **no
///   interpolator touches anything**. This is M10 P6's resampler-free arm
///   rebuilt as a two-sided response measurement. If `R` is faithful here and
///   shrunk under `--self`, the shrinkage at small `delta` is the resampler.
fn run_metacal(args: &[String]) {
    let dir = &args[2];
    let prefix = &args[3];
    let case = arg_val(args, "--case").unwrap_or_else(|| "case".into());
    let cfgnames: Vec<String> = arg_val(args, "--cfgs")
        .unwrap_or_else(|| "m10".into())
        .split(',')
        .map(|s| s.trim().to_string())
        .collect();
    let spans = parse_list(&arg_val(args, "--spans").unwrap_or_else(|| "1,2".into()));
    let deltas: Vec<f32> = arg_val(args, "--deltas")
        .unwrap_or_else(|| "0.0001,0.0002,0.0004,0.0008,0.0016".into())
        .split(',')
        .filter_map(|s| s.trim().parse().ok())
        .collect();
    let limit: usize = arg_val(args, "--limit")
        .and_then(|s| s.parse().ok())
        .unwrap_or(usize::MAX);
    let stride: usize = arg_val(args, "--stride")
        .and_then(|s| s.parse().ok())
        .unwrap_or(1);
    let selfpair = has_flag(args, "--self");
    let pedestal: f32 = arg_val(args, "--pedestal")
        .and_then(|s| s.parse().ok())
        .unwrap_or(0.0);
    let field_reps: usize = arg_val(args, "--field")
        .and_then(|s| s.parse().ok())
        .unwrap_or(0);
    let noise: f32 = arg_val(args, "--noise")
        .and_then(|s| s.parse().ok())
        .unwrap_or(4.2);

    if field_reps > 0 {
        run_metacal_field(&case, &cfgnames, &deltas, field_reps, pedestal, noise, prefix);
        return;
    }

    let planes = load_planes(dir, limit);
    let n = planes.len();
    let (pw, ph) = (planes[0].w, planes[0].h);

    let mut pairs: Vec<(usize, usize)> = Vec::new();
    for &s in &spans {
        if s >= n {
            continue;
        }
        let mut i = 0;
        while i + s < n {
            pairs.push((i, if selfpair { i } else { i + s }));
            i += stride;
        }
    }

    let path = format!("data/{prefix}-metacal.csv");
    let mut out = std::io::BufWriter::new(std::fs::File::create(&path).expect("create csv"));
    let _ = writeln!(
        out,
        "case,cfg,ref,mov,span,delta,l0,rot0,ax0,ay0,rms0,used0,lever0,peak0,\
l_plus,l_minus,r_two,r_plus,r_minus,rms_plus,used_plus,rms_minus,used_minus,plane_w,plane_h"
    );

    for cfgname in &cfgnames {
        let cfg = cfg_by_name(cfgname);
        let t_pyr = Instant::now();
        // With a pedestal the base fit is against the once-warped moving frame,
        // so the base pyramid for `j` is not the one cached here; it is rebuilt
        // per pair below. The cache still serves every reference frame.
        let pyr: Vec<Pyramid> = planes.par_iter().map(|p| build_pyramid(p, &cfg)).collect();
        eprintln!(
            "[mc/{cfgname}] base pyramids for {n} frames in {:.2} s",
            t_pyr.elapsed().as_secs_f64()
        );
        let spots = tile_grid_m(
            &planes[0],
            cfg.fine_tile,
            cfg.fine_grid.0,
            cfg.fine_grid.1,
            cfg.margin,
        )
        .expect("grid");

        let t0 = Instant::now();
        let done = std::sync::atomic::AtomicUsize::new(0);
        let total = pairs.len();
        let rows: Vec<String> = pairs
            .par_iter()
            .map(|&(i, j)| {
                let rf = &planes[i];
                let span = j as i64 - i as i64;
                // `mv_owned` only exists when a pedestal forces a warp.
                let mv_owned = if pedestal != 0.0 {
                    Some(warp_known(
                        &planes[j],
                        Fit {
                            g: pedestal,
                            r: 0.0,
                            ax: 0.0,
                            ay: 0.0,
                        },
                    ))
                } else {
                    None
                };
                let mv: &Plane = mv_owned.as_ref().unwrap_or(&planes[j]);
                let mv_pyr_owned = mv_owned.as_ref().map(|p| build_pyramid(p, &cfg));
                let mv_pyr: &Pyramid = mv_pyr_owned.as_ref().unwrap_or(&pyr[j]);
                let f0 = align_with(&pyr[i], mv_pyr, rf, mv, &spots, &cfg);
                let mut lines = Vec::new();
                let base = match f0 {
                    Some(s) => s,
                    None => {
                        for d in &deltas {
                            lines.push(format!(
                                "{case},{cfgname},{i},{j},{span},{d:.9},\
,,,,,0,,,,,,,,,0,,0,{pw},{ph}"
                            ));
                        }
                        let k = done.fetch_add(1, std::sync::atomic::Ordering::Relaxed) + 1;
                        if k.is_multiple_of(50) {
                            eprintln!(
                                "[mc/{cfgname}] {k}/{total} pairs, {:.1} s",
                                t0.elapsed().as_secs_f64()
                            );
                        }
                        return lines.join("\n");
                    }
                };
                let (a0r, a0i) = (1.0f64 + base.fit.g as f64, base.fit.r as f64);
                let l0 = 0.5 * (a0r * a0r + a0i * a0i).ln();
                for &d in &deltas {
                    let mut cells: [Option<(f64, f32, usize)>; 2] = [None, None];
                    for (k, sgn) in [(0usize, 1.0f32), (1usize, -1.0f32)] {
                        // One bilinear pass whatever the pedestal: the plant is
                        // composed into it, never applied on top of a warp.
                        let g_eff = (1.0 + pedestal) * (1.0 + sgn * d) - 1.0;
                        let w = Fit {
                            g: g_eff,
                            r: 0.0,
                            ax: 0.0,
                            ay: 0.0,
                        };
                        let mv2 = warp_known(&planes[j], w);
                        let mp2 = build_pyramid(&mv2, &cfg);
                        if let Some(s1) = align_with(&pyr[i], &mp2, rf, &mv2, &spots, &cfg) {
                            let (a1r, a1i) = (1.0f64 + s1.fit.g as f64, s1.fit.r as f64);
                            // increment = F1 o F0^-1 in the (a, b) algebra
                            let den = a0r * a0r + a0i * a0i;
                            let ir = (a1r * a0r + a1i * a0i) / den;
                            let ii = (a1i * a0r - a1r * a0i) / den;
                            let l = 0.5 * (ir * ir + ii * ii).ln();
                            cells[k] = Some((l, s1.rms, s1.used));
                        }
                    }
                    lines.push(mc_row(
                        &case, cfgname, i, j, span, d, l0, &base, &cells, pw, ph,
                    ));
                }
                let k = done.fetch_add(1, std::sync::atomic::Ordering::Relaxed) + 1;
                if k.is_multiple_of(50) {
                    eprintln!(
                        "[mc/{cfgname}] {k}/{total} pairs, {:.1} s",
                        t0.elapsed().as_secs_f64()
                    );
                }
                lines.join("\n")
            })
            .collect();
        let secs = t0.elapsed().as_secs_f64();
        let fits = total * (1 + 2 * deltas.len());
        eprintln!(
            "[mc/{cfgname}] {total} pairs x {} deltas = {fits} fits in {secs:.1} s \
({:.1} ms/pair, {:.1} ms/fit)",
            deltas.len(),
            secs / total as f64 * 1e3,
            secs / fits as f64 * 1e3
        );
        for r in rows {
            let _ = writeln!(out, "{r}");
        }
    }
    let _ = out.flush();
    eprintln!("wrote {path}");
}

/// One CSV row of `metacal`, shared by the real-frame and field arms.
#[allow(clippy::too_many_arguments)]
fn mc_row(
    case: &str,
    cfgname: &str,
    i: usize,
    j: usize,
    span: i64,
    d: f32,
    l0: f64,
    base: &Stage,
    cells: &[Option<(f64, f32, usize)>; 2],
    pw: usize,
    ph: usize,
) -> String {
    let lp_true = (1.0f64 + d as f64).ln();
    let lm_true = (1.0f64 - d as f64).ln();
    let f = |c: &Option<(f64, f32, usize)>| match c {
        Some((l, r, u)) => (format!("{l:.10}"), format!("{r:.4}"), format!("{u}")),
        None => (String::new(), String::new(), "0".to_string()),
    };
    let (lps, rps, ups) = f(&cells[0]);
    let (lms, rms_, ums) = f(&cells[1]);
    let r_two = match (&cells[0], &cells[1]) {
        (Some((lp, ..)), Some((lm, ..))) => format!("{:.9}", (lp - lm) / (lp_true - lm_true)),
        _ => String::new(),
    };
    let r_plus = cells[0]
        .as_ref()
        .map(|(l, ..)| format!("{:.9}", l / lp_true))
        .unwrap_or_default();
    let r_minus = cells[1]
        .as_ref()
        .map(|(l, ..)| format!("{:.9}", l / lm_true))
        .unwrap_or_default();
    format!(
        "{case},{cfgname},{i},{j},{span},{d:.9},{l0:.10},{:.9},{:.6},{:.6},\
{:.4},{},{:.2},{:.5},{lps},{lms},{r_two},{r_plus},{r_minus},{rps},{ups},{rms_},{ums},{pw},{ph}",
        base.fit.r,
        base.fit.ax,
        base.fit.ay,
        base.rms,
        base.used,
        base.lever_rms,
        base.peak_mean
    )
}

/// `N4b`: the same two-sided response with **no interpolator anywhere**.
///
/// Reference and both plants are independent point samples of one continuous
/// band-limited field at the composed transforms, so the resampler that
/// `warp_known` introduces is absent by construction rather than cancelled by
/// an argument. `pedestal` sets the pair's pre-existing scale offset, so the
/// `pedestal = 0` arm is the exact resampler-free analogue of the `--self`
/// null.
///
/// The noise seed is held fixed across the three moving renders, so the noise
/// is a fixed function of output position — a sensor-fixed pattern. A bilinear
/// plant instead carries the noise with the content. Neither convention matches
/// the other exactly, and at 0.12 px of plant the difference is far below the
/// effect being measured.
#[allow(clippy::too_many_arguments)]
fn run_metacal_field(
    case: &str,
    cfgnames: &[String],
    deltas: &[f32],
    reps: usize,
    pedestal: f32,
    noise: f32,
    prefix: &str,
) {
    let (w, h) = (3516usize, 2344usize);
    let path = format!("data/{prefix}-metacal.csv");
    let mut out = std::io::BufWriter::new(std::fs::File::create(&path).expect("create csv"));
    let _ = writeln!(
        out,
        "case,cfg,ref,mov,span,delta,l0,rot0,ax0,ay0,rms0,used0,lever0,peak0,\
l_plus,l_minus,r_two,r_plus,r_minus,rms_plus,used_plus,rms_minus,used_minus,plane_w,plane_h"
    );
    for cfgname in cfgnames {
        let cfg = cfg_by_name(cfgname);
        let spots = tile_grid_m(
            &Plane { d: vec![], w, h },
            cfg.fine_tile,
            cfg.fine_grid.0,
            cfg.fine_grid.1,
            cfg.margin,
        )
        .expect("grid");
        let t0 = Instant::now();
        for rep in 0..reps {
            let fld = field::Field::new(384, 1.0 / 220.0, 1.0 / 2.6, 0xF1E1D0 ^ (rep as u64));
            let base_t = Fit {
                g: pedestal,
                r: 0.0,
                ax: 0.0,
                ay: 0.0,
            };
            let rf = fld.render(w, h, None, 900.0, 3000.0, noise, 0x51_u64 ^ (rep as u64));
            let rp = build_pyramid(&rf, &cfg);
            let mv = fld.render(
                w,
                h,
                Some(base_t),
                900.0,
                3000.0,
                noise,
                0x52_u64 ^ (rep as u64),
            );
            let mvp = build_pyramid(&mv, &cfg);
            let base = match align_with(&rp, &mvp, &rf, &mv, &spots, &cfg) {
                Some(s) => s,
                None => continue,
            };
            let (a0r, a0i) = (1.0f64 + base.fit.g as f64, base.fit.r as f64);
            let l0 = 0.5 * (a0r * a0r + a0i * a0i).ln();
            let rows: Vec<String> = deltas
                .par_iter()
                .map(|&d| {
                    let mut cells: [Option<(f64, f32, usize)>; 2] = [None, None];
                    for (k, sgn) in [(0usize, 1.0f32), (1usize, -1.0f32)] {
                        let t = compose(&[
                            base_t,
                            Fit {
                                g: sgn * d,
                                r: 0.0,
                                ax: 0.0,
                                ay: 0.0,
                            },
                        ]);
                        let mv2 = fld.render(
                            w,
                            h,
                            Some(t),
                            900.0,
                            3000.0,
                            noise,
                            0x52_u64 ^ (rep as u64),
                        );
                        let mp2 = build_pyramid(&mv2, &cfg);
                        if let Some(s1) = align_with(&rp, &mp2, &rf, &mv2, &spots, &cfg) {
                            let (a1r, a1i) = (1.0f64 + s1.fit.g as f64, s1.fit.r as f64);
                            let den = a0r * a0r + a0i * a0i;
                            let ir = (a1r * a0r + a1i * a0i) / den;
                            let ii = (a1i * a0r - a1r * a0i) / den;
                            let l = 0.5 * (ir * ir + ii * ii).ln();
                            cells[k] = Some((l, s1.rms, s1.used));
                        }
                    }
                    mc_row(case, cfgname, rep, rep, 0, d, l0, &base, &cells, w, h)
                })
                .collect();
            for r in rows {
                let _ = writeln!(out, "{r}");
            }
            eprintln!("[mc-field/{cfgname}] rep {rep} done ({:.1} s)", t0.elapsed().as_secs_f64());
        }
    }
    let _ = out.flush();
    eprintln!("wrote {path}");
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("usage:");
        eprintln!("  m12-shrinkage synthetic <dir-of-ARW>");
        eprintln!("  m12-shrinkage floor <dir-of-ARW> <out-prefix> --case NAME [--margins 10,32,64,96] [--frames 0,40,80] [--n 24]");
        eprintln!("  m12-shrinkage edges <dir-of-ARW> <out-prefix> --case NAME [--spans 1,2,4] [--direct0] [--cfg m10|m3|wide] [--limit N]");
        eprintln!("  m12-shrinkage synth <dir-of-ARW> <out-prefix> --case NAME [--n 105] [--flavour warp|integer] [--spans ...] [--direct0]");
        eprintln!("  m12-shrinkage focus <dir-of-ARW> <out-prefix> --case NAME [--tile 96] [--stride 96] [--fmargin 160] [--frozen] [--step 1] [--phase 0]");
        eprintln!("  m23-metacal   metacal <dir-of-ARW> <out-prefix> --case NAME [--cfgs m10] [--spans 1,2] [--deltas 1e-4,...] [--self] [--pedestal P] [--field REPS] [--noise E] [--stride 1] [--limit N]");
        std::process::exit(2);
    }
    match args[1].as_str() {
        "synthetic" => {
            assert!(args.len() >= 3, "synthetic needs <dir>");
            run_synthetic(&args[2]);
        }
        "floor" => {
            assert!(args.len() >= 4, "floor needs <dir> <out-prefix>");
            run_floor(&args);
        }
        "edges" => {
            assert!(args.len() >= 4, "edges needs <dir> <out-prefix>");
            run_edges(&args);
        }
        "lock" => {
            assert!(args.len() >= 3, "lock needs <out-prefix>");
            run_lock(&args);
        }
        "increment" => {
            assert!(args.len() >= 4, "increment needs <dir> <out-prefix>");
            run_increment(&args);
        }
        "metacal" => {
            assert!(args.len() >= 4, "metacal needs <dir> <out-prefix>");
            run_metacal(&args);
        }
        "synth" => {
            assert!(args.len() >= 4, "synth needs <dir> <out-prefix>");
            run_synth(&args);
        }
        "focus" => {
            assert!(args.len() >= 4, "focus needs <dir> <out-prefix>");
            run_focus(&args);
        }
        "pairfit" => {
            assert!(args.len() >= 4, "pairfit needs <dir-a> <dir-b>");
            run_pairfit(&args);
        }
        other => {
            eprintln!("unknown mode {other}");
            std::process::exit(2);
        }
    }
}
