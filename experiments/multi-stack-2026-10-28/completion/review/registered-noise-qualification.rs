//! Source-only qualification for real temporal comparisons, before output noise.
//! Streaming one original through bounded existing native-CFA gathers; no volume.
use anyhow::{Context, Result, ensure};
use serde_json::{Value,json};
use sha2::{Digest,Sha256};
use std::{fs,io::Write,path::Path};
use strehl_cli::{session_cache::SourceCache,session_input::{ResolvedSession,SourceIdentity},
    session_sampling::SamplingDomain,session_reconstruction_sampling::RegionSampler};
use strehl_core::{boxfilter::box_mean,plane::QuadSource,warpmap::WarpMap,
    optics::profile_for_capture_env,noise::{NoiseModel,PlaneNoise,Levels,Provenance},CfaPlane};

const SIDE:usize=128;
// Narrow-focus follow-up after the archived20-step scope refused all36 tiles.
// Guides/validation bracket both withheld measurements; no output-noise value
// was consulted. Only two temporal replicates are available in this scope.
const GUIDES:[usize;5]=[26,28,30,32,34];
const VALIDATE:[usize;2]=[27,33];
const MEASURE:[usize;2]=[29,31];
const TILES:[(usize,usize);9]=[(16,16),(48,16),(80,16),(16,48),(48,48),(80,48),(16,80),(48,80),(80,80)];
type Planes=[Vec<f32>;4];
fn zero()->Planes {std::array::from_fn(|_|vec![0.;SIDE*SIDE])}
fn sha(bytes:&[u8])->String {Sha256::digest(bytes).iter().map(|v|format!("{v:02x}")).collect()}
fn read(path:&Path)->Result<Value>{Ok(serde_json::from_slice(&fs::read(path)?)?)}
fn write(path:&Path,value:&Value)->Result<()> {
    let mut file=fs::OpenOptions::new().create_new(true).write(true).open(path)?;
    serde_json::to_writer_pretty(&mut file,value)?;file.write_all(b"\n")?;file.sync_all()?;Ok(())
}
fn quantile(mut values:Vec<f32>,q:f32)->f32 {
    values.sort_by(f32::total_cmp);values[((values.len()-1) as f32*q) as usize]
}
fn smooth(values:&Planes)->Planes {
    let mut out=zero();let mut scratch=vec![0.;SIDE*SIDE];
    for c in 0..4 {box_mean(&values[c],strehl_core::plane::PlaneGeometry{width:SIDE,height:SIDE},2,&mut scratch,&mut out[c]);}
    out
}
struct Qualification {
    sum:Planes, min:Planes,max:Planes,
    validation_min:Planes,validation_max:Planes,
    means:Vec<[[f32;4];9]>,valid:Vec<bool>,guides:usize,validations:usize,
}
impl Qualification {
    fn new()->Self {Self{sum:zero(),min:std::array::from_fn(|_|vec![f32::INFINITY;SIDE*SIDE]),
        max:std::array::from_fn(|_|vec![f32::NEG_INFINITY;SIDE*SIDE]),
        validation_min:std::array::from_fn(|_|vec![f32::INFINITY;SIDE*SIDE]),
        validation_max:std::array::from_fn(|_|vec![f32::NEG_INFINITY;SIDE*SIDE]),
        means:Vec::new(),valid:vec![true;SIDE*SIDE],guides:0,validations:0}}
    fn observe(&mut self,source:&Planes,support:&[bool],validation:bool) {
        let image=smooth(source);let mut means=[[0.;4];9];
        for c in 0..4 {for i in 0..SIDE*SIDE {
            if validation {self.validation_min[c][i]=self.validation_min[c][i].min(image[c][i]);
                self.validation_max[c][i]=self.validation_max[c][i].max(image[c][i]);}
            else {self.sum[c][i]+=image[c][i];self.min[c][i]=self.min[c][i].min(image[c][i]);self.max[c][i]=self.max[c][i].max(image[c][i]);}
        }}
        for (tile,&(x,y)) in TILES.iter().enumerate(){for c in 0..4 {
            let mut total=0.;for yy in y..y+32{for xx in x..x+32{total+=image[c][yy*SIDE+xx];}}
            means[tile][c]=total/1024.;
        }}
        for y in 2..SIDE-2 {for x in 2..SIDE-2 {
            self.valid[y*SIDE+x]&=(y-2..=y+2).all(|yy|(x-2..=x+2).all(|xx|support[yy*SIDE+xx]));
        }}
        self.means.push(means);if validation{self.validations+=1;}else{self.guides+=1;}
    }
    fn result(&self,noise:&NoiseModel,beta:f32)->Result<Vec<Value>> {
        ensure!(self.guides==GUIDES.len()&&self.validations==VALIDATE.len(),"qualification frame census differs");
        ensure!(beta.is_finite()&&beta>0.,"invalid source sampling noise transfer");
        let mut rows=Vec::new();
        for (tile,&(x,y)) in TILES.iter().enumerate() {
            let indices:Vec<_>=(y..y+32).flat_map(|yy|(x..x+32).map(move|xx|yy*SIDE+xx)).collect();
            let support=indices.iter().all(|&i|self.valid[i]);let mut accepted=support;let mut colors=Vec::new();
            for c in 0..4 {
                let mean:Vec<_>=indices.iter().map(|&i|self.sum[c][i]/self.guides as f32).collect();
                let sigma:Vec<_>=mean.iter().map(|&v|(noise.variance(CfaPlane::ALL[c],v)*beta).sqrt()).collect();
                let range=quantile(indices.iter().zip(&sigma).map(|(&i,&s)|(self.max[c][i]-self.min[c][i])/s).collect(),0.95);
                let validation=quantile(indices.iter().zip(&mean).zip(&sigma).map(|((&i,&m),&s)|
                    (self.validation_max[c][i]-m).abs().max((self.validation_min[c][i]-m).abs())/s).collect(),0.95);
                let mean_dn=mean.iter().sum::<f32>()/1024.;let mean_sigma=sigma.iter().sum::<f32>()/1024.;
                let min_mean=self.means.iter().map(|m|m[tile][c]).fold(f32::INFINITY,f32::min);
                let max_mean=self.means.iter().map(|m|m[tile][c]).fold(f32::NEG_INFINITY,f32::max);
                let drift=(max_mean-min_mean)/mean_sigma;
                let gradient=quantile(indices.iter().zip(&sigma).map(|(&i,&s)|{
                    let value=self.sum[c][i]/self.guides as f32;
                    let dx=(self.sum[c][i+1]/self.guides as f32-value).abs();
                    let dy=(self.sum[c][i+SIDE]/self.guides as f32-value).abs();dx.max(dy)/s
                }).collect(),0.95);
                // Two independent validation frames versus a five-frame mean:
                // a 5x5 box gives ~sqrt(1+1/5)/5 = .219 raw-sigma noise.
                // The 95th percentile of max(|Z1|,|Z2|) is about2.49 sigma;
                // .65 leaves finite spatial-sample margin over the .546 null.
                let allowed=mean_dn>64.&&range<=1.0&&validation<=0.65&&drift<=0.25&&gradient<=0.5;
                accepted&=allowed;
                colors.push(json!({"mean_dn":mean_dn,"mean_sample_sigma":mean_sigma,
                    "guide_range_p95_sigma":range,"validation_p95_sigma":validation,"mean_drift_sigma":drift,
                    "guide_gradient_p95_sigma":gradient,"accepted":allowed}));
            }
            rows.push(json!({"tile":tile,"origin_quad_local":[x,y],"size_quad":32,
                "complete_support":support,"colors":colors,"accepted":accepted}));
        }
        Ok(rows)
    }
}

fn random(state:&mut u64)->f32 {*state^=*state<<13;*state^=*state>>7;*state^=*state<<17;
    (((*state>>40)as u32)as f32+0.5)/16777216.}
fn gaussian(state:&mut u64)->f32 {(-2.*random(state).ln()).sqrt()*(std::f32::consts::TAU*random(state)).cos()}
fn model()->NoiseModel {NoiseModel::new([PlaneNoise{gain_dn_per_e:0.229,read_noise_e:4.2,
    levels:Levels{black:512.,white:15360.}};4],100.,Provenance::Profile)}
fn commission()->Result<Value> {
    // Actual qualification code: flat first, then fixed drift and translated
    // two-dimensional structure. A static field need not be perfectly uniform.
    let noise=model();let mut reports=Vec::new();
    for mode in ["flat","drift","translated-texture","defocus"] {
        let mut counts=Vec::new();
        for seed in 0..8 {
            let mut q=Qualification::new();let mut state=1+20261028+seed*53139;
            for frame in 0..7 {
                let validation=frame>=5;
                let temporal=if validation {if frame==5 {1.}else{-1.}}else{(frame as f32-2.)/2.};
                let values=std::array::from_fn(|_|(0..SIDE*SIDE).map(|i|{
                    let x=(i%SIDE)as f32;let y=(i/SIDE)as f32;
                    let signal=match mode {
                        "drift"=>1200.+temporal*30.,
                        "translated-texture"=>1200.+100.*((x+temporal)*0.5).sin()+80.*((y-temporal)*0.3).cos(),
                        "defocus"=>1200.+(1.-0.5*temporal.abs())*(100.*(x*0.5).sin()+80.*(y*0.3).cos()),
                        _=>1200.,};
                    signal+gaussian(&mut state)*noise.variance(CfaPlane::R,signal).sqrt()
                }).collect::<Vec<_>>());
                q.observe(&values,&vec![true;SIDE*SIDE],validation);
            }
            let rows=q.result(&noise,1.)?;
            if mode=="flat" && seed==0 {println!("flat-first actual gate rows: {}",json!(rows));}
            counts.push(rows.iter().filter(|r|r["accepted"]==true).count());
        }
        let total:usize=counts.iter().sum();
        ensure!(if mode=="flat" {total>=64}else{total==0},"qualification commissioning failed: {mode} {counts:?}");
        reports.push(json!({"mode":mode,"accepted_by_seed":counts,"total_tiles":72}));
    }
    Ok(json!({"flat_first":true,"actual_qualification_function":true,"cases":reports,
        "scope":"Known stationary signal and injected noise commissioning, not real camera noise validation."}))
}
fn main()->Result<()> {
    let args:Vec<_>=std::env::args().collect();ensure!(matches!(args.len(),5|6),"RENDER CACHE WITNESSES_JSON OUT [WINDOW_BASE]");
    // Six predeclared, disjoint measurement pairs. All measurement ordinals
    // are3 modulo4; guide/validation photons are globally excluded from them.
    let base=args.get(5).map(|s|s.parse::<usize>()).transpose()?;
    ensure!(base.is_none_or(|v|[12,20,28,36,44,52].contains(&v)),"unknown focus-window census arm");
    let guides=base.map(|v|[v,v+2,v+4,v+6,v+8]).unwrap_or(GUIDES);
    let validation=base.map(|v|[v+1,v+5]).unwrap_or(VALIDATE);
    let measurement=base.map(|v|[v+3,v+7]).unwrap_or(MEASURE);
    let render=Path::new(&args[1]);let output=Path::new(&args[4]);fs::create_dir(output)?;
    let pool=rayon::ThreadPoolBuilder::new().num_threads(4).build()?;
    write(&output.join("qualification-controls.json"),&commission()?)?;
    let session:ResolvedSession=serde_json::from_value(read(&render.join("session.json"))?)?;
    let ids:Vec<SourceIdentity>=serde_json::from_value(read(&render.join("source-identities.json"))?)?;
    let metadata=session.read_metadata()?;let alignment=read(&render.join("alignment.json"))?;
    ensure!(alignment["binding"]["sources"]==serde_json::to_value(&ids)?&&alignment["binding"]["session"]==serde_json::to_value(&session.spec)?,"source or session binding differs");
    let map=WarpMap::from_text(alignment["warpmap"].as_str().context("warpmap")?)?;
    let report=read(&render.join("render-report.json"))?;let calibration=read(&render.join("calibration.json"))?;
    let witnesses=read(Path::new(&args[3]))?;let canvas=report["canvas"].as_array().context("canvas")?;
    let names=["gray-ramp-middle","qr-white-black-grid","low-contrast-dot-field","adverse-flare-p12"];
    let mut rois=Vec::new();
    for name in names {
        let row=witnesses["rois"].as_array().context("witnesses")?.iter().find(|v|v["name"]==name).context("witness missing")?;
        let xy=&row["origins"]["shared-hdr-gauge"];
        let x=canvas[0].as_u64().unwrap() as usize+xy[0].as_u64().unwrap() as usize/2+32;
        let y=canvas[1].as_u64().unwrap() as usize+xy[1].as_u64().unwrap() as usize/2+32;
        rois.push((name,SamplingDomain{full:map.geometry(),x,y,width:SIDE,height:SIDE}));
    }
    let protocol=json!({"schema":"strehl.registered-noise-source-qualification.v1","command":args,
        "source_sha256":sha(include_bytes!("registered-noise-qualification.rs")),"guides_short":guides,
        "validation_short":validation,"measurement_short_not_loaded":measurement,"long_global_offset":62,
        "window_base":base,"component_policy":"Retain each CFA component eligibility separately. An all-RGB refusal must not be relabeled an all-RGB noise measurement.",
        "rois":rois.iter().map(|(name,d)|json!({"name":name,"domain_quad":[d.x,d.y,d.width,d.height]})).collect::<Vec<_>>(),
        "subtiles":TILES,"spatial_filter":"5x5 box, applied separately to each CFA plane",
        "range_p95_max_sigma":1.0,"validation_p95_max_sigma":0.65,"mean_drift_max_sigma":0.25,
        "gradient_p95_max_sigma":0.5,"mean_min_dn":64.,"cross_pass_mean_gap_max_combined_sigma":0.5,
        "noise_scale":"Injected original-sample camera model. Finest-band beta is recorded separately and is not a local variance estimate for the spatially smoothed qualification guide.",
        "workers":4,"memory_limit_bytes":2usize<<30,"alignment_sha256":sha(&fs::read(render.join("alignment.json"))?),
        "witness_sha256":sha(&fs::read(&args[3])?),"qualification_before_measurement":true,
        "scope":"Registered local temporal constancy qualification. No measurement originals, output variance or photographic gain in this stage."});
    write(&output.join("protocol-frozen.json"),&protocol)?;
    let mut cache=SourceCache::new(Path::new(&args[2]),&session,128<<20)?;
    let mut results=Vec::new();let mut receipts=Vec::new();
    pool.install(||->Result<()> {
        for (name,domain) in &rois {
            let mut passes=Vec::new();let mut gains=[1.;2];
            for pass in 0..2 {
                let selected:Vec<_>=guides.into_iter().chain(validation).map(|v|v+62*pass).collect();
                let pn:Vec<_>=calibration[pass]["noise_planes"].as_array().context("noise")?.iter().map(|v|PlaneNoise{
                    gain_dn_per_e:v["gain_dn_per_e"].as_f64().unwrap() as f32,read_noise_e:v["read_noise_e"].as_f64().unwrap() as f32,
                    levels:Levels{black:v["black"].as_f64().unwrap() as f32,white:v["white"].as_f64().unwrap() as f32}}).collect();
                let noise=NoiseModel::new(pn.try_into().map_err(|_|anyhow::anyhow!("four noise planes"))?,100.,Provenance::Profile);
                let mut q=Qualification::new();let mut sampler=RegionSampler::new(*domain,8<<20)?;let mut beta=f32::INFINITY;
                for (j,&index) in selected.iter().enumerate() {
                    ensure!(session.frames[index].pass_index==pass,"frozen offset crosses pass");
                    let source=cache.load(&ids[index])?.context("missing current original cache; no decode fallback")?;
                    ensure!(source.geometry()==map.geometry(),"source gauge differs");
                    let profile=profile_for_capture_env(metadata[index].camera_model.as_deref(),metadata[index].lens_type3)?;
                    let sampled=sampler.gather(source.as_ref(),source.levels(),map.warps()[index].placed().context("unplaced qualification frame")?,profile,map.resampler())?;
                    q.observe(&sampled.planes,&sampled.support,j>=GUIDES.len());
                    let frame=report["frames"].as_array().unwrap().iter().find(|r|r["frame"]==index).context("render source missing")?;
                    beta=beta.min(frame["color_beta"][0].as_f64().context("sampling beta")? as f32);
                    gains[pass]=frame["photometric_gain"].as_f64().context("gain")? as f32;
                    receipts.push(json!({"roi":name,"pass":pass,"global_index":index,"source":ids[index],
                        "cache_file":cache.cache_path(&ids[index])?,"regional_peak_bytes":sampler.peak_reserved_bytes()}));
                }
                let mut rows=q.result(&noise,1.)?;
                for row in &mut rows {row["minimum_saved_finest_color_beta"]=json!(beta);}
                passes.push(rows);
            }
            let mut tiles=Vec::new();
            for tile in 0..TILES.len() {
                let mut accepted=passes[0][tile]["accepted"]==true&&passes[1][tile]["accepted"]==true;let mut gaps=Vec::new();let mut component_accepted=Vec::new();
                for c in 0..4 {
                    let a=&passes[0][tile]["colors"][c];let b=&passes[1][tile]["colors"][c];
                    let mean_a=a["mean_dn"].as_f64().unwrap()*f64::from(gains[0]);let mean_b=b["mean_dn"].as_f64().unwrap()*f64::from(gains[1]);
                    let sa=a["mean_sample_sigma"].as_f64().unwrap()*f64::from(gains[0]);let sb=b["mean_sample_sigma"].as_f64().unwrap()*f64::from(gains[1]);
                    let gap=(mean_a-mean_b).abs()/sa.hypot(sb);gaps.push(gap);accepted&=gap<=0.5;
                    component_accepted.push(passes[0][tile]["complete_support"]==true&&passes[1][tile]["complete_support"]==true
                        &&a["accepted"]==true&&b["accepted"]==true&&gap<=0.5);
                }
                tiles.push(json!({"tile":tile,"passes":[passes[0][tile],passes[1][tile]],
                    "mean_gap_combined_sigma":gaps,"accepted_components_before_measurement":component_accepted,"accepted_before_measurement":accepted}));
            }
            println!("{name}: {} / {} qualified",tiles.iter().filter(|r|r["accepted_before_measurement"]==true).count(),tiles.len());
            results.push(json!({"name":name,"gains":gains,"tiles":tiles}));
        }
        Ok(())
    })?;
    ensure!(cache.stats().decodes==0,"unexpected RAW decode");
    for id in &ids {id.check_unchanged()?;}
    write(&output.join("qualification.json"),&json!({"schema":"strehl.registered-noise-source-qualification.v1",
        "protocol_sha256":sha(&fs::read(output.join("protocol-frozen.json"))?),"rois":results,"receipts":receipts,
        "raw_decodes":0,"cache_disk_hits":cache.stats().disk_hits,"measurement_loaded":false}))
}
