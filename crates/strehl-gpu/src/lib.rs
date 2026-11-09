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
use strehl_core::pyramid::{BandMerge, BaseBand, LevelScalars, LevelSize};
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
    Pack,
}

impl Kernel {
    fn index(self) -> usize {
        self as usize
    }
}

/// Offsets, in f32 elements, of every region in the two arenas.
struct Layout {
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
    acc_len: u64,
}

impl Layout {
    fn new(
        sizes: &[LevelSize],
        planes: usize,
        ensemble: bool,
        hull: bool,
        full: Option<(usize, usize)>,
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
        Self {
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
    /// The frame whose samples are resident in slot 0 because [`Self::probe`]
    /// uploaded them for the [`Self::add_raw_frame`] that must follow: the
    /// buffer address and length, checked there.
    staged: Option<(usize, usize)>,
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
        }
    }
}

/// Maximum dispatches one frame records; sizes the parameter buffers.
const MAX_CALLS: usize = 1024;

/// Values per partial sum in the probe's exact mean.
const SUM_CHUNK: usize = 4096;

/// f64s in `red`: the probe mean's partials and total, then one row sum per
/// interior row of every level (an upper bound) and the interiors' totals.
fn red_len(sizes: &[LevelSize]) -> u64 {
    let parts = sizes[0].pixels().div_ceil(SUM_CHUNK);
    let rows: usize = sizes.iter().map(|s| s.height).sum();
    (parts + 2 + rows + sizes.len() + 16) as u64
}

/// f64s in `xf`: two slots of four site pulls (8 each), then the probe
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

/// What [`GpuFold::probe`] reads back.
#[derive(Debug, Default)]
pub struct ProbeOutput {
    /// One f64 sum of squares per requested interior, in request order.
    pub sums: Vec<f64>,
    /// The requested windows, indexed by level, row-major.
    pub windows: Vec<Option<Vec<f32>>>,
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
        let layout = Layout::new(merge.sizes(), planes, ensemble, hull, full);
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
            staged: None,
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
        let mut out = format!("device time {:.1} ms\n", total * 1e-6);
        for (k, (n, ns)) in rows {
            out.push_str(&format!(
                "  {:<14} {:>6} dispatches {:>9.2} ms {:>5.1}%\n",
                strict::ENTRY_POINTS[k],
                n,
                ns * 1e-6,
                100.0 * ns / total
            ));
        }
        Some(out)
    }

    /// Bytes of device memory the fold holds.
    pub fn device_bytes(&self) -> u64 {
        (self.layout.work_len + self.layout.acc_len) * 4
    }

    fn submit(&mut self, rec: Recorder) {
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
        self.queue.submit([encoder.finish()]);
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
                for (i, (k, _, _)) in rec.calls.iter().enumerate() {
                    let ns = stamps[2 * i + 1].wrapping_sub(stamps[2 * i]) as f64 * prof.period_ns;
                    let t = &mut prof.totals[k.index()];
                    t.0 += 1;
                    t.1 += ns;
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

    /// Size the raw buffer for frames of `samples` u16 each (main + probe).
    fn ensure_raw(&mut self, samples: usize) {
        let samples = samples as u64 + (samples as u64 & 1);
        if self.raw_samples == samples {
            return;
        }
        self.raw = self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("fold-raw"),
            size: samples * 2 * 2,
            usage: wgpu::BufferUsages::STORAGE
                | wgpu::BufferUsages::COPY_DST
                | wgpu::BufferUsages::COPY_SRC,
            mapped_at_creation: false,
        });
        self.raw_samples = samples;
        self.staged = None;
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

    /// Upload a frame's samples into slot 0 and its pulls into `xf` slots 0
    /// and 1 (the probe gathers through the same pulls).
    fn upload_raw(&mut self, frame: &RawFrame<'_>) {
        self.ensure_raw(frame.data.len());
        // Whole words straight from the decoder's buffer, in parallel chunks:
        // wgpu stages each write in fresh host memory before taking its queue
        // lock, so the copies (and their page faults) run concurrently. An odd
        // trailing sample is written as its own padded word.
        let even = frame.data.len() & !1;
        const UPLOAD_CHUNK: usize = 1 << 21;
        let queue = &self.queue;
        let raw = &self.raw;
        frame.data[..even]
            .par_chunks(UPLOAD_CHUNK)
            .enumerate()
            .for_each(|(i, chunk)| {
                queue.write_buffer(
                    raw,
                    (i * UPLOAD_CHUNK * 2) as u64,
                    bytemuck::cast_slice(chunk),
                );
            });
        if even < frame.data.len() {
            let tail = [frame.data[even], 0u16];
            self.queue
                .write_buffer(&self.raw, even as u64 * 2, bytemuck::cast_slice(&tail));
        }
        let (gw, gh) = self.full.expect("preparation layout");
        let (cx, cy) = (gw as f64 * 0.5, gh as f64 * 0.5);
        if let Some(pulls) = frame.pulls {
            let mut xf = [0f64; 64];
            for (i, (&(dx, dy), t)) in SITES.iter().zip(pulls.iter()).enumerate() {
                let site = [
                    t.a[0],
                    t.a[1],
                    t.b[0],
                    t.b[1],
                    dx as f64 * 0.5,
                    dy as f64 * 0.5,
                    cx,
                    cy,
                ];
                xf[8 * i..8 * i + 8].copy_from_slice(&site);
                xf[32 + 8 * i..40 + 8 * i].copy_from_slice(&site);
            }
            self.queue
                .write_buffer(&self.xf, 0, bytemuck::cast_slice(&xf));
        }
    }

    /// The first sample of `slot`'s frame in the raw buffer.
    fn raw_base(&self, slot: usize) -> u32 {
        (slot as u64 * self.raw_samples) as u32
    }

    /// Record the gather (or unwarped extraction) of `sites` into the given
    /// level-0 planes.
    #[allow(clippy::too_many_arguments)]
    fn record_gather(
        &self,
        rec: &mut Recorder,
        frame: &RawFrame<'_>,
        base: u32,
        slot: usize,
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
        if frame.pulls.is_none() {
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
            fw * fh,
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
                    c: [u32::from(black_dn), (4 * slot + s) as u32, 0, 0],
                    f: [black, inv, 0.0, 0.0],
                    ..Default::default()
                },
                lw * lh,
            );
        }
    }

    /// The gate-floor probe on the device: build the probe frame from `frame`
    /// and `noise` as `gatefloor` does (a copy of the frame with its active
    /// complete quads replaced by seeded noise), gather its greens, form and
    /// zero-mean its luma and build its Laplacian pyramid. Returns, from that
    /// pyramid, the f64 sum of squares over each `[level, x, y, w, h]` of
    /// `sums` (each row in column order, then the rows in order:
    /// `gatefloor::square_sum`), and each requested `[x, y, w, h]` window of
    /// `windows` (indexed by level), row-major. Only these cross PCIe.
    ///
    /// Uploads `frame`, which stays resident for the [`Self::add_raw_frame`]
    /// of the same frame that must follow. Requires an integral black level:
    /// the luma's f64 sum is then exact in any order, which is what lets the
    /// device reproduce the CPU's mean.
    pub fn probe(
        &mut self,
        frame: &RawFrame<'_>,
        noise: ProbeNoise,
        sums: &[[usize; 5]],
        windows: &[Option<[usize; 4]>],
    ) -> Result<ProbeOutput, String> {
        self.staged = None;
        let sizes = &self.layout.sizes;
        let fits = |k: usize, [x, y, w, h]: [usize; 4]| {
            k < sizes.len() && x + w <= sizes[k].width && y + h <= sizes[k].height
        };
        if !sums.iter().all(|&[k, x, y, w, h]| fits(k, [x, y, w, h]))
            || !windows
                .iter()
                .enumerate()
                .all(|(k, r)| r.is_none_or(|r| fits(k, r)))
        {
            return Err("GPU probe: a requested rectangle is outside its level".into());
        }
        if frame.black.fract() != 0.0 {
            return Err("GPU probe needs an integral black level".into());
        }
        if frame.pulls.is_none() {
            return Err("the probe is only measured for a warped frame".into());
        }
        let (gw, gh) = self.full.expect("preparation layout");
        let (width, rows) = (2 * gw, 2 * gh);
        let words = frame.data.len().div_ceil(2);
        if frame.stride < frame.active[0] + width
            || frame.data.len() < (frame.active[1] + rows) * frame.stride
            || (width * rows) as u64 + 2 > u64::from(u32::MAX)
            || 2 * (words as u64 * 2) > u64::from(u32::MAX)
        {
            return Err("GPU probe: frame geometry out of range".into());
        }
        self.upload_raw(frame);
        self.staged = Some((frame.data.as_ptr() as usize, frame.data.len()));
        self.queue.write_buffer(
            &self.xf,
            64 * 8,
            bytemuck::cast_slice(&[
                noise.level,
                noise.sigma,
                strehl_core::portable_math::probe_f32_margin(noise.sigma),
            ]),
        );
        let base = self.raw_base(1);
        let mut rec = Recorder { calls: Vec::new() };
        rec.push(
            Kernel::Noise,
            Params {
                a: [words as u32, base / 2, frame.stride as u32, width as u32],
                b: [
                    frame.active[0] as u32,
                    frame.active[1] as u32,
                    rows as u32,
                    0,
                ],
                c: [noise.seed as u32, (noise.seed >> 32) as u32, 0, 0],
                ..Default::default()
            },
            words,
        );
        let l = &self.layout;
        let n0 = l.sizes[0].pixels();
        // Greens into the planes' level-0 slots, which the main frame's gather
        // overwrites only after this download.
        self.record_gather(
            &mut rec,
            frame,
            base,
            1,
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
        let parts = n0.div_ceil(SUM_CHUNK);
        rec.push(
            Kernel::Sum64,
            Params {
                a: [l.probe_lv[0], n0 as u32, 1, SUM_CHUNK as u32],
                ..Default::default()
            },
            parts,
        );
        rec.push(
            Kernel::Sum64Finish,
            Params {
                a: [1, parts as u32, 0, 0],
                ..Default::default()
            },
            1,
        );
        rec.push(
            Kernel::Demean,
            Params {
                a: [l.probe_lv[0], n0 as u32, 0, 0],
                ..Default::default()
            },
            n0,
        );
        rec.laplacian(l.scratch, &l.sizes, &l.probe_lv);
        // Interior sums: row sums, then each interior's rows in order.
        let mut row = (parts + 2) as u32;
        let total = row + sums.iter().map(|s| s[4] as u32).sum::<u32>();
        for (i, &[k, x, y, w, h]) in sums.iter().enumerate() {
            let width = l.sizes[k].width as u32;
            rec.push(
                Kernel::RowSq,
                Params {
                    a: [l.probe_lv[k], width, x as u32, w as u32],
                    b: [y as u32, h as u32, row, 0],
                    ..Default::default()
                },
                h,
            );
            rec.push(
                Kernel::Sum64Finish,
                Params {
                    a: [row, h as u32, total + i as u32, 0],
                    ..Default::default()
                },
                1,
            );
            row += h as u32;
        }
        // Windows packed into the scratch region, free once the pyramid is built.
        let mut packed = 0usize;
        for (k, r) in windows.iter().enumerate() {
            if let Some([x, y, w, h]) = *r {
                rec.push(
                    Kernel::Pack,
                    Params {
                        a: [l.probe_lv[k], l.sizes[k].width as u32, x as u32, w as u32],
                        b: [y as u32, h as u32, l.scratch + packed as u32, 0],
                        ..Default::default()
                    },
                    w * h,
                );
                packed += w * h;
            }
        }
        let scratch = l.scratch;
        self.submit(rec);
        self.download(
            scratch,
            packed,
            u64::from(total),
            sums.len(),
            |floats, totals| {
                let mut at = 0;
                let windows = windows
                    .iter()
                    .map(|r| {
                        r.map(|[_, _, w, h]| {
                            let v = floats[at..at + w * h].to_vec();
                            at += w * h;
                            v
                        })
                    })
                    .collect();
                ProbeOutput {
                    sums: totals.to_vec(),
                    windows,
                }
            },
        )
    }

    /// The probe frame [`Self::probe`] builds on the device, read back: for
    /// testing the noise fill against the CPU's.
    #[doc(hidden)]
    pub fn probe_frame(
        &mut self,
        frame: &RawFrame<'_>,
        noise: ProbeNoise,
    ) -> Result<Vec<u16>, String> {
        self.probe(frame, noise, &[], &[])?;
        self.staged = None;
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
        encoder.copy_buffer_to_buffer(&self.raw, self.raw_samples * 2, &readback, 0, bytes);
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

    /// Gather `frame` on the device into the fold's planes, compute its luma
    /// variance from `noise`, and fold it: equivalent to the CPU's
    /// `load_frame` + `luma_variance` + `add_frame_with_gain`.
    pub fn add_raw_frame(
        &mut self,
        merge: &mut BandMerge,
        frame: &RawFrame<'_>,
        noise: GreenNoise,
        frame_beta: Option<&[f32]>,
    ) {
        if self.pending_reset {
            self.reset_accumulators();
        }
        let scalars: Vec<LevelScalars> = merge.level_scalars(frame_beta);
        // The probe already put this frame in slot 0; otherwise upload it.
        match self.staged.take() {
            Some(staged) => assert_eq!(
                staged,
                (frame.data.as_ptr() as usize, frame.data.len()),
                "add_raw_frame after a probe of a different frame"
            ),
            None => self.upload_raw(frame),
        }
        let base = self.raw_base(0);
        let l = &self.layout;
        let dst: Vec<u32> = (0..4).map(|c| l.plane_lv[c][0]).collect();
        let mut rec = Recorder { calls: Vec::new() };
        self.record_gather(&mut rec, frame, base, 0, &[0, 1, 2, 3], &dst, false);
        self.record_fold(&mut rec, &scalars, Some(noise));
        self.submit(rec);
        merge.note_external_frame();
    }

    /// Hand `count` f32 of the work arena from `at` and `sums` f64 of `red`
    /// from `red_at` to `read`, waiting for the device.
    fn download<T>(
        &self,
        at: u32,
        count: usize,
        red_at: u64,
        sums: usize,
        read: impl FnOnce(&[f32], &[f64]) -> T,
    ) -> Result<T, String> {
        let float_bytes = (count as u64 * 4).div_ceil(8) * 8;
        let bytes = float_bytes + sums as u64 * 8;
        let readback = self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("fold-probe-readback"),
            size: bytes.max(8),
            usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        let mut encoder = self
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                label: Some("probe-readback"),
            });
        if count > 0 {
            encoder.copy_buffer_to_buffer(
                &self.work,
                u64::from(at) * 4,
                &readback,
                0,
                count as u64 * 4,
            );
        }
        if sums > 0 {
            encoder.copy_buffer_to_buffer(
                &self.red,
                red_at * 8,
                &readback,
                float_bytes,
                sums as u64 * 8,
            );
        }
        self.queue.submit([encoder.finish()]);
        readback
            .slice(..)
            .map_async(wgpu::MapMode::Read, |r| r.expect("map probe readback"));
        self.device
            .poll(wgpu::PollType::wait_indefinitely())
            .map_err(|e| format!("GPU probe wait: {e:?}"))?;
        let out = {
            let view = readback
                .slice(..)
                .get_mapped_range()
                .map_err(|e| format!("mapped probe: {e:?}"))?;
            let floats: &[f32] = bytemuck::cast_slice(&view[..float_bytes as usize]);
            let totals: &[f64] = bytemuck::cast_slice(&view[float_bytes as usize..bytes as usize]);
            read(&floats[..count], totals)
        };
        readback.unmap();
        Ok(out)
    }

    /// Write the chunk's accumulators into `merge` (whose own accumulators
    /// must be freshly reset) and reset the device's for the next chunk.
    pub fn finish_chunk(&mut self, merge: &mut BandMerge) {
        let bytes = self.layout.acc_len * 4;
        let readback = self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("fold-readback"),
            size: bytes,
            usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        let mut encoder = self
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                label: Some("fold-readback"),
            });
        encoder.copy_buffer_to_buffer(&self.acc, 0, &readback, 0, bytes);
        self.queue.submit([encoder.finish()]);
        readback
            .slice(..)
            .map_async(wgpu::MapMode::Read, |r| r.expect("map fold readback"));
        self.device
            .poll(wgpu::PollType::wait_indefinitely())
            .expect("GPU fold wait");
        {
            let view = readback
                .slice(..)
                .get_mapped_range()
                .expect("mapped readback");
            let all: &[f32] = bytemuck::cast_slice(&view[..]);
            let l = &self.layout;
            let t = merge.totals_mut();
            let copy = |dst: &mut [Vec<f32>], at: &[u32]| {
                dst.par_iter_mut().zip(at.par_iter()).for_each(|(d, &o)| {
                    let (o, n) = (o as usize, d.len());
                    d.copy_from_slice(&all[o..o + n]);
                });
            };
            copy(t.num, &l.num);
            copy(t.usum, &l.usum);
            copy(t.den, &l.den);
            if self.ensemble {
                copy(t.zmax, &l.zmax);
                copy(t.zsum, &l.zsum);
                copy(t.lsum, &l.lsum);
                copy(t.esum, &l.esum);
            }
            if self.hull {
                copy(t.lo, &l.lo);
                copy(t.hi, &l.hi);
            }
        }
        readback.unmap();
        self.pending_reset = true;
    }
}
