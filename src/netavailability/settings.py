"""Settings: reads config/settings.toml (or the file named by NETAV_CONFIG) and resolves every input path under the
data root. Nothing in the code holds an absolute path: input files are named here relative to the data root, rule
files relative to the settings file's folder.

Input data layout under the data root (README.md, "Input data"):
  sportmonks/standings.csv, league_seasons.csv, team_transfers.csv   shared Sportmonks tables (our CSV format)
  sportmonks/<set>/<name>.csv             the Sportmonks tables of each input set (early, mid, late)
  matchday/<set>/<name>.csv               the corrected matchday files (appearances, fixtures, events)
  matchday/identity_pending_rows.csv      matchday rows of premierleague.com persons whose identity was pending
  premierleague/                          premierleague.com matchday lists and id maps (presence check)
  transfermarkt/                          Transfermarkt squad pages, transfer histories and club ids
  review/                                 the dispute lists, verdicts and the other review inputs
"""
import os
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_SETTINGS = REPO / "config" / "settings.toml"

_cache = {}


def settings_file():
    return Path(os.environ.get("NETAV_CONFIG") or DEFAULT_SETTINGS).resolve()


def load():
    """The settings as a dict (cached per settings file)."""
    f = settings_file()
    if f not in _cache:
        with open(f, "rb") as fh:
            _cache[f] = tomllib.load(fh)
    return _cache[f]


def _resolve(p):
    p = Path(p)
    return p if p.is_absolute() else (settings_file().parent / p).resolve()


def data_roots():
    """The data roots, searched in order: the settings' data_root (a folder or a list of folders), or NETAV_DATA_ROOT
    (folders separated by the path separator)."""
    env = os.environ.get("NETAV_DATA_ROOT")
    if env:
        return [Path(x).resolve() for x in env.split(os.pathsep) if x]
    v = load()["data_root"]
    return [_resolve(x) for x in ([v] if isinstance(v, str) else v)]


def data_root():
    """The first data root (where new input files are looked for first)."""
    return data_roots()[0]


def output_root():
    return _resolve(load().get("output_root", "../output"))


def data_path(*parts):
    """A path under the data roots: the first root that holds it, else under the first root."""
    for r in data_roots():
        p = r.joinpath(*parts)
        if p.exists() or p.is_symlink():
            return p
    return data_roots()[0].joinpath(*parts)


def rel_data(p):
    """A path relative to the data root that holds it (for records)."""
    p = Path(p)
    for r in data_roots():
        try:
            return str(p.relative_to(r))
        except ValueError:
            pass
    return str(p)


def rule_file(name):
    """One of the rule files of the settings' [rule_files] table (kept next to the settings file)."""
    return _resolve(load()["rule_files"][name])


def seasons():
    return list(load()["seasons"])


def export_seasons():
    return list(load().get("export", {}).get("seasons", seasons()))


def run_config():
    """The flat run configuration the stages read: constants, rule switches, rule files (absolute paths), jobs."""
    s = load()
    cfg = dict(s["constants"])
    cfg.update(s["rules"])
    cfg.update({k: str(rule_file(k)) for k in s["rule_files"]})
    cfg["jobs"] = s.get("jobs", 12)
    return cfg


def child_env():
    """Environment entries that make a child process read the same settings and data root."""
    return {"NETAV_CONFIG": str(settings_file()), "NETAV_DATA_ROOT": os.pathsep.join(str(r) for r in data_roots())}


# ------------------------------------------------------------------ named inputs under the data root
INPUTS = {
    "standings": "sportmonks/standings.csv",                       # Premier League standings, one row per club-season
    "league_seasons": "sportmonks/league_seasons.csv",             # Premier League season ids
    "club_season_values": "transfermarkt/club_season_values.csv",  # squad market value per club-season (1 July)
    "tm_club_ids_primary": "transfermarkt/club_ids_primary.csv",   # Sportmonks team id -> Transfermarkt club id
    "tm_club_ids_secondary": "transfermarkt/club_ids_secondary.csv",  # the same, for clubs the primary file lacks
    "tm_squads_2014_2022": "transfermarkt/squads_2014_2022.csv",   # squad pages 2014/15-2021/22 (one file)
    "identity_pending_rows": "matchday/identity_pending_rows.csv", # matchday rows of persons whose identity was pending
    "verdicts_round1": "review/verdicts/round1.csv",               # first verdict round (2018/19-2025/26 disputes)
    "verdicts_round2": "review/verdicts/round2.csv",               # second round (re-settles first-round UNRESOLVED cases)
    "verdicts_round3": "review/verdicts/round3.csv",               # third round (disputes over the bar, both lists)
    "verdicts_gapfill": "review/verdicts/gapfill.csv",             # verdicts on over-the-bar gap-fill cases
    "gapfill_verdict_cases": "review/verdicts/gapfill_cases.csv",  # gap-fill verdict case -> member dispute ids
    "senior_second_source": "review/verdicts/senior_second_source.csv",  # second source on senior records
    "gapfill_cases": "review/gapfill/cases.csv",                   # never-checked gap-fill cases, sized
    "gapfill_size_detail": "review/gapfill/size_detail.csv",
    "unknown_origin_resolved": "review/unknown_origin_resolved.csv",  # unknown arrival origins resolved from Transfermarkt
    "senior_record": "review/senior_record.csv",                   # senior record before arrival (Transfermarkt)
    "player_names_verified": "review/player_names_verified.csv",   # player names checked against premierleague.com / Transfermarkt
}


def inp(key):
    """A named input file or folder under the data root (see INPUTS)."""
    return data_path(*INPUTS[key].split("/"))
