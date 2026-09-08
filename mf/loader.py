import pandas as pd
from datetime import date

from utils.helpers import clean_num, parse_date
from utils.finance import xirr
from mf.utils.mf_price_retreiver import get_today_mf_prices


def _recalculate_mf_values(df):
    prices_path = get_today_mf_prices()
    prices = pd.read_csv(prices_path)
    prices["Scheme Code"] = pd.to_numeric(prices["Scheme Code"], errors="coerce")
    prices["Net Asset Value"] = pd.to_numeric(prices["Net Asset Value"], errors="coerce")

    nav_by_scheme = prices.dropna(subset=["Scheme Code", "Net Asset Value"]).drop_duplicates(
        "Scheme Code"
    ).set_index("Scheme Code")["Net Asset Value"]
    df["nav"] = df["scheme_code"].map(nav_by_scheme).fillna(df["nav"])

    units = df["invested"] / df["bought_nav"].replace(0, pd.NA)
    df["current"] = (units * df["nav"]).fillna(0.0)
    df["pnl"] = df["current"] - df["invested"]
    df["pnl_pct"] = (df["pnl"] / df["invested"].replace(0, pd.NA) * 100).fillna(0.0)

    today = pd.Timestamp(date.today())
    for _, group in df.groupby(["vendor", "n_id", "f_id"], dropna=False):
        dated = group[group["date_parsed"].notna()].sort_values("date_parsed")
        if dated.empty:
            continue
        cashflows = [(row.date_parsed, -row.invested) for row in dated.itertuples()]
        cashflows.append((today, float(group["current"].sum())))
        try:
            calculated_xirr = xirr(cashflows) * 100
        except (ArithmeticError, OverflowError, ZeroDivisionError):
            calculated_xirr = 0.0
        df.loc[group.index, "xirr"] = calculated_xirr

    return df

def load_mf_data(uploaded_file):
    df = pd.read_csv(uploaded_file, skip_blank_lines=True)
    if "Bought NAV" in df.columns:
        df = df[~df["Bought NAV"].isna()]
    df = df.replace("#DIV/0!", 0)
    df.columns = [c.strip().replace("\n", " ") for c in df.columns]

    col_map = {}
    for c in df.columns:
        cl = c.lower()
        if "vendor" in cl:                           col_map["vendor"] = c
        elif "active" in cl:                         col_map["active"] = c
        elif "n identifier" in cl:                   col_map["n_id"] = c
        elif "amfi scheme code" in cl:               col_map["scheme_code"] = c
        elif "invested amount" in cl:                col_map["invested"] = c
        elif "current amount" in cl:                 col_map["current"] = c
        elif cl == "bought nav" :                    col_map["bought_nav"] = c
        elif cl == "nav" or "current nav" in cl:     col_map["nav"] = c
        elif "xirr" in cl:                           col_map["xirr"] = c
        elif cl.startswith("profit") and "%" not in cl: col_map["pnl"] = c
        elif "absolute profit" in cl:                col_map["pnl_pct"] = c
        elif "folio no" in cl:                       col_map["folio"] = c
        elif "f identifier" in cl:                   col_map["f_id"] = c
        elif cl == "date":                           col_map["date"] = c

    df2 = pd.DataFrame()
    df2["vendor"]   = df.get(col_map.get("vendor", ""), "")
    df2["active"]   = df.get(col_map.get("active", ""), "Y")
    df2["n_id"]     = df.get(col_map.get("n_id", ""), "")
    scheme_code_values = df.get(
        col_map.get("scheme_code", ""), pd.Series("", index=df.index)
    )
    df2["scheme_code"] = scheme_code_values.apply(clean_num)
    df2["f_id"]     = df.get(col_map.get("f_id", ""), "")
    df2["folio"]    = df.get(col_map.get("folio", ""), "")
    df2["invested"] = df.get(col_map.get("invested", ""), 0).apply(clean_num)
    df2["current"]  = df.get(col_map.get("current", ""), 0).apply(clean_num)
    df2["bought_nav"]= df.get(col_map.get("bought_nav", ""), 0).apply(clean_num)
    df2["nav"]      = df.get(col_map.get("nav", ""), 0).apply(clean_num)
    df2["pnl"]      = df.get(col_map.get("pnl", ""), 0).apply(clean_num)
    df2["pnl_pct"]  = df.get(col_map.get("pnl_pct", ""), 0).apply(clean_num)
    df2["xirr_raw"] = df.get(col_map.get("xirr", ""), "0%")
    df2["date_raw"] = df.get(col_map.get("date", ""), "")

    df2["xirr"] = df2["xirr_raw"].apply(
        lambda v: float(str(v).replace("%","").strip()) if str(v).replace("%","").strip() else 0.0
    )
    df2["date_parsed"] = df2["date_raw"].apply(parse_date)
    df2["vendor"] = df2["vendor"].astype(str).str.strip()
    df2["active"] = df2["active"].astype(str).str.strip()
    df2 = df2[df2["active"].str.upper() == "Y"]
    df2 = df2[df2["vendor"].isin(["Axis", "DSP"])]
    df2 = df2[df2["n_id"].astype(str).str.strip() != ""]
    return _recalculate_mf_values(df2.reset_index(drop=True))