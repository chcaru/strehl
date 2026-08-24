//! M103 probe — dump the *individual* alignment edges the solve rests on, and
//! re-solve arbitrary subsets of them.
//!
//! M97 measured the end-to-end shortfall (`docs/research/M97-warped-merge.md`
//! §7.2): the sidecar applies ~54% of the scale span that is really there.
//! That is a statement about the *product* of the estimator and the solver.
//! Nothing in the shipped tooling separates the two, because `strehl align`
//! writes only the solved placements. This binary writes the raw per-edge
//! measurements, so the two can be told apart by arithmetic instead of by
//! argument.
//!
//! Deliberately a standalone crate outside the strehl workspace: several
//! milestones are live in this tree tonight and adding a workspace member
//! would edit a shared manifest.

use anyhow::{Context, Result, bail};
use rayon::prelude::*;
use std::io::Write;
use std::path::{Path, PathBuf};

use strehl_core::align::{
    AlignConfig, AlignEdge, AlignFrame, AlignPyramid, Cx, GlobalOptions, PlaneRef, Similarity,
    SimilarityParams, Weighting, align_pair, graph_stats, sample_bilinear, sample_catmull_rom,
    tile_grid, total_drift,
};
use strehl_core::plane::{PlaneGeometry, green_luma};
use strehl_core::warpmap::StackIdentity;

// ---------------------------------------------------------------------------
// stack decode (mirrors align_cmd::decode_stack; kept here so the probe does
// not depend on the CLI crate)
// ---------------------------------------------------------------------------

struct Stack {
    geom: PlaneGeometry,
    planes: Vec<Vec<f32>>,
}

fn list_frames(dir: &Path) -> Result<Vec<PathBuf>> {
    let mut v: Vec<PathBuf> = std::fs::read_dir(dir)
        .with_context(|| format!("reading {}", dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| {
            p.extension()
                .map(|e| e.to_string_lossy().eq_ignore_ascii_case("arw"))
                .unwrap_or(false)
        })
        .collect();
    v.sort();
    if v.is_empty() {
        bail!("no .arw frames in {}", dir.display());
    }
    Ok(v)
}

fn decode_stack(paths: &[PathBuf], threads: usize) -> Result<Stack> {
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()
        .context("decode pool")?;
    let decoded: Result<Vec<(PlaneGeometry, Vec<f32>)>> = pool.install(|| {
        paths
            .par_iter()
            .map(|p| {
                let raw =
                    strehl_raw::decode(p).with_context(|| format!("decoding {}", p.display()))?;
                let geom = PlaneGeometry {
                    width: raw.active.width / 2,
                    height: raw.active.height / 2,
                };
                let mut plane = vec![0f32; geom.pixels()];
                green_luma(&raw, raw.levels.black as f32, &mut plane);
                Ok((geom, plane))
            })
            .collect()
    });
    let decoded = decoded?;
    let geom = decoded[0].0;
    if decoded.iter().any(|(g, _)| *g != geom) {
        bail!("frames do not share a plane geometry");
    }
    Ok(Stack {
        geom,
        planes: decoded.into_iter().map(|(_, p)| p).collect(),
    })
}

// ---------------------------------------------------------------------------
// argument plumbing (hand-rolled; the probe has no clap dependency)
// ---------------------------------------------------------------------------

struct Args {
    map: std::collections::HashMap<String, String>,
}

impl Args {
    fn parse(it: impl Iterator<Item = String>) -> Self {
        let mut map = std::collections::HashMap::new();
        let mut key: Option<String> = None;
        for a in it {
            if let Some(k) = a.strip_prefix("--") {
                if let Some(prev) = key.take() {
                    map.insert(prev, "1".to_string());
                }
                if let Some((k, v)) = k.split_once('=') {
                    map.insert(k.to_string(), v.to_string());
                } else {
                    key = Some(k.to_string());
                }
            } else if let Some(k) = key.take() {
                map.insert(k, a);
            }
        }
        if let Some(k) = key {
            map.insert(k, "1".to_string());
        }
        Self { map }
    }
    fn get(&self, k: &str) -> Option<&str> {
        self.map.get(k).map(|s| s.as_str())
    }
    fn req(&self, k: &str) -> Result<&str> {
        self.get(k).with_context(|| format!("--{k} is required"))
    }
    fn usize_or(&self, k: &str, d: usize) -> Result<usize> {
        match self.get(k) {
            Some(v) => Ok(v.parse()?),
            None => Ok(d),
        }
    }
    fn i32_or(&self, k: &str, d: i32) -> Result<i32> {
        match self.get(k) {
            Some(v) => Ok(v.parse()?),
            None => Ok(d),
        }
    }
    fn f64_or(&self, k: &str, d: f64) -> Result<f64> {
        match self.get(k) {
            Some(v) => Ok(v.parse()?),
            None => Ok(d),
        }
    }
    fn f32_or(&self, k: &str, d: f32) -> Result<f32> {
        match self.get(k) {
            Some(v) => Ok(v.parse()?),
            None => Ok(d),
        }
    }
    fn list(&self, k: &str) -> Result<Vec<usize>> {
        Ok(match self.get(k) {
            Some(v) => v
                .split(',')
                .filter(|s| !s.is_empty())
                .map(|s| s.parse::<usize>())
                .collect::<Result<Vec<_>, _>>()?,
            None => Vec::new(),
        })
    }
}

fn config_from(a: &Args) -> Result<AlignConfig> {
    let base = match a.get("config").unwrap_or("deep") {
        "deep" => AlignConfig::deep(),
        "wide" => AlignConfig::wide(),
        "shallow" => AlignConfig::shallow(),
        "iterated" => AlignConfig::iterated(),
        "iterated-wide" => AlignConfig::iterated_wide(),
        other => bail!("unknown --config {other}"),
    };
    let coarse_factors = {
        let v = a.list("coarse-factors")?;
        if v.is_empty() {
            base.coarse_factors.clone()
        } else {
            v
        }
    };
    Ok(AlignConfig {
        coarse_factors,
        coarse_tile: a.usize_or("coarse-tile", base.coarse_tile)?,
        coarse_radius: a.i32_or("coarse-radius", base.coarse_radius)?,
        fine_tile: a.usize_or("fine-tile", base.fine_tile)?,
        fine_radius: a.i32_or("fine-radius", base.fine_radius)?,
        margin: a.usize_or("margin", base.margin)?,
        min_contrast: a.f32_or("min-contrast", base.min_contrast)?,
        min_peak: a.f32_or("min-peak", base.min_peak)?,
        min_tiles: a.usize_or("min-tiles", base.min_tiles)?,
        outlier_mads: a.f32_or("outlier-mads", base.outlier_mads)?,
        coarse_grid: base.coarse_grid,
        fine_grid: base.fine_grid,
        fine_iters: a.usize_or("fine-iters", base.fine_iters)?,
        warp_tiles: match a.get("warp") {
            Some(v) => v == "1" || v == "true" || v == "yes",
            None => base.warp_tiles,
        },
    })
}

// ---------------------------------------------------------------------------
// measure
// ---------------------------------------------------------------------------

fn cmd_measure(a: &Args) -> Result<()> {
    let dir = PathBuf::from(a.req("dir")?);
    let out = PathBuf::from(a.req("out")?);
    let threads = a.usize_or("threads", 0)?;
    let mut paths = list_frames(&dir)?;
    if let Some(l) = a.get("limit") {
        let l: usize = l.parse()?;
        paths.truncate(l);
    }
    let n = paths.len();
    let cfg = config_from(a)?;
    eprintln!("stack {} : {n} frames", dir.display());
    eprintln!("config {cfg:?}");

    let t0 = std::time::Instant::now();
    let st = decode_stack(&paths, threads)?;
    eprintln!(
        "decoded in {:.1} s, plane {}x{}",
        t0.elapsed().as_secs_f64(),
        st.geom.width,
        st.geom.height
    );

    let mut pairs: Vec<(usize, usize)> = Vec::new();
    for s in a.list("spans")? {
        for i in 0..n.saturating_sub(s) {
            pairs.push((i, i + s));
        }
    }
    // Explicit anchor pairs: `--anchor 0` adds (0, k) for every k, which is the
    // long-baseline information the shipped ladder does not contain.
    if let Some(v) = a.get("anchor") {
        for tok in v.split(',').filter(|s| !s.is_empty()) {
            let r: usize = tok.parse()?;
            for k in 0..n {
                if k != r {
                    pairs.push((r.min(k), r.max(k)));
                }
            }
        }
    }
    // Sparse anchor pairs from a stride, so a full anchor fan is not needed.
    if let (Some(r), Some(step)) = (a.get("anchor-from"), a.get("anchor-stride")) {
        let r: usize = r.parse()?;
        let step: usize = step.parse()?;
        let mut k = 0usize;
        while k < n {
            if k != r {
                pairs.push((r.min(k), r.max(k)));
            }
            k += step.max(1);
        }
        if n > 0 && (n - 1) != r {
            pairs.push((r.min(n - 1), r.max(n - 1)));
        }
    }
    pairs.sort_unstable();
    pairs.dedup();
    eprintln!("{} pairs", pairs.len());

    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()
        .context("measure pool")?;
    let t1 = std::time::Instant::now();
    let pyramids: Vec<AlignPyramid> = pool.install(|| {
        st.planes
            .par_iter()
            .map(|p| {
                let pr = PlaneRef::from_geometry(p, st.geom).expect("plane geometry");
                AlignPyramid::build(pr, &cfg).expect("pyramid")
            })
            .collect()
    });
    eprintln!("pyramids in {:.1} s", t1.elapsed().as_secs_f64());

    let spots = tile_grid(
        PlaneRef::from_geometry(&st.planes[0], st.geom).unwrap(),
        cfg.fine_tile,
        cfg.fine_grid.0,
        cfg.fine_grid.1,
        cfg.margin,
    )
    .context("fine tile grid")?;

    let t2 = std::time::Instant::now();
    let rows: Vec<String> = pool.install(|| {
        pairs
            .par_iter()
            .map(|&(i, j)| {
                let rp = PlaneRef::from_geometry(&st.planes[i], st.geom).unwrap();
                let mp = PlaneRef::from_geometry(&st.planes[j], st.geom).unwrap();
                let r = align_pair(
                    AlignFrame {
                        plane: rp,
                        pyramid: &pyramids[i],
                    },
                    AlignFrame {
                        plane: mp,
                        pyramid: &pyramids[j],
                    },
                    &spots,
                    &cfg,
                );
                match r {
                    Ok(s) => {
                        let t = s.similarity();
                        format!(
                            "{i},{j},{},OK,{:.12e},{:.12e},{:.12e},{:.12e},{},{},{},{:.6},{:.4},{:.6},{},{},{},{},{}",
                            j - i,
                            t.a.re,
                            t.a.im,
                            t.b.re,
                            t.b.im,
                            s.used,
                            s.total,
                            s.raw_n,
                            s.rms,
                            s.lever_rms,
                            s.peak_mean,
                            s.rejected.low_contrast,
                            s.rejected.low_peak,
                            s.rejected.border,
                            s.rejected.oob,
                            s.rejected.outlier
                        )
                    }
                    Err(e) => format!(
                        "{i},{j},{},REFUSED:{:?},,,,,0,{},0,,,,,,,,",
                        j - i,
                        e,
                        spots.len()
                    ),
                }
            })
            .collect()
    });
    eprintln!("measured in {:.1} s", t2.elapsed().as_secs_f64());

    let mut fh = std::fs::File::create(&out)?;
    writeln!(
        fh,
        "# m103probe measure dir={} n={} cfg={:?}",
        dir.display(),
        n,
        cfg
    )?;
    writeln!(
        fh,
        "i,j,span,status,a_re,a_im,b_re,b_im,used,total,raw_n,rms,lever,peak,low_contrast,low_peak,border,oob,outlier"
    )?;
    for r in &rows {
        writeln!(fh, "{r}")?;
    }
    eprintln!("wrote {}", out.display());
    Ok(())
}

// ---------------------------------------------------------------------------
// solve
// ---------------------------------------------------------------------------

struct LoadedEdges {
    edges: Vec<AlignEdge>,
    n: usize,
}

fn load_edges(path: &Path) -> Result<LoadedEdges> {
    let text = std::fs::read_to_string(path)?;
    let mut edges = Vec::new();
    let mut n = 0usize;
    for line in text.lines() {
        if line.starts_with('#') || line.starts_with("i,j,") {
            continue;
        }
        let f: Vec<&str> = line.split(',').collect();
        if f.len() < 14 || f[3] != "OK" {
            if f.len() > 2 {
                let j: usize = f[1].parse().unwrap_or(0);
                n = n.max(j + 1);
            }
            continue;
        }
        let i: usize = f[0].parse()?;
        let j: usize = f[1].parse()?;
        n = n.max(j + 1);
        edges.push(AlignEdge {
            i,
            j,
            t: Similarity {
                a: Cx::new(f[4].parse()?, f[5].parse()?),
                b: Cx::new(f[6].parse()?, f[7].parse()?),
            },
            used: f[8].parse()?,
            rms: f[11].parse()?,
            lever: f[12].parse()?,
        });
    }
    Ok(LoadedEdges { edges, n })
}

fn cmd_solve(a: &Args) -> Result<()> {
    let edges_path = PathBuf::from(a.req("edges")?);
    let loaded = load_edges(&edges_path)?;
    let n = a.usize_or("n", loaded.n)?;
    let min_span = a.usize_or("min-span", 0)?;
    let max_span = a.usize_or("max-span", usize::MAX)?;
    let geom = PlaneGeometry {
        width: a.usize_or("plane-w", 3516)?,
        height: a.usize_or("plane-h", 2344)?,
    };
    // Optional per-edge log-scale gain: a_corrected = a * |a|^(1/g - 1), i.e.
    // the log-magnitude is divided by `g` while rotation and translation are
    // left alone. This is the *correction* under test, applied at the edge.
    let gain = a.f64_or("gain", 1.0)?;
    let gain_min_span = a.usize_or("gain-min-span", 0)?;
    let gain_max_span = a.usize_or("gain-max-span", usize::MAX)?;

    let only: Vec<usize> = a.list("only-spans")?;
    let mut edges: Vec<AlignEdge> = loaded
        .edges
        .into_iter()
        .filter(|e| {
            let s = e.span();
            s >= min_span && s <= max_span && (only.is_empty() || only.contains(&s))
        })
        .collect();
    if gain != 1.0 {
        for e in edges.iter_mut() {
            let s = e.span();
            if s < gain_min_span || s > gain_max_span {
                continue;
            }
            let m = e.t.a.abs();
            if m > 0.0 {
                let corrected = (m.ln() / gain).exp();
                e.t.a = e.t.a.scale(corrected / m);
            }
        }
    }

    let mut opts = GlobalOptions::new(geom);
    opts.weighting = match a.get("weighting").unwrap_or("unit") {
        "unit" => Weighting::Unit,
        "count" => Weighting::Count,
        "invvar" => Weighting::InverseVariance,
        other => bail!("unknown --weighting {other}"),
    };
    opts.irls_iters = a.usize_or("irls", 3)?;
    opts.huber_px = a.f64_or("huber", 3.0)?;
    opts.smooth = a.f64_or("smooth", 0.0)?;

    let gs = graph_stats(&edges, n);
    let placement = strehl_core::align::solve_global(&edges, n, &opts)
        .context("the global system is not full rank")?;
    let placed = placement.iter().filter(|p| p.is_some()).count();
    let drift = total_drift(&placement, geom);

    let reference = a.usize_or("reference", 0)?;
    let refp = placement[reference].context("reference frame unplaced")?;

    println!(
        "edges {} spans[{}..{}] n {} placed {}/{} cycle_rank {} drift {:.3} px",
        edges.len(),
        min_span,
        if max_span == usize::MAX {
            n
        } else {
            max_span
        },
        n,
        placed,
        n,
        gs.cycle_rank,
        drift
    );

    let mut rows = String::from("frame,a_re,a_im,b_re,b_im,scale_rel_ref,ln_scale_rel_ref\n");
    let mut first: Option<f64> = None;
    let mut last: Option<f64> = None;
    for (k, p) in placement.iter().enumerate() {
        match p {
            Some(t) => {
                let rel = Similarity::relative(refp, *t).unwrap_or(Similarity::IDENTITY);
                let s = rel.scale();
                if first.is_none() {
                    first = Some(s);
                }
                last = Some(s);
                rows.push_str(&format!(
                    "{k},{:.12e},{:.12e},{:.12e},{:.12e},{:.9},{:.9}\n",
                    rel.a.re,
                    rel.a.im,
                    rel.b.re,
                    rel.b.im,
                    s,
                    s.ln()
                ));
            }
            None => rows.push_str(&format!("{k},,,,,,\n")),
        }
    }
    if let (Some(f), Some(l)) = (first, last) {
        println!(
            "  |a_first| {f:.6}  |a_last| {l:.6}  span {:.6}  ln-span {:.6}",
            l / f,
            (l / f).ln()
        );
    }
    if let (Some(p0), Some(pn)) = (placement[0], placement[n - 1]) {
        let s0 = Similarity::relative(refp, p0).unwrap().scale();
        let sn = Similarity::relative(refp, pn).unwrap().scale();
        println!(
            "  ENDS |a_0| {s0:.6}  |a_{}| {sn:.6}  span {:.6}  ln-span {:.6}",
            n - 1,
            sn / s0,
            (sn / s0).ln()
        );
    }
    if let Some(o) = a.get("out") {
        std::fs::write(o, rows)?;
        eprintln!("wrote {o}");
    }

    // A sidecar in the shipped `strehl-warpmap 1` format, so M97's own
    // instrument can be pointed at this solve without modification. Written to
    // a temp path and renamed: M97 caught a sidecar being read half-written
    // while a sibling rewrote it, and a torn read here would be silent.
    if let Some(o) = a.get("warpmap") {
        let mut wm = String::from("strehl-warpmap 1\n");
        wm.push_str("# written by M103's probe from a re-solve of a committed edge dump.\n");
        let stack_name = a.get("stack-name").unwrap_or("bee-3-cpl").to_string();
        wm.push_str(&format!("stack-name {stack_name}\n"));
        // `WarpMap::load` requires a stack digest and `check_stack` refuses a
        // mismatch, so a sidecar the merge will actually consume has to carry the
        // real FNV-1a over (name, size) pairs. Computed from the capture
        // directory rather than copied from a shipped sidecar: copying would let
        // this file claim an identity it had never verified, which is exactly the
        // failure `check_stack` exists to catch.
        if let Some(d) = a.get("digest-dir") {
            let mut paths: Vec<std::path::PathBuf> = std::fs::read_dir(d)?
                .filter_map(|e| e.ok().map(|e| e.path()))
                .filter(|p| {
                    p.extension()
                        .is_some_and(|x| x.eq_ignore_ascii_case("arw"))
                })
                .collect();
            paths.sort();
            let id = StackIdentity::from_paths(&stack_name, &paths)?;
            if id.frames != n {
                bail!("digest-dir has {} frames, solve has {n}", id.frames);
            }
            wm.push_str(&format!("stack-digest {:016x}\n", id.digest));
        }
        wm.push_str(&format!("frames {n}\n"));
        wm.push_str(&format!("plane {}x{}\n", geom.width, geom.height));
        wm.push_str(&format!("reference {reference}\n"));
        wm.push_str(&format!("strategy M103-{}\n", a.get("label").unwrap_or("resolve")));
        wm.push_str("resampler catmull-rom\n");
        wm.push_str("# idx state a_re a_im b_re b_im\n");
        for (k, p) in placement.iter().enumerate() {
            match p {
                Some(t) => {
                    let r = Similarity::relative(refp, *t).unwrap_or(Similarity::IDENTITY);
                    wm.push_str(&format!(
                        "{k} placed {:016x} {:016x} {:016x} {:016x} # g={:+.6e} dx={:+.4} dy={:+.4}\n",
                        r.a.re.to_bits(),
                        r.a.im.to_bits(),
                        r.b.re.to_bits(),
                        r.b.im.to_bits(),
                        r.a.re - 1.0,
                        r.b.re,
                        r.b.im
                    ));
                }
                None => wm.push_str(&format!("{k} unplaced\n")),
            }
        }
        // `WarpMap::load` refuses a file that lacks this: a half-written sidecar
        // is a realistic failure and the reader will not accept a short warp
        // list silently. M97 caught exactly that torn read on this stack.
        wm.push_str(&format!("end {n}\n"));
        let tmp = format!("{o}.tmp");
        std::fs::write(&tmp, wm)?;
        std::fs::rename(&tmp, o)?;
        eprintln!("wrote sidecar {o}");
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// plant  --  B5 positive control
// ---------------------------------------------------------------------------
//
// Synthesise a moving frame from a *real* reference frame by a **known**
// similarity, then ask the estimator to recover it. The recovered/planted
// ratio is the estimator's response on a case where the answer is known
// exactly.
//
// Discipline 615: the plant must not act through the mechanism it measures. The
// mechanism under test is displacement measurement, and a resampler is the one
// thing that could forge it (M23 fact 172/174: a bilinear plant manufactured a
// 0.372 self-pair reading and the corpus mistook it for blur asymmetry). So
// every plant is run through **two** resamplers of different order, and a
// zero-plant arm must return the identity. If bilinear and Catmull-Rom disagree
// the resampler is in the answer and the arm is void.

fn warp_plane(src: PlaneRef<'_>, geom: PlaneGeometry, s: SimilarityParams, cubic: bool) -> Vec<f32> {
    let (w, h) = (geom.width, geom.height);
    let (cx, cy) = (w as f64 * 0.5, h as f64 * 0.5);
    let fwd = Similarity::from_params(s);
    // Sample the source at the *exact* inverse, per the warning on
    // `Similarity::invert`: subtracting the forward displacement is the
    // linearised inverse and is wrong at second order by g^2*rho, which at
    // these scales is pixels.
    let inv = fwd.invert().expect("planted similarity is invertible");
    let mut out = vec![0f32; w * h];
    for y in 0..h {
        for x in 0..w {
            let (sx, sy) = inv.apply_at(x as f64, y as f64, cx, cy);
            out[y * w + x] = if cubic {
                sample_catmull_rom(src, sx, sy)
            } else {
                sample_bilinear(src, sx, sy)
            };
        }
    }
    out
}

fn cmd_plant(a: &Args) -> Result<()> {
    let dir = PathBuf::from(a.req("dir")?);
    let out = PathBuf::from(a.req("out")?);
    let frame = a.usize_or("frame", 0)?;
    let threads = a.usize_or("threads", 0)?;
    let cfg = config_from(a)?;
    let scales: Vec<f64> = a
        .req("scales")?
        .split(',')
        .filter(|s| !s.is_empty())
        .map(|s| s.parse::<f64>())
        .collect::<Result<_, _>>()?;
    let shift = a.f64_or("shift", 0.0)?;

    let paths = list_frames(&dir)?;
    let pick = vec![paths[frame].clone()];
    let st = decode_stack(&pick, threads)?;
    let src = PlaneRef::from_geometry(&st.planes[0], st.geom).unwrap();
    eprintln!(
        "plant on {} frame {frame}, plane {}x{}",
        dir.display(),
        st.geom.width,
        st.geom.height
    );
    eprintln!("config {cfg:?}");

    let spots = tile_grid(src, cfg.fine_tile, cfg.fine_grid.0, cfg.fine_grid.1, cfg.margin)
        .context("fine tile grid")?;
    let rpy = AlignPyramid::build(src, &cfg).context("reference pyramid")?;

    let mut rows = String::from("resampler,planted_scale,planted_shift,status,rec_scale,ln_rec,ln_planted,response,rec_ax,used,raw_n,rms,peak,border,low_peak,outlier\n");
    for cubic in [false, true] {
        let name = if cubic { "catmull-rom" } else { "bilinear" };
        for &s in &scales {
            let p = SimilarityParams {
                ax: shift,
                ay: 0.0,
                g: s - 1.0,
                rot: 0.0,
            };
            let moved = warp_plane(src, st.geom, p, cubic);
            let mp = PlaneRef::from_geometry(&moved, st.geom).unwrap();
            let mpy = AlignPyramid::build(mp, &cfg).context("moving pyramid")?;
            let r = align_pair(
                AlignFrame {
                    plane: src,
                    pyramid: &rpy,
                },
                AlignFrame {
                    plane: mp,
                    pyramid: &mpy,
                },
                &spots,
                &cfg,
            );
            match r {
                Ok(f) => {
                    let rec = Similarity::from_params(f.fit).scale();
                    let lr = rec.ln();
                    let lp = s.ln();
                    let resp = if lp.abs() > 1e-12 { lr / lp } else { f64::NAN };
                    rows.push_str(&format!(
                        "{name},{s},{shift},OK,{rec:.9},{lr:.9},{lp:.9},{resp:.6},{:.4},{},{},{:.4},{:.4},{},{},{}\n",
                        f.fit.ax,
                        f.used,
                        f.raw_n,
                        f.rms,
                        f.peak_mean,
                        f.rejected.border,
                        f.rejected.low_peak,
                        f.rejected.outlier
                    ));
                    println!(
                        "{name:>12}  planted {s:.6}  recovered {rec:.6}  response {resp:.4}  \
                         used {:>3}/{:<3} rms {:.3} peak {:.4} bord {:>2} lowpk {:>2}",
                        f.used, spots.len(), f.rms, f.peak_mean, f.rejected.border, f.rejected.low_peak
                    );
                }
                Err(e) => {
                    rows.push_str(&format!("{name},{s},{shift},{e:?},,,,,,,,,,,,\n"));
                    println!("{name:>12}  planted {s:.6}  REFUSED {e:?}");
                }
            }
        }
    }
    std::fs::write(&out, rows)?;
    eprintln!("wrote {}", out.display());
    Ok(())
}

// ---------------------------------------------------------------------------
// tiles  --  per-tile displacement dump
// ---------------------------------------------------------------------------
//
// `align_pair` returns a fitted similarity and a census; it never exposes the
// displacement field the fit was made from. Everything below the fit — whether
// the field is linear in lever arm, whether the sub-pixel estimates pile up at
// integers — is invisible without this.
//
// The seed is deliberately `None`: the window is centred at zero for every
// tile, so nothing the coarse ladder believes can enter the answer. That is
// only valid while the true displacement is inside `radius`, which for short
// spans it comfortably is.

fn cmd_tiles(a: &Args) -> Result<()> {
    let dir = PathBuf::from(a.req("dir")?);
    let out = PathBuf::from(a.req("out")?);
    let i = a.usize_or("i", 0)?;
    let j = a.usize_or("j", 1)?;
    let cfg = config_from(a)?;
    let plant = a.f64_or("plant-scale", 0.0)?;
    let cubic = a.get("cubic").is_some();

    let paths = list_frames(&dir)?;
    let pick = vec![paths[i].clone(), paths[j].clone()];
    let st = decode_stack(&pick, 0)?;
    let rp = PlaneRef::from_geometry(&st.planes[0], st.geom).unwrap();

    let planted;
    let mp = if plant > 0.0 {
        planted = warp_plane(
            rp,
            st.geom,
            SimilarityParams {
                ax: 0.0,
                ay: 0.0,
                g: plant - 1.0,
                rot: 0.0,
            },
            cubic,
        );
        PlaneRef::from_geometry(&planted, st.geom).unwrap()
    } else {
        PlaneRef::from_geometry(&st.planes[1], st.geom).unwrap()
    };

    let spots = tile_grid(rp, cfg.fine_tile, cfg.fine_grid.0, cfg.fine_grid.1, cfg.margin)
        .context("fine tile grid")?;
    let (cx, cy) = (st.geom.width as f64 * 0.5, st.geom.height as f64 * 0.5);

    let mut rows = String::from("tx,ty,ux,uy,lever,status,dx,dy,peak,contrast\n");
    let mut n_ok = 0usize;
    for &(tx, ty) in &spots {
        let mx = tx as f64 + cfg.fine_tile as f64 * 0.5;
        let my = ty as f64 + cfg.fine_tile as f64 * 0.5;
        let m = strehl_core::align::ncc_tile(
            rp,
            mp,
            strehl_core::align::TileProbe {
                tx,
                ty,
                size: cfg.fine_tile,
                predicted: (0.0, 0.0),
                radius: cfg.fine_radius,
            },
            &cfg,
        );
        let (ux, uy) = (mx - cx, my - cy);
        if m.status == strehl_core::align::TileStatus::Ok {
            n_ok += 1;
        }
        rows.push_str(&format!(
            "{tx},{ty},{ux:.2},{uy:.2},{:.2},{:?},{},{},{:.6},{:.4}\n",
            (ux * ux + uy * uy).sqrt(),
            m.status,
            if m.dx.is_nan() {
                String::new()
            } else {
                format!("{:.6}", m.dx)
            },
            if m.dy.is_nan() {
                String::new()
            } else {
                format!("{:.6}", m.dy)
            },
            m.peak,
            m.contrast
        ));
    }
    std::fs::write(&out, rows)?;
    eprintln!(
        "pair ({i},{j}) plant={plant} : {n_ok}/{} tiles ok -> {}",
        spots.len(),
        out.display()
    );
    Ok(())
}

fn main() -> Result<()> {
    let argv: Vec<String> = std::env::args().collect();
    if argv.len() < 2 {
        bail!("usage: m103probe <measure|solve> [--flags]");
    }
    let a = Args::parse(argv[2..].iter().cloned());
    match argv[1].as_str() {
        "measure" => cmd_measure(&a),
        "solve" => cmd_solve(&a),
        "plant" => cmd_plant(&a),
        "tiles" => cmd_tiles(&a),
        other => bail!("unknown subcommand {other}"),
    }
}
