//! Export exactly the production physical-support-selected geometry sites.
use anyhow::{Context, Result, ensure};
use serde_json::json;
use sha2::{Digest, Sha256};
use std::{fs::File, io::{BufReader, BufWriter, Read, Write}, path::Path};
use strehl_cli::{session_cache, session_focus, session_input, session_sampling};
#[path = "../../../../crates/strehl-cli/src/session-mosaic-geometry.rs"]
mod session_mosaic_geometry;
fn hash(path:&Path)->Result<String>{
    let mut file=BufReader::new(File::open(path)?);let mut digest=Sha256::new();let mut buffer=[0_u8;65536];
    loop{let n=file.read(&mut buffer)?;if n==0{break;}digest.update(&buffer[..n]);}
    Ok(digest.finalize().iter().map(|v|format!("{v:02x}")).collect())
}
fn main()->Result<()>{
    let args:Vec<_>=std::env::args().skip(1).collect();ensure!(args.len()==2,"independent-sites NATIVE_REPLAY FRESH_OUTPUT_JSON");
    let root=Path::new(&args[0]);let path=root.join("mosaic-native-measurements.json");
    ensure!(std::fs::metadata(&path)?.len()<128<<20,"native receipt exceeds bounded audit size");
    let native:Vec<session_mosaic_geometry::NativeCorrespondence>=serde_json::from_reader(BufReader::new(File::open(&path)?))?;
    let session:session_input::ResolvedSession=serde_json::from_reader(BufReader::new(File::open(root.join("session.json"))?))?;
    let sites=session_mosaic_geometry::independent_native_constraints(&native,session.passes.len(),0.5)?;
    let records:Vec<_>=sites.receipt_indices.iter().map(|&i|json!({"receipt_index":i,"receipt":native[i]})).collect();
    let fit=sites.observations.iter().filter(|o|o.role==strehl_core::mosaic::ObservationRole::Fit).count();
    let mut writer=BufWriter::new(File::options().write(true).create_new(true).open(&args[1])?);
    serde_json::to_writer_pretty(&mut writer,&json!({"schema":"strehl.mosaic-independent-sites.v1","native_sha256":hash(&path)?,"source_identities_sha256":hash(&root.join("source-identities.json"))?,"passes":session.passes.len(),"sources":session.len(),"fit_sites":fit,"heldout_sites":sites.observations.len()-fit,"measured_loops":sites.loops.len()/2,"records":records,"claim":"Exact production independent-site selection. No new measurement, geometry fit or photographic claim."}))?;
    writer.write_all(b"\n")?;writer.flush()?;
    ensure!(sites.receipt_indices.len()==sites.observations.len(),"index/observation count differs");
    eprintln!("selected{} independent sites: {}FIT/{}heldout",sites.observations.len(),fit,sites.observations.len()-fit);
    Ok(())
}
