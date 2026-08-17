from pathlib import Path


# ============================================================
# Project root
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)


# ============================================================
# Main data directory
# ============================================================

DATA_PATH = (
    PROJECT_ROOT
    / "data"
)


# ============================================================
# Landing-zone directories
# ============================================================

LANDING_ROOT_PATH = (
    DATA_PATH
    / "landing"
)

TRANSACTION_LANDING_PATH = (
    LANDING_ROOT_PATH
    / "transactions"
    / "incoming"
)

CARD_LANDING_PATH = (
    LANDING_ROOT_PATH
    / "cards"
    / "incoming"
)

USER_LANDING_PATH = (
    LANDING_ROOT_PATH
    / "users"
    / "incoming"
)

LANDING_ARCHIVE_PATH = (
    LANDING_ROOT_PATH
    / "Archive"
)


# ============================================================
# Backward-compatible transaction Landing path
# ============================================================

# The current production pipeline processes transaction files.
# Keeping the name LANDING_PATH prevents existing notebooks,
# pipeline code, and tests from breaking.
LANDING_PATH = (
    TRANSACTION_LANDING_PATH
)


# ============================================================
# Processing-layer directories
# ============================================================

BRONZE_PATH = (
    DATA_PATH
    / "bronze"
)

SILVER_PATH = (
    DATA_PATH
    / "silver"
)

QUARANTINE_PATH = (
    DATA_PATH
    / "quarantine"
)

GOLD_PATH = (
    DATA_PATH
    / "gold"
)

ANALYTICS_PATH = (
    DATA_PATH
    / "analytics"
)

METADATA_PATH = (
    DATA_PATH
    / "metadata"
)


# ============================================================
# Documentation and operational directories
# ============================================================

LOGS_PATH = (
    PROJECT_ROOT
    / "logs"
)

MONITORING_PATH = (
    PROJECT_ROOT
    / "monitoring"
)

DOCS_PATH = (
    PROJECT_ROOT
    / "docs"
)

ARCHITECTURE_PATH = (
    PROJECT_ROOT
    / "architecture"
)


# ============================================================
# Pipeline settings
# ============================================================

PIPELINE_NAME = (
    "Enterprise Banking Analytics Pipeline"
)

PIPELINE_VERSION = "2.0"

LOG_LEVEL = "INFO"


# ============================================================
# Source-domain names
# ============================================================

TRANSACTION_SOURCE_DOMAIN = (
    "credit_card_transactions"
)

CARD_SOURCE_DOMAIN = (
    "credit_cards"
)

USER_SOURCE_DOMAIN = (
    "banking_users"
)


# ============================================================
# Create required runtime directories
# ============================================================

REQUIRED_RUNTIME_DIRECTORIES = [
    TRANSACTION_LANDING_PATH,
    CARD_LANDING_PATH,
    USER_LANDING_PATH,
    LANDING_ARCHIVE_PATH,
    BRONZE_PATH,
    SILVER_PATH,
    QUARANTINE_PATH,
    GOLD_PATH,
    ANALYTICS_PATH,
    METADATA_PATH,
    LOGS_PATH,
    MONITORING_PATH,
]


def create_required_directories() -> None:
    """
    Create every directory required by the local pipeline.

    The function is safe to run repeatedly because existing
    directories are preserved.
    """

    for directory_path in (
        REQUIRED_RUNTIME_DIRECTORIES
    ):
        directory_path.mkdir(
            parents=True,
            exist_ok=True,
        )