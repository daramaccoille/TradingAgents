from run_metal_analysis import run_analysis_for_ticker
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run daily trading agent analysis for Palladium.")
    parser.add_argument("--date", type=str, default=None, help="Analysis date YYYY-MM-DD (default: yesterday)")
    args = parser.parse_args()
    
    # PA=F is the yfinance ticker for Palladium futures
    run_analysis_for_ticker("PA=F", args.date)
