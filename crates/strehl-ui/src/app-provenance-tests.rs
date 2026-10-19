//! Domain invalidation must reach the app-owned texture cache, not merely the
//! parser ring. A same-size crop at another origin is a different photograph.
use super::*;

#[test]
fn a_changed_crop_origin_discards_cached_packets_and_textures_before_reimporting_surfaces() {
    let ctx = egui::Context::default();
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.progress.ingest(concat!(
        "planes: 901 x 601\n",
        "analysis domain : 131 x 99 at full-plane origin (17, 29)\n",
        "STREHL_UI_PROGRESS event=diagnostic seq=50 frame=2 level=0 kind=gate-support scope=frame scale=linear width=2 height=1 min=0 max=1 folded=1 total=67 sampling=nearest data=00ff\n",
        "STREHL_UI_PROGRESS event=diagnostic seq=51 frame=2 level=0 kind=coefficient scope=stack scale=symmetric width=2 height=1 min=-10 max=10 folded=3 total=67 sampling=nearest data=00ff\n",
        "STREHL_UI_PROGRESS event=diagnostic seq=52 frame=2 level=3 kind=preview scope=stack scale=linear width=2 height=1 min=10 max=20 folded=3 total=67 sampling=nearest data=00ff\n"
    ));
    app.cache_process_surfaces(&ctx);
    assert_eq!(
        app.process_surfaces.len(),
        3,
        "the cache must contain old-domain evidence"
    );
    let old_ids = app
        .process_surfaces
        .iter()
        .map(|surface| surface.texture.id())
        .collect::<Vec<_>>();
    let old_domain = app.process_domain_epoch;
    let job_epoch = app.epoch;
    app.progress
        .ingest("analysis domain : 131 x 99 at full-plane origin (18, 29)\n");
    assert_eq!(app.progress.analysis_size, Some([131, 99]));
    assert_eq!(app.progress.analysis_origin, Some([18, 29]));
    assert_ne!(app.progress.diagnostic_epoch, old_domain);
    assert!(app.progress.diagnostic_surfaces.is_empty());
    assert_eq!(app.progress.admission_archive.len(), 0);
    app.cache_process_surfaces(&ctx);
    assert!(
        app.process_surfaces.is_empty(),
        "old textures must not re-enter Theater.receive with the same job epoch"
    );
    assert_eq!(
        app.epoch, job_epoch,
        "the fixture must exercise a same-job domain change"
    );
    app.progress.ingest("STREHL_UI_PROGRESS event=diagnostic seq=53 frame=4 level=0 kind=gate-support scope=frame scale=linear width=2 height=1 min=0 max=1 folded=1 total=67 sampling=nearest data=ff00\n");
    app.cache_process_surfaces(&ctx);
    assert_eq!(
        app.process_surfaces.len(),
        1,
        "only observed new-domain kinds return"
    );
    let surface = &app.process_surfaces[0];
    assert_eq!(surface.sequence, 53);
    assert_eq!(surface.frame, Some(4));
    assert_eq!(&*surface.packet.pixels, &[255, 0]);
    assert!(!old_ids.contains(&surface.texture.id()));
    assert_eq!(
        app.progress.admission_archive.sample(0, 4, [0.0, 0.0]),
        Some(true)
    );
    assert_eq!(
        app.progress.admission_archive.sample(0, 2, [0.0, 0.0]),
        None
    );
}
