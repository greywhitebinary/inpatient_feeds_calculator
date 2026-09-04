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
    "name",
    "brand",
    "kcal_per_mL",
    "protein_per_mL",
    "fat_per_mL",
    "carbohydrate_per_mL",
    "fibre_per_mL",
    "sodium_per_mL",
    "potassium_per_mL",
    "calcium_per_mL",
    "magnesium_per_mL",
    "phosphorus_per_mL",
    "free_water_per_mL",
    "source",
    "verified",
}
MODULAR_REQUIRED_COLUMNS = {
    "id",
    "product_type",
    "name",
    "brand",
    "dose_unit",
    "basis_amount",
    "basis_description",
    "kcal_per_basis",
    "protein_g_per_basis",
    "carbohydrate_g_per_basis",
    "fat_g_per_basis",
    "fibre_g_per_basis",
    "free_water_ml_per_basis",
    "preparation_water_rule",
    "source",
    "verified",
    "sodium_mg_per_basis",
    "potassium_mg_per_basis",
    "calcium_mg_per_basis",
    "magnesium_mg_per_basis",
    "phosphorus_mg_per_basis",
}
ONS_REQUIRED_COLUMNS = FORMULA_REQUIRED_COLUMNS | {
    "id",
    "product_name",
    "flavour",
    "container_size_ml",
    "package_unit",
}
ONS_SERVING_COLUMNS = {
    "calculation_basis",
    "serving_size_g",
    "serving_unit",
    "kcal_per_serving",
    "protein_g_per_serving",
    "fat_g_per_serving",
    "carbohydrate_g_per_serving",
    "fibre_g_per_serving",
    "sodium_mg_per_serving",
    "potassium_mg_per_serving",
    "calcium_mg_per_serving",
    "magnesium_mg_per_serving",
    "phosphorus_mg_per_serving",
    "free_water_ml_per_serving",
}

FORMULA_NUMERIC_COLUMNS = {
    "kcal_per_mL",
    "protein_per_mL",
    "fat_per_mL",
    "carbohydrate_per_mL",
    "sodium_per_mL",
    "potassium_per_mL",
    "calcium_per_mL",
    "magnesium_per_mL",
    "phosphorus_per_mL",
    "free_water_per_mL",
}
FORMULA_OPTIONAL_NUMERIC_COLUMNS = {"fibre_per_mL"}
MODULAR_NUMERIC_COLUMNS = {
    "basis_amount",
    "kcal_per_basis",
    "protein_g_per_basis",
    "carbohydrate_g_per_basis",
    "fat_g_per_basis",
    "fibre_g_per_basis",
}
MODULAR_OPTIONAL_NUMERIC_COLUMNS = {
    "sodium_mg_per_basis",
    "potassium_mg_per_basis",
    "calcium_mg_per_basis",
    "magnesium_mg_per_basis",
    "phosphorus_mg_per_basis",
    "free_water_ml_per_basis",
}
ONS_NUMERIC_COLUMNS = FORMULA_NUMERIC_COLUMNS | {
    "container_size_ml",
    "serving_size_g",
    "kcal_per_serving",
    "protein_g_per_serving",
    "fat_g_per_serving",
    "carbohydrate_g_per_serving",
    "fibre_g_per_serving",
    "sodium_mg_per_serving",
    "potassium_mg_per_serving",
    "calcium_mg_per_serving",
    "magnesium_mg_per_serving",
    "phosphorus_mg_per_serving",
    "free_water_ml_per_serving",
}
ONS_OPTIONAL_NUMERIC_COLUMNS = FORMULA_OPTIONAL_NUMERIC_COLUMNS

# Columns where a blank cell means "the manufacturer did not disclose it" rather
# than "the value is zero". These are kept null so the calculation layer can
# report them as undisclosed instead of silently counting them as absent. See
# formula_sources/DATA_CONVENTIONS.md section 1.
#
# Deliberately excludes formula and ONS `fibre_per_mL`. A blank there means the
# panel has no fibre row because the product is fibre-free, which is a declared
# absence, not a missing figure. Marking those undisclosed would raise a flag on
# ten products where nothing is unknown.
UNDISCLOSED_WHEN_BLANK_MODULAR = {
    "sodium_mg_per_basis",
    "potassium_mg_per_basis",
    "calcium_mg_per_basis",
    "magnesium_mg_per_basis",
    "phosphorus_mg_per_basis",
    "free_water_ml_per_basis",
}

# The manufacturer's own statement of the daily volume at which a feed meets the
# Dietary Reference Intakes, and how many micronutrients that claim covers. A
# blank is not a zero: it means the documents we hold make no such claim for
# that product, which is true of every Abbott row. Zero-filling would read as
# "meets the DRI in 0 mL", the opposite of what the blank means.
UNDISCLOSED_WHEN_BLANK_FORMULA = {
    "dri_volume_ml",
    "dri_micronutrients_met",
}

# Free-text provenance columns. `data_note` records why a row holds the value it
# does, where the reason is not obvious from the citation alone: which basis
# column of a self-inconsistent panel was divided, or which conversion factor a
# product's ingredient list dictates. It is maintainer-facing, is displayed
# nowhere, and an empty cell simply means the row needs no explanation, so these
# are filled with an empty string rather than the zero every other column gets.
TEXT_COLUMNS = {"data_note"}


def _fill_zeros_except(frame: pd.DataFrame, keep_null: set[str]) -> pd.DataFrame:
    """Zero-fill every column except those where blank carries meaning."""
    text_columns = [column for column in frame.columns if column in TEXT_COLUMNS]
    if text_columns:
        frame[text_columns] = frame[text_columns].fillna("")
    fill_columns = [
        column
        for column in frame.columns
        if column not in keep_null and column not in TEXT_COLUMNS
    ]
    frame[fill_columns] = frame[fill_columns].fillna(0)
    return frame


def load_master_formulas() -> pd.DataFrame:
    formulas = pd.read_csv(FORMULA_PATH, encoding="utf-8-sig")
    validate_columns(formulas, FORMULA_REQUIRED_COLUMNS, "Master formulary")
    formulas = validate_product_rows(
        formulas,
        FORMULA_NUMERIC_COLUMNS,
        "Master formulary",
        optional_numeric_columns=FORMULA_OPTIONAL_NUMERIC_COLUMNS,
        positive_numeric_columns={"kcal_per_mL"},
    )
    return _fill_zeros_except(formulas, UNDISCLOSED_WHEN_BLANK_FORMULA)


def load_master_modulars() -> pd.DataFrame:
    modulars = pd.read_csv(MODULAR_PATH, encoding="utf-8-sig")
    validate_columns(modulars, MODULAR_REQUIRED_COLUMNS, "Master modulars")
    validated = validate_product_rows(
        modulars,
        MODULAR_NUMERIC_COLUMNS,
        "Master modulars",
        optional_numeric_columns=MODULAR_OPTIONAL_NUMERIC_COLUMNS,
        positive_numeric_columns={"basis_amount"},
    )
    return _fill_zeros_except(validated, UNDISCLOSED_WHEN_BLANK_MODULAR)


def load_master_ons() -> pd.DataFrame:
    ons = pd.read_csv(ONS_PATH, encoding="utf-8-sig")
    validate_columns(ons, ONS_REQUIRED_COLUMNS, "Master ONS")
    ons = _normalise_ons_schema(ons)
    return _fill_zeros_except(_validate_ons_rows(ons, "Master ONS"), set())


def _normalise_ons_schema(frame: pd.DataFrame) -> pd.DataFrame:
    """Add serving-basis fields while keeping older ONS workbooks importable."""
    cleaned = frame.copy()
    if "calculation_basis" not in cleaned:
        cleaned["calculation_basis"] = "container_ml"
    cleaned["calculation_basis"] = cleaned["calculation_basis"].fillna("container_ml")
    if "serving_unit" not in cleaned:
        cleaned["serving_unit"] = ""
    if "serving_size_g" not in cleaned:
        cleaned["serving_size_g"] = 0
    for column in ONS_SERVING_COLUMNS - {
        "calculation_basis",
        "serving_unit",
        "serving_size_g",
    }:
        if column not in cleaned:
            cleaned[column] = 0
    serving_rows = (
        cleaned["calculation_basis"].astype(str).str.strip().str.casefold() == "serving"
    )
    # Serving-based products do not have a liquid container or per-millilitre
    # values. Missing cells in those legacy fields are therefore treated as
    # zero, while any non-numeric value is still rejected by validation.
    for column in FORMULA_NUMERIC_COLUMNS | {"container_size_ml"}:
        if serving_rows.any():
            cleaned.loc[serving_rows, column] = cleaned.loc[
                serving_rows, column
            ].fillna(0)
    if serving_rows.any():
        cleaned.loc[serving_rows, "fibre_per_mL"] = cleaned.loc[
            serving_rows, "fibre_per_mL"
        ].fillna(0)
    return cleaned


def _validate_ons_rows(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    cleaned = validate_product_rows(
        frame,
        ONS_NUMERIC_COLUMNS,
        label,
        optional_numeric_columns=ONS_OPTIONAL_NUMERIC_COLUMNS,
    )
    for column in ("id", "product_name", "flavour", "package_unit"):
        if cleaned[column].astype(str).str.strip().replace("nan", "").eq("").any():
            raise ValueError(f"{label} contains a blank {column.replace('_', ' ')}.")
    if cleaned["id"].astype(str).str.strip().str.casefold().duplicated().any():
        raise ValueError(f"{label} contains duplicate ids.")
    basis = cleaned["calculation_basis"].astype(str).str.strip().str.casefold()
    if (~basis.isin({"container_ml", "serving"})).any():
        raise ValueError(f"{label} has an invalid calculation basis.")
    container_rows = basis == "container_ml"
    if (
        (cleaned.loc[container_rows, "kcal_per_mL"] <= 0)
        | (cleaned.loc[container_rows, "container_size_ml"] <= 0)
    ).any():
        raise ValueError(
            f"{label} requires positive container size and kcal_per_mL for liquid ONS."
        )
    serving_rows = basis == "serving"
    if serving_rows.any():
        if cleaned.loc[serving_rows, "serving_size_g"].le(0).any():
            raise ValueError(
                f"{label} requires a positive serving size for serving-based ONS."
            )
        if cleaned.loc[serving_rows, "kcal_per_serving"].le(0).any():
            raise ValueError(
                f"{label} requires positive kcal_per_serving for serving-based ONS."
            )
        if (
            cleaned.loc[serving_rows, "serving_unit"]
            .astype(str)
            .str.strip()
            .eq("")
            .any()
        ):
            raise ValueError(f"{label} requires a serving unit for serving-based ONS.")
    return cleaned


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
            raise ValueError(
                f"{label} has a blank, non-numeric, or negative value in {column}."
            )
        if column in (positive_numeric_columns or set()) and (converted <= 0).any():
            raise ValueError(f"{label} requires a value greater than zero in {column}.")
        cleaned[column] = converted
    for column in optional_numeric_columns or set():
        raw = cleaned[column]
        converted = pd.to_numeric(raw, errors="coerce")
        has_invalid = raw.notna() & converted.isna()
        if has_invalid.any() or (converted.dropna() < 0).any():
            raise ValueError(
                f"{label} has a blank, non-numeric, or negative value in {column}."
            )
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
    ons = _normalise_ons_schema(ons)
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
    ons = _validate_ons_rows(ons, "My ONS worksheet")
    if modulars["id"].astype(str).str.strip().replace("nan", "").eq("").any():
        raise ValueError("My Modulars worksheet contains a blank id.")
    if modulars["id"].astype(str).str.strip().str.casefold().duplicated().any():
        raise ValueError("My Modulars worksheet contains duplicate ids.")
    return (
        _fill_zeros_except(formulas, UNDISCLOSED_WHEN_BLANK_FORMULA),
        _fill_zeros_except(modulars, UNDISCLOSED_WHEN_BLANK_MODULAR),
        _fill_zeros_except(ons, set()),
    )


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
        raise ValueError(
            "Workbook must contain sheets named: " + ", ".join(sorted(required_sheets))
        )
    formulas = pd.read_excel(workbook, sheet_name="My Formulary")
    modulars = pd.read_excel(workbook, sheet_name="My Modulars")
    ons = (
        pd.read_excel(workbook, sheet_name="My ONS")
        if "My ONS" in workbook.sheet_names
        else load_master_ons().iloc[0:0].copy()
    )
    return validate_import(formulas, modulars, ons)
