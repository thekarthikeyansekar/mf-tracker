import pandas as pd

def aggregate_by_fund(df, vendor, folio_key):
    sub = df[(df["vendor"] == vendor) & (df["f_id"] == folio_key)].copy()
    if sub.empty:
        return pd.DataFrame()

    grp = sub.groupby("n_id").agg(
        invested=("invested", "sum"),
        current=("current", "sum"),
        pnl=("pnl", "sum"),
        xirr=("xirr", "mean"),
    ).reset_index()

    grp["pnl_pct"] = (grp["pnl"] / grp["invested"].replace(0,1)) * 100
    return grp