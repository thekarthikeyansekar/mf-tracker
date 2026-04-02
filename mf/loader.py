import pandas as pd
from utils.helpers import clean_num, parse_date

def load_mf_data(uploaded_file):
    df = pd.read_csv(uploaded_file, skip_blank_lines=True)
    df.columns = [c.strip().replace("\n", " ") for c in df.columns]

    col_map = {}
    for c in df.columns:
        cl = c.lower()
        if "vendor" in cl:                           col_map["vendor"] = c
        elif "active" in cl:                         col_map["active"] = c
        elif "n identifier" in cl:                   col_map["n_id"] = c
        elif "invested amount" in cl:                col_map["invested"] = c
        elif "current amount" in cl:                 col_map["current"] = c
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
    df2["f_id"]     = df.get(col_map.get("f_id", ""), "")
    df2["folio"]    = df.get(col_map.get("folio", ""), "")
    df2["invested"] = df.get(col_map.get("invested", ""), 0).apply(clean_num)
    df2["current"]  = df.get(col_map.get("current", ""), 0).apply(clean_num)
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
    return df2.reset_index(drop=True)