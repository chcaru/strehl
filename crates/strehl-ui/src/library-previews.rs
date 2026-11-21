//! Bounded, completion-driven thumbnails shared by the library grid, the
//! subject page and the project tree. Decoding and scaling run on at most
//! `WORKERS` threads; the UI thread only uploads finished pixels, paced.
//!
//! Grid tiles ask for 256 px pictures made on the worker from the 384 px disk
//! tier (`preview::explorer`). Requests not repeated in the last paint are
//! dropped before they start, visible requests run before prefetched ones,
//! and a row's tiles (one `group`) are uploaded together.
use crate::{
    jobs::{self, Task},
    preview::{self, PreviewImage},
    workspace_history::{PhotoVersion, photographs},
};
use eframe::egui::{self, Rect, TextureHandle};
use std::{
    collections::{BTreeMap, VecDeque},
    path::{Path, PathBuf},
    sync::{Arc, Weak, mpsc},
};
use strehl_edit::LinearImage;

/// The disk tier and the project tree's picture side.
pub(crate) const SIDE: u32 = preview::explorer::SIDE;
/// A library grid tile, scaled on the worker from the disk tier.
pub(crate) const TILE_SIDE: u32 = 256;
/// A cold library fills with three decoders; a warm one starts none.
pub(crate) const WORKERS: usize = 3;
/// 240 tiles of 256 px (about 175 KB each at 3:2) fit the 48 MiB GPU budget.
pub(crate) const MAX_ENTRIES: usize = 240;
pub(crate) const MAX_BYTES: usize = 48 * 1024 * 1024;
/// Texture bytes uploaded from the UI thread per poll (plan 5.2 item 6).
pub(crate) const UPLOAD_BUDGET: usize = 2 * 1024 * 1024;
const MAX_QUEUE: usize = MAX_ENTRIES + 16;

#[derive(Clone)]
enum Request {
    File {
        path: PathBuf,
        source: bool,
    },
    Current {
        path: PathBuf,
        image: Weak<LinearImage>,
        source_size: [u32; 2],
    },
    SavedVersion {
        root: PathBuf,
        version: Box<PhotoVersion>,
    },
    Version {
        root: PathBuf,
        version: Box<PhotoVersion>,
        image: Weak<LinearImage>,
    },
}
impl Request {
    fn key(&self) -> String {
        match self {
            Self::Current { path, .. } => format!("photo:{}", path.display()),
            Self::SavedVersion { root, version } => format!(
                "saved:{}:{}:{}:{}",
                root.display(),
                version.id,
                version.loaded_sha256,
                version.photo.sha256
            ),
            Self::File { path, source } => format!(
                "{}:{}",
                if *source { "camera" } else { "photo" },
                path.display()
            ),
            Self::Version { root, version, .. } => format!(
                "version:{}:{}:{}:{}",
                root.display(),
                version.id,
                version.loaded_sha256,
                version.photo.sha256
            ),
        }
    }
}
/// Entry identity: the request's key, sized variants suffixed by their side.
fn sized_key(key: String, side: u32) -> String {
    if side >= SIDE {
        key
    } else {
        format!("{key}@{side}")
    }
}
fn estimate(side: u32) -> usize {
    side as usize * side as usize * 4
}
struct Entry {
    texture: Option<TextureHandle>,
    error: Option<String>,
    bytes: usize,
    touched: u64,
}
/// What a paint asked for and how urgently.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
struct Want {
    side: u32,
    /// Tiles of one group are uploaded in the same poll.
    group: Option<u64>,
    /// Prefetched one screen ahead; starts only after visible work.
    ahead: bool,
}
struct Queued {
    request: Request,
    key: String,
    seen: u64,
    want: Want,
}
struct Pending {
    key: String,
    task: Task<PreviewImage>,
    want: Want,
}
struct Ready {
    key: String,
    want: Want,
    result: Result<PreviewImage, String>,
}
struct Current {
    path: PathBuf,
    image: Weak<LinearImage>,
    preview: Arc<LinearImage>,
    source_size: [u32; 2],
    identity: Option<String>,
    identifying: Option<Task<String>>,
}
/// Counters for tests and the performance notes.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct PreviewStats {
    pub entries: usize,
    pub bytes: usize,
    pub queued: usize,
    pub running: usize,
    pub staged: usize,
    pub tasks_started: u64,
    pub uploads: u64,
    pub uploaded_last_poll: usize,
    pub largest_poll_upload: usize,
}
#[derive(Default)]
pub(crate) struct LibraryPreviews {
    entries: BTreeMap<String, Entry>,
    queue: VecDeque<Queued>,
    pending: Vec<Pending>,
    staged: Vec<Ready>,
    current: Option<Current>,
    clock: u64,
    ctx: Option<egui::Context>,
    stats: PreviewStats,
    /// The egui pass last polled: views sharing this service poll once a pass.
    polled_pass: Option<u64>,
}

impl LibraryPreviews {
    pub(crate) fn pending(&self) -> bool {
        !self.pending.is_empty()
            || !self.queue.is_empty()
            || !self.staged.is_empty()
            || self
                .current
                .as_ref()
                .is_some_and(|p| p.identifying.is_some())
    }

    #[cfg_attr(
        not(test),
        allow(dead_code, reason = "read by tests and the P4 perf note")
    )]
    pub(crate) fn stats(&self) -> PreviewStats {
        PreviewStats {
            entries: self.entries.len(),
            bytes: self.entries.values().map(|e| e.bytes).sum(),
            queued: self.queue.len(),
            running: self.pending.len(),
            staged: self.staged.len(),
            ..self.stats
        }
    }

    pub(crate) fn set_current(
        &mut self,
        path: Option<&Path>,
        image: Option<&Arc<LinearImage>>,
        preview: Option<&Arc<LinearImage>>,
    ) {
        let (Some(path), Some(image), Some(preview)) = (path, image, preview) else {
            self.current = None;
            self.queue
                .retain(|q| matches!(q.request, Request::File { .. }));
            return;
        };
        if self
            .current
            .as_ref()
            .is_some_and(|p| p.path == path && p.image.ptr_eq(&Arc::downgrade(image)))
        {
            return;
        }
        // A newly accepted loaded image is fresh evidence, even when its path
        // was previously open (or a loading gap temporarily cleared Current).
        // Never leave the old path-only base thumbnail behind the identity gate.
        let base_key = Request::File {
            path: path.into(),
            source: false,
        }
        .key();
        let base = |key: &str| key == base_key || key.starts_with(&format!("{base_key}@"));
        self.entries.retain(|key, _| !base(key));
        self.staged.retain(|ready| !base(&ready.key));
        for pending in self.pending.iter().filter(|p| base(&p.key)) {
            pending.task.cancel();
        }
        self.queue
            .retain(|q| matches!(q.request, Request::File { .. }) && !base(&q.key));
        self.current = Some(Current {
            path: path.into(),
            image: Arc::downgrade(image),
            preview: preview.clone(),
            source_size: [image.width, image.height],
            identity: None,
            identifying: None,
        });
    }

    /// At the start of every paint that may request pictures. Views sharing
    /// the service may each call it: only the first call of a pass counts.
    pub(crate) fn poll(&mut self, ctx: &egui::Context) {
        let pass = ctx.cumulative_pass_nr();
        if self.polled_pass == Some(pass) && self.ctx.as_ref() == Some(ctx) {
            return;
        }
        self.polled_pass = Some(pass);
        self.ctx = Some(ctx.clone());
        self.clock = self.clock.wrapping_add(1);
        if let Some(current) = self.current.as_mut()
            && let Some(task) = &current.identifying
        {
            match task.receiver.try_recv() {
                Ok(result) => {
                    current.identity = Some(result.unwrap_or_default());
                    current.identifying = None;
                }
                Err(mpsc::TryRecvError::Disconnected) => {
                    current.identity = Some(String::new());
                    current.identifying = None;
                }
                Err(mpsc::TryRecvError::Empty) => {}
            }
        }
        let mut at = 0;
        while at < self.pending.len() {
            let ready = match self.pending[at].task.receiver.try_recv() {
                Ok(result) => Some(result),
                Err(mpsc::TryRecvError::Empty) => None,
                Err(mpsc::TryRecvError::Disconnected) => Some(Err("Preview worker ended".into())),
            };
            if let Some(result) = ready {
                let pending = self.pending.swap_remove(at);
                // Cancellation retains its lane until the decoder has actually
                // returned; rapid navigation cannot create unbounded workers.
                if pending.task.is_cancelled() {
                    continue;
                }
                self.staged.push(Ready {
                    key: pending.key,
                    want: pending.want,
                    result,
                });
            } else {
                at += 1;
            }
        }
        self.commit(ctx);
        // Rows not requested in the last completed paint no longer consume decode time.
        let clock = self.clock;
        self.queue.retain(|q| q.seen.saturating_add(1) >= clock);
        self.start_workers(ctx);
    }

    /// Upload finished pictures: whole groups only, at most `UPLOAD_BUDGET`
    /// bytes a poll (one group always proceeds), the rest on the next frame.
    fn commit(&mut self, ctx: &egui::Context) {
        let mut uploaded = 0;
        let mut deferred = false;
        let mut index = 0;
        while index < self.staged.len() {
            let group = self.staged[index].want.group;
            let complete = group.is_none_or(|group| {
                !self.pending.iter().any(|p| p.want.group == Some(group))
                    && !self.queue.iter().any(|q| q.want.group == Some(group))
            });
            if !complete {
                index += 1;
                continue;
            }
            let members: Vec<usize> = match group {
                None => vec![index],
                Some(group) => (index..self.staged.len())
                    .filter(|&i| self.staged[i].want.group == Some(group))
                    .collect(),
            };
            let bytes: usize = members
                .iter()
                .map(|&i| self.staged[i].result.as_ref().map_or(0, |p| p.rgba.len()))
                .sum();
            if uploaded > 0 && uploaded + bytes > UPLOAD_BUDGET {
                deferred = true;
                break;
            }
            uploaded += bytes;
            for i in members.into_iter().rev() {
                let ready = self.staged.remove(i);
                self.publish(ctx, ready);
            }
        }
        self.stats.uploaded_last_poll = uploaded;
        self.stats.largest_poll_upload = self.stats.largest_poll_upload.max(uploaded);
        if deferred {
            // Paced uploads continue on the next frame without a new event.
            ctx.request_repaint();
        }
        self.trim();
    }

    fn publish(&mut self, ctx: &egui::Context, ready: Ready) {
        let published_key = if ready.result.is_ok() {
            ready
                .key
                .strip_prefix("version:")
                .map(|key| format!("saved:{key}"))
                .unwrap_or_else(|| ready.key.clone())
        } else {
            ready.key.clone()
        };
        let entry = match ready.result {
            Ok(image) => {
                let pixels = egui::ColorImage::from_rgba_unmultiplied(image.size, &image.rgba);
                self.stats.uploads += 1;
                Entry {
                    texture: Some(ctx.load_texture(
                        &ready.key,
                        pixels,
                        egui::TextureOptions::LINEAR,
                    )),
                    error: None,
                    bytes: image.rgba.len(),
                    touched: self.clock,
                }
            }
            Err(error) => Entry {
                texture: None,
                error: Some(error),
                bytes: 0,
                touched: self.clock,
            },
        };
        // Reconstructing a legacy derivative replaces its earlier
        // saved-preview miss. It stays inspectable after leaving this
        // photograph; an open document is not required a second time.
        self.entries.insert(published_key, entry);
    }

    fn start_workers(&mut self, ctx: &egui::Context) {
        while self.pending.len() < WORKERS {
            // Visible work first; prefetch only when no visible row waits.
            let Some(at) = self
                .queue
                .iter()
                .position(|q| !q.want.ahead)
                .or_else(|| (!self.queue.is_empty()).then_some(0))
            else {
                break;
            };
            let Queued {
                request, key, want, ..
            } = self.queue.remove(at).unwrap();
            let notify = ctx.clone();
            let side = want.side;
            self.stats.tasks_started += 1;
            let task = jobs::spawn_notifying_task(
                "strehl-library-thumbnail",
                move |cancelled| {
                    let image = match request {
                        Request::File { path, source } => preview::explorer::load_file(
                            &path,
                            source,
                            preview::explorer::default_root().as_deref(),
                            &cancelled,
                        ),
                        Request::Current {
                            path,
                            image,
                            source_size,
                        } => {
                            let image = image.upgrade().ok_or_else(|| {
                                anyhow::anyhow!("Photograph preview is no longer open")
                            })?;
                            preview::explorer::render(
                                &path,
                                &image,
                                &Default::default(),
                                source_size,
                            )
                        }
                        Request::SavedVersion { root, version } => {
                            preview::explorer::load_version(&root, &version)
                        }
                        Request::Version {
                            root,
                            version,
                            image,
                        } => {
                            anyhow::ensure!(
                                !cancelled.load(std::sync::atomic::Ordering::Relaxed),
                                "Preview cancelled"
                            );
                            let image = image.upgrade().ok_or_else(|| {
                                anyhow::anyhow!("Photograph preview is no longer open")
                            })?;
                            let recipe = photographs::read_preview_recipe(&root, &version)?;
                            image.validate_source_repairs(&recipe)?;
                            let coverage = crate::photo_coverage::Coverage::load(
                                &version.owner.output,
                                [image.width, image.height],
                            )?;
                            let job = crate::development_job::DevelopmentJob::native(image, recipe)
                                .with_coverage(coverage);
                            preview::explorer::save_version(&root, &version, &job)
                        }
                    }?;
                    Ok(scale_to(image, side))
                },
                move || notify.request_repaint(),
            );
            self.pending.push(Pending { key, task, want });
        }
    }

    fn trim(&mut self) {
        while self.entries.len() > MAX_ENTRIES
            || self.entries.values().map(|e| e.bytes).sum::<usize>() > MAX_BYTES
        {
            let key = self
                .entries
                .iter()
                .min_by_key(|(_, e)| e.touched)
                .map(|(k, _)| k.clone())
                .unwrap();
            self.entries.remove(&key);
        }
    }
    /// Entries plus work in flight, counted at its largest possible size.
    fn committed(&self) -> (usize, usize) {
        let count = self.entries.len() + self.queue.len() + self.pending.len() + self.staged.len();
        let bytes = self.entries.values().map(|e| e.bytes).sum::<usize>()
            + self
                .queue
                .iter()
                .map(|q| estimate(q.want.side))
                .sum::<usize>()
            + self
                .pending
                .iter()
                .map(|p| estimate(p.want.side))
                .sum::<usize>()
            + self
                .staged
                .iter()
                .map(|r| r.result.as_ref().map_or(0, |p| p.rgba.len()))
                .sum::<usize>();
        (count, bytes)
    }
    fn request(&mut self, request: Request, want: Want) -> Option<TextureHandle> {
        let key = sized_key(request.key(), want.side);
        if let Some(entry) = self.entries.get_mut(&key) {
            entry.touched = self.clock;
            return entry.texture.clone();
        }
        if self
            .pending
            .iter()
            .any(|p| p.key == key && !p.task.is_cancelled())
            || self.staged.iter().any(|r| r.key == key)
        {
            return None;
        }
        if let Some(queued) = self.queue.iter_mut().find(|q| q.key == key) {
            queued.seen = self.clock;
            // A prefetched picture that became visible moves up.
            queued.want.ahead &= want.ahead;
            queued.want.group = want.group;
            return None;
        }
        // Pin this paint's working set. Oversized views stop admitting extra
        // tiles instead of continuously evicting and decoding the same images.
        loop {
            let (count, bytes) = self.committed();
            if count < MAX_ENTRIES && bytes + estimate(want.side) <= MAX_BYTES {
                break;
            }
            if let Some(old) = self
                .entries
                .iter()
                .filter(|(_, e)| e.touched < self.clock)
                .min_by_key(|(_, e)| e.touched)
                .map(|(k, _)| k.clone())
            {
                self.entries.remove(&old);
            } else {
                let old = self.queue.iter().position(|q| q.seen < self.clock)?;
                self.queue.remove(old);
            }
        }
        if self.queue.len() < MAX_QUEUE {
            self.queue.push_back(Queued {
                request,
                key,
                seen: self.clock,
                want,
            });
            if let Some(ctx) = self.ctx.clone() {
                self.start_workers(&ctx);
            }
        }
        None
    }
    #[cfg(test)]
    fn request_row(&mut self, request: Request) -> Option<TextureHandle> {
        self.request(
            request,
            Want {
                side: SIDE,
                ..Default::default()
            },
        )
    }
    fn file_request(&self, path: &Path, source: bool) -> Option<Request> {
        if !source
            && path
                .extension()
                .is_some_and(|e| e.eq_ignore_ascii_case("avif"))
        {
            return None;
        }
        if !source
            && let Some(current) = &self.current
            && current.path == path
        {
            return Some(Request::Current {
                path: path.into(),
                image: Arc::downgrade(&current.preview),
                source_size: current.source_size,
            });
        }
        Some(Request::File {
            path: path.into(),
            source,
        })
    }
    /// A 384 px picture for the project tree and hover previews.
    pub(crate) fn file(&mut self, path: &Path, source: bool) -> Option<TextureHandle> {
        let request = self.file_request(path, source)?;
        self.request(
            request,
            Want {
                side: SIDE,
                ..Default::default()
            },
        )
    }
    /// A visible grid tile of at most `side` px; tiles of one `group` (a grid
    /// row) are uploaded together.
    pub(crate) fn tile(
        &mut self,
        path: &Path,
        source: bool,
        side: u32,
        group: u64,
    ) -> Option<TextureHandle> {
        let request = self.file_request(path, source)?;
        self.request(
            request,
            Want {
                side: side.min(SIDE),
                group: Some(group),
                ahead: false,
            },
        )
    }
    /// A tile one screen ahead: decoded after every visible tile, kept warm
    /// while it is asked for, dropped when it is not.
    pub(crate) fn prefetch(&mut self, path: &Path, source: bool, side: u32, group: u64) {
        if let Some(request) = self.file_request(path, source) {
            self.request(
                request,
                Want {
                    side: side.min(SIDE),
                    group: Some(group),
                    ahead: true,
                },
            );
        }
    }
    pub(crate) fn version(
        &mut self,
        root: Option<&Path>,
        version: &PhotoVersion,
    ) -> (Option<TextureHandle>, bool) {
        let want = Want {
            side: SIDE,
            ..Default::default()
        };
        let mut exact = None;
        let saved = root.map(|root| Request::SavedVersion {
            root: root.into(),
            version: Box::new(version.clone()),
        });
        if let Some(saved) = &saved {
            if let Some(texture) = self.request(saved.clone(), want) {
                return (Some(texture), true);
            }
            // Missing legacy derivatives may be reconstructed from the current
            // image after matching its full loaded-pixel identity. New versions
            // already carry a derivative and never need to hash/decode here.
            if !self
                .entries
                .get(&saved.key())
                .is_some_and(|entry| entry.error.is_some())
            {
                return (self.file(&version.owner.output, false), false);
            }
        }
        if let Some(current) = self
            .current
            .as_mut()
            .filter(|p| p.path == version.owner.output)
        {
            if current.identity.is_none()
                && current.identifying.is_none()
                && let Some(image) = current.image.upgrade()
            {
                let notify = self.ctx.clone();
                current.identifying = Some(jobs::spawn_notifying_task(
                    "strehl-explorer-identity",
                    move |cancelled| photographs::loaded_hash(&image, &cancelled),
                    move || {
                        if let Some(ctx) = &notify {
                            ctx.request_repaint();
                        }
                    },
                ));
            }
            if current.identity.as_deref() == Some(&version.loaded_sha256)
                && let Some(root) = root
            {
                exact = Some(Request::Version {
                    root: root.into(),
                    version: Box::new(version.clone()),
                    image: Arc::downgrade(&current.preview),
                });
            }
        }
        if let Some(request) = exact
            && let Some(texture) = self.request(request, want)
        {
            return (Some(texture), true);
        }
        (self.file(&version.owner.output, false), false)
    }
    pub(crate) fn error(&self, path: &Path, source: bool) -> Option<&str> {
        self.entries
            .get(
                &Request::File {
                    path: path.into(),
                    source,
                }
                .key(),
            )
            .and_then(|e| e.error.as_deref())
    }
    /// Whether a file picture of this side failed (missing or unreadable), so
    /// a view can fall back to its next candidate.
    pub(crate) fn failed(&self, path: &Path, source: bool, side: u32) -> bool {
        self.entries
            .get(&sized_key(
                Request::File {
                    path: path.into(),
                    source,
                }
                .key(),
                side.min(SIDE),
            ))
            .is_some_and(|e| e.error.is_some())
    }
    /// The first candidate that has not failed, as a tile of `side`.
    pub(crate) fn first_tile(
        &mut self,
        candidates: &[(PathBuf, bool)],
        side: u32,
        group: u64,
    ) -> Option<TextureHandle> {
        let (path, source) = candidates
            .iter()
            .find(|(path, source)| !self.failed(path, *source, side))?;
        self.tile(path, *source, side, group)
    }
    pub(crate) fn paint(ui: &egui::Ui, rect: Rect, texture: Option<&TextureHandle>) {
        ui.painter().rect_filled(rect, 0.0, crate::theme::RAISED);
        if let Some(texture) = texture {
            let size = texture.size_vec2();
            let scale = (rect.width() / size.x).min(rect.height() / size.y);
            ui.painter().image(
                texture.id(),
                Rect::from_center_size(rect.center(), size * scale),
                Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(1.0, 1.0)),
                egui::Color32::WHITE,
            );
        }
    }
    /// Fill `rect`, cropping the picture's longer side about its centre.
    pub(crate) fn paint_cover(painter: &egui::Painter, rect: Rect, texture: &TextureHandle) {
        let size = texture.size_vec2();
        if size.x <= 0.0 || size.y <= 0.0 || rect.width() <= 0.0 || rect.height() <= 0.0 {
            return;
        }
        let (picture, frame) = (size.x / size.y, rect.width() / rect.height());
        let uv = if picture > frame {
            let keep = frame / picture;
            Rect::from_min_max(
                egui::pos2((1.0 - keep) * 0.5, 0.0),
                egui::pos2((1.0 + keep) * 0.5, 1.0),
            )
        } else {
            let keep = picture / frame;
            Rect::from_min_max(
                egui::pos2(0.0, (1.0 - keep) * 0.5),
                egui::pos2(1.0, (1.0 + keep) * 0.5),
            )
        };
        painter.image(texture.id(), rect, uv, egui::Color32::WHITE);
    }
    pub(crate) fn hover(ui: &mut egui::Ui, texture: Option<&TextureHandle>, caption: &str) {
        if let Some(texture) = texture {
            let size = texture.size_vec2();
            let width = size.x.min(336.0);
            ui.image((texture.id(), size * (width / size.x)));
        }
        ui.label(egui::RichText::new(caption).small());
    }
}

/// Downscale on the worker so the UI thread uploads only the tile's pixels.
fn scale_to(image: PreviewImage, side: u32) -> PreviewImage {
    let [width, height] = image.size;
    let longest = width.max(height);
    if side == 0 || longest <= side as usize {
        return image;
    }
    let scale = side as f64 / longest as f64;
    let target = |n: usize| ((n as f64 * scale).round() as u32).max(1);
    let Some(buffer) = image::RgbaImage::from_raw(width as u32, height as u32, image.rgba.clone())
    else {
        return image;
    };
    let scaled = image::imageops::resize(
        &buffer,
        target(width),
        target(height),
        image::imageops::FilterType::Triangle,
    );
    PreviewImage {
        size: [scaled.width() as usize, scaled.height() as usize],
        rgba: scaled.into_raw(),
        ..image
    }
}

#[cfg(test)]
#[path = "library-previews-tests.rs"]
mod tests;

#[cfg(test)]
#[path = "library-previews-review-tests.rs"]
mod review_tests;
