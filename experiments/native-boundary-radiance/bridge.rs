// New experiment identity; reuses admitted M194g source and the existing production consumer.
use super::*;
use crate::merge_cmd::native_boundary_radiance::{Configuration, ConfiguredSource};
const BP: &str = "STREHL_BOUNDARY_BRIDGE_";
fn boundary_env(name: &str) -> Result<String> {
    std::env::var(format!("{BP}{name}")).with_context(||format!("missing {BP}{name}"))
}
fn boundary_environment() -> Result<BTreeMap<String,String>> {
    let required = [("STREHL_DEFECT","off"),("STREHL_FIX_CA","off"),
        ("STREHL_FULLRES_GATHER","1"),("STREHL_PYRAMID_WORKERS","2"),("RAYON_NUM_THREADS","2")];
    let allowed = ["MODE","SCENE","SEED","NOISE_ADMISSION","NOISE_ADMISSION_SHA256","OUTPUT","RECEIPT"];
    for (key,value) in required {
        ensure!(std::env::var(key).as_deref()==Ok(value),"boundary bridge requires {key}={value}");
    }
    for (key,_) in std::env::vars() {
        if key.to_ascii_uppercase().starts_with("STREHL_") {
            ensure!(required.iter().any(|(r,_)|key==*r)
                || key.strip_prefix(BP).is_some_and(|k|allowed.contains(&k)),
                "boundary bridge unknown override {key}");
        }
    }
    ensure!(gatefloor::enabled(),"boundary bridge requires measured floor");
    Ok(required.into_iter().map(|(k,v)|(k.into(),v.into())).collect())
}
#[test]
#[ignore = "Requires existing admitted M194g CFA inputs and new experiment output paths"]
fn m194g_boundary_radiance_consumer() -> Result<()> {
    let environment = boundary_environment()?;
    let mode = boundary_env("MODE")?;
    let configuration = match mode.as_str() {
        "off" => None,
        "no-treatment" => Some(Configuration::NoTreatment),
        "apply" => Some(Configuration::M194g { boundary_offset:142.0 }),
        "displaced" => Some(Configuration::M194g { boundary_offset:146.0 }),
        _ => bail!("boundary bridge unknown treatment mode"),
    };
    let seed = boundary_env("SEED")?;
    let settings = Settings {
        scene:boundary_env("SCENE")?,seed:if seed=="noise-off" { None } else { Some(seed.parse()?) },
        subset:"all".into(),admission:AdmissionMode::HardFloor,observer:Observer::Count,
    };
    settings.validate()?;
    let inputs = Inputs::load(Path::new(&boundary_env("NOISE_ADMISSION")?),
        &boundary_env("NOISE_ADMISSION_SHA256")?)?;
    let selected = inputs.selected(&settings)?;
    ensure!(selected.iter().map(|f|f.index).eq(0..5),"boundary bridge requires original all-five order");
    let output = PathBuf::from(boundary_env("OUTPUT")?);
    let receipt = PathBuf::from(boundary_env("RECEIPT")?);
    new_paths(&[output.clone(),receipt.clone()])?;
    let source = Source::new(selected.iter().map(|f|relative(&inputs.bundle_root,&f.cfa.path))
        .collect::<Result<_>>()?,selected.iter().map(|f|f.cfa.sha256.clone()).collect(),
        settings.indices(),Observer::Count)?;
    inputs.ledger.check()?;
    let start = Instant::now();
    if let Some(configuration) = configuration {
        run_source(output.clone(),&settings,&ConfiguredSource::new(&source,configuration))?;
    } else {
        run_source(output.clone(),&settings,&source)?;
    }
    let seconds = start.elapsed().as_secs_f64();
    ensure!(source.counts()==vec![1;5] && source.hooks.load(Ordering::SeqCst)==5,
        "boundary bridge must consume each original CFA once");
    let image = tiff(&output)?;
    ensure!(image["width"]==300 && image["height"]==226,"boundary bridge crop extent changed");
    inputs.ledger.check()?;
    let exe = std::env::current_exe()?;
    let result = json!({"schema":"native-boundary-radiance-consumer-v1","status":"COMPLETE_UNVERIFIED",
        "candidate":"M194g-oracle-local-affine-v1","mode":mode,"scene":settings.scene,"seed":settings.seed,
        "noise_admission_sha256":inputs.authority_sha,"selected":selected,
        "geometry":{"native":[320,240],"crop_offset_native":[10,8],"reference_original":2,
            "normal":[1.0,-0.15],"true_offset":142,"model_offset":if mode=="displaced" {146} else {142},
            "inverse_foci":[0.5,0.625,0.75,0.875,1.0],"pupil_k":12,"depths":[1,2],"oracle":true},
        "treatment":{"native_radius":2,"fixed_band_offset":142,"fixed_band_half_width":8,
            "minimum_observations":12,"minimum_normalized_schur_pivot":0.0001,
            "variance_ceiling":"minimum injected individual observation variance",
            "residual_rejection":false,"wb_applied_by_existing_writer_once":true},
        "output":image,"decode_counts":source.counts(),"consumer_wall_seconds":seconds,
        "environment":environment,"executable_sha256":hash_file(&exe)?,"inputs_unchanged":true,
        "diagnostics":"actual boundary radiance and floor lines in bound stderr",
        "old_m194g_plan_authority":false});
    // A new receipt is published only after the old admitted-input checks and
    // existing TIFF reader succeed; it makes no claim about the frozen old plan.
    check_output(&output,&image)?;
    write_json_new(&receipt,&result)?;
    Ok(())
}
