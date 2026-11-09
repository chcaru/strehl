//! Device timing at a real frame geometry (bug-7: 7032 x 4688 CFA). Not a
//! correctness test: `cargo test --release -p strehl-gpu --test timing --
//! --ignored --nocapture`.
use std::time::Instant;

use strehl_core::pyramid::{BandMerge, MergeConfig, level_sizes};
use strehl_gpu::{GpuFold, GreenNoise, ProbeNoise, RawFrame, SitePull};

#[test]
#[ignore = "timing on a Vulkan GPU with f64"]
fn device_stage_timing() {
    let (gw, gh) = (3516usize, 2344usize);
    let stride = 2 * gw + 16;
    let cfg = MergeConfig {
        bands: 7,
        ..Default::default()
    };
    let mut merge = BandMerge::new(gw, gh, 4, cfg);
    let sizes = level_sizes(gw, gh, cfg.bands);
    let mut gpu = GpuFold::with_preparation(&merge, (gw, gh), [0, 0, gw, gh]).expect("GPU");
    let data: Vec<u16> = (0..stride * (2 * gh + 8))
        .map(|i| (512 + (i * 2_654_435_761) % 3001) as u16)
        .collect();
    let pull = |dx: f64| SitePull {
        a: [1.0002, 0.0001],
        b: [0.3 + dx, -0.2],
    };
    let frame = RawFrame {
        data: &data,
        stride,
        active: [8, 4],
        black: 512.0,
        gain: [2.0, 1.0, 1.6],
        pulls: Some([pull(0.0), pull(0.01), pull(0.02), pull(0.03)]),
    };
    let noise = ProbeNoise {
        seed: 7,
        level: 1024.0,
        sigma: 64.0,
    };
    let interior = |k: usize| {
        let s = sizes[k];
        let (mx, my) = (s.width / 8, s.height / 8);
        [k, mx, my, s.width - 2 * mx, s.height - 2 * my]
    };
    let sums: Vec<[usize; 5]> = (0..4).map(interior).collect();
    let windows = merge.null_window_rects();
    let green = GreenNoise {
        gain: [0.4, 0.4],
        read_dn: [2.0, 2.0],
    };
    let beta = [1.0f32, 0.05, 0.01, 0.002];
    for round in 0..12 {
        let t0 = Instant::now();
        gpu.probe(&frame, noise, &sums, &windows).expect("probe");
        let t1 = Instant::now();
        gpu.add_raw_frame(&mut merge, &frame, green, Some(&beta));
        // A second probe call waits for the fold; time only its wait by
        // timing an empty-request probe and subtracting a solo probe.
        let t2 = Instant::now();
        gpu.probe(&frame, noise, &[], &[]).expect("probe sync");
        let t3 = Instant::now();
        gpu.probe(&frame, noise, &[], &[]).expect("probe solo");
        let t4 = Instant::now();
        let ms = |a: Instant, b: Instant| (b - a).as_secs_f64() * 1e3;
        if round >= 2 {
            eprintln!(
                "probe(full) {:.1} ms | fold submit {:.1} | fold+probe(bare) {:.1} | probe(bare) {:.1}",
                ms(t0, t1),
                ms(t1, t2),
                ms(t2, t3),
                ms(t3, t4)
            );
        }
    }
    if let Some(report) = gpu.profile_report() {
        eprintln!("{report}");
    }
}
