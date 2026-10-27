//! Snapshot-bound camera metadata reads; no panel, selection or recipe mutation.
use super::*;

impl StrehlApp {
    pub(super) fn agent_metadata_read_task(
        &self,
        frame: usize,
    ) -> anyhow::Result<Task<AgentReply>> {
        let source = self
            .stack
            .as_ref()
            .and_then(|stack| stack.frames.get(frame))
            .cloned()
            .ok_or_else(|| anyhow::anyhow!("Unknown source in the current imported bracket"))?;
        let revision = self.agent.revision;
        let epoch = self.epoch;
        let stack_id = self.active_stack;
        let output = self.output.clone();
        Ok(jobs::spawn_task(
            "strehl-agent-metadata",
            move |cancelled| {
                let metadata =
                    crate::camera_metadata::read_agent_report(source, output, &cancelled)?;
                Ok(AgentReply::success(json!({
                    "revision":revision,"stack_epoch":epoch,"stack_id":stack_id,
                    "frame":frame,"metadata":metadata,
                    "binding":"Source and workspace revision captured when the request was accepted."
                })))
            },
        ))
    }
}
