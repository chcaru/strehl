// Opt-in extraction policy. This module does not change storage or merge arithmetic.
pub(super) const ENV: &str = "STREHL_SIGNED_BLACK";

pub(super) fn enabled() -> anyhow::Result<bool> {
    match std::env::var(ENV) {
        Err(std::env::VarError::NotPresent) => Ok(false),
        Ok(value) if value == "0" => Ok(false),
        Ok(value) if value == "1" => Ok(true),
        _ => anyhow::bail!("{ENV} must be unset, 0, or 1"),
    }
}

#[cfg(test)]
mod tests {
    use super::enabled;
    use super::super::*;
    use std::fs::{self, OpenOptions};
    use std::io::Write;
    use strehl_core::noise::{PlaneNoise, Provenance};
    use strehl_raw::Region;

    // Same PyramidFrameSource -> BandWorker -> BandMerge -> native writer seam
    // commissioned by M194. Generate one small padded u16 frame at consumption.
    struct Source {
        negative: bool,
        calls: [AtomicUsize; 3],
    }
    impl PyramidFrameSource for Source {
        fn len(&self) -> usize { 3 }
        fn decode(&self, index: usize) -> Result<Frame> {
            ensure!(index < 3, "fixed smoke source index");
            self.calls[index].fetch_add(1, Ordering::SeqCst);
            let delta = [4_i32, 8, 12][index] * if self.negative { -1 } else { 1 };
            let (width, height, ax, ay, stride, rows) = (128, 96, 2, 4, 135, 103);
            let mut data = vec![65000_u16; stride * rows];
            for y in 0..height {
                for x in 0..width {
                    data[(ay + y) * stride + ax + x] = (512 + delta) as u16;
                }
            }
            Ok(Frame {
                data, stride, buffer_height: rows,
                active: Region { x: ax, y: ay, width, height },
                levels: Levels { black: 512.0, white: 15360.0 },
                iso: Some(160.0), wb_coeffs: [1.0, 1.0, 1.0, f32::NAN],
                xyz_to_cam_rgbe: [[0.0; 3]; 4], color_matrices: Vec::new(),
                camera: "signed-black operator smoke; not calibration".into(),
                path: PathBuf::from(format!("SIGNED-BLACK-NO-RAW-{index}.ARW")),
            })
        }
    }

    #[test]
    #[ignore = "root releases the two fixed small whole-path smoke invocations"]
    fn signed_cfa_whole_path_smoke() -> Result<()> {
        let signed = enabled()?;
        let arm = if signed { "signed" } else { "clamped" };
        let out = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../experiments/native-signed-black").canonicalize()?
            .join(format!("smoke-{arm}"));
        fs::create_dir(&out)?;
        let levels = Levels { black: 512.0, white: 15360.0 };
        let plane = PlaneNoise { gain_dn_per_e: 1.0, read_noise_e: 4.0, levels };
        let noise = NoiseModel::new([plane; 4], 160.0, Provenance::Fallback);
        assert_eq!(plane.variance(-8.0), plane.variance(0.0));
        let geom = PlaneGeometry { width: 64, height: 48 };
        let domain = PyramidDomain::whole(geom);
        let cfg = MergeConfig::default();
        let sizes = level_sizes(geom.width, geom.height, cfg.bands);
        let mut evidence = Vec::new();
        for negative in [true, false] {
            let source = Source { negative, calls: std::array::from_fn(|_| AtomicUsize::new(0)) };
            let mut worker = BandWorker::new(domain, cfg);
            let mut negative_inputs = 0_usize;
            for index in 0..3 {
                assert!(worker.fold(&source, index, levels, &noise, None, None)?);
                negative_inputs += worker.planes.iter().flatten().filter(|v| **v < 0.0).count();
                assert!(worker.var.iter().all(|v| v.is_finite() && *v >= 0.0));
                assert!(worker.beta.is_empty(), "no-map arm must retain existing white-beta path");
            }
            assert_eq!(source.calls.each_ref().map(|n| n.load(Ordering::SeqCst)), [1, 1, 1]);
            assert_eq!(negative_inputs > 0, signed && negative, "actual consumed signed population");
            let planes = worker.merge.finish(&mut Workspace::new(&sizes));
            let expected = if negative { if signed { -8.0 } else { 0.0 } } else { 8.0 };
            assert!(planes.iter().flatten().all(|v| (*v - expected).abs() <= 1e-4),
                    "constant signed value did not survive the actual pyramid/finish");
            let merged = Merged::Bands { domain, planes: &planes };
            for site in [CfaPlane::R, CfaPlane::G1, CfaPlane::G2, CfaPlane::B] {
                assert_eq!(merged.value(site, 0, levels.black), expected.max(0.0));
            }
            let label = if negative { "negative" } else { "nonnegative" };
            let tiff = out.join(format!("{label}.tiff"));
            write_merged(merged, levels, Some([1.0; 3]), None,
                image_out::OutputSpace::CameraLinear, true, Exposure::None, None, &tiff)?;
            evidence.push(serde_json::json!({
                "case": label, "source_calls": [1,1,1], "folds": 3,
                "negative_consumed_values": negative_inputs, "collapsed_constant": expected,
                "writer_boundary_value": expected.max(0.0), "tiff": tiff,
                "tiff_bytes": fs::metadata(&tiff)?.len(),
                "scope": "constant transport/writer smoke; no noise calibration or image-quality claim"
            }));
        }
        let raw = serde_json::to_vec(&serde_json::json!({
            "schema": "native-signed-black-smoke-v1", "signed": signed,
            "configured_bands": cfg.bands, "level_count": sizes.len(), "cases": evidence
        }))?;
        let mut file = OpenOptions::new().write(true).create_new(true).open(out.join("result.json"))?;
        file.write_all(&raw)?; file.write_all(b"\n")?;
        Ok(())
    }
}
