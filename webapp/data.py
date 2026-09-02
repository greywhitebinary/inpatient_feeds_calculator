"""Formulary data loading, validation, and portable workbook helpers."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FORMULA_PATH = PROJECT_ROOT / "formulary_working" / "canada_formulas_working.csv"
MODULAR_PATH = PROJECT_ROOT / "formulary_working" / "modular_products_working.csv"
ONS_PATH = PROJECT_ROOT / "formulary_working" / "ons_products_working.csv"

FORMULA_REQUIRED_COLUMNS = {
    "name", "brand", "kcal_per_mL", "protein_per_mL", "fat_per_mL",
    "carbohydrate_per_mL", "fibre_per_mL", "sodium_per_mL", "potassium_per_mL",
    "calcium_per_mL", "magnesium_per_mL", "phosphorus_per_mL", "free_water_per_mL",
    "source", "verified",
}
MODULAR_REQUIRED_COLUMNS = {
    "id", "product_type", "name", "brand", "dose_unit", "basis_amount",
    "basis_description", "kcal_per_basis", "protein_g_per_basis",
    "carbohydrate_g_per_basis", "fat_g_per_basis", "fibre_g_per_basis",
    "free_water_ml_per_basis", "preparation_water_rule", "source", "verified",
    "sodium_mg_per_basis", "potassium_mg_per_basis", "calcium_mg_per_basis",
    "magnesium_mg_per_basis", "phosphorus_mg_per_basis",
}
ONS_REQUIRED_COLUMNS = FORMULA_REQUIRED_COLUMNS | {
    "id", "product_name", "flavour", "container_size_ml", "package_unit",
}

FORMULA_NUMERIC_COLUMNS = {
    "kcal_per_mL", "protein_per_mL", "fat_per_mL", "carbohydrate_per_mL",
    "sodium_per_mL", "potassium_per_mL", "calcium_per_mL",
    "magnesium_per_mL", "phosphorus_per_mL", "free_water_per_mL",
}
FORMULA_OPTIONAL_NUMERIC_COLUMNS = {"fibre_per_mL"}
MODULAR_NUMERIC_COLUMNS = {
    "basis_amount", "kcal_per_basis", "protein_g_per_basis",
    "carbohydrate_g_per_basis", "fat_g_per_basis", "fibre_g_per_basis",
}
MODULAR_OPTIONAL_NUMERIC_COLUMNS = {
    "sodium_mg_per_basis", "potassium_mg_per_basis", "calcium_mg_per_basis",
    "magnesium_mg_per_basis", "phosphorus_mg_per_basis",
    "free_water_ml_per_basis",
}
ONS_NUMERIC_COLUMNS = FORMULA_NUMERIC_COLUMNS | {"container_size_ml"}
ONS_OPTIONAL_NUMERIC_COLUMNS = FORMULA_OPTIONAL_NUMERIC_COLUMNS


def load_master_formulas() -> pd.DataFrame:
    formulas = pd.read_csv(FORMULA_PATH, encoding="utf-8-sig")
    validate_columns(formulas, FORMULA_REQUIRED_COLUMNS, "Master formulary")
    return validate_product_rows(
        formulas,
        FORMULA_NUMERIC_COLUMNS,
        "Master formulary",
        optional_numeric_columns=FORMULA_OPTIONAL_NUMERIC_COLUMNS,
        positive_numeric_columns={"kcal_per_mL"},
    ).fillna(0)


def load_master_modulars() -> pd.DataFrame:
    modulars = pd.read_csv(MODULAR_PATH, encoding="utf-8-sig")
    validate_columns(modulars, MODULAR_REQUIRED_COLUMNS, "Master modulars")
    return validate_product_rows(
        modulars,
        MODULAR_NUMERIC_COLUMNS,
        "Master modulars",
        optional_numeric_columns=MODULAR_OPTIONAL_NUMERIC_COLUMNS,
        positive_numeric_columns={"basis_amount"},
    ).fillna(0)


def load_master_ons() -> pd.DataFrame:
    ons = pd.read_csv(ONS_PATH, encoding="utf-8-sig")
    validate_columns(ons, ONS_REQUIRED_COLUMNS, "Master ONS")
    cleaned = validate_product_rows(
        ons,
        ONS_NUMERIC_COLUMNS,
        "Master ONS",
        optional_numeric_columns=ONS_OPTIONAL_NUMERIC_COLUMNS,
        positive_numeric_columns={"kcal_per_mL", "container_size_ml"},
    )
    for column in ("id", "product_name", "flavour", "package_unit"):
        if cleaned[column].astype(str).str.strip().replace("nan", "").eq("").any():
            raise ValueError(f"Master ONS contains a blank {column.replace('_', ' ')}.")
    if cleaned["id"].astype(str).str.strip().str.casefold().duplicated().any():
        raise ValueError("Master ONS contains duplicate ids.")
    return cleaned.fillna(0)


def validate_columns(frame: pd.DataFrame, required: set[str], label: str) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{label} is missing required columns: {', '.join(missing)}.")


def validate_product_rows(
    frame: pd.DataFrame,
    numeric_columns: set[str],
    label: str,
    optional_numeric_columns: set[str] | None = None,
    positive_numeric_columns: set[str] | None = None,
) -> pd.DataFrame:
    """Reject incomplete core profiles before a local formulary becomes active."""
    cleaned = frame.copy()
    text_columns = ("name", "brand", "source", "verified")
    for column in text_columns:
        if cleaned[column].astype(str).str.strip().replace("nan", "").eq("").any():
            raise ValueError(f"{label} contains a blank {column.replace('_', ' ')}.")
    duplicated = cleaned["name"].astype(str).str.strip().str.casefold().duplicated()
    if duplicated.any():
        raise ValueError(f"{label} contains duplicate product names.")
    for column in numeric_columns:
        converted = pd.to_numeric(cleaned[column], errors="coerce")
        if converted.isna().any() or (converted < 0).any():
            raise ValueError(f"{label} has a blank, non-numeric, or negative value in {column}.")
        if column in (positive_numeric_columns or set()) and (converted <= 0).any():
            raise ValueError(f"{label} requires a value greater than zero in {column}.")
        cleaned[column] = converted
    for column in optional_numeric_columns or set():
        raw = cleaned[column]
        converted = pd.to_numeric(raw, errors="coerce")
        has_invalid = raw.notna() & converted.isna()
        if has_invalid.any() or (converted.dropna() < 0).any():
            raise ValueError(f"{label} has a blank, non-numeric, or negative value in {column}.")
        cleaned[column] = converted
    return cleaned


def validate_import(
    formulas: pd.DataFrame,
    modulars: pd.DataFrame,
    ons: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    validate_columns(formulas, FORMULA_REQUIRED_COLUMNS, "My Formulary worksheet")
    validate_columns(modulars, MODULAR_REQUIRED_COLUMNS, "My Modulars worksheet")
    if ons is None:
        ons = load_master_ons().iloc[0:0].copy()
    validate_columns(ons, ONS_REQUIRED_COLUMNS, "My ONS worksheet")
    formulas = validate_product_rows(
        formulas,
        FORMULA_NUMERIC_COLUMNS,
        "My Formulary worksheet",
        optional_numeric_columns=FORMULA_OPTIONAL_NUMERIC_COLUMNS,
        positive_numeric_columns={"kcal_per_mL"},
    )
    modulars = validate_product_rows(
        modulars,
        MODULAR_NUMERIC_COLUMNS,
        "My Modulars worksheet",
        optional_numeric_columns=MODULAR_OPTIONAL_NUMERIC_COLUMNS,
        positive_numeric_columns={"basis_amount"},
    )
    ons = validate_product_rows(
        ons,
        ONS_NUMERIC_COLUMNS,
        "My ONS worksheet",
        optional_numeric_columns=ONS_OPTIONAL_NUMERIC_COLUMNS,
        positive_numeric_columns={"kcal_per_mL", "container_size_ml"},
    )
    if modulars["id"].astype(str).str.strip().replace("nan", "").eq("").any():
        raise ValueError("My Modulars worksheet contains a blank id.")
    if modulars["id"].astype(str).str.strip().str.casefold().duplicated().any():
        raise ValueError("My Modulars worksheet contains duplicate ids.")
    for column in ("id", "product_name", "flavour", "package_unit"):
        if ons[column].astype(str).str.strip().replace("nan", "").eq("").any():
            raise ValueError(f"My ONS worksheet contains a blank {column.replace('_', ' ')}.")
    if ons["id"].astype(str).str.strip().str.casefold().duplicated().any():
        raise ValueError("My ONS worksheet contains duplicate ids.")
    return formulas.fillna(0), modulars.fillna(0), ons.fillna(0)


def export_formulary_workbook(
    formulas: pd.DataFrame,
    modulars: pd.DataFrame,
    ons: pd.DataFrame | None = None,
) -> bytes:
    """Create an Excel workbook containing product data only, never case inputs."""
    if ons is None:
        ons = load_master_ons().iloc[0:0].copy()
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        formulas.to_excel(writer, sheet_name="My Formulary", index=False)
        modulars.to_excel(writer, sheet_name="My Modulars", index=False)
        ons.to_excel(writer, sheet_name="My ONS", index=False)
    return buffer.getvalue()


def import_formulary_workbook(
    uploaded_file,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    workbook = pd.ExcelFile(uploaded_file)
    required_sheets = {"My Formulary", "My Modulars"}
    missing = required_sheets - set(workbook.sheet_names)
    if missing:
        raise ValueError("Workbook must contain sheets named: " + ", ".join(sorted(required_sheets)))
    formulas = pd.read_excel(workbook, sheet_name="My Formulary")
    modulars = pd.read_excel(workbook, sheet_name="My Modulars")
    ons = (
        pd.read_excel(workbook, sheet_name="My ONS")
        if "My ONS" in workbook.sheet_names
        else load_master_ons().iloc[0:0].copy()
    )
    return validate_import(formulas, modulars, ons)
