//! The optical restoration's convolution on the device (round-2 plan stage
//! Q8): `strehl_core::optical_restore::convolve` operand for operand
//! (`convolve.wgsl`), on the process's shared device. MEASURED on the CPU:
//! 0.48 s a 9504 x 6336 channel at radius 32 (3,209 live taps), three to
//! five channels a render.
use std::sync::{Mutex, OnceLock};

use wgpu::util::DeviceExt;

use crate::{context, strict};

const SHADER: &str = include_str!("convolve.wgsl");

struct Pipeline {
    bgl: wgpu::BindGroupLayout,
    pipeline: wgpu::ComputePipeline,
}

fn pipeline(device: &wgpu::Device) -> Result<&'static Pipeline, String> {
    static PIPELINE: OnceLock<Pipeline> = OnceLock::new();
    static BUILDING: Mutex<()> = Mutex::new(());
    if let Some(p) = PIPELINE.get() {
        return Ok(p);
    }
    let _guard = BUILDING.lock().unwrap_or_else(|e| e.into_inner());
    if let Some(p) = PIPELINE.get() {
        return Ok(p);
    }
    let (words, _) = strict::compile(SHADER)?;
    let entry = |binding, ty| wgpu::BindGroupLayoutEntry {
        binding,
        visibility: wgpu::ShaderStages::COMPUTE,
        ty: wgpu::BindingType::Buffer {
            ty,
            has_dynamic_offset: false,
            min_binding_size: None,
        },
        count: None,
    };
    let bgl = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
        label: Some("convolve-layout"),
        entries: &[
            entry(0, wgpu::BufferBindingType::Uniform),
            entry(1, wgpu::BufferBindingType::Storage { read_only: true }),
            entry(2, wgpu::BufferBindingType::Storage { read_only: true }),
            entry(3, wgpu::BufferBindingType::Storage { read_only: false }),
        ],
    });
    let layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
        label: Some("convolve-pipeline-layout"),
        bind_group_layouts: &[Some(&bgl)],
        immediate_size: 0,
    });
    // SAFETY: this crate's own shader, validated by naga and altered only by
    // added NoContraction decorations (`strict`).
    let module = unsafe {
        device.create_shader_module_passthrough(wgpu::ShaderModuleDescriptorPassthrough {
            label: Some("strehl-convolve"),
            spirv: Some(std::borrow::Cow::Borrowed(&words)),
            entry_points: std::borrow::Cow::Owned(vec![wgpu::PassthroughShaderEntryPoint {
                name: std::borrow::Cow::Borrowed("conv"),
                workgroup_size: (256, 1, 1),
            }]),
            ..Default::default()
        })
    };
    let pipeline = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
        label: Some("conv"),
        layout: Some(&layout),
        module: &module,
        entry_point: Some("conv"),
        compilation_options: Default::default(),
        cache: None,
    });
    let _ = PIPELINE.set(Pipeline { bgl, pipeline });
    Ok(PIPELINE.get().expect("just set"))
}

/// `src` (`w x h`) convolved with the square kernel of radius `radius`
/// (`taps`, row-major `(2 radius + 1)^2`, zero taps skipped) mirror-reflected
/// at the borders: `strehl_core::optical_restore::convolve`, bit for bit, on
/// the device. `Err` when there is no device or the image does not fit it.
pub fn convolve(
    src: &[f32],
    w: usize,
    h: usize,
    radius: usize,
    taps: &[f32],
) -> Result<Vec<f32>, String> {
    let side = 2 * radius + 1;
    if taps.len() != side * side || src.len() != w * h || w <= radius || h <= radius {
        return Err("device convolution: shapes do not match".into());
    }
    let n = w * h;
    if n as u64 * 4 > u64::from(u32::MAX) {
        return Err("device convolution: image too large".into());
    }
    let ctx = context::shared()?;
    let (device, queue) = (&ctx.device, &ctx.queue);
    let binding = ctx
        .limits
        .max_storage_buffer_binding_size
        .min(ctx.limits.max_buffer_size);
    if n as u64 * 4 > binding {
        return Err("device convolution: image above the device's binding limit".into());
    }
    let pipe = pipeline(device)?;
    // The live taps in (ky, kx) order, as the CPU loops them.
    let live: Vec<[u32; 4]> = taps
        .chunks(side)
        .enumerate()
        .flat_map(|(ky, row)| {
            row.iter()
                .enumerate()
                .filter(|(_, t)| **t != 0.0)
                .map(move |(kx, t)| [kx as u32, ky as u32, t.to_bits(), 0])
        })
        .collect();
    if live.is_empty() {
        return Ok(vec![0.0; n]);
    }
    let params = [w as u32, h as u32, radius as u32, live.len() as u32];
    let uniform = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some("convolve-params"),
        contents: bytemuck::cast_slice(&params),
        usage: wgpu::BufferUsages::UNIFORM,
    });
    let src_buf = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some("convolve-src"),
        contents: bytemuck::cast_slice(src),
        usage: wgpu::BufferUsages::STORAGE,
    });
    let taps_buf = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some("convolve-taps"),
        contents: bytemuck::cast_slice(&live),
        usage: wgpu::BufferUsages::STORAGE,
    });
    let bytes = n as u64 * 4;
    let dst = device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("convolve-dst"),
        size: bytes,
        usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC,
        mapped_at_creation: false,
    });
    let readback = device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("convolve-readback"),
        size: bytes,
        usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
        mapped_at_creation: false,
    });
    let bind = device.create_bind_group(&wgpu::BindGroupDescriptor {
        label: Some("convolve-bind"),
        layout: &pipe.bgl,
        entries: &[
            wgpu::BindGroupEntry {
                binding: 0,
                resource: uniform.as_entire_binding(),
            },
            wgpu::BindGroupEntry {
                binding: 1,
                resource: src_buf.as_entire_binding(),
            },
            wgpu::BindGroupEntry {
                binding: 2,
                resource: taps_buf.as_entire_binding(),
            },
            wgpu::BindGroupEntry {
                binding: 3,
                resource: dst.as_entire_binding(),
            },
        ],
    });
    let groups = n.div_ceil(256) as u32;
    let gx = groups.min(65_535);
    let gy = groups.div_ceil(gx);
    let mut encoder = device.create_command_encoder(&wgpu::CommandEncoderDescriptor {
        label: Some("convolve"),
    });
    {
        let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor {
            label: Some("convolve"),
            timestamp_writes: None,
        });
        pass.set_pipeline(&pipe.pipeline);
        pass.set_bind_group(0, &bind, &[]);
        pass.dispatch_workgroups(gx, gy, 1);
    }
    encoder.copy_buffer_to_buffer(&dst, 0, &readback, 0, bytes);
    let index = queue.submit([encoder.finish()]);
    readback.slice(..).map_async(wgpu::MapMode::Read, |r| {
        r.expect("map convolution read-back")
    });
    device
        .poll(wgpu::PollType::Wait {
            submission_index: Some(index),
            timeout: None,
        })
        .map_err(|e| format!("device convolution wait: {e:?}"))?;
    let out = {
        let view = readback
            .slice(..)
            .get_mapped_range()
            .map_err(|e| format!("device convolution read-back: {e:?}"))?;
        // Read-back memory is slow to read on one thread: in parallel pieces.
        use rayon::prelude::*;
        let src = bytemuck::cast_slice::<u8, f32>(&view);
        let mut out = vec![0f32; n];
        out.par_chunks_mut(1 << 18)
            .zip(src.par_chunks(1 << 18))
            .for_each(|(d, s)| d.copy_from_slice(s));
        out
    };
    readback.unmap();
    Ok(out)
}
