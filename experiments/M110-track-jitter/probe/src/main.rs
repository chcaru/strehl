//! M110 probe — sweep the second-difference roughness penalty in `solve_global`
//! and score it against fact 1435's jitter statistic and the shipped held-out
//! protocol.
//!
//! Deliberately a standalone crate outside the strehl workspace: several
//! milestones are live in this tree and adding a workspace member would edit a
//! shared manifest. Same reasoning as M103's probe.
//!
//! It reads M103's **committed** edge dump rather than re-measuring, so every
//! number here rests on the identical pairwise measurements fact 1435 was
//! computed from. B0 checks that by reproducing M103's committed baseline
//! placement file bit-for-bit.

use anyhow::{Context, Result, bail};
use std::io::Write;
use std::path::{Path, PathBuf};

use strehl_core::plane::PlaneGeometry;
use strehl_core::align::{
    AlignEdge, Cx, GlobalOptions, Placement, Similarity, Weighting, corner_radius,
    edge_errors, solve_global,
};

// ---------------------------------------------------------------------------
// tiny arg parser
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
    fn f64_or(&self, k: &str, d: f64) -> Result<f64> {
        match self.get(k) {
            Some(v) => Ok(v.parse()?),
            None => Ok(d),
        }
    }
    fn flag(&self, k: &str) -> bool {
        matches!(self.get(k), Some("1") | Some("true") | Some("yes"))
    }
    fn usizes(&self, k: &str) -> Result<Vec<usize>> {
        Ok(match self.get(k) {
            Some(v) => v
                .split(',')
                .filter(|s| !s.is_empty())
                .map(|s| s.parse::<usize>())
                .collect::<Result<Vec<_>, _>>()?,
            None => Vec::new(),
        })
    }
    fn f64s(&self, k: &str) -> Result<Vec<f64>> {
        Ok(match self.get(k) {
            Some(v) => v
                .split(',')
                .filter(|s| !s.is_empty())
                .map(|s| s.parse::<f64>())
                .collect::<Result<Vec<_>, _>>()?,
            None => Vec::new(),
        })
    }
}

// ---------------------------------------------------------------------------
// edges
// ---------------------------------------------------------------------------

struct Loaded {
    edges: Vec<AlignEdge>,
    n: usize,
}

/// M103's edge CSV: `i,j,span,status,a_re,a_im,b_re,b_im,used,total,raw_n,rms,lever,...`
fn load_edges(path: &Path, only: &[usize]) -> Result<Loaded> {
    let text = std::fs::read_to_string(path)?;
    let mut edges = Vec::new();
    let mut n = 0usize;
    for line in text.lines() {
        if line.starts_with('#') || line.starts_with("i,j,") {
            continue;
        }
        let f: Vec<&str> = line.split(',').collect();
        if f.len() < 14 {
            continue;
        }
        let i: usize = f[0].parse()?;
        let j: usize = f[1].parse()?;
        n = n.max(j + 1);
        if f[3] != "OK" {
            continue;
        }
        let span = j - i;
        if !only.is_empty() && !only.contains(&span) {
            continue;
        }
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
    Ok(Loaded { edges, n })
}

// ---------------------------------------------------------------------------
// track i/o — hex f64 so a comparison can be bit-exact
// ---------------------------------------------------------------------------

fn rebase(t: Similarity, reference: Option<Similarity>) -> Similarity {
    match reference.and_then(|r| r.invert()) {
        Some(inv) => inv.then(t),
        None => t,
    }
}

fn write_track(path: &Path, p: &Placement, reference: usize, header: &str) -> Result<()> {
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir).ok();
    }
    let mut fh = std::fs::File::create(path)?;
    writeln!(fh, "# m110probe track {header}")?;
    writeln!(fh, "# idx state a_re a_im b_re b_im   (IEEE-754 f64, big-endian hex)")?;
    let refp = p.get(reference).copied().flatten();
    for (k, t) in p.iter().enumerate() {
        match t {
            Some(t) => {
                let r = rebase(*t, refp);
                writeln!(
                    fh,
                    "{k} placed {:016x} {:016x} {:016x} {:016x}",
                    r.a.re.to_bits(),
                    r.a.im.to_bits(),
                    r.b.re.to_bits(),
                    r.b.im.to_bits()
                )?;
            }
            None => writeln!(fh, "{k} refused 0 0 0 0")?,
        }
    }
    Ok(())
}

/// Read a track file, or a `strehl-warpmap` sidecar — both carry
/// `idx state a_re a_im b_re b_im` as big-endian hex f64.
fn read_track(path: &Path) -> Result<Vec<Option<[u64; 4]>>> {
    let text = std::fs::read_to_string(path)?;
    let mut out: Vec<Option<[u64; 4]>> = Vec::new();
    for line in text.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') || line.starts_with("strehl-") {
            continue;
        }
        let p: Vec<&str> = line.split_whitespace().collect();
        if p.len() < 6 {
            continue;
        }
        let Ok(idx) = p[0].parse::<usize>() else {
            continue;
        };
        if out.len() <= idx {
            out.resize(idx + 1, None);
        }
        if p[1] == "placed" || p[1] == "held" {
            let w = [
                u64::from_str_radix(p[2], 16)?,
                u64::from_str_radix(p[3], 16)?,
                u64::from_str_radix(p[4], 16)?,
                u64::from_str_radix(p[5], 16)?,
            ];
            out[idx] = Some(w);
        }
    }
    Ok(out)
}

// ---------------------------------------------------------------------------
// statistics
// ---------------------------------------------------------------------------

fn quantile(sorted: &[f64], q: f64) -> f64 {
    if sorted.is_empty() {
        return f64::NAN;
    }
    // numpy's default linear interpolation, so the numbers compare directly
    // with M103's `jitter.py`.
    let h = (sorted.len() as f64 - 1.0) * q;
    let lo = h.floor() as usize;
    let hi = h.ceil() as usize;
    if lo == hi {
        return sorted[lo];
    }
    sorted[lo] * (hi as f64 - h) + sorted[hi] * (h - lo as f64)
}

#[derive(Clone, Debug, Default)]
struct Stats {
    median: f64,
    p90: f64,
    p99: f64,
    max: f64,
    frac_ge_0p5: f64,
    frac_ge_1p0: f64,
    n: usize,
}

fn stats(v: &[f64]) -> Stats {
    let mut s = v.to_vec();
    s.sort_by(|a, b| a.partial_cmp(b).unwrap());
    Stats {
        median: quantile(&s, 0.5),
        p90: quantile(&s, 0.90),
        p99: quantile(&s, 0.99),
        max: s.last().copied().unwrap_or(f64::NAN),
        frac_ge_0p5: v.iter().filter(|x| **x >= 0.5).count() as f64 / v.len() as f64,
        frac_ge_1p0: v.iter().filter(|x| **x >= 1.0).count() as f64 / v.len() as f64,
        n: v.len(),
    }
}

fn stats_json(s: &Stats) -> String {
    format!(
        "{{\"median_px\":{:.6},\"p90_px\":{:.6},\"p99_px\":{:.6},\"max_px\":{:.6},\
         \"frac_ge_0p5\":{:.6},\"frac_ge_1p0\":{:.6},\"n\":{}}}",
        s.median, s.p90, s.p99, s.max, s.frac_ge_0p5, s.frac_ge_1p0, s.n
    )
}

/// `ln |A_j|` for every placed frame, in solve order. Gauge-invariant once
/// differenced twice, so the reference does not matter.
fn log_scale_track(p: &Placement) -> Vec<Option<f64>> {
    p.iter()
        .map(|t| {
            t.and_then(|t| {
                let m = t.a.abs();
                if m > 0.0 { Some(m.ln()) } else { None }
            })
        })
        .collect()
}

/// M103's statistic: `|d2 ln|A|| * rho`, plane px at the corner radius.
fn jitter_px(p: &Placement, rho: f64) -> (Vec<usize>, Vec<f64>) {
    let t = log_scale_track(p);
    let mut js = Vec::new();
    let mut vs = Vec::new();
    for k in 1..t.len().saturating_sub(1) {
        if let (Some(a), Some(b), Some(c)) = (t[k - 1], t[k], t[k + 1]) {
            js.push(k);
            vs.push((c - 2.0 * b + a).abs() * rho);
        }
    }
    (js, vs)
}

/// The same second difference taken on the **whole similarity**: the largest
/// corner displacement of `d2 A * corner + d2 B`. This is the quantity the
/// merge's gather actually reads; M103 measured only the scale limb of it.
fn corner_jitter_px(p: &Placement, geom: PlaneGeometry) -> Vec<f64> {
    let corners = strehl_core::align::corners(geom);
    let mut out = Vec::new();
    for k in 1..p.len().saturating_sub(1) {
        let (Some(a), Some(b), Some(c)) = (p[k - 1], p[k], p[k + 1]) else {
            continue;
        };
        let da = c.a - b.a.scale(2.0) + a.a;
        let db = c.b - b.b.scale(2.0) + a.b;
        let m = corners
            .iter()
            .map(|q| (da * *q + db).abs())
            .fold(0.0f64, f64::max);
        out.push(m);
    }
    out
}

/// Median held-out corner error under the shipped M10 protocol, copied from
/// `align_cmd.rs:459`: test is `span >= 40 && used >= 12`, train the rest.
fn heldout_error(
    edges: &[AlignEdge],
    n: usize,
    opts: &GlobalOptions,
    geom: PlaneGeometry,
) -> Option<f64> {
    const MIN_SPAN: usize = 40;
    const MIN_USED: usize = 12;
    let is_test = |e: &AlignEdge| e.j - e.i >= MIN_SPAN && e.used >= MIN_USED;
    let test: Vec<AlignEdge> = edges.iter().filter(|e| is_test(e)).copied().collect();
    let train: Vec<AlignEdge> = edges.iter().filter(|e| !is_test(e)).copied().collect();
    if test.is_empty() || train.is_empty() {
        return None;
    }
    let g = solve_global(&train, n, opts)?;
    let mut errs: Vec<f64> = edge_errors(&g, &test, geom).iter().map(|x| x.err).collect();
    if errs.is_empty() {
        return None;
    }
    errs.sort_by(|a, b| a.partial_cmp(b).unwrap());
    Some(errs[errs.len() / 2])
}

/// Bootstrap standard error of the held-out median, so "beyond its noise" has
/// a number attached. Deterministic LCG so the figure reproduces.
fn heldout_se(
    edges: &[AlignEdge],
    n: usize,
    opts: &GlobalOptions,
    geom: PlaneGeometry,
    reps: usize,
) -> Option<f64> {
    const MIN_SPAN: usize = 40;
    const MIN_USED: usize = 12;
    let is_test = |e: &AlignEdge| e.j - e.i >= MIN_SPAN && e.used >= MIN_USED;
    let test: Vec<AlignEdge> = edges.iter().filter(|e| is_test(e)).copied().collect();
    let train: Vec<AlignEdge> = edges.iter().filter(|e| !is_test(e)).copied().collect();
    if test.is_empty() || train.is_empty() {
        return None;
    }
    let g = solve_global(&train, n, opts)?;
    let errs: Vec<f64> = edge_errors(&g, &test, geom).iter().map(|x| x.err).collect();
    if errs.is_empty() {
        return None;
    }
    let mut seed: u64 = 0x9E37_79B9_7F4A_7C15;
    let mut meds = Vec::with_capacity(reps);
    for _ in 0..reps {
        let mut s: Vec<f64> = (0..errs.len())
            .map(|_| {
                seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
                errs[((seed >> 33) as usize) % errs.len()]
            })
            .collect();
        s.sort_by(|a, b| a.partial_cmp(b).unwrap());
        meds.push(s[s.len() / 2]);
    }
    let mean = meds.iter().sum::<f64>() / meds.len() as f64;
    let var = meds.iter().map(|m| (m - mean) * (m - mean)).sum::<f64>() / (meds.len() - 1) as f64;
    Some(var.sqrt())
}

// ---------------------------------------------------------------------------
// solver options
// ---------------------------------------------------------------------------

/// Set the robust-penalty threshold, when the core supports one.
///
/// STAGE 1 (this body): the core does **not** have the field yet, so asking for
/// it is an error rather than a silent no-op. Stage 1 exists to produce the
/// pre-change `lambda = 0` track that B1a compares against; it must be built
/// from an `align.rs` I have not touched.
fn apply_smooth_huber(_o: &mut GlobalOptions, a: &Args) -> Result<()> {
    match a.get("smooth-huber") {
        None | Some("none") => Ok(()),
        Some(v) => bail!("--smooth-huber={v} needs the patched align.rs (stage 2)"),
    }
}

fn opts_from(a: &Args, geom: PlaneGeometry) -> Result<GlobalOptions> {
    let mut o = GlobalOptions::new(geom);
    o.weighting = match a.get("weighting").unwrap_or("unit") {
        "unit" => Weighting::Unit,
        "count" => Weighting::Count,
        "invvar" => Weighting::InverseVariance,
        other => bail!("unknown --weighting {other}"),
    };
    o.irls_iters = a.usize_or("irls", 3)?;
    o.huber_px = a.f64_or("huber", 3.0)?;
    o.smooth = a.f64_or("smooth", 0.0)?;
    apply_smooth_huber(&mut o, a)?;
    Ok(o)
}

// ---------------------------------------------------------------------------
// commands
// ---------------------------------------------------------------------------

fn geom_from(a: &Args) -> Result<PlaneGeometry> {
    Ok(PlaneGeometry {
        width: a.usize_or("plane-w", 3516)?,
        height: a.usize_or("plane-h", 2344)?,
    })
}

fn print_jitter(label: &str, p: &Placement, rho: f64, reference: usize) {
    let (js, v) = jitter_px(p, rho);
    let all = stats(&v);
    let near: Vec<f64> = js
        .iter()
        .zip(v.iter())
        .filter(|(j, _)| (**j as i64 - reference as i64).abs() <= 50)
        .map(|(_, x)| *x)
        .collect();
    let far: Vec<f64> = js
        .iter()
        .zip(v.iter())
        .filter(|(j, _)| (**j as i64 - reference as i64).abs() > 100)
        .map(|(_, x)| *x)
        .collect();
    let ns = stats(&near);
    let fs = stats(&far);
    println!(
        "  {label:<22} med {:.4}  p90 {:.4}  p99 {:.4}  max {:.4}  >=1px {:.3}  | near med {:.4} max {:.4} | far med {:.4} max {:.4}",
        all.median, all.p90, all.p99, all.max, all.frac_ge_1p0, ns.median, ns.max, fs.median, fs.max
    );
}

fn cmd_solve(a: &Args) -> Result<()> {
    let geom = geom_from(a)?;
    let rho = corner_radius(geom);
    let only = a.usizes("only-spans")?;
    let loaded = load_edges(&PathBuf::from(a.req("edges")?), &only)?;
    let n = a.usize_or("n", loaded.n)?;
    let reference = a.usize_or("reference", 149)?;
    let opts = opts_from(a, geom)?;

    let p = solve_global(&loaded.edges, n, &opts).context("solve_global returned None")?;
    let placed = p.iter().filter(|x| x.is_some()).count();
    let span1 = loaded.edges.iter().filter(|e| e.j - e.i == 1).count();
    println!(
        "edges {} (span-1 {}) n {} placed {} smooth {} smooth-huber {}",
        loaded.edges.len(),
        span1,
        n,
        placed,
        opts.smooth,
        a.get("smooth-huber").unwrap_or("none")
    );
    print_jitter("d2 ln|A| px", &p, rho, reference);
    let cj = corner_jitter_px(&p, geom);
    let cs = stats(&cj);
    println!(
        "  {:<22} med {:.4}  p90 {:.4}  p99 {:.4}  max {:.4}  >=1px {:.3}",
        "d2 corner px (A+B)", cs.median, cs.p90, cs.p99, cs.max, cs.frac_ge_1p0
    );
    match heldout_error(&loaded.edges, n, &opts, geom) {
        Some(e) => println!("  held-out median corner error: {e:.4} px"),
        None => println!("  held-out: NOT MEASURED"),
    }
    if a.flag("se") {
        match heldout_se(&loaded.edges, n, &opts, geom, 2000) {
            Some(s) => println!("  held-out bootstrap SE (2000 reps): {s:.4} px"),
            None => println!("  held-out SE: NOT MEASURED"),
        }
    }
    if let Some(t) = a.get("track") {
        write_track(
            Path::new(t),
            &p,
            reference,
            &format!("smooth={} reference={}", opts.smooth, reference),
        )?;
        println!("  wrote {t}");
    }
    Ok(())
}

/// Bit-exact comparison of two track files. `--expect equal|differ` decides the
/// exit code, so this is a gate rather than a print statement.
fn cmd_cmp(a: &Args) -> Result<()> {
    let x = read_track(&PathBuf::from(a.req("a")?))?;
    let y = read_track(&PathBuf::from(a.req("b")?))?;
    let n = x.len().max(y.len());
    let mut words = 0usize;
    let mut diff = 0usize;
    let mut first: Option<(usize, usize)> = None;
    for k in 0..n {
        match (x.get(k).copied().flatten(), y.get(k).copied().flatten()) {
            (Some(u), Some(v)) => {
                for w in 0..4 {
                    words += 1;
                    if u[w] != v[w] {
                        diff += 1;
                        if first.is_none() {
                            first = Some((k, w));
                        }
                    }
                }
            }
            (None, None) => {}
            _ => {
                words += 4;
                diff += 4;
                if first.is_none() {
                    first = Some((k, 99));
                }
            }
        }
    }
    let expect = a.get("expect").unwrap_or("equal");
    println!("words {words}  differing {diff}  first {first:?}  expect {expect}");
    let ok = match expect {
        "equal" => diff == 0,
        "differ" => diff > 0,
        other => bail!("--expect must be equal or differ, got {other}"),
    };
    println!("  -> {}", if ok { "PASS" } else { "FAIL" });
    if !ok {
        std::process::exit(1);
    }
    Ok(())
}

fn cmd_sweep(a: &Args) -> Result<()> {
    let geom = geom_from(a)?;
    let rho = corner_radius(geom);
    let only = a.usizes("only-spans")?;
    let loaded = load_edges(&PathBuf::from(a.req("edges")?), &only)?;
    let n = a.usize_or("n", loaded.n)?;
    let reference = a.usize_or("reference", 149)?;
    let lambdas = a.f64s("lambdas")?;
    let out = PathBuf::from(a.req("out")?);
    if let Some(d) = out.parent() {
        std::fs::create_dir_all(d).ok();
    }
    let mut fh = std::fs::File::create(&out)?;
    writeln!(
        fh,
        "lambda,smooth_huber,placed,heldout_px,jit_med,jit_p90,jit_p99,jit_max,jit_ge1,\
         near_med,near_max,far_med,far_max,corner_med,corner_p90,corner_max"
    )?;
    println!("{:>8} {:>10} {:>10} {:>9} {:>9} {:>9} {:>8}", "lambda", "heldout", "jit_med", "jit_p90", "jit_max", "far_max", ">=1px");
    for &l in &lambdas {
        let mut opts = opts_from(a, geom)?;
        opts.smooth = l;
        let Some(p) = solve_global(&loaded.edges, n, &opts) else {
            println!("{l:>8} SOLVE FAILED");
            continue;
        };
        let (js, v) = jitter_px(&p, rho);
        let all = stats(&v);
        let near: Vec<f64> = js.iter().zip(v.iter())
            .filter(|(j, _)| (**j as i64 - reference as i64).abs() <= 50)
            .map(|(_, x)| *x).collect();
        let far: Vec<f64> = js.iter().zip(v.iter())
            .filter(|(j, _)| (**j as i64 - reference as i64).abs() > 100)
            .map(|(_, x)| *x).collect();
        let ns = stats(&near);
        let fs = stats(&far);
        let cs = stats(&corner_jitter_px(&p, geom));
        let ho = heldout_error(&loaded.edges, n, &opts, geom).unwrap_or(f64::NAN);
        let placed = p.iter().filter(|x| x.is_some()).count();
        writeln!(
            fh,
            "{l},{},{placed},{ho:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6}",
            a.get("smooth-huber").unwrap_or("none"),
            all.median, all.p90, all.p99, all.max, all.frac_ge_1p0,
            ns.median, ns.max, fs.median, fs.max, cs.median, cs.p90, cs.max
        )?;
        println!(
            "{l:>8} {ho:>10.4} {:>10.4} {:>9.4} {:>9.4} {:>9.4} {:>8.3}",
            all.median, all.p90, all.max, fs.max, all.frac_ge_1p0
        );
    }
    println!("wrote {}", out.display());
    Ok(())
}

// ---------------------------------------------------------------------------
// plants — B4
// ---------------------------------------------------------------------------

/// Least-squares polynomial fit of `y` against `t = j/(n-1)`, degree `deg`.
fn polyfit(y: &[Option<f64>], n: usize, deg: usize) -> Vec<f64> {
    let m = deg + 1;
    let mut ata = vec![0.0f64; m * m];
    let mut atb = vec![0.0f64; m];
    for (j, yj) in y.iter().enumerate().take(n) {
        let Some(yj) = *yj else { continue };
        let t = j as f64 / (n - 1) as f64;
        let mut basis = vec![1.0f64; m];
        for k in 1..m {
            basis[k] = basis[k - 1] * t;
        }
        for p in 0..m {
            for q in 0..m {
                ata[p * m + q] += basis[p] * basis[q];
            }
            atb[p] += basis[p] * yj;
        }
    }
    // Gaussian elimination with partial pivoting.
    for c in 0..m {
        let mut piv = c;
        for r in c + 1..m {
            if ata[r * m + c].abs() > ata[piv * m + c].abs() {
                piv = r;
            }
        }
        for k in 0..m {
            ata.swap(c * m + k, piv * m + k);
        }
        atb.swap(c, piv);
        let d = ata[c * m + c];
        for r in c + 1..m {
            let f = ata[r * m + c] / d;
            for k in c..m {
                ata[r * m + k] -= f * ata[c * m + k];
            }
            atb[r] -= f * atb[c];
        }
    }
    let mut x = vec![0.0f64; m];
    for r in (0..m).rev() {
        let mut s = atb[r];
        for k in r + 1..m {
            s -= ata[r * m + k] * x[k];
        }
        x[r] = s / ata[r * m + r];
    }
    x
}

fn polyval(c: &[f64], j: usize, n: usize) -> f64 {
    let t = j as f64 / (n - 1) as f64;
    let mut acc = 0.0;
    for k in (0..c.len()).rev() {
        acc = acc * t + c[k];
    }
    acc
}

/// Synthesise a noiseless edge set from a truth log-scale track, keeping the
/// real edge topology and per-edge statistics.
fn plant_edges(real: &[AlignEdge], truth: &[f64]) -> Vec<AlignEdge> {
    real.iter()
        .map(|e| {
            let a = (truth[e.j] - truth[e.i]).exp();
            AlignEdge {
                i: e.i,
                j: e.j,
                t: Similarity {
                    a: Cx::new(a, 0.0),
                    b: Cx::ZERO,
                },
                used: e.used,
                rms: e.rms,
                lever: e.lever,
            }
        })
        .collect()
}

fn cmd_plant(a: &Args) -> Result<()> {
    let geom = geom_from(a)?;
    let rho = corner_radius(geom);
    let only = a.usizes("only-spans")?;
    let loaded = load_edges(&PathBuf::from(a.req("edges")?), &only)?;
    let n = a.usize_or("n", loaded.n)?;
    let kind = a.get("kind").unwrap_or("jitter").to_string();
    let amp_px = a.f64_or("amp", 0.5)?;
    let at = a.usize_or("at", 150)?;

    // The smooth carrier: a degree-4 fit to the real solved track, so the plant
    // carries this stack's REAL breathing curvature. Fact 1410 forbids a linear
    // plant for alignment work.
    let base_opts = {
        let mut o = opts_from(a, geom)?;
        o.smooth = 0.0;
        o
    };
    let p0 = solve_global(&loaded.edges, n, &base_opts).context("baseline solve")?;
    let coef = polyfit(&log_scale_track(&p0), n, 4);
    let carrier: Vec<f64> = (0..n).map(|j| polyval(&coef, j, n)).collect();

    let planted: Vec<f64> = (0..n)
        .map(|j| {
            let d = match kind.as_str() {
                "jitter" => {
                    (amp_px / rho) * if j % 2 == 0 { 1.0 } else { -1.0 }
                }
                "step" => {
                    if j >= at { amp_px / rho } else { 0.0 }
                }
                "none" => 0.0,
                _ => 0.0,
            };
            carrier[j] + d
        })
        .collect();
    let edges = plant_edges(&loaded.edges, &planted);
    let span1 = edges.iter().filter(|e| e.j - e.i == 1).count();
    let m_pen = n - 2;

    // DERIVED, before the run: the Nyquist transfer of a second-difference
    // penalty against this edge set. Only ODD spans see an alternating mode
    // (an even span samples the same phase twice), so the data term at w = pi
    // is carried by the span-1 edges alone:
    //     |D v|^2 = m1 * 4 / N ,  |L v|^2 = m_pen * 16 / N
    //     H(pi)   = m1 / (m1 + 4 * lambda^2 * m_pen)
    // The rho weighting cancels: edge rows carry rho, penalty rows lambda*rho.
    let h_pred = |l: f64| span1 as f64 / (span1 as f64 + 4.0 * l * l * m_pen as f64);

    let lambdas = if a.f64s("lambdas")?.is_empty() {
        vec![a.f64_or("smooth", 0.0)?]
    } else {
        a.f64s("lambdas")?
    };
    let out = a.get("out").map(PathBuf::from);
    let mut rows = Vec::new();

    println!(
        "plant kind={kind} amp={amp_px} px at={at} edges={} span1={} n={}",
        edges.len(),
        span1,
        n
    );
    match kind.as_str() {
        "jitter" => println!(
            "{:>8} {:>12} {:>12} {:>10} {:>12}",
            "lambda", "rec_amp_px", "ratio", "H_pred", "rel_err"
        ),
        _ => println!(
            "{:>8} {:>12} {:>10} {:>10} {:>12}",
            "lambda", "step_px", "recovery", "n_dev>0.5", "max_dev_px"
        ),
    }
    for &l in &lambdas {
        let mut opts = opts_from(a, geom)?;
        opts.smooth = l;
        let Some(p) = solve_global(&edges, n, &opts) else {
            println!("{l:>8} SOLVE FAILED");
            continue;
        };
        let t = log_scale_track(&p);
        // gauge: the plant fixes A_0 = exp(planted[0]) via the solver's own
        // gauge A_0 = 1, so compare DIFFERENCES from truth, offset-removed.
        let off = t[0].unwrap_or(0.0) - planted[0];
        let dev: Vec<f64> = (0..n)
            .map(|j| (t[j].unwrap_or(f64::NAN) - off - planted[j]) * rho)
            .collect();
        match kind.as_str() {
            "jitter" => {
                let mut acc = 0.0;
                let mut cnt = 0.0;
                for j in 0..n {
                    if let Some(v) = t[j] {
                        acc += if j % 2 == 0 { v } else { -v };
                        cnt += 1.0;
                    }
                }
                let rec = (acc / cnt).abs() * rho;
                let ratio = rec / amp_px;
                let hp = h_pred(l);
                let rel = (ratio - hp) / hp;
                println!("{l:>8} {rec:>12.5} {ratio:>12.5} {hp:>10.5} {rel:>12.4}");
                rows.push(format!(
                    "{{\"lambda\":{l},\"recovered_px\":{rec:.6},\"ratio\":{ratio:.6},\
                     \"H_pred\":{hp:.6},\"rel_err\":{rel:.6}}}"
                ));
            }
            _ => {
                let step = (t[at].unwrap_or(f64::NAN) - t[at - 1].unwrap_or(f64::NAN)) * rho
                    - (carrier[at] - carrier[at - 1]) * rho;
                let recovery = step / amp_px;
                let ndev = dev.iter().filter(|d| d.abs() > 0.5).count();
                let maxdev = dev.iter().fold(0.0f64, |m, d| m.max(d.abs()));
                println!("{l:>8} {step:>12.5} {recovery:>10.5} {ndev:>10} {maxdev:>12.5}");
                rows.push(format!(
                    "{{\"lambda\":{l},\"step_px\":{step:.6},\"recovery\":{recovery:.6},\
                     \"n_dev_gt_0p5\":{ndev},\"max_dev_px\":{maxdev:.6}}}"
                ));
            }
        }
        if let Some(dump) = a.get("dump-dev") {
            let mut fh = std::fs::File::create(format!("{dump}-{l}.csv"))?;
            writeln!(fh, "j,dev_px,truth_ln,solved_ln")?;
            for j in 0..n {
                writeln!(
                    fh,
                    "{j},{:.9},{:.12},{:.12}",
                    dev[j],
                    planted[j],
                    t[j].unwrap_or(f64::NAN)
                )?;
            }
        }
    }
    if let Some(o) = out {
        if let Some(d) = o.parent() {
            std::fs::create_dir_all(d).ok();
        }
        std::fs::write(
            &o,
            format!(
                "{{\"kind\":\"{kind}\",\"amp_px\":{amp_px},\"at\":{at},\"span1_edges\":{span1},\
                 \"penalty_rows\":{m_pen},\"rows\":[{}]}}",
                rows.join(",")
            ),
        )?;
        println!("wrote {}", o.display());
    }
    Ok(())
}

/// B5 — what did the regulariser remove, and is it smooth in `j`?
fn cmd_residual(a: &Args) -> Result<()> {
    let geom = geom_from(a)?;
    let rho = corner_radius(geom);
    let x = read_track(&PathBuf::from(a.req("a")?))?;
    let y = read_track(&PathBuf::from(a.req("b")?))?;
    let n = x.len().min(y.len());
    let mut r = Vec::new();
    let mut js = Vec::new();
    for k in 0..n {
        if let (Some(u), Some(v)) = (x[k], y[k]) {
            let au = Cx::new(f64::from_bits(u[0]), f64::from_bits(u[1])).abs().ln();
            let av = Cx::new(f64::from_bits(v[0]), f64::from_bits(v[1])).abs().ln();
            js.push(k);
            r.push((au - av) * rho);
        }
    }
    // remove the mean and any linear trend: a gauge difference is not a removal
    let m = r.len() as f64;
    let mean = r.iter().sum::<f64>() / m;
    let tmean = js.iter().map(|j| *j as f64).sum::<f64>() / m;
    let sxy: f64 = js.iter().zip(r.iter()).map(|(j, v)| (*j as f64 - tmean) * (v - mean)).sum();
    let sxx: f64 = js.iter().map(|j| (*j as f64 - tmean).powi(2)).sum();
    let slope = sxy / sxx;
    let d: Vec<f64> = js
        .iter()
        .zip(r.iter())
        .map(|(j, v)| v - mean - slope * (*j as f64 - tmean))
        .collect();
    let var = d.iter().map(|v| v * v).sum::<f64>() / m;
    let ac1 = d.windows(2).map(|w| w[0] * w[1]).sum::<f64>() / (m - 1.0) / var;
    // power above w = pi/2, by a plain DFT
    let nn = d.len();
    let mut lo = 0.0;
    let mut hi = 0.0;
    for k in 1..nn / 2 {
        let w = 2.0 * std::f64::consts::PI * k as f64 / nn as f64;
        let (mut re, mut im) = (0.0, 0.0);
        for (t, v) in d.iter().enumerate() {
            let ang = -w * t as f64;
            re += v * ang.cos();
            im += v * ang.sin();
        }
        let p = re * re + im * im;
        if w >= std::f64::consts::FRAC_PI_2 { hi += p } else { lo += p }
    }
    let frac_hi = hi / (hi + lo);
    println!(
        "removed signal: n {} rms {:.4} px  lag1_autocorr {:.4}  power_above_pi/2 {:.4}",
        nn,
        var.sqrt(),
        ac1,
        frac_hi
    );
    println!(
        "  -> {} (registered: rho1 <= 0 AND frac >= 0.5 means estimation error was removed)",
        if ac1 <= 0.0 && frac_hi >= 0.5 {
            "NOISE-LIKE"
        } else {
            "SMOOTH-LIKE"
        }
    );
    if let Some(o) = a.get("out") {
        std::fs::write(
            o,
            format!(
                "{{\"n\":{nn},\"rms_px\":{:.6},\"lag1_autocorr\":{ac1:.6},\
                 \"power_above_half_pi\":{frac_hi:.6}}}",
                var.sqrt()
            ),
        )?;
    }
    if let Some(dump) = a.get("dump") {
        let mut fh = std::fs::File::create(dump)?;
        writeln!(fh, "j,removed_px")?;
        for (j, v) in js.iter().zip(d.iter()) {
            writeln!(fh, "{j},{v:.9}")?;
        }
    }
    Ok(())
}

/// B0 — reproduce fact 1435 from M103's committed baseline placement file.
fn cmd_fact1435(a: &Args) -> Result<()> {
    let geom = geom_from(a)?;
    let rho = corner_radius(geom);
    let t = read_track(&PathBuf::from(a.req("track")?))?;
    let p: Placement = t
        .iter()
        .map(|w| {
            w.map(|w| Similarity {
                a: Cx::new(f64::from_bits(w[0]), f64::from_bits(w[1])),
                b: Cx::new(f64::from_bits(w[2]), f64::from_bits(w[3])),
            })
        })
        .collect();
    println!("rho = {rho:.6} plane px, frames {}", p.len());
    print_jitter("d2 ln|A| px", &p, rho, a.usize_or("reference", 149)?);
    let (_, v) = jitter_px(&p, rho);
    let s = stats(&v);
    println!("  json {}", stats_json(&s));
    let target = a.f64_or("target", 0.4829)?;
    let tol = a.f64_or("tol", 0.0001)?;
    let ok = (s.median - target).abs() <= tol;
    println!(
        "  -> B0 median {:.6} vs fact 1435 {target} (tol {tol}): {}",
        s.median,
        if ok { "PASS" } else { "FAIL" }
    );
    if !ok {
        std::process::exit(1);
    }
    Ok(())
}

fn main() -> Result<()> {
    let mut it = std::env::args().skip(1);
    let cmd = it.next().unwrap_or_default();
    let a = Args::parse(it);
    match cmd.as_str() {
        "solve" => cmd_solve(&a),
        "sweep" => cmd_sweep(&a),
        "plant" => cmd_plant(&a),
        "cmp" => cmd_cmp(&a),
        "residual" => cmd_residual(&a),
        "fact1435" => cmd_fact1435(&a),
        other => bail!(
            "unknown command {other:?}; expected solve|sweep|plant|cmp|residual|fact1435"
        ),
    }
}
