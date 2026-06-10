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

def get_ticker_price(ticker: str, target_date: str) -> float:
    """Fetch the closing price of the ticker for the target date, or the latest price as fallback."""
    try:
        ticker_obj = yf.Ticker(ticker)
        start_dt = datetime.datetime.strptime(target_date, "%Y-%m-%d")
        end_dt = start_dt + datetime.timedelta(days=1)
        end_date = end_dt.strftime("%Y-%m-%d")
        
        hist = ticker_obj.history(start=target_date, end=end_date)
        if not hist.empty and "Close" in hist.columns:
            return float(hist["Close"].iloc[0])
            
        # Fallback to period history
        hist = ticker_obj.history(period="5d")
        if not hist.empty and "Close" in hist.columns:
            return float(hist["Close"].iloc[-1])
            
        # Fallback to info
        info = ticker_obj.info
        price = info.get("regularMarketPrice") or info.get("previousClose")
        if price is not None:
            return float(price)
    except Exception as e:
        print(f"Error fetching price for {ticker}: {e}")
    return 0.0

def main():
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
            
    # Default date to yesterday
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    target_date = yesterday.strftime("%Y-%m-%d")
    
    print("="*60)
    print(f"STARTING DAILY REPORT RUN FOR DATE: {target_date}")
    print("="*60)
    
    for metal, ticker in METALS.items():
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
                price = get_ticker_price(ticker, target_date)
                
                # Save to prices.csv
                with open(prices_csv_path, "a", encoding="utf-8") as f:
                    f.write(f'"{run_timestamp}","{target_date}","{metal}","{ticker}",{price:.2f}\n')
                    
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
    main()
