"""
Ingestion feedback and schema validation utilities.

Provides detailed feedback about data ingestion including:
- Success/failure status
- Row counts (processed, inserted, updated, failed)
- Commodity matches
- Schema validation (expected columns, missing columns, unrecognized columns)
- Error tracking with first N errors
"""

from typing import List, Dict, Any, Set, Tuple
from pydantic import BaseModel


class ColumnValidation(BaseModel):
    """Schema validation result for a single column"""
    expected_name: str
    actual_name: str | None
    matched: bool
    is_alias: bool = False
    alias_used: str | None = None


class SchemaValidation(BaseModel):
    """Complete schema validation results"""
    expected_columns: List[str]
    actual_columns: List[str]
    matched_columns: List[ColumnValidation]
    missing_columns: List[str]
    unrecognized_columns: List[str]
    match_percentage: float  # % of expected columns found


class CommodityMatch(BaseModel):
    """Commodity matching feedback"""
    total_rows: int
    matched_commodities: int
    unmatched_commodities: int
    match_percentage: float
    unmatched_samples: List[str]  # First 5 unmatched product names


class IngestionFeedback(BaseModel):
    """Complete ingestion feedback response"""
    status: str  # "success", "partial_success", "failed"
    message: str
    
    # Row counts
    total_rows: int
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_failed: int = 0
    
    # Commodity matching
    commodity_match: CommodityMatch | None = None
    
    # Schema validation
    schema_validation: SchemaValidation | None = None
    
    # Errors
    error_messages: List[str] = []  # First 10 errors
    
    # Metadata
    report_date: str | None = None
    source_file: str | None = None
    destination_table: str | None = None


def validate_schema(
    expected_columns: List[str],
    actual_columns: List[str],
    column_aliases: Dict[str, Set[str]] | None = None,
) -> SchemaValidation:
    """
    Validate schema by comparing expected and actual columns.
    
    Args:
        expected_columns: List of required column names
        actual_columns: List of columns found in the file
        column_aliases: Mapping of {canonical_name: {alias1, alias2, ...}}
    
    Returns:
        SchemaValidation with details about matches and mismatches
    """
    if column_aliases is None:
        column_aliases = {}
    
    actual_normalized = {col.lower().strip(): col for col in actual_columns}
    matched = []
    missing = []
    
    for expected in expected_columns:
        expected_lower = expected.lower().strip()
        
        # Try exact match first
        if expected_lower in actual_normalized:
            matched.append(ColumnValidation(
                expected_name=expected,
                actual_name=actual_normalized[expected_lower],
                matched=True,
                is_alias=False,
            ))
        # Try alias match
        elif expected in column_aliases:
            found = False
            for alias in column_aliases[expected]:
                alias_lower = alias.lower().strip()
                if alias_lower in actual_normalized:
                    matched.append(ColumnValidation(
                        expected_name=expected,
                        actual_name=actual_normalized[alias_lower],
                        matched=True,
                        is_alias=True,
                        alias_used=alias,
                    ))
                    found = True
                    break
            if not found:
                missing.append(expected)
        else:
            missing.append(expected)
    
    # Find unrecognized columns
    recognized = {col.lower() for col in expected_columns}
    for aliases in column_aliases.values():
        recognized.update(alias.lower() for alias in aliases)
    
    unrecognized = [
        col for col in actual_columns 
        if col.lower() not in recognized
    ]
    
    match_percentage = (len(matched) / len(expected_columns) * 100) if expected_columns else 0
    
    return SchemaValidation(
        expected_columns=expected_columns,
        actual_columns=actual_columns,
        matched_columns=matched,
        missing_columns=missing,
        unrecognized_columns=unrecognized,
        match_percentage=round(match_percentage, 1),
    )


def create_commodity_match_feedback(
    total_rows: int,
    matched_count: int,
    unmatched_products: List[str] = None,
) -> CommodityMatch:
    """
    Create commodity matching feedback.
    
    Args:
        total_rows: Total rows processed
        matched_count: Number of products matched to commodities
        unmatched_products: List of products that couldn't be matched
    
    Returns:
        CommodityMatch feedback object
    """
    if unmatched_products is None:
        unmatched_products = []
    
    unmatched_count = total_rows - matched_count
    match_percentage = (matched_count / total_rows * 100) if total_rows > 0 else 0
    
    # Sample first 5 unmatched
    samples = list(set(unmatched_products))[:5]
    
    return CommodityMatch(
        total_rows=total_rows,
        matched_commodities=matched_count,
        unmatched_commodities=unmatched_count,
        match_percentage=round(match_percentage, 1),
        unmatched_samples=samples,
    )


def create_ingestion_feedback(
    status: str,
    message: str,
    total_rows: int,
    inserted: int = 0,
    updated: int = 0,
    failed: int = 0,
    commodity_match: CommodityMatch | None = None,
    schema_validation: SchemaValidation | None = None,
    errors: List[str] | None = None,
    report_date: str | None = None,
    source_file: str | None = None,
    destination_table: str | None = None,
) -> IngestionFeedback:
    """
    Create complete ingestion feedback response.
    
    Args:
        status: "success", "partial_success", or "failed"
        message: User-friendly message
        total_rows: Total rows processed
        inserted: Rows inserted
        updated: Rows updated
        failed: Rows failed
        commodity_match: Commodity matching feedback
        schema_validation: Schema validation results
        errors: List of error messages (first 10 will be included)
        report_date: Date for the report
        source_file: Name of source file
        destination_table: Name of destination table
    
    Returns:
        IngestionFeedback object
    """
    if errors is None:
        errors = []
    
    return IngestionFeedback(
        status=status,
        message=message,
        total_rows=total_rows,
        rows_inserted=inserted,
        rows_updated=updated,
        rows_failed=failed,
        commodity_match=commodity_match,
        schema_validation=schema_validation,
        error_messages=errors[:10],  # Limit to first 10
        report_date=report_date,
        source_file=source_file,
        destination_table=destination_table,
    )
