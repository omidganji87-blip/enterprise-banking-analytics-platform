from collections.abc import Sequence


def validate_columns(
    actual_columns: Sequence[str],
    expected_columns: Sequence[str],
) -> dict:
    """
    Compare actual source columns with the expected schema contract.

    Returns a dictionary containing:
    - actual_count
    - expected_count
    - missing_columns
    - unexpected_columns
    - is_valid
    """

    actual_set = set(actual_columns)
    expected_set = set(expected_columns)

    missing_columns = sorted(expected_set - actual_set)
    unexpected_columns = sorted(actual_set - expected_set)

    return {
        "actual_count": len(actual_columns),
        "expected_count": len(expected_columns),
        "missing_columns": missing_columns,
        "unexpected_columns": unexpected_columns,
        "is_valid": not missing_columns and not unexpected_columns,
    }

from collections.abc import Mapping


def validate_dtypes(
    actual_dtypes: Mapping[str, str],
    expected_dtypes: Mapping[str, str],
) -> dict:
    """
    Compare actual source data types with the expected schema contract.
    """

    mismatched_columns = {}

    for column, expected_dtype in expected_dtypes.items():
        actual_dtype = actual_dtypes.get(column)

        if actual_dtype != expected_dtype:
            mismatched_columns[column] = {
                "expected": expected_dtype,
                "actual": actual_dtype,
            }

    return {
        "mismatched_columns": mismatched_columns,
        "is_valid": not mismatched_columns,
    }