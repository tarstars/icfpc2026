# Codex Validation

Updated: 2026-07-24

## Environment observations

- Repository branch: `main`, initially at commit `a32ef8c`.
- `medium_data` is mounted at `/media/tarstars/medium_data` as ext4.
- Observed free space at initialization: approximately 427 GiB.
- Git LFS 3.0.2 is installed from the Ubuntu Jammy repository.
- Non-interactive sudo is unavailable.

## Validation performed

- `python3 -m py_compile scripts/check_external_storage.py` — passed.
- `python3 scripts/check_external_storage.py --required-free-gib 1` — exited
  with status 2 as designed, naming the absent physical project root and all
  five missing symlink targets.
- `git diff --check` — passed.
- `git check-ignore -v` — confirmed all five external-backed symlinks are
  ignored by their explicit root rules.
- Repository layout audit — confirmed no files were added to `claude/`.
- `/etc/fstab` verification — zero parse errors; the `medium_data` UUID
  resolves to `/dev/sda1`, with `nofail`, `nosuid`, and `nodev` active in the
  persisted configuration.
- `python3 scripts/check_external_storage.py --required-free-gib 400` — passed
  for all five symlinks with `457867780096` free bytes.
- Create/resolve/delete probes through every logical bulk root — passed; every
  probe resolved beneath
  `/media/tarstars/medium_data/database/icfpc2026`.
- `git lfs install` — passed and updated the user-level Git hooks.
- `git lfs env` and `git lfs status` — passed for this repository.
- `git check-attr` — confirmed `.pt` and `.zip` use the LFS filter while
  ordinary source such as `.cpp` remains normal text.

## Pending validation

- No remaining initialization validation.

No YT connectivity, pool availability, or credentials have been validated for
this project.
