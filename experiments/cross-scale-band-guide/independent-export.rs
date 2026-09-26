// Test-only orchestration. Root runs each split in a separate bounded process.
use super::*;
mod export_consumer {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/cross-scale-band-guide/export-consumer.rs"));
}
mod independent_fixtures {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/cross-scale-band-guide/independent-fixtures.rs"));
    use std::io::Write;

    fn save(path:&Path,value:&Value){serde_json::to_writer_pretty(std::fs::OpenOptions::new().write(true).create_new(true).open(path).unwrap(),value).unwrap();}
    fn output_blob(out:&Path,name:&str,values:&[f32],case:&Case)->Value{
        let crop=case.crop();assert_eq!(values.len(),4*crop.width*crop.height*3);assert!(values.iter().all(|v|v.is_finite()));
        let p=out.join(format!("{name}.f32"));let file=std::fs::OpenOptions::new().write(true).create_new(true).open(&p).unwrap();
        let mut file=std::io::BufWriter::with_capacity(1<<20,file);
        for value in values{file.write_all(&value.to_le_bytes()).unwrap();}file.flush().unwrap();
        json!({"file":p.file_name().unwrap().to_string_lossy(),"shape":[2*crop.height,2*crop.width,3],"dtype":"<f4","sha256":hash32(values)})
    }

    #[test]
    fn export_dataset(){
        let config_path=PathBuf::from(std::env::var("STREHL_CROSS_SCALE_EXPORT_CONFIG").expect("bounded explicit export config"));
        let conf:Value=serde_json::from_slice(&std::fs::read(&config_path).unwrap()).unwrap();
        let training=match conf["split"].as_str().unwrap(){"training"=>true,"heldout"=>false,_=>panic!("explicit independent split required")};
        let out=PathBuf::from(conf["out"].as_str().unwrap());assert!(!out.exists(),"fresh native export output");std::fs::create_dir_all(&out).unwrap();
        let t=textures(Path::new(conf["textures"].as_str().unwrap()),training);
        let all=cases();let salts=all.iter().map(noise_salt).collect::<std::collections::BTreeSet<_>>();
        assert_eq!(salts.len(),all.len(),"every case must have its own noise draw family");
        for case in all.iter().filter(|c|c.family==Family::Scale){
            assert_eq!((0..case.n).map(|k|case.focus(k)).collect::<Vec<_>>(),vec![0.0,0.22,0.5,0.78,1.0]);
        }
        let wanted=all.into_iter().filter(|c|c.training==training).collect::<Vec<_>>();
        assert_eq!(wanted.len(),if training{24}else{10});
        let(mut records,mut labels)=(Vec::new(),Vec::new());
        for case in wanted{
            eprintln!("CROSS_SCALE_EXPORT begin {}",case.id);
            let generated=generate(&case,&t);let folder=out.join(&case.id);
            let noise=profile::noise_model_for("ILCE-7CM2",Some(case.iso),levels());
            let cfg=MergeConfig{bands:case.bands(),..Default::default()};
            let result=super::export_consumer::export_case(&generated.frames,&generated.transforms,case.crop(),&noise,cfg,&generated.truth,&folder).unwrap();
            assert_eq!(result["zero_network_uniform_exact"],true);assert_eq!(result["terminal_mean_exact"],true);
            assert_eq!(result["source_count"],case.n);assert_eq!(result["level_sizes"].as_array().unwrap().len(),case.bands()+1);
            let templates=json!({"base":output_blob(&folder,"truth-base",&generated.base,&case),
                "near":output_blob(&folder,"truth-near",&generated.near_detail,&case),
                "far":output_blob(&folder,"truth-far",&generated.far_detail,&case)});
            let label=metadata(&case,&generated,&t);
            save(&folder.join("independent-truth.json"),&json!({"schema":1,"label":label,"templates":templates,
                "scope":"Independent fixture truth/components only. Predictor must not read this file or truth arrays during inference."}));
            labels.push(label);records.push(folder.join("case.json"));
            eprintln!("CROSS_SCALE_EXPORT complete {}",case.id);
        }
        save(&out.join("dataset.json"),&json!({"schema":1,"split":if training{"training"}else{"heldout"},"cases":records,
            "old19_are_developer_visible":true,"heldout_candidate_scores_read":false,"photographic_replay_admitted":false}));
        save(&out.join("fixture-labels.json"),&json!({"schema":1,"cases":labels,"textures_sha256":t.sha,
            "original_texture_sources":t.manifest["sources"],"original_raw_reads":false,"calibration_validation":false}));
        save(&out.join("completion.json"),&json!({"status":"NATIVE_EXPORT_COMPLETE","cases":if training{24}else{10},
            "split":if training{"training"}else{"heldout"},"original_linear_reconstruction":true,"photographic_replay_admitted":false}));
    }
}
