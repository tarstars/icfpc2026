use bincode::Options;
#[cfg(feature = "python")]
use pyo3::exceptions::{PyKeyError, PyValueError};
#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use pyo3::types::PyDict;
use serde::{Deserialize, Serialize};
use std::io::Read;

const IR_MAGIC: &[u8; 6] = b"LMIR\x01Z";
const MAX_DECODED_IR_BYTES: usize = 256 * 1024 * 1024;

fn default_version() -> i32 {
    1
}

fn default_semantics() -> i32 {
    1
}

fn default_men_cap() -> usize {
    65_536
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Spec {
    #[serde(rename = "ir_version", default = "default_version")]
    pub version: i32,
    #[serde(default = "default_semantics")]
    pub semantics_version: i32,
    #[serde(default = "default_men_cap")]
    pub men_cap: usize,
    #[serde(rename = "W")]
    pub w: usize,
    #[serde(rename = "H")]
    pub h: usize,
    pub n_cells: usize,
    pub code: [Vec<i32>; 4],
    pub lit: [Vec<i64>; 4],
    pub step: [Vec<i32>; 4],
    pub cellpos: Vec<usize>,
    pub mcell: Vec<usize>,
    pub mdir: Vec<u8>,
    pub mroom: Vec<usize>,
    pub mhalt: Vec<u8>,
    #[serde(rename = "mA")]
    pub ma: Vec<i64>,
    #[serde(rename = "mB")]
    pub mb: Vec<i64>,
    #[serde(rename = "mBP")]
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

impl Spec {
    pub fn validate(&self) -> Result<(), String> {
        if self.version != 1 {
            return Err(format!("unsupported IR version {}", self.version));
        }
        if !(1..=2).contains(&self.semantics_version) {
            return Err(format!(
                "unsupported semantics version {}",
                self.semantics_version
            ));
        }
        if self.men_cap == 0 || self.men_cap > 65_536 {
            return Err(format!("men_cap {} is outside 1..=65536", self.men_cap));
        }
        let area = self
            .w
            .checked_mul(self.h)
            .ok_or_else(|| "machine dimensions overflow usize".to_owned())?;
        if self.w == 0 || self.h == 0 {
            return Err("machine dimensions must be nonzero".into());
        }
        if self.n_cells > i32::MAX as usize {
            return Err(format!("n_cells {} exceeds i32::MAX", self.n_cells));
        }
        for (name, len) in [
            ("cellpos", self.cellpos.len()),
            ("code[0]", self.code[0].len()),
            ("code[1]", self.code[1].len()),
            ("code[2]", self.code[2].len()),
            ("code[3]", self.code[3].len()),
            ("lit[0]", self.lit[0].len()),
            ("lit[1]", self.lit[1].len()),
            ("lit[2]", self.lit[2].len()),
            ("lit[3]", self.lit[3].len()),
            ("step[0]", self.step[0].len()),
            ("step[1]", self.step[1].len()),
            ("step[2]", self.step[2].len()),
            ("step[3]", self.step[3].len()),
        ] {
            if len != self.n_cells {
                return Err(format!(
                    "{name} has length {len}, expected {}",
                    self.n_cells
                ));
            }
        }
        for (cell, &position) in self.cellpos.iter().enumerate() {
            if position >= area {
                return Err(format!(
                    "cellpos[{cell}]={position} is outside machine area {area}"
                ));
            }
        }
        for direction in 0..4 {
            for (cell, &next) in self.step[direction].iter().enumerate() {
                if next < -1 || next >= self.n_cells as i32 {
                    return Err(format!(
                        "step[{direction}][{cell}]={next} is outside -1..{}",
                        self.n_cells
                    ));
                }
            }
        }
        let n_men = self.mcell.len();
        for (name, len) in [
            ("mdir", self.mdir.len()),
            ("mroom", self.mroom.len()),
            ("mhalt", self.mhalt.len()),
            ("mA", self.ma.len()),
            ("mB", self.mb.len()),
            ("mBP", self.mbp.len()),
        ] {
            if len != n_men {
                return Err(format!("{name} has length {len}, expected {n_men}"));
            }
        }
        let offset_len = self.room_out_off.len();
        if offset_len < 2
            || self.room_in_off.len() != offset_len
            || self.room_ins_off.len() != offset_len
        {
            return Err("room offset arrays must have one common length >= 2".into());
        }
        let n_rooms = offset_len - 1;
        for man in 0..n_men {
            if self.mcell[man] >= self.n_cells {
                return Err(format!("mcell[{man}] is outside the cell table"));
            }
            if self.mdir[man] >= 4 {
                return Err(format!("mdir[{man}]={} is outside 0..4", self.mdir[man]));
            }
            if self.mroom[man] >= n_rooms {
                return Err(format!(
                    "mroom[{man}]={} is outside 0..{n_rooms}",
                    self.mroom[man]
                ));
            }
            if self.mhalt[man] > 1 {
                return Err(format!("mhalt[{man}]={} is not boolean", self.mhalt[man]));
            }
        }
        let n_pipes = self.p_len.len();
        if n_pipes > i32::MAX as usize {
            return Err(format!("pipe count {n_pipes} exceeds i32::MAX"));
        }
        for (name, len) in [
            ("p_runs", self.p_runs.len()),
            ("p_vals", self.p_vals.len()),
            ("p_turn", self.p_turn.len()),
            ("p_src_pos", self.p_src_pos.len()),
            ("p_dst_pos", self.p_dst_pos.len()),
        ] {
            if len != n_pipes {
                return Err(format!("{name} has length {len}, expected {n_pipes}"));
            }
        }
        for pipe in 0..n_pipes {
            let length = self.p_len[pipe];
            if length == 0 || length > i32::MAX as usize {
                return Err(format!("p_len[{pipe}]={length} is outside 1..=i32::MAX"));
            }
            if self.p_turn[pipe] >= 4 {
                return Err(format!(
                    "p_turn[{pipe}]={} is outside 0..4",
                    self.p_turn[pipe]
                ));
            }
            if self.p_src_pos[pipe] >= area || self.p_dst_pos[pipe] >= area {
                return Err(format!(
                    "pipe {pipe} endpoint is outside machine area {area}"
                ));
            }
            let runs = &self.p_runs[pipe];
            if runs.len() % 2 != 0 {
                return Err(format!("p_runs[{pipe}] has odd length {}", runs.len()));
            }
            let mut values = 0usize;
            let mut previous_end = -1;
            for pair in runs.chunks_exact(2) {
                let (start, end) = (pair[0], pair[1]);
                if start < 0 || start > end || end >= length as i32 {
                    return Err(format!(
                        "p_runs[{pipe}] contains invalid interval {start}..{end}"
                    ));
                }
                if start <= previous_end {
                    return Err(format!("p_runs[{pipe}] intervals overlap or regress"));
                }
                values = values
                    .checked_add((end - start + 1) as usize)
                    .ok_or_else(|| format!("p_runs[{pipe}] value count overflows"))?;
                previous_end = end;
            }
            if values != self.p_vals[pipe].len() {
                return Err(format!(
                    "p_vals[{pipe}] has length {}, expected {values} from runs",
                    self.p_vals[pipe].len()
                ));
            }
        }
        for (name, offsets, indices) in [
            ("room_out", &self.room_out_off, &self.room_out_idx),
            ("room_in", &self.room_in_off, &self.room_in_idx),
            ("room_ins", &self.room_ins_off, &self.room_ins_idx),
        ] {
            if offsets[0] != 0 || offsets[offsets.len() - 1] != indices.len() {
                return Err(format!("{name} offsets do not span the index array"));
            }
            if offsets.windows(2).any(|pair| pair[0] > pair[1])
                || offsets.iter().any(|&offset| offset > indices.len())
            {
                return Err(format!("{name} offsets are not monotone and in bounds"));
            }
            if indices.iter().any(|&pipe| pipe >= n_pipes) {
                return Err(format!("{name} contains an out-of-range pipe index"));
            }
        }
        for (name, pipe) in [
            ("input_pipe", self.input_pipe),
            ("output_pipe", self.output_pipe),
        ] {
            if pipe < -1 || pipe >= n_pipes as i32 {
                return Err(format!("{name}={pipe} is outside -1..{n_pipes}"));
            }
        }
        if self.disp_pipes.iter().any(|&pipe| pipe >= n_pipes) {
            return Err("disp_pipes contains an out-of-range pipe index".into());
        }
        if self.disp_cur.len() != self.disp.len() || self.disp_next.len() != self.disp.len() {
            return Err("display state arrays do not match display count".into());
        }
        for (display, fields) in self.disp.iter().enumerate() {
            if fields.len() != 6 {
                return Err(format!(
                    "disp[{display}] has {} fields, expected 6",
                    fields.len()
                ));
            }
            for (side, &pipe) in fields[..3].iter().enumerate() {
                if pipe < -1 || pipe >= n_pipes as i32 {
                    return Err(format!("disp[{display}][{side}] has invalid pipe {pipe}"));
                }
            }
            let width = usize::try_from(fields[3])
                .map_err(|_| format!("disp[{display}] has negative width"))?;
            let height = usize::try_from(fields[4])
                .map_err(|_| format!("disp[{display}] has negative height"))?;
            let pixels = width
                .checked_mul(height)
                .ok_or_else(|| format!("disp[{display}] dimensions overflow"))?;
            let cursor = usize::try_from(fields[5])
                .map_err(|_| format!("disp[{display}] has negative cursor"))?;
            if width == 0 || height == 0 || cursor >= pixels {
                return Err(format!("disp[{display}] has invalid dimensions/cursor"));
            }
            if self.disp_cur[display].len() != pixels || self.disp_next[display].len() != pixels {
                return Err(format!("disp[{display}] buffers do not match dimensions"));
            }
        }
        Ok(())
    }

    pub fn encode_compressed(&self) -> Result<Vec<u8>, String> {
        self.validate()?;
        let raw = bincode::serialize(self).map_err(|error| error.to_string())?;
        if raw.len() > MAX_DECODED_IR_BYTES {
            return Err(format!(
                "encoded IR size {} exceeds limit {MAX_DECODED_IR_BYTES}",
                raw.len()
            ));
        }
        let compressed = zstd::bulk::compress(&raw, 3).map_err(|error| error.to_string())?;
        let mut output = Vec::with_capacity(IR_MAGIC.len() + 8 + compressed.len());
        output.extend_from_slice(IR_MAGIC);
        output.extend_from_slice(&(raw.len() as u64).to_le_bytes());
        output.extend_from_slice(&compressed);
        Ok(output)
    }

    pub fn decode_compressed(data: &[u8]) -> Result<Self, String> {
        if data.len() < IR_MAGIC.len() + 8 || &data[..IR_MAGIC.len()] != IR_MAGIC {
            return Err("invalid littleman IR magic/version".into());
        }
        let length_offset = IR_MAGIC.len();
        let raw_len =
            u64::from_le_bytes(data[length_offset..length_offset + 8].try_into().unwrap());
        let raw_len = usize::try_from(raw_len).map_err(|_| "IR size does not fit this platform")?;
        if raw_len > MAX_DECODED_IR_BYTES {
            return Err(format!(
                "decoded IR size {raw_len} exceeds limit {MAX_DECODED_IR_BYTES}"
            ));
        }
        let mut decoder = zstd::stream::read::Decoder::new(&data[length_offset + 8..])
            .map_err(|error| error.to_string())?;
        decoder
            .window_log_max(28)
            .map_err(|error| error.to_string())?;
        let mut raw = Vec::with_capacity(raw_len.min(1024 * 1024));
        decoder
            .take(raw_len as u64 + 1)
            .read_to_end(&mut raw)
            .map_err(|error| error.to_string())?;
        if raw.len() != raw_len {
            return Err(format!(
                "IR length mismatch: decoded {}, expected {raw_len}",
                raw.len()
            ));
        }
        let spec: Self = bincode::DefaultOptions::new()
            .with_fixint_encoding()
            .allow_trailing_bytes()
            .with_limit(raw_len as u64)
            .deserialize(&raw)
            .map_err(|error| error.to_string())?;
        spec.validate()?;
        Ok(spec)
    }
}

#[cfg(test)]
mod tests {
    use super::{Spec, IR_MAGIC, MAX_DECODED_IR_BYTES};

    fn header(length: u64) -> Vec<u8> {
        let mut data = IR_MAGIC.to_vec();
        data.extend_from_slice(&length.to_le_bytes());
        data
    }

    #[test]
    fn oversized_cache_header_fails_before_decompression() {
        let error = Spec::decode_compressed(&header(MAX_DECODED_IR_BYTES as u64 + 1)).unwrap_err();
        assert!(error.contains("exceeds limit"));
    }

    #[test]
    fn truncated_cache_payload_is_an_error() {
        let mut data = header(10);
        data.extend_from_slice(b"not-zstd");
        assert!(Spec::decode_compressed(&data).is_err());
    }
}

#[cfg(feature = "python")]
fn item<'py, T>(dict: &Bound<'py, PyDict>, key: &str) -> PyResult<T>
where
    T: FromPyObject<'py>,
{
    dict.get_item(key)?
        .ok_or_else(|| PyKeyError::new_err(format!("missing spec key {key}")))?
        .extract()
}

#[cfg(feature = "python")]
fn four<T>(values: Vec<Vec<T>>, name: &str) -> PyResult<[Vec<T>; 4]> {
    values.try_into().map_err(|v: Vec<Vec<T>>| {
        PyValueError::new_err(format!("{name} must have 4 headings, got {}", v.len()))
    })
}

#[cfg(feature = "python")]
fn check_len(name: &str, actual: usize, expected: usize) -> PyResult<()> {
    if actual == expected {
        Ok(())
    } else {
        Err(PyValueError::new_err(format!(
            "{name} has length {actual}, expected {expected}"
        )))
    }
}

#[cfg(feature = "python")]
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

        let spec = Self {
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
            mhalt: mhalt_i,
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
        };
        spec.validate().map_err(PyValueError::new_err)?;
        Ok(spec)
    }
}
