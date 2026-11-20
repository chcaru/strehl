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

/// `planes` integer-valued planes, as `(u16 - black).max(0)` gives: a scene
/// whose sharp region moves with `f`, plus noise, clipped at zero like real data.
fn frame_of(planes: usize, w: usize, h: usize, f: usize, rng: &mut Rng) -> Vec<Vec<f32>> {
    // The left third is flat ground: weights there sit at the exp(-80) clamp,
    // so the soft-power numerator is subnormal -- the case a flushing device
    // gets wrong.
    (0..planes)
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

fn frame(w: usize, h: usize, f: usize, rng: &mut Rng) -> Vec<Vec<f32>> {
    frame_of(4, w, h, f, rng)
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

/// Three chunks absorbed on the host straight from the device
/// (`absorb_chunk`), counted by a merge whose totals were released, against
/// the CPU's chunk-by-chunk `absorb`: every total, the frame count and the
/// collapsed output identical.
#[test]
#[ignore = "needs a Vulkan GPU with f64"]
fn absorbing_device_chunks_is_the_cpu_absorb() {
    let (w, h, frames) = (640usize, 427usize, 4usize);
    let cfg = MergeConfig {
        bands: 7,
        ..Default::default()
    };
    let sizes = level_sizes(w, h, cfg.bands);
    let mut rng = Rng(0x0DDB_1A5E_5BAD_5EED);
    let data: Vec<Vec<Vec<f32>>> = (0..3 * frames).map(|f| frame(w, h, f, &mut rng)).collect();
    let beta: Vec<f32> = vec![0.41, 0.093, 0.021, 0.006];

    let mut chunk = BandMerge::new(w, h, 4, cfg);
    let mut fws = FrameWorkspace::new(&sizes, 4);
    let mut cpu: Option<BandMerge> = None;
    let mut counter = BandMerge::new(w, h, 4, cfg);
    let mut gpu = GpuFold::new(&counter).expect("GPU fold");
    counter.release_external_totals();
    let mut device: Option<BandMerge> = None;
    for c in 0..3 {
        if c > 0 {
            chunk.reset_for_reuse();
            counter.reset_for_reuse();
        }
        for planes in &data[c * frames..(c + 1) * frames] {
            let luma: Vec<f32> = planes[1]
                .iter()
                .zip(&planes[2])
                .map(|(a, b)| 0.5 * (a + b))
                .collect();
            let var: Vec<f32> = luma.iter().map(|l| 0.3 * l.max(0.0) + 7.0).collect();
            let refs: Vec<&[f32]> = planes.iter().map(Vec::as_slice).collect();
            fws.next_frame();
            chunk.add_frame_with_gain(&refs, &luma, &var, Some(&beta), &mut fws);
            gpu.add_frame(&mut counter, &refs, &var, Some(&beta));
        }
        match cpu.as_mut() {
            None => cpu = Some(chunk.clone()),
            Some(total) => total.absorb(&chunk),
        }
        match device.as_mut() {
            None => {
                let mut total = BandMerge::new(w, h, 4, cfg);
                gpu.finish_chunk(&mut total);
                total.absorb_external_remainder(&counter, &gpu.null_levels(), true);
                device = Some(total);
            }
            Some(total) => {
                gpu.absorb_chunk(total);
                total.absorb_external_remainder(&counter, &gpu.null_levels(), false);
            }
        }
    }
    let (mut cpu, mut device) = (cpu.unwrap(), device.unwrap());
    assert_eq!(cpu.frames(), device.frames());
    let names = [
        "num", "usum", "den", "zmax", "zsum", "lsum", "esum", "lo", "hi",
    ];
    for ((x, y), name) in snapshot(&mut cpu)
        .iter()
        .zip(&snapshot(&mut device))
        .zip(names)
    {
        assert!(x == y, "{name} differs after absorbing three chunks");
    }
    let mut ws = Workspace::new(&sizes);
    assert_eq!(
        bits(&cpu.finish(&mut ws)),
        bits(&device.finish(&mut ws)),
        "collapsed output differs"
    );
}

const NAMES: [&str; 9] = [
    "num", "usum", "den", "zmax", "zsum", "lsum", "esum", "lo", "hi",
];

fn assert_same(a: &mut BandMerge, b: &mut BandMerge, what: &str) {
    assert_eq!(a.frames(), b.frames(), "{what}: frame counts");
    for ((x, y), name) in snapshot(a).iter().zip(&snapshot(b)).zip(NAMES) {
        for (k, (lx, ly)) in x.iter().zip(y).enumerate() {
            let diff = lx.iter().zip(ly).filter(|(p, q)| p != q).count();
            assert_eq!(
                diff,
                0,
                "{what}: {name}[{k}] differs at {diff} of {}",
                lx.len()
            );
        }
    }
}

/// Colour carry folds twelve planes: `accum` then runs three dispatches per
/// level, the first adding the shared weight to `den`. Every total and the
/// collapsed planes must equal the CPU's.
#[test]
#[ignore = "needs a Vulkan GPU with f64"]
fn twelve_planes_fold_bit_identically() {
    twelve_planes(None);
    // About half the totals per bank: both of `fold.wgsl`'s accumulator
    // bindings in use, as at 61 MP.
    twelve_planes(Some(2_500_000));
}

fn twelve_planes(bank_limit: Option<u64>) {
    let (w, h, frames, planes) = (321usize, 214usize, 5usize, 12usize);
    let cfg = MergeConfig {
        bands: 6,
        ..Default::default()
    };
    let sizes = level_sizes(w, h, cfg.bands);
    let mut rng = Rng(0x5EED_0012_F00D_CAFE);
    let beta: Vec<f32> = vec![0.41, 0.093, 0.021, 0.006];
    let mut cpu = BandMerge::new(w, h, planes, cfg);
    let mut gpu_merge = BandMerge::new(w, h, planes, cfg);
    let mut gpu = match bank_limit {
        None => GpuFold::new(&gpu_merge),
        Some(n) => GpuFold::with_bank_limit(&gpu_merge, n),
    }
    .expect("GPU fold");
    assert_eq!(
        gpu.accumulator_bank_count(),
        1 + usize::from(bank_limit.is_some())
    );
    let mut fws = FrameWorkspace::new(&sizes, planes);
    for f in 0..frames {
        let data = frame_of(planes, w, h, f, &mut rng);
        let luma: Vec<f32> = data[1]
            .iter()
            .zip(&data[2])
            .map(|(a, b)| 0.5 * (a + b))
            .collect();
        let var: Vec<f32> = luma.iter().map(|l| 0.3 * l.max(0.0) + 7.0).collect();
        let refs: Vec<&[f32]> = data.iter().map(Vec::as_slice).collect();
        fws.next_frame();
        cpu.add_frame_with_gain(&refs, &luma, &var, Some(&beta), &mut fws);
        gpu.add_frame(&mut gpu_merge, &refs, &var, Some(&beta));
    }
    gpu.finish_chunk(&mut gpu_merge);
    assert_same(&mut cpu, &mut gpu_merge, "twelve planes");
    let mut ws = Workspace::new(&sizes);
    assert_eq!(
        bits(&cpu.finish(&mut ws)),
        bits(&gpu_merge.finish(&mut ws)),
        "collapsed output differs"
    );
}

/// Two half-stacks (`STREHL_OPTICAL_RESTORE`): frames alternate between two
/// device accumulators, counted by two merges whose totals were released,
/// against two CPU merges folding the same frames. Each half, read back
/// after both were folded, equals its CPU merge; then a second chunk on the
/// same accumulators (lazily reset) does too.
#[test]
#[ignore = "needs a Vulkan GPU with f64"]
fn two_accumulators_fold_two_half_stacks() {
    let (w, h, frames, planes) = (257usize, 190usize, 7usize, 12usize);
    let cfg = MergeConfig {
        bands: 6,
        ..Default::default()
    };
    let sizes = level_sizes(w, h, cfg.bands);
    let mut rng = Rng(0x0BAD_C0DE_1234_5678);
    let beta: Vec<f32> = vec![0.41, 0.093, 0.021, 0.006];
    let mut cpu = [
        BandMerge::new(w, h, planes, cfg),
        BandMerge::new(w, h, planes, cfg),
    ];
    let mut counter = [
        BandMerge::new(w, h, planes, cfg),
        BandMerge::new(w, h, planes, cfg),
    ];
    let mut gpu = GpuFold::with_bank_limit(&counter[0], 2_000_000).expect("GPU fold");
    gpu.add_second_accumulator().expect("second accumulator");
    assert_eq!(gpu.accumulator_bank_count(), 2);
    assert_eq!(gpu.accumulators(), 2);
    for c in &mut counter {
        c.release_external_totals();
    }
    let mut fws = FrameWorkspace::new(&sizes, planes);
    for chunk in 0..2 {
        if chunk > 0 {
            for m in cpu.iter_mut().chain(counter.iter_mut()) {
                m.reset_for_reuse();
            }
        }
        for f in 0..frames {
            let data = frame_of(planes, w, h, 10 * chunk + f, &mut rng);
            let luma: Vec<f32> = data[1]
                .iter()
                .zip(&data[2])
                .map(|(a, b)| 0.5 * (a + b))
                .collect();
            let var: Vec<f32> = luma.iter().map(|l| 0.3 * l.max(0.0) + 7.0).collect();
            let refs: Vec<&[f32]> = data.iter().map(Vec::as_slice).collect();
            let half = f % 2;
            fws.next_frame();
            cpu[half].add_frame_with_gain(&refs, &luma, &var, Some(&beta), &mut fws);
            gpu.select_accumulator(half);
            gpu.add_frame(&mut counter[half], &refs, &var, Some(&beta));
        }
        for half in 0..2 {
            let mut total = BandMerge::new(w, h, planes, cfg);
            gpu.select_accumulator(half);
            gpu.finish_chunk(&mut total);
            total.absorb_external_remainder(&counter[half], &gpu.null_levels(), true);
            assert_same(
                &mut cpu[half],
                &mut total,
                &format!("chunk {chunk} half {half}"),
            );
            let mut ws = Workspace::new(&sizes);
            assert_eq!(
                bits(&cpu[half].clone().finish(&mut ws)),
                bits(&total.finish(&mut ws)),
                "chunk {chunk} half {half}: collapsed output differs"
            );
        }
    }
}

/// Round-3 plan R2: the finish on the device. Two half-stacks folded on the
/// device and read back only partly (`finish_chunk_partial` into
/// `new_device_finish` merges) finish on the device (`finish_planes`) to the
/// CPU merges' `finish_with_report` planes, bit for bit, with the same
/// ensemble report and averaged fractions; then the halves absorbed on the
/// device (`absorb_second_accumulator`) and on the host
/// (`absorb_device_finish`) finish to the CPU's `absorb` then `finish`, and
/// the green view's totals equal the CPU's.
#[test]
#[ignore = "needs a Vulkan GPU with f64"]
fn the_device_finish_is_finish_with_report() {
    let (w, h, frames, planes) = (257usize, 190usize, 7usize, 12usize);
    let cfg = MergeConfig {
        bands: 6,
        ..Default::default()
    };
    let sizes = level_sizes(w, h, cfg.bands);
    let mut rng = Rng(0x5EED_F1A1_2026_1119);
    let beta: Vec<f32> = vec![0.41, 0.093, 0.021, 0.006];
    let mut cpu = [
        BandMerge::new(w, h, planes, cfg),
        BandMerge::new(w, h, planes, cfg),
    ];
    let mut counter = [
        BandMerge::new(w, h, planes, cfg),
        BandMerge::new(w, h, planes, cfg),
    ];
    let mut gpu = GpuFold::with_bank_limit(&counter[0], 2_000_000).expect("GPU fold");
    gpu.add_second_accumulator().expect("second accumulator");
    for c in &mut counter {
        c.release_external_totals();
    }
    let mut fws = FrameWorkspace::new(&sizes, planes);
    for f in 0..frames {
        let data = frame_of(planes, w, h, f, &mut rng);
        let luma: Vec<f32> = data[1]
            .iter()
            .zip(&data[2])
            .map(|(a, b)| 0.5 * (a + b))
            .collect();
        let var: Vec<f32> = luma.iter().map(|l| 0.3 * l.max(0.0) + 7.0).collect();
        let refs: Vec<&[f32]> = data.iter().map(Vec::as_slice).collect();
        let half = f % 2;
        fws.next_frame();
        cpu[half].add_frame_with_gain(&refs, &luma, &var, Some(&beta), &mut fws);
        gpu.select_accumulator(half);
        gpu.add_frame(&mut counter[half], &refs, &var, Some(&beta));
    }
    let mut partial: Vec<BandMerge> = Vec::new();
    let mut ws = Workspace::new(&sizes);
    for half in 0..2 {
        let mut m = BandMerge::new_device_finish(w, h, planes, cfg, true);
        gpu.select_accumulator(half);
        gpu.finish_chunk_partial(&mut m);
        m.absorb_external_remainder(&counter[half], &gpu.null_levels(), true);
        let plan = m.finish_plan();
        let device = gpu.finish_planes(&plan).expect("device finish");
        let (host, report) = cpu[half].clone().finish_with_report(&mut ws);
        assert_eq!(
            bits(&host),
            bits(&device),
            "half {half}: finished planes differ"
        );
        assert_eq!(report, plan.report, "half {half}: ensemble report differs");
        assert_eq!(
            cpu[half].averaged_fraction(),
            m.averaged_fraction(),
            "half {half}: averaged fraction differs"
        );
        partial.push(m);
    }
    let odd = partial.pop().expect("odd half");
    let mut even = partial.pop().expect("even half");
    gpu.absorb_second_accumulator().expect("device absorb");
    even.absorb_device_finish(&odd);
    let [mut a, b] = cpu;
    a.absorb(&b);
    let plan = even.finish_plan();
    let device = gpu
        .finish_planes(&plan)
        .expect("device finish of the whole");
    let (host, report) = a.clone().finish_with_report(&mut ws);
    assert_eq!(
        bits(&host),
        bits(&device),
        "absorbed: finished planes differ"
    );
    assert_eq!(report, plan.report, "absorbed: ensemble report differs");
    assert_eq!(a.averaged_fraction(), even.averaged_fraction());
    assert_eq!(a.frames(), even.frames());
}
