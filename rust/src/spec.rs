use pyo3::exceptions::{PyKeyError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyDict;

#[derive(Clone, Debug)]
pub struct Spec {
    pub version: i32,
    pub semantics_version: i32,
    pub men_cap: usize,
    pub w: usize,
    pub h: usize,
    pub n_cells: usize,
    pub code: [Vec<i32>; 4],
    pub lit: [Vec<i64>; 4],
    pub step: [Vec<i32>; 4],
    pub cellpos: Vec<usize>,
    pub mcell: Vec<usize>,
    pub mdir: Vec<u8>,
    pub mroom: Vec<usize>,
    pub mhalt: Vec<bool>,
    pub ma: Vec<i64>,
    pub mb: Vec<i64>,
    pub mbp: Vec<i64>,
    pub p_len: Vec<usize>,
    pub p_runs: Vec<Vec<i32>>,
    pub p_vals: Vec<Vec<i64>>,
    pub p_turn: Vec<u8>,
    pub p_src_pos: Vec<usize>,
    pub p_dst_pos: Vec<usize>,
    pub room_out_off: Vec<usize>,
    pub room_out_idx: Vec<usize>,
    pub room_in_off: Vec<usize>,
    pub room_in_idx: Vec<usize>,
    pub room_ins_off: Vec<usize>,
    pub room_ins_idx: Vec<usize>,
    pub input_pipe: i32,
    pub output_pipe: i32,
    pub disp_pipes: Vec<usize>,
    pub disp: Vec<Vec<i32>>,
    pub disp_cur: Vec<Vec<i8>>,
    pub disp_next: Vec<Vec<i8>>,
}

fn item<'py, T>(dict: &Bound<'py, PyDict>, key: &str) -> PyResult<T>
where
    T: FromPyObject<'py>,
{
    dict.get_item(key)?
        .ok_or_else(|| PyKeyError::new_err(format!("missing spec key {key}")))?
        .extract()
}

fn four<T>(values: Vec<Vec<T>>, name: &str) -> PyResult<[Vec<T>; 4]> {
    values.try_into().map_err(|v: Vec<Vec<T>>| {
        PyValueError::new_err(format!("{name} must have 4 headings, got {}", v.len()))
    })
}

fn check_len(name: &str, actual: usize, expected: usize) -> PyResult<()> {
    if actual == expected {
        Ok(())
    } else {
        Err(PyValueError::new_err(format!(
            "{name} has length {actual}, expected {expected}"
        )))
    }
}

impl Spec {
    pub fn from_python(value: &Bound<'_, PyAny>) -> PyResult<Self> {
        let dict = value.downcast::<PyDict>()?;
        let version = dict
            .get_item("ir_version")?
            .map(|v| v.extract())
            .transpose()?
            .unwrap_or(1);
        if version != 1 {
            return Err(PyValueError::new_err(format!(
                "unsupported IR version {version}"
            )));
        }
        let semantics_version = dict
            .get_item("semantics_version")?
            .map(|v| v.extract())
            .transpose()?
            .unwrap_or(1);
        if !(1..=2).contains(&semantics_version) {
            return Err(PyValueError::new_err(format!(
                "unsupported semantics version {semantics_version}"
            )));
        }
        let men_cap = dict
            .get_item("men_cap")?
            .map(|v| v.extract())
            .transpose()?
            .unwrap_or(65_536);
        let w: usize = item(dict, "W")?;
        let h: usize = item(dict, "H")?;
        let n_cells: usize = item(dict, "n_cells")?;
        let code = four(item(dict, "code")?, "code")?;
        let lit = four(item(dict, "lit")?, "lit")?;
        let step = four(item(dict, "step")?, "step")?;
        let cellpos: Vec<usize> = item(dict, "cellpos")?;
        let mcell: Vec<usize> = item(dict, "mcell")?;
        let n_men = mcell.len();
        let mdir_i: Vec<u8> = item(dict, "mdir")?;
        let mroom: Vec<usize> = item(dict, "mroom")?;
        let mhalt_i: Vec<u8> = item(dict, "mhalt")?;
        let ma: Vec<i64> = item(dict, "mA")?;
        let mb: Vec<i64> = item(dict, "mB")?;
        let mbp: Vec<i64> = item(dict, "mBP")?;
        for (name, len) in [
            ("mdir", mdir_i.len()),
            ("mroom", mroom.len()),
            ("mhalt", mhalt_i.len()),
            ("mA", ma.len()),
            ("mB", mb.len()),
            ("mBP", mbp.len()),
        ] {
            check_len(name, len, n_men)?;
        }
        for d in 0..4 {
            check_len(&format!("code[{d}]"), code[d].len(), n_cells)?;
            check_len(&format!("lit[{d}]"), lit[d].len(), n_cells)?;
            check_len(&format!("step[{d}]"), step[d].len(), n_cells)?;
        }
        check_len("cellpos", cellpos.len(), n_cells)?;

        let p_len: Vec<usize> = item(dict, "p_len")?;
        let n_pipes = p_len.len();
        let p_runs: Vec<Vec<i32>> = item(dict, "p_runs")?;
        let p_vals: Vec<Vec<i64>> = item(dict, "p_vals")?;
        let p_turn: Vec<u8> = item(dict, "p_turn")?;
        let p_src_pos: Vec<usize> = item(dict, "p_src_pos")?;
        let p_dst_pos: Vec<usize> = item(dict, "p_dst_pos")?;
        for (name, len) in [
            ("p_runs", p_runs.len()),
            ("p_vals", p_vals.len()),
            ("p_turn", p_turn.len()),
            ("p_src_pos", p_src_pos.len()),
            ("p_dst_pos", p_dst_pos.len()),
        ] {
            check_len(name, len, n_pipes)?;
        }

        Ok(Self {
            version,
            semantics_version,
            men_cap,
            w,
            h,
            n_cells,
            code,
            lit,
            step,
            cellpos,
            mcell,
            mdir: mdir_i,
            mroom,
            mhalt: mhalt_i.into_iter().map(|v| v != 0).collect(),
            ma,
            mb,
            mbp,
            p_len,
            p_runs,
            p_vals,
            p_turn,
            p_src_pos,
            p_dst_pos,
            room_out_off: item(dict, "room_out_off")?,
            room_out_idx: item(dict, "room_out_idx")?,
            room_in_off: item(dict, "room_in_off")?,
            room_in_idx: item(dict, "room_in_idx")?,
            room_ins_off: item(dict, "room_ins_off")?,
            room_ins_idx: item(dict, "room_ins_idx")?,
            input_pipe: item(dict, "input_pipe")?,
            output_pipe: item(dict, "output_pipe")?,
            disp_pipes: item(dict, "disp_pipes")?,
            disp: item(dict, "disp")?,
            disp_cur: item(dict, "disp_cur")?,
            disp_next: item(dict, "disp_next")?,
        })
    }
}
