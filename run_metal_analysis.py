from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
import os
from dotenv import load_dotenv
from pathlib import Path
import datetime

# Load environment variables
load_dotenv()

def run_analysis_for_ticker(ticker: str, target_date: str = None):
    """Run multi-agent trading analysis for a specific ticker and save results to disk."""
    # Setup config to use Google LLM (since GOOGLE_API_KEY is configured in .env)
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = "ollama"
    config["deep_think_llm"] = "qwen2.5:0.5b"   # Use local CPU-friendly model
    config["quick_think_llm"] = "qwen2.5:0.5b"
    config["max_debate_rounds"] = 1
    config["max_risk_discuss_rounds"] = 1

    # Default to yesterday if target_date is not provided
    if not target_date:
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        target_date = yesterday.strftime("%Y-%m-%d")

    print(f"\n" + "="*60)
    print(f"Starting TradingAgents analysis for {ticker} on {target_date}...")
    print("="*60)

    # Initialize graph
    ta = TradingAgentsGraph(debug=True, config=config)

    try:
        state, decision = ta.propagate(ticker, target_date)

        print("\n--- DECISION ---")
        print(decision)

        # Save reports using main save_report_to_disk function
        from cli.main import save_report_to_disk
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Get metal name for folder path formatting
        from cli.html_reporter import TICKER_TO_METAL_NAME
        metal_name = TICKER_TO_METAL_NAME.get(ticker.upper(), ticker.upper()).upper()
        save_path = Path.cwd() / "reports" / f"{metal_name}_{timestamp}"
        
        report_file = save_report_to_disk(state, ticker, save_path)
        
        print(f"\n[OK] Saved report successfully to: {save_path.resolve()}")
        print(f"  Complete report file: {report_file.name}")
        return True
    except Exception as e:
        print(f"\nAn error occurred during run for {ticker}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run daily trading agent analysis for a metal ticker.")
    parser.add_argument("--ticker", type=str, default="GC=F", help="Ticker symbol (default: GC=F)")
    parser.add_argument("--date", type=str, default=None, help="Analysis date YYYY-MM-DD (default: yesterday)")
    args = parser.parse_args()
    
    run_analysis_for_ticker(args.ticker, args.date)
