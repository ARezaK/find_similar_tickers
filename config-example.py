# copy this file to config.py and fill in your details
FEED_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=S-1&output=atom"
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/TM6E0J/B0813N/9utRw94n7s1sn1"
PROCESSED_LOG = "processed_filings.txt"
TICKER_CACHE_FILE = "tickers_cache.txt"
TICKER_SOURCE_URL = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt"
CACHE_MAX_AGE = 30 * 24 * 60 * 60
HEADERS = {"User-Agent": "TickerCheckerBot/1.0 (joe@bobjoe.com)"}