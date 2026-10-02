"""Transfermarkt side of the reconciliation: club ids, a club's own youth sides, squad pages, cached player transfer
histories, and the mapping of a Transfermarkt club to a Sportmonks team. Read-only on local files under the data root;
nothing here contacts any website.

Two dispute lists use these data, each with the Transfermarkt files it was built from:
  late   the 2018/19-2025/26 disputes: squad pages transfermarkt/squads/<yyyy-yyyy>.csv (falling back to the
         2014/15-2021/22 parse transfermarkt/squads_2014_2022.csv), histories from fetches 1 and 2
  early  the 2014/15-2017/18 disputes: squad pages transfermarkt/squads/<yyyy-yyyy>.csv, histories from fetches 1, 2
         and 3 (the first fetch holding a player wins)
"""
import html
import json
import re
import unicodedata
from functools import lru_cache

import pandas as pd

from . import settings

LISTS = ("late", "early")


def stag(season):
    return season.replace("/", "-")


def y0(season):
    return int(season[:4])


# ------------------------------------------------------------------ club ids (Sportmonks team -> Transfermarkt club)
def club_ids():
    """team_id -> (tm_id, slug, source): the primary id file first, the secondary one for clubs it lacks."""
    e = pd.read_csv(settings.inp("tm_club_ids_primary"))
    f = pd.read_csv(settings.inp("tm_club_ids_secondary"))
    out = {int(r.team_id): (int(r.tm_id), r.tm_slug, "primary") for r in e.itertuples()}
    for r in f.itertuples():
        out.setdefault(int(r.team_id), (int(r.tm_id), r.tm_slug, "secondary"))
    return out


def tm_to_sm():
    """Transfermarkt club id -> Sportmonks team id (the primary id file first)."""
    m = {}
    for f in (settings.inp("tm_club_ids_primary"), settings.inp("tm_club_ids_secondary")):
        for r in pd.read_csv(f).itertuples():
            m.setdefault(int(r.tm_id), int(r.team_id))
    return m


# ------------------------------------------------------------------ a club's own youth / reserve / B sides
# Youth sides of each Premier League club (Transfermarkt id -> ids), read off the club names printed in the cached
# histories (e.g. 9249 = "Arsenal U21 / U23 / Res.", 6945 = "Palace U21 / U23", 6928 = "Spurs U18"). Name-based
# matching missed abbreviations, so the map is explicit.
YOUTH_IDS = {11: {9249, 5679, 50683}, 405: {6933, 12124}, 989: {14648, 38967}, 1148: {14997}, 1237: {9606, 39336},
             1132: {14466}, 603: {14460}, 631: {9250, 6918, 50677}, 873: {6950, 6945}, 29: {9261, 6920, 50769},
             931: {6942, 9262, 32580}, 1110: set(), 3008: {14482}, 399: {10161, 20116}, 1003: {39341, 14389},
             31: {9252, 6922, 50906}, 281: {9265, 6930, 50678}, 985: {9251, 5242, 50672}, 641: {6924}, 762: {9253, 6943},
             1123: {6898}, 1039: set(), 350: {12806, 8824}, 180: {36546, 6893}, 512: {24219, 14494}, 289: {12797},
             2288: {14626, 33616}, 148: {6928, 9254}, 1010: {10732}, 984: {29990, 6951}, 379: {9955, 9267}, 543: {24226}}
YRE = re.compile(r"(\bU\s?\d\d\b|\bYouth\b|\bAcademy\b|\bRes\.?$|\bReserves?\b|\bB$|\bII$|\bYth\.?$)", re.I)
# Further own youth / reserve / B sides, read off the club names in the cached histories (a scan of every youth-like
# name whose stem is the club; false stems such as Man Utd for Man City or West Brom for West Ham rejected by hand).
YOUTH_ADD = {405: {53183},              # A. Villa Yth.
             512: {53129},              # Stoke Academy
             703: {12799, 38588, 53108},  # Nottingham U18 / U21 / Yth. (Forest; Notts County prints "Notts Co.")
             873: {53100},              # C. Palace Yth.
             1110: {14629, 53325},      # Huddersf. U18, Huddersf. Yth.
             148: {51433},              # Tottenham Yth.
             289: {9264, 58235},        # Sunderland Res./U23, Sunderland Yth.
             379: {52975},              # West Ham Yth.
             399: {84125},              # Leeds Youth
             543: {12801, 54097},       # Wolves U18, Wolves Yth.
             603: {29793},              # Cardiff U21
             677: {10006, 26117},       # Ipswich U18, Ipswich U21
             762: {55899},              # Newcastle Yth.
             984: {52928},              # West Brom Yth.
             1003: {55415},             # Leicester Yth.
             1010: {37993, 51466},      # Watford U21/U23, Watford Yth.
             1031: {14619, 52906},      # Luton U18, Luton Academy
             1123: {33614, 53101},      # Norwich U21/U23, Norwich Yth.
             1132: {24214, 78412},      # (FC) Burnley U21/U23, Burnley Youth
             1148: {54704, 54705},      # Brentford B, Brentford Yth.
             1237: {54168},             # Brighton Yth.
             2288: {53127}}             # Swansea Yth.
# the same scan on the 2014/15-2017/18 clubs (used by the early list only)
YOUTH_ADD_EARLY = {1110: {130650},      # Huddersf. U23
                   3008: {19715},       # Hull City U23
                   641: {9256},         # Boro U21 / U23
                   1039: {12805, 33727}}  # QPR U18, QPR U21 / Queens Park U23


def youth_set(tm_id):
    return {tm_id} | YOUTH_IDS.get(tm_id, set())


def youth_sets(list_name):
    """Transfermarkt club id -> the club set (the club + its own youth sides) of every club of the id files."""
    add = {k: set(v) for k, v in YOUTH_ADD.items()}
    if list_name == "early":
        for _k, _v in YOUTH_ADD_EARLY.items():
            add[_k] = add.get(_k, set()) | _v
    out = {}
    for K, (tm_id, slug, _) in club_ids().items():
        out[tm_id] = youth_set(tm_id) | add.get(tm_id, set())
    return out


# ------------------------------------------------------------------ names (players and clubs)
STOP = {"de", "da", "dos", "das", "do", "van", "der", "den", "von", "di", "la", "le", "el", "junior", "jr"}
TRANSLIT = str.maketrans({"ø": "o", "Ø": "O", "æ": "ae", "Æ": "Ae", "ß": "ss", "ł": "l", "Ł": "L", "đ": "d", "Đ": "D",
                          "ı": "i", "œ": "oe", "Œ": "Oe", "þ": "th", "ð": "d"})


def norm(s):
    s = unicodedata.normalize("NFKD", str(s).translate(TRANSLIT)).encode("ascii", "ignore").decode().lower()
    s = s.replace("-", " ").replace("'", "").replace(".", " ")
    return [t for t in re.sub(r"[^a-z ]", " ", s).split() if t]


def nclub(s):
    drop = {"fc", "afc", "cf", "sc", "ac", "the", "club", "sv", "fk", "cd", "ud", "sl", "rc", "as", "us", "ss", "ssc", "de"}
    return " ".join(t for t in norm(s) if t not in drop)


def club_like(a, b):
    a, b = nclub(a), nclub(b)
    if not a or not b:
        return False
    return a == b or a in b or b in a or a.split()[0] == b.split()[0]


def name_score(a, b):
    """3 = same name, 2 = one name's tokens contain the other's or same last name and initial, 1 = same last name or a
    shared long non-first token, 0 = no match."""
    ta, tb = norm(a), norm(b)
    if not ta or not tb:
        return 0
    if ta == tb or "".join(ta) == "".join(tb):
        return 3
    if set(ta) <= set(tb) or set(tb) <= set(ta):
        return 2
    if ta[-1] == tb[-1] and ta[0][0] == tb[0][0]:
        return 2
    if ta[-1] == tb[-1]:
        return 1
    if {t for t in ta[1:] if len(t) >= 4 and t not in STOP} & {t for t in tb[1:] if len(t) >= 4 and t not in STOP}:
        return 1                                                 # a shared non-first token ("de Souza Costa"/"Souza")
    return 0


# ------------------------------------------------------------------ squad pages and transfer histories
def _squad_table(season):
    f = settings.data_path("transfermarkt", "squads", f"{stag(season)}.csv")
    return pd.read_csv(f, dtype={"tm_dob": str}).fillna({"tm_dob": ""}) if f.exists() else None


@lru_cache(None)
def _squads_2014_2022():
    return pd.read_csv(settings.inp("tm_squads_2014_2022"), dtype={"tm_dob": str}).fillna({"tm_dob": ""})


def kader(list_name, season):
    """team_id -> list of dicts (tm_player_id, tm_player, tm_dob, joined, signed_from, position) of the club's squad page."""
    sq = _squad_table(season)
    if sq is None:
        if list_name == "early":
            raise RuntimeError(f"Transfermarkt squad table missing for {season}")
        if y0(season) > 2021:
            raise RuntimeError(f"Transfermarkt squad table missing for {season}")
        sq = _squads_2014_2022()
        sq = sq[sq.season == season]
    return {int(K): g.to_dict("records") for K, g in sq.groupby("team_id")}


def squad_files(list_name):
    """The squad-page tables of a list (names and dates of birth of the Transfermarkt players)."""
    d = settings.data_path("transfermarkt", "squads")
    if list_name == "late":
        return [p for p in d.glob("*.csv") if y0(p.stem) >= 2018] + [settings.inp("tm_squads_2014_2022")]
    return sorted(p for p in d.glob("*.csv") if y0(p.stem) <= 2017)


HIST_FETCHES = {"late": ("fetch1", "fetch2"), "early": ("fetch1", "fetch2", "fetch3")}


@lru_cache(None)
def hist_paths(list_name):
    """tm_player_id -> path of the cached transfer-history JSON; the first fetch holding a player wins."""
    out = {}
    for i, fetch in enumerate(HIST_FETCHES[list_name]):
        d = settings.data_path("transfermarkt", "histories", fetch)
        ps = sorted(d.glob("*.json")) if list_name == "early" else list(d.glob("*.json"))
        for p in ps:
            if re.fullmatch(r"\d+", p.stem):
                out.setdefault(int(p.stem), p)
    return out


def parse_hist(js):
    """Per-player transfer history (Transfermarkt JSON) -> list of dicts oldest first."""
    d = json.loads(js)
    rows = []
    for i, t in enumerate(d.get("transfers", [])):
        def cid(side):
            m = re.search(r"/verein/(\d+)", t[side].get("href") or "")
            return int(m.group(1)) if m else None
        dt = t.get("dateUnformatted") or ""
        dt = "" if dt.startswith("0000") else dt              # an undated move is printed 0000-00-00
        rows.append(dict(order=-i, date=dt, season=t.get("season", ""),
                         from_id=cid("from"), from_name=t["from"].get("clubName", ""),
                         to_id=cid("to"), to_name=t["to"].get("clubName", ""), fee=t.get("fee", ""),
                         upcoming=bool(t.get("upcoming")) or bool(t.get("futureTransfer"))))
    rows.sort(key=lambda r: (r["date"] or "9999", r["order"]))
    return rows


def histories(list_name, ids=None):
    hp = hist_paths(list_name)
    keys = hp.keys() if ids is None else [i for i in ids if i in hp]
    return {k: parse_hist(hp[k].read_text()) for k in keys}


def tm_type(fee):
    f = str(fee).lower()
    if "end of loan" in f:
        return "loan_end"
    if "loan" in f:
        return "loan"
    return "permanent"


# ------------------------------------------------------------------ origin countries (by Transfermarkt flag id)
# Country ids are anchored on clubs: the flag printed for FC Barcelona (131), Bayern (27), Juventus (506), Paris SG (583),
# Benfica (294), Ajax (610) and Anderlecht (58) in the cached histories = Spain, Germany, Italy, France, Portugal,
# Netherlands, Belgium (tier 1). England = the flag of Arsenal (11).
ANCHOR_T1 = {131: "Spain", 27: "Germany", 506: "Italy", 583: "France", 294: "Portugal", 610: "Netherlands", 58: "Belgium"}
ANCHOR_EN = 11
# flag ids met in the unknown-origin rows that the anchors do not cover, read off the clubs that carry them in the
# cached histories: 24 = FK Sarajevo (Bosnia-Herzegovina, Europe); 26 = Corinthians / Atletico-MG (Brazil)
FLAG_COUNTRY = {24: ("Bosnia-Herzegovina", "EU"), 26: ("Brazil", "ROW")}


# ------------------------------------------------------------------ Transfermarkt club -> Sportmonks team
PLACE = 800000000                        # a club with no Sportmonks id: 800000000 + Transfermarkt club id
NULL_TM = {515, 123}                     # Without Club, Retired
# Transfermarkt short names of clubs in the teams file
TM_ALIAS = {"man utd": "manchester united", "man city": "manchester city", "sheff wed": "sheffield wednesday",
            "sheff utd": "sheffield united", "nott m forest": "nottingham forest", "nottm forest": "nottingham forest",
            "west brom": "west bromwich albion", "wolves": "wolverhampton wanderers", "spurs": "tottenham hotspur",
            "qpr": "queens park rangers", "boro": "middlesbrough", "palace": "crystal palace", "brighton": "brighton hove albion",
            "bournemouth": "bournemouth", "newcastle": "newcastle united", "leicester": "leicester city", "norwich": "norwich city",
            "peterborough": "peterborough united", "preston": "preston north end", "hudd": "huddersfield town"}
NAME_MAPPED = {}                         # (tm_id, tm_name) -> (team_id, name, rule)


def name_match(tm_name, by_name):
    """Teams-file club for a Transfermarkt club name: exact normalised name; Transfermarkt short-name alias; or a
    one-word name equal to the first word of exactly one club ("Charlton" -> Charlton Athletic). Youth / reserve / B
    sides never match."""
    raw = html.unescape(str(tm_name or ""))
    if not raw or YRE.search(raw):
        return None
    n = nclub(raw)
    if n in by_name:
        return by_name[n] + ("exact name",)
    a = TM_ALIAS.get(n)
    if a and nclub(a) in by_name:
        return by_name[nclub(a)] + ("TM short name",)
    toks = n.split()
    if len(toks) == 1:
        c = [v for k, v in by_name.items() if k.split()[0] == toks[0]]
        if len(c) == 1:
            return c[0] + ("one-word name = first word of one club",)
    return None


def sm_team(tm_id, tm_name, m, by_name):
    """(Sportmonks team id or None, flag)."""
    if tm_id is not None and not pd.isna(tm_id) and int(tm_id) in NULL_TM:
        return None, ""
    if tm_id is not None and not pd.isna(tm_id) and int(tm_id) in m:
        return m[int(tm_id)], ""
    x = name_match(tm_name, by_name)
    if x is not None:
        NAME_MAPPED[(None if tm_id is None or pd.isna(tm_id) else int(tm_id), str(tm_name))] = x
        return x[0], ""
    if tm_id is None or pd.isna(tm_id):
        return None, "NO_SM_TEAM"
    return PLACE + int(tm_id), "NO_SM_TEAM"


def type_id(tm_type_, fee):
    """Sportmonks transfer type of a Transfermarkt move: loan 218, loan end 9688, free 220, else transfer 219."""
    if tm_type_ == "loan":
        return 218
    if tm_type_ == "loan_end":
        return 9688
    return 220 if "free" in str(fee).lower() else 219
