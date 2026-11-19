//! The device convolution against `strehl_core::optical_restore::convolve`,
//! bit for bit, at odd sizes and radii 4, 5, 17 and 32, with zero taps
//! (skipped by both) and mirrored borders. Needs a Vulkan GPU with f64:
//! `cargo test -p strehl-gpu -- --ignored`.
use strehl_core::optical_restore::{Kernel, convolve};

struct Rng(u64);
impl Rng {
    fn next(&mut self) -> f32 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        (self.0 >> 40) as f32 / (1u64 << 24) as f32
    }
}

#[test]
#[ignore = "needs a Vulkan GPU with f64"]
fn the_device_convolution_is_the_cpu_convolution() {
    let mut rng = Rng(0x2545_F491_4F6C_DD1D);
    for (w, h, radius) in [
        (97usize, 61usize, 4usize),
        (131, 77, 5),
        (203, 151, 17),
        (257, 199, 32),
    ] {
        let side = 2 * radius + 1;
        let taps: Vec<f32> = (0..side * side)
            .map(|i| {
                if i % 7 == 3 {
                    0.0
                } else {
                    (rng.next() - 0.3) * 0.01
                }
            })
            .collect();
        let src: Vec<f32> = (0..w * h)
            .map(|i| match i % 101 {
                0 => -0.0,
                1 => 0.0,
                _ => (rng.next() * 140.0).sqrt(),
            })
            .collect();
        let kernel = Kernel {
            radius,
            taps: taps.clone(),
            band_error: 0.0,
            max_error: 0.0,
            delivered: 1.0,
        };
        let cpu = convolve(&src, w, h, &kernel);
        let gpu = strehl_gpu::convolve(&src, w, h, radius, &taps).expect("device convolution");
        let differ = cpu
            .iter()
            .zip(&gpu)
            .filter(|(a, b)| a.to_bits() != b.to_bits())
            .count();
        assert_eq!(differ, 0, "{w}x{h} radius {radius}: {differ} pixels differ");
    }
}
