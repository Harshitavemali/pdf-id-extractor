import { useState } from 'react'
import { downloadRecordsAsExcel } from '../services/api'

const COLUMNS = [
  { key: 'sNo', label: 'S.No' },
  { key: 'name', label: 'Name' },
  { key: 'address', label: 'Address' },
  { key: 'aadhaarNumber', label: 'Aadhaar No' },
  { key: 'dlNumber', label: 'DL No' },
  { key: 'phoneNumber', label: 'Phone No' },
  { key: 'stand', label: 'Stand' },
  { key: 'slNo', label: 'SL No' },
  { key: 'pdfName', label: 'PDF File Name' },
]

function ResultsTable({ records, loading = false }) {
  const hasRecords = records.length > 0
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState('')

  const handleDownload = async () => {
    if (!hasRecords || downloading) return

    setDownloading(true)
    setDownloadError('')
    try {
      await downloadRecordsAsExcel(records)
    } catch (error) {
      setDownloadError(error.message || 'Failed to download Excel.')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <section className="relative flex min-h-[28rem] flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">
          Extracted Records
        </h2>
        <span className="text-xs text-slate-400">
          {records.length} {records.length === 1 ? 'record' : 'records'}
        </span>
      </div>

      <div className="relative min-h-0 flex-1 overflow-hidden rounded-xl border border-slate-200">
        {loading && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-white/80 backdrop-blur-[1px]">
            <span
              className="h-8 w-8 animate-spin rounded-full border-2 border-blue-200 border-t-blue-600"
              aria-hidden="true"
            />
            <p className="text-sm font-medium text-slate-600">
              Extracting data…
            </p>
          </div>
        )}

        <div className="h-full max-h-[22rem] overflow-auto">
          <table className="min-w-full border-collapse text-left text-sm">
            <thead className="sticky top-0 bg-slate-50">
              <tr>
                {COLUMNS.map((column) => (
                  <th
                    key={column.key}
                    className="whitespace-nowrap border-b border-slate-200 px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-slate-500"
                  >
                    {column.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {hasRecords ? (
                records.map((record, index) => (
                  <tr
                    key={record.id ?? index}
                    className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50/80"
                  >
                    {COLUMNS.map((column) => {
                      const value =
                        column.key === 'sNo'
                          ? String(index + 1)
                          : record[column.key] || ''
                      return (
                        <td
                          key={column.key}
                          className="max-w-[12rem] truncate whitespace-nowrap px-3 py-2.5 text-slate-700"
                          title={value}
                        >
                          {value || '—'}
                        </td>
                      )
                    })}
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    colSpan={COLUMNS.length}
                    className="px-3 py-16 text-center text-sm text-slate-400"
                  >
                    No records extracted.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {downloadError && (
        <p className="mt-3 text-sm text-red-600">{downloadError}</p>
      )}

      <div className="mt-4 flex justify-end">
        <button
          type="button"
          disabled={!hasRecords || loading || downloading}
          onClick={handleDownload}
          className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500 disabled:shadow-none"
        >
          {downloading && (
            <span
              className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
              aria-hidden="true"
            />
          )}
          {downloading ? 'Downloading…' : 'Download Excel'}
        </button>
      </div>
    </section>
  )
}

export default ResultsTable
