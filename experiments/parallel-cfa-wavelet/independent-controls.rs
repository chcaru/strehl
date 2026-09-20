// Independent arithmetic choices; root alone executes.
use super::*;
use serde_json::{json,Value};
mod serial_reference {
    use super::super::*;
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/boundary-cfa-wavelet/transform.rs"));
    pub(super) fn whole(v:&[Complex],w:usize,h:usize,inverse:bool)->Result<Vec<Complex>> {
        transform_all(v,w,h,inverse,true)
    }
}
fn complex_bits(v:&[Complex])->Vec<[u32;2]> {v.iter().map(|z|[z.re.to_bits(),z.im.to_bits()]).collect()}
fn error(a:&[Complex],b:&[Complex])->f64 {assert_eq!(a.len(),b.len());a.iter().zip(b)
    .map(|(a,b)|(a.re as f64-b.re as f64).hypot(a.im as f64-b.im as f64)).fold(0.0,f64::max)}
fn transform_checks()->Value {
    let mut rows=Vec::new();
    let one=rayon::ThreadPoolBuilder::new().num_threads(1).build().unwrap();
    let four=rayon::ThreadPoolBuilder::new().num_threads(4).build().unwrap();
    for(w,h)in[(1usize,1usize),(2,4),(8,16),(128,64),(128,128),(4096,1),(1,4096)] {
        let values=(0..w*h).map(|i|Complex{re:((i*17%53) as f32-26.0)/17.0,
            im:((i*19%43) as f32-21.0)/29.0}).collect::<Vec<_>>();let before=complex_bits(&values);
        let expected=serial_reference::whole(&values,w,h,false).unwrap();
        let inverse=serial_reference::whole(&expected,w,h,true).unwrap();
        let peak=values.iter().map(|v|(v.re as f64).hypot(v.im as f64)).fold(1.0,f64::max);
        let roundtrip=error(&values,&inverse);assert!(roundtrip<=5e-5*peak);
        for pool in [&one,&four] {
            let actual=pool.install(||transform_all(&values,w,h,false,true)).unwrap();
            assert_eq!(complex_bits(&actual),complex_bits(&expected),"parallel forward differs at {w}x{h}");
            let back=pool.install(||transform_all(&actual,w,h,true,true)).unwrap();
            assert_eq!(complex_bits(&back),complex_bits(&inverse),"parallel inverse differs at {w}x{h}");
        }
        assert_eq!(complex_bits(&values),before);
        if w*h>1 {let mut sabotage=expected.clone();sabotage[1].re+=1.0;
            assert_ne!(complex_bits(&sabotage),complex_bits(&expected));}
        rows.push(json!({"shape":[w,h],"levels":level_rectangles_scoped(w,h,true).unwrap().len(),
            "forward_and_inverse_bits_exact_at_threads":[1,4],"roundtrip_max":roundtrip,"input_unchanged":true}));
    }
    let plan=BoundaryPlan::new(113,101).unwrap();let old=serial_reference::BoundaryPlan::new(113,101).unwrap();
    let source=(0..4).map(|c|(0..113*101).map(|i|(c as f32+1.0)*1000.0+((i*19)%257) as f32*0.125).collect::<Vec<_>>()).collect::<Vec<_>>();
    let extended=extend_four(&source,&plan).unwrap();let old_extended=serial_reference::extend_four(&source,&old).unwrap();assert_eq!(extended,old_extended);
    assert_eq!(crop_four(&extended,&plan).unwrap(),source);
    for input in &extended {let complex=input.iter().map(|&re|Complex{re,im:0.0}).collect::<Vec<_>>();
        let expected=serial_reference::whole(&complex,128,128,false).unwrap();
        for pool in [&one,&four] {let actual=pool.install(||forward_real(input,128,128)).unwrap();
            assert_eq!(complex_bits(&actual),complex_bits(&expected));}}
    json!({"serial_reference":"unchanged boundary-cfa-wavelet/transform.rs include","rectangles":rows,
        "odd113x101_reflection_and_four_planes_exact":true,"wrong_coefficient_destroyer":true})
}
fn weighted_oracle(weights:&[f32],values:&[[Complex;4]])->([[f64;2];4],[[f64;2];4],f64) {
    let den=weights.iter().map(|&w|w as f64).sum::<f64>();let mut sum=[[0.0;2];4];let mut abs=[[0.0;2];4];
    for(&w,v)in weights.iter().zip(values){for c in 0..4{for(q,x)in[v[c].re,v[c].im].into_iter().enumerate(){
        sum[c][q]+=w as f64*x as f64;abs[c][q]+=w as f64*(x as f64).abs();}}}
    for c in 0..4{for q in 0..2 {sum[c][q]/=den;abs[c][q]/=den;}}(sum,abs,den)
}
fn weighted_case(name:&str,weights:&[f32],values:&[[Complex;4]])->Value {
    let (oracle,magnitude,unscaled_den)=weighted_oracle(weights,values);
    let maximum=weights.iter().copied().fold(0.0f32,f32::max);assert!(maximum>0.0 && maximum.is_finite());
    let n=weights.len();let ascending=(0..n).collect::<Vec<_>>();let descending=(0..n).rev().collect::<Vec<_>>();
    let interleaved=(0..n).step_by(2).chain((1..n).step_by(2)).collect::<Vec<_>>();let mut rows=Vec::new();
    for(label,order)in[("forward",ascending),("reverse",descending),("even-then-odd",interleaved)]{
        let mut scale=0.0f32;let mut den=0.0f32;let mut num=[Complex::default();4];
        for i in order {scaled_add(weights[i],&values[i],&mut scale,&mut den,&mut num).unwrap();
            assert!(scale.is_finite() && den.is_finite() && num.iter().all(|z|z.re.is_finite() && z.im.is_finite()));}
        assert_eq!(scale.to_bits(),maximum.to_bits());let expected_den=unscaled_den/maximum as f64;
        assert!((den as f64-expected_den).abs()<=1e-5*expected_den.max(1.0));
        let mut max_error=0.0f64;let mut max_scaled_error=0.0f64;
        for c in 0..4 {for(q,x)in[num[c].re/den,num[c].im/den].into_iter().enumerate(){assert!(x.is_finite());
            let e=(x as f64-oracle[c][q]).abs();let unit=magnitude[c][q].max(1.0);
            assert!(e<=1e-5*unit,"{name}/{label}/{c}/{q}: {x} vs{}",oracle[c][q]);
            max_error=max_error.max(e);max_scaled_error=max_scaled_error.max(e/unit);}}
        rows.push(json!({"source_order":label,"maximum_weight":scale,"scaled_denominator":den,
            "f64_expected_scaled_denominator":expected_den,"max_component_error":max_error,"max_relative_absolute_mass_error":max_scaled_error}));
    }
    json!({"case":name,"sources":n,"f64_oracle":oracle,"orders":rows})
}
fn accumulation_checks()->Value {
    let huge=80.0f32.exp();assert!(huge.is_finite());let legacy=huge*100_000.0f32;assert!(!legacy.is_finite());
    let values=(0..3).map(|k|std::array::from_fn(|c|Complex{re:100_000.0*(c+1) as f32-(k as f32)*13000.0,
        im:-70_000.0*(c+1) as f32+1200.0*k as f32})).collect::<Vec<[Complex;4]>>();
    let high=weighted_case("finite_exp80_times_dn_overflows_legacy",&[huge,huge*0.5,huge*0.25],&values);
    let weights=(0..70).map(|k|if k%13==0{0.0}else if k>=65{huge}else{(-60.0+140.0*k as f32/69.0).exp()}).collect::<Vec<_>>();
    let values=(0..70).map(|k|std::array::from_fn(|c|Complex{
        re:(if(k+c)%2==0{1.0}else{-1.0})*(500.0+(k*191+c*719) as f32),
        im:(if(k+2*c)%3==0{-1.0}else{1.0})*(900.0+(k*131+c*431) as f32)})).collect::<Vec<[Complex;4]>>();
    let before=values.iter().flat_map(|v|complex_bits(v)).collect::<Vec<_>>();
    let stress=weighted_case("seventy_sources_zeros_ties_and_late_maxima",&weights,&values);
    assert_eq!(values.iter().flat_map(|v|complex_bits(v)).collect::<Vec<_>>(),before);
    let mut scale=0.0;let mut den=0.0;let mut sums=[Complex::default();4];
    for v in &values {scaled_add(0.0,v,&mut scale,&mut den,&mut sums).unwrap();}
    assert_eq!(scale,0.0);assert_eq!(den,0.0);assert!(sums.iter().all(|v|v.re==0.0 && v.im==0.0));
    let fallback=std::array::from_fn::<_,4,_>(|c|{let mut z=Complex::default();for v in &values {z.re+=v[c].re;z.im+=v[c].im;}
        Complex{re:z.re/70.0,im:z.im/70.0}});
    assert!(fallback.iter().any(|v|v.re!=0.0 && v.im!=0.0));
    // A broken running-max update rescales neither old numerator nor denominator.
    let simple=[[Complex{re:100.0,im:-50.0};4],[Complex{re:1000.0,im:70.0};4]];
    let (oracle,_,_)=weighted_oracle(&[1.0,1000.0],&simple);let broken=(100.0+1000.0)/2.0;
    assert!((broken-oracle[0][0]).abs()>100.0,"rescale destroyer inactive");
    let simple_control=weighted_case("rescale_destroyer",&[1.0,1000.0],&simple);
    for bad in [-1.0,f32::NAN,f32::INFINITY]{let(mut s,mut d,mut n)=(0.0,0.0,[Complex::default();4]);
        assert!(scaled_add(bad,&simple[0],&mut s,&mut d,&mut n).is_err());}
    json!({"legacy_finite_weight_product_nonfinite":true,"high_weight":high,"seventy_source_stress":stress,
        "zero_weights_leave_zero_scaled_state":true,"nonzero_mean_fallback_witness":fallback.iter().map(|z|[z.re,z.im]).collect::<Vec<_>>(),
        "mean_fallback_actual_consumer":"unchanged boundary flat/mean controls plus source audit",
        "rescale_destroyer":simple_control,"inputs_unchanged":true})
}
#[test]
fn independent_parallel_transform_and_scaled_numerator() {
    let transforms=transform_checks();let accumulator=accumulation_checks();
    eprintln!("PARALLEL_CFA_NUMERIC {}",json!({"status":"PASS","transforms":transforms,"accumulation":accumulator,
        "original_quality_admission_changed":false,"scope":"Arithmetic correctness only; no RAW or performance claim"}));
}
