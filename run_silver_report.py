from run_metal_analysis import run_analysis_for_ticker
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run daily trading agent analysis for Silver (XAGUSD).")
    parser.add_argument("--date", type=str, default=None, help="Analysis date YYYY-MM-DD (default: yesterday)")
    args = parser.parse_args()
    
    # SI=F is the yfinance ticker for Silver futures
    run_analysis_for_ticker("SI=F", args.date)
