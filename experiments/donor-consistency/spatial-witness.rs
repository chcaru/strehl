// Optional sink for immutable actual-gather and spatial-consumer witnesses.
use super::*;
use strehl_core::pyramid::LevelSize;
use strehl_core::pyramid::donor_consistency_diagnostic::{
    observe_spatial_source, observe_spatial_finish, AttributionWindow, SpatialWitnessField,
};

const REGIONS: [(&str, [usize; 4]); 2] = [
    ("facet-edges", [2500, 2700, 384, 384]),
    ("dark-inclusion", [3050, 1850, 384, 384]),
];

fn windows() -> Vec<AttributionWindow> {
    REGIONS.iter().map(|(_, r)| AttributionWindow {
        x:r[0]/2,y:r[1]/2,width:r[2]/2,height:r[3]/2,
    }).collect()
}
fn name(field: SpatialWitnessField) -> String {
    use SpatialWitnessField::*;
    match field {
        SourceKnown4=>"source-known4",SourceAc=>"source-ac",SourceBase=>"source-base",
        BaselineAc=>"baseline-ac",BaselineBase=>"baseline-base",BaselinePre=>"baseline-pre",
        BaselinePost=>"baseline-post",BaselineHull=>"baseline-hull",Lo=>"lo",Hi=>"hi",
        Coverage=>"coverage",DonorSum=>"donor-sum",RetainedAc=>"retained-ac",
        PreHull=>"pre-hull",PostHull=>"post-hull",HullCorrection=>"hull-correction",
        Mask(r)=>return format!("mask-{r}"),
    }.to_owned()
}
fn patch(full: &[f32], width: usize, w: AttributionWindow) -> Vec<f32> {
    (w.y..w.y+w.height).flat_map(|y|full[y*width+w.x..y*width+w.x+w.width].iter().copied()).collect()
}
fn same(a:&[f32],b:&[f32])->bool {
    a.len()==b.len() && a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits())
}
fn save_field(directory:&Path, artifacts:&mut Vec<serde_json::Value>, region:usize,
    field:&str, plane:usize, width:usize, height:usize, values:&[f32])->Result<()> {
    ensure!(values.len()==width*height,"witness patch extent");
    let filename=format!("{}-{field}.f32",REGIONS[region].0);
    let path=directory.join(&filename);
    let mut file=if plane==0 {std::fs::OpenOptions::new().write(true).create_new(true).open(&path)?}
        else {let f=std::fs::OpenOptions::new().append(true).open(&path)?;
            ensure!(f.metadata()?.len()==(plane*values.len()*4) as u64,"witness plane order");f};
    let bytes=values.iter().flat_map(|v|v.to_bits().to_le_bytes()).collect::<Vec<_>>();
    file.write_all(&bytes)?;drop(file);
    if plane==3 {artifacts.push(json!({"region":REGIONS[region].0,"field":field,
        "path":format!("{}/{}",directory.file_name().unwrap().to_string_lossy(),filename),
        "shape":[4,height,width],"sha256":file_hash(&path)?}));}
    Ok(())
}

pub(super) struct Witness { directory:PathBuf, output:PathBuf, groups:Vec<serde_json::Value> }
impl Witness {
    pub(super) fn from_env(workspace:&Path,output:&Path)->Result<Option<Self>> {
        let Some(path)=std::env::var_os("STREHL_DONOR_SPATIAL_WITNESS_DIR") else{return Ok(None)};
        let directory=PathBuf::from(path);
        ensure!(directory.is_absolute() && !directory.exists(),"new absolute witness directory required");
        ensure!(directory.parent().context("witness parent")?.canonicalize()?
            .starts_with(workspace.join("experiments").canonicalize()?),"witness outside workspace experiments");
        std::fs::create_dir(&directory)?;
        Ok(Some(Self{directory,output:output.to_path_buf(),groups:Vec::new()}))
    }

    pub(super) fn source(&mut self,index:usize,planes:&[Vec<f32>],sizes:&[LevelSize],
        full_hashes:&[String],levels:Levels,wb:[f32;4],dev:&image_out::Develop)->Result<()> {
        ensure!([25,28,33,69].contains(&index),"unrequested spatial witness source");
        let group=format!("source-{index}");let directory=self.directory.join(&group);
        std::fs::create_dir(&directory)?;
        let mut wins=windows();
        wins.extend(windows().iter().map(|w|AttributionWindow{x:w.x-2,y:w.y-2,width:w.width+4,height:w.height+4}));
        let mut padded=vec![vec![Vec::<f32>::new();4];2];
        let mut artifacts=Vec::new();let mut failure=None;
        let errors=observe_spatial_source(sizes,planes,&wins,&mut Workspace::new(sizes),
            |field,c,window,values|{
                if failure.is_some(){return;}
                let result=(||->Result<()> {
                    if window>=2 {
                        if field!=SpatialWitnessField::SourceKnown4{return Ok(());}
                        let region=window-2;let w=wins[window];
                        let interior=patch(values,w.width,AttributionWindow{x:2,y:2,width:192,height:192});
                        ensure!(same(&interior,&patch(&planes[c],sizes[0].width,wins[region])),"PAD4 centre mismatch");
                        padded[region][c]=values.to_vec();
                        save_field(&directory,&mut artifacts,region,"source-known4-pad4",c,w.width,w.height,values)?;
                    } else {
                        if field==SpatialWitnessField::SourceKnown4 {
                            ensure!(same(values,&patch(&planes[c],sizes[0].width,wins[window])),"source witness differs from actual gather");
                        }
                        save_field(&directory,&mut artifacts,window,&name(field),c,192,192,values)?;
                    }
                    Ok(())
                })();if let Err(error)=result{failure=Some(error);}
            });
        if let Some(error)=failure{return Err(error);}
        ensure!(errors.iter().all(|e|e.is_finite() && *e<=0.02),"source AC/base closure exceeds0.02DN");
        ensure!(planes.iter().map(|p|field_hash(p)).collect::<Vec<_>>().as_slice()==full_hashes,"source witness mutated actual gather");
        let mut developed=Vec::new();
        for region in 0..2 {
            let path=directory.join(format!("{}-actual-source-pad4.tiff",REGIONS[region].0));
            write_planes(&path,&padded[region],align_cmd::CropRect{x:0,y:0,width:196,height:196},levels,wb,dev)?;
            developed.push(json!({"region":REGIONS[region].0,
                "path":format!("{group}/{}",path.file_name().unwrap().to_string_lossy()),
                "sha256":file_hash(&path)?,"native_dimensions":[392,392],"display_crop_xywh":[4,4,384,384],
                "development":"actual held four-CFA write_planes/MHC/developer; no baseline InputRange applied to source"}));
        }
        self.groups.push(json!({"group":group,"index0":index,"actual_known4_sha256":full_hashes,
            "summary":{"source_ac_plus_base_max_abs":errors},"artifacts":artifacts,"developed":developed,
            "pad4_central_known4_bit_exact":true}));
        Ok(())
    }

    pub(super) fn finish_arm(&mut self,arm:&str,merge:&BandMerge,donor:&SpatialDonor,
        sizes:&[LevelSize],delivered:&[Vec<f32>])->Result<()> {
        ensure!(matches!(arm,"candidate"|"late"),"unknown spatial witness arm");
        let directory=self.directory.join(arm);std::fs::create_dir(&directory)?;
        let wins=windows();let mut artifacts=Vec::new();let mut failure=None;
        let summary=observe_spatial_finish(merge,donor,&wins,&mut Workspace::new(sizes),
            |field,c,window,values|{
                if failure.is_some(){return;}
                let result=(||->Result<()> {
                    if field==SpatialWitnessField::PostHull {
                        ensure!(same(values,&patch(&delivered[c],sizes[0].width,wins[window])),"witness differs from actual spatial output");
                    }
                    save_field(&directory,&mut artifacts,window,&name(field),c,192,192,values)
                })();if let Err(error)=result{failure=Some(error);}
            });
        if let Some(error)=failure{return Err(error);}
        ensure!(summary.baseline_sum_max_abs.iter().chain(&summary.mixed_sum_max_abs)
            .chain(&summary.baseline_hull_sum_max_abs).chain(&summary.mixed_hull_sum_max_abs)
            .all(|e|e.is_finite() && *e<=0.02),"spatial witness closure exceeds0.02DN");
        self.groups.push(json!({"group":arm,"artifacts":artifacts,"actual_post_hull_bit_exact":true,
            "summary":{"baseline_sum_max_abs":summary.baseline_sum_max_abs,
                "mixed_sum_max_abs":summary.mixed_sum_max_abs,
                "baseline_hull_sum_max_abs":summary.baseline_hull_sum_max_abs,
                "mixed_hull_sum_max_abs":summary.mixed_hull_sum_max_abs}}));
        Ok(())
    }

    pub(super) fn finish(self,sizes:&[LevelSize],levels:Levels,wb:[f32;4],tone:[f32;3])->Result<()> {
        ensure!(self.groups.len()==6,"four sources and both spatial arms required");
        write_json(&self.directory.join("receipt.json"),&json!({"schema":1,"source_output":self.output,
            "units":"signed black-subtracted source DN; masks and coverage dimensionless",
            "plane_order":["R","G1","G2","B"],"layout":"planar-y-x-f32le",
            "native_dimensions":[2*sizes[0].width,2*sizes[0].height],
            "level_sizes":sizes.iter().map(|s|[s.width,s.height]).collect::<Vec<_>>(),
            "windows":REGIONS.iter().map(|(name,r)|json!({"name":name,"native_xywh":r,
                "quad_xywh":[r[0]/2,r[1]/2,r[2]/2,r[3]/2],
                "pad4_native_xywh":[r[0]-4,r[1]-4,r[2]+8,r[3]+8],
                "pad4_quad_xywh":[r[0]/2-2,r[1]/2-2,r[2]/2+4,r[3]/2+4]})).collect::<Vec<_>>(),
            "levels":[levels.black,levels.white],"wb_bits":wb_gains(wb)?.map(f32::to_bits),
            "raw_metadata_wb_bits":wb[..3].iter().map(|v|v.to_bits()).collect::<Vec<_>>(),
            "matrix":EXPECTED_MATRIX,"tone_bits":tone.map(f32::to_bits),"exposure":1.0,
            "reconstruction_absolute_tolerance_dn":0.02,"groups":self.groups,
            "scope":"actual consumed GPU known4 and full-domain pyramid witnesses; signed fields are not photographs or ownership probabilities"}))
    }
}
