# Test type: Integration
# Validation: All endpoints with PDF example data; parse totals, filter k sums, NPS/Index return values.
# Command: uv run pytest test/test_api.py -v

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
BASE = "/blackrock/challenge/v1"

# PDF example data
EXPENSES = [
    {"timestamp": "2023-10-12 20:15:00", "amount": 250},
    {"timestamp": "2023-02-28 15:49:00", "amount": 375},
    {"timestamp": "2023-07-01 21:59:00", "amount": 620},
    {"timestamp": "2023-12-17 08:09:00", "amount": 480},
]
Q_PERIODS = [{"fixed": 0, "start": "2023-07-01 00:00:00", "end": "2023-07-31 23:59:00"}]
P_PERIODS = [{"extra": 25, "start": "2023-10-01 08:00:00", "end": "2023-12-31 19:59:00"}]
K_PERIODS = [
    {"start": "2023-03-01 00:00:00", "end": "2023-11-30 23:59:00"},
    {"start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:00"},
]


def test_parse():
    r = client.post(f"{BASE}/transactions:parse", json={"expenses": EXPENSES})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 4
    assert sum(t["remanent"] for t in data) == 175
    assert sum(t["amount"] for t in data) == 250 + 375 + 620 + 480


def test_validator():
    parse_r = client.post(f"{BASE}/transactions:parse", json={"expenses": EXPENSES})
    transactions = parse_r.json()
    r = client.post(
        f"{BASE}/transactions:validator",
        json={"wage": 50_000, "transactions": transactions},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["valid"]) == 4
    assert len(data["invalid"]) == 0


def test_filter():
    parse_r = client.post(f"{BASE}/transactions:parse", json={"expenses": EXPENSES})
    transactions = parse_r.json()
    r = client.post(
        f"{BASE}/transactions:filter",
        json={
            "q": Q_PERIODS,
            "p": P_PERIODS,
            "k": K_PERIODS,
            "transactions": transactions,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["savingsByDates"]) == 2
    assert data["savingsByDates"][0]["amount"] == 75
    assert data["savingsByDates"][1]["amount"] == 145


def test_returns_nps():
    parse_r = client.post(f"{BASE}/transactions:parse", json={"expenses": EXPENSES})
    transactions = parse_r.json()
    r = client.post(
        f"{BASE}/returns:nps",
        json={
            "age": 29,
            "wage": 50_000,
            "inflation": 0.055,
            "q": Q_PERIODS,
            "p": P_PERIODS,
            "k": K_PERIODS,
            "transactions": transactions,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["savingsByDates"]) == 2
    assert data["savingsByDates"][1]["amount"] == 145
    assert abs(data["savingsByDates"][1]["profits"] - 86.88) < 2
    assert data["savingsByDates"][1]["taxBenefit"] == 0


def test_returns_index():
    parse_r = client.post(f"{BASE}/transactions:parse", json={"expenses": EXPENSES})
    transactions = parse_r.json()
    r = client.post(
        f"{BASE}/returns:index",
        json={
            "age": 29,
            "wage": 50_000,
            "inflation": 0.055,
            "q": Q_PERIODS,
            "p": P_PERIODS,
            "k": K_PERIODS,
            "transactions": transactions,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["savingsByDates"]) == 2
    assert data["savingsByDates"][1]["amount"] == 145
    assert "return" in data["savingsByDates"][1]
    assert abs(data["savingsByDates"][1]["return"] - 1829.5) < 30


def test_performance():
    r = client.get(f"{BASE}/performance")
    assert r.status_code == 200
    data = r.json()
    assert "time" in data
    assert "memory" in data and "MB" in data["memory"]
    assert "threads" in data and isinstance(data["threads"], int)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
