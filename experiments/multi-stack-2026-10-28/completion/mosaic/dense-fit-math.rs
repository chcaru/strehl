//! Correlated training rows with declared component mass, never new certificates.
use super::*;
use std::collections::BTreeMap;
use strehl_core::mosaic::{
    BackwardMesh, Correspondence, FocusEvidence, ForwardMesh, IndexLimits, MappedPoint,
    MeshFitOptions, MeshValidation, ObservationRole, Visibility, fit_meshes,
};

#[derive(Clone, Debug)]
pub struct Row {
    pub id: String,
    pub a: [f64; 2],
    pub b: [f64; 2],
    pub bounds: [[[f64; 2]; 2]; 2],
    pub priority: f64,
}
pub fn overlap(a: &Row, b: &Row) -> bool {
    (0..2).any(|p| {
        a.bounds[p][0][0] <= b.bounds[p][1][0]
            && b.bounds[p][0][0] <= a.bounds[p][1][0]
            && a.bounds[p][0][1] <= b.bounds[p][1][1]
            && b.bounds[p][0][1] <= a.bounds[p][1][1]
    })
}
pub fn fold(row: &Row) -> usize {
    (3 * (row.a[0] / 512.).floor() as usize + (row.a[1] / 512.).floor() as usize) % 5
}
pub fn split(rows: &[Row], held: usize) -> (Vec<Row>, Vec<Row>, Vec<String>) {
    let test: Vec<_> = rows.iter().filter(|r| fold(r) == held).cloned().collect();
    let mut purged = Vec::new();
    let train = rows
        .iter()
        .filter(|r| fold(r) != held)
        .filter(|r| {
            let safe = !test.iter().any(|t| overlap(r, t));
            if !safe {
                purged.push(r.id.clone());
            }
            safe
        })
        .cloned()
        .collect();
    (train, test, purged)
}
pub fn coherent(rows: &[Row]) -> (Vec<Row>, Vec<Value>) {
    let mut groups: BTreeMap<[u64; 2], Vec<usize>> = BTreeMap::new();
    for (i, r) in rows.iter().enumerate() {
        groups.entry(r.a.map(f64::to_bits)).or_default().push(i);
    }
    let mut output = Vec::new();
    let mut receipts = Vec::new();
    for ids in groups.values() {
        let pass = ids.iter().all(|&i| {
            ids.iter()
                .all(|&j| (rows[i].b[0] - rows[j].b[0]).hypot(rows[i].b[1] - rows[j].b[1]) <= 0.5)
        });
        receipts.push(json!({"ids":ids.iter().map(|&i|&rows[i].id).collect::<Vec<_>>(),"coherent":pass,"representative":pass.then_some(&rows[ids[0]].id)}));
        if pass {
            output.push(rows[ids[0]].clone());
        }
    }
    (output, receipts)
}
fn root(parent: &mut [usize], i: usize) -> usize {
    if parent[i] != i {
        parent[i] = root(parent, parent[i]);
    }
    parent[i]
}
pub fn weights(rows: &[Row]) -> (Vec<f64>, usize, Vec<Value>) {
    let mut parent: Vec<_> = (0..rows.len()).collect();
    for i in 0..rows.len() {
        for j in 0..i {
            if overlap(&rows[i], &rows[j]) {
                let a = root(&mut parent, i);
                let b = root(&mut parent, j);
                parent[a] = b;
            }
        }
    }
    let mut groups: BTreeMap<usize, Vec<usize>> = BTreeMap::new();
    for i in 0..rows.len() {
        groups.entry(root(&mut parent, i)).or_default().push(i);
    }
    let mut w = vec![0.; rows.len()];
    let mut total = 0;
    let mut receipts = Vec::new();
    for ids in groups.values() {
        let mut order = ids.clone();
        order.sort_by(|&a, &b| {
            rows[a]
                .priority
                .total_cmp(&rows[b].priority)
                .then(a.cmp(&b))
        });
        let mut keep = Vec::new();
        for i in order {
            if !keep.iter().any(|&j| overlap(&rows[i], &rows[j])) {
                keep.push(i);
            }
        }
        total += keep.len();
        let mass = keep.len() as f64 / ids.len() as f64;
        for &i in ids {
            w[i] = mass;
        }
        receipts.push(json!({"row_ids":ids.iter().map(|&i|&rows[i].id).collect::<Vec<_>>(),"greedy_nonoverlap_ids":keep.iter().map(|&i|&rows[i].id).collect::<Vec<_>>(),"total_declared_weight":keep.len(),"per_row_weight":mass}));
    }
    (w, total, receipts)
}
pub struct Training {
    pub rows: Vec<Row>,
    pub weights: Vec<f64>,
    pub independent: usize,
    pub receipt: Value,
}
pub fn training(rows: &[Row]) -> Result<Training> {
    let (rows, groups) = coherent(rows);
    let (w, n, cohorts) = weights(&rows);
    ensure!(n >= 8, "fewer than eight independent training sites");
    Ok(Training {
        rows,
        weights: w,
        independent: n,
        receipt: json!({"source_alternative_groups":groups,"overlap_components":cohorts,"declared_independent_sites":n,"semantics":"declared total-weight normalization, not covariance or statistical effective sample size"}),
    })
}

pub fn seed(train: &Training, g: strehl_core::plane::PlaneGeometry) -> Result<Similarity> {
    let mass: f64 = train.weights.iter().sum();
    ensure!(mass > 0., "empty weighted seed");
    let mut a = [0.; 2];
    let mut b = [0.; 2];
    for (r, &w) in train.rows.iter().zip(&train.weights) {
        for k in 0..2 {
            a[k] += r.a[k] * w / mass;
            b[k] += r.b[k] * w / mass;
        }
    }
    let (mut real, mut imag, mut denominator) = (0., 0., 0.);
    for (r, &w) in train.rows.iter().zip(&train.weights) {
        let x = [r.a[0] - a[0], r.a[1] - a[1]];
        let y = [r.b[0] - b[0], r.b[1] - b[1]];
        real += w * (x[0] * y[0] + x[1] * y[1]);
        imag += w * (x[0] * y[1] - x[1] * y[0]);
        denominator += w * (x[0] * x[0] + x[1] * x[1]);
    }
    ensure!(denominator > 1e-12, "singular training similarity");
    real /= denominator;
    imag /= denominator;
    ensure!(
        (0.5..=2.).contains(&real.hypot(imag)),
        "training seed outside declared scale range"
    );
    let center = [g.width as f64 * 0.5, g.height as f64 * 0.5];
    let p = [a[0] - center[0], a[1] - center[1]];
    Ok(Similarity {
        a: strehl_core::align::Cx::new(real, imag),
        b: strehl_core::align::Cx::new(
            b[0] - center[0] - real * p[0] + imag * p[1],
            b[1] - center[1] - imag * p[0] - real * p[1],
        ),
    })
}
fn meshes(
    guides: &[MosaicGuide],
    transform: Similarity,
    spacing: usize,
) -> Result<Vec<ForwardMesh>> {
    let mut result = Vec::new();
    let inverse = transform.invert().context("singular training seed")?;
    for (pass, guide) in guides.iter().enumerate() {
        let g = guide.source_geometry;
        let columns = g.width.div_ceil(spacing) + 1;
        let rows = g.height.div_ceil(spacing) + 1;
        let mut vertices = Vec::new();
        let mut focus = Vec::new();
        for y in 0..rows {
            for x in 0..columns {
                let p = [
                    (g.width - 1) as f64 * x as f64 / (columns - 1) as f64,
                    (g.height - 1) as f64 * y as f64 / (rows - 1) as f64,
                ];
                let q = if pass == 0 {
                    (p[0], p[1])
                } else {
                    inverse.apply_at(p[0], p[1], g.width as f64 * 0.5, g.height as f64 * 0.5)
                };
                vertices.push([q.0, q.1]);
                let xy = [0, 1].map(|a| ((p[a] - guide.origin[a]) / guide.step as f64).round());
                let valid = xy[0] >= 0.
                    && xy[1] >= 0.
                    && xy[0] < guide.geometry.width as f64
                    && xy[1] < guide.geometry.height as f64;
                let i = if valid {
                    xy[1] as usize * guide.geometry.width + xy[0] as usize
                } else {
                    0
                };
                focus.push(FocusEvidence {
                    ordinal: if valid { guide.focus_ordinal[i] } else { 0. },
                    width: if valid { guide.focus_width[i] } else { 0. },
                    usable: valid && guide.covered[i] && guide.usable_focus[i],
                });
            }
        }
        result.push(ForwardMesh::new(
            g,
            columns,
            rows,
            vertices,
            vec![Visibility::SingleView; (columns - 1) * (rows - 1)],
            focus,
        )?);
    }
    Ok(result)
}
pub struct Model {
    pub meshes: Vec<ForwardMesh>,
    backward: Vec<BackwardMesh>,
    pub fit_rms: f64,
    pub maximum_displacement: f64,
}
pub fn fit(
    train: &Training,
    guides: &[MosaicGuide],
    spacing: usize,
    smoothness: f64,
) -> Result<Model> {
    let transform = seed(train, guides[0].source_geometry)?;
    let initial = meshes(guides, transform, spacing)?;
    let observations: Vec<_> = train
        .rows
        .iter()
        .zip(&train.weights)
        .map(|(r, &weight)| Correspondence {
            pass_a: 0,
            point_a: r.a,
            pass_b: 1,
            point_b: r.b,
            weight,
            role: ObservationRole::Fit,
        })
        .collect();
    let (meshes, report) = fit_meshes(
        &initial,
        &observations,
        MeshFitOptions {
            smoothness,
            max_work_bytes: 512 << 20,
            ..Default::default()
        },
    )?;
    let backward = meshes
        .iter()
        .map(|m| {
            BackwardMesh::new(
                m,
                MeshValidation::default(),
                IndexLimits {
                    bin_side: 64,
                    max_bins: 1_000_000,
                    max_entries: 10_000_000,
                },
            )
            .map_err(anyhow::Error::from)
        })
        .collect::<Result<Vec<_>>>()?;
    Ok(Model {
        meshes,
        backward,
        fit_rms: report.fit_rms,
        maximum_displacement: report.maximum_displacement,
    })
}
pub fn errors(model: &Model, rows: &[Row]) -> Result<Vec<[f64; 2]>> {
    rows.iter()
        .map(|r| {
            let a = model.meshes[0]
                .map_source(r.a)
                .context("training/test point outside A")?;
            let b = model.meshes[1]
                .map_source(r.b)
                .context("training/test point outside B")?;
            let (
                MappedPoint::Supported { source: pa, .. },
                MappedPoint::Supported { source: pb, .. },
            ) = (model.backward[0].map(b), model.backward[1].map(a))
            else {
                anyhow::bail!("unsupported/folded inverse placement for {}", r.id);
            };
            Ok([
                ((pa[0] - r.a[0]).powi(2)
                    + (pa[1] - r.a[1]).powi(2)
                    + (pb[0] - r.b[0]).powi(2)
                    + (pb[1] - r.b[1]).powi(2))
                .sqrt()
                    / 2_f64.sqrt(),
                (a[0] - b[0]).hypot(a[1] - b[1]),
            ])
        })
        .collect()
}
pub fn summary(errors: &[[f64; 2]], weights: &[f64]) -> Value {
    let mass: f64 = weights.iter().sum();
    json!({"rows":errors.len(),"total_declared_weight":mass,"weighted_native_rms_quad":(errors.iter().zip(weights).map(|(e,w)|w*e[0]*e[0]).sum::<f64>()/mass).sqrt(),"maximum_native_error_quad":errors.iter().map(|e|e[0]).fold(0.,f64::max),"within_half_quad":errors.iter().filter(|e|e[0]<=0.5).count(),"maximum_common_gauge_error_quad":errors.iter().map(|e|e[1]).fold(0.,f64::max)})
}

pub fn cv(rows: &[Row], guides: &[MosaicGuide]) -> (Option<(usize, f64)>, Vec<Value>) {
    let mut results = Vec::new();
    let mut best = None;
    for spacing in [512, 256, 128] {
        for smoothness in [2., 0.2, 0.02] {
            let mut folds = Vec::new();
            let mut sum = 0.;
            let mut mass = 0.;
            let mut valid = true;
            for f in 0..5 {
                let (train, test, purged) = split(rows, f);
                let evaluated = (|| -> Result<Value> {
                    ensure!(!test.is_empty(), "empty predefined test fold");
                    let trained = training(&train)?;
                    let model = fit(&trained, guides, spacing, smoothness)?;
                    let e = errors(&model, &test)?;
                    let (w, n, cohorts) = weights(&test);
                    let m: f64 = w.iter().sum();
                    sum += e.iter().zip(&w).map(|(e, w)| w * e[0] * e[0]).sum::<f64>();
                    mass += m;
                    Ok(
                        json!({"fold":f,"training":trained.receipt,"test_rows":test.len(),"test_geometry_nonoverlap_count":n,"test_cohorts":cohorts,"test_conflicts":coherent(&test).1,"purged_ids":purged,"metrics":summary(&e,&w),"test_errors":test.iter().zip(e).map(|(r,e)|json!({"id":r.id,"native_error_quad":e[0],"common_gauge_error_quad":e[1]})).collect::<Vec<_>>()}),
                    )
                })();
                match evaluated {
                    Ok(r) => folds.push(r),
                    Err(e) => {
                        valid = false;
                        folds.push(json!({"fold":f,"refusal":format!("{e:#}"),"test_rows":test.len(),"purged_ids":purged}));
                    }
                }
            }
            let score = valid.then(|| (sum / mass).sqrt());
            if let Some(score) = score {
                if best.is_none_or(|(_, _, s)| score < s) {
                    best = Some((spacing, smoothness, score));
                }
            }
            results.push(json!({"spacing_quad":spacing,"smoothness":smoothness,"all_five_folds_valid":valid,"weighted_native_cv_rms_quad":score,"folds":folds}));
        }
    }
    (
        best.map(|(spacing, smoothness, _)| (spacing, smoothness)),
        results,
    )
}
