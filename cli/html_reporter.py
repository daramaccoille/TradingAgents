import json
import datetime
from pathlib import Path
import yfinance as yf
from markdown_it import MarkdownIt

# Mapping of ticker variations to their uniform Metal name
TICKER_TO_METAL_NAME = {
    "GC=F": "Gold",
    "XAUUSD": "Gold",
    "XAU": "Gold",
    "XAUUSD=X": "Gold",
    "XAU-USD": "Gold",
    "SI=F": "Silver",
    "XAGUSD": "Silver",
    "XAG": "Silver",
    "XAGUSD=X": "Silver",
    "XAG-USD": "Silver",
    "HG=F": "Copper",
    "COPPER": "Copper",
    "PL=F": "Platinum",
    "XPTUSD": "Platinum",
    "XPT": "Platinum",
    "XPTUSD=X": "Platinum",
    "PA=F": "Palladium",
    "XPDUSD": "Palladium",
    "XPD": "Palladium",
    "XPDUSD=X": "Palladium"
}

def get_chart_data(ticker: str) -> str:
    """Fetch 90 days of historical daily OHLC+V data for ApexCharts."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        df = ticker_obj.history(period="90d")
        if df.empty:
            return "[]"
        
        data_list = []
        for index, row in df.iterrows():
            data_list.append({
                "time": index.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"])
            })
        return json.dumps(data_list)
    except Exception as e:
        print(f"Error fetching chart data for {ticker}: {e}")
        return "[]"

def generate_html_report(ticker: str, state: dict, save_path: Path, analysis_date: str):
    """Generate a highly-styled premium HTML report for subscribers matching MetalDetector design guidelines."""
    md = MarkdownIt()
    
    # Extract metal name
    metal_name = TICKER_TO_METAL_NAME.get(ticker.upper(), ticker.upper())
    
    # Fetch historical technical data
    chart_data_json = get_chart_data(ticker)
    
    # Process markdown contents to HTML
    def to_html(content_key, default=""):
        val = state.get(content_key)
        if not val:
            return default
        return md.render(val)
        
    market_html = to_html("market_report", "<p class='no-data'>No Market Analyst report available.</p>")
    sentiment_html = to_html("sentiment_report", "<p class='no-data'>No Social Sentiment report available.</p>")
    news_html = to_html("news_report", "<p class='no-data'>No News Analyst report available.</p>")
    fundamentals_html = to_html("fundamentals_report", "<p class='no-data'>No Fundamentals Analyst report available.</p>")
    
    trader_plan_html = to_html("trader_investment_plan", "<p class='no-data'>No Trader Plan available.</p>")
    investment_plan_html = to_html("investment_plan", "<p class='no-data'>No Research Team plan available.</p>")
    final_decision_html = to_html("final_trade_decision", "<p class='no-data'>No Portfolio Manager final decision available.</p>")
    
    # Retrieve debate histories
    debate = state.get("investment_debate_state", {})
    bull_html = md.render(debate.get("bull_history", "")) if debate.get("bull_history") else ""
    bear_html = md.render(debate.get("bear_history", "")) if debate.get("bear_history") else ""
    research_manager_html = md.render(debate.get("judge_decision", "")) if debate.get("judge_decision") else ""
    
    risk = state.get("risk_debate_state", {})
    aggressive_html = md.render(risk.get("aggressive_history", "")) if risk.get("aggressive_history") else ""
    conservative_html = md.render(risk.get("conservative_history", "")) if risk.get("conservative_history") else ""
    neutral_html = md.render(risk.get("neutral_history", "")) if risk.get("neutral_history") else ""
    portfolio_manager_debate_html = md.render(risk.get("judge_decision", "")) if risk.get("judge_decision") else ""
    
    # Try to parse rating from final decision
    rating = "HOLD"
    rating_color = "var(--risk-mod)"
    rating_lower = final_decision_html.lower()
    if "buy" in rating_lower or "overweight" in rating_lower:
        rating = "BUY / OVERWEIGHT"
        rating_color = "var(--risk-low)"
    elif "sell" in rating_lower or "underweight" in rating_lower:
        rating = "SELL / UNDERWEIGHT"
        rating_color = "var(--risk-high)"
        
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MetalDetector Premium Report: {metal_name} ({ticker})</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
    <style>
        :root {{
            --background: #050505;
            --foreground: #f9fafb;
            --glass-bg: rgba(20, 20, 20, 0.6);
            --glass-border: rgba(255, 215, 0, 0.1);
            --glass-highlight: rgba(255, 215, 0, 0.3);
            --glass-blur: 12px;
            --primary: #FFD700; /* Gold */
            --secondary: #C0C0C0; /* Silver */
            --accent: #B87333; /* Copper */
            --risk-high: #EF4444;
            --risk-mod: #F59E0B;
            --risk-low: #10B981;
            --font-main: 'Inter', Arial, system-ui, sans-serif;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background: var(--background);
            color: var(--foreground);
            font-family: var(--font-main);
            min-height: 100vh;
            overflow-x: hidden;
            line-height: 1.6;
        }}

        /* Subtle background ambience */
        .bg-ambience {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 600px;
            background: linear-gradient(to bottom, rgba(113, 63, 18, 0.08), transparent);
            pointer-events: none;
            z-index: 0;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2.5rem 1.5rem;
            position: relative;
            z-index: 1;
        }}

        /* Header design */
        header {{
            margin-bottom: 3rem;
            text-align: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            padding-bottom: 2rem;
        }}

        .logo-text {{
            font-size: 0.875rem;
            color: var(--primary);
            font-weight: 600;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
            display: inline-block;
        }}

        .report-title {{
            font-size: 2.5rem;
            font-weight: 700;
            line-height: 1.1;
            margin-bottom: 1rem;
        }}

        .title-gradient-text {{
            background: linear-gradient(to right, #fde047, #ca8a04);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }}

        .meta-grid {{
            display: flex;
            justify-content: center;
            gap: 2rem;
            font-size: 0.875rem;
            color: #9ca3af;
            margin-top: 1rem;
        }}

        .meta-item strong {{
            color: var(--foreground);
        }}

        /* Rating Badge */
        .rating-badge-container {{
            display: inline-flex;
            align-items: center;
            gap: 0.75rem;
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--glass-border);
            padding: 0.5rem 1.25rem;
            border-radius: 9999px;
            font-size: 0.875rem;
            margin-top: 1rem;
        }}

        .rating-indicator {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background-color: {rating_color};
            box-shadow: 0 0 10px {rating_color};
        }}

        .rating-val {{
            font-weight: 700;
            color: {rating_color};
        }}

        /* Glass Cards */
        .glass-panel {{
            background: var(--glass-bg);
            backdrop-filter: blur(var(--glass-blur));
            -webkit-backdrop-filter: blur(var(--glass-blur));
            border: 1px solid var(--glass-border);
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
            border-radius: 20px;
            padding: 2rem;
            margin-bottom: 2rem;
            transition: all 0.3s ease;
        }}

        .glass-panel:hover {{
            border-color: var(--glass-highlight);
            box-shadow: 0 0 20px rgba(255, 215, 0, 0.05);
        }}

        /* Tabs Interface */
        .tabs-header {{
            display: flex;
            gap: 0.5rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            margin-bottom: 2rem;
            overflow-x: auto;
            padding-bottom: 0.5rem;
        }}

        .tab-btn {{
            background: transparent;
            border: none;
            color: #9ca3af;
            padding: 0.75rem 1.5rem;
            font-size: 0.95rem;
            font-weight: 500;
            cursor: pointer;
            border-radius: 8px;
            white-space: nowrap;
            transition: all 0.2s;
        }}

        .tab-btn:hover {{
            color: var(--foreground);
            background: rgba(255, 255, 255, 0.03);
        }}

        .tab-btn.active {{
            color: #050505;
            background: linear-gradient(to right, #fde047, #ca8a04);
            font-weight: 600;
            box-shadow: 0 0 15px rgba(234, 179, 8, 0.3);
        }}

        .tab-content {{
            display: none;
        }}

        .tab-content.active {{
            display: block;
            animation: fadeIn 0.4s ease;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(5px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* Sub-layout for market and decision views */
        .grid-two-col {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 2rem;
        }}

        @media (min-width: 900px) {{
            .grid-two-col {{
                grid-template-columns: 3fr 2fr;
            }}
        }}

        .report-section-title {{
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
            color: var(--primary);
            border-bottom: 1px solid rgba(255, 215, 0, 0.15);
            padding-bottom: 0.5rem;
        }}

        /* Typography within reports */
        .report-body h1, .report-body h2, .report-body h3 {{
            color: var(--primary);
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
            font-weight: 600;
        }}

        .report-body h1 {{ font-size: 1.4rem; }}
        .report-body h2 {{ font-size: 1.25rem; }}
        .report-body h3 {{ font-size: 1.1rem; }}

        .report-body p {{
            margin-bottom: 1.25rem;
            color: #d4d4d8;
            font-size: 0.975rem;
            line-height: 1.7;
        }}

        .report-body ul, .report-body ol {{
            margin-left: 1.5rem;
            margin-bottom: 1.25rem;
            color: #d4d4d8;
            font-size: 0.95rem;
        }}

        .report-body li {{
            margin-bottom: 0.5rem;
        }}

        .report-body table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
            font-size: 0.9rem;
        }}

        .report-body th, .report-body td {{
            padding: 0.75rem;
            border: 1px solid rgba(255, 255, 255, 0.08);
            text-align: left;
        }}

        .report-body th {{
            background: rgba(255, 255, 255, 0.03);
            font-weight: 600;
            color: var(--primary);
        }}

        .report-body tr:nth-child(even) {{
            background: rgba(255, 255, 255, 0.01);
        }}

        .report-body strong {{
            color: var(--foreground);
            font-weight: 600;
        }}

        .no-data {{
            color: #71717a;
            font-style: italic;
            padding: 1rem 0;
        }}

        /* Analyst Grid styling */
        .analyst-grid {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 1.5rem;
        }}

        @media (min-width: 768px) {{
            .analyst-grid {{
                grid-template-columns: 1fr 1fr;
            }}
        }}

        .analyst-card {{
            background: rgba(10, 10, 10, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 1.5rem;
        }}

        .analyst-card-title {{
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--primary);
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            padding-bottom: 0.5rem;
        }}

        /* Chart styling */
        .chart-container-card {{
            padding: 2rem;
        }}

        .chart-wrapper {{
            margin-bottom: 2rem;
            background: rgba(10, 10, 10, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            padding: 1rem;
        }}

        .chart-title {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: var(--foreground);
        }}

        /* Footer styling */
        footer {{
            margin-top: 5rem;
            text-align: center;
            padding-top: 2rem;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            color: #52525b;
            font-size: 0.85rem;
        }}

        .footer-logo {{
            color: var(--primary);
            font-weight: 700;
            margin-bottom: 0.5rem;
            letter-spacing: 0.1em;
        }}
    </style>
</head>
<body>
    <div class="bg-ambience"></div>
    <div class="container">
        
        <header>
            <span class="logo-text">MetalDetector subscriber feed</span>
            <h1 class="report-title">
                <span class="title-gradient-text">{metal_name} ({ticker})</span> Analysis Report
            </h1>
            <div class="meta-grid">
                <span class="meta-item">Date: <strong>{analysis_date}</strong></span>
                <span class="meta-item">Coverage: <strong>Premium</strong></span>
            </div>
            <div class="rating-badge-container">
                <div class="rating-indicator"></div>
                <span>Strategic Action: <span class="rating-val">{rating}</span></span>
            </div>
        </header>

        <!-- Tabs Headers -->
        <div class="tabs-header">
            <button class="tab-btn active" onclick="openTab(event, 'decision-tab')">Portfolio Decision</button>
            <button class="tab-btn" onclick="openTab(event, 'market-tab')">Market Analyst Feed</button>
            <button class="tab-btn" onclick="openTab(event, 'chart-tab')">Technical Chart</button>
            <button class="tab-btn" onclick="openTab(event, 'debates-tab')">Research & Risk Debates</button>
        </div>

        <!-- Portfolio Decision Tab -->
        <div id="decision-tab" class="tab-content active">
            <div class="grid-two-col">
                <div class="glass-panel">
                    <h2 class="report-section-title">Portfolio Manager Final Decision</h2>
                    <div class="report-body">{final_decision_html}</div>
                </div>
                <div>
                    <div class="glass-panel" style="margin-bottom: 1.5rem;">
                        <h2 class="report-section-title">Trading Team Plan</h2>
                        <div class="report-body">{trader_plan_html}</div>
                    </div>
                    <div class="glass-panel">
                        <h2 class="report-section-title">Research Summary</h2>
                        <div class="report-body">{investment_plan_html}</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Market Analyst Feed Tab -->
        <div id="market-tab" class="tab-content">
            <div class="analyst-grid">
                <div class="glass-panel analyst-card">
                    <h3 class="analyst-card-title">📈 Market Analysis</h3>
                    <div class="report-body">{market_html}</div>
                </div>
                <div class="glass-panel analyst-card">
                    <h3 class="analyst-card-title">📊 Fundamentals</h3>
                    <div class="report-body">{fundamentals_html}</div>
                </div>
                <div class="glass-panel analyst-card">
                    <h3 class="analyst-card-title">🗣️ Social Sentiment</h3>
                    <div class="report-body">{sentiment_html}</div>
                </div>
                <div class="glass-panel analyst-card">
                    <h3 class="analyst-card-title">📰 News Analysis</h3>
                    <div class="report-body">{news_html}</div>
                </div>
            </div>
        </div>

        <!-- Technical Chart Tab -->
        <div id="chart-tab" class="tab-content">
            <div class="glass-panel chart-container-card">
                <h2 class="report-section-title">Interactive Technical Data</h2>
                <div class="chart-wrapper">
                    <div class="chart-title">Candlestick Price Action (Last 90 Days)</div>
                    <div id="price-chart-container"></div>
                </div>
                <div class="chart-wrapper">
                    <div class="chart-title">Trading Volume</div>
                    <div id="volume-chart-container"></div>
                </div>
            </div>
        </div>

        <!-- Research & Risk Debates Tab -->
        <div id="debates-tab" class="tab-content">
            <div class="grid-two-col">
                <div class="glass-panel">
                    <h2 class="report-section-title">Research Manager Debate</h2>
                    <div class="report-body">
                        {research_manager_html}
                        {bull_html and f"<details><summary style='color:var(--primary); cursor:pointer; margin-top:1rem;'>View Bull Researcher History</summary><div style='margin-top:1rem;'>{bull_html}</div></details>"}
                        {bear_html and f"<details><summary style='color:var(--primary); cursor:pointer; margin-top:1rem;'>View Bear Researcher History</summary><div style='margin-top:1rem;'>{bear_html}</div></details>"}
                    </div>
                </div>
                <div class="glass-panel">
                    <h2 class="report-section-title">Risk Management Debate</h2>
                    <div class="report-body">
                        {portfolio_manager_debate_html}
                        {aggressive_html and f"<details><summary style='color:var(--primary); cursor:pointer; margin-top:1rem;'>View Aggressive Analyst History</summary><div style='margin-top:1rem;'>{aggressive_html}</div></details>"}
                        {conservative_html and f"<details><summary style='color:var(--primary); cursor:pointer; margin-top:1rem;'>View Conservative Analyst History</summary><div style='margin-top:1rem;'>{conservative_html}</div></details>"}
                        {neutral_html and f"<details><summary style='color:var(--primary); cursor:pointer; margin-top:1rem;'>View Neutral Analyst History</summary><div style='margin-top:1rem;'>{neutral_html}</div></details>"}
                    </div>
                </div>
            </div>
        </div>

        <footer>
            <div class="footer-logo">METAL DETECTOR</div>
            <div>This report is generated daily for premium subscribers of Tauric Research.</div>
            <div style="margin-top:0.5rem; font-size:0.75rem;">© {datetime.datetime.now().year} Tauric Research. All rights reserved.</div>
        </footer>

    </div>

    <script>
        // Tab switching logic
        function openTab(evt, tabId) {{
            const tabContents = document.querySelectorAll(".tab-content");
            tabContents.forEach(content => {{
                content.classList.remove("active");
            }});

            const tabButtons = document.querySelectorAll(".tab-btn");
            tabButtons.forEach(btn => {{
                btn.classList.remove("active");
            }});

            document.getElementById(tabId).classList.add("active");
            evt.currentTarget.classList.add("active");
        }}

        // Technical Chart Data Rendering
        const rawData = {chart_data_json};

        if (rawData && rawData.length > 0) {{
            const prices = rawData.map(d => ({{
                x: new Date(d.time),
                y: [d.open, d.high, d.low, d.close]
            }}));
            
            const volumes = rawData.map(d => ({{
                x: new Date(d.time),
                y: d.volume
            }}));

            // Price Chart options (Candlestick)
            const priceOptions = {{
                series: [{{
                    name: 'OHLC Price',
                    data: prices
                }}],
                chart: {{
                    type: 'candlestick',
                    height: 380,
                    id: 'price-chart',
                    background: 'transparent',
                    foreColor: '#9ca3af',
                    toolbar: {{ show: true }}
                }},
                theme: {{
                    mode: 'dark'
                }},
                grid: {{
                    borderColor: 'rgba(63, 63, 70, 0.3)'
                }},
                xaxis: {{
                    type: 'datetime'
                }},
                yaxis: {{
                    tooltip: {{
                        enabled: true
                    }}
                }},
                plotOptions: {{
                    candlestick: {{
                        colors: {{
                            upward: '#10B981',   // Green for up
                            downward: '#EF4444'  // Red for down
                        }}
                    }}
                }}
            }};

            const priceChart = new ApexCharts(document.querySelector("#price-chart-container"), priceOptions);
            priceChart.render();
            
            // Volume Chart options (Bar)
            const volumeOptions = {{
                series: [{{
                    name: 'Volume',
                    data: volumes
                }}],
                chart: {{
                    type: 'bar',
                    height: 150,
                    background: 'transparent',
                    foreColor: '#9ca3af',
                    toolbar: {{ show: false }}
                }},
                theme: {{
                    mode: 'dark'
                }},
                grid: {{
                    borderColor: 'rgba(63, 63, 70, 0.3)'
                }},
                xaxis: {{
                    type: 'datetime'
                }},
                colors: ['#FFD700'] // Gold
            }};
            
            const volumeChart = new ApexCharts(document.querySelector("#volume-chart-container"), volumeOptions);
            volumeChart.render();
        }} else {{
            document.querySelector("#chart-tab").innerHTML = "<div class='glass-panel'><h2 class='report-section-title'>Technical Chart</h2><div class='no-data'>No historical technical data available for charting.</div></div>";
        }}
    </script>
</body>
</html>"""

    # Write HTML file
    report_file = save_path / "complete_report.html"
    report_file.write_text(html_template, encoding="utf-8")
    return report_file
