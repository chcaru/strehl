//! Commission the frozen qualification gate after actual original-CFA gathering.
//! Current measured trajectories and saved optical choices; no RAW decoding.
#[path = "real-noise-consumer-gate.rs"]
mod frozen_gate;
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{fs, io::Write, path::Path};
use strehl_cli::{
    session_input::ResolvedSession, session_reconstruction_sampling::RegionSampler,
    session_sampling::SamplingDomain,
};
use strehl_core::{
    CfaPlane,
    align::Similarity,
    noise::{Levels, NoiseModel, PlaneNoise, Provenance},
    optics::{OpticalProfile, cfa_site_channel, profile_for_capture_env},
    plane::{PlaneGeometry, QuadSource},
    warpmap::WarpMap,
};
const SIDE: usize = 128;
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
pub(crate) struct Contexts {
    pub(crate) map: WarpMap,
    pub(crate) noise: [NoiseModel; 2],
    pub(crate) profiles: [Option<&'static OpticalProfile>; 2],
    pub(crate) gains: [f32; 2],
    pub(crate) bindings: Value,
}
pub(crate) fn context(render: &Path) -> Result<Contexts> {
    let session: ResolvedSession = serde_json::from_value(read(&render.join("session.json"))?)?;
    let metadata = session.read_metadata()?;
    let a = read(&render.join("alignment.json"))?;
    ensure!(
        a["binding"]["sources"] == read(&render.join("source-identities.json"))?
            && a["binding"]["session"] == serde_json::to_value(&session.spec)?,
        "source/session binding differs"
    );
    let map = WarpMap::from_text(a["warpmap"].as_str().context("warpmap")?)?;
    let cal = read(&render.join("calibration.json"))?;
    let report = read(&render.join("render-report.json"))?;
    let mut noises = Vec::new();
    let mut profiles = [None; 2];
    let mut gains = [1.; 2];
    for pass in 0..2 {
        let i = session
            .frames
            .iter()
            .position(|f| f.pass_index == pass)
            .context("pass")?;
        profiles[pass] =
            profile_for_capture_env(metadata[i].camera_model.as_deref(), metadata[i].lens_type3)?;
        match profiles[pass] {
            Some(p) => ensure!(
                cal[pass]["optical_profile"]["applied_record"].as_str()
                    == Some(format!("{p:?}").as_str()),
                "current optical profile differs from frozen calibration"
            ),
            None => ensure!(
                cal[pass]["optical_profile"].is_null(),
                "missing saved optical profile"
            ),
        }
        let pn: Vec<_> = cal[pass]["noise_planes"]
            .as_array()
            .context("noise")?
            .iter()
            .map(|v| PlaneNoise {
                gain_dn_per_e: v["gain_dn_per_e"].as_f64().unwrap() as f32,
                read_noise_e: v["read_noise_e"].as_f64().unwrap() as f32,
                levels: Levels {
                    black: v["black"].as_f64().unwrap() as f32,
                    white: v["white"].as_f64().unwrap() as f32,
                },
            })
            .collect();
        noises.push(NoiseModel::new(
            pn.try_into()
                .map_err(|_| anyhow::anyhow!("four noise planes"))?,
            100.,
            Provenance::Profile,
        ));
        gains[pass] = report["frames"]
            .as_array()
            .context("frames")?
            .iter()
            .find(|v| v["frame"] == i)
            .context("gain frame")?["photometric_gain"]
            .as_f64()
            .context("gain")? as f32;
    }
    Ok(Contexts {
        map,
        noise: noises
            .try_into()
            .map_err(|_| anyhow::anyhow!("two passes"))?,
        profiles,
        gains,
        bindings: json!({"alignment_sha256":sha(&fs::read(render.join("alignment.json"))?),"calibration_sha256":sha(&fs::read(render.join("calibration.json"))?),"optics_exact_debug_record_equal":true}),
    })
}
fn uniform(s: &mut u64) -> f32 {
    *s ^= *s << 13;
    *s ^= *s >> 7;
    *s ^= *s << 17;
    (((*s >> 40) as u32) as f32 + 0.5) / 16777216.
}
fn gaussian(s: &mut u64) -> f32 {
    (-2. * uniform(s).ln()).sqrt() * (std::f32::consts::TAU * uniform(s)).cos()
}
pub(crate) struct Plant {
    full: PlaneGeometry,
    first_y: usize,
    rows: Vec<u16>,
}
impl QuadSource for Plant {
    fn geometry(&self) -> PlaneGeometry {
        self.full
    }
    fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
        let row = 2 * (y - self.first_y) * 2 * self.full.width;
        let w = 2 * self.full.width;
        (&self.rows[row..row + w], &self.rows[row + w..row + 2 * w])
    }
}
pub(crate) fn plant(
    domain: SamplingDomain,
    t: Similarity,
    p: Option<&OpticalProfile>,
    noise: &NoiseModel,
    gain: f32,
    mode: &str,
    temporal: f32,
    seed: u64,
) -> Result<Plant> {
    let pulls: [Similarity; 4] = std::array::from_fn(|c| {
        let (dx, dy) = CfaPlane::ALL[c].rggb_offset();
        OpticalProfile::compose(p, cfa_site_channel(dx, dy), t)
    });
    let full = domain.full;
    let center = [full.width as f64 * 0.5, full.height as f64 * 0.5];
    let mut bounds = [
        f64::INFINITY,
        f64::INFINITY,
        f64::NEG_INFINITY,
        f64::NEG_INFINITY,
    ];
    for (c, t) in pulls.iter().enumerate() {
        let (dx, dy) = CfaPlane::ALL[c].rggb_offset();
        let site = [dx as f64 * 0.5 - 0.25, dy as f64 * 0.5 - 0.25];
        for (x, y) in [
            (domain.x, domain.y),
            (domain.x + SIDE - 1, domain.y),
            (domain.x, domain.y + SIDE - 1),
            (domain.x + SIDE - 1, domain.y + SIDE - 1),
        ] {
            let q = t.apply_at(x as f64 + site[0], y as f64 + site[1], center[0], center[1]);
            bounds[0] = bounds[0].min(q.0 - site[0]);
            bounds[1] = bounds[1].min(q.1 - site[1]);
            bounds[2] = bounds[2].max(q.0 - site[0]);
            bounds[3] = bounds[3].max(q.1 - site[1]);
        }
    }
    let x0 = (bounds[0].floor() - 8.).max(0.) as usize;
    let y0 = (bounds[1].floor() - 8.).max(0.) as usize;
    let x1 = (bounds[2].ceil() + 9.).min(full.width as f64) as usize;
    let y1 = (bounds[3].ceil() + 9.).min(full.height as f64) as usize;
    ensure!(
        x1 > x0 && y1 > y0 && x1 - x0 < 384 && y1 - y0 < 384,
        "unbounded plant rectangle"
    );
    let mut out = Plant {
        full,
        first_y: y0,
        rows: vec![65535; 4 * full.width * (y1 - y0)],
    };
    let mut rng = seed.wrapping_mul(0x9e3779b97f4a7c15) | 1;
    for (c, t) in pulls.iter().enumerate() {
        let inverse = t.invert().context("singular pull")?;
        let (dx, dy) = CfaPlane::ALL[c].rggb_offset();
        let site = [dx as f64 * 0.5 - 0.25, dy as f64 * 0.5 - 0.25];
        for y in y0..y1 {
            for x in x0..x1 {
                let q =
                    inverse.apply_at(x as f64 + site[0], y as f64 + site[1], center[0], center[1]);
                let xx = (q.0 - domain.x as f64) as f32;
                let yy = (q.1 - domain.y as f64) as f32;
                let common = match mode {
                    "drift" => 1200. + 30. * temporal,
                    "translated-texture" => {
                        1200.
                            + 100. * ((xx + temporal) * 0.5).sin()
                            + 80. * ((yy - temporal) * 0.3).cos()
                    }
                    "defocus" => {
                        1200.
                            + (1. - 0.5 * temporal.abs())
                                * (100. * (xx * 0.5).sin() + 80. * (yy * 0.3).cos())
                    }
                    "signal" => 1200. + 100. * (xx * 0.07).sin() + 80. * (yy * 0.11).cos(),
                    "stationary-texture" => 1200. + 3. * (xx * 0.5).sin() + 2. * (yy * 0.3).cos(),
                    _ => 1200.,
                };
                let signal = common / gain;
                let pn = noise.plane(CfaPlane::ALL[c]);
                let v = signal
                    + if seed == 0 {
                        0.
                    } else {
                        gaussian(&mut rng) * pn.variance(signal).sqrt()
                    }
                    + pn.levels.black;
                out.rows[(2 * (y - y0) + dy) * 2 * full.width + 2 * x + dx] = if mode == "clipped" {
                    pn.levels.white as u16
                } else {
                    v.round().clamp(0., 65535.) as u16
                };
            }
        }
    }
    Ok(out)
}
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    ensure!(args.len() == 4, "RENDER FROZEN_OUTPUTS_ROOT NEW_OUT");
    let render = Path::new(&args[1]);
    let frozen = Path::new(&args[2]);
    let output = Path::new(&args[3]);
    fs::create_dir(output)?;
    let c = context(render)?;
    let pool = rayon::ThreadPoolBuilder::new().num_threads(4).build()?;
    let mut windows = Vec::new();
    for base in [12, 20, 28, 36, 44, 52] {
        let root = frozen.join(format!("registered-noise-window-{base}-01"));
        let protocol = read(&root.join("protocol-frozen.json"))?;
        let mask = read(&root.join("qualification.json"))?;
        ensure!(
            mask["protocol_sha256"].as_str()
                == Some(sha(&fs::read(root.join("protocol-frozen.json"))?).as_str()),
            "qualification protocol changed"
        );
        ensure!(
            protocol["alignment_sha256"] == c.bindings["alignment_sha256"],
            "qualification geometry differs"
        );
        windows.push((
            base,
            protocol,
            sha(&fs::read(root.join("qualification.json"))?),
        ));
    }
    let mut rows = Vec::new();
    let mut totals = Vec::new();
    for mode in [
        "flat",
        "stationary-texture",
        "drift",
        "translated-texture",
        "defocus",
        "clipped",
    ] {
        let mut accepted = 0;
        let mut cases = 0;
        for (base, protocol, mask_hash) in &windows {
            for pass in 0..2 {
                for seed in 0..4 {
                    // Every measured trajectory window is exercised at the predeclared gray-ramp ROI.
                    let d = &protocol["rois"][0]["domain_quad"];
                    let domain = SamplingDomain {
                        full: c.map.geometry(),
                        x: d[0].as_u64().unwrap() as usize,
                        y: d[1].as_u64().unwrap() as usize,
                        width: SIDE,
                        height: SIDE,
                    };
                    let selected: Vec<_> = protocol["guides_short"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .chain(protocol["validation_short"].as_array().unwrap())
                        .map(|v| v.as_u64().unwrap() as usize + 62 * pass)
                        .collect();
                    let mut gate = frozen_gate::Gate::new();
                    let mut sampler = RegionSampler::new(domain, 8 << 20)?;
                    pool.install(|| -> Result<()> {
                        for (j, index) in selected.iter().enumerate() {
                            let temporal = if j < 5 {
                                (j as f32 - 2.) / 2.
                            } else if j == 5 {
                                1.
                            } else {
                                -1.
                            };
                            let t = c.map.warps()[*index].placed().context("unplaced plant")?;
                            let raw = plant(
                                domain,
                                t,
                                c.profiles[pass],
                                &c.noise[pass],
                                c.gains[pass],
                                mode,
                                temporal,
                                1 + seed * 157 + *index as u64 * 7919,
                            )?;
                            let sampled = sampler.gather(
                                &raw,
                                c.noise[pass].plane(CfaPlane::R).levels,
                                t,
                                c.profiles[pass],
                                c.map.resampler(),
                            )?;
                            gate.observe(&sampled.planes, &sampled.support, j >= 5);
                        }
                        Ok(())
                    })?;
                    let tiles = gate.result(&c.noise[pass])?;
                    let count = tiles.iter().filter(|v| v["accepted"] == true).count();
                    accepted += count;
                    cases += 9;
                    rows.push(json!({"mode":mode,"base":base,"pass":pass,"seed":seed,"accepted":count,"tiles":tiles,"frozen_mask_sha256":mask_hash,"sampler_peak_bytes":sampler.peak_reserved_bytes()}));
                }
            }
        }
        println!("{mode}: {accepted}/{cases}");
        totals.push(json!({"mode":mode,"accepted":accepted,"total":cases}));
        write(
            &output.join(format!("{mode}.json")),
            &json!({"rows":rows.iter().filter(|v|v["mode"]==mode).collect::<Vec<_>>()}),
        )?;
        ensure!(
            if mode == "flat" || mode == "stationary-texture" {
                accepted * 4 >= cases * 3
            } else {
                accepted == 0
            },
            "actual warped qualification commissioning failed: {mode} {accepted}/{cases}"
        );
    }
    write(
        &output.join("report.json"),
        &json!({"schema":"strehl.real-noise-consumer-warped-qualification.v1","command":args,"source_sha256":sha(include_bytes!("real-noise-consumer-warped.rs")),"gate_adapter_sha256":sha(include_bytes!("real-noise-consumer-gate.rs")),"root_gate_sha256":"0edf320de86ef2d6294f2c91461ef8c978d7bf1fba7d910d908dfba59784ec55","bindings":c.bindings,"totals":totals,"workers":4,"raw_decodes":0,"scope":"Complete original-u16 measured-trajectory gather, optical composition,5x5 box and unchanged source gate. Known-signal controls commission the instrument, not real camera calibration or delivered RGB gain."}),
    )?;
    Ok(())
}
