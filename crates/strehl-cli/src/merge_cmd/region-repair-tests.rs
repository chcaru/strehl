//! Source-constraint controls using the actual decoded-CFA production consumer.
//! These establish execution/geometry, not automatic photographic improvement.
use super::*;
use crate::merge_cmd::region_repair::{RepairContext, Repairs};
use sha2::{Digest, Sha256};
use strehl_edit::{Adjustments, DevelopmentRecipe, RegionAdjustment, RegionShape, SourceRange};

fn region(first: usize, last: usize) -> RegionAdjustment {
    RegionAdjustment {
        id: "repair".into(),
        name: "Permitted source control".into(),
        note: String::new(),
        shape: RegionShape::Rectangle { min: [0.0, 0.0], max: [1.0, 1.0] },
        feather: 0.0,
        enabled: true,
        adjustments: Adjustments::default(),
        source_range: Some(SourceRange { first, last }),
    }
}

fn saved_recipe(dir: &Path, name: &str, regions: Vec<RegionAdjustment>) -> PathBuf {
    let recipe = DevelopmentRecipe { regions, ..Default::default() };
    recipe.validate().unwrap();
    let path = dir.join(format!("{name}.json"));
    fs::write(&path, serde_json::to_vec_pretty(&recipe).unwrap()).unwrap();
    path
}

fn config() -> MergeConfig {
    MergeConfig { bands: 3, ..Default::default() }
}

#[test]
fn source_repair_noop_preserves_whole_tiff_hash_and_decode_count() {
    // Failure witness: any recipe-induced change to the merge or TIFF bytes,
    // or any unnecessary extra source pass makes this control fail.
    let dir = work_dir("source-repair-noop");
    let frames: Vec<_> = (0..4).map(|k| fixture_frame(96, 72, k)).collect();
    let baseline = FixtureSource::new(frames.clone());
    let mut opts = fixture_options(dir.join("baseline.tiff"));
    opts.pyramid = config();
    run_fixture(&opts, &baseline, None, None).unwrap();
    let expected = fs::read(opts.out.as_ref().unwrap()).unwrap();

    for disabled in [false, true] {
        let mut r = region(0, 1);
        if disabled { r.enabled = false; } else { r.source_range = None; }
        r.adjustments.exposure = 1.0; // Tone annotations are not applied by this seam.
        opts.region_recipe = Some(saved_recipe(&dir, &format!("noop-{disabled}"), vec![r]));
        opts.out = Some(dir.join(format!("noop-{disabled}.tiff")));
        let source = FixtureSource::new(frames.clone());
        run_fixture(&opts, &source, None, None).unwrap();
        let actual = fs::read(opts.out.as_ref().unwrap()).unwrap();
        assert_eq!(Sha256::digest(&expected), Sha256::digest(&actual));
        assert_eq!(baseline.counts(), source.counts());
        println!("source repair no-op={disabled}: TIFF sha256 {}",
            Sha256::digest(actual).iter().map(|b|format!("{b:02x}")).collect::<String>());
    }
}

#[test]
fn source_repair_full_region_matches_single_donor_whole_output() {
    // Positive: changing the permitted donor must visibly change the full
    // output. Negative: excluded donors must not leak via base/fallback/hull.
    let dir = work_dir("source-repair-donor");
    let frames: Vec<_> = (0..5).map(|k| fixture_frame(96, 72, k * 7)).collect();
    let mut opts = fixture_options(dir.join("ordinary.tiff"));
    opts.pyramid = config();
    let source = FixtureSource::new(frames.clone());
    run_fixture(&opts, &source, None, None).unwrap();
    let (_, _, ordinary, _) = read_tiff(opts.out.as_ref().unwrap());
    for index in [1, 3] {
        let mut single_opts = fixture_options(dir.join(format!("single-{index}.tiff")));
        single_opts.pyramid = config();
        let single = FixtureSource::new(vec![frames[index].clone()]);
        run_fixture(&single_opts, &single, None, None).unwrap();
        let (_, _, expected, _) = read_tiff(single_opts.out.as_ref().unwrap());
        assert!(expected.iter().zip(&ordinary).any(|(a,b)| a.abs_diff(*b) > 20),
            "fixture must exercise a real change, not an identity donor");
        opts.region_recipe = Some(saved_recipe(&dir, &format!("donor-{index}"), vec![region(index,index)]));
        opts.out = Some(dir.join(format!("repaired-{index}.tiff")));
        let source = FixtureSource::new(frames.clone());
        run_fixture(&opts, &source, None, None).unwrap();
        let (w, h, actual, _) = read_tiff(opts.out.as_ref().unwrap());
        assert_eq!((w,h), (96,72));
        assert_eq!(actual, expected, "full repair must reconstruct only its permitted donor");
        for (k,calls) in source.counts().iter().enumerate() {
            assert_eq!(*calls, 1 + usize::from(k == index));
        }
        opts.region_recipe = None;
    }
}

#[test]
fn source_repair_preserves_uncovered_pixels_and_handles_chunk_boundaries() {
    // Deliberately force the ordinary mean fallback at all detail scales.
    // Excluded donors are poison: attempting to decode either fails the test.
    let dir = work_dir("source-repair-feather");
    let frames: Vec<_> = (0..6).map(|k| fixture_frame(96,72,k*13)).collect();
    let mut source = FixtureSource::new(frames);
    source.fail_at = Some(0);
    let domain = PyramidDomain::whole(source.frames[0].geometry());
    let geom = domain.analysis();
    let levels = source.frames[0].levels;
    let noise = profile::noise_model_for(&source.frames[0].camera, source.frames[0].iso, levels);
    let cfg = MergeConfig { gate: 1e15, ..config() };
    let mut r = region(1,4);
    r.shape = RegionShape::Rectangle { min:[0.2,0.2], max:[0.8,0.8] };
    r.feather = 0.4;
    let path = saved_recipe(&dir, "feather", vec![r.clone()]);
    let repairs = Repairs::load(Some(&path)).unwrap();
    repairs.preflight(6,domain,None,None).unwrap();

    // Independent source-only oracle: fold the four allowed sources through
    // the actual worker, bypassing all recipe traversal/chunk/blend code.
    let mut oracle = BandWorker::new(domain,cfg);
    for k in 1..=4 { assert!(oracle.fold(&source,k,levels,&noise,None,None).unwrap()); }
    let expected = oracle.merge.finish(&mut Workspace::new(oracle.merge.sizes()));
    assert!(oracle.merge.averaged_fraction().iter().all(|&f| f > 0.99),
        "the fallback path must actually be active");
    for calls in &source.calls { calls.store(0,Ordering::SeqCst); }
    let before: Vec<Vec<f32>> = (0..4).map(|c|
        (0..geom.pixels()).map(|i| 9000.0 + c as f32*100.0 + (i%13) as f32).collect()).collect();
    let mut actual = before.clone();
    repairs.apply(&mut actual,RepairContext {
        source:&source,domain,config:cfg,levels,noise:&noise,warps:None,defect:None,per_chunk:2,progress:None,
    }).unwrap();
    assert_eq!(source.counts(),vec![0,1,1,1,1,0]);
    let mut outside=0; let mut inside=0; let mut feather=0;
    for c in 0..4 {
        for i in 0..geom.pixels() {
            let uv = [
                ((i%geom.width)*2+c%2) as f32/(geom.width*2) as f32 + 0.25/geom.width as f32,
                ((i/geom.width)*2+c/2) as f32/(geom.height*2) as f32 + 0.25/geom.height as f32,
            ];
            let weight=r.shape.weight(uv,r.feather);
            if weight==0.0 {
                outside+=1;
                assert_eq!(actual[c][i].to_bits(),before[c][i].to_bits());
            } else {
                if weight==1.0 { inside+=1; } else { feather+=1; }
                let want = before[c][i]*(1.0-weight)+expected[c][i]*weight;
                // Canonical chunk grouping can round a mean differently.
                assert!((actual[c][i]-want).abs()<0.01, "CFA {c} sample {i}");
            }
        }
    }
    assert!(outside>100 && inside>100 && feather>100);
}

#[test]
fn source_repair_refuses_invalid_ranges_refused_donors_and_empty_regions() {
    let dir = work_dir("source-repair-refusal");
    let geom = PlaneGeometry { width:48,height:36 };
    let domain = PyramidDomain::whole(geom);
    let entries:Vec<_>=(0..3).map(|k|(format!("generated-{k}.ARW"),1u64)).collect();
    let map = WarpMap::new(WarpProvenance {
        stack:StackIdentity::from_entries("repair-refusal",&entries),
        strategy:"known test refusal".into(),heldout_px:None,cycle_floor_px:None,
        reference:0,note:String::new(),
    },geom,Resampler::CatmullRom,vec![
        FrameWarp::Placed(Similarity::IDENTITY),
        FrameWarp::Refused("control".into()),FrameWarp::Refused("control".into()),
    ]);
    for (label,r,warps,fit,needle) in [
        ("range",region(1,3),None,None,"contains 3 frames"),
        ("refused",region(1,2),Some(&map),Some(align_cmd::CoverFit::Scaled(1.0)),"no permitted placed"),
        ("coverage",region(0,0),Some(&map),Some(align_cmd::CoverFit::Uncovered),"covered alignment"),
        ("empty",RegionAdjustment {
            shape:RegionShape::Ellipse{center:[0.0,0.0],radius:[0.0001,0.0001]},
            ..region(0,0)
        },None,None,"no output sample"),
    ] {
        let path=saved_recipe(&dir,label,vec![r]);
        let error=Repairs::load(Some(&path)).unwrap().preflight(3,domain,warps,fit).unwrap_err();
        assert!(error.to_string().contains(needle),"{label}: {error}");
    }
}

#[test]
fn source_repair_progress_on_off_and_disabled_placebo_preserve_tiff_hash() {
    let dir=work_dir("source-repair-observer");
    let source=FixtureSource::new((0..4).map(|k|fixture_frame(96,72,k*9)).collect());
    let domain=PyramidDomain::whole(source.frames[0].geometry());
    let levels=source.frames[0].levels;
    let noise=profile::noise_model_for(&source.frames[0].camera,source.frames[0].iso,levels);
    let recipe_path=saved_recipe(&dir,"observer",vec![region(1,2)]);
    let repairs=Repairs::load(Some(&recipe_path)).unwrap();
    let (on,on_lines)=crate::ui_progress::Progress::captured_enabled(true);
    let (disabled,disabled_lines)=crate::ui_progress::Progress::captured_enabled(false);
    let mut hashes=Vec::new();
    for (label,progress) in [("off",None),("on",Some(&on)),("placebo",Some(&disabled))] {
        let mut planes=vec![vec![1234.0;domain.analysis().pixels()];4];
        repairs.apply(&mut planes,RepairContext {
            source:&source,domain,config:config(),levels,noise:&noise,
            warps:None,defect:None,per_chunk:2,progress,
        }).unwrap();
        let out=dir.join(format!("{label}.tiff"));
        write_merged(Merged::Bands { domain,planes:&planes },levels,None,None,
            image_out::OutputSpace::CameraLinear,true,
            Exposure::resolve(false,0.0,false).unwrap(),None,&out).unwrap();
        hashes.push(Sha256::digest(fs::read(&out).unwrap()));
    }
    assert_eq!(hashes[0],hashes[1]);
    assert_eq!(hashes[0],hashes[2]);
    assert!(disabled_lines.lock().unwrap().is_empty());
    let lines=on_lines.lock().unwrap();
    assert_eq!(lines.len(),4);
    assert!(lines[0].contains("completed=0 accepted=0 total=2 state=started"));
    assert!(lines[1].contains("index=1 completed=1 accepted=1 total=2 state=folded"));
    assert!(lines[2].contains("index=2 completed=2 accepted=2 total=2 state=folded"));
    assert!(lines[3].contains("completed=2 accepted=2 total=2 state=finished"));
    println!("source repair observer off/on/placebo TIFF sha256 {}",
        hashes[0].iter().map(|b|format!("{b:02x}")).collect::<String>());
}

#[test]
fn source_repair_retains_cropped_gauge_and_records_only_applied_master_recipe() {
    let dir=work_dir("source-repair-crop-master");
    let mut frames:Vec<_>=(0..3).map(|k|fixture_frame(128,96,k*17)).collect();
    for frame in &mut frames {
        frame.xyz_to_cam_rgbe=[
            [0.64,0.25,0.10],[0.20,0.73,0.08],[0.05,0.13,0.92],[0.0;3],
        ];
    }
    let crop=align_cmd::CropRect{x:8,y:6,width:48,height:32};
    let maps=vec![FrameWarp::Placed(Similarity::IDENTITY);3];
    let mut opts=fixture_options(dir.join("crop-repair.tiff"));
    opts.pyramid=config();
    opts.space=image_out::OutputSpace::LinearSrgb;
    opts.linear_master=Some(dir.join("repaired-master.tiff"));
    opts.region_recipe=Some(saved_recipe(&dir,"crop",vec![region(1,1)]));
    run_fixture(&opts,&FixtureSource::new(frames.clone()),Some(maps),Some(crop)).unwrap();
    let (w,h,actual,_)=read_tiff(opts.out.as_ref().unwrap());
    assert_eq!((w,h),(96,64));
    let master=strehl_edit::load_tiff(opts.linear_master.as_ref().unwrap()).unwrap();
    let recipe:DevelopmentRecipe=serde_json::from_slice(&fs::read(opts.region_recipe.as_ref().unwrap()).unwrap()).unwrap();
    assert_eq!(master.baked_recipe.as_ref(),Some(&recipe));
    assert_eq!((master.width,master.height),(w,h));
    master.validate_source_repairs(&recipe).unwrap();
    let mut tone_only=recipe.clone();
    tone_only.global.exposure=-1.0;
    tone_only.regions[0].adjustments.highlights=-30.0;
    master.validate_source_repairs(&tone_only).unwrap();
    tone_only.regions[0].source_range=Some(SourceRange{first:0,last:1});
    assert!(master.validate_source_repairs(&tone_only).is_err());
    assert!(master.validate_source_repairs(&DevelopmentRecipe::default()).is_err());

    opts.out=Some(dir.join("crop-single.tiff"));
    opts.linear_master=Some(dir.join("single-master.tiff"));
    opts.region_recipe=None;
    run_fixture(&opts,&FixtureSource::new(vec![frames[1].clone()]),
        Some(vec![FrameWarp::Placed(Similarity::IDENTITY)]),Some(crop)).unwrap();
    let (_,_,expected,_)=read_tiff(opts.out.as_ref().unwrap());
    assert_eq!(actual,expected,"repair must retain the original crop and CFA phase");
    let plain=strehl_edit::load_tiff(opts.linear_master.as_ref().unwrap()).unwrap();
    assert!(plain.baked_recipe.is_none());
}
