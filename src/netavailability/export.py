"""Export: the publishable club and player tables of a run, for a chosen list of seasons.

  python -m netavailability.export --run DIR --out DIR [--seasons 2015/2016 ...] [--names FILE]

For each season and each variant (sideways adjustment on = the main tables, off = the robustness tables) it writes
  <out>/sideways_on|sideways_off/club_table_<yyyy-yyyy>.csv         byte-for-byte the run's club table
  <out>/sideways_on|sideways_off/club_table_paper_<yyyy-yyyy>.csv   byte-for-byte the run's worst-first club table
  <out>/sideways_on|sideways_off/player_table_<yyyy-yyyy>.csv       the run's player table with two changes:
      player         the verified name where the name is strongly verified, otherwise Sportmonks' name (the run's)
      name_verified  "yes" / "no", inserted after `player`
and <out>/export_manifest.csv (file, rows, sha256, verified names used).

A name is strongly verified when the names file (review/player_names_verified.csv under the data root: sm_player_id,
sm_name, verified_name, dob, source, status) has the player with a status other than UNVERIFIED and a source that holds
none of the markers of a weak match: "[name-only", "[DOB-only", "DOB_ONLY", "NAME_DOB_CONFLICT", "LABEL", "Q2_GIVEN".
Every other cell of the player table is written exactly as the run wrote it.
"""
import argparse, hashlib, shutil
from pathlib import Path
import pandas as pd

from . import common as fb
from . import settings

WEAK_MARKERS = ("[name-only", "[DOB-only", "DOB_ONLY", "NAME_DOB_CONFLICT", "LABEL", "Q2_GIVEN")
VARIANTS = {"sideways_on": "run_on", "sideways_off": "run_off"}


def strong_names(path):
    """sm_player_id (text) -> verified name, for the strongly verified rows of the names file."""
    d = pd.read_csv(path, dtype=str, keep_default_na=False)
    ok = (d.status != "UNVERIFIED") & ~d.source.apply(lambda s: any(m in s for m in WEAK_MARKERS)) & (d.verified_name != "")
    return dict(zip(d.sm_player_id[ok], d.verified_name[ok]))


def export_player_table(src, dst, names):
    """Rewrite one player table: the player column from the strong names, name_verified after it; every other cell as is."""
    t = pd.read_csv(src, dtype=str, keep_default_na=False)
    pid = t.player_id.str.replace(r"\.0$", "", regex=True)
    hit = pid.isin(names.keys())
    t.loc[hit, "player"] = pid[hit].map(names)
    t.insert(t.columns.get_loc("player") + 1, "name_verified", ["yes" if h else "no" for h in hit])
    t.to_csv(dst, index=False)
    return int(hit.sum()), len(t)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def export_run(run_on, run_off, out, seasons, log=print, names_file=None):
    names = strong_names(names_file or settings.inp("player_names_verified"))
    out = Path(out)
    rows = []
    for variant, rundir in (("sideways_on", Path(run_on)), ("sideways_off", Path(run_off))):
        if not (rundir / "runs.csv").exists():
            log(f"  export: {rundir} has no runs.csv; {variant} skipped")
            continue
        d = out / variant
        d.mkdir(parents=True, exist_ok=True)
        sfx = fb.run_sfx(rundir)
        for s in seasons:
            tg = fb.tag(s)
            for name in ("club_table", "club_table_paper"):
                src = rundir / tg / f"{name}_{tg}{sfx}.csv"
                dst = d / f"{name}_{tg}.csv"
                shutil.copyfile(src, dst)
                rows.append(dict(variant=variant, season=s, file=f"{variant}/{dst.name}", rows=sum(1 for _ in open(dst)) - 1,
                                 verified_names=None, sha256=sha(dst), source_sha256=sha(src)))
            src = rundir / tg / f"player_table_{tg}{sfx}.csv"
            dst = d / f"player_table_{tg}.csv"
            n_ver, n = export_player_table(src, dst, names)
            rows.append(dict(variant=variant, season=s, file=f"{variant}/{dst.name}", rows=n, verified_names=n_ver, sha256=sha(dst),
                             source_sha256=sha(src)))
    m = pd.DataFrame(rows)
    m.to_csv(out / "export_manifest.csv", index=False)
    pt = m[m.file.str.contains("player_table")]
    log(f"  export: {len(m)} files for {len(seasons)} seasons into {out}; player rows {int(pt.rows.sum())}, "
        f"verified names used {int(pt.verified_names.sum())}")
    return dict(files=len(m), seasons=list(seasons), player_rows=int(pt.rows.sum()), verified_names=int(pt.verified_names.sum()), out=str(out))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Export the publishable club and player tables of a run")
    ap.add_argument("--run", required=True, help="the run folder (with run_on/ and run_off/)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seasons", nargs="*", default=None, help="default: the settings' [export] seasons")
    ap.add_argument("--names", default=None, help="default: review/player_names_verified.csv under the data root")
    a = ap.parse_args(argv)
    run = Path(a.run)
    export_run(run / "run_on", run / "run_off", a.out, a.seasons or settings.export_seasons(), names_file=a.names)


if __name__ == "__main__":
    main()
