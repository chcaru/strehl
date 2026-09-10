// Feature-gated child module of align_cmd (native-gpu-gather).
// gpu_gather_enabled() validates switches at merge configuration entry,
// even for a plane-route render. The fullres wrapper tries gpu_remosaic before
// its CPU sink; the direct sink tries gpu_rounded_planes after argument checks.
// Neither hook belongs in fullres_with_sink: the fixed CPU oracle stays CPU.
use super::*;
use std::sync::{Mutex, OnceLock};
use strehl_native_gpu_gather::{GpuGather, Input, Output, Schedule};

// One context shared across actual RGB, RGB probe and green-only probe calls.
static GPU: OnceLock<std::result::Result<Mutex<GpuGather>, String>> = OnceLock::new();

#[derive(Clone, Copy)]
enum GpuLog { Off, On, Placebo }
fn gpu_log_mode() -> Result<GpuLog> {
    static LOG: OnceLock<std::result::Result<GpuLog, String>> = OnceLock::new();
    match LOG.get_or_init(|| match std::env::var("STREHL_GPU_GATHER_LOG") {
        Err(std::env::VarError::NotPresent) => Ok(GpuLog::Off),
        Ok(v) if v == "off" => Ok(GpuLog::Off),
        Ok(v) if v == "on" => Ok(GpuLog::On),
        Ok(v) if v == "placebo" => Ok(GpuLog::Placebo),
        other => Err(format!("STREHL_GPU_GATHER_LOG: expected off, on, or placebo, got {other:?}")),
    }) { Ok(mode) => Ok(*mode), Err(message) => bail!("{message}") }
}

fn gpu_schedule() -> Result<Schedule> {
    static SCHEDULE: OnceLock<std::result::Result<Schedule, String>> = OnceLock::new();
    match SCHEDULE.get_or_init(|| match std::env::var("STREHL_GPU_SCHEDULE") {
        Err(std::env::VarError::NotPresent) => Ok(Schedule::Parallel256),
        Ok(v) if v == "parallel" => Ok(Schedule::Parallel256),
        Ok(v) if v == "serial" => Ok(Schedule::Serial32),
        Ok(v) if v == "device" => Ok(Schedule::Device256),
        other => Err(format!("STREHL_GPU_SCHEDULE: expected parallel, serial, or device, got {other:?}")),
    }) { Ok(schedule) => Ok(*schedule), Err(message) => bail!("{message}") }
}

pub(crate) fn gpu_gather_enabled() -> Result<bool> {
    gpu_log_mode()?; // Validate before data, including when GPU dispatch is off.
    static MODE: OnceLock<std::result::Result<bool, String>> = OnceLock::new();
    let enabled = match MODE.get_or_init(|| match std::env::var("STREHL_GPU_GATHER") {
        Err(std::env::VarError::NotPresent) => Ok(false),
        Ok(v) if v == "off" => Ok(false),
        Ok(v) if v == "on" => Ok(true),
        other => Err(format!("STREHL_GPU_GATHER: expected off or on, got {other:?}")),
    }) { Ok(value) => *value, Err(message) => bail!("{message}") };
    if enabled { gpu_schedule()?; } // CPU-only requests never select a GPU schedule.
    Ok(enabled)
}

fn eligible(resampler: Resampler) -> Result<bool> {
    if !gpu_gather_enabled()? { return Ok(false); }
    // The CLI environment is immutable for a process. Match the current
    // demosaic::use_directional choice exactly; unknown values mean Malvar there.
    static MALVAR: OnceLock<bool> = OnceLock::new();
    let malvar = *MALVAR.get_or_init(|| !std::env::var(strehl_core::demosaic::DEMOSAIC_ENV)
        .is_ok_and(|v| v.eq_ignore_ascii_case("directional")));
    if !malvar || resampler != Resampler::CatmullRom {
        eprintln!("  GPU gather requested; this demosaic/resampler remains CPU (Malvar + Catmull only)");
        return Ok(false);
    }
    Ok(true)
}

fn run<const GREEN_ONLY: bool>(frame: &strehl_raw::Frame, t: Similarity,
    geom: PlaneGeometry, resampler: Resampler) -> Result<Output>
{
    anyhow::ensure!(frame.active.width / 2 == geom.width && frame.active.height / 2 == geom.height,
        "frame {} has quad geometry {}x{}, but the warp map was fitted on {}x{}",
        frame.path.display(), frame.active.width / 2, frame.active.height / 2, geom.width, geom.height);
    // Same frame/gear guard, WB normalization, channel composition and host f32
    // reciprocal as the existing fullres consumer. No new profile or calibration.
    let gain = wb_gains(&frame.wb_coeffs);
    let inverse_gain = [1.0 / gain[0], 1.0 / gain[1], 1.0 / gain[2]];
    let ident = strehl_raw::identity(&frame.path);
    let ca = strehl_core::optics::profile_for_capture_env(ident.model.as_deref(), ident.lens_type3)?;
    let pulls = [(0,0),(1,0),(1,1)].map(|(x,y)| strehl_core::optics::OpticalProfile::compose(
        ca, strehl_core::optics::cfa_site_channel(x,y), t));
    let input = Input { data: &frame.data, stride: frame.stride,
        active: [frame.active.x, frame.active.y, frame.active.width, frame.active.height],
        geom, black: frame.levels.black, gain, inverse_gain, pulls,
        green_only: GREEN_ONLY, malvar: true, resampler };
    let gpu = match GPU.get_or_init(|| {
        let gpu = GpuGather::new_with_schedule(gpu_schedule().map_err(|e|e.to_string())?)?;
        match gpu_log_mode().map_err(|e|e.to_string())? {
            GpuLog::Off => {}
            GpuLog::On => eprintln!("  GPU gather: {} / {} / {}; schedule {:?}; initialization {:.3} ms; {}", gpu.adapter,
                gpu.backend, gpu.device_type, gpu.schedule(), gpu.initialization_ms,
                serde_json::to_string(&gpu.compilation).map_err(|e|e.to_string())?),
            GpuLog::Placebo => eprintln!("  GPU gather statistics: INITIALIZATION PLACEBO"),
        }
        if matches!(gpu_log_mode().map_err(|e|e.to_string())?, GpuLog::On) {
            if let Some(report) = &gpu.coordinate_compilation {eprintln!("  GPU device coordinates: {}",serde_json::to_string(report).map_err(|e|e.to_string())?);}
        }
        Ok(Mutex::new(gpu))
    }) { Ok(gpu) => gpu, Err(message) => bail!("GPU gather initialization failed: {message}") };
    // Initialization, validation, allocation, device or dispatch errors abort
    // the explicit experiment. Never turn a failed GPU timing into a CPU run.
    let output = gpu.lock().map_err(|_| anyhow::anyhow!("GPU gather mutex poisoned"))?
        .run(&input).map_err(anyhow::Error::msg)?;
    match gpu_log_mode()? {
        GpuLog::Off => {}
        GpuLog::On => eprintln!("  GPU gather {} {:?}: {}x{}, covered {}/{}, library call {:.3} ms, pack {:.3}, CPU coordinates {:.3}, submit/wait/readback {:.3}; upload {} B, download {} B",
            if GREEN_ONLY { "green-only" } else { "RGB" }, output.schedule, output.width, output.height,
            output.covered, output.consumed_sites, output.costs.total_ms, output.costs.pack_ms,
            output.costs.coordinate_ms, output.costs.submit_wait_readback_ms,
            output.costs.source_upload_bytes + output.costs.coordinate_upload_bytes + output.costs.parameter_upload_bytes,
            output.costs.download_bytes),
        GpuLog::Placebo => eprintln!("  GPU gather statistics: CALL PLACEBO"),
    }
    // Intrinsic route evidence, independent of optional numeric statistics.
    eprintln!("  GPU gather completed {}", if GREEN_ONLY { "green-only" } else { "RGB" });
    if let Some(reason) = output.coordinate_fallback {
        eprintln!("  GPU device coordinates fallback Parallel256: {reason}");
    }
    if output.schedule == Schedule::Device256 {
        eprintln!("  GPU device coordinates completed {}", if GREEN_ONLY {"green-only"} else {"RGB"});
    }
    Ok(output)
}

pub(super) fn gpu_remosaic<const GREEN_ONLY: bool>(frame: &mut strehl_raw::Frame,
    t: Similarity, geom: PlaneGeometry, resampler: Resampler) -> Result<Option<f64>>
{
    if !eligible(resampler)? { return Ok(None); }
    let execution = warp_writeback_mode()?; // Preserve the existing refusal.
    let output = run::<GREEN_ONLY>(frame,t,geom,resampler)?;
    let words_per_row = output.width / 2;
    let (ax,ay,stride) = (frame.active.x,frame.active.y,frame.stride);
    let copy_row = |y: usize, row: &mut [u16]| {
        for (x,&word) in output.packed[y*words_per_row..(y+1)*words_per_row].iter().enumerate() {
            if !GREEN_ONLY || y % 2 == 1 { row[ax+2*x] = word as u16; }
            if !GREEN_ONLY || y % 2 == 0 { row[ax+2*x+1] = (word >> 16) as u16; }
        }
    };
    match execution {
        WarpWriteback::Serial => frame.data.chunks_mut(stride).skip(ay).take(output.height)
            .enumerate().for_each(|(y,row)|copy_row(y,row)),
        WarpWriteback::Parallel => frame.data.par_chunks_mut(stride).skip(ay).take(output.height)
            .enumerate().for_each(|(y,row)|copy_row(y,row)),
    }
    Ok(Some(output.covered as f64 / output.consumed_sites as f64))
}

#[cfg(feature = "native-direct-planes")]
#[allow(clippy::too_many_arguments)]
pub(super) fn gpu_rounded_planes<const GREEN_ONLY: bool>(frame: &strehl_raw::Frame,
    t: Similarity, geom: PlaneGeometry, resampler: Resampler, crop: CropRect,
    offsets: &[(usize,usize)], planes: &mut [Vec<f32>], mode: DirectPlaneMode) -> Result<bool>
{
    if !gpu_gather_enabled()? { return Ok(false); }
    if mode != DirectPlaneMode::Rounded {
        eprintln!("  GPU gather requested; direct mode {mode:?} remains CPU (rounded only)");
        return Ok(false);
    }
    if !eligible(resampler)? { return Ok(false); }
    // The owning direct sink has already checked crop bounds, distinct valid
    // offsets, output lengths and mode. Retain a local guard before indexing.
    anyhow::ensure!(offsets.len() == planes.len()
        && offsets.iter().enumerate().all(|(i,&(x,y))|x<2 && y<2
            && !offsets[..i].contains(&(x,y)) && (!GREEN_ONLY || x!=y))
        && crop.width>0 && crop.height>0
        && crop.x.checked_add(crop.width).is_some_and(|x|x<=geom.width)
        && crop.y.checked_add(crop.height).is_some_and(|y|y<=geom.height)
        && planes.iter().all(|p|p.len()==crop.width*crop.height), "invalid GPU direct-plane destination");
    let execution = warp_writeback_mode()?;
    let output = run::<GREEN_ONLY>(frame,t,geom,resampler)?;
    let black = frame.levels.black;
    for (&(dx,dy), plane) in offsets.iter().zip(planes) {
        let copy_row = |y: usize, values: &mut [f32]| {
            // One word is one native horizontal pair. Crop remains in the
            // original reference's quad coordinates; no recentered geometry.
            let row = (2*(crop.y+y)+dy)*geom.width+crop.x;
            for (x,value) in values.iter_mut().enumerate() {
                let code = ((output.packed[row+x] >> (16*dx)) & 65535) as u16;
                *value = (code as f32-black).max(0.0);
            }
        };
        match execution {
            WarpWriteback::Serial => plane.chunks_mut(crop.width).enumerate().for_each(|(y,row)|copy_row(y,row)),
            WarpWriteback::Parallel => plane.par_chunks_mut(crop.width).enumerate().for_each(|(y,row)|copy_row(y,row)),
        }
    }
    Ok(true)
}
