use pyo3::prelude::*;
use pyo3::types::PyTuple;

mod engine;
mod spec;

#[pyfunction]
fn backend() -> &'static str {
    "rust"
}

#[pyfunction]
fn run(
    py: Python<'_>,
    spec: &Bound<'_, PyAny>,
    controller: &Bound<'_, PyAny>,
    ctrl_queue: &Bound<'_, PyAny>,
    input_queue: &Bound<'_, PyAny>,
    max_ticks: i64,
) -> PyResult<PyObject> {
    let parsed = spec::Spec::from_python(spec)?;
    let result =
        engine::Engine::new(parsed)?.run(py, controller, ctrl_queue, input_queue, max_ticks)?;
    let verdict = result.verdict.unwrap_or_else(|| py.None());
    let items = vec![
        result.status.into_py(py),
        result.error.into_py(py),
        verdict,
        result.ticks.into_py(py),
        result.output.into_py(py),
        result.output_ticks.into_py(py),
        result.frames.into_py(py),
        result.frame_ticks.into_py(py),
        result.mcell.into_py(py),
        result.mdir.into_py(py),
        result.ma.into_py(py),
        result.mb.into_py(py),
        result.mbp.into_py(py),
        result.mhalt.into_py(py),
        result.mwait.into_py(py),
        result.p_runs.into_py(py),
        result.p_vals.into_py(py),
        result.disp_cur.into_py(py),
        result.disp_next.into_py(py),
        result.disp_cursor.into_py(py),
    ];
    Ok(PyTuple::new_bound(py, items).into_py(py))
}

#[pymodule]
fn _fastsim_rust(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(backend, module)?)?;
    module.add_function(wrap_pyfunction!(run, module)?)?;
    Ok(())
}
