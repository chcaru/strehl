// Test-only native adapter. Included into merge_cmd; no alternate numerical kernels.
use super::*;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::sync::{Mutex, OnceLock};
use strehl_core::align::Similarity;
use strehl_core::warpmap::Provenance as WarpProvenance;

const SIDES: [usize; 5] = [128, 64, 32, 16, 8];
const ROOT_INPUT: &str = "D:/personal/macro/requests";
const MAX_JSON: usize = 64 << 10;
const MAX_TRACE: usize = 2 << 20;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Observe { Off, On, Placebo, Absent }
impl Observe {
    fn name(self) -> &'static str { match self {
        Self::Off => "off", Self::On => "on", Self::Placebo => "placebo", Self::Absent => "absent",
    }}
}
struct CliCapture {
    mode: Observe, original: usize, route: usize,
    prepared: Option<Vec<u8>>, prepared_seen: bool,
    arrays: Vec<(u32, Vec<u32>)>,
    inputs: Option<Value>, after: Option<String>, maps: Vec<Value>,
}
static CLI_ACTIVE: OnceLock<Mutex<Option<CliCapture>>> = OnceLock::new();
fn cli_state() -> &'static Mutex<Option<CliCapture>> { CLI_ACTIVE.get_or_init(|| Mutex::new(None)) }
struct CliSession;
impl CliSession {
    fn begin(mode: Observe, original: usize, route: usize) -> Self {
        let mut s = cli_state().lock().expect("native CLI observer lock");
        assert!(s.is_none(), "native CLI nested observer");
        *s = Some(CliCapture { mode, original, route, prepared: None, prepared_seen: false,
            arrays: Vec::new(), inputs: None, after: None, maps: Vec::new() });
        Self
    }
    fn finish(self) -> CliCapture {
        cli_state().lock().expect("native CLI observer lock").take().expect("native CLI session")
    }
}
impl Drop for CliSession {
    fn drop(&mut self) { if let Ok(mut s) = cli_state().lock() { *s = None; } }
}
fn hex(bytes: &[u8]) -> String {
    const H: &[u8] = b"0123456789abcdef";
    let mut s = String::with_capacity(bytes.len() * 2);
    for b in bytes { s.push(H[(b >> 4) as usize] as char); s.push(H[(b & 15) as usize] as char); }
    s
}
fn hash(raw: &[u8]) -> String { hex(Sha256::digest(raw).as_ref()) }
fn f32_hash(values: &[f32]) -> String {
    let mut h = Sha256::new();
    for v in values { h.update(v.to_bits().to_le_bytes()); }
    hex(h.finalize().as_ref())
}
fn roi(frame: &Frame, domain: PyramidDomain) -> Vec<u8> {
    assert_eq!((domain.rect.x, domain.rect.y, domain.rect.width, domain.rect.height), (1694,1108,128,128));
    let mut raw = Vec::with_capacity(131072);
    let x = frame.active.x + 2 * domain.rect.x;
    let y = frame.active.y + 2 * domain.rect.y;
    for row in 0..256 {
        let start = (y + row) * frame.stride + x;
        for v in &frame.data[start..start + 256] { raw.extend_from_slice(&v.to_le_bytes()); }
    }
    assert_eq!(raw.len(), 131072);
    raw
}
// Hook after real/probe warp has finished and before actual extract_planes.
pub(super) fn prepared(frame: &Frame, domain: PyramidDomain) {
    let mut s = cli_state().lock().expect("native CLI observer lock");
    let Some(a) = s.as_mut() else { return; };
    assert!(!a.prepared_seen, "native prepared ROI repeated");
    a.prepared_seen = true;
    if a.mode == Observe::On { a.prepared = Some(roi(frame, domain)); }
    if a.mode == Observe::Placebo { a.prepared = Some(vec![0; 131072]); }
}
// Mandatory identity hashes are common; optional retained arrays participate in on/placebo.
pub(super) fn inputs(planes: &[Vec<f32>], luma: &[f32], variance: &[f32], beta: Option<&[f32]>) {
    let mut s = cli_state().lock().expect("native CLI observer lock");
    let Some(a) = s.as_mut() else { return; };
    assert!(a.inputs.is_none() && planes.len() == 4 && luma.len() == 16384 && variance.len() == 16384);
    a.inputs = Some(json!({
        "plane_sha256": planes.iter().map(|p| f32_hash(p)).collect::<Vec<_>>(),
        "luma_sha256": f32_hash(luma), "variance_before_sha256": f32_hash(variance),
        "beta_bits": beta.unwrap_or(&[]).iter().map(|v| v.to_bits()).collect::<Vec<_>>()
    }));
    if matches!(a.mode, Observe::On | Observe::Placebo) {
        for (tag, values) in planes.iter().map(|p| p.as_slice()).chain([luma,variance]).enumerate() {
            let v = if a.mode == Observe::On { values.iter().map(|v| v.to_bits()).collect() }
                else { vec![0; 16384] };
            a.arrays.push((100 + tag as u32, v));
        }
    }
}
pub(super) fn after(variance: &[f32]) {
    let mut s = cli_state().lock().expect("native CLI observer lock");
    let Some(a) = s.as_mut() else { return; };
    assert!(a.after.is_none());
    a.after = Some(f32_hash(variance));
}
// Called at the existing fullres per-CFA-site compose result, never at pixels.
// Passes actual resolved values; this function does not resolve a profile or map.
#[allow(clippy::too_many_arguments)]
pub(crate) fn gather_site(
    path: &Path, gain: &[f32; 3], model: Option<&str>, lens: Option<u16>,
    ca: Option<&strehl_core::optics::OpticalProfile>, dx: usize, dy: usize, t: Similarity,
) {
    let mut s = cli_state().lock().expect("native CLI observer lock");
    let Some(a) = s.as_mut() else { return; };
    if !matches!(a.mode, Observe::On | Observe::Placebo) { return; }
    assert_eq!(a.route, 1, "no-map reached fullres observer");
    assert!(a.maps.len() < 8 && (dx,dy) == ((a.maps.len()%4)%2,(a.maps.len()%4)/2), "native map order");
    let v = if a.mode == Observe::On {
        json!({"path":path,"wb_gain_bits":gain.map(f32::to_bits),"model":model,"lens_type3":lens,
            "profile_key":ca.map(|c| c.key),"profile_debug":ca.map(|c| format!("{c:?}")),
            "dx":dx,"dy":dy,"similarity_bits":[t.a.re.to_bits(),t.a.im.to_bits(),t.b.re.to_bits(),t.b.im.to_bits()],
            "warp_kind":if a.maps.len()<4 {"real"} else {"synthetic-probe"}})
    } else {
        json!({"path":"PLACEBO","wb_gain_bits":[0,0,0],"model":null,"lens_type3":null,
            "profile_key":null,"profile_debug":null,"dx":dx,"dy":dy,"similarity_bits":[0,0,0,0],
            "warp_kind":if a.maps.len()<4 {"real"} else {"synthetic-probe"}})
    };
    a.maps.push(v);
}
fn write_new(path: &Path, raw: &[u8], cap: usize) -> Result<Value> {
    ensure!(raw.len() <= cap, "native artifact capacity {}", path.display());
    let stage = path.with_extension(format!("{}.stage",path.extension().and_then(|s| s.to_str()).unwrap_or("bin")));
    ensure!(!path.exists() && !stage.exists(), "native artifact already exists");
    let mut f = OpenOptions::new().write(true).create_new(true).open(&stage)?;
    f.write_all(raw)?; f.sync_all()?; drop(f);
    fs::hard_link(&stage, path).with_context(|| format!("create-only publication {}",path.display()))?;
    fs::remove_file(&stage)?;
    Ok(json!({"path":path,"bytes":raw.len(),"sha256":hash(raw)}))
}
fn json_new(path: &Path, value: &Value) -> Result<Value> {
    let mut raw = serde_json::to_vec(value)?; raw.push(b'\n');
    write_new(path, &raw, MAX_JSON)
}
fn source_ref(path: &Path) -> Result<Value> {
    let before = fs::metadata(path)?;
    ensure!(before.is_file() && before.len()>0 && before.len() <= 38825984, "native original extent");
    let mut f = File::open(path)?;
    let opened = f.metadata()?;
    ensure!(opened.len()==before.len() && opened.modified()?==before.modified()?, "native source open changed");
    let mut h = Sha256::new(); let mut buf=[0u8;65536]; let mut total=0u64;
    loop {
        let n=f.read(&mut buf)?; if n==0 {break;}
        total=total.checked_add(n as u64).context("native source extent overflow")?;
        ensure!(total<=before.len(), "native source grew"); h.update(&buf[..n]);
    }
    let closed=f.metadata()?; let named=fs::metadata(path)?;
    ensure!(total==before.len() && closed.len()==opened.len() &&
        closed.modified()?==opened.modified()? && named.len()==before.len() &&
        named.modified()?==before.modified()?, "native source changed during hash");
    Ok(json!({"path":path,"bytes":total,"sha256":hex(h.finalize().as_ref())}))
}
fn same_metadata(path: &Path, before: &fs::Metadata) -> Result<()> {
    let after=fs::metadata(path)?;
    ensure!(after.len()==before.len() && after.modified()?==before.modified()?, "native source changed around decode");
    Ok(())
}
fn paths_for(invocation: usize) -> (Vec<PathBuf>, Observe, usize) {
    assert!(invocation<9);
    let (paper, count, mode) = match invocation {
        0=>(true,5,Observe::On),1=>(false,22,Observe::On),
        2=>(true,5,Observe::Off),3=>(true,5,Observe::Placebo),
        4=>(false,2,Observe::On),5=>(false,2,Observe::Off),6=>(false,2,Observe::Placebo),
        7=>(true,5,Observe::Absent),8=>(false,2,Observe::Absent),_=>unreachable!()
    };
    let (dir,start,base) = if paper {("10-paper-iso-var",235,0)} else {("6-11-extended-dark-frames",872,5)};
    let paths=(0..count).map(|i| Path::new(ROOT_INPUT).join(dir).join(format!("DSC{:05}.ARW",start+i))).collect();
    (paths,mode,base)
}
struct OneFrameSource { frame: Mutex<Option<Frame>>, index: usize, len: usize }
impl PyramidFrameSource for OneFrameSource {
    fn len(&self) -> usize { self.len }
    fn decode(&self, index: usize) -> Result<Frame> {
        ensure!(index==self.index,"native handoff index");
        self.frame.lock().map_err(|_|anyhow::anyhow!("native handoff poisoned"))?
            .take().context("native frame consumed twice")
    }
}
fn check_frame(frame: &Frame) -> Result<()> {
    ensure!(frame.camera=="ILCE-7CM2" && frame.iso==Some(160.0),"native camera/ISO authority");
    ensure!((frame.active.x,frame.active.y,frame.active.width,frame.active.height)==(0,0,7032,4688),
        "native active domain authority");
    ensure!((frame.stride,frame.buffer_height)==(7168,5120) && frame.data.len()==7168*5120,
        "native buffer authority");
    ensure!(frame.levels.black.is_finite() && frame.levels.black>=0.0 &&
        frame.levels.white==15360.0 && frame.levels.black<frame.levels.white,"native levels");
    validate_pyramid_frame(frame,PlaneGeometry{width:3516,height:2344},0)?;
    Ok(())
}
fn field(raw: &mut Vec<u8>, tag: u32, level: u32, plane: u32, words: &[u32]) {
    for v in [tag,level,plane,words.len() as u32] {raw.extend_from_slice(&v.to_le_bytes());}
    for v in words {raw.extend_from_slice(&v.to_le_bytes());}
    assert!(raw.len()<=MAX_TRACE,"native trace capacity");
}
#[cfg(feature="native-sensor-transfer")]
fn core_mode(mode: Observe) -> strehl_core::pyramid::native_sensor_transfer::Mode {
    use strehl_core::pyramid::native_sensor_transfer::Mode;
    match mode {Observe::On=>Mode::On,Observe::Placebo=>Mode::Placebo,Observe::Off=>Mode::Off,Observe::Absent=>panic!("feature-off arm on feature binary")}
}
fn environment() -> Result<Value> {
    let forbidden=["STREHL_GATE_FLOOR","STREHL_GATE_FLOOR_SCALE","STREHL_PYRAMID_MEAN_COARSE",
        "STREHL_PYRAMID_SIGNIFICANCE","STREHL_PYRAMID_WEIGHT_DUMP","STREHL_HULL",
        "STREHL_FIX_CA","STREHL_DEFECT","STREHL_DEFECT_MAP","STREHL_DEFECT_ARM","STREHL_DEFECT_HOT_FLOOR",
        "STREHL_RESTORE","STREHL_CONFIDENCE_DEBUG"];
    for name in forbidden {ensure!(std::env::var_os(name).is_none(),"unexpected override {name}");}
    ensure!(std::env::var_os("STREHL_FULLRES_GATHER").is_none(),"fullres must use current default");
    let threads=std::env::var(BAND_WORKERS_ENV).context("fixed execution threads missing")?;
    ensure!(threads=="4","native execution threads must be4");
    Ok(json!({"unset":forbidden,"fullres":"current-default-on","execution_threads":{"name":BAND_WORKERS_ENV,"value":threads},
        "defect":"current-default-none","ca":"current-default-gear-guarded","restoration":false}))
}
fn run_pair(invocation: usize, out: &Path) -> Result<Value> {
    let (paths,mode,ordinal_base)=paths_for(invocation);
    #[cfg(feature="native-sensor-transfer")]
    ensure!(mode!=Observe::Absent,"feature-on binary used for feature-off arm");
    #[cfg(not(feature="native-sensor-transfer"))]
    ensure!(mode==Observe::Absent,"feature-off binary used for observer arm");
    let env=environment()?;
    let cfg=MergeConfig::default();
    ensure!(cfg.bands==7 && cfg.gate==2.0 && cfg.exponent==2.0 && cfg.sharpen_per_octave==1.4 &&
        cfg.mean_coarse==0 && cfg.significance_scale==0.0 && cfg.admission==AdmissionMode::HardFloor &&
        cfg.select==SelectMode::SoftPower && cfg.base==BaseBand::Mean,"native current config");
    let geom=PlaneGeometry{width:3516,height:2344};
    let domain=PyramidDomain::cropped(geom,align_cmd::CropRect{x:1694,y:1108,width:128,height:128})?;
    let sizes=level_sizes(128,128,cfg.bands);
    ensure!(sizes.iter().map(|s|(s.width,s.height)).collect::<Vec<_>>()==SIDES.map(|s|(s,s)),"native actual levels");
    let entries:Vec<_>=paths.iter().map(|p| Ok((p.to_string_lossy().into_owned(),fs::metadata(p)?.len())))
        .collect::<Result<_>>()?;
    let map=WarpMap::new(WarpProvenance{
        stack:StackIdentity::from_entries("native-sensor-transfer",&entries),
        strategy:"literal-geometric-identity".into(),heldout_px:None,cycle_floor_px:None,reference:0,
        note:"Crop sensor transfer; no physical placement claim".into()
    },geom,Resampler::CatmullRom,vec![FrameWarp::Placed(Similarity::IDENTITY);paths.len()]);
    let mut workers=[BandWorker::new(domain,cfg),BandWorker::new(domain,cfg)];
    let mut merged:[Option<BandMerge>;2]=[None,None];
    let mut rows=Vec::new();
    let mut levels=None; let mut noise=None; let mut partition=None;
    let mut output_wb=None; let mut output_matrix=None;
    let mut pool=None; let mut decoded=0usize;
    for (index,path) in paths.iter().enumerate() {
        let source=source_ref(path)?;
        let before=fs::metadata(path)?;
        let original=strehl_raw::decode(path).with_context(||format!("native decode {}",path.display()))?;
        decoded+=1; same_metadata(path,&before)?; check_frame(&original)?;
        ensure!(original.path==*path,"decoder source path identity");
        if index==0 {
            levels=Some(original.levels);
            output_wb=original.wb_gains(); output_matrix=original.xyz_to_cam_rgb_with_source();
            let model=profile::noise_model_for(&original.camera,original.iso,original.levels);
            ensure!(model.provenance==strehl_core::noise::Provenance::Profile && model.prnu().is_none(),"native model provenance");
            noise=Some(model);
            let fullsizes=level_sizes(geom.width,geom.height,cfg.bands);
            let acc=BandMerge::planning_accumulator_floats(geom.width,geom.height,4,cfg);
            let ws=FrameWorkspace::planning_floats(&fullsizes,4);
            let planning=4*(acc+ws+6*geom.pixels())+original.allocated_bytes();
            let chunks=canonical_band_chunks(planning,paths.len());
            let execution=band_workers(planning,paths.len())?;
            partition=Some((planning,chunks,paths.len().div_ceil(chunks),execution));
            pool=Some(ThreadPoolBuilder::new().num_threads(execution).build()?);
        }
        ensure!(Some(original.levels)==levels,"native per-frame levels changed");
        let raw=roi(&original,domain);
        let raw_ref=write_new(&out.join(format!("frame-{index:02}-original.u16")), &raw,131072)?;
        let row_hashes=raw.chunks_exact(512).map(hash).collect::<Vec<_>>();
        let metadata=json!({"source":source,"original_roi":raw_ref,"original_rows_sha256":row_hashes,
            "path":original.path,"camera":original.camera,"iso_bits":original.iso.map(f32::to_bits),
            "buffer":[original.stride,original.buffer_height],"active":[original.active.x,original.active.y,original.active.width,original.active.height],
            "levels_bits":[original.levels.black.to_bits(),original.levels.white.to_bits()],
            "wb_coeff_bits":original.wb_coeffs.map(f32::to_bits),"model":"profile::noise_model_for",
            "model_planes": [CfaPlane::R,CfaPlane::G1,CfaPlane::G2,CfaPlane::B].map(|p|{
                let n=noise.as_ref().unwrap().plane(p);
                [n.gain_dn_per_e.to_bits(),n.read_noise_e.to_bits(),n.levels.black.to_bits(),n.levels.white.to_bits()]
            })});
        let mut frames=[Some(original.clone()),Some(original)];
        for route in 0..2 {
            let handoff=OneFrameSource{frame:Mutex::new(frames[route].take()),index,len:paths.len()};
            let session=CliSession::begin(mode,ordinal_base+index,route);
            #[cfg(feature="native-sensor-transfer")]
            let core=strehl_core::pyramid::native_sensor_transfer::begin(core_mode(mode),invocation as u32,
                (ordinal_base+index) as u32,route as u32);
            let folded=pool.as_ref().unwrap().install(||workers[route].fold(&handoff,index,levels.unwrap(),
                noise.as_ref().unwrap(),if route==0{None}else{Some(&map)},None))?;
            ensure!(folded && handoff.frame.lock().unwrap().is_none(),"native actual handoff/fold");
            #[cfg(feature="native-sensor-transfer")]
            let observed=core.finish();
            let capture=session.finish();
            #[cfg(feature="native-sensor-transfer")]
            {
                ensure!(capture.prepared_seen && capture.inputs.is_some() && capture.after.is_some(),"native CLI observed population");
                ensure!(capture.inputs.as_ref().unwrap()["variance_before_sha256"]==capture.after.as_ref().unwrap().as_str(),"injected variance mutated");
                ensure!(capture.maps.len()==if mode==Observe::On||mode==Observe::Placebo {route*8}else{0},"actual gather map population");
            }
            let mut trace_ref=Value::Null; let mut prepared_ref=Value::Null;
            #[cfg(feature="native-sensor-transfer")]
            if matches!(mode,Observe::On|Observe::Placebo) {
                prepared_ref=write_new(&out.join(format!("frame-{index:02}-route-{route}-prepared.u16")),
                    capture.prepared.as_ref().context("prepared ROI absent")?,131072)?;
                let mut trace=b"NSTRC001".to_vec();
                trace.extend_from_slice(&u32::try_from(observed.fields.len()+capture.arrays.len()).expect("trace field count").to_le_bytes());
                for f in &observed.fields {field(&mut trace,f.tag,f.level,f.plane,&f.words);}
                for (tag,words) in &capture.arrays {field(&mut trace,*tag,0,u32::MAX,words);}
                trace_ref=write_new(&out.join(format!("frame-{index:02}-route-{route}.trace")), &trace,MAX_TRACE)?;
            }
            let row=json!({"schema":"native-sensor-transfer-frame-v1","invocation":invocation,"index":index,
                "original_ordinal":capture.original,"route":route,"observer":mode.name(),"source_metadata":metadata,
                "prepared_roi":prepared_ref,"trace":trace_ref,"inputs":capture.inputs,
                "variance_after_sha256":capture.after,"gather_site_records":capture.maps,
                "folded":true,"floor_array":"not-stored; threshold derived from exact operands",
                "feature":cfg!(feature="native-sensor-transfer")});
            rows.push(json_new(&out.join(format!("frame-{index:02}-route-{route}.json")),&row)?);
        }
        same_metadata(path,&before)?;
        let (_,_,per_chunk,_)=partition.unwrap();
        if (index+1)%per_chunk==0 || index+1==paths.len() {
            for route in 0..2 {
                match merged[route].as_mut() {
                    Some(acc)=>acc.absorb(&workers[route].merge),
                    None=>merged[route]=Some(std::mem::replace(&mut workers[route].merge,BandMerge::new(128,128,4,cfg))),
                }
                if index+1<paths.len(){workers[route].reset_chunk();}
            }
        }
    }
    ensure!(decoded==paths.len(),"native decoded population");
    drop(workers);
    let mut outputs=Vec::new();
    for route in 0..2 {
        let merge=merged[route].take().context("native route has no merged output")?;
        let planes=merge.finish(&mut Workspace::new(&sizes));
        ensure!(planes.len()==4 && planes.iter().all(|p|p.len()==16384),"native collapsed output shape");
        let mut raw=Vec::with_capacity(262144);
        for p in &planes {for v in p {ensure!(v.is_finite(),"nonfinite collapsed output");raw.extend_from_slice(&v.to_bits().to_le_bytes());}}
        let plane_ref=write_new(&out.join(format!("route-{route}-collapsed.f32")),&raw,262144)?;
        let tiff=out.join(format!("route-{route}-native.tiff"));
        let stage=out.join(format!("route-{route}-native.tiff.stage"));
        ensure!(!tiff.exists() && !stage.exists(),"native TIFF freshness");
        write_merged(Merged::Bands{domain,planes:&planes},levels.unwrap(),output_wb,
            output_matrix.as_ref(),image_out::OutputSpace::CameraLinear,true,Exposure::None,None,&stage)?;
        let extent=fs::metadata(&stage)?.len();
        ensure!(extent>0 && extent<=512*1024,"native TIFF capacity");
        let mut actual=Vec::with_capacity(extent as usize);
        File::open(&stage)?.take(extent+1).read_to_end(&mut actual)?;
        ensure!(actual.len()==extent as usize,"native TIFF publication changed");
        OpenOptions::new().read(true).write(true).open(&stage)?.sync_all()?;
        fs::hard_link(&stage,&tiff)?; fs::remove_file(&stage)?;
        let tiff_ref=json!({"path":tiff,"bytes":actual.len(),"sha256":hash(&actual)});
        outputs.push(json!({"collapsed":plane_ref,"tiff":tiff_ref,"dimensions":[256,256],
            "writer":"write_merged/Merged::Bands","space":"CameraLinear","demosaic":true,
            "exposure":"None","restore":null,"wb_gain_bits":output_wb.map(|g|g.map(f32::to_bits)),
            "levels_bits":[levels.unwrap().black.to_bits(),levels.unwrap().white.to_bits()]}));
    }
    Ok(json!({"schema":"native-sensor-transfer-traversal-v1","status":"COMPLETE_NATIVE_CROP_TRAVERSAL",
        "invocation":invocation,"observer":mode.name(),"feature":cfg!(feature="native-sensor-transfer"),
        "native_decodes":decoded,"source_handoffs":2*decoded,"folds":2*decoded,
        "expected_real_fullres_warps":decoded,"expected_synthetic_probe_warps":decoded,
        "map_callback_visits":if mode==Observe::On||mode==Observe::Placebo{8*decoded}else{0},
        "shape":[128,128],"crop":[1694,1108,128,128],"configured_bands":7,"actual_sides":SIDES,
        "config":format!("{cfg:?}"),"partition":partition,"environment":env,"frames":rows,"outputs":outputs,
        "scope":"conditional native Crop; no physical calibration or photographic quality admission"}))
}
#[test]
#[ignore = "requires separately frozen native sensor transfer source/input/resource release"]
fn fixed_native_sensor_transfer_pair() {
    let invocation=std::env::var("NATIVE_SENSOR_TRANSFER_INVOCATION").expect("released invocation required")
        .parse::<usize>().expect("integer invocation required");
    assert!(invocation<9);
    let root=Path::new(env!("CARGO_MANIFEST_DIR")).join("../../experiments/native-sensor-transfer");
    let out=root.join(format!("native-run-{invocation}"));
    fs::create_dir(&out).expect("fresh native output directory required");
    json_new(&out.join("incomplete.json"),&json!({"schema":"native-sensor-transfer-traversal-v1",
        "status":"INITIAL_INCOMPLETE","invocation":invocation})).expect("initial receipt");
    match run_pair(invocation,&out) {
        Ok(value)=>{json_new(&out.join("result.json"),&value).expect("native terminal publication");}
        Err(error)=>{
            let text=format!("{error:#}"); let bounded:String=text.chars().take(2048).collect();
            let receipt=json!({"schema":"native-sensor-transfer-traversal-v1","status":"REFUSED",
                "invocation":invocation,"error":bounded,"error_truncated":text.chars().count()>2048});
            let _=json_new(&out.join("failure.json"),&receipt);
            panic!("native traversal refused: {error:#}");
        }
    }
}
