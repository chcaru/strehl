//! The `wgpu` harness: buffers, pipelines, timestamps, and the timed variants.

use std::time::Instant;

use wgpu::util::DeviceExt;

use crate::cpu::PlaneGeometry;

pub const TILE_W: u32 = 32;
pub const TILE_H: u32 = 8;
/// Threads per 1-D dispatch (merge, reset, read, copy).
pub const LINEAR_WG: u32 = 256;

#[repr(C)]
#[derive(Clone, Copy, bytemuck::Pod, bytemuck::Zeroable)]
pub struct Params {
    pub plane_w: u32,
    pub plane_h: u32,
    pub row_words: u32,
    pub frame_index: u32,
    pub black: f32,
    pub gain: f32,
    pub read_noise_e: f32,
    pub sigma_eps: f32,
}

fn shader_source(inner_r: u32, outer_r: u32, inner_r2: u32, outer_r2: u32, exact_div: bool) -> String {
    let halo = outer_r.max(outer_r2);
    let sh_w = TILE_W + 2 * halo;
    let sh_h = TILE_H + 2 * halo;
    include_str!("../shaders/focus.wgsl")
        .replace("{{TILE_W}}", &TILE_W.to_string())
        .replace("{{TILE_H}}", &TILE_H.to_string())
        .replace("{{INNER_R}}", &inner_r.to_string())
        .replace("{{OUTER_R}}", &outer_r.to_string())
        .replace("{{INNER_R2}}", &inner_r2.to_string())
        .replace("{{OUTER_R2}}", &outer_r2.to_string())
        .replace("{{SH_W}}", &sh_w.to_string())
        .replace("{{SH_H}}", &sh_h.to_string())
        .replace("{{SH_N}}", &(sh_w * sh_h).to_string())
        .replace("{{HS_N}}", &(TILE_W * sh_h).to_string())
        .replace("{{EXACT_DIV}}", if exact_div { "true" } else { "false" })
}

pub struct Stats {
    pub n: usize,
    pub min: f64,
    pub median: f64,
    pub mean: f64,
    pub p95: f64,
    pub max: f64,
    pub sd: f64,
}

pub fn stats(v: &[f64]) -> Stats {
    let mut s = v.to_vec();
    s.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = s.len();
    let mean = s.iter().sum::<f64>() / n as f64;
    let var = if n > 1 {
        s.iter().map(|x| (x - mean) * (x - mean)).sum::<f64>() / (n - 1) as f64
    } else {
        0.0
    };
    Stats {
        n,
        min: s[0],
        median: s[n / 2],
        mean,
        p95: s[((n as f64 * 0.95) as usize).min(n - 1)],
        max: s[n - 1],
        sd: var.sqrt(),
    }
}

impl std::fmt::Display for Stats {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "n={:<3} min {:8.3}  med {:8.3}  mean {:8.3} +/- {:6.3}  p95 {:8.3}  max {:8.3}",
            self.n, self.min, self.median, self.mean, self.sd, self.p95, self.max
        )
    }
}

/// Total and per-process VRAM in MiB, straight from `nvidia-smi`.
pub fn vram_mib() -> (Option<u64>, Option<u64>) {
    let total = std::process::Command::new("nvidia-smi")
        .args(["--query-gpu=memory.used", "--format=csv,noheader,nounits"])
        .output()
        .ok()
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .and_then(|s| s.lines().next().and_then(|l| l.trim().parse::<u64>().ok()));
    let pid = std::process::id();
    let ours = std::process::Command::new("nvidia-smi")
        .args([
            "--query-compute-apps=pid,used_memory",
            "--format=csv,noheader,nounits",
        ])
        .output()
        .ok()
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .and_then(|s| {
            s.lines()
                .filter_map(|l| {
                    let mut it = l.split(',');
                    let p = it.next()?.trim().parse::<u32>().ok()?;
                    let m = it.next()?.trim().parse::<u64>().ok()?;
                    (p == pid).then_some(m)
                })
                .next()
        });
    (total, ours)
}

pub struct Gpu {
    pub device: wgpu::Device,
    pub queue: wgpu::Queue,
    pub adapter_name: String,
    pub backend: String,
    pub ts_period_ns: f32,
    pub layout: wgpu::BindGroupLayout,
    pub pipeline_layout: wgpu::PipelineLayout,
    /// Single-measure module: radii (1, 3), halo 3.
    pub m_a: wgpu::ShaderModule,
    /// Second-measure module: radii (2, 5), halo 5.
    pub m_b: wgpu::ShaderModule,
    /// Two-measure module: (1, 3) and (2, 5) in one tile, halo 5.
    pub m_f: wgpu::ShaderModule,
    /// Single-measure module with the raw fp32 divide, to price exactness.
    pub m_fast: wgpu::ShaderModule,
}

impl Gpu {
    pub fn new() -> Self {
        let instance = wgpu::Instance::new(wgpu::InstanceDescriptor::new_without_display_handle());
        let adapter = pollster::block_on(instance.request_adapter(&wgpu::RequestAdapterOptions {
            power_preference: wgpu::PowerPreference::HighPerformance,
            force_fallback_adapter: false,
            compatible_surface: None,
            apply_limit_buckets: false,
        }))
        .expect("no GPU adapter");
        let info = adapter.get_info();
        let limits = adapter.limits();
        let (device, queue) = pollster::block_on(adapter.request_device(&wgpu::DeviceDescriptor {
            label: Some("m7"),
            required_features: wgpu::Features::TIMESTAMP_QUERY
                | wgpu::Features::TIMESTAMP_QUERY_INSIDE_ENCODERS,
            required_limits: limits,
            experimental_features: wgpu::ExperimentalFeatures::disabled(),
            memory_hints: wgpu::MemoryHints::Performance,
            trace: wgpu::Trace::Off,
        }))
        .expect("no GPU device");
        device.on_uncaptured_error(std::sync::Arc::new(|e| panic!("wgpu error: {e}")));

        let storage = |ro: bool| wgpu::BindingType::Buffer {
            ty: wgpu::BufferBindingType::Storage { read_only: ro },
            has_dynamic_offset: false,
            min_binding_size: None,
        };
        let mut entries = vec![wgpu::BindGroupLayoutEntry {
            binding: 0,
            visibility: wgpu::ShaderStages::COMPUTE,
            ty: wgpu::BindingType::Buffer {
                ty: wgpu::BufferBindingType::Uniform,
                has_dynamic_offset: false,
                min_binding_size: None,
            },
            count: None,
        }];
        for (b, ro) in [
            (1u32, true),
            (2, false),
            (3, false),
            (4, false),
            (5, false),
            (6, false),
            (7, false),
        ] {
            entries.push(wgpu::BindGroupLayoutEntry {
                binding: b,
                visibility: wgpu::ShaderStages::COMPUTE,
                ty: storage(ro),
                count: None,
            });
        }
        let layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("m7-layout"),
            entries: &entries,
        });
        let pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
            label: Some("m7-pipeline-layout"),
            bind_group_layouts: &[Some(&layout)],
            immediate_size: 0,
        });
        let module = |label: &str, src: String| {
            device.create_shader_module(wgpu::ShaderModuleDescriptor {
                label: Some(label),
                source: wgpu::ShaderSource::Wgsl(src.into()),
            })
        };
        let m_a = module("ring-1-3", shader_source(1, 3, 1, 3, true));
        let m_b = module("ring-2-5", shader_source(2, 5, 2, 5, true));
        let m_f = module("ring-1-3+2-5", shader_source(1, 3, 2, 5, true));
        let m_fast = module("ring-1-3-fastdiv", shader_source(1, 3, 1, 3, false));

        Self {
            adapter_name: info.name.clone(),
            backend: format!("{:?}", info.backend),
            ts_period_ns: queue.get_timestamp_period(),
            device,
            queue,
            layout,
            pipeline_layout,
            m_a,
            m_b,
            m_f,
            m_fast,
        }
    }

    pub fn pipeline(&self, module: &wgpu::ShaderModule, entry: &str) -> wgpu::ComputePipeline {
        self.device
            .create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
                label: Some(entry),
                layout: Some(&self.pipeline_layout),
                module,
                entry_point: Some(entry),
                compilation_options: Default::default(),
                cache: None,
            })
    }
}

/// Everything resident on the device for one stack.
pub struct Resident {
    pub geom: PlaneGeometry,
    pub row_words: u32,
    pub frames: Vec<wgpu::Buffer>,
    pub params: Vec<wgpu::Buffer>,
    pub sel_focus: wgpu::Buffer,
    pub sel_index: wgpu::Buffer,
    pub sel_w0: wgpu::Buffer,
    pub sel_w1: wgpu::Buffer,
    pub focus_io: wgpu::Buffer,
    pub scratch: wgpu::Buffer,
    /// Optional materialised focus volume, one buffer per frame.
    pub volume: Vec<wgpu::Buffer>,
    pub bg_stream: Vec<wgpu::BindGroup>,
    pub bg_vol: Vec<wgpu::BindGroup>,
    pub query: wgpu::QuerySet,
    pub query_resolve: wgpu::Buffer,
    pub query_stage: wgpu::Buffer,
    pub frame_bytes: u64,
    pub plane_bytes: u64,
}

pub const MAX_QUERIES: u32 = 2;

impl Resident {
    pub fn new(
        gpu: &Gpu,
        geom: PlaneGeometry,
        row_words: u32,
        frames_words: &[&[u32]],
        params: &[Params],
        with_volume: bool,
    ) -> Self {
        let n = frames_words.len();
        let frame_bytes = (frames_words[0].len() * 4) as u64;
        let plane_bytes = (geom.pixels() * 4) as u64;
        let dev = &gpu.device;

        let frames: Vec<_> = frames_words
            .iter()
            .enumerate()
            .map(|(k, w)| {
                dev.create_buffer_init(&wgpu::util::BufferInitDescriptor {
                    label: Some(&format!("frame{k}")),
                    contents: bytemuck::cast_slice(w),
                    usage: wgpu::BufferUsages::STORAGE
                        | wgpu::BufferUsages::COPY_DST
                        | wgpu::BufferUsages::COPY_SRC,
                })
            })
            .collect();
        let params_bufs: Vec<_> = params
            .iter()
            .enumerate()
            .map(|(k, p)| {
                dev.create_buffer_init(&wgpu::util::BufferInitDescriptor {
                    label: Some(&format!("params{k}")),
                    contents: bytemuck::bytes_of(p),
                    usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
                })
            })
            .collect();
        let mk = |label: &str, size: u64| {
            dev.create_buffer(&wgpu::BufferDescriptor {
                label: Some(label),
                size,
                usage: wgpu::BufferUsages::STORAGE
                    | wgpu::BufferUsages::COPY_SRC
                    | wgpu::BufferUsages::COPY_DST,
                mapped_at_creation: false,
            })
        };
        let sel_focus = mk("sel_focus", plane_bytes);
        let sel_index = mk("sel_index", plane_bytes);
        let sel_w0 = mk("sel_w0", plane_bytes);
        let sel_w1 = mk("sel_w1", plane_bytes);
        let focus_io = mk("focus_io", plane_bytes);
        let scratch = mk("scratch", frame_bytes.max(plane_bytes));
        let volume: Vec<_> = if with_volume {
            (0..n).map(|k| mk(&format!("vol{k}"), plane_bytes)).collect()
        } else {
            Vec::new()
        };

        let make_bg = |k: usize, focus: &wgpu::Buffer| {
            dev.create_bind_group(&wgpu::BindGroupDescriptor {
                label: Some("bg"),
                layout: &gpu.layout,
                entries: &[
                    wgpu::BindGroupEntry {
                        binding: 0,
                        resource: params_bufs[k].as_entire_binding(),
                    },
                    wgpu::BindGroupEntry {
                        binding: 1,
                        resource: frames[k].as_entire_binding(),
                    },
                    wgpu::BindGroupEntry {
                        binding: 2,
                        resource: sel_focus.as_entire_binding(),
                    },
                    wgpu::BindGroupEntry {
                        binding: 3,
                        resource: sel_index.as_entire_binding(),
                    },
                    wgpu::BindGroupEntry {
                        binding: 4,
                        resource: sel_w0.as_entire_binding(),
                    },
                    wgpu::BindGroupEntry {
                        binding: 5,
                        resource: sel_w1.as_entire_binding(),
                    },
                    wgpu::BindGroupEntry {
                        binding: 6,
                        resource: focus.as_entire_binding(),
                    },
                    wgpu::BindGroupEntry {
                        binding: 7,
                        resource: scratch.as_entire_binding(),
                    },
                ],
            })
        };
        let bg_stream: Vec<_> = (0..n).map(|k| make_bg(k, &focus_io)).collect();
        let bg_vol: Vec<_> = if with_volume {
            (0..n).map(|k| make_bg(k, &volume[k])).collect()
        } else {
            Vec::new()
        };

        let query = dev.create_query_set(&wgpu::QuerySetDescriptor {
            label: Some("ts"),
            ty: wgpu::QueryType::Timestamp,
            count: MAX_QUERIES,
        });
        let qbytes = (MAX_QUERIES as u64) * 8;
        let query_resolve = dev.create_buffer(&wgpu::BufferDescriptor {
            label: Some("qresolve"),
            size: qbytes,
            usage: wgpu::BufferUsages::QUERY_RESOLVE | wgpu::BufferUsages::COPY_SRC,
            mapped_at_creation: false,
        });
        let query_stage = dev.create_buffer(&wgpu::BufferDescriptor {
            label: Some("qstage"),
            size: qbytes,
            usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });

        Self {
            geom,
            row_words,
            frames,
            params: params_bufs,
            sel_focus,
            sel_index,
            sel_w0,
            sel_w1,
            focus_io,
            scratch,
            volume,
            bg_stream,
            bg_vol,
            query,
            query_resolve,
            query_stage,
            frame_bytes,
            plane_bytes,
        }
    }

    pub fn n(&self) -> usize {
        self.frames.len()
    }

    pub fn grid_2d(&self) -> (u32, u32) {
        (
            (self.geom.width as u32).div_ceil(TILE_W),
            (self.geom.height as u32).div_ceil(TILE_H),
        )
    }

    pub fn grid_linear(&self, n: u64) -> u32 {
        ((n as u32) + LINEAR_WG - 1) / LINEAR_WG
    }
}

/// One encoded dispatch: which pipeline, which bind group, which grid.
pub enum Job<'a> {
    Tile(&'a wgpu::ComputePipeline, &'a wgpu::BindGroup),
    Linear(&'a wgpu::ComputePipeline, &'a wgpu::BindGroup, u32),
    Copy(&'a wgpu::Buffer, &'a wgpu::Buffer, u64),
}

/// Encode a list of jobs, bracket them with encoder timestamps, submit and
/// wait. Returns (wall ms, gpu ms).
///
/// Each job gets its own compute pass so that the read-after-write dependency
/// between an unfused focus pass and its merge pass is honoured by wgpu's own
/// barrier insertion rather than assumed.
pub fn run_jobs(gpu: &Gpu, res: &Resident, jobs: &[Job]) -> (f64, f64) {
    let t0 = Instant::now();
    let mut enc = gpu
        .device
        .create_command_encoder(&wgpu::CommandEncoderDescriptor { label: Some("job") });
    enc.write_timestamp(&res.query, 0);
    for job in jobs {
        match job {
            Job::Tile(p, bg) => {
                let (gx, gy) = res.grid_2d();
                let mut pass = enc.begin_compute_pass(&wgpu::ComputePassDescriptor {
                    label: None,
                    timestamp_writes: None,
                });
                pass.set_pipeline(p);
                pass.set_bind_group(0, *bg, &[]);
                pass.dispatch_workgroups(gx, gy, 1);
            }
            Job::Linear(p, bg, groups) => {
                let mut pass = enc.begin_compute_pass(&wgpu::ComputePassDescriptor {
                    label: None,
                    timestamp_writes: None,
                });
                pass.set_pipeline(p);
                pass.set_bind_group(0, *bg, &[]);
                pass.dispatch_workgroups(*groups, 1, 1);
            }
            Job::Copy(src, dst, size) => {
                enc.copy_buffer_to_buffer(src, 0, dst, 0, *size);
            }
        }
    }
    enc.write_timestamp(&res.query, 1);
    enc.resolve_query_set(&res.query, 0..2, &res.query_resolve, 0);
    enc.copy_buffer_to_buffer(&res.query_resolve, 0, &res.query_stage, 0, 16);
    gpu.queue.submit([enc.finish()]);
    gpu.device.poll(wgpu::PollType::wait_indefinitely()).unwrap();
    let wall = t0.elapsed().as_secs_f64() * 1000.0;

    res.query_stage.map_async(wgpu::MapMode::Read, .., |_| {});
    gpu.device.poll(wgpu::PollType::wait_indefinitely()).unwrap();
    let t: Vec<u64> = {
        let view = res.query_stage.get_mapped_range(..).unwrap();
        bytemuck::cast_slice::<u8, u64>(&view).to_vec()
    };
    res.query_stage.unmap();
    let gpu_ms = (t[1].saturating_sub(t[0])) as f64 * gpu.ts_period_ns as f64 / 1.0e6;
    (wall, gpu_ms)
}

/// Read a device buffer back to host memory.
pub fn readback(gpu: &Gpu, buf: &wgpu::Buffer, bytes: u64) -> Vec<u8> {
    let stage = gpu.device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("readback"),
        size: bytes,
        usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
        mapped_at_creation: false,
    });
    let mut enc = gpu.device.create_command_encoder(&Default::default());
    enc.copy_buffer_to_buffer(buf, 0, &stage, 0, bytes);
    gpu.queue.submit([enc.finish()]);
    gpu.device.poll(wgpu::PollType::wait_indefinitely()).unwrap();
    stage.map_async(wgpu::MapMode::Read, .., |_| {});
    gpu.device.poll(wgpu::PollType::wait_indefinitely()).unwrap();
    let out = stage.get_mapped_range(..).unwrap().to_vec();
    stage.unmap();
    out
}
