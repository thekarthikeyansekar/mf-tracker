import requests
import pandas as pd
from io import StringIO
import json
from datetime import date, datetime
from pathlib import Path


def get_today_mf_prices(path="data/mf_today_prices.csv", marker_path="data/date.json"):
    """
    Get today's MF prices, reusing the existing daily pull when available.
    """
    output_path = Path(path)
    marker_file = Path(marker_path)
    today = date.today().isoformat()

    if output_path.exists() and marker_file.exists():
        try:
            with marker_file.open(encoding="utf-8") as file:
                marker = json.load(file)
            if marker.get("last_run") == today:
                return output_path
        except (json.JSONDecodeError, OSError):
            pass

    nav_url = "https://www.amfiindia.com/spages/NAVAll.txt"

    response = requests.get(nav_url, timeout=30)
    response.raise_for_status()

    all_lines = response.text.splitlines()
    all_lines = [x for x in all_lines if ';' in x]

    df = pd.read_csv(StringIO("\n".join(all_lines)), delimiter=';')
    df['Date'] = pd.to_datetime(df['Date'], format='%d-%b-%Y')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    marker_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    with marker_file.open("w", encoding="utf-8") as file:
        json.dump({"last_run": today, "last_run_at": datetime.now().isoformat()}, file, indent=2)

    return output_path


if __name__ =="__main__":
    path = r'C:\D Drive\Workspace Finance\mf-tracker\data/mf_today_prices.csv'
    get_today_mf_prices(path)