import os
import datetime
import time
import traceback
import logging
import yfinance as yf
from pathlib import Path
from run_metal_analysis import run_analysis_for_ticker

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("daily_pipeline")

# Metal configuration
METALS = {
    "GOLD": "GC=F",
    "SILVER": "SI=F",
    "COPPER": "HG=F",
    "PLATINUM": "PL=F",
    "PALLADIUM": "PA=F"
}

# Static list of US/CME holidays where commodity futures do not trade.
# Add new years as needed. Dates in YYYY-MM-DD format.
_CME_HOLIDAYS = {
    # 2024
    "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29",
    "2024-05-27", "2024-06-19", "2024-07-04", "2024-09-02",
    "2024-11-28", "2024-12-25",
    # 2025
    "2025-01-01", "2025-01-20", "2025-02-17", "2025-04-18",
    "2025-05-26", "2025-06-19", "2025-07-04", "2025-09-01",
    "2025-11-27", "2025-12-25",
    # 2026
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03",
    "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07",
    "2026-11-26", "2026-12-25",
}


def get_last_trading_day(from_date: datetime.date) -> datetime.date:
    """Return the most recent trading day on or before from_date.

    Skips weekends (Saturday=5, Sunday=6) and CME commodity holidays.
    Walks backward at most 10 days to handle extended holiday periods.
    """
    candidate = from_date
    for _ in range(10):
        if candidate.weekday() < 5 and candidate.strftime("%Y-%m-%d") not in _CME_HOLIDAYS:
            return candidate
        candidate -= datetime.timedelta(days=1)
    # Fallback: return the original date (shouldn't happen in practice)
    return from_date


def get_ticker_price(ticker: str, target_date: str) -> tuple[float, str]:
    """Fetch the closing price and the candle timestamp of the ticker for the target date using H4 timeframe."""
    try:
        ticker_obj = yf.Ticker(ticker)
        # Download 1h data to resample to H4.
        # We need a range around the target date to ensure we get the full day's H4 candles.
        target_dt = datetime.datetime.strptime(target_date, "%Y-%m-%d")
        start_dt = target_dt - datetime.timedelta(days=5)
        end_dt = target_dt + datetime.timedelta(days=2)
        
        hist = ticker_obj.history(start=start_dt.strftime("%Y-%m-%d"), end=end_dt.strftime("%Y-%m-%d"), interval="1h")
        if hist.empty:
            hist = ticker_obj.history(period="7d", interval="1h")
            
        if not hist.empty:
            # Resample to 4H
            hist_h4 = hist.resample('4h').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
            
            if not hist_h4.empty:
                # Format index to YYYY-MM-DD
                hist_h4['DateStr'] = hist_h4.index.map(lambda x: x.strftime("%Y-%m-%d"))
                matching_candles = hist_h4[hist_h4['DateStr'] == target_date]
                
                if not matching_candles.empty:
                    latest_candle = matching_candles.iloc[-1]
                    price = float(latest_candle['Close'])
                    timestamp = str(matching_candles.index[-1])
                    return price, timestamp
                else:
                    # Fallback to the latest available H4 candle in hist_h4
                    latest_candle = hist_h4.iloc[-1]
                    price = float(latest_candle['Close'])
                    timestamp = str(hist_h4.index[-1])
                    return price, timestamp
        
        # Fallback to daily close if H4/1h download fails
        hist = ticker_obj.history(start=target_date, end=(target_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d"))
        if not hist.empty and "Close" in hist.columns:
            return float(hist["Close"].iloc[0]), f"{target_date} 00:00:00"
            
        hist = ticker_obj.history(period="5d")
        if not hist.empty and "Close" in hist.columns:
            return float(hist["Close"].iloc[-1]), f"{hist.index[-1].strftime('%Y-%m-%d')} 00:00:00"
            
        info = ticker_obj.info
        price = info.get("regularMarketPrice") or info.get("previousClose") or 0.0
        return float(price), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"Error fetching H4 price for {ticker}: {e}")
        return 0.0, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main(date_arg=None):
    # Setup directory
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    # Path for CSVs and logs
    prices_csv_path = reports_dir / "prices.csv"
    times_csv_path = reports_dir / "times.csv"
    error_log_path = reports_dir / "error.log"
    
    # Initialize files if they don't exist
    if not prices_csv_path.exists():
        with open(prices_csv_path, "w", encoding="utf-8") as f:
            f.write("Timestamp,Date,Metal,Ticker,Price\n")
            
    if not times_csv_path.exists():
        with open(times_csv_path, "w", encoding="utf-8") as f:
            f.write("Timestamp,Date,Metal,Ticker,ExecutionTimeSeconds\n")
            
    if date_arg:
        target_date = date_arg
    else:
        # Default to the last valid trading day (handles weekends and CME holidays)
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).date()
        last_trading = get_last_trading_day(yesterday)
        target_date = last_trading.strftime("%Y-%m-%d")
        logger.info("Resolved default target date to last trading day: %s", target_date)
    
    # Load already completed tickers for target_date to support resumption
    completed_tickers = set()
    if prices_csv_path.exists():
        try:
            with open(prices_csv_path, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split(",")
                    if len(parts) >= 4:
                        date_val = parts[1].replace('"', '')
                        ticker_val = parts[3].replace('"', '')
                        if date_val == target_date:
                            completed_tickers.add(ticker_val)
        except Exception as e:
            print(f"Error reading completed tickers: {e}")

    print("="*60)
    print(f"STARTING DAILY REPORT RUN FOR DATE: {target_date}")
    print("="*60)
    
    for metal, ticker in METALS.items():
        if ticker in completed_tickers:
            print(f"Skipping {metal} ({ticker}) as it is already completed for {target_date}.")
            continue
            
        run_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_time = time.time()
        
        print(f"\n--- Processing {metal} ({ticker}) ---")
        try:
            # Run the daily agent report pipeline
            success = run_analysis_for_ticker(ticker, target_date)
            exec_time = time.time() - start_time
            
            if success:
                print(f"[SUCCESS] Finished report for {metal}")
                
                # Fetch price
                price, candle_ts = get_ticker_price(ticker, target_date)
                
                # Save to prices.csv
                with open(prices_csv_path, "a", encoding="utf-8") as f:
                    f.write(f'"{candle_ts}","{target_date}","{metal}","{ticker}",{price:.2f}\n')
                    
                # Save to times.csv
                with open(times_csv_path, "a", encoding="utf-8") as f:
                    f.write(f'"{run_timestamp}","{target_date}","{metal}","{ticker}",{exec_time:.2f}\n')
            else:
                raise RuntimeError("run_analysis_for_ticker returned False")
                
        except Exception as e:
            exec_time = time.time() - start_time
            err_msg = f"[{run_timestamp}] Error processing {metal} ({ticker}) for {target_date}: {e}\n"
            print(f"[ERROR] {err_msg}")
            
            # Log to error.log
            with open(error_log_path, "a", encoding="utf-8") as f:
                f.write(err_msg)
                f.write(traceback.format_exc())
                f.write("-" * 60 + "\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run daily trading reports and save prices/execution times.")
    parser.add_argument("--date", type=str, default=None, help="Analysis date YYYY-MM-DD (default: yesterday)")
    args = parser.parse_args()
    main(args.date)
