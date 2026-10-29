//! Actual paired core CFA outputs on frozen, source-only component masks.
#![allow(dead_code)]
#[path = "real-noise-consumer-warped.rs"]
mod warped;
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{fs, io::Write, path::Path};
use strehl_cli::{
    session_cache::SourceCache,
    session_focus::complete_support,
    session_input::{ResolvedSession, SourceIdentity},
    session_reconstruction_sampling::RegionSampler,
    session_sampling::{SampledCfa, SamplingDomain},
};
use strehl_core::{
    CfaPlane,
    boxfilter::box_mean,
    plane::{PlaneGeometry, QuadSource},
    pyramid::{
        MergeConfig,
        session_fusion::{
            FrozenPrediction, GroupFocusReference, GroupMode, GroupPolicy, GroupWorkspace,
            PreparedSource, SessionMerge, SourceKey,
        },
    },
};
type Planes = [Vec<f32>; 4];
const W: usize = 128;
const ARMS: [&str; 4] = ["short", "long", "equal-repeat", "precision-repeat"];
fn zero(n: usize) -> Planes {
    std::array::from_fn(|_| vec![0.; n])
}
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
    let mut f = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(p)?;
    serde_json::to_writer_pretty(&mut f, v)?;
    f.write_all(b"\n")?;
    f.sync_all()?;
    Ok(())
}
fn binary(p: &Path, v: &Planes) -> Result<()> {
    let mut f = std::io::BufWriter::new(
        fs::OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(p)?,
    );
    for plane in v {
        for x in plane {
            f.write_all(&x.to_le_bytes())?;
        }
    }
    f.flush()?;
    f.get_ref().sync_all()?;
    Ok(())
}
fn copied(s: &SampledCfa) -> SampledCfa {
    SampledCfa {
        planes: s.planes.clone(),
        coverage: s.coverage.clone(),
        clipped: s.clipped.clone(),
        support: s.support.clone(),
    }
}
struct Outcome {
    planes: Planes,
    valid: Vec<bool>,
    diagnostics: Value,
}
fn beta(report: &Value, index: usize, name: &str) -> Result<Vec<f32>> {
    Ok(report["frames"]
        .as_array()
        .context("frames")?
        .iter()
        .find(|v| v["frame"] == index)
        .context("frame")?[name]
        .as_array()
        .context("beta")?
        .iter()
        .map(|v| v.as_f64().unwrap() as f32)
        .collect())
}
fn produce(
    c: &warped::Contexts,
    report: &Value,
    indices: [usize; 2],
    guide: &Planes,
    guide_support: &[bool],
    guide_id: usize,
    mut load: impl FnMut(usize) -> Result<SampledCfa>,
) -> Result<Vec<Outcome>> {
    let cfg = MergeConfig {
        bands: 7,
        gate: 2.,
        exponent: 2.,
        sharpen_per_octave: 1.4,
        ..Default::default()
    };
    let policy = GroupPolicy {
        mode: GroupMode::Repeat,
        ..Default::default()
    };
    let mut merges: Vec<_> = (0..4)
        .map(|_| SessionMerge::new(W, W, cfg))
        .collect::<std::result::Result<_, _>>()?;
    let mut groups: Vec<_> = (0..4)
        .map(|i| GroupWorkspace::new_with_precision(W, W, cfg, policy, i == 3))
        .collect::<std::result::Result<_, _>>()?;
    let mut source = PreparedSource::new(W, W, cfg)?;
    for pass in 0..2 {
        let index = indices[pass];
        let measured = load(index)?;
        let lb = beta(report, index, "luma_beta")?;
        let cb = beta(report, index, "color_beta")?;
        source.prepare_with_masks(
            SourceKey {
                acquisition: index as u64,
                bracket: pass,
            },
            std::array::from_fn(|color| measured.planes[color].as_slice()),
            &c.noise[pass],
            Some(&lb),
            Some(&cb),
            &measured.coverage,
            &measured.support,
            c.gains[pass],
        )?;
        merges[pass].add_source(&mut groups[pass], &source)?;
        merges[2].add_source(&mut groups[2], &source)?;
        let prediction: Planes =
            std::array::from_fn(|color| guide[color].iter().map(|v| v / c.gains[pass]).collect());
        source.predict_precision(
            FrozenPrediction {
                acquisition: guide_id as u64,
                signal: std::array::from_fn(|color| prediction[color].as_slice()),
                support: guide_support,
            },
            &c.noise[pass],
            c.gains[pass],
            Some(&lb),
            Some(&cb),
        )?;
        merges[3].add_source(&mut groups[3], &source)?;
    }
    let mut result = Vec::new();
    for arm in 0..4 {
        if arm == 3 {
            merges[arm].fold_group_with_focus_reference(
                &mut groups[arm],
                GroupFocusReference::EqualObservation,
            )?;
        } else {
            merges[arm].fold_group(&mut groups[arm])?;
        }
        let out = merges[arm].finish()?;
        let diagnostics=out.diagnostics.iter().map(|v|json!({"averaged":v.averaged_coefficients,"precision":v.precision_averaged_coefficients,"missing_prediction":v.missing_prediction_coefficients,"ordinary_fallback":v.ordinary_fallback_coefficients,"saturated":v.saturated_fallback_coefficients})).collect::<Vec<_>>();
        result.push(Outcome {
            planes: out.planes,
            valid: out.valid,
            diagnostics: json!(diagnostics),
        });
    }
    Ok(result)
}
fn guide(
    c: &warped::Contexts,
    cache: &mut SourceCache,
    ids: &[SourceIdentity],
    domain: SamplingDomain,
    selected: &[usize],
) -> Result<(Planes, Vec<bool>)> {
    let d = SamplingDomain {
        full: domain.full,
        x: domain.x - 8,
        y: domain.y - 8,
        width: W + 16,
        height: W + 16,
    };
    let g = PlaneGeometry {
        width: d.width,
        height: d.height,
    };
    let mut sampler = RegionSampler::new(d, 8 << 20)?;
    let mut sum = zero(W * W);
    let mut valid = vec![true; W * W];
    let mut scratch = vec![0.; g.pixels()];
    let mut blur = scratch.clone();
    let mut mask = vec![0u32; g.pixels()];
    let mut support = vec![false; g.pixels()];
    for &index in selected {
        let pass = usize::from(index >= 62);
        let source = cache
            .load(&ids[index])?
            .context("missing current source cache; no decoding")?;
        let sampled = sampler.gather(
            source.as_ref(),
            source.levels(),
            c.map.warps()[index].placed().context("unplaced guide")?,
            c.profiles[pass],
            c.map.resampler(),
        )?;
        complete_support(&sampled.support, g, 8, &mut mask, &mut support)?;
        for color in 0..4 {
            box_mean(&sampled.planes[color], g, 8, &mut scratch, &mut blur);
            for y in 0..W {
                for x in 0..W {
                    sum[color][y * W + x] +=
                        blur[(y + 8) * g.width + x + 8] * c.gains[pass] / selected.len() as f32;
                    valid[y * W + x] &= support[(y + 8) * g.width + x + 8];
                }
            }
        }
    }
    Ok((sum, valid))
}
fn component_stats(
    a: &Outcome,
    b: &Outcome,
    color: usize,
    x: usize,
    y: usize,
    side: usize,
) -> Value {
    let mut count = 0;
    let mut sum = 0.;
    let mut sq = 0.;
    let mut invalid = 0;
    let mut mean = 0.;
    for yy in y..y + side {
        for xx in x..x + side {
            let i = yy * W + xx;
            let d = f64::from(b.planes[color][i]) - f64::from(a.planes[color][i]);
            sum += d;
            sq += d * d;
            mean += (f64::from(a.planes[color][i]) + f64::from(b.planes[color][i])) * 0.5;
            count += 1;
            invalid += usize::from(!a.valid[i] || !b.valid[i]);
        }
    }
    let n = count as f64;
    json!({"pixels":count,"invalid_pixels":invalid,"mean_signal_dn":mean/n,"signed_mean_difference_dn":sum/n,"raw_half_difference_squared_dn2":sq/(2.*n),"centered_half_difference_squared_dn2":(sq/n-(sum/n).powi(2)).max(0.)*0.5,"scope":"One temporal difference; spatial samples correlated. Entire frozen mask retained, including core fallbacks."})
}
#[path = "real-noise-consumer-controls.rs"]
mod controls;
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    ensure!(args.len() == 5, "RENDER CACHE FROZEN_OUTPUTS_ROOT NEW_OUT");
    let render = Path::new(&args[1]);
    let output = Path::new(&args[4]);
    fs::create_dir(output)?;
    let c = warped::context(render)?;
    let session: ResolvedSession = serde_json::from_value(read(&render.join("session.json"))?)?;
    let ids: Vec<SourceIdentity> =
        serde_json::from_value(read(&render.join("source-identities.json"))?)?;
    let report = read(&render.join("render-report.json"))?;
    let mut windows = Vec::new();
    for base in [12, 20, 28, 36, 44, 52] {
        let root = Path::new(&args[3]).join(format!("registered-noise-window-{base}-01"));
        let p = read(&root.join("protocol-frozen.json"))?;
        let q = read(&root.join("qualification.json"))?;
        ensure!(
            q["protocol_sha256"].as_str()
                == Some(sha(&fs::read(root.join("protocol-frozen.json"))?).as_str())
                && p["alignment_sha256"] == c.bindings["alignment_sha256"],
            "frozen qualification changed"
        );
        windows.push((base, p, q, sha(&fs::read(root.join("qualification.json"))?)));
    }
    // This receipt is complete before opening any current measurement original.
    write(
        &output.join("protocol-before-measurement.json"),
        &json!({"schema":"strehl.real-noise-consumer-paired-protocol.v1","command":args,"bindings":c.bindings,"source_sha256":sha(include_bytes!("real-noise-consumer-paired.rs")),"helper_sha256":sha(include_bytes!("real-noise-consumer-warped.rs")),"arms":ARMS,"recipe":{"bands":7,"gate":2.,"exponent":2.,"sharpen_per_octave":1.4,"precision_focus_reference":"equal-observation"},"windows":windows.iter().map(|(b,p,_,h)|json!({"base":b,"qualification_sha256":h,"measurements":p["measurement_short_not_loaded"],"guides":p["guides_short"]})).collect::<Vec<_>>(),"mask_policy":"Every frozen accepted component tile, no output-driven survivor selection; complete-mask and8x8block summaries, including delivered fallback/refusal pixels.","guide_policy":"Average ten globally measurement-excluded even-ordinal acquisitions, exposure normalized then17x17 spatial mean with complete plugin halo; same frozen guide for both temporal outputs.","scope":"Actual bounded core CFA repeatability, conditional on frozen geometry/guide and adaptive unqualified-green decisions. Two temporal samples/window; no developed-RGB SNR or pure sensor-variance claim.","workers":4,"memory_limit_bytes":2usize<<30}),
    )?;
    controls::commission(&c, &report, output)?;
    let mut cache = SourceCache::new(Path::new(&args[2]), &session, 128 << 20)?;
    let pool = rayon::ThreadPoolBuilder::new().num_threads(4).build()?;
    let mut rows = Vec::new();
    let mut all_diagnostics = Vec::new();
    for (base, p, q, mask_hash) in &windows {
        for (roi_index, roi) in q["rois"].as_array().context("rois")?.iter().enumerate() {
            if !roi["tiles"].as_array().unwrap().iter().any(|tile| {
                tile["accepted_components_before_measurement"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .any(|v| v == true)
            }) {
                continue;
            }
            let d = &p["rois"][roi_index]["domain_quad"];
            let domain = SamplingDomain {
                full: c.map.geometry(),
                x: d[0].as_u64().unwrap() as usize,
                y: d[1].as_u64().unwrap() as usize,
                width: W,
                height: W,
            };
            let guide_ids: Vec<_> = (0..2)
                .flat_map(|pass| {
                    p["guides_short"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .map(move |v| v.as_u64().unwrap() as usize + 62 * pass)
                })
                .collect();
            let (prediction, prediction_support) =
                pool.install(|| guide(&c, &mut cache, &ids, domain, &guide_ids))?;
            let mut results = Vec::new();
            for measurement in p["measurement_short_not_loaded"].as_array().unwrap() {
                let i = measurement.as_u64().unwrap() as usize;
                let mut sampler = RegionSampler::new(domain, 8 << 20)?;
                let outputs = pool.install(|| {
                    produce(
                        &c,
                        &report,
                        [i, i + 62],
                        &prediction,
                        &prediction_support,
                        guide_ids[0],
                        |index| {
                            let pass = usize::from(index >= 62);
                            let original = cache
                                .load(&ids[index])?
                                .context("measurement cache missing; no decode fallback")?;
                            Ok(copied(
                                sampler.gather(
                                    original.as_ref(),
                                    original.levels(),
                                    c.map.warps()[index]
                                        .placed()
                                        .context("unplaced measurement")?,
                                    c.profiles[pass],
                                    c.map.resampler(),
                                )?,
                            ))
                        },
                    )
                })?;
                for (arm, out) in outputs.iter().enumerate() {
                    binary(
                        &output.join(format!(
                            "base{base}-roi{roi_index}-frame{i}-{}.f32",
                            ARMS[arm]
                        )),
                        &out.planes,
                    )?;
                    all_diagnostics.push(json!({"base":base,"roi":roi["name"],"measurement":i,"arm":ARMS[arm],"diagnostics":out.diagnostics}));
                }
                results.push(outputs);
            }
            ensure!(results.len() == 2, "two temporal repetitions required");
            for tile in roi["tiles"].as_array().unwrap() {
                let t = tile["tile"].as_u64().unwrap() as usize;
                let origin = &p["subtiles"][t];
                let x = origin[0].as_u64().unwrap() as usize;
                let y = origin[1].as_u64().unwrap() as usize;
                for color in 0..4 {
                    if tile["accepted_components_before_measurement"][color] != true {
                        continue;
                    }
                    for arm in 0..4 {
                        let a = &results[0][arm];
                        let b = &results[1][arm];
                        let blocks:Vec<_>=(0..4).flat_map(|by|(0..4).map(move |bx|(bx,by))).map(|(bx,by)|json!({"origin_quad_local":[x+8*bx,y+8*by],"stats":component_stats(a,b,color,x+8*bx,y+8*by,8)})).collect();
                        rows.push(json!({"window_base":base,"roi":roi["name"],"tile":t,"color":format!("{:?}",CfaPlane::ALL[color]),"arm":ARMS[arm],"domain_quad":[domain.x,domain.y,W,W],"frozen_mask_sha256":mask_hash,"stats":component_stats(a,b,color,x,y,32),"spatial_blocks":blocks}));
                    }
                }
            }
        }
    }
    ensure!(cache.stats().decodes == 0, "unexpected RAW decode");
    for id in &ids {
        id.check_unchanged()?;
    }
    write(
        &output.join("report.json"),
        &json!({"schema":"strehl.real-noise-consumer-paired.v1","protocol_sha256":sha(&fs::read(output.join("protocol-before-measurement.json"))?),"rows":rows,"diagnostics":all_diagnostics,"cache_disk_hits":cache.stats().disk_hits,"raw_decodes":0,"mask_selection_after_measurement":false,"interpretation":"Component repeatability only, with one difference per acquisition window. Adaptive green and residual scene/focus variation can contribute; no independent-pixel CI, developed-RGB SNR or guaranteed pure noise gain."}),
    )?;
    Ok(())
}
