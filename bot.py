import os, json, requests, sys
from datetime import datetime, timezone

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
COINGECKO_SIMPLE = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
COINGECKO_ATH = ("https://api.coingecko.com/api/v3/coins/bitcoin"
                 "?localization=false&tickers=false&market_data=true"
                 "&community_data=false&developer_data=false&sparkline=false")
STATE_FILE = ".github/state/btc_state.json"
BANDS = [5, 10]

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def send(msg):
    r = requests.post(WEBHOOK_URL, json={"content": msg}, timeout=10)
    r.raise_for_status()

def price():
    r = requests.get(COINGECKO_SIMPLE, timeout=10)
    r.raise_for_status()
    return float(r.json()["bitcoin"]["usd"])

def seed_ath():
    r = requests.get(COINGECKO_ATH, timeout=20)
    r.raise_for_status()
    d = r.json().get("market_data", {}).get("ath", {}).get("usd")
    return float(d) if d else None

def fmt(x):
    return f"${x:,.0f}" if x >= 1000 else f"${x:,.2f}"

try:
    with open(STATE_FILE, "r") as f:
        s = json.load(f)
except Exception:
    s = {"initialized": False, "ath": 0.0, "baseline_price": 0.0, "last_price": 0.0}

p = price()
if not s["initialized"]:
    ath = seed_ath() or p
    s.update({"initialized": True, "ath": max(ath, p), "baseline_price": p, "last_price": p})
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(s, f)
    send(f"🟢 Bot init {now_iso()} — baseline {fmt(p)}, ATH {fmt(s['ath'])}")
    sys.exit(0)

# One-shot checks
if p > s["ath"] * 1.0000005:
    s["ath"] = p
    send(f"🚀 NEW ATH: {fmt(p)} at {now_iso()}")
    s["baseline_price"] = p

if s["baseline_price"] > 0:
    pct = (p - s["baseline_price"]) / s["baseline_price"] * 100
    crossed = next((b for b in sorted(BANDS) if abs(pct) >= b - 1e-9), None)
    if crossed is not None:
        direction = "▲ up" if pct > 0 else "▼ down"
        send(f"📈 {direction} {abs(pct):.1f}% (band {crossed}%) — {fmt(p)} at {now_iso()}\n"
             f"Baseline was {fmt(s['baseline_price'])}")
        s["baseline_price"] = p

s["last_price"] = p
os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
with open(STATE_FILE, "w") as f:
    json.dump(s, f)
