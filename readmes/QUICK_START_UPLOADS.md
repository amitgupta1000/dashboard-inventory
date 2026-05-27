# 🚀 Upload System - Quick Start Guide

## For Users (Frontend)

### How to Upload a File

#### 1. Click Upload Button
- Find the **blue upload button** in the top header bar
- Click it to open the **Data Management** panel

#### 2. Choose Upload Type
The panel shows 3 upload options:

**📤 Upload Inventory**
- Daily stock levels by commodity
- Accepted formats: `.xlsx`, `.csv`, `.xls`
- Example: `12-5-26.xlsx`

**🎯 Upload Market Prices**
- Current prices & replacement costs
- Accepted formats: `.xlsx`, `.csv`, `.xls`
- Example: `prices_2026-05-25.csv`

**📊 Upload Sales Register**
- Recent sales transactions
- Accepted formats: `.xlsx`, `.csv`, `.xls`
- Example: `sales_register_May.xlsx`

#### 3. Select File
- Click the button for your file type
- A file picker will open
- Select your `.xlsx`, `.csv`, or `.xls` file
- Click "Open"

#### 4. Watch Upload Progress
- Status changes to: **"Uploading filename.xlsx..."**
- Shows a loading spinner
- Do NOT close the browser tab

#### 5. Confirm Upload
- Status changes to: **"✓ File uploaded successfully!"** (Green)
- Auto-closes after 3 seconds
- File now appears in "Recent Files" section

#### 6. Check Recent Files
- Scroll down in the upload panel
- See last 3 uploaded files
- Each shows the timestamp it was uploaded

---

## For Developers (Backend/API)

### API Endpoints

#### Upload a File
```bash
curl -X POST \
  -H "Content-Type: multipart/form-data" \
  -F "file=@inventory.xlsx" \
  http://localhost:8000/api/uploads/inventory

# Response:
{
  "success": true,
  "gcs_path": "uploads/inventory/2026-05-25T14-30-45_inventory.xlsx",
  "filename": "inventory.xlsx",
  "upload_type": "inventory",
  "uploaded_at": "2026-05-25T14:30:45.123456",
  "message": "Inventory file 'inventory.xlsx' uploaded successfully"
}
```

#### List Uploaded Files
```bash
# Get all inventory uploads
curl http://localhost:8000/api/uploads/inventory

# Get all prices uploads
curl http://localhost:8000/api/uploads/prices

# Get all sales register uploads
curl http://localhost:8000/api/uploads/sales-register

# Response:
{
  "upload_type": "inventory",
  "count": 5,
  "files": [
    {
      "gcs_path": "uploads/inventory/2026-05-25T14-30-45_data.xlsx",
      "filename": "2026-05-25T14-30-45_data.xlsx",
      "uploaded_at": "2026-05-25T14:30:45.123456Z"
    }
  ]
}
```

#### Get Summary
```bash
curl http://localhost:8000/api/uploads/summary

# Response:
{
  "inventory_files": 5,
  "prices_files": 3,
  "sales_register_files": 2,
  "total_files": 10
}
```

---

## Setting Up Locally

### 1. Backend Setup

#### Install Requirements
```bash
cd backend
pip install -r requirements.txt
```

#### Configure Environment
Create `.env` file in `backend/` directory:
```env
# Google Cloud Storage
GCS_BUCKET_NAME=dashboard-inventory
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Local development
USE_SQLITE=true
```

#### Get GCS Credentials
1. Go to Google Cloud Console
2. Create a service account with Storage permissions
3. Generate JSON key
4. Save to a secure location
5. Update GOOGLE_APPLICATION_CREDENTIALS path

#### Start API Server
```bash
cd c:\dashboard-inventory
python main.py

# You should see:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# Open http://localhost:8000/docs to see all endpoints
```

### 2. Frontend Setup

#### Install Dependencies
```bash
cd frontend
npm install
```

#### Start Development Server
```bash
npm run dev

# You should see:
# ➜  Local:   http://localhost:5173/
# Open browser and navigate to this URL
```

### 3. Test the System

#### Via Frontend
1. Open http://localhost:5173/
2. Click the blue upload button in the header
3. Select a file and upload
4. Watch the success notification

#### Via API
```bash
# In PowerShell
Invoke-WebRequest -Method GET -Uri http://localhost:8000/api/uploads/summary
```

---

## File Organization in GCS

After uploading files, they're stored in Google Cloud Storage like this:

```
dashboard-inventory/
├── uploads/
│   ├── inventory/
│   │   └── 2026-05-25T14-30-45_inventory.xlsx     ← Your files here
│   │
│   ├── prices/
│   │   └── 2026-05-25T14-32-10_prices.csv         ← Your files here
│   │
│   └── sales_register/
│       └── 2026-05-25T15-45-30_sales.xlsx         ← Your files here
```

**Naming Format:**
- `{YYYY-MM-DDTHH-MM-SS}_{original_filename}`
- Example: `2026-05-25T14-30-45_inventory.xlsx`
- Timestamp prevents file conflicts

---

## Troubleshooting

### Upload Button Not Visible
**Problem:** Can't see the blue upload button in the header
- ✅ Make sure you're on the correct page
- ✅ Try refreshing the browser (F5)
- ✅ Check browser console for errors (F12)

### File Not Uploading
**Problem:** Upload gets stuck on "Uploading..."
- ✅ Check file size (should be <100MB)
- ✅ Check file format (.xlsx, .csv, .xls only)
- ✅ Check internet connection
- ✅ Check browser console for error message

### "Invalid file type" Error
**Problem:** Getting error after selecting file
- ✅ File must be one of: `.xlsx`, `.csv`, `.xls`
- ✅ Rename the file if extension is wrong
- ✅ Use Excel or Google Sheets to save in correct format

### "Upload failed" Error
**Problem:** Getting server error
- ✅ Check if API server is running (`python main.py`)
- ✅ Check GCS credentials are valid
- ✅ Check GOOGLE_APPLICATION_CREDENTIALS path
- ✅ Check GCS bucket exists and is accessible

### No Success Notification
**Problem:** Upload completes but no confirmation appears
- ✅ Check browser network tab (F12 → Network)
- ✅ Look for 200 status code on upload request
- ✅ Check if response contains success: true

---

## Common Tasks

### Retrieve Files from GCS

#### Using Python
```python
from backend import gcs

# List all inventory uploads
files = gcs.list_inventory_files()
for file in files:
    print(file['gcs_path'])  # uploads/inventory/2026-05-25T14-30-45_file.xlsx

# Download a file
file_bytes = gcs.download_file('uploads/inventory/2026-05-25T14-30-45_file.xlsx')
```

#### Using Google Cloud CLI
```bash
# List files
gsutil ls gs://dashboard-inventory/uploads/inventory/

# Download a file
gsutil cp gs://dashboard-inventory/uploads/inventory/2026-05-25T14-30-45_file.xlsx ./

# View file contents (for text/CSV)
gsutil cat gs://dashboard-inventory/uploads/inventory/2026-05-25T14-30-45_file.csv
```

### Monitor Uploads
```bash
# Watch upload history
curl http://localhost:8000/api/uploads/summary | python -m json.tool

# Get detailed file list
curl http://localhost:8000/api/uploads/inventory | python -m json.tool
```

---

## Performance Tips

### Optimize Upload Speed
- **Use WiFi** instead of mobile data
- **Smaller files** upload faster
- **Close other apps** to free up bandwidth

### File Size Guidelines
- **Small:** < 5MB (instant)
- **Medium:** 5-50MB (< 10 seconds)
- **Large:** 50-500MB (< 1 minute)
- **Very Large:** > 500MB (contact support)

### Best Practices
- ✅ Upload during off-peak hours
- ✅ Keep file names short and descriptive
- ✅ Use consistent date formats
- ✅ Validate file contents before uploading

---

## Security Notes

### For Administrators
- 🔒 Credentials are read-only files
- 🔒 Service account has minimal permissions
- 🔒 Files stored in private GCS bucket
- ⚠️ Add authentication layer for production

### For End Users
- ✅ Don't share upload links with unauthorized users
- ✅ Verify file contents before uploading
- ✅ Report suspicious errors to IT

---

## Next Steps After Upload

Once files are uploaded:

1. **Parser reads the file** from GCS
2. **Data is validated** and cleaned
3. **Records are created** in database
4. **Insights are generated** automatically
5. **Dashboard updates** with new data

---

## Support

### Getting Help
- **API Errors:** Check browser console (F12)
- **Upload Errors:** Check API logs (`python main.py` terminal)
- **GCS Issues:** Check Google Cloud Console
- **Questions:** See UPLOAD_TECHNICAL_DOCS.md

### Contact
- Backend Issues: Check `main.py` logs
- Frontend Issues: Check browser console
- GCS Issues: Check service account permissions

---

## Quick Reference

| Task | Command/Action |
|------|---|
| Start API | `python main.py` |
| Start Frontend | `npm run dev` |
| Upload file | Click blue button → Select file |
| List uploads | `curl http://localhost:8000/api/uploads/summary` |
| Check health | `curl http://localhost:8000/api/uploads/summary` |
| View API docs | Open http://localhost:8000/docs |
| View dashboard | Open http://localhost:5173/ |

---

**Last Updated:** 2026-05-25  
**Status:** ✅ Ready for Use
