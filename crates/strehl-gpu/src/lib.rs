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
use std::borrow::Cow;

use rayon::prelude::*;
use strehl_core::portable_math::{
    COS_SERIES, EXP_SERIES, LN_SERIES, LN_UNIFORM_FLOOR, LN64_SERIES, PIO2_HI, PIO2_LO, SIN_SERIES,
};
use strehl_core::pyramid::{BandMerge, BaseBand, Combine, FoldCombine, LevelScalars, LevelSize};
use wgpu::util::DeviceExt;

pub mod strict;

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
    /// device prepares frames.
    rgb: u32,
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
    acc_len: u64,
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
        let (rgb, probe_lv) = match full {
            Some((gw, gh)) => (take(3 * 4 * gw * gh), pyramid(&mut take)),
            None => (0, Vec::new()),
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
        let mut acc = 0u64;
        let mut put = |n: usize| {
            let at = acc as u32;
            acc += n as u64;
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
            rgb,
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
            acc_len: acc,
        }
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

    fn accum(&mut self, l: &Layout, weight: u32, k: usize) {
        let mut b = [0u32; 4];
        let mut c = [0u32; 4];
        let mut d = [0u32; 4];
        for p in 0..l.planes {
            b[p] = l.plane_lv[p][k];
            c[p] = l.num[k * l.planes + p];
            d[p] = l.usum[k * l.planes + p];
        }
        self.push(
            Kernel::Accum,
            Params {
                a: [
                    weight,
                    l.den[k],
                    l.sizes[k].pixels() as u32,
                    l.planes as u32,
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

/// The device, its pipelines, and one stack geometry's buffers.
pub struct GpuFold {
    /// Per-dispatch timing (`STREHL_GPU_PROFILE`), diagnostic only.
    profile: Option<Profile>,
    device: wgpu::Device,
    queue: wgpu::Queue,
    pipelines: Vec<wgpu::ComputePipeline>,
    bind: Vec<wgpu::BindGroup>,
    params: Vec<wgpu::Buffer>,
    param_stride: u64,
    work: wgpu::Buffer,
    acc: wgpu::Buffer,
    bgl: wgpu::BindGroupLayout,
    consts: wgpu::Buffer,
    /// Raw u16 frames, main then probe, two samples per word.
    raw: wgpu::Buffer,
    raw_samples: u64,
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
    pending_reset: bool,
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

/// Raw buffer slots: two frame slots, then the probe's.
const RAW_SLOTS: usize = 3;
const PROBE_SLOT: usize = 2;

/// `xf` index of the probe noise's level, sigma and f32-screen margin.
const XF_NOISE: u64 = 64;

/// f64s in `xf`: two frame slots of four site pulls (8 each), then the probe
/// noise's level, sigma and f32-screen margin.
const XF_LEN: u64 = 67;

fn make_binds(
    device: &wgpu::Device,
    bgl: &wgpu::BindGroupLayout,
    params: &[wgpu::Buffer],
    [work, acc, consts, raw, xf, red]: [&wgpu::Buffer; 6],
) -> Vec<wgpu::BindGroup> {
    params
        .iter()
        .map(|pb| {
            let storage = [work, acc, consts, raw, xf, red];
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
}

/// A probe submitted by [`GpuFold::probe_submit`], read by
/// [`GpuFold::probe_collect`].
pub struct PendingProbe {
    readback: wgpu::Buffer,
    index: wgpu::SubmissionIndex,
    sums: usize,
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
        Self::build(merge, None)
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
        let mut fold = Self::build(merge, Some(full))?;
        fold.rect = rect;
        Ok(fold)
    }

    fn build(merge: &BandMerge, full: Option<(usize, usize)>) -> Result<Self, String> {
        if let Some(why) = merge.external_fold_refusal() {
            return Err(format!("GPU fold unavailable: {why}"));
        }
        let cfg = merge.config();
        let planes = merge.planes();
        if planes > 4 {
            return Err("GPU fold supports at most four planes".into());
        }
        let (words, decorated_results) = strict::compile(SHADER)?;
        let mut descriptor = wgpu::InstanceDescriptor::new_without_display_handle();
        descriptor.backends = wgpu::Backends::VULKAN;
        let instance = wgpu::Instance::new(descriptor);
        let adapter = pollster::block_on(instance.request_adapter(&wgpu::RequestAdapterOptions {
            power_preference: wgpu::PowerPreference::HighPerformance,
            force_fallback_adapter: false,
            compatible_surface: None,
            apply_limit_buckets: false,
        }))
        .map_err(|e| e.to_string())?;
        let info = adapter.get_info();
        if info.device_type != wgpu::DeviceType::DiscreteGpu {
            return Err(format!(
                "GPU fold requires a discrete GPU, got {}",
                info.name
            ));
        }
        let mut features = wgpu::Features::PASSTHROUGH_SHADERS | wgpu::Features::SHADER_F64;
        if !adapter.features().contains(features) {
            return Err("GPU fold requires Vulkan passthrough shaders and f64".into());
        }
        let profiling = std::env::var_os(PROFILE_ENV).is_some()
            && adapter.features().contains(wgpu::Features::TIMESTAMP_QUERY);
        if profiling {
            features |= wgpu::Features::TIMESTAMP_QUERY;
        }
        let (device, queue) = pollster::block_on(adapter.request_device(&wgpu::DeviceDescriptor {
            label: Some("strehl-gpu-fold"),
            required_features: features,
            required_limits: adapter.limits(),
            experimental_features: wgpu::ExperimentalFeatures::disabled(),
            memory_hints: wgpu::MemoryHints::Performance,
            trace: wgpu::Trace::Off,
        }))
        .map_err(|e| e.to_string())?;
        let limits = device.limits();

        let ensemble = cfg.ensemble;
        let hull = cfg.hull.bounds();
        // The null's windows without the smoothing reach: the device smooths
        // whole levels, so it needs only the windows themselves.
        let null_rects: Vec<Option<[usize; 4]>> = merge
            .null_window_rects()
            .into_iter()
            .map(|r| r.map(|[x, y, w, h]| [x + 2, y + 2, w - 4, h - 4]))
            .collect();
        let layout = Layout::new(merge.sizes(), planes, ensemble, hull, full, &null_rects);
        let (work_bytes, acc_bytes) = (layout.work_len * 4, layout.acc_len * 4);
        for (name, bytes) in [("workspace", work_bytes), ("accumulators", acc_bytes)] {
            if bytes > limits.max_storage_buffer_binding_size || bytes > limits.max_buffer_size {
                return Err(format!(
                    "GPU fold {name} needs {bytes} bytes, above this device's {} byte binding limit",
                    limits.max_storage_buffer_binding_size
                ));
            }
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
        let acc = storage("fold-acc", acc_bytes);
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
        let consts = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("fold-consts"),
            contents: bytemuck::cast_slice(&consts),
            usage: wgpu::BufferUsages::STORAGE,
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
        let entry = |binding, ty| wgpu::BindGroupLayoutEntry {
            binding,
            visibility: wgpu::ShaderStages::COMPUTE,
            ty: wgpu::BindingType::Buffer {
                ty,
                has_dynamic_offset: binding == 0,
                min_binding_size: None,
            },
            count: None,
        };
        let bgl = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("fold-layout"),
            entries: &[
                entry(0, wgpu::BufferBindingType::Uniform),
                entry(1, wgpu::BufferBindingType::Storage { read_only: false }),
                entry(2, wgpu::BufferBindingType::Storage { read_only: false }),
                entry(3, wgpu::BufferBindingType::Storage { read_only: true }),
                entry(4, wgpu::BufferBindingType::Storage { read_only: false }),
                entry(5, wgpu::BufferBindingType::Storage { read_only: true }),
                entry(6, wgpu::BufferBindingType::Storage { read_only: false }),
            ],
        });
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
        let bind = make_binds(
            &device,
            &bgl,
            &params,
            [&work, &acc, &consts, &raw, &xf, &red],
        );
        let pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
            label: Some("fold-pipeline-layout"),
            bind_group_layouts: &[Some(&bgl)],
            immediate_size: 0,
        });
        // SAFETY: the words are this crate's own embedded shader, validated by
        // naga and altered only by added NoContraction decorations (`strict`).
        // Passthrough is required because naga's SPIR-V frontend drops them.
        let module = unsafe {
            device.create_shader_module_passthrough(wgpu::ShaderModuleDescriptorPassthrough {
                label: Some("strehl-fold"),
                spirv: Some(Cow::Borrowed(&words)),
                entry_points: Cow::Owned(
                    strict::ENTRY_POINTS
                        .iter()
                        .map(|name| wgpu::PassthroughShaderEntryPoint {
                            name: Cow::Borrowed(*name),
                            workgroup_size: (WG, 1, 1),
                        })
                        .collect(),
                ),
                ..Default::default()
            })
        };
        let pipelines = strict::ENTRY_POINTS
            .iter()
            .map(|name| {
                device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
                    label: Some(name),
                    layout: Some(&pipeline_layout),
                    module: &module,
                    entry_point: Some(name),
                    compilation_options: Default::default(),
                    cache: None,
                })
            })
            .collect();
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
            acc,
            bgl,
            consts,
            raw,
            raw_samples: 0,
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
            pending_reset: true,
            adapter: info.name,
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
        (self.layout.work_len + self.layout.acc_len) * 4
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
                    &self.bind[slot],
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
                    &self.bind[slot],
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
        rec.fill(0, self.layout.acc_len as usize, 0.0, true);
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
        self.pending_reset = false;
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
        if self.pending_reset {
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
        self.record_fold(&mut rec, &scalars, None);
        self.submit(rec);
        merge.note_external_frame();
    }

    /// The fold's dispatches for planes already at `plane_lv[c][0]`; with
    /// `noise`, the luma variance is computed here rather than uploaded.
    fn record_fold(&self, rec: &mut Recorder, scalars: &[LevelScalars], noise: Option<GreenNoise>) {
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
    fn ensure_raw(&mut self, samples: usize) {
        let samples = samples as u64 + (samples as u64 & 1);
        if self.raw_samples == samples {
            return;
        }
        self.raw = self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("fold-raw"),
            size: samples * 2 * RAW_SLOTS as u64,
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
                    size: samples * 2,
                    usage: wgpu::BufferUsages::MAP_WRITE | wgpu::BufferUsages::COPY_SRC,
                    mapped_at_creation: true,
                }),
                copy: None,
                mapped: std::sync::Arc::new(std::sync::atomic::AtomicBool::new(true)),
            })
            .collect();
        self.bind = make_binds(
            &self.device,
            &self.bgl,
            &self.params,
            [
                &self.work,
                &self.acc,
                &self.consts,
                &self.raw,
                &self.xf,
                &self.red,
            ],
        );
    }

    /// The first sample of `slot`'s frame in the raw buffer.
    fn raw_base(&self, slot: usize) -> u32 {
        (slot as u64 * self.raw_samples) as u32
    }

    /// Upload `frame` into the next frame slot and its pulls into that slot's
    /// `xf` sites. wgpu copies the samples before this returns, so the caller
    /// may free the frame at once. The slot stays valid until the second
    /// `stage` after this one.
    pub fn stage(&mut self, frame: &RawFrame<'_>) -> Result<Staged, String> {
        let (gw, gh) = self.full.ok_or("GPU preparation layout")?;
        let (width, rows) = (2 * gw, 2 * gh);
        let padded = frame.data.len() as u64 + (frame.data.len() as u64 & 1);
        if frame.stride < frame.active[0] + width
            || frame.data.len() < (frame.active[1] + rows) * frame.stride
            || (width * rows) as u64 + 2 > u64::from(u32::MAX)
            || RAW_SLOTS as u64 * padded > u64::from(u32::MAX)
        {
            return Err("GPU preparation: frame geometry out of range".into());
        }
        self.ensure_raw(frame.data.len());
        let slot = self.next_slot;
        self.next_slot ^= 1;
        let base = u64::from(self.raw_base(slot)) * 2;
        // Through this slot's persistently mapped upload buffer: wait for its
        // last copy out (two frames ago) and the re-map, fill it in parallel
        // chunks, then copy it to the device. No staging memory is allocated
        // per frame. An odd trailing sample is padded to a whole word.
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
        let bytes: &[u8] = bytemuck::cast_slice(frame.data);
        // Mapped ranges start 8-byte aligned and span whole words, so chunks
        // are fixed-size over the (word-padded) buffer and the last one carries
        // the zero padding.
        const UPLOAD_CHUNK: usize = 1 << 22;
        let size = (self.raw_samples * 2) as usize;
        let buffer = &up.buffer;
        (0..size.div_ceil(UPLOAD_CHUNK))
            .into_par_iter()
            .for_each(|i| {
                let (at, end) = (i * UPLOAD_CHUNK, ((i + 1) * UPLOAD_CHUNK).min(size));
                let data = &bytes[at.min(bytes.len())..end.min(bytes.len())];
                let mut view = buffer
                    .slice(at as u64..end as u64)
                    .get_mapped_range_mut()
                    .expect("mapped upload buffer");
                view.slice(..data.len()).copy_from_slice(data);
                if data.len() < end - at {
                    view.slice(data.len()..)
                        .copy_from_slice(&vec![0u8; end - at - data.len()]);
                }
            });
        let size = size as u64;
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
            let mut xf = [0f64; 32];
            for (i, (&(dx, dy), t)) in SITES.iter().zip(pulls.iter()).enumerate() {
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
            self.queue
                .write_buffer(&self.xf, (slot * 32 * 8) as u64, bytemuck::cast_slice(&xf));
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
    /// level-0 planes.
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
        let raw_base = base + (frame.active[1] * frame.stride + frame.active[0]) as u32;
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
        rec.push(
            Kernel::Mhc,
            Params {
                a: [l.rgb, fw as u32, fh as u32, u32::from(green_only)],
                b: [raw_base, frame.stride as u32, 0, 0],
                f: [black, frame.gain[0], frame.gain[1], frame.gain[2]],
                ..Default::default()
            },
            // One invocation per 2x2 quad.
            gw * gh,
        );
        for (&s, &d) in sites.iter().zip(dst) {
            let (dx, dy) = SITES[s];
            let ci = site_channel(dx, dy);
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
                    c: [u32::from(black_dn), (4 * pulls + s) as u32, 0, 0],
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
        if self.raw_samples * 2 * (RAW_SLOTS as u64) < words * 4 {
            self.ensure_raw((words * 2) as usize);
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
    /// null: `BandMerge::add_null_windows`.
    pub fn add_staged(
        &mut self,
        merge: &mut BandMerge,
        frame: &Staged,
        noise: GreenNoise,
        frame_beta: Option<&[f32]>,
        null_units: Option<&[Option<f32>]>,
    ) -> Result<(), String> {
        self.check_staged(frame)?;
        if self.pending_reset {
            self.reset_accumulators();
        }
        let scalars: Vec<LevelScalars> = merge.level_scalars(frame_beta);
        let base = self.raw_base(frame.slot);
        let l = &self.layout;
        let dst: Vec<u32> = (0..4).map(|c| l.plane_lv[c][0]).collect();
        let mut rec = Recorder { calls: Vec::new() };
        self.record_gather(
            &mut rec,
            frame,
            base,
            frame.slot,
            &[0, 1, 2, 3],
            &dst,
            false,
        );
        self.record_fold(&mut rec, &scalars, Some(noise));
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
        self.submit(rec);
        merge.note_external_frame();
        Ok(())
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
        type Region<'a> = (usize, &'a mut [f32], Option<Combine>);
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
                regions.push((o as usize, &mut d[..], op));
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
                    regions.push((o as usize, dst, ops.map(|c| c.null[i])));
                }
            }
        }
        assert!(
            regions.iter().all(|r| !r.1.is_empty()),
            "reading a chunk back into released totals"
        );
        regions.sort_by_key(|r| r.0);
        const PIECE: usize = 16 << 20; // floats: 64 MB
        let total = l.acc_len as usize;
        let piece = PIECE.min(total.max(1));
        let readback = self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("fold-readback"),
            size: piece as u64 * 4,
            usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        let mut start = 0usize;
        while start < total {
            let n = piece.min(total - start);
            let mut encoder = self
                .device
                .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                    label: Some("fold-readback"),
                });
            encoder.copy_buffer_to_buffer(&self.acc, start as u64 * 4, &readback, 0, n as u64 * 4);
            let index = self.queue.submit([encoder.finish()]);
            let slice = readback.slice(..n as u64 * 4);
            slice.map_async(wgpu::MapMode::Read, |r| r.expect("map fold readback"));
            self.device
                .poll(wgpu::PollType::Wait {
                    submission_index: Some(index),
                    timeout: None,
                })
                .expect("GPU fold wait");
            {
                let view = slice.get_mapped_range().expect("mapped readback");
                let all: &[f32] = bytemuck::cast_slice(&view[..]);
                let end = start + n;
                regions
                    .par_iter_mut()
                    .filter(|(o, d, _)| *o < end && *o + d.len() > start)
                    .for_each(|(o, d, op)| {
                        let from = start.max(*o);
                        let to = end.min(*o + d.len());
                        let (dst, src) =
                            (&mut d[from - *o..to - *o], &all[from - start..to - start]);
                        match op {
                            None => dst.copy_from_slice(src),
                            Some(op) => op.apply(dst, src),
                        }
                    });
            }
            readback.unmap();
            start += n;
        }
        self.pending_reset = true;
    }
}
