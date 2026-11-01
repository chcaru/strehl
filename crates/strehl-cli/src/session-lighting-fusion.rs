//! Lighting fusion: blend separately merged, differently lit renders of one
//! geometrically consistent subject into a single photograph.
//!
//! Passes lit differently (a moved or re-aimed lamp) cannot be averaged into
//! one radiance without leaving patches, but each is a valid view. The anchor
//! render is the photograph; a layer takes over a region only where its pooled
//! local detail beats the anchor's by a margin, or where the anchor is clipped
//! or crushed. Averaging every lighting everywhere (plain exposure-fusion
//! weights) measured as a hazier, lower-contrast photograph on bug-4, with a
//! glow where brighter layers won flat background. Layers fade in from their
//! coverage edge and uncovered pixels are filled from the anchor before the
//! Laplacian pyramids, so coverage boundaries cannot leave seams. It operates on merged native CFA planes before
//! development, so demosaic, colour and tone stay exactly the ordinary path.
//! This is an appearance blend, **not** a radiance estimate.

/// One lighting group's merged planes in native API order R, G1, B, G2, in
/// shared signal units, with its coverage on the common canvas.
#[derive(Clone)]
pub struct GroupPlanes {
    pub planes: [Vec<f32>; 4],
    pub valid: Vec<bool>,
    /// Black-subtracted clipping level in these signal units.
    pub ceiling: f32,
}

#[derive(Clone, Debug, serde::Serialize)]
pub struct FusionReport {
    pub schema: &'static str,
    pub groups: usize,
    /// Mean normalized weight of each group over the canvas.
    pub mean_weight: Vec<f64>,
    /// Fraction of canvas pixels where each group carried the largest weight.
    pub dominant_fraction: Vec<f64>,
    pub levels: usize,
    pub config: FusionConfig,
    pub semantics: &'static str,
}

/// Anchor-first fusion parameters.
#[derive(Clone, Copy, Debug, serde::Serialize)]
pub struct FusionConfig {
    /// Box radius (plane px) over which local detail is pooled.
    pub detail_radius: usize,
    /// Exponent sharpening the choice toward the most detailed group.
    pub selection_power: f32,
    /// Detail multiplier of the anchor group: a layer must beat the anchor's
    /// local detail by this factor before it takes over.
    pub anchor_bias: f32,
    /// Distance (plane px) over which a layer fades in from its coverage edge.
    pub feather: usize,
    /// Display-domain luma below which a pixel counts as crushed.
    pub dark: f32,
    /// Display-domain luma above which a pixel counts as near clipping.
    pub bright: f32,
    /// Normalized local detail-band disagreement with the anchor,
    /// `E[(d - d0)^2] / (E[d^2] + E[d0^2])` (0 same structure, 1 unrelated,
    /// 2 opposite), at which a layer starts, and stops, being trusted. Scale
    /// free, so it needs no private noise estimate.
    pub consistent: f32,
    pub inconsistent: f32,
    /// First pyramid level from which tone is the anchor's alone.
    pub base_level: usize,
}

impl Default for FusionConfig {
    fn default() -> Self {
        Self {
            detail_radius: 8,
            selection_power: 4.0,
            anchor_bias: 1.5,
            feather: 24,
            dark: 0.06,
            bright: 0.9,
            consistent: 0.4,
            inconsistent: 0.8,
            base_level: 3,
        }
    }
}

/// Pixels at or above this fraction of the ceiling count as clipped.
const CLIP_FRACTION: f32 = 0.92;
const EPSILON: f32 = 1e-6;
/// Detail floor (display units) so flat regions fall back to the bias.
const DETAIL_FLOOR: f32 = 1e-3;

fn display(value: f32, ceiling: f32) -> f32 {
    (value.max(0.0) / ceiling).min(1.0).powf(1.0 / 2.2)
}

fn smoothstep(edge0: f32, edge1: f32, x: f32) -> f32 {
    let t = ((x - edge0) / (edge1 - edge0)).clamp(0.0, 1.0);
    t * t * (3.0 - 2.0 * t)
}

/// Separable box mean with clamped borders.
fn box_mean(data: &[f32], width: usize, height: usize, radius: usize) -> Vec<f32> {
    if radius == 0 {
        return data.to_vec();
    }
    let pass = |src: &[f32], len: usize, count: usize, stride: usize, step: usize| -> Vec<f32> {
        let mut out = vec![0.0f32; src.len()];
        let r = radius as isize;
        for line in 0..count {
            let base = line * stride;
            let at = |i: isize| src[base + (i.clamp(0, len as isize - 1) as usize) * step];
            let mut sum: f64 = (-r..=r).map(|i| f64::from(at(i))).sum();
            for i in 0..len as isize {
                out[base + i as usize * step] = (sum / (2 * r + 1) as f64) as f32;
                sum += f64::from(at(i + r + 1)) - f64::from(at(i - r));
            }
        }
        out
    };
    let rows = pass(data, width, height, width, 1);
    pass(&rows, height, width, 1, width)
}

/// Display-domain luma of a group and its fine detail band.
fn luma_and_band(
    group: &GroupPlanes,
    width: usize,
    height: usize,
    reference_ceiling: f32,
) -> (Vec<f32>, Vec<f32>) {
    let [_, g1, _, g2] = &group.planes;
    let luma: Vec<f32> = (0..width * height)
        .map(|i| display(0.5 * (g1[i] + g2[i]), reference_ceiling))
        .collect();
    let smooth = box_mean(&luma, width, height, 2);
    let band = luma.iter().zip(&smooth).map(|(l, s)| l - s).collect();
    (luma, band)
}

fn energy(band: &[f32], width: usize, height: usize, radius: usize) -> Vec<f32> {
    box_mean(
        &band.iter().map(|v| v * v).collect::<Vec<_>>(),
        width,
        height,
        radius,
    )
}

/// The anchor's quantities every layer is judged against.
struct AnchorContext {
    band: Vec<f32>,
    /// Pooled energy of `band`.
    energy: Vec<f32>,
}

/// Per-pixel unnormalized fine-level weights of one group. `anchor` is `None`
/// for the anchor group itself, which then returns its context.
fn weights(
    group: &GroupPlanes,
    anchor: Option<&AnchorContext>,
    width: usize,
    height: usize,
    reference_ceiling: f32,
    cfg: &FusionConfig,
) -> (Vec<f32>, Option<AnchorContext>) {
    let n = width * height;
    let [r, g1, b, g2] = &group.planes;
    let (luma, band) = luma_and_band(group, width, height, reference_ceiling);
    let mut laplace = vec![0.0f32; n];
    for y in 1..height.saturating_sub(1) {
        for x in 1..width.saturating_sub(1) {
            let i = y * width + x;
            laplace[i] = (luma[i - 1] + luma[i + 1] + luma[i - width] + luma[i + width]
                - 4.0 * luma[i])
                .abs();
        }
    }
    let detail = box_mean(&laplace, width, height, cfg.detail_radius);
    drop(laplace);
    let coverage: Vec<f32> = group
        .valid
        .iter()
        .map(|&v| f32::from(u8::from(v)))
        .collect();
    let coverage = box_mean(&coverage, width, height, cfg.feather);
    let clipped: Vec<f32> = (0..n)
        .map(|i| {
            f32::from(u8::from(
                [r[i], g1[i], b[i], g2[i]]
                    .iter()
                    .any(|&v| v >= CLIP_FRACTION * group.ceiling),
            ))
        })
        .collect();
    let clipped = box_mean(&clipped, width, height, 2);
    // Layers are trusted only where their detail band agrees with the
    // anchor's. Nothing overrides this: a clipped anchor highlight is usually a
    // real specular, and handing it to another lighting punched dark holes
    // into the developed photograph (bug-4).
    let trust: Option<Vec<f32>> = anchor.map(|a| {
        let own = energy(&band, width, height, cfg.detail_radius);
        let disagreement: Vec<f32> = band
            .iter()
            .zip(&a.band)
            .map(|(x, y)| (x - y) * (x - y))
            .collect();
        let disagreement = box_mean(&disagreement, width, height, cfg.detail_radius);
        (0..n)
            .map(|i| {
                let ratio = disagreement[i] / (own[i] + a.energy[i] + 1e-12);
                1.0 - smoothstep(cfg.consistent, cfg.inconsistent, ratio)
            })
            .collect()
    });
    let bias = if anchor.is_none() {
        cfg.anchor_bias
    } else {
        1.0
    };
    let weights: Vec<f32> = (0..n)
        .map(|i| {
            if !group.valid[i] {
                return 0.0;
            }
            // Full weight only once the whole feather window is covered.
            let edge = if anchor.is_none() {
                1.0
            } else {
                smoothstep(0.5, 1.0, coverage[i])
            };
            let trust = trust.as_ref().map_or(1.0, |t| t[i]);
            let exposure =
                smoothstep(0.0, cfg.dark, luma[i]) * (1.0 - smoothstep(cfg.bright, 1.0, luma[i]));
            let usable = exposure * (1.0 - clipped[i]).max(0.0);
            edge * trust
                * (0.02 + 0.98 * usable)
                * (bias * (detail[i] + DETAIL_FLOOR)).powf(cfg.selection_power)
        })
        .collect();
    let context = anchor.is_none().then(|| AnchorContext {
        energy: energy(&band, width, height, cfg.detail_radius),
        band,
    });
    (weights, context)
}

/// Normalize weights per pixel; where none carries evidence the anchor (or
/// any covering group) supplies the pixel.
fn normalize(w: &mut [Vec<f32>], groups: &[GroupPlanes], n: usize) {
    for i in 0..n {
        let total: f32 = w.iter().map(|v| v[i]).sum();
        if total.is_nan() || total <= 0.0 {
            for (k, v) in w.iter_mut().enumerate() {
                v[i] = if k == 0 || !groups[0].valid[i] && groups[k].valid[i] {
                    1.0
                } else {
                    0.0
                };
            }
            let t: f32 = w.iter().map(|v| v[i]).sum();
            for v in w.iter_mut() {
                v[i] /= t.max(EPSILON);
            }
        } else {
            for v in w.iter_mut() {
                v[i] /= total;
            }
        }
    }
}

/// Diagnostic dump of captured groups (`STREHL_LIGHTING_DUMP`), so fusion can
/// be studied without re-merging: `meta.json` plus raw little-endian planes.
pub fn dump(
    groups: &[GroupPlanes],
    width: usize,
    height: usize,
    dir: &std::path::Path,
) -> anyhow::Result<()> {
    use std::io::Write;
    std::fs::create_dir_all(dir)?;
    let ceilings: Vec<f32> = groups.iter().map(|g| g.ceiling).collect();
    std::fs::write(
        dir.join("meta.json"),
        serde_json::to_vec(
            &serde_json::json!({"width": width, "height": height, "ceilings": ceilings}),
        )?,
    )?;
    for (k, g) in groups.iter().enumerate() {
        let mut f =
            std::io::BufWriter::new(std::fs::File::create(dir.join(format!("group-{k}.f32")))?);
        for plane in &g.planes {
            for v in plane {
                f.write_all(&v.to_le_bytes())?;
            }
        }
        f.flush()?;
        std::fs::write(
            dir.join(format!("group-{k}.valid")),
            g.valid.iter().map(|&v| u8::from(v)).collect::<Vec<_>>(),
        )?;
    }
    Ok(())
}

/// Read a [`dump`].
pub fn load_dump(dir: &std::path::Path) -> anyhow::Result<(Vec<GroupPlanes>, usize, usize)> {
    let meta: serde_json::Value = serde_json::from_slice(&std::fs::read(dir.join("meta.json"))?)?;
    let width = meta["width"].as_u64().unwrap_or(0) as usize;
    let height = meta["height"].as_u64().unwrap_or(0) as usize;
    let n = width * height;
    let mut groups = Vec::new();
    for (k, c) in meta["ceilings"]
        .as_array()
        .into_iter()
        .flatten()
        .enumerate()
    {
        let bytes = std::fs::read(dir.join(format!("group-{k}.f32")))?;
        anyhow::ensure!(bytes.len() == 16 * n, "group {k} has the wrong size");
        let values: Vec<f32> = bytes
            .as_chunks::<4>()
            .0
            .iter()
            .map(|b| f32::from_le_bytes(*b))
            .collect();
        let planes = std::array::from_fn(|p| values[p * n..(p + 1) * n].to_vec());
        let valid = std::fs::read(dir.join(format!("group-{k}.valid")))?
            .into_iter()
            .map(|v| v != 0)
            .collect();
        groups.push(GroupPlanes {
            planes,
            valid,
            ceiling: c.as_f64().unwrap_or(1.0) as f32,
        });
    }
    Ok((groups, width, height))
}

// --- pyramids --------------------------------------------------------------

#[derive(Clone)]
struct Image {
    data: Vec<f32>,
    width: usize,
    height: usize,
}

const KERNEL: [f32; 5] = [1.0 / 16.0, 4.0 / 16.0, 6.0 / 16.0, 4.0 / 16.0, 1.0 / 16.0];

fn blur(image: &Image) -> Image {
    let (w, h) = (image.width, image.height);
    let mut tmp = vec![0.0; w * h];
    for y in 0..h {
        for x in 0..w {
            let mut s = 0.0;
            for (k, &c) in KERNEL.iter().enumerate() {
                let xx = (x as isize + k as isize - 2).clamp(0, w as isize - 1) as usize;
                s += c * image.data[y * w + xx];
            }
            tmp[y * w + x] = s;
        }
    }
    let mut out = vec![0.0; w * h];
    for y in 0..h {
        for x in 0..w {
            let mut s = 0.0;
            for (k, &c) in KERNEL.iter().enumerate() {
                let yy = (y as isize + k as isize - 2).clamp(0, h as isize - 1) as usize;
                s += c * tmp[yy * w + x];
            }
            out[y * w + x] = s;
        }
    }
    Image {
        data: out,
        width: w,
        height: h,
    }
}

fn down(image: &Image) -> Image {
    let b = blur(image);
    let (w, h) = (image.width.div_ceil(2), image.height.div_ceil(2));
    let mut data = vec![0.0; w * h];
    for y in 0..h {
        for x in 0..w {
            data[y * w + x] =
                b.data[(2 * y).min(image.height - 1) * image.width + (2 * x).min(image.width - 1)];
        }
    }
    Image {
        data,
        width: w,
        height: h,
    }
}

fn up(image: &Image, width: usize, height: usize) -> Image {
    let mut data = vec![0.0; width * height];
    for y in 0..height {
        for x in 0..width {
            // Bilinear from the coarse grid (sample centres at even fine pixels).
            let (u, v) = (x as f32 * 0.5, y as f32 * 0.5);
            let (x0, y0) = (u.floor() as usize, v.floor() as usize);
            let (x1, y1) = (
                (x0 + 1).min(image.width - 1),
                (y0 + 1).min(image.height - 1),
            );
            let (fx, fy) = (u - x0 as f32, v - y0 as f32);
            let at = |xx: usize, yy: usize| image.data[yy * image.width + xx];
            let top = at(x0.min(image.width - 1), y0.min(image.height - 1)) * (1.0 - fx)
                + at(x1, y0.min(image.height - 1)) * fx;
            let bottom = at(x0.min(image.width - 1), y1) * (1.0 - fx) + at(x1, y1) * fx;
            data[y * width + x] = top * (1.0 - fy) + bottom * fy;
        }
    }
    Image {
        data,
        width,
        height,
    }
}

fn gaussian(image: Image, levels: usize) -> Vec<Image> {
    let mut out = vec![image];
    for _ in 1..levels {
        let next = down(out.last().expect("level"));
        out.push(next);
    }
    out
}

fn laplacian(image: Image, levels: usize) -> Vec<Image> {
    let g = gaussian(image, levels);
    let mut out = Vec::with_capacity(levels);
    for k in 0..levels - 1 {
        let expanded = up(&g[k + 1], g[k].width, g[k].height);
        out.push(Image {
            data: g[k]
                .data
                .iter()
                .zip(&expanded.data)
                .map(|(a, b)| a - b)
                .collect(),
            width: g[k].width,
            height: g[k].height,
        });
    }
    out.push(g[levels - 1].clone());
    out
}

fn collapse(mut pyramid: Vec<Image>) -> Image {
    let mut image = pyramid.pop().expect("coarsest level");
    while let Some(level) = pyramid.pop() {
        let expanded = up(&image, level.width, level.height);
        image = Image {
            data: level
                .data
                .iter()
                .zip(&expanded.data)
                .map(|(a, b)| a + b)
                .collect(),
            width: level.width,
            height: level.height,
        };
    }
    image
}

/// Fuse lighting groups on a `width` x `height` plane canvas. Group 0 is the
/// anchor group; where no group has positive weight it supplies the pixel.
pub fn fuse(groups: &[GroupPlanes], width: usize, height: usize) -> ([Vec<f32>; 4], FusionReport) {
    fuse_with(groups, width, height, &FusionConfig::default())
}

pub fn fuse_with(
    groups: &[GroupPlanes],
    width: usize,
    height: usize,
    cfg: &FusionConfig,
) -> ([Vec<f32>; 4], FusionReport) {
    assert!(!groups.is_empty());
    let n = width * height;
    let reference_ceiling = groups[0].ceiling;
    let mut w = Vec::with_capacity(groups.len());
    let (w0, context) = weights(&groups[0], None, width, height, reference_ceiling, cfg);
    let context = context.expect("anchor context");
    w.push(w0);
    for g in &groups[1..] {
        w.push(weights(g, Some(&context), width, height, reference_ceiling, cfg).0);
    }
    drop(context);
    normalize(&mut w, groups, n);
    let mut dominant = vec![0usize; groups.len()];
    let mut mean = vec![0.0f64; groups.len()];
    for i in 0..n {
        let (best, _) = w
            .iter()
            .enumerate()
            .map(|(k, v)| (k, v[i]))
            .fold((0, f32::NEG_INFINITY), |a, b| if b.1 > a.1 { b } else { a });
        dominant[best] += 1;
        for (k, v) in w.iter().enumerate() {
            mean[k] += f64::from(v[i]);
        }
    }
    let levels = {
        let mut l = 1;
        let mut s = width.min(height);
        while s > 16 && l < 10 {
            s /= 2;
            l += 1;
        }
        l
    };
    // Fine levels follow the detail weights; from `base_level` on, tone is the
    // anchor's alone.
    let weight_pyramids: Vec<Vec<Image>> = w
        .into_iter()
        .enumerate()
        .map(|(g, data)| {
            gaussian(
                Image {
                    data,
                    width,
                    height,
                },
                levels,
            )
            .into_iter()
            .enumerate()
            .map(|(level, mut image)| {
                if level >= cfg.base_level {
                    image.data.fill(if g == 0 { 1.0 } else { 0.0 });
                }
                image
            })
            .collect()
        })
        .collect();
    let fused: [Vec<f32>; 4] = std::array::from_fn(|channel| {
        let mut acc: Option<Vec<Image>> = None;
        for (g, group) in groups.iter().enumerate() {
            let data = group.planes[channel]
                .iter()
                .zip(&group.valid)
                .zip(&groups[0].planes[channel])
                .map(|((&v, &ok), &a)| if ok { v } else { a })
                .collect();
            let lap = laplacian(
                Image {
                    data,
                    width,
                    height,
                },
                levels,
            );
            let weighted: Vec<Image> = lap
                .into_iter()
                .zip(&weight_pyramids[g])
                .map(|(l, wp)| Image {
                    data: l.data.iter().zip(&wp.data).map(|(a, b)| a * b).collect(),
                    width: l.width,
                    height: l.height,
                })
                .collect();
            acc = Some(match acc {
                None => weighted,
                Some(prev) => prev
                    .into_iter()
                    .zip(weighted)
                    .map(|(a, b)| Image {
                        data: a.data.iter().zip(&b.data).map(|(x, y)| x + y).collect(),
                        width: a.width,
                        height: a.height,
                    })
                    .collect(),
            });
        }
        collapse(acc.expect("at least one group")).data
    });
    let report = FusionReport {
        schema: "strehl.session-lighting-fusion.v4",
        groups: groups.len(),
        mean_weight: mean.iter().map(|m| m / n as f64).collect(),
        dominant_fraction: dominant.iter().map(|&d| d as f64 / n as f64).collect(),
        levels,
        config: *cfg,
        semantics: "Anchor-first blend of separately merged, differently lit renders: layers contribute fine detail only where their detail band agrees with the anchor's and beats the anchor's detail by the bias; coarse tone is the anchor's alone (Laplacian pyramid). Not a radiance estimate.",
    };
    (fused, report)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn group(width: usize, height: usize, value: impl Fn(usize, usize) -> f32) -> GroupPlanes {
        let plane: Vec<f32> = (0..width * height)
            .map(|i| value(i % width, i / width))
            .collect();
        GroupPlanes {
            planes: [plane.clone(), plane.clone(), plane.clone(), plane],
            valid: vec![true; width * height],
            ceiling: 1000.0,
        }
    }

    #[test]
    fn identical_groups_fuse_to_the_input() {
        let (w, h) = (64, 48);
        let f =
            |x: usize, y: usize| 200.0 + 50.0 * ((x as f32 * 0.4).sin() + (y as f32 * 0.3).cos());
        let (fused, report) = fuse(&[group(w, h, f), group(w, h, f)], w, h);
        for (i, v) in fused[1].iter().enumerate() {
            let expected = f(i % w, i / w);
            assert!((v - expected).abs() < 0.5, "pixel {i}: {v} vs {expected}");
        }
        assert!(report.mean_weight[0] > 0.8, "{report:?}");
    }

    #[test]
    fn partial_coverage_leaves_no_seam() {
        let (w, h) = (96, 64);
        let f =
            |x: usize, y: usize| 300.0 + 80.0 * ((x as f32 * 0.5).sin() * (y as f32 * 0.4).cos());
        let anchor = group(w, h, f);
        // Same content, but the right half is uncovered and holds zeros.
        let mut layer = group(w, h, f);
        for y in 0..h {
            for x in w / 2..w {
                layer.valid[y * w + x] = false;
                for plane in &mut layer.planes {
                    plane[y * w + x] = 0.0;
                }
            }
        }
        let (fused, _) = fuse(&[anchor, layer], w, h);
        for (i, v) in fused[1].iter().enumerate() {
            let expected = f(i % w, i / w);
            assert!((v - expected).abs() < 0.5, "pixel {i}: {v} vs {expected}");
        }
    }

    #[test]
    fn layers_never_add_structure_absent_from_the_anchor_and_respect_clipping() {
        let (w, h) = (96, 64);
        let texture = |x: usize, y: usize| 60.0 * ((x as f32 * 0.9).sin() * (y as f32 * 0.7).cos());
        // Anchor: left half detailed, right half flat (e.g. where a highlight
        // sits in another lighting). Layer: the opposite.
        let a = group(w, h, |x, y| {
            if x < w / 2 {
                250.0 + texture(x, y)
            } else {
                250.0
            }
        });
        let mut b = group(w, h, |x, y| {
            if x >= w / 2 {
                250.0 + texture(x, y)
            } else {
                250.0
            }
        });
        let (fused, _) = fuse(&[a, b], w, h);
        let mut worst_left = 0.0f32;
        let mut worst_right = 0.0f32;
        for y in 8..h - 8 {
            for x in 4..w - 4 {
                let v = fused[1][y * w + x];
                if x < w / 2 - 8 {
                    worst_left = worst_left.max((v - (250.0 + texture(x, y))).abs());
                } else if x > w / 2 + 8 {
                    worst_right = worst_right.max((v - 250.0).abs());
                }
            }
        }
        assert!(
            worst_left < 3.0 && worst_right < 3.0,
            "{worst_left} {worst_right}"
        );
        // Invalid coverage and clipping carry no weight.
        b = group(w, h, |_, _| 990.0);
        b.valid[0] = false;
        let a = group(w, h, |x, y| 250.0 + texture(x, y));
        let (fused, report) = fuse(&[a, b], w, h);
        assert!(report.mean_weight[1] < 0.01, "{report:?}");
        assert!((fused[0][w * 10 + 10] - (250.0 + texture(10, 10))).abs() < 5.0);
    }

    /// Deterministic pseudo-noise in [-1, 1].
    fn noise(x: usize, y: usize, seed: u32) -> f32 {
        let mut v = (x as u32).wrapping_mul(0x9E37_79B9)
            ^ (y as u32).wrapping_mul(0x85EB_CA6B)
            ^ seed.wrapping_mul(0xC2B2_AE35);
        v ^= v >> 15;
        v = v.wrapping_mul(0x2C1B_3C6D);
        v ^= v >> 12;
        (v & 0xFFFF) as f32 / 32767.5 - 1.0
    }

    #[test]
    fn layers_contribute_only_consistent_detail() {
        let (w, h) = (128, 96);
        let texture = |x: f32, y: f32| 40.0 * ((x * 0.35).sin() * (y * 0.3).cos());
        let anchor = group(w, h, |x, y| {
            300.0 + texture(x as f32, y as f32) + 6.0 * noise(x, y, 1)
        });
        // Same structure, independent noise: a consistent layer.
        let consistent = group(w, h, |x, y| {
            300.0 + texture(x as f32, y as f32) + 6.0 * noise(x, y, 2)
        });
        // Displaced, stronger structure (moved highlights): inconsistent.
        let moved = group(w, h, |x, y| {
            300.0 + 2.5 * texture(x as f32 + 4.0, y as f32 + 3.0) + 6.0 * noise(x, y, 3)
        });
        let (_, report) = fuse(&[anchor.clone(), consistent], w, h);
        assert!(report.mean_weight[1] > 0.05, "{report:?}");
        let (fused, report) = fuse(&[anchor.clone(), moved], w, h);
        assert!(report.mean_weight[1] < 0.02, "{report:?}");
        let mut worst = 0.0f32;
        for y in 12..h - 12 {
            for x in 12..w - 12 {
                worst = worst.max((fused[1][y * w + x] - anchor.planes[1][y * w + x]).abs());
            }
        }
        assert!(
            worst < 6.0,
            "moved structure leaked into the anchor: {worst}"
        );
    }
}

/// Offline study of a [`dump`]: `STREHL_LIGHTING_DUMP_IN` (input),
/// `STREHL_LIGHTING_DUMP_OUT` (fused planes, dump format) and optional
/// `STREHL_LIGHTING_CONFIG` (JSON `[detail_radius, selection_power,
/// anchor_bias, feather, dark, bright, consistent, inconsistent, base_level]`).
#[cfg(test)]
#[test]
#[ignore = "needs a lighting-fusion dump"]
fn lighting_fusion_from_dump() {
    let input = std::env::var_os("STREHL_LIGHTING_DUMP_IN").expect("STREHL_LIGHTING_DUMP_IN");
    let output = std::env::var_os("STREHL_LIGHTING_DUMP_OUT").expect("STREHL_LIGHTING_DUMP_OUT");
    let (groups, width, height) = load_dump(std::path::Path::new(&input)).unwrap();
    let mut cfg = FusionConfig::default();
    if let Ok(text) = std::env::var("STREHL_LIGHTING_CONFIG") {
        let v: Vec<f64> = serde_json::from_str(&text).unwrap();
        cfg = FusionConfig {
            detail_radius: v[0] as usize,
            selection_power: v[1] as f32,
            anchor_bias: v[2] as f32,
            feather: v[3] as usize,
            dark: v[4] as f32,
            bright: v[5] as f32,
            consistent: v[6] as f32,
            inconsistent: v[7] as f32,
            base_level: v[8] as usize,
        };
    }
    let (planes, report) = fuse_with(&groups, width, height, &cfg);
    eprintln!("{}", serde_json::to_string(&report).unwrap());
    let fused = GroupPlanes {
        planes,
        valid: vec![true; width * height],
        ceiling: groups[0].ceiling,
    };
    dump(&[fused], width, height, std::path::Path::new(&output)).unwrap();
}
