"""Shared helpers: season sets, input sets, the per-season compute command, a parallel season runner and table access.

Run-folder contract (every stage, the calibration and the analyses read it):
  <run-dir>/runs.csv                                       season, input_set, rc, seconds, command (JSON list)
  <run-dir>/<season-tag>/<name>_<season-tag><SFX>.csv      the compute's tables; SFX = the --out-suffix of the command
  <run-dir>/compute_log_<season-tag>.txt
Input folders: <inputs>/<set>/<name>.csv for each input set, plus the shared Sportmonks tables (SHARED).
"""
import hashlib, json, os, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import pandas as pd

from . import settings

HERE = Path(__file__).resolve().parent
COMPUTE = HERE / "compute.py"
PY = sys.executable

SET7 = ["2018/2019", "2019/2020", "2021/2022", "2022/2023", "2023/2024", "2024/2025", "2025/2026"]
SET11 = ["2014/2015", "2015/2016", "2016/2017", "2017/2018"] + SET7
ROBUST = "2020/2021"
FILES = ["appearances", "fixtures", "events", "teams", "squads", "transfers", "contracts", "contracts_no_dated_record"]
MATCHDAY = ["appearances", "fixtures", "events"]
# input set -> seasons computed from it (each set is one Sportmonks pull: early = the 2005-2017 history pull,
# mid = the 2016/17-2017/18 pull, late = the 2018/19-2025/26 pull)
SETS = {"early": ["2014/2015", "2015/2016", "2016/2017"],
        "mid": ["2017/2018"],
        "late": [f"{y}/{y + 1}" for y in range(2018, 2026)]}
SET_OF = {s: k for k, ss in SETS.items() for s in ss}
PLACEHOLDER_BASE, TM_PLAYER_BASE = 800000000, 900000000
VALID_TYPES = {218, 219, 9688, 220}


class Stop(SystemExit):
    """An integrity failure: the run stops."""


def tag(s):
    return s.replace("/", "-")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def now():
    return datetime.now().strftime("%H:%M:%S")


def sm_file(set_name, name):
    """An original Sportmonks input file of an input set."""
    return settings.data_path("sportmonks", set_name, f"{name}.csv")


def spec_flags(cfg, sideways):
    """The method's constants as compute flags."""
    f = ["--L", str(cfg.get("L", 12)), "--mover-delta", str(cfg.get("mover_delta", "0.10")),
         "--tier1-fill", str(cfg.get("tier1_fill", 0.5)), "--tier2-fill", str(cfg.get("tier2_fill", 0.35)),
         "--tier3-fill", str(cfg.get("tier3_fill", 0.25)), "--data-club-fill", str(cfg.get("data_club_fill", 0.45)),
         "--youth-fill", str(cfg.get("youth_fill", 0)), "--unknown-fill", str(cfg.get("unknown_fill", 0.35)),
         "--allowance-genuine-only", "--academy-gate", "any", "--trace-all"]
    if sideways:
        f += ["--sideways-adjust", str(cfg.get("sideways_adjust", 0.15))]
    return f


def compute_cmd(season, inputs_dir, outdir, out_sfx, cfg, sideways, keeper=None, overrides=None, window_table=None,
                retention=None, first_team_first=True, compute=None, in_sfx=""):
    cmd = [PY, str(compute or COMPUTE), "--season", season, "--pulls", str(inputs_dir), "--suffix", in_sfx, "--meta-suffix", in_sfx,
           "--out", str(outdir), "--out-suffix", out_sfx] + spec_flags(cfg, sideways)
    cmd += ["--keeper-override", str(keeper or settings.rule_file("keeper_overrides"))]
    if overrides:
        cmd += ["--origin-overrides", str(overrides)]
    if window_table:
        cmd += ["--window-closes", str(window_table)]
    if retention:
        cmd += ["--retention-overrides", str(retention)]
    if first_team_first:
        cmd += ["--first-team-first"]
    return cmd


def module_cmd(module, *args):
    """A command that runs one of this package's modules in a fresh interpreter."""
    return [PY, "-m", f"netavailability.{module}", *map(str, args)]


def child_env(**extra):
    """The environment of a child process: this package importable, the same settings file."""
    env = dict(os.environ, **{k: str(v) for k, v in extra.items()})
    src = str(HERE.parent)
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env.update(settings.child_env())
    return env


def run_seasons(jobs, rundir, max_workers=12, log=print):
    """jobs: list of dict(season, input_set, cmd). Runs each compute in its own folder <rundir>/<season-tag>/ and writes
    <rundir>/runs.csv. Raises Stop when a compute fails."""
    rundir = Path(rundir)
    rundir.mkdir(parents=True, exist_ok=True)

    def one(j):
        d = rundir / tag(j["season"])
        if d.exists() and any(d.iterdir()):
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        r = subprocess.run(j["cmd"], capture_output=True, text=True, cwd=HERE)
        (rundir / f"compute_log_{tag(j['season'])}.txt").write_text(r.stdout + ("\nSTDERR\n" + r.stderr if r.stderr else ""))
        return dict(season=j["season"], input_set=j.get("input_set", ""), rc=r.returncode, seconds=round(time.time() - t0, 1),
                    command=json.dumps(j["cmd"]))
    with ThreadPoolExecutor(max_workers) as ex:
        res = list(ex.map(one, jobs))
    pd.DataFrame(res).to_csv(rundir / "runs.csv", index=False)
    bad = [r["season"] for r in res if r["rc"] != 0]
    if bad:
        raise Stop(f"STOP: compute failed for {bad}; see compute_log_* in {rundir}")
    log(f"  ran {len(res)} seasons into {rundir.name}: " + ", ".join(f"{r['season'][2:4]}/{r['season'][7:9]} {r['seconds']}s" for r in res))
    return res


def run_sfx(rundir):
    """The --out-suffix of a run folder (from runs.csv)."""
    c = json.loads(pd.read_csv(Path(rundir) / "runs.csv").command.iloc[0])
    return c[c.index("--out-suffix") + 1]


def table(rundir, name, season, sfx=None, **kw):
    sfx = sfx or run_sfx(rundir)
    return pd.read_csv(Path(rundir) / tag(season) / f"{name}_{tag(season)}{sfx}.csv", **kw)


SHARED = ["standings.csv", "league_seasons.csv", "team_transfers.csv"]      # Sportmonks tables every season reads


def link_shared(d):
    for name in SHARED:
        dst = Path(d) / name
        if not (dst.exists() or dst.is_symlink()):
            os.symlink(settings.data_path("sportmonks", name), dst)


def norm_club(name):
    import re
    s = str(name).lower().replace("&", "and").replace(".", "")
    s = re.sub(r"\butd\b", "united", s)
    return " ".join(t for t in s.split() if t not in ("afc", "fc", "cf"))
