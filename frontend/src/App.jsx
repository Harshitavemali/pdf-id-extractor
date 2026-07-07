import { useState } from 'react'
import FileUpload from './components/FileUpload'
import ResultsTable from './components/ResultsTable'
import { extractPdfs } from './services/api'

function App() {
  const [files, setFiles] = useState([])
  const [records, setRecords] = useState([])
  const [fileResults, setFileResults] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [warning, setWarning] = useState('')

  const handleFilesAdd = (newFiles) => {
    const entries = newFiles.map((file) => ({
      id: `${file.name}-${file.size}-${file.lastModified}-${crypto.randomUUID()}`,
      file,
    }))
    setFiles((prev) => [...prev, ...entries])
    setError('')
    // New files haven't been extracted yet - clear any stale status for them.
    setFileResults((prev) => {
      const next = { ...prev }
      for (const file of newFiles) {
        delete next[file.name]
      }
      return next
    })
  }

  const handleRemove = (id) => {
    setFiles((prev) => prev.filter((entry) => entry.id !== id))
  }

  const handleExtract = async () => {
    if (files.length === 0 || loading) return

    setLoading(true)
    setError('')
    setWarning('')

    try {
      const pdfFiles = files.map((entry) => entry.file)
      const { records: extracted, warnings, fileResults: results } =
        await extractPdfs(pdfFiles)
      setRecords(extracted)

      const resultsByName = {}
      for (const result of results) {
        resultsByName[result.pdfName] = result
      }
      setFileResults(resultsByName)

      if (warnings.length > 0) {
        setWarning(warnings.join(' '))
      }
    } catch (err) {
      setRecords([])
      setFileResults({})
      setError(err.message || 'Something went wrong while extracting data.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">
              PDF to Excel Extractor
            </h1>
            <p className="mt-0.5 text-sm text-slate-500">
              Upload PDFs and extract structured data into Excel
            </p>
          </div>
          <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 ring-1 ring-blue-100">
            Dashboard
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Left panel */}
          <section className="flex flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold text-slate-900">
              Upload PDFs
            </h2>

            <FileUpload onFilesAdd={handleFilesAdd} disabled={loading} />

            {Object.keys(fileResults).length > 0 && (() => {
              const results = Object.values(fileResults)
              const succeeded = results.filter((r) => r.success).length
              const failed = results.length - succeeded
              return (
                <div className="mt-4 flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-600">
                  <span className="inline-flex items-center gap-1 text-green-700">
                    ✓ {succeeded} extracted
                  </span>
                  {failed > 0 && (
                    <span className="inline-flex items-center gap-1 text-red-700">
                      ✗ {failed} not extracted
                    </span>
                  )}
                </div>
              )
            })()}

            <div className="mt-5">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-sm font-medium text-slate-700">
                  Uploaded files
                </h3>
                <span className="text-xs text-slate-400">
                  {files.length} {files.length === 1 ? 'file' : 'files'}
                </span>
              </div>

              {files.length === 0 ? (
                <p className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-400">
                  No PDFs uploaded yet
                </p>
              ) : (
                <ul className="max-h-64 space-y-2 overflow-y-auto">
                  {files.map(({ id, file }) => {
                    const result = fileResults[file.name]
                    return (
                      <li
                        key={id}
                        className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5"
                      >
                        <div className="flex min-w-0 items-center gap-2.5">
                          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-red-50 text-xs font-bold text-red-600">
                            PDF
                          </span>
                          <div className="min-w-0">
                            <span
                              className="block truncate text-sm font-medium text-slate-700"
                              title={file.name}
                            >
                              {file.name}
                            </span>
                            {result && (
                              <span
                                className={
                                  result.success
                                    ? 'mt-0.5 inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700 ring-1 ring-green-200'
                                    : 'mt-0.5 inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700 ring-1 ring-red-200'
                                }
                                title={result.message || undefined}
                              >
                                {result.success
                                  ? `✓ Extracted (${result.recordCount})`
                                  : '✗ Not extracted'}
                              </span>
                            )}
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemove(id)}
                          disabled={loading}
                          className="shrink-0 rounded-md px-2.5 py-1 text-xs font-semibold text-red-600 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Remove
                        </button>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          </section>

          {/* Right panel */}
          <ResultsTable records={records} loading={loading} />
        </div>

        {error && (
          <div
            role="alert"
            className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          >
            {error}
          </div>
        )}

        {warning && !error && (
          <div
            role="status"
            className="mt-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"
          >
            Some files could not be processed. {warning}
          </div>
        )}

        {/* Bottom action */}
        <div className="mt-6 flex justify-center">
          <button
            type="button"
            onClick={handleExtract}
            disabled={files.length === 0 || loading}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-8 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500 disabled:shadow-none"
          >
            {loading && (
              <span
                className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
                aria-hidden="true"
              />
            )}
            {loading ? 'Extracting…' : 'Extract Data'}
          </button>
        </div>
      </main>
    </div>
  )
}

export default App
