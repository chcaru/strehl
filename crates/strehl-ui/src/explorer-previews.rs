//! One bounded background lane shared by tiny rows and larger hover previews.
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

const SIDE: u32 = 384;
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
    Version {
        root: PathBuf,
        version: Box<PhotoVersion>,
        image: Weak<LinearImage>,
    },
}
impl Request {
    fn key(&self) -> String {
        match self {
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
    identity: Option<String>,
    identifying: Option<Task<String>>,
}
#[derive(Default)]
pub(super) struct ExplorerPreviews {
    entries: BTreeMap<String, Entry>,
    queue: VecDeque<(Request, u64)>,
    pending: Option<Pending>,
    current: Option<Current>,
    clock: u64,
    ctx: Option<egui::Context>,
}

impl ExplorerPreviews {
    pub(super) fn pending(&self) -> bool {
        self.pending.is_some()
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
        if self.pending.as_ref().is_some_and(|p| p.key == base_key) {
            self.pending = None;
        }
        self.queue
            .retain(|(r, _)| matches!(r, Request::File { .. }) && r.key() != base_key);
        self.current = Some(Current {
            path: path.into(),
            image: Arc::downgrade(image),
            preview: preview.clone(),
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
        if let Some(pending) = &self.pending {
            let ready = match pending.task.receiver.try_recv() {
                Ok(result) => Some(result),
                Err(mpsc::TryRecvError::Empty) => None,
                Err(mpsc::TryRecvError::Disconnected) => Some(Err("Preview worker ended".into())),
            };
            if let Some(result) = ready {
                let pending = self.pending.take().unwrap();
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
                self.entries.insert(pending.key, entry);
                self.trim();
            }
        }
        // Rows not requested in the last completed paint no longer consume decode time.
        self.queue
            .retain(|(_, seen)| seen.saturating_add(1) >= self.clock);
        if self.pending.is_none()
            && let Some((request, _)) = self.queue.pop_front()
        {
            let key = request.key();
            let task = match request {
                Request::File { path, source: true } => {
                    jobs::spawn_task("strehl-explorer-source", move |cancelled| {
                        crate::source_preview::load_draft_source(&path, SIDE, &cancelled)
                    })
                }
                Request::File {
                    path,
                    source: false,
                } => preview::load_preview(path, SIDE),
                Request::Version {
                    root,
                    version,
                    image,
                } => jobs::spawn_task("strehl-explorer-version", move |cancelled| {
                    anyhow::ensure!(
                        !cancelled.load(std::sync::atomic::Ordering::Relaxed),
                        "Preview cancelled"
                    );
                    let image = image
                        .upgrade()
                        .ok_or_else(|| anyhow::anyhow!("Photograph preview is no longer open"))?;
                    let recipe = photographs::read_preview_recipe(&root, &version)?;
                    image.validate_source_repairs(&recipe)?;
                    let (width, height, rgb) =
                        image.render_region_sdr8(&recipe, [0.0, 0.0], [1.0, 1.0], SIDE)?;
                    let rgba = rgb
                        .as_chunks::<3>()
                        .0
                        .iter()
                        .flat_map(|p| [p[0], p[1], p[2], 255])
                        .collect();
                    Ok(PreviewImage {
                        path: version.owner.output,
                        source_size: [width, height],
                        size: [width as usize, height as usize],
                        rgba,
                        is_overview: true,
                    })
                }),
            };
            self.pending = Some(Pending { key, task });
        }
        if self.pending.is_some()
            || self
                .current
                .as_ref()
                .is_some_and(|p| p.identifying.is_some())
        {
            ctx.request_repaint_after(std::time::Duration::from_millis(80));
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
        if self.pending.as_ref().is_some_and(|p| p.key == key) {
            return None;
        }
        if let Some((_, seen)) = self.queue.iter_mut().find(|(r, _)| r.key() == key) {
            *seen = self.clock;
            return None;
        }
        // Pin this paint's working set. Oversized trees stop admitting extra
        // rows instead of continuously evicting and decoding the same images.
        if self.entries.len() + self.queue.len() + usize::from(self.pending.is_some())
            >= MAX_ENTRIES
        {
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
            if let Some(ctx) = &self.ctx {
                ctx.request_repaint();
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
        if let Some(current) = self
            .current
            .as_mut()
            .filter(|p| p.path == version.owner.output)
        {
            if current.identity.is_none()
                && current.identifying.is_none()
                && let Some(image) = current.image.upgrade()
            {
                current.identifying = Some(jobs::spawn_task(
                    "strehl-explorer-identity",
                    move |cancelled| photographs::loaded_hash(&image, &cancelled),
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
