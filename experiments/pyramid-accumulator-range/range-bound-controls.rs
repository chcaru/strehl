// Root executes; independently reviewed before running. Child of pyramid.
// Prescribed coefficients/weights below test the REAL accumulate/absorb/finish
// arithmetic, not whether focus selection or a camera would produce the pair.
use super::*;

const N: usize = 16;
fn cfg(select: SelectMode, base: BaseBand) -> MergeConfig {
    MergeConfig { bands:1, exponent:2.0, sharpen_per_octave:1.0,
        select, base, admission:AdmissionMode::HardFloor, hull:Hull::Unclamped,
        fallback:Fallback::Mean, mean_coarse:0, significance_scale:0.0,
        ..MergeConfig::default() }
}
fn prescribed(merge:&mut BandMerge, coefficients:[f32;4], weight:f32) {
    let mut cache=PlaneCache::new(&merge.sizes,4);
    for (p,c) in cache.pyramids.iter_mut().zip(coefficients) {p.level_mut(0).fill(c);}
    cache.valid=true;
    let zero=vec![0.;N*N];let refs=[zero.as_slice();4];
    merge.accumulate_level(0,&refs,&mut cache,&vec![weight;N*N]);
    // The terminal residual is zero in this arithmetic-only fixture.
    merge.frames+=1;
}
fn bits(a:&[Vec<f32>],b:&[Vec<f32>]) -> bool {
    a.len()==b.len() && a.iter().zip(b).all(|(a,b)|a.len()==b.len()
        && a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits()))
}

#[test]
fn range_01_peak_1024_serial_and_absorb_are_finite() {
    let weight=80_f32.exp();
    let values=[65535.,-65535.,32767.5,-32767.5];
    assert!(!(weight*values[0]).is_finite(),"legacy destroyer unexercised");
    let mut serial=BandMerge::new(N,N,4,cfg(SelectMode::SoftPower,BaseBand::Mean));
    let mut chunks=BandMerge::new(N,N,4,serial.cfg);
    for _ in 0..32 {
        let mut part=BandMerge::new(N,N,4,serial.cfg);
        for _ in 0..32 {prescribed(&mut serial,values,weight);prescribed(&mut part,values,weight);}
        chunks.absorb(&part);
    }
    for merge in [&serial,&chunks] {
        assert_eq!(merge.frames,1024);
        assert!(merge.num.iter().chain(&merge.den).chain(&merge.usum).flatten().all(|v|v.is_finite()));
        let out=merge.finish(&mut Workspace::new(&merge.sizes));
        for (image,expected) in out.iter().zip(values) {
            assert!(image.iter().all(|v|v.is_finite() && (*v-expected).abs()<2.0),
                "1024-term range error exceeds 2 DN (3.1e-5 of bounded full scale)");
        }
    }
}

#[test]
fn range_02_clamped_floor_tiny_signed_products_have_small_absolute_error() {
    let weight=(-80_f32).exp();
    let values=[1e-6_f32,-1e-6,1e-4,-1e-4];
    let mut merge=BandMerge::new(N,N,4,cfg(SelectMode::SoftPower,BaseBand::Mean));
    for _ in 0..8 {prescribed(&mut merge,values,weight);}
    assert!(merge.num.iter().flatten().any(|v|v.is_subnormal()),"tiny-product branch unexercised");
    let out=merge.finish(&mut Workspace::new(&merge.sizes));
    for (image,expected) in out.iter().zip(values) {
        assert!(image.iter().all(|v|v.is_finite() && (*v-expected).abs()<1.1e-5),
            "subnormal error exceeds declared absolute DN bound");
    }
    // The bound is NOT a promise for arbitrary p=1/2 weights below exp(-80).
}

fn source(low:f32,high:f32)->Vec<Vec<f32>> {
    [0.75_f32,1.,0.875,0.5].into_iter().map(|g|
        (0..N*N).map(|i|g*if (i%N+i/N)%2==0 {low}else{high}).collect()).collect()
}
// Independent legacy f32 arithmetic oracle. Single-frame actual consumers
// expose the unchanged weights; no new num representation is read by it.
fn legacy_control(select:SelectMode,base:BaseBand) {
    let config=cfg(select,base);let sizes=level_sizes(N,N,config.bands);
    let frames=[source(100.,2100.),source(400.,3200.),source(200.,1800.)];
    let mut merge=BandMerge::new(N,N,4,config);
    let mut ws=FrameWorkspace::new(&sizes,4);
    let mut numerator:Vec<Vec<f32>>=(0..sizes.len()*4).map(|i|vec![0.;sizes[i/4].pixels()]).collect();
    let mut means=numerator.clone();
    let mut denominator:Vec<Vec<f32>>=sizes.iter().map(|s|vec![0.;s.pixels()]).collect();
    let mut saw_weight=false;let mut saw_distinct=false;
    let mut previous:Option<Vec<Vec<f32>>>=None;
    for frame in &frames {
        let refs:Vec<&[f32]>=frame.iter().map(Vec::as_slice).collect();
        let luma:Vec<f32>=frame[1].iter().zip(&frame[2]).map(|(a,b)|(a+b)*0.5).collect();
        let variance=vec![4.;N*N];
        ws.next_frame();merge.add_frame(&refs,&luma,&variance,&mut ws);
        let mut one=BandMerge::new(N,N,4,config);
        let mut one_ws=FrameWorkspace::new(&sizes,4);
        one_ws.next_frame();one.add_frame(&refs,&luma,&variance,&mut one_ws);
        if let Some(old)=&previous {saw_distinct|=!bits(old,&one.den);}
        previous=Some(one.den.clone());
        let mut pyramids:Vec<Pyramid>=(0..4).map(|_|Pyramid::zeros(&sizes)).collect();
        for c in 0..4 {pyramids[c].build(&frame[c],&mut Workspace::new(&sizes));}
        for k in 0..sizes.len() {for j in 0..sizes[k].pixels() {
            let weight=one.den[k][j];saw_weight|=weight>0.;
            let old=denominator[k][j];
            for c in 0..4 {let i=k*4+c;let coefficient=pyramids[c].level(k)[j];
                means[i][j]+=coefficient;
                match select {
                    SelectMode::SoftPower=>numerator[i][j]+=weight*coefficient,
                    SelectMode::HardMax=>if weight>old {numerator[i][j]=coefficient;},
                }
            }
            denominator[k][j]=match select {SelectMode::SoftPower=>old+weight,SelectMode::HardMax=>old.max(weight)};
        }}
    }
    assert!(saw_weight && saw_distinct,"source-selection branch unexercised");
    assert!(numerator.iter().flatten().all(|v|v.is_finite()),"legacy finite control overflowed");
    assert!(bits(&merge.den,&denominator),"denominator/weights changed");
    assert!(bits(&merge.usum,&means),"unweighted fallback changed");
    let kb=sizes.len()-1;
    match base {
        BaseBand::Mean=>assert!(merge.den[kb].iter().all(|v|*v==0.)),
        BaseBand::WeightedFromCoarsest=>assert!(merge.den[kb].iter().any(|v|*v>0.),"sharp-base branch unexercised"),
    }
    let expected:Vec<Vec<f32>>=(0..4).map(|c| {
        let mut p=Pyramid::zeros(&sizes);
        for k in 0..sizes.len() {for j in 0..sizes[k].pixels() {
            let i=k*4+c;
            p.level_mut(k)[j]=if denominator[k][j]>0. {match select {
                SelectMode::SoftPower=>numerator[i][j]/denominator[k][j],
                SelectMode::HardMax=>numerator[i][j],
            }}else{means[i][j]*(1.0/frames.len() as f32)};
        }}
        p.collapse(&mut Workspace::new(&sizes))
    }).collect();
    let actual=merge.finish(&mut Workspace::new(&sizes));
    assert!(bits(&actual,&expected),"finite normal operator changed from legacy bits");
}

#[test]
fn range_03_normal_soft_mean_base_matches_legacy_bits() {
    legacy_control(SelectMode::SoftPower,BaseBand::Mean);
}
#[test]
fn range_04_hard_max_both_base_modes_match_legacy_bits() {
    for base in [BaseBand::Mean,BaseBand::WeightedFromCoarsest] {legacy_control(SelectMode::HardMax,base);}
}
#[test]
fn range_05_weighted_sharp_base_matches_legacy_bits() {
    legacy_control(SelectMode::SoftPower,BaseBand::WeightedFromCoarsest);
}
