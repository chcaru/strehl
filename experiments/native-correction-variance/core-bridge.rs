// Feature-gated access to the actual production kernels; no alternate filters.
use super::{LevelSize, Pyramid, Workspace};

pub fn laplacian(luma: &[f32], sizes: &[LevelSize]) -> Vec<Vec<f32>> {
    let mut pyramid = Pyramid::zeros(sizes);
    pyramid.build(luma, &mut Workspace::new(sizes));
    (0..pyramid.bands()).map(|k| pyramid.level(k).to_vec()).collect()
}
pub fn gaussian(variance: &[f32], sizes: &[LevelSize]) -> Vec<Vec<f32>> {
    let mut pyramid = Pyramid::zeros(sizes);
    pyramid.build_gaussian(variance, &mut Workspace::new(sizes));
    (0..pyramid.bands()).map(|k| pyramid.level(k).to_vec()).collect()
}
pub fn smooth(values: &[f32], size: LevelSize) -> Vec<f32> {
    let mut result = values.to_vec();
    super::smooth5(&mut result, size, &mut vec![0.0; size.pixels()+size.width]);
    result
}
pub fn energy(coefficients: &[f32], size: LevelSize) -> Vec<f32> {
    let squared: Vec<f32> = coefficients.iter().map(|x| x*x).collect();
    smooth(&squared, size)
}
