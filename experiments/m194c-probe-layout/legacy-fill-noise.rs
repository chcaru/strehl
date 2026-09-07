fn fill_noise(data: &mut [u16], level: f64, sigma: f64, index: usize) {
    // SplitMix64. Self-contained on purpose: the probe's determinism is a
    // property of this file and should not move if a shared RNG is retuned.
    let mut s = 0x9E37_79B9_7F4A_7C15u64
        .wrapping_mul(index as u64 + 1)
        ^ 0x2545_F491_4F6C_DD1D;
    let mut next = || {
        s = s.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = s;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        f64::from(((z ^ (z >> 31)) >> 40) as u32) / f64::from(1u32 << 24)
    };
    let mut spare: Option<f64> = None;
    for d in data.iter_mut() {
        // Box-Muller, both draws used.
        let g = match spare.take() {
            Some(g) => g,
            None => {
                let (u1, u2) = (next().max(1e-12), next());
                let r = (-2.0 * u1.ln()).sqrt();
                let th = std::f64::consts::TAU * u2;
                spare = Some(r * th.sin());
                r * th.cos()
            }
        };
        *d = (level + sigma * g).round().clamp(0.0, f64::from(u16::MAX)) as u16;
    }
}
