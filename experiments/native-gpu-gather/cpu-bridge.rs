// Included only in align_cmd under cfg(test, feature="native-gpu-gather").
// The oracle executes current source reconstruction, sampler and writeback.
pub(crate) struct GpuCpuOracle {
    pub coverage: Vec<bool>,
    /// Existing gathered value * current CPU inverse WB + black, before round.
    /// Missing and green-probe-unconsumed sites are NaN.
    pub sensor_values: Vec<f32>,
    pub gain: [f32;3],
    pub inverse_gain: [f32;3],
    pub pulls: [Similarity;3],
    pub covered: usize,
}

pub(crate) fn gpu_cpu_oracle(frame: &mut strehl_raw::Frame, t: Similarity,
    geom: PlaneGeometry, ca: Option<strehl_core::optics::OpticalProfile>,
    green_only: bool) -> Result<GpuCpuOracle> {
    gpu_cpu_oracle_mode(frame,t,geom,ca,green_only,false)
}

/// Same trace allocation/traversal and actual writeback, fixed trace values.
pub(crate) fn gpu_cpu_oracle_placebo(frame: &mut strehl_raw::Frame, t: Similarity,
    geom: PlaneGeometry, ca: Option<strehl_core::optics::OpticalProfile>,
    green_only: bool) -> Result<GpuCpuOracle> {
    gpu_cpu_oracle_mode(frame,t,geom,ca,green_only,true)
}

fn gpu_cpu_oracle_mode(frame: &mut strehl_raw::Frame, t: Similarity,
    geom: PlaneGeometry, ca: Option<strehl_core::optics::OpticalProfile>,
    green_only: bool, placebo: bool) -> Result<GpuCpuOracle> {
    anyhow::ensure!(!std::env::var(strehl_core::demosaic::DEMOSAIC_ENV)
        .map(|v|v.eq_ignore_ascii_case("directional")).unwrap_or(false),
        "GPU oracle requires the current Malvar arm");
    if green_only { gpu_cpu_oracle_inner::<true>(frame,t,geom,ca,placebo) }
    else { gpu_cpu_oracle_inner::<false>(frame,t,geom,ca,placebo) }
}

fn gpu_cpu_oracle_inner<const GREEN_ONLY: bool>(frame: &mut strehl_raw::Frame,
    t: Similarity, geom: PlaneGeometry, ca: Option<strehl_core::optics::OpticalProfile>,
    placebo: bool) -> Result<GpuCpuOracle> {
    let gain = wb_gains(&frame.wb_coeffs);
    let inverse_gain = [1.0/gain[0],1.0/gain[1],1.0/gain[2]];
    let pulls = [(0,0),(1,0),(1,1)].map(|(dx,dy)|
        strehl_core::optics::OpticalProfile::compose(ca.as_ref(),strehl_core::optics::cfa_site_channel(dx,dy),t));
    let width = 2*geom.width;
    let mut coverage = vec![false;4*geom.pixels()];
    let mut sensor_values = vec![f32::NAN;4*geom.pixels()];
    let mut scratch = WarpScratch::new(geom);
    warp_frame_fullres_with_sink_impl::<GREEN_ONLY,_>(frame,t,geom,Resampler::CatmullRom,&mut scratch,
        |frame,(dx,dy),dst,cover,inv,black,execution| {
            for py in 0..geom.height {for px in 0..geom.width {
                let i=py*geom.width+px;let j=(2*py+dy)*width+2*px+dx;
                if placebo {
                    coverage[j]=false;
                    sensor_values[j]=-12345.0;
                } else {
                    coverage[j]=cover[i];
                    if cover[i] {sensor_values[j]=dst[i]*inv+black;}
                }
            }}
            Ok(writeback_fullres_site(&mut frame.data,frame.stride,(frame.active.x,frame.active.y),
                geom,(dx,dy),dst,cover,inv,black,execution))
        },Some(ca))?;
    let covered=coverage.iter().filter(|&&v|v).count();
    Ok(GpuCpuOracle{coverage,sensor_values,gain,inverse_gain,pulls,covered})
}
