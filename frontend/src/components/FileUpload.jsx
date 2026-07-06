import { useRef, useState } from 'react'

function FileUpload({ onFilesAdd, disabled = false }) {
  const inputRef = useRef(null)
  const [dragActive, setDragActive] = useState(false)

  const collectPdfs = (fileList) => {
    return Array.from(fileList || []).filter(
      (file) =>
        file.type === 'application/pdf' ||
        file.name.toLowerCase().endsWith('.pdf'),
    )
  }

  const handleFiles = (fileList) => {
    if (disabled) return
    const pdfs = collectPdfs(fileList)
    if (pdfs.length > 0) {
      onFilesAdd(pdfs)
    }
  }

  return (
    <div
      className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
        disabled
          ? 'cursor-not-allowed border-slate-200 bg-slate-50 opacity-60'
          : dragActive
            ? 'border-blue-500 bg-blue-50'
            : 'border-slate-300 bg-slate-50 hover:border-blue-400 hover:bg-blue-50/50'
      }`}
      onDragOver={(event) => {
        event.preventDefault()
        if (!disabled) setDragActive(true)
      }}
      onDragLeave={() => setDragActive(false)}
      onDrop={(event) => {
        event.preventDefault()
        setDragActive(false)
        handleFiles(event.dataTransfer.files)
      }}
    >
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-blue-100 text-blue-600">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.75"
          className="h-6 w-6"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 16V4m0 0 4 4m-4-4-4 4M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"
          />
        </svg>
      </div>

      <p className="text-sm font-medium text-slate-800">
        Drag and drop PDF files here
      </p>
      <p className="mt-1 text-xs text-slate-500">or</p>

      <button
        type="button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        className="mt-3 rounded-lg bg-white px-4 py-2 text-sm font-semibold text-blue-600 shadow-sm ring-1 ring-slate-200 transition hover:bg-blue-50 hover:ring-blue-200 disabled:cursor-not-allowed disabled:opacity-50"
      >
        Choose Files
      </button>

      <input
        ref={inputRef}
        type="file"
        accept=".pdf,application/pdf"
        multiple
        disabled={disabled}
        onChange={(event) => {
          handleFiles(event.target.files)
          event.target.value = ''
        }}
        className="hidden"
      />

      <p className="mt-3 text-xs text-slate-400">PDF files only</p>
    </div>
  )
}

export default FileUpload
