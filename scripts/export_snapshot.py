from __future__ import annotations

import argparse
import csv
import json
import zipfile
from html import escape
from pathlib import Path
from typing import Any

from snapshot_common import OUTPUT_FORMATS, PHAROS_ATLANTIC, parse_formats


SCHEMAS = {
    "erc20-holders": ["address", "balance", "raw_balance", "token_symbol", "token_contract", "block_number"],
    "erc721-owners": ["owner", "token_id", "token_contract", "block_number"],
    "erc1155-balances": ["owner", "token_id", "balance", "token_contract", "block_number"],
    "contract-activity": ["address", "contract", "event_name", "tx_hash", "block_number", "timestamp", "direction", "value", "token_id"],
    "wallet-activity": ["address", "contract", "event_name", "tx_hash", "block_number", "timestamp", "direction", "value", "token_id"],
    "campaign-eligibility": ["address", "eligible", "reason", "balance", "event_count", "contract", "block_number"],
}


def load_rows(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        data = data["rows"]
    if not isinstance(data, list):
        raise ValueError("input must be a JSON array or an object with a rows array")
    rows: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("each row must be an object")
        rows.append(item)
    return rows


def ordered_fields(snapshot_type: str, rows: list[dict[str, Any]]) -> list[str]:
    base = SCHEMAS[snapshot_type]
    extra = sorted({key for row in rows for key in row if key not in base})
    return base + extra


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def col_name(index: int) -> str:
    name = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        name = chr(65 + rem) + name
    return name


def sheet_xml(rows: list[list[Any]]) -> str:
    xml_rows = []
    for r_idx, row in enumerate(rows, start=1):
        cells = []
        for c_idx, value in enumerate(row):
            ref = f"{col_name(c_idx)}{r_idx}"
            text = escape("" if value is None else str(value))
            cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>')
        xml_rows.append(f'<row r="{r_idx}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(xml_rows)}</sheetData></worksheet>'
    )


def write_xlsx(path: Path, sheets: dict[str, list[list[Any]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet_names = list(sheets)
    workbook_sheets = []
    rels = []
    overrides = [
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    ]
    for idx, name in enumerate(sheet_names, start=1):
        workbook_sheets.append(f'<sheet name="{escape(name)}" sheetId="{idx}" r:id="rId{idx}"/>')
        rels.append(f'<Relationship Id="rId{idx}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{idx}.xml"/>')
        overrides.append(f'<Override PartName="/xl/worksheets/sheet{idx}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        f'{"".join(overrides)}</Types>'
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets>{"".join(workbook_sheets)}</sheets></workbook>'
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{"".join(rels)}</Relationships>'
    )

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        for idx, name in enumerate(sheet_names, start=1):
            archive.writestr(f"xl/worksheets/sheet{idx}.xml", sheet_xml(sheets[name]))


def build_payload(args: argparse.Namespace, rows: list[dict[str, Any]], fields: list[str]) -> dict[str, Any]:
    return {
        "summary": {
            "snapshot_type": args.snapshot_type,
            "network": PHAROS_ATLANTIC,
            "contract": args.contract,
            "block": args.block,
            "row_count": len(rows),
        },
        "fields": fields,
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Pharos snapshot rows to CSV, JSON, and XLSX.")
    parser.add_argument("--input", required=True, help="Input JSON rows.")
    parser.add_argument("--output", required=True, help="Output path prefix without extension.")
    parser.add_argument("--snapshot-type", required=True, choices=sorted(SCHEMAS), help="Snapshot type.")
    parser.add_argument("--contract", help="Related contract address.")
    parser.add_argument("--block", default="latest", help="Snapshot block.")
    parser.add_argument("--formats", default="csv", help="Comma-separated formats: csv,json,xlsx.")
    args = parser.parse_args()

    formats = parse_formats(args.formats)
    invalid = sorted(set(formats) - OUTPUT_FORMATS)
    if invalid:
        raise SystemExit(f"unsupported output format(s): {', '.join(invalid)}")

    rows = load_rows(Path(args.input))
    fields = ordered_fields(args.snapshot_type, rows)
    payload = build_payload(args, rows, fields)
    output = Path(args.output)
    written: list[str] = []

    if "csv" in formats:
        path = output.with_suffix(".csv")
        write_csv(path, rows, fields)
        written.append(str(path))
    if "json" in formats:
        path = output.with_suffix(".json")
        write_json(path, payload)
        written.append(str(path))
    if "xlsx" in formats:
        path = output.with_suffix(".xlsx")
        summary_rows = [[key, value] for key, value in payload["summary"].items()]
        data_rows = [fields] + [[row.get(field, "") for field in fields] for row in rows]
        sheet_name = {
            "erc721-owners": "NFT Owners",
            "contract-activity": "Activity",
            "wallet-activity": "Activity",
        }.get(args.snapshot_type, "Holders")
        write_xlsx(path, {"Summary": summary_rows, sheet_name: data_rows})
        written.append(str(path))

    print(json.dumps({"status": "safe", "written": written, "row_count": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

