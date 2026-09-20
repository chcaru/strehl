// Test-only access to the existing native band consumer. No alternate merge arithmetic.
use super::{AdmissionMode, BandMerge, BaseBand, Fallback, FrameWorkspace, Hull,
    LevelSize, MergeConfig, SelectMode};

pub struct Fields {
    pub energy: Vec<Vec<f32>>,
    pub floor: Vec<Vec<f32>>,
    pub weights: Vec<Vec<f32>>,
}
fn supported(cfg: MergeConfig) {
    assert!(cfg.select == SelectMode::SoftPower && cfg.fallback == Fallback::Mean
        && cfg.base == BaseBand::Mean && cfg.hull == Hull::InputRange
        && cfg.admission == AdmissionMode::HardFloor,
        "R/B experiment requires held SoftPower / mean / input hull modes");
}
pub fn fields_from_energy(sizes: &[LevelSize], cfg: MergeConfig,
    energy: Vec<Vec<f32>>, floor: Vec<Vec<f32>>) -> Fields {
    supported(cfg);
    let nb = sizes.len()-1;
    assert_eq!(energy.len(), nb); assert_eq!(floor.len(), nb);
    let weights = (0..nb).map(|k| {
        assert_eq!(energy[k].len(), sizes[k].pixels());
        assert_eq!(floor[k].len(), sizes[k].pixels());
        assert!(energy[k].iter().chain(&floor[k]).all(|v| v.is_finite() && *v>=0.0));
        let averaged = k+cfg.mean_coarse>=nb;
        let exponent = cfg.exponent_at(k,nb);
        let r_floor = super::significance_floor(cfg.gate)*cfg.significance_scale;
        energy[k].iter().zip(&floor[k]).map(|(&e,&f)| {
            let w = if averaged {0.0} else {super::select_weight((e-f).max(0.0),f,exponent,r_floor)};
            assert!(w.is_finite() && w>=0.0); w
        }).collect()
    }).collect();
    Fields {energy,floor,weights}
}
/// Retained actual guide and Gaussian variance, with the production multiplication order.
pub fn canonical_fields(merge: &BandMerge, ws: &FrameWorkspace, beta: Option<&[f32]>) -> Fields {
    supported(merge.cfg);
    let nb=merge.sizes.len()-1;
    let energy=(0..nb).map(|k| super::correction_variance_diagnostic::energy(
        ws.luma.level(k),merge.sizes[k])).collect();
    let floor=(0..nb).map(|k| {
        let b=BandMerge::beta_for(&merge.gain,beta,k);
        ws.var.level(k).iter().map(|v| merge.cfg.gate*b*v.max(0.0)).collect()
    }).collect();
    fields_from_energy(&merge.sizes,merge.cfg,energy,floor)
}
/// Same accumulation, mean base, and input bounds as add_frame_with_gain.
/// Only the precomputed AC weights may differ. Workspace invalidation is mandatory.
pub fn add_fields(merge: &mut BandMerge, planes: &[&[f32]], fields: &Fields, ws: &mut FrameWorkspace) {
    supported(merge.cfg);
    assert_eq!(planes.len(),merge.planes);
    let n=merge.sizes[0].pixels();let nb=merge.sizes.len()-1;
    assert!(planes.iter().all(|p| p.len()==n && p.iter().all(|v|v.is_finite())));
    assert_eq!(fields.weights.len(),nb);
    ws.next_frame();
    for k in 0..nb {
        assert_eq!(fields.weights[k].len(),merge.sizes[k].pixels());
        assert!(fields.weights[k].iter().all(|v|v.is_finite() && *v>=0.0));
        merge.accumulate_level(k,planes,&mut ws.plane,&fields.weights[k]);
    }
    ws.coarse[..merge.sizes[nb].pixels()].fill(0.0);
    merge.accumulate_level(nb,planes,&mut ws.plane,&ws.coarse[..merge.sizes[nb].pixels()]);
    for c in 0..merge.planes {for j in 0..n {
        merge.lo[c][j]=merge.lo[c][j].min(planes[c][j]);
        merge.hi[c][j]=merge.hi[c][j].max(planes[c][j]);
    }}
    assert!(merge.num.iter().chain(&merge.usum).chain(&merge.den)
        .all(|v|v.iter().all(|x|x.is_finite())),"nonfinite native band accumulation");
    merge.frames+=1;
}
pub fn terminal_means(merge: &BandMerge) -> Vec<Vec<f32>> {
    supported(merge.cfg);assert!(merge.frames>0);
    let kb=merge.sizes.len()-1;let inv=1.0/merge.frames as f32;
    assert!(merge.den[kb].iter().all(|&v|v==0.0));
    (0..merge.planes).map(|c| merge.usum[kb*merge.planes+c].iter().map(|v|v*inv).collect()).collect()
}
