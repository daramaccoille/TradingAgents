from run_metal_analysis import run_analysis_for_ticker
import argparse

METALS = {
    "GOLD": "GC=F",
    "SILVER": "SI=F",
    "COPPER": "HG=F",
    "PLATINUM": "PL=F",
    "PALLADIUM": "PA=F"
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run daily trading agent analysis for all 5 metals.")
    parser.add_argument("--date", type=str, default=None, help="Analysis date YYYY-MM-DD (default: yesterday)")
    args = parser.parse_args()
    
    print("="*60)
    print("STARTING BULK METALS TRADING AGENTS RUN")
    print("="*60)
    
    for metal, ticker in METALS.items():
        try:
            success = run_analysis_for_ticker(ticker, args.date)
            if success:
                print(f"\n[SUCCESS] Completed run for {metal} ({ticker})")
            else:
                print(f"\n[FAILURE] Failed run for {metal} ({ticker})")
        except Exception as e:
            print(f"\n[ERROR] Error running for {metal} ({ticker}): {e}")
            
    print("\nBulk metal runs processed!")
