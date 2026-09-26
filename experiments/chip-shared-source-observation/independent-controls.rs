// Capacity-only commission. The original generated quality rejection is held.
use super::{CostVolume,aggregate_costs,memberships};
use crate::merge_cmd::shared_source_field as old;
use strehl_core::pyramid::{self, BandMerge,FrameWorkspace,MergeConfig,Workspace,
    shared_source_field_diagnostic as old_replay,
    chip_shared_source_observation_diagnostic as new_replay};

fn exact(a:&[f32],b:&[f32])->bool {a.len()==b.len() && a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits())}
fn exact4(a:&[Vec<f32>],b:&[Vec<f32>])->bool {a.len()==b.len() && a.iter().zip(b).all(|(a,b)|exact(a,b))}
fn input(k:usize)->(Vec<f32>,Vec<f32>) {
    let floor=vec![4.0,8.0,2.0,0.0,16.0,3.0];
    let energy=(0..6).map(|p|if p==0 {floor[p]}else {floor[p]+((k*17+p*11)%31)as f32*5.0}).collect();
    (energy,floor)
}

#[test]
fn independent_common_capacity_costs_are_bit_exact() {
    let guide=[10.0,10.0,80.0,12.0,90.0,89.0];
    for n in [1usize,5,70] {
        let mut a=old::CostVolume::new(3,2,n).unwrap();let mut b=CostVolume::new(3,2,n).unwrap();
        for k in 0..n {let(e,f)=input(k);a.set_source(k,&e,&f).unwrap();b.set_source(k,&e,&f).unwrap();}
        let ar=a.normalize().unwrap();let br=b.normalize().unwrap();
        assert!(exact(&ar.costs,&br.costs) && exact(&ar.rmax,&br.rmax) && exact(&ar.spread,&br.spread));
        let aa=old::aggregate_costs(&ar,&guide).unwrap();let ba=aggregate_costs(&br,&guide).unwrap();assert!(exact(&aa,&ba));
        let am=old::memberships(aa,&ar).unwrap();let bm=memberships(ba,&br).unwrap();
        assert!(exact(&am.pixel_major_q,&bm.pixel_major_q) && exact(&am.alpha,&bm.alpha));
        for k in 0..n {assert!(exact(&am.source(k),&bm.source(k)));}
    }
    assert!(old::CostVolume::new(3,2,71).is_err());assert!(CostVolume::new(3,2,300).is_err());
}

#[test]
fn independent_299_labels_and_checked_resource_extent() {
    let labels=[0usize,69,70,298];let guide=vec![0.0;6];
    let make=|reverse:bool| {
        let mut v=CostVolume::new(3,2,299).unwrap();
        for source in 0..299 {
            let original=if reverse {298-source}else{source};
            let mut e=vec![1.0;6];for p in 0..4 {if original==labels[p] {e[p]=101.0;}}
            // Pixel4 has identical strong evidence (zero spread); pixel5 flat.
            e[4]=101.0;v.set_source(source,&e,&vec![1.0;6]).unwrap();
        }
        let raw=v.normalize().unwrap();let combined=aggregate_costs(&raw,&guide).unwrap();memberships(combined,&raw).unwrap()
    };
    let a=make(false);let b=make(true);
    assert_eq!((a.width,a.height,a.frames),(3,2,299));assert!(exact(&a.alpha,&b.alpha));
    for p in 0..6 {
        let row=&a.pixel_major_q[p*299..(p+1)*299];let perm=&b.pixel_major_q[p*299..(p+1)*299];
        assert!((row.iter().sum::<f32>()-a.alpha[p]).abs()<=8e-6);
        assert!(row.iter().enumerate().all(|(k,v)|v.to_bits()==perm[298-k].to_bits()));
        if p<4 {assert!(a.alpha[p]>0.0 && row[labels[p]]>0.0);}
        else {assert_eq!(a.alpha[p],0.0);assert!(row.iter().all(|v|*v==0.0));}
    }
    for k in labels {assert_eq!(a.source(k).len(),6);}
    let mut incomplete=CostVolume::new(3,2,299).unwrap();incomplete.set_source(298,&vec![1.0;6],&vec![1.0;6]).unwrap();
    assert!(incomplete.set_source(298,&vec![1.0;6],&vec![1.0;6]).is_err());
    assert!(incomplete.set_source(299,&vec![1.0;6],&vec![1.0;6]).is_err());assert!(incomplete.normalize().is_err());
    let scalar_pair_bytes=3250usize.checked_mul(2166).unwrap().checked_mul(299).unwrap().checked_mul(4).unwrap().checked_mul(2).unwrap();
    assert_eq!(scalar_pair_bytes,16_838_484_000usize);
    assert_eq!(super::scalar_volume_pair_bytes(3250,2166,299).unwrap(),scalar_pair_bytes);
    assert!(super::scalar_volume_pair_bytes(3250,2166,300).is_err());
    assert!(super::scalar_volume_pair_bytes(usize::MAX,2166,299).is_err());
    eprintln!("SHARED_SOURCE_CAPACITY scalar_pair_bytes={scalar_pair_bytes}; this excludes gather/replay/writer and is not peak memory");
}

fn planes(k:usize,n:usize)->Vec<Vec<f32>> {
    (0..4).map(|c|(0..n).map(|j|1200.0+((j*11+c*31+k*17)%127)as f32+100.0*k as f32).collect()).collect()
}
#[test]
fn independent_actual_replay_common_and_299_sources() {
    let sizes=pyramid::level_sizes(17,17,1);let n=17*17;assert_eq!(sizes.len(),2);
    let frames=(0..4).map(|k|planes(k,n)).collect::<Vec<_>>();
    let mut ws=FrameWorkspace::new(&sizes,4);
    // Use an explicitly one-AC merge matching the fixture's reached sizes.
    let mut cfg=MergeConfig::default();cfg.bands=1;let mut merge=BandMerge::new(17,17,4,cfg);
    for frame in &frames {merge.add_frame(&frame.iter().map(Vec::as_slice).collect::<Vec<_>>(),&frame[1],&vec![16.0;n],&mut ws);}
    for count in [5usize,70] {
        let alpha=vec![1.0;n];let mut a=old_replay::Replay::new(&sizes,&alpha).unwrap();let mut b=new_replay::Replay::new(&sizes,&alpha).unwrap();
        for k in 0..count {let q=vec![if k==0 {0.25}else if k==count-1 {0.75}else{0.0};n];
            a.add_source(&q,&frames[k%4]).unwrap();b.add_source(&q,&frames[k%4]).unwrap();}
        assert!(exact(a.coverage(),b.coverage()) && exact4(a.detail_sums(),b.detail_sums()));
        assert!(exact4(&a.finish(&merge,&mut Workspace::new(&sizes)).unwrap(),&b.finish(&merge,&mut Workspace::new(&sizes)).unwrap()));
        if count==70 {assert!(a.add_source(&vec![0.0;n],&frames[0]).is_err());}
    }
    let alpha=vec![1.0;n];let mut old=old_replay::Replay::new(&sizes,&alpha).unwrap();let mut extended=new_replay::Replay::new(&sizes,&alpha).unwrap();
    let labels=[0usize,69,70,298];let q=[0.125f32,0.125,0.25,0.5];
    for k in 0..4 {old.add_source(&vec![q[k];n],&frames[k]).unwrap();}
    for source in 0..299 {if let Some(k)=labels.iter().position(|k|*k==source) {extended.add_source(&vec![q[k];n],&frames[k]).unwrap();}
        else {extended.add_source(&vec![0.0;n],&frames[0]).unwrap();}}
    assert!(exact(old.coverage(),extended.coverage()) && exact4(old.detail_sums(),extended.detail_sums()));
    assert!(exact4(&old.finish(&merge,&mut Workspace::new(&sizes)).unwrap(),&extended.finish(&merge,&mut Workspace::new(&sizes)).unwrap()));
    assert!(extended.add_source(&vec![0.0;n],&frames[0]).is_err());
    assert!(extended.detail_sums().iter().flatten().any(|v|v.abs()>1.0));
}
