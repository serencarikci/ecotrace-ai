#!/usr/bin/env python3
"""Deterministic CBAM SEE workbook → normalized CN catalog seed JSON.

Does not copy the binary workbook into the repository. Point WORKBOOK_PATH / CBAM_SEE_WORKBOOK_PATH
at the local official CBAM SEE template (default: repo local-reference copy).

Usage:
  WORKBOOK_PATH=/path/to/CBAM_SEE.xlsx \\
    python scripts/extract_cbam_see_cn_catalog.py

Output:
  src/ecotrace/modules/cbam/data/cbam_see_v2_1_cn_catalog.json
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
DEFAULT_OUT = ROOT / 'src/ecotrace/modules/cbam/data/cbam_see_v2_1_cn_catalog.json'
DEFAULT_WORKBOOK = (
    REPO_ROOT
    / 'local-reference'
    / (
        'CBAM SEE V2.1_Example Steel 3 Screws and nuts_final '
        'Dosyasının Kopyası- (1) (1).xlsx'
    )
)

DATASET_CODE = 'CBAM_SEE_CN_CODES'
DATASET_VERSION = 'SEE_V2.1'
TEMPLATE_VERSION = '2.1'
VALID_FROM = '2024-06-05'

REQUIRED_SHEETS = (
    'Parameters_CNCodes',
    'c_CodeLists',
    'Summary_Products',
    'D_Processes',
    'Parameters_Constants',
)

FIELD_FLAGS = {
    11: 'reducingAgent',
    12: 'steelMillIdentificationNumber',
    13: 'percentMn',
    14: 'percentCr',
    15: 'percentNi',
    16: 'percentOtherAlloys',
    17: 'percentCarbon',
    18: 'scrapPerTonneSteel',
    19: 'percentPreConsumerScrap',
}

FIELD_APPLICABILITY_KEYS = (
    'reducingAgent',
    'steelMillIdentificationNumber',
    'percentMn',
    'percentCr',
    'percentNi',
    'percentOtherAlloys',
    'percentOtherMaterials',
)


def _normalize_code(value: object) -> str:
    return str(value).strip().replace(' ', '')


def _field_applicability_from_sector_entry(entry: dict | None) -> dict[str, bool]:
    if not entry:
        return {key: False for key in FIELD_APPLICABILITY_KEYS}
    flags = entry.get('flags') if isinstance(entry.get('flags'), dict) else {}
    return {
        'reducingAgent': bool(flags.get('reducingAgent', False)),
        'steelMillIdentificationNumber': bool(
            flags.get('steelMillIdentificationNumber', False)
        ),
        'percentMn': bool(flags.get('percentMn', False)),
        'percentCr': bool(flags.get('percentCr', False)),
        'percentNi': bool(flags.get('percentNi', False)),
        'percentOtherAlloys': bool(flags.get('percentOtherAlloys', False)),
        'percentOtherMaterials': bool(entry.get('percentOtherMaterials', False)),
    }


def extract(workbook_path: Path) -> dict:
    wb = load_workbook(workbook_path, read_only=True, data_only=True)
    missing = [name for name in REQUIRED_SHEETS if name not in wb.sheetnames]
    if missing:
        raise SystemExit(f'Missing required sheets: {missing}')

    ws = wb['Parameters_CNCodes']
    codes: list[dict] = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=4, values_only=True), start=4):
        cells = list(row) + [None] * 8
        cn_key, display, desc, normalized, sector, numbering, _, desc_en = cells[:8]
        if cn_key is None or normalized is None:
            continue
        # Header/meta rows use non-numeric keys such as 'ausblenden' / 'CNKEY'.
        key_text = str(cn_key).strip()
        if not key_text or not key_text[0].isdigit():
            continue
        codes.append(
            {
                'sourceRow': row_idx,
                'cnKey': key_text,
                'normalizedCode': _normalize_code(normalized),
                'displayCode': str(display).strip() if display else _normalize_code(normalized),
                'descriptionEn': str(desc_en or desc or '').strip(),
                'cbamSector': str(sector).strip() if sector else '',
                'numberingLabel': str(numbering).strip() if numbering else None,
            }
        )

    if not codes:
        raise SystemExit('No CN codes extracted from Parameters_CNCodes')
    if len(codes) != len({c['cnKey'] for c in codes}):
        raise SystemExit('Duplicate CNKEY values in Parameters_CNCodes')
    if len(codes) != len({c['normalizedCode'] for c in codes}):
        raise SystemExit('Duplicate normalized CN codes in Parameters_CNCodes')

    ws_const = wb['Parameters_Constants']
    reducing: list[str] = []
    for col in range(2, 6):
        value = ws_const.cell(58, col).value
        if value:
            reducing.append(str(value).strip())
    if reducing != ['Coal or coke', 'Natural gas', 'Biogas', 'Hydrogen']:
        raise SystemExit(f'Unexpected reducing-agent list: {reducing}')

    applicability: dict[str, dict] = {}
    for row_idx in range(110, 128):
        good = ws_const.cell(row_idx, 1).value
        if not good:
            continue
        good_name = str(good).strip()
        labels = []
        for col in range(2, 10):
            value = ws_const.cell(row_idx, col).value
            if value and str(value).strip() not in ('n.a.', 'n.a'):
                labels.append(str(value).strip())
        flags = {
            FIELD_FLAGS[col]: bool(ws_const.cell(row_idx, col).value) for col in FIELD_FLAGS
        }
        applicability[good_name] = {
            'parameterLabels': labels,
            'flags': flags,
            'percentOtherMaterials': '% other materials' in labels,
        }

    wb.close()
    # Persist per-CN applicability at extraction time from the workbook matrix
    # (not reconstructed later via sector-name string matching in the API).
    for code in codes:
        code['fieldApplicability'] = _field_applicability_from_sector_entry(
            applicability.get(code['cbamSector'])
        )

    payload = {
        'dataset': {
            'datasetCode': DATASET_CODE,
            'datasetVersion': DATASET_VERSION,
            'sourceWorkbookName': workbook_path.name,
            'sourceWorkbookSha256': hashlib.sha256(workbook_path.read_bytes()).hexdigest(),
            'sourceTemplateVersion': TEMPLATE_VERSION,
            'validFrom': VALID_FROM,
            'validUntil': None,
            'sourceSheets': {
                'cnCodes': 'Parameters_CNCodes',
                'codeLists': 'c_CodeLists',
                'reducingAgents': 'Parameters_Constants',
                'specialParameters': 'Parameters_Constants',
                'summaryProducts': 'Summary_Products',
            },
        },
        'cnCodes': codes,
        'controlledLists': {
            'REDUCING_AGENT': [{'code': value, 'label': value} for value in reducing]
        },
        'sectorSpecialParameters': applicability,
    }
    # Checksum excludes itself: hash canonical payload without contentChecksum.
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    payload['dataset']['contentChecksum'] = hashlib.sha256(canonical.encode()).hexdigest()
    return payload


def main() -> int:
    workbook = Path(os.environ.get('WORKBOOK_PATH', str(DEFAULT_WORKBOOK)))
    out = Path(os.environ.get('OUT_PATH', str(DEFAULT_OUT)))
    if not workbook.is_file():
        print(f'Workbook not readable: {workbook}', file=sys.stderr)
        return 1
    payload = extract(workbook)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {out}')
    print(f'CN codes: {len(payload["cnCodes"])}')
    print(f'contentChecksum: {payload["dataset"]["contentChecksum"]}')
    print(f'sourceWorkbookSha256: {payload["dataset"]["sourceWorkbookSha256"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
