import os
import requests
import json
from pathlib import Path
from dotenv import load_dotenv
import time

load_dotenv()

API_URL = "http://localhost:3000/api/reports/ingest"
API_KEY = os.environ.get("INGEST_API_KEY", "dev-secret-key")

def push_all_reports():
    reports_payload = []
    
    # Check both reports and reports1 directories
    for base_dir_name in ["reports", "reports1"]:
        base_dir = Path(base_dir_name)
        if not base_dir.exists():
            continue

        directories = [d for d in base_dir.iterdir() if d.is_dir()]
        
        for batch_dir in directories:
            batch_id = batch_dir.name
            
            # Parse Metal and Date from batch_id (e.g. GOLD_20260503_210554)
            parts = batch_id.split('_')
            if len(parts) >= 2:
                metal = parts[0]
                raw_date = parts[1]
                if len(raw_date) >= 8:
                    date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
                else:
                    date = raw_date
            else:
                metal = "Unknown"
                date = "Unknown"

            for root, _, files in os.walk(batch_dir):
                stage = Path(root).name
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
        print("No markdown files found to push.")
        return

    print(f"Found {len(reports_payload)} total reports across all directories. Pushing to Neon DB...")

    try:
        response = requests.post(
            API_URL,
            headers={"Content-Type": "application/json", "x-api-key": API_KEY},
            json={"reports": reports_payload}
        )
        
        if response.status_code == 200:
            print("Successfully pushed all reports to Neon DB!")
            print(response.json())
        else:
            print(f"Failed to push: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error connecting to API: {e}")

if __name__ == "__main__":
    push_all_reports()
