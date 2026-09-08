// Included only in the feature-gated child of the original M194g test bridge.
// It reuses the original admission, source, consumer, TIFF reader and writer.
use super::*;
use strehl_core::pyramid::m194h::{Arm, Observation, Session, Snapshot, TRACE_WORD_CAP};
use std::panic::{catch_unwind, AssertUnwindSafe};
const TEST: &str = "merge_cmd::known_scene_benchmark::noise_pupil_bridge::pedestal_causality::m194h_fixed_pedestal_case";
const CASE_ROOT: &str = "experiments/m194h-pedestal-causality/subject-1";
const RESULT_CAP: usize = 32 * 1024;
const PLAN_CAP: usize = 128 * 1024;
const HEADER_CAP: usize = 16 * 1024;
const GRANT_CAP: usize = 1024 * 1024;
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Case { ordinal: usize, seed: Option<u64>, arm: String, observation: String, output_directory: String }
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Grant {
    schema: String,
    source_bindings: BTreeMap<String,Binding>,
    noise_admission: Ref,
    matrix_index: Ref,
    quality_verification: Ref,
    binary: Ref,
    commands: Vec<Vec<String>>,
    cases: Vec<Case>,
}
fn parse_arm(s: &str) -> Result<Arm> { match s { "H"=>Ok(Arm::H),"P"=>Ok(Arm::P),"P0"=>Ok(Arm::P0),_=>bail!("M194h arm") } }
fn parse_observer(s: &str) -> Result<Observation> { match s { "off"=>Ok(Observation::Off),"on"=>Ok(Observation::On),"placebo"=>Ok(Observation::Placebo),_=>bail!("M194h observer") } }
fn case_spec(i: usize) -> (Option<u64>, &'static str, &'static str) {
    assert!(i<12);
    if i<9 {(Some(743),["H","P","P0"][i/3],["off","on","placebo"][i%3])}
    else {(None,["H","P","P0"][i-9],"off")}
}
fn extra_env(k: &str) -> Result<String> { std::env::var(format!("M194H_{k}")).with_context(||format!("missing M194H_{k}")) }
fn json_bytes(value: &Value, cap: usize) -> Result<Vec<u8>> {
    let mut bytes=serde_json::to_vec_pretty(value)?;bytes.push(b'\n');
    ensure!(bytes.len()<=cap,"M194h metadata prewrite capacity");Ok(bytes)
}
fn write_new(path: &Path, bytes: &[u8], cap: usize) -> Result<()> {
    use std::io::Write;
    ensure!(bytes.len()<=cap,"M194h artifact prewrite capacity");
    let mut f=fs::OpenOptions::new().write(true).create_new(true).open(path)?;
    f.write_all(bytes)?;f.sync_all()?;Ok(())
}
fn file_ref(path: &Path) -> Result<Value> {
    Ok(json!({"path":path.canonicalize()?,"bytes":fs::metadata(path)?.len(),"sha256":hash_file(path)?}))
}
// A fixed, prewritten refusal survives abort/kill. The current result is replaced
// only from a fully written same-directory stage. The outer actual exit prevails.
fn publish(root: &Path, value: &Value, initial: bool) -> Result<()> {
    let mut bytes=json_bytes(value,RESULT_CAP)?;
    bytes.resize(RESULT_CAP,b' ');*bytes.last_mut().unwrap()=b'\n';
    let final_path=root.join("result.json");
    if initial {write_new(&final_path,&bytes,RESULT_CAP)?;}
    else {
        let stage=root.join("result-stage.json");write_new(&stage,&bytes,RESULT_CAP)?;
        // std::fs::rename replaces this experiment's own file on Windows too.
        fs::rename(stage,final_path)?;
    }
    Ok(())
}
fn failure(error: &anyhow::Error) -> Value {
    let all=format!("{error:#}");
    let bounded:String=all.chars().take(1024).collect();
    json!({"text":bounded,"full_utf8_bytes":all.len(),"full_sha256":digest(all.as_bytes()),"truncated":all.chars().count()>1024})
}
fn header(s: &Snapshot, binary: Value) -> Value {
    json!({"schema":"m194h-core-trace-v1","status":if s.complete{"COMPLETE_CORE_CALLS_UNVERIFIED"}else{"INCOMPLETE_CORE_CALLS"},
        "format":"little-endian-u32-TLV-original-f32-bits","format_version":strehl_core::pyramid::m194h::FORMAT_VERSION,
        "arm":s.arm.name(),"observation":s.observation.name(),"production":s.production,
        "quad_sizes":s.sizes.iter().map(|s|[s.width,s.height]).collect::<Vec<_>>(),
        "native_crop_offset":[10,8],"native_sites":[[202,104],[205,113]],"cfa_plane_order":["R","G1","G2","B"],
        "support_indices":s.support,"support_rule":"all-four-plane union of full native5x5 MHC envelopes followed by exact nonzero inverse-expand closure",
        "binary":binary,"word_count":s.words.len(),"word_cap":TRACE_WORD_CAP,
        "calls":{"frames":s.frames,"bands":s.band_calls,"bases":s.base_calls,"resolved":s.resolved_calls,"pre_hull":s.pre_hull_calls,"post_hull":s.post_hull_calls,"absorb":s.absorb_calls,"reset":s.reset_calls},
        "observer_records":s.observer_records,"placebo_records":s.placebo_records,
        "scope":"actual four CFA-plane operands; RGB comes later through unchanged MHC and writer; partial data never implies a completed case"})
}
fn authority() -> Result<(PathBuf, Grant, Case, Ledger, Value, Value)> {
    let root=repo()?;let grant_path=PathBuf::from(extra_env("GRANT")?);
    ensure!(grant_path.is_absolute(),"M194h grant absolute path");
    let sha=extra_env("GRANT_SHA256")?;let mut ledger=Ledger::default();
    let value=unique(&ledger.raw(&grant_path,&sha,None,GRANT_CAP)?)?;
    let grant:Grant=serde_json::from_value(value)?;
    ensure!(grant.schema=="m194h-pedestal-causality-release-v1"&&grant.cases.len()==12,"M194h exact fixed release");
    for (i,c) in grant.cases.iter().enumerate() {
        let (seed,arm,observer)=case_spec(i);
        ensure!(c.ordinal==i&&c.seed==seed&&c.arm==arm&&c.observation==observer
            &&c.output_directory==format!("{CASE_ROOT}/case-{i:02}"),"M194h fixed case population");
    }
    let ordinal:usize=extra_env("CASE")?.parse()?;
    let selected=grant.cases.get(ordinal).context("M194h case out of range")?.clone();
    let mandatory=["crates/strehl-core/Cargo.toml","crates/strehl-cli/Cargo.toml",
        "crates/strehl-core/src/pyramid.rs","crates/strehl-cli/src/merge_cmd.rs",
        "crates/strehl-cli/src/merge_cmd/noise-pupil-bridge.rs",
        "crates/strehl-cli/src/merge_cmd/known-scene-benchmark.rs","crates/strehl-cli/src/image_out.rs",
        "crates/strehl-core/src/demosaic.rs","experiments/m194h-pedestal-causality/core-hook.rs",
        "experiments/m194h-pedestal-causality/component-controls.rs","experiments/m194h-pedestal-causality/production-bridge.rs",
        "experiments/m194h-pedestal-causality/preregister.md"];
    ensure!(mandatory.iter().all(|p|grant.source_bindings.contains_key(*p)),"M194h missing current source closure");
    let mut total=0u64;
    for b in grant.source_bindings.values() {
        ensure!(b.bytes>0&&b.bytes<=4*1024*1024,"M194h source byte cap");
        total=total.checked_add(b.bytes).context("M194h source extent overflow")?;
    }
    ensure!(total<=16*1024*1024,"M194h whole source closure cap");
    ledger.sources(&root,&grant.source_bindings)?;
    let exe=std::env::current_exe()?.canonicalize()?;
    let expected_exe=relative(&root,&grant.binary.path)?;
    ensure!(exe==expected_exe&&fs::metadata(&exe)?.len()==grant.binary.bytes
        &&hash_file(&exe)?==grant.binary.sha256,"M194h released actual binary");
    let actual:Vec<String>=std::env::args().collect();
    let expected_tail=["--exact",TEST,"--ignored","--test-threads=1","--nocapture"];
    ensure!(actual.len()==6&&actual[1..].iter().map(String::as_str).eq(expected_tail)
        &&Path::new(&actual[0]).canonicalize()?==exe
        &&grant.commands.len()==1&&grant.commands[0]==actual,"M194h exact actual argv and executable identity");
    for (name,_) in std::env::vars() {
        if name.starts_with("M194H_") {ensure!(["M194H_GRANT","M194H_GRANT_SHA256","M194H_CASE"].contains(&name.as_str()),"M194h unknown environment");}
        ensure!(!name.to_ascii_uppercase().starts_with("STREHL_M194G_BRIDGE_"),"M194h old bridge override present");
    }
    let environment=super::environment()?;
    ensure!(grant.noise_admission.path=="experiments/m194g-larger-pupil/independent-noise-files-1/noise-admission.json"
        &&grant.noise_admission.bytes==1082&&grant.noise_admission.sha256=="088272bfbeca6d00a816a5de72eeaf7aac8f8ca6e0ef68941ab236655fa298e7","M194h fixed original noise admission");
    ensure!(grant.matrix_index.path=="experiments/m194g-larger-pupil/production-matrix-1/run-index.json"
        &&grant.matrix_index.bytes==66801&&grant.matrix_index.sha256=="03e7ffe9028cca5d56266603db09fbadd3f7f3cc19e95db609007a96914d55ca","M194h fixed old matrix");
    ensure!(grant.quality_verification.path=="experiments/m194g-larger-pupil/independent-quality-result-check-1/result.json"
        &&grant.quality_verification.bytes==317942&&grant.quality_verification.sha256=="5a0c6dcc84608a64e7545ee9ac751441c468194347eb0cf7534793b0c971a4c5","M194h fixed independent prior quality verification");
    let (_,matrix)=ledger.json(&root,&grant.matrix_index)?;
    let (_,quality)=ledger.json(&root,&grant.quality_verification)?;
    ensure!(quality["status"]=="PASS_INDEPENDENT_FIXED_DIAGNOSTICS_ONLY"&&quality["error"].is_null(),"M194h prior diagnostic verification");
    let grant_ref=json!({"path":grant_path.canonicalize()?,"bytes":fs::metadata(&grant_path)?.len(),"sha256":sha});
    Ok((root,grant,selected,ledger,matrix,json!({"grant":grant_ref,"environment":environment})))
}
fn endpoint(root: &Path, ledger: &mut Ledger, matrix: &Value, c: &Case) -> Result<Value> {
    let ordinal=if c.seed.is_none(){0}else if c.arm=="H"{15}else{14};
    let rows=matrix["entries"].as_array().context("M194h old matrix entries")?;
    ensure!(rows.len()==38,"M194h old complete population");
    let row=&rows[ordinal];
    ensure!(row["ordinal"]==ordinal&&row["scene"]=="flat"&&row["seed"]==json!(c.seed),"M194h historical case association");
    let r:Ref=serde_json::from_value(row["receipt"].clone())?;
    let (_,receipt)=ledger.json(root,&r)?;
    let image:Ref=serde_json::from_value(row["tiff"].clone())?;
    ledger.file(root,&image,512*1024)?;
    ensure!(receipt["output"]["sha256"]==image.sha256&&receipt["output"]["bytes"]==image.bytes,"M194h old TIFF receipt association");
    Ok(json!({"required_identity":c.seed.is_none()||c.arm!="P0","ordinal":ordinal,"receipt":r,"tiff":image,"output":receipt["output"]}))
}
fn run_case() -> Result<()> {
    let (root,grant,c,mut ledger,matrix,authority)=authority()?;
    let out_root=root.join(&c.output_directory);
    ensure!(!out_root.exists(),"M194h fresh case directory required");
    ensure!(out_root.parent().context("M194h parent")?.is_dir(),"M194h subject directory must be prepared");
    fs::create_dir(&out_root)?;
    let mut result=json!({"schema":"m194h-pedestal-case-v1","status":"INITIAL_INCOMPLETE","case":c,"authority":authority,"science_complete":false});
    publish(&out_root,&result,true)?;
    let execution=(||->Result<()> {
        let arm=parse_arm(&c.arm)?;let observation=parse_observer(&c.observation)?;
        let old=endpoint(&root,&mut ledger,&matrix,&c)?;
        let input_path=relative(&root,&grant.noise_admission.path)?;
        let inputs=Inputs::load(&input_path,&grant.noise_admission.sha256)?;
        let settings=Settings{scene:"flat".into(),seed:c.seed,subset:"all".into(),admission:arm.admission(),observer:Observer::Count};
        let environment=super::environment()?;
        let (_,_,original_plan)=super::plan(&inputs,&settings,&environment)?;
        ensure!(original_plan["geometry"]["canonical_native_offset"]==json!([10,8])
            &&original_plan["geometry"]["output_native"]==json!([300,226])
            &&original_plan["geometry"]["level_sizes"]==json!([[150,113],[75,57],[38,29],[19,15]]),"M194h exact consumer geometry");
        let plan=json!({"schema":"m194h-pedestal-plan-v1","case":c,"authority":authority,"original_consumer_plan":original_plan,
            "experiment":{"arm":c.arm,"observation":c.observation,"cutoff_only":arm==Arm::P0,"zero_condition":"E<=F before actual accumulate_level; positive-excess P weights unchanged","frame_indices":[0,1,2,3,4]},"historical_endpoint":old});
        let plan_path=out_root.join("plan.json");write_new(&plan_path,&json_bytes(&plan,PLAN_CAP)?,PLAN_CAP)?;
        result["plan"]=file_ref(&plan_path)?;
        let selected=inputs.selected(&settings)?;
        let source=Source::new(selected.iter().map(|f|relative(&inputs.bundle_root,&f.cfa.path)).collect::<Result<_>>()?,
            selected.iter().map(|f|f.cfa.sha256.clone()).collect(),settings.indices(),Observer::Count)?;
        let image_path=out_root.join("output.tif");
        let session=Session::production(arm,observation);
        let call=catch_unwind(AssertUnwindSafe(||super::run_source(image_path.clone(),&settings,&source)));
        let snapshot=session.take();
        let mut bytes=Vec::with_capacity(snapshot.words.len()*4);
        for &w in &snapshot.words {bytes.extend_from_slice(&w.to_le_bytes());}
        let bin=out_root.join("trace.bin");write_new(&bin,&bytes,TRACE_WORD_CAP*4)?;
        let trace=header(&snapshot,file_ref(&bin)?);
        let trace_path=out_root.join("trace.json");write_new(&trace_path,&json_bytes(&trace,HEADER_CAP)?,HEADER_CAP)?;
        result["trace"]=file_ref(&trace_path)?;
        match call {Ok(r)=>r?,Err(_)=>bail!("M194h consumer panic; original panic text is retained in actual stderr")}
        ensure!(snapshot.complete,"M194h incomplete actual core lifecycle");
        ensure!(source.counts()==vec![1;5]&&source.hooks.load(Ordering::SeqCst)==5,"M194h fixed source observer requires each original index exactly once");
        let image=super::tiff(&image_path)?;
        ensure!(image["width"]==300&&image["height"]==226,"M194h actual output shape");
        ensure!(fs::metadata(&image_path)?.len()<=512*1024,"M194h actual output file cap");
        if old["required_identity"]==true {
            for key in ["bytes","sha256","pixel_sha256_le","width","height","channels","sample_type","software"] {
                ensure!(image[key]==old["output"][key],"M194h archived whole TIFF endpoint mismatch at {key}");
            }
        }
        result["source_decode_counts"]=json!(source.counts());
        result["source_hook_calls"]=json!(source.hooks.load(Ordering::SeqCst));
        result["output"]=image.clone();
        result["historical_endpoint"]=old;
        result["inputs_unchanged"]=json!(true);
        inputs.ledger.check()?;ledger.check()?;super::check_output(&image_path,&image)?;
        result["status"]=json!("COMPLETE_CASE_UNVERIFIED");result["science_complete"]=json!(true);
        publish(&out_root,&result,false)?;
        // Same exact input/output association after publication. A failure is
        // revoked below and actual outer exit must still agree with canonical.
        inputs.ledger.check()?;ledger.check()?;super::check_output(&image_path,&image)?;
        Ok(())
    })();
    if let Err(e)=execution {
        result["status"]=json!("REFUSED");result["science_complete"]=json!(false);result["error"]=failure(&e);
        let note=out_root.join("failure.json");
        if let Ok(bytes)=json_bytes(&json!({"schema":"m194h-case-failure-v1","case":c,"error":failure(&e)}),8*1024) {
            let _=write_new(&note,&bytes,8*1024);
        }
        if let Err(revoke)=publish(&out_root,&result,false) {
            eprintln!("M194H_REFUSAL_PUBLICATION_FAILED {revoke:#}");
        }
        return Err(e);
    }
    println!("M194H_CASE_COMPLETE {}",c.ordinal);Ok(())
}
#[test]
#[ignore = "M194h twelve fixed cases require exact source, build, controls and release"]
fn m194h_fixed_pedestal_case() -> Result<()> {run_case()}
