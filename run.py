#!/usr/bin/env python3
"""NETavailability: one command from the input files to the tables, checks and analyses.

  python run.py                         every stage (config/settings.toml)
  python run.py --stages prepare base   chosen stages, on the same run folder
  python run.py --with-switches         also the switch-effect runs (each rule switch flipped alone)
  python run.py --data-root DIR         the input data folder (overrides settings.toml and NETAV_DATA_ROOT)
  python run.py --config FILE           another settings file

See README.md for the stages and the input data layout.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))


def main():
    argv = sys.argv[1:]
    for flag, env in (("--data-root", "NETAV_DATA_ROOT"), ("--config", "NETAV_CONFIG")):
        if flag in argv:
            i = argv.index(flag)
            os.environ[env] = str(Path(argv[i + 1]).resolve())
            del argv[i:i + 2]
    from netavailability import pipeline
    pipeline.main(argv)


if __name__ == "__main__":
    main()
