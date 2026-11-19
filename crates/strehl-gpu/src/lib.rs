//! Bit-exact GPU execution of strehl's default pyramid fold.
//!
//! [`GpuFold`] performs [`BandMerge::add_frame_with_gain`]'s work for the
//! default configuration on a Vulkan device and keeps the merge's accumulators
//! resident in device memory for a whole canonical chunk. At the chunk's end
//! [`GpuFold::finish_chunk`] writes them into the CPU `BandMerge`, which then
//! absorbs, thresholds and collapses exactly as before. Nothing about chunking,
//! reduction order or the writer changes.
//!
//! # Exactness
//!
//! Every kernel in `fold.wgsl` evaluates its CPU counterpart's expressions
//! operand for operand. The SPIR-V is decorated `NoContraction` throughout
//! ([`strict`]), f32 division runs through f64, and `ln`/`exp` are
//! [`strehl_core::portable_math`] with their constants passed as data. On the
//! RTX 5090 these primitives were measured bit-identical to the CPU
//! (`experiments/native-gpu-gather/src/arith-probe.rs`); the fold itself is
//! tested against the CPU fold bit for bit (`tests/fold.rs`). A different
//! device or driver must pass the same tests before it is trusted.
//!
//! Subnormal f32 values may be flushed on the device. The fold's values are
//! DN-scale band coefficients and energies, so this is not expected to occur;
//! the end-to-end pixel comparison is the check.

use rayon::prelude::*;
use strehl_core::portable_math::{
    COS_SERIES, EXP_SERIES, LN_SERIES, LN_UNIFORM_FLOOR, LN64_SERIES, PIO2_HI, PIO2_LO, SIN_SERIES,
};
use strehl_core::pyramid::{BandMerge, BaseBand, Combine, FoldCombine, LevelScalars, LevelSize};
use wgpu::util::DeviceExt;

mod context;
mod convolve;
mod selftest;
pub mod strict;
pub use context::set_pipeline_cache_dir;
pub use convolve::convolve;
pub use selftest::self_test;

const SHADER: &str = include_str!("fold.wgsl");
const WG: u32 = 256;

#[repr(C)]
#[derive(Clone, Copy, Default, bytemuck::Pod, bytemuck::Zeroable)]
struct Params {
    a: [u32; 4],
    b: [u32; 4],
    c: [u32; 4],
    d: [u32; 4],
    e: [u32; 4],
    f: [f32; 4],
    g: [f32; 4],
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum Kernel {
    Fill,
    Luma,
    Hull,
    ReduceH,
    ReduceV,
    ExpandH,
    ExpandSubV,
    SmoothH,
    SmoothV,
    Level,
    Accum,
    Mhc,
    Gather,
    Extract,
    Variance,
    Sum64,
    Sum64Finish,
    Demean,
    Noise,
    RowSq,
    RowSqFinish,
    Pack,
    NullAccum,
    ScreenCensus,
    Assemble,
    DgBlurH,
    DgBlurV,
    DgEnergy,
}

impl Kernel {
    fn index(self) -> usize {
        self as usize
    }
}

/// Offsets, in f32 elements, of every region in the two arenas.
struct Layout {
    /// The ln/exp screens' tables (`weight_screen_tables`), at offset 0,
    /// where `fold.wgsl` reads them (`TAB_LN`, `TAB_EXP`).
    tables: u32,
    sizes: Vec<LevelSize>,
    planes: usize,
    plane_lv: Vec<Vec<u32>>,
    var_lv: Vec<u32>,
    luma_lv: Vec<u32>,
    scratch: u32,
    sq: u32,
    weight: u32,
    ev_a: u32,
    ev_b: u32,
    coarse: u32,
    /// Three full-resolution channel planes (`2gw x 2gh` each), when the
    /// device prepares frames: an offset into their own buffer (`rgbw`).
    rgb: u32,
    rgb_len: u64,
    /// A copy of level 0's luma before the fold decomposes it in place, read
    /// back for the depth measurement taken during the fold.
    luma_keep: u32,
    /// The gate-floor probe's luma pyramid, when the device prepares frames.
    probe_lv: Vec<u32>,
    work_len: u64,
    num: Vec<u32>,
    usum: Vec<u32>,
    den: Vec<u32>,
    zmax: Vec<u32>,
    zsum: Vec<u32>,
    lsum: Vec<u32>,
    esum: Vec<u32>,
    lo: Vec<u32>,
    hi: Vec<u32>,
    /// The ensemble null's windows, per level, when the device prepares
    /// frames and the merge has them.
    null: Vec<Option<NullRegion>>,
    /// Elements per accumulator bank (one storage binding each).
    acc_len: Vec<u64>,
}

/// One level's ensemble-null window on the device: its rectangle within the
/// level, the probe's coefficients and energies packed per frame slot (work),
/// and the window's accumulators (acc).
#[derive(Clone, Copy)]
struct NullRegion {
    rect: [usize; 4],
    lv: [u32; 2],
    energy: [u32; 2],
    /// zmax, zsum, lsum, esum.
    acc: [u32; 4],
}

impl Layout {
    fn new(
        sizes: &[LevelSize],
        planes: usize,
        ensemble: bool,
        hull: bool,
        full: Option<(usize, usize)>,
        null_rects: &[Option<[usize; 4]>],
        bank_elems: u64,
    ) -> Self {
        let nl = sizes.len();
        let n0 = sizes[0].pixels() as u64;
        let mut work = 0u64;
        let mut take = |n: usize| {
            let at = work as u32;
            work += n as u64;
            at
        };
        let pyramid = |take: &mut dyn FnMut(usize) -> u32| -> Vec<u32> {
            sizes.iter().map(|s| take(s.pixels())).collect()
        };
        let tables = take(SCREEN_TABLES_LEN);
        let plane_lv = (0..planes).map(|_| pyramid(&mut take)).collect();
        let var_lv = pyramid(&mut take);
        let luma_lv = pyramid(&mut take);
        let scratch = take(sizes[0].pixels() + sizes[0].width + sizes[0].height + 16);
        let sq = take(sizes[0].pixels());
        let weight = take(sizes[0].pixels());
        let ev_a = take(sizes[0].pixels());
        let ev_b = take(sizes[0].pixels());
        let coarse = take(sizes[nl - 1].pixels());
        let (rgb_len, probe_lv, luma_keep) = match full {
            Some((gw, gh)) => (
                (3 * 4 * gw * gh) as u64,
                pyramid(&mut take),
                take(sizes[0].pixels()),
            ),
            None => (0, Vec::new(), 0),
        };
        let null_rects: Vec<Option<[usize; 4]>> = if full.is_some() {
            null_rects.to_vec()
        } else {
            Vec::new()
        };
        let null_work: Vec<Option<([u32; 2], [u32; 2])>> = null_rects
            .iter()
            .map(|r| {
                r.map(|[_, _, w, h]| {
                    let lv = [take(w * h), take(w * h)];
                    let energy = [take(w * h), take(w * h)];
                    (lv, energy)
                })
            })
            .collect();
        let work_len = work;
        // Accumulator regions fill bank 0, then bank 1 (`ACC_BANK` set in the
        // offset); a region never straddles two.
        let mut acc_len = vec![0u64];
        let mut put = |n: usize| {
            let bank = acc_len.len() - 1;
            if acc_len[bank] + n as u64 > bank_elems {
                acc_len.push(0);
            }
            let bank = acc_len.len() - 1;
            let at = acc_len[bank] as u32 | if bank > 0 { ACC_BANK } else { 0 };
            acc_len[bank] += n as u64;
            at
        };
        let num = (0..nl * planes)
            .map(|i| put(sizes[i / planes].pixels()))
            .collect();
        let usum = (0..nl * planes)
            .map(|i| put(sizes[i / planes].pixels()))
            .collect();
        let den = (0..nl).map(|k| put(sizes[k].pixels())).collect();
        let mut per_level = |on: bool| -> Vec<u32> {
            if on {
                (0..nl).map(|k| put(sizes[k].pixels())).collect()
            } else {
                Vec::new()
            }
        };
        let zmax = per_level(ensemble);
        let zsum = per_level(ensemble);
        let lsum = per_level(ensemble);
        let esum = per_level(ensemble);
        let (lo, hi) = if hull {
            (
                (0..planes).map(|_| put(n0 as usize)).collect(),
                (0..planes).map(|_| put(n0 as usize)).collect(),
            )
        } else {
            (Vec::new(), Vec::new())
        };
        let null = null_rects
            .iter()
            .zip(null_work)
            .map(|(r, w)| {
                let (rect, (lv, energy)) = (r.as_ref()?, w?);
                let n = rect[2] * rect[3];
                Some(NullRegion {
                    rect: *rect,
                    lv,
                    energy,
                    acc: [put(n), put(n), put(n), put(n)],
                })
            })
            .collect();
        Self {
            tables,
            sizes: sizes.to_vec(),
            planes,
            plane_lv,
            var_lv,
            luma_lv,
            scratch,
            sq,
            weight,
            ev_a,
            ev_b,
            coarse,
            rgb: 0,
            rgb_len,
            luma_keep,
            probe_lv,
            work_len,
            num,
            usum,
            den,
            zmax,
            zsum,
            lsum,
            esum,
            lo,
            hi,
            null,
            acc_len,
        }
    }
}

/// Offset flag of an accumulator region in the second bank (`acc_hi` in
/// `fold.wgsl`). Bank offsets stay below 2^29 elements, so adding an index
/// within a region never reaches the flag.
const ACC_BANK: u32 = 0x4000_0000;

/// A bank's index and the element offset within it.
fn acc_bank(offset: u32) -> (usize, usize) {
    if offset >= ACC_BANK {
        (1, (offset - ACC_BANK) as usize)
    } else {
        (0, offset as usize)
    }
}

/// One frame's dispatches, recorded then encoded in order.
struct Recorder {
    calls: Vec<(Kernel, Params, u32)>,
}

impl Recorder {
    fn push(&mut self, k: Kernel, p: Params, n: usize) {
        self.calls.push((k, p, n as u32));
    }

    fn fill(&mut self, at: u32, n: usize, value: f32, acc: bool) {
        let p = Params {
            a: [at, n as u32, value.to_bits(), acc as u32],
            ..Default::default()
        };
        self.push(Kernel::Fill, p, n);
    }

    /// `reduce` from `src` (size `s`) into `dst` (size `s.reduced()`).
    fn reduce(&mut self, scratch: u32, src: u32, s: LevelSize, dst: u32) {
        let d = s.reduced();
        self.push(
            Kernel::ReduceH,
            Params {
                a: [src, s.width as u32, s.height as u32, scratch],
                b: [d.width as u32, 0, 0, 0],
                ..Default::default()
            },
            d.width * s.height,
        );
        self.push(
            Kernel::ReduceV,
            Params {
                a: [scratch, d.width as u32, s.height as u32, dst],
                b: [d.height as u32, 0, 0, 0],
                ..Default::default()
            },
            d.pixels(),
        );
    }

    /// `dst -= expand(src)`, `src` of size `s`, `dst` of size `d`.
    fn expand_sub(&mut self, scratch: u32, src: u32, s: LevelSize, dst: u32, d: LevelSize) {
        self.push(
            Kernel::ExpandH,
            Params {
                a: [src, s.width as u32, s.height as u32, scratch],
                b: [d.width as u32, 0, 0, 0],
                ..Default::default()
            },
            d.width * s.height,
        );
        self.push(
            Kernel::ExpandSubV,
            Params {
                a: [scratch, d.width as u32, s.height as u32, dst],
                b: [d.height as u32, 0, 0, 0],
                ..Default::default()
            },
            d.pixels(),
        );
    }

    /// The f64 sum of the `n` values at `src` into `red[0]`, through partials
    /// at `red[1..]`; returns the first `red` index after them. The values
    /// must make every partial sum exact (the probe luma: half-integers, far
    /// below 2^52 in total), because the order of addition is free here.
    fn exact_sum(&mut self, src: u32, n: usize) -> u32 {
        let parts = n.div_ceil(SUM_CHUNK);
        self.push(
            Kernel::Sum64,
            Params {
                a: [src, n as u32, 1, SUM_CHUNK as u32],
                ..Default::default()
            },
            // One workgroup per chunk.
            parts * WG as usize,
        );
        // The partials are exact, so one workgroup sums them as a tree.
        self.push(
            Kernel::Sum64Finish,
            Params {
                a: [1, parts as u32, 0, 1],
                ..Default::default()
            },
            WG as usize,
        );
        (parts + 2) as u32
    }

    /// Each `(level, level width, [x, y, w, h])` window's
    /// `gatefloor::square_sum` (each row summed in column order, then the row
    /// sums in row order) into `red[total + i]`, row sums from `red[row]`;
    /// returns `total`. Up to four windows share a dispatch, so their ordered
    /// chains run side by side. Coordinates must be below 2^16
    /// ([`SQ_WINDOW_MAX`]).
    fn square_sums(&mut self, windows: &[(u32, u32, [usize; 4])], mut row: u32) -> u32 {
        let total = row + windows.iter().map(|w| w.2[3] as u32).sum::<u32>();
        for (g, group) in windows.chunks(4).enumerate() {
            let mut packed = [[0u32; 4]; 4];
            for (slot, &(level, width, [x, y, w, h])) in packed.iter_mut().zip(group) {
                assert!(
                    [x, y, w, h].iter().all(|&v| v <= SQ_WINDOW_MAX),
                    "square-sum window beyond 16 bits"
                );
                *slot = [
                    level,
                    width,
                    x as u32 | (y as u32) << 16,
                    w as u32 | (h as u32) << 16,
                ];
            }
            let rows: usize = group.iter().map(|w| w.2[3]).sum();
            let [a, b, c, d] = packed;
            let e = [row, group.len() as u32, total + 4 * g as u32, 0];
            self.push(
                Kernel::RowSq,
                Params {
                    a,
                    b,
                    c,
                    d,
                    e,
                    ..Default::default()
                },
                rows,
            );
            self.push(
                Kernel::RowSqFinish,
                Params {
                    a,
                    b,
                    c,
                    d,
                    e,
                    ..Default::default()
                },
                group.len(),
            );
            row += rows as u32;
        }
        total
    }
    /// `Pyramid::build` (Laplacian) in place over `lv`, whose level 0 holds
    /// the source.
    fn laplacian(&mut self, scratch: u32, sizes: &[LevelSize], lv: &[u32]) {
        for k in 1..sizes.len() {
            self.reduce(scratch, lv[k - 1], sizes[k - 1], lv[k]);
        }
        for k in 0..sizes.len() - 1 {
            self.expand_sub(scratch, lv[k + 1], sizes[k + 1], lv[k], sizes[k]);
        }
    }

    /// `Pyramid::build_gaussian` over `lv`, whose level 0 holds the source.
    fn gaussian(&mut self, scratch: u32, sizes: &[LevelSize], lv: &[u32]) {
        for k in 1..sizes.len() {
            self.reduce(scratch, lv[k - 1], sizes[k - 1], lv[k]);
        }
    }

    /// `accumulate_level` for level `k`: one dispatch per four planes, the
    /// first also adding the weight to `den` (flag `0x100`). Every
    /// accumulator element receives exactly one addition per frame.
    fn accum(&mut self, l: &Layout, weight: u32, k: usize) {
        for first in (0..l.planes).step_by(4) {
            let group = (l.planes - first).min(4);
            let mut b = [0u32; 4];
            let mut c = [0u32; 4];
            let mut d = [0u32; 4];
            for (j, p) in (first..first + group).enumerate() {
                b[j] = l.plane_lv[p][k];
                c[j] = l.num[k * l.planes + p];
                d[j] = l.usum[k * l.planes + p];
            }
            let den = if first == 0 { 0x100 } else { 0 };
            self.push(
                Kernel::Accum,
                Params {
                    a: [
                        weight,
                        l.den[k],
                        l.sizes[k].pixels() as u32,
                        group as u32 | den,
                    ],
                    b,
                    c,
                    d,
                    ..Default::default()
                },
                l.sizes[k].pixels(),
            );
        }
    }
}

/// The device, its pipelines, and one stack geometry's buffers.
pub struct GpuFold {
    /// Per-dispatch timing (`STREHL_GPU_PROFILE`), diagnostic only.
    profile: Option<Profile>,
    device: wgpu::Device,
    queue: wgpu::Queue,
    pipelines: Vec<wgpu::ComputePipeline>,
    /// Bind groups per accumulator, then per parameter slot.
    bind: Vec<Vec<wgpu::BindGroup>>,
    params: Vec<wgpu::Buffer>,
    param_stride: u64,
    work: wgpu::Buffer,
    /// The accumulator arenas: one, or two when the caller folds two
    /// half-stacks ([GpuFold::add_second_accumulator]).
    acc: Vec<[wgpu::Buffer; 2]>,
    /// The accumulator the next fold, reset and read-back address.
    target: usize,
    bgl: wgpu::BindGroupLayout,
    consts: wgpu::Buffer,
    /// Raw u16 frames, main then probe, two samples per word.
    raw: wgpu::Buffer,
    /// Samples per frame in `raw` (even), and frames per frame slot.
    raw_samples: u64,
    raw_members: usize,
    /// At least this many frames per slot ([`GpuFold::reserve_members`]).
    min_members: usize,
    /// The full-resolution channel planes (`fold.wgsl`'s `rgbw`).
    rgbw: wgpu::Buffer,
    /// Mapped read-back buffers for level 0's luma, reused.
    luma_pool: std::sync::Arc<std::sync::Mutex<Vec<wgpu::Buffer>>>,
    /// The frame slot the next [`GpuFold::stage`] fills (0 or 1).
    next_slot: usize,
    /// One persistently mapped upload buffer per frame slot.
    upload: Vec<UploadSlot>,
    /// Bumped whenever the raw buffer is reallocated, evicting staged frames.
    raw_generation: u64,
    xf: wgpu::Buffer,
    red: wgpu::Buffer,
    /// Full quad geometry `(gw, gh)` and the analysis rectangle, when the
    /// device prepares frames.
    full: Option<(usize, usize)>,
    rect: [usize; 4],
    layout: Layout,
    base_weighted: bool,
    ensemble: bool,
    hull: bool,
    frame: usize,
    /// Per accumulator: reset before its next fold (lazy, so a finished
    /// chunk can be read before it is cleared).
    pending_reset: Vec<bool>,
    /// [`GpuFold::enable_depth`]: kept luma is read back as depth energies.
    depth: Option<DepthPlan>,
    pub adapter: String,
    pub decorated_results: usize,
}

/// Time every dispatch with GPU timestamps and keep per-kernel totals
/// ([`GpuFold::profile_report`]). Each dispatch then runs in its own pass and
/// every submit waits, so throughput drops: a diagnostic, never a default.
pub const PROFILE_ENV: &str = "STREHL_GPU_PROFILE";

struct Profile {
    set: wgpu::QuerySet,
    resolve: wgpu::Buffer,
    readback: wgpu::Buffer,
    period_ns: f64,
    /// Per kernel: dispatches and total nanoseconds.
    totals: Vec<(u64, f64)>,
    /// Each submission's first-begin to last-end nanoseconds, summed: the
    /// kernels plus the device's gaps between them.
    span_ns: f64,
    /// Per kernel: nanoseconds the device spent between the previous
    /// kernel's end and this one's start.
    gaps: Vec<f64>,
}

impl Profile {
    fn new(device: &wgpu::Device, queue: &wgpu::Queue) -> Self {
        let n = 2 * MAX_CALLS as u32;
        let bytes = u64::from(n) * 8;
        Self {
            set: device.create_query_set(&wgpu::QuerySetDescriptor {
                label: Some("fold-profile"),
                ty: wgpu::QueryType::Timestamp,
                count: n,
            }),
            resolve: device.create_buffer(&wgpu::BufferDescriptor {
                label: Some("fold-profile-resolve"),
                size: bytes,
                usage: wgpu::BufferUsages::QUERY_RESOLVE | wgpu::BufferUsages::COPY_SRC,
                mapped_at_creation: false,
            }),
            readback: device.create_buffer(&wgpu::BufferDescriptor {
                label: Some("fold-profile-readback"),
                size: bytes,
                usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
                mapped_at_creation: false,
            }),
            period_ns: f64::from(queue.get_timestamp_period()),
            totals: vec![(0, 0.0); strict::ENTRY_POINTS.len()],
            span_ns: 0.0,
            gaps: vec![0.0; strict::ENTRY_POINTS.len()],
        }
    }
}

/// f32s of the ln/exp screens' tables at the start of `work`.
const SCREEN_TABLES_LEN: usize = 3 * 128 + 2 * 64;

/// `ln(x)` for `x` in `[0.5, 2]` from the `atanh` series in f64, the same
/// operations in the same order on every IEEE platform (a table constant must
/// not depend on a C runtime's `log`).
fn ln_series(x: f64) -> f64 {
    let s = (x - 1.0) / (x + 1.0);
    let s2 = s * s;
    let (mut term, mut sum) = (s, 0.0);
    for k in 0..40 {
        sum += term / f64::from(2 * k + 1);
        term *= s2;
    }
    2.0 * sum
}

/// `e^x` for `x` in `[0, 1)` from its Taylor series in f64.
fn exp_series(x: f64) -> f64 {
    let (mut term, mut sum) = (1.0, 1.0);
    for k in 1..30 {
        term *= x / f64::from(k);
        sum += term;
    }
    sum
}

/// The tables `fold.wgsl`'s ln and exp screens read. ln: for each of 128
/// mantissa intervals `j` (`m` in `[1 + j/128, 1 + (j+1)/128)`), an f32 `r`
/// near `1 / c_j` and `-ln r` as an f32 pair, less `ln 2` for `j >= 64`
/// (where the screen adds one to the exponent). `j = 0` and `j = 127` use
/// `c = 1` and `c = 2`, so a value near 1 reduces exactly and does not cancel.
/// exp: `2^(j/64)` as an f32 pair for `j` in `0..64`. Only their accuracy
/// matters to the screens; the census proves the result.
fn weight_screen_tables() -> Vec<f32> {
    let pair = |v: f64| {
        let hi = v as f32;
        [hi, (v - f64::from(hi)) as f32]
    };
    let mut t = Vec::with_capacity(SCREEN_TABLES_LEN);
    for j in 0..128u32 {
        let (r, l) = match j {
            0 => (1.0f32, [0.0, 0.0]),
            127 => (0.5, [0.0, 0.0]),
            _ => {
                let c = 1.0 + (f64::from(j) + 0.5) / 128.0;
                let r = (1.0 / c) as f32;
                let fold = if j >= 64 { std::f64::consts::LN_2 } else { 0.0 };
                (r, pair(-ln_series(f64::from(r)) - fold))
            }
        };
        t.extend_from_slice(&[r, l[0], l[1]]);
    }
    for j in 0..64u32 {
        t.extend_from_slice(&pair(exp_series(
            f64::from(j) * std::f64::consts::LN_2 / 64.0,
        )));
    }
    debug_assert_eq!(t.len(), SCREEN_TABLES_LEN);
    t
}

/// One range of [`GpuFold::screen_census`].
#[derive(Debug, Clone, Copy, Default)]
pub struct ScreenCensus {
    pub inputs: u64,
    /// Accepted screen values that differ from the f64 function's: must be 0.
    pub mismatches: u64,
    /// Inputs the screen left to the f64 function.
    pub fallbacks: u64,
    /// The smallest input (f32 bits) whose accepted value differed.
    pub first_mismatch: Option<u32>,
    /// The largest error of the screen's hi + lo against the f64 value before
    /// rounding, as a fraction of the bound the screen used: at most 0.5.
    pub worst_ratio: f32,
}

/// Maximum dispatches one frame records; sizes the parameter buffers.
const MAX_CALLS: usize = 1024;

/// Room for the depth energies' blur taps in `consts` (`fold.wgsl`'s
/// `C_TAPS`), both blurs together.
const DEPTH_TAPS_MAX: usize = 64;

/// The depth energies on the device ([`GpuFold::enable_depth`]): each blur's
/// radius, tap count and first tap in `consts`.
#[derive(Clone, Copy, Debug)]
struct DepthPlan {
    blurs: [(u32, u32, u32); 2],
    cells: (u32, u32),
    /// Also read the luma back, after the energies (for checking them).
    with_luma: bool,
}

/// Largest coordinate or extent of a square-sum window (packed in 16 bits).
const SQ_WINDOW_MAX: usize = 0xffff;

/// Values per partial sum in the probe's exact mean.
const SUM_CHUNK: usize = 4096;

/// f64s in `red`: the probe mean's partials and total, then one row sum per
/// interior row of every level (an upper bound) and the interiors' totals.
fn red_len(sizes: &[LevelSize]) -> u64 {
    let parts = sizes[0].pixels().div_ceil(SUM_CHUNK);
    let rows: usize = sizes.iter().map(|s| s.height).sum();
    (parts + 2 + rows + sizes.len() + 16) as u64
}

/// Raw buffer slots: two frame slots (each of `members` frames: a pixel-shift
/// group's four members, side by side), then the probe's (one frame).
const PROBE_SLOT: usize = 2;

/// Frames the raw buffer holds for members frames per frame slot: two
/// frame slots, then the probe's single frame.
fn raw_frames(members: usize) -> u64 {
    2 * members as u64 + 1
}

/// Site pulls per frame slot: the four CFA sites, then the eight carried
/// channels ([`CARRIED_SITES`]).
const PULLS: usize = 12;

/// `xf` index of the probe noise's level, sigma and f32-screen margin.
const XF_NOISE: u64 = 2 * 8 * PULLS as u64;

/// f64s in `xf`: two frame slots of twelve site pulls (8 each), then the
/// probe noise's level, sigma and f32-screen margin.
const XF_LEN: u64 = XF_NOISE + 3;

/// One accumulator arena's two banks (`fold.wgsl`'s `acc` and `acc_hi`): a
/// second bank only when the totals exceed one binding, else a stand-in of
/// one word that no offset reaches.
fn accumulator_banks(device: &wgpu::Device, lens: &[u64], label: &str) -> [wgpu::Buffer; 2] {
    std::array::from_fn(|bank| {
        device.create_buffer(&wgpu::BufferDescriptor {
            label: Some(label),
            size: lens.get(bank).map_or(16, |n| (n * 4).max(16)),
            usage: wgpu::BufferUsages::STORAGE
                | wgpu::BufferUsages::COPY_DST
                | wgpu::BufferUsages::COPY_SRC,
            mapped_at_creation: false,
        })
    })
}

fn make_binds(
    device: &wgpu::Device,
    bgl: &wgpu::BindGroupLayout,
    params: &[wgpu::Buffer],
    [work, acc, consts, raw, xf, red, acc_hi, rgb]: [&wgpu::Buffer; 8],
) -> Vec<wgpu::BindGroup> {
    params
        .iter()
        .map(|pb| {
            let storage = [work, acc, consts, raw, xf, red, acc_hi, rgb];
            let mut entries = vec![wgpu::BindGroupEntry {
                binding: 0,
                resource: wgpu::BindingResource::Buffer(wgpu::BufferBinding {
                    buffer: pb,
                    offset: 0,
                    size: wgpu::BufferSize::new(std::mem::size_of::<Params>() as u64),
                }),
            }];
            for (i, b) in storage.iter().enumerate() {
                entries.push(wgpu::BindGroupEntry {
                    binding: i as u32 + 1,
                    resource: b.as_entire_binding(),
                });
            }
            device.create_bind_group(&wgpu::BindGroupDescriptor {
                label: Some("fold-bind"),
                layout: bgl,
                entries: &entries,
            })
        })
        .collect()
}

/// One CFA site's pull, reference coordinates to source plane coordinates,
/// exactly as `OpticalProfile::compose` returns it.
#[derive(Clone, Copy, Debug)]
pub struct SitePull {
    pub a: [f64; 2],
    pub b: [f64; 2],
}

/// A decoded frame for device preparation.
pub struct RawFrame<'a> {
    /// The decoder's whole buffer, `stride` samples per row.
    pub data: &'a [u16],
    pub stride: usize,
    /// Active-area origin within `data`.
    pub active: [usize; 2],
    pub black: f32,
    /// `align_cmd::wb_gains`, R G B.
    pub gain: [f32; 3],
    /// Per CFA site in `(0,0) (1,0) (0,1) (1,1)` order; `None` extracts the
    /// frame unwarped.
    pub pulls: Option<[SitePull; 4]>,
    /// `STREHL_CARRY_RGB`: the carried channels' pulls in [`CARRIED_SITES`]
    /// order; the fold then gathers twelve planes (needs `pulls`).
    pub carried: Option<[SitePull; 8]>,
    /// A checked pixel-shift group whose member 1 is `data`: its channels are
    /// assembled from the members (`assemble`) instead of demosaiced.
    pub group: Option<RawGroup<'a>>,
}

/// A pixel-shift group's other members and measurements for [`RawFrame`]
/// (`align_cmd::MeasuredGroup`).
pub struct RawGroup<'a> {
    /// Members 2-4's buffers: the frame's stride, height and active area.
    pub members: [&'a [u16]; 3],
    /// Each member's integer offset (`strehl_core::pixel_shift`), member 1's
    /// `(0, 0)`; at most 7 photosites each way.
    pub offsets: [(isize, isize); 4],
    /// Each member's `(1 / exposure gain) as f32`.
    pub inv: [f32; 4],
    /// Each member's residual as `compensate_rows` applies it
    /// (`sign * r as f32`), or `None` to assemble at the integer offsets.
    pub residuals: Option<[[f32; 2]; 4]>,
}

/// The eight non-native `(dx, dy, channel)` samples of a quad that the carry
/// gathers, in the order of the fold's planes 4-11: `align_cmd::CARRIED_SITES`.
pub const CARRIED_SITES: [(usize, usize, usize); 8] = [
    (0, 0, 1),
    (0, 0, 2),
    (1, 0, 0),
    (1, 0, 2),
    (0, 1, 0),
    (0, 1, 2),
    (1, 1, 0),
    (1, 1, 1),
];

/// A staged group's `assemble` parameters.
#[derive(Clone, Copy, Debug)]
struct GroupParams {
    /// Member offsets, 8 bits each: `(ox + 8) | (oy + 8) << 4`.
    offsets: u32,
    /// `site_members` per parity class, 8 bits each.
    table: u32,
    inv: [f32; 4],
    residuals: Option<[[f32; 2]; 4]>,
}

/// The gate-floor probe's noise fill (`gatefloor::ProbeFill`): SplitMix64
/// from `seed`, `level + sigma * g` quantised to u16 over the frame's active
/// complete quads.
#[derive(Clone, Copy, Debug)]
pub struct ProbeNoise {
    pub seed: u64,
    pub level: f64,
    pub sigma: f64,
}

/// A host-visible upload buffer, mapped for writing whenever it is idle.
struct UploadSlot {
    buffer: wgpu::Buffer,
    /// The copy out of it last submitted, after which it is re-mapped.
    copy: Option<wgpu::SubmissionIndex>,
    mapped: std::sync::Arc<std::sync::atomic::AtomicBool>,
}

/// A frame uploaded by [`GpuFold::stage`]: where it lives and what the
/// device needs to prepare it. Valid until the second `stage` after it.
#[derive(Clone, Debug)]
pub struct Staged {
    slot: usize,
    generation: u64,
    len: usize,
    stride: usize,
    active: [usize; 2],
    black: f32,
    gain: [f32; 3],
    warped: bool,
    /// Twelve planes are gathered (four native, eight carried).
    carried: bool,
    group: Option<GroupParams>,
}

/// A probe submitted by [`GpuFold::probe_submit`], read by
/// [`GpuFold::probe_collect`].
pub struct PendingProbe {
    readback: wgpu::Buffer,
    index: wgpu::SubmissionIndex,
    sums: usize,
}

/// A frame's level-0 luma copied by [`GpuFold::add_staged_keeping_luma`],
/// read by [`GpuFold::luma_collect`].
pub struct PendingLuma {
    readback: wgpu::Buffer,
    index: wgpu::SubmissionIndex,
    n: usize,
}

/// A frame's kept luma handed off by [`GpuFold::luma_handoff`]: read on any
/// thread, while the fold goes on.
pub struct LumaReadback {
    device: wgpu::Device,
    pending: PendingLuma,
    pool: std::sync::Arc<std::sync::Mutex<Vec<wgpu::Buffer>>>,
}

impl LumaReadback {
    /// Wait for the copy (not for later work), read it, and return the
    /// read-back buffer to the fold's pool.
    pub fn read(self) -> Result<Vec<f32>, String> {
        let LumaReadback {
            device,
            pending,
            pool,
        } = self;
        device
            .poll(wgpu::PollType::Wait {
                submission_index: Some(pending.index),
                timeout: None,
            })
            .map_err(|e| format!("GPU luma wait: {e:?}"))?;
        let out = {
            let view = pending
                .readback
                .slice(..)
                .get_mapped_range()
                .map_err(|e| format!("mapped luma: {e:?}"))?;
            // Read-back memory is slow to read on one thread (MEASURED 36 ms
            // for these 60 MB on the RTX 5090, 1.7 GB/s); in parallel pieces,
            // as `read_chunk` reads the accumulators.
            let src = bytemuck::cast_slice::<u8, f32>(&view[..pending.n * 4]);
            let mut out = vec![0f32; pending.n];
            out.par_chunks_mut(1 << 18)
                .zip(src.par_chunks(1 << 18))
                .for_each(|(d, s)| d.copy_from_slice(s));
            out
        };
        pending.readback.unmap();
        pool.lock()
            .unwrap_or_else(|e| e.into_inner())
            .push(pending.readback);
        Ok(out)
    }
}

/// What [`GpuFold::probe`] reads back.
#[derive(Debug, Default)]
pub struct ProbeOutput {
    /// One f64 sum of squares per requested interior, in request order.
    pub sums: Vec<f64>,
}

/// The injected noise model's two green planes: gain (DN/e) and read floor
/// (`read_noise_e * gain`, as `PlaneNoise::variance` forms it).
#[derive(Clone, Copy, Debug)]
pub struct GreenNoise {
    pub gain: [f32; 2],
    pub read_dn: [f32; 2],
}

/// CFA site `(dx, dy)` of fold plane `c`: `BAND_PLANE_OFFSETS`.
const SITES: [(usize, usize); 4] = [(0, 0), (1, 0), (0, 1), (1, 1)];

/// `rggb_channel_index` for a site.
fn site_channel(dx: usize, dy: usize) -> usize {
    match (dx, dy) {
        (0, 0) => 0,
        (1, 1) => 2,
        _ => 1,
    }
}

impl GpuFold {
    /// A fold for `merge`'s geometry and configuration, or why there is none.
    pub fn new(merge: &BandMerge) -> Result<Self, String> {
        Self::build(merge, None, None)
    }

    /// [`Self::new`] with accumulator banks of at most `bank_elems` f32s, so
    /// a test can put small totals in both banks (`fold.wgsl`'s `acc_hi`).
    #[doc(hidden)]
    pub fn with_bank_limit(merge: &BandMerge, bank_elems: u64) -> Result<Self, String> {
        Self::build(merge, None, Some(bank_elems))
    }

    /// A fold that also prepares frames on the device: `full` is the frame's
    /// quad geometry `(gw, gh)` and `rect` the analysis rectangle
    /// `[x, y, w, h]` within it (the merge's level-0 size).
    pub fn with_preparation(
        merge: &BandMerge,
        full: (usize, usize),
        rect: [usize; 4],
    ) -> Result<Self, String> {
        let s0 = merge.sizes()[0];
        if (rect[2], rect[3]) != (s0.width, s0.height)
            || rect[0] + rect[2] > full.0
            || rect[1] + rect[3] > full.1
        {
            return Err("GPU preparation: analysis rectangle does not fit the frame".into());
        }
        let mut fold = Self::build(merge, Some(full), None)?;
        fold.rect = rect;
        Ok(fold)
    }

    fn build(
        merge: &BandMerge,
        full: Option<(usize, usize)>,
        bank_limit: Option<u64>,
    ) -> Result<Self, String> {
        if let Some(why) = merge.external_fold_refusal() {
            return Err(format!("GPU fold unavailable: {why}"));
        }
        let cfg = merge.config();
        let planes = merge.planes();
        // Any plane count (colour carry folds twelve): `accum` adds them four
        // per dispatch, and the arenas' size check below refuses a geometry
        // whose accumulators do not fit one binding.
        let ctx = context::shared()?;
        let context::Context {
            device,
            queue,
            bgl,
            pipelines,
            limits,
            adapter: adapter_name,
            decorated_results,
            profiling,
            key: _,
        } = ctx;

        let ensemble = cfg.ensemble;
        let hull = cfg.hull.bounds();
        // The null's windows without the smoothing reach: the device smooths
        // whole levels, so it needs only the windows themselves.
        let null_rects: Vec<Option<[usize; 4]>> = merge
            .null_window_rects()
            .into_iter()
            .map(|r| r.map(|[x, y, w, h]| [x + 2, y + 2, w - 4, h - 4]))
            .collect();
        // One storage binding's elements (wgpu caps a binding below 2 GiB);
        // the accumulators may span two.
        let binding = limits
            .max_storage_buffer_binding_size
            .min(limits.max_buffer_size);
        let bank_elems = (binding / 4)
            .min(u64::from(ACC_BANK) / 2)
            .min(bank_limit.unwrap_or(u64::MAX));
        let layout = Layout::new(
            merge.sizes(),
            planes,
            ensemble,
            hull,
            full,
            &null_rects,
            bank_elems,
        );
        let work_bytes = layout.work_len * 4;
        if work_bytes > binding {
            return Err(format!(
                "GPU fold workspace needs {work_bytes} bytes, above this device's {binding} byte binding limit"
            ));
        }
        if layout.acc_len.len() > 2 {
            return Err(format!(
                "GPU fold accumulators need {} bytes, above two of this device's {binding} byte bindings",
                layout.acc_len.iter().sum::<u64>() * 4
            ));
        }
        let storage = |label, size| {
            device.create_buffer(&wgpu::BufferDescriptor {
                label: Some(label),
                size,
                usage: wgpu::BufferUsages::STORAGE
                    | wgpu::BufferUsages::COPY_DST
                    | wgpu::BufferUsages::COPY_SRC,
                mapped_at_creation: false,
            })
        };
        let work = storage("fold-work", work_bytes);
        assert_eq!(
            layout.tables, 0,
            "fold.wgsl reads the screen tables at offset 0"
        );
        queue.write_buffer(&work, 0, bytemuck::cast_slice(&weight_screen_tables()));
        let acc = accumulator_banks(&device, &layout.acc_len, "fold-acc");
        let mut consts: Vec<f64> = Vec::with_capacity(30);
        consts.extend_from_slice(&LN_SERIES);
        consts.extend_from_slice(&EXP_SERIES);
        consts.extend_from_slice(&[
            std::f64::consts::LN_2,
            std::f64::consts::LOG2_E,
            std::f64::consts::SQRT_2,
        ]);
        consts.extend_from_slice(&LN64_SERIES);
        consts.extend_from_slice(&SIN_SERIES);
        consts.extend_from_slice(&COS_SERIES);
        consts.extend_from_slice(&[
            PIO2_HI,
            PIO2_LO,
            PIO2_HI + PIO2_LO,
            std::f64::consts::TAU,
            LN_UNIFORM_FLOOR,
            1.0 / f64::from(1u32 << 24),
        ]);
        // The f32 screen's constants, exactly as `portable_math` rounds them.
        consts.extend(
            [
                std::f32::consts::SQRT_2,
                std::f32::consts::LN_2,
                LN_UNIFORM_FLOOR as f32,
                1.0f32 / 3.0,
                0.2f32,
                1.0f32 / 7.0,
                1.0f32 / 9.0,
                1.0f32 / 11.0,
                std::f32::consts::FRAC_PI_2 / (1u32 << 22) as f32,
                -1.0f32 / 6.0,
                1.0f32 / 120.0,
                -1.0f32 / 5040.0,
                1.0f32 / 362_880.0,
                -0.5f32,
                1.0f32 / 24.0,
                -1.0f32 / 720.0,
                1.0f32 / 40320.0,
                -1.0f32 / 3_628_800.0,
            ]
            .map(f64::from),
        );
        debug_assert_eq!(consts.len(), 91, "fold.wgsl consts layout");
        // `C_TAPS`: the depth energies' blur taps ([`Self::enable_depth`]).
        consts.extend_from_slice(&[0.0; DEPTH_TAPS_MAX]);
        let consts = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("fold-consts"),
            contents: bytemuck::cast_slice(&consts),
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST,
        });
        let align = u64::from(limits.min_uniform_buffer_offset_alignment);
        let param_stride = (std::mem::size_of::<Params>() as u64).div_ceil(align) * align;
        let params: Vec<wgpu::Buffer> = (0..2)
            .map(|_| {
                device.create_buffer(&wgpu::BufferDescriptor {
                    label: Some("fold-params"),
                    size: param_stride * MAX_CALLS as u64,
                    usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
                    mapped_at_creation: false,
                })
            })
            .collect();
        let small = |label, size, usage| {
            device.create_buffer(&wgpu::BufferDescriptor {
                label: Some(label),
                size,
                usage,
                mapped_at_creation: false,
            })
        };
        let raw = small(
            "fold-raw",
            16,
            wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST,
        );
        let xf = small(
            "fold-xf",
            8 * XF_LEN,
            wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST,
        );
        let red = small(
            "fold-red",
            8 * red_len(&layout.sizes),
            wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC,
        );
        if layout.rgb_len * 4 > binding {
            return Err(format!(
                "GPU preparation's channel planes need {} bytes, above this device's {binding} byte binding limit",
                layout.rgb_len * 4
            ));
        }
        let rgbw = small(
            "fold-rgb",
            (layout.rgb_len * 4).max(16),
            // Read back: the depth energies are written here.
            wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC,
        );
        let bind = vec![make_binds(
            &device,
            &bgl,
            &params,
            [&work, &acc[0], &consts, &raw, &xf, &red, &acc[1], &rgbw],
        )];
        let profile = profiling.then(|| Profile::new(&device, &queue));
        let mut fold = Self {
            profile,
            device,
            queue,
            pipelines,
            bind,
            params,
            param_stride,
            work,
            acc: vec![acc],
            target: 0,
            bgl,
            consts,
            raw,
            raw_samples: 0,
            raw_members: 1,
            min_members: 1,
            rgbw,
            luma_pool: Default::default(),
            next_slot: 0,
            upload: Vec::new(),
            raw_generation: 0,
            xf,
            red,
            full,
            rect: [0; 4],
            layout,
            base_weighted: cfg.base == BaseBand::WeightedFromCoarsest,
            ensemble,
            hull,
            frame: 0,
            pending_reset: vec![true],
            depth: None,
            adapter: adapter_name,
            decorated_results,
        };
        fold.reset_accumulators();
        Ok(fold)
    }

    /// Per-kernel device time since creation, under [`PROFILE_ENV`]; `None`
    /// when not profiling.
    pub fn profile_report(&self) -> Option<String> {
        let prof = self.profile.as_ref()?;
        let total: f64 = prof.totals.iter().map(|t| t.1).sum();
        let mut rows: Vec<(usize, &(u64, f64))> = prof
            .totals
            .iter()
            .enumerate()
            .filter(|(_, t)| t.0 > 0)
            .collect();
        rows.sort_by(|a, b| b.1.1.total_cmp(&a.1.1));
        let mut out = format!(
            "device time {:.1} ms in kernels, {:.1} ms from each submission's first kernel to its last\n",
            total * 1e-6,
            prof.span_ns * 1e-6
        );
        for (k, (n, ns)) in rows {
            out.push_str(&format!(
                "  {:<14} {:>6} dispatches {:>9.2} ms {:>5.1}%, gaps before {:>7.2} ms\n",
                strict::ENTRY_POINTS[k],
                n,
                ns * 1e-6,
                100.0 * ns / total,
                prof.gaps[k] * 1e-6
            ));
        }
        Some(out)
    }

    /// Bytes of device memory the fold holds.
    pub fn device_bytes(&self) -> u64 {
        (self.layout.work_len + self.layout.acc_len.iter().sum::<u64>() * self.acc.len() as u64) * 4
    }

    /// A second accumulator arena, for a fold that keeps two half-stacks
    /// (`STREHL_OPTICAL_RESTORE`): [`Self::select_accumulator`] then chooses
    /// which one the next fold, read-back and reset address. Each holds its
    /// own totals, hull and ensemble windows, as two CPU merges would.
    pub fn add_second_accumulator(&mut self) -> Result<(), String> {
        if self.acc.len() > 1 {
            return Ok(());
        }
        let bytes = self.layout.acc_len.iter().sum::<u64>() * 4;
        let scope = self.device.push_error_scope(wgpu::ErrorFilter::OutOfMemory);
        let acc = accumulator_banks(&self.device, &self.layout.acc_len, "fold-acc-alt");
        if let Some(e) = pollster::block_on(scope.pop()) {
            return Err(format!(
                "GPU fold: a second {bytes}-byte accumulator does not fit this device: {e}"
            ));
        }
        self.acc.push(acc);
        self.pending_reset.push(true);
        self.rebind();
        let target = self.target;
        self.target = 1;
        self.reset_accumulators();
        self.target = target;
        Ok(())
    }

    /// Bindings each accumulator arena spans (one, or two past one binding).
    #[doc(hidden)]
    pub fn accumulator_bank_count(&self) -> usize {
        self.layout.acc_len.len()
    }

    /// The accumulator arenas this fold holds.
    pub fn accumulators(&self) -> usize {
        self.acc.len()
    }

    /// Fold into, read back and reset accumulator `target` from now on.
    pub fn select_accumulator(&mut self, target: usize) {
        assert!(target < self.acc.len(), "no accumulator {target}");
        self.target = target;
    }

    /// Bind groups for every accumulator over the current buffers.
    fn rebind(&mut self) {
        self.bind = self
            .acc
            .iter()
            .map(|acc| {
                make_binds(
                    &self.device,
                    &self.bgl,
                    &self.params,
                    [
                        &self.work,
                        &acc[0],
                        &self.consts,
                        &self.raw,
                        &self.xf,
                        &self.red,
                        &acc[1],
                        &self.rgbw,
                    ],
                )
            })
            .collect();
    }

    fn submit(&mut self, rec: Recorder) -> wgpu::SubmissionIndex {
        self.submit_with(rec, |_, _| {})
    }

    /// Submit `rec`'s dispatches, then whatever `after` records (copies) in
    /// the same command buffer.
    fn submit_with(
        &mut self,
        rec: Recorder,
        after: impl FnOnce(&mut wgpu::CommandEncoder, &Self),
    ) -> wgpu::SubmissionIndex {
        assert!(rec.calls.len() <= MAX_CALLS, "too many dispatches");
        let slot = self.frame % self.params.len();
        let mut bytes = vec![0u8; self.param_stride as usize * rec.calls.len()];
        for (i, (_, p, _)) in rec.calls.iter().enumerate() {
            let at = i * self.param_stride as usize;
            bytes[at..at + std::mem::size_of::<Params>()].copy_from_slice(bytemuck::bytes_of(p));
        }
        if !bytes.is_empty() {
            self.queue.write_buffer(&self.params[slot], 0, &bytes);
        }
        let mut encoder = self
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                label: Some("fold"),
            });
        if let Some(prof) = &self.profile {
            for (i, (k, _, n)) in rec.calls.iter().enumerate() {
                let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor {
                    label: Some("fold-profiled"),
                    timestamp_writes: Some(wgpu::ComputePassTimestampWrites {
                        query_set: &prof.set,
                        beginning_of_pass_write_index: Some(2 * i as u32),
                        end_of_pass_write_index: Some(2 * i as u32 + 1),
                    }),
                });
                if *n == 0 {
                    continue;
                }
                pass.set_pipeline(&self.pipelines[k.index()]);
                pass.set_bind_group(
                    0,
                    &self.bind[self.target][slot],
                    &[(i as u64 * self.param_stride) as u32],
                );
                let groups = n.div_ceil(WG);
                let (x, y) = if groups <= 65535 {
                    (groups, 1)
                } else {
                    (65535, groups.div_ceil(65535))
                };
                pass.dispatch_workgroups(x, y, 1);
            }
            let q = 2 * rec.calls.len() as u32;
            if q > 0 {
                encoder.resolve_query_set(&prof.set, 0..q, &prof.resolve, 0);
                encoder.copy_buffer_to_buffer(
                    &prof.resolve,
                    0,
                    &prof.readback,
                    0,
                    u64::from(q) * 8,
                );
            }
        } else {
            let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor {
                label: Some("fold"),
                timestamp_writes: None,
            });
            for (i, (k, _, n)) in rec.calls.iter().enumerate() {
                if *n == 0 {
                    continue;
                }
                pass.set_pipeline(&self.pipelines[k.index()]);
                pass.set_bind_group(
                    0,
                    &self.bind[self.target][slot],
                    &[(i as u64 * self.param_stride) as u32],
                );
                let groups = n.div_ceil(WG);
                let (x, y) = if groups <= 65535 {
                    (groups, 1)
                } else {
                    (65535, groups.div_ceil(65535))
                };
                pass.dispatch_workgroups(x, y, 1);
            }
        }
        after(&mut encoder, self);
        let index = self.queue.submit([encoder.finish()]);
        if let Some(prof) = &mut self.profile
            && !rec.calls.is_empty()
        {
            let q = 2 * rec.calls.len();
            let slice = prof.readback.slice(..q as u64 * 8);
            slice.map_async(wgpu::MapMode::Read, |r| r.expect("map profile"));
            self.device
                .poll(wgpu::PollType::wait_indefinitely())
                .expect("GPU profile wait");
            {
                let view = slice.get_mapped_range().expect("mapped profile");
                let stamps: &[u64] = bytemuck::cast_slice(&view[..]);
                prof.span_ns += stamps[q - 1].wrapping_sub(stamps[0]) as f64 * prof.period_ns;
                for (i, (k, _, _)) in rec.calls.iter().enumerate() {
                    let ns = stamps[2 * i + 1].wrapping_sub(stamps[2 * i]) as f64 * prof.period_ns;
                    let t = &mut prof.totals[k.index()];
                    t.0 += 1;
                    t.1 += ns;
                    if i > 0 {
                        prof.gaps[k.index()] +=
                            stamps[2 * i].wrapping_sub(stamps[2 * i - 1]) as f64 * prof.period_ns;
                    }
                }
            }
            prof.readback.unmap();
        }
        if std::env::var_os("STREHL_GPU_SYNC").is_some() {
            self.device
                .poll(wgpu::PollType::wait_indefinitely())
                .expect("GPU fold wait");
        }
        self.frame += 1;
        index
    }

    fn reset_accumulators(&mut self) {
        let mut rec = Recorder { calls: Vec::new() };
        for (bank, &n) in self.layout.acc_len.iter().enumerate() {
            let at = if bank > 0 { ACC_BANK } else { 0 };
            rec.fill(at, n as usize, 0.0, true);
        }
        for c in 0..self.layout.lo.len() {
            rec.fill(
                self.layout.lo[c],
                self.layout.sizes[0].pixels(),
                f32::INFINITY,
                true,
            );
            rec.fill(
                self.layout.hi[c],
                self.layout.sizes[0].pixels(),
                f32::NEG_INFINITY,
                true,
            );
        }
        self.submit(rec);
        self.pending_reset[self.target] = false;
    }

    fn upload(&self, at: u32, data: &[f32]) {
        let bytes: &[u8] = bytemuck::cast_slice(data);
        let size = wgpu::BufferSize::new(bytes.len() as u64).expect("non-empty upload");
        let mut view = self
            .queue
            .write_buffer_with(&self.work, u64::from(at) * 4, size)
            .expect("upload staging");
        view.copy_from_slice(bytes);
    }

    /// Fold one frame: `planes` black-subtracted at level 0, `variance` the
    /// luma noise variance, `frame_beta` the measured band floor. Equivalent to
    /// `merge.add_frame_with_gain(planes, luma, variance, frame_beta, ws)` with
    /// `luma = (planes[1] + planes[2]) / 2`. The call returns once the work is
    /// queued; the device runs it while the caller prepares the next frame.
    pub fn add_frame(
        &mut self,
        merge: &mut BandMerge,
        planes: &[&[f32]],
        variance: &[f32],
        frame_beta: Option<&[f32]>,
    ) {
        if self.pending_reset[self.target] {
            self.reset_accumulators();
        }
        let l = &self.layout;
        let n0 = l.sizes[0].pixels();
        assert_eq!(planes.len(), l.planes, "wrong number of planes");
        assert!(l.planes >= 3, "green luma needs planes 1 and 2");
        assert!(planes.iter().all(|p| p.len() == n0) && variance.len() == n0);
        let scalars: Vec<LevelScalars> = merge.level_scalars(frame_beta);
        for (c, plane) in planes.iter().enumerate() {
            self.upload(l.plane_lv[c][0], plane);
        }
        self.upload(l.var_lv[0], variance);
        let mut rec = Recorder { calls: Vec::new() };
        self.record_fold(&mut rec, &scalars, None, false);
        self.submit(rec);
        merge.note_external_frame();
    }

    /// The fold's dispatches for planes already at `plane_lv[c][0]`; with
    /// `noise`, the luma variance is computed here rather than uploaded.
    fn record_fold(
        &self,
        rec: &mut Recorder,
        scalars: &[LevelScalars],
        noise: Option<GreenNoise>,
        keep_luma: bool,
    ) {
        let l = &self.layout;
        let n0 = l.sizes[0].pixels();
        let sizes = &l.sizes;
        let nl = sizes.len();
        let nb = nl - 1;
        // Luma from the raw greens, before the planes are decomposed in place.
        rec.push(
            Kernel::Luma,
            Params {
                a: [l.plane_lv[1][0], l.plane_lv[2][0], l.luma_lv[0], n0 as u32],
                ..Default::default()
            },
            n0,
        );
        if keep_luma {
            // The level-0 luma as formed, before `laplacian` rewrites it.
            let s = sizes[0];
            rec.push(
                Kernel::Pack,
                Params {
                    a: [l.luma_lv[0], s.width as u32, 0, s.width as u32],
                    b: [0, s.height as u32, l.luma_keep, 0],
                    ..Default::default()
                },
                n0,
            );
        }
        if let Some(nz) = noise {
            rec.push(
                Kernel::Variance,
                Params {
                    a: [l.luma_lv[0], l.var_lv[0], n0 as u32, 0],
                    f: [nz.gain[0], nz.read_dn[0], nz.gain[1], nz.read_dn[1]],
                    ..Default::default()
                },
                n0,
            );
        }
        // Hull of the raw inputs.
        if self.hull {
            for c in 0..l.planes {
                rec.push(
                    Kernel::Hull,
                    Params {
                        a: [l.plane_lv[c][0], l.lo[c], l.hi[c], n0 as u32],
                        ..Default::default()
                    },
                    n0,
                );
            }
        }
        rec.laplacian(l.scratch, sizes, &l.luma_lv);
        rec.gaussian(l.scratch, sizes, &l.var_lv);
        for c in 0..l.planes {
            rec.laplacian(l.scratch, sizes, &l.plane_lv[c]);
        }
        for k in 0..nb {
            let s = sizes[k];
            let px = s.pixels();
            let sc = scalars[k];
            if !sc.averaged {
                rec.push(
                    Kernel::SmoothH,
                    Params {
                        a: [l.luma_lv[k], s.width as u32, s.height as u32, l.scratch],
                        ..Default::default()
                    },
                    px,
                );
                rec.push(
                    Kernel::SmoothV,
                    Params {
                        a: [l.scratch, s.width as u32, s.height as u32, l.sq],
                        ..Default::default()
                    },
                    px,
                );
                if k > 0 {
                    rec.reduce(l.scratch, l.ev_a, sizes[k - 1], l.ev_b);
                }
            }
            let flags = u32::from(k == 0)
                | if self.ensemble { 2 } else { 0 }
                | if sc.averaged { 4 } else { 0 };
            let ens = if self.ensemble {
                [l.zmax[k], l.zsum[k], l.lsum[k], l.esum[k]]
            } else {
                [0; 4]
            };
            rec.push(
                Kernel::Level,
                Params {
                    a: [l.sq, l.var_lv[k], l.luma_lv[k], l.ev_a],
                    b: [l.ev_b, l.weight, px as u32, flags],
                    c: ens,
                    f: [sc.beta, sc.gate, sc.p, sc.ratio],
                    g: [sc.levels, 0.0, 0.0, 0.0],
                    ..Default::default()
                },
                px,
            );
            rec.accum(l, l.weight, k);
        }
        // The base band: the coarsest band's weight reduced once, or zero.
        let base = sizes[nb];
        if self.base_weighted && nb > 0 {
            rec.reduce(l.scratch, l.weight, sizes[nb - 1], l.coarse);
        } else {
            rec.fill(l.coarse, base.pixels(), 0.0, false);
        }
        rec.accum(l, l.coarse, nb);
    }

    /// Size the raw buffer for frames of `samples` u16 each: two frame slots,
    /// alternating so one frame can be staged and probed while the other is
    /// still to be folded, and the probe's slot.
    fn ensure_raw(&mut self, samples: usize, members: usize) {
        // A whole number of 8-byte words per member, so every member's region
        // in a frame slot can be mapped on its own (`stage`).
        let samples = (samples as u64).next_multiple_of(4);
        let members = members.max(self.min_members);
        if self.raw_samples == samples && self.raw_members >= members {
            return;
        }
        let members = members.max(self.raw_members);
        self.raw_members = members;
        self.raw = self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("fold-raw"),
            size: samples * 2 * raw_frames(members),
            usage: wgpu::BufferUsages::STORAGE
                | wgpu::BufferUsages::COPY_DST
                | wgpu::BufferUsages::COPY_SRC,
            mapped_at_creation: false,
        });
        self.raw_samples = samples;
        // Frames staged in the old buffer are gone.
        self.raw_generation += 1;
        self.upload = (0..2)
            .map(|_| UploadSlot {
                buffer: self.device.create_buffer(&wgpu::BufferDescriptor {
                    label: Some("fold-upload"),
                    size: samples * 2 * members as u64,
                    usage: wgpu::BufferUsages::MAP_WRITE | wgpu::BufferUsages::COPY_SRC,
                    mapped_at_creation: true,
                }),
                copy: None,
                mapped: std::sync::Arc::new(std::sync::atomic::AtomicBool::new(true)),
            })
            .collect();
        self.rebind();
    }

    /// The first sample of `slot`'s frame (its member 1) in the raw buffer.
    fn raw_base(&self, slot: usize) -> u32 {
        (slot as u64 * self.raw_members as u64 * self.raw_samples) as u32
    }

    /// Hold room for `members` frames per frame slot from the first stage on
    /// (a pixel-shift stack: four), so a group arriving after single frames
    /// does not reallocate the raw buffer under staged frames.
    pub fn reserve_members(&mut self, members: usize) {
        self.min_members = members.max(1);
    }

    /// Upload `frame` (with its group's members, side by side in the slot)
    /// into the next frame slot and its pulls into that slot's `xf` sites.
    /// wgpu copies the samples before this returns, so the caller may free
    /// the frames at once. The slot stays valid until the second `stage`
    /// after this one.
    pub fn stage(&mut self, frame: &RawFrame<'_>) -> Result<Staged, String> {
        let (gw, gh) = self.full.ok_or("GPU preparation layout")?;
        let (width, rows) = (2 * gw, 2 * gh);
        let members = if frame.group.is_some() { 4 } else { 1 };
        let padded = (frame.data.len() as u64).next_multiple_of(4);
        if frame.stride < frame.active[0] + width
            || frame.data.len() < (frame.active[1] + rows) * frame.stride
            || (width * rows) as u64 + 2 > u64::from(u32::MAX)
            || raw_frames(members.max(self.min_members)) * padded > i32::MAX as u64
        {
            return Err("GPU preparation: frame geometry out of range".into());
        }
        if frame.carried.is_some() && frame.pulls.is_none() {
            return Err("GPU preparation: carried channels need the aligned gather".into());
        }
        let group = match &frame.group {
            None => None,
            Some(g) => {
                if frame.pulls.is_none() {
                    return Err(
                        "pixel-shift assembly needs the aligned gather and no defect correction"
                            .into(),
                    );
                }
                if g.members.iter().any(|m| m.len() != frame.data.len()) {
                    return Err("GPU preparation: group members differ in size".into());
                }
                if g.offsets
                    .iter()
                    .any(|&(x, y)| !(-8..8).contains(&x) || !(-8..8).contains(&y))
                {
                    return Err("GPU preparation: a member offset beyond 7 photosites".into());
                }
                let offsets = g
                    .offsets
                    .iter()
                    .enumerate()
                    .fold(0u32, |acc, (j, &(x, y))| {
                        acc | (((x + 8) as u32 | ((y + 8) as u32) << 4) << (8 * j))
                    });
                let mut table = 0u32;
                for class in 0..4usize {
                    let sm = strehl_core::pixel_shift::site_members(
                        &g.offsets,
                        (class & 1) as isize,
                        (class >> 1) as isize,
                    );
                    if sm.iter().any(|&k| k > 3) {
                        return Err(
                            "GPU preparation: group offsets do not cover the CFA parities".into(),
                        );
                    }
                    let packed = sm[0] as u32
                        | (sm[1] as u32) << 2
                        | (sm[2] as u32) << 4
                        | (sm[3] as u32) << 6;
                    table |= packed << (8 * class);
                }
                Some(GroupParams {
                    offsets,
                    table,
                    inv: g.inv,
                    residuals: g.residuals,
                })
            }
        };
        self.ensure_raw(frame.data.len(), members);
        let slot = self.next_slot;
        self.next_slot ^= 1;
        let base = u64::from(self.raw_base(slot)) * 2;
        // Through this slot's persistently mapped upload buffer: wait for its
        // last copy out (two frames ago) and the re-map, fill it in parallel
        // chunks, then copy it to the device. No staging memory is allocated
        // per frame. Each member's tail is zero-padded to its slot length.
        let up = &mut self.upload[slot];
        if let Some(index) = up.copy.take() {
            self.device
                .poll(wgpu::PollType::Wait {
                    submission_index: Some(index),
                    timeout: None,
                })
                .map_err(|e| format!("GPU upload wait: {e:?}"))?;
        }
        if !up.mapped.load(std::sync::atomic::Ordering::Acquire) {
            return Err("GPU upload buffer was not re-mapped".into());
        }
        let sources: Vec<&[u8]> = std::iter::once(frame.data)
            .chain(frame.group.iter().flat_map(|g| g.members))
            .map(bytemuck::cast_slice)
            .collect();
        // Mapped ranges start 8-byte aligned and span whole words: each
        // member's region is a multiple of 8 bytes (`ensure_raw`), and so is
        // every chunk within it.
        const UPLOAD_CHUNK: usize = 1 << 22;
        let per = (self.raw_samples * 2) as usize;
        let jobs: Vec<(usize, usize, usize)> = (0..sources.len())
            .flat_map(|j| {
                (0..per.div_ceil(UPLOAD_CHUNK))
                    .map(move |i| (j, i * UPLOAD_CHUNK, ((i + 1) * UPLOAD_CHUNK).min(per)))
            })
            .collect();
        let buffer = &up.buffer;
        jobs.into_par_iter().for_each(|(j, at, end)| {
            let bytes = sources[j];
            let data = &bytes[at.min(bytes.len())..end.min(bytes.len())];
            let mut view = buffer
                .slice((j * per + at) as u64..(j * per + end) as u64)
                .get_mapped_range_mut()
                .expect("mapped upload buffer");
            view.slice(..data.len()).copy_from_slice(data);
            if data.len() < end - at {
                view.slice(data.len()..)
                    .copy_from_slice(&vec![0u8; end - at - data.len()]);
            }
        });
        let size = (sources.len() * per) as u64;
        up.mapped.store(false, std::sync::atomic::Ordering::Release);
        up.buffer.unmap();
        let mut encoder = self
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                label: Some("fold-upload"),
            });
        encoder.copy_buffer_to_buffer(&self.upload[slot].buffer, 0, &self.raw, base, size);
        let index = self.queue.submit([encoder.finish()]);
        let up = &mut self.upload[slot];
        let mapped = up.mapped.clone();
        up.buffer
            .slice(..)
            .map_async(wgpu::MapMode::Write, move |r| {
                r.expect("re-map upload buffer");
                mapped.store(true, std::sync::atomic::Ordering::Release);
            });
        up.copy = Some(index);
        let (cx, cy) = (gw as f64 * 0.5, gh as f64 * 0.5);
        if let Some(pulls) = frame.pulls {
            let mut xf = [0f64; 8 * PULLS];
            let native = SITES.iter().zip(pulls.iter());
            let carried = CARRIED_SITES
                .iter()
                .map(|&(dx, dy, _)| (dx, dy))
                .zip(frame.carried.iter().flatten());
            let site_pulls: Vec<((usize, usize), &SitePull)> =
                native.map(|(&s, t)| (s, t)).chain(carried).collect();
            for (i, ((dx, dy), t)) in site_pulls.into_iter().enumerate() {
                xf[8 * i..8 * i + 8].copy_from_slice(&[
                    t.a[0],
                    t.a[1],
                    t.b[0],
                    t.b[1],
                    dx as f64 * 0.5,
                    dy as f64 * 0.5,
                    cx,
                    cy,
                ]);
            }
            self.queue.write_buffer(
                &self.xf,
                (slot * 8 * PULLS * 8) as u64,
                bytemuck::cast_slice(&xf),
            );
        }
        Ok(Staged {
            slot,
            generation: self.raw_generation,
            len: frame.data.len(),
            stride: frame.stride,
            active: frame.active,
            black: frame.black,
            gain: frame.gain,
            warped: frame.pulls.is_some(),
            carried: frame.carried.is_some(),
            group,
        })
    }

    fn check_staged(&self, staged: &Staged) -> Result<(), String> {
        if staged.generation != self.raw_generation {
            return Err("GPU preparation: staged frame was evicted by a geometry change".into());
        }
        Ok(())
    }

    /// Record the gather (or unwarped extraction) of `sites` of the frame at
    /// raw sample `base`, through slot `pulls`' site pulls, into the given
    /// level-0 planes. Sites 0-3 are the CFA sites, 4-11 the carried channels
    /// ([`CARRIED_SITES`]). A staged group's channels are assembled from its
    /// members (`assemble`); otherwise, and for the probe (`green_only`),
    /// demosaiced from member 1 (`mhc`).
    #[allow(clippy::too_many_arguments)]
    fn record_gather(
        &self,
        rec: &mut Recorder,
        frame: &Staged,
        base: u32,
        pulls: usize,
        sites: &[usize],
        dst: &[u32],
        green_only: bool,
    ) {
        let (gw, gh) = self.full.expect("preparation layout");
        let (fw, fh) = (2 * gw, 2 * gh);
        let [rx, ry, lw, lh] = self.rect;
        let rect = [rx as u32, ry as u32, lw as u32, lh as u32];
        let black = frame.black;
        let black_dn = black.round().clamp(0.0, f32::from(u16::MAX)) as u16;
        let origin = (frame.active[1] * frame.stride + frame.active[0]) as u32;
        let raw_base = base + origin;
        let l = &self.layout;
        if !frame.warped {
            for (&s, &d) in sites.iter().zip(dst) {
                let (dx, dy) = SITES[s];
                rec.push(
                    Kernel::Extract,
                    Params {
                        a: [raw_base, frame.stride as u32, d, 0],
                        b: rect,
                        c: [dx as u32, dy as u32, 0, 0],
                        f: [black, 0.0, 0.0, 0.0],
                        ..Default::default()
                    },
                    lw * lh,
                );
            }
            return;
        }
        match frame.group.filter(|_| !green_only) {
            Some(g) => {
                let member = |j: usize| raw_base + (j as u64 * self.raw_samples) as u32;
                let (rx, ry) = match g.residuals {
                    Some(r) => (r.map(|v| v[0].to_bits()), r.map(|v| v[1].to_bits())),
                    None => ([0; 4], [0; 4]),
                };
                rec.push(
                    Kernel::Assemble,
                    Params {
                        a: [
                            l.rgb,
                            fw as u32,
                            fh as u32,
                            u32::from(g.residuals.is_some()),
                        ],
                        b: [member(0), member(1), member(2), member(3)],
                        c: [frame.stride as u32, g.offsets, g.table, 0],
                        d: rx,
                        e: ry,
                        f: [black, frame.gain[0], frame.gain[1], frame.gain[2]],
                        g: g.inv,
                    },
                    fw * fh,
                );
            }
            None => rec.push(
                Kernel::Mhc,
                Params {
                    a: [l.rgb, fw as u32, fh as u32, u32::from(green_only)],
                    b: [raw_base, frame.stride as u32, 0, 0],
                    f: [black, frame.gain[0], frame.gain[1], frame.gain[2]],
                    ..Default::default()
                },
                // One invocation per 2x2 quad.
                gw * gh,
            ),
        }
        for (&s, &d) in sites.iter().zip(dst) {
            let ci = if s < 4 {
                let (dx, dy) = SITES[s];
                site_channel(dx, dy)
            } else {
                CARRIED_SITES[s - 4].2
            };
            let plane = if green_only {
                l.rgb
            } else {
                l.rgb + (ci * fw * fh) as u32
            };
            let inv = 1.0 / frame.gain[ci];
            rec.push(
                Kernel::Gather,
                Params {
                    a: [plane, fw as u32, fh as u32, d],
                    b: rect,
                    c: [u32::from(black_dn), (PULLS * pulls + s) as u32, 0, 0],
                    f: [black, inv, 0.0, 0.0],
                    ..Default::default()
                },
                lw * lh,
            );
        }
    }

    /// The gate-floor probe on the device: build the probe frame from the
    /// staged frame and `noise` as `gatefloor` does (a copy of the frame with
    /// its active complete quads replaced by seeded noise), gather its greens,
    /// form and zero-mean its luma and build its Laplacian pyramid. Reads back,
    /// from that pyramid, the f64 sum of squares over each `[level, x, y, w, h]`
    /// of `sums` (each row in column order, then the rows in order:
    /// `gatefloor::square_sum`), and each requested `[x, y, w, h]` window of
    /// `windows` (indexed by level), row-major. Only these cross PCIe.
    ///
    /// Returns without waiting: [`Self::probe_collect`] waits for this probe
    /// alone, so the caller can fold the previous frame meanwhile. Requires an
    /// integral black level: the luma's f64 sum is then exact in any order,
    /// which is what lets the device reproduce the CPU's mean.
    pub fn probe_submit(
        &mut self,
        frame: &Staged,
        noise: ProbeNoise,
        sums: &[[usize; 5]],
    ) -> Result<PendingProbe, String> {
        self.check_staged(frame)?;
        let sizes = &self.layout.sizes;
        let fits = |k: usize, [x, y, w, h]: [usize; 4]| {
            k < sizes.len()
                && x + w <= sizes[k].width
                && y + h <= sizes[k].height
                && [x, y, w, h].iter().all(|&v| v <= SQ_WINDOW_MAX)
        };
        if !sums.iter().all(|&[k, x, y, w, h]| fits(k, [x, y, w, h])) {
            return Err("GPU probe: a requested rectangle is outside its level".into());
        }
        if frame.black.fract() != 0.0 {
            return Err("GPU probe needs an integral black level".into());
        }
        if !frame.warped {
            return Err("the probe is only measured for a warped frame".into());
        }
        let (gw, gh) = self.full.expect("preparation layout");
        let (width, rows) = (2 * gw, 2 * gh);
        let words = frame.len.div_ceil(2);
        self.queue.write_buffer(
            &self.xf,
            XF_NOISE * 8,
            bytemuck::cast_slice(&[
                noise.level,
                noise.sigma,
                strehl_core::portable_math::probe_f32_margin(noise.sigma),
            ]),
        );
        let base = self.raw_base(PROBE_SLOT);
        let mut rec = Recorder { calls: Vec::new() };
        rec.push(
            Kernel::Noise,
            Params {
                a: [words as u32, base / 2, frame.stride as u32, width as u32],
                b: [
                    frame.active[0] as u32,
                    frame.active[1] as u32,
                    rows as u32,
                    self.raw_base(frame.slot) / 2,
                ],
                c: [noise.seed as u32, (noise.seed >> 32) as u32, 0, 0],
                ..Default::default()
            },
            words,
        );
        let l = &self.layout;
        let n0 = l.sizes[0].pixels();
        // Greens into the planes' level-0 slots: the fold that follows in the
        // queue regathers them, and the readback below precedes it.
        self.record_gather(
            &mut rec,
            frame,
            base,
            frame.slot,
            &[1, 2],
            &[l.plane_lv[1][0], l.plane_lv[2][0]],
            true,
        );
        rec.push(
            Kernel::Luma,
            Params {
                a: [l.plane_lv[1][0], l.plane_lv[2][0], l.probe_lv[0], n0 as u32],
                ..Default::default()
            },
            n0,
        );
        let row = rec.exact_sum(l.probe_lv[0], n0);
        rec.push(
            Kernel::Demean,
            Params {
                a: [l.probe_lv[0], n0 as u32, 0, 0],
                ..Default::default()
            },
            n0,
        );
        rec.laplacian(l.scratch, &l.sizes, &l.probe_lv);
        let windows: Vec<(u32, u32, [usize; 4])> = sums
            .iter()
            .map(|&[k, x, y, w, h]| (l.probe_lv[k], l.sizes[k].width as u32, [x, y, w, h]))
            .collect();
        let total = rec.square_sums(&windows, row);
        // The ensemble null's windows, kept on the device for this frame's
        // fold: each band's coefficients, and its energy (the fold's own
        // smoothing over the whole level, so the window's interior is the
        // level's), packed into this frame slot's region.
        for (k, region) in l.null.iter().enumerate() {
            let Some(region) = region else { continue };
            let s = l.sizes[k];
            let [x, y, w, h] = region.rect;
            rec.push(
                Kernel::SmoothH,
                Params {
                    a: [l.probe_lv[k], s.width as u32, s.height as u32, l.scratch],
                    ..Default::default()
                },
                s.pixels(),
            );
            rec.push(
                Kernel::SmoothV,
                Params {
                    a: [l.scratch, s.width as u32, s.height as u32, l.sq],
                    ..Default::default()
                },
                s.pixels(),
            );
            for (src, dst) in [
                (l.probe_lv[k], region.lv[frame.slot]),
                (l.sq, region.energy[frame.slot]),
            ] {
                rec.push(
                    Kernel::Pack,
                    Params {
                        a: [src, s.width as u32, x as u32, w as u32],
                        b: [y as u32, h as u32, dst, 0],
                        ..Default::default()
                    },
                    w * h,
                );
            }
        }
        let bytes = sums.len() as u64 * 8;
        let readback = self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("fold-probe-readback"),
            size: bytes.max(8),
            usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        let index = self.submit_with(rec, |encoder, fold| {
            if bytes > 0 {
                encoder.copy_buffer_to_buffer(&fold.red, u64::from(total) * 8, &readback, 0, bytes);
            }
        });
        readback
            .slice(..)
            .map_async(wgpu::MapMode::Read, |r| r.expect("map probe readback"));
        Ok(PendingProbe {
            readback,
            index,
            sums: sums.len(),
        })
    }

    /// Wait for one submitted probe (not for later work) and read it.
    pub fn probe_collect(&self, pending: PendingProbe) -> Result<ProbeOutput, String> {
        self.device
            .poll(wgpu::PollType::Wait {
                submission_index: Some(pending.index),
                timeout: None,
            })
            .map_err(|e| format!("GPU probe wait: {e:?}"))?;
        let out = {
            let view = pending
                .readback
                .slice(..)
                .get_mapped_range()
                .map_err(|e| format!("mapped probe: {e:?}"))?;
            let totals: &[f64] = bytemuck::cast_slice(&view[..pending.sums * 8]);
            ProbeOutput {
                sums: totals.to_vec(),
            }
        };
        pending.readback.unmap();
        Ok(out)
    }

    /// [`Self::stage`], [`Self::probe_submit`] and [`Self::probe_collect`] in
    /// one blocking call.
    pub fn probe(
        &mut self,
        frame: &RawFrame<'_>,
        noise: ProbeNoise,
        sums: &[[usize; 5]],
    ) -> Result<ProbeOutput, String> {
        let staged = self.stage(frame)?;
        let pending = self.probe_submit(&staged, noise, sums)?;
        self.probe_collect(pending)
    }

    /// Run the weight's ln (`exp == false`) or exp screen over every f32 whose
    /// bits lie in `first..=last` against the f64 function on this device
    /// (`screen_census` in `fold.wgsl`). For tests: the screens are exact only
    /// if this finds no mismatch over every input they can receive.
    #[doc(hidden)]
    pub fn screen_census(&mut self, exp: bool, first: u32, last: u32) -> ScreenCensus {
        const PER: u32 = 256;
        const INVOCATIONS: u32 = 1 << 18;
        let words = 4 * u64::from(INVOCATIONS);
        if self.raw_samples * 2 * raw_frames(self.raw_members) < words * 4 {
            self.ensure_raw((words * 2) as usize, 1);
        }
        let readback = self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("screen-census"),
            size: words * 4,
            usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        let mut out = ScreenCensus::default();
        let mut start = u64::from(first);
        while start <= u64::from(last) {
            let count = (u64::from(last) - start + 1).min(u64::from(PER * INVOCATIONS));
            let invocations = count.div_ceil(u64::from(PER)) as u32;
            let mut rec = Recorder { calls: Vec::new() };
            rec.push(
                Kernel::ScreenCensus,
                Params {
                    a: [start as u32, PER, u32::from(exp), invocations],
                    b: [(start + count - 1) as u32, 0, 0, 0],
                    ..Default::default()
                },
                invocations as usize,
            );
            let n = u64::from(invocations) * 16;
            let index = self.submit_with(rec, |encoder, fold| {
                encoder.copy_buffer_to_buffer(&fold.raw, 0, &readback, 0, n);
            });
            let slice = readback.slice(..n);
            slice.map_async(wgpu::MapMode::Read, |r| r.expect("map census"));
            self.device
                .poll(wgpu::PollType::Wait {
                    submission_index: Some(index),
                    timeout: None,
                })
                .expect("census wait");
            {
                let view = slice.get_mapped_range().expect("mapped census");
                for w in bytemuck::cast_slice::<u8, [u32; 4]>(&view[..]) {
                    out.mismatches += u64::from(w[0]);
                    out.fallbacks += u64::from(w[1]);
                    if w[2] != u32::MAX {
                        out.first_mismatch = Some(out.first_mismatch.map_or(w[2], |f| f.min(w[2])));
                    }
                    out.worst_ratio = out.worst_ratio.max(f32::from_bits(w[3]));
                }
            }
            readback.unmap();
            out.inputs += count;
            start += count;
        }
        out
    }

    /// The probe frame [`Self::probe`] builds on the device, read back: for
    /// testing the noise fill against the CPU's.
    #[doc(hidden)]
    pub fn probe_frame(
        &mut self,
        frame: &RawFrame<'_>,
        noise: ProbeNoise,
    ) -> Result<Vec<u16>, String> {
        self.probe(frame, noise, &[])?;
        let bytes = frame.data.len().div_ceil(2) as u64 * 4;
        let readback = self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("fold-raw-readback"),
            size: bytes,
            usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        let mut encoder = self
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                label: Some("raw-readback"),
            });
        let from = u64::from(self.raw_base(PROBE_SLOT)) * 2;
        encoder.copy_buffer_to_buffer(&self.raw, from, &readback, 0, bytes);
        self.queue.submit([encoder.finish()]);
        readback
            .slice(..)
            .map_async(wgpu::MapMode::Read, |r| r.expect("map raw readback"));
        self.device
            .poll(wgpu::PollType::wait_indefinitely())
            .map_err(|e| format!("GPU wait: {e:?}"))?;
        let mut out = {
            let view = readback
                .slice(..)
                .get_mapped_range()
                .map_err(|e| format!("{e:?}"))?;
            bytemuck::cast_slice::<u8, u16>(&view[..]).to_vec()
        };
        out.truncate(frame.data.len());
        Ok(out)
    }

    /// The probe's two f64 reductions over supplied values, read back: the
    /// exact sum the zero-mean takes (values must keep it exact, as the probe
    /// luma does), and each `[x, y, w, h]` window's `gatefloor::square_sum`
    /// with `values` as a level `width` samples wide. For testing the device's
    /// order of addition against the CPU's.
    #[doc(hidden)]
    pub fn probe_sums(
        &mut self,
        values: &[f32],
        width: usize,
        windows: &[[usize; 4]],
    ) -> Result<(f64, Vec<f64>), String> {
        let at = self.layout.probe_lv[0];
        let n = values.len();
        if n > self.layout.sizes[0].pixels() || width == 0 || !n.is_multiple_of(width) {
            return Err("probe sums: values do not fit the probe level".into());
        }
        let rows = n / width;
        if !windows.iter().all(|&[x, y, w, h]| {
            x + w <= width && y + h <= rows && [x, y, w, h].iter().all(|&v| v <= SQ_WINDOW_MAX)
        }) {
            return Err("probe sums: a window is outside the values".into());
        }
        let mut rec = Recorder { calls: Vec::new() };
        let row = rec.exact_sum(at, n);
        let level: Vec<(u32, u32, [usize; 4])> =
            windows.iter().map(|&r| (at, width as u32, r)).collect();
        let total = rec.square_sums(&level, row);
        let len = u64::from(total) + windows.len() as u64;
        if len > red_len(&self.layout.sizes) {
            return Err("probe sums: too many window rows".into());
        }
        self.queue
            .write_buffer(&self.work, u64::from(at) * 4, bytemuck::cast_slice(values));
        let readback = self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("probe-sums-readback"),
            size: len * 8,
            usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        let index = self.submit_with(rec, |encoder, fold| {
            encoder.copy_buffer_to_buffer(&fold.red, 0, &readback, 0, len * 8);
        });
        readback
            .slice(..)
            .map_async(wgpu::MapMode::Read, |r| r.expect("map probe sums"));
        self.device
            .poll(wgpu::PollType::Wait {
                submission_index: Some(index),
                timeout: None,
            })
            .map_err(|e| format!("GPU wait: {e:?}"))?;
        let view = readback
            .slice(..)
            .get_mapped_range()
            .map_err(|e| format!("{e:?}"))?;
        let red: &[f64] = bytemuck::cast_slice(&view[..]);
        Ok((red[0], red[total as usize..].to_vec()))
    }

    /// Gather a staged frame on the device into the fold's planes, compute its
    /// luma variance from `noise`, and fold it: equivalent to the CPU's
    /// `load_frame` + `luma_variance` + `add_frame_with_gain`. With
    /// `null_units` (from `BandMerge::note_external_null_frame`), the frame's
    /// probe, packed by [`Self::probe_submit`], is also added to the ensemble
    /// null: `BandMerge::add_null_windows`. A frame staged with carried
    /// channels gathers all twelve planes.
    pub fn add_staged(
        &mut self,
        merge: &mut BandMerge,
        frame: &Staged,
        noise: GreenNoise,
        frame_beta: Option<&[f32]>,
        null_units: Option<&[Option<f32>]>,
    ) -> Result<(), String> {
        self.add_staged_impl(merge, frame, noise, frame_beta, null_units, false)
            .map(|_| ())
    }

    /// [`Self::add_staged`], also copying level 0's green luma (before the
    /// fold decomposes it) to a host buffer: [`Self::luma_collect`] waits for
    /// it alone, so the caller collects it a frame later without stalling.
    pub fn add_staged_keeping_luma(
        &mut self,
        merge: &mut BandMerge,
        frame: &Staged,
        noise: GreenNoise,
        frame_beta: Option<&[f32]>,
        null_units: Option<&[Option<f32>]>,
    ) -> Result<PendingLuma, String> {
        self.add_staged_impl(merge, frame, noise, frame_beta, null_units, true)
            .map(|p| p.expect("luma kept"))
    }

    fn add_staged_impl(
        &mut self,
        merge: &mut BandMerge,
        frame: &Staged,
        noise: GreenNoise,
        frame_beta: Option<&[f32]>,
        null_units: Option<&[Option<f32>]>,
        keep_luma: bool,
    ) -> Result<Option<PendingLuma>, String> {
        self.check_staged(frame)?;
        let sites = if frame.carried { PULLS } else { SITES.len() };
        if self.layout.planes != sites {
            return Err(format!(
                "GPU preparation: {sites} gathered planes for a {}-plane fold",
                self.layout.planes
            ));
        }
        if self.pending_reset[self.target] {
            self.reset_accumulators();
        }
        let scalars: Vec<LevelScalars> = merge.level_scalars(frame_beta);
        let base = self.raw_base(frame.slot);
        let l = &self.layout;
        let dst: Vec<u32> = (0..sites).map(|c| l.plane_lv[c][0]).collect();
        let all: Vec<usize> = (0..sites).collect();
        let mut rec = Recorder { calls: Vec::new() };
        self.record_gather(&mut rec, frame, base, frame.slot, &all, &dst, false);
        self.record_fold(&mut rec, &scalars, Some(noise), keep_luma);
        for (region, unit) in l.null.iter().zip(null_units.unwrap_or(&[])) {
            let (Some(region), Some(unit)) = (region, unit) else {
                continue;
            };
            let n = region.rect[2] * region.rect[3];
            rec.push(
                Kernel::NullAccum,
                Params {
                    a: [
                        region.lv[frame.slot],
                        region.energy[frame.slot],
                        n as u32,
                        0,
                    ],
                    b: region.acc,
                    f: [*unit, 0.0, 0.0, 0.0],
                    ..Default::default()
                },
                n,
            );
        }
        let pending = if keep_luma {
            // The luma itself, or its depth energies (`enable_depth`), and
            // then the luma when checking them.
            let luma_keep = l.luma_keep;
            let luma_n = self.layout.sizes[0].pixels();
            let (energies, n) = match self.depth {
                Some(plan) => {
                    let (at, cells) = self.record_depth(&mut rec, plan, luma_keep);
                    let n = cells + if plan.with_luma { luma_n } else { 0 };
                    (
                        Some((u64::from(at) * 4, cells as u64 * 4, plan.with_luma)),
                        n,
                    )
                }
                None => (None, luma_n),
            };
            let bytes = n as u64 * 4;
            let pooled = self
                .luma_pool
                .lock()
                .unwrap_or_else(|e| e.into_inner())
                .pop();
            let readback = pooled.unwrap_or_else(|| {
                self.device.create_buffer(&wgpu::BufferDescriptor {
                    label: Some("fold-luma-readback"),
                    size: bytes,
                    usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
                    mapped_at_creation: false,
                })
            });
            let luma_at = u64::from(luma_keep) * 4;
            let index = self.submit_with(rec, |encoder, fold| match energies {
                None => encoder.copy_buffer_to_buffer(&fold.work, luma_at, &readback, 0, bytes),
                Some((at, len, with_luma)) => {
                    encoder.copy_buffer_to_buffer(&fold.rgbw, at, &readback, 0, len);
                    if with_luma {
                        encoder.copy_buffer_to_buffer(
                            &fold.work,
                            luma_at,
                            &readback,
                            len,
                            luma_n as u64 * 4,
                        );
                    }
                }
            });
            readback
                .slice(..)
                .map_async(wgpu::MapMode::Read, |r| r.expect("map luma readback"));
            Some(PendingLuma { readback, index, n })
        } else {
            self.submit(rec);
            None
        };
        merge.note_external_frame();
        Ok(pending)
    }

    /// Read kept luma back as depth energies instead of the luma itself:
    /// [`Self::add_staged_keeping_luma`] then blurs level 0's luma twice on
    /// the device, separably and edge clamped, with `blurs[k] = (radius,
    /// taps)` (each output sums its taps in tap order from zero, as
    /// `axial_colour::blur_into`), and takes per `cell x cell` block the mean
    /// of the squared differences luma - blur 1 and blur 1 - blur 2 (f64
    /// sums in row-major order, as `cell_energy_of_difference`). The pending
    /// read-back then holds those two cell grids, band 0 then band 1, each
    /// `(w / cell) x (h / cell)` in row-major order, and with `with_luma` the
    /// luma itself after them (to check the energies against the CPU's).
    /// Only an 8-px cell, and only with device preparation (its
    /// full-resolution buffer is the scratch).
    pub fn enable_depth(
        &mut self,
        blurs: [(usize, &[f32]); 2],
        cell: usize,
        with_luma: bool,
    ) -> Result<(), String> {
        if cell != 8 {
            return Err("GPU depth energies: only an 8 px cell".into());
        }
        if self.full.is_none() {
            return Err("GPU depth energies need device preparation".into());
        }
        let s0 = self.layout.sizes[0];
        let n = s0.pixels();
        let cells = (s0.width / cell, s0.height / cell);
        let need = 3 * n + 2 * cells.0 * cells.1;
        if need > self.layout.rgb_len as usize {
            return Err("GPU depth energies: no room in the full-resolution buffer".into());
        }
        let mut taps: Vec<f64> = Vec::new();
        let mut plan = [(0u32, 0u32, 0u32); 2];
        for (k, (r, t)) in blurs.iter().enumerate() {
            if t.len() != 2 * r + 1 {
                return Err("GPU depth energies: a blur's taps do not match its radius".into());
            }
            plan[k] = (*r as u32, t.len() as u32, taps.len() as u32);
            taps.extend(t.iter().map(|&v| f64::from(v)));
        }
        if taps.len() > DEPTH_TAPS_MAX {
            return Err("GPU depth energies: too many taps".into());
        }
        self.queue
            .write_buffer(&self.consts, 91 * 8, bytemuck::cast_slice(&taps));
        self.depth = Some(DepthPlan {
            blurs: plan,
            cells: (cells.0 as u32, cells.1 as u32),
            with_luma,
        });
        Ok(())
    }

    /// Record the depth energies of the luma kept at `luma` (work arena) into
    /// the full-resolution buffer; returns where the two cell grids start
    /// there and how many floats they take.
    fn record_depth(&self, rec: &mut Recorder, plan: DepthPlan, luma: u32) -> (u32, usize) {
        let s0 = self.layout.sizes[0];
        let (w, h) = (s0.width as u32, s0.height as u32);
        let n = s0.pixels() as u32;
        let (tmp, g1, g2, e) = (0u32, n, 2 * n, 3 * n);
        let cells = (plan.cells.0 * plan.cells.1) as usize;
        let blur = |rec: &mut Recorder, src: u32, src_rgbw: bool, dst: u32, k: usize| {
            let (r, taps, first) = plan.blurs[k];
            rec.push(
                Kernel::DgBlurH,
                Params {
                    a: [src, w, h, tmp],
                    b: [r, taps, first, u32::from(src_rgbw)],
                    ..Default::default()
                },
                n as usize,
            );
            rec.push(
                Kernel::DgBlurV,
                Params {
                    a: [tmp, w, h, dst],
                    b: [r, taps, first, 0],
                    ..Default::default()
                },
                n as usize,
            );
        };
        blur(rec, luma, false, g1, 0);
        blur(rec, g1, true, g2, 1);
        for (k, (a, a_rgbw, b)) in [(luma, false, g1), (g1, true, g2)].into_iter().enumerate() {
            rec.push(
                Kernel::DgEnergy,
                Params {
                    a: [a, b, w, e + (k * cells) as u32],
                    b: [plan.cells.0, plan.cells.1, u32::from(a_rgbw), 0],
                    ..Default::default()
                },
                cells,
            );
        }
        (e, 2 * cells)
    }

    /// Wait for one frame's kept luma (not for later work) and read it.
    pub fn luma_collect(&mut self, pending: PendingLuma) -> Result<Vec<f32>, String> {
        self.luma_handoff(pending).read()
    }

    /// One frame's kept luma, to be waited for and read on another thread
    /// ([`LumaReadback::read`]): the fold's own thread then only submits.
    pub fn luma_handoff(&self, pending: PendingLuma) -> LumaReadback {
        LumaReadback {
            device: self.device.clone(),
            pending,
            pool: std::sync::Arc::clone(&self.luma_pool),
        }
    }

    /// [`Self::stage`] then [`Self::add_staged`].
    pub fn add_raw_frame(
        &mut self,
        merge: &mut BandMerge,
        frame: &RawFrame<'_>,
        noise: GreenNoise,
        frame_beta: Option<&[f32]>,
    ) -> Result<(), String> {
        let staged = self.stage(frame)?;
        self.add_staged(merge, &staged, noise, frame_beta, None)
    }
    /// Write the chunk's accumulators into `merge` (whose own accumulators
    /// must be freshly reset) and reset the device's for the next chunk.
    ///
    /// Read back through one reusable 64 MB host buffer, piece by piece: the
    /// accumulators are over a gigabyte at 33 MP, and a host-visible copy of
    /// all of them at once was that much more peak memory beside the CPU
    /// merge being written.
    /// Wait until the device has run everything submitted so far (for
    /// timing: the readback waits for it anyway).
    pub fn wait_idle(&self) {
        let _ = self.device.poll(wgpu::PollType::Wait {
            submission_index: None,
            timeout: None,
        });
    }

    pub fn finish_chunk(&mut self, merge: &mut BandMerge) {
        self.read_chunk(merge, None);
    }

    /// Absorb the chunk's accumulators into `merge`, which holds earlier
    /// chunks, exactly as `merge.absorb(&chunk)` would with the chunk read
    /// back ([`BandMerge::EXTERNAL_ABSORB`]), and reset the device's. No
    /// second host merge is needed for the chunk; the caller moves its frame
    /// counts, and the null windows the device does not hold
    /// ([`Self::null_levels`]), with [`BandMerge::absorb_external_remainder`].
    pub fn absorb_chunk(&mut self, merge: &mut BandMerge) {
        self.read_chunk(merge, Some(BandMerge::EXTERNAL_ABSORB));
    }

    /// Per level, whether the device accumulates the ensemble null's window.
    /// Only with preparation on the device; otherwise the host's
    /// `add_null_frame` does, into the counting merge.
    pub fn null_levels(&self) -> Vec<bool> {
        self.layout.null.iter().map(Option::is_some).collect()
    }

    /// Read the accumulators back into `merge`: copied, or combined by `ops`.
    fn read_chunk(&mut self, merge: &mut BandMerge, ops: Option<FoldCombine>) {
        let l = &self.layout;
        // (bank, offset within the bank, destination, combination)
        type Region<'a> = (usize, usize, &'a mut [f32], Option<Combine>);
        let mut regions: Vec<Region<'_>> = Vec::new();
        let (t, null) = merge.all_totals_mut();
        let op = |pick: fn(&FoldCombine) -> Combine| ops.as_ref().map(pick);
        fn add<'a>(
            regions: &mut Vec<Region<'a>>,
            dst: &'a mut [Vec<f32>],
            at: &[u32],
            op: Option<Combine>,
        ) {
            for (d, &o) in dst.iter_mut().zip(at) {
                let (bank, o) = acc_bank(o);
                regions.push((bank, o, &mut d[..], op));
            }
        }
        add(&mut regions, t.num, &l.num, op(|c| c.num));
        add(&mut regions, t.usum, &l.usum, op(|c| c.usum));
        add(&mut regions, t.den, &l.den, op(|c| c.den));
        if self.ensemble {
            add(&mut regions, t.zmax, &l.zmax, op(|c| c.zmax));
            add(&mut regions, t.zsum, &l.zsum, op(|c| c.zsum));
            add(&mut regions, t.lsum, &l.lsum, op(|c| c.lsum));
            add(&mut regions, t.esum, &l.esum, op(|c| c.esum));
        }
        if self.hull {
            add(&mut regions, t.lo, &l.lo, op(|c| c.lo));
            add(&mut regions, t.hi, &l.hi, op(|c| c.hi));
        }
        // The ensemble null's windows, accumulated by `null_accum`. Only
        // levels the device holds a window for: the CPU has the same ones.
        for (totals, region) in null.into_iter().zip(&l.null) {
            if let (Some(totals), Some(region)) = (totals, region) {
                for (i, (dst, &o)) in totals.into_iter().zip(&region.acc).enumerate() {
                    let (bank, o) = acc_bank(o);
                    regions.push((bank, o, dst, ops.map(|c| c.null[i])));
                }
            }
        }
        assert!(
            regions.iter().all(|r| !r.2.is_empty()),
            "reading a chunk back into released totals"
        );
        regions.sort_by_key(|r| (r.0, r.1));
        const PIECE: usize = 16 << 20; // floats: 64 MB
        // Pieces in flight: while the host copies one piece out, the device
        // copies the next ones into their own buffers. Each piece is still
        // read exactly once into the same destinations, so the totals are
        // the same bytes as one piece at a time.
        const IN_FLIGHT: usize = 4;
        let largest = l.acc_len.iter().copied().max().unwrap_or(0) as usize;
        let piece = PIECE.min(largest.max(1));
        let pieces: Vec<(usize, usize, usize)> = l
            .acc_len
            .iter()
            .enumerate()
            .flat_map(|(bank, &len)| {
                let total = len as usize;
                (0..total.div_ceil(piece))
                    .map(move |k| (bank, k * piece, piece.min(total - k * piece)))
            })
            .collect();
        let buffers: Vec<wgpu::Buffer> = (0..IN_FLIGHT.min(pieces.len()))
            .map(|_| {
                self.device.create_buffer(&wgpu::BufferDescriptor {
                    label: Some("fold-readback"),
                    size: piece as u64 * 4,
                    usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
                    mapped_at_creation: false,
                })
            })
            .collect();
        let submit = |k: usize| -> wgpu::SubmissionIndex {
            let (bank, start, n) = pieces[k];
            let readback = &buffers[k % buffers.len()];
            let mut encoder = self
                .device
                .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                    label: Some("fold-readback"),
                });
            encoder.copy_buffer_to_buffer(
                &self.acc[self.target][bank],
                start as u64 * 4,
                readback,
                0,
                n as u64 * 4,
            );
            let index = self.queue.submit([encoder.finish()]);
            readback
                .slice(..n as u64 * 4)
                .map_async(wgpu::MapMode::Read, |r| r.expect("map fold readback"));
            index
        };
        let mut queued: std::collections::VecDeque<wgpu::SubmissionIndex> =
            (0..buffers.len()).map(submit).collect();
        for k in 0..pieces.len() {
            let (bank, start, n) = pieces[k];
            let index = queued.pop_front().expect("a queued readback piece");
            self.device
                .poll(wgpu::PollType::Wait {
                    submission_index: Some(index),
                    timeout: None,
                })
                .expect("GPU fold wait");
            let readback = &buffers[k % buffers.len()];
            let slice = readback.slice(..n as u64 * 4);
            {
                let view = slice.get_mapped_range().expect("mapped readback");
                let all: &[f32] = bytemuck::cast_slice(&view[..]);
                let end = start + n;
                // A piece usually lies in one or two destinations: split each
                // overlap into 1 MB runs so the copy (and the first touch of
                // freshly allocated totals) uses the whole pool. Every
                // combine is elementwise, so the split cannot change a value.
                const RUN: usize = 1 << 18;
                regions
                    .iter_mut()
                    .filter(|(b, o, d, _)| *b == bank && *o < end && *o + d.len() > start)
                    .for_each(|(_, o, d, op)| {
                        let from = start.max(*o);
                        let to = end.min(*o + d.len());
                        let (dst, src) =
                            (&mut d[from - *o..to - *o], &all[from - start..to - start]);
                        let op = *op;
                        dst.par_chunks_mut(RUN)
                            .zip(src.par_chunks(RUN))
                            .for_each(|(dst, src)| match op {
                                None => dst.copy_from_slice(src),
                                Some(op) => op.apply(dst, src),
                            });
                    });
            }
            readback.unmap();
            if k + buffers.len() < pieces.len() {
                queued.push_back(submit(k + buffers.len()));
            }
        }
        self.pending_reset[self.target] = true;
    }
}
