//! The probe's f64 reductions on the device against the CPU's order of
//! addition: the zero-mean's exact sum, and `gatefloor::square_sum` (each row
//! in column order, then the row sums in row order), bit for bit.
//! `cargo test --release -p strehl-gpu --test probe-sums -- --ignored`
use strehl_core::pyramid::{BandMerge, MergeConfig};
use strehl_gpu::GpuFold;

fn splitmix(state: &mut u64) -> u64 {
    *state = state.wrapping_add(0x9e37_79b9_7f4a_7c15);
    let mut z = *state;
    z = (z ^ (z >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
    z ^ (z >> 31)
}

/// The CPU's `gatefloor::square_sum`.
fn square_sum(level: &[f32], width: usize, [x, y, w, h]: [usize; 4]) -> f64 {
    let rows: Vec<f64> = (y..y + h)
        .map(|r| {
            level[r * width + x..r * width + x + w]
                .iter()
                .fold(0.0f64, |acc, v| acc + f64::from(*v) * f64::from(*v))
        })
        .collect();
    rows.iter().fold(0.0f64, |acc, r| acc + r)
}

/// The same terms, each row and the rows added in reverse: a different
/// association, to show the comparison can see one.
fn square_sum_reversed(level: &[f32], width: usize, [x, y, w, h]: [usize; 4]) -> f64 {
    let rows: Vec<f64> = (y..y + h)
        .rev()
        .map(|r| {
            level[r * width + x..r * width + x + w]
                .iter()
                .rev()
                .fold(0.0f64, |acc, v| acc + f64::from(*v) * f64::from(*v))
        })
        .collect();
    rows.iter().fold(0.0f64, |acc, r| acc + r)
}

#[test]
#[ignore = "needs a Vulkan GPU with f64"]
fn the_device_probe_sums_are_the_cpu_sums() {
    let (gw, gh) = (1203usize, 811usize);
    let cfg = MergeConfig {
        bands: 6,
        ..Default::default()
    };
    let merge = BandMerge::new(gw, gh, 4, cfg);
    let mut gpu = GpuFold::with_preparation(&merge, (gw, gh), [0, 0, gw, gh]).expect("GPU");
    let mut state = 7u64;
    // Half-integers of probe-luma size: every partial sum is exact.
    let luma: Vec<f32> = (0..gw * gh)
        .map(|_| (splitmix(&mut state) % 131_071) as f32 * 0.5 - 32_767.5)
        .collect();
    // Square sums over values spanning many binades, so the association of
    // the f64 additions shows in the result.
    let level: Vec<f32> = (0..gw * gh)
        .map(|_| {
            let r = splitmix(&mut state);
            let m = (r & 0xff_ffff) as f32 / 16_777_216.0 + 0.5;
            let e = ((r >> 24) % 41) as i32 - 20;
            let s = if (r >> 40) & 1 == 1 { -1.0 } else { 1.0 };
            s * m * 2f32.powi(e)
        })
        .collect();
    let windows = [
        [0, 0, gw, gh],
        [150, 101, 903, 300],
        [3, 5, 7, 100],
        [17, 0, 1, 1],
        [1000, 700, 203, 111],
        [8, 9, 16, 1],
    ];
    let (total, _) = gpu.probe_sums(&luma, gw, &[]).expect("luma sum");
    let expect: f64 = luma.iter().map(|v| f64::from(*v)).sum();
    assert_eq!(
        total.to_bits(),
        expect.to_bits(),
        "exact sum {total} vs {expect}"
    );

    let (_, sums) = gpu.probe_sums(&level, gw, &windows).expect("square sums");
    let mut order_visible = 0;
    for (i, &w) in windows.iter().enumerate() {
        let cpu = square_sum(&level, gw, w);
        assert_eq!(
            sums[i].to_bits(),
            cpu.to_bits(),
            "window {w:?}: device {} vs CPU {cpu}",
            sums[i]
        );
        order_visible += usize::from(square_sum_reversed(&level, gw, w).to_bits() != cpu.to_bits());
    }
    assert!(
        order_visible >= 3,
        "the inputs must make the order of addition visible ({order_visible} windows)"
    );
}
