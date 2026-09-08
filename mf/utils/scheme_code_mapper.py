FUNDS_SCEHME_CODES = {
        "DSP Mid Cap": 119071,
        "Axis Retirement Aggressive": 147825,
        "DSP Small Cap": 119212,
        "Axis Nifty 100": 147666,
        "DSP Nifty 50": 146376,
        "DSP ELSS Tax Saver": 119242,
        "DSP Multi Asset Allocation": 152056,
        "DSP Gold ETF FoF": 152183,
        "Axis MultiCap": 149383,
        "Axis Nifty 50": 149373,
        "Axis ELSS Tax Saver": 120503,
        "DSP Silver ETF FoF": 153487,
    }

def get_all_scheme_codes():
    return FUNDS_SCEHME_CODES

def get_scheme_code_by_name(name):
    return FUNDS_SCEHME_CODES[name]