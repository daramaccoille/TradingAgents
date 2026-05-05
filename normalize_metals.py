import os
from pathlib import Path

# Mapping of all possible ticker variations to their uniform Metal name
TICKER_TO_METAL = {
    # Gold
    "GC=F": "GOLD",
    "XAUUSD": "GOLD",
    "XAU": "GOLD",
    "XAUUSD=X": "GOLD",
    "XAU-USD": "GOLD",

    # Silver
    "SI=F": "SILVER",
    "XAGUSD": "SILVER",
    "XAG": "SILVER",
    "XAGUSD=X": "SILVER",
    "XAG-USD": "SILVER",

    # Copper
    "HG=F": "COPPER",
    "COPPER": "COPPER",

    # Platinum
    "PL=F": "PLATINUM",
    "XPTUSD": "PLATINUM",
    "XPT": "PLATINUM",
    "XPTUSD=X": "PLATINUM",

    # Palladium
    "PA=F": "PALLADIUM",
    "XPDUSD": "PALLADIUM",
    "XPD": "PALLADIUM",
    "XPDUSD=X": "PALLADIUM"
}

def normalize_directories(base_path: str):
    reports_dir = Path(base_path)
    if not reports_dir.exists():
        print(f"Directory {base_path} not found.")
        return

    renamed_count = 0
    for folder in reports_dir.iterdir():
        if not folder.is_dir():
            continue

        # Expected folder structure: TICKER_YYYYMMDD_HHMMSS
        parts = folder.name.split('_')
        if len(parts) >= 3:
            ticker = parts[0].upper()
            
            # Look up the uniform name
            uniform_metal = TICKER_TO_METAL.get(ticker)
            
            # If we found a match and it's not already named uniformly
            if uniform_metal and ticker != uniform_metal:
                new_folder_name = f"{uniform_metal}_{'_'.join(parts[1:])}"
                new_folder_path = folder.parent / new_folder_name
                
                # Check for collisions
                if new_folder_path.exists():
                    print(f"Skipped {folder.name} -> {new_folder_name} (Destination already exists)")
                    continue
                    
                print(f"Renamed: {folder.name}  ->  {new_folder_name}")
                folder.rename(new_folder_path)
                renamed_count += 1

    print(f"\nFinished! Renamed {renamed_count} folders in {base_path}")

if __name__ == "__main__":
    # Standard reports directory
    reports_path = Path(r"c:\Users\daraw\Downloads\TradingAgents\reports")
    normalize_directories(reports_path)
    
    # Also check reports1 if it exists
    reports1_path = Path(r"c:\Users\daraw\Downloads\TradingAgents\reports1")
    if reports1_path.exists():
        normalize_directories(reports1_path)
