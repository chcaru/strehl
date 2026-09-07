// Separate private component observation. No production TIFF or RAW decode.
// Intended nested parent: production_truth::m193c_output_grid::precision_witness.
use super::*;
use strehl_core::align::PlaneRef;
use strehl_core::demosaic::{Mosaic, demosaic_malvar_row};

const XS: [usize; 8] = [40, 68, 96, 124, 152, 180, 208, 236];
const YS: [usize; 4] = [36, 68, 100, 132];
const OUTPUT_KEY: &str = "STREHL_M193C_PRECISION_OUTPUT";

fn witness_case(case: Case, folder: &Path, env: &BTreeMap<String, String>) -> Result<Value> {
    ensure!((0..9).all(|i| !sentinel(i).exists()), "M193c precision source sentinel exists");
    let prepared = prepare(case)?;
    let plan = make_plan(case, &prepared, env)?;
    let source = Source::new(case, prepared.source_pulls);
    let geom = PlaneGeometry { width: WIDTH, height: HEIGHT };
    let mut rows = Vec::new();
    for (local, &original) in source.original.iter().enumerate() {
        let mut frame = source.decode(local)?;
        let mosaic: Vec<f32> = frame.data.iter().map(|&v| v as f32 - 512.0).collect();
        // Only one unwarped source is resident; channel planes are consumed
        // here and dropped before the next frame. This is not an aligned stack.
        let mut channels = [vec![0f32; WIDTH * HEIGHT], vec![0f32; WIDTH * HEIGHT]];
        let mut row = vec![0f32; WIDTH * 3];
        {
            let m = Mosaic { data: &mosaic, width: WIDTH, height: HEIGHT };
            for y in 0..HEIGHT {
                demosaic_malvar_row(&m, y, &mut row);
                for x in 0..WIDTH {
                    channels[0][y * WIDTH + x] = row[3 * x];
                    channels[1][y * WIDTH + x] = row[3 * x + 1];
                }
            }
        }
        drop(mosaic);
        let pull = prepared.post_fault[original];
        let mut observations = Vec::new();
        for (yi, &y) in YS.iter().enumerate() {
            for (xi, &x) in XS.iter().enumerate() {
                for (channel, dx) in [(0, 0), (1, 1)] {
                    let nx = x + dx + 2 * prepared.domain.rect.x;
                    let ny = y + 2 * prepared.domain.rect.y;
                    let (qx, qy) = pull.apply_at(nx as f64 * 0.5, ny as f64 * 0.5, 80.0, 60.0);
                    let sx = 2.0 * qx;
                    let sy = 2.0 * qy;
                    let plane = PlaneRef::from_geometry(&channels[channel], geom)
                        .context("M193c precision channel shape")?;
                    let value = Resampler::CatmullRom.sample_checked(plane, sx, sy)
                        .context("M193c precision unsupported fixed site")?;
                    ensure!(value.is_finite(), "M193c precision nonfinite kernel result");
                    let restored = value * 1.0 + 512.0;
                    let rounded = restored.round().clamp(0.0, u16::MAX as f32) as u16;
                    observations.push((nx, ny, rounded, json!({
                        "pair_index": yi * XS.len() + xi,
                        "channel": if channel == 0 { "R" } else { "G1" },
                        "output_native_xy": [x + dx, y],
                        "full_native_xy": [nx, ny],
                        "sample_native_xy": [sx, sy],
                        "sample_f32_dn": value, "sample_f32_bits": value.to_bits(),
                        "black_restored_f32_dn": restored,
                        "black_restored_f32_bits": restored.to_bits(),
                        "rounded_u16": rounded,
                    })));
                }
            }
        }
        drop(channels);
        // Compare with the actual full-resolution warp body, so an accidental
        // difference in this component reconstruction cannot self-certify.
        let mut scratch = align_cmd::WarpScratch::new(PlaneGeometry::from_active(WIDTH, HEIGHT));
        let coverage = align_cmd::warp_frame_in_place_fullres(
            &mut frame, pull, PlaneGeometry::from_active(WIDTH, HEIGHT),
            Resampler::CatmullRom, &mut scratch,
        )?;
        for (nx, ny, rounded, mut observation) in observations {
            let actual = frame.active_row(ny)[nx];
            ensure!(actual == rounded, "M193c precision actual warp disagrees: case{} local{} ({},{}) {} vs {}",
                    case.ordinal, local, nx, ny, actual, rounded);
            observation["actual_warp_u16"] = json!(actual);
            observation["local_index"] = json!(local);
            observation["original_index"] = json!(original);
            rows.push(observation);
        }
        ensure!(coverage.is_finite() && coverage > 0.0, "M193c precision warp coverage");
    }
    source.complete()?;
    ensure!(rows.len() == source.original.len() * 64, "M193c precision sample population");
    let planned_bytes = json_bytes(&plan)?;
    let result = json!({
        "schema": "m193c-precision-case-v1", "status": "COMPONENT_OBSERVED_UNVERIFIED",
        "plan": plan, "plan_sha256": digest(&planned_bytes), "plan_bytes": planned_bytes.len(),
        "source": source.evidence()?, "rows": rows,
        "scope": "existing MHC/Catmull f32 values and actual warp u16; independent numeric oracle pending",
    });
    let path = folder.join(format!("{:02}-{}.json", case.ordinal, case.name()));
    write_new_json(&path, &result)?;
    file_ref(&path, JSON_LIMIT)
}

#[test]
#[ignore = "M193c requires committed component command and independent fixed-site oracle"]
fn m193c_private_precision_witness() -> Result<()> {
    let started = Instant::now();
    let mut env = BTreeMap::new();
    for (key, expected) in [
        ("STREHL_DEFECT", "off"), ("STREHL_FIX_CA", "off"),
        ("STREHL_FULLRES_GATHER", "1"), ("STREHL_PYRAMID_WORKERS", "2"),
        ("RAYON_NUM_THREADS", "2"),
    ] {
        ensure!(std::env::var(key).as_deref() == Ok(expected), "M193c precision required environment {key}");
        env.insert(key.to_string(), expected.to_string());
    }
    for (key, _) in std::env::vars() {
        ensure!(!key.starts_with("STREHL_") || key == OUTPUT_KEY || env.contains_key(&key),
                "M193c precision unexpected environment {key}");
    }
    let folder = PathBuf::from(std::env::var(OUTPUT_KEY)?);
    ensure!(folder.is_absolute() && !folder.exists() && folder.parent().is_some_and(Path::is_dir),
            "M193c precision fresh absolute output directory");
    fs::create_dir(&folder)?;
    let mut completed = Vec::new();
    let outcome = (|| -> Result<()> {
        for ordinal in 0..CASE_NAMES.len() {
            completed.push(witness_case(Case { ordinal }, &folder, &env)?);
        }
        ensure!(completed.len() == 10, "M193c complete precision cases");
        Ok(())
    })();
    let result = json!({
        "schema": "m193c-precision-witness-v1",
        "status": if outcome.is_ok() { "COMPONENT_OBSERVED_UNVERIFIED" } else { "REFUSED_COMPONENT" },
        "cases": completed, "command": std::env::args().collect::<Vec<_>>(),
        "environment": env, "elapsed_seconds_before_receipt": started.elapsed().as_secs_f64(),
        "error": outcome.as_ref().err().map(|e| format!("{e:#}")), "secondary_errors": [],
        "compiled_inputs": {"precision_witness_sha256": digest(include_bytes!(concat!(env!("CARGO_MANIFEST_DIR"),
            "/../../experiments/m193c-output-grid/precision-witness.rs")))},
        "scope": "58 generated frames,3712 fixed R/G1 component samples; no production TIFF/no random plant noise",
    });
    if let Err(persist) = write_new_json(&folder.join("result.json"), &result) {
        if let Err(primary) = outcome {
            return Err(primary.context(format!("component receipt persistence: {persist:#}")));
        }
        return Err(persist);
    }
    outcome
}
