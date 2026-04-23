#!/usr/bin/env bash
# Smoke-test every API endpoint the frontend uses.
# Run after each deploy:
#   ./scripts/smoke.sh                   # defaults to http://localhost:8000
#   BASE_URL=http://1.2.3.4:8000 ./scripts/smoke.sh
#
# Exit code: 0 if every endpoint returns 2xx, non-zero otherwise.

set -u

BASE_URL="${BASE_URL:-http://localhost:8000}"

# Colors
if [[ -t 1 ]]; then
    GREEN=$'\033[0;32m'; RED=$'\033[0;31m'; YELLOW=$'\033[0;33m'; DIM=$'\033[2m'; NC=$'\033[0m'
else
    GREEN=""; RED=""; YELLOW=""; DIM=""; NC=""
fi

pass=0; fail=0; warn=0
failed_endpoints=()

check() {
    local method="$1" path="$2" body="${3:-}" expect="${4:-2}"
    local url="$BASE_URL$path"
    local opts=(-s -o /dev/null -w '%{http_code}' --max-time 10)
    if [[ "$method" == "POST" ]]; then
        opts+=(-X POST -H 'Content-Type: application/json')
        [[ -n "$body" ]] && opts+=(-d "$body")
    fi
    local code
    code=$(curl "${opts[@]}" "$url" || echo "000")
    local head="${code:0:1}"
    if [[ "$head" == "$expect" ]]; then
        printf "  ${GREEN}✓${NC} %-6s %-40s ${DIM}%s${NC}\n" "$method" "$path" "$code"
        pass=$((pass + 1))
    elif [[ "$code" == "000" ]]; then
        printf "  ${RED}✗${NC} %-6s %-40s ${RED}unreachable${NC}\n" "$method" "$path"
        fail=$((fail + 1))
        failed_endpoints+=("$method $path (unreachable)")
    else
        printf "  ${RED}✗${NC} %-6s %-40s ${RED}%s${NC}\n" "$method" "$path" "$code"
        fail=$((fail + 1))
        failed_endpoints+=("$method $path ($code)")
    fi
}

echo
echo "SmartTrader API smoke test → $BASE_URL"
echo "=========================================================="

echo
echo "— Status / config —"
check GET  /api/health
check GET  /api/status
check GET  /api/config
check GET  /api/bot/control-status
check GET  /api/bot/activity-log

echo
echo "— Trades —"
check GET  /api/trades/open
check GET  /api/trades/recent?days=14
check GET  /api/trades/stats?days=14
check GET  /api/chart/pnl?days=14

echo
echo "— Analytics —"
check GET  /api/analytics/overview
check GET  /api/analytics/daily-breakdown?days=14
check GET  /api/analytics/hourly-performance?days=14
check GET  /api/analytics/instrument-breakdown?days=30
check GET  /api/analytics/strategy-breakdown?days=14
check GET  /api/analytics/trade-distribution?days=14

echo
echo "— Strategies —"
check GET  "/api/strategies/scorecard?days=30&min_trades=2"
check GET  /api/strategy-library

echo
echo "— Journal —"
check GET  /api/journal/notes?limit=50
check GET  /api/journal/tags
check GET  /api/journal/trades-for-linking?days=60

echo
echo "— AI / Learning —"
check GET  /api/ai/status
check GET  "/api/ai/analyze?days=1"
check GET  /api/ai/why-waiting
check GET  /api/learning/history?limit=20
check GET  /api/memory

echo
echo "— News —"
check GET  /api/news/status

echo
echo "— Frontend (SPA) —"
check GET  /

echo
echo "=========================================================="
total=$((pass + fail + warn))
if [[ $fail -eq 0 ]]; then
    echo "${GREEN}All $total endpoints healthy.${NC}"
    exit 0
else
    echo "${RED}$fail of $total endpoints failed.${NC}"
    for e in "${failed_endpoints[@]}"; do echo "  - $e"; done
    exit 1
fi
