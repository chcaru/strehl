//! One device per process: the instance, adapter, device, queue, shader
//! module and pipelines a fold needs, built once and shared by every
//! [`crate::GpuFold`] the process makes (a render's preview and main pass,
//! the desktop's successive renders). A fold creates only its buffers.
//!
//! The pipelines are compiled through a [`wgpu::PipelineCache`] kept on disk
//! when the adapter supports one and the caller named a directory
//! ([`set_pipeline_cache_dir`]): a new binary with an unchanged shader then
//! skips the driver's compile (MEASURED 1.6 s on the first run of a binary,
//! 2026-11-18). The cache is keyed by adapter, driver and a hash of the
//! shader's words; a stale or damaged file is ignored by the driver and
//! rewritten. Neither the sharing nor the cache can change a pipeline: the
//! same words compile the same kernels.
use std::borrow::Cow;
use std::path::PathBuf;
use std::sync::{Mutex, OnceLock};

use crate::{PROFILE_ENV, SHADER, WG, strict};

#[derive(Clone)]
pub(crate) struct Context {
    pub device: wgpu::Device,
    pub queue: wgpu::Queue,
    pub bgl: wgpu::BindGroupLayout,
    pub pipelines: Vec<wgpu::ComputePipeline>,
    pub limits: wgpu::Limits,
    pub adapter: String,
    pub decorated_results: usize,
    pub profiling: bool,
    /// Adapter, driver and shader, as a file-name-safe key
    /// ([`self_test_key`]).
    pub key: String,
}

/// A key naming this process's adapter, its driver and the shader's words,
/// safe in a file name; `None` without a device.
pub(crate) fn self_test_key() -> Option<String> {
    shared().ok().map(|c| c.key)
}

static SHARED: Mutex<Option<Context>> = Mutex::new(None);
static CACHE_DIR: OnceLock<PathBuf> = OnceLock::new();

/// Keep compiled pipelines in `dir` (created when needed). Takes effect
/// before the process's first fold; later calls are ignored.
pub fn set_pipeline_cache_dir(dir: PathBuf) {
    let _ = CACHE_DIR.set(dir);
}

/// The process's context, built on first use. A failure is not remembered,
/// so a later fold tries again.
pub(crate) fn shared() -> Result<Context, String> {
    let mut slot = SHARED.lock().unwrap_or_else(|e| e.into_inner());
    if let Some(ctx) = slot.as_ref() {
        return Ok(ctx.clone());
    }
    let ctx = build()?;
    *slot = Some(ctx.clone());
    Ok(ctx)
}

/// Remove the files beside `kept` that share its name up to the last `-`
/// (the same adapter, an older shader): a changed shader leaves nothing
/// behind.
pub(crate) fn remove_siblings(kept: &std::path::Path) {
    let (Some(dir), Some(name)) = (kept.parent(), kept.file_name().and_then(|n| n.to_str())) else {
        return;
    };
    let Some(cut) = name.rfind('-') else {
        return;
    };
    let prefix = &name[..=cut];
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        let other = entry.file_name();
        let Some(other) = other.to_str() else {
            continue;
        };
        if other != name && other.starts_with(prefix) {
            let _ = std::fs::remove_file(entry.path());
        }
    }
}

/// FNV-1a over the shader's words: the cache file's name changes with them.
fn words_hash(words: &[u32]) -> u64 {
    let mut h = 0xcbf2_9ce4_8422_2325u64;
    for w in words {
        for b in w.to_le_bytes() {
            h ^= u64::from(b);
            h = h.wrapping_mul(0x0000_0100_0000_01b3);
        }
    }
    h
}

fn build() -> Result<Context, String> {
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
    let cache_file = CACHE_DIR
        .get()
        .filter(|_| adapter.features().contains(wgpu::Features::PIPELINE_CACHE))
        .and_then(|dir| {
            let key = wgpu::util::pipeline_cache_key(&info)?;
            Some(dir.join(format!("{key}-{:016x}", words_hash(&words))))
        });
    if cache_file.is_some() {
        features |= wgpu::Features::PIPELINE_CACHE;
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
            entry(7, wgpu::BufferBindingType::Storage { read_only: false }),
            entry(8, wgpu::BufferBindingType::Storage { read_only: false }),
            entry(9, wgpu::BufferBindingType::Storage { read_only: true }),
            entry(10, wgpu::BufferBindingType::Storage { read_only: false }),
        ],
    });
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
    let cached = cache_file.as_ref().and_then(|p| std::fs::read(p).ok());
    // SAFETY: `data` is either absent or bytes this function wrote from
    // `get_data` for the same cache key; `fallback` makes the driver ignore
    // data it does not accept rather than fail.
    let cache = cache_file.as_ref().map(|_| unsafe {
        device.create_pipeline_cache(&wgpu::PipelineCacheDescriptor {
            label: Some("strehl-fold"),
            data: cached.as_deref(),
            fallback: true,
        })
    });
    let pipelines = strict::ENTRY_POINTS
        .iter()
        .map(|name| {
            device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
                label: Some(name),
                layout: Some(&pipeline_layout),
                module: &module,
                entry_point: Some(name),
                compilation_options: Default::default(),
                cache: cache.as_ref(),
            })
        })
        .collect();
    if let (Some(path), Some(cache)) = (cache_file, cache.as_ref())
        && let Some(data) = cache.get_data()
        && cached.as_deref() != Some(data.as_slice())
    {
        // Written beside, then renamed: a reader never sees half a file.
        // Failing to keep the cache costs the next run its compile, nothing else.
        if let Some(dir) = path.parent()
            && std::fs::create_dir_all(dir).is_ok()
        {
            let partial = path.with_extension(format!("partial-{}", std::process::id()));
            if std::fs::write(&partial, &data).is_ok() && std::fs::rename(&partial, &path).is_err()
            {
                let _ = std::fs::remove_file(&partial);
            }
            remove_siblings(&path);
        }
    }
    let identity = format!(
        "{} {} {} {:x} {:x}",
        info.name, info.driver, info.driver_info, info.vendor, info.device
    );
    let key = format!(
        "{:016x}-{:016x}",
        words_hash(&identity.bytes().map(u32::from).collect::<Vec<_>>()),
        words_hash(&words)
    );
    Ok(Context {
        device,
        queue,
        bgl,
        pipelines,
        limits,
        adapter: info.name,
        decorated_results,
        profiling,
        key,
    })
}
