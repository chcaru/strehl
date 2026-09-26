// Experiment-owned calibration math. No source selection, scene fit or RAW IO.
use anyhow::{ensure,Result};
use serde::{Deserialize,Serialize};

pub type Matrix=[[f64;3];3];
pub const WARM_KELVIN:f64=2856.0;
pub const COOL_KELVIN:f64=6504.0;
const BRADFORD:Matrix=[[0.8951,0.2664,-0.1614],[-0.7502,1.7135,0.0367],[0.0389,-0.0685,1.0296]];

#[derive(Clone,Debug,Serialize,Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NamedMatrix {pub name:String,pub bits:[[u32;3];3]}
#[derive(Clone,Debug,Serialize,Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CameraMetadata {
    pub camera:String,pub wb_gains_bits:[u32;3],pub matrices:Vec<NamedMatrix>,
    pub selected_source:String,pub selected_matrix_bits:[[u32;3];3],pub direct_matrix_bits:[[u32;3];4],
}
#[derive(Clone,Debug,Serialize,Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Transform {
    pub matrix:[[f32;3];3],pub matrix_f64:Matrix,pub source_white_xyz:[f64;3],
    pub unnormalized_white_y:f64,pub camera_neutral:[f64;3],
}
#[derive(Clone,Debug,Serialize,Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Selection {
    pub warm:NamedMatrix,pub cool:NamedMatrix,pub warm_kelvin:f64,pub cool_kelvin:f64,
    pub shot_kelvin:f64,pub warm_fraction:f64,pub interpolated_xyz_to_camera:Matrix,pub transform:Transform,
}
pub fn apply(m:Matrix,v:[f64;3])->[f64;3] {
    std::array::from_fn(|i|(0..3).map(|j|m[i][j]*v[j]).sum())
}
fn multiply(a:Matrix,b:Matrix)->Matrix {
    std::array::from_fn(|i|std::array::from_fn(|j|(0..3).map(|k|a[i][k]*b[k][j]).sum()))
}
fn diagonal(v:[f64;3])->Matrix {
    std::array::from_fn(|i|std::array::from_fn(|j|if i==j{v[i]}else{0.0}))
}
fn inverse(m:Matrix)->Result<Matrix> {
    ensure!(m.iter().flatten().all(|v|v.is_finite()),"nonfinite color matrix");
    let scale=m.iter().flatten().copied().map(f64::abs).fold(0.0f64,f64::max);
    ensure!(scale>0.0,"zero color matrix");
    let a=m.map(|r|r.map(|v|v/scale));
    let det=a[0][0]*(a[1][1]*a[2][2]-a[1][2]*a[2][1])
        -a[0][1]*(a[1][0]*a[2][2]-a[1][2]*a[2][0])
        +a[0][2]*(a[1][0]*a[2][1]-a[1][1]*a[2][0]);
    ensure!(det.is_finite()&&det.abs()>=1e-12,"singular or ill-conditioned color matrix");
    let out:Matrix=std::array::from_fn(|i|std::array::from_fn(|j|{
        let(r0,r1)=((j+1)%3,(j+2)%3);let(c0,c1)=((i+1)%3,(i+2)%3);
        (a[r0][c0]*a[r1][c1]-a[r0][c1]*a[r1][c0])/det/scale
    }));
    ensure!(out.iter().flatten().all(|v|v.is_finite()),"nonfinite matrix inverse");
    Ok(out)
}
pub fn interpolate(warm:Matrix,cool:Matrix,warm_kelvin:f64,cool_kelvin:f64,shot_kelvin:f64)->Result<(Matrix,f64)> {
    ensure!(warm_kelvin.is_finite()&&cool_kelvin.is_finite()&&shot_kelvin.is_finite()
        &&warm_kelvin>0.0&&cool_kelvin>warm_kelvin&&shot_kelvin>0.0,"invalid calibration temperature");
    inverse(warm)?;inverse(cool)?;
    let a=((1.0/shot_kelvin-1.0/cool_kelvin)/(1.0/warm_kelvin-1.0/cool_kelvin)).clamp(0.0,1.0);
    let matrix=std::array::from_fn(|i|std::array::from_fn(|j|a*warm[i][j]+(1.0-a)*cool[i][j]));
    inverse(matrix)?;Ok((matrix,a))
}
pub fn replacement(xyz_to_camera:Matrix,wb:[f64;3])->Result<Transform> {
    ensure!(wb.iter().all(|v|v.is_finite()&&*v>0.0),"invalid as-shot WB");
    let camera_neutral=wb.map(|v|1.0/v);
    let camera_to_xyz=inverse(xyz_to_camera)?;
    let white=apply(camera_to_xyz,camera_neutral);
    ensure!(white.iter().all(|v|v.is_finite()&&*v>0.0),"invalid source white from matrix/WB");
    let unnormalized_white_y=white[1];let source_white_xyz=white.map(|v|v/unnormalized_white_y);
    let destination=strehl_core::color::D65_XYZ;
    let source_cones=apply(BRADFORD,source_white_xyz);let destination_cones=apply(BRADFORD,destination);
    ensure!(source_cones.iter().chain(&destination_cones).all(|v|v.is_finite()&&*v>0.0),"invalid Bradford cone response");
    let ratio=std::array::from_fn(|i|destination_cones[i]/source_cones[i]);
    let cat=multiply(multiply(inverse(BRADFORD)?,diagonal(ratio)),BRADFORD);
    let rgb_from_xyz=inverse(strehl_core::color::SRGB_TO_XYZ_D65)?;
    let matrix_f64=multiply(multiply(multiply(rgb_from_xyz,cat),camera_to_xyz),diagonal(camera_neutral))
        .map(|r|r.map(|v|v/unnormalized_white_y));
    let matrix=matrix_f64.map(|r|r.map(|v|v as f32));
    ensure!(matrix.iter().flatten().all(|v|v.is_finite()),"replacement matrix exceeds f32 range");
    ensure!(apply(matrix_f64,[1.0;3]).iter().all(|v|(*v-1.0).abs()<2e-6),"replacement does not preserve unit neutral");
    Ok(Transform{matrix,matrix_f64,source_white_xyz,unnormalized_white_y,camera_neutral})
}
fn value(m:&NamedMatrix)->Matrix {m.bits.map(|r|r.map(|v|f64::from(f32::from_bits(v))))}
pub fn select(meta:&CameraMetadata,shot_kelvin:f64)->Result<Selection> {
    ensure!(meta.camera=="ILCE-7CM2","experiment is scoped to the recorded camera");
    ensure!(meta.direct_matrix_bits.iter().flatten().all(|v|f32::from_bits(*v)==0.0),
        "direct matrix is nonzero or ambiguous; no inferred dual-calibration semantics");
    ensure!(meta.selected_source=="decoder color_matrix[D65]","current selected calibration is not held D65");
    let choose=|name:&str|->Result<NamedMatrix>{let matches=meta.matrices.iter().filter(|m|m.name==name).collect::<Vec<_>>();
        ensure!(matches.len()==1,"missing or duplicated exact calibration label {name}");Ok(matches[0].clone())};
    let warm=choose("A")?;let cool=choose("D65")?;
    ensure!(cool.bits==meta.selected_matrix_bits,"selected D65 and calibration table differ");
    let wb=meta.wb_gains_bits.map(|v|f64::from(f32::from_bits(v)));
    ensure!(wb[1]==1.0,"consumed WB must be green-normalized");
    let(interpolated_xyz_to_camera,warm_fraction)=interpolate(value(&warm),value(&cool),WARM_KELVIN,COOL_KELVIN,shot_kelvin)?;
    let transform=replacement(interpolated_xyz_to_camera,wb)?;
    Ok(Selection{warm,cool,warm_kelvin:WARM_KELVIN,cool_kelvin:COOL_KELVIN,shot_kelvin,warm_fraction,
        interpolated_xyz_to_camera,transform})
}
