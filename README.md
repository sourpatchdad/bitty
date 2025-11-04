# Bitty BTC Bot 🚀
 
A lightweight Bitcoin price monitoring bot that sends Discord notifications for significant price movements, all-time highs, and regular market summaries. Runs automatically via GitHub Actions every 5 minutes.
 
## Features
 
- 🚨 **Price Band Alerts** - Get notified when BTC moves 5%, 10%, or 15% from midnight baseline
- 🎯 **All-Time High Tracking** - Instant alerts when BTC hits new ATHs
- 📊 **Weekly Summaries** - Sunday midnight reports with 7-day and 30-day performance
- 📅 **Monthly Summaries** - Month-over-month comparison with market data
- 🔄 **Spam Prevention** - Each band only triggers once per day
- 🛡️ **Robust Error Handling** - Automatic retries and graceful degradation
 
## Quick Start
 
### Prerequisites
 
- GitHub account (for GitHub Actions)
- Discord webhook URL ([How to create one](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks))
- Python 3.11+ (if running locally)
 
### Setup
 
1. **Fork/Clone this repository**
 
2. **Add Discord Webhook Secret**
   - Go to your repo → Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `DISCORD_WEBHOOK_URL`
   - Value: Your Discord webhook URL
 
3. **Enable GitHub Actions**
   - Go to Actions tab
   - Click "I understand my workflows, go ahead and enable them"
 
4. **Done!** The bot will run automatically every 5 minutes.
 
## Notifications
 
### 🟢 Bot Initialization (One-time)
 
Sent when the bot first starts up.
 
```
🟢 Bot initialized 2025-11-04T03:25:00Z
Baseline: $110,032
ATH: $126,080
```
 
### 🚀 New All-Time High
 
Triggered whenever BTC exceeds its previous ATH.
 
```
🚀 **New All-Time High: $127,500**
*Friday, November 15, 2025 03:32PM*
```
 
**Details:**
- Checks every 5 minutes
- No spam prevention (every new ATH triggers)
- Independent from daily band tracking
 
### 📈📉 Daily Band Alerts
 
Notified when BTC moves 5%, 10%, or 15% from midnight CST/CDT baseline.
 
**Up 5% Example:**
```
📈 **Bitcoin is up 5.2% today**
Current: **$115,584**
All-Time High: *$126,080*
```
 
**Down 10% Example:**
```
📉 **Bitcoin is down 10.1% today**
Current: **$98,900**
All-Time High: *$126,080*
```
 
**Details:**
- Baseline resets daily at midnight CST/CDT
- Each band (5%, 10%, 15%) triggers **once per day**
- If price drops after triggering, no duplicate alerts
- All bands reset at midnight for next day
 
**Example Day:**
```
12:00am CST: $110,000 (baseline set)
3:00am:      $115,500 → "up 5.0% today" ✅
6:00am:      $121,000 → "up 10.0% today" ✅
9:00am:      $118,000 (no alert - 5% already triggered)
12:00pm:     $126,500 → "up 15.0% today" ✅
Next day:    Bands reset, can trigger again
```
 
### 📊 Weekly Summary
 
Sent every **Sunday at midnight CST/CDT**.
 
```
📊 **Weekly Summary**
*Sunday, November 03, 2025 12:00AM*
 
BTC Price: **$112,450**
ATH: **$126,080**
ATH Δ: **-10.8%**
 
7d Change: **+3.2%**
30d Change: **-8.5%**
```
 
**Details:**
- Shows current price and distance from ATH
- 7-day and 30-day performance from CoinGecko
- Sent once per week
 
### 📅 Monthly Summary
 
Sent on the **1st of each month at midnight CST/CDT**.
 
```
📅 **Monthly Summary**
*Monday, December 01, 2025 12:00AM*
 
November EOM Price: **$115,500**
October EOM Price: **$110,032**
MoM Δ: **+5.0%**
 
Circulating Supply: **19,955,123**
Market Cap: **$2,305,127,950,000**
```
 
**Details:**
- Captures price at midnight on 1st of month
- Compares to previous month's stored price
- Shows month-over-month percentage change
- Includes Bitcoin supply and market cap metrics
- First month won't show MoM (no previous data)
 
### ⚠️ Error Alerts
 
Sent if API calls fail after all retry attempts.
 
```
⚠️ Error fetching BTC price: HTTPError('429 Too Many Requests')
```
 
## Configuration
 
All settings in `bot.py`:
 
```python
BANDS = [5, 10, 15]                     # Price movement thresholds (%)
TZ = ZoneInfo("America/Chicago")        # Timezone for midnight resets
MAX_RETRIES = 4                         # API retry attempts
RETRY_DELAYS = [3, 6, 12, 24]          # Retry delays in seconds
```
 
### Customization Examples
 
**Change band thresholds:**
```python
BANDS = [3, 7, 12, 20]  # More sensitive with additional bands
```
 
**Change timezone:**
```python
TZ = ZoneInfo("America/New_York")  # Use EST/EDT
TZ = ZoneInfo("Europe/London")      # Use GMT/BST
```
 
**Adjust scheduling (in `.github/workflows/btc-bot.yml`):**
```yaml
schedule:
  - cron: "*/10 * * * *"  # Every 10 minutes
  - cron: "0 * * * *"     # Every hour
```
 
## State File
 
The bot persists state in `.github/state/btc_state.json`:
 
```json
{
  "initialized": true,
  "ath": 126080.0,
  "daily_baseline": 110032.0,
  "daily_baseline_date": "2025-11-04",
  "triggered_bands": [5, 10],
  "last_price": 121000.0,
  "last_weekly_summary": "2025-11-03",
  "last_monthly_summary": "2025-11-01",
  "prev_month_eom_price": 110032.0
}
```
 
**Fields:**
- `initialized` - Bot has run at least once
- `ath` - Highest price ever seen
- `daily_baseline` - Price at last midnight CST/CDT
- `daily_baseline_date` - Date of current baseline
- `triggered_bands` - Bands triggered today (prevents spam)
- `last_price` - Most recent price check
- `last_weekly_summary` - Last Sunday's date
- `last_monthly_summary` - Last 1st of month date
- `prev_month_eom_price` - Previous month's price for MoM
 
The GitHub Actions workflow automatically commits state changes back to the repo.
 
## Local Development
 
### Setup
 
```bash
# Clone repo
git clone https://github.com/yourusername/bitty.git
cd bitty
 
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
 
# Install dependencies
pip install requests
```
 
### Run Locally
 
```bash
# Set webhook URL
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_WEBHOOK"
 
# Create state directory
mkdir -p .github/state
 
# Run bot
python bot.py
```
 
### Testing
 
**Test initialization:**
```bash
# Remove state file to trigger initialization
rm .github/state/btc_state.json
python bot.py
```
 
**Test with custom timezone (for testing summaries):**
```python
# In bot.py, temporarily change:
TZ = ZoneInfo("UTC")  # Or any timezone where it's currently midnight/Sunday
```
 
## Reliability Features
 
### Retry Logic
 
- **4 retry attempts** with exponential backoff
- Delays: 3s → 6s → 12s → 24s
- Total potential wait: ~45 seconds
 
### Timeouts
 
- Price API: 30 seconds
- Market data API: 45 seconds
- Discord webhook: 20 seconds
 
### Graceful Degradation
 
- Critical price fetch fails → Error notification sent
- Market data fails → Summaries skip silently
- Network issues → Automatic retries
 
## Troubleshooting
 
**No notifications appearing:**
- Verify `DISCORD_WEBHOOK_URL` secret is set correctly
- Check Actions tab for failed runs
- Test webhook manually: `curl -H "Content-Type: application/json" -d '{"content":"test"}' YOUR_WEBHOOK_URL`
 
**Duplicate weekly/monthly summaries:**
- Check system timezone matches expected
- Verify state file is being committed/persisted
- Look for `last_weekly_summary` / `last_monthly_summary` in state
 
**Failed GitHub Actions runs:**
- Check Actions tab logs for specific error
- Common: CoinGecko rate limiting (will auto-retry)
- Verify repo has write permissions for Actions
 
**Bot not triggering at expected times:**
- Remember: All times are CST/CDT (America/Chicago)
- GitHub Actions runs every 5 minutes in UTC
- Bot checks local CST time internally
 
**State file conflicts:**
- If multiple workflow runs overlap, git push may fail
- Check workflow has `concurrency.cancel-in-progress: false`
- State should auto-recover on next successful run
 
## API Information
 
**CoinGecko API:**
- Simple price endpoint: No auth required
- Market data endpoint: No auth required
- Rate limit: ~50 calls/minute (free tier)
- Bot makes 1-2 API calls every 5 minutes
 
**No API key needed** - CoinGecko's free tier is sufficient for this bot's usage pattern.
 
## Security
 
- ✅ Webhook URL stored as GitHub secret (never exposed)
- ✅ State file contains no sensitive data (safe to commit)
- ✅ No API keys required
- ✅ Runs in isolated GitHub Actions environment
 
**Important:** Never commit your Discord webhook URL to the repository!
 
## Contributing
 
Contributions welcome! Please:
 
1. Fork the repo
2. Create a feature branch
3. Test changes locally
4. Submit a pull request
 
## License
 
MIT License - See [LICENSE](LICENSE) file for details
 
## Credits
 
Built with:
- [CoinGecko API](https://www.coingecko.com/en/api) for Bitcoin data
- [Discord Webhooks](https://discord.com/developers/docs/resources/webhook) for notifications
- [GitHub Actions](https://github.com/features/actions) for automation
 
---
 
**Questions or issues?** Open an issue on GitHub!
