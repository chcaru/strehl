pub(crate) const SEGMENTS:[([f32;2],[f32;2]);3]=[
    ([2624.0,2906.0],[2602.0,2945.0]),
    ([3080.0,2150.0],[3102.0,2203.0]),
    ([3240.0,2070.0],[3240.0,2070.0]),
];
pub(crate) fn capsule_at(x:f32,y:f32,start:[f32;2],end:[f32;2])->f32 {
    assert!([x,y,start[0],start[1],end[0],end[1]].iter().all(|v|v.is_finite()));
    let (vx,vy)=(end[0]-start[0],end[1]-start[1]);let norm=vx*vx+vy*vy;
    // Ordinary projection, not a rounded or snapped native coordinate.
    let t=if norm>0.0 {(((x-start[0])*vx+(y-start[1])*vy)/norm).clamp(0.0,1.0)} else {0.0};
    let d=(x-(start[0]+t*vx)).hypot(y-(start[1]+t*vy));
    if d<=16.0 {1.0} else if d>=24.0 {0.0} else {
        let u=(d-16.0)/8.0;1.0-u*u*(3.0-2.0*u)
    }
}
/// Native origin is relative to the original baseline OUTPUT, not the sensor.
/// Common four-plane mask is evaluated at the native quad centre (2x+.5,2y+.5).
pub(crate) fn fixed_masks(w:usize,h:usize,origin_native:[isize;2])->Vec<Vec<f32>> {
    assert!(w>0 && h>0);
    SEGMENTS.iter().map(|&(a,b)|(0..h).flat_map(|y|(0..w).map(move|x|
        capsule_at(origin_native[0] as f32+2.0*x as f32+0.5,
            origin_native[1] as f32+2.0*y as f32+0.5,a,b))).collect()).collect()
}

use strehl_core::pyramid::{level_sizes,Pyramid,Workspace};
use strehl_core::pyramid::donor_consistency_diagnostic::DonorBlend;
fn main() {
 let sizes=level_sizes(3460,2306,7);let masks=fixed_masks(3460,2306,[0,0]);
 let mix=DonorBlend::new(&sizes,4,&masks);let mut ws=Workspace::new(&sizes);
 let points=[("facet-core",2624,2906),("facet-fan",2602,2945),
 ("dark-core",3080,2150),("dark-fan",3102,2203),("nearby",3240,2070)];
 for k in 0..sizes.len()-1 {
  let mut p=Pyramid::zeros(&sizes);p.level_mut(k).copy_from_slice(mix.coverage().level(k));
  let up=p.collapse(&mut ws);
  for &(name,x,y) in &points {let j=(y/2)*3460+x/2;
   println!("{}",serde_json::json!({"point":name,"output_native_xy":[x,y],
    "level":k,"effective_weight_for_constant_coefficient":up[j],
    "native_mask":mix.coverage().level(0)[j]}));
  }
 }
}
