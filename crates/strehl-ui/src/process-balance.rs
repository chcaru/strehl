//! Optional observation-balance lens for an owned, completed result.
//!
//! The engine stores folded rank centrality, not a quality probability. Values
//! are preserved as Gray16; display sampling never changes the underlying map.
//! The caller must certify final-image UV against the analysis domain before
//! calling `paint`. Camera JPEG UV is not such a certificate.

use std::{
    path::{Path, PathBuf},
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
        mpsc::TryRecvError,
    },
    time::Duration,
};

use anyhow::{Context as _, Result, ensure};
use eframe::egui::{
    self, Align2, Color32, ColorImage, FontId, Painter, Pos2, Rect, Sense, TextureHandle,
    TextureOptions, Ui,
};
use image::{DynamicImage, ImageFormat, ImageReader};

use crate::{jobs, theme};

#[path = "process-balance-evidence.rs"]
mod evidence;
pub(crate) use evidence::read_evidence;

const MAX_SIDE: usize = 32_768;
const MAX_PIXELS: usize = 32_000_000;
const MAX_DECODE_BYTES: u64 = 128 * 1024 * 1024;
const TEXTURE_SIDE: usize = 1024;
const HISTOGRAM_SIDE: usize = 128;
const BINS: usize = 20;
const MISSING: u16 = u16::MAX;
const BLUE: Color32 = Color32::from_rgb(107, 159, 193);
const SAND: Color32 = Color32::from_rgb(201, 188, 153);

#[derive(Clone, Debug, PartialEq, Eq)]
struct Key {
    output: PathBuf,
    size: [usize; 2],
}

struct Pending {
    key: Key,
    obsolete: Arc<AtomicBool>,
    task: jobs::Task<Decoded>,
}

struct Decoded {
    size: [usize; 2],
    values: Vec<u16>,
    image: ColorImage,
}

struct Loaded {
    size: [usize; 2],
    values: Vec<u16>,
    texture: TextureHandle,
    window: PixelWindow,
}

/// Integer-pixel cache key. Its full footprint encloses the requested aperture,
/// retaining partially visible edge pixels without stretching a cropped sample.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct PixelWindow {
    min: [usize; 2],
    max: [usize; 2],
}

impl PixelWindow {
    fn full(size: [usize; 2]) -> Self {
        Self {
            min: [0, 0],
            max: size,
        }
    }

    fn enclosing(size: [usize; 2], aperture: Rect) -> Self {
        let low = [aperture.min.x, aperture.min.y];
        let high = [aperture.max.x, aperture.max.y];
        let min =
            std::array::from_fn(|i| ((low[i] * size[i] as f32).floor() as usize).min(size[i] - 1));
        let max = std::array::from_fn(|i| {
            ((high[i] * size[i] as f32).ceil() as usize).clamp(min[i] + 1, size[i])
        });
        Self { min, max }
    }

    fn extent(self) -> [usize; 2] {
        std::array::from_fn(|i| self.max[i] - self.min[i])
    }

    fn uv(self, size: [usize; 2], aperture: Rect) -> Rect {
        let extent = self.extent();
        let project = |p: Pos2| {
            egui::pos2(
                ((p.x * size[0] as f32 - self.min[0] as f32) / extent[0] as f32).clamp(0.0, 1.0),
                ((p.y * size[1] as f32 - self.min[1] as f32) / extent[1] as f32).clamp(0.0, 1.0),
            )
        };
        Rect::from_min_max(project(aperture.min), project(aperture.max))
    }
}

#[derive(Clone, Debug, Default, PartialEq, Eq)]
struct Distribution {
    bins: [u32; BINS],
    observed: u32,
    missing: u32,
}

/// One retained run and at most one decoder, including during rapid navigation.
#[derive(Default)]
pub(crate) struct ObservationBalance {
    key: Option<Key>,
    attempted: bool,
    pending: Option<Pending>,
    loaded: Option<Loaded>,
    enabled: bool,
    aperture: Option<Rect>,
    distribution: Distribution,
    at_pin: Option<u16>,
}

impl ObservationBalance {
    /// Clear visible evidence before a new photograph can paint. Keep an
    /// obsolete decoder until retirement so rapid switching cannot fan out IO.
    pub(crate) fn invalidate(&mut self) {
        if let Some(pending) = &self.pending {
            pending.obsolete.store(true, Ordering::Relaxed);
        }
        self.key = None;
        self.attempted = false;
        self.loaded = None;
        self.enabled = false;
        self.aperture = None;
        self.distribution = Distribution::default();
        self.at_pin = None;
    }

    /// `output_path` is the selected owned result, not an arbitrary opened TIFF.
    /// Absence, malformed data, and uncertified dimensions leave the control
    /// visibly unavailable and never paint an uncertified map.
    pub(crate) fn update(
        &mut self,
        ctx: &egui::Context,
        output_path: Option<&Path>,
        expected_analysis: Option<[usize; 2]>,
    ) {
        let key = output_path.zip(expected_analysis).and_then(|(path, size)| {
            valid_size(size).then(|| Key {
                output: path.to_owned(),
                size,
            })
        });
        if self.key != key {
            self.invalidate();
            self.key = key;
        }
        self.poll(ctx);
        if self.pending.is_none()
            && !self.attempted
            && let Some(key) = self.key.clone()
        {
            self.attempted = true;
            let obsolete = Arc::new(AtomicBool::new(false));
            let worker_obsolete = Arc::clone(&obsolete);
            let worker_key = key.clone();
            let repaint = ctx.clone();
            let task = jobs::spawn_task("strehl-observation-balance", move |cancelled| {
                let result = decode(
                    &worker_key.output.with_file_name("confidence.tiff"),
                    worker_key.size,
                    &cancelled,
                    &worker_obsolete,
                );
                repaint.request_repaint();
                result
            });
            self.pending = Some(Pending {
                key,
                obsolete,
                task,
            });
        }
        if self.pending.is_some() {
            ctx.request_repaint_after(Duration::from_millis(50));
        }
    }

    fn poll(&mut self, ctx: &egui::Context) {
        let Some(pending) = &self.pending else {
            return;
        };
        let result = match pending.task.receiver.try_recv() {
            Ok(result) => Some(result),
            Err(TryRecvError::Disconnected) => None,
            Err(TryRecvError::Empty) => return,
        };
        let pending = self.pending.take().expect("pending receiver was present");
        if self.key.as_ref() != Some(&pending.key) || pending.obsolete.load(Ordering::Relaxed) {
            return;
        }
        if let Some(Ok(decoded)) = result {
            let texture = ctx.load_texture(
                "observation-balance",
                decoded.image,
                TextureOptions::NEAREST,
            );
            self.loaded = Some(Loaded {
                size: decoded.size,
                values: decoded.values,
                texture,
                window: PixelWindow::full(decoded.size),
            });
            // Publication runs after the photograph has painted. The worker's
            // wake-up can precede channel delivery, so this newly visible state
            // needs its own next paint even with a stationary pointer.
            ctx.request_repaint();
        }
    }

    pub(crate) fn ready(&self) -> bool {
        self.loaded.is_some()
    }

    pub(crate) fn enabled(&self) -> bool {
        self.enabled && self.ready()
    }

    pub(crate) fn set_enabled(&mut self, enabled: bool) {
        self.enabled = enabled && self.ready();
    }

    /// Exact stored value at a certified final-image UV; missing stays unknown.
    pub(crate) fn reading_at(&self, uv: Pos2) -> Option<u16> {
        let loaded = self.loaded.as_ref()?;
        value_at(&loaded.values, loaded.size, uv)
    }

    /// Returns true only when the toggle changed. Fits a 120x24 caption slot;
    /// the expanded histogram and exact pin reading live in its local tooltip.
    pub(crate) fn control(&mut self, ui: &mut Ui, rect: Rect) -> bool {
        if rect.width() < 90.0 || rect.height() < 20.0 {
            return false;
        }
        if !self.ready() {
            let label = if rect.width() < 145.0 {
                if self.pending.is_some() {
                    "Confidence · …"
                } else {
                    "Confidence · —"
                }
            } else if self.pending.is_some() {
                "Confidence · loading"
            } else {
                "Confidence · unavailable"
            };
            let p = ui.painter_at(rect);
            p.text(
                rect.left_center() + egui::vec2(4.0, 0.0),
                Align2::LEFT_CENTER,
                label,
                FontId::proportional(9.0),
                theme::MUTED,
            );
            ui.interact(rect, ui.id().with("confidence-unavailable"), Sense::hover())
                .on_hover_text(if self.pending.is_some() { "Loading the saved confidence map and checking its image dimensions." } else { "This result has no usable confidence map: it may be absent, unreadable or belong to another image domain. New stacks save it by default; for a reopened stack enable Save confidence map in Adjust, then Stack. The map measures observation balance, not image quality." });
            return false;
        }
        let response = ui.interact(rect, ui.id().with("observation-balance"), Sense::click());
        let changed = response.clicked();
        if changed {
            self.set_enabled(!self.enabled);
        }
        let p = ui.painter_at(rect);
        if response.hovered() || self.enabled {
            p.rect_filled(rect, 0.0, theme::RAISED);
        }
        let wide = rect.width() >= 280.0;
        let label_width = if wide { 145.0 } else { 78.0 };
        p.text(
            rect.left_center() + egui::vec2(4.0, 0.0),
            Align2::LEFT_CENTER,
            if wide {
                "Confidence · balance"
            } else {
                "Confidence"
            },
            FontId::proportional(10.0),
            if self.enabled { BLUE } else { theme::MUTED },
        );
        let histogram = Rect::from_min_max(
            egui::pos2(rect.left() + label_width, rect.top() + 4.0),
            rect.right_bottom() - egui::vec2(4.0, 4.0),
        );
        paint_histogram(&p, histogram, &self.distribution);
        if self.enabled {
            theme::rule(&p, rect.left_bottom(), rect.right_bottom(), BLUE);
        }
        response.on_hover_ui(|ui| {
            ui.set_max_width(310.0);
            ui.strong("Confidence map · observation balance");
            ui.label(if self.enabled { "Click to hide the lens" } else { "Click to show the lens" });
            let (rect, _) = ui.allocate_exact_size(egui::vec2(280.0, 48.0), Sense::hover());
            paint_histogram(ui.painter(), rect.shrink2(egui::vec2(0.0, 7.0)), &self.distribution);
            ui.horizontal(|ui| {
                ui.label("0 · one-sided");
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    ui.label("balanced · 1000");
                });
            });
            ui.label(format!(
                "At crosshair: {} · view samples: {} observed, {} missing",
                self.at_pin.map_or_else(|| "unobserved".into(), |v| v.to_string()),
                self.distribution.observed,
                self.distribution.missing,
            ));
            ui.label("Counts below versus at-or-above the merged green-luma value. Ties are at-or-above: identical observations also read 0.");
            ui.label("Neither end is a quality grade. Direction, distance, source identity and observation count are absent from this map. It does not certify warp support.");
            ui.label("Fixed 0–1000 colors; transparent means missing. The lens refines the visible region up to 1024 pixels per side as you zoom. The histogram samples this view; the crosshair reads its exact stored value.");
        });
        changed
    }

    /// Call on the certified final photograph even while the lens is hidden,
    /// so its readout follows the same aperture and normalized crosshair.
    pub(crate) fn paint(&mut self, painter: &Painter, image: Rect, aperture: Rect, pin: Pos2) {
        let enabled = self.enabled();
        let Some(loaded) = &mut self.loaded else {
            return;
        };
        let Some(aperture) = normalized(aperture) else {
            self.at_pin = None;
            self.aperture = None;
            self.distribution = Distribution::default();
            return;
        };
        if self.aperture != Some(aperture) {
            self.distribution = distribution(&loaded.values, loaded.size, aperture);
            self.aperture = Some(aperture);
        }
        self.at_pin = value_at(&loaded.values, loaded.size, pin);
        if enabled && finite_rect(image) {
            let window = PixelWindow::enclosing(loaded.size, aperture);
            if window != loaded.window {
                // Bounded in-memory refinement, with no source IO. Subpixel
                // motion within the same enclosing pixels only changes UV.
                loaded.texture.set(
                    texture_for(&loaded.values, loaded.size, window),
                    TextureOptions::NEAREST,
                );
                loaded.window = window;
            }
            painter
                .with_clip_rect(painter.clip_rect().intersect(image))
                .image(
                    loaded.texture.id(),
                    image,
                    window.uv(loaded.size, aperture),
                    Color32::WHITE,
                );
        }
    }
}

fn valid_size(size: [usize; 2]) -> bool {
    size.iter().all(|&n| n > 0 && n <= MAX_SIDE)
        && size[0]
            .checked_mul(size[1])
            .is_some_and(|n| n <= MAX_PIXELS)
}

fn reader(path: &Path) -> Result<ImageReader<std::io::BufReader<std::fs::File>>> {
    let mut reader = ImageReader::open(path)?.with_guessed_format()?;
    let mut limits = image::Limits::default();
    limits.max_image_width = Some(MAX_SIDE as u32);
    limits.max_image_height = Some(MAX_SIDE as u32);
    limits.max_alloc = Some(MAX_DECODE_BYTES);
    reader.limits(limits);
    Ok(reader)
}

fn decode(
    path: &Path,
    expected: [usize; 2],
    cancelled: &AtomicBool,
    obsolete: &AtomicBool,
) -> Result<Decoded> {
    let check = || {
        ensure!(
            !cancelled.load(Ordering::Relaxed) && !obsolete.load(Ordering::Relaxed),
            "Balance load cancelled"
        );
        Ok::<_, anyhow::Error>(())
    };
    check()?;
    ensure!(valid_size(expected), "Invalid balance analysis domain");
    let header = reader(path)?;
    ensure!(
        header.format() == Some(ImageFormat::Tiff),
        "Balance map is not TIFF"
    );
    let dimensions = header.into_dimensions().context("Balance dimensions")?;
    ensure!(
        [dimensions.0 as usize, dimensions.1 as usize] == expected,
        "Balance dimensions differ from the analysis domain"
    );
    check()?;
    let DynamicImage::ImageLuma16(image) = reader(path)?.decode()? else {
        anyhow::bail!("Balance map must be single-channel 16-bit TIFF");
    };
    ensure!(
        [image.width() as usize, image.height() as usize] == expected,
        "Balance dimensions changed during loading"
    );
    let values = image.into_raw();
    for chunk in values.chunks(16_384) {
        check()?;
        ensure!(
            chunk.iter().all(|&v| v <= 1000 || v == MISSING),
            "Balance map contains an invalid rank"
        );
    }
    check()?;
    let image = texture_for(&values, expected, PixelWindow::full(expected));
    check()?;
    Ok(Decoded {
        size: expected,
        values,
        image,
    })
}

fn texture_for(values: &[u16], size: [usize; 2], window: PixelWindow) -> ColorImage {
    let extent = window.extent();
    let texture_size = sampled_size(extent, TEXTURE_SIDE);
    let colors: [Color32; 1001] = std::array::from_fn(|value| {
        let color = palette(value as u16);
        Color32::from_rgba_unmultiplied(color.r(), color.g(), color.b(), 108)
    });
    let mut pixels = Vec::with_capacity(texture_size[0] * texture_size[1]);
    for y in 0..texture_size[1] {
        let source_y = window.min[1] + sample_index(y, texture_size[1], extent[1]);
        for x in 0..texture_size[0] {
            let source_x = window.min[0] + sample_index(x, texture_size[0], extent[0]);
            let value = values[source_y * size[0] + source_x];
            pixels.push(
                colors
                    .get(usize::from(value))
                    .copied()
                    .unwrap_or(Color32::TRANSPARENT),
            );
        }
    }
    ColorImage::new(texture_size, pixels)
}

fn sampled_size(size: [usize; 2], side: usize) -> [usize; 2] {
    let longest = size[0].max(size[1]);
    size.map(|n| {
        if longest <= side {
            n
        } else {
            (n * side / longest).max(1)
        }
    })
}

fn sample_index(index: usize, count: usize, extent: usize) -> usize {
    ((2 * index + 1) * extent / (2 * count)).min(extent - 1)
}

fn palette(value: u16) -> Color32 {
    if value == MISSING {
        return Color32::TRANSPARENT;
    }
    let t = f32::from(value) / 1000.0;
    let channel = |a: u8, b: u8| (f32::from(a) + (f32::from(b) - f32::from(a)) * t).round() as u8;
    Color32::from_rgb(
        channel(BLUE.r(), SAND.r()),
        channel(BLUE.g(), SAND.g()),
        channel(BLUE.b(), SAND.b()),
    )
}

fn finite_rect(rect: Rect) -> bool {
    [rect.min.x, rect.min.y, rect.max.x, rect.max.y]
        .iter()
        .all(|n| n.is_finite())
        && rect.is_positive()
}

fn normalized(rect: Rect) -> Option<Rect> {
    if !finite_rect(rect)
        || rect.min.x < 0.0
        || rect.min.y < 0.0
        || rect.max.x > 1.0
        || rect.max.y > 1.0
    {
        return None;
    }
    // Clamping an invalid UV while keeping the original screen rectangle
    // would silently stretch the map relative to the photograph.
    Some(rect)
}

fn value_at(values: &[u16], size: [usize; 2], uv: Pos2) -> Option<u16> {
    if !uv.x.is_finite()
        || !uv.y.is_finite()
        || !(0.0..=1.0).contains(&uv.x)
        || !(0.0..=1.0).contains(&uv.y)
    {
        return None;
    }
    let x = ((uv.x * size[0] as f32) as usize).min(size[0] - 1);
    let y = ((uv.y * size[1] as f32) as usize).min(size[1] - 1);
    values.get(y * size[0] + x).copied().filter(|&v| v <= 1000)
}

fn distribution(values: &[u16], size: [usize; 2], aperture: Rect) -> Distribution {
    let mut result = Distribution::default();
    let Some(aperture) = normalized(aperture) else {
        return result;
    };
    let start = [aperture.min.x, aperture.min.y];
    let end = [aperture.max.x, aperture.max.y];
    let lower: [usize; 2] = std::array::from_fn(|axis| {
        (start[axis] * size[axis] as f32 - 0.5).ceil().max(0.0) as usize
    });
    let upper: [usize; 2] = std::array::from_fn(|axis| {
        ((end[axis] * size[axis] as f32 - 0.5).ceil().max(0.0) as usize).min(size[axis])
    });
    let extent: [usize; 2] = std::array::from_fn(|axis| upper[axis].saturating_sub(lower[axis]));
    if extent.contains(&0) {
        return result;
    }
    let samples = extent.map(|n| n.min(HISTOGRAM_SIDE));
    for y in 0..samples[1] {
        let y = lower[1] + sample_index(y, samples[1], extent[1]);
        for x in 0..samples[0] {
            let x = lower[0] + sample_index(x, samples[0], extent[0]);
            match values.get(y * size[0] + x).copied() {
                Some(v @ 0..=1000) => {
                    result.bins[(usize::from(v) * BINS / 1000).min(BINS - 1)] += 1;
                    result.observed += 1;
                }
                _ => result.missing += 1,
            }
        }
    }
    result
}

fn paint_histogram(painter: &Painter, rect: Rect, distribution: &Distribution) {
    if !finite_rect(rect) {
        return;
    }
    let p = painter.with_clip_rect(painter.clip_rect().intersect(rect));
    let max = distribution.bins.iter().copied().max().unwrap_or(0).max(1) as f32;
    let width = rect.width() / BINS as f32;
    for (i, &count) in distribution.bins.iter().enumerate() {
        let left = rect.left() + i as f32 * width;
        let bar = Rect::from_min_max(
            egui::pos2(left, rect.bottom() - rect.height() * count as f32 / max),
            egui::pos2(left + (width - 0.5).max(0.25), rect.bottom()),
        );
        p.rect_filled(bar, 0.0, palette((i * 1000 / (BINS - 1)) as u16));
    }
    theme::rule(&p, rect.left_bottom(), rect.right_bottom(), theme::LINE);
}

#[cfg(test)]
#[path = "process-balance-tests.rs"]
mod tests;
