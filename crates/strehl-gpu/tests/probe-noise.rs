//! The device's probe noise against the CPU fill's definition, over awkward
//! geometry: odd stride, odd active origin, odd sample count, so fill rows
//! start and end mid-word. Needs a Vulkan GPU with f64:
//! `cargo test -p strehl-gpu -- --ignored`.
use strehl_core::portable_math::probe_gaussian_pair;
use strehl_core::pyramid::{BandMerge, MergeConfig};
use strehl_gpu::{GpuFold, ProbeNoise, RawFrame, SitePull};

/// `gatefloor::fill_probe_noise`, serial order: SplitMix64 from `seed`, one
/// pair per two sites, rows of `width` in active-relative order.
fn cpu_fill(
    data: &mut [u16],
    stride: usize,
    ax: usize,
    ay: usize,
    width: usize,
    rows: usize,
    n: ProbeNoise,
) {
    let mut s = n.seed;
    let mut next = || {
        s = s.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = s;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        ((z ^ (z >> 31)) >> 40) as u32
    };
    let mut spare = None;
    for y in 0..rows {
        for x in 0..width {
            let g = match spare.take() {
                Some(g) => g,
                None => {
                    let k1 = next();
                    let (c, s) = probe_gaussian_pair(k1, next());
                    spare = Some(s);
                    c
                }
            };
            data[(ay + y) * stride + ax + x] = (n.level + n.sigma * g)
                .round()
                .clamp(0.0, f64::from(u16::MAX))
                as u16;
        }
    }
}

#[test]
#[ignore = "needs a Vulkan GPU with f64"]
fn the_device_probe_noise_matches_the_cpu_fill() {
    // (gw, gh, stride, ax, ay, extra rows)
    for (gw, gh, stride, ax, ay, extra) in
        // The last is a full 33 MP frame: ~33 M samples, so the f32 screen's
        // f64 fallback runs thousands of times.
        [
            (97usize, 61usize, 201usize, 3usize, 1usize, 2usize),
            (128, 80, 256, 0, 0, 0),
            (75, 40, 157, 5, 2, 1),
            (3516, 2344, 7048, 8, 4, 8),
        ]
    {
        let (w, h) = (gw, gh);
        let merge = BandMerge::new(
            w,
            h,
            4,
            MergeConfig {
                bands: 4,
                ..Default::default()
            },
        );
        let mut gpu = GpuFold::with_preparation(&merge, (gw, gh), [0, 0, w, h]).expect("GPU");
        let len = (ay + 2 * gh + extra) * stride + extra;
        let data: Vec<u16> = (0..len).map(|i| (i * 2654435761 % 4001) as u16).collect();
        for (k, seed) in [0x2545_F491_4F6C_DD1Du64, 0x9E37_79B9_7F4A_7C15 ^ 77]
            .into_iter()
            .enumerate()
        {
            let noise = ProbeNoise {
                seed,
                level: 2512.0 + 37.0 * k as f64,
                sigma: 40.0 + 24.0 * k as f64,
            };
            let ident = SitePull {
                a: [1.0, 0.0],
                b: [0.0, 0.0],
            };
            let frame = RawFrame {
                data: &data,
                stride,
                active: [ax, ay],
                black: 512.0,
                gain: [2.0, 1.0, 1.5],
                pulls: Some([ident; 4]),
            };
            let got = gpu.probe_frame(&frame, noise).expect("probe frame");
            let mut want = data.clone();
            cpu_fill(&mut want, stride, ax, ay, 2 * gw, 2 * gh, noise);
            let diff = got.iter().zip(&want).filter(|(a, b)| a != b).count();
            assert_eq!(
                diff, 0,
                "{gw}x{gh} stride {stride} at ({ax},{ay}) seed {k}: {diff} of {len} differ"
            );
            assert_ne!(got, data, "the fill wrote nothing");
        }
    }
}
