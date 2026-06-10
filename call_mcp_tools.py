import asyncio
import os
import argparse
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client
from rich.console import Console
from rich.table import Table

# Load environment variables
load_dotenv()

# Configuration Defaults
DEFAULT_SERVER_URL = os.environ.get("MT5_MCP_SERVER_URL", "http://127.0.0.1:8020/sse")
MT5_PATH = os.environ.get("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
MT5_LOGIN = os.environ.get("MT5_LOGIN")
MT5_PASSWORD = os.environ.get("MT5_PASSWORD")
MT5_SERVER = os.environ.get("MT5_SERVER")

# Metal Ticker Mapping
METAL_TICKERS = {
    "GOLD": "XAUUSD",
    "SILVER": "XAGUSD",
    "COPPER": "COPPER",
    "PLATINUM": "XPTUSD",
    "PALLADIUM": "XPDUSD"
}

console = Console()

def parse_tool_result(res):
    """Helper to parse MCP tool result into python objects."""
    if not res or not hasattr(res, "content") or not res.content:
        return None
    
    text = res.content[0].text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Return raw string if not JSON
        if text.lower() == "true":
            return True
        if text.lower() == "false":
            return False
        return text

async def execute_mcp_command(url, action_func):
    """Runs a session client, initializes it, and executes the custom action."""
    try:
        async with sse_client(url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                # Automatically initialize MT5 on each run
                console.print(f"[dim]Initializing MT5 terminal connection...[/dim]")
                init_res = await session.call_tool("initialize", {"path": MT5_PATH})
                if not parse_tool_result(init_res):
                    console.print("[red]Error: Failed to initialize MT5 connection.[/red]")
                    return
                
                # Automatically login if credentials are provided in .env
                if MT5_LOGIN and MT5_PASSWORD and MT5_SERVER:
                    console.print(f"[dim]Logging in to account {MT5_LOGIN}...[/dim]")
                    login_res = await session.call_tool("login", {
                        "login": int(MT5_LOGIN),
                        "password": MT5_PASSWORD,
                        "server": MT5_SERVER
                    })
                    if not parse_tool_result(login_res):
                        console.print("[yellow]Warning: Account login failed, using current active terminal session.[/yellow]")
                
                # Execute the specific command logic
                await action_func(session)
                
                # Graceful shutdown
                await session.call_tool("shutdown", {})
    except Exception as e:
        console.print(f"[red]Failed to connect to MCP Server at {url}: {e}[/red]")
        console.print("[yellow]Make sure the server is running with 'uv run fastmcp dev inspector src/mcp_mt5/main.py' or in http mode.[/yellow]")

# --- Command Handlers ---

async def handle_account(session):
    res = await session.call_tool("get_account_info", {})
    info = parse_tool_result(res)
    
    if not info:
        console.print("[red]Failed to retrieve account info.[/red]")
        return
        
    table = Table(title="MetaTrader 5 Account Details", show_header=True, header_style="bold magenta")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Account Holder", info.get("name"))
    table.add_row("Login Number", str(info.get("login")))
    table.add_row("Broker Server", info.get("server"))
    table.add_row("Leverage", f"1:{info.get('leverage')}")
    table.add_row("Currency", info.get("currency"))
    table.add_row("Balance", f"${info.get('balance'):,.2f}")
    table.add_row("Equity", f"${info.get('equity'):,.2f}")
    table.add_row("Margin", f"${info.get('margin'):,.2f}")
    table.add_row("Free Margin", f"${info.get('margin_free'):,.2f}")
    table.add_row("Floating Profit/Loss", f"${info.get('profit'):,.2f}", style="bold" if info.get('profit', 0) >= 0 else "bold red")
    
    console.print(table)

async def handle_positions(session):
    res = await session.call_tool("positions_get", {})
    positions = parse_tool_result(res)
    
    if not positions:
        console.print("[yellow]No open positions found.[/yellow]")
        return
        
    table = Table(title="Active MT5 Positions", show_header=True, header_style="bold blue")
    table.add_column("Ticket", style="dim")
    table.add_column("Symbol", style="cyan")
    table.add_column("Type", style="bold")
    table.add_column("Volume (Lots)", style="green")
    table.add_column("Open Price", style="yellow")
    table.add_column("Current Price", style="yellow")
    table.add_column("Profit ($)", style="bold")
    
    for pos in positions:
        # type 0 is Buy, type 1 is Sell
        pos_type = "BUY" if pos.get("type") == 0 else "SELL"
        type_style = "bold green" if pos_type == "BUY" else "bold red"
        profit = pos.get("profit", 0)
        profit_style = "bold green" if profit >= 0 else "bold red"
        
        table.add_row(
            str(pos.get("ticket")),
            pos.get("symbol"),
            pos_type,
            f"{pos.get('volume'):.2f}",
            f"{pos.get('price_open'):.5f}",
            f"{pos.get('price_current'):.5f}",
            f"${profit:,.2f}",
            style=profit_style if profit != 0 else ""
        )
        
    console.print(table)

async def handle_prices(session, symbols):
    if not symbols:
        symbols = list(METAL_TICKERS.values())
        
    table = Table(title="Live Metals Prices", show_header=True, header_style="bold green")
    table.add_column("Symbol", style="cyan")
    table.add_column("Bid Price", style="green")
    table.add_column("Ask Price", style="green")
    table.add_column("Spread (pts)", style="yellow")
    table.add_column("Last Updated", style="dim")
    
    for sym in symbols:
        # Resolve mapped metals (e.g. Gold -> XAUUSD)
        resolved_sym = METAL_TICKERS.get(sym.upper(), sym.upper())
        
        # Select symbol
        await session.call_tool("symbol_select", {"symbol": resolved_sym, "visible": True})
        
        # Get price tick
        res = await session.call_tool("get_symbol_info_tick", {"symbol": resolved_sym})
        tick = parse_tool_result(res)
        
        if tick and isinstance(tick, dict):
            # Parse timestamp
            tick_time = datetime.fromtimestamp(tick.get("time"))
            table.add_row(
                resolved_sym,
                f"{tick.get('bid'):.3f}",
                f"{tick.get('ask'):.3f}",
                str(tick.get('spread')),
                tick_time.strftime("%H:%M:%S")
            )
        else:
            table.add_row(resolved_sym, "N/A", "N/A", "N/A", "Error")
            
    console.print(table)

async def handle_trade(session, args):
    symbol = METAL_TICKERS.get(args.symbol.upper(), args.symbol.upper())
    action_type = args.action.upper()
    volume = args.volume
    
    # 1. Select the symbol
    await session.call_tool("symbol_select", {"symbol": symbol, "visible": True})
    
    # 2. Get current price
    tick_res = await session.call_tool("get_symbol_info_tick", {"symbol": symbol})
    tick = parse_tool_result(tick_res)
    if not tick:
        console.print(f"[red]Error: Could not retrieve price tick for {symbol}.[/red]")
        return
        
    price = tick.get("ask") if action_type == "BUY" else tick.get("bid")
    type_code = 0 if action_type == "BUY" else 1 # 0=Buy, 1=Sell
    
    order_req = {
        "action": 1, # TRADE_ACTION_DEAL (Execute immediately)
        "symbol": symbol,
        "volume": float(volume),
        "type": type_code,
        "price": float(price),
        "comment": args.comment or "MetalDetectors AI Signal"
    }
    
    if args.sl:
        order_req["sl"] = float(args.sl)
    if args.tp:
        order_req["tp"] = float(args.tp)
        
    console.print(f"Placing [bold cyan]{action_type}[/bold cyan] order for {volume} lots of {symbol} at {price}...")
    
    # Send order
    try:
        res = await session.call_tool("order_send", {"request": order_req})
        result = parse_tool_result(res)
        if result:
            console.print(f"[green]✓ Trade executed successfully![/green]")
            console.print(f"  - Order Ticket: [yellow]{result.get('order')}[/yellow]")
            console.print(f"  - Deal Ticket: [yellow]{result.get('deal')}[/yellow]")
            console.print(f"  - Volume: {result.get('volume')} lots")
            console.print(f"  - Executed Price: {result.get('price')}")
            console.print(f"  - Comment: {order_req['comment']}")
    except Exception as e:
        console.print(f"[red]Failed to execute trade: {e}[/red]")

async def handle_close(session, ticket):
    # Get active positions to find the details
    res_pos = await session.call_tool("positions_get", {})
    positions = parse_tool_result(res_pos)
    
    target_pos = None
    if positions:
        for pos in positions:
            if pos.get("ticket") == ticket:
                target_pos = pos
                break
                
    if not target_pos:
        # Fallback to direct get by ticket if tool available
        try:
            res_pos_by_t = await session.call_tool("positions_get_by_ticket", {"ticket": ticket})
            target_pos = parse_tool_result(res_pos_by_t)
        except Exception:
            pass
            
    if not target_pos:
        console.print(f"[red]Error: Active position with ticket {ticket} not found.[/red]")
        return
        
    symbol = target_pos.get("symbol")
    volume = target_pos.get("volume")
    pos_type = target_pos.get("type") # 0 = Buy, 1 = Sell
    
    # Opposite order type
    close_type = 1 if pos_type == 0 else 0
    
    # Get current price
    tick_res = await session.call_tool("get_symbol_info_tick", {"symbol": symbol})
    tick = parse_tool_result(tick_res)
    price = tick.get("bid") if close_type == 1 else tick.get("ask")
    
    order_req = {
        "action": 1, # TRADE_ACTION_DEAL
        "symbol": symbol,
        "volume": float(volume),
        "type": close_type,
        "price": float(price),
        "position": int(ticket), # Pass position ticket to close it out
        "comment": "Close Position via CLI"
    }
    
    console.print(f"Closing position #{ticket} ({symbol}) of {volume} lots at {price}...")
    
    try:
        res = await session.call_tool("order_send", {"request": order_req})
        result = parse_tool_result(res)
        if result:
            console.print(f"[green]✓ Position #{ticket} closed successfully![/green]")
            console.print(f"  - Close Ticket: {result.get('deal')}")
            console.print(f"  - Executed Price: {result.get('price')}")
    except Exception as e:
        console.print(f"[red]Failed to close position: {e}[/red]")

async def handle_history(session, days):
    # Query history from date
    from_date = datetime.now() - timedelta(days=days)
    # Format to ISO-8601 string or datetime object depending on FastMCP
    # Standard format: datetime object serialized to ISO format by the SDK
    res = await session.call_tool("history_deals_get", {
        "from_date": from_date.isoformat()
    })
    deals = parse_tool_result(res)
    
    if not deals:
        console.print(f"[yellow]No historical deals found for the last {days} days.[/yellow]")
        return
        
    table = Table(title=f"Trade History (Last {days} Days)", show_header=True, header_style="bold yellow")
    table.add_column("Deal Ticket", style="dim")
    table.add_column("Symbol", style="cyan")
    table.add_column("Action", style="bold")
    table.add_column("Volume", style="green")
    table.add_column("Price", style="yellow")
    table.add_column("Profit/Loss", style="bold")
    table.add_column("Time (UTC)", style="dim")
    
    total_pl = 0.0
    for deal in deals:
        # entry: 0=Entry In, 1=Entry Out (Close), 2=InOut (Reverse)
        entry_type = deal.get("entry")
        deal_type = "BUY" if deal.get("type") == 0 else "SELL"
        action_desc = f"{deal_type} ({'IN' if entry_type == 0 else 'OUT' if entry_type == 1 else 'REV'})"
        
        profit = deal.get("profit", 0)
        total_pl += profit
        profit_style = "green" if profit > 0 else "red" if profit < 0 else ""
        
        # Formatting timestamp
        deal_time_str = deal.get("time")
        
        table.add_row(
            str(deal.get("ticket")),
            deal.get("symbol"),
            action_desc,
            f"{deal.get('volume'):.2f}",
            f"{deal.get('price'):.5f}",
            f"${profit:,.2f}" if profit != 0 else "$0.00",
            deal_time_str,
            style=profit_style if profit != 0 else ""
        )
        
    console.print(table)
    console.print(f"\n[bold]Total Net Profit/Loss: [style green]${total_pl:,.2f}[/style green][/bold]" if total_pl >= 0 
                  else f"\n[bold]Total Net Profit/Loss: [style red]${total_pl:,.2f}[/style red][/bold]")

# --- Main Entry Point ---

def main():
    parser = argparse.ArgumentParser(
        description="CLI Integration for calling MT5 MCP tools with MetalDetectors",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python call_mcp_tools.py account
  python call_mcp_tools.py positions
  python call_mcp_tools.py prices
  python call_mcp_tools.py prices GOLD SILVER
  python call_mcp_tools.py trade --symbol GOLD --action buy --volume 0.1 --sl 1900.0 --tp 2100.0
  python call_mcp_tools.py close --ticket 5678912
  python call_mcp_tools.py history --days 14
"""
    )
    
    parser.add_argument("--url", default=DEFAULT_SERVER_URL, help=f"MCP SSE HTTP server URL (default: {DEFAULT_SERVER_URL})")
    
    subparsers = parser.add_subparsers(dest="command", required=True, help="Command to run")
    
    # Account command
    subparsers.add_parser("account", help="Retrieve active trading account info")
    
    # Positions command
    subparsers.add_parser("positions", help="Retrieve active open positions")
    
    # Prices command
    prices_parser = subparsers.add_parser("prices", help="Retrieve current prices of metals")
    prices_parser.add_argument("symbols", nargs="*", help="Optional specific symbols (e.g. GOLD SILVER)")
    
    # Trade command
    trade_parser = subparsers.add_parser("trade", help="Place a market order (BUY/SELL)")
    trade_parser.add_argument("--symbol", "-s", required=True, help="Symbol name (e.g. GOLD, XAUUSD, SILVER)")
    trade_parser.add_argument("--action", "-a", required=True, choices=["buy", "sell"], help="Order action type")
    trade_parser.add_argument("--volume", "-v", type=float, default=0.01, help="Lots size (default: 0.01)")
    trade_parser.add_argument("--sl", type=float, help="Optional stop loss price")
    trade_parser.add_argument("--tp", type=float, help="Optional take profit price")
    trade_parser.add_argument("--comment", "-c", help="Optional comment for the trade")
    
    # Close command
    close_parser = subparsers.add_parser("close", help="Close a position by ticket number")
    close_parser.add_argument("--ticket", "-t", type=int, required=True, help="Active position ticket number")
    
    # History command
    history_parser = subparsers.add_parser("history", help="Retrieve recent trading history")
    history_parser.add_argument("--days", "-d", type=int, default=7, help="Number of days of history to check (default: 7)")
    
    args = parser.parse_args()
    
    # Map command to handler
    if args.command == "account":
        asyncio.run(execute_mcp_command(args.url, handle_account))
    elif args.command == "positions":
        asyncio.run(execute_mcp_command(args.url, handle_positions))
    elif args.command == "prices":
        asyncio.run(execute_mcp_command(args.url, lambda s: handle_prices(s, args.symbols)))
    elif args.command == "trade":
        asyncio.run(execute_mcp_command(args.url, lambda s: handle_trade(s, args)))
    elif args.command == "close":
        asyncio.run(execute_mcp_command(args.url, lambda s: handle_close(s, args.ticket)))
    elif args.command == "history":
        asyncio.run(execute_mcp_command(args.url, lambda s: handle_history(s, args.days)))

if __name__ == "__main__":
    main()