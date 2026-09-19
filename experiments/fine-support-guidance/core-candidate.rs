// Experimental fine-only intervention, compiled through the existing diagnostic
// feature. No candidate arithmetic or allocation occurs in Mode::Off.
use super::{AdmissionMode,BaseBand,BandMerge,Fallback,LevelSize,MergeConfig,SelectMode};
use crate::{boxfilter::box_mean,plane::PlaneGeometry};
use rayon::prelude::*;

pub const ENV:&str="STREHL_FINE_SUPPORT";
pub const RADIUS:usize=32;
#[derive(Clone,Copy,Debug,Eq,PartialEq,Default)]
pub enum Mode {#[default] Off,Radius32}
impl Mode {
    pub fn parse(value:&str)->Result<Self,String> {
        match value {"off"=>Ok(Self::Off),"radius32"=>Ok(Self::Radius32),
            _=>Err(format!("{ENV}: expected off or radius32, got {value:?}"))}
    }
}
pub fn environment_mode()->Mode {
    static MODE:std::sync::OnceLock<Mode>=std::sync::OnceLock::new();
    *MODE.get_or_init(||match std::env::var(ENV) {
        Err(std::env::VarError::NotPresent)=>Mode::Off,
        Ok(value)=>Mode::parse(&value).unwrap_or_else(|e|panic!("{e}")),
        Err(e)=>panic!("{ENV}: {e}"),
    })
}
pub(super) fn validate_config(mode:Mode,cfg:MergeConfig) {
    if mode==Mode::Off{return;}
    assert!(cfg.admission==AdmissionMode::HardFloor && cfg.select==SelectMode::SoftPower
        && cfg.base==BaseBand::Mean && cfg.fallback==Fallback::Mean && cfg.significance_scale==0.0,
        "radius32 diagnostic supports soft hard-floor admission, mean base/fallback, and no significance override");
}
#[derive(Clone,Debug,Default)]
pub(super) struct Scratch {energy:Vec<f32>,floor:Vec<f32>}

#[allow(clippy::too_many_arguments)]
pub(super) fn rewrite_weights(mode:Mode,energy:&[f32],variance:&[f32],size:LevelSize,
    beta:f32,gate:f32,exponent:f32,significance:f32,weights:&mut[f32],
    smooth_scratch:&mut[f32],pooled:&mut Scratch) {
    if mode==Mode::Off{return;}
    let n=size.pixels();
    assert_eq!(energy.len(),n);assert_eq!(variance.len(),n);assert_eq!(weights.len(),n);
    assert!(smooth_scratch.len()>=n && beta.is_finite() && beta>0.0 && gate.is_finite() && gate>0.0);
    let geometry=PlaneGeometry{width:size.width,height:size.height};
    pooled.energy.resize(n,0.0);pooled.floor.resize(n,0.0);
    box_mean(energy,geometry,RADIUS,&mut smooth_scratch[..n],&mut pooled.energy);
    // Weight storage is no longer needed until this hook returns, so it holds
    // the exact current injected floor while both physical fields are pooled.
    weights.par_iter_mut().zip(variance).for_each(|(f,v)| {
        assert!(v.is_finite() && *v>=0.0,"nonfinite/negative injected variance");
        *f=gate*beta*v.max(0.0);
    });
    box_mean(weights,geometry,RADIUS,&mut smooth_scratch[..n],&mut pooled.floor);
    weights.par_iter_mut().zip(&pooled.energy).zip(&pooled.floor).for_each(|((w,e),f)| {
        assert!(e.is_finite() && *e>=0.0 && f.is_finite() && *f>=0.0,"invalid pooled energy/floor");
        *w=super::select_weight((*e-*f).max(0.0),*f,exponent,significance);
    });
}

fn same(a:&[Vec<f32>],b:&[Vec<f32>])->bool {
    a.len()==b.len() && a.iter().zip(b).all(|(a,b)|a.len()==b.len()
        && a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits()))
}
/// Diagnostic assertion surface: all non-finest weighted accumulators, every
/// fallback sum, and all input/per-level hull data must remain identical.
pub fn non_finest_bit_exact(a:&BandMerge,b:&BandMerge)->bool {
    a.planes==b.planes && a.sizes==b.sizes && a.frames==b.frames
        && same(&a.num[a.planes..],&b.num[b.planes..]) && same(&a.den[1..],&b.den[1..])
        && same(&a.usum,&b.usum) && same(&a.lo,&b.lo) && same(&a.hi,&b.hi)
        && same(&a.lo_lv,&b.lo_lv) && same(&a.hi_lv,&b.hi_lv) && same(&a.sig_lv,&b.sig_lv)
}

/// One generated-operator control may inspect the exact current candidate
/// weights without constructing another merge implementation.
pub fn weights_from_fields(energy:&[f32],variance:&[f32],size:LevelSize,
    beta:f32,gate:f32,exponent:f32)->Vec<f32> {
    let mut weights=vec![0.0;size.pixels()];
    rewrite_weights(Mode::Radius32,energy,variance,size,beta,gate,exponent,0.0,
        &mut weights,&mut vec![0.0;size.pixels()],&mut Scratch::default());
    weights
}
