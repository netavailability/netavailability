"""Checks C2-C7 on a finished run (reported in checks.csv, never stopping the run). C1 (every dispute has exactly one
ledger outcome) runs inside the reconcile stage and stops the run on failure.

  C2  two clubs on one date: no player is in two clubs' retention windows at once, and no player is charged by two
      clubs on one date
  C3  presence: every premierleague.com named player-match is named in the compute's input (presence.py)
  C4  the sum of exclusive xU of the named players per team-fixture is close to 11 (target 11, tolerance 0.5)
  C5  no placeholder teams: arrivals from clubs Sportmonks lacks are priced by the origin-club rule, not the unknown tier
  C6  mechanism tests on small test inputs: a never-named squad player is charged every fixture; a Transfermarkt-dated
      loan-out stops the charges (with and without a return row); the review-format converter
  C7  named cases follow their verdicts
plus run_comparison.csv: per season, the sideways-on tables against the base run and the sideways-off run.
"""
import os, shutil
import pandas as pd

from . import common as fb
from . import settings


def run_checks(run):
    """run = the pipeline's Run. Writes checks.csv and the detail files; returns ({check: PASS|FAIL|REPORT}, rows)."""
    from . import presence
    from . import reconcile as R
    root, cfg, seasons = run.root, run.cfg, run.seasons
    on, off, base = root / "run_on", root / "run_off", run.proot("run_base") / "run_base"
    rows = []

    def add(check, season, value, result, detail=""):
        rows.append(dict(check=check, season=season, value=value, result=result, detail=detail))
    L = pd.read_csv(root / "ledger.csv", low_memory=False)
    # C2 two clubs on one date
    rem = pd.read_csv(root / "two_club_remaining.csv") if (root / "two_club_remaining.csv").stat().st_size > 5 else pd.DataFrame()
    clo = pd.read_csv(root / "two_club_closures.csv") if (root / "two_club_closures.csv").stat().st_size > 5 else pd.DataFrame()
    dbl = []
    for s in seasons:
        tr = fb.table(on, "absence_trace", s)
        g = tr.groupby(["player_id", "date"]).team_id.nunique()
        for (pid, d) in g[g > 1].index:
            sub = tr[(tr.player_id == pid) & (tr.date == d)]
            dbl.append(dict(season=s, player_id=pid, player=sub.player.iloc[0], date=d, clubs=" / ".join(sorted(sub.club.unique())), minutes=round(sub.minutes.sum(), 1)))
        n_rem = int((rem.season == s).sum()) if len(rem) else 0
        n_clo = int(((clo.season == s) & clo.applied).sum()) if len(clo) else 0
        n_dbl = sum(1 for x in dbl if x["season"] == s)
        add("C2 two clubs on one date", s, n_rem, "PASS" if n_rem == 0 and n_dbl == 0 else "REPORT",
            f"{n_clo} overlaps closed at the new club's arrival; {n_rem} window overlaps remain (two_club_remaining.csv); {n_dbl} same-date double charges")
    pd.DataFrame(dbl, columns=["season", "player_id", "player", "date", "clubs", "minutes"]).to_csv(root / "two_club_double_charges.csv", index=False)
    # C3 presence (needs the premierleague.com extracts, which the public data do not include)
    if not settings.data_path("premierleague").exists() or not settings.inp("identity_pending_rows").exists():
        add("C3 presence", "", "", "SKIPPED", "skipped in the public run: needs the premierleague.com match-page extracts (not distributed)")
    else:
        try:
            presence.main(["--inputs", str(root / "inputs"), "--out", str(root / "c3"), "--sets", *run.sets])
            P = pd.read_csv(root / "c3" / "c3_presence.csv")
            for r in P.itertuples():
                add("C3 presence: premierleague.com named player-matches named in the compute", r.season + (" (look-back)" if r.scope != "checked" else ""),
                    int(r.missing_outside_identity_pending), r.result,
                    f"{r.matched_in_ours} of {r.pl_named_player_matches} matched; {r.missing_identity_pending} identity-pending; extra {r.extra_in_ours}")
        except Exception as e:                                             # reported, not stopping
            add("C3 presence", "", "", "ERROR", repr(e)[:300])
    # C4 sum of xU of the named per team-fixture
    for s in seasons:
        cal = fb.table(on, "calibration", s)
        ts = pd.concat([cal.home_sum_xU, cal.away_sum_xU])
        add("C4 sum of exclusive xU of the named per team-fixture (target ~11)", s, round(ts.mean(), 3), "PASS" if abs(ts.mean() - 11) <= 0.5 else "REPORT",
            f"min {ts.min():.2f} max {ts.max():.2f} over {len(ts)} team-fixtures")
    # C5 placeholder teams
    ph = pd.read_csv(root / "reconciled/placeholder_origin_arrivals.csv") if (root / "reconciled/placeholder_origin_arrivals.csv").stat().st_size > 5 else pd.DataFrame()
    unpriced = []
    if len(ph):
        pairs = {(int(a), int(b)) for a, b in zip(ph.player_id, ph.team_id)}
        for s in seasons:
            pt = fb.table(on, "player_table", s)
            x = pt[[(int(a), int(b)) in pairs for a, b in zip(pt.player_id, pt.team_id)]]
            x = x[(x.origin_tier == "unknown") & ((x.NET > 0) | (x.NETabsence > 0))]
            for r in x.itertuples():
                unpriced.append(dict(season=s, player_id=r.player_id, player=r.player, club=r.club, origin_from=r.origin_from, origin_tier=r.origin_tier, fill=r.fill,
                                     NET=r.NET, NETabsence=r.NETabsence))
    pd.DataFrame(unpriced).to_csv(root / "c5_placeholder_priced_unknown.csv", index=False)
    add("C5 no placeholder teams", "all", len(unpriced), "PASS" if not unpriced else "REPORT",
        f"{len(ph)} arrivals written from clubs Sportmonks lacks (placeholder or blank id); {int(ph.tm_fill.notna().sum()) if len(ph) else 0} priced by the origin-club rule; "
        f"{len(unpriced)} player-club-seasons priced at the unknown tier with minutes (c5_placeholder_priced_unknown.csv)")
    # C6 mechanism tests a / b / b2 / c (small test inputs under <data>/tests/)
    if "2019/2020" in seasons and not (base / "runs.csv").exists():
        add("C6 mechanism tests a, b, b2", "2019/2020", "", "SKIPPED", "skipped in the public run: needs the base run and test inputs of the full chain (run.py --full-chain)")
    if "2019/2020" in seasons and (base / "runs.csv").exists():
        c6 = root / "c6"
        tests_dir = settings.data_path("tests")
        binp = run.proot("inputs_base") / "inputs_base" / "late"
        tests = {"a": dict(squads=tests_dir / "squads_testA.csv"), "b": dict(transfers=tests_dir / "transfers_testB.csv"),
                 "b2": dict(transfers=tests_dir / "transfers_testB2.csv")}
        jobs = []
        for k, t in tests.items():
            d = c6 / k / "in"
            if d.parent.exists():
                shutil.rmtree(d.parent)
            d.mkdir(parents=True)
            fb.link_shared(d)
            for f in fb.FILES:
                os.symlink((binp / f"{f}.csv").resolve(), d / f"{f}.csv")
            for f, src in t.items():
                (d / f"{f}.csv").unlink()
                x = pd.read_csv(src, dtype={"player_id": str})
                (R.convert_review_format(sq=x) if f == "squads" else R.convert_review_format(tr=x)).to_csv(d / f"{f}.csv", index=False)
            jobs.append((k, fb.compute_cmd("2019/2020", d, c6 / k / "run" / "2019-2020", f"_test-{k}", cfg, True, window_table=run.window_table())))
        for k, cmd in jobs:
            fb.run_seasons([dict(season="2019/2020", input_set="late + test " + k, cmd=cmd)], c6 / k / "run", 1, lambda *_: None)
        bt = fb.table(base, "absence_trace", "2019/2020", parse_dates=["date"])
        pa = fb.table(c6 / "a" / "run", "player_table", "2019/2020")
        cl = pa[(pa.player_id == 1202) & (pa.team_id == 8)]
        ok = len(cl) == 1 and int(cl.E.iloc[0]) == 38 and int(cl.N.iloc[0]) == 0 and float(cl.NETabsence.iloc[0]) > 1500
        add("C6 mechanism test a: never-named squad player (Clyne, Liverpool 2019/20) is charged every fixture", "2019/2020",
            "" if not len(cl) else f"E {int(cl.E.iloc[0])} N {int(cl.N.iloc[0])} xU {float(cl.xU.iloc[0]):.4f} NETabsence {float(cl.NETabsence.iloc[0]):.1f}",
            "PASS" if ok else "FAIL", "expected: E 38, xU about 0.53, about 1,800 min")
        cut = pd.Timestamp("2020-06-22")
        base_after = bt[(bt.player_id == 1920) & (bt.team_id == 8) & (bt.date > cut)]
        for k in ("b", "b2"):
            tt = fb.table(c6 / k / "run", "absence_trace", "2019/2020", parse_dates=["date"])
            aft = tt[(tt.player_id == 1920) & (tt.team_id == 8) & (tt.date > cut)]
            add(f"C6 mechanism test {k}: Transfermarkt-dated loan-out (Matip, 22 Jun 2020" + (", with return row 1 Aug 2020)" if k == "b2" else ", no return row)")
                + " stops the charges", "2019/2020", f"{len(aft)} absences after 22 Jun 2020, {aft.minutes.sum():.1f} min (base run: {len(base_after)}, {base_after.minutes.sum():.1f})",
                "PASS" if len(aft) == 0 and len(base_after) > 0 else "FAIL",
                f"loan_return_2019_20 = {cfg['loan_return_2019_20']}" + ("" if k == "b2" else " (under the 1 July nominal end the July 2020 fixtures would be charged again)"))
    tc = pd.read_csv(settings.data_path("tests", "transfers_testC_5rows.csv"), dtype={"player_id": str})
    conv = R.convert_review_format(tr=tc)
    teams = pd.read_csv(fb.sm_file("late", "teams"))
    bad, unm = R.validate_transfers(conv, teams)
    okc = len(bad) == 1 and len(unm) == 2 and int(conv.player_id.iloc[0]) == 900123456 and conv.transfer_id.notna().all()
    add("C6 mechanism test c: converter on the 5-row review-format file", "", f"{len(conv) - len(bad) - 1} rows convert; STOP faults: {len(bad)} blank/invalid type, {len(unm)} unmapped data club",
        "PASS" if okc else "FAIL", "expected: rows 1-3 convert (TM123456 -> 900123456, blank transfer id filled), row 4 blank type and row 5 Tottenham null/placeholder id stop the run")
    # C7 named cases
    if "2019/2020" in seasons:
        pt = fb.table(on, "player_table", "2019/2020")
        tr = fb.table(on, "absence_trace", "2019/2020", parse_dates=["date"])
        c = pt[(pt.player_id == 1202) & (pt.team_id == 8)]
        late = tr[(tr.player_id == 1202) & (tr.team_id == 8) & (tr.date > pd.Timestamp("2020-06-30"))]
        lc = L[(L.case_type == "AUDIT_ROSTER_TM_ONLY") & (L.player.astype(str).str.contains("Clyne")) & (L.season == "2019/2020")]
        okc7 = len(c) == 1 and int(c.E.iloc[0]) > 0 and len(late) == 0
        add("C7 Clyne, Liverpool 2019/20 follows his verdict (at the club to 30 Jun 2020, not for the July fixtures)", "2019/2020",
            "" if not len(c) else f"E {int(c.E.iloc[0])} A {int(c.A.iloc[0])} NETabsence {float(c.NETabsence.iloc[0]):.1f}; absences after 30 Jun 2020: {len(late)}",
            "PASS" if okc7 else "REPORT", "ledger: " + ("; ".join(f"{r.outcome} ({r.basis})" for r in lc.itertuples()) or "no row"))
    if "2021/2022" in seasons:
        ptg = fb.table(on, "player_table", "2021/2022")
        sg = ptg[ptg.player.astype(str).str.contains("Sigur") & (ptg.team_id == 13)]
        lsg = L[(L.season == "2021/2022") & L.player.astype(str).str.contains("Sigur")]
        add("C7 Sigurdsson, Everton 2021/22 is charged", "2021/2022",
            "" if not len(sg) else f"E {int(sg.E.iloc[0])} A {int(sg.A.iloc[0])} NETabsence {float(sg.NETabsence.iloc[0]):.1f}",
            "PASS" if len(sg) and float(sg.NETabsence.iloc[0]) > 0 else "REPORT", "ledger: " + "; ".join(f"{x.case_type} {x.outcome} [verdict {x.verdict_kind}]" for x in lsg.itertuples()))
    for nm, pid, K, s, cts in (("Matty James, Leicester 2015/16", 2237, 42, "2015/2016", ("AUDIT_ROSTER_TM_ONLY", "ROSTER_TM_ONLY")),
                               ("Kaboul, Sunderland 2016/17", 73, 3, "2016/2017", ("TM_ONLY", "TWO_CLUBS_SAME_DATE"))):
        if s not in seasons:
            continue
        ptx = fb.table(on, "player_table", s)
        r = ptx[(ptx.player_id == pid) & (ptx.team_id == K)]
        ll = L[(L.season == s) & L.case_type.isin(cts) & (L.sm_player_id.astype(str).str.replace(r"\.0$", "", regex=True) == str(pid))]
        mins = float(r.NETabsence.iloc[0]) if len(r) else 0.0
        E_ = int(r.E.iloc[0]) if len(r) else 0
        outs = set(ll.outcome)
        if "James" in nm:
            consistent = (mins == 0) if outs <= {"EXCLUDED"} or (ll.verdict_kind == "SM").all() else (mins > 0)
        else:
            consistent = E_ <= 5
        add(f"C7 {nm} follows the third-round verdict (EXCLUDED if none)", s, f"E {E_}, NETabsence {mins:.1f}", "PASS" if consistent and len(ll) else "REPORT",
            "ledger: " + "; ".join(f"{x.case_type} {x.outcome} [verdict {x.verdict_kind or 'NONE'}] ({x.basis})" for x in ll.itertuples()))
    # comparison per season: sideways on against the base run and against sideways off
    cmp_rows = []
    for s in seasons:
        new = fb.table(on, "club_table", s).set_index("team_id")
        basec = fb.table(base, "club_table", s).set_index("team_id").reindex(new.index) if (base / "runs.csv").exists() else None
        offc = fb.table(off, "club_table", s).set_index("team_id").reindex(new.index) if (off / "runs.csv").exists() else None
        row = dict(season=s, netabsence_new=int(new.NETabsence.sum()))
        if basec is not None:
            row.update(spearman_vs_base=round(new.NETavailability.rank().corr(basec.NETavailability.rank()), 4), netabsence_base=int(basec.NETabsence.sum()))
        if offc is not None:
            row.update(spearman_on_vs_off=round(new.NETavailability.rank().corr(offc.NETavailability.rank()), 4), netabsence_off=int(offc.NETabsence.sum()),
                       clubs_moved_on_vs_off=int((new.NETavailability.rank(ascending=False) != offc.NETavailability.rank(ascending=False)).sum()))
        cmp_rows.append(row)
    pd.DataFrame(cmp_rows).to_csv(root / "run_comparison.csv", index=False)
    C = pd.DataFrame(rows)
    C.to_csv(root / "checks.csv", index=False)
    res = C.groupby(C.check.str.split(":").str[0].str.split(" ").str[0]).result.agg(
        lambda v: "PASS" if v.isin(["PASS", "SKIPPED"]).all() and (v == "PASS").any() else ("FAIL" if (v == "FAIL").any() else ("SKIPPED" if (v == "SKIPPED").all() else "REPORT"))).to_dict()
    return res, len(C)
