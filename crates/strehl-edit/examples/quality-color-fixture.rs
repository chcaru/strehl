//! Independent review fixture for color conversion and PQ metadata.
use strehl_edit::*;
fn main() -> anyhow::Result<()> {
    let dir = std::path::PathBuf::from(std::env::args().nth(1).expect("output directory"));
    std::fs::create_dir_all(&dir)?;
    let patches: [[f32; 3]; 8] = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [2.0, 0.25, 0.08],
        [0.03, 1.8, 0.12],
        [0.1, 0.06, 3.0],
        [1.6, 1.6, 1.6],
        [-0.02, 0.15, 0.8],
    ];
    let mut pixels = Vec::new();
    for _y in 0..64 {
        for x in 0..256 {
            pixels.extend_from_slice(&patches[x / 32]);
        }
    }
    let image = LinearImage {
        width: 256,
        height: 64,
        pixels,
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    };
    let mut recipe = DevelopmentRecipe::default();
    recipe.hdr.reference_white_nits = 250.0; // Alternate from author's 203 nit fixture.
    recipe.hdr.peak_nits = 1500.0;
    recipe.hdr.quality = 100;
    recipe.hdr.speed = 8;
    save_linear_tiff(&dir.join("color.linear.tiff"), &image)?;
    let report = export_hdr_avif(&dir.join("color.avif"), &image, &recipe)?;
    std::fs::write(
        dir.join("fixture.json"),
        serde_json::to_vec_pretty(&serde_json::json!({
            "patches_linear_bt709":patches,"reference_white_nits":250.0,"report":report
        }))?,
    )?;
    Ok(())
}
