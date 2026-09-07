//! BUILD-RESAMP — the gather kernels' MTF, measured through the SHIPPING
//! samplers, with a null and a potency arm.
//!
//! # Why this exists
//!
//! `restore::gather_mtf` *models* each kernel's phase-averaged transfer. A
//! model is not a measurement of the code that ships. This harness plants a
//! pure sinusoid, gathers it with `Resampler::sample` — the exact function the
//! merge calls — and fits the amplitude back out. The model is printed beside
//! it as a cross-check, not as the answer.
//!
//! # Units
//!
//! `f` is **cycles per sample of the plane the gather runs on**. The merge's
//! alignment plane is the 2x2 CFA quad grid, so one cycle per *output* pixel of
//! a `--demosaic` render is TWO cycles per sample here. Every number below is
//! in plane units and the caller must convert.
//!
//! # Commissioning
//!
//! * **Null.** A zero-offset gather is an identity for every interpolating
//!   kernel, so every ratio at `dx = 0` must be exactly 1.000000. If it is not,
//!   this harness is wrong, not `align.rs`.
//! * **Potency.** `nearest` is a crippled kernel by construction and must show
//!   a large loss at high `f`. If it does not, the plant carries no signal at
//!   that frequency.
//!
//! The fit is exact rather than least-squares-approximate: `N = 400` samples
//! and every frequency is an integer multiple of `1/400`, so the cos/sin basis
//! is orthogonal over the window and the amplitude read-out is a one-bin DFT.

use strehl_core::align::{PlaneRef, Resampler};
use strehl_core::restore::gather_mtf;

/// Samples in the fit window. Every frequency below is `m / N` for integer `m`,
/// which makes the basis orthogonal and the amplitude exact.
const N: usize = 400;
/// Guard band so no kernel's support ever leaves the plane (lanczos3 needs 3).
const MARGIN: usize = 8;
const W: usize = N + 2 * MARGIN;
const H: usize = 16;
/// Row the gather reads. Integer, so the vertical pass is an exact identity for
/// every kernel and only the horizontal kernel is under test.
const ROW: f64 = 8.0;
/// Sub-pixel phases the phase-average runs over. Matches `gather_mtf`.
const PHASES: usize = 64;

const KERNELS: &[(&str, Resampler)] = &[
    ("nearest", Resampler::Nearest),
    ("bilinear", Resampler::Bilinear),
    ("catmull-rom", Resampler::CatmullRom),
    ("lanczos2", Resampler::Lanczos2),
    ("lanczos3", Resampler::Lanczos3),
];

/// Frequencies in cycles per plane sample. Every one is an integer multiple of
/// `1/400`. `0.48` rather than `0.50` because the DFT bin at exactly Nyquist is
/// degenerate and would need a different normalisation.
const FREQS: &[f64] = &[0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.48];

/// A plane carrying `cos(2 pi f x)`, constant down the columns, at a chosen
/// width. The width is a parameter because the pure-scale arm reads up to
/// `N / (2k)` samples either side of the centre and every sampler CLAMPS at the
/// plane edge — a fit window that reaches the clamp measures the clamp.
fn plant_w(f: f64, w: usize) -> Vec<f32> {
    let mut v = vec![0f32; w * H];
    for y in 0..H {
        for x in 0..w {
            v[y * w + x] = (2.0 * std::f64::consts::PI * f * x as f64).cos() as f32;
        }
    }
    v
}

/// A plane carrying `cos(2 pi f x)`, constant down the columns.
fn plant(f: f64) -> Vec<f32> {
    plant_w(f, W)
}

/// One-bin DFT amplitude of `s` at `f`, over `N` samples starting at `x0`.
fn amplitude(s: &[f64], x0: usize, f: f64) -> f64 {
    let (mut re, mut im) = (0.0, 0.0);
    for (i, v) in s.iter().enumerate() {
        let th = 2.0 * std::f64::consts::PI * f * (x0 + i) as f64;
        re += v * th.cos();
        im += v * th.sin();
    }
    2.0 * (re * re + im * im).sqrt() / N as f64
}

/// Gather the whole fit window at a constant sub-pixel offset and read the
/// amplitude back out. The plant has unit amplitude, so this IS the ratio.
fn ratio_at_offset(r: Resampler, f: f64, dx: f64) -> f64 {
    let data = plant(f);
    let p = PlaneRef::new(&data, W, H).expect("plane");
    let mut out = Vec::with_capacity(N);
    for i in 0..N {
        let x = (MARGIN + i) as f64 + dx;
        out.push(f64::from(r.sample(p, x, ROW)));
    }
    // The gathered signal is the source shifted by dx, so its amplitude at f is
    // unchanged by the shift itself and any loss is the kernel's.
    amplitude(&out, MARGIN, f)
}

/// Phase-averaged ratio, over the same 64 phases `gather_mtf` integrates.
fn ratio_phase_avg(r: Resampler, f: f64) -> f64 {
    let mut acc = 0.0;
    for p in 0..PHASES {
        acc += ratio_at_offset(r, f, (p as f64 + 0.5) / PHASES as f64);
    }
    acc / PHASES as f64
}

/// RMS error of the gathered signal against the analytically shifted truth,
/// in units of the plant's amplitude.
///
/// **This exists because the amplitude read-out above has a blind spot and the
/// blind spot is not hypothetical.** `nearest` displaces every sample to the
/// grid but does not attenuate the sinusoid, so a passband-gain statistic
/// scores it 1.000 — perfect — at every frequency. It is the worst gather in
/// the enum. Any metric built on band power alone therefore ranks the crippled
/// kernel first, which is the direction this class of metric can be fooled in
/// (M118 pre-registered exactly this and observed it).
fn rms_error_at_offset(r: Resampler, f: f64, dx: f64) -> f64 {
    let data = plant(f);
    let p = PlaneRef::new(&data, W, H).expect("plane");
    let mut acc = 0.0;
    for i in 0..N {
        let x = (MARGIN + i) as f64;
        let got = f64::from(r.sample(p, x + dx, ROW));
        let want = (2.0 * std::f64::consts::PI * f * (x + dx)).cos();
        acc += (got - want) * (got - want);
    }
    (acc / N as f64).sqrt()
}

/// A pure scale gather about the field centre, which is what `fit_to_cover`
/// composes onto every placement: destination `x` reads source
/// `cx + (x - cx) / k`. To land at OUTPUT frequency `f` the source must carry
/// `f * k`, so the plant frequency is chosen for the band being asked about.
fn ratio_pure_scale(r: Resampler, f_out: f64, k: f64) -> f64 {
    let f_src = f_out * k;
    // Wide enough that the widest read (N / (2k) either side of the centre)
    // never reaches the sampler's edge clamp.
    let w = 2 * (N + 2 * MARGIN);
    let data = plant_w(f_src, w);
    let p = PlaneRef::new(&data, w, H).expect("plane");
    let cx = (w / 2) as f64;
    let x0 = w / 2 - N / 2;
    let mut out = Vec::with_capacity(N);
    for i in 0..N {
        let xd = (x0 + i) as f64;
        out.push(f64::from(r.sample(p, cx + (xd - cx) / k, ROW)));
    }
    amplitude(&out, x0, f_out)
}

fn main() {
    println!("BUILD-RESAMP — isolated gather-kernel MTF, measured on align.rs's own samplers");
    println!(
        "plane {W} x {H}, fit window N = {N} from x = {MARGIN}, row {ROW}, {PHASES} phases\n"
    );

    println!("=== NULL: dx = 0 must read 1.000000 for every kernel at every f ===");
    print!("{:<14}", "kernel");
    for f in FREQS {
        print!("{:>12}", format!("f={f:.2}"));
    }
    println!();
    let mut null_worst: f64 = 0.0;
    for (name, r) in KERNELS {
        print!("{name:<14}");
        for f in FREQS {
            let v = ratio_at_offset(*r, *f, 0.0);
            null_worst = null_worst.max((v - 1.0).abs());
            print!("{v:>12.6}");
        }
        println!();
    }
    println!("worst |ratio - 1| at dx=0 : {null_worst:.3e}");
    println!(
        "NULL {}\n",
        if null_worst < 1e-6 { "PASS" } else { "FAIL — the harness is wrong, not align.rs" }
    );

    println!("=== dx = 0.5 (worst phase) ===");
    print!("{:<14}", "kernel");
    for f in FREQS {
        print!("{:>12}", format!("f={f:.2}"));
    }
    println!();
    for (name, r) in KERNELS {
        print!("{name:<14}");
        for f in FREQS {
            print!("{:>12.6}", ratio_at_offset(*r, *f, 0.5));
        }
        println!();
    }
    println!();

    println!("=== phase-averaged over 64 sub-pixel offsets (MEASURED) ===");
    print!("{:<14}", "kernel");
    for f in FREQS {
        print!("{:>12}", format!("f={f:.2}"));
    }
    println!();
    for (name, r) in KERNELS {
        print!("{name:<14}");
        for f in FREQS {
            print!("{:>12.6}", ratio_phase_avg(*r, *f));
        }
        println!();
    }
    println!();

    println!("=== restore::gather_mtf, the MODEL, same axis (cross-check) ===");
    print!("{:<14}", "kernel");
    for f in FREQS {
        print!("{:>12}", format!("f={f:.2}"));
    }
    println!();
    for (name, r) in KERNELS {
        print!("{name:<14}");
        for f in FREQS {
            print!("{:>12.6}", gather_mtf(*r, *f));
        }
        println!();
    }
    println!();

    println!("=== POTENCY: measured phase-averaged loss vs catmull-rom ===");
    println!("(a kernel that cannot lose signal cannot be evidence about a kernel that can)");
    print!("{:<14}", "kernel/CR");
    for f in FREQS {
        print!("{:>12}", format!("f={f:.2}"));
    }
    println!();
    let cr: Vec<f64> = FREQS
        .iter()
        .map(|f| ratio_phase_avg(Resampler::CatmullRom, *f))
        .collect();
    for (name, r) in KERNELS {
        print!("{name:<14}");
        for (i, f) in FREQS.iter().enumerate() {
            print!("{:>12.4}", ratio_phase_avg(*r, *f) / cr[i]);
        }
        println!();
    }
    println!();

    println!("=== FIDELITY at dx = 0.5: rms(gathered - truth) / amplitude ===");
    println!("the amplitude table above scores `nearest` 1.000 everywhere; this one does not.");
    print!("{:<14}", "kernel");
    for f in FREQS {
        print!("{:>12}", format!("f={f:.2}"));
    }
    println!();
    for (name, r) in KERNELS {
        print!("{name:<14}");
        for f in FREQS {
            print!("{:>12.6}", rms_error_at_offset(*r, *f, 0.5));
        }
        println!();
    }
    println!();

    println!("=== the fit_to_cover coverage upscale, ALONE, catmull-rom ===");
    println!("k is the field-of-view scale the merge prints; the upscale is 1/k.");
    print!("{:<14}", "k");
    for f in FREQS {
        print!("{:>12}", format!("f={f:.2}"));
    }
    println!();
    for k in [1.0, 0.9765, 0.9653, 0.9315] {
        print!("{k:<14.4}");
        for f in FREQS {
            print!("{:>12.6}", ratio_pure_scale(Resampler::CatmullRom, *f, k));
        }
        println!();
    }
    println!();
    println!("=== the same upscale under lanczos3 ===");
    print!("{:<14}", "k");
    for f in FREQS {
        print!("{:>12}", format!("f={f:.2}"));
    }
    println!();
    for k in [1.0, 0.9765, 0.9653, 0.9315] {
        print!("{k:<14.4}");
        for f in FREQS {
            print!("{:>12.6}", ratio_pure_scale(Resampler::Lanczos3, *f, k));
        }
        println!();
    }
}
