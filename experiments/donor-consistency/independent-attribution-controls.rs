use super::*;
use std::collections::BTreeMap;
use strehl_core::pyramid::donor_consistency_diagnostic::{
    observe_attribution,AttributionField as Field,AttributionWindow as Window,
};

type Records=BTreeMap<(String,usize,usize),Vec<f32>>;
fn key(field:Field,plane:usize,window:usize)->(String,usize,usize) {
    (format!("{field:?}"),plane,window)
}
fn read(records:&Records,field:Field,plane:usize,window:usize)->&[f32] {
    records.get(&key(field,plane,window)).expect("missing attribution field")
}
fn windows()->[Window;3] {
    [Window{x:0,y:0,width:W,height:H},Window{x:5,y:7,width:33,height:29},
        Window{x:6,y:8,width:31,height:27}]
}
fn slice(values:&[f32],window:&Window)->Vec<f32> {
    (window.y..window.y+window.height).flat_map(|y|
        values[y*W+window.x..y*W+window.x+window.width].iter().copied()).collect()
}
fn capture(base:&BandMerge,blend:&DonorBlend)->Records {
    let windows=windows();let mut records=Records::new();
    let sizes=level_sizes(W,H,3);
    let summary=observe_attribution(base,blend,&windows,&mut Workspace::new(&sizes),|f,c,w,values| {
        assert!(c<4 && w<windows.len());assert_eq!(values.len(),windows[w].width*windows[w].height);
        assert!(values.iter().all(|v|v.is_finite()));
        assert!(records.insert(key(f,c,w),values.to_vec()).is_none(),"duplicate attribution field");
    });
    for values in [summary.baseline_sum_max_abs,summary.mixed_sum_max_abs,
        summary.baseline_hull_sum_max_abs,summary.mixed_hull_sum_max_abs] {
        assert!(values.iter().all(|v|v.is_finite() && *v<=0.02));
    }
    // 3 bands x 3 signed parts, one terminal base and six reconstruction fields.
    assert_eq!(records.len(),16*4*3);
    for ((name,c,w),values) in &records {
        let full=records.get(&(name.clone(),*c,0)).unwrap();
        assert_eq!(hash(values),hash(&slice(full,&windows[*w])),"crop was redecomposed or phase shifted");
    }
    records
}
fn isolated(level:usize,values:&[f32])->Vec<f32> {
    let sizes=level_sizes(W,H,3);let mut p=Pyramid::zeros(&sizes);
    p.level_mut(level).copy_from_slice(values);p.collapse(&mut Workspace::new(&sizes))
}
fn compare_field(records:&Records,field:Field,c:usize,expected:&[f32])->f32 {
    let error=worst(read(records,field,c,0),expected);
    assert!(error<=0.003,"{field:?} plane{c} differs by {error}DN");error
}
fn sum_identity(records:&Records,c:usize,baseline:bool)->f64 {
    let mut error=0.0f64;
    let pre=read(records,if baseline{Field::BaselinePreHull}else{Field::PreHull},c,0);
    let base=read(records,Field::Base,c,0);
    for i in 0..W*H {
        let mut sum=f64::from(base[i]);
        for level in 0..3 {
            if baseline {sum+=f64::from(read(records,Field::BaselineAc(level),c,0)[i]);}
            else {sum+=f64::from(read(records,Field::RetainedAc(level),c,0)[i])
                +f64::from(read(records,Field::DonorAc(level),c,0)[i]);}
        }
        error=error.max((sum-f64::from(pre[i])).abs());
    }
    assert!(error<=0.02,"signed AC/base identity differs by {error}DN");error
}

#[test]
fn independent_attribution_signed_parts_and_neutrality() {
    let (raw,frames)=fixtures();let raw_before=raw.clone();let input_hashes=hashes(&frames);
    let sizes=level_sizes(W,H,3);let baseline=merge(&frames);
    let coefficients=resolved_coefficients(&baseline);
    let original=frames.iter().map(|f|pyramids(f)).collect::<Vec<_>>();
    let masks=vec![(0..W*H).map(|i|if i%W<W/2{0.9}else{0.2}).collect::<Vec<_>>(),
        (0..W*H).map(|i|if i/W<H/2{0.8}else{0.35}).collect::<Vec<_>>()];
    let mut expected_masks=masks.iter().map(|m|{
        let mut p=Pyramid::zeros(&sizes);p.build_gaussian(m,&mut Workspace::new(&sizes));p
    }).collect::<Vec<_>>();
    for level in 0..sizes.len(){for i in 0..sizes[level].pixels(){
        let sum=expected_masks[0].level(level)[i]+expected_masks[1].level(level)[i];
        if sum>1.0 {for p in &mut expected_masks {p.level_mut(level)[i]/=sum;}}
    }}
    let mut focused=DonorBlend::new(&sizes,4,&masks);
    focused.add_source(&[0],&frames[0]);focused.add_source(&[1],&frames[1]);
    let mut late=DonorBlend::new(&sizes,4,&masks);late.add_source(&[0,1],&frames[2]);
    let base_before=baseline.finish(&mut Workspace::new(&sizes));
    let focus_before=focused.finish(&baseline,&mut Workspace::new(&sizes));
    let late_before=late.finish(&baseline,&mut Workspace::new(&sizes));
    let observed=[capture(&baseline,&focused),capture(&baseline,&late)];
    let mut field_error=0.0f32;let mut identity_error=0.0f64;let mut hull_error=0.0f64;
    let mut false_weight_difference=0.0f32;let mut negative_terms=0;let mut positive_terms=0;
    let mut live_retained=0;let mut live_donor=[0usize;2];let mut cancellation_samples=0;
    for (arm,records) in observed.iter().enumerate(){
        let mut expected=coefficients.clone();
        for c in 0..4 {
            field_error=field_error.max(compare_field(records,Field::Base,c,&isolated(3,coefficients[c].level(3))));
            for level in 0..3 {
                let mut retained=vec![0.0;sizes[level].pixels()];let mut donor=retained.clone();let mut membership=retained.clone();
                for i in 0..retained.len(){
                    let a=expected_masks[0].level(level)[i];let b=expected_masks[1].level(level)[i];
                    membership[i]=a+b;retained[i]=(1.0-membership[i])*coefficients[c].level(level)[i];
                    donor[i]=if arm==0 {a*original[0][c].level(level)[i]+b*original[1][c].level(level)[i]}
                        else {a*original[2][c].level(level)[i]+b*original[2][c].level(level)[i]};
                    expected[c].level_mut(level)[i]=retained[i]+donor[i];
                }
                let b=isolated(level,coefficients[c].level(level));
                let r=isolated(level,&retained);let d=isolated(level,&donor);
                field_error=field_error.max(compare_field(records,Field::BaselineAc(level),c,&b));
                field_error=field_error.max(compare_field(records,Field::RetainedAc(level),c,&r));
                field_error=field_error.max(compare_field(records,Field::DonorAc(level),c,&d));
                live_retained+=r.iter().filter(|v|v.abs()>0.003).count();
                live_donor[arm]+=d.iter().filter(|v|v.abs()>0.003).count();
                negative_terms+=r.iter().chain(&d).filter(|&&v|v< -0.003).count();
                positive_terms+=r.iter().chain(&d).filter(|&&v|v>0.003).count();
                let expanded_membership=isolated(level,&membership);
                for i in 0..W*H {
                    false_weight_difference=false_weight_difference.max((r[i]-(1.0-expanded_membership[i])*b[i]).abs());
                    cancellation_samples+=usize::from(r[i]*d[i]<0.0 &&
                        (r[i]+d[i]).abs()+0.003<r[i].abs()+d[i].abs());
                }
            }
            field_error=field_error.max(compare_field(records,Field::BaselinePreHull,c,
                &coefficients[c].collapse(&mut Workspace::new(&sizes))));
            field_error=field_error.max(compare_field(records,Field::PreHull,c,
                &expected[c].collapse(&mut Workspace::new(&sizes))));
            field_error=field_error.max(compare_field(records,Field::BaselinePostHull,c,&base_before[c]));
            let actual=if arm==0{&focus_before[c]}else{&late_before[c]};
            field_error=field_error.max(compare_field(records,Field::PostHull,c,actual));
            identity_error=identity_error.max(sum_identity(records,c,true)).max(sum_identity(records,c,false));
            for (pre,post,correction) in [(Field::BaselinePreHull,Field::BaselinePostHull,Field::BaselineHullCorrection),
                (Field::PreHull,Field::PostHull,Field::HullCorrection)] {
                for ((&a,&b),&d) in read(records,pre,c,0).iter().zip(read(records,post,c,0)).zip(read(records,correction,c,0)) {
                    hull_error=hull_error.max((f64::from(a)+f64::from(d)-f64::from(b)).abs());
                    assert!((d-(b-a)).abs()<=0.003);
                }
            }
        }
        let (bounded,_) =collapse_hull(&expected,&frames);
        let actual=if arm==0{&focus_before}else{&late_before};
        for c in 0..4 {assert!(worst(&bounded[c],&actual[c])<=0.003);}
    }
    assert!(false_weight_difference>0.003,"mask-as-output-weight destroyer did not differ");
    assert!(live_retained>100 && live_donor.iter().all(|&n|n>100));
    assert!(negative_terms>100 && positive_terms>100 && cancellation_samples>10 && hull_error<=0.02);
    // Retain the original shared-pin witness; full donor AC plus the true
    // three-source mean base creates substantial excursions at all four pins.
    let mut ones=DonorBlend::new(&sizes,4,&[vec![1.0;W*H]]);ones.add_source(&[0],&frames[0]);
    let ones_before=ones.finish(&baseline,&mut Workspace::new(&sizes));
    let clamped=capture(&baseline,&ones);let pin=(H/2)*W+W/2;
    let mut clamps=0;let mut clamp_size=0.0f32;
    for c in 0..4 {
        let pre=read(&clamped,Field::PreHull,c,0)[pin];let post=read(&clamped,Field::PostHull,c,0)[pin];
        let correction=read(&clamped,Field::HullCorrection,c,0)[pin];
        assert!(pre-post>100.0 && correction< -100.0);clamps+=1;clamp_size=clamp_size.max(pre-post);
        assert_eq!(post.to_bits(),frames[0][c][pin].to_bits());
        assert!((pre+correction-post).abs()<=0.003);
        assert_eq!(hash(read(&clamped,Field::PostHull,c,0)),hash(&ones_before[c]));
    }
    let late_changed=focus_before.iter().zip(&late_before).flat_map(|(a,b)|a.iter().zip(b))
        .filter(|(a,b)|a.to_bits()!=b.to_bits()).count();assert!(late_changed>100);
    exact(&baseline.finish(&mut Workspace::new(&sizes)),&base_before);
    exact(&focused.finish(&baseline,&mut Workspace::new(&sizes)),&focus_before);
    exact(&late.finish(&baseline,&mut Workspace::new(&sizes)),&late_before);
    exact(&ones.finish(&baseline,&mut Workspace::new(&sizes)),&ones_before);
    assert_eq!(raw,raw_before);assert_eq!(hashes(&frames),input_hashes);
    eprintln!("DONOR_ATTRIBUTION {}",json!({"status":"PASS","domain_quads":[W,H],
        "windows":[[0,0,W,H],[5,7,33,29],[6,8,31,27]],"field_max_error_dn":field_error,
        "signed_reconstruction_max_error_dn":identity_error,"hull_identity_max_error_dn":hull_error,
        "false_mask_weight_max_difference_dn":false_weight_difference,"positive_terms":positive_terms,
        "negative_terms":negative_terms,"live_retained_samples":live_retained,"live_donor_samples":live_donor,
        "opposed_sign_cancellation_samples":cancellation_samples,
        "shared_pin_clamps":clamps,"largest_pin_clamp_dn":clamp_size,"late_changed_samples":late_changed,
        "whole_crop_field_bits_equal":true,"all_three_observer_output_hashes_equal":true,"inputs_unchanged":true,
        "scope":"Signed actual-coefficient observer controls; not photographic source ownership or quality"}));
}
