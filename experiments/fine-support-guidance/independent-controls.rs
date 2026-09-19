// One fixed operator control. This is not a quality or sensor-calibration gate.
use super::{measure_fields,Fields};
use strehl_core::{plane::PlaneGeometry,pyramid::{level_sizes,correction_variance_diagnostic as actual}};

fn arrays(f:&Fields)->[&[f32];5] {
    [&f.laplacian0,&f.energy0,&f.floor0,&f.pooled_energy0,&f.pooled_floor0]
}
fn close(a:f32,b:f32) {assert!((a-b).abs()<=2e-6*a.abs().max(b.abs()).max(1.0),"{a} versus {b}");}
fn direct_box(v:&[f32],g:PlaneGeometry,x:usize,y:usize)->f32 {
    let mut sum=0.0f64;let mut n=0usize;
    for yy in y.saturating_sub(32)..=(y+32).min(g.height-1) {
        for xx in x.saturating_sub(32)..=(x+32).min(g.width-1) {sum+=f64::from(v[yy*g.width+xx]);n+=1;}
    }
    (sum/n as f64) as f32
}
fn crop(v:&[f32],g:PlaneGeometry,x0:usize,y0:usize,s:PlaneGeometry)->Vec<f32> {
    let mut out=Vec::with_capacity(s.pixels());
    for y in 0..s.height {out.extend_from_slice(&v[(y0+y)*g.width+x0..(y0+y)*g.width+x0+s.width]);}
    out
}

#[test]
fn independent_fixed_support_phase_floor_and_pooling() {
    let g=PlaneGeometry{width:257,height:251};let s=PlaneGeometry{width:211,height:197};
    let beta=0.875f32;let gate=2.0f32;
    let luma=(0..g.height).flat_map(|y|(0..g.width).map(move|x| {
        let detail=((17*x+23*y+3*x*y)%97) as f32-48.0;
        1000.0+0.7*detail+60.0*((x as f32)*0.13+(y as f32)*0.17).sin()
    })).collect::<Vec<_>>();
    let variance=(0..g.height).flat_map(|y|(0..g.width).map(move|x|
        16.0+(x%41) as f32*0.25+(y%37) as f32*0.5)).collect::<Vec<_>>();
    let before_luma=luma.iter().map(|v|v.to_bits()).collect::<Vec<_>>();
    let before_variance=variance.iter().map(|v|v.to_bits()).collect::<Vec<_>>();
    let full=measure_fields(&luma,&variance,g,beta,gate).unwrap();
    let lap=actual::laplacian(&luma,&level_sizes(g.width,g.height,1));
    let energy=actual::energy(&lap[0],strehl_core::pyramid::LevelSize{width:g.width,height:g.height});
    assert!(full.laplacian0.iter().zip(&lap[0]).all(|(a,b)|a.to_bits()==b.to_bits()));
    assert!(full.energy0.iter().zip(&energy).all(|(a,b)|a.to_bits()==b.to_bits()));
    for (&floor,&v) in full.floor0.iter().zip(&variance) {assert_eq!(floor.to_bits(),(gate*beta*v).to_bits());}
    assert!(full.energy0.iter().any(|v|*v>1.0));
    assert!(full.energy0.iter().zip(&full.pooled_energy0).any(|(a,b)|(a-b).abs()>1.0));
    let points=[(0,0),(1,2),(31,32),(32,31),(96,105),(128,125),(224,218),(255,249),(256,250)];
    let mut box_checks=0usize;
    for (x,y) in points {
        close(full.pooled_energy0[y*g.width+x],direct_box(&full.energy0,g,x,y));
        close(full.pooled_floor0[y*g.width+x],direct_box(&full.floor0,g,x,y));box_checks+=2;
    }
    let even=measure_fields(&crop(&luma,g,18,22,s),&crop(&variance,g,18,22,s),s,beta,gate).unwrap();
    let odd=measure_fields(&crop(&luma,g,19,22,s),&crop(&variance,g,19,22,s),s,beta,gate).unwrap();
    let mut crop_checks=0usize;let mut phase_mismatches=0usize;
    for y in 48..s.height-48 {for x in 48..s.width-48 {
        let local=y*s.width+x;let global=(y+22)*g.width+x+18;
        for (f,e) in arrays(&full).into_iter().zip(arrays(&even)) {close(f[global],e[local]);crop_checks+=1;}
        if (odd.laplacian0[local]-full.laplacian0[(y+22)*g.width+x+19]).abs()>1e-3 {phase_mismatches+=1;}
    }}
    assert!(phase_mismatches>1000,"odd-quad crop did not exercise the reduction-phase failure");
    let scaled_luma=luma.iter().map(|v|2.0*v).collect::<Vec<_>>();
    let scaled_var=variance.iter().map(|v|4.0*v).collect::<Vec<_>>();
    let scaled=measure_fields(&scaled_luma,&scaled_var,g,beta,gate).unwrap();
    for (index,(a,b)) in arrays(&full).into_iter().zip(arrays(&scaled)).enumerate() {
        let factor=if index==0 {2.0} else {4.0};
        assert_eq!(a.len(),g.pixels());assert_eq!(b.len(),g.pixels());
        for (&x,&y) in a.iter().zip(b) {assert!(x.is_finite() && y.is_finite());close(factor*x,y);}
    }
    let flat=measure_fields(&vec![1024.0;g.pixels()],&vec![16.0;g.pixels()],g,beta,gate).unwrap();
    assert!(flat.laplacian0.iter().chain(&flat.energy0).chain(&flat.pooled_energy0).all(|v|*v==0.0));
    assert!(flat.floor0.iter().chain(&flat.pooled_floor0).all(|v|*v==28.0));
    assert!(measure_fields(&luma[..luma.len()-1],&variance,g,beta,gate).is_err());
    assert!(measure_fields(&luma,&variance,g,0.0,gate).is_err());
    let mut invalid=luma.clone();invalid[31]=f32::NAN;
    assert!(measure_fields(&invalid,&variance,g,beta,gate).is_err());
    let mut invalid_var=variance.clone();invalid_var[17]=-1.0;
    assert!(measure_fields(&luma,&invalid_var,g,beta,gate).is_err());
    assert_eq!(before_luma,luma.iter().map(|v|v.to_bits()).collect::<Vec<_>>());
    assert_eq!(before_variance,variance.iter().map(|v|v.to_bits()).collect::<Vec<_>>());
    eprintln!("FINE_SUPPORT_OPERATOR direct_box_checks={box_checks}, even_crop_field_checks={crop_checks}, odd_phase_mismatches={phase_mismatches}, scaling_values={}, flat_energy_zero=true, flat_floor=28, source_unchanged=true",g.pixels()*5);
}
