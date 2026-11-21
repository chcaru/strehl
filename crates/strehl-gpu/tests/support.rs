//! The GPU fold's per-plane admission maps (`GpuFold::enable_support`)
//! against the CPU observer's view of the same fold: for every frame and
//! level, `weight > 0` at every lattice site, bit for bit. Needs a Vulkan GPU
//! with f64, so it is ignored by default: `cargo test -p strehl-gpu -- --ignored`.
use std::sync::Mutex;
use strehl_core::pyramid::{
    BandMerge, BandObservation, FoldPhase, FrameWorkspace, LevelSize, MergeConfig, MergeObserver,
    level_sizes,
};
use strehl_gpu::GpuFold;

struct Rng(u64);
impl Rng {
    fn next(&mut self) -> f32 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        (self.0 >> 40) as f32 / (1u64 << 24) as f32
    }
}

/// Integer-valued planes whose sharp region moves with `f`, with a flat left
/// third (weights there sit at the exp(-80) clamp or zero): both outcomes
/// occur at every fine level.
fn frame(w: usize, h: usize, f: usize, rng: &mut Rng) -> Vec<Vec<f32>> {
    (0..4)
        .map(|c| {
            (0..w * h)
                .map(|i| {
                    let (x, y) = ((i % w) as f32, (i / w) as f32);
                    let sharp = if (x as usize * 6 / w + f).is_multiple_of(6) {
                        1.0
                    } else {
                        0.15
                    };
                    let flat = x < w as f32 / 3.0;
                    let detail = if flat { 0.0 } else { 1.0 }
                        * 900.0
                        * sharp
                        * ((x * 0.71 + c as f32).sin() * (y * 0.43).cos());
                    let base = 300.0 + 40.0 * c as f32 + 200.0 * (x / w as f32);
                    let noise = (rng.next() - 0.5) * if flat { 60.0 } else { 30.0 };
                    (base + detail + noise).round().max(0.0)
                })
                .collect()
        })
        .collect()
}

/// The desktop lattice, written here from its definition rather than shared
/// with the CLI: at most 128 x 96, aspect preserved, never upsampled.
fn lattice(size: LevelSize) -> (usize, usize) {
    let factor = (128.0 / size.width as f64)
        .min(96.0 / size.height as f64)
        .min(1.0);
    (
        ((size.width as f64 * factor).floor() as usize).max(1),
        ((size.height as f64 * factor).floor() as usize).max(1),
    )
}

/// Nearest-coefficient sample of site `s` of `m` along an axis of `n`.
fn site(s: usize, m: usize, n: usize) -> usize {
    ((2 * s + 1) * n / (2 * m)).min(n - 1)
}

/// Each band the CPU fold observes, sampled at the lattice: `(level, bits)`.
struct Observed {
    maps: Mutex<Vec<(usize, Vec<bool>)>>,
    shifted: bool,
}
impl MergeObserver for Observed {
    fn phase(&self, _: FoldPhase) {}
    fn band(&self, band: BandObservation<'_>) {
        let (lw, lh) = lattice(band.size);
        let (w, h) = (band.size.width, band.size.height);
        let mut bits = Vec::with_capacity(lw * lh);
        for y in 0..lh {
            for x in 0..lw {
                // The negative control samples one coefficient to the left.
                let sx = if self.shifted {
                    site(x, lw, w).saturating_sub(1)
                } else {
                    site(x, lw, w)
                };
                bits.push(band.weights[site(y, lh, h) * w + sx] > 0.0);
            }
        }
        self.maps.lock().unwrap().push((band.level, bits));
    }
}

fn unpack(bytes: &[u8], sites: usize) -> Vec<bool> {
    assert_eq!(bytes.len(), sites.div_ceil(8));
    if !sites.is_multiple_of(8) {
        assert_eq!(
            bytes[sites / 8] >> (sites % 8),
            0,
            "bits past the last site"
        );
    }
    (0..sites)
        .map(|i| bytes[i / 8] & (1 << (i % 8)) != 0)
        .collect()
}

#[test]
#[ignore = "needs a Vulkan GPU with f64"]
fn gpu_admission_maps_are_the_cpu_weights_above_zero() {
    for (w, h, bands, frames) in [(193usize, 131usize, 5usize, 7usize), (640, 427, 7, 12)] {
        let cfg = MergeConfig {
            bands,
            ..Default::default()
        };
        let sizes = level_sizes(w, h, cfg.bands);
        let lattices: Vec<(usize, usize)> = sizes.iter().map(|&s| lattice(s)).collect();
        let mut rng = Rng(0x2545_F491_4F6C_DD1D ^ w as u64);
        let beta: Vec<f32> = vec![0.41, 0.093, 0.021, 0.006];
        let mut cpu = BandMerge::new(w, h, 4, cfg);
        let mut gpu_merge = BandMerge::new(w, h, 4, cfg);
        let mut gpu = GpuFold::new(&gpu_merge).expect("GPU fold");
        gpu.enable_support(&lattices).expect("lattices fit");
        let mut fws = FrameWorkspace::new(&sizes, 4);
        let mut cpu_maps = Vec::new();
        let mut shifted_maps = Vec::new();
        let mut gpu_maps = Vec::new();
        for f in 0..frames {
            let planes = frame(w, h, f, &mut rng);
            let luma: Vec<f32> = planes[1]
                .iter()
                .zip(&planes[2])
                .map(|(a, b)| 0.5 * (a + b))
                .collect();
            let var: Vec<f32> = luma.iter().map(|l| 0.3 * l.max(0.0) + 7.0).collect();
            let refs: Vec<&[f32]> = planes.iter().map(Vec::as_slice).collect();
            for (shifted, out) in [(false, &mut cpu_maps), (true, &mut shifted_maps)] {
                let observer = Observed {
                    maps: Mutex::new(Vec::new()),
                    shifted,
                };
                // The shifted pass folds into a throwaway merge.
                let mut target = if shifted {
                    BandMerge::new(w, h, 4, cfg)
                } else {
                    std::mem::replace(&mut cpu, BandMerge::new(1, 1, 4, cfg))
                };
                fws.next_frame();
                target.add_frame_with_gain_observed(
                    &refs,
                    &luma,
                    &var,
                    Some(&beta),
                    &mut fws,
                    &observer,
                );
                if !shifted {
                    cpu = target;
                }
                out.push(observer.maps.into_inner().unwrap());
            }
            gpu.tag_support(100 + f);
            gpu.add_frame(&mut gpu_merge, &refs, &var, Some(&beta));
            gpu_maps.extend(gpu.collect_support(false).expect("maps"));
        }
        gpu_maps.extend(gpu.collect_support(true).expect("maps"));
        assert_eq!(
            gpu_maps.iter().map(|m| m.tag).collect::<Vec<_>>(),
            (100..100 + frames).collect::<Vec<_>>(),
            "one set of maps per fold, in fold order"
        );
        let (mut on, mut off, mut shifted_differs) = (0, 0, 0);
        for (f, (maps, device)) in cpu_maps.iter().zip(&gpu_maps).enumerate() {
            assert_eq!(maps.len(), sizes.len(), "the CPU observes every level");
            assert_eq!(device.levels.len(), sizes.len());
            for (k, (level, bits)) in maps.iter().enumerate() {
                assert_eq!(*level, k);
                let (lw, lh) = lattices[k];
                let device_bits = unpack(&device.levels[k], lw * lh);
                let differ = bits
                    .iter()
                    .zip(&device_bits)
                    .filter(|(a, b)| a != b)
                    .count();
                assert_eq!(
                    differ, 0,
                    "{w}x{h} frame {f} level {k}: {differ} sites differ"
                );
                on += bits.iter().filter(|&&b| b).count();
                off += bits.iter().filter(|&&b| !b).count();
                shifted_differs += usize::from(shifted_maps[f][k].1 != device_bits);
            }
        }
        assert!(
            on > 0 && off > 0,
            "{w}x{h}: both outcomes must occur ({on} on, {off} off)"
        );
        assert!(
            shifted_differs > 0,
            "{w}x{h}: a one-coefficient sampling shift must be detectable"
        );
        // The maps are reads: the fold's totals are still the CPU's.
        gpu.finish_chunk(&mut gpu_merge);
        let (a, b) = (
            cpu.totals_mut().den.to_vec(),
            gpu_merge.totals_mut().den.to_vec(),
        );
        for (k, (x, y)) in a.iter().zip(&b).enumerate() {
            let differ = x
                .iter()
                .zip(y)
                .filter(|(p, q)| p.to_bits() != q.to_bits())
                .count();
            assert_eq!(
                differ, 0,
                "{w}x{h}: den[{k}] differs at {differ} coefficients"
            );
        }
    }
}

#[test]
#[ignore = "needs a Vulkan GPU with f64"]
fn lattices_that_do_not_fit_are_refused() {
    let cfg = MergeConfig {
        bands: 5,
        ..Default::default()
    };
    let merge = BandMerge::new(193, 131, 4, cfg);
    let mut gpu = GpuFold::new(&merge).expect("GPU fold");
    let sizes = level_sizes(193, 131, cfg.bands);
    let good: Vec<(usize, usize)> = sizes.iter().map(|&s| lattice(s)).collect();
    assert!(
        gpu.enable_support(&good[1..]).is_err(),
        "one lattice per level"
    );
    let mut wide = good.clone();
    wide[0] = (129, 96);
    assert!(
        gpu.enable_support(&wide).is_err(),
        "above the 128 x 96 limit"
    );
    let mut beyond = good.clone();
    let last = sizes.len() - 1;
    beyond[last] = (sizes[last].width + 1, sizes[last].height);
    assert!(
        gpu.enable_support(&beyond).is_err(),
        "more sites than coefficients"
    );
    assert!(gpu.enable_support(&good).is_ok());
    assert!(
        gpu.collect_support(true).unwrap().is_empty(),
        "nothing folded yet"
    );
}
