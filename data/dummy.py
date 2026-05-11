"""Dummy data — replaces real source loaders until DB queries are wired in."""

from __future__ import annotations
import pandas as pd
import numpy as np
from datetime import date, timedelta
import random

_CORPS = [
    ("C001", "Infosys Ltd",          "Infosys BPO",        "Corporates"),
    ("C002", "Wipro Technologies",   "Wipro IT",           "Corporates"),
    ("C003", "HCL Technologies",     "HCL India",          "Corporates"),
    ("C004", "TCS Global",           "TCS Mumbai",         "Corporates"),
    ("C005", "Accenture India",      "Accenture Delivery", "Corporates"),
    ("M001", "Marriott Events",      "Marriott MICE",      "MICE"),
    ("M002", "ITC Grand Conclave",   "ITC Events",         "MICE"),
    ("S001", "Ministry of Finance",  "MoF Secretariat",    "Selected Accounts"),
    ("S002", "ONGC Corporate",       "ONGC Delhi",         "Selected Accounts"),
]

_PROPERTIES = [
    "FabHotel Prime Central", "FabHotel City Square", "FabHotel Business Park",
    "FabHotel Airport Inn", "FabHotel Skyline", "FabHotel Green Valley",
]

_LOCATIONS = ["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Pune", "Chennai"]
_STATUSES  = ["Confirmed", "Cancelled", "No-Show"]


def load_dummy_data() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows = []
    today = date.today()

    for i in range(600):
        corp_id, corp_name, entity, category = random.choice(_CORPS)
        checkin  = today - timedelta(days=int(rng.integers(1, 400)))
        checkout = checkin + timedelta(days=int(rng.integers(1, 6)))
        rns      = (checkout - checkin).days
        base     = float(rng.integers(3000, 25000)) * rns
        sgst     = round(base * 0.06, 2)
        cgst     = round(base * 0.06, 2)
        grand    = base + sgst + cgst
        discount = round(grand * rng.uniform(0, 0.1), 2)
        grand   -= discount
        tds      = round(grand * 0.02, 2)
        received = round(grand * rng.uniform(0, 1.0), 2)
        outstanding = round(grand - received - tds, 2)
        status   = rng.choice(_STATUSES, p=[0.75, 0.18, 0.07])

        # co_month from checkout
        co_month = checkout.strftime("%b-%y")

        rows.append({
            "Corp ID":           corp_id,
            "Corporate Name":    corp_name,
            "Entity Name":       entity,
            "Booking ID":        f"BK{100000 + i}",
            "Status":            status,
            "Invoice No.":       f"INV{200000 + i}" if status == "Confirmed" else None,
            "Location":          random.choice(_LOCATIONS),
            "Property Name":     random.choice(_PROPERTIES),
            "Occupancy":         "Single",
            "Guest Name":        f"Guest {i+1}",
            "Checkin":           checkin.isoformat(),
            "Checkout":          checkout.isoformat(),
            "Room":              f"{rng.integers(100, 500)}",
            "RNs":               rns,
            "Base_Amount":       base,
            "Retention_Base_Amount": 0,
            "SGST":              sgst,
            "CGST":              cgst,
            "Inclusion/IGST":    0,
            "convenience_fee":   0,
            "convenience_fee_sgst": 0,
            "convenience_fee_cgst": 0,
            "convenience_fee_igst": 0,
            "Discount":          discount,
            "Grand_Total":       grand,
            "Consol./Manual Invoice": None,
            "CN Reason":         None,
            "CN No":             None,
            "CN_Amount":         0,
            "Effective_total":   grand,
            "Amount_Received":   received,
            "TDS":               tds,
            "Commission":        round(grand * 0.05, 2),
            "write off":         0,
            "Outstanding":       outstanding,
            "Remarks":           None,
            "Payment Ref\nNumber Part1":  None,
            "Payment recd DatePart1":     None,
            "Payment Ref \nNumber Part2": None,
            "Payment recd DatePart2":     None,
            "Bank":              None,
            "Invoice creation\nDate":    None,
            "Invoice Submission\nDate":  None,
            "Credit Days":       30,
            "Ageing":            (today - checkout).days,
            "CO Month":          co_month,
            "Payment Recon":     "Reconciled" if received >= grand * 0.95 else "Pending",
            "category":          category,
        })

    return pd.DataFrame(rows)
