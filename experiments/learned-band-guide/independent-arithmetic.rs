// Independent fixed-input scorer and forward-fixture commissioning; no RAW/probe replay.
use super::Model as ArithmeticModel;
use strehl_core::pyramid::LevelSize as ArithmeticSize;

fn arithmetic_max_error(a:&[f32],b:&[f32])->f64{
    assert_eq!(a.len(),b.len());assert!(a.iter().chain(b).all(|v|v.is_finite()));
    a.iter().zip(b).map(|(&a,&b)|(f64::from(a)-f64::from(b)).abs()).fold(0.0,f64::max)
}
fn arithmetic_features(n:usize,s:ArithmeticSize)->Vec<f32>{
    let p=s.pixels();let mut out=vec![0.0;n*10*p];
    for source in 0..n{for f in 0..5{for y in 0..s.height{for x in 0..s.width{
        out[(source*10+f)*p+y*s.width+x]=(13*source+7*f+3*y+x)as f32/64.0;
        // For n=4, the exact arithmetic mean is dyadic and independent of order.
        out[(source*10+f+5)*p+y*s.width+x]=(13.0*(n-1)as f32/2.0+(7*f+3*y+x)as f32)/64.0;
    }}}}out
}
fn arithmetic_oracle(features:&[f32],n:usize,s:ArithmeticSize,wrap:bool)->Vec<f32>{
    // Literal selected channel/tap, independently expanded from the fixed test model.
    let p=s.pixels();let mut scores=vec![0.0f64;n*p];
    for source in 0..n{for y in 0..s.height{for x in 0..s.width{
        let yy=if wrap{(y+s.height-1)%s.height}else{y.saturating_sub(1)};
        let xx=if wrap{(x+1)%s.width}else{(x+1).min(s.width-1)};
        let v=f64::from(features[(source*10+2)*p+yy*s.width+xx]);
        scores[source*p+y*s.width+x]=0.25+0.75*(0.125+0.5*v).tanh();
    }}}
    let mut weights=vec![0.0;n*p];for j in 0..p{
        let maximum=(0..n).map(|source|scores[source*p+j]).fold(f64::NEG_INFINITY,f64::max);
        for source in 0..n{weights[source*p+j]=(scores[source*p+j]-maximum).exp()as f32;}
    }weights
}

#[test]
fn independent_arithmetic_controls(){
    let size=ArithmeticSize{width:5,height:4};let n=4;let p=size.pixels();
    let features=arithmetic_features(n,size);let zero=ArithmeticModel::zero();zero.validate().unwrap();
    let unit=zero.weights(&features,n,size).unwrap();assert!(unit.iter().all(|&v|v==1.0));
    let mut bad=zero.clone();bad.conv1.pop();assert!(bad.validate().is_err());
    let mut bad=zero.clone();bad.schema=2;assert!(bad.validate().is_err());
    let mut bad=zero.clone();bad.bias1[3]=f32::NAN;assert!(bad.validate().is_err());
    let mut bad=zero.clone();bad.conv2[0]=f32::INFINITY;assert!(bad.validate().is_err());
    assert!(zero.weights(&features,1,size).is_err());assert!(zero.weights(&features,18,size).is_err());
    assert!(zero.weights(&features[..features.len()-1],n,size).is_err());
    let mut nonfinite=features.clone();nonfinite[p+1]=f32::NAN;assert!(zero.weights(&nonfinite,n,size).is_err());

    let mut model=zero.clone();
    // h0, input channel2, ky0/kx2: upper-right replicated-border sample.
    model.conv1[20]=0.5;model.bias1[0]=0.125;model.conv2[0]=0.75;model.bias2[0]=0.25;
    let weights=model.weights(&features,n,size).unwrap();let expected=arithmetic_oracle(&features,n,size,false);
    let oracle_error=arithmetic_max_error(&weights,&expected);assert!(oracle_error<2e-6);
    assert!(weights.iter().any(|&w|w<0.95),"nonzero model failed to exercise source preference");
    let wrong_border=arithmetic_oracle(&features,n,size,true);
    let border_destroyer_error=arithmetic_max_error(&weights,&wrong_border);
    assert!(border_destroyer_error>1e-4,"wrapped-border destroyer is inert");

    // Permute already constructed feature blocks, including their fixed set means.
    // Do not regenerate RAW/noise/probe seeds and mistake that for set algebra.
    let permutation=[2usize,0,3,1];let block=10*p;
    let reordered=permutation.iter().flat_map(|&i|features[i*block..(i+1)*block].iter().copied()).collect::<Vec<_>>();
    let permuted=model.weights(&reordered,n,size).unwrap();
    for (new,&old)in permutation.iter().enumerate(){assert_eq!(&permuted[new*p..(new+1)*p],&weights[old*p..(old+1)*p]);}
    let duplicated=features.iter().chain(&features).copied().collect::<Vec<_>>();
    let duplicate_weights=model.weights(&duplicated,2*n,size).unwrap();
    assert_eq!(&duplicate_weights[..n*p],weights.as_slice());assert_eq!(&duplicate_weights[n*p..],weights.as_slice());
    let mut duplication_average_error=0.0f64;
    for j in 0..p{
        let average=|count:usize,w:&[f32]|{let(mut num,mut den)=(0.0f64,0.0f64);for i in 0..count{
            let weight=f64::from(w[i*p+j]);num+=weight*((i%n)as f64-0.125*j as f64);den+=weight;
        }num/den};
        duplication_average_error=duplication_average_error.max((average(n,&weights)-average(2*n,&duplicate_weights)).abs());
    }
    assert!(duplication_average_error<1e-12);

    // A varying alpha with identical near/far radiance must still preserve DC.
    let all=cases();let curved=all.iter().find(|c|!c.training&&c.family==Family::Curved).unwrap();
    let mut constant=latent(curved);
    for j in 0..W*H{for c in 0..3{constant.near[3*j+c]=0.25*constant.alpha[j];constant.far[3*j+c]=0.25;}}
    let selections=[
        all.iter().find(|c|c.training&&c.family==Family::Straight).unwrap(),
        curved,
        all.iter().find(|c|!c.training&&c.family==Family::Glint).unwrap(),
    ];let mut pupil_records=Vec::new();
    for case in selections{let points=pupil(case);assert_eq!(points.len(),64);
        for pair in points.chunks_exact(2){assert_eq!(pair[0][0],-pair[1][0]);assert_eq!(pair[0][1],-pair[1][1]);}
        let image=render(&constant,&points,0.5,false);assert!(image.iter().all(|v|v.is_finite()));
        let error=image.iter().map(|&v|(f64::from(v)-0.25).abs()).fold(0.0,f64::max);
        assert!(error<2e-6,"constant radiance changed by pupil/visibility renderer");
        pupil_records.push(json!({"pupil":pupil_name(case),"samples":64,"constant_maximum_error":error}));
    }
    let scene=latent(curved);let points=pupil(curved);
    let actual=cut(&render(&scene,&points,0.5,false));let wrong=cut(&render(&scene,&points,0.5,true));
    let visibility_max=arithmetic_max_error(&actual,&wrong);
    let visibility_rms=(actual.iter().zip(&wrong).map(|(&a,&b)|(f64::from(a)-f64::from(b)).powi(2)).sum::<f64>()/actual.len()as f64).sqrt();
    assert!(visibility_max>1e-4&&visibility_rms>1e-6,"average-visibility destroyer is inert");
    // Inspect original active u16 samples on a literal flat, before any gather.
    // Shared injected constants commission sampling/order, not sensor calibration.
    let flat_case=all.iter().find(|c|!c.training&&c.family==Family::Flat&&c.n==5).unwrap();
    let flat=generate(flat_case);let noise=profile::noise_model_for("ILCE-7CM2",Some(flat_case.iso),levels());
    assert_ne!(hash16(&flat.frames[0].data),hash16(&flat.frames[1].data),"distinct source noise draws are identical");
    let phases=[CfaPlane::R,CfaPlane::G1,CfaPlane::G2,CfaPlane::B];let mut raw_noise=Vec::new();
    for (frame_index,frame)in flat.frames.iter().take(2).enumerate(){
        let mut outside=0usize;
        for y in 0..frame.buffer_height{for x in 0..frame.stride{
            if x<frame.active.x||x>=frame.active.x+W||y<frame.active.y||y>=frame.active.y+H{
                assert_eq!(frame.data[y*frame.stride+x],64999);outside+=1;
            }
        }}assert!(outside>0);
        for phase in 0..4{
            let c=if phase==0{0}else if phase==3{2}else{1};
            let signal=0.25*levels().range()/WB[c];let expected=f64::from(noise.sigma(phases[phase],signal)).powi(2);
            let(mut count,mut sum,mut square)=(0usize,0.0f64,0.0f64);
            for y in (phase/2..H).step_by(2){for x in (phase%2..W).step_by(2){
                let value=frame.active_row(y)[x];assert!(value>512&&value<15360);
                let residual=f64::from(value)-512.0-f64::from(signal);count+=1;sum+=residual;square+=residual*residual;
            }}
            let variance=(square-sum*sum/count as f64)/(count-1)as f64;
            let ratio=variance/expected;assert!((ratio-1.0).abs()<=0.10,"original flat variance/order mismatch");
            raw_noise.push(json!({"frame":frame_index,"phase":phase,"active_samples":count,
                "excluded_sentinel_samples":outside,"residual_mean_dn":sum/count as f64,
                "centered_residual_variance":variance,"injected_variance":expected,"variance_ratio":ratio}));
        }
    }
    let out=output();std::fs::create_dir_all(&out).unwrap();
    write(&out.join("arithmetic.json"),&json!({"status":"ARITHMETIC_COMPLETE","mechanical_pass":true,
        "model_shape_nonfinite_refusals":true,"zero_uniform_exact":true,"nonzero_model_oracle_maximum_error":oracle_error,
        "replicate_border_destroyer_error":border_destroyer_error,"fixed_features_permutation_exact":true,
        "whole_set_duplicate_weights_exact":true,"duplicated_normalized_average_error":duplication_average_error,
        "pupil_constant_controls":pupil_records,"wrong_visibility_maximum_difference":visibility_max,
        "wrong_visibility_rms_difference":visibility_rms,"original_flat_noise":raw_noise,
        "original_flat_source_draws_distinct":true,"noise_calibration_validation":false,"photographic_quality_admitted":false,
        "scope":"Fixed synthetic export-layout feature tensors, not RAW/probe permutation. Renderer equations commissioned, not optical calibration. No reconstructed-image duplication claim."}));
    eprintln!("LEARNED_BAND_GUIDE_ARITHMETIC_COMPLETE");
}
