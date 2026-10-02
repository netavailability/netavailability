"""The pipeline: one command from the input files to the tables, the checks, the calibration and the analyses.

  python run.py [--name RUN] [--stages s1 s2 ...] [--full-chain] [--with-switches] [--data-root DIR] [--config SETTINGS.toml]

Everything is written under <output_root>/<RUN>/ (settings.toml). Every rule is a setting of config/settings.toml; only
integrity failures stop a run (a missing input, check C1, a failed compute); everything else is reported.

Stages, in order (each writes <root>/stage_<name>.json with its timing and headline numbers):
  integrity   the settings and the input files are present; sha256 of every input
  reconciled  (published run, the default) the reconciled inputs of data/inputs/reconciled/ are taken as the reconcile
              stage's output; the stages prepare, base, size and reconcile are then not run
  prepare     match length: every fixture's length = max(duration, latest substitution or dismissal time); the
              minutes and proportion of every appearance row recomputed (prepare.py)
  base        the method on the unreconciled inputs (three input sets, every season): the run that sizes disputes
  size        every disputed record sized at real xU on the base run (sizing.py); >= bar_minutes = over the bar
  reconcile   the verdicts applied, the exclusions, identity merges, origin overrides and the ledger (reconcile.py);
              check C1 stops the run on failure
  run         the method on the reconciled inputs, sideways adjustment on and off; a player at two clubs on one date is
              closed at the new club's arrival record and the seasons are run again
  checks      checks C2-C7 (checks.csv)
  calibration the constants re-measured on the run (calibrate.py; measures only, changes nothing)
  analyses    the analysis battery on the 7- and 11-season sets (analyses/battery.py), in the background
  export      the publishable club and player tables (export.py)
  switches    optional (--with-switches): each rule switch flipped alone; Spearman per season, minutes moved
"""
import argparse, json, os, shutil, subprocess, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pandas as pd

from . import common as fb
from . import settings

CLOSURE_TID0 = 992000000
# the published run starts from the reconciled inputs (data/inputs/reconciled/); the full chain starts from the provider
# data and needs the Transfermarkt pages and histories the sizing and reconcile read, which are not distributed
STAGES = ["integrity", "reconciled", "run", "checks", "calibration", "analyses", "export"]
FULL_CHAIN = ["integrity", "prepare", "base", "size", "reconcile", "run", "checks", "calibration", "analyses", "export"]
LISTS = ("late", "early")                    # the dispute lists: late = 2018/19-2025/26, early = 2014/15-2017/18


def reconcile_mod():
    from . import reconcile
    return reconcile


class Run:
    def __init__(self, cfg, name, root, parent=None, seasons=None):
        self.cfg, self.name, self.root = cfg, name, Path(root)
        self.root = self.root.resolve()
        self.parent = Path(parent).resolve() if parent else None      # a switch run reuses its parent's prepare / base / size stages
        self.root.mkdir(parents=True, exist_ok=True)
        self.seasons = list(seasons or settings.seasons())
        # the input sets and dispute lists the configured seasons need
        self.sets = [st for st in ("early", "mid", "late") if any(s in self.seasons for s in fb.SETS[st])]
        self.lists = [k for k in LISTS if any(reconcile_mod().SETS[st]["src"] == k for st in self.sets)]
        self.lines = []

    def log(self, s=""):
        print(s, flush=True)
        self.lines.append(str(s))
        with open(self.root / "run_log.txt", "a") as f:
            f.write(str(s) + "\n")

    def stage_done(self, name, t0, start, info):
        d = dict(info)
        d.update(stage=name, start=start, end=fb.now(), seconds=round(time.time() - t0, 1))
        (self.root / f"stage_{name}.json").write_text(json.dumps(d, indent=1, default=str))
        return d

    def rel(self, p):
        """A path for the run's records: relative to the data root or to the run folder."""
        p = Path(p)
        for base, tag in [(r, "<data>") for r in settings.data_roots()] + [(self.root, "<run>"), (self.parent, "<parent>")]:
            if base is not None:
                try:
                    return f"{tag}/{p.relative_to(base)}"
                except ValueError:
                    pass
        return str(p)

    # ------------------------------------------------------------ window table (window closes and nominal loan ends)
    def window_table(self):
        p = self.root / "window_table.csv"
        w = pd.read_csv(self.cfg["window_closes"])
        w = w[(w.used == "y") & (w.kind == "window_close")][["date"]].assign(kind="window_close")
        y0 = int(w.date.min()[:4]) + 1
        r7 = self.cfg["loan_return_2019_20"]
        nom = [("2020-07-01" if r7 == "NOMINAL" else r7) if y == 2020 else f"{y}-07-01" for y in range(y0, 2027)]
        t = pd.concat([w, pd.DataFrame(dict(date=nom, kind="nominal_loan_end"))], ignore_index=True)
        t.to_csv(p, index=False)
        return p

    # ------------------------------------------------------------ input folders
    def corrected(self):
        return bool(self.cfg.get("use_corrected_matchday", True))

    def matchday_source(self, set_name, f, raw=False):
        """Path of a matchday file (appearances / fixtures / events) of an input set: the corrected set when
        use_corrected_matchday is on, else the Sportmonks original; appearances after the prepare stage."""
        if f == "appearances" and not raw:
            for r in (self.root, self.parent):
                pth = None if r is None else r / "prepared" / set_name / "appearances.csv"
                if pth is not None and pth.exists():
                    return pth, "prepared (match length) on " + self.matchday_source(set_name, f, raw=True)[1]
        orig = fb.sm_file(set_name, f)
        if self.corrected():
            c = settings.data_path("matchday", set_name, f"{f}.csv")
            if c.exists():
                return c, "corrected"
            raise fb.Stop(f"STOP (integrity): use_corrected_matchday is on but {c} does not exist")
        return orig, "original"

    def proot(self, name):
        """The root that holds a stage output: this run's, else its parent's (switch runs)."""
        return self.root if (self.root / name).exists() or self.parent is None else self.parent

    def md(self, set_name, f):
        return self.matchday_source(set_name, f)[0]

    def assemble(self, inputs, files=None):
        """<inputs>/<set>/<name>.csv: symlinks to the unchanged files; files = {set: {name: path}} replaces them."""
        man = []
        for st in self.sets:
            d = Path(inputs) / st
            d.mkdir(parents=True, exist_ok=True)
            fb.link_shared(d)
            for f in fb.FILES:
                dst = d / f"{f}.csv"
                src, kind = (self.matchday_source(st, f) if f in fb.MATCHDAY else (fb.sm_file(st, f), "original"))
                if files is not None and f in files.get(st, {}):
                    src, kind = files[st][f], "reconciled"
                if dst.is_symlink() or dst.exists():
                    dst.unlink()
                os.symlink(src, dst)
                man.append(dict(input_set=st, file=f, source=self.rel(src), kind=kind, sha256=fb.sha(src)))
        m = pd.DataFrame(man)
        m.to_csv(Path(inputs) / "inputs_manifest.csv", index=False)
        return m

    def jobs(self, inputs, rundir, sfx, sideways, overrides=None, retention=None, seasons=None, first_team_first=True):
        wt = self.window_table()
        out = []
        for s in (seasons or self.seasons):
            st = fb.SET_OF[s]
            out.append(dict(season=s, input_set=st, cmd=fb.compute_cmd(
                s, Path(inputs) / st, Path(rundir) / fb.tag(s), sfx, self.cfg, sideways, overrides=overrides, window_table=wt,
                retention=retention, first_team_first=first_team_first)))
        return out

    # ------------------------------------------------------------ stages
    def integrity(self):
        t0, start = time.time(), fb.now()
        cfg = self.cfg
        need = [fb.COMPUTE] + [Path(cfg[k]) for k in settings.load()["rule_files"]]
        need += [settings.data_path("sportmonks", f) for f in fb.SHARED]
        if getattr(self, "full_chain", False):
            need += [settings.data_path("review", lst, "disputes.csv") for lst in self.lists]
            need += [settings.inp(k) for k in ("verdicts_round1", "verdicts_round2", "senior_record", "unknown_origin_resolved")]
            for st in self.sets:
                need += [fb.sm_file(st, f) for f in fb.FILES]
                if self.corrected():
                    need += [settings.data_path("matchday", st, f"{f}.csv") for f in fb.MATCHDAY]
        else:
            need += [settings.data_path("reconciled", f) for f in RECONCILED_FILES]
            for st in self.sets:
                need += [settings.data_path("reconciled", st, f"{f}.csv") for f in RECONCILED_SET_FILES]
                need += [fb.sm_file(st, f) for f in ("teams", "contracts_no_dated_record")]
                need += [settings.data_path("matchday", st, "fixtures.csv") if self.corrected() else fb.sm_file(st, "fixtures")]
        missing = [str(p) for p in need if not Path(p).exists()]
        if missing:
            raise fb.Stop("STOP (integrity): missing inputs: " + "; ".join(missing))
        opt = {k: settings.inp(k).exists() for k in ("verdicts_round3", "verdicts_gapfill", "gapfill_cases", "identity_pending_rows",
                                                         "senior_second_source")}
        sh = [dict(file=self.rel(p) if not str(p).startswith(str(fb.HERE)) else f"src/netavailability/{Path(p).name}", sha256=fb.sha(p)) for p in need]
        sh += [dict(file=f"src/netavailability/{p.relative_to(fb.HERE)}", sha256=fb.sha(p)) for p in sorted(fb.HERE.rglob("*.py"))]
        pd.DataFrame(sh).to_csv(self.root / "inputs_sha256.csv", index=False)
        (self.root / "config_used.json").write_text(json.dumps(dict(cfg, seasons=self.seasons, data_roots=[str(r) for r in settings.data_roots()]), indent=1))
        self.log(f"integrity: {len(need)} required inputs present; optional: " + ", ".join(f"{k}={'yes' if v else 'NO'}" for k, v in opt.items()))
        return self.stage_done("integrity", t0, start, dict(optional=opt, n_required=len(need)))

    def prepare(self):
        t0, start = time.time(), fb.now()
        from . import prepare as prep
        d = self.root / "prepared"
        if d.exists():
            shutil.rmtree(d)

        def source(st, f):
            return self.matchday_source(st, f, raw=True)[0] if f in fb.MATCHDAY else fb.sm_file(st, f)
        _, S, infos = prep.prepare(source, d, self.log, cfg=self.cfg, corrected=self.corrected(), sets=self.sets)
        return self.stage_done("prepare", t0, start, dict(sets=infos))

    def base(self):
        t0, start = time.time(), fb.now()
        inputs = self.root / "inputs_base"
        man = self.assemble(inputs)
        rundir = self.root / "run_base"
        fb.run_seasons(self.jobs(inputs, rundir, "_base", True), rundir, self.cfg["jobs"], self.log)
        tot = {s: int(fb.table(rundir, "club_table", s).NETabsence.sum()) for s in self.seasons}
        self.log("base run (unreconciled inputs, sideways on) league NETabsence: " + ", ".join(f"{s[2:4]}/{s[7:9]} {v}" for s, v in tot.items()))
        return self.stage_done("base", t0, start, dict(netabsence=tot, matchday=sorted(set(man[man.file.isin(fb.MATCHDAY)].kind))))

    def reconciled(self):
        """The published reconciled inputs (data/inputs/reconciled/) taken as the reconcile stage's output: the corrected
        squads, transfers, appearances, events and contracts of each input set, the exclusions (retention overrides), the
        origin overrides, the placeholder arrivals and the ledger, copied into <root>/reconciled/."""
        t0, start = time.time(), fb.now()
        out = self.root / "reconciled"
        out.mkdir(parents=True, exist_ok=True)
        files = {}
        for st in self.sets:
            (out / st).mkdir(exist_ok=True)
            files[st] = {}
            for f in RECONCILED_SET_FILES:
                shutil.copyfile(settings.data_path("reconciled", st, f"{f}.csv"), out / st / f"{f}.csv")
                files[st][f] = out / st / f"{f}.csv"
        for f in RECONCILED_FILES:
            shutil.copyfile(settings.data_path("reconciled", f), (self.root if f == "ledger.csv" else out) / f)
        info = dict(source=self.rel(settings.data_path("reconciled")), files={k: {a: str(b) for a, b in v.items()} for k, v in files.items()},
                    origin_overrides=str(out / "origin_overrides.csv"), retention_overrides=str(out / "retention_overrides.csv"))
        (out / "reconcile_info.json").write_text(json.dumps(info, indent=1))
        self.log(f"reconciled: the published reconciled inputs of sets {self.sets} copied from {info['source']}")
        return self.stage_done("reconciled", t0, start, info)

    # ------------------------------------------------------------ sizing
    def size(self):
        """Every dispute sized at real xU on the base run (sizing.py). The disputed fixtures of each case are part of the
        dispute lists (review/<list>/disputes.csv)."""
        t0, start = time.time(), fb.now()
        out = self.root / "size"
        out.mkdir(exist_ok=True)
        lists = {k: settings.data_path("review", k, "disputes.csv") for k in self.lists}
        for k, pth in lists.items():
            if not pth.exists():
                raise fb.Stop(f"STOP (integrity): sizing needs {pth}")

        def one(k):
            c = fb.module_cmd("sizing", "--hand-list", lists[k], "--list", k, "--base-run", self.proot("run_base") / "run_base",
                              "--out", out / f"out_{k}", "--bar", self.cfg["bar_minutes"])
            r = subprocess.run(c, capture_output=True, text=True, cwd=fb.HERE, env=fb.child_env())
            (out / f"size_stdout_{k}.txt").write_text(r.stdout + ("\nSTDERR\n" + r.stderr if r.stderr else ""))
            return k, r.returncode
        with ThreadPoolExecutor(2) as ex:
            rc = dict(ex.map(one, lists))
        if any(rc.values()):
            raise fb.Stop(f"STOP (integrity): sizing failed {rc}; see {out}/size_stdout_*.txt")
        info = {}
        for k in lists:
            h = pd.read_csv(out / f"out_{k}" / f"hand_list_{k}_sized.csv")
            info[k] = dict(cases=int(len(h)), over_bar=int((h.size_xu_min >= self.cfg["bar_minutes"]).sum()), minutes=round(float(h.size_xu_min.sum()), 1),
                           minutes_over_bar=round(float(h[h.size_xu_min >= self.cfg["bar_minutes"]].size_xu_min.sum()), 1))
        self.log(f"size: " + "; ".join(f"{k}: {v['cases']} cases, {v['over_bar']} over the bar ({v['minutes_over_bar']} of {v['minutes']} min)" for k, v in info.items()))
        return self.stage_done("size", t0, start, info)

    def sized(self):
        out = {}
        for k in self.lists:
            d = self.proot("size") / "size" / f"out_{k}"
            out[k] = (pd.read_csv(d / f"hand_list_{k}_sized.csv"), pd.read_csv(d / f"size_detail_{k}.csv", low_memory=False))
        return out

    # ------------------------------------------------------------ reconcile + ledger (C1)
    def reconcile(self):
        t0, start = time.time(), fb.now()
        info = reconcile_mod().run(self.cfg, self.root, self.proot("run_base") / "run_base", self.sized(), self.log, xa=self.corrected(),
                                   matchday=self.md, sets=self.sets)
        return self.stage_done("reconcile", t0, start, info)

    # ------------------------------------------------------------ the runs (sideways on / off) + two-club closure
    def two_club(self, rundir, seasons=None):
        """Overlapping retention windows of one player at two clubs (presence ledgers), one row per pair."""
        rows = []
        for s in (seasons or self.seasons):
            led = fb.table(rundir, "presence_ledger", s, parse_dates=["start", "end"])
            multi = led.groupby("player_id").team_id.nunique()
            for pid in multi[multi > 1].index:
                g = led[led.player_id == pid].sort_values("start")
                ws = list(g.itertuples())
                for i in range(len(ws)):
                    for j in range(i + 1, len(ws)):
                        a, b = ws[i], ws[j]
                        if a.team_id == b.team_id or max(a.start, b.start) > min(a.end, b.end):
                            continue
                        rows.append(dict(season=s, player_id=int(pid), player=a.player, old_team_id=int(a.team_id), old_club=a.club,
                                         old_window=f"{a.start.date()}..{a.end.date()} ({a.start_source}->{a.end_source}, A {a.A})",
                                         new_team_id=int(b.team_id), new_club=b.club,
                                         new_window=f"{b.start.date()}..{b.end.date()} ({b.start_source}->{b.end_source}, A {b.A})",
                                         overlap_from=max(a.start, b.start).date(), overlap_to=min(a.end, b.end).date(),
                                         new_start=b.start.date(), same_start=bool(a.start == b.start),
                                         minutes_old=float(a.NETabsence), minutes_new=float(b.NETabsence)))
        return pd.DataFrame(rows)

    def closures(self, tc, inputs):
        """Close a two-club overlap at the new club's arrival record (or the day before the player's first naming there,
        whichever is earlier). Returns {set: rows to append to the set's transfers} and the listing."""
        add, listing, n = {}, [], 0
        cache = {}
        for r in tc.itertuples():
            st = fb.SET_OF[r.season]
            if st not in cache:
                tr = pd.read_csv(Path(inputs) / st / "transfers.csv", parse_dates=["date"])
                ap_ = pd.read_csv(Path(inputs) / st / "appearances.csv", usecols=["date", "team_id", "player_id"], parse_dates=["date"])
                tm = pd.read_csv(Path(inputs) / st / "teams.csv")
                cache[st] = (tr, ap_, dict(zip(tm.team_id, tm.name)))
            tr, ap_, cname = cache[st]
            lo = pd.Timestamp(r.overlap_from) - pd.Timedelta(days=150)
            hi = pd.Timestamp(r.overlap_to)
            arr = tr[(tr.player_id == r.player_id) & (tr.to_team_id == r.new_team_id) & tr.type_id.isin([218, 219, 220]) & (tr.date >= lo) & (tr.date <= hi)]
            nam_new = ap_[(ap_.player_id == r.player_id) & (ap_.team_id == r.new_team_id) & (ap_.date >= pd.Timestamp(r.overlap_from) - pd.Timedelta(days=3))].date
            nam_old = ap_[(ap_.player_id == r.player_id) & (ap_.team_id == r.old_team_id)].date
            cands = []
            if len(arr):                                                  # the record that opens the new window: the latest on or before its start
                arr = arr.sort_values("date")
                a0 = arr[arr.date <= pd.Timestamp(r.overlap_from)]
                a0 = a0.iloc[-1] if len(a0) else arr.iloc[0]
                cands.append((a0.date, "arrival record at the new club", int(a0.type_id)))
            if len(nam_new):
                cands.append((nam_new.min().normalize() - pd.Timedelta(days=1), "day before the first naming at the new club", 219))
            row = dict(r._asdict()); row.pop("Index", None)
            if not cands or r.same_start and not len(arr):
                listing.append(dict(row, rule="two-club closure", closure_date=None, basis="no arrival record or naming at the later club: not closed", applied=False))
                continue
            X, basis, typ = min(cands, key=lambda c: c[0])
            typ = cands[0][2] if len(arr) else 219
            if len(nam_old) and (nam_old > X + pd.Timedelta(days=1)).any() and (nam_old[nam_old > X + pd.Timedelta(days=1)] <= hi).any():
                listing.append(dict(row, rule="two-club closure", closure_date=X.date(), basis="named for the old club after the closure date: not closed", applied=False))
                continue
            dup = tr[(tr.player_id == r.player_id) & (tr.from_team_id == r.old_team_id) & (tr.date == X)]
            if len(dup):
                listing.append(dict(row, rule="two-club closure", closure_date=X.date(), basis="a departure record on that date already exists: not closed again", applied=False))
                continue
            n += 1
            add.setdefault(st, []).append(dict(transfer_id=CLOSURE_TID0 + n, player_id=r.player_id, player=r.player, date=X.strftime("%Y-%m-%d"),
                                               from_team_id=r.old_team_id, from_team=cname.get(r.old_team_id, r.old_club), to_team_id=r.new_team_id,
                                               to_team=cname.get(r.new_team_id, r.new_club), type_id=typ, career_ended=False, completed=True, amount=None))
            listing.append(dict(row, rule="two-club closure", closure_date=X.date(), basis=basis, applied=True))
        return add, pd.DataFrame(listing)

    def run(self):
        t0, start = time.time(), fb.now()
        info = json.loads((self.root / "reconciled/reconcile_info.json").read_text())
        files = {st: {k: Path(v) for k, v in d.items()} for st, d in info["files"].items()}
        inputs = self.root / "inputs"
        self.assemble(inputs, files)
        ov, ret = info["origin_overrides"], info["retention_overrides"]
        on, off = self.root / "run_on", self.root / "run_off"
        fb.run_seasons(self.jobs(inputs, on, "_on", True, ov, ret), on, self.cfg["jobs"], self.log)
        tc1 = self.two_club(on)
        add, listing = self.closures(tc1, inputs) if len(tc1) else ({}, pd.DataFrame())
        n_add = sum(len(v) for v in add.values())
        for st, rows in add.items():
            src = files[st]["transfers"]
            t = pd.concat([pd.read_csv(src), pd.DataFrame(rows)], ignore_index=True)
            for c in ("from_team_id", "to_team_id"):
                t[c] = pd.to_numeric(t[c], errors="coerce").astype("Int64")
            dst = src.with_name("transfers_closed.csv")
            t.to_csv(dst, index=False)
            files[st]["transfers"] = dst
        on_only = getattr(self, "on_only", False)
        if n_add:
            man = self.assemble(inputs, files)
            todo = [(on, "_on", True)] + ([] if on_only else [(off, "_off", False)])
            with ThreadPoolExecutor(2) as ex:
                list(ex.map(lambda a: fb.run_seasons(self.jobs(inputs, a[0], a[1], a[2], ov, ret), a[0],
                                                     self.cfg["jobs"] if on_only else max(4, self.cfg["jobs"] // 2 + 2), self.log), todo))
        elif not on_only:
            fb.run_seasons(self.jobs(inputs, off, "_off", False, ov, ret), off, self.cfg["jobs"], self.log)
        tc2 = self.two_club(on)
        listing.to_csv(self.root / "two_club_closures.csv", index=False)
        tc2.to_csv(self.root / "two_club_remaining.csv", index=False)
        (self.root / "reconciled/files_in_use.json").write_text(json.dumps({st: {k: str(v) for k, v in d.items()} for st, d in files.items()}, indent=1))
        tot = {s: int(fb.table(on, "club_table", s).NETabsence.sum()) for s in self.seasons}
        self.log(f"run: two-club overlaps before closure {len(tc1)}, closure rows added {n_add}, overlaps remaining {len(tc2)}; "
                 "league NETabsence (sideways on): " + ", ".join(f"{s[2:4]}/{s[7:9]} {v}" for s, v in tot.items()))
        return self.stage_done("run", t0, start, dict(netabsence_on=tot, two_club_before=int(len(tc1)), closures=n_add, two_club_remaining=int(len(tc2))))

    # ------------------------------------------------------------ checks C2-C7 (reported, never stopping)
    def checks(self):
        from .checks import run_checks
        t0, start = time.time(), fb.now()
        res, n = run_checks(self)
        self.log("checks: " + ", ".join(f"{k} {v}" for k, v in res.items()))
        return self.stage_done("checks", t0, start, dict(results=res, rows=n))

    # ------------------------------------------------------------ calibration, analyses (background), export, switch effects
    def calibration(self):
        t0, start = time.time(), fb.now()
        out = self.root / "calibration"
        both = all(s in self.seasons for s in fb.SET11)           # the 11-season set only when its seasons are computed
        c = fb.module_cmd("calibrate", "--run-dir", self.root / "run_on", "--out", out, "--set", "both" if both else "SET7")
        out.mkdir(exist_ok=True)
        r = subprocess.run(c, capture_output=True, text=True, cwd=fb.HERE, env=fb.child_env())
        (out / "calibration_stdout.txt").write_text(r.stdout + ("\nSTDERR\n" + r.stderr if r.stderr else ""))
        # the constants are measured on the 7-season set only (fit 2018/19, 2019/20, 2021/22; test 2022/23-2025/26).
        # 2014/15-2017/18 is the out-of-sample test of those constants: the same measurement on the eleven seasons with
        # fit = the 7-season set and test = the four earlier seasons (folder out_of_sample/, captures reused).
        oos = out / "out_of_sample"
        if not both:
            self.log(f"calibration: rc {r.returncode} (SET7); the out-of-sample test needs 2014/15-2017/18 in the season list")
            return self.stage_done("calibration", t0, start, dict(rc=r.returncode, command=c))
        if oos.exists():
            shutil.rmtree(oos)
        oos.mkdir()
        if (out / "inst").exists():
            os.symlink((out / "inst").resolve(), oos / "inst")
        c2 = fb.module_cmd("calibrate", "--run-dir", self.root / "run_on", "--out", oos, "--set", "SET11",
                           "--fit", *fb.SET7, "--test", *[s for s in fb.SET11 if s not in fb.SET7], "--skip-instrument")
        r2 = subprocess.run(c2, capture_output=True, text=True, cwd=fb.HERE, env=fb.child_env())
        (oos / "calibration_stdout.txt").write_text(r2.stdout + ("\nSTDERR\n" + r2.stderr if r2.stderr else ""))
        self.log(f"calibration: rc {r.returncode} (SET7 and SET11); out-of-sample 2014/15-2017/18 rc {r2.returncode}")
        return self.stage_done("calibration", t0, start, dict(rc=r.returncode, rc_out_of_sample=r2.returncode, command=c, command_out_of_sample=c2))

    def analyses(self):
        """Started in the background (the 7- and 11-season sets in parallel inside the battery); waited for at the end."""
        t0, start = time.time(), fb.now()
        out = self.root / "analyses"
        out.mkdir(exist_ok=True)
        both = all(s in self.seasons for s in fb.SET11)
        c = fb.module_cmd("analyses.battery", "--run-dir", self.root / "run_on", "--out", out, "--set", "both" if both else "SET7")
        self._bat = (subprocess.Popen(c, stdout=open(out / "analyses_stdout.txt", "w"), stderr=subprocess.STDOUT, cwd=fb.HERE,
                                      env=fb.child_env()), t0, start, c)
        self.log("analyses: started in the background")
        return dict(seconds=0.0)

    def analyses_wait(self):
        if getattr(self, "_bat", None) is None:
            return None
        pr, t0, start, c = self._bat
        rc = pr.wait()
        self._bat = None
        self.log(f"analyses: rc {rc}")
        return self.stage_done("analyses", t0, start, dict(rc=rc, command=c))

    def export(self):
        from .export import export_run
        t0, start = time.time(), fb.now()
        seasons = [s for s in settings.export_seasons() if s in self.seasons]     # the export seasons this run computed
        info = export_run(self.root / "run_on", self.root / "run_off", self.root / "export", seasons, self.log)
        return self.stage_done("export", t0, start, info)

    def switches(self):
        t0, start = time.time(), fb.now()
        d0 = self.root / "switches"
        d0.mkdir(exist_ok=True)

        def one(item):
            name, flip = item
            d = d0 / name
            if d.exists():
                shutil.rmtree(d)
            d.mkdir(parents=True)
            (d / "overrides.json").write_text(json.dumps(dict(flip, jobs=6), indent=1))
            c = fb.module_cmd("pipeline", "--overrides", d / "overrides.json", "--name", f"{self.name}_switch_{name}", "--root", d,
                              "--parent", self.root, "--on-only", "--stages", "reconcile", "run")
            t1 = time.time()
            r = subprocess.run(c, capture_output=True, text=True, cwd=fb.HERE, env=fb.child_env())
            (d / "stdout.txt").write_text(r.stdout + ("\nSTDERR\n" + r.stderr if r.stderr else ""))
            return name, flip, r.returncode, round(time.time() - t1, 1), (r.stdout + r.stderr)[-400:]
        with ThreadPoolExecutor(4) as ex:
            res = list(ex.map(one, SWITCH_FLIPS))
        main_on = self.root / "run_on"
        rows, per = [], []
        mainL = pd.read_csv(self.root / "ledger.csv", low_memory=False)

        def rank_of(run, season, team):
            if season not in self.seasons:
                return None
            t = fb.table(run, "club_table", season)
            return int(t.loc[t.team_id == team, "NETavailability rank"].iloc[0])
        for name, flip, rc, secs, tail in res:
            row = dict(switch=name, flip=json.dumps(flip), rc=rc, seconds=secs)
            if rc != 0:
                row.update(note=("STOP: " + tail.strip().splitlines()[-1][:300]) if tail.strip() else "failed")
                rows.append(row); continue
            sub = d0 / name / "run_on"
            sl = pd.read_csv(d0 / name / "ledger.csv", low_memory=False)
            mm = mainL[["case_id", "outcome"]].merge(sl[["case_id", "outcome"]], on="case_id", how="outer", suffixes=("_main", "_flip"))
            row["ledger_outcomes_changed"] = int((mm.outcome_main.fillna("") != mm.outcome_flip.fillna("")).sum())
            tot_abs = tot_net = 0.0
            for s in self.seasons:
                a = fb.table(main_on, "club_table", s).set_index("team_id")
                b = fb.table(sub, "club_table", s).set_index("team_id").reindex(a.index)
                sp = a.NETavailability.rank().corr(b.NETavailability.rank())
                dabs, dnet = float((b.NETabsence - a.NETabsence).abs().sum()), float((b.NETabsence - a.NETabsence).sum())
                moved = int((a["NETavailability rank"] != b["NETavailability rank"]).sum())
                per.append(dict(switch=name, season=s, spearman=round(sp, 4), minutes_moved_abs=round(dabs), minutes_net=round(dnet), clubs_changing_rank=moved))
                tot_abs += dabs; tot_net += dnet
            pp = [x for x in per if x["switch"] == name]
            row.update(min_spearman=min(x["spearman"] for x in pp), seasons_changed=sum(1 for x in pp if x["minutes_moved_abs"] > 0),
                       minutes_moved_abs=round(tot_abs), minutes_net=round(tot_net),
                       leicester_1516_rank=rank_of(sub, "2015/2016", 42), leicester_1516_rank_main=rank_of(main_on, "2015/2016", 42),
                       spurs_2526_rank=rank_of(sub, "2025/2026", 6), spurs_2526_rank_main=rank_of(main_on, "2025/2026", 6), note="")
            rows.append(row)
        pd.DataFrame(rows).to_csv(self.root / "switch_effects.csv", index=False)
        pd.DataFrame(per).to_csv(self.root / "switch_effects_by_season.csv", index=False)
        self.log("switch effects: " + "; ".join(f"{r['switch']}: " + (f"min rho {r['min_spearman']}, {r['minutes_moved_abs']} min moved" if r["rc"] == 0 else r.get("note", "failed")[:80]) for r in rows))
        return self.stage_done("switches", t0, start, dict(n=len(rows), failed=[r["switch"] for r in rows if r["rc"] != 0]))


RECONCILED_SET_FILES = ["squads", "transfers", "appearances", "events", "contracts"]
RECONCILED_FILES = ["retention_overrides.csv", "origin_overrides.csv", "placeholder_origin_arrivals.csv", "ledger.csv"]

# each switch flipped alone (the settings' alternatives)
SWITCH_FLIPS = [
    ("senior_REQUIRE_SECOND_FILL_ZERO", {"senior_fill_source": "REQUIRE_SECOND", "senior_unconfirmed": "FILL_ZERO"}),
    ("senior_REQUIRE_SECOND_EXCLUDE", {"senior_fill_source": "REQUIRE_SECOND", "senior_unconfirmed": "EXCLUDE"}),
    ("loan_return_NOMINAL", {"loan_return_2019_20": "NOMINAL"}),
    ("unforeseen_STOP", {"unforeseen_case_types": "STOP"}),
    ("verdict_dates_TM", {"verdict_dates": "TM"}),
    ("identity_links_EXCLUDE", {"identity_links": "EXCLUDE"}),
    ("gap_fill_ADD", {"gap_fill_tm_only": "ADD"}),
    ("other_club_NOT", {"other_club_in_deal": "NOT"}),
    ("kesler_hayden_false", {"kesler_hayden_merge": False}),
]


def main(argv=None):
    ap = argparse.ArgumentParser(description="NETavailability pipeline")
    ap.add_argument("--name", default="run", help="run name: the output folder <output_root>/<name>")
    ap.add_argument("--stages", nargs="*", default=None, help=f"default: all of {STAGES}")
    ap.add_argument("--full-chain", action="store_true", help="start from the provider data (prepare, base, size, reconcile) instead of the "
                    "published reconciled inputs; needs the Transfermarkt pages and histories, which are not distributed")
    ap.add_argument("--with-switches", action="store_true", help="also run the switch-effect runs (slow; needs the full chain's inputs)")
    ap.add_argument("--seasons", nargs="*", default=None, help="override the settings' season list")
    ap.add_argument("--root", default=None, help="output folder (default <output_root>/<name>)")
    ap.add_argument("--overrides", default=None, help="JSON file of setting values that replace the settings' (switch runs)")
    ap.add_argument("--parent", default=None, help="switch runs: the main run folder whose prepare / base / size stages are reused")
    ap.add_argument("--on-only", action="store_true", help="switch runs: sideways-on run only")
    args = ap.parse_args(argv)
    cfg = settings.run_config()
    if args.overrides:
        user = json.loads(Path(args.overrides).read_text())
        unknown = sorted(set(user) - set(cfg))
        if unknown:
            raise fb.Stop(f"STOP (integrity): unknown setting keys {unknown}")
        cfg.update(user)
    root = Path(args.root) if args.root else settings.output_root() / args.name
    run = Run(cfg, args.name, root, parent=args.parent, seasons=args.seasons)
    run.on_only = args.on_only
    run.full_chain = args.full_chain or (args.stages is not None and "reconcile" in args.stages)
    stages = args.stages or ((FULL_CHAIN if args.full_chain else STAGES) + (["switches"] if args.with_switches else []))
    run.log(f"=== NETavailability pipeline, run {args.name}, stages {stages}, started {time.strftime('%Y-%m-%d %H:%M:%S')}")
    for st in stages:
        if not hasattr(run, st):
            run.log(f"stage {st}: not implemented"); continue
        d = getattr(run, st)()
        run.log(f"stage {st}: {d['seconds']} s")
    run.analyses_wait()
    run.log("=== done")


if __name__ == "__main__":
    main()
