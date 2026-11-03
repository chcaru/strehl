//! Fold a synthetic focus stack through the production `BandMerge`.
//!
//! usage: iq-synth-merge DIR W H N
//! Reads DIR/frame-XXX.f32 (luma, DN, little-endian, W*H) and DIR/var-XXX.f32
//! (per-pixel noise variance, DN^2) for XXX in 0..N, folds them in index order
//! with the default merge configuration (the ensemble gate follows its
//! environment switch exactly as in production) and writes DIR/merged.f32.
use std::fs;
use strehl_core::pyramid::{BandGain, BandMerge, FrameWorkspace, MergeConfig, Pyramid, Workspace, level_sizes};

fn read(path: &str, n: usize) -> Vec<f32> {
    let b = fs::read(path).unwrap_or_else(|e| panic!("{path}: {e}"));
    assert_eq!(b.len(), n * 4, "{path} has the wrong size");
    b.chunks_exact(4).map(|c| f32::from_le_bytes([c[0], c[1], c[2], c[3]])).collect()
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    let dir = &a[1];
    let (w, h, n): (usize, usize, usize) = (a[2].parse().unwrap(), a[3].parse().unwrap(), a[4].parse().unwrap());
    let mut cfg = MergeConfig::default();
    if std::env::var("SYNTH_BASE").as_deref() == Ok("weighted") {
        cfg.base = strehl_core::pyramid::BaseBand::WeightedFromCoarsest;
    }
    if let Some(p) = std::env::var("SYNTH_EXPONENT").ok().and_then(|v| v.parse().ok()) {
        cfg.exponent = p;
    }
    if let Some(r) = std::env::var("SYNTH_SHARPEN").ok().and_then(|v| v.parse().ok()) {
        cfg.sharpen_per_octave = r;
    }
    let sizes = level_sizes(w, h, cfg.bands);
    let mut merge = BandMerge::new(w, h, 1, cfg);
    let mut fws = FrameWorkspace::new(&sizes, 1);
    // Per-frame null probe, as the CLI supplies for warped frames: unit white
    // noise through the same pyramid, gated by the same white floor.
    let white = BandGain::measure(sizes.len() - 1);
    let beta: Vec<f32> = (0..sizes.len() - 1).map(|k| white.beta(k)).collect();
    let mut ws = Workspace::new(&sizes);
    let mut state: u64 = 0x5EED;
    let mut normal = move || {
        let mut acc = 0.0f32;
        for _ in 0..12 {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            acc += ((state >> 11) as f64 / (1u64 << 53) as f64) as f32;
        }
        acc - 6.0
    };
    for i in 0..n {
        let noise: Vec<f32> = (0..w * h).map(|_| normal()).collect();
        let mut pyr = Pyramid::zeros(&sizes);
        pyr.build(&noise, &mut ws);
        let levels: Vec<&[f32]> = (0..sizes.len() - 1).map(|k| pyr.level(k)).collect();
        merge.add_null_frame(&levels, &beta, 1.0);
        let f = read(&format!("{dir}/frame-{i:03}.f32"), w * h);
        let v = read(&format!("{dir}/var-{i:03}.f32"), w * h);
        fws.next_frame();
        merge.add_frame(&[&f], &f, &v, &mut fws);
    }
    let out = merge.finish(&mut Workspace::new(&sizes));
    let bytes: Vec<u8> = out[0].iter().flat_map(|v| v.to_le_bytes()).collect();
    fs::write(format!("{dir}/merged.f32"), bytes).unwrap();
    eprintln!("folded {n} frames of {w}x{h}");
}
