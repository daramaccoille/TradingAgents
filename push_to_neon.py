import os
import requests
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

# Config
API_URL = os.environ.get("INGEST_API_URL", "http://localhost:3000/api/reports/ingest")
API_KEY = os.environ.get("INGEST_API_KEY", "dev-secret-key")
REPORTS_DIR = Path("reports")

def push_reports(target_date: Optional[str] = None):
    if not REPORTS_DIR.exists():
        print("No reports directory found.")
        return

    # Find matching batch directories
    all_directories = [d for d in REPORTS_DIR.iterdir() if d.is_dir()]
    if not all_directories:
        print("No report directories found.")
        return

    selected_batch_dirs = []
    if target_date:
        # Normalize date to YYYYMMDD for matching
        normalized_date = target_date.replace("-", "")
        # Look for folders containing the date pattern, e.g. "GOLD_20260604_130723"
        date_pattern = f"_{normalized_date}_"
        for d in all_directories:
            if date_pattern in d.name:
                selected_batch_dirs.append(d)
        if not selected_batch_dirs:
            print(f"No report batches found matching date: {target_date}")
            return
        print(f"Found {len(selected_batch_dirs)} report batches matching date: {target_date}")
    else:
        # Fallback to the single most recently created report batch directory
        latest_batch_dir = max(all_directories, key=os.path.getmtime)
        selected_batch_dirs = [latest_batch_dir]
        print(f"No date specified. Defaulting to latest batch directory: {latest_batch_dir.name}")

    # Load prices from prices.csv mapping (date, metal) -> (price, timestamp)
    prices_map = {}
    prices_csv_path = REPORTS_DIR / "prices.csv"
    if prices_csv_path.exists():
        try:
            import csv
            with open(prices_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None) # Timestamp,Date,Metal,Ticker,Price
                if header:
                    for row in reader:
                        if len(row) >= 5:
                            ts, dt, met, tick, pr = row
                            prices_map[(dt.strip(), met.strip().upper())] = (pr.strip(), ts.strip())
        except Exception as e:
            print(f"Error loading prices.csv: {e}")

    reports_payload = []

    for batch_dir in selected_batch_dirs:
        batch_id = batch_dir.name
        
        # Parse Metal and Date from batch_id (e.g. XAUUSD_20260503_210554)
        parts = batch_id.split('_')
        if len(parts) >= 2:
            metal = parts[0]
            # Format date as YYYY-MM-DD for easier reading
            raw_date = parts[1]
            date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
        else:
            metal = "Unknown"
            date = "Unknown"

        # Look up price and priceTimestamp
        price_val, price_ts = prices_map.get((date, metal.upper()), (None, None))

        # Walk through the directory and collect all markdown files
        for root, _, files in os.walk(batch_dir):
            stage = Path(root).name
            # If the root is the main batch folder itself, it's the complete report
            if stage == batch_id:
                stage = "complete"
                
            for file in files:
                if file.endswith(".md"):
                    file_path = Path(root) / file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    reports_payload.append({
                        "reportBatchId": batch_id,
                        "metal": metal,
                        "date": date,
                        "stage": stage,
                        "agentName": file,
                        "contentMd": content,
                        "price": price_val,
                        "priceTimestamp": price_ts
                    })

    if not reports_payload:
        print("No markdown files found in the selected directories.")
        return

    print(f"Found {len(reports_payload)} reports in total. Pushing to Neon DB...")

    # Send to Next.js API
    try:
        response = requests.post(
            API_URL,
            headers={
                "Content-Type": "application/json",
                "x-api-key": API_KEY
            },
            json={"reports": reports_payload}
        )
        
        if response.status_code == 200:
            print("Successfully pushed to Neon DB!")
            print(response.json())
        else:
            print(f"Failed to push: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error connecting to API: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Push report batches to Neon DB.")
    parser.add_argument("--date", "-d", type=str, default=None, help="Filter batches by date YYYY-MM-DD or YYYYMMDD")
    args = parser.parse_args()
    
    push_reports(args.date)
