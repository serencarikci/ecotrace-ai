"""Migration integrity: calculation-definition checks and precursor audit columns."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

API_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = API_ROOT / "src" / "ecotrace" / "db" / "migrations" / "versions"


def test_migration_head_includes_precursor_audit_and_calc_def_ck() -> None:
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "src" / "ecotrace" / "db" / "migrations"))
    heads = ScriptDirectory.from_config(cfg).get_heads()
    assert heads == ["0032_cbam_prec_audit"]


def test_0023_drops_legacy_calc_def_check_names() -> None:
    text = (MIGRATIONS / "0023_cbam_purchased_electricity.py").read_text(encoding="utf-8")
    assert "DROP CONSTRAINT IF EXISTS ck_cbam_calc_def_type" in text
    assert "DROP CONSTRAINT IF EXISTS ck_cbam_calc_def_factor_req" in text
    assert "PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_V1" in text


def test_0026_includes_purchased_precursor_audit_columns() -> None:
    text = (MIGRATIONS / "0026_cbam_purchased_precursor.py").read_text(encoding="utf-8")
    assert "created_by_user_id UUID" in text
    assert "updated_by_user_id UUID" in text
    assert "fk_cbam_purch_prec_created_by" in text
    assert "fk_cbam_purch_prec_use_created_by" in text
