import sys
sys.path.append(r"c:\Users\daraw\Downloads\TradingAgents")
from tradingagents.dataflows.y_finance import get_stock_stats_indicators_window

try:
    res = get_stock_stats_indicators_window("GC=F", "macdh", "2026-05-04", 5)
    print("SUCCESS")
    print(res)
except Exception as e:
    print("ERROR:", e)
