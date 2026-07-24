# Codex Worklog

## 2026-07-24

- Initialized the shared contest workspace and Codex handoff structure.
- Adapted external-storage and YT policy from neighboring `troll_farm` and
  `math_through_eml` projects.
- Corrected persistent `medium_data` mounting with a UUID-based, boot-safe
  `fstab` entry.
- Provisioned all five external-backed roots and validated writes through
  their repository symlinks.
- Installed and initialized Git LFS 3.0.2; verified project attribute routing.
- Imported the team credentials into the ignored `.env`, completed the normal
  browser/CAPTCHA login, and saved the bearer key without logging it.
- Added and live-validated the `icfpc-api` problem, clock, submission, wait,
  and guarded submit commands; documented them in `docs/api-tools.md`.
- Implemented and tested a 16-stage streaming Sort pipeline, submitted the
  exact validated source once, and received 25/25 server passes; see
  `reports/2026-07-24-sort-pipeline.md`.
- Added an immutable Sort variant catalogue and a geometry-only 92×92
  candidate that improves the local footprint-tick score by 23.23%.
- Submitted that candidate once; it passed 25/25 with server score
  38,830,462.08, improving the prior server score by 22.89%.
- Implemented a generated radix-packed History Lesson candidate at 89×88,
  preserved its variant metadata, and corrected footprint-only local scoring.
- Preserved its server parser rejection, corrected literal pairing locally,
  and submitted the fixed-slot 89×89 replacement successfully at score 7,921.
