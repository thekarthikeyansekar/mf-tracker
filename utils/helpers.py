from datetime import datetime

def clean_num(val):
    try:
        return float(str(val).replace(",", "").replace('"', "").strip())
    except:
        return 0.0

def parse_date(val):
    s = str(val).strip()
    for fmt in ("%d-%b-%y", "%d-%b-%Y", "%d-%m-%Y", "%d/%m/%Y",
                "%Y-%m-%d", "%d-%B-%Y", "%d-%B-%y"):
        try:
            return datetime.strptime(s, fmt)
        except:
            pass
    return None

def fmt_inr(val):
    try:
        v = float(val)
        sign = "-" if v < 0 else ""
        return f"{sign}₹{abs(v):,.0f}"
    except:
        return str(val)

def fmt_pct(val):
    try:
        v = float(val)
        return f"{'+' if v >= 0 else ''}{v:.2f}%"
    except:
        return str(val)