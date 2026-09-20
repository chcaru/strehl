use super::*;

fn near(a:f32,b:f64) {assert!((a as f64-b).abs()<=2e-5*(1.0+b.abs()),"{a} != {b}");}
fn check(summary:&PlaneSummary,fields:&[Vec<f32>;5],size:LevelSize,roi:[usize;4],origin:[usize;2]) {
    let [x,y,w,h]=roi;let ids=(y..y+h).flat_map(|yy|(x..x+w).map(move |xx|(xx,yy))).collect::<Vec<_>>();
    assert_eq!(summary.count,ids.len());
    let means=fields.iter().map(|a|ids.iter().map(|&(xx,yy)|a[yy*size.width+xx] as f64).sum::<f64>()/ids.len() as f64).collect::<Vec<_>>();
    for (v,e) in [summary.mean_dn,summary.mean_l0,summary.mean_energy,summary.mean_guide,summary.mean_guide_variance].into_iter().zip(means) {near(v,e);}
    for p in 0..2 {let subset=ids.iter().copied().filter(|&(xx,yy)|(xx+origin[0]+yy+origin[1])%2==p).collect::<Vec<_>>();
        assert_eq!(summary.checker_count[p],subset.len());
        for (v,field) in [(summary.checker_mean_dn[p],0),(summary.checker_mean_l0[p],1)] {
            near(v,subset.iter().map(|&(xx,yy)|fields[field][yy*size.width+xx] as f64).sum::<f64>()/subset.len() as f64);
        }
    }
}

#[test]
fn independent_through_focus_summary_controls()->Result<()> {
    let size=LevelSize{width:19,height:13};let roi=[3,2,7,5];let origin=[28,19];
    let fields: [Vec<f32>;5]=std::array::from_fn(|k|(0..size.pixels()).map(|j| {
        let x=(j%size.width) as f32;let y=(j/size.width) as f32;
        match k {0=>3.0*x-5.0*y-11.0,1=>2.0*x+3.0*y-21.0,2=>x*x+2.0*y+1.0,3=>100.0+7.0*x-y,_=>0.25+(j%4) as f32}
    }).collect());
    let before=fields.iter().map(|a|field_hash(a)).collect::<Vec<_>>();
    let apply=|f:&[Vec<f32>;5],r,o|summarize_roi(&f[0],&f[1],&f[2],&f[3],&f[4],size,r,o);
    let a=apply(&fields,roi,origin)?;check(&a,&fields,size,roi,origin);assert!(a.mean_dn<0.0);
    let shifted=[roi[0]+1,roi[1],roi[2],roi[3]];let s=apply(&fields,shifted,origin)?;
    check(&s,&fields,size,shifted,origin);assert_ne!(a.mean_dn.to_bits(),s.mean_dn.to_bits());
    let swapped=apply(&fields,roi,[29,19])?;
    assert_eq!(a.mean_dn.to_bits(),swapped.mean_dn.to_bits());
    for p in 0..2 {assert_eq!(a.checker_count[p],swapped.checker_count[1-p]);
        assert_eq!(a.checker_mean_dn[p].to_bits(),swapped.checker_mean_dn[1-p].to_bits());}
    let mut offset=fields.clone();for v in &mut offset[0]{*v+=1024.0;}
    let o=apply(&offset,roi,origin)?;near(o.mean_dn,a.mean_dn as f64+1024.0);
    assert_eq!(o.mean_l0.to_bits(),a.mean_l0.to_bits());assert_eq!(o.mean_energy.to_bits(),a.mean_energy.to_bits());
    let mut sentinel=fields.clone();for a in &mut sentinel {a[0]=f32::NAN;}
    let untouched=apply(&sentinel,roi,origin)?;assert_eq!(untouched.mean_dn.to_bits(),a.mean_dn.to_bits());
    for (field,bad) in [(0,f32::NAN),(2,-1.0),(4,-1.0)] {
        let mut invalid=fields.clone();invalid[field][roi[1]*size.width+roi[0]]=bad;
        assert!(apply(&invalid,roi,origin).is_err());
    }
    assert!(apply(&fields,[18,12,2,2],origin).is_err());assert!(apply(&fields,[3,2,1,1],origin).is_err());
    let mut short=fields.clone();short[0].pop();assert!(apply(&short,roi,origin).is_err());
    assert_eq!(before,fields.iter().map(|a|field_hash(a)).collect::<Vec<_>>());
    eprintln!("THROUGH_FOCUS_SUMMARY {}",json!({"asymmetric_direct_index_means":true,
        "signed_values":true,"one_quad_shift_live":true,"global_parity_swap_exact":true,
        "ignored_outside_sentinel":true,"invalid_values_refused":true,"source_unchanged":true,
        "scope":"arithmetic only; no optical or image-quality evidence"}));Ok(())
}
