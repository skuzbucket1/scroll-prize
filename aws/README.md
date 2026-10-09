# AWS spot workers (run from the Mac)

Burst the ink search onto EC2 spot GPUs next to the open data (us-east-1), then tear everything down.
The GPU box at home is CPU-bound (4 cores); each spot instance brings its own CPUs, and rendering reads the
CT straight from the Vesuvius Challenge S3 bucket in-region.

## Setup (once)
1. `cp aws/spot.env.example aws/spot.env` and fill in the profile, account id, VPC and public subnets
   (`aws/spot.env` and `aws/state/` are git-ignored).
2. `aws/spot_check.sh` — read-only: confirms the account, subnets and internet routes, spot quota, AMI and current spot prices.

## Proof of concept
`aws/poc.sh` — requests one g4dn.2xlarge spot instance, bootstraps it, renders the PHerc. 343 winning segment
(our positive control; mesh by Erwin Nieuwlaar, MIT) from S3, runs one ink map (ink_9um seed 42, depth +1), copies the
results to `data/aws-results/<instance id>/`, and terminates the instance. Expected: ~30–40 min, well under $1.
`aws/poc.sh --keep` leaves the instance up for inspection.

## Building blocks
| script | does |
|---|---|
| `spot_check.sh` | read-only readiness check (creates nothing) |
| `spot_up.sh` | key pair + security group (SSH from this Mac's IP only) if missing; spot request in the configured public subnets; waits for the bootstrap |
| `spot_push.sh` | copies Nieuwlaar's ink scripts (MIT) and `aws/remote/*` to the instance; lays out the four ink checkpoints |
| `spot_run.sh <name> <segment.tifxyz> <volume URL> <native µm> <models> <depths>` | uploads a segment, runs render + ink detached, waits |
| `spot_fetch.sh` | copies maps, previews, logs and timings back (not the renders) |
| `spot_down.sh [--all] [--cleanup]` | terminates the recorded instance (or all Project-tagged ones); `--cleanup` also deletes the SG and key pair |
| `spot_status.sh` | lists Project-tagged instances with the current spot price |

## Safety
- Every script checks the AWS account id against `EXPECTED_ACCOUNT_ID` and refuses otherwise.
- The instance powers itself off after `MAX_HOURS` (set in user-data at boot), and shutdown means terminate.
- Spot one-time requests with a price ceiling (`MAX_PRICE`); interruptions terminate, never stop.
- Root volume is deleted on termination; everything is tagged `Project=scroll-prize`; teardown only touches tagged resources.
- No AWS credentials on the instance: the CT is public over HTTPS and the models are public on Hugging Face.

## What runs on the instance
Ubuntu 24.04 Deep Learning Base GPU AMI (looked up via SSM at launch) → uv → villa `vesuvius` at a pinned commit
(`uv sync --extra models`, skipping the compiled VC package, which ink inference does not need) → VC3D Linux AppImage
from the villa GitHub release (for `vc_render_tifxyz`) → checkpoints from Hugging Face: ink_9um seeds 42/43
(Vesuvius Challenge), Hecate (Giorgio Angelotti), dense_native (Erwin Nieuwlaar).

## Fleet (many workers; prepped, run only on Ted's go-ahead)
`aws/fleet.sh N --yes [windings|all]` = stage flattened windings from the GPU box → split across N workers → launch them in
parallel → each runs render + four-model ink ensemble (depths 0,+1) per winding → poll + fetch every 5 min → final fetch →
terminate everything (also on failure or Ctrl-C). Results: `data/aws-results/fleet/<worker>/<segment>/ensemble/*.png`.

Step by step: `stage_segments.sh [--skip-done] [w… | all]` → `fleet_plan.sh N` (prints time and cost) →
`fleet_up.sh --yes [max_hours]` → `fleet_run.sh` → `fleet_status.sh` → `fleet_fetch.sh [--maps]` → `fleet_down.sh`.

Measured on the proof of concept (on-demand g4dn.2xlarge): bootstrap 2 min, render from S3 43 s, one ink map 157 s,
output identical to the home GPU box within 1/255. Estimate: ~35 min per winding for all four models at two depths.
