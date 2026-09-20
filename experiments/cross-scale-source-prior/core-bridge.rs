// Read-only test surface. No merge arithmetic or normal path is changed.
use super::BandMerge;
fn same(a:&[Vec<f32>],b:&[Vec<f32>])->bool {
    a.len()==b.len() && a.iter().zip(b).all(|(a,b)|a.len()==b.len()
        && a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits()))
}
/// Exact b0 weighted state, terminal weighted state, every mean/fallback sum,
/// and all input/per-level bounds. Coarse AC numerators/denominators may differ.
pub fn held_state_bit_exact(a:&BandMerge,b:&BandMerge)->bool {
    if a.planes!=b.planes || a.sizes!=b.sizes || a.frames!=b.frames {return false;}
    let terminal=a.sizes.len()-1;let p=a.planes;
    same(&a.num[..p],&b.num[..p]) && same(&a.den[..1],&b.den[..1])
        && same(&a.num[terminal*p..],&b.num[terminal*p..])
        && same(&a.den[terminal..],&b.den[terminal..])
        && same(&a.usum,&b.usum) && same(&a.lo,&b.lo) && same(&a.hi,&b.hi)
        && same(&a.lo_lv,&b.lo_lv) && same(&a.hi_lv,&b.hi_lv)
        && same(&a.sig_lv,&b.sig_lv)
}
