// Independent choices and literal support reference. Root alone builds/runs.
// Plain-included by independent-controls.rs; no RAW or new fixture family.

const OP_DN_TOL: f64 = 0.02;

fn op_error(a: &[f32], b: &[f32]) -> f64 {
    assert_eq!(a.len(), b.len());
    assert!(a.iter().chain(b).all(|x| x.is_finite()));
    a.iter().zip(b).map(|(x,y)| (*x as f64-*y as f64).abs()).fold(0.0, f64::max)
}
fn op_clamp(i: isize, n: usize) -> usize { i.max(0).min(n as isize-1) as usize }
fn op_reflect(i: isize, n: usize) -> usize {
    // Deliberate wrong boundary: reflect without repeating the edge pixel.
    if i<0 {(-i) as usize} else if i>=n as isize {(2*n as isize-2-i) as usize} else {i as usize}
}
fn op_variance(noise: &NoiseModel, g: f32) -> f64 {
    // Independent f64 assembly from the declared injected plane models.
    let a=(noise.plane(CfaPlane::G1).variance(g) as f64).sqrt();
    let b=(noise.plane(CfaPlane::G2).variance(g) as f64).sqrt();
    (a+b).powi(2)/4.0
}
fn op_affinity(noise: &NoiseModel, a: f32, b: f32) -> f64 {
    let v=op_variance(noise,a)+op_variance(noise,b);
    v/(v+(a as f64-b as f64).powi(2))
}
fn op_restrict_reference(p: &EdgePyramid, k: usize, x: &[f32], noise: &NoiseModel,
                         reflect: bool) -> Vec<f64> {
    let s=p.sizes[k]; let d=p.sizes[k+1]; let g=&p.guides[k];
    let coeff=[1.0,4.0,6.0,4.0,1.0];
    (0..d.pixels()).map(|j| {
        let cx=2*(j%d.width); let cy=2*(j/d.width);
        let mut numerator=0.0; let mut mass=0.0;
        for dy in -2isize..=2 { for dx in -2isize..=2 {
            let address=if reflect {op_reflect} else {op_clamp};
            let q=address(cy as isize+dy,s.height)*s.width+address(cx as isize+dx,s.width);
            let w=coeff[(dy+2) as usize]*coeff[(dx+2) as usize]
                *op_affinity(noise,g[cy*s.width+cx],g[q]);
            numerator+=w*x[q] as f64; mass+=w;
        }}
        numerator/mass
    }).collect()
}
fn op_expand_reference(p: &EdgePyramid, k: usize, x: &[f32], noise: &NoiseModel,
                       wrong_parity: bool) -> Vec<f64> {
    let s=p.sizes[k]; let d=p.sizes[k+1];
    // Enumerate coarse lattice points by their distance from the fine point.
    // This does not call the author's parity/support/address helpers.
    let kernel=|delta:isize| match delta.abs() {0=>6.0,1=>4.0,2=>1.0,_=>0.0};
    (0..s.pixels()).map(|j| {
        let fx=if wrong_parity {(j%s.width)^1} else {j%s.width};
        let fy=j/s.width; let mut numerator=0.0; let mut mass=0.0;
        for cy in (fy as isize/2-1)..=(fy as isize/2+1) {
            for cx in (fx as isize/2-1)..=(fx as isize/2+1) {
                let spatial=kernel(fx as isize-2*cx)*kernel(fy as isize-2*cy);
                if spatial==0.0 {continue;}
                let q=op_clamp(cy,d.height)*d.width+op_clamp(cx,d.width);
                let w=spatial*op_affinity(noise,p.guides[k][j],p.guides[k+1][q]);
                numerator+=w*x[q] as f64; mass+=w;
            }
        }
        numerator/mass
    }).collect()
}
fn op_reference_error(a: &[f32], b: &[f64]) -> f64 {
    assert_eq!(a.len(),b.len());
    assert!(b.iter().all(|x| x.is_finite()));
    a.iter().zip(b).map(|(x,y)| (*x as f64-y).abs()).fold(0.0,f64::max)
}
fn op_signal(w: usize, h: usize, variant: usize) -> Vec<f32> {
    (0..w*h).map(|j| {
        let x=j%w; let y=j/w;
        9500.0+((x*37+y*71+variant*137)%1009) as f32
            +if x>w/2 {1700.0} else {0.0}
            +if (x+2*y+variant)%17==0 {2100.0} else {0.0}
    }).collect()
}
fn op_membership(sizes: &[strehl_core::pyramid::LevelSize], value: f32) -> Vec<Vec<f32>> {
    sizes[..sizes.len()-1].iter().map(|s| vec![value;s.pixels()]).collect()
}

fn op_domain(w: usize, h: usize, ac: usize, noise: &NoiseModel) -> Value {
    let sizes=level_sizes(w,h,ac);
    assert_eq!(sizes.len(),ac+1,"requested AC support must actually exist");
    let guide=(0..w*h).map(|j| if j%w>=w/2+7 {9000.0} else {1000.0}).collect::<Vec<_>>();
    let p=EdgePyramid::new(&sizes,&guide,noise).unwrap();
    let mut roundtrips=Vec::new();
    let mut impulse=vec![0.0;w*h];
    for j in [0,w-1,(h-1)*w,w*h-1,(h/2)*w+w/2] {impulse[j]=14000.0;}
    for (name,signal) in [("high-dn",op_signal(w,h,0)),("impulse",impulse),
                           ("false-guide-constant",vec![5000.0;w*h])] {
        let bands=p.analyze(&signal).unwrap();
        let out=p.synthesize(&bands).unwrap(); let error=op_error(&out,&signal);
        assert!(error<=OP_DN_TOL,"{w}x{h} {name}: {error} DN");
        roundtrips.push(json!({"signal":name,"max_error_dn":error}));
    }
    // Uniform memberships and the all-zero fallback must give the direct mean.
    // Equal AC weights exercise averaging in the NEW basis, not an old output.
    let mut uniform=EdgeMerge::new(&sizes,3);
    let mut fallback=if ac==3 {Some(EdgeMerge::new(&sizes,3))} else {None};
    let mut direct=vec![vec![0.0f64;w*h];4];
    for source in 0..3 {
        let planes=(0..4).map(|c| op_signal(w,h,source+3*c)).collect::<Vec<_>>();
        for c in 0..4 {for j in 0..w*h {direct[c][j]+=planes[c][j] as f64/3.0;}}
        uniform.add(source,&planes,&op_membership(&sizes,1.0),&p).unwrap();
        if let Some(ref mut merge)=fallback {
            merge.add(source,&planes,&op_membership(&sizes,0.0),&p).unwrap();
        }
    }
    let mean=uniform.finish(&p).unwrap();
    let mean_error=(0..4).map(|c| op_reference_error(&mean.planes4[c],&direct[c])).fold(0.0,f64::max);
    assert!(mean_error<=OP_DN_TOL,"uniform {w}x{h}: {mean_error} DN");
    let fallback_error=fallback.map(|merge| {
        let result=merge.finish(&p).unwrap();
        let error=(0..4).map(|c|op_reference_error(&result.planes4[c],&direct[c])).fold(0.0,f64::max);
        assert!(error<=OP_DN_TOL); error
    });
    let mut constant=EdgeMerge::new(&sizes,2);
    for (source,value,weight) in [(0,1000.0,1.0),(1,9000.0,3.0)] {
        constant.add(source,&vec![vec![value;w*h];4],&op_membership(&sizes,weight),&p).unwrap();
    }
    let result=constant.finish(&p).unwrap();
    let const_error=result.planes4.iter().flatten().map(|v|(*v as f64-5000.0).abs()).fold(0.0,f64::max);
    let terminal_error=result.terminal4.iter().flatten().map(|v|(*v as f64-5000.0).abs()).fold(0.0,f64::max);
    assert!(const_error<=OP_DN_TOL&&terminal_error<=OP_DN_TOL,"terminal mean must not become weighted DC");
    // Compare the actual result to the wrong weighted-DC target, not a
    // constant against its own arithmetic definition.
    let distance_to_wrong_dc=result.planes4.iter().flatten()
        .map(|v|(*v as f64-7000.0).abs()).fold(f64::INFINITY,f64::min);
    assert!(distance_to_wrong_dc>1000.0);
    json!({"width":w,"height":h,"actual_ac":sizes.len()-1,"stencil_bytes":p.stencil_bytes(),
        "roundtrips":roundtrips,"uniform_direct_mean_max_error_dn":mean_error,
        "zero_weight_fallback_max_error_dn":fallback_error,
        "unequal_ac_weights_constant_error_dn":const_error,"terminal_mean_error_dn":terminal_error,
        "distance_to_wrong_weighted_dc_dn":distance_to_wrong_dc})
}

fn op_small_references(noise: &NoiseModel) -> Value {
    let (w,h)=(81,73); let sizes=level_sizes(w,h,3);
    let guide=(0..w*h).map(|j| if j%w<w/2 {1000.0} else {9000.0}).collect::<Vec<_>>();
    let p=EdgePyramid::new(&sizes,&guide,noise).unwrap();
    let null=EdgePyramid::new(&sizes,&vec![5000.0;w*h],noise).unwrap();
    let mut levels_checked=Vec::new();
    for k in 0..3 {
        let s=sizes[k]; let d=sizes[k+1];
        let x=op_signal(s.width,s.height,k); let y=op_signal(d.width,d.height,k+4);
        let r=op_reference_error(&p.reduce(k,&x).unwrap(),&op_restrict_reference(&p,k,&x,noise,false));
        let e=op_reference_error(&p.expand(k,&y).unwrap(),&op_expand_reference(&p,k,&y,noise,false));
        assert!(r<=OP_DN_TOL&&e<=OP_DN_TOL,"literal f64 support {k}: R {r}, E {e}");
        for row in &p.restriction[k] {assert!(row.iter().all(|v|v.is_finite()&&*v>=0.0));
            assert!((row.iter().map(|v|*v as f64).sum::<f64>()-1.0).abs()<2e-6);}
        for row in &p.expansion[k] {assert!(row.iter().all(|v|v.is_finite()&&*v>=0.0));
            assert!((row.iter().map(|v|*v as f64).sum::<f64>()-1.0).abs()<2e-6);}
        let nr=op_reference_error(&null.reduce(k,&x).unwrap(),&op_restrict_reference(&null,k,&x,noise,false));
        let ne=op_reference_error(&null.expand(k,&y).unwrap(),&op_expand_reference(&null,k,&y,noise,false));
        assert!(nr<=OP_DN_TOL&&ne<=OP_DN_TOL);
        levels_checked.push(json!({"level":k,"restriction_error_dn":r,"expansion_error_dn":e,
            "constant_guide_restriction_error_dn":nr,"constant_guide_expansion_error_dn":ne}));
    }
    let mut corner=vec![0.0;w*h]; corner[0]=14000.0;
    let wrong_boundary=op_reference_error(&null.reduce(0,&corner).unwrap(),
        &op_restrict_reference(&null,0,&corner,noise,true));
    let coarse=op_signal(sizes[1].width,sizes[1].height,0);
    let wrong_parity=op_reference_error(&null.expand(0,&coarse).unwrap(),
        &op_expand_reference(&null,0,&coarse,noise,true));
    assert!(wrong_boundary>1.0&&wrong_parity>1.0,"literal support destroyers must be live");
    let bands=p.analyze(&guide).unwrap();
    let wrong_guide=op_error(&null.synthesize(&bands).unwrap(),&guide);
    assert!(wrong_guide>1.0,"synthesis with a mismatched guide must actually destroy this signal");
    assert!(p.synthesize(&bands[..bands.len()-1]).is_err(),"missing band must reject");
    let mut zeroed=bands.clone(); zeroed[0].fill(0.0);
    let zeroed_error=op_error(&p.synthesize(&zeroed).unwrap(),&guide);
    // The guide's own step may have tiny AC because conductance isolates it.
    // Instead erase a rich high-DN band's coefficients to prove sensitivity.
    let rich=op_signal(w,h,0); let mut erased=p.analyze(&rich).unwrap(); erased[0].fill(0.0);
    let erased_error=op_error(&p.synthesize(&erased).unwrap(),&rich);
    assert!(erased_error>1.0,"missing detail with valid shape must not pass roundtrip");
    json!({"f64_levels":levels_checked,"wrong_reflected_boundary_error_dn":wrong_boundary,
        "wrong_expansion_parity_error_dn":wrong_parity,"wrong_synthesis_guide_error_dn":wrong_guide,
        "missing_band_rejected":true,"zeroed_step_band_error_dn":zeroed_error,
        "zeroed_rich_band_error_dn":erased_error,
        "reference_scope":"f64 taps independently enumerated from exact stored f32 guide levels; no calibration claim"})
}

#[test]
#[ignore]
fn b_independent_operator_controls() {
    let noise=profile::noise_model_for("ILCE-7CM2",Some(100.0),levels());
    assert!(noise.is_trustworthy()&&noise.prnu().is_none());
    let reference=op_small_references(&noise);
    let domains=[(80,72,3),(81,73,3),(1024,1024,7),(1031,1029,7)].into_iter()
        .map(|(w,h,ac)|op_domain(w,h,ac,&noise)).collect::<Vec<_>>();
    write(&output().join("operator.json"),&json!({"passed":true,"max_error_allowance_dn":OP_DN_TOL,
        "domains":domains,"independent_support":reference,
        "scope":"generated f32 operator arithmetic only; no seven-band occlusion, RAW or image-quality qualification"}));
}
