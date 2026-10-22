//! Optional parser-free NNEF execution. This module is absent from default builds.
//! Call from the service factory; never prepare a graph in a UI callback.
use crate::{
    Backend, Cancellation, HEADS, INPUT_SHAPE, OutputTensor, PredictorPackage, PreparedInput,
};
use anyhow::{Result, ensure};
use tract::prelude::*;

struct TractBackend {
    forward: Box<dyn FnMut(&PreparedInput, &Cancellation) -> Result<Vec<OutputTensor>>>,
}
impl Backend for TractBackend {
    fn run(&mut self, input: &PreparedInput, cancel: &Cancellation) -> Result<Vec<OutputTensor>> {
        (self.forward)(input, cancel)
    }
}

fn fact_shape(fact: &Fact) -> Result<Vec<usize>> {
    ensure!(
        fact.datum_type()? == DatumType::F32,
        "Expected FP32 graph tensor"
    );
    (0..fact.rank()?)
        .map(|i| Ok(usize::try_from(fact.dim(i)?.to_int64()?)?))
        .collect()
}

/// Only package bytes already checked against the caller's exact allowlist enter
/// the runtime. NNEF parsing/execution is not a sandbox for an untrusted graph.
pub fn load(package: &PredictorPackage, cancel: &Cancellation) -> Result<Box<dyn Backend>> {
    cancel.check()?;
    let mut framework = tract::nnef()?;
    // Runtime operator registration, not the ONNX file parser.
    framework.enable_onnx()?;
    framework.enable_tract_extra()?;
    let model = framework.load_buffer(package.model_bytes())?;
    cancel.check()?;
    ensure!(
        model.input_count()? == 1 && fact_shape(&model.input_fact(0)?)? == INPUT_SHAPE,
        "Graph input differs from package"
    );
    ensure!(
        model.output_count()? == HEADS.len(),
        "Graph output count differs from package"
    );
    for (slot, (_, shape)) in HEADS.iter().enumerate() {
        ensure!(
            fact_shape(&model.output_fact(slot)?)? == *shape,
            "Graph output shape differs at slot {slot}"
        );
    }
    let runnable = model.into_runnable()?;
    cancel.check()?;
    Ok(Box::new(TractBackend {
        forward: Box::new(move |input, cancel| {
            cancel.check()?;
            let bytes: Vec<u8> = input
                .values()
                .iter()
                .flat_map(|v| v.to_le_bytes())
                .collect();
            let tensor = Tensor::from_bytes(DatumType::F32, &INPUT_SHAPE, &bytes)?;
            cancel.check()?;
            // No promise of mid-call interruption: the service retains this lane.
            let outputs = runnable.run([tensor])?;
            cancel.check()?;
            ensure!(
                outputs.len() == HEADS.len(),
                "Graph returned wrong output count"
            );
            let mut fields = Vec::with_capacity(HEADS.len());
            for (slot, output) in outputs.into_iter().enumerate() {
                cancel.check()?;
                ensure!(
                    output.datum_type()? == DatumType::F32 && output.shape()? == HEADS[slot].1,
                    "Graph returned wrong output layout"
                );
                fields.push(OutputTensor {
                    shape: output.shape()?.to_vec(),
                    values: output.as_slice::<f32>()?.to_vec(),
                });
            }
            Ok(fields)
        }),
    }))
}
