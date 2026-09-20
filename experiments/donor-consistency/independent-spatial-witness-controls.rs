use super::*;
use std::collections::BTreeMap;
use strehl_core::pyramid::donor_consistency_diagnostic::{SpatialDonor,
    AttributionWindow as Window,SpatialWitnessField as Field,
    observe_spatial_source,observe_spatial_finish};

type Records=BTreeMap<(String,usize,usize),Vec<f32>>;
fn windows()->[Window;3] {[Window{x:0,y:0,width:W,height:H},
    Window{x:5,y:7,width:33,height:29},Window{x:6,y:8,width:31,height:27}]}
fn read(r:&Records,f:Field,c:usize)->&[f32] {r.get(&(format!("{f:?}"),c,0)).unwrap()}
fn insert(r:&mut Records,f:Field,c:usize,w:usize,v:&[f32]) {
    let window=windows()[w];assert!(c<4);assert_eq!(v.len(),window.width*window.height);
    assert!(v.iter().all(|v|v.is_finite()));
    assert!(r.insert((format!("{f:?}"),c,w),v.to_vec()).is_none());
}
fn cropped_exact(r:&Records,fields:usize) {
    assert_eq!(r.len(),fields*4*3);
    for ((name,c,w),v) in r {let all=&r[&(name.clone(),*c,0)];let b=windows()[*w];
        let expected=(b.y..b.y+b.height).flat_map(|y|
            all[y*W+b.x..y*W+b.x+b.width].iter().copied()).collect::<Vec<_>>();
        assert_eq!(hash(v),hash(&expected));
    }
}
fn source_record(p:&[Vec<f32>])->Records {
    let sizes=level_sizes(W,H,3);let mut r=Records::new();
    let errors=observe_spatial_source(&sizes,p,&windows(),&mut Workspace::new(&sizes),
        |f,c,w,v|insert(&mut r,f,c,w,v));
    assert!(errors.iter().all(|v|v.is_finite() && *v<=0.02));cropped_exact(&r,3);r
}
fn finish_record(base:&BandMerge,donor:&SpatialDonor)->Records {
    let sizes=level_sizes(W,H,3);let mut r=Records::new();
    let s=observe_spatial_finish(base,donor,&windows(),&mut Workspace::new(&sizes),
        |f,c,w,v|insert(&mut r,f,c,w,v));
    for errors in [s.baseline_sum_max_abs,s.mixed_sum_max_abs,s.baseline_hull_sum_max_abs,s.mixed_hull_sum_max_abs] {
        assert!(errors.iter().all(|v|v.is_finite() && *v<=0.02));
    }
    cropped_exact(&r,13+donor.masks().len());r
}
fn parts(p:&Pyramid)->(Vec<f32>,Vec<f32>) {
    let sizes=p.sizes();let mut a=p.clone();a.level_mut(sizes.len()-1).fill(0.0);
    let mut b=Pyramid::zeros(sizes);b.level_mut(sizes.len()-1).copy_from_slice(p.level(sizes.len()-1));
    (a.collapse(&mut Workspace::new(sizes)),b.collapse(&mut Workspace::new(sizes)))
}
fn compare(r:&Records,f:Field,c:usize,v:&[f32])->f32 {
    let error=worst(read(r,f,c),v);assert!(error<=0.003,"{f:?} plane{c}: {error}DN");error
}

#[test]
fn independent_spatial_witness_fields_and_neutrality() {
    let (raw,frames)=fixtures();let raw_before=raw.clone();let hashes_before=hashes(&frames);
    let sizes=level_sizes(W,H,3);let baseline=merge(&frames);
    let ordinary=baseline.finish(&mut Workspace::new(&sizes));let coeff=resolved_coefficients(&baseline);
    let original=frames.iter().map(|p|pyramids(p)).collect::<Vec<_>>();
    let source_parts=original.iter().map(|ps|ps.iter().map(parts).collect::<Vec<_>>()).collect::<Vec<_>>();
    let base_parts=coeff.iter().map(parts).collect::<Vec<_>>();
    let mut field_error=0.0f32;let mut source_identity_error=0.0f64;let mut live_base_difference=0.0f32;
    for source in 0..3 {let r=source_record(&frames[source]);
        for c in 0..4 {
            assert_eq!(hash(read(&r,Field::SourceKnown4,c)),hash(&frames[source][c]));
            field_error=field_error.max(compare(&r,Field::SourceBase,c,&source_parts[source][c].1));
            let subtracted=frames[source][c].iter().zip(&source_parts[source][c].1).map(|(&v,&b)|v-b).collect::<Vec<_>>();
            field_error=field_error.max(compare(&r,Field::SourceAc,c,&subtracted));
            for i in 0..W*H {
                source_identity_error=source_identity_error.max((f64::from(read(&r,Field::SourceAc,c)[i])
                    +f64::from(read(&r,Field::SourceBase,c)[i])-f64::from(frames[source][c][i])).abs());
                live_base_difference=live_base_difference.max((base_parts[c].1[i]-source_parts[source][c].1[i]).abs());
            }
        }
    }
    assert!(source_identity_error<=0.02 && live_base_difference>100.0);
    let masks=(0..2).map(|r|(0..W*H).map(|i|{let x=i%W;let y=i/W;
        if x<11 || x>=W-9 || y<7 || y>=H-12 {0.0}
        else if r==0 {if x<W/2 {0.85}else{0.25}}
        else if y<H/2 {0.7}else{0.4}
    }).collect::<Vec<_>>()).collect::<Vec<_>>();
    let mut expected_masks=masks.clone();let mut coverage=vec![0.0;W*H];let mut overlap=0;
    for i in 0..W*H {let sum=masks[0][i]+masks[1][i];coverage[i]=if sum>1.0 {
        overlap+=1;for m in &mut expected_masks {m[i]/=sum;}1.0
    }else{sum};}assert!(overlap>100);
    let mut focused=SpatialDonor::new(&sizes,4,&masks);
    focused.add_source(&[0],&frames[0]);focused.add_source(&[1],&frames[1]);
    let mut late=SpatialDonor::new(&sizes,4,&masks);late.add_source(&[0,1],&frames[2]);
    let before=[focused.finish(&baseline,&mut Workspace::new(&sizes)),late.finish(&baseline,&mut Workspace::new(&sizes))];
    let observed=[finish_record(&baseline,&focused),finish_record(&baseline,&late)];
    let mut closure_error=0.0f64;let mut hull_identity_error=0.0f64;let mut nonzero_donor=0;let mut nonzero_retained=0;
    for (arm,r) in observed.iter().enumerate() {for c in 0..4 {
        assert_eq!(hash(read(r,Field::Coverage,c)),hash(&coverage));
        for region in 0..2 {assert_eq!(hash(read(r,Field::Mask(region),c)),hash(&expected_masks[region]));}
        field_error=field_error.max(compare(r,Field::BaselineAc,c,&base_parts[c].0));
        field_error=field_error.max(compare(r,Field::BaselineBase,c,&base_parts[c].1));
        let pre=coeff[c].collapse(&mut Workspace::new(&sizes));
        field_error=field_error.max(compare(r,Field::BaselinePre,c,&pre));
        assert_eq!(hash(read(r,Field::BaselinePost,c)),hash(&ordinary[c]));
        assert_eq!(hash(read(r,Field::PostHull,c)),hash(&before[arm][c]));
        for i in 0..W*H {
            let lo=frames.iter().map(|p|p[c][i]).fold(f32::INFINITY,f32::min);
            let hi=frames.iter().map(|p|p[c][i]).fold(f32::NEG_INFINITY,f32::max);
            assert_eq!(read(r,Field::Lo,c)[i].to_bits(),lo.to_bits());assert_eq!(read(r,Field::Hi,c)[i].to_bits(),hi.to_bits());
            let mut donor=0.0f32;
            for region in 0..2 {if expected_masks[region][i]>0.0 {
                donor+=expected_masks[region][i]*source_parts[if arm==0{region}else{2}][c].0[i];
            }}
            let retained=(1.0-coverage[i])*base_parts[c].0[i];
            field_error=field_error.max((read(r,Field::DonorSum,c)[i]-donor).abs());
            field_error=field_error.max((read(r,Field::RetainedAc,c)[i]-retained).abs());
            nonzero_donor+=usize::from(donor.abs()>0.003);nonzero_retained+=usize::from(retained.abs()>0.003);
            let expected=if coverage[i]==0.0 {pre[i]}else{pre[i]+(donor-coverage[i]*base_parts[c].0[i])};
            field_error=field_error.max((read(r,Field::PreHull,c)[i]-expected).abs());
            assert!((read(r,Field::PostHull,c)[i]-expected.clamp(lo,hi)).abs()<=0.003);
            closure_error=closure_error.max((f64::from(read(r,Field::RetainedAc,c)[i])
                +f64::from(read(r,Field::DonorSum,c)[i])+f64::from(read(r,Field::BaselineBase,c)[i])
                -f64::from(read(r,Field::PreHull,c)[i])).abs());
            for (a,b,d) in [(Field::BaselinePre,Field::BaselinePost,Field::BaselineHull),
                (Field::PreHull,Field::PostHull,Field::HullCorrection)] {
                let error=(f64::from(read(r,a,c)[i])+f64::from(read(r,d,c)[i])-f64::from(read(r,b,c)[i])).abs();
                hull_identity_error=hull_identity_error.max(error);
                assert!((read(r,d,c)[i]-(read(r,b,c)[i]-read(r,a,c)[i])).abs()<=0.003);
            }
        }
    }}
    assert!(field_error<=0.003 && closure_error<=0.02 && hull_identity_error<=0.02);
    assert!(nonzero_donor>100 && nonzero_retained>100);
    let mut upper_clamps=0;let mut lower_clamps=0;let mut max_clamp=0.0f32;let pin=(H/2)*W+W/2;
    for source in [0usize,2] {let mut one=SpatialDonor::new(&sizes,4,&[vec![1.0;W*H]]);
        one.add_source(&[0],&frames[source]);let before=one.finish(&baseline,&mut Workspace::new(&sizes));
        let r=finish_record(&baseline,&one);
        for c in 0..4 {let delta=read(&r,Field::HullCorrection,c)[pin];max_clamp=max_clamp.max(delta.abs());
            if source==0 {assert!(delta< -100.0);upper_clamps+=1;}else{assert!(delta>100.0);lower_clamps+=1;}
            assert_eq!(read(&r,Field::PostHull,c)[pin].to_bits(),frames[0][c][pin].to_bits());
            assert_eq!(hash(read(&r,Field::PostHull,c)),hash(&before[c]));
        }
        exact(&one.finish(&baseline,&mut Workspace::new(&sizes)),&before);
    }
    assert_eq!((upper_clamps,lower_clamps),(4,4));
    let late_changes=before[0].iter().zip(&before[1]).flat_map(|(a,b)|a.iter().zip(b))
        .filter(|(a,b)|a.to_bits()!=b.to_bits()).count();assert!(late_changes>100);
    exact(&baseline.finish(&mut Workspace::new(&sizes)),&ordinary);
    exact(&focused.finish(&baseline,&mut Workspace::new(&sizes)),&before[0]);
    exact(&late.finish(&baseline,&mut Workspace::new(&sizes)),&before[1]);
    assert_eq!(raw,raw_before);assert_eq!(hashes(&frames),hashes_before);
    eprintln!("DONOR_SPATIAL_WITNESS {}",json!({"status":"PASS","domain_quads":[W,H],
        "field_max_error_dn":field_error,"source_identity_max_error_dn":source_identity_error,
        "spatial_closure_max_error_dn":closure_error,"hull_identity_max_error_dn":hull_identity_error,
        "live_source_mean_base_difference_dn":live_base_difference,"normalized_samples":overlap,
        "nonzero_donor_samples":nonzero_donor,"nonzero_retained_samples":nonzero_retained,
        "upper_pin_clamps":upper_clamps,"lower_pin_clamps":lower_clamps,"largest_pin_clamp_dn":max_clamp,
        "late_changed_samples":late_changes,"whole_crop_bits_equal":true,"post_hull_finish_bits_equal":true,
        "three_outputs_observer_neutral":true,"inputs_unchanged":true,
        "scope":"Immutable source-gauge and spatial-reconstruction witness; no photographic quality claim"}));
}
