"""Loader for public.mis_data (PostgreSQL) — billed outstanding source."""

from __future__ import annotations
import pandas as pd
from config.connections import get_pg_conn
from config.settings import PG_MIS_TABLE

# Column name normalisation: maps whatever the DB returns → canonical snake_case.
# Keys cover both "Title Case with spaces" (direct sheet import) and
# lowercase/underscore variants.  Add more aliases here if the DB uses
# different names — nothing else in the codebase needs to change.
_COL_MAP: dict[str, str] = {
    # Corp
    "corp id":                  "corp_id",
    "corp_id":                  "corp_id",
    "corporate name":           "corporate_name",
    "corporate_name":           "corporate_name",
    "entity name":              "entity_name",
    "entity_name":              "entity_name",
    # Booking
    "booking id":               "booking_id",
    "booking_id":               "booking_id",
    "status":                   "status",
    "invoice no.":              "invoice_no",
    "invoice_no":               "invoice_no",
    "invoice no":               "invoice_no",
    # Property
    "location":                 "location",
    "property name":            "property_name",
    "property_name":            "property_name",
    "occupancy":                "occupancy",
    "guest name":               "guest_name",
    "guest_name":               "guest_name",
    # Dates
    "checkin":                  "checkin",
    "checkout":                 "checkout",
    "room":                     "room",
    "rns":                      "rns",
    # Financials
    "base_amount":              "base_amount",
    "base amount":              "base_amount",
    "retention_base_amount":    "retention_base_amount",
    "retention base amount":    "retention_base_amount",
    "sgst":                     "sgst",
    "cgst":                     "cgst",
    "inclusion/igst":           "inclusion_igst",
    "inclusion_igst":           "inclusion_igst",
    "convenience_fee":          "convenience_fee",
    "convenience fee":          "convenience_fee",
    "convenience_fee_sgst":     "convenience_fee_sgst",
    "convenience_fee_cgst":     "convenience_fee_cgst",
    "convenience_fee_igst":     "convenience_fee_igst",
    "discount":                 "discount",
    "grand_total":              "grand_total",
    "grand total":              "grand_total",
    "consol./manual invoice":   "consol_manual_invoice",
    "consol_manual_invoice":    "consol_manual_invoice",
    "cn reason":                "cn_reason",
    "cn_reason":                "cn_reason",
    "cn no":                    "cn_no",
    "cn_no":                    "cn_no",
    "cn_amount":                "cn_amount",
    "cn amount":                "cn_amount",
    "effective_total":          "effective_total",
    "effective total":          "effective_total",
    "amount_received":          "amount_received",
    "amount received":          "amount_received",
    "tds":                      "tds",
    "commission":               "commission",
    "write off":                "write_off",
    "write_off":                "write_off",
    "outstanding":              "outstanding",
    "remarks":                  "remarks",
    # Payment
    "payment ref\nnumber part1":    "payment_ref_1",
    "payment ref \nnumber part2":   "payment_ref_2",
    "payment recd datepart1":       "payment_date_1",
    "payment recd datepart2":       "payment_date_2",
    "bank":                         "bank",
    "invoice creation\ndate":       "invoice_creation_date",
    "invoice creation date":        "invoice_creation_date",
    "invoice submission\ndate":     "invoice_submission_date",
    "invoice submission date":      "invoice_submission_date",
    "credit days":                  "credit_days",
    "ageing":                       "ageing",
    "co month":                     "co_month",
    "payment recon":                "payment_recon",
}


def _normalise_cols(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={c: _COL_MAP.get(c.lower(), c) for c in df.columns})
    return df


def load_mis_data() -> pd.DataFrame:
    sql = f"SELECT * FROM {PG_MIS_TABLE}"
    conn = get_pg_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()
    df = pd.DataFrame(rows, columns=cols)
    return _normalise_cols(df)
