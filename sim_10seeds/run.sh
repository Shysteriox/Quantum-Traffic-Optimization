#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python real_city_sim.py
.venv/bin/python check_model.py
.venv/bin/python city_video.py
