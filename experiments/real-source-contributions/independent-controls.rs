// Included as a child test module of observer.rs. Author-independent, no RAW.
use super::*;
use strehl_core::pyramid::{AdmissionMode, BaseBand, Fallback, Hull, MergeConfig, SelectMode};

fn config() -> MergeConfig {
    MergeConfig { bands: 7, gate: 2.0, exponent: 2.0, sharpen_per_octave: 1.4,
        select: SelectMode::SoftPower, admission: AdmissionMode::HardFloor,
        base: BaseBand::Mean, mean_coarse: 0, hull: Hull::InputRange,
        fallback: Fallback::Mean, significance_scale: 0.0, ..Default::default() }
}

fn sampled_bands(merge: &BandMerge, nodes: &[Vec<usize>], c: usize) -> Vec<Vec<f32>> {
    nodes.iter().enumerate().map(|(k, nn)| nn.iter().map(|&j| bridge::state(merge,k,j)[9+c]).collect()).collect()
}

#[test]
fn independent_noncentral_tap_has_known_effect() {
    let sizes = level_sizes(128,96,7);
    assert!(sizes.len() >= 3, "fixture omitted coarse levels");
    let nodes = closure(&sizes, &[[4,4]]);
    let mut bands: Vec<Vec<f32>> = nodes.iter().map(|nn| vec![0.0; nn.len()]).collect();
    // One diagonal noncentral coefficient, expanded with 1/8 on each axis:
    // 64 * (1/8) * (1/8) = 1. This is independent of the sparse recurrence.
    let q = nodes[1].binary_search(&(sizes[1].width + 1)).expect("noncentral tap absent");
    bands[1][q] = 64.0;
    assert_eq!(sparse_collapse(&sizes,&nodes,&bands), vec![1.0]);
    bands[1][q] = 0.0;
    assert_eq!(sparse_collapse(&sizes,&nodes,&bands), vec![0.0]);
}

#[test]
fn independent_actual_zero_weight_fallback_keeps_nonzero_mean_base() {
    let (w,h) = (128,96);
    let cfg = config();
    let sizes = level_sizes(w,h,cfg.bands);
    let nodes = closure(&sizes,&[[4,4],[31,30],[64,48],[127,95]]);
    let mut merge = BandMerge::new(w,h,4,cfg);
    let mut ws = FrameWorkspace::new(&sizes,4);
    let variance = vec![1.0e6; w*h];
    for value in [120.0,360.0] {
        let p = vec![value;w*h];
        ws.next_frame();
        merge.add_frame(&[&p,&p,&p,&p],&p,&variance,&mut ws);
    }
    for (k, nn) in nodes.iter().enumerate() {
        for &j in nn {
            let row = bridge::state(&merge,k,j);
            assert_eq!(row[0],0.0,"fixture unexpectedly selected");
            for c in 0..4 { assert_eq!(row[9+c],if k+1==sizes.len(){240.0}else{0.0}); }
        }
    }
    let actual = merge.finish(&mut Workspace::new(&sizes));
    let bands = sampled_bands(&merge,&nodes,0);
    assert!(sparse_collapse(&sizes,&nodes,&bands).iter().all(|&v|v==240.0));
    assert!(actual.iter().flatten().all(|&v|v==240.0));
    let mut missing_base = bands.clone();
    missing_base.last_mut().unwrap().fill(0.0);
    assert!(sparse_collapse(&sizes,&nodes,&missing_base).iter().all(|&v|v==0.0),
        "base omission destroyer did not affect reconstruction");
}

#[test]
fn independent_actual_signed_coefficients_cancel_without_losing_dc() {
    let (w,h) = (128,96);
    let cfg = config();
    let sizes = level_sizes(w,h,cfg.bands);
    let mut merge = BandMerge::new(w,h,4,cfg);
    let mut ws = FrameWorkspace::new(&sizes,4);
    let guide: Vec<f32> = (0..w*h).map(|j|100.0+if (j%w+j/w)%2==0{32.0}else{-32.0}).collect();
    let variance = vec![1.0;w*h];
    let j = 40*w+40;
    let mut coefficients = Vec::new();
    for sign in [1.0,-1.0] {
        let p: Vec<f32> = guide.iter().map(|v|100.0+sign*(v-100.0)).collect();
        ws.next_frame();
        merge.add_frame(&[&p,&p,&p,&p],&guide,&variance,&mut ws);
        coefficients.push(bridge::coefficients(&ws,0)[0][j]);
    }
    assert!(coefficients[0]>0.0 && coefficients[1]<0.0);
    assert_eq!(coefficients[0],-coefficients[1]);
    let row = bridge::state(&merge,0,j);
    assert!(row[0]>0.0,"weighted cancellation never selected");
    assert_eq!(row[9],0.0);
    assert!(coefficients.iter().map(|v|v.abs()).sum::<f32>()>0.0);
    let output = merge.finish(&mut Workspace::new(&sizes));
    assert_eq!(output[0][j],100.0,"cancelled signed AC lost the nonzero base");
}

#[test]
fn independent_actual_live_clamp_requires_nonzero_residual() {
    // Independently choose horizontal support, dimensions, values and texture
    // phase. Contradicting scales are intentional; this is not a photograph.
    let (w,h,nf) = (136usize,184usize,8usize);
    let cfg = config();
    let sizes = level_sizes(w,h,cfg.bands);
    let mut merge = BandMerge::new(w,h,4,cfg);
    let mut ws = FrameWorkspace::new(&sizes,4);
    let variance = vec![4.0;w*h];
    for f in 0..nf {
        let stripe = h/nf;
        let fine_lo = f*stripe;
        let coarse_lo = ((f+nf/2)%nf)*stripe;
        let plane: Vec<f32> = (0..w*h).map(|j| {
            let (x,y)=(j%w,j/w);
            let background=if y<h/3{75.0}else{850.0};
            let coarse=if (coarse_lo..coarse_lo+stripe).contains(&y){600.0}else{0.0};
            let fine=if (fine_lo..fine_lo+stripe).contains(&y) {
                220.0*(((x*7+y*5)%9)as f32/9.0-0.5)
            }else{0.0};
            background+coarse+fine
        }).collect();
        ws.next_frame();
        merge.add_frame(&[&plane,&plane,&plane,&plane],&plane,&variance,&mut ws);
    }
    // A small complete generated image makes this checker independent of an
    // author's preferred sample sites. No photographic-site search is allowed.
    let xy: Vec<[usize;2]>=(0..w*h).map(|j|[j%w,j/w]).collect();
    let nodes=closure(&sizes,&xy);
    let pre=sparse_collapse(&sizes,&nodes,&sampled_bands(&merge,&nodes,0));
    let output=merge.finish(&mut Workspace::new(&sizes));
    let mut live=0usize;
    let mut omitted_residual_error=0.0f32;
    for (q,&j) in nodes[0].iter().enumerate() {
        let [lo,hi]=bridge::hull(&merge,j)[0];
        let bounded=pre[q].clamp(lo,hi);
        assert_eq!(bounded.to_bits(),output[0][j].to_bits());
        let residual=output[0][j]-pre[q];
        if residual.abs()>0.01 {live+=1; omitted_residual_error=omitted_residual_error.max(residual.abs());}
    }
    assert!(live>0,"fixture never exercised the final hull clamp");
    assert!(omitted_residual_error>0.01,"zero-clamp-residual destroyer was not rejected");
}
