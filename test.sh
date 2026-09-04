#!/usr/bin/env bash

set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"

python -m pytest -q