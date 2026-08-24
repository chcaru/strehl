//! M86 — does the alignment module actually align a **deep** focus bracket,
//! and how accurately?
//!
//! The shipped merge combines frames with no geometric registration at all
//! (`stack.rs`: `decode -> calibrate -> Tenengrad`, no alignment stage). This
//! instrument measures whether `strehl_core::align` fixes that, on stacks an
//! order of magnitude deeper than the 105 frames M10 worked with.
//!
//! Not a product path. Additive: it modifies no shared crate code and no
//! shipped behaviour, and it never writes to any capture directory. It does
//! **not** wire alignment into the merge; that is a later, separate step.
//!
//! Subcommands, in the order the pre-registration requires them to be run:
//!
//! | mode | what it answers | needs raw frames |
//! | --- | --- | --- |
//! | `solve-csv` | **G0** — does the Rust solver reproduce M10's held-out ruling from M10's own committed edges? | no |
//! | `edges` | measure a pairwise edge set for a stack, write CSV | yes |
//! | `heldout` | **the accuracy result** — held-out `E*`, graph stats, cycle consistency | no (reads `edges` output) |
//! | `drift` | total corner drift across the bracket — settles the honest-negative branch | no (reads `edges` output) |
//! | `plant` | **C2** — plant a known warp on real frames, verify by read-back, recover it | yes |
//! | `field` | **C1** — interpolator-free recovery of a synthetic field | no |
//! | `resample` | what the resampler costs in high-frequency energy | yes |
//!
//! ```text
//! cargo run --release -p strehl-cli --example m86-align -- solve-csv <EDGES_CSV> --n <FRAMES> --cfg m10 --min-span <S> --min-used <U>
//! cargo run --release -p strehl-cli --example m86-align -- edges <DIR> --out <CSV> [--spans 1,2,4,...] [--limit N]
//! cargo run --release -p strehl-cli --example m86-align -- heldout <EDGES_CSV> --n <FRAMES> --min-span <S> --min-used <U>
//! cargo run --release -p strehl-cli --example m86-align -- drift <EDGES_CSV> --n <FRAMES>
//! cargo run --release -p strehl-cli --example m86-align -- plant <DIR> --scale 1.01 --frames 0,40,80
//! cargo run --release -p strehl-cli --example m86-align -- field --n 299
//! cargo run --release -p strehl-cli --example m86-align -- resample <DIR> --frame 0
//! ```
//!
//! All errors are **plane px at the worst plane corner**, on the CFA-quad green
//! plane, so that they are directly comparable to M10's figures. One plane px
//! is two sensor px.

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use rayon::prelude::*;
use strehl_core::align::{
    AlignConfig, AlignEdge, AlignFrame, AlignPyramid, GlobalOptions, PlaneRef, PolyOptions,
    Resampler, Similarity, SimilarityParams, TranslationModel, Weighting, align_pair,
    corner_radius, cycle_consistency, edge_errors, gather_into, graph_stats, predict, solve_fixed,
    solve_global, solve_hops, solve_poly, tile_grid, total_drift,
};
use strehl_core::plane::{PlaneGeometry, green_luma};

// --------------------------------------------------------------------------
// the edge table, in the schema M10 committed
// --------------------------------------------------------------------------

/// One measured pairwise edge, as stored in
/// `experiments/m10-deep-align/data/*-edges.csv`. The Rust reader must accept
/// M10's file byte-for-byte, because gate G0 is the check that this port did
/// not change the answer.
#[derive(Clone, Debug)]
struct Row {
    /// One measured pair. Provenance of the row. `read_edges` already filters on this, so nothing
    /// downstream consumes it; it is retained so a parsed row round-trips the
    /// full CSV schema rather than silently dropping a column.
    #[allow(dead_code)]
    cfg: String,
    i: usize,
    j: usize,
    span: usize,
    ok: bool,
    t: Similarity,
    rms: f64,
    used: usize,
    lever: f64,
    pw: usize,
    ph: usize,
}

impl Row {
    fn to_edge(&self) -> AlignEdge {
        AlignEdge {
            i: self.i,
            j: self.j,
            t: self.t,
            rms: self.rms,
            used: self.used,
            lever: self.lever,
        }
    }

    /// A pair the estimator refused. Recorded rather than dropped, because the
    /// refusal rate against span is one of the results.
    fn failed(i: usize, j: usize, geom: PlaneGeometry) -> Self {
        Row {
            cfg: String::new(),
            i,
            j,
            span: j - i,
            ok: false,
            t: Similarity::IDENTITY,
            rms: f64::NAN,
            used: 0,
            lever: f64::NAN,
            pw: geom.width,
            ph: geom.height,
        }
    }
}

fn parse_f(s: &str, default: f64) -> f64 {
    if s.is_empty() {
        default
    } else {
        s.parse().unwrap_or(default)
    }
}

fn read_edges(path: &Path, cfg: Option<&str>) -> Result<Vec<Row>> {
    let text = std::fs::read_to_string(path)
        .with_context(|| format!("reading edge table {}", path.display()))?;
    let mut lines = text.lines();
    let header: Vec<&str> = lines
        .next()
        .context("edge table is empty")?
        .trim_end_matches('\r')
        .split(',')
        .collect();
    let col = |name: &str| -> Result<usize> {
        header
            .iter()
            .position(|h| *h == name)
            .with_context(|| format!("edge table has no `{name}` column"))
    };
    let (c_cfg, c_ref, c_mov, c_span, c_status) = (
        col("cfg")?,
        col("ref")?,
        col("mov")?,
        col("span")?,
        col("status")?,
    );
    let (c_g, c_rot, c_ax, c_ay) = (col("g")?, col("rot")?, col("ax")?, col("ay")?);
    let (c_rms, c_used, c_lever) = (col("rms")?, col("used")?, col("lever_rms")?);
    let (c_pw, c_ph) = (col("plane_w")?, col("plane_h")?);

    let mut out = Vec::new();
    for line in lines {
        let line = line.trim_end_matches('\r');
        if line.is_empty() {
            continue;
        }
        let f: Vec<&str> = line.split(',').collect();
        if f.len() != header.len() {
            bail!(
                "edge table row has {} fields, header has {}",
                f.len(),
                header.len()
            );
        }
        if let Some(want) = cfg
            && f[c_cfg] != want
        {
            continue;
        }
        out.push(Row {
            cfg: f[c_cfg].to_string(),
            i: f[c_ref].parse()?,
            j: f[c_mov].parse()?,
            span: f[c_span].parse()?,
            ok: f[c_status] == "ok",
            t: Similarity::from_params(SimilarityParams {
                ax: parse_f(f[c_ax], 0.0),
                ay: parse_f(f[c_ay], 0.0),
                g: parse_f(f[c_g], 0.0),
                rot: parse_f(f[c_rot], 0.0),
            }),
            rms: parse_f(f[c_rms], f64::NAN),
            used: f[c_used].parse().unwrap_or(0),
            lever: parse_f(f[c_lever], f64::NAN),
            pw: f[c_pw].parse().unwrap_or(0),
            ph: f[c_ph].parse().unwrap_or(0),
        });
    }
    Ok(out)
}

fn write_edges(path: &Path, case: &str, cfg: &str, rows: &[Row]) -> Result<()> {
    let mut s = String::new();
    s.push_str("case,cfg,ref,mov,span,status,g,rot,ax,ay,rms,used,lever_rms,plane_w,plane_h\n");
    for r in rows {
        let p = r.t.to_params();
        if r.ok {
            writeln!(
                s,
                "{case},{cfg},{},{},{},ok,{:.9},{:.9},{:.6},{:.6},{:.6},{},{:.4},{},{}",
                r.i, r.j, r.span, p.g, p.rot, p.ax, p.ay, r.rms, r.used, r.lever, r.pw, r.ph
            )?;
        } else {
            writeln!(
                s,
                "{case},{cfg},{},{},{},no-fit,,,,,,{},,{},{}",
                r.i, r.j, r.span, r.used, r.pw, r.ph
            )?;
        }
    }
    std::fs::write(path, s).with_context(|| format!("writing {}", path.display()))?;
    Ok(())
}

// --------------------------------------------------------------------------
// the held-out protocol, replicated from m10_measure.py
// --------------------------------------------------------------------------

/// The twelve named training sets, each guaranteed disjoint from the test set
/// by `(i, j)` key. Replicated exactly from `m10_measure.py::train_sets` --
/// including the "drop the empty ones" rule, because a training set that is
/// empty on one stack and populated on another would silently change which
/// strategies compete for `E*`.
/// Predicate selecting which frame indices a named training subset covers.
/// Boxed because each of M10's twelve named sets is a distinct closure.
type TrainPred = Box<dyn Fn(usize) -> bool>;

fn train_sets(rows: &[Row], test_keys: &[(usize, usize)]) -> Vec<(String, Vec<AlignEdge>)> {
    let is_test = |e: &Row| test_keys.contains(&(e.i, e.j));
    let keep = |pred: &dyn Fn(usize) -> bool| -> Vec<AlignEdge> {
        rows.iter()
            .filter(|e| e.ok && !is_test(e) && pred(e.span))
            .map(|e| e.to_edge())
            .collect()
    };
    let defs: Vec<(&str, TrainPred)> = vec![
        ("chain (span 1)", Box::new(|s| s == 1)),
        ("span <= 2", Box::new(|s| s <= 2)),
        ("span <= 4", Box::new(|s| s <= 4)),
        ("span <= 8", Box::new(|s| s <= 8)),
        ("span <= 16", Box::new(|s| s <= 16)),
        ("span <= 32", Box::new(|s| s <= 32)),
        ("span <= 32, >= 8", Box::new(|s| (8..=32).contains(&s))),
        ("span <= 32, >= 12", Box::new(|s| (12..=32).contains(&s))),
        ("span >= 16", Box::new(|s| s >= 16)),
        ("span >= 24", Box::new(|s| s >= 24)),
        ("span >= 32", Box::new(|s| s >= 32)),
        ("all measurable", Box::new(|_| true)),
    ];
    defs.into_iter()
        .map(|(name, pred)| (name.to_string(), keep(&*pred)))
        .filter(|(_, v)| !v.is_empty())
        .collect()
}

/// The strategy family, replicated from `m10_measure.py::strategies`.
///
/// `S0` places by a single fixed reference, `S1`/`S2` chain in hops of at most
/// `M`, `S3` is the global least squares under three weightings, `S4`/`S5` are
/// the parametric solves, `S6` adds the smoothness prior. The point of keeping
/// all of them rather than only the winner is that the ruling picks the best
/// *full-coverage, non-tree* row from data, and a family with only one member
/// cannot be ruled on.
/// M10's poly ladder. Kept exactly as published so the G0 protocol still
/// produces its 136 candidate rows and reproduces M10's winner.
const POLY_DEFAULT: &[usize] = &[2, 4, 6];

/// The ladder that answers M84b's question. Degree 1 forces the per-frame
/// log-scale increment to be *constant*, which is what a uniform focus step
/// implies; every higher degree is free to let it drift.
const POLY_UNIFORMITY: &[usize] = &[1, 2, 3, 4, 6];

fn strategies(
    train: &[AlignEdge],
    n: usize,
    geom: PlaneGeometry,
    poly_degrees: &[usize],
) -> Vec<(String, Vec<Option<Similarity>>)> {
    let mut out: Vec<(String, Vec<Option<Similarity>>)> = Vec::new();
    out.push(("S0-fixed".into(), solve_fixed(train, n)));
    for m in [1usize, 8, 16, 32] {
        if !train.iter().any(|e| e.span() <= m) {
            continue;
        }
        let (g, _) = solve_hops(train, n, m);
        out.push((format!("S{}-hops{m}", if m == 1 { '1' } else { '2' }), g));
    }
    for (name, w) in [
        ("S3-ba-invvar", Weighting::InverseVariance),
        ("S3-ba-unit", Weighting::Unit),
        ("S3-ba-count", Weighting::Count),
    ] {
        let mut opts = GlobalOptions::new(geom);
        opts.weighting = w;
        if let Some(g) = solve_global(train, n, &opts) {
            out.push((name.into(), g));
        }
    }
    for &d in poly_degrees {
        let mut opts = PolyOptions::new(geom);
        opts.degree = d;
        opts.translation = TranslationModel::Poly(d);
        if let Some(s) = solve_poly(train, n, &opts) {
            out.push((format!("S4-poly{d}"), s.transforms));
        }
    }
    let mut opts = PolyOptions::new(geom);
    opts.degree = 4;
    opts.translation = TranslationModel::FixedCentre;
    if let Some(s) = solve_poly(train, n, &opts) {
        out.push(("S5-centre4".into(), s.transforms));
    }
    let mut opts = GlobalOptions::new(geom);
    opts.weighting = Weighting::Unit;
    opts.smooth = 0.02;
    if let Some(g) = solve_global(train, n, &opts) {
        out.push(("S6-ba-smooth".into(), g));
    }
    out
}

/// One scored held-out prediction.
struct Scored {
    span: usize,
    err: f64,
    scale: f64,
    trans: f64,
}

fn score(g: &[Option<Similarity>], test: &[Row], geom: PlaneGeometry) -> Vec<Scored> {
    test.iter()
        .filter_map(|e| {
            let p = predict(g, e.i, e.j)?;
            let (s, t) = p.corner_err_parts(e.t, geom);
            Some(Scored {
                span: e.span,
                err: p.corner_err(e.t, geom),
                scale: s,
                trans: t,
            })
        })
        .collect()
}

fn median(v: &mut [f64]) -> f64 {
    if v.is_empty() {
        return f64::NAN;
    }
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = v.len();
    if n.is_multiple_of(2) {
        0.5 * (v[n / 2 - 1] + v[n / 2])
    } else {
        v[n / 2]
    }
}

/// Linear-interpolated percentile, matching `numpy.percentile`'s default
/// method. G0 compares against numbers numpy produced, so the percentile rule
/// has to be the same one or the comparison measures the percentile rule.
fn percentile(sorted: &[f64], p: f64) -> f64 {
    if sorted.is_empty() {
        return f64::NAN;
    }
    let idx = (p / 100.0) * (sorted.len() - 1) as f64;
    let lo = idx.floor() as usize;
    let hi = idx.ceil() as usize;
    if lo == hi {
        sorted[lo]
    } else {
        sorted[lo] + (idx - lo as f64) * (sorted[hi] - sorted[lo])
    }
}

/// Ordinary least squares slope and its standard error, for the
/// "does error grow with span" test. Replicated from `m10_ruling.py::ols`.
fn ols(x: &[f64], y: &[f64]) -> (f64, f64) {
    let n = x.len();
    if n < 3 {
        return (f64::NAN, f64::NAN);
    }
    let (xmin, xmax) = x
        .iter()
        .fold((f64::MAX, f64::MIN), |(a, b), v| (a.min(*v), b.max(*v)));
    if xmax - xmin == 0.0 {
        return (f64::NAN, f64::NAN);
    }
    let nf = n as f64;
    let mx = x.iter().sum::<f64>() / nf;
    let my = y.iter().sum::<f64>() / nf;
    let sxx: f64 = x.iter().map(|v| (v - mx) * (v - mx)).sum();
    let sxy: f64 = x.iter().zip(y).map(|(a, b)| (a - mx) * (b - my)).sum();
    let slope = sxy / sxx;
    let icept = my - slope * mx;
    let s2: f64 = x
        .iter()
        .zip(y)
        .map(|(a, b)| {
            let r = b - (slope * a + icept);
            r * r
        })
        .sum::<f64>()
        / (n as f64 - 2.0).max(1.0);
    (slope, (s2 / sxx).max(0.0).sqrt())
}

const T_SOLVED: f64 = 1.0;
const T_USABLE: f64 = 4.0;
const T_CHAIN: f64 = 12.5;

fn cell(e: f64) -> &'static str {
    if e <= T_SOLVED {
        "A/B"
    } else if e <= T_USABLE {
        "B/C/D"
    } else if e <= T_CHAIN {
        "E"
    } else {
        "F"
    }
}

/// One candidate row in the ruling: a (training set, strategy) pair scored on
/// the held-out test edges.
struct Candidate {
    train: String,
    strat: String,
    n: usize,
    cover: usize,
    top_span: usize,
    e_top: f64,
    k_top: usize,
    q: f64,
    e_q: f64,
    k_q: usize,
    med: f64,
    p90: f64,
    mx: f64,
    med_scale: f64,
    med_trans: f64,
    slope: f64,
    slope_se: f64,
    is_tree: bool,
}

/// Run the whole held-out protocol for one (stack, cfg) and return every
/// scored candidate. This is the single place the protocol is implemented;
/// both G0 and the M86 measurements go through it, so they cannot drift apart.
fn run_protocol(
    rows: &[Row],
    n: usize,
    min_span: usize,
    min_used: usize,
    geom: PlaneGeometry,
    verbose: bool,
    poly_degrees: &[usize],
) -> Result<(Vec<Candidate>, usize)> {
    let test: Vec<Row> = rows
        .iter()
        .filter(|e| e.ok && e.span >= min_span && e.used >= min_used)
        .cloned()
        .collect();
    if test.len() < 5 {
        bail!(
            "only {} test edges at span >= {min_span}, used >= {min_used}",
            test.len()
        );
    }
    let test_keys: Vec<(usize, usize)> = test.iter().map(|e| (e.i, e.j)).collect();

    if verbose {
        let mut used: Vec<f64> = test.iter().map(|e| e.used as f64).collect();
        let mut rms: Vec<f64> = test.iter().map(|e| e.rms).collect();
        println!(
            "  test set: {} edges, median {:.0} tiles, median rms {:.2} px, spans {}-{}",
            test.len(),
            median(&mut used),
            median(&mut rms),
            test.iter().map(|e| e.span).min().unwrap(),
            test.iter().map(|e| e.span).max().unwrap(),
        );
    }

    let mut cands = Vec::new();
    for (tname, train) in train_sets(rows, &test_keys) {
        let st = graph_stats(&train, n);
        if verbose {
            println!(
                "\n  train = {tname}: {} edges, cycle rank {}, components {}{}",
                train.len(),
                st.cycle_rank,
                st.components,
                if st.is_tree { "  TREE" } else { "" }
            );
            println!(
                "      {:>15} {:>8} {:>5} {:>8} {:>8} {:>8} {:>8} {:>8}",
                "strategy", "cover", "n", "median", "p90", "max", "scale", "trans"
            );
        }
        for (sname, g) in strategies(&train, n, geom, poly_degrees) {
            let s = score(&g, &test, geom);
            let cover = g.iter().filter(|x| x.is_some()).count();
            if s.is_empty() {
                if verbose {
                    println!("      {sname:>15} {cover:>4}/{n:<3}     0        -       -       -");
                }
                continue;
            }
            let mut errs: Vec<f64> = s.iter().map(|x| x.err).collect();
            let mut spans_f: Vec<f64> = s.iter().map(|x| x.span as f64).collect();
            let mut sc: Vec<f64> = s.iter().map(|x| x.scale).collect();
            let mut tr: Vec<f64> = s.iter().map(|x| x.trans).collect();
            let (slope, slope_se) = ols(&spans_f, &errs);
            let top = s.iter().map(|x| x.span).max().unwrap();
            let mut at_top: Vec<f64> = s.iter().filter(|x| x.span == top).map(|x| x.err).collect();
            spans_f.sort_by(|a, b| a.partial_cmp(b).unwrap());
            let q = percentile(&spans_f, 75.0);
            let mut at_q: Vec<f64> = s
                .iter()
                .filter(|x| x.span as f64 >= q)
                .map(|x| x.err)
                .collect();
            let mut sorted = errs.clone();
            sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
            let c = Candidate {
                train: tname.clone(),
                strat: sname.clone(),
                n: s.len(),
                cover,
                top_span: top,
                k_top: at_top.len(),
                e_top: median(&mut at_top),
                q,
                k_q: at_q.len(),
                e_q: median(&mut at_q),
                med: median(&mut errs),
                p90: percentile(&sorted, 90.0),
                mx: *sorted.last().unwrap(),
                med_scale: median(&mut sc),
                med_trans: median(&mut tr),
                slope,
                slope_se,
                is_tree: st.is_tree,
            };
            if verbose {
                println!(
                    "      {:>15} {:>4}/{:<3} {:>5} {:>8.3} {:>8.3} {:>8.3} {:>8.3} {:>8.3}",
                    c.strat, c.cover, n, c.n, c.med, c.p90, c.mx, c.med_scale, c.med_trans
                );
            }
            cands.push(c);
        }
    }
    Ok((cands, test.len()))
}

/// Apply the pre-registered decision rule mechanically: full-coverage,
/// non-tree rows only; `E*` is the median over the top-span quartile.
fn rule(cands: &[Candidate]) -> Option<&Candidate> {
    let n_all = cands.iter().map(|c| c.n).max()?;
    cands
        .iter()
        .filter(|c| c.n == n_all && !c.is_tree)
        .min_by(|a, b| a.e_q.partial_cmp(&b.e_q).unwrap())
}

fn report_ruling(label: &str, cands: &[Candidate]) {
    match rule(cands) {
        None => println!("  {label}: no non-degenerate full-coverage row"),
        Some(b) => {
            let sig = !b.slope_se.is_nan() && b.slope > 2.0 * b.slope_se;
            println!(
                "  {label}   {} test edges predicted, top span {}",
                b.n, b.top_span
            );
            println!(
                "    best full-coverage row : {} trained on '{}'",
                b.strat, b.train
            );
            println!(
                "    E* registered (span {:<3}) : {:>7.3} px over {:>3} edges  -> cell {}",
                b.top_span,
                b.e_top,
                b.k_top,
                cell(b.e_top)
            );
            println!(
                "    E* robust (span >= {:.0})  : {:>7.3} px over {:>3} edges  -> cell {}",
                b.q,
                b.e_q,
                b.k_q,
                cell(b.e_q)
            );
            println!(
                "    all test spans         : median {:.3} px, p90 {:.3} px, max {:.3} px",
                b.med, b.p90, b.mx
            );
            println!(
                "    slope on test span     : {:+.4} +- {:.4} px/frame   significantly > 0: {}",
                b.slope,
                b.slope_se,
                if sig { "yes" } else { "no" }
            );
            let mut up: Vec<&Candidate> = cands
                .iter()
                .filter(|c| c.n == b.n && !c.is_tree && !std::ptr::eq(*c, b))
                .collect();
            up.sort_by(|a, c| a.e_q.partial_cmp(&c.e_q).unwrap());
            println!("    runners-up by robust E*:");
            for c in up.iter().take(4) {
                println!("      {:>15} on '{}': {:.3} px", c.strat, c.train, c.e_q);
            }
        }
    }
}

// --------------------------------------------------------------------------
// gate G0 — the Rust solver against M10's own committed edges
// --------------------------------------------------------------------------

/// Reproduce M10's held-out ruling from M10's committed edge table.
///
/// This is the cheapest possible falsification of the port: it needs no raw
/// frames, no decode and no estimator. If the Rust solver disagrees with the
/// Python one on the *same* edges, every later number is suspect and nothing
/// else in this milestone is worth running.
fn cmd_solve_csv(args: &[String]) -> Result<()> {
    let mut path: Option<PathBuf> = None;
    let mut n = 0usize;
    let mut cfg = "m10".to_string();
    let mut min_span = 40usize;
    let mut min_used = 12usize;
    let mut expect: Option<f64> = None;
    let mut plane: Option<(usize, usize)> = None;
    let mut it = args.iter();
    while let Some(a) = it.next() {
        match a.as_str() {
            "--n" => n = it.next().context("--n needs a value")?.parse()?,
            "--cfg" => cfg = it.next().context("--cfg needs a value")?.clone(),
            "--min-span" => min_span = it.next().context("--min-span")?.parse()?,
            "--min-used" => min_used = it.next().context("--min-used")?.parse()?,
            "--expect" => expect = Some(it.next().context("--expect")?.parse()?),
            "--plane" => {
                let v = it.next().context("--plane needs WxH")?;
                let (w, h) = v.split_once('x').context("--plane wants WxH")?;
                plane = Some((w.parse()?, h.parse()?));
            }
            other if other.starts_with("--") => bail!("unknown flag {other}"),
            other => path = Some(PathBuf::from(other)),
        }
    }
    let path = path.context("solve-csv needs an edge CSV path")?;
    if n == 0 {
        bail!("--n <frames> is required: the solver cannot infer the bracket depth");
    }
    let rows = read_edges(&path, Some(&cfg))?;
    if rows.is_empty() {
        bail!("no rows with cfg={cfg} in {}", path.display());
    }

    // AGENTS.md rule 7: take the geometry from the data, never assume it.
    let geom = match plane {
        Some((w, h)) => PlaneGeometry {
            width: w,
            height: h,
        },
        None => {
            let (w, h) = (rows[0].pw, rows[0].ph);
            if rows.iter().any(|r| r.pw != w || r.ph != h) {
                bail!("edge table mixes plane geometries; pass --plane WxH to disambiguate");
            }
            if w == 0 || h == 0 {
                bail!("edge table carries no plane geometry; pass --plane WxH");
            }
            PlaneGeometry {
                width: w,
                height: h,
            }
        }
    };

    println!("{}", "=".repeat(92));
    println!("M86 G0 - RUST SOLVER vs M10's COMMITTED EDGES");
    println!("  edges  : {}", path.display());
    println!(
        "  cfg    : {cfg}   {} rows, {} ok, {n} frames",
        rows.len(),
        rows.iter().filter(|r| r.ok).count()
    );
    println!(
        "  plane  : {}x{} px, rho {:.2} px  (from the edge table, not assumed)",
        geom.width,
        geom.height,
        corner_radius(geom)
    );
    println!("  test   : span >= {min_span}, used >= {min_used}");
    println!("  all errors are plane px at the worst plane corner");
    println!("{}", "=".repeat(92));

    let t0 = std::time::Instant::now();
    let (cands, _ntest) = run_protocol(&rows, n, min_span, min_used, geom, true, POLY_DEFAULT)?;
    let solve_ms = t0.elapsed().as_secs_f64() * 1e3;

    println!("\n{}", "=".repeat(92));
    println!("PREREGISTERED DECISION RULE - applied mechanically");
    println!("  T_solved {T_SOLVED} px   T_usable {T_USABLE} px   T_chain {T_CHAIN} px");
    println!("  full-coverage strategies only; tree training graphs excluded");
    println!("{}", "=".repeat(92));
    report_ruling(&format!("cfg={cfg}"), &cands);
    println!(
        "\n  whole protocol ({} candidate rows solved and scored): {:.0} ms",
        cands.len(),
        solve_ms
    );

    if let Some(want) = expect {
        let got = rule(&cands).map(|c| c.e_q).unwrap_or(f64::NAN);
        let d = (got - want).abs();
        println!(
            "\n  GATE G0: E* robust = {got:.3} px, M10 reported {want:.3} px, |delta| = {d:.4} px"
        );
        if d <= 0.05 {
            println!("  GATE G0: PASS (registered bar: |delta| <= 0.05 px)");
        } else {
            println!("  GATE G0: FAIL (registered bar: |delta| <= 0.05 px)");
            bail!("G0 failed: the Rust solver does not reproduce M10's ruling");
        }
    }
    Ok(())
}

// --------------------------------------------------------------------------
// decoding a stack into green planes
// --------------------------------------------------------------------------

/// List a capture directory's frames in filename order.
///
/// Read-only, always: `AGENTS.md` rule 14. Nothing in this instrument opens a
/// capture path for writing, and the caches it does write go under
/// `experiments/M86-alignment/out/`.
fn list_frames(dir: &Path) -> Result<Vec<PathBuf>> {
    let mut v: Vec<PathBuf> = std::fs::read_dir(dir)
        .with_context(|| format!("listing {}", dir.display()))?
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| {
            p.extension()
                .and_then(|s| s.to_str())
                .is_some_and(|s| s.eq_ignore_ascii_case("arw"))
        })
        .collect();
    v.sort();
    if v.is_empty() {
        bail!("no .ARW frames in {}", dir.display());
    }
    Ok(v)
}

/// The decoded green plane of a stack, held as `f32` because the estimator
/// correlates in `f32`.
struct Stack {
    geom: PlaneGeometry,
    planes: Vec<Vec<f32>>,
    black: f32,
    decode_s: f64,
}

/// Decode `paths` into black-subtracted CFA-quad green planes.
///
/// The plane geometry comes from the **decoder's** reported active area, never
/// from a constant: `AGENTS.md` rule 7. Every frame is checked against the
/// first, because a stack that silently changes active area mid-way would
/// otherwise produce a large fake "drift".
fn decode_stack(paths: &[PathBuf], threads: usize) -> Result<Stack> {
    let t0 = std::time::Instant::now();
    let first = strehl_raw::decode(&paths[0])
        .map_err(|e| anyhow::anyhow!("decoding {}: {e}", paths[0].display()))?;
    let geom = PlaneGeometry::from_active(first.active.width, first.active.height);
    let black = first.levels.black as f32;
    let (aw, ah) = (first.active.width, first.active.height);
    drop(first);

    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()
        .context("building the decode pool")?;
    let planes: Vec<Result<Vec<f32>>> = pool.install(|| {
        paths
            .par_iter()
            .map(|p| {
                let f = strehl_raw::decode(p)
                    .map_err(|e| anyhow::anyhow!("decoding {}: {e}", p.display()))?;
                if f.active.width != aw || f.active.height != ah {
                    bail!(
                        "{} has active area {}x{}, but the stack starts at {aw}x{ah}",
                        p.display(),
                        f.active.width,
                        f.active.height
                    );
                }
                let mut plane = vec![0f32; geom.pixels()];
                green_luma(&f, black, &mut plane);
                Ok(plane)
            })
            .collect()
    });
    let planes: Result<Vec<Vec<f32>>> = planes.into_iter().collect();
    Ok(Stack {
        geom,
        planes: planes?,
        black,
        decode_s: t0.elapsed().as_secs_f64(),
    })
}

/// The span ladder: which `(i, j)` pairs to measure.
///
/// M10 measured a dense ladder on 105 frames. At 299 frames a dense ladder is
/// 299*|spans| pairs, so the ladder is a parameter rather than a constant, and
/// the default is stated in the report next to its cost.
fn pair_ladder(n: usize, spans: &[usize]) -> Vec<(usize, usize)> {
    let mut out = Vec::new();
    for &s in spans {
        for i in 0..n.saturating_sub(s) {
            out.push((i, i + s));
        }
    }
    out
}

/// Measure every pair in `pairs`, in parallel across pairs.
///
/// `strehl-core` carries no rayon (it depends only on `thiserror` and
/// `anyhow`), so the estimator is single-threaded by construction and the
/// parallelism lives here, in the caller. That is deliberate: it keeps the
/// measured per-pair cost a real per-pair cost.
fn measure_edges(
    st: &Stack,
    pairs: &[(usize, usize)],
    cfg: &AlignConfig,
    threads: usize,
) -> Result<(Vec<Row>, f64)> {
    let t0 = std::time::Instant::now();
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()
        .context("building the measure pool")?;
    let geom = st.geom;

    // Pyramids are built once per frame, not once per pair: at a dense ladder
    // each frame appears in |spans| pairs and rebuilding would dominate.
    let pyramids: Vec<Option<AlignPyramid>> = pool.install(|| {
        st.planes
            .par_iter()
            .map(|p| PlaneRef::from_geometry(p, geom).and_then(|v| AlignPyramid::build(v, cfg)))
            .collect()
    });

    let spots = {
        let p0 = PlaneRef::from_geometry(&st.planes[0], geom).context("plane view")?;
        tile_grid(
            p0,
            cfg.fine_tile,
            cfg.fine_grid.0,
            cfg.fine_grid.1,
            cfg.margin,
        )
        .context("the fine tile grid does not fit in this plane")?
    };

    let rows: Vec<Row> = pool.install(|| {
        pairs
            .par_iter()
            .map(|&(i, j)| {
                let mk = |k: usize| -> Option<AlignFrame<'_>> {
                    Some(AlignFrame {
                        plane: PlaneRef::from_geometry(&st.planes[k], geom)?,
                        pyramid: pyramids[k].as_ref()?,
                    })
                };
                let (Some(a), Some(b)) = (mk(i), mk(j)) else {
                    return Row::failed(i, j, geom);
                };
                match align_pair(a, b, &spots, cfg) {
                    Ok(f) => Row {
                        cfg: String::new(),
                        i,
                        j,
                        span: j - i,
                        ok: true,
                        t: f.similarity(),
                        rms: f.rms as f64,
                        used: f.used,
                        lever: f.lever_rms as f64,
                        pw: geom.width,
                        ph: geom.height,
                    },
                    Err(_) => Row::failed(i, j, geom),
                }
            })
            .collect()
    });
    Ok((rows, t0.elapsed().as_secs_f64()))
}

/// Measure a stack's pairwise edge set and write it as CSV.
fn cmd_edges(args: &[String]) -> Result<()> {
    let mut dir: Option<PathBuf> = None;
    let mut out: Option<PathBuf> = None;
    let mut case = String::new();
    let mut spans: Vec<usize> = vec![1, 2, 4, 8, 16, 32, 64, 96, 128];
    let mut limit = usize::MAX;
    let mut margin: Option<usize> = None;
    let mut threads = 0usize;
    let mut pairs_from: Option<PathBuf> = None;
    let mut cfg_name = String::from("m86");
    let mut it = args.iter();
    while let Some(a) = it.next() {
        match a.as_str() {
            "--out" => out = Some(PathBuf::from(it.next().context("--out")?)),
            "--case" => case = it.next().context("--case")?.clone(),
            "--limit" => limit = it.next().context("--limit")?.parse()?,
            "--margin" => margin = Some(it.next().context("--margin")?.parse()?),
            "--pairs-from" => pairs_from = Some(PathBuf::from(it.next().context("--pairs-from")?)),
            "--cfg-name" => cfg_name = it.next().context("--cfg-name")?.clone(),
            "--threads" => threads = it.next().context("--threads")?.parse()?,
            "--spans" => {
                spans = it
                    .next()
                    .context("--spans")?
                    .split(',')
                    .map(|s| s.trim().parse::<usize>())
                    .collect::<std::result::Result<_, _>>()?;
            }
            other if other.starts_with("--") => bail!("unknown flag {other}"),
            other => dir = Some(PathBuf::from(other)),
        }
    }
    let dir = dir.context("edges needs a capture directory")?;
    let out = out.context("edges needs --out <CSV>")?;
    if case.is_empty() {
        case = dir
            .file_name()
            .and_then(|s| s.to_str())
            .unwrap_or("unknown")
            .to_string();
    }
    let threads = if threads == 0 {
        std::thread::available_parallelism()
            .map(|v| v.get())
            .unwrap_or(8)
    } else {
        threads
    };

    let mut paths = list_frames(&dir)?;
    paths.truncate(limit);
    let n = paths.len();
    println!("{}", "=".repeat(92));
    println!("M86 EDGE MEASUREMENT - {case}");
    println!("  frames : {n} from {}", dir.display());
    println!("  threads: {threads}");
    println!("{}", "=".repeat(92));

    let st = decode_stack(&paths, threads)?;
    println!(
        "  decoded {n} frames in {:.1} s ({:.0} ms/frame wall, {threads} threads)",
        st.decode_s,
        1e3 * st.decode_s / n as f64
    );
    println!(
        "  plane  : {}x{} px (from the decoder's active area), black {} DN, rho {:.1} px",
        st.geom.width,
        st.geom.height,
        st.black,
        corner_radius(st.geom)
    );
    println!(
        "  memory : {:.2} GiB of green planes held",
        (n as f64 * st.geom.pixels() as f64 * 4.0) / (1024.0 * 1024.0 * 1024.0)
    );

    let mut cfg = AlignConfig::deep();
    if let Some(m) = margin {
        cfg = cfg.with_margin(m);
    }
    let spans: Vec<usize> = spans.into_iter().filter(|s| *s > 0 && *s < n).collect();
    let pairs = match &pairs_from {
        // Gate G1 must measure the *same* pairs the reference table measured,
        // or the comparison is confounded by which pairs each side chose.
        Some(p) => {
            let ref_rows = read_edges(p, None)?;
            let mut v: Vec<(usize, usize)> = ref_rows
                .iter()
                .filter(|r| r.i < n && r.j < n)
                .map(|r| (r.i, r.j))
                .collect();
            v.sort_unstable();
            v.dedup();
            println!("  pairs  : {} taken from {}", v.len(), p.display());
            v
        }
        None => pair_ladder(n, &spans),
    };
    println!(
        "  ladder : spans {:?} -> {} pairs, margin {} px",
        spans,
        pairs.len(),
        cfg.margin
    );

    let (rows, meas_s) = measure_edges(&st, &pairs, &cfg, threads)?;
    let ok = rows.iter().filter(|r| r.ok).count();
    println!(
        "\n  measured {} pairs in {:.1} s ({:.1} ms/pair wall, {:.1} ms/pair core-time)",
        rows.len(),
        meas_s,
        1e3 * meas_s / rows.len() as f64,
        1e3 * meas_s * threads as f64 / rows.len() as f64
    );
    println!(
        "  {ok} fitted, {} refused ({:.1}%)",
        rows.len() - ok,
        100.0 * (rows.len() - ok) as f64 / rows.len() as f64
    );

    // Per-span census: where does the estimator stop being able to correlate?
    println!(
        "\n  {:>6} {:>7} {:>7} {:>9} {:>9} {:>9}",
        "span", "pairs", "ok", "med rms", "med used", "med |g|"
    );
    for &s in &spans {
        let sub: Vec<&Row> = rows.iter().filter(|r| r.span == s).collect();
        let fit: Vec<&&Row> = sub.iter().filter(|r| r.ok).collect();
        if fit.is_empty() {
            println!(
                "  {s:>6} {:>7} {:>7} {:>9} {:>9} {:>9}",
                sub.len(),
                0,
                "-",
                "-",
                "-"
            );
            continue;
        }
        let mut rms: Vec<f64> = fit.iter().map(|r| r.rms).collect();
        let mut used: Vec<f64> = fit.iter().map(|r| r.used as f64).collect();
        let mut g: Vec<f64> = fit.iter().map(|r| r.t.to_params().g.abs()).collect();
        println!(
            "  {s:>6} {:>7} {:>7} {:>9.3} {:>9.0} {:>9.5}",
            sub.len(),
            fit.len(),
            median(&mut rms),
            median(&mut used),
            median(&mut g)
        );
    }

    if let Some(p) = out.parent() {
        std::fs::create_dir_all(p).ok();
    }
    write_edges(&out, &case, &cfg_name, &rows)?;
    println!("\n  wrote {} rows to {}", rows.len(), out.display());
    Ok(())
}

// --------------------------------------------------------------------------
// the accuracy result, and the honest-negative branch
// --------------------------------------------------------------------------

/// Read an M86 edge table and run the full held-out protocol on it.
fn cmd_heldout(args: &[String]) -> Result<()> {
    let mut path: Option<PathBuf> = None;
    let mut n = 0usize;
    let mut min_span = 40usize;
    let mut min_used = 12usize;
    // Off by default: adding degrees changes the candidate row count, and G0's
    // reproduction of M10 depends on that count being exactly M10's.
    let mut uniformity = false;
    let mut it = args.iter();
    while let Some(a) = it.next() {
        match a.as_str() {
            "--n" => n = it.next().context("--n")?.parse()?,
            "--min-span" => min_span = it.next().context("--min-span")?.parse()?,
            "--min-used" => min_used = it.next().context("--min-used")?.parse()?,
            "--uniformity" => uniformity = true,
            other if other.starts_with("--") => bail!("unknown flag {other}"),
            other => path = Some(PathBuf::from(other)),
        }
    }
    let path = path.context("heldout needs an edge CSV")?;
    let rows = read_edges(&path, None)?;
    if n == 0 {
        n = rows.iter().map(|r| r.j + 1).max().context("empty table")?;
    }
    let geom = PlaneGeometry {
        width: rows[0].pw,
        height: rows[0].ph,
    };
    println!("{}", "=".repeat(92));
    println!("M86 HELD-OUT PREDICTION OF TRUSTWORTHY LONG EDGES");
    println!(
        "  edges  : {}  ({} rows, {} ok)",
        path.display(),
        rows.len(),
        rows.iter().filter(|r| r.ok).count()
    );
    println!("  frames : {n}");
    println!(
        "  plane  : {}x{} px, rho {:.1} px",
        geom.width,
        geom.height,
        corner_radius(geom)
    );
    println!("  test   : span >= {min_span}, used >= {min_used}");
    println!("  all errors are plane px at the worst plane corner");
    println!("{}", "=".repeat(92));

    let t0 = std::time::Instant::now();
    let ladder = if uniformity {
        POLY_UNIFORMITY
    } else {
        POLY_DEFAULT
    };
    let (cands, _) = run_protocol(&rows, n, min_span, min_used, geom, true, ladder)?;
    let ms = t0.elapsed().as_secs_f64() * 1e3;

    println!("\n{}", "=".repeat(92));
    println!("PREREGISTERED DECISION RULE - applied mechanically");
    println!("  T_solved {T_SOLVED} px   T_usable {T_USABLE} px   T_chain {T_CHAIN} px");
    println!("  full-coverage strategies only; tree training graphs excluded");
    println!("{}", "=".repeat(92));
    report_ruling("ruling", &cands);
    println!(
        "\n  whole protocol: {:.0} ms over {} candidate rows",
        ms,
        cands.len()
    );
    Ok(())
}

/// The honest-negative branch: how far does the field actually move across the
/// whole bracket, and is the recovered track smooth (real breathing) or noisy
/// (estimation error)?
///
/// Pre-registration section 4.2: if the total corner drift is at or below
/// `T_usable`, breathing is not why these stacks look soft and M86 must say so.
fn cmd_drift(args: &[String]) -> Result<()> {
    let mut path: Option<PathBuf> = None;
    let mut n = 0usize;
    let mut it = args.iter();
    while let Some(a) = it.next() {
        match a.as_str() {
            "--n" => n = it.next().context("--n")?.parse()?,
            other if other.starts_with("--") => bail!("unknown flag {other}"),
            other => path = Some(PathBuf::from(other)),
        }
    }
    let path = path.context("drift needs an edge CSV")?;
    let rows = read_edges(&path, None)?;
    if n == 0 {
        n = rows.iter().map(|r| r.j + 1).max().context("empty table")?;
    }
    let geom = PlaneGeometry {
        width: rows[0].pw,
        height: rows[0].ph,
    };
    let rho = corner_radius(geom);
    let edges: Vec<AlignEdge> = rows.iter().filter(|r| r.ok).map(|r| r.to_edge()).collect();
    let st = graph_stats(&edges, n);

    println!("{}", "=".repeat(92));
    println!("M86 TOTAL FIELD DRIFT ACROSS THE BRACKET");
    println!("  edges  : {}", path.display());
    println!(
        "  graph  : {} frames, {} usable edges, cycle rank {}, {} component(s){}",
        st.n_frames,
        st.n_edges,
        st.cycle_rank,
        st.components,
        if st.is_tree { ", TREE" } else { "" }
    );
    println!(
        "  plane  : {}x{} px, rho {rho:.1} px",
        geom.width, geom.height
    );
    println!("{}", "=".repeat(92));

    // The raw data's own consistency floor, before any solver is involved.
    let trip = cycle_consistency(&edges, geom, 4000);
    if !trip.is_empty() {
        let mut e: Vec<f64> = trip.iter().map(|t| t.err).collect();
        let mut s: Vec<f64> = trip.iter().map(|t| t.err_scale).collect();
        let mut t: Vec<f64> = trip.iter().map(|t| t.err_trans).collect();
        let med = median(&mut e);
        let mut sorted = e.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
        println!(
            "\n  cycle consistency of the RAW edges ({} triples, no solver):",
            trip.len()
        );
        println!(
            "    median {med:.3} px, p90 {:.3} px, max {:.3} px  (scale {:.3}, trans {:.3})",
            percentile(&sorted, 90.0),
            sorted.last().copied().unwrap_or(f64::NAN),
            median(&mut s),
            median(&mut t)
        );
        println!(
            "    this is the floor: no solver can predict an edge better than the\n\
             \x20   edges agree with each other."
        );
    }

    for (name, mut opts) in [
        ("S3-ba-unit", GlobalOptions::new(geom)),
        ("S6-ba-smooth", GlobalOptions::new(geom)),
    ] {
        opts.weighting = Weighting::Unit;
        if name == "S6-ba-smooth" {
            opts.smooth = 0.02;
        }
        let Some(g) = solve_global(&edges, n, &opts) else {
            println!("\n  {name}: no solution (system not full rank)");
            continue;
        };
        let cover = g.iter().filter(|x| x.is_some()).count();
        let drift = total_drift(&g, geom);
        println!("\n  {name}: {cover}/{n} frames placed");
        println!(
            "    total corner drift frame 0 -> {}: {drift:.3} plane px",
            n - 1
        );

        // The scale track, and whether it is smooth or noisy. Real breathing is
        // monotonic in focus; estimation error is not.
        let mut gs: Vec<Option<f64>> = Vec::with_capacity(n);
        for t in g.iter() {
            gs.push(t.map(|t| t.scale() - 1.0));
        }
        let known: Vec<(usize, f64)> = gs
            .iter()
            .enumerate()
            .filter_map(|(i, v)| v.map(|x| (i, x)))
            .collect();
        if known.len() >= 3 {
            let last = known.last().unwrap().1;
            println!(
                "    scale at the last frame: {:+.5} ({:+.3} plane px at the corner)",
                last,
                last * rho
            );
            // Second difference: a smooth track has a small one. Reported in
            // plane px so it is comparable with everything else.
            let mut d2: Vec<f64> = Vec::new();
            let mut nonmono = 0usize;
            for w in known.windows(3) {
                d2.push(((w[0].1 - 2.0 * w[1].1 + w[2].1) * rho).abs());
            }
            for w in known.windows(2) {
                if (w[1].1 - w[0].1) * last < 0.0 {
                    nonmono += 1;
                }
            }
            let mut d2s = d2.clone();
            d2s.sort_by(|a, b| a.partial_cmp(b).unwrap());
            println!(
                "    scale track roughness |d2g|*rho: median {:.4} px, p90 {:.4} px, max {:.4} px",
                median(&mut d2),
                percentile(&d2s, 90.0),
                d2s.last().copied().unwrap_or(f64::NAN)
            );
            println!(
                "    steps against the overall direction: {nonmono}/{} ({:.0}% -- 0% is perfectly monotonic)",
                known.len() - 1,
                100.0 * nonmono as f64 / (known.len() - 1) as f64
            );
        }

        // Residual of the solve against every measured edge: fit error, which
        // is NOT the accuracy claim, but does say whether the model fits.
        let errs = edge_errors(&g, &edges, geom);
        if !errs.is_empty() {
            let mut e: Vec<f64> = errs.iter().map(|x| x.err).collect();
            let mut sorted = e.clone();
            sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
            println!(
                "    in-sample residual vs all edges: median {:.3} px, p90 {:.3} px, max {:.3} px",
                median(&mut e),
                percentile(&sorted, 90.0),
                sorted.last().copied().unwrap()
            );
        }
    }
    Ok(())
}

// --------------------------------------------------------------------------
// gate G1 — the Rust estimator against M10's committed fits
// --------------------------------------------------------------------------

/// Compare two edge tables pair-for-pair.
///
/// Gate G1: the port must reproduce `M10:`'s own fits on `M10:`'s own frames.
/// This is a stronger check than G0 because it exercises the correlator, the
/// tile grid, the refusal rules and the parabolic peak, none of which G0
/// touches.
fn cmd_compare(args: &[String]) -> Result<()> {
    let mut a: Option<PathBuf> = None;
    let mut b: Option<PathBuf> = None;
    let mut cfg_a: Option<String> = None;
    let mut bar = 0.19f64;
    let mut min_shared = 200usize;
    let mut it = args.iter();
    while let Some(x) = it.next() {
        match x.as_str() {
            "--cfg-a" => cfg_a = Some(it.next().context("--cfg-a")?.clone()),
            "--bar" => bar = it.next().context("--bar")?.parse()?,
            "--min-shared" => min_shared = it.next().context("--min-shared")?.parse()?,
            other if other.starts_with("--") => bail!("unknown flag {other}"),
            other if a.is_none() => a = Some(PathBuf::from(other)),
            other => b = Some(PathBuf::from(other)),
        }
    }
    let (pa, pb) = (
        a.context("compare needs a reference CSV")?,
        b.context("compare needs a second CSV")?,
    );
    let ra = read_edges(&pa, cfg_a.as_deref())?;
    let rb = read_edges(&pb, None)?;
    let geom = PlaneGeometry {
        width: ra[0].pw,
        height: ra[0].ph,
    };
    if rb[0].pw != geom.width || rb[0].ph != geom.height {
        bail!(
            "plane geometries differ: {}x{} vs {}x{}",
            geom.width,
            geom.height,
            rb[0].pw,
            rb[0].ph
        );
    }

    let idx: std::collections::HashMap<(usize, usize), &Row> =
        rb.iter().map(|r| ((r.i, r.j), r)).collect();
    let mut diffs: Vec<(usize, f64)> = Vec::new();
    let (mut shared, mut agree_status, mut both_ok) = (0usize, 0usize, 0usize);
    for x in &ra {
        let Some(y) = idx.get(&(x.i, x.j)) else {
            continue;
        };
        shared += 1;
        if x.ok == y.ok {
            agree_status += 1;
        }
        if x.ok && y.ok {
            both_ok += 1;
            diffs.push((x.span, x.t.corner_err(y.t, geom)));
        }
    }

    println!("{}", "=".repeat(92));
    println!("M86 G1 - RUST ESTIMATOR vs A REFERENCE EDGE TABLE");
    println!(
        "  reference : {}{}",
        pa.display(),
        cfg_a.map(|c| format!("  (cfg {c})")).unwrap_or_default()
    );
    println!("  measured  : {}", pb.display());
    println!(
        "  plane     : {}x{} px, rho {:.1} px",
        geom.width,
        geom.height,
        corner_radius(geom)
    );
    println!("{}", "=".repeat(92));
    if shared == 0 {
        bail!("the two tables share no (i, j) pairs");
    }
    let status_frac = agree_status as f64 / shared as f64;
    println!("  shared pairs        : {shared}");
    println!(
        "  agree on ok/no-fit  : {agree_status}/{shared} ({:.1}%)",
        100.0 * status_frac
    );
    println!("  both fitted         : {both_ok}");
    if diffs.is_empty() {
        bail!("no pair is fitted in both tables");
    }
    let mut e: Vec<f64> = diffs.iter().map(|d| d.1).collect();
    let mut sorted = e.clone();
    sorted.sort_by(|p, q| p.partial_cmp(q).unwrap());
    let med = median(&mut e);
    println!(
        "  corner difference   : median {med:.4} px, p90 {:.4} px, max {:.4} px",
        percentile(&sorted, 90.0),
        sorted.last().copied().unwrap()
    );

    // Difference against span: a constant offset is a port bug, a difference
    // that grows with span is the estimator's own noise being sampled twice.
    println!(
        "\n  {:>10} {:>7} {:>10} {:>10}",
        "span band", "n", "median", "p90"
    );
    for (lo, hi) in [(1usize, 4usize), (5, 16), (17, 32), (33, 64), (65, 1000)] {
        let mut v: Vec<f64> = diffs
            .iter()
            .filter(|d| d.0 >= lo && d.0 <= hi)
            .map(|d| d.1)
            .collect();
        if v.is_empty() {
            continue;
        }
        let mut s = v.clone();
        s.sort_by(|p, q| p.partial_cmp(q).unwrap());
        println!(
            "  {:>10} {:>7} {:>10.4} {:>10.4}",
            format!(
                "{lo}-{}",
                if hi > 999 {
                    "max".into()
                } else {
                    hi.to_string()
                }
            ),
            v.len(),
            median(&mut v),
            percentile(&s, 90.0)
        );
    }

    let pass = shared >= min_shared && med <= bar && status_frac >= 0.95;
    println!(
        "\n  GATE G1: median {med:.4} px vs bar {bar:.2} px; {shared} shared (need {min_shared}); \
         status agreement {:.1}% (need 95.0%)",
        100.0 * status_frac
    );
    if pass {
        println!("  GATE G1: PASS");
        Ok(())
    } else {
        println!("  GATE G1: FAIL");
        bail!("G1 failed")
    }
}

// --------------------------------------------------------------------------
// C1 — the estimator floor, with no interpolator anywhere
// --------------------------------------------------------------------------

/// A band-limited analytic field, evaluated in closed form at any real
/// coordinate.
///
/// This is what makes C1 interpolator-free. `M23:` fact 172 measured that a
/// bilinear resampler is itself a lowpass strong enough to read a zero-defocus
/// self-pair's response as 0.372 where the truth is 1.000, so any plant built
/// by resampling measures the resampler as much as the estimator. Here the
/// "warped" frame is not resampled at all: it is the *same* analytic function
/// evaluated at transformed coordinates, so the only thing between the plant
/// and the measurement is the estimator.
struct BandLimited {
    waves: Vec<(f64, f64, f64, f64)>,
}

impl BandLimited {
    fn new(seed: u64, n: usize, max_cycles_per_px: f64) -> Self {
        let mut s = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
        let mut next = || {
            s = s
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            ((s >> 11) as f64) / ((1u64 << 53) as f64)
        };
        let waves = (0..n)
            .map(|_| {
                let theta = next() * std::f64::consts::TAU;
                // Uniform in frequency magnitude up to the stated band limit,
                // with a floor so the field is not all DC.
                let f = (0.15 + 0.85 * next()) * max_cycles_per_px * std::f64::consts::TAU;
                (
                    f * theta.cos(),
                    f * theta.sin(),
                    next() * std::f64::consts::TAU,
                    0.4 + next(),
                )
            })
            .collect();
        BandLimited { waves }
    }

    fn at(&self, x: f64, y: f64) -> f32 {
        let mut v = 0.0;
        for (u, w, p, a) in &self.waves {
            v += a * (u * x + w * y + p).cos();
        }
        (1000.0 + 120.0 * v) as f32
    }

    /// Render the field into a plane, sampling **through** `t`: pixel `p` of
    /// the output holds the field at `t(p)`. No interpolation is involved.
    fn render(&self, geom: PlaneGeometry, t: Similarity) -> Vec<f32> {
        let (cx, cy) = (geom.width as f64 / 2.0, geom.height as f64 / 2.0);
        let mut out = vec![0f32; geom.pixels()];
        for y in 0..geom.height {
            for x in 0..geom.width {
                let (sx, sy) = t.apply_at(x as f64, y as f64, cx, cy);
                out[y * geom.width + x] = self.at(sx, sy);
            }
        }
        out
    }
}

/// C1: does the estimator recover a planted scale, with no resampler anywhere
/// in the loop?
fn cmd_field(args: &[String]) -> Result<()> {
    let mut w = 3516usize;
    let mut h = 2344usize;
    let mut seed = 20250607u64;
    let mut it = args.iter();
    while let Some(a) = it.next() {
        match a.as_str() {
            "--plane" => {
                let v = it.next().context("--plane WxH")?;
                let (a, b) = v.split_once('x').context("--plane wants WxH")?;
                w = a.parse()?;
                h = b.parse()?;
            }
            "--seed" => seed = it.next().context("--seed")?.parse()?,
            other => bail!("unknown flag {other}"),
        }
    }
    let geom = PlaneGeometry {
        width: w,
        height: h,
    };
    let rho = corner_radius(geom);
    let cfg = AlignConfig::deep();
    let field = BandLimited::new(seed, 48, 0.12);

    println!("{}", "=".repeat(92));
    println!("M86 C1 - ESTIMATOR FLOOR, NO INTERPOLATOR ANYWHERE");
    println!("  plane {w}x{h}, rho {rho:.1} px, band limit 0.12 cycles/px");
    println!("  both frames are the SAME analytic field evaluated at different");
    println!("  coordinates, so no resampler touches either one (M23: fact 172).");
    println!("{}", "=".repeat(92));

    let base = field.render(geom, Similarity::IDENTITY);
    let bp = PlaneRef::from_geometry(&base, geom).context("plane view")?;
    let bpy = AlignPyramid::build(bp, &cfg).context("pyramid")?;
    let spots = tile_grid(
        bp,
        cfg.fine_tile,
        cfg.fine_grid.0,
        cfg.fine_grid.1,
        cfg.margin,
    )
    .context("tile grid")?;

    println!(
        "\n  {:>10} {:>12} {:>12} {:>10} {:>10} {:>9} {:>7}",
        "planted g", "planted px", "recovered", "ratio", "err px", "rms px", "tiles"
    );
    let mut worst_ratio_err = 0.0f64;
    for &(g, ax, ay) in &[
        (0.0, 0.0, 0.0),
        (0.001, 0.0, 0.0),
        (0.002, 3.0, -2.0),
        (0.005, 0.0, 0.0),
        (0.010, -7.0, 4.0),
        (0.020, 0.0, 0.0),
        (0.046, 11.0, -6.0),
        (0.100, 0.0, 0.0),
    ] {
        let planted = Similarity::from_params(SimilarityParams {
            ax,
            ay,
            g,
            rot: 0.0,
        });
        let moved = field.render(geom, planted);
        let mp = PlaneRef::from_geometry(&moved, geom).context("plane view")?;
        let mpy = AlignPyramid::build(mp, &cfg).context("pyramid")?;
        let a = AlignFrame {
            plane: bp,
            pyramid: &bpy,
        };
        let b = AlignFrame {
            plane: mp,
            pyramid: &mpy,
        };
        // `render(geom, t)` samples the field at `t(p)`, so the rendered frame
        // is the base warped by `t^-1`: the transform the estimator should
        // report for base -> moved is the INVERSE of the planted one. Getting
        // this backwards is exactly the linearisation trap -- at g = 0.046 the
        // difference between `-g` and `1/(1+g) - 1` is 4.3 plane px, the same
        // size as the effect. The expectation is therefore built with the
        // exact inverse, never with `-g`.
        let expect = planted.invert().context("planted transform is singular")?;
        let planted_px = expect.corner_err(Similarity::IDENTITY, geom);
        let expect_g = expect.scale() - 1.0;
        match align_pair(a, b, &spots, &cfg) {
            Ok(f) => {
                let rec = f.similarity();
                let err = rec.corner_err(expect, geom);
                let ratio = if expect_g.abs() > 1e-12 {
                    (rec.scale() - 1.0) / expect_g
                } else {
                    f64::NAN
                };
                if ratio.is_finite() {
                    worst_ratio_err = worst_ratio_err.max((ratio - 1.0).abs());
                }
                println!(
                    "  {g:>10.4} {planted_px:>12.3} {:>12.6} {ratio:>10.4} {err:>10.4} {:>9.3} {:>7}",
                    rec.scale() - 1.0,
                    f.rms,
                    f.used
                );
            }
            Err(e) => println!("  {g:>10.4} {planted_px:>12.3}   REFUSED: {e:?}"),
        }
    }
    println!("\n  GATE C1: worst |ratio - 1| = {worst_ratio_err:.4}  (registered bar: <= 0.02)");
    if worst_ratio_err <= 0.02 {
        println!("  GATE C1: PASS");
        Ok(())
    } else {
        println!("  GATE C1: FAIL");
        bail!("C1 failed: the estimator's scale gain is not unity on a clean field")
    }
}

// --------------------------------------------------------------------------
// C2 — a planted warp on real frames, and the defocus-asymmetry gain probe
// --------------------------------------------------------------------------

/// C2 plus the question M12, M23 and M78 all circle: **is the estimator's
/// scale gain still unity when the two frames are at different defocus?**
///
/// The design isolates that. For a base pair `(i, j)` the instrument measures
/// `T(i -> j)` and then `T(i -> warp(j, s))` for a ladder of planted scales
/// `s`. The *increment* between those two fits must equal `s` exactly,
/// whatever the defocus gap between `i` and `j` does to the fit itself. Any
/// systematic departure of the increment from `s` is a multiplicative gain
/// error -- precisely the shrinkage M12 tried and failed to correct with a
/// fitted scalar.
///
/// Running the same ladder at `j = i` (zero defocus gap) and at increasing
/// gaps turns "does defocus bias the scale?" into a measured curve.
///
/// The plant is applied to a **copy held in memory**; no capture file is
/// opened for writing. Its correctness is verified by read-back before any
/// fit is attempted.
fn cmd_plant(args: &[String]) -> Result<()> {
    let mut dir: Option<PathBuf> = None;
    let mut bases: Vec<usize> = vec![40, 100, 160, 220];
    let mut gaps: Vec<usize> = vec![0, 1, 2, 4, 8, 16, 32];
    let mut scales: Vec<f64> = vec![1.002, 1.005, 1.01, 1.02];
    let mut resampler = Resampler::CatmullRom;
    let mut threads = 0usize;
    let mut it = args.iter();
    let numlist = |s: &String| -> Result<Vec<usize>> {
        Ok(s.split(',')
            .map(|v| v.trim().parse::<usize>())
            .collect::<std::result::Result<_, _>>()?)
    };
    while let Some(a) = it.next() {
        match a.as_str() {
            "--bases" => bases = numlist(it.next().context("--bases")?)?,
            "--gaps" => gaps = numlist(it.next().context("--gaps")?)?,
            "--threads" => threads = it.next().context("--threads")?.parse()?,
            "--scales" => {
                scales = it
                    .next()
                    .context("--scales")?
                    .split(',')
                    .map(|s| s.trim().parse::<f64>())
                    .collect::<std::result::Result<_, _>>()?;
            }
            "--resampler" => {
                resampler = match it.next().context("--resampler")?.as_str() {
                    "nearest" => Resampler::Nearest,
                    "bilinear" => Resampler::Bilinear,
                    "catmull-rom" => Resampler::CatmullRom,
                    o => bail!("unknown resampler {o}"),
                }
            }
            other if other.starts_with("--") => bail!("unknown flag {other}"),
            other => dir = Some(PathBuf::from(other)),
        }
    }
    let dir = dir.context("plant needs a capture directory")?;
    if !gaps.contains(&0) {
        bail!("--gaps must include 0: that is the C2 arm");
    }
    let threads = if threads == 0 {
        std::thread::available_parallelism()
            .map(|v| v.get())
            .unwrap_or(8)
    } else {
        threads
    };

    let all = list_frames(&dir)?;
    let mut want: Vec<usize> = Vec::new();
    for &b in &bases {
        for &g in &gaps {
            if b + g < all.len() {
                want.push(b);
                want.push(b + g);
            }
        }
    }
    want.sort_unstable();
    want.dedup();
    if want.is_empty() {
        bail!(
            "no requested (base, gap) pair fits in the {} frames",
            all.len()
        );
    }
    let paths: Vec<PathBuf> = want.iter().map(|k| all[*k].clone()).collect();
    let st = decode_stack(&paths, threads)?;
    let geom = st.geom;
    let rho = corner_radius(geom);
    let cfg = AlignConfig::deep();
    let idx = |k: usize| want.iter().position(|w| *w == k);

    println!("{}", "=".repeat(92));
    println!("M86 C2 - PLANTED WARP ON REAL FRAMES, AND THE DEFOCUS-ASYMMETRY GAIN");
    println!("  stack     : {} ({} frames)", dir.display(), all.len());
    println!("  bases     : {bases:?}");
    println!("  gaps      : {gaps:?}");
    println!("  scales    : {scales:?}");
    println!(
        "  plane     : {}x{} px, rho {rho:.1} px",
        geom.width, geom.height
    );
    println!("  resampler : {resampler:?}");
    println!(
        "  {} frames decoded; the plant is applied to an in-memory copy, and",
        want.len()
    );
    println!("  no capture file is opened for writing.");
    println!("{}", "=".repeat(92));
    println!(
        "\n  `gather_into(p, t, ..)` fills output pixel q from source `t(q)`, so the\n\
         \x20 warped frame is the source warped by t^-1. The expected increment is\n\
         \x20 therefore 1/s - 1, built with the EXACT inverse: at s = 1.02 the\n\
         \x20 difference between -(s-1) and 1/s-1 is {:.2} plane px, which is larger\n\
         \x20 than the whole effect being measured.",
        ((1.0f64 / 1.02 - 1.0) + 0.02).abs() * rho
    );

    // gap -> observed gains
    let mut by_gap: BTreeMap<usize, Vec<f64>> = BTreeMap::new();
    let mut by_scale: BTreeMap<i64, Vec<f64>> = BTreeMap::new();
    let mut n_refused = 0usize;

    let spots0 = {
        let p = PlaneRef::from_geometry(&st.planes[0], geom).context("plane view")?;
        tile_grid(
            p,
            cfg.fine_tile,
            cfg.fine_grid.0,
            cfg.fine_grid.1,
            cfg.margin,
        )
        .context("tile grid")?
    };

    for &b in &bases {
        let Some(bi) = idx(b) else { continue };
        let bp = PlaneRef::from_geometry(&st.planes[bi], geom).context("plane view")?;
        let bpy = AlignPyramid::build(bp, &cfg).context("pyramid")?;
        for &gap in &gaps {
            let j = b + gap;
            let Some(ji) = idx(j) else { continue };
            let jp = PlaneRef::from_geometry(&st.planes[ji], geom).context("plane view")?;
            let jpy = AlignPyramid::build(jp, &cfg).context("pyramid")?;
            let Ok(bf) = align_pair(
                AlignFrame {
                    plane: bp,
                    pyramid: &bpy,
                },
                AlignFrame {
                    plane: jp,
                    pyramid: &jpy,
                },
                &spots0,
                &cfg,
            ) else {
                n_refused += 1;
                continue;
            };
            for &s in &scales {
                let plant = Similarity::from_params(SimilarityParams {
                    ax: 0.0,
                    ay: 0.0,
                    g: s - 1.0,
                    rot: 0.0,
                });
                let expect = plant.invert().context("planted transform is singular")?;
                let expect_g = expect.scale() - 1.0;
                let mut warped = vec![0f32; geom.pixels()];
                gather_into(jp, plant, geom, resampler, &mut warped);
                let wp = PlaneRef::from_geometry(&warped, geom).context("plane view")?;

                // Read-back: a plant that silently did nothing would look like
                // a total gain failure, so it is refused loudly instead.
                let mut moved = 0.0f64;
                let mut np = 0usize;
                for gy in 1..8 {
                    for gx in 1..8 {
                        let x = geom.width * gx / 8;
                        let y = geom.height * gy / 8;
                        moved += (wp.at(x, y) - jp.at(x, y)).abs() as f64;
                        np += 1;
                    }
                }
                let mean_delta = moved / np as f64;
                if mean_delta < 1e-6 {
                    bail!("the plant s = {s} changed nothing: mean |delta| = {mean_delta:.3e} DN");
                }

                let wpy = AlignPyramid::build(wp, &cfg).context("pyramid")?;
                match align_pair(
                    AlignFrame {
                        plane: bp,
                        pyramid: &bpy,
                    },
                    AlignFrame {
                        plane: wp,
                        pyramid: &wpy,
                    },
                    &spots0,
                    &cfg,
                ) {
                    Ok(f) => {
                        let Some(inc) = Similarity::relative(bf.similarity(), f.similarity())
                        else {
                            n_refused += 1;
                            continue;
                        };
                        let gain = (inc.scale() - 1.0) / expect_g;
                        by_gap.entry(gap).or_default().push(gain);
                        by_scale
                            .entry(((s - 1.0) * 1e9).round() as i64)
                            .or_default()
                            .push(gain);
                    }
                    Err(_) => n_refused += 1,
                }
            }
        }
    }

    println!(
        "\n  Recovered gain = (measured increment) / (1/s - 1). Unity means the\n\
         \x20 estimator's scale response is undistorted by the defocus gap.\n"
    );
    println!(
        "  {:>5} {:>6} {:>10} {:>10} {:>10} {:>10} {:>12}",
        "gap", "n", "median", "MAD", "min", "max", "median err px"
    );
    let mut worst_c2 = f64::NAN;
    for (gap, v) in &by_gap {
        let mut g = v.clone();
        let med = median(&mut g);
        let mut dev: Vec<f64> = v.iter().map(|x| (x - med).abs()).collect();
        let mad = 1.4826 * median(&mut dev);
        let lo = v.iter().cloned().fold(f64::INFINITY, f64::min);
        let hi = v.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        // Turn the gain error into plane px at a representative 1% plant.
        let err_px = (med - 1.0).abs() * 0.01 * rho;
        println!(
            "  {gap:>5} {:>6} {med:>10.4} {mad:>10.4} {lo:>10.4} {hi:>10.4} {err_px:>12.3}",
            v.len()
        );
        if *gap == 0 {
            worst_c2 = v.iter().map(|x| (x - 1.0).abs()).fold(0.0f64, f64::max);
        }
    }
    if n_refused > 0 {
        println!("\n  {n_refused} pair(s) refused and were excluded.");
    }

    if worst_c2.is_nan() {
        bail!("no gap-0 measurement survived; C2 has no verdict");
    }
    if by_scale.len() > 1 {
        println!(
            "\n  Same fits, grouped by PLANT SIZE instead. Corner motion is the\n\
             \x20 quantity a correlation peak-locks on, so attenuation of small\n\
             \x20 displacements shows up here and is invisible in the table above.\n"
        );
        println!(
            "  {:>12} {:>12} {:>6} {:>10} {:>10}",
            "plant s - 1", "corner px", "n", "median", "MAD"
        );
        for (key, v) in &by_scale {
            let g0 = *key as f64 / 1e9;
            let corner = (1.0 / (1.0 + g0) - 1.0).abs() * rho;
            let mut g = v.clone();
            let med = median(&mut g);
            let mut dev: Vec<f64> = v.iter().map(|x| (x - med).abs()).collect();
            let mad = 1.4826 * median(&mut dev);
            println!(
                "  {:>12.2e} {corner:>12.3} {:>6} {med:>10.4} {mad:>10.4}",
                g0,
                v.len()
            );
        }
    }

    println!(
        "\n  GATE C2 (gap 0, zero defocus difference): worst |gain - 1| = {worst_c2:.4}\
         (registered bar: <= 0.02)"
    );
    if worst_c2 <= 0.02 {
        println!("  GATE C2: PASS");
    } else {
        println!("  GATE C2: FAIL");
        bail!("C2 failed: the estimator does not recover a planted scale on real frames");
    }
    Ok(())
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() {
        bail!(
            "usage: m86-align <solve-csv|edges|heldout|drift|plant|field|resample> ...\n\
             see the module doc comment for the full invocation lines"
        );
    }
    match args[0].as_str() {
        "solve-csv" => cmd_solve_csv(&args[1..]),
        "edges" => cmd_edges(&args[1..]),
        "heldout" => cmd_heldout(&args[1..]),
        "drift" => cmd_drift(&args[1..]),
        "compare" => cmd_compare(&args[1..]),
        "field" => cmd_field(&args[1..]),
        "plant" => cmd_plant(&args[1..]),
        other => bail!("unknown mode `{other}`"),
    }
}
