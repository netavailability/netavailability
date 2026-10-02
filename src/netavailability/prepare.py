"""Input preparation: match length, for every fixture of every input set.

  match length = the larger of the fixture's duration and the latest substitution (on or off) or dismissal time recorded
                 in that match (appearance rows' on_at / off_at, and the Substitution and non-rescinded dismissal events);
  then, for every row of that match: minutes = end - start (start = on_at, 0 for a starter; end = the earliest of
  sub-off and dismissal = the row's off_at, else the match length) and proportion = minutes / match length.

Why: the pull capped minutes at an estimated duration, so a player who went off (or was sent off) in long stoppage
time lost minutes, and a substitute's share was computed on too short a match. A dismissal the pull clamped to the
duration (off_at = duration on a sent-off row while the dismissal event is later) is unclamped to the event time first.
Substitution times beyond the duration are kept. The input files are only read: the adjusted appearances are written to
<out>/<set>/appearances.csv, changing only the cells that change (off_at, minutes, duration, proportion of rows in
stretched matches); every other byte of the file is kept. The fixtures file is not rewritten (the compute does not read
its duration); the per-fixture lengths are in match_length_<set>.csv.

With identity_links = MERGE_FILE, the matchday rows of a premierleague.com person linked in identity_merges.csv
(merge_into = PL<person id>) take premierleague.com's minutes (identity_pending_rows.csv gives them); the other pending
rows stay as Sportmonks has them.
"""
from pathlib import Path
import numpy as np
import pandas as pd

from . import common as fb
from . import settings

DISMISSAL = ("Redcard", "Yellow/Red card")


def fnum(x, nd):
    return repr(round(float(x), nd))


PENDING_SET = {"early": "hist", "mid": "1617", "late": "v3h"}       # input set -> its label in identity_pending_rows.csv


def apply_pl_links(set_name, a, T, link_pl):
    """The identity-pending matchday rows of a linked premierleague.com person take the premierleague.com minutes (the
    corrected matchday files left them as Sportmonks has them). The pending file gives premierleague.com's minutes; the
    difference is moved onto the row's on_at (a substitute) or off_at (a starter taken off)."""
    pend = pd.read_csv(settings.inp("identity_pending_rows"))
    pend = pend[pend["set"] == PENDING_SET[set_name]]
    rows, kept = [], pend[~pend.pl_person_id.isin(link_pl)]
    for r in pend[pend.pl_person_id.isin(link_pl)].itertuples():
        d = float(r.pl_minutes) - float(r.sm_minutes)
        sel = a.index[(a.fixture_id == r.sm_fixture_id) & (a.team_id == r.sm_team_id) & (a.player_id == r.sm_player_id)]
        done = "no change needed"
        if abs(d) > 0.05 and len(sel) == 1:
            i = sel[0]
            if pd.notna(a.at[i, "on_at"]) and a.at[i, "on_at"] > 0:
                a.at[i, "on_at"] = round(a.at[i, "on_at"] - d, 1); T.at[i, "on_at"] = repr(float(a.at[i, "on_at"]))
            elif pd.notna(a.at[i, "off_at"]):
                a.at[i, "off_at"] = round(a.at[i, "off_at"] + d, 1); T.at[i, "off_at"] = repr(float(a.at[i, "off_at"]))
            a.at[i, "minutes"] = round(float(r.pl_minutes), 1); T.at[i, "minutes"] = fnum(r.pl_minutes, 1)
            a.at[i, "proportion"] = round(a.at[i, "minutes"] / a.at[i, "duration"], 4); T.at[i, "proportion"] = fnum(a.at[i, "proportion"], 4)
            done = "minutes set to premierleague.com's"
        elif abs(d) > 0.05:
            done = f"NOT APPLIED: {len(sel)} rows match"
        rows.append(dict(input_set=set_name, pl_person_id=r.pl_person_id, pl_name=r.pl_name, sm_player_id=r.sm_player_id, season=r.season, date=r.date,
                         match=r.match, sm_minutes=r.sm_minutes, pl_minutes=r.pl_minutes, result=done))
    return rows, kept.assign(input_set=set_name, flag="identity pending: kept as Sportmonks has it")


def prepare_set(set_name, app_path, ev_path, teams_path, out_dir, link_pl=None, corrected=False):
    out_dir = Path(out_dir)
    (out_dir / set_name).mkdir(parents=True, exist_ok=True)
    T = pd.read_csv(app_path, dtype=str, keep_default_na=False)          # text, written back byte-for-byte where unchanged
    a = pd.read_csv(app_path)
    link_rows, kept = apply_pl_links(set_name, a, T, link_pl or set()) if settings.inp("identity_pending_rows").exists() and corrected else ([], pd.DataFrame())
    pd.DataFrame(link_rows).to_csv(out_dir / f"identity_linked_matchday_rows_{set_name}.csv", index=False)
    kept.to_csv(out_dir / f"identity_pending_kept_{set_name}.csv", index=False)
    ev = pd.read_csv(ev_path)
    teams = pd.read_csv(teams_path).drop_duplicates("season_id")
    lg, sn = dict(zip(teams.season_id, teams.league)), dict(zip(teams.season_id, teams.season))
    played = a.played == 1
    dur = a.groupby("fixture_id").duration.max()
    resc = ev.rescinded.astype(str).str.lower().eq("true")
    dis = ev[ev.type.isin(DISMISSAL) & ~resc & ev.player_id.notna()]
    dis_t = dis.groupby(["fixture_id", "player_id"]).elapsed.min()
    # unclamp dismissals the pull cut at the duration
    key = list(zip(a.fixture_id, a.player_id))
    ev_dis = pd.Series([dis_t.get(k, np.nan) for k in key], index=a.index)
    unclamp = played & (a.sent_off == 1) & a.off_at.notna() & ((a.off_at - a.duration).abs() < 1e-6) & (ev_dis > a.duration + 1e-9)
    off = a.off_at.where(~unclamp, ev_dis)
    sub = ev[ev.type == "Substitution"]
    ev_lat = pd.concat([dis.groupby("fixture_id").elapsed.max(), sub.groupby("fixture_id").elapsed.max()], axis=1).max(axis=1)
    row_lat = pd.concat([a[played].groupby("fixture_id").on_at.max(), off[played].groupby(a.fixture_id[played]).max()], axis=1).max(axis=1)
    L = pd.DataFrame(dict(duration=dur, latest_row_time=row_lat.reindex(dur.index), latest_event_time=ev_lat.reindex(dur.index)))
    L["match_length"] = L[["duration", "latest_row_time", "latest_event_time"]].max(axis=1)
    L["stretch"] = (L.match_length - L.duration).round(4)
    fx1 = a.drop_duplicates("fixture_id").set_index("fixture_id")
    L["season_id"], L["date"] = fx1.season_id.reindex(L.index), fx1.date.reindex(L.index)
    L["league"], L["season"] = L.season_id.map(lg), L.season_id.map(sn)
    length = a.fixture_id.map(L.match_length)
    start = a.on_at.fillna(0.0)
    end = off.fillna(length)
    new_min = pd.Series(np.where(played, np.round(np.maximum(0.0, end - start), 1), 0.0), index=a.index)
    new_prop = (new_min / length).round(4)
    stretched = length > a.duration + 1e-9
    ch_min = (new_min - a.minutes).abs() > 0.0501
    ch_prop = (new_prop - a.proportion).abs() > 0.00006
    ch = ch_min | ch_prop | unclamp
    outside = int((ch & ~stretched).sum())
    for i in a.index[ch | stretched]:
        if stretched[i]:
            T.at[i, "duration"] = repr(float(length[i]))
        if unclamp[i]:
            T.at[i, "off_at"] = repr(float(off[i]))
        if ch_min[i] or stretched[i]:
            T.at[i, "minutes"] = fnum(new_min[i], 1)
        if ch_prop[i] or stretched[i]:
            T.at[i, "proportion"] = fnum(new_prop[i], 4)
    dst = out_dir / set_name / "appearances.csv"
    T.to_csv(dst, index=False)
    back = pd.read_csv(dst)
    assert len(back) == len(a) and list(back.columns) == list(a.columns)
    pl_ = back.played == 1
    assert ((back.minutes[pl_] - (back.off_at.fillna(back.duration) - back.on_at.fillna(0)).clip(lower=0)[pl_]).abs() < 0.0501).all(), "minutes != end - start"
    assert ((back.proportion - back.minutes / back.duration).abs() < 0.00006).all(), "proportion != minutes / match length"
    assert (back.proportion <= 1.00001).all(), "proportion above 1"
    same = [c for c in a.columns if c not in ("on_at", "off_at", "minutes", "duration", "proportion")]
    T0 = pd.read_csv(app_path, dtype=str, keep_default_na=False)
    assert T[same].equals(T0[same]), "a column other than on_at / off_at / minutes / duration / proportion changed"
    L.reset_index().to_csv(out_dir / f"match_length_{set_name}.csv", index=False)
    rows = a[ch][["fixture_id", "season_id", "date", "team_id", "player_id", "player", "role", "on_at", "off_at", "sent_off", "minutes", "duration", "proportion"]].copy()
    rows["off_at_new"], rows["minutes_new"], rows["match_length"], rows["proportion_new"] = off[ch], new_min[ch], length[ch], new_prop[ch]
    rows["dismissal_unclamped"] = unclamp[ch].astype(int)
    rows["league"], rows["season"] = rows.season_id.map(lg), rows.season_id.map(sn)
    rows.to_csv(out_dir / f"rows_changed_{set_name}.csv", index=False)
    a["dm"] = np.where(ch, new_min - a.minutes, 0.0)
    a["ch"] = ch.astype(int)
    a["league"], a["season"] = a.season_id.map(lg), a.season_id.map(sn)
    g1 = L.groupby(["league", "season"]).agg(fixtures=("duration", "size"), matches_stretched=("stretch", lambda s: int((s > 1e-9).sum())),
                                              largest_stretch=("stretch", "max"))
    g2 = a.groupby(["league", "season"]).agg(rows=("ch", "size"), rows_changed=("ch", "sum"), net_minutes=("dm", "sum"))
    S = g1.join(g2).reset_index()
    S.insert(0, "input_set", set_name)
    S["net_minutes"] = S.net_minutes.round(1)
    info = dict(input_set=set_name, source=settings.rel_data(app_path), fixtures=int(len(L)), matches_stretched=int((L.stretch > 1e-9).sum()),
                largest_stretch=float(L.stretch.max()), rows=int(len(a)), rows_changed=int(ch.sum()), rows_changed_outside_stretched=outside,
                dismissals_unclamped=int(unclamp.sum()), net_minutes=round(float(a.dm.sum()), 1), sha256=fb.sha(dst),
                identity_linked_rows=len(link_rows), identity_linked_rows_changed=sum(1 for x in link_rows if x["result"].startswith("minutes set")),
                identity_pending_rows_kept=int(len(kept)))
    return dst, S, info


def prepare(source, out_dir, log=print, cfg=None, corrected=False, sets=("early", "mid", "late")):
    """source(set, file) -> path of the set's matchday / teams file; corrected = the matchday files are the corrected set.
    Returns {set: prepared appearances path}, summary, infos."""
    out, summ, infos = {}, [], []
    link_pl = set()
    if cfg and cfg.get("identity_links") == "MERGE_FILE":
        mf = pd.read_csv(cfg["identity_merges"], dtype=str, keep_default_na=False)
        link_pl = {int(str(x).strip()[2:]) for x in mf.merge_into if str(x).strip().upper().startswith("PL")}
    for st in sets:
        dst, S, info = prepare_set(st, source(st, "appearances"), source(st, "events"), source(st, "teams"), out_dir, link_pl, corrected)
        out[st] = dst
        summ.append(S); infos.append(info)
        log(f"  match length, set {st}: {info['matches_stretched']} of {info['fixtures']} fixtures stretched (largest {info['largest_stretch']:.1f} min), "
            f"{info['rows_changed']} rows changed ({info['dismissals_unclamped']} dismissals unclamped), net {info['net_minutes']:+.1f} min; "
            f"identity-linked matchday rows {info['identity_linked_rows']} ({info['identity_linked_rows_changed']} changed), other identity-pending rows kept {info['identity_pending_rows_kept']}")
    S = pd.concat(summ, ignore_index=True)
    S.to_csv(Path(out_dir) / "match_length_summary.csv", index=False)
    pd.DataFrame(infos).to_csv(Path(out_dir) / "match_length_sets.csv", index=False)
    return out, S, infos
