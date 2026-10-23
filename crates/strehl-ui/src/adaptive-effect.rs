//! A bounded explanation of the actual developed treatment, computed off-thread.
use super::*;
use std::sync::atomic::{AtomicBool, Ordering};

#[derive(Clone)]
struct Key {
    image: Arc<LinearImage>,
    recipe: DevelopmentRecipe,
    target: Option<String>,
}

impl Key {
    fn matches(
        &self,
        image: &Arc<LinearImage>,
        recipe: &DevelopmentRecipe,
        target: Option<&str>,
    ) -> bool {
        Arc::ptr_eq(&self.image, image)
            && self.target.as_deref() == target
            && self.recipe == *recipe
    }
}

struct Pending {
    key: Key,
    task: Task<EffectImage>,
}

pub(super) struct EffectImage {
    pub image: egui::ColorImage,
    pub lift_fraction: f32,
    pub deepen_fraction: f32,
    pub color_fraction: f32,
}

#[derive(Default)]
pub(super) struct EffectMap {
    pending: Option<Pending>,
    key: Option<Key>,
    texture: Option<TextureHandle>,
    summary: Option<[f32; 3]>,
    error: Option<String>,
}

impl EffectMap {
    pub fn poll(
        &mut self,
        ctx: &egui::Context,
        image: Option<&Arc<LinearImage>>,
        recipe: &DevelopmentRecipe,
        target: Option<&str>,
    ) {
        // A stale map must never be shown on another photograph or region.
        if self.key.as_ref().is_some_and(|key| {
            image.is_none_or(|i| !Arc::ptr_eq(i, &key.image)) || key.target.as_deref() != target
        }) {
            self.key = None;
            self.texture = None;
            self.summary = None;
        }
        if self
            .pending
            .as_ref()
            .is_some_and(|p| image.is_none_or(|i| !p.key.matches(i, recipe, target)))
        {
            self.pending = None;
        }
        let result = self
            .pending
            .as_ref()
            .and_then(|p| match p.task.receiver.try_recv() {
                Ok(result) => Some(result),
                Err(mpsc::TryRecvError::Empty) => None,
                Err(mpsc::TryRecvError::Disconnected) => {
                    Some(Err("Effect preview ended without a result".into()))
                }
            });
        if let Some(result) = result {
            let pending = self.pending.take().unwrap();
            self.key = Some(pending.key);
            match result {
                Ok(effect) => {
                    self.texture = Some(ctx.load_texture(
                        "adaptive-effect",
                        effect.image,
                        egui::TextureOptions::LINEAR,
                    ));
                    self.summary = Some([
                        effect.lift_fraction,
                        effect.deepen_fraction,
                        effect.color_fraction,
                    ]);
                    self.error = None;
                }
                Err(error) => {
                    // The key identifies the failed request to avoid a retry
                    // loop; its previous photograph must not look current.
                    self.texture = None;
                    self.summary = None;
                    self.error = Some(error);
                }
            }
        }
    }

    pub fn show(
        &mut self,
        ui: &mut egui::Ui,
        image: &Arc<LinearImage>,
        recipe: &DevelopmentRecipe,
        target: Option<&str>,
    ) {
        self.poll(ui.ctx(), Some(image), recipe, target);
        let current = self
            .key
            .as_ref()
            .is_some_and(|key| key.matches(image, recipe, target));
        // No work while a control is being dragged. Keep the old map in place,
        // then publish one replacement when the pointer settles.
        if !current && self.pending.is_none() && !ui.input(|i| i.pointer.any_down()) {
            let key = Key {
                image: Arc::clone(image),
                recipe: recipe.clone(),
                target: target.map(str::to_owned),
            };
            let work = key.clone();
            let wake = ui.ctx().clone();
            self.pending = Some(Pending {
                key,
                task: jobs::spawn_notifying_task(
                    "strehl-adaptive-effect",
                    move |cancelled| {
                        render_effect(
                            &work.image,
                            &work.recipe,
                            work.target.as_deref(),
                            &cancelled,
                        )
                    },
                    move || wake.request_repaint(),
                ),
            });
        }
        let aspect = image.height as f32 / image.width as f32;
        let width = ui.available_width().min(126.0 / aspect);
        let height = width * aspect;
        let (rect, _) = ui.allocate_exact_size(
            egui::vec2(ui.available_width(), height),
            egui::Sense::hover(),
        );
        let photo = egui::Rect::from_center_size(rect.center(), egui::vec2(width, height));
        ui.painter().rect_filled(photo, 0.0, BG);
        if let Some(texture) = &self.texture {
            ui.painter().image(
                texture.id(),
                photo,
                egui::Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(1.0, 1.0)),
                Color32::WHITE,
            );
        }
        ui.horizontal(|ui| {
            for (label, color) in [
                ("Lift", Color32::from_rgb(239, 181, 94)),
                ("Deepen", Color32::from_rgb(85, 167, 224)),
                ("Color", Color32::from_rgb(188, 135, 222)),
            ] {
                ui.colored_label(color, RichText::new(label).size(10.0));
            }
            if !current {
                theme::caption(ui, "Updating…");
            }
        });
        theme::caption(ui, "Changes amplified for visibility · sampled preview");
        if let Some(error) = &self.error {
            ui.colored_label(AMBER, error);
        }
    }
}

fn luminance(rgb: [f32; 3]) -> f32 {
    (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]).max(0.0)
}

fn render_effect(
    image: &LinearImage,
    recipe: &DevelopmentRecipe,
    target: Option<&str>,
    cancelled: &AtomicBool,
) -> anyhow::Result<EffectImage> {
    recipe.validate()?;
    anyhow::ensure!(
        image.width > 0
            && image.height > 0
            && image.pixels.len() == image.width as usize * image.height as usize * 3,
        "Invalid effect preview image"
    );
    let mut before = recipe.clone();
    before.clear_adaptive_scope(target);
    let scale = 128.0 / image.width.max(image.height) as f32;
    let width = (image.width as f32 * scale).round().max(1.0) as usize;
    let height = (image.height as f32 * scale).round().max(1.0) as usize;
    let mut pixels = Vec::with_capacity(width * height);
    let mut changed = [0usize; 3];
    for y in 0..height {
        anyhow::ensure!(
            !cancelled.load(Ordering::Relaxed),
            "Effect preview cancelled"
        );
        for x in 0..width {
            let sx = ((x as f64 + 0.5) * image.width as f64 / width as f64) as usize;
            let sy = ((y as f64 + 0.5) * image.height as f64 / height as f64) as usize;
            let i = sy.min(image.height as usize - 1) * image.width as usize
                + sx.min(image.width as usize - 1);
            let a = image.developed_pixel(i, &before);
            let b = image.developed_pixel(i, recipe);
            anyhow::ensure!(
                a.into_iter().chain(b).all(f32::is_finite),
                "Nonfinite effect preview sample"
            );
            let ya = luminance(a);
            let yb = luminance(b);
            let ev = if ya > 1e-6 && yb > 1e-6 {
                (yb / ya).log2()
            } else {
                0.0
            };
            let chroma = if ya > 0.002 && yb > 0.002 {
                a.into_iter()
                    .zip(b)
                    .map(|(a, b)| (a / ya - b / yb).abs())
                    .fold(0.0, f32::max)
            } else {
                0.0
            };
            changed[0] += usize::from(ev > 0.01);
            changed[1] += usize::from(ev < -0.01);
            changed[2] += usize::from(chroma > 0.01);
            let gray = 0.08 + 0.45 * (ya / (0.1 + ya)).sqrt();
            let tone_weight = (ev.abs() * 5.0).clamp(0.0, 0.85);
            let color_weight = (chroma * 3.0).clamp(0.0, 0.75) * (1.0 - tone_weight);
            let tint = if ev >= 0.0 {
                [0.94, 0.71, 0.37]
            } else {
                [0.33, 0.65, 0.88]
            };
            let color = [0.74, 0.53, 0.87];
            let rgb: [u8; 3] = std::array::from_fn(|c| {
                (255.0
                    * (gray * (1.0 - tone_weight - color_weight)
                        + tint[c] * tone_weight
                        + color[c] * color_weight))
                    .round()
                    .clamp(0.0, 255.0) as u8
            });
            pixels.push(Color32::from_rgb(rgb[0], rgb[1], rgb[2]));
        }
    }
    let n = pixels.len() as f32;
    Ok(EffectImage {
        image: egui::ColorImage::new([width, height], pixels),
        lift_fraction: changed[0] as f32 / n,
        deepen_fraction: changed[1] as f32 / n,
        color_fraction: changed[2] as f32 / n,
    })
}

#[cfg(test)]
#[path = "adaptive-effect-tests.rs"]
mod tests;
