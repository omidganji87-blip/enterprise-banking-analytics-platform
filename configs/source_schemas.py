"""
Source-system schema contracts.

Each contract defines:

1. Required source columns.
2. Expected number of columns.
3. Expected pandas data types.

These contracts protect the pipeline from unexpected source-schema
changes before data is published to downstream layers.
"""


# ============================================================
# Transaction source schema
# ============================================================

TRANSACTION_REQUIRED_COLUMNS = [
    "User",
    "Card",
    "Year",
    "Month",
    "Day",
    "Time",
    "Amount",
    "Use Chip",
    "Merchant Name",
    "Merchant City",
    "Merchant State",
    "Zip",
    "MCC",
    "Errors?",
    "Is Fraud?",
]

TRANSACTION_EXPECTED_COLUMN_COUNT = 15

TRANSACTION_EXPECTED_DTYPES = {
    "User": "int64",
    "Card": "int64",
    "Year": "int64",
    "Month": "int64",
    "Day": "int64",
    "Time": "str",
    "Amount": "str",
    "Use Chip": "str",
    "Merchant Name": "int64",
    "Merchant City": "str",
    "Merchant State": "str",
    "Zip": "float64",
    "MCC": "int64",
    "Errors?": "str",
    "Is Fraud?": "str",
}


# ============================================================
# Card source schema
# ============================================================

CARD_REQUIRED_COLUMNS = [
    "User",
    "CARD INDEX",
    "Card Brand",
    "Card Type",
    "Card Number",
    "Expires",
    "CVV",
    "Has Chip",
    "Cards Issued",
    "Credit Limit",
    "Acct Open Date",
    "Year PIN last Changed",
    "Card on Dark Web",
]

CARD_EXPECTED_COLUMN_COUNT = 13

CARD_EXPECTED_DTYPES = {
    "User": "int64",
    "CARD INDEX": "int64",
    "Card Brand": "str",
    "Card Type": "str",
    "Card Number": "int64",
    "Expires": "str",
    "CVV": "int64",
    "Has Chip": "str",
    "Cards Issued": "int64",
    "Credit Limit": "str",
    "Acct Open Date": "str",
    "Year PIN last Changed": "int64",
    "Card on Dark Web": "str",
}


# ============================================================
# User source schema
# ============================================================

USER_REQUIRED_COLUMNS = [
    "Person",
    "Current Age",
    "Retirement Age",
    "Birth Year",
    "Birth Month",
    "Gender",
    "Address",
    "Apartment",
    "City",
    "State",
    "Zipcode",
    "Latitude",
    "Longitude",
    "Per Capita Income - Zipcode",
    "Yearly Income - Person",
    "Total Debt",
    "FICO Score",
    "Num Credit Cards",
]

USER_EXPECTED_COLUMN_COUNT = 18

USER_EXPECTED_DTYPES = {
    "Person": "str",
    "Current Age": "int64",
    "Retirement Age": "int64",
    "Birth Year": "int64",
    "Birth Month": "int64",
    "Gender": "str",
    "Address": "str",
    "Apartment": "float64",
    "City": "str",
    "State": "str",
    "Zipcode": "int64",
    "Latitude": "float64",
    "Longitude": "float64",
    "Per Capita Income - Zipcode": "str",
    "Yearly Income - Person": "str",
    "Total Debt": "str",
    "FICO Score": "int64",
    "Num Credit Cards": "int64",
}


# ============================================================
# Sensitive source columns
# ============================================================

# These columns may exist in the protected raw/Bronze layer,
# but they must never be exposed directly in Gold tables,
# dashboards, exports, screenshots, or the public repository.

CARD_SENSITIVE_COLUMNS = [
    "Card Number",
    "CVV",
]

USER_SENSITIVE_COLUMNS = [
    "Person",
    "Address",
    "Apartment",
    "Latitude",
    "Longitude",
]


# ============================================================
# Central source-schema registry
# ============================================================

SOURCE_SCHEMA_REGISTRY = {
    "transactions": {
        "required_columns": TRANSACTION_REQUIRED_COLUMNS,
        "expected_column_count": (
            TRANSACTION_EXPECTED_COLUMN_COUNT
        ),
        "expected_dtypes": TRANSACTION_EXPECTED_DTYPES,
        "sensitive_columns": [],
    },
    "cards": {
        "required_columns": CARD_REQUIRED_COLUMNS,
        "expected_column_count": (
            CARD_EXPECTED_COLUMN_COUNT
        ),
        "expected_dtypes": CARD_EXPECTED_DTYPES,
        "sensitive_columns": CARD_SENSITIVE_COLUMNS,
    },
    "users": {
        "required_columns": USER_REQUIRED_COLUMNS,
        "expected_column_count": (
            USER_EXPECTED_COLUMN_COUNT
        ),
        "expected_dtypes": USER_EXPECTED_DTYPES,
        "sensitive_columns": USER_SENSITIVE_COLUMNS,
    },
}