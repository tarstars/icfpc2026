use std::collections::VecDeque;
use std::convert::Infallible;
use std::fs;
use std::io::{self, Read};
use std::sync::Arc;

use _fastsim_rust::engine::{Engine, Hooks, RunOutput};
use _fastsim_rust::spec::Spec;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};

#[derive(Deserialize)]
struct Request {
    #[serde(default)]
    spec: Option<Spec>,
    jobs: Vec<Job>,
    #[serde(default = "default_ticks")]
    max_ticks: i64,
    #[serde(default)]
    workers: Option<usize>,
    #[serde(default)]
    include_state: bool,
}

fn default_ticks() -> i64 {
    5_000_000
}

#[derive(Deserialize)]
struct Job {
    id: String,
    #[serde(default)]
    inputs: Vec<i64>,
    #[serde(default)]
    rounds: Option<Vec<Round>>,
}

#[derive(Clone, Deserialize)]
struct Round {
    #[serde(rename = "in", default)]
    input: Vec<i64>,
    #[serde(rename = "out", default)]
    output: Vec<i64>,
    #[serde(default)]
    frames: Vec<Vec<Vec<i8>>>,
}

#[derive(Serialize)]
struct JobResult {
    id: String,
    status: String,
    error: Option<String>,
    ticks: i64,
    judged_ticks: i64,
    output: Vec<i64>,
    output_ticks: Vec<i64>,
    frames: Vec<Vec<Vec<i8>>>,
    frame_ticks: Vec<i64>,
    state: Option<RunOutput>,
}

struct RawHooks {
    input: VecDeque<i64>,
}

impl Hooks for RawHooks {
    type Error = Infallible;

    fn pop_input(&mut self) -> Result<Option<i64>, Self::Error> {
        Ok(self.input.pop_front())
    }

    fn on_output(&mut self, _value: i64, _tick: i64) -> Result<bool, Self::Error> {
        Ok(false)
    }

    fn on_frame(&mut self, _frame: &[Vec<i8>], _tick: i64) -> Result<bool, Self::Error> {
        Ok(false)
    }
}

struct RoundHooks {
    rounds: Vec<Round>,
    round: usize,
    out: usize,
    frame: usize,
    input: VecDeque<i64>,
    done: bool,
    verdict: Option<String>,
    last_output_tick: i64,
}

impl RoundHooks {
    fn new(rounds: Vec<Round>) -> Self {
        let mut hooks = Self {
            rounds,
            round: 0,
            out: 0,
            frame: 0,
            input: VecDeque::new(),
            done: false,
            verdict: None,
            last_output_tick: 0,
        };
        hooks.release();
        hooks
    }

    fn release(&mut self) {
        while self.round < self.rounds.len() {
            self.input
                .extend(self.rounds[self.round].input.iter().copied());
            if !self.rounds[self.round].output.is_empty()
                || !self.rounds[self.round].frames.is_empty()
            {
                return;
            }
            self.round += 1;
        }
        self.done = true;
    }

    fn complete(&mut self, tick: i64) -> bool {
        let round = &self.rounds[self.round];
        if self.out < round.output.len() || self.frame < round.frames.len() {
            return false;
        }
        self.round += 1;
        self.out = 0;
        self.frame = 0;
        self.last_output_tick = tick;
        self.release();
        if self.done {
            self.verdict = Some("passed".into());
            true
        } else {
            false
        }
    }

    fn fail(&mut self) -> Result<bool, Infallible> {
        self.verdict = Some("failed".into());
        Ok(true)
    }
}

impl Hooks for RoundHooks {
    type Error = Infallible;

    fn pop_input(&mut self) -> Result<Option<i64>, Self::Error> {
        Ok(self.input.pop_front())
    }

    fn on_output(&mut self, value: i64, tick: i64) -> Result<bool, Self::Error> {
        if self.done {
            return self.fail();
        }
        let expected = &self.rounds[self.round].output;
        if self.out >= expected.len() || value != expected[self.out] {
            return self.fail();
        }
        self.out += 1;
        self.last_output_tick = tick;
        Ok(self.complete(tick))
    }

    fn on_frame(&mut self, frame: &[Vec<i8>], tick: i64) -> Result<bool, Self::Error> {
        if self.done {
            return self.fail();
        }
        let expected = &self.rounds[self.round].frames;
        if self.frame >= expected.len() || frame != expected[self.frame] {
            return self.fail();
        }
        self.frame += 1;
        self.last_output_tick = tick;
        Ok(self.complete(tick))
    }
}

fn strip_state(run: &mut RunOutput) {
    run.mcell.clear();
    run.mdir.clear();
    run.ma.clear();
    run.mb.clear();
    run.mbp.clear();
    run.mhalt.clear();
    run.mwait.clear();
    run.malive.clear();
    run.p_runs.clear();
    run.p_vals.clear();
    run.disp_cur.clear();
    run.disp_next.clear();
    run.disp_cursor.clear();
}

fn result(
    job: &Job,
    mut run: RunOutput,
    verdict: Option<String>,
    judged: i64,
    state: bool,
) -> JobResult {
    let status = if run.error.is_some() {
        "error".to_owned()
    } else {
        verdict.clone().unwrap_or_else(|| run.status.to_owned())
    };
    let output = run.output.clone();
    let output_ticks = run.output_ticks.clone();
    let frames = run.frames.clone();
    let frame_ticks = run.frame_ticks.clone();
    if !state {
        strip_state(&mut run);
    }
    JobResult {
        id: job.id.clone(),
        status,
        error: run.error.map(str::to_owned),
        ticks: run.ticks,
        judged_ticks: judged,
        output,
        output_ticks,
        frames,
        frame_ticks,
        state: state.then_some(run),
    }
}

fn run_job(spec: Arc<Spec>, job: &Job, max_ticks: i64, state: bool) -> JobResult {
    if let Some(rounds) = &job.rounds {
        let mut hooks = RoundHooks::new(rounds.clone());
        if hooks.done {
            return JobResult {
                id: job.id.clone(),
                status: "passed".into(),
                error: None,
                ticks: 0,
                judged_ticks: 0,
                output: vec![],
                output_ticks: vec![],
                frames: vec![],
                frame_ticks: vec![],
                state: None,
            };
        }
        let run = Engine::new(spec).run(&mut hooks, max_ticks).unwrap();
        let judged = if hooks.verdict.as_deref() == Some("passed") {
            hooks.last_output_tick
        } else {
            run.ticks
        };
        result(job, run, hooks.verdict, judged, state)
    } else {
        let mut hooks = RawHooks {
            input: job.inputs.iter().copied().collect(),
        };
        let run = Engine::new(spec).run(&mut hooks, max_ticks).unwrap();
        let ticks = run.ticks;
        result(job, run, None, ticks, state)
    }
}

fn read_request(path: Option<&str>) -> Result<String, String> {
    if let Some(path) = path {
        fs::read_to_string(path).map_err(|error| format!("{path}: {error}"))
    } else {
        let mut text = String::new();
        io::stdin()
            .read_to_string(&mut text)
            .map_err(|error| error.to_string())?;
        Ok(text)
    }
}

fn main() {
    let mut path = None;
    let mut ir_path = None;
    let mut pretty = false;
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--pretty" => pretty = true,
            "--ir" => {
                ir_path = Some(args.next().unwrap_or_else(|| {
                    eprintln!("littleman-rust: --ir requires a path");
                    std::process::exit(2);
                }));
            }
            _ if path.is_none() => path = Some(arg),
            _ => {
                eprintln!("littleman-rust: unexpected argument {arg}");
                std::process::exit(2);
            }
        }
    }
    let text = read_request(path.as_deref()).unwrap_or_else(|error| {
        eprintln!("littleman-rust: {error}");
        std::process::exit(2);
    });
    let request: Request = serde_json::from_str(&text).unwrap_or_else(|error| {
        eprintln!("littleman-rust: invalid request: {error}");
        std::process::exit(2);
    });
    let spec = if let Some(ir_path) = ir_path {
        let data = fs::read(&ir_path).unwrap_or_else(|error| {
            eprintln!("littleman-rust: {ir_path}: {error}");
            std::process::exit(2);
        });
        Spec::decode_compressed(&data).unwrap_or_else(|error| {
            eprintln!("littleman-rust: invalid cached IR: {error}");
            std::process::exit(2);
        })
    } else {
        request.spec.unwrap_or_else(|| {
            eprintln!("littleman-rust: request has no spec and --ir was not provided");
            std::process::exit(2);
        })
    };
    spec.validate().unwrap_or_else(|error| {
        eprintln!("littleman-rust: invalid IR: {error}");
        std::process::exit(2);
    });
    let spec = Arc::new(spec);
    let workers = request
        .workers
        .unwrap_or_else(|| std::thread::available_parallelism().map_or(1, usize::from))
        .max(1);
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(workers)
        .build()
        .unwrap();
    let results: Vec<_> = pool.install(|| {
        request
            .jobs
            .par_iter()
            .map(|job| {
                run_job(
                    Arc::clone(&spec),
                    job,
                    request.max_ticks,
                    request.include_state,
                )
            })
            .collect()
    });
    let output = if pretty {
        serde_json::to_string_pretty(&results)
    } else {
        serde_json::to_string(&results)
    }
    .unwrap();
    println!("{output}");
}
