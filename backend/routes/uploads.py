"""
API routes for data file uploads (inventory, prices, sales register)
Files are stored in Google Cloud Storage with folder structure and datetime stamps
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, status
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
import logging
import os
import tempfile

from backend import gcs
from backend.load_stock_report import load_stock_report
from backend.load_market_data import load_market_data_from_excel
from backend.ingestion_feedback import IngestionFeedback

router = APIRouter(prefix="/api/uploads", tags=["uploads"])
logger = logging.getLogger(__name__)

# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class FileUploadResponse(BaseModel):
    """Response after successful file upload"""
    success: bool
    gcs_path: str
    filename: str
    upload_type: str
    uploaded_at: datetime
    message: str
    ingestion: Optional[IngestionFeedback] = None

class FileListResponse(BaseModel):
    """List of uploaded files by type"""
    upload_type: str
    count: int
    files: List[dict]

class UploadSummary(BaseModel):
    """Summary of all uploads"""
    inventory_files: int
    prices_files: int
    sales_register_files: int
    total_files: int


def _infer_report_date_from_filename(file_name: str):
    """Try to infer DD-MM-YYYY date in filename for market data reports."""
    import re
    from datetime import datetime as dt

    if not file_name:
        return None

    match = re.search(r"(\d{1,2})-(\d{1,2})-(\d{4})", file_name)
    if not match:
        return None

    day, month, year = match.groups()
    try:
        return dt(int(year), int(month), int(day)).date()
    except ValueError:
        return None


def _process_uploaded_file(upload_type: str, gcs_path: str, original_filename: str) -> IngestionFeedback:
    """
    Unified workflow: download from GCS, parse, and upsert into destination table.
    
    Returns:
        IngestionFeedback with detailed processing results
    """
    file_bytes = gcs.download_file(gcs_path)
    _, ext = os.path.splitext(original_filename or "")
    suffix = ext if ext else ".bin"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        if upload_type == "inventory":
            if suffix.lower() not in {".csv", ".xlsx", ".xls"}:
                from backend.ingestion_feedback import create_ingestion_feedback
                return create_ingestion_feedback(
                    status="failed",
                    message="Inventory parser supports CSV and Excel (.xlsx/.xls) formats",
                    total_rows=0,
                    source_file=original_filename,
                    destination_table="inventory_detail",
                )

            result = load_stock_report(tmp_path)
            return result

        if upload_type == "prices":
            if suffix.lower() not in {".xlsx", ".xls"}:
                from backend.ingestion_feedback import create_ingestion_feedback
                return create_ingestion_feedback(
                    status="failed",
                    message="Market price parser currently supports Excel (.xlsx/.xls) format only",
                    total_rows=0,
                    source_file=original_filename,
                    destination_table="market_data_hvb",
                )

            report_date = _infer_report_date_from_filename(original_filename)
            result = load_market_data_from_excel(tmp_path, report_date)
            return result

        # Sales-register parser/upsert is not implemented yet.
        from backend.ingestion_feedback import create_ingestion_feedback
        return create_ingestion_feedback(
            status="failed",
            message="Upload stored in GCS; parser/upsert for sales-register is not implemented yet",
            total_rows=0,
            source_file=original_filename,
            destination_table=None,
        )
    
    except Exception as exc:
        from backend.ingestion_feedback import create_ingestion_feedback
        return create_ingestion_feedback(
            status="failed",
            message=f"Ingestion failed: {str(exc)}",
            total_rows=0,
            errors=[str(exc)],
            source_file=original_filename,
            destination_table=None,
        )
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

# ============================================================================
# INVENTORY UPLOADS
# ============================================================================

@router.post("/inventory", response_model=FileUploadResponse)
async def upload_inventory(file: UploadFile = File(...)):
    """
    Upload inventory data file.
    Stores in GCS at: uploads/inventory/{timestamp}_{filename}
    
    Supported formats: .xlsx, .csv
    """
    try:
        # Validate file extension
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided"
            )
        
        valid_extensions = {'.xlsx', '.csv', '.xls'}
        file_ext = '.' + file.filename.split('.')[-1].lower()
        
        if file_ext not in valid_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Supported: {valid_extensions}"
            )
        
        # Read file into memory
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )
        
        # Upload to GCS
        gcs_path = gcs.upload_inventory_file(file_bytes, file.filename)
        
        logger.info(f"Inventory file uploaded: {gcs_path}")
        
        ingestion_result = _process_uploaded_file("inventory", gcs_path, file.filename)

        return FileUploadResponse(
            success=True,
            gcs_path=gcs_path,
            filename=file.filename,
            upload_type="inventory",
            uploaded_at=datetime.utcnow(),
            message=f"Inventory file '{file.filename}' uploaded and processed successfully",
            ingestion=ingestion_result,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading inventory file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.get("/inventory", response_model=FileListResponse)
async def list_inventory_files():
    """Get list of all uploaded inventory files"""
    try:
        files = gcs.list_inventory_files()
        return FileListResponse(
            upload_type="inventory",
            count=len(files),
            files=files
        )
    except Exception as e:
        logger.error(f"Error listing inventory files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}"
        )


# ============================================================================
# PRICES UPLOADS
# ============================================================================

@router.post("/prices", response_model=FileUploadResponse)
async def upload_prices(file: UploadFile = File(...)):
    """
    Upload market prices data file.
    Stores in GCS at: uploads/prices/{timestamp}_{filename}
    
    Supported formats: .xlsx, .csv
    """
    try:
        # Validate file extension
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided"
            )
        
        valid_extensions = {'.xlsx', '.csv', '.xls'}
        file_ext = '.' + file.filename.split('.')[-1].lower()
        
        if file_ext not in valid_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Supported: {valid_extensions}"
            )
        
        # Read file into memory
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )
        
        # Upload to GCS
        gcs_path = gcs.upload_prices_file(file_bytes, file.filename)
        
        logger.info(f"Prices file uploaded: {gcs_path}")
        
        ingestion_result = _process_uploaded_file("prices", gcs_path, file.filename)

        return FileUploadResponse(
            success=True,
            gcs_path=gcs_path,
            filename=file.filename,
            upload_type="prices",
            uploaded_at=datetime.utcnow(),
            message=f"Market prices file '{file.filename}' uploaded and processed successfully",
            ingestion=ingestion_result,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading prices file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.get("/prices", response_model=FileListResponse)
async def list_prices_files():
    """Get list of all uploaded prices files"""
    try:
        files = gcs.list_prices_files()
        return FileListResponse(
            upload_type="prices",
            count=len(files),
            files=files
        )
    except Exception as e:
        logger.error(f"Error listing prices files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}"
        )


# ============================================================================
# SALES REGISTER UPLOADS
# ============================================================================

@router.post("/sales-register", response_model=FileUploadResponse)
async def upload_sales_register(file: UploadFile = File(...)):
    """
    Upload sales register data file.
    Stores in GCS at: uploads/sales_register/{timestamp}_{filename}
    
    Supported formats: .xlsx, .csv
    """
    try:
        # Validate file extension
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided"
            )
        
        valid_extensions = {'.xlsx', '.csv', '.xls'}
        file_ext = '.' + file.filename.split('.')[-1].lower()
        
        if file_ext not in valid_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Supported: {valid_extensions}"
            )
        
        # Read file into memory
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )
        
        # Upload to GCS
        gcs_path = gcs.upload_sales_register_file(file_bytes, file.filename)
        
        logger.info(f"Sales register file uploaded: {gcs_path}")
        
        ingestion_result = _process_uploaded_file("sales_register", gcs_path, file.filename)

        return FileUploadResponse(
            success=True,
            gcs_path=gcs_path,
            filename=file.filename,
            upload_type="sales_register",
            uploaded_at=datetime.utcnow(),
            message=f"Sales register file '{file.filename}' uploaded successfully",
            ingestion=ingestion_result,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading sales register file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.get("/sales-register", response_model=FileListResponse)
async def list_sales_register_files():
    """Get list of all uploaded sales register files"""
    try:
        files = gcs.list_sales_register_files()
        return FileListResponse(
            upload_type="sales_register",
            count=len(files),
            files=files
        )
    except Exception as e:
        logger.error(f"Error listing sales register files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}"
        )


# ============================================================================
# SUMMARY ENDPOINTS
# ============================================================================

@router.get("/summary", response_model=UploadSummary)
async def get_uploads_summary():
    """Get summary of all uploaded files by type"""
    try:
        inventory = gcs.list_inventory_files()
        prices = gcs.list_prices_files()
        sales = gcs.list_sales_register_files()
        
        return UploadSummary(
            inventory_files=len(inventory),
            prices_files=len(prices),
            sales_register_files=len(sales),
            total_files=len(inventory) + len(prices) + len(sales)
        )
    except Exception as e:
        logger.error(f"Error getting uploads summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get summary: {str(e)}"
        )
