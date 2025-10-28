import os, json, requests, sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
COINGECKO_SIMPLE = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
COINGECKO_FULL = ("https://api.coingecko.com/api/v3/coins/bitcoin"
                  "?localization=false&tickers=false&market_data=true"
                  "&community_data=false&developer_data=false&sparkline=false")
STATE_FILE = ".github/state/btc_state.json"
BANDS = [5, 10, 15]
TZ = ZoneInfo("America/Chicago")  # CST/CDT

def now_utc():
    return datetime.now(timezone.utc)

def now_cst():
    return datetime.now(TZ)

def now_iso():
    return now_utc().isoformat(timespec="seconds")

def send(msg):
    r = requests.post(WEBHOOK_URL, json={"content": msg}, timeout=10)
    r.raise_for_status()

def price():
    r = requests.get(COINGECKO_SIMPLE, timeout=10)
    r.raise_for_status()
    return float(r.json()["bitcoin"]["usd"])

def market_data():
    """Fetch full market data from CoinGecko including ATH, 7d/30d changes, market cap, supply"""
    r = requests.get(COINGECKO_FULL, timeout=20)
    r.raise_for_status()
    data = r.json().get("market_data", {})
    return {
        "price": float(data.get("current_price", {}).get("usd", 0)),
        "ath": float(data.get("ath", {}).get("usd", 0)),
        "change_7d": float(data.get("price_change_percentage_7d_in_currency", {}).get("usd", 0)),
        "change_30d": float(data.get("price_change_percentage_30d_in_currency", {}).get("usd", 0)),
        "market_cap": float(data.get("market_cap", {}).get("usd", 0)),
        "circulating_supply": float(data.get("circulating_supply", 0))
    }

def fmt(x):
    return f"${x:,.0f}" if x >= 1000 else f"${x:,.2f}"

def fmt_pct(x):
    return f"{x:+.1f}%" if x != 0 else "0.0%"

# Load state
try:
    with open(STATE_FILE, "r") as f:
        s = json.load(f)
except Exception:
    s = {
        "initialized": False,
        "ath": 0.0,
        "daily_baseline": 0.0,
        "daily_baseline_date": None,
        "last_price": 0.0,
        "last_weekly_summary": None,
        "last_monthly_summary": None
    }

# Get current price and market data
p = price()
now = now_cst()
today = now.date().isoformat()

# Initialize if needed
if not s["initialized"]:
    data = market_data()
    s.update({
        "initialized": True,
        "ath": max(data["ath"], p),
        "daily_baseline": p,
        "daily_baseline_date": today,
        "last_price": p,
        "last_weekly_summary": None,
        "last_monthly_summary": None
    })
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(s, f, indent=2)
    send(f"🟢 Bot initialized {now_iso()}\nBaseline: {fmt(p)}\nATH: {fmt(s['ath'])}")
    sys.exit(0)

# Reset daily baseline at midnight CST/CDT
if s.get("daily_baseline_date") != today:
    s["daily_baseline"] = p
    s["daily_baseline_date"] = today

# Check for new ATH
if p > s["ath"] * 1.0000005:
    s["ath"] = p
    send(f"🚀 NEW ATH: {fmt(p)} at {now_iso()}")
    s["daily_baseline"] = p  # Reset daily baseline on new ATH

# Check for daily band movements
if s["daily_baseline"] > 0:
    pct = (p - s["daily_baseline"]) / s["daily_baseline"] * 100
    crossed = next((b for b in sorted(BANDS) if abs(pct) >= b - 1e-9), None)
    if crossed is not None:
        direction = "up" if pct > 0 else "down"
        emoji = "📈" if pct > 0 else "📉"
        send(f"{emoji} **Bitcoin is {direction} {abs(pct):.1f}% today**\n"
             f"Current: **{fmt(p)}**\n"
             f"All-Time High: *{fmt(s['ath'])}*")

# Weekly summary - Sunday at midnight CST/CDT
if now.weekday() == 6 and now.hour == 0 and s.get("last_weekly_summary") != today:
    data = market_data()
    ath_delta = ((p - s['ath']) / s['ath'] * 100) if s['ath'] > 0 else 0

    send(f"📊 **Weekly Summary**\n"
         f"*{now.strftime('%A, %B %d, %Y %I:%M%p')}*\n\n"
         f"BTC Price: **{fmt(p)}**\n"
         f"ATH: **{fmt(s['ath'])}**\n"
         f"ATH Δ: **{fmt_pct(ath_delta)}**\n\n"
         f"7d Change: **{fmt_pct(data['change_7d'])}**\n"
         f"30d Change: **{fmt_pct(data['change_30d'])}**")

    s["last_weekly_summary"] = today

# Monthly summary - Last day of month at midnight CST/CDT
def is_last_day_of_month(dt):
    """Check if date is the last day of its month"""
    next_day = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta
    next_day = next_day + timedelta(days=1)
    return next_day.month != dt.month

if is_last_day_of_month(now) and now.hour == 0 and s.get("last_monthly_summary") != today:
    data = market_data()

    send(f"📅 **Monthly Summary**\n"
         f"*{now.strftime('%A, %B %d, %Y %I:%M%p')}*\n\n"
         f"{now.strftime('%B')} EOM Price: **{fmt(p)}**\n\n"
         f"Circulating Supply: **{data['circulating_supply']:,.0f}**\n"
         f"Market Cap: **{fmt(data['market_cap'])}**")

    s["last_monthly_summary"] = today

# Update state
s["last_price"] = p
os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
with open(STATE_FILE, "w") as f:
    json.dump(s, f, indent=2)
