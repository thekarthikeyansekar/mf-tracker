import requests
import pandas as pd
import matplotlib.pyplot as plt


def get_mf_history(scheme_code):
    """
    Download complete historical NAV data for an Indian mutual fund
    using its AMFI scheme code.
    """

    url = f"https://api.mfapi.in/mf/{scheme_code}"

    response = requests.get(url)
    response.raise_for_status()

    data = response.json()

    df = pd.DataFrame(data["data"])

    df["date"] = pd.to_datetime(
        df["date"],
        format="%d-%m-%Y"
    )

    df["nav"] = pd.to_numeric(df["nav"])

    df = df.rename(columns={
        "date": "Date",
        "nav": "NAV"
    })

    df = df.sort_values("Date")

    return df


if __name__ == "__main__":
    # Example
    dsp_nifty50 = get_mf_history(146376)

    print(dsp_nifty50.head())
    print(dsp_nifty50.tail())