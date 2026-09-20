// Eight independent source-space pairs; all reuse/rounding remains in actual GPU gather.
pub(crate) const PROBE_PAIRS:usize=8;
pub(crate) fn probe_seed(source_id:usize,draw:usize)->usize {
    ((0x4b1d_5e7a_1926_0901u64.wrapping_add((source_id as u64).wrapping_mul(0x1f123bb5))
        .wrapping_add((draw as u64).wrapping_mul(0x9e3779b9))) & 0x7fff_ffff_ffff_ffff) as usize
}
pub(crate) fn original_variances(frame:&Frame,noise:&NoiseModel)->Result<Vec<f32>> {
    let full=frame.geometry();validate_pyramid_frame(frame,full,0)?;
    let planes=[CfaPlane::R,CfaPlane::G1,CfaPlane::G2,CfaPlane::B];
    let mut out=Vec::with_capacity(4*full.pixels());
    for y in 0..2*full.height {for x in 0..2*full.width {
        let signal=frame.active_row(y)[x] as f32-frame.levels.black;
        let variance=noise.variance(planes[2*(y%2)+x%2],signal);
        ensure!(variance.is_finite() && variance>=0.0,"invalid injected original-CFA variance");out.push(variance);
    }}Ok(out)
}
pub(crate) fn noisy_source(frame:&Frame,variance:&[f32],seed:usize)->Result<Frame> {
    let full=frame.geometry();ensure!(variance.len()==4*full.pixels()
        && variance.iter().all(|v|v.is_finite() && *v>=0.0),"source variance shape/values");
    let mut normals=frame.clone();gatefloor::boundary_wavelet_fill(&mut normals,seed)?;
    let mut output=frame.clone();
    for y in 0..2*full.height {for x in 0..2*full.width {
        let index=(frame.active.y+y)*frame.stride+frame.active.x+x;
        let code=normals.data[index];
        ensure!(code>0 && code<u16::MAX,"standardized probe generator clipped");
        let z=(code as f32-32768.0)/4096.0;
        let value=(frame.data[index] as f32+variance[y*2*full.width+x].sqrt()*z).round();
        ensure!(value>0.0 && value<u16::MAX as f32,"generated source lacks u16 exposure headroom");
        output.data[index]=value as u16;
    }}Ok(output)
}
fn gather_scope(frame:&Frame,warp:Similarity,crop:align_cmd::CropRect)->Result<()> {
    ensure!(!frame.path.exists() && frame.geometry().width<=512 && frame.geometry().height<=512,
        "bounded generated sources only; no RAW decoding");
    validate_pyramid_frame(frame,frame.geometry(),0)?;
    ensure!(align_cmd::fullres_gather_enabled() && align_cmd::direct_plane_mode()?==align_cmd::DirectPlaneMode::Rounded
        && align_cmd::native_gpu_integration::gpu_gather_enabled()?,"actual GPU rounded fullres gather required");
    ensure!(!std::env::var(strehl_core::demosaic::DEMOSAIC_ENV).is_ok_and(|v|v.eq_ignore_ascii_case("directional")),"Malvar required");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none(),"local placement excluded");
    let id=strehl_raw::identity(&frame.path);
    ensure!(strehl_core::optics::profile_for_capture_env(id.model.as_deref(),id.lens_type3)?.is_none(),"fixed no-CA scope");
    ensure!(phase_packed_rgb::full_stack::full_source_supported(warp,frame.geometry(),crop,None),"covered fullres pull required");
    Ok(())
}
pub(crate) fn gather_known4(frame:&Frame,warp:Similarity,crop:align_cmd::CropRect)->Result<Vec<Vec<f32>>> {
    gather_known4_scoped(frame,warp,crop,false)
}
pub(crate) fn full_gather_binding(full:PlaneGeometry,crop:align_cmd::CropRect,warp:Similarity,
    profile:Option<&OpticalProfile>)->Result<()> {
    ensure!(full==PlaneGeometry{width:3516,height:2344}
        && [crop.x,crop.y,crop.width,crop.height]==[28,19,3460,2306],"fixed full observational domain required");
    ensure!(profile.is_some_and(|p|p.key=="a7c2-fe100gm-2xtc-x4cpl"),"held full CA profile required");
    ensure!(phase_packed_rgb::full_stack::full_source_supported(warp,full,crop,profile),"full CA pull unsupported");Ok(())
}
fn gather_known4_scoped(frame:&Frame,warp:Similarity,crop:align_cmd::CropRect,full:bool)->Result<Vec<Vec<f32>>> {
    if full {
        ensure!(align_cmd::fullres_gather_enabled() && align_cmd::direct_plane_mode()?==align_cmd::DirectPlaneMode::Rounded
            && align_cmd::native_gpu_integration::gpu_gather_enabled()?,"actual GPU rounded fullres gather required");
        ensure!(!std::env::var(strehl_core::demosaic::DEMOSAIC_ENV).is_ok_and(|v|v.eq_ignore_ascii_case("directional"))
            && std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none(),"held Malvar/no-local-placement route required");
        validate_pyramid_frame(frame,frame.geometry(),0)?;
        let id=strehl_raw::identity(&frame.path);
        let profile=strehl_core::optics::profile_for_capture_env(id.model.as_deref(),id.lens_type3)?;
        full_gather_binding(frame.geometry(),crop,warp,profile)?;
    }else{gather_scope(frame,warp,crop)?;}
    let mut current=frame.clone();let mut planes=vec![vec![0.0;crop.width*crop.height];4];
    align_cmd::warp_frame_fullres_into_planes::<false>(&mut current,warp,frame.geometry(),Resampler::CatmullRom,
        &mut WarpScratch::new(frame.geometry()),crop,&[(0,0),(1,0),(0,1),(1,1)],&mut planes,align_cmd::DirectPlaneMode::Rounded)?;
    ensure!(planes.iter().flatten().all(|v|v.is_finite()),"nonfinite consumed samples");Ok(planes)
}
pub(crate) fn gathered_wave(frame:&Frame,warp:Similarity,crop:align_cmd::CropRect,plan:&BoundaryPlan)->Result<Vec<Vec<Complex>>> {
    gathered_wave_scoped(frame,warp,crop,plan,false)
}
fn gathered_wave_scoped(frame:&Frame,warp:Similarity,crop:align_cmd::CropRect,plan:&BoundaryPlan,full:bool)->Result<Vec<Vec<Complex>>> {
    ensure!(crop.width==plan.input_width && crop.height==plan.input_height,"probe boundary/crop mismatch");
    extend_four(&gather_known4_scoped(frame,warp,crop,full)?,plan)?.iter()
        .map(|p|forward_real_scoped(p,plan.padded_width,plan.padded_height,full)).collect()
}
pub(crate) struct ProbeResult {
    pub variance4:Vec<Vec<f32>>,
    pub original_variance:Vec<f32>,
    pub seeds:[usize;16],
    pub bias4:Option<Vec<Vec<Complex>>>,
    pub pair_band_mean4:Vec<Vec<[f64;4]>>,
}
pub(crate) fn probe_variance8(frame:&Frame,warp:Similarity,crop:align_cmd::CropRect,noise:&NoiseModel,
    plan:&BoundaryPlan,source_id:usize,diagnostics:bool)->Result<ProbeResult> {
    let signal=gathered_wave(frame,warp,crop,plan)?;
    probe_from_wave(frame,warp,crop,noise,plan,source_id,diagnostics,&signal)
}
fn probe_from_wave(frame:&Frame,warp:Similarity,crop:align_cmd::CropRect,noise:&NoiseModel,
    plan:&BoundaryPlan,source_id:usize,diagnostics:bool,signal:&[Vec<Complex>])->Result<ProbeResult> {
    probe_from_wave_scoped(frame,warp,crop,noise,plan,source_id,diagnostics,signal,false)
}
fn probe_from_wave_scoped(frame:&Frame,warp:Similarity,crop:align_cmd::CropRect,noise:&NoiseModel,
    plan:&BoundaryPlan,source_id:usize,diagnostics:bool,signal:&[Vec<Complex>],full:bool)->Result<ProbeResult> {
    let original_variance=original_variances(frame,noise)?;
    let n=plan.padded_width*plan.padded_height;
    ensure!(signal.len()==4 && signal.iter().all(|v|v.len()==n),"signal coefficient shape");
    let seeds=std::array::from_fn(|draw|probe_seed(source_id,draw));
    let mut variance4=vec![vec![0.0f32;n];4];
    let mut bias4=diagnostics.then(||vec![vec![Complex::default();n];4]);
    let bands=subbands_scoped(plan.padded_width,plan.padded_height,full)?;
    let mut pair_band_mean4=Vec::new();
    for pair in 0..PROBE_PAIRS {
        // Two independent original-source draws. Never antithetic +/- draws.
        let mut member=|draw:usize|->Result<Vec<Vec<Complex>>> {
            let noisy=noisy_source(frame,&original_variance,seeds[draw])?;
            let wave=gathered_wave_scoped(&noisy,warp,crop,plan,full)?;
            if let Some(mean)=bias4.as_mut(){for c in 0..4 {for i in 0..n {
                mean[c][i].re+=wave[c][i].re;mean[c][i].im+=wave[c][i].im;
            }}}
            Ok(wave)
        };
        let a=member(2*pair)?;let b=member(2*pair+1)?;
        for c in 0..4 {for i in 0..n {
            let delta=Complex{re:a[c][i].re-b[c][i].re,im:a[c][i].im-b[c][i].im};
            variance4[c][i]+=squared(delta);
        }}
        if diagnostics {
            pair_band_mean4.push(bands.iter().map(|band|std::array::from_fn(|c|
                band.positions.iter().map(|&i|{
                    let dr=a[c][i].re as f64-b[c][i].re as f64;
                    let di=a[c][i].im as f64-b[c][i].im as f64;
                    0.5*(dr*dr+di*di)
                }).sum::<f64>()/band.positions.len() as f64)).collect());
        }
    }
    for c in 0..4 {for i in 0..n {variance4[c][i]/=(2*PROBE_PAIRS) as f32;}}
    if let Some(mean)=bias4.as_mut(){for c in 0..4 {for i in 0..n {
        mean[c][i].re=mean[c][i].re/(2*PROBE_PAIRS) as f32-signal[c][i].re;
        mean[c][i].im=mean[c][i].im/(2*PROBE_PAIRS) as f32-signal[c][i].im;
    }}}
    ensure!(variance4.iter().flatten().all(|v|v.is_finite() && *v>=0.0),"nonfinite probe variance");
    Ok(ProbeResult{variance4,original_variance,seeds,bias4,pair_band_mean4})
}
