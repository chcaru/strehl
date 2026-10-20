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
