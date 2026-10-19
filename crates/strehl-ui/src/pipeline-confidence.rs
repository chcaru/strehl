//! Receipts for the optional second traversal comparing green observations
//! with the already reconstructed merge. Attempts are not accepted frames.
use super::{PipelineProgress, RenderStep, Stage, WorkState};
use std::collections::BTreeMap;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ConfidenceProgress {
    pub state: WorkState,
    pub completed: usize,
    pub compared: usize,
    pub total: usize,
    pub last_frame: Option<(usize, bool)>,
    /// Only source identities actually received; cumulative receipts never
    /// fill gaps left by a bounded or interrupted log transport.
    pub observations: BTreeMap<usize, bool>,
}

impl PipelineProgress {
    pub(super) fn confidence_event(&mut self, fields: &str) {
        let field = |name| {
            fields.split_whitespace().find_map(|part| {
                let (key, value) = part.split_once('=')?;
                (key == name).then_some(value)
            })
        };
        let number = |name| field(name).and_then(|v| v.parse::<usize>().ok());
        let (Some(total), Some(completed), Some(compared)) =
            (number("total"), number("completed"), number("compared"))
        else {
            return;
        };
        if total == 0
            || total > super::MAX_FRAME_OBSERVATIONS
            || completed > total
            || compared > completed
            || self.frames_total.is_some_and(|known| known != total)
            || self.stage > Stage::Rendering
            || matches!(
                self.render_step,
                Some(RenderStep::Develop | RenderStep::Write)
            )
        {
            return;
        }
        let (state, frame) = match (field("event"), field("state")) {
            (Some("confidence-pass"), Some("started"))
                if completed == 0 && compared == 0 && self.confidence.is_none() =>
            {
                (WorkState::Started, None)
            }
            (Some("confidence-pass"), Some("finished")) if completed == total => {
                (WorkState::Finished, None)
            }
            (Some("confidence-frame"), None) if completed > 0 => {
                let (Some(index), Some(mapped)) = (
                    number("index"),
                    match field("mapped") {
                        Some("true") => Some(true),
                        Some("false") => Some(false),
                        _ => None,
                    },
                ) else {
                    return;
                };
                if index >= total || (mapped && compared == 0) || (!mapped && compared == completed)
                {
                    return;
                }
                (WorkState::Started, Some((index, mapped)))
            }
            _ => return,
        };
        if let Some(old) = &self.confidence {
            if old.state == WorkState::Finished
                || old.total != total
                || completed < old.completed
                || compared < old.compared
                || compared - old.compared > completed - old.completed
            {
                return;
            }
            if let Some((index, mapped)) = frame
                && (completed == old.completed
                    || old.observations.contains_key(&index)
                    || mapped && compared == old.compared
                    || !mapped && compared - old.compared == completed - old.completed)
            {
                return;
            }
        }
        let progress = self.confidence.get_or_insert_with(|| ConfidenceProgress {
            state,
            completed: 0,
            compared: 0,
            total,
            last_frame: None,
            observations: BTreeMap::new(),
        });
        progress.state = state;
        progress.completed = completed;
        progress.compared = compared;
        if let Some((index, mapped)) = frame {
            progress.last_frame = Some((index, mapped));
            progress.observations.insert(index, mapped);
        }
        self.frames_total = Some(total);
        self.advance(Stage::Rendering);
    }
}

#[cfg(test)]
#[path = "pipeline-confidence-tests.rs"]
mod tests;
