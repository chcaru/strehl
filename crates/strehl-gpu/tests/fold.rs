//! The GPU fold against the CPU fold, bit for bit. Needs a Vulkan GPU with f64,
//! so it is ignored by default: `cargo test -p strehl-gpu -- --ignored`.
use strehl_core::pyramid::{BandMerge, FrameWorkspace, MergeConfig, Workspace, level_sizes};
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

/// Four integer-valued planes, as `(u16 - black).max(0)` gives: a scene whose
/// sharp region moves with `f`, plus noise, clipped at zero like real data.
fn frame(w: usize, h: usize, f: usize, rng: &mut Rng) -> Vec<Vec<f32>> {
    // The left third is flat ground: weights there sit at the exp(-80) clamp,
    // so the soft-power numerator is subnormal -- the case a flushing device
    // gets wrong.
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

fn bits(v: &[Vec<f32>]) -> Vec<Vec<u32>> {
    v.iter()
        .map(|l| l.iter().map(|x| x.to_bits()).collect())
        .collect()
}

fn snapshot(m: &mut BandMerge) -> Vec<Vec<Vec<u32>>> {
    let t = m.totals_mut();
    vec![
        bits(t.num),
        bits(t.usum),
        bits(t.den),
        bits(t.zmax),
        bits(t.zsum),
        bits(t.lsum),
        bits(t.esum),
        bits(t.lo),
        bits(t.hi),
    ]
}

#[test]
#[ignore = "needs a Vulkan GPU with f64"]
fn the_gpu_fold_is_bit_identical_to_the_cpu_fold() {
    for (w, h, bands, frames) in [(193usize, 131usize, 5usize, 5usize), (640, 427, 7, 6)] {
        let cfg = MergeConfig {
            bands,
            ..Default::default()
        };
        let sizes = level_sizes(w, h, cfg.bands);
        let mut rng = Rng(0x9E37_79B9_7F4A_7C15 ^ w as u64);
        let data: Vec<Vec<Vec<f32>>> = (0..2 * frames).map(|f| frame(w, h, f, &mut rng)).collect();
        let beta: Vec<f32> = vec![0.41, 0.093, 0.021, 0.006];

        let mut cpu = BandMerge::new(w, h, 4, cfg);
        let mut gpu_merge = BandMerge::new(w, h, 4, cfg);
        let mut gpu = GpuFold::new(&gpu_merge).expect("GPU fold");
        let mut fws = FrameWorkspace::new(&sizes, 4);
        for chunk in 0..2 {
            if chunk > 0 {
                cpu.reset_for_reuse();
                gpu_merge.reset_for_reuse();
            }
            for planes in &data[chunk * frames..(chunk + 1) * frames] {
                let luma: Vec<f32> = planes[1]
                    .iter()
                    .zip(&planes[2])
                    .map(|(a, b)| 0.5 * (a + b))
                    .collect();
                let var: Vec<f32> = luma.iter().map(|l| 0.3 * l.max(0.0) + 7.0).collect();
                let refs: Vec<&[f32]> = planes.iter().map(Vec::as_slice).collect();
                fws.next_frame();
                cpu.add_frame_with_gain(&refs, &luma, &var, Some(&beta), &mut fws);
                gpu.add_frame(&mut gpu_merge, &refs, &var, Some(&beta));
            }
            gpu.finish_chunk(&mut gpu_merge);
            assert_eq!(cpu.frames(), gpu_merge.frames());
            let (a, b) = (snapshot(&mut cpu), snapshot(&mut gpu_merge));
            let names = [
                "num", "usum", "den", "zmax", "zsum", "lsum", "esum", "lo", "hi",
            ];
            for ((x, y), name) in a.iter().zip(&b).zip(names) {
                for (k, (lx, ly)) in x.iter().zip(y).enumerate() {
                    let diff = lx.iter().zip(ly).filter(|(p, q)| p != q).count();
                    assert_eq!(
                        diff,
                        0,
                        "{w}x{h} chunk {chunk}: {name}[{k}] differs at {diff} of {}",
                        lx.len()
                    );
                }
            }
            let mut ws = Workspace::new(&sizes);
            let (oa, ob) = (cpu.finish(&mut ws), gpu_merge.finish(&mut ws));
            assert_eq!(
                bits(&oa),
                bits(&ob),
                "{w}x{h} chunk {chunk}: collapsed output differs"
            );
        }
    }
}
