//! Generate a deterministic HDR/color fixture for independent decoder verification.
use strehl_edit::*;
fn main() -> anyhow::Result<()> {
    let dir = std::path::PathBuf::from(std::env::args().nth(1).expect("output directory"));
    std::fs::create_dir_all(&dir)?;
    let width = 128u32;
    let height = 64u32;
    let mut pixels = vec![0.0; (width * height * 3) as usize];
    let levels = [0.01, 0.18, 0.5, 1.0, 2.0, 4.0, 0.1, 0.8];
    for y in 0..height {
        for x in 0..width {
            let tile = (x / 16) as usize;
            let value = levels[tile];
            let p = if y < 32 {
                [value; 3]
            } else {
                match tile % 4 {
                    0 => [value, 0.0, 0.0],
                    1 => [0.0, value, 0.0],
                    2 => [0.0, 0.0, value],
                    _ => [value, value * 0.7, value * 0.2],
                }
            };
            let i = ((y * width + x) * 3) as usize;
            pixels[i..i + 3].copy_from_slice(&p);
        }
    }
    let image = LinearImage {
        width,
        height,
        pixels,
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    };
    let recipe = DevelopmentRecipe {
        hdr: HdrSettings {
            quality: 100,
            speed: 10,
            ..Default::default()
        },
        ..Default::default()
    };
    save_linear_tiff(&dir.join("fixture.linear.tiff"), &image)?;
    let report = export_hdr_avif(&dir.join("fixture.avif"), &image, &recipe)?;
    println!("{}", serde_json::to_string_pretty(&report)?);
    Ok(())
}
