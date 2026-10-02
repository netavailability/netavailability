"""Check C3, presence: every premierleague.com named player-match is a named row in the compute's input.

Rule: every premierleague.com named player-match (starter or substitute on the matchday list) must be a named row
(player_id present) in the appearances file the compute reads, except the rows listed in identity_pending_rows.csv
(persons whose identity was pending, whose rows stay as Sportmonks has them).

premierleague.com side: the matchday lists of three parts (premierleague/part_a|b|c, each covering a set of seasons,
WORKER_OF), with each part's fixture map, its person id -> Sportmonks id mapping and its unmatched persons.
Compute side: one appearances file per input set, early (2014/15-2016/17 and the 2013/14 look-back), mid (2017/18),
late (2018/19-2025/26). Each season is checked against the set it is computed from.

A person on a premierleague.com team-match list is
  matched   when a Sportmonks id mapped to him is the player_id of a row of that team-match (fixture_id, team_id) in ours;
  missing   otherwise, with reason
    IDENTITY_PENDING             the person and fixture are in identity_pending_rows.csv AND the pending Sportmonks row is
                                 in ours
    IDENTITY_PENDING_ROW_ABSENT  listed pending, but the pending Sportmonks row is not in ours           (counts against PASS)
    UNMATCHED_NO_PENDING         the person has no Sportmonks id (the part's unmatched list) and no pending row  (counts)
    MAPPED_NULL_ID_ROW           mapped; no named row, but a null-id row of the team-match carries his name     (counts)
    MAPPED_NO_ROW                mapped; no row of his in the team-match                                        (counts)
    NO_ROWS_FOR_TEAM_MATCH       ours has no row at all for the team-match                                      (counts)
Extra in ours = named rows of a listed team-match whose id belongs to nobody on the list and is not a pending row.
Duplicates (a second row of a matched person) and null-id rows are counted in their own columns.
PASS for a season = 0 missing outside IDENTITY_PENDING.

CLI:  python -m netavailability.presence --inputs DIR --out DIR [--appearances-pattern PAT]
  PAT is relative to --inputs; placeholder {set} = early|mid|late; * allowed (must resolve to exactly one file).
Writes <out>/c3_presence.csv (one row per season), <out>/c3_missing.csv (every missing person-match),
<out>/c3_extra.csv (every extra named row in ours). main(argv=None) returns the per-season DataFrame.
"""
import argparse, re, unicodedata
from collections import defaultdict
from pathlib import Path
import pandas as pd

from . import common as fb
from . import settings

PATTERN = "{set}/appearances.csv"
PENDING_SET = {"early": "hist", "mid": "1617", "late": "v3h"}     # input set -> its label in identity_pending_rows.csv
LOOKBACK = "2013/14"
CHECKED = [f"{y}/{str(y + 1)[2:]}" for y in range(2014, 2026)]     # the premierleague.com files' season spelling
SET_OF = {s: fb.SET_OF[f"{s[:4]}/{s[:2]}{s[5:]}"] for s in CHECKED}
SET_OF[LOOKBACK] = "early"
COUNTS = ["IDENTITY_PENDING_ROW_ABSENT", "UNMATCHED_NO_PENDING", "MAPPED_NULL_ID_ROW", "MAPPED_NO_ROW", "NO_ROWS_FOR_TEAM_MATCH"]
WORKER_OF = {"2018/19": "A", "2019/20": "A", "2021/22": "A", "2022/23": "A",
             "2020/21": "B", "2023/24": "B", "2024/25": "B", "2025/26": "B",
             "2013/14": "C", "2014/15": "C", "2015/16": "C", "2016/17": "C", "2017/18": "C"}
SM_SEASON_ID = {"2013/14": 3, "2014/15": 12, "2015/16": 10, "2016/17": 13, "2017/18": 6397, "2018/19": 12962,
                "2019/20": 16036, "2020/21": 17420, "2021/22": 18378, "2022/23": 19734, "2023/24": 21646,
                "2024/25": 23614, "2025/26": 25583}


def part_dir(w):
    return settings.data_path("premierleague", f"part_{w.lower()}")


def sfile(p):
    return p.replace("/", "-")


# ---------------------------------------------------------------- premierleague.com files of each part
def fixture_map(w):
    """One row per Sportmonks fixture: season, sm_fixture_id, pl_fixture_id, {pl_team_id: sm_team_id}."""
    fm = pd.read_csv(part_dir(w) / "fixture_map.csv")
    if w == "A":
        fm = fm.rename(columns={"fixture_id": "sm_fixture_id"})
    elif w == "B":
        fm = fm.rename(columns={"pl_home_team_id": "pl_home_id", "pl_away_team_id": "pl_away_id"})
    else:
        fm = fm.rename(columns={"fixture_id": "sm_fixture_id"})
    return fm[["season", "sm_fixture_id", "pl_fixture_id", "home_id", "away_id", "pl_home_id", "pl_away_id"]]


def lineups(w, season):
    """premierleague.com list for one season, normalised: sm_fixture_id, sm_team_id, pl_person_id, name, dob, role,
    on/off/dismissal (half, secs), dismissed, card_codes, dis_code (code of the dismissing card)."""
    L = pd.read_csv(part_dir(w) / f"lineups_{sfile(season)}.csv")
    fm = fixture_map(w)
    fm = fm[fm.season == season]
    t = {}
    for r in fm.itertuples():
        t[(int(r.sm_fixture_id), int(r.pl_home_id))] = int(r.home_id)
        t[(int(r.sm_fixture_id), int(r.pl_away_id))] = int(r.away_id)
    L["sm_team_id"] = [t[(int(a), int(b))] for a, b in zip(L.sm_fixture_id, L.pl_team_id)]
    out = []
    for r in L.itertuples():
        codes = r.card_codes if isinstance(r.card_codes, str) else ""
        dis_code = None
        if r.dismissed == "Y":
            dis_code = dismissing_code(w, codes, r)
        out.append(dict(sm_fixture_id=int(r.sm_fixture_id), sm_team_id=int(r.sm_team_id), pl_fixture_id=int(r.match),
                        pl_person_id=int(r.pl_person_id), name=r.name, dob=r.dob, role=r.role,
                        on=_t(r.on_half, r.on_secs) if r.role == "sub" else None,
                        off=_t(r.off_half, r.off_secs), dismissed=r.dismissed == "Y",
                        dis=_t(r.dismissal_half, r.dismissal_secs) if r.dismissed == "Y" else None,
                        card_codes=codes, dis_code=dis_code))
    return out


def _t(h, s):
    if pd.isna(h) or h == "":
        return None
    return (int(float(h)), int(float(s)))


def dismissing_code(w, codes, r):
    """Code of the card that dismissed: the earlier of the first R-containing card and the second card."""
    if w == "C":                       # 'Y;YR' — codes in time order, no times
        cs = [c for c in codes.split(";") if c]
    elif w == "A":                     # 'Y@2:4020;YR@2:5100' sorted by (half, secs)
        cs = [c.split("@")[0] for c in codes.split(";") if c]
    else:                              # 'Y@1:840|YR@2:5100' sorted
        cs = [c.split("@")[0] for c in codes.split("|") if c]
    if not cs:
        return None
    idx = [i for i, c in enumerate(cs) if "R" in c]
    cand = ([idx[0]] if idx else []) + ([1] if len(cs) >= 2 else [])
    return cs[min(cand)] if cand else None


def mapping(w):
    m = pd.read_csv(part_dir(w) / "mapping.csv")
    d = {}
    for a, b in zip(m.pl_person_id, m.sm_player_id):
        d.setdefault(int(a), []).append(int(b))
    return d


def unmatched_pairs(w):
    """pl_person_id -> list of (sm_id, basis, sm_name, sm_dob, score) from the part's unmatched.csv."""
    u = pd.read_csv(part_dir(w) / "unmatched.csv", dtype=str).fillna("")
    out = {}
    for r in u.itertuples():
        pid = int(r.pl_person_id)
        lst = out.setdefault(pid, [])
        if w == "A":
            for c in [x for x in r.name_only_candidates.split(";") if x]:
                sid, nm, dob = c.split(":", 2)
                lst.append((int(sid), "NAME_ONLY", nm, dob, None))
            for c in [x for x in r.dob_only_candidates.split(";") if x]:
                sid, nm, dob = (c.split(":", 2) + ["", ""])[:3]
                lst.append((int(sid), "DOB_ONLY", nm, dob or r.dob, None))
        elif w == "B":
            for c in [x.strip() for x in r.name_candidates.split("|") if x.strip()]:
                sid, rest = c.split(" ", 1)
                nm, rest2 = rest.rsplit(" score", 1)
                sc, dob = rest2.split(" dob=")
                lst.append((int(sid), "NAME_ONLY", nm, "" if dob == "None" else dob, int(sc)))
            for c in [x.strip() for x in r.dob_candidates.split("|") if x.strip()]:
                sid, nm = c.split(" ", 1)
                lst.append((int(sid), "DOB_ONLY", nm, r.dob, None))
        else:
            for c in [x.strip() for x in r.name_only_cands.split("|") if x.strip()]:
                sid, rest = c.split(" ", 1)
                nm, dob = rest.rsplit(" dob=", 1)
                lst.append((int(sid), "NAME_ONLY", nm, "" if dob == "None" else dob, None))
            for c in [x.strip() for x in r.dob_only_cands.split("|") if x.strip()]:
                sid, nm = c.split(" ", 1)
                lst.append((int(sid), "DOB_ONLY", nm, r.dob, None))
    # de-duplicate, keep order (a person can be listed once per season)
    return {k: list(dict.fromkeys(v)) for k, v in out.items()}


def norm_tokens(name):
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    return {t for t in re.split(r"[^a-z]+", s) if len(t) > 1}


def resolve(inputs, pattern, key):
    rel = pattern.format(set=key)
    hits = sorted(Path(inputs).glob(rel))
    if len(hits) != 1:
        raise fb.Stop(f"STOP: C3 appearances file for set {key}: '{rel}' under {inputs} resolves to {len(hits)} files")
    return hits[0]


def part_fixture_info(w):
    """sm_fixture_id -> (date, 'Home v Away') from the part's fixture map (column names differ per part)."""
    fm = pd.read_csv(part_dir(w) / "fixture_map.csv", dtype=str, keep_default_na=False)
    fid = "sm_fixture_id" if "sm_fixture_id" in fm.columns else "fixture_id"
    dcol = "uk_date" if "uk_date" in fm.columns else "date"
    return {int(f): (d[:10], f"{h} v {a}") for f, d, h, a in zip(fm[fid], fm[dcol], fm.pl_home, fm.pl_away)}


def load_apps(path):
    a = pd.read_csv(path, usecols=["fixture_id", "season_id", "team_id", "player_id", "player", "role", "played", "date"],
                    dtype=str, keep_default_na=False)
    a["fixture_id"] = a.fixture_id.astype(float).astype(int)
    a["season_id"] = a.season_id.astype(float).astype(int)
    a["team_id"] = a.team_id.astype(float).astype(int)
    return a                                       # player_id stays text ("" = null id; "1078.0" in the 1617 file)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--inputs", required=True, help="inputs folder (<inputs>/<set>/appearances.csv)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--appearances-pattern", default=None, help="relative to --inputs; {set}, * allowed")
    ap.add_argument("--pending", default=str(settings.inp("identity_pending_rows")))
    ap.add_argument("--sets", nargs="*", default=list(PENDING_SET), help="input sets to check (default all)")
    args = ap.parse_args(argv)
    pattern = args.appearances_pattern or PATTERN
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print("C3 presence")
    print(f"  inputs {args.inputs} | pattern {pattern} | pending {args.pending}")

    files = {k: resolve(args.inputs, pattern, k) for k in PENDING_SET if k in args.sets}
    APPS = {}
    for k, p in files.items():
        APPS[k] = load_apps(p)
        print(f"  set {k}: {p.name} ({len(APPS[k])} rows, sha256 {fb.sha(p)[:12]})")
    R = pd.read_csv(args.pending)
    pend = defaultdict(dict)        # pending-file set label -> (sm_fixture_id, pl_person_id) -> pending Sportmonks id
    for r in R.itertuples():
        pend[str(r.set)][(int(r.sm_fixture_id), int(r.pl_person_id))] = int(r.sm_player_id)
    print(f"  identity-pending rows: {len(R)} ({ {k: len(v) for k, v in pend.items()} })")
    seasons = [x for x in [LOOKBACK] + CHECKED if SET_OF[x] in files]
    parts = sorted({WORKER_OF[x] for x in seasons})
    MAP = {w: mapping(w) for w in parts}
    UNM = {w: unmatched_pairs(w) for w in parts}
    FXI = {w: part_fixture_info(w) for w in parts}

    summary, missing, extra = [], [], []
    for s in seasons:
        w, key = WORKER_OF[s], SET_OF[s]
        a = APPS[key]
        P = pend.get(PENDING_SET[key], {})
        lists = defaultdict(list)
        for p in lineups(w, s):
            lists[(p["sm_fixture_id"], p["sm_team_id"])].append(p)
        fx_scope = {f for f, _ in lists}
        sub = a[a.fixture_id.isin(fx_scope)]
        named, nullrows, names = defaultdict(list), defaultdict(list), {}
        for f, t, ps, nm, role in zip(sub.fixture_id, sub.team_id, sub.player_id, sub.player, sub.role):
            if ps == "":
                nullrows[(f, t)].append(nm)
            else:
                pid = int(float(ps))
                named[(f, t)].append(pid)
                names[(f, t, pid)] = (nm, role)
        ours_season_fx = set(a[a.season_id == SM_SEASON_ID[s]].fixture_id)
        n = dict(pl=0, matched=0, pending=0, dup=0, extra=0, null=0)
        n.update({c: 0 for c in COUNTS})
        for (f, t), plist in sorted(lists.items()):
            ids_here = named.get((f, t), [])
            idset = set(ids_here)
            nulls = nullrows.get((f, t), [])
            n["null"] += len(nulls)
            date, match = FXI[w].get(f, ("", ""))
            used = set()
            for p in plist:
                n["pl"] += 1
                pid = p["pl_person_id"]
                sm_ids = MAP[w].get(pid, [])
                hit = [i for i in sm_ids if i in idset]
                if hit:
                    n["matched"] += 1
                    used.update(hit)
                    n["dup"] += sum(ids_here.count(i) for i in hit) - 1
                    continue
                detail, sm_out = "", ";".join(map(str, sm_ids))
                pending_id = P.get((f, pid))
                if pending_id is not None:
                    if pending_id in idset:
                        reason = "IDENTITY_PENDING"
                        used.add(pending_id)
                        detail = f"pending Sportmonks row {pending_id} {names[(f, t, pending_id)][0]} present"
                    else:
                        reason = "IDENTITY_PENDING_ROW_ABSENT"
                        detail = f"pending Sportmonks id {pending_id} has no row in this team-match"
                    sm_out = sm_out or str(pending_id)
                elif not ids_here and not nulls:
                    reason = "NO_ROWS_FOR_TEAM_MATCH"
                elif not sm_ids:
                    reason = "UNMATCHED_NO_PENDING"
                    cands = UNM[w].get(pid, [])
                    detail = "candidates: " + ("; ".join(f"{c[0]} {c[2]} ({c[1]})" for c in cands) if cands else "none")
                    here = [c[0] for c in cands if c[0] in idset]
                    if here:
                        detail += f" | candidate row(s) in ours: {here}"
                else:
                    tk = norm_tokens(p["name"])
                    nm_hit = [x for x in nulls if tk & norm_tokens(x)]
                    if nm_hit:
                        reason = "MAPPED_NULL_ID_ROW"
                        detail = "null-id row(s) in ours: " + "; ".join(nm_hit)
                    else:
                        reason = "MAPPED_NO_ROW"
                        if nulls:
                            detail = "other null-id row(s) in this team-match: " + "; ".join(map(str, nulls))
                if reason == "IDENTITY_PENDING":
                    n["pending"] += 1
                else:
                    n[reason] += 1
                missing.append(dict(season=s, scope="look-back" if s == LOOKBACK else "checked", input_set=key, date=date,
                                    match=match, team=plist_team(w, s, f, t, TEAMS), pl_fixture_id=p["pl_fixture_id"],
                                    sm_fixture_id=f, sm_team_id=t, pl_person_id=pid, pl_name=p["name"], pl_dob=p["dob"],
                                    pl_role=p["role"], pl_played=int(p["role"] == "starter" or p["on"] is not None),
                                    sm_player_id=sm_out, reason=reason,
                                    counts_against_pass=reason != "IDENTITY_PENDING", detail=detail))
            for i in ids_here:
                if i not in used:
                    n["extra"] += 1
                    used_by = [k for k, v in MAP[w].items() if i in v]
                    nm, role = names[(f, t, i)]
                    extra.append(dict(season=s, scope="look-back" if s == LOOKBACK else "checked", input_set=key, date=date,
                                      match=match, team=plist_team(w, s, f, t, TEAMS), sm_fixture_id=f, sm_team_id=t,
                                      sm_player_id=i, sm_name=nm, sm_role=role,
                                      note=("id maps to premierleague.com person(s) not on this list: " + ";".join(map(str, used_by)))
                                      if used_by else "id not mapped to any premierleague.com person"))
        miss = n["pending"] + sum(n[c] for c in COUNTS)
        assert n["pl"] == n["matched"] + miss
        outside = miss - n["pending"]
        no_rows = len([1 for k in lists if not named.get(k) and not nullrows.get(k)])
        summary.append(dict(season=s, scope="look-back" if s == LOOKBACK else "checked", input_set=key, part=w,
                            appearances_file=files[key].name, pl_fixtures=len(fx_scope), pl_team_matches=len(lists),
                            pl_named_player_matches=n["pl"], matched_in_ours=n["matched"], missing=miss,
                            missing_identity_pending=n["pending"], missing_unmatched_no_pending=n["UNMATCHED_NO_PENDING"],
                            missing_mapped_null_id_row=n["MAPPED_NULL_ID_ROW"], missing_mapped_no_row=n["MAPPED_NO_ROW"],
                            missing_identity_row_absent=n["IDENTITY_PENDING_ROW_ABSENT"],
                            missing_no_rows_for_team_match=n["NO_ROWS_FOR_TEAM_MATCH"], missing_outside_identity_pending=outside,
                            extra_in_ours=n["extra"], duplicate_rows_in_ours=n["dup"], null_id_rows_in_ours=n["null"],
                            team_matches_without_rows_in_ours=no_rows,
                            our_season_fixtures_not_on_plcom=len(ours_season_fx - fx_scope),
                            result="PASS" if outside == 0 else "REPORT"))
        print(f"  {'PASS  ' if outside == 0 else 'REPORT'} C3 {s}{' (look-back)' if s == LOOKBACK else ''} [{key}]: premierleague.com "
              f"{n['pl']}, matched {n['matched']}, missing {miss} (identity-pending {n['pending']}, unmatched no pending "
              f"{n['UNMATCHED_NO_PENDING']}, mapped null-id row {n['MAPPED_NULL_ID_ROW']}, mapped no row {n['MAPPED_NO_ROW']}, "
              f"other {n['IDENTITY_PENDING_ROW_ABSENT'] + n['NO_ROWS_FOR_TEAM_MATCH']}); extra in ours {n['extra']}, "
              f"duplicates {n['dup']}, null-id rows {n['null']}")

    S = pd.DataFrame(summary)
    S.to_csv(out / "c3_presence.csv", index=False)
    mcols = ["season", "scope", "input_set", "date", "match", "team", "pl_fixture_id", "sm_fixture_id", "sm_team_id",
             "pl_person_id", "pl_name", "pl_dob", "pl_role", "pl_played", "sm_player_id", "reason", "counts_against_pass", "detail"]
    pd.DataFrame(missing, columns=mcols).to_csv(out / "c3_missing.csv", index=False)
    ecols = ["season", "scope", "input_set", "date", "match", "team", "sm_fixture_id", "sm_team_id", "sm_player_id",
             "sm_name", "sm_role", "note"]
    pd.DataFrame(extra, columns=ecols).to_csv(out / "c3_extra.csv", index=False)
    chk = S[S.scope == "checked"]
    bad = chk[chk.result != "PASS"]
    lb = S[S.scope == "look-back"]
    print(f"  C3 overall: {'PASS' if bad.empty else 'REPORT'} — {len(chk) - len(bad)}/{len(chk)} seasons PASS; "
          f"missing outside identity-pending {int(chk.missing_outside_identity_pending.sum())}"
          + (f"; look-back 2013/14 {lb.result.iloc[0]} ({int(lb.missing_outside_identity_pending.iloc[0])} outside identity-pending)" if len(lb) else ""))
    print(f"  wrote {out / 'c3_presence.csv'}, c3_missing.csv ({len(missing)} rows), c3_extra.csv ({len(extra)} rows)")
    return S


# team name of a premierleague.com team-match: the lineup files carry it ('team'); lineups() drops the column, so it is
# read once per season from the part's file, keyed as lineups() keys the list (sm_fixture_id, pl_team_id -> sm team).
class _Teams(dict):
    def get_name(self, w, s, f, t):
        if (w, s) not in self:
            L = pd.read_csv(part_dir(w) / f"lineups_{sfile(s)}.csv",
                            usecols=["sm_fixture_id", "pl_team_id", "team"]).drop_duplicates()
            fm = fixture_map(w)
            fm = fm[fm.season == s]
            tm = {}
            for r in fm.itertuples():
                tm[(int(r.sm_fixture_id), int(r.pl_home_id))] = int(r.home_id)
                tm[(int(r.sm_fixture_id), int(r.pl_away_id))] = int(r.away_id)
            self[(w, s)] = {(int(a), tm[(int(a), int(b))]): c for a, b, c in zip(L.sm_fixture_id, L.pl_team_id, L.team)}
        return self[(w, s)].get((f, t), "")


TEAMS = _Teams()


def plist_team(w, s, f, t, teams):
    return teams.get_name(w, s, f, t)


if __name__ == "__main__":
    main()
