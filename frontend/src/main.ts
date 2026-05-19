import './style.css'

const API = 'http://localhost:8000'
const PASSWORD = '12345'

// ── DOM ──────────────────────────────────────────────────────────────────────
document.querySelector<HTMLDivElement>('#app')!.innerHTML = `
  <header class="inv-header">
    <h1 class="inv-title">Crystal Inventory Dashboard</h1>
    <button id="toggle-data" class="btn-toggle">&#9776; View Data</button>
  </header>

  <div id="data-panel" class="data-panel hidden">
    <div class="panel-toolbar">
      <span class="toolbar-label">Latest inventory snapshot</span>
      <div class="toolbar-actions">
        <label class="btn btn-upload" title="Password protected">
          &#8593; Upload Excel
          <input type="file" id="file-input" accept=".xlsx,.xls" hidden />
        </label>
        <button id="btn-refresh" class="btn btn-refresh" title="Password protected">
          &#8635; Refresh
        </button>
        <span id="status-msg" class="status-msg"></span>
      </div>
    </div>
    <div id="table-container" class="table-container">
      <p class="panel-hint">Loading…</p>
    </div>
  </div>
`

// ── Elements ─────────────────────────────────────────────────────────────────
const toggleBtn    = document.getElementById('toggle-data')!
const dataPanel    = document.getElementById('data-panel')!
const tableContainer = document.getElementById('table-container')!
const fileInput    = document.getElementById('file-input') as HTMLInputElement
const btnRefresh   = document.getElementById('btn-refresh')!
const statusMsg    = document.getElementById('status-msg')!

let panelOpen  = false
let dataLoaded = false

// ── Toggle panel ─────────────────────────────────────────────────────────────
toggleBtn.addEventListener('click', () => {
  panelOpen = !panelOpen
  dataPanel.classList.toggle('hidden', !panelOpen)
  toggleBtn.textContent = panelOpen ? '✕ Close' : '☰ View Data'
  if (panelOpen && !dataLoaded) loadData()
})

// ── Load table ───────────────────────────────────────────────────────────────
async function loadData() {
  tableContainer.innerHTML = '<p class="panel-hint">Loading…</p>'
  try {
    const res  = await fetch(`${API}/api/inventory`)
    const json = await res.json()
    renderTable(json.data ?? [])
    dataLoaded = true
  } catch {
    tableContainer.innerHTML = '<p class="panel-error">Could not reach the backend. Is it running?</p>'
  }
}

function renderTable(rows: Record<string, unknown>[]) {
  if (!rows.length) {
    tableContainer.innerHTML = '<p class="panel-hint">No data in the database yet. Upload a file to get started.</p>'
    return
  }
  const cols = Object.keys(rows[0]).filter(k => k !== 'id')
  const thead = `<tr>${cols.map(c => `<th>${c.replace(/_/g, ' ')}</th>`).join('')}</tr>`
  const tbody = rows.map(row =>
    `<tr>${cols.map(c => {
      const val = row[c] ?? ''
      if (c === 'status') {
        const cls = String(val).toLowerCase()
        return `<td><span class="badge badge-${cls}">${val}</span></td>`
      }
      return `<td>${val}</td>`
    }).join('')}</tr>`
  ).join('')
  tableContainer.innerHTML =
    `<div class="table-scroll"><table><thead>${thead}</thead><tbody>${tbody}</tbody></table></div>`
}

// ── Upload ───────────────────────────────────────────────────────────────────
fileInput.addEventListener('change', async () => {
  const file = fileInput.files?.[0]
  if (!file) return
  if (!checkPassword()) { fileInput.value = ''; return }

  setStatus('Uploading…', 'info')
  const form = new FormData()
  form.append('file', file)
  try {
    const res  = await fetch(`${API}/api/upload`, { method: 'POST', body: form })
    const json = await res.json()
    json.success
      ? setStatus(`Uploaded: ${json.filename}`, 'ok')
      : setStatus(`Upload failed: ${json.detail}`, 'error')
  } catch {
    setStatus('Upload failed — backend unreachable.', 'error')
  }
  fileInput.value = ''
})

// ── Refresh ──────────────────────────────────────────────────────────────────
btnRefresh.addEventListener('click', async () => {
  if (!checkPassword()) return
  setStatus('Refreshing…', 'info')
  try {
    const res  = await fetch(`${API}/api/refresh`, { method: 'POST' })
    const json = await res.json()
    if (json.success) {
      const n = json.imported.length
      setStatus(n ? `Imported ${n} new file(s). Reloading…` : 'No new files found.', 'ok')
      if (n) { dataLoaded = false; await loadData() }
    }
  } catch {
    setStatus('Refresh failed — backend unreachable.', 'error')
  }
})

// ── Helpers ──────────────────────────────────────────────────────────────────
function checkPassword(): boolean {
  const input = window.prompt('Enter password to continue:')
  if (input === PASSWORD) return true
  if (input !== null) alert('Incorrect password.')
  return false
}

function setStatus(msg: string, type: 'info' | 'ok' | 'error') {
  statusMsg.textContent = msg
  statusMsg.className   = `status-msg status-${type}`
  if (type !== 'info') setTimeout(() => { statusMsg.textContent = ''; statusMsg.className = 'status-msg' }, 4000)
}
