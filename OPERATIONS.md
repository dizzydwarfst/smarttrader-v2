# SmartTrader — Operations & Monitoring

Everything you need to keep the bot healthy once it's deployed.

## 1. Telegram push alerts

Fast feedback when things go sideways — crashes, SIGINT stops, or (wired manually) circuit breakers.

**One-time setup:**
1. Message `@BotFather` on Telegram → `/newbot` → follow prompts → copy the token.
2. Send any message to your new bot.
3. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and grab the `"chat":{"id":...}` value.
4. On the server:
   ```
   cd ~/smarttrader-v2
   echo "TELEGRAM_BOT_TOKEN=123456:ABC..." >> .env
   echo "TELEGRAM_CHAT_ID=987654321" >> .env
   docker compose restart
   ```
5. You should receive `ℹ️ SmartTrader — Bot starting — mode=practice` within 10 seconds.

Leaving the vars blank disables alerts entirely; the bot doesn't care.

Add your own alert points in code:
```python
from alerts import send_alert_safe
send_alert_safe("Daily loss limit hit, pausing", level="critical")
```
Levels: `info`, `success`, `warning`, `critical`, `trade`.

---

## 2. Deep health endpoint + external uptime monitor

The container's built-in healthcheck now hits `/api/health`, which verifies:

| Check | Critical? | What it catches |
|---|---|---|
| `database` | yes | trades.db missing / locked / corrupt |
| `heartbeat` | yes | `bot_status.json` stale (> 180s old) = bot stuck |
| `oanda` | no | OANDA API unreachable / bad credentials |
| `frontend` | no | React build missing, SPA won't load |
| `disk` | no | Less than 250 MB free |

Returns **200** when critical checks pass, **503** otherwise.

Point [UptimeRobot](https://uptimerobot.com) (free) at:
```
http://YOUR_SERVER_IP:8000/api/health
```
Set it to ping every 5 minutes and alert on any non-2xx. You'll get an SMS/email the moment the bot goes silent.

Inspect by hand:
```
curl http://localhost:8000/api/health | jq
```

---

## 3. Daily backups

`scripts/backup.sh` snapshots the stateful files into `~/smarttrader-backups/YYYY-MM-DD/`. It runs idempotently and auto-rotates anything older than 30 days.

**Install once on the server:**
```
chmod +x ~/smarttrader-v2/scripts/backup.sh
crontab -e
```
Add this line:
```
0 3 * * *  /root/smarttrader-v2/scripts/backup.sh >> /root/smarttrader-v2/scripts/backup.log 2>&1
```
That's 3 AM server time, daily. Change the path if your repo lives elsewhere.

**Run it on demand:**
```
./scripts/backup.sh
```

**Restore:** copy the wanted file out of `~/smarttrader-backups/2026-04-17/` back into the repo root, then `docker compose restart`.

Backed-up files: `trades.db`, `soul.md`, `skills.md`, `ai_review_state.json`, `bot_status.json`, `runtime_commands.json`, and `strategy_cards/`.

---

## 4. Post-deploy smoke test

`scripts/smoke.sh` hits every endpoint the React frontend depends on (31 routes) and prints a green/red table. Exit code is non-zero on any failure, so it's safe to chain with deploy scripts.

```
cd ~/smarttrader-v2
chmod +x scripts/smoke.sh
./scripts/smoke.sh
```

Or against another host:
```
BASE_URL=http://1.2.3.4:8000 ./scripts/smoke.sh
```

Typical use:
```
git pull --ff-only && docker compose up -d --build && sleep 20 && ./scripts/smoke.sh
```

---

## Daily operator checklist

- [ ] `docker compose ps` shows `healthy`
- [ ] UptimeRobot dashboard is green
- [ ] Last Telegram alert is the expected `Bot starting` from the last restart
- [ ] `tail scripts/backup.log` shows last night's backup succeeded
- [ ] Open positions in the dashboard match OANDA web UI

## Troubleshooting

**Container reports `unhealthy`:**
```
curl -s http://localhost:8000/api/health | jq .checks
```
Look for `"ok": false` with `"critical": true`.

**No Telegram alerts:**
```
docker compose exec smarttrader python -c "from alerts import send_alert, alerts_configured; print('configured:', alerts_configured()); send_alert('test', level='info')"
```

**Smoke test fails on one endpoint after deploy:**
Usually frontend/backend drift — a React call without a matching FastAPI route. Check `api.py` added the route before the last frontend commit.
