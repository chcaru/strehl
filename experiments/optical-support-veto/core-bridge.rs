// Read-only state invariant. Root integrates only under existing experimental feature.
use super::BandMerge;
fn same(a:&[Vec<f32>],b:&[Vec<f32>])->bool {
    a.len()==b.len()&&a.iter().zip(b).all(|(a,b)|a.len()==b.len()
        &&a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits()))
}
pub fn held_state_exact(a:&BandMerge,b:&BandMerge)->bool {
    if a.planes!=b.planes||a.sizes!=b.sizes||a.frames!=b.frames{return false;}
    let terminal=a.sizes.len()-1;let p=a.planes;
    same(&a.num[terminal*p..],&b.num[terminal*p..])&&same(&a.den[terminal..],&b.den[terminal..])
        &&same(&a.usum,&b.usum)&&same(&a.lo,&b.lo)&&same(&a.hi,&b.hi)
        &&same(&a.lo_lv,&b.lo_lv)&&same(&a.hi_lv,&b.hi_lv)&&same(&a.sig_lv,&b.sig_lv)
}
