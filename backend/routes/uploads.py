"""
API routes for data file uploads (inventory, prices, sales register)
Files are stored in Google Cloud Storage with folder structure and datetime stamps
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, status
from pydantic import BaseModel
from datetime import datetime
from typing import List
import logging

from backend import gcs

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
        
        return FileUploadResponse(
            success=True,
            gcs_path=gcs_path,
            filename=file.filename,
            upload_type="inventory",
            uploaded_at=datetime.utcnow(),
            message=f"Inventory file '{file.filename}' uploaded successfully"
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
        
        return FileUploadResponse(
            success=True,
            gcs_path=gcs_path,
            filename=file.filename,
            upload_type="prices",
            uploaded_at=datetime.utcnow(),
            message=f"Market prices file '{file.filename}' uploaded successfully"
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
        
        return FileUploadResponse(
            success=True,
            gcs_path=gcs_path,
            filename=file.filename,
            upload_type="sales_register",
            uploaded_at=datetime.utcnow(),
            message=f"Sales register file '{file.filename}' uploaded successfully"
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
