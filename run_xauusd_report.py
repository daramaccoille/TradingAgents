from run_metal_analysis import run_analysis_for_ticker
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run daily trading agent analysis for Gold (XAUUSD).")
    parser.add_argument("--date", type=str, default=None, help="Analysis date YYYY-MM-DD (default: yesterday)")
    args = parser.parse_args()
    
    # GC=F is the yfinance ticker for Gold futures
    run_analysis_for_ticker("GC=F", args.date)
