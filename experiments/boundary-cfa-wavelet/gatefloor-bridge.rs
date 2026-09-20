// Test-only reuse of the actual original-u16 Gaussian probe generator.
pub(crate) fn boundary_wavelet_fill(frame:&mut Frame,index:usize)->Result<()> {
    use strehl_core::plane::QuadSource;
    fill_probe_noise(frame,frame.geometry(),32768.0,4096.0,index)
}
