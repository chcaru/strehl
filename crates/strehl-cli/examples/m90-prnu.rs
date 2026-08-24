//! M90 — PRNU in the noise model: the correction, its identity proof, and its
//! blast radius.
//!
//! Not a product path. This is the instrument for
//! `docs/research/M90-prnu-noise-model.md`.
//!
//! # Subcommands
//!
//! ```text
//! cargo run --release -p strehl-cli --example m90-prnu -- identity [--out PATH] [--stack DIR] [--limit N]
//! ```
//!
//! `identity` writes a deterministic binary blob summarising **everything the
//! default path computes** from the noise model: a dense per-plane variance and
//! sigma table over the whole container range at eleven ISOs, the green-luma
//! sigma over the same range, and a full synthetic two-pass merge — focus field,
//! regulariser, election, gate, `n_eff`, the four merged planes,
//! `predicted_sigma` and `disagreement`. Hash the blob before and after a change
//! to `noise.rs` or `profile.rs`; an unchanged hash is the bit-identity proof
//! Deliverable A requires.
//!
//! **This subcommand deliberately uses only API that existed before M90.** It is
//! written and run *first*, at the pre-change revision, so the baseline hash is
//! produced by code that cannot know what the change will be.
//!
//! The synthetic plant supplies its **own** noise constants rather than drawing
//! them from [`strehl_core::noise`] — AGENTS rule 34: a plant that draws its
//! noise from the constant under test is scale-invariant in it and cannot detect
//! it being wrong.
//!
//! **Reads only.** It never writes to a stack directory.

use std::io::Write;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use strehl_core::CfaPlane;
use strehl_core::clip::CONTAINER_MAX_DN;
use strehl_core::focus::FocusField;
use strehl_core::merge::{DEFAULT_GATE, Estimator, FocusStats, Gate, regularise};
use strehl_core::noise::{Levels, NoiseModel};
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma_with_clip};
use strehl_core::profile;

/// Reference levels for the A7C II, as `M1` measured them.
const BLACK: f32 = 512.0;
const WHITE: f32 = 15360.0;

/// Every ISO the profile can distinguish, including both sides of the dual-gain
/// switch and the extended-ISO floor.
const ISOS: [f32; 11] = [
    50.0, 100.0, 160.0, 200.0, 400.0, 500.0, 640.0, 800.0, 1000.0, 1600.0, 2000.0,
];

/// Signal sweep for the identity table: every integer DN the container can hold.
const SWEEP_MAX: u32 = 16_383;

// ---------------------------------------------------------------------------
// a deterministic synthetic stack
// ---------------------------------------------------------------------------

/// SplitMix64. Copied rather than imported so the plant's stream is fixed by
/// this file and cannot drift with a library change.
struct Rng(u64);

impl Rng {
    fn new(seed: u64) -> Self {
        Rng(seed)
    }
    fn next_u64(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
    fn uniform(&mut self) -> f64 {
        ((self.next_u64() >> 11) as f64 + 1.0) / (1u64 << 53) as f64
    }
    fn normal(&mut self) -> f64 {
        let (u1, u2) = (self.uniform(), self.uniform());
        (-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos()
    }
}

/// A synthetic mosaiced frame, `2*width x 2*height` samples with no padding.
struct SynthFrame {
    geom: PlaneGeometry,
    rows: Vec<u16>,
}

impl QuadSource for SynthFrame {
    fn geometry(&self) -> PlaneGeometry {
        self.geom
    }
    fn quad_rows(&self, py: usize) -> (&[u16], &[u16]) {
        let w = 2 * self.geom.width;
        let base = 2 * py * w;
        let (a, b) = self.rows[base..base + 2 * w].split_at(w);
        (a, b)
    }
}

/// Plant geometry. Small enough to run in a second, large enough that the
/// 27-box focus window and the 17-box regulariser both have interior.
const PLANT_W: usize = 192;
const PLANT_H: usize = 144;
const PLANT_FRAMES: u16 = 9;

/// The plant's own gain and read noise, in DN. **Not** read from the profile —
/// rule 34.
const PLANT_GAIN_DN_PER_E: f64 = 0.2290;
const PLANT_READ_DN: f64 = 0.9615;

/// Build frame `k` of the synthetic stack.
///
/// The scene is a horizontal signal ramp from near-black to near-clipping, so a
/// single frame spans the whole working range of the noise model, crossed with a
/// vertical sweep of the in-focus frame index. Detail is a fixed high-frequency
/// block pattern whose amplitude follows the defocus envelope.
fn synth_frame(k: u16) -> SynthFrame {
    let geom = PlaneGeometry {
        width: PLANT_W,
        height: PLANT_H,
    };
    let w = 2 * PLANT_W;
    let mut rows = vec![0u16; w * 2 * PLANT_H];
    // One stream per frame, seeded by frame index: reproducible, and different
    // frames get genuinely different noise.
    let mut rng = Rng::new(0x4D39_0000 ^ u64::from(k));
    for py in 0..PLANT_H {
        let kfoc = (py as f64 / (PLANT_H - 1) as f64) * f64::from(PLANT_FRAMES - 1);
        let d = (f64::from(k) - kfoc) / 1.25;
        let contrast = (-0.5 * d * d).exp();
        for px in 0..PLANT_W {
            let ramp = px as f64 / (PLANT_W - 1) as f64;
            let base = 60.0 + ramp * 11_940.0;
            let block = if ((px / 3) + (py / 3)) % 2 == 0 {
                1.0
            } else {
                -1.0
            };
            for plane in CfaPlane::ALL {
                // Per-plane offsets so the four planes are not the same number
                // four times; the merge stores them separately.
                let tint = match plane {
                    CfaPlane::R => 0.86,
                    CfaPlane::G1 => 1.00,
                    CfaPlane::B => 0.74,
                    CfaPlane::G2 => 1.00,
                };
                let s = base * tint * (1.0 + 0.25 * contrast * block);
                let sigma =
                    (PLANT_GAIN_DN_PER_E * s + PLANT_READ_DN * PLANT_READ_DN).max(0.0).sqrt();
                let v = f64::from(BLACK) + s + sigma * rng.normal();
                let (sx, sy) = geom.sensor_coord(plane, px, py);
                rows[sy * w + sx] = v.clamp(0.0, f64::from(CONTAINER_MAX_DN)).round() as u16;
            }
        }
    }
    SynthFrame { geom, rows }
}

// ---------------------------------------------------------------------------
// blob writing
// ---------------------------------------------------------------------------

/// An append-only little-endian byte blob.
struct Blob(Vec<u8>);

impl Blob {
    fn new() -> Self {
        Blob(Vec::with_capacity(1 << 22))
    }
    fn tag(&mut self, s: &str) {
        self.0.extend_from_slice(&(s.len() as u32).to_le_bytes());
        self.0.extend_from_slice(s.as_bytes());
    }
    fn f32(&mut self, v: f32) {
        self.0.extend_from_slice(&v.to_le_bytes());
    }
    fn f64(&mut self, v: f64) {
        self.0.extend_from_slice(&v.to_le_bytes());
    }
    fn u16(&mut self, v: u16) {
        self.0.extend_from_slice(&v.to_le_bytes());
    }
    fn u32(&mut self, v: u32) {
        self.0.extend_from_slice(&v.to_le_bytes());
    }
}

/// FNV-1a 64, printed alongside the file so a run is self-describing even
/// without an external hasher. The **authoritative** identity check is
/// `Get-FileHash -Algorithm SHA256` over the blob itself.
fn fnv1a64(bytes: &[u8]) -> u64 {
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    for b in bytes {
        h ^= u64::from(*b);
        h = h.wrapping_mul(0x0000_0100_0000_01b3);
    }
    h
}

// ---------------------------------------------------------------------------
// the identity probe
// ---------------------------------------------------------------------------

/// Every number `noise.rs` and `profile.rs` produce on the default path, at
/// every ISO the profile distinguishes and every DN the container can hold.
fn model_tables(blob: &mut Blob) {
    let levels = Levels {
        black: BLACK,
        white: WHITE,
    };
    blob.tag("model-tables-v1");
    for iso in ISOS {
        let m = profile::noise_model_for("ILCE-7CM2", Some(iso), levels);
        blob.f32(m.iso);
        blob.u32(m.provenance as u32);
        for p in CfaPlane::ALL {
            let pn = m.plane(p);
            blob.f32(pn.gain_dn_per_e);
            blob.f32(pn.read_noise_e);
            blob.f32(pn.levels.black);
            blob.f32(pn.levels.white);
            for s in 0..=SWEEP_MAX {
                blob.f32(m.variance(p, s as f32));
                blob.f32(m.sigma(p, s as f32));
            }
        }
        for s in 0..=SWEEP_MAX {
            blob.f32(m.green_luma_sigma(s as f32));
        }
        // Sub-DN and below-black behaviour, which the integer sweep cannot see.
        for t in [-1000.0f32, -1.0, -0.5, 0.0, 0.25, 0.5, 1e-6, 1e6] {
            blob.f32(m.green_luma_sigma(t));
            blob.f32(m.sigma(CfaPlane::G1, t));
        }
    }
    // The fallback path is part of the default path's contract too.
    let f = profile::fallback(0.0, levels);
    blob.tag("fallback");
    blob.u32(f.provenance as u32);
    for s in 0..=SWEEP_MAX {
        blob.f32(f.green_luma_sigma(s as f32));
    }
}

/// The full two-pass merge, on the deterministic plant, at the shipped gate.
fn synthetic_merge(blob: &mut Blob, noise: &NoiseModel) -> Result<()> {
    let geom = PlaneGeometry {
        width: PLANT_W,
        height: PLANT_H,
    };
    let px = geom.pixels();
    let mut field = FocusField::new(geom);
    let mut luma = vec![0.0f32; px];
    let mut clipped = vec![false; px];
    let mut scratch = vec![0.0f32; px];
    let mut reg = vec![0.0f32; px];

    let frames: Vec<SynthFrame> = (0..PLANT_FRAMES).map(synth_frame).collect();

    blob.tag("synthetic-merge-v1");
    let mut stats = FocusStats::new(geom);
    for (k, f) in frames.iter().enumerate() {
        green_luma_with_clip(f, BLACK, CONTAINER_MAX_DN, &mut luma, &mut clipped);
        field.compute(&luma, noise);
        // The focus field itself is a direct consumer of green_luma_sigma.
        for v in field.values() {
            blob.f32(*v);
        }
        regularise(field.values(), geom, &mut scratch, &mut reg);
        stats.fold(k as u16, &reg)?;
    }
    for v in stats.best_focus() {
        blob.f32(*v);
    }
    for v in stats.best_index() {
        blob.u16(*v);
    }

    let mut est = Estimator::new(&stats, Gate::new(DEFAULT_GATE));
    est.track_disagreement();
    for (k, f) in frames.iter().enumerate() {
        green_luma_with_clip(f, BLACK, CONTAINER_MAX_DN, &mut luma, &mut clipped);
        field.compute(&luma, noise);
        regularise(field.values(), geom, &mut scratch, &mut reg);
        est.fold_censored(k as u16, f, &reg, CONTAINER_MAX_DN)?;
    }

    for v in est.n_eff() {
        blob.u16(*v);
    }
    for p in CfaPlane::ALL {
        for i in 0..px {
            blob.f32(est.value(p, i));
        }
    }
    for i in 0..px {
        blob.f32(est.predicted_sigma(noise, i, BLACK));
        blob.f64(est.disagreement(noise, i, BLACK).unwrap_or(f64::NAN));
    }
    blob.f64(est.mean_n_eff());
    blob.f64(est.mean_predicted_sigma_gain(noise, BLACK));
    blob.f64(est.disagreement_exposure());
    Ok(())
}

/// The same two-pass merge on a real stack, so the identity claim is made on the
/// product's own data and not only on a plant.
///
/// Written to its own file because a full-plane dump is ~130 MB and the model
/// tables are meant to stay cheap to re-hash.
fn real_merge(blob: &mut Blob, dir: &Path, limit: Option<usize>) -> Result<()> {
    let mut paths: Vec<PathBuf> = std::fs::read_dir(dir)
        .with_context(|| format!("reading {}", dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().is_some_and(|e| e.eq_ignore_ascii_case("ARW")))
        .collect();
    paths.sort();
    if let Some(n) = limit {
        paths.truncate(n);
    }
    if paths.len() < 2 {
        bail!("{} holds {} ARW files; need at least 2", dir.display(), paths.len());
    }

    let first = strehl_raw::decode(&paths[0]).context("decoding the first frame")?;
    let geom = first.geometry();
    let levels = first.levels;
    let noise = profile::noise_model_for(&first.camera, first.iso, levels);
    let black = levels.black;
    drop(first);
    let px = geom.pixels();

    let mut field = FocusField::new(geom);
    let mut luma = vec![0.0f32; px];
    let mut clipped = vec![false; px];
    let mut scratch = vec![0.0f32; px];
    let mut reg = vec![0.0f32; px];

    blob.tag("real-merge-v1");
    blob.tag(&dir.display().to_string());
    blob.u32(paths.len() as u32);

    let mut stats = FocusStats::new(geom);
    for (k, p) in paths.iter().enumerate() {
        let frame = strehl_raw::decode(p).with_context(|| format!("decoding {}", p.display()))?;
        green_luma_with_clip(&frame, black, CONTAINER_MAX_DN, &mut luma, &mut clipped);
        field.compute(&luma, &noise);
        regularise(field.values(), geom, &mut scratch, &mut reg);
        stats.fold(k as u16, &reg)?;
    }
    let mut est = Estimator::new(&stats, Gate::new(DEFAULT_GATE));
    est.track_disagreement();
    for (k, p) in paths.iter().enumerate() {
        let frame = strehl_raw::decode(p).with_context(|| format!("decoding {}", p.display()))?;
        green_luma_with_clip(&frame, black, CONTAINER_MAX_DN, &mut luma, &mut clipped);
        field.compute(&luma, &noise);
        regularise(field.values(), geom, &mut scratch, &mut reg);
        est.fold_censored(k as u16, &frame, &reg, CONTAINER_MAX_DN)?;
    }

    for v in est.n_eff() {
        blob.u16(*v);
    }
    for p in CfaPlane::ALL {
        for i in 0..px {
            blob.f32(est.value(p, i));
        }
    }
    blob.f64(est.mean_n_eff());
    blob.f64(est.mean_predicted_sigma_gain(&noise, black));
    println!(
        "real stack      : {} frames from {}, mean n_eff {:.6}, sigma gain {:.6}",
        paths.len(),
        dir.display(),
        est.mean_n_eff(),
        est.mean_predicted_sigma_gain(&noise, black)
    );
    Ok(())
}

fn cmd_identity(out: &Path, stack: Option<&Path>, limit: Option<usize>) -> Result<()> {
    let levels = Levels {
        black: BLACK,
        white: WHITE,
    };
    let mut blob = Blob::new();
    model_tables(&mut blob);
    let noise = profile::noise_model_for("ILCE-7CM2", Some(100.0), levels);
    synthetic_merge(&mut blob, &noise)?;
    write_blob(out, &blob, "model+synthetic")?;
    if let Some(dir) = stack {
        let mut rblob = Blob::new();
        real_merge(&mut rblob, dir, limit)?;
        let mut real_out = out.to_path_buf();
        let stem = out
            .file_stem()
            .map(|s| s.to_string_lossy().into_owned())
            .unwrap_or_else(|| "identity".to_string());
        real_out.set_file_name(format!("{stem}-real.bin"));
        write_blob(&real_out, &rblob, "real-stack")?;
    }
    Ok(())
}

fn write_blob(out: &Path, blob: &Blob, label: &str) -> Result<()> {
    if let Some(parent) = out.parent() {
        std::fs::create_dir_all(parent).ok();
    }
    let mut fh = std::fs::File::create(out).with_context(|| format!("writing {}", out.display()))?;
    fh.write_all(&blob.0)?;
    fh.flush()?;
    println!(
        "{label:<16}: {} ({} bytes) fnv1a64 {:016x}",
        out.display(),
        blob.0.len(),
        fnv1a64(&blob.0)
    );
    Ok(())
}

// ---------------------------------------------------------------------------

fn usage() -> ! {
    eprintln!(
        "usage:\n  m90-prnu identity [--out PATH] [--stack DIR] [--limit N]"
    );
    std::process::exit(2)
}

fn main() -> Result<()> {
    let mut args = std::env::args().skip(1);
    let cmd = args.next().unwrap_or_default();
    let mut out = PathBuf::from("experiments/M90-prnu/out/cache/identity.bin");
    let mut stack: Option<PathBuf> = None;
    let mut limit: Option<usize> = None;
    while let Some(a) = args.next() {
        match a.as_str() {
            "--out" => out = PathBuf::from(args.next().context("--out needs a value")?),
            "--stack" => stack = Some(PathBuf::from(args.next().context("--stack needs a value")?)),
            "--limit" => {
                limit = Some(
                    args.next()
                        .context("--limit needs a value")?
                        .parse()
                        .context("--limit value")?,
                )
            }
            _ => usage(),
        }
    }
    match cmd.as_str() {
        "identity" => cmd_identity(&out, stack.as_deref(), limit),
        _ => usage(),
    }
}
