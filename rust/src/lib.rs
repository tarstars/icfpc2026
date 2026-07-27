pub mod engine;
pub mod spec;

#[cfg(feature = "python")]
mod python_api {
    use super::{engine, spec};
    use pyo3::prelude::*;
    use pyo3::types::{PyBytes, PyDict, PyTuple};

    struct PyHooks<'a, 'py> {
        py: Python<'py>,
        controller: &'a Bound<'py, PyAny>,
        ctrl_queue: &'a Bound<'py, PyAny>,
        input_queue: &'a Bound<'py, PyAny>,
        has_controller: bool,
        has_frame_callback: bool,
        verdict: Option<PyObject>,
    }

    impl<'a, 'py> PyHooks<'a, 'py> {
        fn new(
            py: Python<'py>,
            controller: &'a Bound<'py, PyAny>,
            ctrl_queue: &'a Bound<'py, PyAny>,
            input_queue: &'a Bound<'py, PyAny>,
        ) -> PyResult<Self> {
            let has_controller = !controller.is_none();
            Ok(Self {
                py,
                controller,
                ctrl_queue,
                input_queue,
                has_controller,
                has_frame_callback: has_controller && controller.hasattr("on_frame")?,
                verdict: None,
            })
        }
    }

    impl engine::Hooks for PyHooks<'_, '_> {
        type Error = PyErr;

        fn pop_input(&mut self) -> PyResult<Option<i64>> {
            if self.has_controller {
                if !self.ctrl_queue.is_none() && self.ctrl_queue.len().ok() == Some(0) {
                    return Ok(None);
                }
                let value = self.controller.call_method0("pop_input")?;
                return if value.is_none() {
                    Ok(None)
                } else {
                    Ok(Some(value.extract()?))
                };
            }
            if self.input_queue.len().ok().unwrap_or(0) == 0 {
                return Ok(None);
            }
            let value = self.input_queue.get_item(0)?.extract()?;
            self.input_queue.del_item(0)?;
            Ok(Some(value))
        }

        fn on_output(&mut self, value: i64, tick: i64) -> PyResult<bool> {
            if !self.has_controller {
                return Ok(false);
            }
            let result = self.controller.call_method1("on_output", (value, tick))?;
            if result.is_truthy()? {
                self.verdict = Some(result.unbind());
                Ok(true)
            } else {
                Ok(false)
            }
        }

        fn on_frame(&mut self, frame: &[Vec<i8>], tick: i64) -> PyResult<bool> {
            if !self.has_frame_callback {
                return Ok(false);
            }
            let result = self
                .controller
                .call_method1("on_frame", (frame.to_vec().into_py(self.py), tick))?;
            if result.is_truthy()? {
                self.verdict = Some(result.unbind());
                Ok(true)
            } else {
                Ok(false)
            }
        }
    }

    #[pyfunction]
    fn backend() -> &'static str {
        "rust"
    }

    #[pyfunction]
    fn encode_ir(py: Python<'_>, spec: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        let parsed = spec::Spec::from_python(spec)?;
        let encoded = parsed
            .encode_compressed()
            .map_err(pyo3::exceptions::PyValueError::new_err)?;
        Ok(PyBytes::new_bound(py, &encoded).into_py(py))
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
        let mut hooks = PyHooks::new(py, controller, ctrl_queue, input_queue)?;
        let result = engine::Engine::new(std::sync::Arc::new(parsed)).run(&mut hooks, max_ticks)?;
        let verdict = hooks.verdict.unwrap_or_else(|| py.None());
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
        let mut hooks = PyHooks::new(py, controller, ctrl_queue, input_queue)?;
        let result = engine::Engine::new(std::sync::Arc::new(parsed)).run(&mut hooks, max_ticks)?;
        let out = PyDict::new_bound(py);
        out.set_item("status", result.status)?;
        out.set_item("error", result.error)?;
        out.set_item("verdict", hooks.verdict.unwrap_or_else(|| py.None()))?;
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
        module.add_function(wrap_pyfunction!(encode_ir, module)?)?;
        module.add_function(wrap_pyfunction!(run, module)?)?;
        module.add_function(wrap_pyfunction!(run_official, module)?)?;
        Ok(())
    }
}
