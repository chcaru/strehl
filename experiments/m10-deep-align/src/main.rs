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
//!   m10-deep-align synthetic  <dir-of-ARW>
//!   m10-deep-align edges      <dir-of-ARW> <out-prefix> --case NAME [opts]
//!   m10-deep-align synth      <dir-of-ARW> <out-prefix> --case NAME [opts]
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
    let spec = synth::SynthSpec {
        n,
        flavour,
        // Matches coffee-bean's measured total drift (M6 fact 32: -4.575%).
        g_total: -0.04575,
        curve: 1.6,
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

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("usage:");
        eprintln!("  m10-deep-align synthetic <dir-of-ARW>");
        eprintln!("  m10-deep-align floor <dir-of-ARW> <out-prefix> --case NAME [--margins 10,32,64,96] [--frames 0,40,80] [--n 24]");
        eprintln!("  m10-deep-align edges <dir-of-ARW> <out-prefix> --case NAME [--spans 1,2,4] [--direct0] [--cfg m10|m3|wide] [--limit N]");
        eprintln!("  m10-deep-align synth <dir-of-ARW> <out-prefix> --case NAME [--n 105] [--flavour warp|integer] [--spans ...] [--direct0]");
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
        "synth" => {
            assert!(args.len() >= 4, "synth needs <dir> <out-prefix>");
            run_synth(&args);
        }
        other => {
            eprintln!("unknown mode {other}");
            std::process::exit(2);
        }
    }
}
