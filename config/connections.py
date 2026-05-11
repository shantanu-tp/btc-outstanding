"""Connection factory functions — PostgreSQL, MySQL instances, Google Sheets."""

import os
import psycopg2
import psycopg2.extras
import pymysql
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

# ── PostgreSQL ────────────────────────────────────────────────────────────────

def get_pg_conn():
    return psycopg2.connect(
        host=os.environ["PG_HOST"],
        port=int(os.environ.get("PG_PORT", 5432)),
        dbname=os.environ["PG_DATABASE"],
        user=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"],
        connect_timeout=15,
    )


# ── MySQL helpers ─────────────────────────────────────────────────────────────

def _mysql_conn(prefix: str):
    return pymysql.connect(
        host=os.environ[f"{prefix}_HOST"],
        port=int(os.environ.get(f"{prefix}_PORT", 3306)),
        database=os.environ[f"{prefix}_DATABASE"],
        user=os.environ[f"{prefix}_USER"],
        password=os.environ[f"{prefix}_PASSWORD"],
        connect_timeout=15,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def get_mysql2_conn():
    """booking_java_microservice"""
    return _mysql_conn("MYSQL2")


def get_mysql3_conn():
    """flight_service"""
    return _mysql_conn("MYSQL3")


def get_mysql4_conn():
    """user_microservice"""
    return _mysql_conn("MYSQL4")


def get_mysql6_conn():
    """conference_service"""
    return _mysql_conn("MYSQL6")


# ── Google Sheets ─────────────────────────────────────────────────────────────

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def get_gspread_client() -> gspread.Client:
    creds_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    creds = Credentials.from_service_account_file(creds_path, scopes=_SCOPES)
    return gspread.authorize(creds)


def open_sheet(sheet_id: str, worksheet: str | int = 0) -> gspread.Worksheet:
    gc = get_gspread_client()
    return gc.open_by_key(sheet_id).get_worksheet(worksheet) if isinstance(worksheet, int) \
        else gc.open_by_key(sheet_id).worksheet(worksheet)
