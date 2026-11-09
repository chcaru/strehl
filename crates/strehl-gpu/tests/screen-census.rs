//! The selection weight's f32 ln and exp screens (`fold.wgsl`) against the
//! f64 functions on this device, over every input each can receive: every
//! positive normal f32 for ln (subnormals always fall back), every f32 in
//! [-80, 80] for exp (the weight clamps its exponent there). An accepted value
//! that differs from the f64 function's would change the fold's output, so the
//! census must find none. Needs a Vulkan GPU with f64, so it is ignored by
//! default: `cargo test --release -p strehl-gpu --test screen-census --
//! --ignored --nocapture`.
use std::time::Instant;

use strehl_core::pyramid::{BandMerge, MergeConfig};
use strehl_gpu::GpuFold;

#[test]
#[ignore = "needs a Vulkan GPU with f64; every input of both screens"]
fn the_weight_screens_are_exact_on_every_input() {
    let merge = BandMerge::new(64, 64, 4, MergeConfig::default());
    let mut gpu = GpuFold::new(&merge).expect("GPU fold");
    let ranges = [
        (
            "ln, positive normals",
            false,
            0x0080_0000u32,
            0x7f7f_ffffu32,
        ),
        ("exp, [0, 80]", true, 0, 80.0f32.to_bits()),
        ("exp, [-80, -0]", true, 0x8000_0000, (-80.0f32).to_bits()),
    ];
    let mut failed = false;
    for (name, exp, first, last) in ranges {
        let t = Instant::now();
        let c = gpu.screen_census(exp, first, last);
        eprintln!(
            "{name}: {} inputs, {} mismatches (first {:?}), {} fallbacks ({:.4}%), worst error {:.3} of the bound ({:.1} s)",
            c.inputs,
            c.mismatches,
            c.first_mismatch.map(|b| (b, f32::from_bits(b))),
            c.fallbacks,
            100.0 * c.fallbacks as f64 / c.inputs as f64,
            c.worst_ratio,
            t.elapsed().as_secs_f64()
        );
        assert_eq!(c.inputs, u64::from(last - first) + 1);
        failed |= c.mismatches != 0 || c.worst_ratio > 0.5;
    }
    assert!(
        !failed,
        "a screen accepted a value the f64 function does not give, or its error exceeded half its bound"
    );
}
