// Independent algebra/metadata controls. No RAW or photographic truth claim.
use super::operator::{self, CameraMetadata, Matrix, NamedMatrix};

// Numerical facts: ICC Technical Note 02-2003, https://www.color.org/chadtag/.
const BRADFORD: Matrix = [[0.8951,0.2664,-0.1614],[-0.7502,1.7135,0.0367],[0.0389,-0.0685,1.0296]];
// Independently selected non-diagonal camera, not a Sony calibration.
const CAMERA: Matrix = [[0.80,0.12,0.04],[0.08,0.91,0.05],[0.02,0.11,0.65]];
const WARM_WHITE: [f64;3] = [1.12,1.0,0.40];
const PATCHES: [[f64;3];5] = [[0.10,0.05,0.02],[0.10,0.20,0.03],[0.08,0.10,0.25],
    [0.45,0.35,0.08],[0.04,0.06,0.02]];

fn mv(a: Matrix, x: [f64;3]) -> [f64;3] {
    std::array::from_fn(|i| (0..3).map(|j|a[i][j]*x[j]).sum())
}
fn transpose(a: Matrix) -> Matrix { std::array::from_fn(|i|std::array::from_fn(|j|a[j][i])) }
// Independent partial-pivot Gauss-Jordan, not the candidate's inverse helper.
fn inverse(a: Matrix) -> Matrix {
    let mut m=[[0.0;6];3];
    for i in 0..3 {for j in 0..3 {m[i][j]=a[i][j];}m[i][i+3]=1.0;}
    for k in 0..3 {
        let pivot=(k..3).max_by(|&i,&j|m[i][k].abs().total_cmp(&m[j][k].abs())).unwrap();
        assert!(m[pivot][k].abs()>1e-12);m.swap(k,pivot);
        let scale=m[k][k];for j in 0..6 {m[k][j]/=scale;}
        let row=m[k];
        for i in 0..3 {if i!=k {let s=m[i][k];for j in 0..6 {m[i][j]-=s*row[j];}}}
    }
    std::array::from_fn(|i|std::array::from_fn(|j|m[i][j+3]))
}
fn max_error(a:[f64;3],b:[f64;3])->f64 {(0..3).map(|i|(a[i]-b[i]).abs()).fold(0.0,f64::max)}
fn matrix_error(a:Matrix,b:Matrix)->f64 {(0..3).map(|i|max_error(a[i],b[i])).fold(0.0,f64::max)}
fn srgb_from_xyz(x:[f64;3])->[f64;3] {mv(inverse(strehl_core::color::SRGB_TO_XYZ_D65),x)}
fn adapt(x:[f64;3],white:[f64;3])->[f64;3] {
    let response=mv(BRADFORD,x);let source=mv(BRADFORD,white);
    let target=mv(BRADFORD,strehl_core::color::D65_XYZ);
    mv(inverse(BRADFORD),std::array::from_fn(|i|response[i]*target[i]/source[i]))
}
fn wb(camera:Matrix,white:[f64;3])->[f64;3] {
    let n=mv(camera,white);[n[1]/n[0],1.0,n[1]/n[2]]
}
fn balanced_patch(camera:Matrix,white:[f64;3],xyz:[f64;3])->[f64;3] {
    // Prescribed XYZ -> independent forward camera response, normalized by the
    // independently prescribed white. Never invert the candidate to make truth.
    let p=mv(camera,xyz);let n=mv(camera,white);
    std::array::from_fn(|i|p[i]/n[i])
}
fn f64_matrix(a:[[f32;3];3])->Matrix {a.map(|r|r.map(f64::from))}

fn flat_first(matrix:[[f32;3];3],w:[f64;3]) {
    // This validates propagated covariance, NOT equal noise between two colour
    // transforms. The eight balanced sign draws have prescribed diagonal input
    // covariance. All values are far below the unchanged sensor knee/ceilings.
    let levels=strehl_core::noise::Levels{black:512.0,white:15360.0};
    let candidate=strehl_core::color::Render::new(matrix).with_saturation(levels,w.map(|v|v as f32),1.0);
    let baseline=strehl_core::color::camera_to_srgb(CAMERA.map(|r|r.map(|v|v as f32))).unwrap()
        .with_saturation(levels,w.map(|v|v as f32),1.0);
    let center=[0.2f32;3];let c0=candidate.develop(center);let b0=baseline.develop(center);
    assert!(max_error(c0.map(f64::from),[0.2;3])<2e-6);
    let mut cv=[0.0f64;3];let mut bv=[0.0f64;3];let mut ev=[0.0f64;3];
    let n=mv(CAMERA,WARM_WHITE);let camera_inverse=inverse(CAMERA);
    for draw in 0..8 {
        let x: [f32;3]=std::array::from_fn(|i|center[i]+if draw&(1<<i)==0 {-[0.001,0.002,0.003][i]}else{[0.001,0.002,0.003][i]});
        let noise:[f64;3]=std::array::from_fn(|i|f64::from(x[i])-f64::from(center[i]));
        let xyz=mv(camera_inverse,std::array::from_fn(|i|n[i]*noise[i]));
        let expected=srgb_from_xyz(adapt(xyz,WARM_WHITE));
        let cp=candidate.develop(x);let bp=baseline.develop(x);
        for i in 0..3 {
            cv[i]+=(f64::from(cp[i])-f64::from(c0[i])).powi(2)/8.0;
            bv[i]+=(f64::from(bp[i])-f64::from(b0[i])).powi(2)/8.0;
            ev[i]+=expected[i].powi(2)/8.0;
        }
    }
    assert!((0..3).all(|i|ev[i]>1e-8&&bv[i]>1e-8&&(cv[i]-ev[i]).abs()<=ev[i]*5e-4+1e-11));
    let ratios: [f64;3]=std::array::from_fn(|i|cv[i]/bv[i]);
    let propagation_relative_error: [f64;3]=std::array::from_fn(|i|(cv[i]-ev[i]).abs()/ev[i]);
    println!("ILLUMINANT_FLAT {}",serde_json::json!({"candidate_variance":cv,"baseline_variance":bv,
        "independent_expected_variance":ev,"candidate_baseline_variance_ratio":ratios,
        "propagation_relative_error":propagation_relative_error,
        "scope":"actual Render covariance arithmetic only; no photographic quality admission"}));
}

#[test]
fn independent_d65_equivalence_controls() {
    let camera=CAMERA.map(|r|r.map(|v|v as f32));
    let c=f64_matrix(camera);
    let w=wb(c,strehl_core::color::D65_XYZ);
    let result=operator::replacement(c,w).unwrap();
    let current=strehl_core::color::camera_to_srgb(camera).unwrap();
    assert!(matrix_error(result.matrix_f64,f64_matrix(*current.matrix()))<2e-6);
    for p in [[1.0;3],[0.7,0.2,0.1],[0.03,0.08,0.8],[0.1,0.1,0.0]] {
        assert!(max_error(mv(result.matrix_f64,p),mv(f64_matrix(*current.matrix()),p))<2e-6);
    }
    // A neutral-preserving wrong map can be perfect on grey and wrong on colour.
    let wrong:Matrix=[[1.15,-0.15,0.0],[-0.05,1.05,0.0],[0.0,-0.1,1.1]];
    assert!(max_error(mv(wrong,[1.0;3]),[1.0;3])<1e-14);
    assert!(max_error(mv(wrong,[0.7,0.2,0.1]),[0.7,0.2,0.1])>0.05);
}

#[test]
fn independent_warm_colour_controls() {
    let w=wb(CAMERA,WARM_WHITE);
    let result=operator::replacement(CAMERA,w).unwrap();
    flat_first(result.matrix,w);
    let renderer=strehl_core::color::Render::new(result.matrix);
    assert!(max_error(result.source_white_xyz,WARM_WHITE)<1e-12);
    let mut transposed_error=0.0f64;let mut missing_undo_error=0.0f64;
    let wrong=operator::replacement(transpose(CAMERA),w).unwrap();
    for xyz in PATCHES {
        let input=balanced_patch(CAMERA,WARM_WHITE,xyz);
        let expected=srgb_from_xyz(adapt(xyz,WARM_WHITE));
        assert!(max_error(mv(result.matrix_f64,input),expected)<1e-11);
        assert!(max_error(mv(f64_matrix(result.matrix),input),expected)<2e-6);
        assert!(max_error(renderer.develop(input.map(|v|v as f32)).map(f64::from),expected)<2e-6);
        transposed_error=transposed_error.max(max_error(mv(wrong.matrix_f64,input),expected));
        // Omitting inverse(W) from T is exactly T*W on its already-WB input.
        let twice_wb=std::array::from_fn(|i|input[i]*w[i]);
        missing_undo_error=missing_undo_error.max(max_error(mv(result.matrix_f64,twice_wb),expected));
    }
    assert!(transposed_error>1e-3,"matrix-direction destroyer inactive");
    assert!(missing_undo_error>0.05,"WB-undo destroyer inactive");
    for scale in [0.0,0.02,0.25,0.75,1.2] {
        assert!(max_error(mv(result.matrix_f64,[scale;3]),[scale;3])<2e-6);
    }
    // Appending this CAT to an already-D65 neutral incorrectly changes grey.
    let double_adapted=srgb_from_xyz(adapt(strehl_core::color::D65_XYZ,WARM_WHITE));
    assert!(max_error(double_adapted,[1.0;3])>0.1,"appended-CAT destroyer inactive");
    // Matrix normalization scale is a gauge, not an exposure correction.
    let scaled=operator::replacement(CAMERA.map(|r|r.map(|v|2.0*v)),w).unwrap();
    assert!(matrix_error(scaled.matrix_f64,result.matrix_f64)<1e-12);
}

#[test]
fn independent_interpolation_controls() {
    let cool:Matrix=[[0.73,0.10,0.08],[0.07,0.94,0.08],[0.03,0.13,0.71]];
    // 3000 K is exactly the reciprocal-temperature midpoint of 2000/6000 K.
    let (middle,f)=operator::interpolate(CAMERA,cool,2000.0,6000.0,3000.0).unwrap();
    let expected=std::array::from_fn(|i|std::array::from_fn(|j|0.5*(CAMERA[i][j]+cool[i][j])));
    assert!((f-0.5).abs()<1e-12&&matrix_error(middle,expected)<1e-12);
    for (t,expected,fraction) in [(1000.0,CAMERA,1.0),(2000.0,CAMERA,1.0),(6000.0,cool,0.0),(9000.0,cool,0.0)] {
        let (actual,f)=operator::interpolate(CAMERA,cool,2000.0,6000.0,t).unwrap();
        assert!(matrix_error(actual,expected)<1e-12&&(f-fraction).abs()<1e-12);
    }
    for t in [0.0,-1.0,f64::NAN,f64::INFINITY] {
        assert!(operator::interpolate(CAMERA,cool,2000.0,6000.0,t).is_err());
    }
    assert!(operator::interpolate(CAMERA,cool,6000.0,2000.0,3000.0).is_err());
    assert!(operator::interpolate(CAMERA,cool,2000.0,2000.0,3000.0).is_err());
    for w in [[0.0,1.0,1.0],[-1.0,1.0,1.0],[1.0,f64::NAN,1.0]] {
        assert!(operator::replacement(CAMERA,w).is_err());
    }
    assert!(operator::replacement([[0.0;3];3],[1.0;3]).is_err());
    let mut nonfinite=CAMERA;nonfinite[0][1]=f64::INFINITY;
    assert!(operator::replacement(nonfinite,[1.0;3]).is_err());
}

fn metadata()->CameraMetadata {
    let cool=CAMERA.map(|r|r.map(|v|(v as f32).to_bits()));
    let warm=CAMERA.map(|r|r.map(|v|((v*1.03)as f32).to_bits()));
    CameraMetadata {camera:"ILCE-7CM2".into(),wb_gains_bits:wb(CAMERA,WARM_WHITE).map(|v|(v as f32).to_bits()),
        matrices:vec![NamedMatrix{name:"A".into(),bits:warm},NamedMatrix{name:"D65".into(),bits:cool}],
        selected_source:"decoder color_matrix[D65]".into(),selected_matrix_bits:cool,direct_matrix_bits:[[0;3];4]}
}

#[test]
fn independent_metadata_refusal_controls() {
    let value=operator::select(&metadata(),3000.0).unwrap();
    assert!(value.warm.name=="A"&&value.cool.name=="D65");
    assert!(value.warm_kelvin==2856.0&&value.cool_kelvin==6504.0&&value.shot_kelvin==3000.0);
    assert!(value.warm_fraction>0.0&&value.warm_fraction<1.0);
    let mut m=metadata();m.matrices.remove(0);assert!(operator::select(&m,3000.0).is_err());
    let mut m=metadata();m.matrices.push(NamedMatrix{name:"A".into(),bits:m.matrices[0].bits});
    assert!(operator::select(&m,3000.0).is_err());
    let mut m=metadata();m.selected_source="decoder xyz_to_cam".into();assert!(operator::select(&m,3000.0).is_err());
    let mut m=metadata();m.selected_matrix_bits[0][0]=0;assert!(operator::select(&m,3000.0).is_err());
    let mut m=metadata();m.direct_matrix_bits[0][0]=1.0f32.to_bits();assert!(operator::select(&m,3000.0).is_err());
    let mut m=metadata();m.camera="uncharacterized-camera".into();assert!(operator::select(&m,3000.0).is_err());
    let mut m=metadata();m.wb_gains_bits[1]=0;assert!(operator::select(&m,3000.0).is_err());
    let mut m=metadata();m.matrices[0].name="Tungsten".into();assert!(operator::select(&m,3000.0).is_err());
    let mut m=metadata();m.matrices[0].bits=[[0;3];3];assert!(operator::select(&m,3000.0).is_err());
}
