//! Bounded, completion-driven thumbnail lanes shared by rows and hover previews.
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

#[cfg(test)]
const SIDE: u32 = preview::explorer::SIDE;
const WORKERS: usize = 2;
// Forty maximum-size RGBA previews fit below the 24 MiB GPU budget.
const MAX_ENTRIES: usize = 40;
const MAX_BYTES: usize = 24 * 1024 * 1024;
const MAX_QUEUE: usize = 64;

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
struct Entry {
    texture: Option<TextureHandle>,
    error: Option<String>,
    bytes: usize,
    touched: u64,
}
struct Pending {
    key: String,
    task: Task<PreviewImage>,
}
struct Current {
    path: PathBuf,
    image: Weak<LinearImage>,
    preview: Arc<LinearImage>,
    source_size: [u32; 2],
    identity: Option<String>,
    identifying: Option<Task<String>>,
}
#[derive(Default)]
pub(super) struct ExplorerPreviews {
    entries: BTreeMap<String, Entry>,
    queue: VecDeque<(Request, u64)>,
    pending: Vec<Pending>,
    current: Option<Current>,
    clock: u64,
    ctx: Option<egui::Context>,
}

impl ExplorerPreviews {
    pub(super) fn pending(&self) -> bool {
        !self.pending.is_empty()
            || !self.queue.is_empty()
            || self
                .current
                .as_ref()
                .is_some_and(|p| p.identifying.is_some())
    }

    pub(super) fn set_current(
        &mut self,
        path: Option<&Path>,
        image: Option<&Arc<LinearImage>>,
        preview: Option<&Arc<LinearImage>>,
    ) {
        let (Some(path), Some(image), Some(preview)) = (path, image, preview) else {
            self.current = None;
            self.queue
                .retain(|(r, _)| matches!(r, Request::File { .. }));
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
        self.entries.remove(&base_key);
        for pending in self.pending.iter().filter(|p| p.key == base_key) {
            pending.task.cancel();
        }
        self.queue
            .retain(|(r, _)| matches!(r, Request::File { .. }) && r.key() != base_key);
        self.current = Some(Current {
            path: path.into(),
            image: Arc::downgrade(image),
            preview: preview.clone(),
            source_size: [image.width, image.height],
            identity: None,
            identifying: None,
        });
    }

    pub(super) fn poll(&mut self, ctx: &egui::Context) {
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
                let published_key = if result.is_ok() {
                    pending
                        .key
                        .strip_prefix("version:")
                        .map(|key| format!("saved:{key}"))
                        .unwrap_or_else(|| pending.key.clone())
                } else {
                    pending.key.clone()
                };
                let entry = match result {
                    Ok(image) => {
                        let pixels =
                            egui::ColorImage::from_rgba_unmultiplied(image.size, &image.rgba);
                        Entry {
                            texture: Some(ctx.load_texture(
                                &pending.key,
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
                self.trim();
            } else {
                at += 1;
            }
        }
        // Rows not requested in the last completed paint no longer consume decode time.
        self.queue
            .retain(|(_, seen)| seen.saturating_add(1) >= self.clock);
        self.start_workers(ctx);
    }

    fn start_workers(&mut self, ctx: &egui::Context) {
        while self.pending.len() < WORKERS {
            let Some((request, _)) = self.queue.pop_front() else {
                break;
            };
            let key = request.key();
            let notify = ctx.clone();
            let task = jobs::spawn_notifying_task(
                "strehl-explorer-thumbnail",
                move |cancelled| match request {
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
                        preview::explorer::render(&path, &image, &Default::default(), source_size)
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
                        preview::explorer::save_version(&root, &version, &image, &recipe)
                    }
                },
                move || notify.request_repaint(),
            );
            self.pending.push(Pending { key, task });
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
    fn request(&mut self, request: Request) -> Option<TextureHandle> {
        let key = request.key();
        if let Some(entry) = self.entries.get_mut(&key) {
            entry.touched = self.clock;
            return entry.texture.clone();
        }
        if self
            .pending
            .iter()
            .any(|p| p.key == key && !p.task.is_cancelled())
        {
            return None;
        }
        if let Some((_, seen)) = self.queue.iter_mut().find(|(r, _)| r.key() == key) {
            *seen = self.clock;
            return None;
        }
        // Pin this paint's working set. Oversized trees stop admitting extra
        // rows instead of continuously evicting and decoding the same images.
        if self.entries.len() + self.queue.len() + self.pending.len() >= MAX_ENTRIES {
            if let Some(old) = self
                .entries
                .iter()
                .filter(|(_, e)| e.touched < self.clock)
                .min_by_key(|(_, e)| e.touched)
                .map(|(k, _)| k.clone())
            {
                self.entries.remove(&old);
            } else {
                let old = self.queue.iter().position(|(_, seen)| *seen < self.clock)?;
                self.queue.remove(old);
            }
        }
        if self.queue.len() < MAX_QUEUE {
            self.queue.push_back((request, self.clock));
            if let Some(ctx) = self.ctx.clone() {
                self.start_workers(&ctx);
            }
        }
        None
    }
    pub(super) fn file(&mut self, path: &Path, source: bool) -> Option<TextureHandle> {
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
            return self.request(Request::Current {
                path: path.into(),
                image: Arc::downgrade(&current.preview),
                source_size: current.source_size,
            });
        }
        self.request(Request::File {
            path: path.into(),
            source,
        })
    }
    pub(super) fn version(
        &mut self,
        root: Option<&Path>,
        version: &PhotoVersion,
    ) -> (Option<TextureHandle>, bool) {
        let mut exact = None;
        let saved = root.map(|root| Request::SavedVersion {
            root: root.into(),
            version: Box::new(version.clone()),
        });
        if let Some(saved) = &saved {
            if let Some(texture) = self.request(saved.clone()) {
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
            && let Some(texture) = self.request(request)
        {
            return (Some(texture), true);
        }
        (self.file(&version.owner.output, false), false)
    }
    pub(super) fn error(&self, path: &Path, source: bool) -> Option<&str> {
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
    pub(super) fn paint(ui: &egui::Ui, rect: Rect, texture: Option<&TextureHandle>) {
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
    pub(super) fn hover(ui: &mut egui::Ui, texture: Option<&TextureHandle>, caption: &str) {
        if let Some(texture) = texture {
            let size = texture.size_vec2();
            let width = size.x.min(336.0);
            ui.image((texture.id(), size * (width / size.x)));
        }
        ui.label(egui::RichText::new(caption).small());
    }
}

#[cfg(test)]
#[path = "explorer-previews-tests.rs"]
mod tests;

#[cfg(test)]
#[path = "explorer-previews-review-tests.rs"]
mod review_tests;
