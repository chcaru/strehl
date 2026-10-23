//! Independent readback choices: cropped UVs, negative scRGB, peak fitting,
//! fractional detail opacity, and both SDR attachment encodings.
use super::*;

fn wait<T>(future: impl std::future::Future<Output = T>) -> T {
    struct Signal(std::thread::Thread);
    impl std::task::Wake for Signal {
        fn wake(self: Arc<Self>) {
            self.0.unpark();
        }
    }
    let waker = std::task::Waker::from(Arc::new(Signal(std::thread::current())));
    let mut context = std::task::Context::from_waker(&waker);
    let mut future = std::pin::pin!(future);
    loop {
        if let std::task::Poll::Ready(value) = future.as_mut().poll(&mut context) {
            return value;
        }
        std::thread::park();
    }
}

fn draw(
    device: &wgpu::Device,
    queue: &wgpu::Queue,
    format: wgpu::TextureFormat,
    source: &[[f32; 4]; 8],
    parameters: [f32; 8],
) -> Vec<[f32; 4]> {
    let (pipeline, layout) = photo_pipeline(device, format);
    let input = device.create_texture(&wgpu::TextureDescriptor {
        label: Some("Independent crop fixture"),
        size: wgpu::Extent3d {
            width: 4,
            height: 2,
            depth_or_array_layers: 1,
        },
        mip_level_count: 1,
        sample_count: 1,
        dimension: wgpu::TextureDimension::D2,
        format: wgpu::TextureFormat::Rgba32Float,
        usage: wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::COPY_DST,
        view_formats: &[],
    });
    queue.write_texture(
        input.as_image_copy(),
        bytemuck::cast_slice(source),
        wgpu::TexelCopyBufferLayout {
            offset: 0,
            bytes_per_row: Some(64),
            rows_per_image: Some(2),
        },
        input.size(),
    );
    let view = input.create_view(&Default::default());
    let uniform = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: None,
        contents: bytemuck::cast_slice(&parameters),
        usage: wgpu::BufferUsages::UNIFORM,
    });
    let group = device.create_bind_group(&wgpu::BindGroupDescriptor {
        label: None,
        layout: &layout,
        entries: &[
            wgpu::BindGroupEntry {
                binding: 0,
                resource: wgpu::BindingResource::TextureView(&view),
            },
            wgpu::BindGroupEntry {
                binding: 1,
                resource: uniform.as_entire_binding(),
            },
        ],
    });
    let output = device.create_texture(&wgpu::TextureDescriptor {
        label: Some("Independent output"),
        size: wgpu::Extent3d {
            width: 2,
            height: 2,
            depth_or_array_layers: 1,
        },
        mip_level_count: 1,
        sample_count: 1,
        dimension: wgpu::TextureDimension::D2,
        format,
        usage: wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::COPY_SRC,
        view_formats: &[],
    });
    let target = output.create_view(&Default::default());
    let readback = device.create_buffer(&wgpu::BufferDescriptor {
        label: None,
        size: 512,
        usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ,
        mapped_at_creation: false,
    });
    let mut encoder = device.create_command_encoder(&Default::default());
    {
        let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
            color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                view: &target,
                resolve_target: None,
                depth_slice: None,
                ops: wgpu::Operations {
                    load: wgpu::LoadOp::Clear(wgpu::Color {
                        r: 0.05,
                        g: 0.2,
                        b: 0.4,
                        a: 1.0,
                    }),
                    store: wgpu::StoreOp::Store,
                },
            })],
            ..Default::default()
        });
        pass.set_pipeline(&pipeline);
        pass.set_bind_group(0, &group, &[]);
        pass.draw(0..3, 0..1);
    }
    encoder.copy_texture_to_buffer(
        output.as_image_copy(),
        wgpu::TexelCopyBufferInfo {
            buffer: &readback,
            layout: wgpu::TexelCopyBufferLayout {
                offset: 0,
                bytes_per_row: Some(256),
                rows_per_image: Some(2),
            },
        },
        output.size(),
    );
    queue.submit([encoder.finish()]);
    let (sender, receiver) = mpsc::channel();
    readback
        .slice(..)
        .map_async(wgpu::MapMode::Read, move |result| {
            sender.send(result).unwrap();
        });
    device.poll(wgpu::PollType::wait_indefinitely()).unwrap();
    receiver.recv().unwrap().unwrap();
    let bytes = readback.slice(..).get_mapped_range();
    let mut pixels = Vec::new();
    for y in 0..2 {
        for x in 0..2 {
            pixels.push(std::array::from_fn(|c| {
                if format == wgpu::TextureFormat::Rgba16Float {
                    let offset = y * 256 + x * 8 + c * 2;
                    let bits = u16::from_le_bytes([bytes[offset], bytes[offset + 1]]);
                    let sign = if bits & 32768 == 0 { 1.0 } else { -1.0 };
                    let exponent = (bits >> 10) & 31;
                    let mantissa = (bits & 1023) as f32;
                    sign * if exponent == 0 {
                        mantissa / 16777216.0
                    } else {
                        (1024.0 + mantissa) * 2.0f32.powi(exponent as i32 - 25)
                    }
                } else {
                    bytes[y * 256 + x * 4 + c] as f32 / 255.0
                }
            }));
        }
    }
    pixels
}

#[test]
#[ignore = "independent real-GPU review; run explicitly on a desktop"]
fn independent_crop_peak_alpha_and_sdr_encodings() {
    let instance = wgpu::Instance::new(&wgpu::InstanceDescriptor {
        backends: if cfg!(windows) {
            wgpu::Backends::DX12
        } else {
            wgpu::Backends::PRIMARY
        },
        ..Default::default()
    });
    let adapter = wait(instance.request_adapter(&Default::default())).unwrap();
    let (device, queue) = wait(adapter.request_device(&Default::default())).unwrap();
    let source = [
        [9.0, 0.0, 0.0, 1.0],
        [-0.07, 0.6, 3.5, 1.0],
        [0.02, 0.3, 0.7, 1.0],
        [0.0, 9.0, 0.0, 1.0],
        [0.0, 0.0, 9.0, 1.0],
        [2.0, 1.0, 0.1, 1.0],
        [0.001, 0.002, 0.003, 1.0],
        [9.0, 9.0, 9.0, 1.0],
    ];
    let result = draw(
        &device,
        &queue,
        wgpu::TextureFormat::Rgba16Float,
        &source,
        [0.25, 0.0, 0.75, 1.0, 1.25, 3.0, 0.375, 0.0],
    );
    let expected_linear = [
        [-0.06, 0.5142857, 3.0],
        [0.025, 0.375, 0.875],
        [2.5, 1.25, 0.125],
        [0.00125, 0.0025, 0.00375],
    ];
    for (actual, expected) in result.iter().zip(expected_linear) {
        for c in 0..3 {
            let composite = expected[c] * 0.375 + [0.05, 0.2, 0.4][c] * 0.625;
            assert!(
                (actual[c] - composite).abs() < 0.002,
                "{actual:?} expected {composite}"
            );
        }
    }
    assert!(result[0][2] > 1.0, "fixture must retain above-white detail");
    // An uncropped/fixed-UV implementation would pull the red/green/blue sentinels.
    let gamma = [[0.02, 0.3, 0.8, 1.0]; 8];
    let linear = draw(
        &device,
        &queue,
        wgpu::TextureFormat::Rgba16Float,
        &gamma,
        [0.25, 0.0, 0.75, 1.0, 1.75, 1.0, 1.0, 2.0],
    );
    for (c, expected) in [0.0015479876, 0.07323896, 0.60382734]
        .into_iter()
        .enumerate()
    {
        assert!((linear[0][c] - expected * 1.75).abs() < 0.002);
    }
    for (format, mode) in [
        (wgpu::TextureFormat::Rgba8Unorm, 1.0),
        (wgpu::TextureFormat::Rgba8UnormSrgb, 3.0),
    ] {
        let sdr = draw(
            &device,
            &queue,
            format,
            &gamma,
            [0.25, 0.0, 0.75, 1.0, 1.0, 1.0, 1.0, mode],
        );
        for (actual, expected) in sdr[0].into_iter().zip(gamma[0]) {
            assert!(
                (actual - expected).abs() <= 1.1 / 255.0,
                "{format:?}: {sdr:?}"
            );
        }
    }
    eprintln!(
        "Independent GPU {:?}: cropped HDR={:?}, SDR-in-linear={:?}",
        adapter.get_info().name,
        result,
        linear[0]
    );
}
