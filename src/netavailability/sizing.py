#!/usr/bin/env python3
"""Sizing of every disputed record (Sportmonks versus Transfermarkt) at real xU, on a run folder of the unreconciled
inputs. A dispute that is worth `--bar` expected minutes or more needs an independent verdict before it may change the
inputs; a smaller one is left out of the charge when it has none.

  python -m netavailability.sizing --hand-list PATH --list late|early --base-run DIR --out DIR [--bar 180] [--jobs N]

--hand-list  a dispute list WITH a `disputed` column (each disputed fixture as date@team_id:kind): the late list
             (2018/19-2025/26) or the early list (2014/15-2017/18). The disputed fixtures are taken as given; only
             the sizing is computed, on the base run.
--base-run   a run folder (common.py's contract): runs.csv (one row per season, the exact compute command as a JSON
             list) and <season-tag>/<name>_<season-tag><SFX>.csv.
--list       which Transfermarkt squad pages and history fetches the list was built from (transfermarkt.py).

A dispute is worth sum xU x 90 over its disputed fixtures. Per disputed fixture:
  kind C (charged absent, Transfermarkt has him away) and A (charged absent; identity / two-clubs / ambiguous dispute):
    the player's traced xU x 90 at that fixture from the base run's absence_trace_*         -> basis TRACED
    (no trace row -> 0 minutes, note NO TRACE ROW)
  kind M (Transfermarkt has him at the club, not retained): the xU the method would give him there, evaluated by the
    compute's own xU_calc through a probe copy of the compute script named in the run's command
    (<out>/probe/<list>/<name>_probe.py = that file + a hook that, when NETAV_PROBE is set, evaluates xU at requested
    (player, club, date) points and returns before any table is built), run with the season's exact command (script
    path swapped, --out -> <out>/probe/<list>/<season-tag>):
    (1) a Sportmonks id with namings inside the compute window (an actual or carried slot) -> the method's xU from them
        -> NAMINGS_AT_CLUB (at least one slot at this club) / NAMINGS_CARRIED (only slots carried from other PL clubs)
    (2) else a Sportmonks arrival record at the club (the compute's own import origin) -> the method's xU with that
        origin's fill -> PROVISIONAL_FILL, or 0 when the fill is 0 (ZERO_YOUTH / ZERO_GK)
    (3) else Transfermarkt's arrival: the latest Transfermarkt move into the club set (club + own youth sides) dated on
        or before the fixture, end-of-loan returns excluded (not an arrival). None -> own academy -> 0 (ZERO_ACADEMY).
        From a youth / reserve / B side -> own youth = academy, 0; another club's youth side, 0 (ZERO_YOUTH). From a
        senior club -> the fill by origin as the method prices it (a club of the data 0.45, tier-1 country 0.5, England
        outside the data 0.35, other European 0.35, rest of the world 0.25, any other country = the unknown tier 0.35;
        a free agent -> his last senior club), keepers 0, then the method's xU_calc with that fill and the
        Transfermarkt arrival (+3 days) as arrival, so the fill expiry applies -> PROVISIONAL_FILL.
        "A club of the data" = a team of the teams file the run's command reads (the compute's data clubs).
Row: size_xu_min = sum over its disputed fixtures; size_basis = the bases met (joined with +); over_bar = size >= bar
(blank for unlinked rows). Probe validation: the probe at 300 traced absences per season must reproduce the traced
xU to 5e-5 (the trace stores 4 dp); STOP otherwise.

Writes in <out>/: hand_list_<list>_sized.csv, size_detail_<list>.csv, probe_validation_<list>.csv,
size_summary_<list>.csv, probe/<list>/ (probe copy, its diff, per-season scratch). Importable: main(argv=None) returns a
dict of the headline figures. Writes nothing outside <out>.
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from . import common as fb
from . import transfermarkt as TM

SYN0 = fb.TM_PLAYER_BASE                                    # id of a Transfermarkt-only player (no Sportmonks id): 900000000 + TM id
SIZE_COLS = ["size_xu_min", "size_basis", "over_bar", "disputed", "n_disputed", "size_fill_noexpiry_min", "unlinked"]
DETAIL_COLS = ["case_id", "season", "team_id", "date", "kind", "sm_id", "tm_id", "player_id_used", "xU", "minutes", "basis",
               "note", "tm_class", "tm_fill", "tm_arrival", "tm_label", "fill_noexpiry_min"]
# the method's fills by Transfermarkt origin (fixed here; they equal the [constants] of config/settings.toml)
FILL_DATA_CLUB, FILL_T1, FILL_T2, FILL_T3, FILL_UNKNOWN = 0.45, 0.5, 0.35, 0.25, 0.35

HOOK = '''    # ---- probe hook (NETAV_PROBE): evaluate xU at requested (player, club, date) points, then stop
    import os as _os
    if _os.environ.get("NETAV_PROBE"):
{probe_def}
        _pr = pd.read_csv(_os.environ["NETAV_PROBE"], parse_dates=["date", "arr_ov"])
        _rows = []
        for _r in _pr.itertuples():
            _x, _inf = xU_probe(int(_r.player_id), int(_r.team_id), _r.date, fill_ov=_r.fill_ov,
                                arr_ov=None if pd.isna(_r.arr_ov) else _r.arr_ov, use_ov=bool(_r.use_ov))
            _rows.append(dict(req_id=_r.req_id, xU=_x, **_inf))
        pd.DataFrame(_rows).to_csv(_os.environ["NETAV_PROBE_OUT"], index=False)
        print(f"probe: {{len(_rows)}} points written")
        return

'''


def make_probe(src_path, probe_dir, name=None):
    """The probe copy of a compute script: xU_calc duplicated as xU_probe (fill / arrival override) and a hook
    before '# ---- eligibility bases' that evaluates the requested points and returns. Written under probe_dir only."""
    src_path = Path(src_path)
    src = src_path.read_text()
    head = "    def xU_calc(pid, club, ref_date, exclusive=True, delta_override=None):\n"
    if src.count(head) != 1:
        raise fb.Stop(f"STOP: {src_path.name}: xU_calc signature not found exactly once; the probe cannot be built")
    a = src.index(head)
    b = src.index("        return xU, info\n", a) + len("        return xU, info\n")
    body = src[a:b]
    body = body.replace(head, "    def xU_probe(pid, club, ref_date, fill_ov=None, arr_ov=None, use_ov=False, exclusive=True, delta_override=None):\n")
    old = "        arr = arrival_eff(pid, club, ref_date)\n"
    if body.count(old) != 1:
        raise fb.Stop(f"STOP: {src_path.name}: arrival_eff call not found exactly once in xU_calc")
    body = body.replace(old, old + "        if use_ov:                                                        # probe override\n"
                                       "            fill = 0.0 if is_gk else float(fill_ov)\n"
                                       "            arr = arr_ov\n")
    body = "\n".join(("    " + l) if l else l for l in body.split("\n"))
    anchor = "    # ---- eligibility bases\n"
    if src.count(anchor) != 1:
        raise fb.Stop(f"STOP: {src_path.name}: anchor '# ---- eligibility bases' not found exactly once")
    new = src.replace(anchor, HOOK.format(probe_def=body.rstrip() + "\n") + anchor)
    probe_dir = Path(probe_dir)
    probe_dir.mkdir(parents=True, exist_ok=True)
    out = probe_dir / f"{name or src_path.stem}_probe.py"
    out.write_text(new)
    (probe_dir / f"{out.stem}_diff.txt").write_text("".join(difflib.unified_diff(
        src.splitlines(True), new.splitlines(True), fromfile=src_path.name, tofile=out.name)))
    return out


def run_probe(season, script, req, cmd, probe_dir):
    """The season's exact command with the script swapped for the probe copy and --out -> a scratch folder."""
    tg = fb.tag(season)
    d = Path(probe_dir) / tg
    d.mkdir(parents=True, exist_ok=True)
    fin, fout = d / f"probe_in_{tg}.csv", d / f"probe_out_{tg}.csv"
    if fout.exists():
        fout.unlink()
    req.to_csv(fin, index=False)
    cmd = list(cmd)
    cwd = str(Path(cmd[1]).resolve().parent)
    cmd[1] = str(script)
    if "--out" in cmd:
        cmd[cmd.index("--out") + 1] = str(d)
    else:
        cmd += ["--out", str(d)]
    env = dict(os.environ, NETAV_PROBE=str(fin), NETAV_PROBE_OUT=str(fout))
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)
    (d / f"probe_stdout_{tg}.txt").write_text(p.stdout + "\n--- stderr ---\n" + p.stderr)
    if p.returncode != 0 or not fout.exists():
        raise fb.Stop(f"STOP: probe {season} failed (rc {p.returncode}): {p.stderr[-800:]}")
    return pd.read_csv(fout)


def parse_disp(s):
    out = []
    if not isinstance(s, str) or not s:
        return out
    for x in s.split(";"):
        d, rest = x.split("@")
        k, kind = rest.split(":")
        out.append((pd.Timestamp(d), int(k), kind))
    return out


def arg_of(cmd, flag, default=None):
    return cmd[cmd.index(flag) + 1] if flag in cmd else default


class Sizer:
    """Transfermarkt side of one dispute list (late or early): squad pages, histories, the origin tiers."""

    def __init__(self, list_name):
        self.list = list_name
        self.hp = dict(TM.hist_paths(list_name))
        self.ids = TM.club_ids()
        self.ksets = TM.youth_sets(list_name)
        self._raw, self._fl, self._tm, self._teams = {}, None, {}, {}
        self.tm_club_map = TM.tm_to_sm()

    # -------------------------------------------------------------- Transfermarkt arrival
    def raw(self, tp):
        if tp not in self._raw:
            p = self.hp.get(tp)
            out = []
            if p is not None:
                for i, t in enumerate(json.loads(p.read_text()).get("transfers", [])):
                    def side(s):
                        m = re.search(r"/verein/(\d+)", t[s].get("href") or "")
                        f = re.search(r"/flagge/\w+/(\d+)\.png", t[s].get("countryFlag") or "")
                        return (int(m.group(1)) if m else None, t[s].get("clubName", ""), int(f.group(1)) if f else None)
                    dd = t.get("dateUnformatted") or ""
                    out.append(dict(order=-i, date="" if dd.startswith("0000") else dd, fee=t.get("fee", ""), frm=side("from"),
                                    to=side("to"), upcoming=bool(t.get("upcoming")) or bool(t.get("futureTransfer"))))
                out.sort(key=lambda r: (r["date"] or "9999", r["order"]))
            self._raw[tp] = out
        return self._raw[tp]

    def flag_map(self):
        """The country anchors (flag id -> tier-1 country / England), read off every cached history of the list."""
        if self._fl is None:
            fl = {}
            for tp in self.hp:
                for r in self.raw(tp):
                    for cid, name, f in (r["frm"], r["to"]):
                        if cid in TM.ANCHOR_T1 and f:
                            fl[f] = ("T1", TM.ANCHOR_T1[cid])
                        if cid == TM.ANCHOR_EN and f:
                            fl[f] = ("EN", "England")
            self._fl = fl
        return self._fl

    def teams(self, teams_file):
        if teams_file not in self._teams:
            self._teams[teams_file] = pd.read_csv(teams_file)
        return self._teams[teams_file]

    def team_maps(self, teams_file):
        if teams_file not in self._tm:
            t = self.teams(teams_file).drop_duplicates("team_id")
            by_name = {TM.nclub(n): (int(i), n) for i, n in zip(t.team_id, t.name)}
            self._tm[teams_file] = (self.tm_club_map, by_name, set(t.team_id.astype(int)))
        return self._tm[teams_file]

    def pl_clubs(self, teams_file, season):
        t = self.teams(teams_file)
        t = t[(t.league == "Premier League") & (t.season == season)]
        return dict(zip(t.team_id.astype(int), t.name))

    def tier_of(self, side, hist_before, club, teams_file):
        """Origin tier of a Transfermarkt club, with 'a club of the data' = a team of the run's input teams file (the
        compute's data clubs)."""
        cid, name, f = side
        YRE, M4 = TM.YRE, TM
        if cid in (515,):
            last = [x for x in hist_before if x["to"][0] not in (515,) and not YRE.search(x["to"][1] or "")]
            if last:
                src = last[-1]["to"]
                t, lab, n = self.tier_of(src, [x for x in hist_before if x["date"] < last[-1]["date"]], club, teams_file)
                return t, f"free agent; last senior club {src[1]} -> {lab}", n
            return "YOUTH", "free agent whose only earlier clubs are youth sides -> youth rule", 0.0
        if YRE.search(name or ""):
            if M4.club_like(YRE.sub("", name), club):
                return "OWN_YOUTH", "own youth side (academy, not an arrival)", 0.0
            return "YOUTH", "another club's youth / reserve / B side (--youth-fill 0)", 0.0
        m, by_name, data = self.team_maps(teams_file)
        smt, flag = TM.sm_team(cid, name, m, by_name)
        if not flag and smt in data:
            return "DATA_CLUB", "a club in our data (season input teams)", FILL_DATA_CLUB
        fl = self.flag_map()
        if f in fl and fl[f][0] == "T1":
            return "T1", fl[f][1], FILL_T1
        if f in fl and fl[f][0] == "EN":
            return "T2", "England (outside our data)", FILL_T2
        if f in TM.FLAG_COUNTRY:
            c, reg = TM.FLAG_COUNTRY[f]
            return ("T2", f"{c} (other European senior)", FILL_T2) if reg == "EU" else ("T3", f"{c} (rest of world)", FILL_T3)
        return "UNKNOWN", f"flag id {f} not classified -> the compute's unknown tier", FILL_UNKNOWN

    def tm_arrival(self, tp, club, d, teams_file, kset, kad=None):
        """(class, fill, arrival record date, label) for TM player tp at the club on fixture date d. With no cached
        history, the squad page's own 'joined' date and 'signed from' club stand in for the move (tier by name; the
        date gives the C1 expiry)."""
        h = [e for e in self.raw(tp) if e["date"] and not e["upcoming"]]
        if not self.raw(tp):
            if kad is not None and isinstance(kad.get("joined"), str) and re.fullmatch(r"\d\d/\d\d/\d{4}", kad["joined"]):
                jd = pd.to_datetime(kad["joined"], format="%d/%m/%Y")
                frm = str(kad.get("signed_from") or "").split(":")[0].strip()
                t, lab, fill = self.tier_of((None, frm, None), [], club, teams_file)
                cls = {"OWN_YOUTH": "ACADEMY", "YOUTH": "YOUTH"}.get(t, "SENIOR")
                return cls, fill, jd, f"no TM history; squad page joined {kad['joined']} from {frm}: {t} {lab}"
            return "NO_TM_HISTORY", FILL_UNKNOWN, None, "no cached TM history and no squad-page joined date -> unknown tier 0.35"
        into = [e for e in h if pd.Timestamp(e["date"]) <= d and e["to"][0] in kset and e["frm"][0] not in kset
                and "end of loan" not in str(e["fee"]).lower()]
        if not into:
            return "ACADEMY", 0.0, None, "no TM move into the club set before the fixture (own academy)"
        e = into[-1]
        t, lab, fill = self.tier_of(e["frm"], [x for x in h if x["date"] < e["date"]], club, teams_file)
        cls = {"OWN_YOUTH": "ACADEMY", "YOUTH": "YOUTH"}.get(t, "SENIOR")
        return cls, fill, pd.Timestamp(e["date"]), f"{e['date']} from {e['frm'][1]} ({e['fee']}): {t} {lab}"


def sm_int(sid):
    if isinstance(sid, (int, float)) and pd.notna(sid):
        return int(float(sid))
    if isinstance(sid, str) and re.fullmatch(r"\d+(\.0)?", sid.strip()):
        return int(float(sid))
    return None


def as_bool(v):
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes")
    return bool(v) if pd.notna(v) else False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hand-list", required=True)
    ap.add_argument("--list", required=True, choices=list(TM.LISTS))
    ap.add_argument("--base-run", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--bar", type=float, default=180.0)
    ap.add_argument("--jobs", type=int, default=min(12, os.cpu_count() or 4))
    a = ap.parse_args(argv)
    t0 = time.time()
    S, bar = a.list, a.bar
    run = Path(a.base_run).resolve()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    probe_dir = out / "probe" / S                            # per set, so Q and Y may share --out and run side by side
    H = pd.read_csv(a.hand_list)
    if "disputed" not in H.columns:
        raise fb.Stop(f"STOP: {a.hand_list} has no `disputed` column")
    if "unlinked" not in H.columns:
        H["unlinked"] = H.case_type.astype(str).str.startswith("UNLINKED_")
    H["unlinked"] = [as_bool(v) for v in H.unlinked]
    runs = pd.read_csv(run / "runs.csv")
    cmds = {r.season: json.loads(r.command) for r in runs.itertuples()}
    seasons = [s for s in runs.season if s in set(H.season)]
    miss = sorted(set(H.season) - set(seasons))
    if miss:
        raise fb.Stop(f"STOP: hand-list seasons not in {run / 'runs.csv'}: {miss}")
    Z = Sizer(S)
    teams_file = {s: str(Path(arg_of(cmds[s], "--pulls")) / f"teams{arg_of(cmds[s], '--meta-suffix', '')}.csv") for s in seasons}
    sfx = {s: arg_of(cmds[s], "--out-suffix") for s in seasons}
    pos_tm, kad_tm = {}, {}
    for s in seasons:
        for K, rows in TM.kader(S, s).items():
            for r in rows:
                pos_tm[(s, int(K), int(r["tm_player_id"]))] = str(r.get("position"))
                kad_tm[(s, int(K), int(r["tm_player_id"]))] = dict(joined=r.get("joined"), signed_from=r.get("signed_from"))
    # ---- probe copies (one per distinct compute script named in the run's commands)
    scripts, by_src = {}, {}
    for s in seasons:
        src = cmds[s][1]
        if src not in by_src:
            stem = Path(src).stem
            name = stem if stem not in {Path(x).stem for x in by_src} else f"{stem}_{len(by_src)}"
            by_src[src] = make_probe(src, probe_dir, name)
        scripts[s] = by_src[src]
    # ---- traces
    trace_df, traces = {}, {}
    for s in seasons:
        d = pd.read_csv(run / fb.tag(s) / f"absence_trace_{fb.tag(s)}{sfx[s]}.csv", parse_dates=["date"])
        trace_df[s] = d
        t = {}
        for p_, k_, dt, x, m in zip(d.player_id, d.team_id, d.date, d.xU, d.minutes):
            t.setdefault((int(p_), int(k_)), {})[dt] = (float(x), float(m))
        traces[s] = t
    clubs = {s: Z.pl_clubs(teams_file[s], s) for s in seasons}
    # ---- requests
    reqs = {s: [] for s in seasons}
    plan = []                                                    # one row per (case, disputed fixture)
    for r in H.itertuples():
        s = r.season
        sid_int = sm_int(r.sm_player_id)
        tp = int(r.tm_player_id) if pd.notna(r.tm_player_id) else None
        used = sid_int if sid_int is not None else (SYN0 + tp if tp is not None else None)
        for d, K, kind in parse_disp(r.disputed):
            row = dict(case_id=r.case_id, season=s, team_id=K, date=d, kind=kind, sm_id=sid_int, tm_id=tp, player_id_used=used)
            if kind in ("C", "A"):
                v = traces[s].get((used, K), {}).get(d) if used is not None else None   # the id the compute uses
                row.update(xU=None if v is None else v[0], minutes=0.0 if v is None else v[1], basis="TRACED",
                           note="" if v is not None else "NO TRACE ROW")
                plan.append(row)
                continue
            if kind != "M":
                raise fb.Stop(f"STOP: {r.case_id}: unknown disputed kind {kind!r}")
            if used is None:
                row.update(xU=0.0, minutes=0.0, basis="NO_ID", note="kind M with neither an SM id nor a TM id")
                plan.append(row)
                continue
            club = clubs[s][K]
            if tp is not None:
                cls, fill, adate, lab = Z.tm_arrival(tp, club, d, teams_file[s], Z.ksets[Z.ids[K][0]], kad_tm.get((s, K, tp)))
                if "Goalkeeper" in pos_tm.get((s, K, tp), ""):
                    fill, lab = 0.0, lab + "; TM position Goalkeeper -> keepers 0 (C2)"
                    cls = cls if cls in ("ACADEMY", "YOUTH") else "GK"
            else:
                cls, fill, adate, lab = "NO_TM_ID", FILL_UNKNOWN, None, "no TM id"
            n = len(reqs[s])
            reqs[s].append(dict(req_id=f"p{n}", player_id=used, team_id=K, date=d.date(), fill_ov=None, arr_ov=None, use_ov=0))
            reqs[s].append(dict(req_id=f"o{n}", player_id=used, team_id=K, date=d.date(), fill_ov=fill,
                                arr_ov=None if adate is None else (adate + pd.Timedelta(days=3)).date(), use_ov=1))
            row.update(req_plain=f"p{n}", req_ov=f"o{n}", tm_class=cls, tm_fill=fill, tm_arrival=adate, tm_label=lab,
                       has_sm_id=sid_int is not None)
            plan.append(row)
    # validation points: 300 traced absences per season, the plain probe must equal the trace
    val = {}
    for s in seasons:
        tr = trace_df[s]
        tr = tr.sample(min(300, len(tr)), random_state=1)
        val[s] = tr
        for i, r in enumerate(tr.itertuples()):
            reqs[s].append(dict(req_id=f"v{i}", player_id=int(r.player_id), team_id=int(r.team_id), date=r.date.date(),
                                fill_ov=None, arr_ov=None, use_ov=0))
    t_prep = time.time() - t0
    cols = ["req_id", "player_id", "team_id", "date", "fill_ov", "arr_ov", "use_ov"]
    with ThreadPoolExecutor(max(1, min(a.jobs, len(seasons)))) as ex:
        outs = dict(zip(seasons, ex.map(lambda s: run_probe(s, scripts[s], pd.DataFrame(reqs[s], columns=cols), cmds[s], probe_dir)
                                        .set_index("req_id"), seasons)))
    t_probe = time.time() - t0 - t_prep
    vrows = []
    for s in seasons:
        o = outs[s]
        for i, r in enumerate(val[s].itertuples()):
            vrows.append(dict(season=s, player_id=r.player_id, team_id=r.team_id, date=r.date.date(), trace_xU=r.xU,
                              probe_xU=o.loc[f"v{i}", "xU"], diff=o.loc[f"v{i}", "xU"] - r.xU))
    V = pd.DataFrame(vrows, columns=["season", "player_id", "team_id", "date", "trace_xU", "probe_xU", "diff"])
    V.to_csv(out / f"probe_validation_{S}.csv", index=False)
    vmax = float(V["diff"].abs().max()) if len(V) else 0.0
    print(f"list {S}: probe validation max |probe - trace| = {vmax:.3g} on {len(V)} traced absences ({len(seasons)} seasons)")
    if vmax > 5.01e-5:                                       # the trace stores xU rounded to 4 dp
        raise fb.Stop(f"STOP: the probe does not reproduce the traced xU (max diff {vmax:.3g}); see {out / f'probe_validation_{S}.csv'}")
    # ---- per-fixture values
    det = []
    for row in plan:
        if row["kind"] in ("C", "A") or "req_plain" not in row:
            det.append(row)
            continue
        o = outs[row["season"]]
        pl, ov = o.loc[row["req_plain"]], o.loc[row["req_ov"]]
        at_club = int(pl.slots_actual) - int(pl.slots_carried)
        sm_import = row["has_sm_id"] and int(pl.is_import) == 1
        if row["has_sm_id"] and int(pl.slots_actual) > 0:
            x, basis = float(pl.xU), "NAMINGS_AT_CLUB" if at_club > 0 else "NAMINGS_CARRIED"
            note = f"slots actual {at_club}, carried {int(pl.slots_carried)}, unseen {int(pl.slots_unseen)}, fill {pl.fill}"
        elif sm_import:
            x = float(pl.xU)
            basis = "PROVISIONAL_FILL" if float(pl.fill) > 0 else ("ZERO_GK" if int(pl.is_gk) else "ZERO_YOUTH")
            note = (f"SM arrival origin tier {pl.origin_tier}, fill {pl.fill}, arrival_eff {pl.arrival_eff}, "
                    f"fixtures since arrival {pl.fixtures_since_arrival}, filled slots {pl.slots_empty_filled}")
        else:
            x = float(ov.xU)
            c = row["tm_class"]
            basis = {"ACADEMY": "ZERO_ACADEMY", "YOUTH": "ZERO_YOUTH", "GK": "ZERO_GK"}.get(c, "PROVISIONAL_FILL")
            if basis.startswith("ZERO"):
                x = 0.0 if float(ov.slots_actual) == 0 else x
            note = (f"TM arrival {row['tm_label']}; fill {row['tm_fill']}; fixtures since arrival {ov.fixtures_since_arrival}, "
                    f"filled slots {ov.slots_empty_filled}, unseen {int(ov.slots_unseen)}")
        row.update(xU=round(x, 4), minutes=round(x * 90, 4), basis=basis, note=note,
                   fill_noexpiry_min=round(float(row["tm_fill"] if not sm_import else pl.fill) * 90, 4)
                   if basis == "PROVISIONAL_FILL" else None)
        det.append(row)
    Dt = pd.DataFrame(det).reindex(columns=DETAIL_COLS)
    Dt.to_csv(out / f"size_detail_{S}.csv", index=False)
    agg = Dt.groupby("case_id").agg(size_xu_min=("minutes", lambda v: round(float(pd.to_numeric(v).fillna(0).sum()), 1)),
                                    size_basis=("basis", lambda v: "+".join(sorted(set(v)))),
                                    n_disputed=("kind", "size"), n_missing_trace=("note", lambda v: int((v == "NO TRACE ROW").sum())),
                                    size_fill_noexpiry_min=("fill_noexpiry_min", lambda v: round(float(pd.to_numeric(v).fillna(0).sum()), 1)))
    base_cols = [c for c in H.columns if c not in SIZE_COLS and c != "disputed_note"]
    tail_cols = [c for c in H.columns if c == "disputed_note"]
    Hs = H.drop(columns=[c for c in ("size_xu_min", "size_basis", "over_bar", "n_disputed", "size_fill_noexpiry_min") if c in H.columns])
    Hs = Hs.merge(agg, left_on="case_id", right_index=True, how="left")
    Hs["size_xu_min"] = Hs.size_xu_min.fillna(0.0)
    Hs["size_fill_noexpiry_min"] = Hs.size_fill_noexpiry_min.fillna(0.0)
    Hs["n_disputed"] = Hs.n_disputed.fillna(0).astype(int)
    Hs.loc[Hs.size_basis.isna(), "size_basis"] = "NO_DISPUTED_FIXTURES"
    Hs["over_bar"] = [None if u else bool(v >= bar) for u, v in zip(Hs.unlinked, Hs.size_xu_min)]
    Hs = Hs.sort_values(["size_xu_min", "minutes_at_stake"], ascending=False, kind="stable")
    Hs = Hs.reindex(columns=base_cols + SIZE_COLS + tail_cols)
    Hs.to_csv(out / f"hand_list_{S}_sized.csv", index=False)
    ob = Hs.over_bar == True                                   # noqa: E712 (None for unlinked rows)
    g = Hs.assign(_ob=ob, _mo=Hs.size_xu_min.where(ob, 0.0), _mu=Hs.size_xu_min.where(Hs.unlinked, 0.0))
    summ = g.groupby(["season", "case_type"]).agg(cases=("case_id", "size"), cases_over_bar=("_ob", "sum"),
                                                  minutes_over_bar=("_mo", "sum"), minutes_all=("size_xu_min", "sum"),
                                                  cases_unlinked=("unlinked", "sum"), minutes_unlinked=("_mu", "sum")).reset_index()
    for c in ("minutes_over_bar", "minutes_all", "minutes_unlinked"):
        summ[c] = summ[c].round(1)
    summ["bar"] = bar
    summ.to_csv(out / f"size_summary_{S}.csv", index=False)
    n_m = int((Dt.kind == "M").sum())
    res = dict(set=S, cases=len(Hs), fixtures=len(Dt), fixtures_traced=int(Dt.kind.isin(["C", "A"]).sum()), fixtures_M=n_m,
               missing_trace=int(agg.n_missing_trace.sum()) if len(agg) else 0, probe_validation_max_diff=vmax,
               probe_validation_points=len(V), over_bar=int(ob.sum()), minutes_over_bar=round(float(Hs.size_xu_min[ob].sum()), 1),
               minutes_all=round(float(Hs.size_xu_min.sum()), 1), unlinked=int(Hs.unlinked.sum()),
               seconds=round(time.time() - t0, 1), seconds_probe=round(t_probe, 1), out=str(out))
    print(f"list {S}: {res['cases']} cases, {res['fixtures']} disputed fixtures (C/A traced {res['fixtures_traced']}, "
          f"M {n_m}; no trace row {res['missing_trace']}); size {res['minutes_all']} min; over bar {bar:g}: {res['over_bar']} cases, "
          f"{res['minutes_over_bar']} min; unlinked {res['unlinked']}; {res['seconds']}s (probes {res['seconds_probe']}s)")
    return res


if __name__ == "__main__":
    main()
