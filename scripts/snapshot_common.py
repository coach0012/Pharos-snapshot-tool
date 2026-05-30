from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


PHAROS_ATLANTIC = {
    "name": "Pharos Atlantic Testnet",
    "chain_id": 688689,
    "rpc_url": "https://atlantic.dplabs-internal.com",
    "explorer": "https://atlantic.pharosscan.xyz/",
    "native_token": "PHRS",
}

SNAPSHOT_TYPES = {
    "erc20-holders",
    "erc721-owners",
    "erc1155-balances",
    "contract-activity",
    "wallet-activity",
    "campaign-eligibility",
}

OUTPUT_FORMATS = {"csv", "json", "xlsx"}
ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


@dataclass
class ValidationResult:
    status: str
    warnings: list[str]
    errors: list[str]


def is_address(value: str) -> bool:
    return bool(ADDRESS_RE.fullmatch(value or ""))


def normalize_address(value: str) -> str:
    if not is_address(value):
        raise ValueError(f"invalid address: {value}")
    return "0x" + value[2:].lower()


def block_to_rpc(value: int | str) -> str:
    if value == "latest":
        return "latest"
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"invalid block value: {value}")
    return hex(value)


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_block(value: str | None, field: str, errors: list[str]) -> str | int | None:
    if value is None:
        return None
    if value == "latest":
        return value
    try:
        parsed = int(value)
    except ValueError:
        errors.append(f"{field} must be a non-negative integer or latest")
        return None
    if parsed < 0:
        errors.append(f"{field} must not be negative")
    return parsed


def parse_formats(value: str | None) -> list[str]:
    formats = split_csv(value or "csv")
    return formats or ["csv"]


def validate_formats(formats: list[str], errors: list[str]) -> None:
    unknown = sorted(set(formats) - OUTPUT_FORMATS)
    if unknown:
        errors.append(f"unsupported output format(s): {', '.join(unknown)}")


def validate_addresses(values: list[str], label: str, errors: list[str]) -> None:
    for item in values:
        if not is_address(item):
            errors.append(f"invalid {label} address: {item}")


def as_jsonable(value: Any) -> Any:
    if isinstance(value, set):
        return sorted(value)
    return value
