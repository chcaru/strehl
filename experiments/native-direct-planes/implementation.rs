// Default-off handoff from the existing full-resolution gather into consumed planes.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum DirectPlaneMode { Off, Rounded, Float }

pub(crate) fn direct_plane_mode() -> Result<DirectPlaneMode> {
    const ENV: &str = "STREHL_DIRECT_PLANES";
    static MODE: std::sync::OnceLock<std::result::Result<DirectPlaneMode,String>> = std::sync::OnceLock::new();
    match MODE.get_or_init(|| {
        let mode = match std::env::var(ENV) {
            Err(std::env::VarError::NotPresent) => DirectPlaneMode::Off,
            Ok(v) if v == "off" => DirectPlaneMode::Off,
            Ok(v) if v == "rounded" => DirectPlaneMode::Rounded,
            Ok(v) if v == "float" => DirectPlaneMode::Float,
            other => return Err(format!("{ENV}: expected off, rounded, or float; got {other:?}")),
        };
        if mode != DirectPlaneMode::Off {
            #[cfg(feature = "native-signed-black")]
            if std::env::var("STREHL_SIGNED_BLACK").is_ok_and(|v| v != "0") {
                return Err("direct planes cannot combine with signed-black extraction".into());
            }
            #[cfg(feature = "native-sensor-transfer")]
            return Err("direct planes cannot combine with the sensor-transfer mutated-frame diagnostic".into());
        }
        Ok(mode)
    }) { Ok(mode) => Ok(*mode), Err(message) => bail!("{message}") }
}

pub(crate) fn consumed_fullres_value(value: f32, covered: bool, inv: f32,
    black: f32, mode: DirectPlaneMode) -> f32
{
    assert!(mode != DirectPlaneMode::Off);
    let sensor = if !covered {
        black.round().clamp(0.0,u16::MAX as f32) as u16 as f32
    } else if mode == DirectPlaneMode::Rounded {
        (value*inv+black).round().clamp(0.0,u16::MAX as f32) as u16 as f32
    } else {
        // Keep the inverse-WB/pedestal cancellation and both original clamps.
        // A NaN used to cast to u16 zero; omitting the store must preserve that.
        let clipped = (value*inv+black).clamp(0.0,u16::MAX as f32);
        if clipped.is_nan() { 0.0 } else { clipped }
    };
    (sensor-black).max(0.0)
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn write_fullres_plane(out: &mut [f32], full: PlaneGeometry, crop: CropRect,
    dst: &[f32], cover: &[bool], inv: f32, black: f32, mode: DirectPlaneMode,
    execution: WarpWriteback) -> Result<usize>
{
    anyhow::ensure!(mode != DirectPlaneMode::Off && crop.width>0 && crop.height>0
        && crop.x.checked_add(crop.width).is_some_and(|x|x<=full.width)
        && crop.y.checked_add(crop.height).is_some_and(|y|y<=full.height)
        && out.len()==crop.width*crop.height && dst.len()>=full.pixels() && cover.len()>=full.pixels(),
        "direct plane has invalid mode, crop, or buffer extent");
    let row = |y: usize, values: &mut [f32]| {
        let start=(crop.y+y)*full.width+crop.x;
        for (x,value) in values.iter_mut().enumerate() {
            *value=consumed_fullres_value(dst[start+x],cover[start+x],inv,black,mode);
        }
    };
    match execution {
        WarpWriteback::Serial => out.chunks_mut(crop.width).enumerate().for_each(|(y,v)|row(y,v)),
        WarpWriteback::Parallel => out.par_chunks_mut(crop.width).enumerate().for_each(|(y,v)|row(y,v)),
    }
    Ok(cover[..full.pixels()].par_iter().filter(|&&v|v).count())
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn warp_frame_fullres_into_planes<const GREEN_ONLY: bool>(
    frame: &mut strehl_raw::Frame, t: Similarity, geom: PlaneGeometry,
    resampler: Resampler, scratch: &mut WarpScratch, crop: CropRect,
    offsets: &[(usize,usize)], planes: &mut [Vec<f32>], mode: DirectPlaneMode,
) -> Result<()> {
    anyhow::ensure!(mode != DirectPlaneMode::Off && offsets.len()==planes.len()
        && offsets.iter().enumerate().all(|(i,&(x,y))|x<2 && y<2
            && !offsets[..i].contains(&(x,y)) && (!GREEN_ONLY || x!=y))
        && crop.width>0 && crop.height>0
        && crop.x.checked_add(crop.width).is_some_and(|x|x<=geom.width)
        && crop.y.checked_add(crop.height).is_some_and(|y|y<=geom.height)
        && planes.iter().all(|p|p.len()==crop.width*crop.height),
        "direct fullres sink has invalid mode, CFA sites, crop, or plane lengths");
    // Validate geometry/support before the base gather writes anything. The
    // exact same entry point consumes actual frames and the synthetic probe.
    let local = local_placement::prepare(frame,t,geom,resampler,crop,offsets,mode)?;
    #[cfg(feature = "native-gpu-gather")]
    if native_gpu_integration::gpu_rounded_planes::<GREEN_ONLY>(frame,t,geom,resampler,crop,offsets,planes,mode)? {
        if let Some(local) = local { local.apply(frame,planes,mode)?; }
        return Ok(());
    }
    warp_frame_fullres_with_sink::<GREEN_ONLY,_>(frame,t,geom,resampler,scratch,
        |_,site,dst,cover,inv,black,execution| {
            if let Some(slot)=offsets.iter().position(|&s|s==site) {
                write_fullres_plane(&mut planes[slot],geom,crop,dst,cover,inv,black,mode,execution)
            } else {
                Ok(cover[..geom.pixels()].par_iter().filter(|&&v|v).count())
            }
        })?;
    if let Some(local) = local { local.apply(frame,planes,mode)?; }
    Ok(())
}

// Test-only liveness markers: explicit arithmetic helpers do not touch these.
#[cfg(test)]
static DIRECT_OBSERVER: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);
#[cfg(test)]
static DIRECT_ACTUAL_HITS: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
#[cfg(test)]
static DIRECT_PROBE_HITS: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
#[cfg(test)]
pub(crate) fn direct_plane_observer(enabled: bool) {
    DIRECT_OBSERVER.store(enabled, std::sync::atomic::Ordering::SeqCst);
}
#[cfg(test)]
pub(crate) fn direct_plane_hits() -> (usize, usize) {
    (DIRECT_ACTUAL_HITS.load(std::sync::atomic::Ordering::SeqCst),
     DIRECT_PROBE_HITS.load(std::sync::atomic::Ordering::SeqCst))
}
#[cfg(test)]
pub(crate) fn direct_plane_actual_hit() {
    if DIRECT_OBSERVER.load(std::sync::atomic::Ordering::SeqCst) {
        DIRECT_ACTUAL_HITS.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
    }
}
#[cfg(test)]
pub(crate) fn direct_plane_probe_hit() {
    if DIRECT_OBSERVER.load(std::sync::atomic::Ordering::SeqCst) {
        DIRECT_PROBE_HITS.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
    }
}
