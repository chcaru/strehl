// Binary residual activation over normalized actual coefficients, before collapse/hull.
use super::{AdmissionMode,BandMerge,BaseBand,Fallback,Hull,Pyramid,SelectMode,Workspace};

pub fn mix_scalar(parent:f32,own:f32,mask:f32)->f32 {
    assert!(parent.is_finite() && own.is_finite() && (mask==0.0 || mask==1.0));
    if mask==0.0 {parent} else {parent+mask*(own-parent)}
}

fn held(merge:&BandMerge) {
    assert!(merge.frames>0 && merge.cfg.select==SelectMode::SoftPower
        && merge.cfg.fallback==Fallback::Mean && merge.cfg.base==BaseBand::Mean
        && merge.cfg.hull==Hull::InputRange && merge.cfg.admission==AdmissionMode::HardFloor);
}
pub fn resolved(merge:&BandMerge,c:usize)->Pyramid {
    held(merge);assert!(c<merge.planes);
    let mut p=Pyramid::zeros(&merge.sizes);let inv=1.0/merge.frames as f32;
    for k in 0..merge.sizes.len() {let i=k*merge.planes+c;
        for (j,v) in p.level_mut(k).iter_mut().enumerate() {
            *v=if merge.den[k][j]>0.0 {super::resolve_soft_numerator(merge.num[i][j],merge.den[k][j])} else {merge.usum[i][j]*inv};
            assert!(v.is_finite());
        }
    }p
}
pub fn mixed_coefficients(baseline:&BandMerge,own_rb:[&BandMerge;2],
    masks:&[Vec<Vec<f32>>;2])->[Pyramid;2] {
    held(baseline);assert_eq!(baseline.planes,4);let nb=baseline.sizes.len()-1;
    std::array::from_fn(|i| {
        let own=own_rb[i];held(own);
        assert!(own.planes==1 && own.sizes==baseline.sizes && own.frames==baseline.frames);
        assert_eq!(masks[i].len(),nb);
        let mut out=resolved(baseline,[0,3][i]);let candidate=resolved(own,0);
        assert!(candidate.level(nb).iter().zip(out.level(nb)).all(|(a,b)|a.to_bits()==b.to_bits()),
            "terminal means differ");
        for k in 0..nb {
            assert_eq!(masks[i][k].len(),out.level(k).len());
            for ((b,&c),&a) in out.level_mut(k).iter_mut().zip(candidate.level(k)).zip(&masks[i][k]) {
                assert!(a==0.0 || a==1.0,"binary guard mask required");
                *b=mix_scalar(*b,c,a);
                // Literal zero avoids subtract/add rounding on canonical coefficients.
                assert!(b.is_finite());
            }
        }out
    })
}
pub fn finish_guarded(baseline:&BandMerge,own_rb:[&BandMerge;2],
    masks:&[Vec<Vec<f32>>;2],ws:&mut Workspace)->Vec<Vec<f32>> {
    let mixed=mixed_coefficients(baseline,own_rb,masks);
    let mut output=baseline.finish(ws);
    for (i,c) in [0,3].into_iter().enumerate() {
        if masks[i].iter().all(|v|v.iter().all(|&a|a==0.0)) {continue;}
        output[c]=mixed[i].collapse(ws);
        for ((v,&lo),&hi) in output[c].iter_mut().zip(&baseline.lo[c]).zip(&baseline.hi[c]) {*v=v.clamp(lo,hi);}
        assert!(output[c].iter().all(|v|v.is_finite()));
    }output
}
