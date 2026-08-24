//! M95: verify the Lanczos-3 gather kernel delivered as a patch in
//! `docs/research/M95-cdiff.md` §7.
//!
//! The patch adds a resampler to `strehl_core::align`, which is **M86's file**
//! and which M95 does not own and has not touched. This example carries the
//! same `lanczos3_weights` body verbatim so that the numerics handed over are
//! compiled and asserted rather than asserted alone.
//!
//! Run: `cargo run -p strehl-cli --release --example m95-lanczos`

/// Verbatim from the patch in `docs/research/M95-cdiff.md` §7.
#[inline]
fn lanczos3_weights(f: f32) -> [f32; 6] {
    #[inline]
    fn l3(x: f32) -> f32 {
        if x.abs() < 1e-6 {
            return 1.0;
        }
        if x.abs() >= 3.0 {
            return 0.0;
        }
        let px = std::f32::consts::PI * x;
        3.0 * (px.sin() * (px / 3.0).sin()) / (px * px)
    }
    let mut w = [0f32; 6];
    let mut s = 0f32;
    for (i, wi) in w.iter_mut().enumerate() {
        *wi = l3(f - (i as f32 - 2.0));
        s += *wi;
    }
    if s.abs() > 1e-12 {
        for wi in w.iter_mut() {
            *wi /= s;
        }
    }
    w
}

/// Catmull-Rom weights, matching `strehl_core::align::catmull_rom_weights`.
/// Present as the **control**: the assertions below must separate the two.
#[inline]
fn catmull_rom_weights(f: f32) -> [f32; 4] {
    let f2 = f * f;
    let f3 = f2 * f;
    [
        -0.5 * f3 + f2 - 0.5 * f,
        1.5 * f3 - 2.5 * f2 + 1.0,
        -1.5 * f3 + 2.0 * f2 + 0.5 * f,
        0.5 * f3 - 0.5 * f2,
    ]
}

fn main() {
    let mut fail = 0usize;

    // C1 INTERPOLATING. At phase 0 the kernel must be a delta on the centre
    // tap, or an identity transform is not an identity. This is the control
    // that Mitchell fails (-0.2008 dex at identity phase) and it is why the
    // measured Lanczos-3 number is admissible.
    let w = lanczos3_weights(0.0);
    let want = [0.0f32, 0.0, 1.0, 0.0, 0.0, 0.0];
    let e: f32 = w
        .iter()
        .zip(want.iter())
        .map(|(a, b)| (a - b).abs())
        .fold(0.0, f32::max);
    println!("C1 interpolating at phase 0   max|w - delta| = {e:.3e}");
    if e > 1e-6 {
        println!("   FAIL");
        fail += 1;
    }

    // C2 PARTITION OF UNITY at every phase, or a flat field acquires a
    // phase-dependent gain and smooth gradients band.
    let mut worst = 0f32;
    for i in 0..=1000 {
        let f = i as f32 / 1000.0;
        let s: f32 = lanczos3_weights(f).iter().sum();
        worst = worst.max((s - 1.0).abs());
    }
    println!("C2 partition of unity         max|sum(w) - 1| = {worst:.3e}");
    if worst > 1e-6 {
        println!("   FAIL");
        fail += 1;
    }

    // C3 SUPPORT. Taps must vanish at the window edge, or the clamp in
    // sample_lanczos3 is reading pixels the kernel still weights.
    let edge = lanczos3_weights(1.0);
    println!(
        "C3 support                    w[0] at phase 1 = {:.3e}",
        edge[0]
    );
    if edge[0].abs() > 1e-6 {
        println!("   FAIL");
        fail += 1;
    }

    // C4 DISCRIMINATION. A control that cannot separate the two kernels is not
    // evidence that they differ. Reconstruct a half-pixel-shifted cosine near
    // Nyquist with each and show Lanczos-3 preserves more of it.
    let recon = |freq: f32, phase: f32, taps: usize| -> f32 {
        let mut num = 0f32;
        let mut den = 0f32;
        for k in -40i32..40 {
            let want = (std::f32::consts::TAU * freq * (k as f32 + phase)).cos();
            let got = if taps == 6 {
                let w = lanczos3_weights(phase);
                (0..6)
                    .map(|j| {
                        w[j] * (std::f32::consts::TAU * freq * (k + j as i32 - 2) as f32).cos()
                    })
                    .sum::<f32>()
            } else {
                let w = catmull_rom_weights(phase);
                (0..4)
                    .map(|j| {
                        w[j] * (std::f32::consts::TAU * freq * (k + j as i32 - 1) as f32).cos()
                    })
                    .sum::<f32>()
            };
            num += got * want;
            den += want * want;
        }
        num / den
    };
    let (f, ph) = (0.40f32, 0.5f32);
    let g_l = recon(f, ph, 6);
    let g_c = recon(f, ph, 4);
    println!("C4 gain at {f} cyc/px, phase {ph}   lanczos3 {g_l:.4}  catmullrom {g_c:.4}");
    if g_l <= g_c {
        println!("   FAIL -- kernels not separated, the comparison is not evidence");
        fail += 1;
    }

    println!();
    if fail == 0 {
        println!("M95 LANCZOS-3 PATCH VERIFIED  (4/4 controls)");
    } else {
        println!("M95 LANCZOS-3 PATCH FAILED  ({fail} control(s))");
        std::process::exit(1);
    }
}
