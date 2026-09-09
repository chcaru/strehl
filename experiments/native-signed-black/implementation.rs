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
    use super::super::*;
    use super::enabled;
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
        fn len(&self) -> usize {
            3
        }
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
                data,
                stride,
                buffer_height: rows,
                active: Region {
                    x: ax,
                    y: ay,
                    width,
                    height,
                },
                levels: Levels {
                    black: 512.0,
                    white: 15360.0,
                },
                iso: Some(160.0),
                wb_coeffs: [1.0, 1.0, 1.0, f32::NAN],
                xyz_to_cam_rgbe: [[0.0; 3]; 4],
                color_matrices: Vec::new(),
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
            .join("../../experiments/native-signed-black")
            .canonicalize()?
            .join(format!("smoke-{arm}"));
        fs::create_dir(&out)?;
        let levels = Levels {
            black: 512.0,
            white: 15360.0,
        };
        let plane = PlaneNoise {
            gain_dn_per_e: 1.0,
            read_noise_e: 4.0,
            levels,
        };
        let noise = NoiseModel::new([plane; 4], 160.0, Provenance::Fallback);
        assert_eq!(plane.variance(-8.0), plane.variance(0.0));
        let geom = PlaneGeometry {
            width: 64,
            height: 48,
        };
        let domain = PyramidDomain::whole(geom);
        let cfg = MergeConfig::default();
        let sizes = level_sizes(geom.width, geom.height, cfg.bands);
        let mut evidence = Vec::new();
        for negative in [true, false] {
            let source = Source {
                negative,
                calls: std::array::from_fn(|_| AtomicUsize::new(0)),
            };
            let mut worker = BandWorker::new(domain, cfg);
            let mut negative_inputs = 0_usize;
            for index in 0..3 {
                assert!(worker.fold(&source, index, levels, &noise, None, None)?);
                negative_inputs += worker.planes.iter().flatten().filter(|v| **v < 0.0).count();
                assert!(worker.var.iter().all(|v| v.is_finite() && *v >= 0.0));
                assert!(
                    worker.beta.is_empty(),
                    "no-map arm must retain existing white-beta path"
                );
            }
            assert_eq!(
                source.calls.each_ref().map(|n| n.load(Ordering::SeqCst)),
                [1, 1, 1]
            );
            assert_eq!(
                negative_inputs > 0,
                signed && negative,
                "actual consumed signed population"
            );
            let planes = worker.merge.finish(&mut Workspace::new(&sizes));
            let expected = if negative {
                if signed { -8.0 } else { 0.0 }
            } else {
                8.0
            };
            assert!(
                planes
                    .iter()
                    .flatten()
                    .all(|v| (*v - expected).abs() <= 1e-4),
                "constant signed value did not survive the actual pyramid/finish"
            );
            let merged = Merged::Bands {
                domain,
                planes: &planes,
            };
            for site in [CfaPlane::R, CfaPlane::G1, CfaPlane::G2, CfaPlane::B] {
                assert_eq!(merged.value(site, 0, levels.black), expected.max(0.0));
            }
            let label = if negative { "negative" } else { "nonnegative" };
            let tiff = out.join(format!("{label}.tiff"));
            write_merged(
                merged,
                levels,
                Some([1.0; 3]),
                None,
                image_out::OutputSpace::CameraLinear,
                true,
                Exposure::None,
                None,
                &tiff,
            )?;
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
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(out.join("result.json"))?;
        file.write_all(&raw)?;
        file.write_all(b"\n")?;
        Ok(())
    }

    const CW: usize = 64;
    const CH: usize = 48;
    const CASE_IDS: [&str; 4] = [
        "split-offset",
        "nonnegative-depth",
        "noisy-flat",
        "noisy-depth",
    ];

    // Fixed two-surface software fixture. Blur each complete surface before
    // composition; this is not an optical occlusion or sensor calibration model.
    fn latent(side: usize, x: usize, y: usize) -> i32 {
        let base = if side == 0 { 1 } else { 3 };
        if y < 20 {
            return base;
        }
        base + if side == 0 {
            12 * (((x / 4 + y / 4) % 2) as i32)
        } else {
            20 * (((x / 5 + y / 3) % 2) as i32)
        }
    }

    fn blurred(side: usize, frame: usize, x: usize, y: usize) -> i32 {
        let best = [1_usize, 3][side];
        let radius = frame.abs_diff(best) as isize;
        let mut sum = 0;
        let mut count = 0;
        for dy in -radius..=radius {
            for dx in -radius..=radius {
                let xx = (x as isize + dx).clamp(0, CW as isize - 1) as usize;
                let yy = (y as isize + dy).clamp(0, CH as isize - 1) as usize;
                sum += latent(side, xx, yy);
                count += 1;
            }
        }
        (sum + count / 2) / count
    }

    fn sign(x: usize, y: usize, site: usize, phase: usize) -> i32 {
        let mut z = (x as u32).wrapping_mul(0x9e3779b9)
            ^ (y as u32).wrapping_mul(0x85ebca6b)
            ^ (site as u32).wrapping_mul(0xc2b2ae35)
            ^ ((phase as u32) + 1).wrapping_mul(0x27d4eb2d);
        z ^= z >> 16;
        z = z.wrapping_mul(0x7feb352d);
        z ^= z >> 15;
        z = z.wrapping_mul(0x846ca68b);
        z ^= z >> 16;
        if z & 1 == 0 { -4 } else { 4 }
    }

    fn perturb(frame: usize, x: usize, y: usize, site: usize) -> i32 {
        match frame {
            0 => sign(x, y, site, 0),
            1 => -sign(x, y, site, 0),
            2 => sign(x, y, site, 1),
            3 => -sign(x, y, site, 1),
            4 => 0,
            _ => unreachable!(),
        }
    }

    fn hex(bytes: &[u8]) -> String {
        const DIGITS: &[u8; 16] = b"0123456789abcdef";
        let mut out = String::with_capacity(bytes.len() * 2);
        for b in bytes {
            out.push(DIGITS[(b >> 4) as usize] as char);
            out.push(DIGITS[(b & 15) as usize] as char);
        }
        out
    }

    fn file_ref(path: &Path) -> Result<serde_json::Value> {
        use sha2::{Digest, Sha256};
        let bytes = fs::read(path)?;
        ensure!(bytes.len() <= 256 * 1024, "fixed comparison file extent");
        Ok(serde_json::json!({
            "path": path, "bytes": bytes.len(),
            "sha256": hex(Sha256::digest(&bytes).as_ref())
        }))
    }

    fn values_summary<'a>(values: impl Iterator<Item = &'a f32>) -> serde_json::Value {
        let (mut min, mut max, mut sum, mut count, mut negative) =
            (f32::INFINITY, f32::NEG_INFINITY, 0.0_f64, 0_usize, 0_usize);
        for &v in values {
            assert!(v.is_finite(), "actual nonfinite comparison operand");
            min = min.min(v);
            max = max.max(v);
            sum += f64::from(v);
            count += 1;
            negative += usize::from(v < 0.0);
        }
        assert!(count > 0);
        serde_json::json!({
            "min": min, "max": max, "mean": sum / count as f64,
            "count": count, "negative_values": negative
        })
    }

    struct ComparisonSource {
        case: usize,
        calls: [AtomicUsize; 5],
        observations: std::sync::Mutex<Vec<serde_json::Value>>,
    }

    impl PyramidFrameSource for ComparisonSource {
        fn len(&self) -> usize {
            5
        }
        fn decode(&self, frame: usize) -> Result<Frame> {
            use sha2::{Digest, Sha256};
            ensure!(frame < 5 && self.case < 4, "fixed comparison source index");
            self.calls[frame].fetch_add(1, Ordering::SeqCst);
            let (ax, ay, stride, rows) = (2, 4, 2 * CW + 7, 2 * CH + 7);
            let mut data = vec![65000_u16; stride * rows];
            let mut digest = Sha256::new();
            let mut blur_error = [0_u64; 2];
            let mut raw_min = u16::MAX;
            let mut raw_max = 0_u16;
            for site in 0..4 {
                let (dx, dy) = [(0, 0), (1, 0), (0, 1), (1, 1)][site];
                for y in 0..CH {
                    for x in 0..CW {
                        let side = usize::from(x >= CW / 2);
                        let signal = match self.case {
                            0 => side as i32 + [-4, -2, 0, 2, 4][frame],
                            1 | 3 => {
                                let value = blurred(side, frame, x, y);
                                let error = i64::from(value - latent(side, x, y));
                                blur_error[side] += (error * error) as u64;
                                value
                                    + if self.case == 1 {
                                        64
                                    } else {
                                        perturb(frame, x, y, site)
                                    }
                            }
                            2 => perturb(frame, x, y, site),
                            _ => unreachable!(),
                        };
                        assert!(
                            (-512..=14848).contains(&signal),
                            "fixture representable in raw u16"
                        );
                        let raw = (512 + signal) as u16;
                        data[(ay + 2 * y + dy) * stride + ax + 2 * x + dx] = raw;
                        digest.update(raw.to_le_bytes());
                        raw_min = raw_min.min(raw);
                        raw_max = raw_max.max(raw);
                    }
                }
            }
            self.observations.lock().unwrap().push(serde_json::json!({
                "frame": frame, "raw_min": raw_min, "raw_max": raw_max,
                "active_u16_sha256": hex(digest.finalize().as_ref()),
                "hash_layout": "plane-major R G1 G2 B, row-major u16LE, active sites only",
                "blur_squared_error_by_surface": blur_error
            }));
            Ok(Frame {
                data,
                stride,
                buffer_height: rows,
                active: Region {
                    x: ax,
                    y: ay,
                    width: 2 * CW,
                    height: 2 * CH,
                },
                levels: Levels {
                    black: 512.0,
                    white: 15360.0,
                },
                iso: Some(160.0),
                wb_coeffs: [1.0, 1.0, 1.0, f32::NAN],
                xyz_to_cam_rgbe: [[0.0; 3]; 4],
                color_matrices: Vec::new(),
                camera: "signed-black fixed software comparison; not calibration".into(),
                path: PathBuf::from(format!("SIGNED-BLACK-NO-RAW-{}-{frame}.ARW", self.case)),
            })
        }
    }

    #[test]
    #[ignore = "root releases clamped/signed once each; four additional consumer cases per invocation"]
    fn signed_cfa_comparison() -> Result<()> {
        let signed = enabled()?;
        let arm = if signed { "signed" } else { "clamped" };
        let out = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../experiments/native-signed-black")
            .canonicalize()?
            .join(format!("comparison-{arm}"));
        fs::create_dir(&out)?;
        let levels = Levels {
            black: 512.0,
            white: 15360.0,
        };
        let plane = PlaneNoise {
            gain_dn_per_e: 1.0,
            read_noise_e: 4.0,
            levels,
        };
        let noise = NoiseModel::new([plane; 4], 160.0, Provenance::Fallback);
        assert_eq!(plane.variance(-8.0), plane.variance(0.0));
        let geom = PlaneGeometry {
            width: CW,
            height: CH,
        };
        let domain = PyramidDomain::whole(geom);
        let cfg = MergeConfig::default();
        let sizes = level_sizes(CW, CH, cfg.bands);
        let mut evidence = Vec::new();
        for (case, id) in CASE_IDS.iter().enumerate() {
            let source = ComparisonSource {
                case,
                calls: std::array::from_fn(|_| AtomicUsize::new(0)),
                observations: std::sync::Mutex::new(Vec::new()),
            };
            let mut worker = BandWorker::new(domain, cfg);
            let mut folds = Vec::new();
            let mut negatives = 0;
            for index in 0..5 {
                assert!(worker.fold(&source, index, levels, &noise, None, None)?);
                let negative = worker.planes.iter().flatten().filter(|v| **v < 0.0).count();
                negatives += negative;
                assert!(worker.beta.is_empty(), "no-map existing white-beta path");
                assert!(worker.var.iter().all(|v| v.is_finite() && *v >= 0.0));
                folds.push(serde_json::json!({
                    "index": index, "negative_values": negative,
                    "consumed": values_summary(worker.planes.iter().flatten()),
                    "variance": values_summary(worker.var.iter()),
                    "beta_prefix": worker.beta,
                    "averaged_fraction": worker.merge.averaged_fraction()
                }));
            }
            let source_calls = source.calls.each_ref().map(|n| n.load(Ordering::SeqCst));
            assert_eq!(source_calls, [1; 5]);
            assert_eq!(
                negatives > 0,
                signed && case != 1,
                "actual signed fixture population"
            );
            let observed = source.observations.into_inner().unwrap();
            assert_eq!(observed.len(), 5);
            if case == 1 || case == 3 {
                for (frame, row) in observed.iter().enumerate() {
                    assert_eq!(row["frame"].as_u64().unwrap(), frame as u64);
                    for side in 0..2 {
                        let error = row["blur_squared_error_by_surface"][side].as_u64().unwrap();
                        assert_eq!(
                            error == 0,
                            frame == [1, 3][side],
                            "actual distinct best-focus population"
                        );
                    }
                }
                assert_ne!(
                    observed[1]["active_u16_sha256"],
                    observed[3]["active_u16_sha256"]
                );
            }
            let planes = worker.merge.finish(&mut Workspace::new(&sizes));
            assert_eq!(planes.len(), 4);
            assert!(planes.iter().all(|p| p.len() == CW * CH));
            let actual = values_summary(planes.iter().flatten());
            let collapsed_path = out.join(format!("{id}.f32"));
            let mut f = OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&collapsed_path)?;
            for v in planes.iter().flatten() {
                f.write_all(&v.to_le_bytes())?;
            }
            f.flush()?;
            drop(f);
            let mut collapsed = file_ref(&collapsed_path)?;
            for (k, v) in actual.as_object().unwrap() {
                collapsed[k] = v.clone();
            }
            let tiff = out.join(format!("{id}.tiff"));
            write_merged(
                Merged::Bands {
                    domain,
                    planes: &planes,
                },
                levels,
                Some([1.0; 3]),
                None,
                image_out::OutputSpace::CameraLinear,
                true,
                Exposure::None,
                None,
                &tiff,
            )?;
            evidence.push(serde_json::json!({
                "id": id, "source_calls": source_calls, "folds": 5,
                "negative_consumed_values": negatives, "folds_observed": folds,
                "collapsed": collapsed, "tiff": file_ref(&tiff)?,
                "fixture": { "best_frames": [1,3], "frames": observed },
                "scope": "actual operator/output evidence; independent fidelity scoring required"
            }));
        }
        let raw = serde_json::to_vec_pretty(&serde_json::json!({
            "schema": "native-signed-black-comparison-v1", "signed": signed,
            "geometry": { "width": CW, "height": CH }, "cfa_order": ["R","G1","G2","B"],
            "levels": { "black": levels.black, "white": levels.white },
            "configured_bands": cfg.bands,
            "level_sizes": sizes.iter().map(|s| [s.width,s.height]).collect::<Vec<_>>(),
            "noise": { "gain_dn_per_e": 1.0, "read_noise_e": 4.0, "iso": 160.0,
                "scope": "fixed injected smoke model; deterministic anticorrelated perturbations are not sensor calibration" },
            "recipe": {
                "split_x": 32, "flat_y": [0,20], "best_frames": [1,3],
                "left": "1+12*((x/4+y/4)%2); y<20 overrides to1",
                "right": "3+20*((x/5+y/3)%2); y<20 overrides to3",
                "blur": "each full surface first; radius=abs(frame-best); clamp-edge square box; (sum+count/2)/count integer rounding; then compose atx32",
                "split_offset": "left0/right1 plus frame offsets[-4,-2,0,2,4]",
                "nonnegative_depth": "blurred composite plus64; no perturbation",
                "noisy_flat": "zero plus perturbation",
                "noisy_depth": "blurred composite plus perturbation",
                "perturbation": "[s,-s,t,-t,0], each sign +/-4; exact wrapping-u32 sign() in source, x/y/CFA/phase domains",
                "producer_masks": {
                    "flat": [[8,24,8,16],[40,56,8,16]],
                    "texture": [[8,24,24,40],[40,56,24,40]],
                    "boundary": [[28,36,8,40]]
                },
                "mask_coordinates": "half-open [x0,x1,y0,y1] on CFA plane grid",
                "scope": "two-surface software plant; no physical occlusion, noise calibration or SOTA claim"
            },
            "cases": evidence
        }))?;
        ensure!(raw.len() < 128 * 1024, "fixed result extent");
        let mut f = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(out.join("result.json"))?;
        f.write_all(&raw)?;
        f.write_all(b"\n")?;
        Ok(())
    }
}
