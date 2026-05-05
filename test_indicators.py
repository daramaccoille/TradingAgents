import sys
import os

# Add TradingAgents to path so we can import from it
sys.path.append(r"c:\Users\daraw\Downloads\TradingAgents")

from tradingagents.dataflows.y_finance import _get_stock_stats_bulk
try:
    res = _get_stock_stats_bulk("GC=F", "macdh", "2026-05-04")
    print("SUCCESS")
    print(list(res.items())[-5:])
except Exception as e:
    print("ERROR:", e)
