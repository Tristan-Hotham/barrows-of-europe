#!/bin/sh
# Rebuild everything from the raw inputs. Usage (from anywhere): sh code/run_all.sh
# Inputs are read in place from ../_data3/ (set DATA3 to point elsewhere) and the IntCal20 curve
# from work/intcal/3Col_intcal20.14C (see README: how to rerun).
set -e
cd "$(dirname "$0")"
mkdir -p ../work
python3 01_build.py
python3 02_dates.py
python3 03_analyse.py
python3 build_site.py
python3 05_header.py
