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
pub(crate) fn fixed_masks(w:usize,h:usize,origin_native:[isize;2])->Vec<Vec<f32>> {
    assert!(w>0 && h>0);
    SEGMENTS.iter().map(|&(a,b)|(0..h).flat_map(|y|(0..w).map(move|x|
        capsule_at(origin_native[0] as f32+2.0*x as f32+0.5,
            origin_native[1] as f32+2.0*y as f32+0.5,a,b))).collect()).collect()
}
mod independent_controls { include!(r"C:/dev/blog/death-of-software/projects/strehl/experiments/donor-consistency/independent-controls.rs"); }
