//! Diagnostic actual per-original-site Q-guide prediction. Every product/SR
//! admission remains FALSE; this does not commission the shared guide model.
#![allow(dead_code)]
pub use strehl_core::{CfaPlane, align, noise, plane};
#[path = "noise-bee-repeat-binding.rs"]
mod binding;
#[path = "real-noise-consumer-warped.rs"]
mod context;
#[path = "noise-bee-repeat-compatibility.rs"]
mod decision;
#[path = "noise-bee-repeat-guide-predictor.rs"]
mod predictor;
#[path = "../../../../crates/strehl-core/src/repeat-evidence.rs"]
mod tap;
#[path = "noise-bee-repeat-model.rs"]
mod temporal;
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    collections::BTreeSet,
    fs,
    io::{BufWriter, Write},
    path::Path,
};
use strehl_cli::{
    session_cache::SourceCache,
    session_input::{ResolvedSession, SourceIdentity},
};
use strehl_core::optics::{OpticalProfile, cfa_site_channel};
fn sha(b: &[u8]) -> String {
    Sha256::digest(b)
        .iter()
        .map(|v| format!("{v:02x}"))
        .collect()
}
fn read(p: &Path) -> Result<Value> {
    Ok(serde_json::from_slice(&fs::read(p)?)?)
}
fn write(p: &Path, v: &Value) -> Result<()> {
    let mut f = BufWriter::new(
        fs::OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(p)?,
    );
    serde_json::to_writer_pretty(&mut f, v)?;
    f.write_all(b"\n")?;
    f.flush()?;
    f.get_ref().sync_all()?;
    Ok(())
}
fn iv(i: Option<decision::Interval>) -> Value {
    i.map_or(Value::Null, |v| json!([v.lower, v.upper]))
}
fn ev(e: &decision::Evidence) -> Value {
    json!({"diagnostic_decision":format!("{:?}",e.decision),"points":e.points,"identity_difference_to_noise":iv(e.identity_difference_to_noise),"joint_difference_to_noise":iv(e.joint_difference_to_noise),"bands":e.bands.iter().map(|b|json!({"band":b.band,"diagnostic_decision":format!("{:?}",b.decision),"signal_x":iv(b.signal_x),"signal_y":iv(b.signal_y),"signed_cross":iv(b.signed_cross),"y_from_x_amplitude":iv(b.y_from_x_amplitude),"x_from_y_amplitude":iv(b.x_from_y_amplitude),"disagreement_cost_to_equal_noise_benefit":iv(b.difference_cost_to_equal_noise_benefit)})).collect::<Vec<_>>()})
}
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    ensure!(args.len() == 5, "RENDER CACHE PROTOCOL NEW_OUT");
    let render = Path::new(&args[1]);
    let input = Path::new(&args[3]);
    let out = Path::new(&args[4]);
    fs::create_dir(out)?;
    let pb = fs::read(input)?;
    ensure!(
        sha(&pb) == "f2fc47d451314ef0bf4a188cdf52d147d17de4fd72b947f58069017f631fcae4",
        "protocol"
    );
    let p: Value = serde_json::from_slice(&pb)?;
    let c = context::context(render)?;
    ensure!(c.gains == [1., 1.], "rawgain1 comparison");
    let session: ResolvedSession = serde_json::from_value(read(&render.join("session.json"))?)?;
    let ids: Vec<SourceIdentity> =
        serde_json::from_value(read(&render.join("source-identities.json"))?)?;
    let ob = fs::read(input.parent().unwrap().join("source-identities32.json"))?;
    ensure!(
        p["input_receipts"][r"inputs\source-identities32.json"] == sha(&ob),
        "original hashreceipt"
    );
    let originals: Vec<Value> = serde_json::from_slice(&ob)?;
    let originals: Vec<_> = originals
        .iter()
        .map(|v| {
            Ok(binding::Record {
                filename: Path::new(v["path"].as_str().context("path")?)
                    .file_name()
                    .unwrap()
                    .to_str()
                    .unwrap()
                    .into(),
                bytes: v["bytes"].as_u64().context("bytes")?,
                sha256: v["sha256"].as_str().context("sha")?.into(),
            })
        })
        .collect::<Result<_>>()?;
    let copied: Vec<_> = ids
        .iter()
        .map(|v| binding::Record {
            filename: Path::new(&v.path)
                .file_name()
                .unwrap()
                .to_str()
                .unwrap()
                .into(),
            bytes: v.bytes,
            sha256: v.sha256.clone(),
        })
        .collect();
    let indices = binding::bind32(&originals, &copied).map_err(anyhow::Error::msg)?;
    let target = [indices[3], indices[2]];
    let guide = [indices[0], indices[7]];
    ensure!(
        target == [1, 17] && guide == [0, 3],
        "frozen four source nomination"
    );
    ensure!(
        session.frames.len() == 32 && ids.len() == 32,
        "exact32 source set"
    );
    for (i, f) in session.frames.iter().enumerate() {
        ensure!(
            f.global_index == i && f.path == ids[i].path,
            "sourceidentityorder"
        );
    }
    let all = [target[0], target[1], guide[0], guide[1]];
    ensure!(
        all.iter().copied().collect::<BTreeSet<_>>().len() == 4,
        "guide/source collision"
    );
    let times = p["timestamps_unix"].as_array().unwrap();
    let t0 = times[0].as_f64().unwrap();
    let gt = [0., times[7].as_f64().unwrap() - t0];
    let temporal_weights =
        [3, 2].map(|o| temporal::weights(gt, times[o].as_f64().unwrap() - t0).unwrap());
    write(
        &out.join("protocol-frozen.json"),
        &json!({"schema":"strehl.bee-real-original-guide-diagnostic.v1","command":args,"protocol_sha256":sha(&pb),"original_identity_sha256":sha(&ob),"bindings":c.bindings,"target_global":target,"guide_global":guide,"target_ordinal":[3,2],"guide_ordinal":[0,7],"weights":temporal_weights,"patches":&p["geometry_patches"].as_array().unwrap()[1..3],"source_sha256":sha(include_bytes!("noise-bee-repeat-compatibility-real.rs")),"decision_sha256":sha(include_bytes!("noise-bee-repeat-compatibility.rs")),"primitive_sha256":sha(include_bytes!("../../../../crates/strehl-core/src/repeat-evidence.rs")),"product_admission":false,"sr_admission":false,"workers":1,"budget_bytes":4usize<<30,"guide_model":"Actual distinctQ0/Q7 original-CFA Catmull values at each targetoriginalsite, timestampinterpolated without extrapolation; no localconstant/center shortcut. Shared guide and fitted geometry mean real envelopes are diagnostic, not calibrated probabilities."}),
    )?;
    let mut cache = SourceCache::new(Path::new(&args[2]), &session, 384 << 20)?;
    let sources = all
        .iter()
        .map(|&i| {
            cache
                .load(&ids[i])?
                .context("missing originalcache; RAWforbidden")
        })
        .collect::<Result<Vec<_>>>()?;
    let full = c.map.geometry();
    let bands = tap::binomial_bands();
    let filters: Vec<_> = bands.iter().map(Vec::as_slice).collect();
    let mut rows = Vec::new();
    for patch in &p["geometry_patches"].as_array().unwrap()[1..3] {
        let f = patch["active_fraction_center"].as_array().unwrap();
        let origin = [
            (f[0].as_f64().unwrap() * full.width as f64).floor() as usize - 128,
            (f[1].as_f64().unwrap() * full.height as f64).floor() as usize - 128,
        ];
        for color in 0..4 {
            let plane = CfaPlane::ALL[color];
            let (dx, dy) = plane.rggb_offset();
            let pulls: Vec<_> = all
                .iter()
                .map(|&i| {
                    OpticalProfile::compose(
                        c.profiles[session.frames[i].pass_index],
                        cfa_site_channel(dx, dy),
                        c.map.warps()[i].placed().unwrap(),
                    )
                })
                .collect();
            let mut target_used: [BTreeSet<(usize, usize)>; 2] =
                std::array::from_fn(|_| BTreeSet::new());
            let mut guide_used: [BTreeSet<(usize, usize)>; 2] =
                std::array::from_fn(|_| BTreeSet::new());
            let mut points = Vec::new();
            let mut saved_points = Vec::new();
            let mut refusals = Vec::new();
            let mut predicted_range = [f32::INFINITY, f32::NEG_INFINITY];
            for yy in (8..256).step_by(16) {
                for xx in (8..256).step_by(16) {
                    let center_sensor = [
                        2. * (origin[0] + xx) as f64 + 0.5,
                        2. * (origin[1] + yy) as f64 + 0.5,
                    ];
                    let mut observations = Vec::new();
                    for source in 0..2 {
                        let pass = session.frames[target[source]].pass_index;
                        let acquisition_id: [u8; 32] = ids[target[source]]
                            .sha256
                            .as_bytes()
                            .chunks_exact(2)
                            .map(|v| {
                                u8::from_str_radix(std::str::from_utf8(v).unwrap(), 16).unwrap()
                            })
                            .collect::<Vec<_>>()
                            .try_into()
                            .unwrap();
                        let view = tap::OriginalView {
                            acquisition_id,
                            source: sources[source].as_ref(),
                            plane,
                            color_pull: pulls[source],
                            noise: *c.noise[pass].plane(plane),
                            gain: 1.,
                        };
                        let o = tap::observe(
                            &view,
                            full,
                            center_sensor,
                            &filters,
                            tap::Kernel::CatmullRom,
                            2 << 20,
                            |original| {
                                let mean = predictor::predict(
                                    original.quad,
                                    plane,
                                    pulls[source],
                                    full,
                                    [sources[2].as_ref(), sources[3].as_ref()],
                                    [pulls[2], pulls[3]],
                                    [sources[2].levels(), sources[3].levels()],
                                    temporal_weights[source],
                                    &mut guide_used,
                                )?;
                                predicted_range[0] = predicted_range[0].min(mean);
                                predicted_range[1] = predicted_range[1].max(mean);
                                Some(mean)
                            },
                        );
                        match o {
                            Ok(o) => {
                                for tap in &o.taps {
                                    ensure!(
                                        target_used[source]
                                            .insert((tap.site.quad[0], tap.site.quad[1])),
                                        "original point footprints overlap"
                                    );
                                }
                                observations.push(o);
                            }
                            Err(e) => refusals.push(
                                json!({"grid":[xx,yy],"source":source,"reason":format!("{e:?}")}),
                            ),
                        }
                    }
                    if observations.len() == 2 {
                        // Diagnostic serialization only: values below are the exact
                        // observations already consumed by the unchanged decision.
                        let source_plane_centers: Vec<_> = pulls[..2]
                            .iter()
                            .map(|pull| {
                                let (sx, sy) = pull.apply_at(
                                    (center_sensor[0] - 0.5) * 0.5,
                                    (center_sensor[1] - 0.5) * 0.5,
                                    full.width as f64 * 0.5,
                                    full.height as f64 * 0.5,
                                );
                                [sx + 0.25 - dx as f64 * 0.5, sy + 0.25 - dy as f64 * 0.5]
                            })
                            .collect();
                        saved_points.push(json!({
                            "grid": [xx, yy], "center_sensor": center_sensor,
                            "source_plane_centers": source_plane_centers,
                            "x": &observations[0].values[..3],
                            "y": &observations[1].values[..3],
                            "covariance_x": observations[0].covariance[..3].iter()
                                .map(|row| &row[..3]).collect::<Vec<_>>(),
                            "covariance_y": observations[1].covariance[..3].iter()
                                .map(|row| &row[..3]).collect::<Vec<_>>(),
                        }));
                        points.push(decision::PairSample {
                            x: std::array::from_fn(|i| f64::from(observations[0].values[i])),
                            y: std::array::from_fn(|i| f64::from(observations[1].values[i])),
                            covariance_x: std::array::from_fn(|i| {
                                std::array::from_fn(|j| f64::from(observations[0].covariance[i][j]))
                            }),
                            covariance_y: std::array::from_fn(|i| {
                                std::array::from_fn(|j| f64::from(observations[1].covariance[i][j]))
                            }),
                        });
                    }
                }
            }
            let evaluated = if refusals.is_empty() {
                Some(
                    decision::evaluate(&points, decision::Policy::default())
                        .map_err(anyhow::Error::msg)?,
                )
            } else {
                None
            };
            let footprints = json!({"target_global":target,"guide_global":guide,"color":color,"target_sites":target_used.iter().map(|s|s.iter().copied().collect::<Vec<_>>()).collect::<Vec<_>>(),"guide_sites":guide_used.iter().map(|s|s.iter().copied().collect::<Vec<_>>()).collect::<Vec<_>>()});
            let filename = format!("{}-c{color}-footprints.json", patch["id"].as_str().unwrap());
            write(&out.join(&filename), &footprints)?;
            let point_filename = format!(
                "{}-c{color}-observations.json",
                patch["id"].as_str().unwrap()
            );
            write(
                &out.join(&point_filename),
                &json!({
                    "schema": "strehl.bee-original-guide-points.v1", "patch": patch["id"],
                    "color": color, "target_global": target, "guide_global": guide,
                    "full_quad_geometry": [full.width, full.height], "points": saved_points,
                    "refusals": refusals, "product_admission": false, "sr_admission": false,
                }),
            )?;
            rows.push(json!({"observation_receipt": {"path":point_filename,"sha256":sha(&fs::read(out.join(&point_filename))?)},"patch":patch["id"],"color":color,"origin_quad":origin,"points":points.len(),"prediction_range_dn":predicted_range,"refusals":refusals,"evidence":evaluated.as_ref().map(ev),"target_original_sites":target_used.iter().map(BTreeSet::len).collect::<Vec<_>>(),"guide_original_sites":guide_used.iter().map(BTreeSet::len).collect::<Vec<_>>(),"footprint_receipt":{"path":filename,"sha256":sha(&fs::read(out.join(&filename))?)},"product_admission":false,"sr_admission":false}));
        }
    }
    for &i in &all {
        ids[i].check_unchanged()?;
    }
    ensure!(cache.stats().decodes == 0, "zeroRAW");
    write(
        &out.join("result.json"),
        &json!({"schema":"strehl.bee-real-original-guide-diagnostic.v1","protocol_sha256":sha(&fs::read(out.join("protocol-frozen.json"))?),"rows":rows,"source_identities":all.iter().map(|&i|&ids[i]).collect::<Vec<_>>(),"cache_disk_hits":cache.stats().disk_hits,"raw_decodes":0,"all_admission_false":true,"limitations":["Shared Qguide photons and previous wholephoto geometry; covariance envelopes not calibrated real significance.","No consuming localgeometry or PSFequivalence certificate yet for nominated calibration patches.","Native mean operator only; current3binomial bands do not map directly to7product pyramid bands.","No actualsource-dependent point filtering or mask pruning; any supportfailure prevents patch evidence."]}),
    )?;
    println!("8patch/component diagnostics;4cache-only sources;alladmissionfalse");
    Ok(())
}
