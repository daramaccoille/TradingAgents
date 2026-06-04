from run_metal_analysis import run_analysis_for_ticker
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run daily trading agent analysis for Copper.")
    parser.add_argument("--date", type=str, default=None, help="Analysis date YYYY-MM-DD (default: yesterday)")
    args = parser.parse_args()
    
    # HG=F is the yfinance ticker for Copper futures
    run_analysis_for_ticker("HG=F", args.date)
