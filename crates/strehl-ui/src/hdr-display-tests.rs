//! Real GPU controls. Run explicitly on a desktop: the normal test suite does
//! not require a GPU. The independent reviewer must change the colors/white.
use super::*;

fn block_on<T>(future: impl std::future::Future<Output = T>) -> T {
    struct Wake(std::thread::Thread);
    impl std::task::Wake for Wake {
        fn wake(self: Arc<Self>) {
            self.0.unpark();
        }
        fn wake_by_ref(self: &Arc<Self>) {
            self.0.unpark();
        }
    }
    let waker = std::task::Waker::from(Arc::new(Wake(std::thread::current())));
    let mut task = std::task::Context::from_waker(&waker);
    let mut future = std::pin::pin!(future);
    loop {
        match future.as_mut().poll(&mut task) {
            std::task::Poll::Ready(value) => return value,
            std::task::Poll::Pending => std::thread::park(),
        }
    }
}

fn target(device: &wgpu::Device, format: wgpu::TextureFormat) -> wgpu::Texture {
    device.create_texture(&wgpu::TextureDescriptor {
        label: Some("HDR verification target"),
        size: wgpu::Extent3d {
            width: 8,
            height: 2,
            depth_or_array_layers: 1,
        },
        mip_level_count: 1,
        sample_count: 1,
        dimension: wgpu::TextureDimension::D2,
        format,
        usage: wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::COPY_SRC,
        view_formats: &[],
    })
}

fn read(device: &wgpu::Device, queue: &wgpu::Queue, texture: &wgpu::Texture) -> Vec<[f32; 4]> {
    let buffer = device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("HDR verification readback"),
        size: 512,
        usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ,
        mapped_at_creation: false,
    });
    let mut encoder = device.create_command_encoder(&Default::default());
    encoder.copy_texture_to_buffer(
        texture.as_image_copy(),
        wgpu::TexelCopyBufferInfo {
            buffer: &buffer,
            layout: wgpu::TexelCopyBufferLayout {
                offset: 0,
                bytes_per_row: Some(256),
                rows_per_image: Some(2),
            },
        },
        texture.size(),
    );
    queue.submit([encoder.finish()]);
    let (tx, rx) = mpsc::sync_channel(1);
    buffer
        .slice(..)
        .map_async(wgpu::MapMode::Read, move |value| {
            tx.send(value).unwrap();
        });
    device.poll(wgpu::PollType::wait_indefinitely()).unwrap();
    rx.recv().unwrap().unwrap();
    let bytes = buffer.slice(..).get_mapped_range();
    let mut values = Vec::new();
    for row in bytes.as_chunks::<256>().0 {
        for i in 0..8 {
            if texture.format() == wgpu::TextureFormat::Rgba16Float {
                values.push(std::array::from_fn(|c| {
                    let off = i * 8 + c * 2;
                    let bits = u16::from_le_bytes([row[off], row[off + 1]]);
                    let sign = if bits & 0x8000 != 0 { -1.0 } else { 1.0 };
                    let e = ((bits >> 10) & 31) as i32;
                    let m = (bits & 1023) as f32;
                    sign * if e == 0 {
                        m * 2.0f32.powi(-24)
                    } else {
                        (1.0 + m / 1024.0) * 2.0f32.powi(e - 15)
                    }
                }));
            } else {
                values.push(std::array::from_fn(|c| row[i * 4 + c] as f32 / 255.0));
            }
        }
    }
    values
}

fn photograph(
    device: &wgpu::Device,
    queue: &wgpu::Queue,
    format: wgpu::TextureFormat,
    mode: f32,
) -> Vec<[f32; 4]> {
    let (pipeline, layout) = photo_pipeline(device, format);
    let source = device.create_texture(&wgpu::TextureDescriptor {
        label: Some("HDR known colored headroom"),
        size: wgpu::Extent3d {
            width: 2,
            height: 1,
            depth_or_array_layers: 1,
        },
        mip_level_count: 1,
        sample_count: 1,
        dimension: wgpu::TextureDimension::D2,
        format: wgpu::TextureFormat::Rgba32Float,
        usage: wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::COPY_DST,
        view_formats: &[],
    });
    let data = [0.25f32, 2.0, 4.0, 1.0, 0.125, 0.25, 0.5, 1.0];
    queue.write_texture(
        source.as_image_copy(),
        bytemuck::cast_slice(&data),
        wgpu::TexelCopyBufferLayout {
            offset: 0,
            bytes_per_row: Some(32),
            rows_per_image: Some(1),
        },
        source.size(),
    );
    let view = source.create_view(&Default::default());
    let params = [0.0f32, 0.0, 1.0, 1.0, 2.5, 12.5, 1.0, mode];
    let buffer = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: None,
        contents: bytemuck::cast_slice(&params),
        usage: wgpu::BufferUsages::UNIFORM,
    });
    let bindings = device.create_bind_group(&wgpu::BindGroupDescriptor {
        label: None,
        layout: &layout,
        entries: &[
            wgpu::BindGroupEntry {
                binding: 0,
                resource: wgpu::BindingResource::TextureView(&view),
            },
            wgpu::BindGroupEntry {
                binding: 1,
                resource: buffer.as_entire_binding(),
            },
        ],
    });
    let output = target(device, format);
    let output_view = output.create_view(&Default::default());
    let mut encoder = device.create_command_encoder(&Default::default());
    {
        let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
            color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                view: &output_view,
                resolve_target: None,
                depth_slice: None,
                ops: wgpu::Operations {
                    load: wgpu::LoadOp::Clear(wgpu::Color::BLACK),
                    store: wgpu::StoreOp::Store,
                },
            })],
            ..Default::default()
        });
        pass.set_pipeline(&pipeline);
        pass.set_bind_group(0, &bindings, &[]);
        pass.draw(0..3, 0..1);
    }
    queue.submit([encoder.finish()]);
    read(device, queue, &output)
}

fn ui(device: &wgpu::Device, queue: &wgpu::Queue, scale: f32) -> Vec<[f32; 4]> {
    let mut renderer = egui_wgpu::Renderer::new(
        device,
        wgpu::TextureFormat::Rgba16Float,
        egui_wgpu::RendererOptions::PREDICTABLE,
    );
    renderer.set_output_white_scale(scale);
    renderer.update_texture(
        device,
        queue,
        egui::TextureId::Managed(0),
        &egui::epaint::ImageDelta::full(
            egui::ColorImage::filled([1, 1], egui::Color32::WHITE),
            egui::TextureOptions::NEAREST,
        ),
    );
    let mut mesh = egui::Mesh::default();
    mesh.add_colored_rect(
        Rect::from_min_max(egui::pos2(0.0, 0.0), egui::pos2(4.0, 2.0)),
        egui::Color32::WHITE,
    );
    mesh.add_colored_rect(
        Rect::from_min_max(egui::pos2(4.0, 0.0), egui::pos2(8.0, 2.0)),
        egui::Color32::from_rgba_premultiplied(64, 32, 16, 128),
    );
    let jobs = [egui::ClippedPrimitive {
        clip_rect: Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(8.0, 2.0)),
        primitive: egui::epaint::Primitive::Mesh(mesh),
    }];
    let screen = egui_wgpu::ScreenDescriptor {
        size_in_pixels: [8, 2],
        pixels_per_point: 1.0,
    };
    let output = target(device, wgpu::TextureFormat::Rgba16Float);
    let view = output.create_view(&Default::default());
    let mut encoder = device.create_command_encoder(&Default::default());
    let commands = renderer.update_buffers(device, queue, &mut encoder, &jobs, &screen);
    {
        let pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
            color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                view: &view,
                resolve_target: None,
                depth_slice: None,
                ops: wgpu::Operations {
                    load: wgpu::LoadOp::Clear(wgpu::Color {
                        r: 0.2,
                        g: 0.2,
                        b: 0.2,
                        a: 1.0,
                    }),
                    store: wgpu::StoreOp::Store,
                },
            })],
            ..Default::default()
        });
        renderer.render(&mut pass.forget_lifetime(), &jobs, &screen);
    }
    queue.submit(commands.into_iter().chain([encoder.finish()]));
    read(device, queue, &output)
}

#[test]
#[ignore = "real GPU: run explicitly with normal desktop permissions"]
fn native_float_pixels_ui_white_and_sdr_negative_control() {
    let instance = wgpu::Instance::new(&wgpu::InstanceDescriptor {
        backends: if cfg!(windows) {
            wgpu::Backends::DX12
        } else {
            wgpu::Backends::PRIMARY
        },
        ..Default::default()
    });
    let adapter = block_on(instance.request_adapter(&Default::default())).unwrap();
    let (device, queue) = block_on(adapter.request_device(&Default::default())).unwrap();
    eprintln!("GPU verification: {:?}", adapter.get_info());
    let hdr = photograph(&device, &queue, wgpu::TextureFormat::Rgba16Float, 0.0);
    assert!((hdr[0][0] - 0.625).abs() < 0.002, "{hdr:?}");
    assert!((hdr[0][1] - 5.0).abs() < 0.002 && (hdr[0][2] - 10.0).abs() < 0.002);
    assert!(hdr[0][2] > hdr[7][2] * 7.9); // Fixture carries real above-white contrast.
    let sdr = photograph(&device, &queue, wgpu::TextureFormat::Rgba8Unorm, 0.0);
    assert_eq!(sdr[0][1], sdr[0][2]); // Negative control destroys headroom contrast.
    assert_eq!(sdr[0][2], 1.0);
    let native_ui = ui(&device, &queue, 2.5);
    assert!((native_ui[1][0] - 2.5).abs() < 0.003);
    let alpha = 128.0 / 255.0;
    for (channel, straight) in [0.5f32, 0.25, 0.125].into_iter().enumerate() {
        let linear = if straight <= 0.04045 {
            straight / 12.92
        } else {
            ((straight + 0.055) / 1.055).powf(2.4)
        };
        let expected = linear * alpha * 2.5 + 0.2 * (1.0 - alpha);
        assert!(
            (native_ui[6][channel] - expected).abs() < 0.003,
            "{native_ui:?}; channel{channel} expected{expected}"
        );
    }
    let neutral_ui = ui(&device, &queue, 1.0);
    assert!((neutral_ui[1][0] - 1.0).abs() < 0.002);
    assert!(native_ui[6][0] > neutral_ui[6][0] + 0.1);
    eprintln!(
        "HDR {:?}; SDR placebo {:?}; UI {:?}",
        hdr[0], sdr[0], native_ui[6]
    );
}

fn sdr_presenter(
    adapter: &wgpu::Adapter,
    device: &wgpu::Device,
    queue: &wgpu::Queue,
    format: wgpu::TextureFormat,
    white: f32,
    options: egui_wgpu::RendererOptions,
) -> PhotoPresenter {
    let (pipeline, bindings) = photo_pipeline(device, format);
    let mut renderer = egui_wgpu::Renderer::new(device, format, options);
    renderer.set_output_white_scale(white);
    PhotoPresenter(Arc::new(Presenter {
        render: egui_wgpu::RenderState {
            adapter: adapter.clone(),
            available_adapters: vec![adapter.clone()],
            device: device.clone(),
            queue: queue.clone(),
            target_format: format,
            renderer: Arc::new(egui::mutex::RwLock::new(renderer)),
        },
        pipeline,
        bindings,
        status: RwLock::new(DisplayStatus {
            active: white > 1.0,
            sdr_white_nits: white * 80.0,
            ..Default::default()
        }),
        refresh: Mutex::new(Refresh {
            next: Instant::now(),
            pending: None,
            #[cfg(windows)]
            window: WindowDisplay::default(),
        }),
        #[cfg(any(windows, target_os = "macos"))]
        window: 0,
        #[cfg(target_os = "macos")]
        native_color_space: false,
        context: egui::Context::default(),
        sdr_retirement: Arc::default(),
    }))
}

#[test]
#[cfg(windows)]
fn display_changes_reject_a_previous_monitors_delayed_reply() {
    let mut window = WindowDisplay::default();
    assert!(window.observe_monitor(0x91));
    window.queried_monitor = 0x91;
    assert!(window.accepts_reply());
    // A drag inside the same monitor must not restart capability enumeration.
    assert!(!window.observe_monitor(0x91));
    assert!(window.accepts_reply());
    // Both directions matter: reject a stale HDR reply on SDR, and a stale SDR
    // reply when the photograph has returned to the HDR display.
    assert!(window.observe_monitor(0x38));
    assert!(!window.accepts_reply());
    window.queried_monitor = 0x38;
    assert!(window.accepts_reply());
    assert!(window.observe_monitor(0x91));
    assert!(!window.accepts_reply());
    window.queried_monitor = 0x91;
    assert!(window.accepts_reply());
    assert!(window.observe_monitor(0));
    assert!(!window.accepts_reply());
}

#[test]
#[cfg(windows)]
#[ignore = "real GPU: run explicitly with normal desktop permissions"]
fn actual_poll_discards_stale_monitor_reply_before_publishing_display_state() {
    let instance = wgpu::Instance::new(&wgpu::InstanceDescriptor {
        backends: wgpu::Backends::DX12,
        ..Default::default()
    });
    let adapter = block_on(instance.request_adapter(&Default::default())).unwrap();
    let (device, queue) = block_on(adapter.request_device(&Default::default())).unwrap();
    let mut presenter = sdr_presenter(
        &adapter,
        &device,
        &queue,
        wgpu::TextureFormat::Rgba16Float,
        1.0,
        Default::default(),
    );
    // This presenter deliberately owns no HWND. The actual OS lookup therefore
    // returns monitor 0. A queued HDR reply for an earlier real monitor must not
    // become active after that window disappears, even if the worker finishes.
    let before = presenter.status();
    let (tx, rx) = mpsc::sync_channel(1);
    tx.send(DisplayStatus {
        active: true,
        supported: true,
        monitor: "old HDR monitor".into(),
        sdr_white_nits: 240.0,
        peak_nits: 600.0,
        headroom: 2.5,
        ..Default::default()
    })
    .unwrap();
    {
        let mut refresh = presenter.0.refresh.lock().unwrap();
        refresh.next = Instant::now() + Duration::from_secs(60);
        refresh.window.monitor = 0;
        refresh.window.queried_monitor = 0x91;
        refresh.pending = Some(rx);
    }
    assert!(
        !presenter.poll(),
        "Stale HDR reply changed the active display"
    );
    assert_eq!(presenter.status(), before);
    assert!(presenter.0.refresh.lock().unwrap().pending.is_none());

    // Positive control: the real unavailable-window reply has the matching key,
    // must traverse the same receiver path and must update the displayed reason.
    let (tx, rx) = mpsc::sync_channel(1);
    tx.send(platform::detect_monitor(0)).unwrap();
    {
        let mut refresh = presenter.0.refresh.lock().unwrap();
        refresh.window.queried_monitor = 0;
        refresh.pending = Some(rx);
    }
    assert!(
        presenter.poll(),
        "Matching current-monitor reply was not published"
    );
    let actual = presenter.status();
    assert!(!actual.active && !actual.supported && actual.monitor.is_empty());
    assert_eq!(actual.sdr_white_nits, 80.0);
    assert_eq!(actual.headroom, 1.0);
    assert!(actual.reason.contains("unavailable"));
    assert!(presenter.0.refresh.lock().unwrap().pending.is_none());
}

fn draw_sdr_layers(presenter: &PhotoPresenter, layer: &PhotoLayer, alpha: f32) -> Vec<[f32; 4]> {
    let render = &presenter.0.render;
    let ctx = &presenter.0.context;
    let screen_rect = Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(8.0, 2.0));
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(screen_rect),
            ..Default::default()
        },
        |ctx| {
            let painter = ctx.layer_painter(egui::LayerId::background());
            // Two placements of the same layer must keep independent UVs and
            // both remain ordinary mesh draws on the optimized target formats.
            for (x, aperture) in [
                (
                    0.0,
                    Rect::from_min_max(egui::pos2(0.25, 0.0), egui::pos2(0.75, 1.0)),
                ),
                (
                    4.0,
                    Rect::from_min_max(egui::pos2(0.0, 0.0), egui::pos2(0.5, 1.0)),
                ),
            ] {
                presenter.paint_sdr_layer(
                    &painter,
                    Rect::from_min_size(egui::pos2(x, 0.0), egui::vec2(4.0, 2.0)),
                    aperture,
                    layer,
                    alpha,
                );
            }
        },
    );
    let jobs = ctx.tessellate(output.shapes, output.pixels_per_point);
    if !render.target_format.is_srgb() || alpha == 1.0 {
        assert!(
            jobs.iter()
                .all(|job| matches!(job.primitive, egui::epaint::Primitive::Mesh(_)))
        );
        assert!(!jobs.is_empty(), "The fixture must emit real image meshes");
    } else {
        assert!(
            jobs.iter()
                .any(|job| matches!(job.primitive, egui::epaint::Primitive::Callback(_)))
        );
    }
    let screen = egui_wgpu::ScreenDescriptor {
        size_in_pixels: [8, 2],
        pixels_per_point: 1.0,
    };
    let texture = target(&render.device, render.target_format);
    let view = texture.create_view(&Default::default());
    let mut encoder = render.device.create_command_encoder(&Default::default());
    let mut renderer = render.renderer.write();
    let commands =
        renderer.update_buffers(&render.device, &render.queue, &mut encoder, &jobs, &screen);
    {
        let pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
            color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                view: &view,
                resolve_target: None,
                depth_slice: None,
                ops: wgpu::Operations {
                    load: wgpu::LoadOp::Clear(wgpu::Color {
                        r: 0.15,
                        g: 0.25,
                        b: 0.35,
                        a: 1.0,
                    }),
                    store: wgpu::StoreOp::Store,
                },
            })],
            ..Default::default()
        });
        renderer.render(&mut pass.forget_lifetime(), &jobs, &screen);
    }
    drop(renderer);
    render
        .queue
        .submit(commands.into_iter().chain([encoder.finish()]));
    read(&render.device, &render.queue, &texture)
}

#[test]
#[ignore = "real GPU: run explicitly with normal desktop permissions"]
fn registered_sdr_images_preserve_color_crop_alpha_and_deferred_lifetime() {
    let instance = wgpu::Instance::new(&wgpu::InstanceDescriptor {
        backends: if cfg!(windows) {
            wgpu::Backends::DX12
        } else {
            wgpu::Backends::PRIMARY
        },
        ..Default::default()
    });
    let adapter = block_on(instance.request_adapter(&Default::default())).unwrap();
    let (device, queue) = block_on(adapter.request_device(&Default::default())).unwrap();
    eprintln!("Registered SDR GPU verification: {:?}", adapter.get_info());
    let colors = [
        [32u8, 128, 224, 255],
        [192, 64, 96, 255],
        [80, 176, 48, 255],
        [240, 112, 160, 255],
    ];
    let decode = |v: f32| {
        if v <= 0.04045 {
            v / 12.92
        } else {
            ((v + 0.055) / 1.055).powf(2.4)
        }
    };
    let encode = |v: f32| {
        if v <= 0.0031308 {
            v * 12.92
        } else {
            1.055 * v.powf(1.0 / 2.4) - 0.055
        }
    };
    for (format, options) in [
        wgpu::TextureFormat::Rgba16Float,
        wgpu::TextureFormat::Rgba8Unorm,
        wgpu::TextureFormat::Rgba8UnormSrgb,
    ]
    .into_iter()
    .flat_map(|format| {
        [egui_wgpu::RendererOptions::PREDICTABLE, Default::default()]
            .map(|options| (format, options))
    }) {
        for white in [1.0, 2.5] {
            let presenter = sdr_presenter(&adapter, &device, &queue, format, white, options);
            // The actual upload/registration takes place on a worker thread.
            let upload = presenter.clone();
            let bytes: Arc<[u8]> = colors.into_iter().flatten().collect::<Vec<_>>().into();
            let layer = std::thread::spawn(move || {
                upload
                    .upload_sdr([4, 1], bytes, [[0.0, 0.0], [1.0, 1.0]])
                    .unwrap()
            })
            .join()
            .unwrap();
            let id = layer.0.registered.as_ref().unwrap().id;
            for alpha in [1.0, 0.37] {
                let actual = draw_sdr_layers(&presenter, &layer, alpha);
                let quantized_alpha = egui::Color32::WHITE.gamma_multiply(alpha).a() as f32 / 255.0;
                for (x, pixel) in actual[..8].iter().enumerate() {
                    // Apertures sample source positions .75..2.25 and -.25..1.25.
                    let location = if x < 4 {
                        0.75 + x as f32 * 0.5
                    } else {
                        -0.25 + (x - 4) as f32 * 0.5
                    };
                    let lo = location.floor() as i32;
                    let t = location - location.floor();
                    for c in 0..3 {
                        let sample = (f32::from(colors[lo.clamp(0, 3) as usize][c]) * (1.0 - t)
                            + f32::from(colors[(lo + 1).clamp(0, 3) as usize][c]) * t)
                            / 255.0;
                        let background = [0.15, 0.25, 0.35][c];
                        let expected = if format == wgpu::TextureFormat::Rgba16Float {
                            decode(sample) * quantized_alpha * white
                                + background * (1.0 - quantized_alpha)
                        } else if format.is_srgb() {
                            encode(decode(sample) * alpha + background * (1.0 - alpha))
                        } else {
                            sample * quantized_alpha + background * (1.0 - quantized_alpha)
                        };
                        assert!(
                            (pixel[c] - expected).abs() < 0.006,
                            "{format:?} white{white} alpha{alpha} pixel{x} c{c}: {} vs {expected}",
                            pixel[c]
                        );
                    }
                }
                assert_ne!(
                    actual[0], actual[4],
                    "Two distinct crops must remain distinct"
                );
            }
            let retained = layer.clone();
            drop(layer);
            assert!(presenter.0.sdr_retirement.0.lock().unwrap().is_empty());
            assert!(presenter.0.render.renderer.read().texture(&id).is_some());
            let replacement = presenter
                .upload_sdr([1, 1], Arc::from([255u8; 4]), [[0.0, 0.0], [1.0, 1.0]])
                .unwrap();
            let replacement_id = replacement.0.registered.as_ref().unwrap().id;
            assert_ne!(id, replacement_id);
            drop(retained);
            presenter.retire_sdr_textures();
            assert!(
                presenter.0.render.renderer.read().texture(&id).is_some(),
                "Already-emitted meshes must keep their binding"
            );
            for elapsed in 1..=2 {
                let _ = presenter.0.context.run(Default::default(), |_| {});
                presenter.retire_sdr_textures();
                assert_eq!(
                    presenter.0.render.renderer.read().texture(&id).is_some(),
                    elapsed < 2,
                    "Retirement must follow the completed-frame boundary"
                );
            }
            presenter.retire_sdr_textures();
            assert!(presenter.0.render.renderer.read().texture(&id).is_none());
            assert!(
                presenter
                    .0
                    .render
                    .renderer
                    .read()
                    .texture(&replacement_id)
                    .is_some()
            );
            drop(replacement);
            for _ in 0..2 {
                let _ = presenter.0.context.run(Default::default(), |_| {});
            }
            presenter.retire_sdr_textures();
            assert!(
                presenter
                    .0
                    .render
                    .renderer
                    .read()
                    .texture(&replacement_id)
                    .is_none()
            );
            assert!(presenter.0.sdr_retirement.0.lock().unwrap().is_empty());
            let region = presenter
                .upload_sdr([1, 1], Arc::from([255u8; 4]), [[0.2, 0.3], [0.8, 0.9]])
                .unwrap();
            let clip = Rect::from_min_max(egui::pos2(1.0, 0.5), egui::pos2(9.0, 3.5));
            let output = presenter.0.context.run(
                egui::RawInput {
                    screen_rect: Some(Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(12.0, 8.0))),
                    ..Default::default()
                },
                |ctx| {
                    let painter = ctx
                        .layer_painter(egui::LayerId::background())
                        .with_clip_rect(clip);
                    presenter.paint_sdr_layer(
                        &painter,
                        Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(10.0, 4.0)),
                        Rect::from_min_max(egui::pos2(0.05, 0.15), egui::pos2(0.65, 0.75)),
                        &region,
                        1.0,
                    );
                },
            );
            let meshes = output
                .shapes
                .iter()
                .filter_map(|shape| {
                    if let egui::Shape::Mesh(mesh) = &shape.shape {
                        Some((shape.clip_rect, mesh))
                    } else {
                        None
                    }
                })
                .collect::<Vec<_>>();
            assert_eq!(meshes.len(), 1);
            assert_eq!(meshes[0].0, clip);
            let bounds = meshes[0].1.calc_bounds();
            assert!(bounds.min.distance(egui::pos2(2.5, 1.0)) < 0.00001);
            assert!(bounds.max.distance(egui::pos2(10.0, 4.0)) < 0.00001);
            let uv_bounds = Rect::from_points(
                &meshes[0]
                    .1
                    .vertices
                    .iter()
                    .map(|v| v.uv)
                    .collect::<Vec<_>>(),
            );
            assert!(uv_bounds.min.distance(egui::Pos2::ZERO) < 0.00001);
            assert!(uv_bounds.max.distance(egui::pos2(0.75, 0.75)) < 0.00001);
        }
    }
}
