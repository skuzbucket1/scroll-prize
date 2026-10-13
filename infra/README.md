# infra: plumbing

Nothing here is a method. It moves data, runs machines, keeps backups and builds the site. All of it is in use.

- `box/`: helpers on the GPU box. `mirror_s3_v2.py` (mirror a public S3 prefix), `fetch_zarr.py` (fetch chosen
  pyramid levels), `status.sh`.
  - `sync_bin.py` runs on the Mac. On the box every script lives flat in `~/scroll-prizes/bin/`, so jobs and scripts that
    call each other never depend on this repo's folders. `sync_bin.py check` lists what differs between the two by file
    name. `pull` copies box versions into their repo folders. `push <names>` sends named scripts to the box.
- `aws/`: the EC2 GPU fleet (see its README). `spot.env` and `state/` are git-ignored. Every launch costs money and is
  decided run by run.
- `backup/`: `backup_r2.sh mac|box` backs up the critical set to private object storage (`r2_env.sh` reads the
  credentials, never prints them). `windings_of_interest.tsv` says which ink maps count. `catalog.py`,
  `results_db.py` and `catalog_report.py` build the artifact catalog in `docs/DATA_CATALOG.md`.
- `site/`: `build_site.py` turns `research/registry.json` into the site in `docs/`. `build_viewer.py` builds the
  private offline viewer of every inked winding. `pull_preview.sh` brings a preview from the box.
- `moved-2026-10-13.tsv`: old path → new path for every file moved when the repo was sorted by status.
