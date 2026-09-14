// Bounded saved-CFA diagnostic: actual gather, probe, BandWorker and writer.
// 196-plane-pixel analysis has FOUR Laplacian bands, not the full render's seven.
use super::*;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::io::Write;
use strehl_core::align::{Cx, Similarity};
use strehl_core::demosaic::{Mosaic, demosaic_row};
use strehl_core::optics::{OpticalProfile, cfa_site_channel};

const FIRST: usize = 146;
const LAST: usize = 153;
const SIDE: usize = 392;
const MAP_HASH: &str = "ce8534c9e65c5c761373bad87df5352c1c46319b7eaf7f7c91477ea61b4f4922";

fn sha(bytes: &[u8]) -> String { Sha256::digest(bytes).iter().map(|v|format!("{v:02x}")).collect() }
fn read_json(path: &Path) -> Result<Value> { Ok(serde_json::from_slice(&std::fs::read(path)?)?) }
fn text<'a>(v: &'a Value, key: &str) -> Result<&'a str> { v[key].as_str().with_context(||format!("missing {key}")) }
fn numbers<const N: usize>(v: &Value) -> Result<[f64;N]> {
    let a=v.as_array().context("numeric array")?; ensure!(a.len()==N,"array extent");
    let mut out=[0.0;N];
    for (o,n) in out.iter_mut().zip(a) { *o=n.as_f64().context("number")?; ensure!(o.is_finite(),"nonfinite input"); }
    Ok(out)
}
fn integer(v: &Value) -> Result<usize> { Ok(v.as_u64().context("unsigned integer")?.try_into()?) }
fn bits3(v: &Value) -> Result<[f32;3]> {
    let a=v.as_array().context("bits")?; ensure!(a.len()==3,"bits extent");
    Ok([f32::from_bits(integer(&a[0])?.try_into()?),f32::from_bits(integer(&a[1])?.try_into()?),f32::from_bits(integer(&a[2])?.try_into()?)])
}
fn root() -> PathBuf { PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap().to_path_buf() }
fn full() -> PlaneGeometry { PlaneGeometry {width:3516,height:2344} }
fn domain() -> Result<PyramidDomain> { PyramidDomain::cropped(full(),align_cmd::CropRect{x:666,y:552,width:196,height:196}) }
fn config() -> Result<(PathBuf,PathBuf,Value)> {
    let path=PathBuf::from(std::env::var_os("STREHL_LOCAL_PLACEMENT_CONFIG").context("explicit configuration required")?);
    let cfg=read_json(&path)?;
    let input=PathBuf::from(text(&cfg,"input_dir")?).canonicalize()?;
    let out=PathBuf::from(text(&cfg,"out")?);
    ensure!(input.starts_with(root().canonicalize()?) && out.parent().context("output parent")?.canonicalize()?.starts_with(root().canonicalize()?),"repository-only diagnostic paths");
    let manifest=read_json(&input.join("manifest.json"))?;
    Ok((input,out,manifest))
}

// Conservative complete support: each Catmull tap [-1,+2] reads a radius-two
// MHC stencil. Include a 1e-7-native coordinate interval for host/device f64
// last-bit differences; this may refuse a marginal patch, never invent support.
fn support(pull: Similarity, retained: [usize;4]) -> Result<[i64;4]> {
    let mut bounds=[i64::MAX,i64::MAX,i64::MIN,i64::MIN];
    let [rx,ry,rw,rh]=retained;
    for y in 1104..1104+SIDE { for x in 1332..1332+SIDE {
        let (sx,sy)=pull.apply_at(x as f64*0.5,y as f64*0.5,1758.0,1172.0);
        let (sx,sy)=(2.0*sx,2.0*sy);
        ensure!(sx.is_finite()&&sy.is_finite(),"nonfinite pull");
        let lo_x=(sx-1e-7).floor() as i64-3; let hi_x=(sx+1e-7).floor() as i64+4;
        let lo_y=(sy-1e-7).floor() as i64-3; let hi_y=(sy+1e-7).floor() as i64+4;
        ensure!(lo_x>=rx as i64 && lo_y>=ry as i64 && hi_x<(rx+rw) as i64 && hi_y<(ry+rh) as i64,
            "unsupported original CFA stencil: dst({x},{y}) source({sx},{sy}) needs [{lo_x},{lo_y}..{hi_x},{hi_y}], retained {retained:?}");
        bounds[0]=bounds[0].min(lo_x); bounds[1]=bounds[1].min(lo_y);
        bounds[2]=bounds[2].max(hi_x); bounds[3]=bounds[3].max(hi_y);
    }}
    Ok(bounds)
}
fn retained(f: &Value) -> Result<[usize;4]> {
    let a=f["source_xywh"].as_array().context("source bounds")?;ensure!(a.len()==4,"source bounds extent");
    Ok([integer(&a[0])?,integer(&a[1])?,integer(&a[2])?,integer(&a[3])?])
}
fn environment() -> Result<()> {
    ensure!(align_cmd::fullres_gather_enabled(),"full-resolution gather required");
    ensure!(align_cmd::direct_plane_mode()?==align_cmd::DirectPlaneMode::Rounded,"rounded direct planes required");
    ensure!(gatefloor::enabled(),"current measured noise probe required");
    ensure!(std::env::var("STREHL_PROBE_GATHER").unwrap_or_else(|_|"green".into())=="green","green noise probe required");
    for name in ["STREHL_FIX_CA","STREHL_DEMOSAIC","STREHL_GATE_FLOOR_SCALE","STREHL_PYRAMID_MEAN_COARSE",
        "STREHL_PYRAMID_SIGNIFICANCE","STREHL_PYRAMID_WEIGHT_DUMP","STREHL_RESTORE"] {
        ensure!(std::env::var_os(name).is_none(),"unexpected override {name}");
    }
    Ok(())
}
fn prepare(input: &Path, m: &Value) -> Result<(WarpMap,WarpMap,Vec<Value>)> {
    environment()?;
    ensure!(numbers::<2>(&m["target_shape"])?==[392.0,392.0] && numbers::<2>(&m["target_origin_native"])?==[1332.0,1104.0]
        && numbers::<2>(&m["native_sensor_shape"])?==[4688.0,7032.0],"fixed crop/native geometry");
    ensure!(integer(&m["reference_index"])?==149 && numbers::<2>(&m["levels"])?==[512.0,15360.0],"fixed reference/levels");
    ensure!(text(m,"camera")?=="ILCE-7CM2" && m["iso"].as_f64()==Some(100.0),"observed capture metadata");
    ensure!(bits3(&m["wb_bits"])?==[1637.0/1024.0,1.0,2774.0/1024.0],"observed WB");
    let sizes=level_sizes(196,196,7);
    ensure!(sizes.iter().map(|s|(s.width,s.height)).collect::<Vec<_>>()==vec![(196,196),(98,98),(49,49),(25,25),(13,13)],"must be four actual Laplacian bands");
    let path=root().join("experiments/quality-september14/chip-baseline-1/chip.warpmap.txt");
    ensure!(sha(&std::fs::read(&path)?)==MAP_HASH && text(m,"map_sha256")?==MAP_HASH,"original map binding");
    let original=WarpMap::load(&path)?;
    ensure!(original.geometry()==full()&&original.len()==299&&original.provenance().reference==149&&original.resampler()==Resampler::CatmullRom,"original map gauge");
    let fit_path=root().join("experiments/quality-september14/local-green-translation-1/result.json");
    ensure!(sha(&std::fs::read(&fit_path)?)==text(m,"local_alignment_sha256")?,"frozen local fit binding");
    let fits=read_json(&fit_path)?;
    let frames=m["frames"].as_array().context("frames")?;ensure!(frames.len()==8,"exactly eight frames");
    let mut warps=original.warps().to_vec();let mut report=Vec::new();
    for (slot,f) in frames.iter().enumerate() {
        let index=integer(&f["index"])?;ensure!(index==FIRST+slot&&index<=LAST,"prescribed frame order");
        let r=retained(f)?;ensure!(r[0]%2==0&&r[1]%2==0&&r[0]+r[2]<=7032&&r[1]+r[3]<=4688,"original RGGB crop");
        let name=format!("frame-{index}.u16");ensure!(text(f,"file")?==name,"prescribed sample filename");
        let raw=std::fs::read(input.join(name))?;
        ensure!(raw.len()==r[2]*r[3]*2&&sha(&raw)==text(f,"raw_u16_sha256")?,"saved original sample binding");
        let old=original.placement(index)?;
        ensure!(numbers::<2>(&f["a"])?==[old.a.re,old.a.im]&&numbers::<2>(&f["b_plane"])?==[old.b.re,old.b.im],"manifest changed original transform");
        let fit=fits["frames"].as_array().context("fitted frames")?.iter().find(|v|v["frame"].as_u64()==Some(index as u64)).context("missing independent fit")?;
        let delta=numbers::<2>(&f["delta_source_native"])?;
        ensure!(delta==numbers::<2>(&fit["delta_source_native"])?&&delta.iter().all(|d|d.abs()<4.0),"fixed interior correction; bounded frame145 excluded");
        ensure!(fit["converged"]==true && fit["at_translation_bound"]==false,"fit did not converge inside bounds");
        if index==149 { ensure!(delta==[0.0,0.0],"reference correction must be zero"); }
        let new=if index==149 {old} else {Similarity{a:old.a,b:Cx::new(old.b.re+delta[0]*0.5,old.b.im+delta[1]*0.5)}};
        if index==149 {
            ensure!([old.a.re,old.a.im,old.b.re,old.b.im].map(f64::to_bits)==[new.a.re,new.a.im,new.b.re,new.b.im].map(f64::to_bits),"reference transform bits changed");
        }
        warps[index]=FrameWarp::Placed(new);
        let source=PathBuf::from(text(f,"source")?);
        let expected_source=format!("DSC{:05}.ARW",index+1);
        ensure!(source.file_name().and_then(|v|v.to_str())==Some(expected_source.as_str()),"source/frame mapping");
        let id=strehl_raw::identity(&source); // Header/gear identity only; never decode RAW.
        let ca=strehl_core::optics::profile_for_capture_env(id.model.as_deref(),id.lens_type3)?.context("current gear-matched CA required")?;
        let mut checks=Vec::new();
        for (arm,t) in [("original",old),("corrected",new)] { for site in [(0,0),(1,0),(1,1)] {
            let pull=OpticalProfile::compose(Some(ca),cfa_site_channel(site.0,site.1),t);
            checks.push(json!({"arm":arm,"site":site,"inclusive_source_bounds":support(pull,r)?}));
        }}
        report.push(json!({"frame":index,"source":source,"retained":r,"delta_source_native":delta,
            "identity_model":id.model,"identity_lens_type3":id.lens_type3,"ca":format!("{ca:?}"),"stencils":checks}));
    }
    // Power to refuse: a crop incapable of holding even identity gather support.
    ensure!(support(Similarity::IDENTITY,[1332,1104,392,392]).is_err(),"unsupported-stencil negative control did not fail");
    ensure!(support(Similarity{a:Cx::new(1.0,0.0),b:Cx::new(16.0,0.0)},[1322,1096,410,412]).is_err(),"32-native translation must leave retained source");
    let corrected=WarpMap::new(original.provenance().clone(),full(),original.resampler(),warps);
    Ok((original,corrected,report))
}

struct Source<'a> { input: &'a Path, manifest: &'a Value, filler:u16 }
impl PyramidFrameSource for Source<'_> {
    fn len(&self) -> usize {299} // Preserve original IDs, including the probe's seed.
    fn decode(&self,index:usize) -> Result<Frame> {
        ensure!((FIRST..=LAST).contains(&index),"attempted unsupplied frame");
        let f=&self.manifest["frames"][index-FIRST];let [x,y,w,h]=retained(f)?;
        let bytes=std::fs::read(self.input.join(text(f,"file")?))?;
        ensure!(bytes.len()==w*h*2&&sha(&bytes)==text(f,"raw_u16_sha256")?,"saved samples changed after preflight");
        let mut data=vec![self.filler;7032*4688];
        for (row,values) in bytes.chunks_exact(w*2).enumerate() { for (col,p) in values.chunks_exact(2).enumerate() {
            data[(y+row)*7032+x+col]=u16::from_le_bytes([p[0],p[1]]);
        }}
        let wb=bits3(&self.manifest["wb_bits"])?;
        Ok(Frame{data,stride:7032,buffer_height:4688,active:strehl_raw::Region{x:0,y:0,width:7032,height:4688},
            levels:Levels{black:512.0,white:15360.0},iso:Some(100.0),wb_coeffs:[wb[0],wb[1],wb[2],f32::NAN],
            xyz_to_cam_rgbe:[[0.0;3];4],color_matrices:Vec::new(),camera:text(self.manifest,"camera")?.into(),path:PathBuf::from(text(f,"source")?)})
    }
}
fn f32_bytes(values: impl IntoIterator<Item=f32>) -> Vec<u8> { values.into_iter().flat_map(|v|v.to_bits().to_le_bytes()).collect() }
fn create(path:&Path,bytes:&[u8])->Result<()> {
    let mut f=std::fs::OpenOptions::new().write(true).create_new(true).open(path)?;f.write_all(bytes)?;Ok(())
}
fn outputs(out:&Path,arm:&str,planes:&[Vec<f32>],m:&Value)->Result<Value> {
    let d=domain()?;let levels=Levels{black:512.0,white:15360.0};let wb=bits3(&m["wb_bits"])?;
    let collapsed=f32_bytes(planes.iter().flat_map(|p|p.iter().copied()));
    create(&out.join(format!("{arm}-collapsed-planes.f32")),&collapsed)?;
    let linear_path=out.join(format!("{arm}-camera-linear.tiff"));
    write_merged(Merged::Bands{domain:d,planes},levels,Some(wb),None,image_out::OutputSpace::CameraLinear,true,Exposure::None,None,&linear_path)?;
    let mut cfa=Vec::with_capacity(SIDE*SIDE);
    for y in 0..SIDE { for x in 0..SIDE {
        let slot=(y%2)*2+x%2;let gain=wb[if slot==0 {0}else if slot==3 {2}else{1}];
        // Exact no-restoration write_merged interleave and normalization order.
        cfa.push(planes[slot][(y/2)*196+x/2].max(0.0)*gain*1.0/levels.range());
    }}
    create(&out.join(format!("{arm}-cfa.f32")),&f32_bytes(cfa.iter().copied()))?;
    let mosaic=Mosaic{data:&cfa,width:SIDE,height:SIDE};let mut rgb=vec![0.0;SIDE*SIDE*3];
    for y in 0..SIDE {demosaic_row(&mosaic,y,&mut rgb[y*SIDE*3..(y+1)*SIDE*3]);}
    create(&out.join(format!("{arm}-mhc-camera-rgb.f32")),&f32_bytes(rgb.iter().copied()))?;
    // Check copied interleave against the real writer, before any viewing arm.
    let check_path=out.join(format!("{arm}-interleave-control.tiff"));
    image_out::write_demosaiced(&check_path,SIDE,SIDE,&cfa,&image_out::OutputSpace::CameraLinear.develop(None))?;
    ensure!(std::fs::read(&linear_path)?==std::fs::read(&check_path)?,"manual interleave differs from actual write_merged");
    let xyz=m["xyz_to_cam"].as_array().context("matrix")?;ensure!(xyz.len()==3,"matrix rows");
    let mat=[numbers::<3>(&xyz[0])?.map(|v|v as f32),numbers::<3>(&xyz[1])?.map(|v|v as f32),numbers::<3>(&xyz[2])?.map(|v|v as f32)];
    let matrix=color::camera_to_srgb(mat).context("camera matrix inverse")?.with_saturation(levels,wb,1.0);
    let tone=bits3(&m["tone_bits"])?;
    let mut dev=image_out::OutputSpace::Srgb.develop(Some(matrix));
    dev.tone=Some(image_out::Tone{black:tone[0],white:tone[1],contrast:tone[2]});dev.exposure_gain=1.0;
    let product=out.join(format!("{arm}-product.tiff"));image_out::write_demosaiced(&product,SIDE,SIDE,&cfa,&dev)?;
    Ok(json!({"arm":arm,"collapsed_sha256":sha(&collapsed),"linear_tiff_sha256":sha(&std::fs::read(linear_path)?),
        "product_tiff_sha256":sha(&std::fs::read(product)?),"interleave_actual_writer_exact":true}))
}

#[test]
#[ignore="root-owned saved-CFA configuration and current CA preflight; no RAW decode"]
fn local_placement_configuration_preflight() {
    let (input,_,m)=config().unwrap();let (_,_,report)=prepare(&input,&m).unwrap();
    println!("LOCAL_PLACEMENT_PREFLIGHT {}",json!({"status":"PASS","actual_laplacian_bands":4,"frames":report}));
}

#[test]
#[ignore="root-owned actual saved-CFA consumer; full-geometry gather, no RAW decode"]
fn local_placement_actual_consumer() { run().unwrap(); }
fn run()->Result<()> {
    let (input,out,m)=config()?;let (original,corrected,support_report)=prepare(&input,&m)?;
    std::fs::create_dir(&out)?;
    let cfg=MergeConfig::default();
    ensure!(cfg.bands==7&&cfg.gate==2.0&&cfg.exponent==2.0&&cfg.sharpen_per_octave==1.4&&cfg.mean_coarse==0
        &&cfg.significance_scale==0.0&&cfg.admission==strehl_core::pyramid::AdmissionMode::HardFloor
        &&cfg.select==strehl_core::pyramid::SelectMode::SoftPower
        &&cfg.base==strehl_core::pyramid::BaseBand::Mean,"fixed current merge options");
    let levels=Levels{black:512.0,white:15360.0};
    let noise=profile::noise_model_for(text(&m,"camera")?,Some(100.0),levels);
    ensure!(noise.provenance==strehl_core::noise::Provenance::Profile&&noise.prnu().is_none(),"injected shipping profile");
    for p in [CfaPlane::R,CfaPlane::G1,CfaPlane::G2,CfaPlane::B] {
        let n=noise.plane(p);ensure!(n.gain_dn_per_e.to_bits()==(m["noise"]["gain_dn_per_e"].as_f64().context("profile gain")? as f32).to_bits()
            &&n.read_noise_e.to_bits()==(m["noise"]["read_noise_e"].as_f64().context("profile read noise")? as f32).to_bits(),"profile differs from supplied variance source");
    }
    let mut records=Vec::new();let mut changed=0;
    let mut original_collapsed=None;
    for (name,map) in [("original",&original),("corrected",&corrected)] {
        let mut first:Option<(Vec<u8>,Value)>=None;
        for (filler_name,filler) in [("black",512u16),("white",15360u16)] {
            let source=Source{input:&input,manifest:&m,filler};let mut worker=BandWorker::new(domain()?,cfg);
            let mut beta=Vec::new();
            for index in FIRST..=LAST {
                ensure!(worker.fold(&source,index,levels,&noise,Some(map),None)?,"frame refused");
                beta.push(json!({"frame":index,"finite_consumed_beta":worker.beta}));
            }
            let planes=worker.merge.finish(&mut Workspace::new(&level_sizes(196,196,cfg.bands)));
            ensure!(planes.len()==4&&planes.iter().all(|p|p.len()==196*196&&p.iter().all(|v|v.is_finite())),"collapsed extent/finite");
            let bytes=f32_bytes(planes.iter().flat_map(|p|p.iter().copied()));
            let record=outputs(&out,&format!("{name}-{filler_name}"),&planes,&m)?;
            if let Some((old,prior))=&first {
                ensure!(*old==bytes,"unsupported source filler changed collapsed {name}");
                ensure!(prior["product_tiff_sha256"]==record["product_tiff_sha256"]&&prior["linear_tiff_sha256"]==record["linear_tiff_sha256"],"filler changed written output {name}");
            } else {
                if name=="original" {original_collapsed=Some(bytes.clone());} else {
                    changed=original_collapsed.as_ref().context("original arm")?.chunks_exact(4).zip(bytes.chunks_exact(4)).filter(|(a,b)|a!=b).count();
                }
                first=Some((bytes,record.clone()));
            }
            records.push(json!({"output":record,"probe":beta}));
        }
    }
    ensure!(changed>0,"correction did not reach the actual consumer");
    let receipt=json!({"status":"LOCAL_CROPPED_CONSUMER_COMPLETE","input_manifest_sha256":sha(&std::fs::read(input.join("manifest.json"))?),
        "source_decode":"saved original u16 only; RAW paths queried for existing CA gear identity, never decoded",
        "frames":[146,147,148,149,150,151,152,153],"reference":149,"full_quad_geometry":[3516,2344],
        "crop_quad_xywh":[666,552,196,196],"native_extent":[392,392],"viewing_trim":32,
        "requested_bands":7,"actual_laplacian_bands":4,"level_sides":[196,98,49,25,13],
        "scope":"Same cropped actual consumer in both arms; four bands with replicated crop boundaries. No seven-band/full-stack/within-DOF claim. No fitted photometric terms. Original global IDs retained for probe seeds.",
        "filler_values_dn":[512,15360],"filler_collapsed_and_output_exact":true,"changed_collapsed_f32_words":changed,
        "support":support_report,"outputs":records,"wb_bits":m["wb_bits"],"tone_bits":m["tone_bits"],"levels":m["levels"]});
    create(&out.join("receipt.json"),&serde_json::to_vec_pretty(&receipt)?)?;
    Ok(())
}
