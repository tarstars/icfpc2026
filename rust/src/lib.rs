use pyo3::prelude::*;
use pyo3::types::{PyDict, PyTuple};

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

#[pyfunction]
fn run_official(
    py: Python<'_>,
    spec: &Bound<'_, PyAny>,
    controller: &Bound<'_, PyAny>,
    ctrl_queue: &Bound<'_, PyAny>,
    input_queue: &Bound<'_, PyAny>,
    max_ticks: i64,
) -> PyResult<PyObject> {
    let parsed = spec::Spec::from_python(spec)?;
    if parsed.semantics_version != 2 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "run_official requires semantics_version=2",
        ));
    }
    let result =
        engine::Engine::new(parsed)?.run(py, controller, ctrl_queue, input_queue, max_ticks)?;
    let out = PyDict::new_bound(py);
    out.set_item("status", result.status)?;
    out.set_item("error", result.error)?;
    out.set_item("verdict", result.verdict.unwrap_or_else(|| py.None()))?;
    out.set_item("ticks", result.ticks)?;
    out.set_item("output", result.output)?;
    out.set_item("output_ticks", result.output_ticks)?;
    out.set_item("frames", result.frames)?;
    out.set_item("frame_ticks", result.frame_ticks)?;
    out.set_item("mcell", result.mcell)?;
    out.set_item("mdir", result.mdir)?;
    out.set_item("mA", result.ma)?;
    out.set_item("mB", result.mb)?;
    out.set_item("mBP", result.mbp)?;
    out.set_item("mhalt", result.mhalt)?;
    out.set_item("mwait", result.mwait)?;
    out.set_item("malive", result.malive)?;
    out.set_item("p_runs", result.p_runs)?;
    out.set_item("p_vals", result.p_vals)?;
    out.set_item("disp_cur", result.disp_cur)?;
    out.set_item("disp_next", result.disp_next)?;
    out.set_item("disp_cursor", result.disp_cursor)?;
    Ok(out.into_py(py))
}

#[pymodule]
fn _fastsim_rust(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(backend, module)?)?;
    module.add_function(wrap_pyfunction!(run, module)?)?;
    module.add_function(wrap_pyfunction!(run_official, module)?)?;
    Ok(())
}
