import pandas as pd
import pytest

from configs.source_schemas import (
    CARD_EXPECTED_DTYPES,
    CARD_REQUIRED_COLUMNS,
    CARD_SENSITIVE_COLUMNS,
    SOURCE_SCHEMA_REGISTRY,
    USER_EXPECTED_DTYPES,
    USER_REQUIRED_COLUMNS,
    USER_SENSITIVE_COLUMNS,
)
from src.schema_validation import (
    validate_columns,
    validate_dtypes,
)


# ============================================================
# Basic column-validation tests
# ============================================================

def test_validate_columns_returns_valid_for_matching_schema():
    actual_columns = [
        "User",
        "Card",
        "Amount",
    ]

    expected_columns = [
        "User",
        "Card",
        "Amount",
    ]

    result = validate_columns(
        actual_columns=actual_columns,
        expected_columns=expected_columns,
    )

    assert result["is_valid"] is True
    assert result["missing_columns"] == []
    assert result["unexpected_columns"] == []
    assert result["actual_count"] == 3
    assert result["expected_count"] == 3


def test_validate_columns_detects_missing_column():
    actual_columns = [
        "User",
        "Card",
    ]

    expected_columns = [
        "User",
        "Card",
        "Amount",
    ]

    result = validate_columns(
        actual_columns=actual_columns,
        expected_columns=expected_columns,
    )

    assert result["is_valid"] is False
    assert result["missing_columns"] == ["Amount"]
    assert result["unexpected_columns"] == []


def test_validate_columns_detects_unexpected_column():
    actual_columns = [
        "User",
        "Card",
        "Amount",
        "UnexpectedColumn",
    ]

    expected_columns = [
        "User",
        "Card",
        "Amount",
    ]

    result = validate_columns(
        actual_columns=actual_columns,
        expected_columns=expected_columns,
    )

    assert result["is_valid"] is False
    assert result["missing_columns"] == []
    assert result["unexpected_columns"] == [
        "UnexpectedColumn"
    ]


# ============================================================
# Basic data-type-validation tests
# ============================================================

def test_validate_dtypes_returns_valid_for_matching_types():
    actual_dtypes = {
        "User": "int64",
        "Amount": "str",
    }

    expected_dtypes = {
        "User": "int64",
        "Amount": "str",
    }

    result = validate_dtypes(
        actual_dtypes=actual_dtypes,
        expected_dtypes=expected_dtypes,
    )

    assert result["is_valid"] is True
    assert result["mismatched_columns"] == {}


def test_validate_dtypes_detects_type_mismatch():
    actual_dtypes = {
        "User": "int64",
        "Amount": "float64",
    }

    expected_dtypes = {
        "User": "int64",
        "Amount": "str",
    }

    result = validate_dtypes(
        actual_dtypes=actual_dtypes,
        expected_dtypes=expected_dtypes,
    )

    assert result["is_valid"] is False

    assert result["mismatched_columns"] == {
        "Amount": {
            "expected": "str",
            "actual": "float64",
        }
    }


def test_validate_dtypes_detects_missing_dtype():
    actual_dtypes = {
        "User": "int64",
    }

    expected_dtypes = {
        "User": "int64",
        "Amount": "str",
    }

    result = validate_dtypes(
        actual_dtypes=actual_dtypes,
        expected_dtypes=expected_dtypes,
    )

    assert result["is_valid"] is False

    assert result["mismatched_columns"] == {
        "Amount": {
            "expected": "str",
            "actual": None,
        }
    }


# ============================================================
# Source-schema registry tests
# ============================================================

def test_source_schema_registry_contains_all_domains():
    assert set(SOURCE_SCHEMA_REGISTRY) == {
        "transactions",
        "cards",
        "users",
    }


@pytest.mark.parametrize(
    "domain_name",
    [
        "transactions",
        "cards",
        "users",
    ],
)
def test_source_schema_contract_is_internally_consistent(
    domain_name,
):
    contract = SOURCE_SCHEMA_REGISTRY[domain_name]

    required_columns = contract["required_columns"]
    expected_column_count = contract[
        "expected_column_count"
    ]
    expected_dtypes = contract["expected_dtypes"]
    sensitive_columns = contract["sensitive_columns"]

    assert len(required_columns) == expected_column_count

    assert set(expected_dtypes) == set(required_columns)

    assert set(sensitive_columns).issubset(
        set(required_columns)
    )


# ============================================================
# Card source-schema tests
# ============================================================

def test_card_source_contract_accepts_representative_data():
    card_df = pd.DataFrame(
        {
            "User": [0],
            "CARD INDEX": [0],
            "Card Brand": ["Visa"],
            "Card Type": ["Debit"],
            "Card Number": [1234567890123456],
            "Expires": ["12/2030"],
            "CVV": [123],
            "Has Chip": ["YES"],
            "Cards Issued": [1],
            "Credit Limit": ["$5000"],
            "Acct Open Date": ["01/2018"],
            "Year PIN last Changed": [2025],
            "Card on Dark Web": ["No"],
        }
    )

    actual_dtypes = {
        column: str(dtype)
        for column, dtype in card_df.dtypes.items()
    }

    column_validation = validate_columns(
        actual_columns=card_df.columns.tolist(),
        expected_columns=CARD_REQUIRED_COLUMNS,
    )

    dtype_validation = validate_dtypes(
        actual_dtypes=actual_dtypes,
        expected_dtypes=CARD_EXPECTED_DTYPES,
    )

    assert column_validation["is_valid"] is True
    assert dtype_validation["is_valid"] is True


def test_card_source_contract_rejects_missing_cvv():
    actual_columns = [
        column
        for column in CARD_REQUIRED_COLUMNS
        if column != "CVV"
    ]

    result = validate_columns(
        actual_columns=actual_columns,
        expected_columns=CARD_REQUIRED_COLUMNS,
    )

    assert result["is_valid"] is False
    assert result["missing_columns"] == ["CVV"]


# ============================================================
# User source-schema tests
# ============================================================

def test_user_source_contract_accepts_representative_data():
    user_df = pd.DataFrame(
        {
            "Person": ["Synthetic User"],
            "Current Age": [40],
            "Retirement Age": [65],
            "Birth Year": [1986],
            "Birth Month": [6],
            "Gender": ["Female"],
            "Address": ["100 Example Street"],
            "Apartment": [12.0],
            "City": ["Toronto"],
            "State": ["ON"],
            "Zipcode": [12345],
            "Latitude": [43.65],
            "Longitude": [-79.38],
            "Per Capita Income - Zipcode": ["$35000"],
            "Yearly Income - Person": ["$75000"],
            "Total Debt": ["$12000"],
            "FICO Score": [720],
            "Num Credit Cards": [3],
        }
    )

    actual_dtypes = {
        column: str(dtype)
        for column, dtype in user_df.dtypes.items()
    }

    column_validation = validate_columns(
        actual_columns=user_df.columns.tolist(),
        expected_columns=USER_REQUIRED_COLUMNS,
    )

    dtype_validation = validate_dtypes(
        actual_dtypes=actual_dtypes,
        expected_dtypes=USER_EXPECTED_DTYPES,
    )

    assert column_validation["is_valid"] is True
    assert dtype_validation["is_valid"] is True


def test_user_source_contract_rejects_missing_fico_score():
    actual_columns = [
        column
        for column in USER_REQUIRED_COLUMNS
        if column != "FICO Score"
    ]

    result = validate_columns(
        actual_columns=actual_columns,
        expected_columns=USER_REQUIRED_COLUMNS,
    )

    assert result["is_valid"] is False
    assert result["missing_columns"] == ["FICO Score"]


# ============================================================
# Sensitive-column governance tests
# ============================================================

def test_sensitive_columns_are_registered_correctly():
    assert set(CARD_SENSITIVE_COLUMNS) == {
        "Card Number",
        "CVV",
    }

    assert set(USER_SENSITIVE_COLUMNS) == {
        "Person",
        "Address",
        "Apartment",
        "Latitude",
        "Longitude",
    }

    assert set(CARD_SENSITIVE_COLUMNS).issubset(
        set(CARD_REQUIRED_COLUMNS)
    )

    assert set(USER_SENSITIVE_COLUMNS).issubset(
        set(USER_REQUIRED_COLUMNS)
    )