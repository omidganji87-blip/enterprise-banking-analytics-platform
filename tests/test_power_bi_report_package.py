from pathlib import Path
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PBIX_PATH = (
    PROJECT_ROOT
    / "dashboard"
    / "Enterprise_Banking_Intelligence_Command_Center.pbix"
)

EXPECTED_ALT_TEXT = (
    "Combo chart showing monthly transaction count",
    "Donut chart showing the share of transactions",
    "Time-series comparison of fraud and error transaction counts",
    "Horizontal bar chart ranking transaction error categories",
    "Horizontal bar chart ranking merchants by fraud transaction count",
    "Horizontal bar chart comparing fraud transaction counts across merchant category codes",
    "Transaction-level evidence table for the selected merchant",
)


def _read_layout() -> tuple[set[str], str]:
    with ZipFile(PBIX_PATH) as package:
        names = set(package.namelist())
        layout = package.read("Report/Layout").decode("utf-16")
    return names, layout


def test_power_bi_report_is_a_complete_package() -> None:
    names, _ = _read_layout()

    assert {
        "Version",
        "Connections",
        "DataModel",
        "Report/Layout",
    } <= names


def test_power_bi_report_preserves_exact_safe_merchant_display_contract() -> None:
    _, layout = _read_layout()

    assert "dim_merchant_analytics.merchant_display_label" in layout
    assert "Merchant Label" in layout
    assert "LocalDateTable_" not in layout


def test_power_bi_report_packages_all_analytical_alt_text() -> None:
    _, layout = _read_layout()

    assert layout.count("altText") == len(EXPECTED_ALT_TEXT)
    for description in EXPECTED_ALT_TEXT:
        assert description in layout
