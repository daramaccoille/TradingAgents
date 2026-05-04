import os
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Config
# For local testing, use localhost. In production, change to: https://metaldetectors.online/api/reports/ingest
API_URL = "http://localhost:3000/api/reports/ingest"
API_KEY = os.environ.get("INGEST_API_KEY", "dev-secret-key")
REPORTS_DIR = Path("reports")

def push_latest_report():
    if not REPORTS_DIR.exists():
        print("No reports directory found.")
        return

    # Find the most recently created report batch directory
    directories = [d for d in REPORTS_DIR.iterdir() if d.is_dir()]
    if not directories:
        print("No report directories found.")
        return
        
    latest_batch_dir = max(directories, key=os.path.getmtime)
    batch_id = latest_batch_dir.name
    
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

    reports_payload = []

    # Walk through the directory and collect all markdown files
    for root, _, files in os.walk(latest_batch_dir):
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
                    "contentMd": content
                })

    if not reports_payload:
        print(f"No markdown files found in {latest_batch_dir}")
        return

    print(f"Found {len(reports_payload)} reports in {batch_id}. Pushing to Neon DB...")

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
    push_latest_report()
