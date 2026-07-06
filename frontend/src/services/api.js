const API_BASE = import.meta.env.VITE_API_URL || ''

function friendlyError(detail, status) {
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => {
      const field = Array.isArray(item.loc) ? item.loc.slice(-1)[0] : null
      if (item.msg === 'Field required' && field) {
        return `Missing form field "${field}".`
      }
      return item.msg || JSON.stringify(item)
    })
    return messages.join(' ')
  }
  if (status === 422) {
    return 'No ID card records could be extracted from the uploaded PDFs.'
  }
  if (status === 413) {
    return 'One or more files are too large to upload.'
  }
  if (status >= 500) {
    return 'The server encountered an error. Please try again.'
  }
  return 'Extraction failed. Please try again.'
}

async function readErrorMessage(response) {
  try {
    const error = await response.json()
    return friendlyError(error.detail, response.status)
  } catch {
    return friendlyError(null, response.status)
  }
}

function mapRecord(record, index) {
  return {
    id: `${record.pdf_name || 'pdf'}-${index}-${crypto.randomUUID()}`,
    name: record.name || '',
    address: record.address || '',
    aadhaarNumber: record.aadhaar || '',
    dlNumber: record.dl_number || '',
    phoneNumber: record.phone || '',
    stand: record.stand || '',
    slNo: record.sl_no || '',
    pdfName: record.pdf_name || '',
  }
}

function toApiRecord(record) {
  return {
    name: record.name || '',
    address: record.address || '',
    aadhaar: record.aadhaarNumber || '',
    dl_number: record.dlNumber || '',
    phone: record.phoneNumber || '',
    stand: record.stand || '',
    sl_no: record.slNo || '',
    pdf_name: record.pdfName || '',
  }
}

/**
 * Upload one or more PDFs to POST /api/extract.
 * @param {File[]} files
 * @returns {Promise<{ records: object[], warnings: string[] }>}
 */
export async function extractPdfs(files) {
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }

  let response
  try {
    response = await fetch(`${API_BASE}/api/extract`, {
      method: 'POST',
      body: formData,
    })
  } catch {
    throw new Error(
      'Unable to reach the server. Make sure the backend is running.',
    )
  }

  if (!response.ok) {
    throw new Error(await readErrorMessage(response))
  }

  const data = await response.json()

  if (!data?.success || !Array.isArray(data.records)) {
    throw new Error('Unexpected response from the server.')
  }

  return {
    records: data.records.map(mapRecord),
    warnings: [],
  }
}

/**
 * Download Drivers.xlsx from POST /api/download-excel.
 * @param {object[]} records
 */
export async function downloadRecordsAsExcel(records) {
  let response
  try {
    response = await fetch(`${API_BASE}/api/download-excel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ records: records.map(toApiRecord) }),
    })
  } catch {
    throw new Error(
      'Unable to reach the server. Make sure the backend is running.',
    )
  }

  if (!response.ok) {
    throw new Error(await readErrorMessage(response))
  }

  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'Drivers.xlsx'
  link.click()
  URL.revokeObjectURL(url)
}
