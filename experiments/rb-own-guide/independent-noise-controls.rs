// Independent arithmetic/routing control; called before the sole image screen.
use super::*;
use serde_json::{json,Value};
use strehl_core::pyramid::{Pyramid as LiteralPyramid,Workspace as LiteralWorkspace};

fn literal_laplacian(values:&[f32],sizes:&[LevelSize])->Vec<Vec<f32>>{
    let mut p=LiteralPyramid::zeros(sizes);
    p.build(values,&mut LiteralWorkspace::new(sizes));
    (0..sizes.len()-1).map(|k|p.level(k).to_vec()).collect()
}
fn literal_guides(known:&[Vec<f32>],sizes:&[LevelSize])->GuideBands{
    let mut green=vec![0.0;known[0].len()];
    for i in 0..green.len(){green[i]=(known[1][i]+known[2][i])*0.5;}
    [literal_laplacian(&known[0],sizes),literal_laplacian(&green,sizes),literal_laplacian(&known[3],sizes)]
}
fn same(a:&GuideBands,b:&GuideBands)->bool{
    a.iter().zip(b).all(|(a,b)|a.len()==b.len() && a.iter().zip(b).all(|(a,b)|
        a.len()==b.len() && a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits())))
}
fn assert_close(actual:&GuideBands,expected:&GuideBands,label:&str)->Result<f32>{
    let mut maximum=0.0f32;
    for c in 0..3{ensure!(actual[c].len()==expected[c].len(),"{label}: band count");
        for k in 0..actual[c].len(){ensure!(actual[c][k].len()==expected[c][k].len(),"{label}: band shape");
            for (&a,&e) in actual[c][k].iter().zip(&expected[c][k]){
                let error=(a-e).abs();maximum=maximum.max(error);
                ensure!(a.is_finite() && e.is_finite() && error<=1e-5+2e-5*a.abs().max(e.abs()),
                    "{label}: guide{c}/band{k}: actual{a}, expected{e}");
            }
        }
    }Ok(maximum)
}
fn operands(width:usize,height:usize,draw:usize,scale:i32,positive_green:bool)->Vec<Vec<f32>>{
    let mut p=vec![vec![0.0;width*height];4];
    for y in 0..height{for x in 0..width{
        let r=((7*x+11*y+5*draw+(x*y+3*draw)%13)%23) as i32-11;
        let g=((3*x+5*y+7*draw+(x+draw)*(y+2)%17)%29) as i32-14;
        let b=((17*x+2*y+3*draw+(x+2)*(y+draw)%11)%19) as i32-9;
        let i=y*width+x;
        p[0][i]=(128+scale*r) as f32;p[1][i]=(192+2*scale*g) as f32;
        p[2][i]=(192+if positive_green{2*scale*g}else{-2*scale*g}) as f32;
        p[3][i]=(256+3*scale*b) as f32;
    }}p
}
struct Case{actual:GuideBands,oracle:GuideBands,no_covariance_green:Vec<Vec<f32>>,error:f32}
fn case(sizes:&[LevelSize],scale:i32,positive_green:bool)->Result<Case>{
    let mut actual=NoiseEnergy::new(sizes);
    let mut sums:GuideBands=std::array::from_fn(|_|sizes[..sizes.len()-1].iter().map(|s|vec![0.0;s.pixels()]).collect());
    let mut no_cov=sizes[..sizes.len()-1].iter().map(|s|vec![0.0;s.pixels()]).collect::<Vec<_>>();
    for pair in 0..8{
        let a=operands(sizes[0].width,sizes[0].height,2*pair,scale,positive_green);
        let b=operands(sizes[0].width,sizes[0].height,2*pair+1,scale,positive_green);
        let ga=guide_laplacians(&a,sizes)?;let gb=guide_laplacians(&b,sizes)?;
        let la=literal_guides(&a,sizes);let lb=literal_guides(&b,sizes);
        ensure!(same(&ga,&la) && same(&gb,&lb),"actual R/meanG/B routing or Laplacian differs from independent production-Pyramid route");
        actual.add_pair(&ga,&gb)?;
        for c in 0..3{for k in 0..sizes.len()-1{for i in 0..sums[c][k].len(){
            let d=la[c][k][i]-lb[c][k][i];sums[c][k][i]+=d*d;
        }}}
        // Intentionally wrong: Var((G1+G2)/2) with their covariance deleted.
        for plane in [1,2]{
            let a=literal_laplacian(&a[plane],sizes);let b=literal_laplacian(&b[plane],sizes);
            for k in 0..sizes.len()-1{for i in 0..no_cov[k].len(){let d=a[k][i]-b[k][i];no_cov[k][i]+=d*d;}}
        }
    }
    for c in 0..3{for k in 0..sizes.len()-1{
        for v in &mut sums[c][k]{*v/=16.0;}
        sums[c][k]=kernels::smooth(&sums[c][k],sizes[k]);
    }}
    for k in 0..sizes.len()-1{
        for v in &mut no_cov[k]{*v/=64.0;}
        no_cov[k]=kernels::smooth(&no_cov[k],sizes[k]);
    }
    let actual=actual.finish()?;let error=assert_close(&actual,&sums,"eight-pair literal floor")?;
    Ok(Case{actual,oracle:sums,no_covariance_green:no_cov,error})
}
fn scaled(a:&GuideBands,factor:f32)->GuideBands{
    std::array::from_fn(|c|a[c].iter().map(|p|p.iter().map(|v|v*factor).collect()).collect())
}

pub(super) fn check_noise_floor()->Result<Value>{
    let sizes=level_sizes(89,73,7);
    ensure!(sizes.len()==4,"fixed odd-domain operator must reach three AC bands");
    let anti=case(&sizes,1,false)?;let positive=case(&sizes,1,true)?;let doubled=case(&sizes,2,true)?;
    for k in 0..sizes.len()-1{
        ensure!(anti.actual[0][k].iter().any(|v|*v>0.1) && anti.actual[2][k].iter().any(|v|*v>0.1),"R/B band{k} floor fixture unexercised");
        ensure!(anti.actual[1][k].iter().all(|v|*v==0.0),"anti-correlated greens did not cancel exactly before Laplacian");
        ensure!(anti.no_covariance_green[k].iter().any(|v|*v>0.1),"missing-green-covariance destroyer not live at band{k}");
        ensure!(positive.actual[1][k].iter().any(|v|*v>0.1),"positive green covariance fixture not live at band{k}");
    }
    ensure!(anti.actual[0].iter().flatten().zip(anti.actual[2].iter().flatten()).any(|(r,b)|(r-b).abs()>1.0),"R/B route distinction unexercised");
    let scale_error=assert_close(&doubled.actual,&scaled(&positive.actual,4.0),"double residual amplitude gives fourfold energy")?;
    let wrong_factor=scaled(&positive.oracle,2.0);
    ensure!(assert_close(&positive.actual,&wrong_factor,"wrong divisor eight / repeated beta two").is_err(),"factor-two destroyer escaped literal witness");
    ensure!(assert_close(&doubled.actual,&scaled(&positive.actual,2.0),"wrong linear noise-amplitude scaling").is_err(),"doubled-noise destroyer escaped");
    let a=guide_laplacians(&operands(89,73,0,1,true),&sizes)?;
    let b=guide_laplacians(&operands(89,73,1,1,true),&sizes)?;
    let mut seven=NoiseEnergy::new(&sizes);for _ in 0..7{seven.add_pair(&a,&b)?;}
    ensure!(seven.finish().is_err(),"seven-pair floor accepted");
    let mut nine=NoiseEnergy::new(&sizes);for _ in 0..8{nine.add_pair(&a,&b)?;}
    ensure!(nine.add_pair(&a,&b).is_err(),"ninth pair accepted");
    let mut bad_shape=a.clone();bad_shape[2][1].pop();
    ensure!(NoiseEnergy::new(&sizes).add_pair(&bad_shape,&b).is_err(),"malformed band accepted");
    let mut bad=a.clone();bad[0][0][0]=f32::NAN;
    ensure!(NoiseEnergy::new(&sizes).add_pair(&bad,&b).is_err(),"nonfinite coefficient accepted");
    let mut bad_known=operands(89,73,0,1,true);bad_known[3][6]=f32::INFINITY;
    ensure!(guide_laplacians(&bad_known,&sizes).is_err(),"nonfinite input guide accepted");
    let means=|a:&GuideBands|a.iter().map(|g|g.iter().map(|p|p.iter().map(|v|*v as f64).sum::<f64>()/p.len() as f64).collect::<Vec<_>>()).collect::<Vec<_>>();
    Ok(json!({"status":"PASS","domain_quad":[89,73],"level_sizes":sizes.iter().map(|s|[s.width,s.height]).collect::<Vec<_>>(),
        "pairs":8,"divisor":16,"returned_energy_has_gate":false,"routing_bit_exact":true,
        "literal_max_abs_error":[anti.error,positive.error,doubled.error],"amplitude_scale_max_abs_error":scale_error,
        "anti_correlated_guide_band_means":means(&anti.actual),"positive_correlated_guide_band_means":means(&positive.actual),
        "wrong_covariance_green_band_means":anti.no_covariance_green.iter().map(|p|p.iter().map(|v|*v as f64).sum::<f64>()/p.len() as f64).collect::<Vec<_>>(),
        "destroyers_rejected":["missing green covariance","divisor8 or repeated factor-two beta","linear energy scaling for doubled residual amplitude"],
        "invalid_inputs_refused":["seven pairs","ninth pair","malformed band","nonfinite coefficient","nonfinite guide"],
        "scope":"operator routing and arithmetic only; deterministic operands do not test random independence or camera calibration"}))
}
