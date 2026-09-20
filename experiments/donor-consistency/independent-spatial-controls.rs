use super::*;
use strehl_core::pyramid::donor_consistency_diagnostic::SpatialDonor;

fn ac(p:&Pyramid)->Vec<f32> {
    let mut q=p.clone();let last=q.levels()-1;q.level_mut(last).fill(0.0);
    q.collapse(&mut Workspace::new(q.sizes()))
}
fn bound(value:f32,frames:&[Vec<Vec<f32>>],c:usize,i:usize)->f32 {
    let lo=frames.iter().map(|f|f[c][i]).fold(f32::INFINITY,f32::min);
    let hi=frames.iter().map(|f|f[c][i]).fold(f32::NEG_INFINITY,f32::max);
    value.clamp(lo,hi)
}

#[test]
fn independent_spatial_masks_after_full_collapse() {
    let (raw,frames)=fixtures();let raw_before=raw.clone();let before=hashes(&frames);
    let sizes=level_sizes(W,H,3);let baseline=merge(&frames);
    let ordinary=baseline.finish(&mut Workspace::new(&sizes));
    let resolved=resolved_coefficients(&baseline);
    let source=frames.iter().map(|f|pyramids(f)).collect::<Vec<_>>();
    let donor_ac=source.iter().map(|ps|ps.iter().map(ac).collect::<Vec<_>>()).collect::<Vec<_>>();
    let baseline_ac=resolved.iter().map(ac).collect::<Vec<_>>();
    let pre=resolved.iter().map(|p|p.collapse(&mut Workspace::new(&sizes))).collect::<Vec<_>>();
    let shared=resolved.iter().map(|p|{let mut q=Pyramid::zeros(&sizes);
        q.level_mut(3).copy_from_slice(p.level(3));q.collapse(&mut Workspace::new(&sizes))}).collect::<Vec<_>>();
    for c in 0..4 {
        assert!(worst(source[0][c].level(3),source[2][c].level(3))>100.0);
        let mean=(0..sizes[3].pixels()).map(|i|{let mut total=0.0f32;
            for p in &source {total+=p[c].level(3)[i];}total*(1.0/3.0)}).collect::<Vec<_>>();
        assert_eq!(hash(&mean),hash(resolved[c].level(3)));
        assert!(pre[c].iter().zip(&baseline_ac[c]).zip(&shared[c])
            .all(|((&v,&a),&b)|(v-(a+b)).abs()<=0.02));
    }
    let off=SpatialDonor::new(&sizes,4,&[]);
    exact(&off.finish(&baseline,&mut Workspace::new(&sizes)),&ordinary);
    let mut zero=SpatialDonor::new(&sizes,4,&[vec![0.0;W*H]]);
    zero.add_source(&[0],&frames[0]);exact(&zero.finish(&baseline,&mut Workspace::new(&sizes)),&ordinary);

    let masks=(0..3).map(|r|(0..W*H).map(|i|{let x=i%W;let y=i/W;
        if x<11 || x>=W-9 || y<7 || y>=H-12 {0.0}
        else if r==0 {if x<W/2 {0.85}else{0.25}}
        else if r==1 {if y<H/2 {0.7}else{0.4}}
        else if x+y<W {0.15}else{0.3}
    }).collect::<Vec<_>>()).collect::<Vec<_>>();
    let mut normalized=masks.clone();let mut coverage=vec![0.0;W*H];let mut normalized_count=0;
    for i in 0..W*H {let sum=masks.iter().map(|m|m[i]).sum::<f32>();
        coverage[i]=if sum>1.0 {normalized_count+=1;
            for m in &mut normalized {m[i]/=sum;}1.0}else{sum};
    }
    assert!(normalized_count>100);
    let mut focused=SpatialDonor::new(&sizes,4,&masks);
    focused.add_source(&[2],&frames[0]);focused.add_source(&[0],&frames[1]);focused.add_source(&[1],&frames[2]);
    assert_eq!(focused.normalized_count(),normalized_count);
    assert_eq!(hash(focused.coverage()),hash(&coverage));
    for r in 0..3 {assert_eq!(hash(&focused.masks()[r]),hash(&normalized[r]));}
    let mut late=SpatialDonor::new(&sizes,4,&masks);late.add_source(&[0,1,2],&frames[2]);
    let output=focused.finish(&baseline,&mut Workspace::new(&sizes));
    let late_output=late.finish(&baseline,&mut Workspace::new(&sizes));
    let mut sum_error=0.0f32;let mut output_error=0.0f32;
    let mut outside_samples=0;let mut changed_inside=0;let mut late_changed=0;
    for (arm,(actual,consumer)) in [(&output,&focused),(&late_output,&late)].into_iter().enumerate(){
        for c in 0..4 {for i in 0..W*H {
            let mut a=0.0f32;
            for r in if arm==0{[2,0,1]}else{[0,1,2]} {if normalized[r][i]>0.0 {
                let donor=if arm==0{(r+1)%3}else{2};a+=normalized[r][i]*donor_ac[donor][c][i];
            }}
            sum_error=sum_error.max((consumer.detail_sums()[c][i]-a).abs());
            let expected=if coverage[i]==0.0 {ordinary[c][i]}
                else {bound(pre[c][i]+(a-coverage[i]*baseline_ac[c][i]),&frames,c,i)};
            output_error=output_error.max((actual[c][i]-expected).abs());
            if coverage[i]==0.0 {assert_eq!(actual[c][i].to_bits(),ordinary[c][i].to_bits());outside_samples+=1;}
            else {changed_inside+=usize::from(actual[c][i].to_bits()!=ordinary[c][i].to_bits());}
            assert_eq!(actual[c][i].to_bits(),bound(actual[c][i],&frames,c,i).to_bits());
            if arm==0 {late_changed+=usize::from(actual[c][i].to_bits()!=late_output[c][i].to_bits());}
        }}
    }
    assert!(sum_error<=0.003 && output_error<=0.003);
    assert!(outside_samples>100 && changed_inside>100 && late_changed>100);
    let mut old=DonorBlend::new(&sizes,4,&masks);
    old.add_source(&[2],&frames[0]);old.add_source(&[0],&frames[1]);old.add_source(&[1],&frames[2]);
    let old_out=old.finish(&baseline,&mut Workspace::new(&sizes));
    let old_difference=old_out.iter().zip(&output).map(|(a,b)|worst(a,b)).fold(0.0f32,f32::max);
    assert!(old_difference>0.003,"the fixture must distinguish masking orders");

    let mut ones_error=0.0f32;let mut alternate_error=0.0f32;let mut positive_clamps=0;let mut negative_clamps=0;
    let pin=(H/2)*W+W/2;let mut largest_clamp=0.0f32;let mut direct_donor_difference=0.0f32;
    for donor in [0usize,2] {
        let mut all=SpatialDonor::new(&sizes,4,&[vec![1.0;W*H]]);all.add_source(&[0],&frames[donor]);
        let actual=all.finish(&baseline,&mut Workspace::new(&sizes));
        for c in 0..4 {for i in 0..W*H {
            let literal=pre[c][i]+(donor_ac[donor][c][i]-baseline_ac[c][i]);
            let alternative=shared[c][i]+donor_ac[donor][c][i];
            alternate_error=alternate_error.max((literal-alternative).abs());
            ones_error=ones_error.max((actual[c][i]-bound(alternative,&frames,c,i)).abs());
            direct_donor_difference=direct_donor_difference.max((actual[c][i]-frames[donor][c][i]).abs());
            if i==pin {
                let excursion=literal-frames[0][c][i];largest_clamp=largest_clamp.max(excursion.abs());
                if donor==0 {assert!(excursion>100.0);positive_clamps+=1;}
                else {assert!(excursion< -100.0);negative_clamps+=1;}
                assert_eq!(actual[c][i].to_bits(),frames[0][c][i].to_bits());
            }
        }}
    }
    assert!(ones_error<=0.02 && alternate_error<=0.02 && direct_donor_difference>100.0);
    assert_eq!((positive_clamps,negative_clamps),(4,4));
    let phase0=fixed_masks(W,H,[2561,2853]);let phase1=fixed_masks(W,H,[2562,2854]);
    let phase_changes=phase0.iter().zip(&phase1).flat_map(|(a,b)|a.iter().zip(b))
        .filter(|(a,b)|a.to_bits()!=b.to_bits()).count();assert!(phase_changes>100);
    for masks in [&phase0,&phase1] {let spatial=SpatialDonor::new(&sizes,4,masks);
        for r in 0..masks.len(){assert_eq!(hash(&spatial.masks()[r]),hash(&masks[r]));}}
    for bad in [f32::NAN,-0.01,1.01]{refused(||{SpatialDonor::new(&sizes,4,&[vec![bad;W*H]]);});}
    refused(||{SpatialDonor::new(&sizes,4,&[vec![0.0;W*H-1]]);});
    refused(||{let missing=SpatialDonor::new(&sizes,4,&[vec![1.0;W*H]]);missing.finish(&baseline,&mut Workspace::new(&sizes));});
    refused(||{let mut duplicate=SpatialDonor::new(&sizes,4,&[vec![1.0;W*H]]);
        duplicate.add_source(&[0],&frames[0]);duplicate.add_source(&[0],&frames[1]);});
    assert_eq!(raw,raw_before);assert_eq!(hashes(&frames),before);
    exact(&baseline.finish(&mut Workspace::new(&sizes)),&ordinary);
    eprintln!("DONOR_SPATIAL {}",json!({"status":"PASS","domain_quads":[W,H],
        "normalization_count":normalized_count,"detail_sum_max_error_dn":sum_error,"output_max_error_dn":output_error,
        "zero_outside_exact_samples":outside_samples,"changed_covered_samples":changed_inside,"late_changed_samples":late_changed,
        "old_coefficient_mask_max_difference_dn":old_difference,"allones_shared_base_max_error_dn":ones_error,
        "alternate_pre_hull_algebra_max_error_dn":alternate_error,"positive_pin_clamps":positive_clamps,
        "negative_pin_clamps":negative_clamps,"largest_pin_clamp_dn":largest_clamp,
        "direct_donor_max_difference_dn":direct_donor_difference,"native_phase_changed_samples":phase_changes,
        "off_zero_exact":true,"independent_mean_base_exact":true,"inputs_unchanged":true,"baseline_unchanged":true,
        "scope":"Post-collapse masking integration controls; no photographic quality or noise calibration claim"}));
}
