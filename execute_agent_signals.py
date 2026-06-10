import asyncio
import os
import argparse
import re
import json
import datetime
from pathlib import Path
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client
from rich.console import Console

# Load environment variables
load_dotenv()

# Configuration Defaults
DEFAULT_SERVER_URL = os.environ.get("MT5_MCP_SERVER_URL", "http://127.0.0.1:8020/sse")
MT5_PATH = os.environ.get("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
MT5_LOGIN = os.environ.get("MT5_LOGIN")
MT5_PASSWORD = os.environ.get("MT5_PASSWORD")
MT5_SERVER = os.environ.get("MT5_SERVER")

# Ticker to MT5 Symbol Mapping
TICKER_MAPPING = {
    "GC=F": "XAUUSD",      # Gold futures -> XAUUSD Spot
    "SI=F": "XAGUSD",      # Silver futures -> XAGUSD Spot
    "HG=F": "COPPER",      # Copper futures -> COPPER Spot
    "PL=F": "XPTUSD",      # Platinum futures -> XPTUSD Spot
    "PA=F": "XPDUSD",      # Palladium futures -> XPDUSD Spot
    "XAUUSD": "XAUUSD",
    "XAGUSD": "XAGUSD",
    "COPPER": "COPPER",
    "PLATINUM": "XPTUSD",
    "PALLADIUM": "XPDUSD"
}

console = Console()

def parse_decision_markdown(md_text: str):
    """Extract Rating, Entry, SL, and TP from Portfolio Manager markdown decision."""
    rating_match = re.search(r"\*\*Rating\*\*:\s*(\w+)", md_text, re.IGNORECASE)
    entry_match = re.search(r"\*\*Entry Price\*\*:\s*([\d\.]+)", md_text, re.IGNORECASE)
    sl_match = re.search(r"\*\*Stop Loss\*\*:\s*([\d\.]+)", md_text, re.IGNORECASE)
    tp_match = re.search(r"\*\*Take Profit\*\*:\s*([\d\.]+)", md_text, re.IGNORECASE)
    
    rating = rating_match.group(1).strip() if rating_match else None
    entry = float(entry_match.group(1)) if entry_match else None
    sl = float(sl_match.group(1)) if sl_match else None
    tp = float(tp_match.group(1)) if tp_match else None
    
    return rating, entry, sl, tp

def parse_tool_result(res):
    if not res or not hasattr(res, "content") or not res.content:
        return None
    try:
        return json.loads(res.content[0].text)
    except Exception:
        text = res.content[0].text
        if text.lower() == "true": return True
        if text.lower() == "false": return False
        return text

async def execute_trade_on_mt5(session, mt5_symbol: str, signal: str, sl: float = None, tp: float = None, volume: float = 0.01):
    """Handles position checking, closing opposite trades, and opening new ones."""
    console.print(f"[bold cyan]Syncing trades for {mt5_symbol} (Signal: {signal})...[/bold cyan]")
    
    # 1. Check existing positions
    pos_res = await session.call_tool("positions_get", {"symbol": mt5_symbol})
    positions = parse_tool_result(pos_res)
    
    # Analyze current positions
    existing_buy = None
    existing_sell = None
    
    if positions:
        for pos in positions:
            if pos.get("type") == 0:  # 0 is BUY
                existing_buy = pos
            elif pos.get("type") == 1:  # 1 is SELL
                existing_sell = pos
                
    # 2. Close opposite trades
    if signal == "BUY" and existing_sell:
        console.print(f"[yellow]Closing opposite SELL position #{existing_sell.get('ticket')}...[/yellow]")
        await close_position(session, existing_sell)
        existing_sell = None
    elif signal == "SELL" and existing_buy:
        console.print(f"[yellow]Closing opposite BUY position #{existing_buy.get('ticket')}...[/yellow]")
        await close_position(session, existing_buy)
        existing_buy = None
    elif signal == "HOLD":
        console.print("[dim]Signal is HOLD. Maintaining current positions (no action taken).[/dim]")
        return

    # 3. Open new trade if none exists
    if signal == "BUY" and not existing_buy:
        await open_position(session, mt5_symbol, 0, volume, sl, tp)
    elif signal == "SELL" and not existing_sell:
        await open_position(session, mt5_symbol, 1, volume, sl, tp)
    else:
        console.print(f"[green]✓ Trade already matches signal. Holding position.[/green]")

async def close_position(session, position):
    ticket = position.get("ticket")
    symbol = position.get("symbol")
    volume = position.get("volume")
    pos_type = position.get("type")
    
    close_type = 1 if pos_type == 0 else 0
    tick_res = await session.call_tool("get_symbol_info_tick", {"symbol": symbol})
    tick = parse_tool_result(tick_res)
    price = tick.get("bid") if close_type == 1 else tick.get("ask")
    
    order_req = {
        "action": 1, # TRADE_ACTION_DEAL
        "symbol": symbol,
        "volume": float(volume),
        "type": close_type,
        "price": float(price),
        "position": int(ticket),
        "comment": "Close via Agent Signal"
    }
    
    res = await session.call_tool("order_send", {"request": order_req})
    result = parse_tool_result(res)
    if result:
        console.print(f"[green]✓ Position #{ticket} closed successfully.[/green]")

async def open_position(session, symbol, type_code, volume, sl, tp):
    await session.call_tool("symbol_select", {"symbol": symbol, "visible": True})
    tick_res = await session.call_tool("get_symbol_info_tick", {"symbol": symbol})
    tick = parse_tool_result(tick_res)
    
    price = tick.get("ask") if type_code == 0 else tick.get("bid")
    action_desc = "BUY" if type_code == 0 else "SELL"
    
    order_req = {
        "action": 1,
        "symbol": symbol,
        "volume": float(volume),
        "type": type_code,
        "price": float(price),
        "comment": "Agent Daily Signal"
    }
    
    # Include SL/TP if they are logical and provided
    if sl: order_req["sl"] = float(sl)
    if tp: order_req["tp"] = float(tp)
    
    console.print(f"[cyan]Opening {action_desc} position: {volume} lots of {symbol} at {price}...[/cyan]")
    try:
        res = await session.call_tool("order_send", {"request": order_req})
        result = parse_tool_result(res)
        if result:
            console.print(f"[green]✓ Order executed! Ticket: #{result.get('order')}[/green]")
    except Exception as e:
        console.print(f"[red]Error placing trade: {e}[/red]")

async def run_pipeline_and_execute(ticker: str, volume: float):
    """Runs a fresh TradingAgents run and executes the resulting advice."""
    from run_metal_analysis import run_analysis_for_ticker
    
    # 1. Run the daily agent report pipeline
    target_date = datetime.datetime.now().strftime("%Y-%m-%d")
    console.print(f"[bold green]Starting fresh Agent Analysis for {ticker}...[/bold green]")
    
    # This runs the LangGraph framework and saves reports
    success = run_analysis_for_ticker(ticker, target_date)
    if not success:
        console.print("[red]Agent analysis pipeline failed. Aborting trade execution.[/red]")
        return
        
    # 2. Find the most recently generated report JSON log to read the decision
    log_dir = Path("reports")
    # Ticker folder matching
    from cli.html_reporter import TICKER_TO_METAL_NAME
    metal_name = TICKER_TO_METAL_NAME.get(ticker.upper(), ticker.upper()).upper()
    
    batch_dirs = [d for d in log_dir.iterdir() if d.is_dir() and metal_name in d.name]
    if not batch_dirs:
        console.print("[red]Could not find generated report batch directory.[/red]")
        return
        
    latest_batch = max(batch_dirs, key=os.path.getmtime)
    complete_report_path = latest_batch / "complete.md"
    
    if not complete_report_path.exists():
        console.print("[red]Could not find complete.md report file.[/red]")
        return
        
    with open(complete_report_path, "r", encoding="utf-8") as f:
        report_content = f.read()
        
    # Extract decision block
    # Search for Portfolio Manager Decision
    pm_section = re.search(r"## Portfolio Manager Decision.*?(##|$)", report_content, re.DOTALL)
    if not pm_section:
        console.print("[red]Could not extract Portfolio Manager Decision block from report.[/red]")
        return
        
    pm_text = pm_section.group(0)
    rating, entry, sl, tp = parse_decision_markdown(pm_text)
    
    if not rating:
        console.print("[red]Could not parse trading rating from decision.[/red]")
        return
        
    console.print(f"\n[bold green]--- Parsed Signal ---[/bold green]")
    console.print(f"  - Rating: {rating}")
    console.print(f"  - Entry Target: {entry or 'Market'}")
    console.print(f"  - Stop Loss: {sl or 'None'}")
    console.print(f"  - Take Profit: {tp or 'None'}")
    
    # Map Rating to Action
    # Buy/Overweight -> BUY; Sell/Underweight -> SELL; Hold -> HOLD
    signal = "HOLD"
    if rating.upper() in ["BUY", "OVERWEIGHT"]:
        signal = "BUY"
    elif rating.upper() in ["SELL", "UNDERWEIGHT"]:
        signal = "SELL"
        
    mt5_symbol = TICKER_MAPPING.get(ticker.upper(), ticker.upper())
    
    # 3. Connect to MT5 MCP Server and place trade
    async def place_trade_callback(session):
        await execute_trade_on_mt5(session, mt5_symbol, signal, sl, tp, volume)
        
    await execute_mcp_command(DEFAULT_SERVER_URL, place_trade_callback)

async def execute_mcp_command(url, action_func):
    async with sse_client(url) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            await session.call_tool("initialize", {"path": MT5_PATH})
            if MT5_LOGIN and MT5_PASSWORD and MT5_SERVER:
                await session.call_tool("login", {
                    "login": int(MT5_LOGIN),
                    "password": MT5_PASSWORD,
                    "server": MT5_SERVER
                })
            
            await action_func(session)
            await session.call_tool("shutdown", {})

def main():
    parser = argparse.ArgumentParser(description="Automate MT5 execution of TradingAgents signals.")
    parser.add_argument("--ticker", required=True, help="Metal ticker to analyze and trade (e.g. GC=F, XAUUSD)")
    parser.add_argument("--volume", type=float, default=0.01, help="Lots volume size to trade (default: 0.01)")
    args = parser.parse_args()
    
    asyncio.run(run_pipeline_and_execute(args.ticker, args.volume))

if __name__ == "__main__":
    main()
