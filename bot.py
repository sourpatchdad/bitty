import os, json, requests, sys, time
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
MAX_RETRIES = 4
RETRY_DELAYS = [3, 6, 12, 24]  # exponential backoff in seconds

def now_utc():
    return datetime.now(timezone.utc)

def now_cst():
    return datetime.now(TZ)

def now_iso():
    return now_utc().isoformat(timespec="seconds")

def retry_request(func, *args, **kwargs):
    """Execute a function with exponential backoff retry logic"""
    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise e
            time.sleep(RETRY_DELAYS[attempt])
    return None

def send(msg):
    """Send Discord notification with retry logic"""
    def _send():
        r = requests.post(WEBHOOK_URL, json={"content": msg}, timeout=20)
        r.raise_for_status()

    try:
        retry_request(_send)
    except Exception as e:
        print(f"Failed to send Discord notification after {MAX_RETRIES} attempts: {e}")

def price():
    """Fetch current BTC price with retry logic"""
    def _fetch():
        r = requests.get(COINGECKO_SIMPLE, timeout=30)
        r.raise_for_status()
        return float(r.json()["bitcoin"]["usd"])

    try:
        return retry_request(_fetch)
    except Exception as e:
        print(f"Failed to fetch price after {MAX_RETRIES} attempts: {e}")
        send(f"⚠️ Error fetching BTC price: {str(e)}")
        sys.exit(1)

def market_data():
    """Fetch full market data from CoinGecko with retry logic"""
    def _fetch():
        r = requests.get(COINGECKO_FULL, timeout=45)
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

    try:
        return retry_request(_fetch)
    except Exception as e:
        print(f"Failed to fetch market data after {MAX_RETRIES} attempts: {e}")
        return None

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
        "triggered_bands": [],
        "last_price": 0.0,
        "last_weekly_summary": None,
        "last_monthly_summary": None,
        "prev_month_eom_price": None
    }

# Get current price and market data
p = price()
now = now_cst()
today = now.date().isoformat()

# Initialize if needed
if not s["initialized"]:
    data = market_data()
    if data is None:
        print("Failed to fetch market data during initialization")
        sys.exit(1)

    s.update({
        "initialized": True,
        "ath": max(data["ath"], p),
        "daily_baseline": p,
        "daily_baseline_date": today,
        "triggered_bands": [],
        "last_price": p,
        "last_weekly_summary": None,
        "last_monthly_summary": None,
        "prev_month_eom_price": None
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
    s["triggered_bands"] = []  # Reset triggered bands for new day

# Check for new ATH
if p > s["ath"] * 1.0000005:
    s["ath"] = p
    send(f"🚀 **New All-Time High: {fmt(p)}**\n*{now.strftime('%A, %B %d, %Y %I:%M%p')}*")

# Check for daily band movements with spam prevention
if s["daily_baseline"] > 0:
    pct = (p - s["daily_baseline"]) / s["daily_baseline"] * 100
    crossed = next((b for b in sorted(BANDS) if abs(pct) >= b - 1e-9), None)

    # Only notify if band crossed and not already triggered today
    if crossed is not None and crossed not in s.get("triggered_bands", []):
        direction = "up" if pct > 0 else "down"
        emoji = "📈" if pct > 0 else "📉"
        send(f"{emoji} **Bitcoin is {direction} {abs(pct):.1f}% today.**\n"
             f"Current: **{fmt(p)}**\n"
             f"All-Time High: *{fmt(s['ath'])}*")

        # Mark this band as triggered for today
        if "triggered_bands" not in s:
            s["triggered_bands"] = []
        s["triggered_bands"].append(crossed)

# Weekly summary - Sunday at midnight CST/CDT
if now.weekday() == 6 and now.hour == 0 and s.get("last_weekly_summary") != today:
    data = market_data()

    if data is not None:
        ath_delta = ((p - s['ath']) / s['ath'] * 100) if s['ath'] > 0 else 0

        send(f"📊 **Weekly Summary**\n"
             f"*{now.strftime('%A, %B %d, %Y %I:%M%p')}*\n\n"
             f"BTC Price: **{fmt(p)}**\n"
             f"ATH: **{fmt(s['ath'])}**\n"
             f"ATH Δ: **{fmt_pct(ath_delta)}**\n\n"
             f"7d Change: **{fmt_pct(data['change_7d'])}**\n"
             f"30d Change: **{fmt_pct(data['change_30d'])}**")

        s["last_weekly_summary"] = today
    else:
        print("Skipping weekly summary due to market data API failure")

# Monthly summary - First day of month at midnight CST/CDT
if now.day == 1 and now.hour == 0 and s.get("last_monthly_summary") != today:
    data = market_data()

    if data is not None:
        # Get previous month name (the month that just ended)
        from datetime import timedelta
        prev_month = (now.replace(day=1) - timedelta(days=1)).strftime('%B')

        msg = f"📅 **Monthly Summary**\n*{now.strftime('%A, %B %d, %Y %I:%M%p')}*\n\n"
        msg += f"{prev_month} EOM Price: **{fmt(p)}**\n"

        # Add MoM comparison if we have previous month's stored price
        if s.get("prev_month_eom_price") is not None and s["prev_month_eom_price"] > 0:
            mom_pct = ((p - s["prev_month_eom_price"]) / s["prev_month_eom_price"] * 100)

            # Get the name of the month before the previous month
            # On Dec 1: prev_month is "November", so we want "October"
            prev_prev_month_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1) - timedelta(days=1)
            prev_prev_month = prev_prev_month_date.strftime('%B')

            msg += f"{prev_prev_month} EOM Price: **{fmt(s['prev_month_eom_price'])}**\n"
            msg += f"MoM Δ: **{fmt_pct(mom_pct)}**\n"

        msg += f"\nCirculating Supply: **{data['circulating_supply']:,.0f}**\n"
        msg += f"Market Cap: **{fmt(data['market_cap'])}**"

        send(msg)

        # Store current price for next month's comparison
        s["prev_month_eom_price"] = p
        s["last_monthly_summary"] = today
    else:
        print("Skipping monthly summary due to market data API failure")

# Update state
s["last_price"] = p
os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
with open(STATE_FILE, "w") as f:
    json.dump(s, f, indent=2)
