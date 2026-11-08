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
use strehl_core::portable_math::{EXP_SERIES, LN_SERIES};
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
    fn new(sizes: &[LevelSize], planes: usize, ensemble: bool, hull: bool) -> Self {
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
    device: wgpu::Device,
    queue: wgpu::Queue,
    pipelines: Vec<wgpu::ComputePipeline>,
    bind: Vec<wgpu::BindGroup>,
    params: Vec<wgpu::Buffer>,
    param_stride: u64,
    work: wgpu::Buffer,
    acc: wgpu::Buffer,
    layout: Layout,
    base_weighted: bool,
    ensemble: bool,
    hull: bool,
    frame: usize,
    pending_reset: bool,
    pub adapter: String,
    pub decorated_results: usize,
}

/// Maximum dispatches one frame records; sizes the parameter buffers.
const MAX_CALLS: usize = 1024;

impl GpuFold {
    /// A fold for `merge`'s geometry and configuration, or why there is none.
    pub fn new(merge: &BandMerge) -> Result<Self, String> {
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
        let features = wgpu::Features::PASSTHROUGH_SHADERS | wgpu::Features::SHADER_F64;
        if !adapter.features().contains(features) {
            return Err("GPU fold requires Vulkan passthrough shaders and f64".into());
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
        let layout = Layout::new(merge.sizes(), planes, ensemble, hull);
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
            ],
        });
        let bind = params
            .iter()
            .map(|pb| {
                device.create_bind_group(&wgpu::BindGroupDescriptor {
                    label: Some("fold-bind"),
                    layout: &bgl,
                    entries: &[
                        wgpu::BindGroupEntry {
                            binding: 0,
                            resource: wgpu::BindingResource::Buffer(wgpu::BufferBinding {
                                buffer: pb,
                                offset: 0,
                                size: wgpu::BufferSize::new(std::mem::size_of::<Params>() as u64),
                            }),
                        },
                        wgpu::BindGroupEntry {
                            binding: 1,
                            resource: work.as_entire_binding(),
                        },
                        wgpu::BindGroupEntry {
                            binding: 2,
                            resource: acc.as_entire_binding(),
                        },
                        wgpu::BindGroupEntry {
                            binding: 3,
                            resource: consts.as_entire_binding(),
                        },
                    ],
                })
            })
            .collect();
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
        let mut fold = Self {
            device,
            queue,
            pipelines,
            bind,
            params,
            param_stride,
            work,
            acc,
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
        {
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

        let l = &self.layout;
        let sizes = &l.sizes;
        let nl = sizes.len();
        let nb = nl - 1;
        let mut rec = Recorder { calls: Vec::new() };
        // Luma from the raw greens, before the planes are decomposed in place.
        rec.push(
            Kernel::Luma,
            Params {
                a: [l.plane_lv[1][0], l.plane_lv[2][0], l.luma_lv[0], n0 as u32],
                ..Default::default()
            },
            n0,
        );
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
        self.submit(rec);
        merge.note_external_frame();
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
