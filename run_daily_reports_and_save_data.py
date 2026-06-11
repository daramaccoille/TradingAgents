import os
import datetime
import time
import traceback
import yfinance as yf
from pathlib import Path
from run_metal_analysis import run_analysis_for_ticker

# Metal configuration
METALS = {
    "GOLD": "GC=F",
    "SILVER": "SI=F",
    "COPPER": "HG=F",
    "PLATINUM": "PL=F",
    "PALLADIUM": "PA=F"
}

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
        # Default date to yesterday
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        target_date = yesterday.strftime("%Y-%m-%d")
    
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
