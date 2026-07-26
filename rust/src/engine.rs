use std::cmp::Reverse;
use std::collections::{BinaryHeap, HashMap, VecDeque};
use std::sync::Arc;

use serde::Serialize;

use crate::spec::Spec;

const WAIT_NONE: u8 = 0;
const WAIT_R: u8 = 1;
const WAIT_RU: u8 = 2;
const WAIT_S: u8 = 3;
const WAIT_ALL: u8 = 4;

#[derive(Debug)]
struct Man {
    cell: usize,
    dir: u8,
    room: usize,
    halted: bool,
    a: i64,
    b: i64,
    bp: i64,
    wait: u8,
    wait_pipes: Vec<usize>,
    runnable: bool,
    stamp: i64,
    alive: bool,
    born: i64,
}

#[derive(Debug)]
struct Pipe {
    len: usize,
    runs: Vec<i32>,
    vals: VecDeque<i64>,
    turn: u8,
    src_pos: usize,
    dst_pos: usize,
    recv_waiters: Vec<usize>,
    send_waiters: Vec<usize>,
}

#[derive(Debug)]
struct Display {
    addr: i32,
    data: i32,
    swap: i32,
    w: usize,
    h: usize,
    cursor: usize,
    current: Vec<i8>,
    next: Vec<i8>,
}

#[derive(Serialize)]
pub struct RunOutput {
    pub status: &'static str,
    pub error: Option<&'static str>,
    pub hook_stopped: bool,
    pub ticks: i64,
    pub output: Vec<i64>,
    pub output_ticks: Vec<i64>,
    pub frames: Vec<Vec<Vec<i8>>>,
    pub frame_ticks: Vec<i64>,
    pub mcell: Vec<usize>,
    pub mdir: Vec<u8>,
    pub ma: Vec<i64>,
    pub mb: Vec<i64>,
    pub mbp: Vec<i64>,
    pub mhalt: Vec<u8>,
    pub mwait: Vec<u8>,
    pub malive: Vec<u8>,
    pub p_runs: Vec<Vec<i32>>,
    pub p_vals: Vec<Vec<i64>>,
    pub disp_cur: Vec<Vec<i8>>,
    pub disp_next: Vec<Vec<i8>>,
    pub disp_cursor: Vec<usize>,
}

pub trait Hooks {
    type Error;

    fn pop_input(&mut self) -> Result<Option<i64>, Self::Error>;
    fn on_output(&mut self, value: i64, tick: i64) -> Result<bool, Self::Error>;
    fn on_frame(&mut self, frame: &[Vec<i8>], tick: i64) -> Result<bool, Self::Error>;
}

pub struct Engine {
    spec: Arc<Spec>,
    men: Vec<Man>,
    pipes: Vec<Pipe>,
    displays: Vec<Display>,
    runnable_buf: Vec<usize>,
    runnable_count: usize,
    heap: BinaryHeap<Reverse<usize>>,
    active: Vec<usize>,
    active_pos: Vec<isize>,
    occupied: Vec<isize>,
    near_out: Vec<i32>,
    near_in: Vec<i32>,
    recv_wait_count: usize,
    send_wait_count: usize,
    in_execute: bool,
    current_man: isize,
    tick: i64,
}

impl Engine {
    pub fn new(spec: Arc<Spec>) -> Self {
        let mut men = Vec::with_capacity(spec.mcell.len());
        let mut runnable_buf = Vec::new();
        let mut occupied = vec![-1; spec.w * spec.h];
        for i in 0..spec.mcell.len() {
            let halted = spec.mhalt[i] != 0;
            let runnable = !halted;
            if runnable {
                runnable_buf.push(i);
            }
            occupied[spec.cellpos[spec.mcell[i]]] = i as isize;
            men.push(Man {
                cell: spec.mcell[i],
                dir: spec.mdir[i],
                room: spec.mroom[i],
                halted,
                a: spec.ma[i],
                b: spec.mb[i],
                bp: spec.mbp[i],
                wait: WAIT_NONE,
                wait_pipes: Vec::new(),
                runnable,
                stamp: -1,
                alive: true,
                born: 0,
            });
        }
        let pipes: Vec<Pipe> = spec
            .p_len
            .iter()
            .enumerate()
            .map(|(i, &len)| Pipe {
                len,
                runs: spec.p_runs[i].clone(),
                vals: spec.p_vals[i].iter().copied().collect(),
                turn: spec.p_turn[i],
                src_pos: spec.p_src_pos[i],
                dst_pos: spec.p_dst_pos[i],
                recv_waiters: Vec::new(),
                send_waiters: Vec::new(),
            })
            .collect();
        let mut active = Vec::new();
        let mut active_pos = vec![-1; pipes.len()];
        for (i, pipe) in pipes.iter().enumerate() {
            if Self::pipe_active(pipe) {
                active_pos[i] = active.len() as isize;
                active.push(i);
            }
        }
        let displays = spec
            .disp
            .iter()
            .enumerate()
            .map(|(i, d)| Display {
                addr: d[0],
                data: d[1],
                swap: d[2],
                w: d[3] as usize,
                h: d[4] as usize,
                cursor: d[5] as usize,
                current: spec.disp_cur[i].clone(),
                next: spec.disp_next[i].clone(),
            })
            .collect();
        let n_cells = spec.n_cells;
        Self {
            spec,
            men,
            pipes,
            displays,
            runnable_count: runnable_buf.len(),
            runnable_buf,
            heap: BinaryHeap::new(),
            active,
            active_pos,
            occupied,
            near_out: vec![-2; n_cells],
            near_in: vec![-2; n_cells],
            recv_wait_count: 0,
            send_wait_count: 0,
            in_execute: false,
            current_man: -1,
            tick: 0,
        }
    }

    fn pipe_active(pipe: &Pipe) -> bool {
        !pipe.runs.is_empty()
            && (pipe.runs.len() > 2 || pipe.runs[pipe.runs.len() - 1] != pipe.len as i32 - 1)
    }

    fn runnable_add(&mut self, man: usize) {
        if !self.men[man].alive || self.men[man].halted || self.men[man].runnable {
            return;
        }
        self.men[man].runnable = true;
        self.runnable_buf.push(man);
        self.runnable_count += 1;
    }

    fn runnable_discard(&mut self, man: usize) {
        if !self.men[man].runnable {
            return;
        }
        self.men[man].runnable = false;
        self.runnable_count -= 1;
    }

    fn kill(&mut self, man: usize) {
        if !self.men[man].alive {
            return;
        }
        self.runnable_discard(man);
        self.clear_wait(man);
        let pos = self.spec.cellpos[self.men[man].cell];
        if self.occupied[pos] == man as isize {
            self.occupied[pos] = -1;
        }
        self.men[man].alive = false;
    }

    fn kill_pair(&mut self, first: usize, second: usize) {
        self.kill(first);
        self.kill(second);
    }

    fn split_man(&mut self, man: usize) -> Result<(), &'static str> {
        let dir = self.men[man].dir;
        let right_dir = (dir + 1) & 3;
        let left_dir = (dir + 3) & 3;
        let cell = self.men[man].cell;
        let right_cell = self.spec.step[right_dir as usize][cell];
        let left_cell = self.spec.step[left_dir as usize][cell];
        if right_cell < 0 || left_cell < 0 {
            return Err("wall-birth");
        }
        let right_cell = right_cell as usize;
        let left_cell = left_cell as usize;
        let room = self.men[man].room;
        let (a, b, bp) = (self.men[man].a, self.men[man].b, self.men[man].bp);
        let old_pos = self.spec.cellpos[cell];
        if self.occupied[old_pos] == man as isize {
            self.occupied[old_pos] = -1;
        }
        self.men[man] = Man {
            cell: right_cell,
            dir: right_dir,
            room,
            halted: false,
            a,
            b,
            bp,
            wait: WAIT_NONE,
            wait_pipes: Vec::new(),
            runnable: false,
            stamp: self.tick,
            alive: true,
            born: self.tick,
        };
        let left = self.men.len();
        self.men.push(Man {
            cell: left_cell,
            dir: left_dir,
            room,
            halted: false,
            a,
            b,
            bp,
            wait: WAIT_NONE,
            wait_pipes: Vec::new(),
            runnable: false,
            stamp: self.tick,
            alive: true,
            born: self.tick,
        });
        self.runnable_add(man);
        self.runnable_add(left);
        if self.men.iter().filter(|m| m.alive).count() > self.spec.men_cap {
            return Err("men-cap");
        }
        for baby in [man, left] {
            if !self.men[baby].alive {
                continue;
            }
            let pos = self.spec.cellpos[self.men[baby].cell];
            let occupant = self.occupied[pos];
            if occupant >= 0 && occupant as usize != baby {
                self.kill_pair(baby, occupant as usize);
            } else {
                self.occupied[pos] = baby as isize;
            }
        }
        Ok(())
    }

    fn active_add(&mut self, pipe: usize) {
        if self.active_pos[pipe] >= 0 {
            return;
        }
        self.active_pos[pipe] = self.active.len() as isize;
        self.active.push(pipe);
    }

    fn active_del(&mut self, pipe: usize) {
        let pos = self.active_pos[pipe];
        if pos < 0 {
            return;
        }
        let pos = pos as usize;
        let last = self.active.pop().unwrap();
        if pos < self.active.len() {
            self.active[pos] = last;
            self.active_pos[last] = pos as isize;
        }
        self.active_pos[pipe] = -1;
    }

    fn waiter_add(waiters: &mut Vec<usize>, man: usize) {
        if !waiters.contains(&man) {
            waiters.push(man);
        }
    }

    fn clear_wait(&mut self, man: usize) {
        let kind = self.men[man].wait;
        if kind == WAIT_NONE {
            self.men[man].wait_pipes.clear();
            return;
        }
        let pipes = std::mem::take(&mut self.men[man].wait_pipes);
        let recv = kind == WAIT_R || kind == WAIT_RU;
        for pipe in pipes {
            let waiters = if recv {
                &mut self.pipes[pipe].recv_waiters
            } else {
                &mut self.pipes[pipe].send_waiters
            };
            if let Some(pos) = waiters.iter().position(|&v| v == man) {
                waiters.swap_remove(pos);
            }
        }
        if recv {
            self.recv_wait_count -= 1;
        } else {
            self.send_wait_count -= 1;
        }
        self.men[man].wait = WAIT_NONE;
    }

    fn set_wait(&mut self, man: usize, kind: u8, pipes: Vec<usize>) {
        let recv = kind == WAIT_R || kind == WAIT_RU;
        for &pipe in &pipes {
            if recv {
                Self::waiter_add(&mut self.pipes[pipe].recv_waiters, man);
            } else {
                Self::waiter_add(&mut self.pipes[pipe].send_waiters, man);
            }
        }
        self.men[man].wait = kind;
        self.men[man].wait_pipes = pipes;
        if recv {
            self.recv_wait_count += 1;
        } else {
            self.send_wait_count += 1;
        }
    }

    fn condition_ready(&self, man: usize) -> bool {
        let m = &self.men[man];
        match m.wait {
            WAIT_R => {
                let p = &self.pipes[m.wait_pipes[0]];
                p.runs.last().copied() == Some(p.len as i32 - 1)
            }
            WAIT_RU => m.wait_pipes.iter().any(|&pi| {
                let p = &self.pipes[pi];
                p.runs.last().copied() == Some(p.len as i32 - 1)
            }),
            WAIT_S => self.pipes[m.wait_pipes[0]].runs.first().copied() != Some(0),
            WAIT_ALL => m
                .wait_pipes
                .iter()
                .all(|&pi| self.pipes[pi].runs.first().copied() != Some(0)),
            _ => false,
        }
    }

    fn maybe_wake(&mut self, man: usize) {
        if self.men[man].wait == WAIT_NONE || self.men[man].halted || !self.condition_ready(man) {
            return;
        }
        self.clear_wait(man);
        if self.in_execute && man as isize > self.current_man && self.men[man].stamp != self.tick {
            self.heap.push(Reverse(man));
        } else {
            self.runnable_add(man);
        }
    }

    fn wake_recv(&mut self, pipe: usize) {
        let waiters = self.pipes[pipe].recv_waiters.clone();
        for man in waiters {
            self.maybe_wake(man);
        }
    }

    fn wake_send(&mut self, pipe: usize) {
        let waiters = self.pipes[pipe].send_waiters.clone();
        for man in waiters {
            self.maybe_wake(man);
        }
    }

    fn put0(&mut self, pipe: usize, value: i64) {
        {
            let p = &mut self.pipes[pipe];
            p.vals.push_front(value);
            if p.runs.first().copied() == Some(1) {
                p.runs[0] = 0;
            } else {
                p.runs.insert(0, 0);
                p.runs.insert(1, 0);
            }
        }
        if Self::pipe_active(&self.pipes[pipe]) {
            self.active_add(pipe);
        } else {
            self.active_del(pipe);
        }
        let p = &self.pipes[pipe];
        if p.runs.last().copied() == Some(p.len as i32 - 1) {
            self.wake_recv(pipe);
        }
    }

    fn take_last(&mut self, pipe: usize) -> i64 {
        let value;
        {
            let p = &mut self.pipes[pipe];
            value = p.vals.pop_back().unwrap();
            let last = p.len as i32 - 1;
            let n = p.runs.len();
            if p.runs[n - 2] == last {
                p.runs.truncate(n - 2);
            } else {
                p.runs[n - 1] = last - 1;
            }
        }
        if Self::pipe_active(&self.pipes[pipe]) {
            self.active_add(pipe);
        } else {
            self.active_del(pipe);
        }
        if self.pipes[pipe].runs.first().copied() != Some(0) {
            self.wake_send(pipe);
        }
        value
    }

    fn shift_pipes(&mut self) {
        let snapshot = self.active.clone();
        for pipe in snapshot {
            let (src_was_full, dst_was_empty);
            {
                let p = &mut self.pipes[pipe];
                let last = p.len as i32 - 1;
                src_was_full = p.runs[0] == 0;
                dst_was_empty = *p.runs.last().unwrap() != last;
                let blocked = *p.runs.last().unwrap() == last;
                let moving = if blocked {
                    p.runs.len() - 2
                } else {
                    p.runs.len()
                };
                for pair in p.runs[..moving].chunks_exact_mut(2) {
                    pair[0] += 1;
                    pair[1] += 1;
                }
                if blocked && moving > 0 && p.runs[moving - 1] + 1 == p.runs[moving] {
                    p.runs[moving - 1] = p.runs[moving + 1];
                    p.runs.drain(moving..moving + 2);
                }
            }
            if !Self::pipe_active(&self.pipes[pipe]) {
                self.active_del(pipe);
            }
            if src_was_full && self.pipes[pipe].runs[0] != 0 {
                self.wake_send(pipe);
            }
            let p = &self.pipes[pipe];
            if dst_was_empty && p.runs.last().copied() == Some(p.len as i32 - 1) {
                self.wake_recv(pipe);
            }
        }
    }

    fn nearest_pick(&self, indices: &[usize], pos: usize, output: bool) -> i32 {
        if indices.is_empty() {
            return -1;
        }
        let (r, c) = (pos / self.spec.w, pos % self.spec.w);
        indices
            .iter()
            .copied()
            .min_by_key(|&pi| {
                let p = &self.pipes[pi];
                let endpoint = if output { p.src_pos } else { p.dst_pos };
                let (pr, pc) = (endpoint / self.spec.w, endpoint % self.spec.w);
                (pr.abs_diff(r) + pc.abs_diff(c), pr, pc)
            })
            .unwrap() as i32
    }

    fn room_slice<'a>(offsets: &[usize], indices: &'a [usize], room: usize) -> &'a [usize] {
        &indices[offsets[room]..offsets[room + 1]]
    }

    fn nearest_out(&mut self, cell: usize, room: usize) -> i32 {
        if self.near_out[cell] == -2 {
            let candidates =
                Self::room_slice(&self.spec.room_out_off, &self.spec.room_out_idx, room);
            self.near_out[cell] = self.nearest_pick(candidates, self.spec.cellpos[cell], true);
        }
        self.near_out[cell]
    }

    fn nearest_in(&mut self, cell: usize, room: usize) -> i32 {
        if self.near_in[cell] == -2 {
            let candidates = Self::room_slice(&self.spec.room_in_off, &self.spec.room_in_idx, room);
            self.near_in[cell] = self.nearest_pick(candidates, self.spec.cellpos[cell], false);
        }
        self.near_in[cell]
    }

    fn floor_divmod(a: i64, b: i64) -> (i64, i64) {
        if b == -1 {
            return (a.wrapping_neg(), 0);
        }
        let mut q = a / b;
        let mut r = a % b;
        if r != 0 && ((r < 0) != (b < 0)) {
            q -= 1;
            r += b;
        }
        (q, r)
    }

    fn execute_man(&mut self, man: usize) -> Result<bool, &'static str> {
        let cell = self.men[man].cell;
        let dir = self.men[man].dir as usize;
        let room = self.men[man].room;
        let op = self.spec.code[dir][cell];
        match op {
            0 => {}
            1..=4 => self.men[man].dir = (op - 1) as u8,
            5 => self.men[man].a = self.spec.lit[dir][cell],
            7 => {
                self.men[man].halted = true;
                return Ok(false);
            }
            8 => self.men[man].b = self.men[man].a,
            9 => {
                let m = &mut self.men[man];
                std::mem::swap(&mut m.a, &mut m.b);
            }
            10 => {
                let m = &mut self.men[man];
                m.a = m.a.wrapping_add(m.b);
            }
            11 => {
                let m = &mut self.men[man];
                m.a = m.a.wrapping_sub(m.b);
            }
            12 => {
                let m = &mut self.men[man];
                m.a = m.a.wrapping_mul(m.b);
            }
            13 => self.men[man].a = self.men[man].a.wrapping_neg(),
            14 => {
                let m = &mut self.men[man];
                m.a = if m.b == 0 {
                    0
                } else {
                    Self::floor_divmod(m.a, m.b).1
                };
            }
            15 => {
                let m = &mut self.men[man];
                if m.b == 0 {
                    m.b = m.a;
                    m.a = 0;
                } else {
                    (m.a, m.b) = Self::floor_divmod(m.a, m.b);
                }
            }
            16 => self.men[man].a &= self.men[man].b,
            17 => self.men[man].a |= self.men[man].b,
            18 => self.men[man].a ^= self.men[man].b,
            19 => {
                let m = &mut self.men[man];
                m.a = if (0..=63).contains(&m.b) {
                    ((m.a as u64) << m.b) as i64
                } else {
                    0
                };
            }
            20 => {
                let m = &mut self.men[man];
                m.a = if m.b < 0 { 0 } else { m.a >> m.b.min(63) };
            }
            21 => {
                let m = &mut self.men[man];
                if m.a > 0 {
                    m.dir = (dir as u8 + 1) & 3;
                } else if m.a < 0 {
                    m.dir = (dir as u8 + 3) & 3;
                }
            }
            22 => {
                let pipe = self.nearest_out(cell, room);
                if pipe < 0 {
                    return Err("no-pipe");
                }
                let pipe = pipe as usize;
                if self.pipes[pipe].runs.first().copied() == Some(0) {
                    self.set_wait(man, WAIT_S, vec![pipe]);
                    return Ok(false);
                }
                self.put0(pipe, self.men[man].a);
            }
            23 => {
                let outs = Self::room_slice(&self.spec.room_out_off, &self.spec.room_out_idx, room)
                    .to_vec();
                if outs.is_empty() {
                    return Err("no-pipe");
                }
                if outs
                    .iter()
                    .any(|&pi| self.pipes[pi].runs.first().copied() == Some(0))
                {
                    self.set_wait(man, WAIT_ALL, outs);
                    return Ok(false);
                }
                let value = self.men[man].a;
                for pipe in outs {
                    self.put0(pipe, value);
                }
            }
            24 => {
                let pipe = self.nearest_in(cell, room);
                if pipe < 0 {
                    return Err("no-pipe");
                }
                let pipe = pipe as usize;
                let p = &self.pipes[pipe];
                if p.runs.last().copied() == Some(p.len as i32 - 1) {
                    self.men[man].a = self.take_last(pipe);
                } else {
                    self.set_wait(man, WAIT_R, vec![pipe]);
                    return Ok(false);
                }
            }
            25 | 26 => {
                let ins =
                    Self::room_slice(&self.spec.room_in_off, &self.spec.room_in_idx, room).to_vec();
                if ins.is_empty() {
                    return Err("no-pipe");
                }
                let ordered =
                    Self::room_slice(&self.spec.room_ins_off, &self.spec.room_ins_idx, room);
                let chosen = ordered.iter().copied().find(|&pi| {
                    let p = &self.pipes[pi];
                    p.runs.last().copied() == Some(p.len as i32 - 1)
                });
                if let Some(pipe) = chosen {
                    self.men[man].a = self.take_last(pipe);
                    if op == 26 {
                        self.men[man].dir = self.pipes[pipe].turn;
                    }
                } else {
                    self.set_wait(man, WAIT_RU, ins);
                    return Ok(false);
                }
            }
            27 => {
                let pipe = self.nearest_in(cell, room);
                if pipe < 0 {
                    return Err("no-pipe");
                }
                self.men[man].bp = self.pipes[pipe as usize].vals.len() as i64;
            }
            28 => self.men[man].bp = self.men[man].a,
            29 => self.men[man].bp = self.men[man].bp.wrapping_sub(1),
            30 => {
                if self.men[man].bp > 0 {
                    self.men[man].dir = (dir as u8 + 1) & 3;
                }
            }
            31 => {
                if self.men[man].bp > 0 {
                    self.men[man].dir = (dir as u8 + 3) & 3;
                }
            }
            32 => self.men[man].bp >>= 1,
            33 => {
                self.men[man].dir = if self.men[man].bp & 1 != 0 {
                    (dir as u8 + 1) & 3
                } else {
                    (dir as u8 + 3) & 3
                };
            }
            35 => {
                if self.spec.semantics_version != 2 {
                    return Err("bad-op");
                }
                self.split_man(man)?;
                return Ok(false);
            }
            _ => return Err("bad-op"),
        }
        Ok(true)
    }

    fn move_legacy(&mut self, movers: Vec<usize>) -> Option<&'static str> {
        for man in movers {
            if !self.men[man].alive || self.men[man].halted {
                continue;
            }
            let cell = self.men[man].cell;
            let next = self.spec.step[self.men[man].dir as usize][cell];
            if next < 0 {
                return Some("wall");
            }
            let next = next as usize;
            let next_pos = self.spec.cellpos[next];
            let occupant = self.occupied[next_pos];
            if occupant >= 0 {
                let occupant = occupant as usize;
                self.men[man].halted = true;
                self.men[occupant].halted = true;
                self.runnable_discard(man);
                self.runnable_discard(occupant);
                self.clear_wait(occupant);
                continue;
            }
            self.occupied[self.spec.cellpos[cell]] = -1;
            self.men[man].cell = next;
            self.occupied[next_pos] = man as isize;
        }
        None
    }

    fn move_official(&mut self, movers: Vec<usize>) -> Option<&'static str> {
        let movers: Vec<usize> = movers
            .into_iter()
            .filter(|&i| self.men[i].alive && !self.men[i].halted && self.men[i].born != self.tick)
            .collect();
        let mut targets = HashMap::with_capacity(movers.len());
        let mut mover_mask = vec![false; self.men.len()];
        for &man in &movers {
            mover_mask[man] = true;
            let cell = self.men[man].cell;
            let next = self.spec.step[self.men[man].dir as usize][cell];
            if next < 0 {
                return Some("wall");
            }
            targets.insert(man, next as usize);
        }
        let mut doomed = vec![false; self.men.len()];
        for &man in &movers {
            let next_pos = self.spec.cellpos[targets[&man]];
            let occupant = self.occupied[next_pos];
            if occupant < 0 {
                continue;
            }
            let other = occupant as usize;
            if mover_mask[other] {
                let other_target = targets[&other];
                if self.spec.cellpos[other_target] == self.spec.cellpos[self.men[man].cell] {
                    doomed[man] = true;
                    doomed[other] = true;
                }
            } else if self.men[other].alive {
                doomed[man] = true;
                doomed[other] = true;
            }
        }
        let mut arrivals: HashMap<usize, Vec<usize>> = HashMap::new();
        for &man in &movers {
            arrivals.entry(targets[&man]).or_default().push(man);
        }
        for group in arrivals.values().filter(|group| group.len() > 1) {
            for &man in group {
                doomed[man] = true;
            }
        }
        for &man in &movers {
            let origin = self.spec.cellpos[self.men[man].cell];
            if self.occupied[origin] == man as isize {
                self.occupied[origin] = -1;
            }
        }
        for man in 0..doomed.len() {
            if doomed[man] {
                self.kill(man);
            }
        }
        for man in movers {
            if self.men[man].alive {
                let next = targets[&man];
                self.men[man].cell = next;
                self.occupied[self.spec.cellpos[next]] = man as isize;
            }
        }
        None
    }

    pub fn run<H: Hooks>(mut self, hooks: &mut H, max_ticks: i64) -> Result<RunOutput, H::Error> {
        let mut status = "tick-cap";
        let mut error = None;
        let mut hook_stopped = false;
        let mut output = Vec::new();
        let mut output_ticks = Vec::new();
        let mut frames = Vec::new();
        let mut frame_ticks = Vec::new();

        'ticks: for _ in 0..max_ticks {
            self.tick += 1;
            self.shift_pipes();

            if self.spec.output_pipe >= 0 {
                let pipe = self.spec.output_pipe as usize;
                let ready = {
                    let p = &self.pipes[pipe];
                    p.runs.last().copied() == Some(p.len as i32 - 1)
                };
                if ready {
                    let value = self.take_last(pipe);
                    output.push(value);
                    output_ticks.push(self.tick);
                    if hooks.on_output(value, self.tick)? {
                        hook_stopped = true;
                        break 'ticks;
                    }
                }
            }

            if self.spec.input_pipe >= 0 {
                let pipe = self.spec.input_pipe as usize;
                let open = self.pipes[pipe].runs.first().copied() != Some(0);
                if open {
                    if let Some(value) = hooks.pop_input()? {
                        self.put0(pipe, value);
                    }
                }
            }

            self.heap.clear();
            let runnable = std::mem::take(&mut self.runnable_buf);
            for man in runnable {
                if self.men[man].runnable {
                    self.men[man].runnable = false;
                    self.heap.push(Reverse(man));
                }
            }
            self.runnable_count = 0;
            self.in_execute = true;
            let mut movers = Vec::with_capacity(self.men.len());
            while let Some(Reverse(man)) = self.heap.pop() {
                if self.men[man].stamp == self.tick {
                    continue;
                }
                self.men[man].stamp = self.tick;
                self.current_man = man as isize;
                if !self.men[man].alive || self.men[man].halted {
                    continue;
                }
                match self.execute_man(man) {
                    Ok(true) => {
                        movers.push(man);
                        self.runnable_add(man);
                    }
                    Ok(false) => {}
                    Err(err) => {
                        error = Some(err);
                        break;
                    }
                }
            }
            self.in_execute = false;
            self.current_man = -1;
            if error.is_some() {
                break;
            }

            for display in 0..self.displays.len() {
                let sides = [
                    self.displays[display].addr,
                    self.displays[display].data,
                    self.displays[display].swap,
                ];
                for (side, pipe_i) in sides.into_iter().enumerate() {
                    if pipe_i < 0 {
                        continue;
                    }
                    let pipe = pipe_i as usize;
                    let ready = {
                        let p = &self.pipes[pipe];
                        p.runs.last().copied() == Some(p.len as i32 - 1)
                    };
                    if !ready {
                        continue;
                    }
                    let value = self.take_last(pipe);
                    let d = &mut self.displays[display];
                    match side {
                        0 => {
                            if value < 0 || value as usize >= d.w * d.h {
                                error = Some("display");
                                break;
                            }
                            d.cursor = value as usize;
                        }
                        1 => {
                            if !(0..=15).contains(&value) {
                                error = Some("display");
                                break;
                            }
                            d.next[d.cursor] = value as i8;
                            d.cursor = (d.cursor + 1) % (d.w * d.h);
                        }
                        _ => {
                            if value != 0 && value != 1 {
                                error = Some("display");
                                break;
                            }
                            d.current.clone_from(&d.next);
                            let frame: Vec<Vec<i8>> =
                                d.current.chunks(d.w).map(|row| row.to_vec()).collect();
                            frame_ticks.push(self.tick);
                            if hooks.on_frame(&frame, self.tick)? {
                                hook_stopped = true;
                            }
                            frames.push(frame);
                            if value == 0 {
                                d.next.fill(0);
                                d.cursor = 0;
                            }
                        }
                    }
                }
                if error.is_some() {
                    break;
                }
            }
            if error.is_some() {
                break;
            }

            error = if self.spec.semantics_version == 2 {
                self.move_official(movers)
            } else {
                self.move_legacy(movers)
            };
            if error.is_some() || hook_stopped {
                break;
            }
            if self.runnable_count == 0 && self.recv_wait_count == 0 && self.send_wait_count == 0 {
                let output_pending = self.spec.output_pipe >= 0
                    && !self.pipes[self.spec.output_pipe as usize].vals.is_empty();
                let display_pending = self
                    .spec
                    .disp_pipes
                    .iter()
                    .any(|&pi| !self.pipes[pi].vals.is_empty());
                if !output_pending && !display_pending {
                    status = "halted";
                    break;
                }
            }
        }
        if error.is_some() {
            status = "error";
        }
        Ok(self.finish(
            status,
            error,
            hook_stopped,
            output,
            output_ticks,
            frames,
            frame_ticks,
        ))
    }

    fn finish(
        self,
        status: &'static str,
        error: Option<&'static str>,
        hook_stopped: bool,
        output: Vec<i64>,
        output_ticks: Vec<i64>,
        frames: Vec<Vec<Vec<i8>>>,
        frame_ticks: Vec<i64>,
    ) -> RunOutput {
        RunOutput {
            status,
            error,
            hook_stopped,
            ticks: self.tick,
            output,
            output_ticks,
            frames,
            frame_ticks,
            mcell: self.men.iter().map(|m| m.cell).collect(),
            mdir: self.men.iter().map(|m| m.dir).collect(),
            ma: self.men.iter().map(|m| m.a).collect(),
            mb: self.men.iter().map(|m| m.b).collect(),
            mbp: self.men.iter().map(|m| m.bp).collect(),
            mhalt: self.men.iter().map(|m| u8::from(m.halted)).collect(),
            mwait: self.men.iter().map(|m| m.wait).collect(),
            malive: self.men.iter().map(|m| u8::from(m.alive)).collect(),
            p_runs: self.pipes.iter().map(|p| p.runs.clone()).collect(),
            p_vals: self
                .pipes
                .iter()
                .map(|p| p.vals.iter().copied().collect())
                .collect(),
            disp_cur: self.displays.iter().map(|d| d.current.clone()).collect(),
            disp_next: self.displays.iter().map(|d| d.next.clone()).collect(),
            disp_cursor: self.displays.iter().map(|d| d.cursor).collect(),
        }
    }
}
