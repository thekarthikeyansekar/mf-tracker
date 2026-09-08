import requests
import pandas as pd
from io import StringIO
import os
import shutil
from datetime import datetime


def get_today_mf_prices():
    """
    Get Today MF Prices to data folder - mf_prices.csv
    Archieves Old Pulls to data/archive folder
    """

    nav_url = "https://www.amfiindia.com/spages/NAVAll.txt"

    response = requests.get(nav_url)

    all_lines = response.text.splitlines()
    all_lines = [x for x in all_lines if ';' in x]

    df = pd.read_csv(StringIO("\n".join(all_lines)), delimiter=';')
    df['Date'] = pd.to_datetime(df['Date'], format='%d-%b-%Y')

    if os.path.exists('data/mf_prices.csv'):
        timestamp_string = str(datetime.today()).replace("-", "_").replace(" ", "_").replace(":", "_").split(".")[0]
        shutil.move('data/mf_prices.csv', 'data/archive/mf_prices_' + timestamp_string + ".csv")  

    df.to_csv(r'C:\D Drive\Workspace Finance\mf-tracker\data/mf_prices.csv', index=False)


if __name__ =="__main__":
    get_today_mf_prices()