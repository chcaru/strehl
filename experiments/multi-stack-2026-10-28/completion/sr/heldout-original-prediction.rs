//! Original-sensel cross validation for an already prepared, bounded pilot.
//! Both estimators omit the scored acquisition. Focus/motion remain adaptive
//! fields computed earlier; these scores are conditional, not independent SNR.
use super::*;
use strehl_core::demosaic::{Mosaic, demosaic_malvar_row};
use strehl_core::plane::QuadSource;

fn interpolate_field(inputs: &Inputs, p: [f64; 2]) -> Option<([usize; 4], [f32; 4])> {
    let l = inputs.lattice;
    let q = [
        (p[0] - l.origin_sensor[0]) / l.step_sensor[0],
        (p[1] - l.origin_sensor[1]) / l.step_sensor[1],
    ];
    if q.iter().any(|v| !v.is_finite() || *v < 0.) {
        return None;
    }
    let (x, y) = (q[0].floor() as usize, q[1].floor() as usize);
    if x + 1 >= l.width || y + 1 >= l.height {
        return None;
    }
    let dx = (q[0] - x as f64) as f32;
    let dy = (q[1] - y as f64) as f32;
    Some((
        [
            y * l.width + x,
            y * l.width + x + 1,
            (y + 1) * l.width + x,
            (y + 1) * l.width + x + 1,
        ],
        [
            (1. - dx) * (1. - dy),
            dx * (1. - dy),
            (1. - dx) * dy,
            dx * dy,
        ],
    ))
}
fn weighted_rgb(values: &[[f32; 3]], indices: [usize; 4], weights: [f32; 4]) -> [f32; 3] {
    std::array::from_fn(|c| (0..4).map(|k| weights[k] * values[indices[k]][c]).sum())
}
/// Same-color bilinear interpolation, complete nonzero original-tap support.
/// This is the intentionally resampled no-SR arm, not the direct candidate.
fn bilinear_original(
    src: &SourceView<'_>,
    full: PlaneGeometry,
    anchor: [f64; 2],
    plane: usize,
) -> Option<f32> {
    let color = match plane {
        0 => 0,
        2 => 2,
        _ => 1,
    };
    let site = match plane {
        0 => [0., 0.],
        1 => [1., 0.],
        2 => [1., 1.],
        _ => [0., 1.],
    };
    let s = sensor_pull(src.source_pull[color], full, anchor);
    let q = [(s[0] - site[0]) * 0.5, (s[1] - site[1]) * 0.5];
    if q.iter().any(|v| !v.is_finite()) {
        return None;
    }
    let x = q[0].floor() as isize;
    let y = q[1].floor() as isize;
    let dx = (q[0] - x as f64) as f32;
    let dy = (q[1] - y as f64) as f32;
    let mut value = 0.;
    for (ox, oy, w) in [
        (0, 0, (1. - dx) * (1. - dy)),
        (1, 0, dx * (1. - dy)),
        (0, 1, (1. - dx) * dy),
        (1, 1, dx * dy),
    ] {
        if w == 0. {
            continue;
        }
        let (sx, sy) = (x + ox, y + oy);
        if sx < 0 || sy < 0 || sx >= full.width as isize || sy >= full.height as isize {
            return None;
        }
        let (r0, r1) = src.source.quad_rows(sy as usize);
        let row = if site[1] == 0. { r0 } else { r1 };
        let at = 2 * sx as usize + site[0] as usize;
        if at >= row.len() {
            return None;
        }
        let raw = f32::from(row[at]);
        let noise = src.noise[plane];
        if raw >= noise.levels.white {
            return None;
        }
        value += w * (raw - noise.levels.black) * src.gain;
    }
    Some(value)
}
/// Merge one tiny final CFA mosaic, then MHC exactly once. Same acquisitions,
/// point-frozen admission and calibrated exposure as the direct candidate.
/// No source is demosaiced and no aligned image volume is materialized.
fn matched_mhc(
    full: PlaneGeometry,
    p: [f64; 2],
    sources: &[SourceView<'_>],
    expected: [f32; 3],
    wb: [f32; 3],
) -> Option<[f32; 3]> {
    let origin = [
        (p[0].floor() as isize - 4).div_euclid(2) * 2,
        (p[1].floor() as isize - 4).div_euclid(2) * 2,
    ];
    if origin.iter().any(|v| *v < 0) {
        return None;
    }
    let mut data = [0f32; 100];
    for y in 0..10 {
        for x in 0..10 {
            let plane = match (x % 2, y % 2) {
                (0, 0) => 0,
                (1, 0) => 1,
                (1, 1) => 2,
                _ => 3,
            };
            let color = match plane {
                0 => 0,
                2 => 2,
                _ => 1,
            };
            let mut sum = 0.;
            let mut total = 0.;
            for source in sources {
                let a = source.admission;
                if !a.valid[0]
                    || a.focus[0] < (-0.5f32).exp()
                    || a.motion[0] <= 0.
                    || a.registration_sigma_sensor[0] > 0.15
                {
                    continue;
                }
                let value = bilinear_original(
                    source,
                    full,
                    [
                        (origin[0] + x as isize) as f64,
                        (origin[1] + y as isize) as f64,
                    ],
                    plane,
                )?;
                let variance = (source.noise[plane].variance(expected[color] / source.gain)
                    * source.gain
                    * source.gain)
                    .max(1e-6);
                let w = a.focus[0] * a.motion[0] / variance;
                sum += w * value;
                total += w;
            }
            if total <= 0. {
                return None;
            }
            data[y * 10 + x] = sum / total * wb[color];
        }
    }
    let q = [p[0] - origin[0] as f64, p[1] - origin[1] as f64];
    let x = q[0].floor() as usize;
    let y = q[1].floor() as usize;
    if x < 2 || y < 2 || x + 3 >= 10 || y + 3 >= 10 {
        return None;
    }
    let dx = (q[0] - x as f64) as f32;
    let dy = (q[1] - y as f64) as f32;
    let mosaic = Mosaic {
        data: &data,
        width: 10,
        height: 10,
    };
    let mut a = [0.; 30];
    let mut b = [0.; 30];
    demosaic_malvar_row(&mosaic, y, &mut a);
    demosaic_malvar_row(&mosaic, y + 1, &mut b);
    Some(std::array::from_fn(|c| {
        ((1. - dy) * ((1. - dx) * a[3 * x + c] + dx * a[3 * (x + 1) + c])
            + dy * ((1. - dx) * b[3 * x + c] + dx * b[3 * (x + 1) + c]))
            / wb[c]
    }))
}

/// Whole-ROI causal comparator at the direct candidate's coherent support.
/// Same target acquisitions and point-frozen admission, bilinear original CFA
/// gather into a tiny final mosaic, then MHC once. No held-out truth claim.
pub(super) fn matched_roi(
    inputs: &Inputs,
    support: &[bool],
    wb: [f32; 3],
) -> Vec<Option<[f32; 3]>> {
    support
        .par_iter()
        .enumerate()
        .map(|(p, valid)| {
            if !*valid {
                return None;
            }
            let views: Vec<_> = inputs
                .originals
                .iter()
                .zip(&inputs.fields)
                .enumerate()
                .map(|(s, (source, a))| SourceView {
                    acquisition_id: inputs.acquisitions[s] as u64,
                    source: source.as_ref(),
                    source_pull: inputs.pulls[s],
                    noise: inputs.noise,
                    gain: inputs.gains[s],
                    admission: Admission {
                        focus: &a.focus[p..p + 1],
                        motion: &a.motion[p..p + 1],
                        valid: &a.valid[p..p + 1],
                        registration_sigma_sensor: &a.sigma[p..p + 1],
                    },
                })
                .collect();
            matched_mhc(
                inputs.lattice.full,
                inputs
                    .lattice
                    .position(p % inputs.lattice.width, p / inputs.lattice.width),
                &views,
                inputs.expected[p],
                wb,
            )
        })
        .collect()
}

fn prediction_withheld_indices(count: usize) -> Result<Vec<usize>> {
    ensure!(
        (4..=14).contains(&count),
        "prediction source count outside bounded pilot"
    );
    Ok([3usize, 10].into_iter().filter(|&i| i < count).collect())
}

pub(super) fn evaluate(inputs: &Inputs, wb: [f32; 3]) -> Result<Value> {
    ensure!(
        wb.iter().all(|v| v.is_finite() && *v > 0.),
        "invalid prediction WB"
    );
    let mut observations = Vec::new();
    let mut attempted = [0usize; 3];
    let mut reconstructed = [0usize; 3];
    let withheld_indices = prediction_withheld_indices(inputs.originals.len())?;
    for &withheld in &withheld_indices {
        let full = inputs.lattice.full;
        for oy in (8..inputs.lattice.height - 8).step_by(8) {
            for ox in (8..inputs.lattice.width - 8).step_by(8) {
                let nominal = inputs.lattice.position(ox, oy);
                for plane in 0..4 {
                    let color = match plane {
                        0 => 0,
                        2 => 2,
                        _ => 1,
                    };
                    let site = match plane {
                        0 => [0usize, 0usize],
                        1 => [1, 0],
                        2 => [1, 1],
                        _ => [0, 1],
                    };
                    let s = sensor_pull(inputs.pulls[withheld][color], full, nominal);
                    if s.iter().any(|v| !v.is_finite() || *v < 2.) {
                        continue;
                    }
                    let sx = 2 * ((s[0] - site[0] as f64) * 0.5).round() as usize + site[0];
                    let sy = 2 * ((s[1] - site[1] as f64) * 0.5).round() as usize + site[1];
                    if sx >= 2 * full.width || sy >= 2 * full.height {
                        continue;
                    }
                    let inverse = inputs.pulls[withheld][color]
                        .invert()
                        .context("singular prediction pull")?;
                    let p = sensor_pull(inverse, full, [sx as f64, sy as f64]);
                    let Some((indices, weights)) = interpolate_field(inputs, p) else {
                        continue;
                    };
                    if indices.iter().any(|i| !inputs.fallback_valid[*i]) {
                        continue;
                    }
                    let (a, b) = inputs.originals[withheld].quad_rows(sy / 2);
                    let code = if sy % 2 == 0 { a[sx] } else { b[sx] };
                    if f32::from(code) >= inputs.noise[plane].levels.white {
                        continue;
                    }
                    attempted[color] += 1;
                    let expected = [weighted_rgb(&inputs.expected, indices, weights)];
                    let tensor = [weighted_rgb(&inputs.tensor, indices, weights)];
                    let fallback = [weighted_rgb(&inputs.fallback, indices, weights)];
                    let fields: Vec<_> = inputs
                        .fields
                        .iter()
                        .map(|f| OwnedAdmission {
                            focus: vec![indices.iter().map(|i| f.focus[*i]).fold(1., f32::min)],
                            motion: vec![indices.iter().map(|i| f.motion[*i]).fold(1., f32::min)],
                            sigma: vec![indices.iter().map(|i| f.sigma[*i]).fold(0., f32::max)],
                            valid: vec![indices.iter().all(|i| f.valid[*i])],
                        })
                        .collect();
                    let sources: Vec<_> = inputs
                        .originals
                        .iter()
                        .enumerate()
                        .filter(|(i, _)| *i != withheld)
                        .map(|(i, source)| SourceView {
                            acquisition_id: inputs.acquisitions[i] as u64,
                            source: source.as_ref(),
                            source_pull: inputs.pulls[i],
                            noise: inputs.noise,
                            gain: inputs.gains[i],
                            admission: Admission {
                                focus: &fields[i].focus,
                                motion: &fields[i].motion,
                                valid: &fields[i].valid,
                                registration_sigma_sensor: &fields[i].sigma,
                            },
                        })
                        .collect();
                    let result = reconstruct_tile(
                        OutputLattice {
                            origin_sensor: p,
                            width: 1,
                            height: 1,
                            ..inputs.lattice
                        },
                        &sources,
                        FrozenGuide {
                            expected_rgb: &expected,
                            tensor: &tensor,
                            fallback_rgb: &fallback,
                            fallback_variance: None,
                            fallback_valid: &[true],
                        },
                        inputs.config,
                    )
                    .map_err(err)?;
                    if !result.reason[0].iter().all(|r| *r == Reason::Reconstructed) {
                        continue;
                    }
                    let Some(null_prediction) = matched_mhc(full, p, &sources, expected[0], wb)
                    else {
                        continue;
                    };
                    reconstructed[color] += 1;
                    let measured = (f32::from(code) - inputs.noise[plane].levels.black)
                        * inputs.gains[withheld];
                    observations.push(json!({"withheld_acquisition":inputs.acquisitions[withheld],"original_sensor":[sx,sy],"anchor_sensor":p,"cfa_plane":plane,"color":color,"spatial_block":[ox/32,oy/32],"original_black_subtracted_dn":measured,"direct_prediction_dn":result.rgb[0][color],"matched_resampled_mhc_prediction_dn":null_prediction[color],"dependent_native_prediction_dn":fallback[0][color],"direct_conditional_variance":result.variance[0][color],"withheld_model_variance":inputs.noise[plane].variance(expected[0][color]/inputs.gains[withheld])*inputs.gains[withheld]*inputs.gains[withheld],"withheld_gain":inputs.gains[withheld],"phase_condition":result.phase_condition[0],"independent_acquisitions":result.independent_acquisitions[0]}));
                }
            }
        }
    }
    Ok(
        json!({"schema":"strehl.sr-heldout-original-prediction.v1","source_sha256":hex(&Sha256::digest(include_bytes!("heldout-original-prediction.rs"))),"withheld_acquisitions":withheld_indices.iter().map(|&i| inputs.acquisitions[i]).collect::<Vec<_>>(),"attempted_by_color":attempted,"common_coherent_predictions_by_color":reconstructed,"observations":observations,"interpretation":"Scored original acquisition is absent from both estimators. The same remaining acquisitions and point-frozen focus/motion gates feed direct original-CFA regression and bilinear-CFA-merge plus one MHC null. The native master contains the scored acquisition and is an optimistic dependent comparator. Focus, motion and global geometry retain adaptive/shared-photon dependence; these are conditional raw prediction errors, not a calibrated unconditional noise or photographic-quality claim.","null_limitations":"Bilinear CFA and MHC have a wider spatial footprint; null variance is not reported as if samples were independent. The guide predicts a locally constant shot variance. Only common coherent support is compared; attempted and retained counts are explicit."}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn prediction_centers_preserve_union_and_fit_single_neighborhood() {
        assert_eq!(prediction_withheld_indices(14).unwrap(), vec![3, 10]);
        assert_eq!(prediction_withheld_indices(7).unwrap(), vec![3]);
        assert_eq!(prediction_withheld_indices(4).unwrap(), vec![3]);
        assert!(prediction_withheld_indices(3).is_err());
        assert!(prediction_withheld_indices(15).is_err());
    }
    use strehl_core::align::Cx;
    struct Raw {
        pixels: Vec<u16>,
    }
    impl QuadSource for Raw {
        fn geometry(&self) -> PlaneGeometry {
            PlaneGeometry {
                width: 32,
                height: 32,
            }
        }
        fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
            let i = 2 * y * 64;
            (&self.pixels[i..i + 64], &self.pixels[i + 64..i + 128])
        }
    }
    fn noise() -> [PlaneNoise; 4] {
        [PlaneNoise {
            gain_dn_per_e: 0.01,
            read_noise_e: 1.,
            levels: Levels {
                black: 512.,
                white: 15360.,
            },
        }; 4]
    }
    fn maps() -> Vec<Similarity> {
        (0..4)
            .flat_map(|x| {
                (0..4).map(move |y| Similarity {
                    a: Cx::new(1., 0.),
                    b: Cx::new(x as f64 * 0.25, y as f64 * 0.25),
                })
            })
            .collect()
    }
    fn raws(maps: &[Similarity], scene: &dyn Fn([f64; 2]) -> [f32; 3]) -> Vec<Raw> {
        maps.iter()
            .map(|t| {
                let pixels = (0..64 * 64)
                    .map(|i| {
                        let x = i % 64;
                        let y = i / 64;
                        let c = match (x % 2, y % 2) {
                            (0, 0) => 0,
                            (1, 1) => 2,
                            _ => 1,
                        };
                        // Independent translation oracle; no production coordinate helper.
                        let p = [x as f64 - 2. * t.b.re, y as f64 - 2. * t.b.im];
                        (512. + scene(p)[c]).round().clamp(0., 65535.) as u16
                    })
                    .collect();
                Raw { pixels }
            })
            .collect()
    }
    fn views<'a>(raws: &'a [Raw], maps: &[Similarity]) -> Vec<SourceView<'a>> {
        raws.iter()
            .enumerate()
            .map(|(i, r)| SourceView {
                acquisition_id: i as u64,
                source: r,
                source_pull: [maps[i]; 3],
                noise: noise(),
                gain: 1.,
                admission: Admission {
                    focus: &[1.],
                    motion: &[1.],
                    valid: &[true],
                    registration_sigma_sensor: &[0.],
                },
            })
            .collect()
    }
    #[test]
    fn a01_matched_mhc_preserves_flat_and_linear_color_with_wb_before_demosaic() {
        let maps = maps();
        let scenes: [&dyn Fn([f64; 2]) -> [f32; 3]; 2] = [&|_| [3000., 4000., 5000.], &|p| {
            let x = (p[0] - 32.) as f32;
            let y = (p[1] - 32.) as f32;
            [
                3000. + 30. * x - 10. * y,
                4000. - 20. * x + 15. * y,
                5000. + 10. * x + 20. * y,
            ]
        }];
        for scene in scenes {
            let raw = raws(&maps, scene);
            let sources = views(&raw, &maps);
            for p in [[28., 30.], [31.25, 33.75], [34.5, 32.25]] {
                let expected = scene(p);
                let got =
                    matched_mhc(raw[0].geometry(), p, &sources, expected, [2.4, 1., 1.7]).unwrap();
                for c in 0..3 {
                    assert!(
                        (got[c] - expected[c]).abs() < 0.8,
                        "p{p:?} c{c}: got{} expected{}",
                        got[c],
                        expected[c]
                    );
                }
            }
        }
    }
    #[test]
    fn b01_same_count_original_cfa_has_colored_alias_positive_against_one_mhc_null() {
        let scene = |p: [f64; 2]| {
            [(0.35, 0.11), (0.21, 0.23), (0.13, 0.34)].map(|(fx, fy)| {
                let sinc = |v: f64| (std::f64::consts::PI * v).sin() / (std::f64::consts::PI * v);
                (4000.
                    + 1500.
                        * sinc(fx)
                        * sinc(fy)
                        * (std::f64::consts::TAU * (fx * p[0] + fy * p[1])).sin())
                    as f32
            })
        };
        let maps = maps();
        let raw = raws(&maps, &scene);
        let sources = views(&raw, &maps);
        let full = raw[0].geometry();
        for model in [RegressionModel::LocalConstant, RegressionModel::LocalAffine] {
            let mut direct_error = [0f64; 3];
            let mut null_error = [0f64; 3];
            for y in 0..8 {
                for x in 0..8 {
                    let p = [22.25 + x as f64, 22.75 + y as f64];
                    let truth = scene(p);
                    let null = matched_mhc(full, p, &sources, [4000.; 3], [2.4, 1., 1.7]).unwrap();
                    let got = reconstruct_tile(
                        OutputLattice {
                            full,
                            origin_sensor: p,
                            step_sensor: [1.; 2],
                            width: 1,
                            height: 1,
                        },
                        &sources,
                        FrozenGuide {
                            expected_rgb: &[[4000.; 3]],
                            tensor: &[[0.; 3]],
                            fallback_rgb: &[null],
                            fallback_variance: None,
                            fallback_valid: &[true],
                        },
                        Config {
                            model,
                            ..Config::default()
                        },
                    )
                    .unwrap();
                    assert!(
                        got.reason[0].iter().all(|r| *r == Reason::Reconstructed),
                        "{model:?}: {:?}",
                        got.reason
                    );
                    for c in 0..3 {
                        direct_error[c] += f64::from(got.rgb[0][c] - truth[c]).powi(2);
                        null_error[c] += f64::from(null[c] - truth[c]).powi(2);
                    }
                }
            }
            for c in [0, 2] {
                assert!(
                    direct_error[c] < 0.6 * null_error[c],
                    "{model:?} color{c}: direct{} null{}",
                    direct_error[c],
                    null_error[c]
                );
            }
        }
    }
    #[test]
    fn c01_matched_mhc_refuses_original_clipped_tap_instead_of_using_zero() {
        let maps = maps();
        let mut raw = raws(&maps, &|_| [3000.; 3]);
        raw[0].pixels[32 * 64 + 32] = 15360;
        let sources = views(&raw, &maps);
        assert!(
            matched_mhc(
                raw[0].geometry(),
                [32., 32.],
                &sources,
                [3000.; 3],
                [2.4, 1., 1.7]
            )
            .is_none()
        );
    }
    #[test]
    fn a02_matched_null_respects_output_exposure_units_before_wb() {
        let maps = maps();
        let raw = raws(&maps, &|_| [1500., 2000., 2500.]);
        let mut sources = views(&raw, &maps);
        for source in &mut sources {
            source.gain = 2.;
        }
        let got = matched_mhc(
            raw[0].geometry(),
            [31.25, 32.75],
            &sources,
            [3000., 4000., 5000.],
            [2.4, 1., 1.7],
        )
        .unwrap();
        for (c, expected) in [3000., 4000., 5000.].into_iter().enumerate() {
            assert!((got[c] - expected).abs() < 0.01);
        }
    }
}
