// Independent operator controls; the main actual-image screen calls this first.
use super::*;
use serde_json::{json,Value};

// Independent SciPy1.17.1 f.isf/sf outputs, root's retained quantile-reference.json.
const REFERENCES:[(usize,usize,f64,f64,f64);6]=[
    (2,1,0.0001,50.69445529015648,0.0010083713269955186),
    (5,4,0.00001,95.69792676129401,0.00012237642195527792),
    (9,4,5.555555555555556e-6,111.97862357387781,7.042928636037911e-5),
    (16,7,1.7857142857142857e-6,151.068365041692,2.39395424029783e-5),
    (70,7,4.081632653061225e-7,221.6844284406637,5.7726805359195636e-6),
    (299,7,9.555661729574773e-8,321.84026754602087,1.4024582115652613e-6),
];
fn close64(a:f64,b:f64,label:&str)->Result<()>{
    ensure!(a.is_finite() && b.is_finite() && (a-b).abs()<=2e-7*b.abs(),"{label}: actual{a}, reference{b}");Ok(())
}
fn filled(sizes:&[LevelSize],value:f32)->GuideBands{
    std::array::from_fn(|_|sizes[..sizes.len()-1].iter().map(|s|vec![value;s.pixels()]).collect())
}
fn compare_variance(a:&GuideBands,b:&GuideBands)->Result<f32>{
    let mut worst=0.0f32;
    for c in 0..3{ensure!(a[c].len()==b[c].len(),"variance band shape");for k in 0..a[c].len(){
        ensure!(a[c][k].len()==b[c][k].len(),"variance coefficient shape");
        for (&x,&y) in a[c][k].iter().zip(&b[c][k]){let e=(x-y).abs();worst=worst.max(e);
            ensure!(x.is_finite() && y.is_finite() && e<=1e-5+2e-5*x.abs().max(y.abs()),"raw coefficient variance differs: {x} vs{y}");
        }
    }}Ok(worst)
}
fn raw_pair_control(sizes:&[LevelSize])->Result<Value>{
    let mut accumulator=NoiseEnergy::new(sizes);let mut expected=filled(sizes,0.0);
    for pair in 0..8{
        let mut a=filled(sizes,0.0);let mut b=filled(sizes,0.0);
        for c in 0..3{for k in 0..sizes.len()-1{
            let n=sizes[k].pixels();let first=(3*c+7*k)%n;let second=(first+5)%n;
            a[c][k][first]=((pair+1)*(c+2)) as f32;
            b[c][k][first]=((pair+3)*(c+1)) as f32*0.25;
            b[c][k][second]=((pair+2)*(c+1)) as f32*0.5;
            for j in 0..n{let d=a[c][k][j]-b[c][k][j];expected[c][k][j]+=d*d;}
        }}accumulator.add_pair(&a,&b)?;
    }
    for guide in &mut expected{for band in guide{for value in band{*value/=16.0;}}}
    let actual=accumulator.finish()?;
    let raw_error=compare_variance(&actual.coefficient_variance3,&expected)?;
    let smoothed:GuideBands=std::array::from_fn(|c|(0..sizes.len()-1).map(|k|kernels::smooth(&expected[c][k],sizes[k])).collect());
    let smooth_error=compare_variance(&actual.energy3,&smoothed)?;
    ensure!(actual.coefficient_variance3[0][0].iter().zip(&actual.energy3[0][0]).any(|(a,b)|(a-b).abs()>1.0),"smoothed-before-test destroyer not exercised");
    let doubled:GuideBands=std::array::from_fn(|c|expected[c].iter().map(|p|p.iter().map(|v|2.0*v).collect()).collect());
    ensure!(compare_variance(&actual.coefficient_variance3,&doubled).is_err(),"wrong divisor eight escaped variance witness");
    let a=filled(sizes,1.0);let b=filled(sizes,0.0);let mut short=NoiseEnergy::new(sizes);
    for _ in 0..7{short.add_pair(&a,&b)?;}ensure!(short.finish().is_err(),"seven-pair estimate accepted");
    let mut extra=NoiseEnergy::new(sizes);for _ in 0..8{extra.add_pair(&a,&b)?;}
    ensure!(extra.add_pair(&a,&b).is_err(),"ninth noise pair accepted");
    Ok(json!({"raw_max_abs_error":raw_error,"smoothed_max_abs_error":smooth_error,
        "unsmoothed_impulse_live":true,"wrong_pair_factor_rejected":true,"pair_count_refusals":true}))
}
#[derive(Clone,Copy)]
struct Trigger{source:usize,colour:usize,band:usize,x:usize,y:usize}
fn literal_mask(sizes:&[LevelSize],triggers:&[Trigger])->[Vec<Vec<f32>>;2]{
    std::array::from_fn(|c|(0..sizes.len()-1).map(|k|{
        let s=sizes[k];let mut mask=vec![0.0;s.pixels()];
        for y in 0..s.height{for x in 0..s.width{
            let mut active=false;
            for dy in -2isize..=2{for dx in -2isize..=2{
                let sx=(x as isize+dx).clamp(0,s.width as isize-1) as usize;
                let sy=(y as isize+dy).clamp(0,s.height as isize-1) as usize;
                active|=triggers.iter().any(|t|t.colour==c && t.band==k && t.x==sx && t.y==sy);
            }}mask[y*s.width+x]=if active{1.0}else{0.0};
        }}mask
    }).collect())
}
fn activated(sizes:&[LevelSize],n:usize,triggers:&[Trigger],signal_ratio:f64,variance:f32,green_only:bool)->Result<[Vec<Vec<f32>>;2]>{
    let q=threshold(n,sizes.len()-1)?;let amplitude=(signal_ratio*q).sqrt() as f32;
    let mut activation=Activation::new(sizes,n,q)?;
    for source in 0..n{
        let mut signal=filled(sizes,0.0);let noise=filled(sizes,variance);
        if green_only{for band in &mut signal[1]{band.fill(1000.0);}}
        else{for t in triggers.iter().filter(|t|t.source==source){
            signal[if t.colour==0{0}else{2}][t.band][t.y*sizes[t.band].width+t.x]=amplitude;
        }}activation.add_source(&signal,&noise)?;
    }activation.finish()
}
fn mask_equal(a:&[Vec<Vec<f32>>;2],b:&[Vec<Vec<f32>>;2])->bool{
    a.iter().zip(b).all(|(a,b)|a.len()==b.len() && a.iter().zip(b).all(|(a,b)|
        a.len()==b.len() && a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits())))
}

pub(super) fn check_residual_guard()->Result<Value>{
    let mut references=Vec::new();
    for (n,nb,p,q,half_sf) in REFERENCES{
        let got=f1_8_quantile_tail(p)?;let bound=threshold(n,nb)?;
        close64(got,q,"independent inverse-tail reference")?;close64(bound,q,"count/band local threshold")?;
        close64(f1_8_tail(q)?,p,"independent survival reference")?;
        close64(f1_8_tail(q/2.0)?,half_sf,"independent half-threshold survival")?;
        ensure!(f1_8_tail(q/2.0)?>5.0*p,"half-threshold destroyer not decisive");
        let image_q=threshold_f32(n,nb)?;
        ensure!(image_q.is_finite() && image_q>0.0 && (image_q as f64)>=bound
            && (f32::from_bits(image_q.to_bits()-1) as f64)<bound,
            "f32 image threshold is not the least value at or above scalar q");
        references.push(json!({"sources":n,"bands":nb,"tail":p,"reference_q":q,"actual_q":got,"bound_q":bound,
            "upward_f32_q":image_q,"upward_f32_bits":image_q.to_bits()}));
    }
    close64(f1_8_tail(0.0)?,1.0,"F survival at zero")?;
    ensure!(f1_8_tail(f64::INFINITY)?==0.0 && f1_8_quantile_tail(1.0)?==0.0,"valid scalar distribution endpoints differ");
    for p in [0.0,-0.1,1.1,f64::NAN,f64::INFINITY]{ensure!(f1_8_quantile_tail(p).is_err(),"invalid tail probability accepted");}
    for t in [-1.0,f64::NAN]{ensure!(f1_8_tail(t).is_err(),"invalid F statistic accepted");}
    ensure!(threshold(0,3).is_err() && threshold(3,0).is_err(),"empty multiplicity accepted");
    let sizes=level_sizes(89,73,7);ensure!(sizes.len()==4,"odd-domain three AC bands required");
    let raw=raw_pair_control(&sizes)?;let n=3;let q=threshold(n,sizes.len()-1)?;
    let triggers=[Trigger{source:0,colour:0,band:0,x:17,y:19},Trigger{source:1,colour:0,band:0,x:23,y:17},
        Trigger{source:1,colour:1,band:0,x:0,y:0},Trigger{source:2,colour:0,band:1,x:6,y:9},
        Trigger{source:2,colour:1,band:2,x:sizes[2].width-1,y:sizes[2].height-1}];
    let actual=activated(&sizes,n,&triggers,2.0,1.0,false)?;let expected=literal_mask(&sizes,&triggers);
    ensure!(mask_equal(&actual,&expected),"activation differs from literal existing 5x5 OR support");
    let counts=actual.iter().map(|c|c.iter().map(|p|p.iter().filter(|v|**v==1.0).count()).collect::<Vec<_>>()).collect::<Vec<_>>();
    ensure!(counts==vec![vec![50,25,0],vec![9,0,9]],"interior/edge/channel/band witnesses not exercised");
    let zero=literal_mask(&sizes,&[]);
    ensure!(mask_equal(&activated(&sizes,n,&triggers,0.5,1.0,false)?,&zero),"subthreshold input activated");
    ensure!(mask_equal(&activated(&sizes,n,&triggers,2.0,1.0,true)?,&zero),"green-only evidence activated R/B");
    let one=&triggers[..1];
    ensure!(!mask_equal(&activated(&sizes,n,one,1.5,1.0,false)?,&zero)
        && mask_equal(&activated(&sizes,n,one,1.5,2.0,false)?,&zero),"doubling variance did not suppress chosen exceedance");
    ensure!(Activation::new(&sizes,n,q*2.0).is_err(),"unbound threshold accepted");
    let signal=filled(&sizes,0.0);let noise=filled(&sizes,1.0);
    for v in [-1.0,f32::INFINITY,f32::NAN]{
        let mut invalid=noise.clone();invalid[0][0][0]=v;
        ensure!(Activation::new(&sizes,n,q)?.add_source(&signal,&invalid).is_err(),"invalid red variance accepted");
        let mut invalid=noise.clone();invalid[2][1][2]=v;
        ensure!(Activation::new(&sizes,n,q)?.add_source(&signal,&invalid).is_err(),"invalid blue variance accepted");
    }
    let mut bad=signal.clone();bad[2][0][0]=f32::INFINITY;
    ensure!(Activation::new(&sizes,n,q)?.add_source(&bad,&noise).is_err(),"nonfinite signal accepted");
    let mut overflow=signal.clone();overflow[0][0][0]=f32::MAX;
    ensure!(Activation::new(&sizes,n,q)?.add_source(&overflow,&noise).is_err(),"finite signal squared overflow accepted");
    let mut overflow=noise.clone();overflow[2][0][0]=f32::MAX;
    ensure!(Activation::new(&sizes,n,q)?.add_source(&signal,&overflow).is_err(),"finite threshold-times-variance overflow accepted");
    for value in [0.0,1000.0]{
        let mut zero_noise=noise.clone();let mut zero_signal=signal.clone();
        zero_noise[0][0][0]=0.0;zero_noise[2][1][2]=0.0;
        zero_signal[0][0][0]=value;zero_signal[2][1][2]=value;
        let mut abstain=Activation::new(&sizes,n,q)?;
        for _ in 0..n{abstain.add_source(&zero_signal,&zero_noise)?;}
        ensure!(mask_equal(&abstain.finish()?,&zero),"zero variance manufactured activation");
    }
    let mut short=Activation::new(&sizes,n,q)?;for _ in 0..n-1{short.add_source(&signal,&noise)?;}
    ensure!(short.finish().is_err(),"incomplete activation sources accepted");
    let mut extra=Activation::new(&sizes,n,q)?;for _ in 0..n{extra.add_source(&signal,&noise)?;}
    ensure!(extra.add_source(&signal,&noise).is_err(),"extra activation source accepted");
    let mut changed=0;
    for (parent,own) in [(-0.0f32,71.5f32),(0.0,-17.25),(2048.125,4096.25),(-8192.5,-2048.125)]{
        let off=strehl_core::pyramid::rb_residual_guard_diagnostic::mix_scalar(parent,own,0.0);
        let on=strehl_core::pyramid::rb_residual_guard_diagnostic::mix_scalar(parent,own,1.0);
        ensure!(off.to_bits()==parent.to_bits(),"zero mask changed literal parent bits");
        ensure!(on.to_bits()==own.to_bits(),"unit-mask dyadic witness differs from own coefficient");
        changed+=usize::from(on.to_bits()!=off.to_bits());
    }
    ensure!(changed==4,"parent-zero mixing witness is not live");
    Ok(json!({"status":"PASS","references":references,"raw_variance":raw,"activation_ones_by_colour_band":counts,
        "literal_clamped_support_bit_exact":true,"subthreshold_zero_exact":true,"green_only_zero_exact":true,
        "doubled_variance_turns_exceedance_off":true,"zero_variance_abstains_for_zero_and_nonzero_signal":true,
        "invalid_variance_signal_source_counts_refused":true,"parent_zero_mask_exact_including_negative_zero":true,
        "scope":"conditional F1,8 arithmetic and local coefficient-support OR only; no native-pixel/full-image family-wise or camera-calibration claim"}))
}
