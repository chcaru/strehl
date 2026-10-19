//! A bounded, progressive camera-preview browser.
//!
//! Selection and display are deliberately separate: a missed cache lookup must
//! never remove a photograph that is already on screen. The UI can name both
//! frames while the newest request is being prepared. One detail decoder and
//! one filmstrip batch can run, including across imports. A large preview can
//! never block a visible strip, and scrubbing cannot multiply decoder threads.

use std::{
    collections::{BTreeMap, BTreeSet, VecDeque},
    path::PathBuf,
    sync::mpsc::TryRecvError,
    time::{Duration, Instant},
};

use eframe::egui::{self, TextureHandle};

use crate::{
    jobs::{FrameFile, Task},
    preview::PreviewImage,
    source_preview::{self, FilmstripBatch, SourcePreview},
    viewer::Viewer,
};

const THUMB_SIDE: u32 = 240;
const OVERVIEW_SIDE: u32 = 960;
const OVERVIEW_RADIUS: usize = 4;
// Selected photograph + its bidirectional trajectory + two distant probes.
// Eleven worst-case square overviews fit the existing 40 MiB byte budget.
const OVERVIEW_COUNT: usize = OVERVIEW_RADIUS * 2 + 3;
const OVERVIEW_BYTES: usize = 40 * 1024 * 1024;
// Canonical camera crops for immediate whole-stack scrubbing. The resolution
// adapts to stack length using a square-image bound, never optimistic aspect
// ratios. Refined overviews/details retain their independent quality tiers.
const SCRUB_SIDE: u32 = 640;
const SCRUB_COUNT: usize = 512;
const SCRUB_BYTES: usize = 192 * 1024 * 1024;
const SCRUB_BATCH: usize = 4;
const SCRUB_UPLOAD_BYTES: usize = 2 * 1024 * 1024;
const SCRUB_IDLE: Duration = Duration::from_millis(180);
const IMAGE_SIDE: u32 = 1_920;
const IMAGE_COUNT: usize = 6;
const IMAGE_BYTES: usize = 48 * 1024 * 1024;
// Keep every native contact alongside the resident scrub tier. Even512 square
// 240px contacts occupy only112.5 MiB, below this independent byte ceiling.
const THUMB_COUNT: usize = 512;
const THUMB_BYTES: usize = 128 * 1024 * 1024;
const ERROR_COUNT: usize = 256;
// A resized capture board can expose 48 photographs beside the source dock,
// capture axis and pair endpoints. The visible set plus the 81-frame trajectory
// still fits the worst-case square thumbnail budget without eviction churn.
const VISIBLE_WARM_COUNT: usize = 96;
const SETTLE: Duration = Duration::from_millis(90);

#[derive(Clone)]
struct CachedImage {
    texture: TextureHandle,
    source_size: [u32; 2],
    overview: bool,
    bytes: usize,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
enum Kind {
    Thumbnail,
    Scrub,
    Overview,
    Image,
}

struct Work {
    epoch: u64,
    index: usize,
    kind: Kind,
    task: Task<SourcePreview>,
}

struct FilmWork {
    epoch: u64,
    indices: Vec<usize>,
    kind: Kind,
    task: Task<FilmstripBatch>,
}

pub struct SourceBrowser {
    epoch: u64,
    requested: Option<usize>,
    displayed: Option<(usize, Kind)>,
    requested_at: Instant,
    direction: isize,
    work: Option<Work>,
    film_work: Option<FilmWork>,
    warm_thumbs: Vec<usize>,
    images: BTreeMap<usize, CachedImage>,
    overviews: BTreeMap<usize, CachedImage>,
    scrubs: BTreeMap<usize, CachedImage>,
    scrub_window: std::ops::Range<usize>,
    scrub_pending: VecDeque<(usize, SourcePreview)>,
    scrub_side: u32,
    scrub_failures: BTreeSet<usize>,
    thumbs: BTreeMap<usize, CachedImage>,
    errors: BTreeMap<(usize, Kind), String>,
    probe_frames: [Option<usize>; 2],
    live_frame: Option<usize>,
}

impl Default for SourceBrowser {
    fn default() -> Self {
        Self {
            epoch: 0,
            requested: None,
            displayed: None,
            requested_at: Instant::now(),
            direction: 1,
            work: None,
            film_work: None,
            warm_thumbs: Vec::new(),
            images: BTreeMap::new(),
            overviews: BTreeMap::new(),
            scrubs: BTreeMap::new(),
            scrub_window: 0..0,
            scrub_pending: VecDeque::new(),
            scrub_side: SCRUB_SIDE,
            scrub_failures: BTreeSet::new(),
            thumbs: BTreeMap::new(),
            errors: BTreeMap::new(),
            probe_frames: [None, None],
            live_frame: None,
        }
    }
}

impl SourceBrowser {
    /// Retain the old task until it returns, but make its delivery ineligible.
    /// The caller clears its Viewer when changing brackets.
    pub fn reset(&mut self, epoch: u64) {
        if let Some(work) = &self.work {
            work.task.cancel();
        }
        if let Some(work) = &self.film_work {
            work.task.cancel();
        }
        self.epoch = epoch;
        self.requested = None;
        self.displayed = None;
        self.images.clear();
        self.overviews.clear();
        self.scrubs.clear();
        self.scrub_window = 0..0;
        self.scrub_pending.clear();
        self.scrub_failures.clear();
        self.thumbs.clear();
        self.errors.clear();
        self.probe_frames = [None, None];
        self.live_frame = None;
        self.warm_thumbs.clear();
    }

    pub fn set_probe_frames(&mut self, frames: [Option<usize>; 2]) {
        self.probe_frames = frames;
    }

    pub fn set_live_frame(&mut self, frame: Option<usize>) {
        self.live_frame = frame;
    }

    /// A snapshot retains the actual bracket epoch and frame identity. Its
    /// aperture is the canonical largest embedded-JPEG size, not sensor RAW
    /// dimensions. Filmstrip-only textures are ineligible; a genuinely small
    /// overview decoded from a small source is still valid. Callers must not
    /// attach a requested index to a fallback.
    pub fn texture_snapshot(&self, index: usize) -> Option<(u64, TextureHandle, [u32; 2])> {
        self.images
            .get(&index)
            .or_else(|| self.overviews.get(&index))
            .or_else(|| self.scrubs.get(&index))
            .map(|image| (self.epoch, image.texture.clone(), image.source_size))
    }

    /// Canonical photographs available for same-paint inspection. Native
    /// contact residency is independent and must not truncate this set on
    /// stacks larger than the filmstrip's bounded texture budget.
    pub fn canonical_indices(&self) -> Vec<usize> {
        self.images
            .keys()
            .chain(self.overviews.keys())
            .chain(self.scrubs.keys())
            .copied()
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect()
    }

    pub fn select(&mut self, index: usize, viewer: &mut Viewer) {
        self.select_at(index, viewer, Instant::now());
    }

    fn select_at(&mut self, index: usize, viewer: &mut Viewer, now: Instant) {
        if self.requested != Some(index) {
            viewer.cancel_reveal();
            if let Some(previous) = self.requested {
                self.direction = if index >= previous { 1 } else { -1 };
            }
            self.requested = Some(index);
            self.requested_at = now;
        }
        self.install_selected(viewer);
    }

    pub fn displayed_index(&self) -> Option<usize> {
        self.displayed.map(|(index, _)| index)
    }

    /// A previous capture remains on screen until the requested one is ready.
    pub fn pending(&self) -> bool {
        self.requested.is_some() && self.requested != self.displayed_index()
    }

    /// The requested capture is visible, with its small JPEG being refined.
    pub fn refining(&self) -> bool {
        !self.pending()
            && self.displayed.is_some_and(|(index, kind)| {
                matches!(kind, Kind::Scrub | Kind::Overview) && self.missing(index, Kind::Image)
            })
    }

    pub fn active(&self) -> bool {
        self.work.is_some() || self.film_work.is_some() || !self.scrub_pending.is_empty()
    }

    pub fn error(&self, index: usize) -> Option<&str> {
        if self.images.contains_key(&index) {
            return None;
        }
        if let Some(error) = self.errors.get(&(index, Kind::Image)) {
            return Some(error);
        }
        if self.overviews.contains_key(&index) || self.scrubs.contains_key(&index) {
            return None;
        }
        self.errors
            .get(&(index, Kind::Overview))
            .or_else(|| self.errors.get(&(index, Kind::Thumbnail)))
            .map(String::as_str)
    }

    pub fn thumbnail(&self, index: usize) -> Option<&TextureHandle> {
        self.thumbs
            .get(&index)
            .or_else(|| self.overviews.get(&index))
            .or_else(|| self.images.get(&index))
            .map(|image| &image.texture)
    }

    /// Contact-lane pixels only. Unlike `thumbnail`, this never substitutes an
    /// overview or a full image, so a retained contact cannot hold a large tier.
    pub fn native_thumbnail(&self, index: usize) -> Option<&TextureHandle> {
        self.thumbs.get(&index).map(|image| &image.texture)
    }

    pub fn native_thumbnail_indices(&self) -> Vec<usize> {
        self.thumbs.keys().copied().collect()
    }

    /// A contact failure remains visible even when a higher tier succeeded.
    pub fn native_thumbnail_error(&self, index: usize) -> Option<&str> {
        self.errors
            .get(&(index, Kind::Thumbnail))
            .map(String::as_str)
    }

    pub fn has_image(&self, index: usize) -> bool {
        self.images.contains_key(&index)
    }

    pub fn has_thumbnail(&self, index: usize) -> bool {
        self.thumbnail(index).is_some()
    }

    /// Enumerate bounded cached photos for the stack map without walking the
    /// source list. Current visible/trajectory cells survive any truncation.
    pub fn thumbnail_indices(&self) -> Vec<usize> {
        let mut indices: Vec<_> = self
            .thumbs
            .keys()
            .chain(self.overviews.keys())
            .chain(self.images.keys())
            .copied()
            .collect();
        indices.sort_unstable();
        indices.dedup();
        if indices.len() > THUMB_COUNT {
            let selected = self.requested.unwrap_or(0);
            indices.sort_unstable_by_key(|index| {
                (!self.warm_thumbs.contains(index), index.abs_diff(selected))
            });
            indices.truncate(THUMB_COUNT);
            indices.sort_unstable();
        }
        indices
    }

    /// Poll on every UI update, even during a scan (pass an empty frame slice).
    #[allow(clippy::too_many_arguments)]
    pub fn poll(
        &mut self,
        ctx: &egui::Context,
        epoch: u64,
        selected: usize,
        frames: &[FrameFile],
        visible: &[usize],
        max_texture_side: u32,
        viewer: &mut Viewer,
    ) {
        self.poll_with(
            ctx,
            epoch,
            selected,
            frames,
            visible,
            max_texture_side,
            viewer,
            Instant::now(),
            |path, side, kind, thumbnail| {
                source_preview::load_browser_preview(
                    path,
                    side,
                    kind == Kind::Overview,
                    thumbnail.then_some(THUMB_SIDE),
                )
            },
            |paths, side, kind, thumbnail| match kind {
                Kind::Scrub => {
                    source_preview::load_scrub_batch(paths, side, thumbnail.then_some(THUMB_SIDE))
                }
                Kind::Overview => source_preview::load_overview_batch(
                    paths,
                    side,
                    thumbnail.then_some(THUMB_SIDE),
                ),
                _ => source_preview::load_filmstrip_batch(paths, side),
            },
        );
    }

    #[allow(clippy::too_many_arguments)]
    fn poll_with(
        &mut self,
        ctx: &egui::Context,
        epoch: u64,
        selected: usize,
        frames: &[FrameFile],
        visible: &[usize],
        max_texture_side: u32,
        viewer: &mut Viewer,
        now: Instant,
        mut load: impl FnMut(PathBuf, u32, Kind, bool) -> Task<SourcePreview>,
        mut load_film: impl FnMut(Vec<(usize, PathBuf)>, u32, Kind, bool) -> Task<FilmstripBatch>,
    ) {
        if epoch != self.epoch {
            self.reset(epoch);
        }
        if selected < frames.len() {
            self.scrub_side = scrub_side(frames.len()).min(max_texture_side.max(1));
            self.select_at(selected, viewer, now);
            if !cache_covers_range(&self.thumbs, &(0..frames.len())) {
                self.warm_thumbs = self.thumbnail_targets(frames.len(), visible);
            }
            self.retire_obsolete_work(selected);
        }
        let delivery = self
            .work
            .as_ref()
            .and_then(|work| match work.task.receiver.try_recv() {
                Ok(result) => Some(result),
                Err(TryRecvError::Disconnected) => {
                    Some(Err("The camera preview worker stopped unexpectedly".into()))
                }
                Err(TryRecvError::Empty) => None,
            });
        if let Some(delivery) = delivery {
            let work = self.work.take().expect("delivery belongs to a task");
            if work.epoch == self.epoch && !work.task.is_cancelled() {
                match delivery {
                    Ok(preview) => {
                        if !self.thumbs.contains_key(&work.index)
                            && let Some(thumbnail) = preview.thumbnail
                        {
                            self.thumbs
                                .insert(work.index, cache_image(ctx, thumbnail, Kind::Thumbnail));
                            self.errors.remove(&(work.index, Kind::Thumbnail));
                        }
                        let cached = cache_image(ctx, preview.image, work.kind);
                        let cache = match work.kind {
                            Kind::Image => &mut self.images,
                            Kind::Overview => &mut self.overviews,
                            Kind::Scrub => &mut self.scrubs,
                            Kind::Thumbnail => &mut self.thumbs,
                        };
                        cache.insert(work.index, cached);
                        self.errors.remove(&(work.index, work.kind));
                        self.install_selected(viewer);
                        self.trim();
                    }
                    Err(error) => {
                        self.errors.insert((work.index, work.kind), error);
                    }
                }
            }
        }

        let film_delivery =
            self.film_work
                .as_ref()
                .and_then(|work| match work.task.receiver.try_recv() {
                    Ok(result) => Some(result),
                    Err(TryRecvError::Disconnected) => {
                        Some(Err("The filmstrip worker stopped unexpectedly".into()))
                    }
                    Err(TryRecvError::Empty) => None,
                });
        if let Some(delivery) = film_delivery {
            let work = self
                .film_work
                .take()
                .expect("delivery belongs to a filmstrip batch");
            if work.epoch == self.epoch && !work.task.is_cancelled() {
                let (images, failure) = match delivery {
                    Ok(images) => (images, None),
                    Err(error) => (Vec::new(), Some(error)),
                };
                let mut images: BTreeMap<_, _> = images.into_iter().collect();
                for index in work.indices {
                    match images.remove(&index).unwrap_or_else(|| {
                        Err(failure.clone().unwrap_or_else(|| {
                            "The filmstrip worker did not return this frame".into()
                        }))
                    }) {
                        Ok(preview) => {
                            // A detail derivative may have arrived first. Do
                            // not replace its established thumbnail geometry.
                            if work.kind == Kind::Scrub {
                                self.scrub_pending.push_back((index, preview));
                            } else if work.kind == Kind::Overview {
                                if let Some(thumbnail) = preview.thumbnail {
                                    self.thumbs.entry(index).or_insert_with(|| {
                                        cache_image(ctx, thumbnail, Kind::Thumbnail)
                                    });
                                }
                                self.overviews
                                    .insert(index, cache_image(ctx, preview.image, Kind::Overview));
                            } else {
                                self.thumbs.entry(index).or_insert_with(|| {
                                    cache_image(ctx, preview.image, Kind::Thumbnail)
                                });
                            }
                            if work.kind != Kind::Scrub {
                                self.errors.remove(&(index, Kind::Thumbnail));
                            }
                            self.errors.remove(&(index, work.kind));
                        }
                        Err(error) => {
                            if work.kind == Kind::Scrub {
                                // Whole-stack warming has its own bounded
                                // failure set. The smaller foreground error
                                // log must not evict these identities and make
                                // a large damaged stack decode forever.
                                // A useful old batch may finish after the
                                // resident window moved. Its late failures
                                // must not outlive the window that requested it.
                                if self.scrub_range(frames.len()).contains(&index) {
                                    self.scrub_failures.insert(index);
                                }
                            } else {
                                self.errors.insert((index, work.kind), error);
                            }
                        }
                    }
                }
                self.install_selected(viewer);
                self.trim();
            }
        }
        if self.upload_scrubs(ctx, selected, frames.len()) {
            self.install_selected(viewer);
        }
        self.trim_errors(selected);

        if self.work.is_none()
            && selected < frames.len()
            && let Some((index, kind)) = self.next_detail(frames.len(), now)
        {
            let side = match kind {
                Kind::Thumbnail => THUMB_SIDE,
                Kind::Scrub => self.scrub_side,
                Kind::Overview => OVERVIEW_SIDE,
                Kind::Image => IMAGE_SIDE,
            }
            .min(max_texture_side.max(1));
            self.work = Some(Work {
                epoch,
                index,
                kind,
                // Native contacts already in cache need no second resize or
                // allocation when their canonical image is refined.
                task: load(
                    frames[index].path.clone(),
                    side,
                    kind,
                    !self.thumbs.contains_key(&index),
                ),
            });
        }

        if self.film_work.is_none() && selected < frames.len() {
            let rescue = self.missing(selected, Kind::Overview)
                && !self.scrubs.contains_key(&selected)
                && self.work.as_ref().is_some_and(|work| {
                    work.epoch != epoch
                        || work.index != selected
                        || work.kind != Kind::Overview
                        || work.task.is_cancelled()
                });
            let (mut indices, mut kind) = if rescue {
                (vec![selected], Kind::Overview)
            } else {
                (
                    self.next_filmstrip(frames.len(), visible, now),
                    Kind::Thumbnail,
                )
            };
            if indices.is_empty()
                && self.scrub_pending.is_empty()
                && now.saturating_duration_since(self.requested_at) >= SCRUB_IDLE
            {
                indices = self.next_scrubs(frames.len());
                kind = Kind::Scrub;
            }
            if !indices.is_empty() {
                let thumbnail = match kind {
                    Kind::Overview => !self.thumbs.contains_key(&selected),
                    Kind::Scrub => indices.iter().any(|index| !self.thumbs.contains_key(index)),
                    _ => false,
                };
                let paths = indices
                    .iter()
                    .map(|&index| (index, frames[index].path.clone()))
                    .collect();
                let side = match kind {
                    Kind::Overview => OVERVIEW_SIDE,
                    Kind::Scrub => self.scrub_side,
                    _ => THUMB_SIDE,
                };
                self.film_work = Some(FilmWork {
                    epoch,
                    indices,
                    kind,
                    task: load_film(paths, side.min(max_texture_side.max(1)), kind, thumbnail),
                });
            }
        }

        // A cached small image needs another UI turn after the settling period,
        // even when no decoder is currently running.
        if self.active()
            || (self.refining() && self.missing(selected, Kind::Image))
            || (selected < frames.len()
                && !cache_covers_range(&self.scrubs, &self.scrub_range(frames.len()))
                && self
                    .scrub_range(frames.len())
                    .any(|index| self.missing(index, Kind::Scrub)))
        {
            ctx.request_repaint_after(Duration::from_millis(16));
        }
    }

    fn missing(&self, index: usize, kind: Kind) -> bool {
        let cache = match kind {
            Kind::Thumbnail => &self.thumbs,
            Kind::Overview => &self.overviews,
            Kind::Scrub => &self.scrubs,
            Kind::Image => &self.images,
        };
        // A large image may satisfy its canonical overview, but it cannot
        // satisfy a contact-lane request after the small texture was evicted.
        !cache.contains_key(&index)
            && !(kind == Kind::Overview && self.images.contains_key(&index))
            && !(kind == Kind::Scrub && self.scrub_failures.contains(&index))
            && !self.errors.contains_key(&(index, kind))
    }

    /// A newly requested canvas outranks speculative detail and contacts from
    /// a distant position. Cancellation retains the task until its codec and
    /// all batch workers really return, so repeated pointer moves never create
    /// additional decoder lanes. Nearby overviews remain useful on reversal.
    fn retire_obsolete_work(&self, selected: usize) {
        // Whole-stack warming is useful across pointer moves, but a genuinely
        // cold foreground must not wait behind it. The cancelled batch still
        // owns its worker lane until every codec returns.
        if self.missing(selected, Kind::Overview)
            && self.missing(selected, Kind::Scrub)
            && let Some(work) = &self.film_work
            && work.kind == Kind::Scrub
            && !work.indices.contains(&selected)
        {
            work.task.cancel();
        }
        // A process hover is a real foreground request even when its overview
        // is already cached. Do not make its refinement wait for an obsolete
        // large decode. Probe pins require canonical overviews, not refinement.
        if self.missing(selected, Kind::Image)
            && let Some(work) = &self.work
            && work.index != selected
            && work.kind == Kind::Image
        {
            work.task.cancel();
        }
        if !self.missing(selected, Kind::Overview) {
            return;
        }
        let useful_overview = |index: usize| {
            index.abs_diff(selected) <= OVERVIEW_RADIUS || self.probe_frames.contains(&Some(index))
        };
        if let Some(work) = &self.work
            && work.index != selected
            && !self.probe_frames.contains(&Some(work.index))
            && (work.kind == Kind::Image || !useful_overview(work.index))
        {
            work.task.cancel();
        }
        if let Some(work) = &self.film_work {
            let useful = match work.kind {
                Kind::Scrub => true,
                Kind::Overview => work.indices.iter().any(|&index| useful_overview(index)),
                _ => work
                    .indices
                    .iter()
                    .any(|index| self.warm_thumbs.contains(index)),
            };
            if !useful {
                work.task.cancel();
            }
        }
    }

    fn next_detail(&self, count: usize, now: Instant) -> Option<(usize, Kind)> {
        let selected = self.requested?;
        let settled = now.saturating_duration_since(self.requested_at) >= SETTLE;
        if !settled && self.scrubs.contains_key(&selected) {
            // During a gesture the already resident canonical image follows
            // every pointer sample. Do not chase it with immediately obsolete
            // refinement decodes or uploads; refine where the gesture rests.
            return None;
        }
        if self.missing(selected, Kind::Overview) {
            if self.film_work.as_ref().is_some_and(|work| {
                work.epoch == self.epoch
                    && work.kind == Kind::Overview
                    && work.indices == [selected]
                    && !work.task.is_cancelled()
            }) {
                return None;
            }
            return Some((selected, Kind::Overview));
        }
        if let Some(index) = self
            .probe_frames
            .into_iter()
            .flatten()
            .filter(|&index| index < count)
            .find(|&index| self.missing(index, Kind::Overview))
        {
            return Some((index, Kind::Overview));
        }
        if self.missing(selected, Kind::Image)
            && (settled || self.errors.contains_key(&(selected, Kind::Overview)))
        {
            return Some((selected, Kind::Image));
        }

        if let Some(index) = neighborhood(selected, count, self.direction, OVERVIEW_RADIUS)
            .into_iter()
            .find(|&index| self.missing(index, Kind::Overview))
        {
            return Some((index, Kind::Overview));
        }

        if settled {
            // Selected + two immediate neighbors fit the byte budget even for
            // square 1920-pixel previews. A larger warming set could evict its
            // own entries and cause an endless decode/evict cycle.
            if let Some(index) = neighborhood(selected, count, self.direction, 1)
                .into_iter()
                .find(|&index| self.missing(index, Kind::Image))
            {
                return Some((index, Kind::Image));
            }
        }
        None
    }

    fn scrub_range(&self, count: usize) -> std::ops::Range<usize> {
        let capacity = count.min(SCRUB_COUNT);
        let selected = self.requested.unwrap_or(0).min(count.saturating_sub(1));
        let start = selected.saturating_sub(capacity / 2).min(count - capacity);
        start..start + capacity
    }

    fn next_scrubs(&self, count: usize) -> Vec<usize> {
        let Some(selected) = self.requested else {
            return Vec::new();
        };
        let range = self.scrub_range(count);
        if cache_covers_range(&self.scrubs, &range) {
            return Vec::new();
        }
        std::iter::once(Some(selected))
            .chain((1..=range.len()).flat_map(|distance| {
                [self.direction, -self.direction]
                    .map(|sign| selected.checked_add_signed(sign * distance as isize))
            }))
            .flatten()
            .filter(|index| range.contains(index) && self.missing(*index, Kind::Scrub))
            .take(SCRUB_BATCH)
            .collect()
    }

    fn upload_scrubs(&mut self, ctx: &egui::Context, selected: usize, count: usize) -> bool {
        let range = self.scrub_range(count);
        if self.scrub_window != range {
            self.scrubs.retain(|index, _| range.contains(index));
            self.scrub_failures.retain(|index| range.contains(index));
            self.scrub_window = range.clone();
        }
        if self.scrub_pending.is_empty() {
            return false;
        }
        self.scrub_pending
            .retain(|(index, _)| range.contains(index));
        // Foreground publication wins even when it completed in the middle of
        // the bounded worker batch. Unrelated ready images wait for their own
        // upload budget; they cannot turn a scrub into a four-texture hitch.
        if let Some(at) = self
            .scrub_pending
            .iter()
            .position(|(index, _)| *index == selected)
            && at != 0
            && let Some(image) = self.scrub_pending.remove(at)
        {
            self.scrub_pending.push_front(image);
        }
        let mut uploaded = 0;
        while let Some((index, preview)) = self.scrub_pending.front() {
            let bytes = preview.image.rgba.len()
                + preview
                    .thumbnail
                    .as_ref()
                    .filter(|_| !self.thumbs.contains_key(index))
                    .map_or(0, |thumbnail| thumbnail.rgba.len());
            if uploaded + bytes > SCRUB_UPLOAD_BYTES {
                break;
            }
            let (index, preview) = self.scrub_pending.pop_front().expect("ready scrub image");
            if self.scrubs.contains_key(&index) {
                continue;
            }
            uploaded += bytes;
            if !self.thumbs.contains_key(&index)
                && let Some(thumbnail) = preview.thumbnail
            {
                self.thumbs
                    .insert(index, cache_image(ctx, thumbnail, Kind::Thumbnail));
                self.errors.remove(&(index, Kind::Thumbnail));
            }
            self.scrubs
                .insert(index, cache_image(ctx, preview.image, Kind::Scrub));
        }
        if uploaded > 0 {
            self.trim();
        }
        uploaded > 0
    }

    fn bounded_visible(&self, count: usize, visible: &[usize]) -> Vec<usize> {
        let selected = self.requested.unwrap_or(0);
        let mut visible: Vec<_> = visible
            .iter()
            .copied()
            .filter(|&index| index < count)
            .collect();
        visible.sort_unstable_by_key(|index| index.abs_diff(selected));
        visible.dedup();
        visible.truncate(VISIBLE_WARM_COUNT);
        visible
    }

    fn thumbnail_targets(&self, count: usize, visible: &[usize]) -> Vec<usize> {
        let selected = self.requested.unwrap_or(0);
        let mut targets = self.bounded_visible(count, visible);
        targets.extend(self.live_frame.filter(|&index| index < count));
        targets.extend(
            self.probe_frames
                .into_iter()
                .flatten()
                .filter(|&index| index < count),
        );
        targets.push(selected);
        targets.extend(neighborhood(selected, count, self.direction, 40));
        targets.sort_unstable();
        targets.dedup();
        targets
    }

    fn next_filmstrip(&self, count: usize, visible: &[usize], now: Instant) -> Vec<usize> {
        let Some(selected) = self.requested else {
            return Vec::new();
        };
        if cache_covers_range(&self.thumbs, &(0..count)) {
            return Vec::new();
        }
        let mut candidates: Vec<_> = self
            .live_frame
            .filter(|&index| index < count)
            .into_iter()
            .collect();
        candidates.extend(self.bounded_visible(count, visible));
        candidates.extend(
            self.probe_frames
                .into_iter()
                .flatten()
                .filter(|&index| index < count),
        );
        let radius = if now.saturating_duration_since(self.requested_at) >= SETTLE {
            40
        } else {
            12
        };
        candidates.extend(neighborhood(selected, count, self.direction, radius));
        let mut indices = Vec::with_capacity(source_preview::FILMSTRIP_BATCH_MAX);
        for index in candidates {
            if self.missing(index, Kind::Thumbnail)
                && !indices.contains(&index)
                && !self
                    .work
                    .as_ref()
                    .is_some_and(|work| work.epoch == self.epoch && work.index == index)
            {
                indices.push(index);
                if indices.len() == source_preview::FILMSTRIP_BATCH_MAX {
                    break;
                }
            }
        }
        // Commit a contiguous visible neighborhood together, rather than
        // exposing completion order as a numbered, one-cell-at-a-time pop-in.
        indices.sort_unstable();
        indices
    }

    fn trim_errors(&mut self, selected: usize) {
        while self.errors.len() > ERROR_COUNT {
            let protected = |index: usize, kind: Kind| {
                (kind == Kind::Thumbnail && self.warm_thumbs.contains(&index))
                    || index.abs_diff(selected) <= 1
                    || self.probe_frames.contains(&Some(index))
            };
            let key = *self
                .errors
                .keys()
                .filter(|(index, kind)| !protected(*index, *kind))
                .max_by_key(|(index, _)| index.abs_diff(selected))
                .or_else(|| {
                    self.errors
                        .keys()
                        .max_by_key(|(index, _)| index.abs_diff(selected))
                })
                .expect("nonempty error cache");
            self.errors.remove(&key);
        }
    }

    fn install_selected(&mut self, viewer: &mut Viewer) {
        let Some(index) = self.requested else { return };
        let selected = self
            .images
            .get(&index)
            .map(|image| (image, Kind::Image))
            .or_else(|| {
                self.overviews
                    .get(&index)
                    .map(|image| (image, Kind::Overview))
            })
            .or_else(|| self.scrubs.get(&index).map(|image| (image, Kind::Scrub)));
        if let Some((image, kind)) = selected {
            if self.displayed == Some((index, kind))
                && viewer.has_source(&image.texture, (self.epoch, index))
            {
                return;
            }
            // Preserve inspection pan/zoom when moving between focus planes.
            // A small preview cannot truthfully offer a native-pixel view.
            viewer.install_source(
                &image.texture,
                image.source_size,
                image.overview || matches!(kind, Kind::Scrub | Kind::Overview),
                (self.epoch, index),
            );
            self.displayed = Some((index, kind));
        }
    }

    fn trim(&mut self) {
        let selected = self.requested.unwrap_or(0);
        trim_cache(&mut self.scrubs, selected, SCRUB_COUNT, SCRUB_BYTES);
        trim_cache(&mut self.images, selected, IMAGE_COUNT, IMAGE_BYTES);
        trim_cache_pinned(
            &mut self.overviews,
            selected,
            OVERVIEW_COUNT,
            OVERVIEW_BYTES,
            self.probe_frames,
        );
        trim_cache_protected(
            &mut self.thumbs,
            selected,
            THUMB_COUNT,
            THUMB_BYTES,
            &self.warm_thumbs,
        );
    }
}

/// A dense key range can be recognized without visiting every resident image.
/// Length alone is insufficient: a moving512-frame window can have equal size.
fn cache_covers_range(
    cache: &BTreeMap<usize, CachedImage>,
    range: &std::ops::Range<usize>,
) -> bool {
    cache.len() == range.len()
        && (range.is_empty()
            || (cache.first_key_value().map(|(&index, _)| index) == Some(range.start)
                && cache.last_key_value().map(|(&index, _)| index) == Some(range.end - 1)))
}

fn scrub_side(count: usize) -> u32 {
    let capacity = count.clamp(1, SCRUB_COUNT);
    let square_bound = ((SCRUB_BYTES / (capacity * 4)) as f64).sqrt() as u32;
    (square_bound / 16 * 16).clamp(256, SCRUB_SIDE)
}

fn trim_cache(
    cache: &mut BTreeMap<usize, CachedImage>,
    selected: usize,
    max_count: usize,
    max_bytes: usize,
) {
    trim_cache_pinned(cache, selected, max_count, max_bytes, [None, None]);
}

fn trim_cache_pinned(
    cache: &mut BTreeMap<usize, CachedImage>,
    selected: usize,
    max_count: usize,
    max_bytes: usize,
    pinned: [Option<usize>; 2],
) {
    let protected: Vec<_> = pinned.into_iter().flatten().collect();
    trim_cache_protected(cache, selected, max_count, max_bytes, &protected);
}

fn trim_cache_protected(
    cache: &mut BTreeMap<usize, CachedImage>,
    selected: usize,
    max_count: usize,
    max_bytes: usize,
    protected: &[usize],
) {
    let mut bytes: usize = cache.values().map(|image| image.bytes).sum();
    while cache.len() > max_count || bytes > max_bytes {
        let key = cache
            .keys()
            .copied()
            .filter(|index| *index != selected && !protected.contains(index))
            .max_by_key(|index| index.abs_diff(selected))
            .or_else(|| {
                cache
                    .keys()
                    .copied()
                    .max_by_key(|index| index.abs_diff(selected))
            });
        let Some(key) = key else {
            break;
        };
        let removed = cache.remove(&key).expect("key belongs to this cache");
        bytes -= removed.bytes;
    }
}

fn neighborhood(selected: usize, count: usize, direction: isize, radius: usize) -> Vec<usize> {
    let mut indices = Vec::with_capacity(radius * 2);
    for distance in 1..=radius {
        for sign in [direction, -direction] {
            if let Some(index) = selected.checked_add_signed(sign * distance as isize)
                && index < count
            {
                indices.push(index);
            }
        }
    }
    indices
}

fn cache_image(ctx: &egui::Context, image: PreviewImage, kind: Kind) -> CachedImage {
    let bytes = image.rgba.len();
    let color = egui::ColorImage::from_rgba_unmultiplied(image.size, &image.rgba);
    CachedImage {
        texture: ctx.load_texture(
            format!("{}:{kind:?}", image.path.display()),
            color,
            egui::TextureOptions::LINEAR,
        ),
        source_size: image.source_size,
        overview: image.is_overview,
        bytes,
    }
}

#[cfg(test)]
#[path = "source-browser-tests.rs"]
mod tests;
