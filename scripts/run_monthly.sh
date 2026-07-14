#!/bin/zsh
# Capitol Wave — 월간 무인 갱신 (의회 거래 + N-PORT + 대시보드)
cd "$(dirname "$0")/.." || exit 1
PY=${PY:-$(command -v python3)}
mkdir -p logs
LOG="logs/monthly_$(date +%Y%m%d_%H%M).log"
{
  echo "===== Capitol Wave 월간 갱신 시작 $(date) ====="
  echo "--- 1/5 하원 PTR ---";    $PY scripts/congress_ptr_pipeline.py
  echo "--- 2/5 상원 eFD ---";    $PY scripts/senate_ptr_pipeline.py
  echo "--- 3/5 통합·플로우 ---"; $PY scripts/exposure_timing.py
  echo "--- 4/6 N-PORT 보유 ---"; $PY scripts/nport_holdings.py
  echo "--- 5/6 정책발자국(로비·계약) ---"; $PY scripts/policy_footprint_panel.py
  echo "--- 6/6 대시보드 ---";    $PY scripts/policy_radar_dashboard.py
  echo "===== 완료 $(date) ====="
} >> "$LOG" 2>&1
