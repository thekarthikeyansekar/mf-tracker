import pandas as pd
from utils.helpers import clean_num, parse_date


def load_nps_data(uploaded_file):
    df = pd.read_csv(uploaded_file, skip_blank_lines=True)
    df.columns = [c.strip() for c in df.columns]

    def find_col(df, *names):
        for n in names:
            if n in df.columns:
                return n
        for c in df.columns:
            for n in names:
                if n.lower() in c.lower():
                    return c
        return None

    year_col  = find_col(df, "Year")
    cat_col   = find_col(df, "Category")
    fund_col  = find_col(df, "Fund Name")
    date_col  = find_col(df, "Date")
    part_col  = find_col(df, "Particulars")
    amt_col   = find_col(df, "Amount")
    nav_col   = find_col(df, "NAV")
    units_col = find_col(df, "Units")

    df2 = pd.DataFrame()
    df2["year"]        = df[year_col].astype(str).str.strip() if year_col else ""
    df2["category"]    = df[cat_col].astype(str).str.strip() if cat_col else ""
    df2["fund_name"]   = df[fund_col].astype(str).str.strip() if fund_col else ""
    df2["particulars"] = df[part_col].astype(str).str.strip() if part_col else ""
    df2["amount"]      = df[amt_col].apply(clean_num) if amt_col else 0.0
    df2["nav"]         = df[nav_col].apply(clean_num) if nav_col else 0.0
    df2["units"]       = df[units_col].apply(clean_num) if units_col else 0.0
    df2["date_parsed"] = df[date_col].apply(parse_date) if date_col else None
    df2['current_nav'] = None

    df2 = df2[df2["date_parsed"].notna() & (df2["amount"] > 0)]
    
    return df2.reset_index(drop=True)
