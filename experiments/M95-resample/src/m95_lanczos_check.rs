// M95 arm 4 - standalone verification of the Lanczos-3 gather patch handed to M86.
//
// The workspace does not currently compile (align_cmd.rs is M86's mid-edit untracked
// file), so this cannot be checked by building strehl. It is compiled and run on its own
// with rustc instead, so the patch in the report is KNOWN to compile and to satisfy the
// properties align.rs already asserts of its interpolators, rather than merely asserted.
//
//   rustc -O m95_lanczos_check.rs -o m95_lanczos_check.exe && ./m95_lanczos_check.exe

// ---- verbatim from the patch --------------------------------------------------------

/// Normalised Lanczos-3 weights for the six taps at offsets `-2 ..= 3`.
#[inline]
fn lanczos3_weights(f: f32) -> [f32; 6] {
    #[inline]
    fn l3(x: f32) -> f32 {
        if x == 0.0 {
            return 1.0;
        }
        let ax = x.abs();
        if ax >= 3.0 {
            return 0.0;
        }
        let px = std::f32::consts::PI * x;
        3.0 * px.sin() * (px / 3.0).sin() / (px * px)
    }
    let mut w = [0f32; 6];
    let mut s = 0f32;
    for (i, wi) in w.iter_mut().enumerate() {
        *wi = l3(f - (i as f32 - 2.0));
        s += *wi;
    }
    // Lanczos weights do NOT sum to one at an arbitrary phase. Without this the
    // gather applies a phase-dependent gain, which on a zoom is a smooth radial
    // brightness ripple -- exactly the kind of artefact that looks like a halo.
    if s != 0.0 {
        for wi in w.iter_mut() {
            *wi /= s;
        }
    }
    w
}

// ---- a stand-in for PlaneRef so this file needs no crate -----------------------------

struct Plane {
    data: Vec<f32>,
    width: usize,
    height: usize,
}

fn sample_lanczos3(p: &Plane, x: f64, y: f64) -> f32 {
    let x = x.clamp(2.0, (p.width - 4) as f64);
    let y = y.clamp(2.0, (p.height - 4) as f64);
    let (x0, y0) = (x.floor() as usize, y.floor() as usize);
    let wx = lanczos3_weights((x - x0 as f64) as f32);
    let wy = lanczos3_weights((y - y0 as f64) as f32);
    let mut acc = 0f32;
    for (dy, wyv) in wy.iter().enumerate() {
        let row = (y0 + dy - 2) * p.width + x0 - 2;
        let mut r = 0f32;
        for (dx, wxv) in wx.iter().enumerate() {
            r += p.data[row + dx] * *wxv;
        }
        acc += r * *wyv;
    }
    acc
}

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

fn sample_catmull_rom(p: &Plane, x: f64, y: f64) -> f32 {
    let x = x.clamp(1.0, (p.width - 3) as f64);
    let y = y.clamp(1.0, (p.height - 3) as f64);
    let (x0, y0) = (x.floor() as usize, y.floor() as usize);
    let wx = catmull_rom_weights((x - x0 as f64) as f32);
    let wy = catmull_rom_weights((y - y0 as f64) as f32);
    let mut acc = 0f32;
    for (dy, wyv) in wy.iter().enumerate() {
        let row = (y0 + dy - 1) * p.width + x0 - 1;
        let mut r = 0f32;
        for (dx, wxv) in wx.iter().enumerate() {
            r += p.data[row + dx] * *wxv;
        }
        acc += r * *wyv;
    }
    acc
}

fn main() {
    let mut fails = 0;

    // --- 1. weights are normalised at every phase ---
    let mut worst = 0f32;
    for i in 0..=1000 {
        let f = i as f32 / 1000.0;
        let s: f32 = lanczos3_weights(f).iter().sum();
        worst = worst.max((s - 1.0).abs());
    }
    println!("1. weights sum to 1: worst |sum-1| = {worst:.3e}");
    if worst > 1e-5 {
        println!("   FAIL");
        fails += 1;
    }

    // --- 2. INTERPOLATING: reproduces the samples at integer positions ---
    // align.rs asserts exactly this of Catmull-Rom in
    // `catmull_rom_reproduces_the_samples_at_integer_positions`.
    let n = 32;
    let mut p = Plane { data: vec![0.0; n * n], width: n, height: n };
    for y in 0..n {
        for x in 0..n {
            p.data[y * n + x] = ((x * 7 + y * 13) % 251) as f32;
        }
    }
    let mut worst_id = 0f32;
    for y in 4..n - 5 {
        for x in 4..n - 5 {
            let s = sample_lanczos3(&p, x as f64, y as f64);
            worst_id = worst_id.max((s - p.data[y * n + x]).abs());
        }
    }
    println!("2. identity at integer positions: worst error = {worst_id:.3e} DN");
    if worst_id > 1e-2 {
        println!("   FAIL");
        fails += 1;
    }

    // --- 3. keeps MORE high frequency than Catmull-Rom at a half-pixel shift ---
    // This is the whole point of the patch and it must be visible in the Rust, not
    // only in the Python that motivated it.
    for y in 0..n {
        for x in 0..n {
            let v = (std::f32::consts::PI * (x as f32) * 0.45).cos()
                * (std::f32::consts::PI * (y as f32) * 0.45).cos();
            p.data[y * n + x] = 1000.0 + 400.0 * v;
        }
    }
    let energy = |f: &dyn Fn(&Plane, f64, f64) -> f32| -> f32 {
        let mut e = 0f32;
        for y in 4..n - 5 {
            for x in 4..n - 5 {
                let a = f(&p, x as f64 + 0.5, y as f64 + 0.5);
                let b = f(&p, x as f64 + 1.5, y as f64 + 0.5);
                e += (b - a) * (b - a);
            }
        }
        e
    };
    let e_cr = energy(&sample_catmull_rom);
    let e_l3 = energy(&sample_lanczos3);
    println!("3. half-pixel gather, gradient energy at 0.45 cyc/px:");
    println!("     catmull-rom {e_cr:.4e}");
    println!("     lanczos-3   {e_l3:.4e}   ({:.3}x)", e_l3 / e_cr);
    if e_l3 <= e_cr {
        println!("   FAIL: lanczos-3 did not retain more");
        fails += 1;
    }

    // --- 4. NEGATIVE CONTROL: on a SMOOTH field the two must agree closely. ---
    // A kernel change that moved a smooth ramp would be changing geometry or gain,
    // not sharpness, and that would invalidate reading (3) as a sharpness result.
    for y in 0..n {
        for x in 0..n {
            p.data[y * n + x] = 100.0 + 3.0 * x as f32 + 5.0 * y as f32;
        }
    }
    let mut worst_smooth = 0f32;
    for y in 4..n - 5 {
        for x in 4..n - 5 {
            let a = sample_catmull_rom(&p, x as f64 + 0.5, y as f64 + 0.5);
            let b = sample_lanczos3(&p, x as f64 + 0.5, y as f64 + 0.5);
            worst_smooth = worst_smooth.max((a - b).abs());
        }
    }
    println!("4. smooth ramp, worst |catmull-rom - lanczos3| = {worst_smooth:.3e} DN");
    if worst_smooth > 1e-2 {
        println!("   FAIL: the kernels disagree on a ramp, so (3) is not purely sharpness");
        fails += 1;
    }

    println!("\n{}", if fails == 0 { "ALL CHECKS PASS" } else { "SOME CHECKS FAILED" });
    std::process::exit(if fails == 0 { 0 } else { 1 });
}
