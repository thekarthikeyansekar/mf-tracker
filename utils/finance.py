import requests
from datetime import datetime


def xirr(cashflows):
    def xnpv(rate):
        return sum(cf / (1 + rate) ** ((d - cashflows[0][0]).days / 365)
                   for d, cf in cashflows)

    rate = 0.1
    for _ in range(100):
        f = xnpv(rate)
        df = sum(
            -((d - cashflows[0][0]).days / 365) * cf /
            (1 + rate) ** (((d - cashflows[0][0]).days / 365) + 1)
            for d, cf in cashflows
        )
        rate -= f / df if df != 0 else 0
    return rate


def fetch_latest_nav(scheme_code):
    url = f"https://npsnav.in/api/{scheme_code}"
    return requests.get(url).json()