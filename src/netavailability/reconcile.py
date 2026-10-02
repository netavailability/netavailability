"""The reconcile stage: Sportmonks' squads and transfers corrected where an independent verdict settles a dispute with
Transfermarkt, for the three input sets (early = 2014/15-2016/17 and mid = 2017/18 with the early dispute list,
late = 2018/19-2025/26 with the late list). Called by the pipeline.

Rules, in plain words:
  - A dispute changes the inputs only when an independent verdict settles it (Transfermarkt's version, Sportmonks'
    version, or OTHER = the evidenced status and dates). With no settling verdict (none, UNRESOLVED, verdicts that
    disagree, a verdict that cannot be applied by machine) the disputed player-club-fixtures are not charged and not in
    RET (EXCLUDED). When verdicts disagree, the one resting on the stronger evidence wins (matchday or squad lists >
    an official club / league source > two quality press sources).
  - A record dated by a verdict takes the date its sources evidence; Transfermarkt's date is kept when it lies inside
    the evidenced window (settings: verdict_dates).
  - A squad row (undated) of a club-season whose player is not named for the club that season is left out when a dated
    record contradicts it (he arrives after the season ends, or left before it started).
  - Two Sportmonks ids of one person are merged when both are named and name and date of birth agree, or when the
    identity file links them; an id never named that duplicates a named one is folded into it.
  - Arrivals written from Transfermarkt whose origin club Sportmonks lacks are priced by the origin-club rule
    (origin_overrides.csv); so are players whose only earlier clubs are youth sides (the senior-record rule).
  - Matchday data are the corrected input set (squads, minutes and events checked against premierleague.com); a
    player at two clubs on one date is closed at the new club's arrival record in the run stage.

It writes the corrected squads / transfers (and, when an identity merge touches them, appearances / events /
contracts) in the input files' own columns, plus for the whole run:
  ledger.csv                 one row per dispute with exactly one outcome (check C1):
                               APPLIED           an independent settling verdict (Transfermarkt / Sportmonks / OTHER)
                                                 was applied, or a rule settles the case type (corrected matchday data,
                                                 two-club closure)
                               EXCLUDED          no settling verdict; the disputed player-club-fixtures are not charged
                               ADDED_NO_VERDICT  setting gap_fill_tm_only = ADD: a Transfermarkt-only squad player of
                                                 2014/15-2021/22 that was never put to a verdict is added as
                                                 Transfermarkt has him, with his Transfermarkt-dated moves
  retention_overrides.csv    the exclusions input of the compute (manual overrides first)
  origin_overrides.csv       per player-club fills: senior record, resolved unknown origins, the Transfermarkt
                             origin-club rule for arrivals from clubs Sportmonks lacks
  lists                      verdicts_disagreeing.csv, verdicts_other_club_downgraded.csv, verdicts_not_applicable.csv,
                             unforeseen.csv, squad_rows_removed_contradicted.csv, identity_merges_applied.csv,
                             senior_record_players.csv, west_ham_us_records.csv, added_squad_rows.csv,
                             added_transfer_rows.csv, removed_rows.csv
"""
import json, re, time
from pathlib import Path
import numpy as np
import pandas as pd

from . import common as fb
from . import settings
from . import transfermarkt as TM

M4 = TM
PLACE, SYNTH_TID0, FAR = 800000000, 991000000, "2099-12-31"
GAP_SEASONS = {f"{y}/{y + 1}" for y in range(2014, 2022)}                  # 2014/15-2021/22 (setting gap_fill_tm_only)
ROSTER_TM = ("ROSTER_TM_ONLY", "AUDIT_ROSTER_TM_ONLY")
EVENT_TYPES = ("TM_ONLY", "SM_ONLY", "DATE_DIFF", "TYPE_DIFF", "PAGE_TYPE_DIFF", "TM_PAGE_ONLY")
ID_TYPES = ("ID_DOB_ONLY", "ID_DUPLICATE_ID", "ID_NAME_DOB_CONFLICT", "ID_NONE")
KNOWN = set(ROSTER_TM) | {"ROSTER_SM_ONLY", "ROSTER_AMBIGUOUS", "TWO_CLUBS_SAME_DATE"} | set(EVENT_TYPES) | set(ID_TYPES)
SQ_COLS = ["team_id", "season_id", "player_id", "player", "dob", "nationality_id", "start", "end", "jersey", "captain"]
TR_COLS = ["transfer_id", "player_id", "player", "date", "from_team_id", "from_team", "to_team_id", "to_team", "type_id",
           "career_ended", "completed", "amount"]
# input set -> the dispute list it is reconciled with
SETS = {"late": dict(src="late", seasons=fb.SETS["late"]), "early": dict(src="early", seasons=fb.SETS["early"]),
        "mid": dict(src="early", seasons=fb.SETS["mid"])}
# official club sites (setting other_club_in_deal = NOT; first- and second-round verdicts: classified by URL domain)
CLUB_DOMAINS = {
    "arsenal": ["arsenal.com"], "aston villa": ["avfc.co.uk"], "bournemouth": ["afcb.co.uk"], "brentford": ["brentfordfc.com"],
    "brighton and hove albion": ["brightonandhovealbion.com"], "burnley": ["burnleyfootballclub.com", "burnleyfc.com"],
    "cardiff city": ["cardiffcityfc.co.uk"], "chelsea": ["chelseafc.com"], "crystal palace": ["cpfc.co.uk"], "everton": ["evertonfc.com"],
    "fulham": ["fulhamfc.com"], "huddersfield town": ["htafc.com"], "ipswich town": ["itfc.co.uk"], "leeds united": ["leedsunited.com"],
    "leicester city": ["lcfc.com"], "liverpool": ["liverpoolfc.com"], "luton town": ["lutontown.co.uk"], "manchester city": ["mancity.com"],
    "manchester united": ["manutd.com"], "newcastle united": ["nufc.co.uk", "newcastleunited.com"], "norwich city": ["canaries.co.uk"],
    "nottingham forest": ["nottinghamforest.co.uk"], "sheffield united": ["sufc.co.uk"], "southampton": ["southamptonfc.com"],
    "sunderland": ["safc.com"], "tottenham hotspur": ["tottenhamhotspur.com"], "watford": ["watfordfc.com"],
    "west bromwich albion": ["wba.co.uk"], "west ham united": ["whufc.com"], "wolverhampton wanderers": ["wolves.co.uk"]}
LEAGUE_DOMAINS = ("premierleague.com", "pulselive.com")
PRESS_DOMAINS = ("bbc.co.uk", "bbc.com", "theguardian.com", "independent.co.uk", "espn.", "telegraph.co.uk", "thetimes.", "reuters.com",
                 "apnews.com")
# the verdict sources, in the order they are read (a later source's verdict is taken over an earlier one's)
ROUND1, ROUND2, ROUND3, GAPFILL = "round1", "round2", "round3", "gapfill"


def vkind(v):
    """TM | SM | OTHER | UNRESOLVED from a verdict row (CONFIRMS_TM / CONTRADICTS_TM: the audit wording)."""
    if v is None:
        return None
    x = str(v.get("verdict", "")).strip().upper()
    if x == "CONFIRMS_TM":                                  # audit wording: Transfermarkt's at-club claim confirmed
        return "TM"
    if x == "CONTRADICTS_TM":                               # audit wording: Transfermarkt contradicted (full or PARTIAL)
        return "SM"
    for k in ("TM", "SM", "OTHER"):
        if x == k or x.startswith(k + " ") or x.startswith(k + "_") or x.startswith(k + ":"):
            return k
    return "UNRESOLVED"


def vurl(v):
    return (v.get("src1_url") or v.get("settled_by") or "verdict") if v else ""


def source_url(v):
    """The source URL(s) of the verdict a ledger row rests on ("" when there is none)."""
    r = (v or {}).get("row") or {}
    return " | ".join(u for u in (str(r.get("src1_url", "")).strip(), str(r.get("src2_url", "")).strip()) if u.startswith("http"))


def iso(s):
    m = re.match(r"\s*(\d{4}-\d{2}-\d{2})\b", str(s))
    return m.group(1) if m else None


def any_iso(s):
    return re.findall(r"\d{4}-\d{2}-\d{2}", str(s))


def blank(v):
    return v is None or (isinstance(v, float) and np.isnan(v)) or str(v).strip() in ("", "nan", "None", "NaT", "<NA>")


def pid_num(v):
    """'TM123' -> 900000123; '123.0' -> 123; blank -> None."""
    if blank(v):
        return None
    s = str(v).strip()
    if s.upper().startswith("TM"):
        return fb.TM_PLAYER_BASE + int(float(s[2:]))
    if re.fullmatch(r"\d+(\.0)?", s):
        return int(float(s))
    return None


# ------------------------------------------------------------------ verdicts
def domain_class(url, clubs):
    u = str(url).lower()
    if not u.startswith("http"):
        return None
    if any(d in u for d in LEAGUE_DOMAINS):
        return "LEAGUE"
    for c in clubs:
        if any(d in u for d in CLUB_DOMAINS.get(fb.norm_club(c), [])):
            return "OWN_CLUB"
    for d in PRESS_DOMAINS:
        if d in u:
            return "PRESS:" + d
    return "OTHER_CLUB"


class Verdicts:
    """case_id -> the settling verdict over the sources: the first round, the second round (which re-settled the first
    round's UNRESOLVED cases), the third round and the gap-fill verdicts, in that order."""

    def __init__(self, cfg, log):
        self.cfg, self.rows, self.downgraded, self.disagree, self.sources = cfg, {}, [], [], {}
        self.conflicts_resolved, self.g_member, self.g_rows = [], {}, []
        src = [(ROUND1, settings.inp("verdicts_round1")), (ROUND2, settings.inp("verdicts_round2"))]
        if settings.inp("verdicts_round3").exists():
            src.append((ROUND3, settings.inp("verdicts_round3")))
        for name, p in src:
            d = pd.read_csv(p, dtype=str, keep_default_na=False)
            self.sources[name] = (settings.rel_data(p), len(d))
            for r in d.to_dict("records"):
                self.rows.setdefault(r["case_id"], []).append((name, r))
        # gap-fill verdicts: a gap-fill case is a player-club-season and its verdict is the verdict of every member
        # dispute (member_case_ids of the gap-fill case file)
        gp = settings.inp("verdicts_gapfill")
        gfiles = [gp] if gp.exists() else []
        if gfiles:
            gc = pd.read_csv(settings.inp("gapfill_verdict_cases"), dtype=str, keep_default_na=False)
            members = {r.case_id: [m for m in str(r.member_case_ids).split(";") if m] for r in gc.itertuples()}
            g = pd.concat([pd.read_csv(f, dtype=str, keep_default_na=False) for f in gfiles], ignore_index=True)
            self.sources[GAPFILL] = (settings.rel_data(gp), len(g))
            for r in g.to_dict("records"):
                self.g_rows.append(r)
                for m in members.get(r["case_id"], []) + [r["case_id"]]:
                    self.rows.setdefault(m, []).append((GAPFILL, dict(r, g_case_id=r["case_id"], case_id=m)))
                    self.g_member[m] = r["case_id"]
        self.corrections, self.except_dates = [], {}
        cpth = Path(cfg["verdict_corrections"]) if cfg.get("verdict_corrections") else None
        if cpth is not None and cpth.exists():
            for c in pd.read_csv(cpth, dtype=str, keep_default_na=False).to_dict("records"):
                hit = [(n, r) for n, r in self.rows.get(c["case_id"], []) if n == ROUND3]
                old = "; ".join(r.get("verdict", "") for _, r in hit)
                for _, r in hit:
                    r["verdict"] = c["new_verdict"]
                    if "verdict_excl_other_club" in r:
                        r["verdict_excl_other_club"] = c["new_verdict"]
                dates = [d.strip() for d in str(c.get("except_dates", "")).split(";") if d.strip()]
                if dates:
                    self.except_dates[c["case_id"]] = dates
                self.corrections.append(dict(case_id=c["case_id"], player=c["player"], club=c["club"], season=c["season"], verdict_before=old,
                                             verdict_applied=c["new_verdict"], fixtures_excluded=";".join(dates), applied=bool(hit), reason=c["reason"]))
            log(f"  verdict corrections (verdict_corrections.csv): {sum(c['applied'] for c in self.corrections)} of {len(self.corrections)} applied over the third round")
        log(f"  verdict sources: " + "; ".join(f"{k} {v[1]} rows" for k, v in self.sources.items()))

    @staticmethod
    def level(r):
        """Evidence hierarchy: 3 squad list (matchday / registration lists, namings) > 2 official (either club in
        the deal, PL, EFL) > 1 two quality press > 0 none."""
        et, sb = str(r.get("evidence_types", "")).upper(), str(r.get("settled_by", "")).lower()
        if "NAMING" in et or "SQUAD" in et or re.search(r"\(a\)|naming|matchday|squad list|team sheet", sb):
            return 3
        if "OFFICIAL" in et or re.search(r"\(b\)|official|premierleague\.com|efl", sb):
            return 2
        if "PRESS" in et or re.search(r"\(c\)|bbc|guardian|independent|press", sb):
            return 1
        return 0

    def kind(self, name, r, clubs):
        raw = str(r.get("verdict", "")).strip()
        mode = self.cfg["other_club_in_deal"]
        tab = name.startswith((ROUND3, GAPFILL))
        # COUNTS = the other club in the deal counts for a completed move only: a verdict on a roster / at-club
        # claim that rests on the other club's site alone falls back to its verdict without that source
        move_done = str(r.get("evidenced_event", "")) in ("LEFT", "LOAN_OUT", "ARRIVED", "LOAN_RETURN")
        ctype = str(r.get("case_type", "")).replace("UNLINKED_", "").replace("AUDIT_", "")
        is_move_case = ctype in EVENT_TYPES or ctype == "TWO_CLUBS_SAME_DATE"
        if tab and (mode == "NOT" or (mode == "COUNTS" and not (move_done or is_move_case))) and str(r.get("verdict_excl_other_club", "")).strip():
            v2 = str(r["verdict_excl_other_club"]).strip()
            if vkind(dict(verdict=v2)) != vkind(dict(verdict=raw)):
                self.downgraded.append(dict(case_id=r["case_id"], source=name, player=r.get("player"), verdict=raw, verdict_excl_other_club=v2,
                                            rule="third-round verdict_excl_other_club", urls=""))
            raw = v2
        k = vkind(dict(verdict=raw))
        if k in ("TM", "SM", "OTHER") and not tab and (mode == "NOT" or (mode == "COUNTS" and not is_move_case)):
            cls = [domain_class(r.get(c), clubs) for c in ("src1_url", "src2_url")]
            cls = [c for c in cls if c]
            official = [c for c in cls if c in ("OWN_CLUB", "LEAGUE", "OTHER_CLUB")]
            press = {c for c in cls if c.startswith("PRESS")}
            sb = str(r.get("settled_by", "")).lower()
            league_text = "premierleague.com" in sb
            if official and all(c == "OTHER_CLUB" for c in official) and len(press) < 2 and not league_text:
                self.downgraded.append(dict(case_id=r["case_id"], source=name, player=r.get("player"), verdict=raw,
                                            verdict_excl_other_club="UNRESOLVED", rule="only official source is the other club's site (URL domain)",
                                            urls=" | ".join(str(r.get(c, "")) for c in ("src1_url", "src2_url"))))
                k = "UNRESOLVED"
        return k

    def settle(self, case_id, clubs=()):
        """-> dict(kind = TM | SM | OTHER | UNRESOLVED | NONE | DISAGREE, row, source, raw)."""
        got = [(n, r, self.kind(n, r, clubs)) for n, r in self.rows.get(case_id, [])]
        if not got:
            return dict(kind="NONE", row=None, source="", raw="")
        sett = [(n, r, k) for n, r, k in got if k in ("TM", "SM", "OTHER")]
        if not sett:
            n, r, k = got[-1]
            return dict(kind="UNRESOLVED", row=r, source=n, raw=r.get("verdict", ""))
        kinds = {k for _, _, k in sett}
        if len(kinds) > 1:                                                # the verdict with evidence higher in the hierarchy wins
            lv = [(self.level(r), n, r, k) for n, r, k in sett]
            top = max(x[0] for x in lv)
            win = [x for x in lv if x[0] == top]
            txt = "; ".join(f"{n}: {r.get('verdict')} (level {l})" for l, n, r, _ in lv)
            if len({x[3] for x in win}) == 1:
                self.conflicts_resolved.append(dict(case_id=case_id, verdicts=txt, winner=f"{win[-1][1]}: {win[-1][2].get('verdict')}"))
                sett = [(n, r, k) for _, n, r, k in win]
            else:
                self.disagree.append(dict(case_id=case_id, verdicts=txt))
                return dict(kind="DISAGREE", row=sett[-1][1], source="+".join(n for n, _, _ in sett), raw="/".join(r.get("verdict", "") for _, r, _ in sett))
        n, r, k = sett[-1]
        return dict(kind=k, row=r, source=n, raw=r.get("verdict", ""))


def verdict_date(cfg, v, tm_date):
    """verdict_dates. EVIDENCED: the third round's evidenced_from is the date the sources evidence for the event (effective date, else
    announcement); evidenced_to is the end of what they evidence (effective date after an announcement, first naming
    elsewhere, or the end of a loan). With evidenced_from given, Transfermarkt's date is kept when it lies in
    evidenced_from..evidenced_to and moved to the nearer end otherwise; with only evidenced_to given the event itself is
    not dated by the sources and Transfermarkt's date stands. A first- / second-round OTHER verdict gives its evidenced
    ISO date.
    TM: always Transfermarkt's date. Returns (date or None, note)."""
    tm = None if blank(tm_date) else str(tm_date)[:10]
    if cfg["verdict_dates"] == "TM" and tm:
        return tm, "TM date (verdict_dates = TM)"
    r = v["row"] or {}
    lo, hi = iso(r.get("evidenced_from", "")), iso(r.get("evidenced_to", ""))
    # a gap-fill verdict is on a player-club-season; its evidenced window dates one event of that season, so it is not
    # used to move the Transfermarkt date of another member move of a roster case
    g_roster = v["source"].startswith(GAPFILL) and "ROSTER" in str(r.get("case_type", ""))
    if v["source"].startswith((ROUND3, GAPFILL)) and not g_roster and str(r.get("evidenced_event", "")) in ("LEFT", "LOAN_OUT", "ARRIVED", "LOAN_RETURN") and lo:
        hi = hi if (hi and hi >= lo) else lo
        if tm is None:
            return lo, f"evidenced {lo}..{hi} (no TM date)"
        d = min(max(tm, lo), hi)
        return d, ("TM date inside the evidenced window" if d == tm else f"TM date {tm} moved into the evidenced window {lo}..{hi}")
    if v["source"].startswith((ROUND3, GAPFILL)) and v["kind"] == "TM" and tm:
        return tm, "TM date (the sources do not date the event itself)"
    if v["kind"] == "OTHER":
        d = iso(r.get("evidence_date", ""))
        if not d and len(set(any_iso(r.get("evidence_date", "")))) == 1:   # one full date anywhere in the text
            d = any_iso(r.get("evidence_date", ""))[0]
        if d:
            return d, "OTHER verdict: evidenced date"
        return (tm, "OTHER verdict without a machine-readable date") if cfg["verdict_dates"] == "TM" else (None, "OTHER verdict without a machine-readable date")
    return tm, "TM date"


# ------------------------------------------------------------------ per-source context
class Source:
    """One dispute list (late or early): its diff tables, Transfermarkt at-club intervals, identity files, squad pages."""

    def __init__(self, name):
        self.name = name
        d = settings.data_path("review", name)
        self.R = pd.read_csv(d / "diff_roster.csv", dtype={"sm_player_id": str})
        self.E = pd.read_csv(d / "diff_events.csv", dtype={"sm_player_id": str})
        self.iv = pd.read_csv(d / "tm_intervals.csv", parse_dates=["from_date", "to_date", "window_from"])
        squad_files = TM.squad_files(name)
        self.identity_files = sorted((d / "identity").glob("*.csv"))
        if name == "late":
            self.dup_global = d / "identity_duplicates_global.csv"
            self.extra_dups = [(1052, 37702647)]                               # a transfers-only twin id of one player
        else:
            self.dup_global = None
            self.extra_dups = []
        self.tmdob = {}
        for f in squad_files:
            for r in pd.read_csv(f, dtype={"tm_dob": str}).itertuples():
                self.tmdob.setdefault(int(r.tm_player_id), (r.tm_player, r.tm_dob if isinstance(r.tm_dob, str) else ""))
        self._hists = None
        self.tm2sm = TM.tm_to_sm()

    def hists(self):
        if self._hists is None:
            self._hists = TM.histories(self.name)
        return self._hists


def dup_pairs(S, apps):
    """[(keep, drop, how)] and the both-named groups, from the identity files (DUPLICATE_ID)."""
    nm_any = apps.player_id.dropna().astype(int).value_counts().to_dict()
    ids, info = set(), {}
    for f in S.identity_files:
        d = pd.read_csv(f)
        for r in d[d.id_class == "DUPLICATE_ID"].itertuples():
            if isinstance(r.dup_ids, str):
                ids.add(tuple(int(x) for x in r.dup_ids.split(" / ")))
            info[int(r.sm_player_id)] = (r.player_name, r.dob if isinstance(r.dob, str) else "")
    if S.dup_global is not None and S.dup_global.exists() and S.dup_global.stat().st_size > 5:
        for s in pd.read_csv(S.dup_global).sm_ids:
            ids.add(tuple(int(x) for x in str(s).split(" / ")))
    for t in S.extra_dups:
        ids.add(t)
    pairs, both = [], []
    for tup in sorted(ids):
        named = [i for i in tup if nm_any.get(i, 0) > 0]
        unnamed = [i for i in tup if nm_any.get(i, 0) == 0]
        if len(named) == 1 and unnamed:
            pairs += [(named[0], u, "one id named, the other never named") for u in unnamed]
        elif len(named) >= 2:
            both.append((tup, {i: nm_any.get(i, 0) for i in named}, {i: info.get(i, ("", "")) for i in tup}))
    return pairs, both


def validate_transfers(tr, teams):
    """The driver's blocking faults: a type id outside 218/219/9688/220, or a club of our data (a name in the teams
    file) with a null or placeholder id. A blank from-club (no name, no id) is accepted."""
    bad = tr[~pd.to_numeric(tr.type_id, errors="coerce").isin(fb.VALID_TYPES)]
    data_names = {fb.norm_club(n): int(t) for n, t in zip(teams.name, teams.team_id)}
    unm = []
    for side_id, side_nm in (("from_team_id", "from_team"), ("to_team_id", "to_team")):
        ids = pd.to_numeric(tr[side_id], errors="coerce")
        for tid, nm, t_id in zip(ids, tr[side_nm], tr.transfer_id):
            if isinstance(nm, str) and fb.norm_club(nm) in data_names and (pd.isna(tid) or int(tid) >= PLACE):
                unm.append(dict(transfer_id=t_id, side=side_nm, name=nm, id=None if pd.isna(tid) else int(tid), data_team_id=data_names[fb.norm_club(nm)]))
    return bad, unm


def convert_review_format(sq=None, tr=None, tid0=993000000):
    """A review-format squads / transfers frame (the input columns + appended columns, 'TM{id}' player ids, blank
    transfer ids) -> the compute's columns and ids."""
    out = []
    if sq is not None:
        sq = sq.copy()
        sq["player_id"] = sq.player_id.map(pid_num).astype("Int64")
        out.append(sq[SQ_COLS])
    if tr is not None:
        tr = tr.copy()
        tr["player_id"] = tr.player_id.map(pid_num).astype("Int64")
        b = tr.transfer_id.isna() | (tr.transfer_id.astype(str).str.strip() == "")
        tr.loc[b, "transfer_id"] = [tid0 + i for i in range(int(b.sum()))]
        for c in ("from_team_id", "to_team_id"):
            tr[c] = pd.to_numeric(tr[c], errors="coerce").astype("Int64")
        out.append(tr[TR_COLS])
    return out[0] if len(out) == 1 else out


# ------------------------------------------------------------------ one input set
def reconcile_set(set_name, S, H, D, V, cfg, out, log, state):
    """H = the sized hand list of the source restricted to this set's seasons; D = its size detail."""
    seasons = SETS[set_name]["seasons"]
    teams = pd.read_csv(fb.sm_file(set_name, "teams"))
    tpl = teams[teams.league == "Premier League"]
    sids = dict(zip(tpl.season, tpl.season_id.astype(int)))
    club_name = dict(zip(teams.team_id.astype(int), teams.name))
    tdd = teams.drop_duplicates("team_id")
    by_name = {M4.nclub(n): (int(i), n) for i, n in zip(tdd.team_id, tdd.name)}
    sq = pd.read_csv(fb.sm_file(set_name, "squads"), dtype={"player_id": str})
    tr = pd.read_csv(fb.sm_file(set_name, "transfers"), dtype={"player_id": str}).drop_duplicates("transfer_id")
    apps_src = state["matchday"](set_name, "appearances")
    apps = pd.read_csv(apps_src, usecols=["fixture_id", "season_id", "date", "team_id", "player_id"])
    sq["provenance"], sq["q_flag"] = "SM", ""
    tr["provenance"], tr["q_flag"] = "SM", ""
    R = S.R[S.R.season.isin(seasons)]
    E = S.E[S.E.season.isin(seasons)]
    H = H[H.season.isin(seasons)]
    hl = {r["case_id"]: r for r in H.to_dict("records")}
    hl_roster_key = {(r["season"], str(r["team_id"]), str(r["sm_player_id"])): r for r in H.to_dict("records")
                     if str(r["case_type"]).replace("UNLINKED_", "") in ROSTER_TM}
    ledger, excl_cases, removed, added_sq, added_tr, new_rows, notapp, unforeseen = [], [], [], [], [], [], [], []
    seen = set()
    nxt = [state["next_tid"]]

    def new_tid():
        nxt[0] += 1
        return nxt[0]

    def led(case, outcome, basis, action="", v=None, in_hand=True, case_type=None, flags=""):
        cid = case.get("case_id")
        if in_hand:
            if cid in seen:
                return
            seen.add(cid)
        h = hl.get(cid, {}) if in_hand else {}
        gf = state["gf"].get(cid, {})
        size = h.get("size_xu_min", case.get("size_xu_min")) if in_hand else (gf.get("size", 0.0) if gf.get("primary") else 0.0)
        ledger.append(dict(case_id=cid, source=S.name, input_set=set_name, in_hand_list=in_hand, marker=h.get("marker", case.get("marker", "")),
                           season=case.get("season"), team_id=case.get("team_id"), club=case.get("club"),
                           case_type=case_type or h.get("case_type") or case.get("case_type") or case.get("cls"),
                           player=case.get("player"), sm_player_id=case.get("sm_player_id"), tm_player_id=case.get("tm_player_id"),
                           size_xu_min=0.0 if blank(size) else float(size),
                           over_bar=bool((0.0 if blank(size) else float(size)) >= cfg["bar_minutes"]),
                           n_disputed=(0 if blank(h.get("n_disputed")) else int(float(h.get("n_disputed")))) if in_hand else int(gf.get("n", 0) if gf.get("primary") else 0),
                           minutes_at_stake=h.get("minutes_at_stake", case.get("minutes_at_stake")),
                           verdict=(v or {}).get("raw", ""), verdict_kind=(v or {}).get("kind", ""), verdict_source=(v or {}).get("source", ""),
                           outcome=outcome, basis=basis, action=action, flags=flags, gapfill_case_id=gf.get("case_id", ""),
                           gapfill_verdict_case_id=V.g_member.get(cid, ""), source_url=source_url(v)))
        if outcome == "EXCLUDED" and in_hand:
            excl_cases.append(cid)

    def clubs_of(case):
        return [c.strip() for c in str(case.get("club", "")).split("/")]

    def sm_team(tm_id, tm_name):
        return TM.sm_team(tm_id, tm_name, S.tm2sm, by_name)

    def ev_row(r, date, why, prov, flag=""):
        K = int(r["team_id"])
        other_sm, of = sm_team(r.get("tm_other_id"), r.get("tm_other"))
        d = r["direction"]
        row = {c: None for c in TR_COLS}
        row.update(transfer_id=new_tid(), player_id=r["sm_player_id"], player=r["player"], date=str(date),
                   from_team_id=other_sm if d == "in" else K, from_team=r.get("tm_other") if d == "in" else club_name.get(K),
                   to_team_id=K if d == "in" else other_sm, to_team=club_name.get(K) if d == "in" else r.get("tm_other"),
                   type_id=TM.type_id(r["tm_type"], r.get("tm_fee")), career_ended=False, completed=True, amount=None, provenance=prov,
                   q_flag=";".join(x for x in (flag, of, "NO_SM_ID" if str(r["sm_player_id"]).startswith("TM") else "") if x))
        added_tr.append(dict(row, case_id=r.get("case_id"), season=r["season"], club=r["club"], why=why, tm_other_tm_id=r.get("tm_other_id"),
                             tm_player_id=r.get("tm_player_id")))
        return row

    # ---------------- roster: both
    both = R[R.cls == "BOTH"]
    kb = {(sids[s], int(t_), str(p)) for s, t_, p in zip(both.season, both.team_id, both.sm_player_id)}
    sq.loc[[(a, b, str(c)) in kb for a, b, c in zip(sq.season_id, sq.team_id, sq.player_id)], "provenance"] = "both"

    # ---------------- roster: SM only / ambiguous
    for r in R[R.cls.isin(["ROSTER_SM_ONLY", "ROSTER_AMBIGUOUS"])].to_dict("records"):
        inh = r["case_id"] in hl
        v = V.settle(r["case_id"], clubs_of(r))
        sel = (sq.season_id == sids[r["season"]]) & (sq.team_id == r["team_id"]) & (sq.player_id.astype(str) == str(r["sm_player_id"]))
        unl = str(hl.get(r["case_id"], {}).get("case_type", "")).startswith("UNLINKED_")
        if unl:
            Ys = [k for k, x in state["link_tm"].items() if str(x) == str(r["sm_player_id"])]
            if not Ys:
                continue                                                  # not linked: excluded with the identity cases below
            if ((R.cls == "ROSTER_TM_ONLY") & (R.season == r["season"]) & (R.team_id == r["team_id"]) & R.sm_player_id.isin(Ys)).any():
                led(r, "APPLIED", f"identity linked (identity_merges.csv): Sportmonks {r['sm_player_id']} is Transfermarkt {Ys[0]}, whom Transfermarkt has at the club; "
                    "squad row kept", "", v, True)
                continue
        if v["kind"] == "TM":
            removed.append(sq[sel].assign(removed_because=f"{r['cls']} verdict TM ({v['source']})"))
            sq = sq[~sel]
            led(r, "APPLIED", "verdict TM: not at the club", "squad row removed", v, inh)
        elif v["kind"] == "SM":
            sq.loc[sel, "provenance"] = vurl(v["row"]); sq.loc[sel, "q_flag"] = f"{r['cls']}_VERDICT_SM"
            led(r, "APPLIED", "verdict SM: squad row kept", "", v, inh)
        elif inh:
            sq.loc[sel, "q_flag"] = f"{r['cls']}_EXCLUDED"
            if v["kind"] == "OTHER":
                notapp.append(dict(case_id=r["case_id"], case_type=r["cls"], player=r["player"], verdict=v["raw"],
                                   evidence=(v["row"] or {}).get("evidence_date", ""), why="OTHER on a roster row: dates not machine-readable"))
            led(r, "EXCLUDED", f"no settling verdict ({v['kind']})" if v["kind"] != "OTHER" else "OTHER verdict not machine-applicable",
                "disputed fixtures excluded", v, True)

    # ---------------- roster: TM only
    adds, added_players = [], set()
    for r in R[R.cls == "ROSTER_TM_ONLY"].to_dict("records"):
        s = r["season"]
        h = hl.get(r["case_id"]) or hl_roster_key.get((s, str(r["team_id"]), str(r["sm_player_id"])))
        case = dict(r, case_id=h["case_id"]) if h else r
        ctype = h["case_type"] if h else "ROSTER_TM_ONLY (not on the hand list)"
        v = V.settle(case["case_id"], clubs_of(r)) if h else V.settle(r["case_id"], clubs_of(r))
        if h and str(h["case_type"]).startswith("UNLINKED_"):
            X = state["link_tm"].get(str(r["sm_player_id"]))
            if X is None:
                continue                                                  # not linked: excluded (below)
            if ((sq.season_id == sids[s]) & (sq.team_id == r["team_id"]) & (sq.player_id.astype(str) == str(X))).any():
                led(case, "APPLIED", f"identity linked (identity_merges.csv): Transfermarkt {r['sm_player_id']} is Sportmonks {X}, who is in the Sportmonks squad; no change",
                    "", v, True, case_type=ctype)
                continue
            r = dict(r, sm_player_id=str(X)); case = dict(case, sm_player_id=str(X))
        row_v = v["row"] or {}
        partial_out = None
        if v["kind"] in ("SM", "OTHER") and "PARTIAL" in str(row_v.get("notes", "")).upper():
            ds = any_iso(row_v.get("evidence_date", ""))
            if ds and re.search(r"depart|left|leave|released|expiry", str(row_v.get("evidence_date", "")), re.I):
                partial_out = ds[-1]
        add, outcome, basis, prov = False, None, None, "TM"
        if v["kind"] == "TM":
            add, outcome, basis, prov = True, "APPLIED", "verdict TM: at the club as Transfermarkt says", vurl(row_v)
        elif partial_out:
            add, outcome, prov = True, "APPLIED", vurl(row_v)
            basis = f"verdict {v['raw']} PARTIAL: at the club until {partial_out} (evidenced departure); squad row added with a departure record"
        elif v["kind"] == "SM":
            outcome, basis = "APPLIED", "verdict SM: not added"
        elif v["kind"] == "OTHER" and v["source"].startswith((ROUND3, GAPFILL)) and iso(row_v.get("evidenced_from", "")) and \
                str(row_v.get("evidenced_event", "")) in ("ARRIVED", "LOAN_RETURN", "LEFT", "LOAN_OUT"):
            # OTHER = the evidenced status and dates: at the club as the roster says, but from / until the evidenced date
            y_, d0 = int(s[:4]), pd.Timestamp(iso(row_v["evidenced_from"]))
            add, outcome, prov = True, "APPLIED", vurl(row_v)
            if row_v["evidenced_event"] in ("ARRIVED", "LOAN_RETURN"):
                win = (f"{y_}-07-01", str((d0 - pd.Timedelta(days=1)).date()))
                basis = f"verdict OTHER: at the club from {d0.date()} (evidenced {row_v['evidenced_event']}); squad row added, not retained before that date"
            else:
                d1 = iso(row_v.get("evidenced_to", "")) if row_v["evidenced_event"] == "LOAN_OUT" else None
                win = (str((d0 + pd.Timedelta(days=1)).date()), d1 or f"{y_ + 1}-07-31")
                basis = f"verdict OTHER: away from {d0.date()} (evidenced {row_v['evidenced_event']}); squad row added, not retained {win[0]}..{win[1]}"
            state["auto_overrides"].append(dict(player_id=r["sm_player_id"], team_id=int(r["team_id"]), **{"from": win[0], "to": win[1]}, action="NOT_RETAIN",
                                                case_id=f"{case['case_id']} (OTHER verdict: evidenced dates)"))
        elif v["kind"] == "OTHER":
            outcome, basis = "EXCLUDED", "OTHER verdict on a roster case is not machine-applicable"
            notapp.append(dict(case_id=case["case_id"], case_type=ctype, player=r["player"], verdict=v["raw"],
                               evidence=row_v.get("evidence_date", ""), why="OTHER on a roster case"))
        else:                                                             # no settling verdict
            size = 0.0 if not h or blank(h.get("size_xu_min")) else float(h["size_xu_min"])
            gsz = state["gf"].get(case["case_id"], {}).get("size", size)
            never_put = (not h) or (size < cfg["bar_minutes"] and v["kind"] == "NONE") or (S.name == "late" and size < cfg["bar_minutes"])
            if cfg["gap_fill_tm_only"] == "ADD" and s in GAP_SEASONS and never_put:   # setting gap_fill_tm_only = ADD
                add, outcome = True, "ADDED_NO_VERDICT"
                basis = "gap_fill_tm_only = ADD: Transfermarkt-only roster player, no settling verdict, " + ("not on the hand list" if not h else "under the bar")
            else:                                                         # sized; excluded without a settling verdict
                outcome = "EXCLUDED"
                basis = f"no settling verdict ({v['kind']}); " + ("over the bar: needs an independent verdict (gap-fill verdicts)" if max(size, gsz) >= cfg["bar_minutes"]
                                                                  else "under the bar (gap_fill_tm_only = EXCLUDE)")
        if add:
            sid = r["sm_player_id"]
            tp = None if blank(r["tm_player_id"]) else int(float(r["tm_player_id"]))
            nmx, dob = S.tmdob.get(tp, (r["player"], ""))
            flag = ("GAP_FILL" if outcome == "ADDED_NO_VERDICT" else "VERDICT_ADD") + (";NO_SM_ID" if str(sid).startswith("TM") else "")
            row = {c: None for c in SQ_COLS}
            row.update(team_id=int(r["team_id"]), season_id=sids[s], player_id=sid, player=nmx, dob=dob or None, provenance=prov, q_flag=flag)
            adds.append(row)
            added_sq.append(dict(r, flag=flag, provenance=prov, outcome=outcome, case_id=case["case_id"]))
            if s in GAP_SEASONS:
                added_players.add((s, int(r["team_id"]), str(sid)))
            if partial_out:
                x = dict(case, direction="out", tm_type="permanent", tm_fee="free transfer (contract expiry)", tm_other=None, tm_other_id=None)
                new_rows.append(ev_row(x, partial_out, "PARTIAL verdict: evidenced departure", prov, "VERDICT_PARTIAL_OUT"))
        led(case, outcome, basis, "squad row added" if add else ("disputed fixtures excluded" if outcome == "EXCLUDED" else ""), v,
            in_hand=bool(h), case_type=ctype)
    sq = pd.concat([sq, pd.DataFrame(adds)], ignore_index=True) if adds else sq

    # ---------------- events
    ag = E[E.cls.isin(["AGREE", "PAGE_AGREE"]) & E.sm_transfer_id.notna()]
    tr.loc[tr.transfer_id.isin(set(ag.sm_transfer_id.astype(int))), "provenance"] = "both"
    for r in E.to_dict("records"):
        cls = r["cls"]
        if cls in ("AGREE", "PAGE_AGREE", "TM_UNDATED"):
            continue
        inh = r.get("case_id") in hl
        v = V.settle(r.get("case_id"), clubs_of(r))
        if inh and str(hl[r["case_id"]]["case_type"]).startswith("UNLINKED_"):
            sid_ = str(r["sm_player_id"])
            X = state["link_tm"].get(sid_)
            if X is None and sid_ not in state["link_sm_ids"]:
                continue                                                  # not linked: excluded (below)
            K_ = int(r["team_id"])
            if X is not None:                                             # the Transfermarkt-side record of a linked player
                d0 = pd.to_datetime(r.get("tm_date"), errors="coerce")
                same = tr[(tr.player_id.astype(str) == str(X)) & ((tr.to_team_id == K_) if r["direction"] == "in" else (tr.from_team_id == K_))]
                if pd.notna(d0) and len(same) and ((pd.to_datetime(same.date, errors="coerce") - d0).abs() <= pd.Timedelta(days=7)).any():
                    led(r, "APPLIED", f"identity linked (identity_merges.csv): Sportmonks holds the same record for {X}; no change", "", v, True)
                    continue
                r = dict(r, sm_player_id=str(X))
            else:                                                         # the Sportmonks-side record of a linked player
                Ys = [k for k, x in state["link_tm"].items() if str(x) == sid_]
                if ((E.cls == "TM_ONLY") & (E.season == r["season"]) & (E.team_id == r["team_id"]) & E.sm_player_id.isin(Ys) & (E.direction == r["direction"])).any():
                    led(r, "APPLIED", f"identity linked (identity_merges.csv): Transfermarkt holds the matching record as {Ys[0]}; record kept", "", v, True)
                    continue
        k = v["kind"]
        key = (r["season"], int(r["team_id"]), str(r["sm_player_id"]))
        sel = tr.transfer_id == (int(r["sm_transfer_id"]) if pd.notna(r.get("sm_transfer_id")) else -1)
        d, dnote = verdict_date(cfg, v, r.get("tm_date")) if k in ("TM", "OTHER") else (None, "")
        if cls in ("TM_ONLY", "TM_PAGE_ONLY"):
            if k in ("TM", "OTHER") and d and not blank(r.get("tm_type")):
                new_rows.append(ev_row(r, d, f"{cls} verdict {k} ({dnote})", vurl(v["row"]), "VERDICT_TM_ONLY"))
                led(r, "APPLIED", f"verdict {k}: record written, {dnote}", f"transfer row added {d}", v, inh)
            elif k == "SM":
                led(r, "APPLIED", "verdict SM: no record written", "", v, inh)
            elif cls == "TM_ONLY" and key in added_players and not blank(r.get("tm_date")) and not (
                    inh and float(hl[r["case_id"]].get("size_xu_min") or 0) >= cfg["bar_minutes"]):
                new_rows.append(ev_row(r, r["tm_date"], "TM-dated event of an added Transfermarkt-only roster player", "TM", "GAP_FILL_EVENT"))
                led(r, "ADDED_NO_VERDICT", "Transfermarkt-dated move, no verdict of its own, of a player whose roster row is added" +
                    (" on a verdict" if cfg["gap_fill_tm_only"] != "ADD" else "") + ": written as Transfermarkt dates it, so the games he is away are not charged",
                    f"transfer row added {r['tm_date']}", v, inh)
            elif inh:
                if k == "OTHER":
                    notapp.append(dict(case_id=r["case_id"], case_type=cls, player=r["player"], verdict=v["raw"],
                                       evidence=(v["row"] or {}).get("evidence_date", ""), why=dnote))
                led(r, "EXCLUDED", f"no settling verdict ({k})" if k != "OTHER" else "OTHER verdict not machine-applicable",
                    "disputed fixtures excluded", v, True)
            continue
        if not sel.any():
            if inh:
                led(r, "EXCLUDED", f"the Sportmonks record of the case is not in the input ({k})", "disputed fixtures excluded", v, True,
                    flags="SM_RECORD_NOT_FOUND")
            continue
        if k == "SM":
            tr.loc[sel, "provenance"] = vurl(v["row"]); tr.loc[sel, "q_flag"] = f"{cls}_VERDICT_SM"
            led(r, "APPLIED", "verdict SM: record kept", "", v, inh)
        elif k in ("TM", "OTHER") and cls == "DATE_DIFF" and d:
            tr.loc[sel, "date"] = str(d); tr.loc[sel, "provenance"] = vurl(v["row"]); tr.loc[sel, "q_flag"] = f"DATE_DIFF_VERDICT_{k}"
            led(r, "APPLIED", f"verdict {k}: date set, {dnote}", f"date -> {d}", v, inh)
        elif k == "TM" and cls in ("TYPE_DIFF", "PAGE_TYPE_DIFF"):
            tr.loc[sel, "type_id"] = TM.type_id(r["tm_type"], r.get("tm_fee"))
            tr.loc[sel, "provenance"] = vurl(v["row"]); tr.loc[sel, "q_flag"] = f"{cls}_VERDICT_TM"
            led(r, "APPLIED", "verdict TM: type set", f"type -> {TM.type_id(r['tm_type'], r.get('tm_fee'))}", v, inh)
        elif k == "TM" and cls == "SM_ONLY":
            removed.append(tr[sel].assign(removed_because=f"SM_ONLY verdict TM ({v['source']})"))
            tr = tr[~sel]
            led(r, "APPLIED", "verdict TM: Sportmonks record removed", "transfer row removed", v, inh)
        elif k == "OTHER" and cls == "SM_ONLY" and d:
            tr.loc[sel, "date"] = str(d); tr.loc[sel, "provenance"] = vurl(v["row"]); tr.loc[sel, "q_flag"] = "SM_ONLY_VERDICT_OTHER"
            led(r, "APPLIED", f"verdict OTHER: date set, {dnote}", f"date -> {d}", v, inh)
        elif inh:
            if k in ("TM", "OTHER"):
                notapp.append(dict(case_id=r["case_id"], case_type=cls, player=r["player"], verdict=v["raw"],
                                   evidence=(v["row"] or {}).get("evidence_date", ""), why=f"verdict {k} cannot be applied to a {cls} row"))
                tr.loc[sel, "q_flag"] = f"{cls}_VERDICT_{k}_NOT_APPLICABLE"
            else:
                tr.loc[sel, "q_flag"] = f"{cls}_EXCLUDED"
            led(r, "EXCLUDED", f"no settling verdict ({k})" if k not in ("TM", "OTHER") else f"verdict {k} not machine-applicable",
                "disputed fixtures excluded", v, True)

    # an added player whose first Transfermarkt interval starts after the window start gets his earlier departure too
    hists = None
    for a in added_sq:
        if a["season"] not in GAP_SEASONS or not str(a.get("tm_cls", "")).startswith("AT_CLUB_PART") or blank(a.get("tm_player_id")):
            continue
        x = S.iv[(S.iv.season == a["season"]) & (S.iv.team_id == a["team_id"]) & (S.iv.tm_player_id == a["tm_player_id"])]
        if x.empty or x.from_date.min() <= x.window_from.iloc[0]:
            continue
        hists = hists if hists is not None else S.hists()
        kset = TM.youth_sets(S.name)[TM.club_ids()[int(a["team_id"])][0]]
        lo = pd.Timestamp(f"{int(a['season'][:4])}-06-01")
        hh = [e for e in hists.get(int(a["tm_player_id"]), []) if e["date"] and not e["upcoming"]
              and pd.Timestamp(e["date"]) < lo and ((e["from_id"] in kset) != (e["to_id"] in kset))]
        if hh and hh[-1]["from_id"] in kset:
            e = hh[-1]
            r = dict(a, direction="out", tm_type=TM.tm_type(e["fee"]), tm_fee=e["fee"], tm_other=e["to_name"], tm_other_id=e["to_id"], case_id=None)
            dup = tr[(tr.player_id.astype(str) == str(a["sm_player_id"])) & (tr.date.astype(str).str[:10] == e["date"])]
            if dup.empty:
                new_rows.append(ev_row(r, e["date"], "departure before the window (player away at the start)", "TM", "GAP_FILL_EVENT_PRIOR"))
    if new_rows:
        tr = pd.concat([tr, pd.DataFrame(new_rows)], ignore_index=True)

    # ---------------- the remaining hand-list cases: identity, matchday, two clubs, unlinked, unforeseen
    for h in H.to_dict("records"):
        cid, ct = h["case_id"], str(h["case_type"])
        if cid in seen:
            continue
        v = V.settle(cid, clubs_of(h))
        base = ct.replace("UNLINKED_", "")
        if ct.startswith("UNLINKED_"):
            toks = {str(x).strip().replace(".0", "") for x in re.split(r"[ /]+", str(h.get("sm_player_id"))) if x}
            linked = bool(toks & (set(state["link_tm"]) | state["link_sm_ids"]))
            if linked:
                led(h, "APPLIED", "identity_links = MERGE_FILE: identity linked by identity_merges.csv (independent evidence of the same person)", "", v)
            else:
                led(h, "EXCLUDED", f"identity_links = {cfg['identity_links']}: identity near-miss not linked", "disputed fixtures excluded", v)
        elif base.startswith("NAMINGS_"):
            led(h, "APPLIED", "matchday data = the corrected input set (" + ("in use" if state["xa"] else "ABSENT in this run: originals used") + ")",
                "", v, flags="" if state["xa"] else "CORRECTED_MATCHDAY_ABSENT")
        elif base == "TWO_CLUBS_SAME_DATE":
            led(h, "APPLIED", "two-club overlap closed at the new club's arrival record (or first naming)", "closure row added in the run stage if still open", v)
        elif base in ID_TYPES:
            if v["kind"] in ("TM", "SM", "OTHER"):
                extra = ""
                if v["kind"] == "OTHER":
                    notapp.append(dict(case_id=cid, case_type=ct, player=h["player"], verdict=v["raw"], evidence=(v["row"] or {}).get("evidence_date", ""),
                                       why="OTHER on an identity case: status and dates are free text; applied by excluding the disputed fixtures"))
                    led(h, "EXCLUDED", "OTHER verdict not machine-applicable (free-text status and dates)", "disputed fixtures excluded", v)
                else:
                    led(h, "APPLIED", f"identity verdict {v['kind']}: no input change" + (" (duplicate ids merged where name + DOB agree)" if base == "ID_DUPLICATE_ID" else ""), "", v)
            else:
                led(h, "EXCLUDED", f"no settling verdict ({v['kind']})", "disputed fixtures excluded", v)
        elif base in KNOWN:
            led(h, "EXCLUDED", f"the case has no row in the diff tables to apply ({v['kind']})", "disputed fixtures excluded", v, flags="NO_DIFF_ROW")
        else:
            unforeseen.append(dict(case_id=cid, case_type=ct, season=h["season"], club=h["club"], player=h["player"]))
            if cfg["unforeseen_case_types"] == "STOP":
                raise fb.Stop(f"STOP (unforeseen_case_types = STOP): dispute type {ct!r} is not recognised (case {cid})")
            led(h, "EXCLUDED", f"unforeseen_case_types = EXCLUDE_AND_FLAG: dispute type {ct} not recognised", "disputed fixtures excluded", v, flags="UNFORESEEN")

    # ---------------- duplicate ids (merge on name + DOB; settings kesler_hayden_merge and identity_links = MERGE_FILE)
    pairs, both_named = dup_pairs(S, apps)
    merges = []                                                           # (drop, keep, why) applied to every file of the set
    for keep, drop, how in pairs:
        merges.append((drop, keep, how))
    file_pairs = set()
    if cfg["identity_links"] == "MERGE_FILE":
        _mf = pd.read_csv(cfg["identity_merges"], dtype=str, keep_default_na=False)
        file_pairs = {frozenset((int(a_), int(b_))) for a_, b_ in zip(_mf.sm_id, _mf.merge_into) if re.fullmatch(r"\d+", str(b_).strip())}
    for tup, named, info in both_named:
        ids = sorted(named, key=lambda i: -named[i])
        keep = ids[0]
        for drop in ids[1:]:
            (n1, d1), (n2, d2) = info.get(keep, ("", "")), info.get(drop, ("", ""))
            sc = M4.name_score(str(n1), str(n2)) if n1 and n2 else 0
            if {keep, drop} == {28912779, 37259159}:
                if cfg["kesler_hayden_merge"]:
                    merges.append((37259159, 28912779, "switch kesler_hayden_merge (premierleague.com person 53074)"))
                else:
                    state["merge_skipped"].append(dict(input_set=set_name, ids=f"{keep} / {drop}", why="kesler_hayden_merge = false"))
            elif sc >= 1 and d1 and d1 == d2:
                merges.append((drop, keep, f"both named, name score {sc}, same DOB {d1}"))
            elif frozenset((keep, drop)) in file_pairs:
                pass                                                      # decided in identity_merges.csv (premierleague.com person record)
            else:
                state["merge_skipped"].append(dict(input_set=set_name, ids=f"{keep} / {drop}", why=f"both named; name score {sc}, DOB {d1!r} vs {d2!r}: not name + DOB; "
                                                   "no premierleague.com person record decides it in identity_merges.csv: listed, not guessed"))
    if cfg["identity_links"] == "MERGE_FILE":
        mf = pd.read_csv(cfg["identity_merges"], dtype=str, keep_default_na=False)
        for r in mf.itertuples():
            if re.fullmatch(r"\d+", str(r.merge_into).strip()):             # a Sportmonks id: a true id merge
                merges.append((int(r.sm_id), int(r.merge_into), f"identity_merges.csv: {r.reason}"))
    ids_in_set = set(pd.to_numeric(sq.player_id.map(pid_num), errors="coerce").dropna().astype(int)) | set(apps.player_id.dropna().astype(int)) \
        | set(pd.to_numeric(tr.player_id.map(pid_num), errors="coerce").dropna().astype(int))
    merges = [(a, b, w) for a, b, w in dict(((a, b), (a, b, w)) for a, b, w in merges).values() if a in ids_in_set]
    for drop, keep, why in merges:
        s_sel = sq.player_id.map(pid_num) == drop
        t_sel = tr.player_id.map(pid_num) == drop
        state["merges"].append(dict(input_set=set_name, drop_id=drop, keep_id=keep, why=why, squad_rows=int(s_sel.sum()), transfer_rows=int(t_sel.sum()),
                                    appearance_rows=int((apps.player_id == drop).sum())))
        if (apps.player_id == drop).sum() == 0:                           # the unnamed twin's squad rows go, its records are re-keyed
            removed.append(sq[s_sel].assign(removed_because=f"duplicate id {drop} (unnamed twin of {keep})"))
            sq = sq[~s_sel]
        else:
            sq.loc[s_sel, "player_id"] = str(keep); sq.loc[s_sel, "q_flag"] = f"DUP_REKEYED from {drop}"
            sq = sq.drop_duplicates(["team_id", "season_id", "player_id"], keep="first")
        for i in tr[t_sel].index:
            r = tr.loc[i]
            same = tr[(tr.player_id.map(pid_num) == keep) & (tr.date.astype(str).str[:10] == str(r.date)[:10]) & (tr.type_id == r.type_id)
                      & (tr.from_team_id.fillna(-1) == (r.from_team_id if pd.notna(r.from_team_id) else -1))]
            if len(same):
                removed.append(tr.loc[[i]].assign(removed_because=f"duplicate id {drop}: record already held by {keep}"))
                tr = tr.drop(i)
            else:
                tr.loc[i, "player_id"] = str(keep); tr.loc[i, "q_flag"] = f"DUP_REKEYED from {drop}"
    state["set_merges"][set_name] = [(a, b) for a, b, _ in merges if (apps.player_id == a).sum() > 0]

    # ---------------- convert ids, validate (a blank from-club is accepted)
    sq["player_id"] = sq.player_id.map(pid_num).astype("Int64")
    tr["player_id"] = tr.player_id.map(pid_num).astype("Int64")
    bad, unm = validate_transfers(tr, teams)
    if len(bad):
        bad.to_csv(out / f"STOP_invalid_type_{set_name}.csv", index=False)
        raise fb.Stop(f"STOP (integrity): {len(bad)} transfer rows of set {set_name} have an invalid or blank type_id (must be 218/219/9688/220); "
                      f"listed in {out}/STOP_invalid_type_{set_name}.csv")
    if unm:
        pd.DataFrame(unm).to_csv(out / f"STOP_unmapped_clubs_{set_name}.csv", index=False)
        raise fb.Stop(f"STOP (integrity): {len(unm)} transfer rows of set {set_name} name a club of our data with a null or placeholder id; "
                      f"listed in {out}/STOP_unmapped_clubs_{set_name}.csv")
    state["next_tid"] = nxt[0]
    return dict(sq=sq, tr=tr, teams=teams, club_name=club_name, sids=sids, apps=apps, ledger=ledger, excl_cases=excl_cases, removed=removed,
                added_sq=added_sq, added_tr=added_tr, notapp=notapp, unforeseen=unforeseen, merges=merges)


# ------------------------------------------------------------------ contradicted undated squad rows
def remove_contradicted(res, seasons, fixtures):
    """A squad row (undated) of a PL club-season whose player is not named for the club that season is left out when a
    dated record contradicts it: Sportmonks' own records, or a Transfermarkt move written with an independent verdict
    (provenance not 'TM'). A Transfermarkt date with no verdict never removes a squad row.
      ARRIVES_AFTER_END      no dated record at the club on or before the season end, the first one after it is an
                             arrival, and no naming for the club before that date;
      DEPARTED_BEFORE_START  the last dated record at the club before the season start is a departure, nothing at the
                             club inside the season, the next record (if any) is after the season end, and no naming for
                             the club between the departure and the season end; a loan-out needs a dated return after
                             the season end."""
    sq, tr, club_name, sids, apps = res["sq"], res["tr"], res["club_name"], res["sids"], res["apps"]
    t = tr[(tr.provenance != "TM") & tr.date.notna()].copy()
    t["d"] = pd.to_datetime(t.date, errors="coerce")
    t = t[t.d.notna() & t.player_id.notna()]
    recs = {}
    for r in t.itertuples():
        pid = int(r.player_id)
        for tid, nm, kind in ((r.to_team_id, r.to_team, "in"), (r.from_team_id, r.from_team, "out")):
            if not pd.isna(tid):
                recs.setdefault((pid, int(tid)), []).append((r.d, kind, int(r.type_id)))
    for k in recs:
        recs[k].sort()
    apps = apps[apps.player_id.notna()]
    named = set(zip(apps.season_id.astype(int), apps.team_id.astype(int), apps.player_id.astype(int)))
    cand = set(zip(pd.to_numeric(sq.player_id, errors="coerce").fillna(-1).astype(int), sq.team_id.astype(int)))
    a2 = apps[[k in cand for k in zip(apps.player_id.astype(int), apps.team_id.astype(int))]]
    nam = {(int(p), int(c)): sorted(pd.to_datetime(g.date).dt.normalize()) for (p, c), g in a2.groupby(["player_id", "team_id"])}
    drop, rows = [], []
    sid_season = {v: k for k, v in sids.items()}
    for i, r in zip(sq.index, sq.itertuples()):
        s = sid_season.get(int(r.season_id))
        if s not in seasons or pd.isna(r.player_id):
            continue
        pid, K = int(r.player_id), int(r.team_id)
        if (int(r.season_id), K, pid) in named:
            continue
        rr = recs.get((pid, K))
        if not rr:
            continue
        s0, s1 = fixtures[s]
        before = [x for x in rr if x[0] < s0]
        inside = [x for x in rr if s0 <= x[0] <= s1]
        after = [x for x in rr if x[0] > s1]
        nm = nam.get((pid, K), [])
        cls = None
        if not before and not inside and after and after[0][1] == "in" and after[0][2] in (218, 219, 220) and not [d for d in nm if d < after[0][0]]:
            cls = "ARRIVES_AFTER_END"
        elif before and not inside and before[-1][1] == "out" and not [d for d in nm if before[-1][0] < d <= s1]:
            if before[-1][2] in (219, 220) or (before[-1][2] == 218 and after and after[0][1] == "in" and after[0][2] == 9688):
                cls = "DEPARTED_BEFORE_START"
        if cls:
            drop.append(i)
            rows.append(dict(season=s, team_id=K, club=club_name.get(K), player_id=pid, player=r.player, reason=cls,
                             key_record=str((before[-1] if cls.startswith("DEP") else after[0])[0].date()), provenance=r.provenance))
    res["sq"] = sq.drop(index=drop)
    return rows


# ------------------------------------------------------------------ the stage
def run(cfg, root, base_run, sized, log, xa=False, matchday=None, sets=("early", "mid", "late")):
    """sized = {"late": (dispute list with sizes, size detail), "early": (...)}. Writes <root>/reconciled/ and returns a
    summary. sets = the input sets reconciled (those of the configured seasons)."""
    t0 = time.time()
    out = Path(root) / "reconciled"
    out.mkdir(parents=True, exist_ok=True)
    V = Verdicts(cfg, log)
    state = dict(next_tid=SYNTH_TID0, merges=[], merge_skipped=[], set_merges={}, xa=xa, matchday=matchday, link_tm={}, link_sm_ids=set(), link_rows=[],
                 auto_overrides=[])
    if cfg["identity_links"] == "MERGE_FILE":
        mf = pd.read_csv(cfg["identity_merges"], dtype=str, keep_default_na=False)
        for r in mf.itertuples():
            tgt = str(r.merge_into).strip().upper()
            if tgt.startswith("TM"):
                state["link_tm"][tgt] = str(r.sm_id).strip()
                state["link_sm_ids"].add(str(r.sm_id).strip())
            state["link_rows"].append(dict(sm_id=r.sm_id, merge_into=r.merge_into, kind="Transfermarkt link" if tgt.startswith("TM") else
                                           ("premierleague.com link (matchday rows, prepare stage)" if tgt.startswith("PL") else "Sportmonks id merge"), reason=r.reason))
    # the never-checked gap-fill rows, sized: member row -> its case, size on the first member
    gfp = settings.inp("gapfill_cases")
    state["gf"], gf_detail = {}, pd.DataFrame()
    if gfp.exists():
        for r in pd.read_csv(gfp, low_memory=False).itertuples():
            mem = [m for m in str(r.member_case_ids).split(";") if m]
            for i, m in enumerate(mem):
                state["gf"][m] = dict(case_id=r.case_id, size=float(r.size_xu_min), n=0 if pd.isna(r.n_disputed) else int(r.n_disputed), primary=(i == 0))
        gf_detail = pd.read_csv(settings.inp("gapfill_size_detail"), low_memory=False)
    src = {k: Source(k) for k in ("late", "early") if any(SETS[st]["src"] == k for st in sets)}
    results, ledger = {}, []
    for st in [x for x in ("early", "mid", "late") if x in sets]:
        S = src[SETS[st]["src"]]
        H, D = sized[S.name]
        results[st] = reconcile_set(st, S, H, D, V, cfg, out, log, state)
        ledger += results[st]["ledger"]

    # ---- contradicted squad rows + write the input files
    files, contradicted_rows = {}, []
    for st, res in results.items():
        fx = pd.read_csv(matchday(st, "fixtures"), usecols=["season_id", "date"])
        fx["date"] = pd.to_datetime(fx.date).dt.normalize()
        b = fx.groupby("season_id").date.agg(["min", "max"])
        fixtures = {s: (b.loc[sid, "min"], b.loc[sid, "max"]) for s, sid in res["sids"].items() if sid in b.index}
        rr = remove_contradicted(res, SETS[st]["seasons"], fixtures)
        contradicted_rows += [dict(input_set=st, **x) for x in rr]
        d = out / st
        d.mkdir(exist_ok=True)
        sq, tr = res["sq"], res["tr"].copy()
        sq[SQ_COLS + ["provenance", "q_flag"]].to_csv(d / "squads_provenance.csv", index=False)
        tr[TR_COLS + ["provenance", "q_flag"]].to_csv(d / "transfers_provenance.csv", index=False)
        tr["date"] = pd.to_datetime(tr.date, errors="coerce").dt.strftime("%Y-%m-%d")
        for c in ("from_team_id", "to_team_id"):
            tr[c] = pd.to_numeric(tr[c], errors="coerce").astype("Int64")
        tr["type_id"] = tr.type_id.astype("int64")
        tr["transfer_id"] = tr.transfer_id.astype("int64")
        sq[SQ_COLS].to_csv(d / "squads.csv", index=False)
        tr[TR_COLS].to_csv(d / "transfers.csv", index=False)
        files[st] = dict(squads=d / "squads.csv", transfers=d / "transfers.csv")
        # identity merges in the matchday and contract files (text-level: only the id column changes)
        mm = state["set_merges"].get(st, [])
        if mm:
            mp = {str(a): str(b) for a, b in mm}
            for f in ("appearances", "events", "contracts"):
                srcp = matchday(st, f) if f in fb.MATCHDAY else fb.sm_file(st, f)
                x = pd.read_csv(srcp, dtype=str, keep_default_na=False)
                for col in [c for c in ("player_id", "related_player_id") if c in x.columns]:
                    key = x[col].str.replace(r"\.0$", "", regex=True)
                    hit = key.isin(mp)
                    x.loc[hit, col] = key[hit].map(mp)
                if f == "appearances":
                    x["_p"] = (x.played != "1").astype(int)
                    x = x.sort_values("_p", kind="stable").drop_duplicates(["fixture_id", "team_id", "player_id"], keep="first").sort_index().drop(columns="_p")
                x.to_csv(d / f"{f}.csv", index=False)
                files[st][f] = d / f"{f}.csv"

    # ---- West Ham: the US-club records Sportmonks files under team 1 (completed = False)
    whu, whu_ex = [], []
    t = pd.read_csv(fb.sm_file("late", "transfers")).drop_duplicates("transfer_id")
    t = t[(t.completed == False) & ((t.to_team_id == 1) | (t.from_team_id == 1))]   # noqa: E712
    for r in t.itertuples():
        whu.append(dict(case_id=f"WHU-{int(r.transfer_id)}", source="WHU", input_set="late", in_hand_list=False, marker="WEST_HAM_US_RECORD",
                        season="", team_id=1, club="West Ham United", case_type="SM_RECORD_WRONG_CLUB (completed = False)", player=r.player,
                        sm_player_id=int(r.player_id), tm_player_id=None, size_xu_min=0.0, over_bar=False, n_disputed=0, minutes_at_stake=0,
                        verdict="", verdict_kind="NONE", verdict_source="", outcome="EXCLUDED",
                        basis="no verdict; the player is excluded at West Ham United for every fixture (not in RET, flagged)",
                        action=f"exclusion {r.date}: {r.from_team} -> {r.to_team} type {r.type_id}", flags="", source_url=""))
        whu_ex.append(dict(player_id=int(r.player_id), team_id=1, **{"from": "2014-07-01", "to": FAR}, action="EXCLUDE", case_id=f"WHU-{int(r.transfer_id)}"))
    ledger += whu

    # ---- exclusions: manual overrides first, then the disputes without a settling verdict
    ex = []
    mo = pd.read_csv(cfg["manual_overrides"], dtype=str, keep_default_na=False)
    for r in mo.to_dict("records"):
        act = r["action"].strip().upper()
        if act not in ("RETAIN", "NOT_RETAIN", "EXCLUDE"):
            raise fb.Stop(f"STOP (integrity): manual_overrides.csv action {r['action']!r} is not RETAIN / NOT_RETAIN / EXCLUDE")
        ex.append(dict(player_id=pid_num(r["sm_player_id"]), team_id=int(r["team_id"]), **{"from": r["from"], "to": r["to"]}, action=act,
                       case_id="MANUAL: " + r["reason"]))
    for a_ in state["auto_overrides"]:                                    # OTHER roster verdicts with evidenced dates (after the manual rows)
        ex.append(dict(a_, player_id=pid_num(a_["player_id"])))
    L = pd.DataFrame(ledger)
    for c_ in ("gapfill_case_id", "gapfill_verdict_case_id"):
        L[c_] = L[c_].fillna("") if c_ in L.columns else ""
    excl_ids = set(L[(L.outcome == "EXCLUDED") & L.in_hand_list].case_id)
    excl_gf = set(L[(L.outcome == "EXCLUDED") & ~L.in_hand_list & (L.gapfill_case_id != "")].gapfill_case_id) - set(L[(L.outcome != "EXCLUDED") & (L.gapfill_case_id != "")].gapfill_case_id)
    # an OTHER verdict applied through manual_overrides.csv: the rows of the file govern the dates they cover (they come
    # first); any disputed fixture they do not cover stays excluded
    man_cases = {str(r["reason"]).split(" ")[0] for r in mo.to_dict("records")}
    hitm = L.case_id.isin(man_cases) & (L.outcome == "EXCLUDED")
    L.loc[hitm, "outcome"] = "APPLIED"
    L.loc[hitm, "basis"] = "OTHER verdict applied through manual_overrides.csv (evidenced status and dates); disputed fixtures the rows do not cover stay excluded"
    L.loc[hitm, "action"] = "manual RETAIN / NOT_RETAIN rows"
    # a partly settled case: the evidenced part is applied, a manual EXCLUDE row leaves the rest out
    for r in mo.to_dict("records"):
        if r["action"].strip().upper() == "EXCLUDE":
            cid = str(r["reason"]).split(" ")[0]
            hit = ((L.case_id == cid) | (L.gapfill_verdict_case_id == cid) | (L.gapfill_case_id == cid)) & (L.outcome == "APPLIED")
            note = f"partly settled: disputed fixtures {r['from']}..{r['to']} EXCLUDED (manual_overrides.csv)"
            L.loc[hit, "flags"] = [note if blank(f) else f"{f}; {note}" for f in L.loc[hit, "flags"]]
    n_fx = {}
    for nm in ("late", "early", "GF"):
        D = gf_detail if nm == "GF" else (sized[nm][1] if nm in sized else None)
        if D is None or D.empty:
            continue
        dd = D[D.case_id.isin(excl_gf if nm == "GF" else excl_ids)]
        for r in dd.itertuples():
            pid = getattr(r, "player_id_used", None)
            if blank(pid):
                pid = r.sm_id if not blank(r.sm_id) else (fb.TM_PLAYER_BASE + int(float(r.tm_id)) if not blank(r.tm_id) else None)
            if blank(pid):
                continue
            ex.append(dict(player_id=int(float(pid)), team_id=int(r.team_id), **{"from": str(r.date)[:10], "to": str(r.date)[:10]},
                           action="EXCLUDE", case_id=r.case_id))
            n_fx[r.case_id] = n_fx.get(r.case_id, 0) + 1
    Hall_ = pd.concat([sized[k][0] for k in ("late", "early") if k in sized], ignore_index=True).set_index("case_id")
    for cid, dates in V.except_dates.items():
        if cid in Hall_.index:
            h = Hall_.loc[cid]
            pid = pid_num(h.sm_player_id) or (fb.TM_PLAYER_BASE + int(float(h.tm_player_id)))
            for d in dates:
                ex.insert(len(mo), dict(player_id=pid, team_id=int(str(h.team_id).split("/")[0]), **{"from": d, "to": d}, action="EXCLUDE",
                                        case_id=f"{cid} (verdict correction: fixture excluded)"))
    ex += whu_ex
    X = pd.DataFrame(ex, columns=["player_id", "team_id", "from", "to", "action", "case_id"])
    X.to_csv(out / "retention_overrides.csv", index=False)
    L["exclusion_fixtures"] = [n_fx.get(c, 0) if o == "EXCLUDED" else 0 for c, o in zip(L.case_id, L.outcome)]

    # ---- origin overrides: senior record, resolved unknown origins, Transfermarkt origin-club rule for placeholder origins
    ov, senior_rows = {}, []
    tierfill = {"DATA_CLUB": cfg["data_club_fill"], "T1": cfg["tier1_fill"], "T2": cfg["tier2_fill"], "T3": cfg["tier3_fill"], "YOUTH": cfg["youth_fill"]}
    uo = pd.read_csv(settings.inp("unknown_origin_resolved"), dtype={"sm_player_id": str})
    tn = pd.read_csv(fb.sm_file("late", "teams")).drop_duplicates("team_id")
    tid_of = {fb.norm_club(n): int(i) for n, i in zip(tn.name, tn.team_id)}
    for r in uo.itertuples():
        if r.tier in tierfill and fb.norm_club(r.club) in tid_of:
            ov[(pid_num(r.sm_player_id), tid_of[fb.norm_club(r.club)])] = (float(tierfill[r.tier]), f"unknown origin resolved: {r.tier} ({r.origin_league})")
    senior_path = settings.inp("senior_record")
    senior = pd.read_csv(senior_path, dtype={"sm_player_id": str})
    senior_src = settings.rel_data(senior_path)
    # REQUIRE_SECOND: a SENIOR class (a senior record before arrival, so a fill above 0) counts only when the second
    # source confirms it (result SENIOR_CONFIRMED); an unconfirmed one follows senior_unconfirmed
    # (FILL_ZERO: priced 0, as NO_SENIOR; EXCLUDE: the player-club is excluded). A NO_SENIOR class needs no second source.
    second, conf_cases, conf_players = None, set(), set()
    if cfg["senior_fill_source"] == "REQUIRE_SECOND":
        p = settings.inp("senior_second_source")
        second = pd.read_csv(p, dtype=str, keep_default_na=False) if p.exists() else pd.DataFrame(columns=["case_id", "result"])
        conf_cases = set(second[second.result == "SENIOR_CONFIRMED"].case_id)
        for cid in conf_cases:
            if cid in Hall_.index:
                h = Hall_.loc[cid]
                for K_ in str(h.team_id).split("/"):
                    for pid_ in (pid_num(h.sm_player_id), None if blank(h.tm_player_id) else fb.TM_PLAYER_BASE + int(float(h.tm_player_id)),
                                 pid_num(state["link_tm"].get(str(h.sm_player_id)))):
                        if pid_ is not None:
                            conf_players.add((pid_, int(K_)))
    senior_ex = []
    for r in senior.to_dict("records"):
        pid, K, cls = pid_num(r["sm_player_id"]), int(r["team_id"]), r["class"]
        how, cls_eff = "TM_ALONE", cls
        if second is not None and cls == "SENIOR":
            if r["case_id"] in conf_cases or (pid, K) in conf_players:
                how = "REQUIRE_SECOND: confirmed by the second source"
            else:
                how = f"REQUIRE_SECOND: no second source -> senior_unconfirmed = {cfg['senior_unconfirmed']}"
                if cfg["senior_unconfirmed"] == "EXCLUDE":
                    senior_ex.append(dict(player_id=pid, team_id=K, **{"from": "2014-07-01", "to": FAR}, action="EXCLUDE", case_id=f"SENIOR-{r['case_id']}"))
                    cls_eff = "EXCLUDED"
                else:
                    cls_eff = "NO_SENIOR"
        if cls_eff == "NO_SENIOR":
            ov[(pid, K)] = (0.0, f"senior record: NO_SENIOR ({how})")
        senior_rows.append(dict(case_id=r["case_id"], player=r["player"], player_id=pid, team_id=K, season=r["season"], class_tm=cls, used_as=cls_eff, how=how,
                            arrival_date=r.get("arrival_date")))
    # arrivals written from Transfermarkt whose origin club Sportmonks lacks (placeholder id): the origin-club rule as the sizing priced it
    place_rows, origin_rule = [], []
    for st, res in results.items():
        S = src[SETS[st]["src"]]
        D = sized[S.name][1]
        dfill = {}
        if D is not None and not D.empty and "tm_fill" in D.columns:
            for r in D[D.tm_fill.notna()].itertuples():
                pid = getattr(r, "player_id_used", None)
                if blank(pid):
                    pid = r.sm_id if not blank(r.sm_id) else (fb.TM_PLAYER_BASE + int(float(r.tm_id)) if not blank(r.tm_id) else None)
                if not blank(pid):
                    dfill[(int(float(pid)), int(r.team_id), str(r.tm_arrival)[:10])] = (float(r.tm_fill), str(r.tm_class), str(r.tm_label))
        for a in res["added_tr"]:
            if a["type_id"] not in (218, 219, 220) or blank(a["to_team_id"]):
                continue
            ph = blank(a["from_team_id"]) or int(a["from_team_id"]) >= PLACE
            pid = pid_num(a["player_id"])
            key = (pid, int(a["to_team_id"]), str(a["date"])[:10])
            hit = dfill.get(key)
            if hit is None:                                               # any sized arrival of the player-club (a linked player was sized under his TM id)
                ids_ = {pid} | {pid_num(k) for k, x in state["link_tm"].items() if pid_num(x) == pid}
                c = [v for k, v in dfill.items() if k[0] in ids_ and k[1] == int(a["to_team_id"])]
                hit = c[-1] if c else None
            if ph:
                place_rows.append(dict(input_set=st, player_id=pid, player=a["player"], team_id=int(a["to_team_id"]), date=a["date"], from_team=a["from_team"],
                                       from_team_id=a["from_team_id"], tm_fill=None if hit is None else hit[0], tm_class=None if hit is None else hit[1],
                                       priced=("origin-club rule (override)" if hit is not None else "compute: unknown tier / youth name")))
            if hit is not None and (ph or st != "late") and (pid, int(a["to_team_id"])) not in ov:
                fill_, how_ = hit[0], "TM_ALONE"
                # REQUIRE_SECOND: a senior origin outside our data needs the second source; a club of our data is its own record
                if second is not None and fill_ > 0 and hit[1] == "SENIOR" and "DATA_CLUB" not in hit[2]:
                    if (pid, int(a["to_team_id"])) in conf_players or a.get("case_id") in conf_cases:
                        how_ = "REQUIRE_SECOND: confirmed by the second source"
                    else:
                        how_ = f"REQUIRE_SECOND: no second source -> senior_unconfirmed = {cfg['senior_unconfirmed']}"
                        if cfg["senior_unconfirmed"] == "EXCLUDE":
                            senior_ex.append(dict(player_id=pid, team_id=int(a["to_team_id"]), **{"from": "2014-07-01", "to": FAR}, action="EXCLUDE",
                                              case_id=f"SENIOR-{a.get('case_id')}"))
                        fill_ = 0.0
                ov[(pid, int(a["to_team_id"]))] = (fill_, f"Transfermarkt origin-club rule (as the sizing priced it): {hit[1]} {hit[2][:80]} [{how_}]")
                origin_rule.append(dict(input_set=st, season=a["season"], player_id=pid, player=a["player"], team_id=int(a["to_team_id"]), club=a["club"],
                                        arrival=a["date"], from_team=a["from_team"], fill=fill_, fill_tm=hit[0], tm_class=hit[1], label=hit[2], senior_rule=how_))
    if senior_ex:
        X = pd.concat([X, pd.DataFrame(senior_ex).drop_duplicates(["player_id", "team_id"])], ignore_index=True)
        X.to_csv(out / "retention_overrides.csv", index=False)
    O = pd.DataFrame([dict(player_id=k[0], team_id=k[1], fill=v[0], why=v[1]) for k, v in sorted(ov.items()) if k[0] is not None])
    O.to_csv(out / "origin_overrides.csv", index=False)

    # ---- lists
    L.to_csv(Path(root) / "ledger.csv", index=False)
    summ = L[L.season.astype(str) != ""].groupby(["season", "outcome"]).agg(cases=("case_id", "size"), minutes=("size_xu_min", "sum"),
                                                                             over_bar=("over_bar", "sum")).round(1).reset_index()
    summ.to_csv(Path(root) / "ledger_summary.csv", index=False)

    def dump(rows, name, cols=None):
        pd.DataFrame(rows, columns=cols).to_csv(out / name, index=False)
    dump(V.disagree, "verdicts_disagreeing.csv", ["case_id", "verdicts"])
    dump(V.conflicts_resolved, "verdicts_conflicts_resolved_by_hierarchy.csv", ["case_id", "verdicts", "winner"])
    gl = L[L.gapfill_verdict_case_id != ""].groupby("gapfill_verdict_case_id").agg(members=("case_id", "size"), outcomes=("outcome", lambda v: "+".join(sorted(set(v)))),
                                                         season=("season", "first"), club=("club", "first"), player=("player", "first")).reset_index()
    gv = pd.DataFrame(V.g_rows)
    if len(gv):
        gl = gl.merge(gv[["case_id", "verdict", "evidence_types", "evidenced_event", "evidenced_from", "evidenced_to"]].rename(columns={"case_id": "gapfill_verdict_case_id"}), on="gapfill_verdict_case_id", how="outer")
    gl.to_csv(out / "gapfill_verdict_outcomes.csv", index=False)
    dump(V.corrections, "verdict_corrections_applied.csv", ["case_id", "player", "club", "season", "verdict_before", "verdict_applied", "fixtures_excluded", "applied", "reason"])
    dump(state["link_rows"], "identity_links_applied.csv", ["sm_id", "merge_into", "kind", "reason"])
    dump(V.downgraded, "verdicts_other_club_downgraded.csv", ["case_id", "source", "player", "verdict", "verdict_excl_other_club", "rule", "urls"])
    dump(sum((r["notapp"] for r in results.values()), []), "verdicts_not_applicable.csv", ["case_id", "case_type", "player", "verdict", "evidence", "why"])
    dump(sum((r["unforeseen"] for r in results.values()), []), "unforeseen.csv", ["case_id", "case_type", "season", "club", "player"])
    dump(contradicted_rows, "squad_rows_removed_contradicted.csv", ["input_set", "season", "team_id", "club", "player_id", "player", "reason", "key_record", "provenance"])
    dump(state["merges"], "identity_merges_applied.csv", ["input_set", "drop_id", "keep_id", "why", "squad_rows", "transfer_rows", "appearance_rows"])
    dump(state["merge_skipped"], "identity_merges_skipped.csv", ["input_set", "ids", "why"])
    dump(senior_rows, "senior_record_players.csv")
    dump(origin_rule, "origin_club_rule_players.csv")
    dump(place_rows, "placeholder_origin_arrivals.csv")
    dump(whu, "west_ham_us_records.csv")
    dump(sum(([dict(input_set=st, **a) for a in r["added_sq"]] for st, r in results.items()), []), "added_squad_rows.csv")
    dump(sum(([dict(input_set=st, **a) for a in r["added_tr"]] for st, r in results.items()), []), "added_transfer_rows.csv")
    rem = [x.assign(input_set=st) for st, r in results.items() for x in r["removed"] if len(x)]
    (pd.concat(rem, ignore_index=True) if rem else pd.DataFrame()).to_csv(out / "removed_rows.csv", index=False)

    # ---- C1 (STOP on fail): every hand-list case has exactly one outcome with size and bar flag
    Hall = pd.concat([sized[k][0] for k in ("late", "early") if k in sized], ignore_index=True)
    lh = L[L.in_hand_list]
    cnt = lh.case_id.value_counts()
    missing = sorted(set(Hall.case_id) - set(lh.case_id))
    multi = sorted(cnt[cnt > 1].index)
    bad_out = lh[~lh.outcome.isin(["APPLIED", "EXCLUDED", "ADDED_NO_VERDICT"])]
    no_size = lh[lh.size_xu_min.isna() | lh.over_bar.isna()]
    c1 = dict(hand_list_cases=int(len(Hall)), ledger_hand_rows=int(len(lh)), missing=len(missing), multiple=len(multi), bad_outcome=int(len(bad_out)),
              no_size=int(len(no_size)), west_ham_records=len(whu), result="PASS" if not (missing or multi or len(bad_out) or len(no_size)) else "FAIL")
    info = dict(c1=c1, seconds=round(time.time() - t0, 1), files={k: {a: str(b) for a, b in v.items()} for k, v in files.items()},
                origin_overrides=str(out / "origin_overrides.csv"), retention_overrides=str(out / "retention_overrides.csv"),
                outcomes=L.outcome.value_counts().to_dict(), hand_outcomes=lh.outcome.value_counts().to_dict(),
                exclusion_rows=int(len(X)), origin_override_rows=int(len(O)), contradicted_squad_rows_removed=len(contradicted_rows), merges=len(state["merges"]),
                disagreeing=len(V.disagree), other_club_downgraded=len(V.downgraded), not_applicable=sum(len(r["notapp"]) for r in results.values()),
                unforeseen=sum(len(r["unforeseen"]) for r in results.values()), verdict_corrections=V.corrections,
                conflicts_resolved=len(V.conflicts_resolved), manual_override_rows=int(len(mo)), manual_cases=sorted(man_cases & set(L.case_id)),
                gapfill_cases_excluded=len(excl_gf),
                identity_links=len(state["link_rows"]), verdict_sources=V.sources, senior_record_source=senior_src,
                added_squad_rows=sum(len(r["added_sq"]) for r in results.values()), added_transfer_rows=sum(len(r["added_tr"]) for r in results.values()),
                placeholder_arrivals=len(place_rows), placeholder_unpriced=sum(1 for p in place_rows if p["tm_fill"] is None))
    (out / "reconcile_info.json").write_text(json.dumps(info, indent=1, default=str))
    log(f"  reconcile: ledger {len(L)} rows ({len(lh)} hand-list); outcomes {info['hand_outcomes']}; squad rows added {info['added_squad_rows']}, "
        f"transfer rows added {info['added_transfer_rows']}; exclusion rows {len(X)}; origin overrides {len(O)}; contradicted squad rows removed {len(contradicted_rows)}; "
        f"merges {len(state['merges'])}; C1 {c1['result']}")
    if c1["result"] != "PASS":
        pd.DataFrame(dict(case_id=missing)).to_csv(out / "C1_missing_cases.csv", index=False)
        raise fb.Stop(f"STOP (C1): ledger incomplete: {c1}")
    return info
