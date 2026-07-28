#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../apps/api"
python -m ecotrace.db.seed
echo "Seed completed successfully."
