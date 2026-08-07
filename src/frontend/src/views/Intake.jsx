import { useCallback, useEffect, useRef, useState } from 'react';
import Icon from '../components/Icon';
import { Chip } from '../components/Chip';
import { api, runtime } from '../lib/api';

/**
 * Where a batch starts: drop documents in, choose which to run, process them.
 *
 * The daily scheduled run processes the whole inbox unattended. This view is
 * the manual path - a clerk dropping today's post on the pile, or re-running
 * one invoice after a correction in SAP.
 */

const kb = (bytes) => `${(bytes / 1024).toFixed(0)} KB`;

export default function Intake({ onProcessed, busy }) {
  const [files, setFiles] = useState(null);
  const [selected, setSelected] = useState(() => new Set());
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [notice, setNotice] = useState(null);
  const inputRef = useRef(null);

  const load = useCallback(async () => {
    const list = await api.inbox();
    setFiles(list);
    // Default to whatever has not been through a batch yet - the common case
    // is "process what just arrived", not "process everything again".
    const fresh = list.filter((f) => !f.processed).map((f) => f.name);
    setSelected(new Set(fresh.length ? fresh : list.map((f) => f.name)));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function upload(fileList) {
    const pdfs = [...fileList].filter((f) => f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf'));
    const skipped = [...fileList].length - pdfs.length;
    if (!pdfs.length) {
      setNotice({ tone: 'error', text: 'Those are not PDFs. Invoices must be PDF documents.' });
      return;
    }
    setUploading(true);
    setNotice(null);
    try {
      const result = await api.upload(pdfs);
      await load();
      setSelected(new Set(result.saved));
      const rejected = result.rejected?.length || 0;
      setNotice({
        tone: rejected || skipped ? 'warn' : 'success',
        text:
          `Added ${result.saved.length} invoice${result.saved.length === 1 ? '' : 's'}.` +
          (rejected + skipped ? ` ${rejected + skipped} skipped - not a readable PDF.` : ''),
      });
    } catch (err) {
      setNotice({ tone: 'error', text: err.message });
    }
    setUploading(false);
  }

  function toggle(name) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  const allSelected = files && files.length > 0 && selected.size === files.length;

  return (
    <div className="view view-intake">
      <div className="intake-left">
        <div
          className={`dropzone ${dragging ? 'is-dragging' : ''}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            upload(e.dataTransfer.files);
          }}
        >
          <Icon name="download" size={28} className="dropzone-icon" />
          <p className="t-title">Drop invoices here</p>
          <p className="t-body-sm t-muted">PDF documents, any number at once</p>
          <button
            className="btn btn-outlined"
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            type="button"
          >
            {uploading ? <span className="spinner" /> : <Icon name="doc" size={14} />}
            {uploading ? 'Adding' : 'Choose files'}
          </button>
          <input
            ref={inputRef}
            className="sr-only"
            type="file"
            accept="application/pdf,.pdf"
            multiple
            onChange={(e) => {
              upload(e.target.files);
              e.target.value = '';
            }}
          />
        </div>

        {notice ? (
          <p className={`notice notice-${notice.tone}`} role="status">
            <Icon name={notice.tone === 'success' ? 'check' : notice.tone === 'warn' ? 'warning' : 'error'} size={14} />
            {notice.text}
          </p>
        ) : null}

        <div className="panel intake-about">
          <div className="panel-head">
            <Icon name="info" size={16} />
            <span className="t-title">How a batch runs</span>
          </div>
          <ol className="intake-steps">
            <li>Every selected document is read and its fields mapped to SAP.</li>
            <li>Each invoice is checked against live purchase order and goods receipt data.</li>
            <li>Passing invoices go to Approvals; the rest go to Exceptions with the reason.</li>
            <li>Nothing is written to SAP until you approve.</li>
          </ol>
        </div>
      </div>

      <div className="panel queue">
        <div className="panel-head">
          <Icon name="inbox" size={16} />
          <span className="t-title">Inbox</span>
          {files ? <Chip tone="neutral">{files.length}</Chip> : null}
          <span className="spacer" />
          <button className="btn btn-icon" onClick={load} aria-label="Refresh the inbox">
            <Icon name="refresh" size={16} />
          </button>
          <button
            className="btn btn-filled"
            disabled={selected.size === 0 || busy}
            onClick={() => onProcessed([...selected])}
          >
            {busy ? <span className="spinner" /> : <Icon name="check" size={16} />}
            Process {selected.size} invoice{selected.size === 1 ? '' : 's'}
          </button>
        </div>

        {!files ? (
          <div className="empty">
            <span className="spinner" />
            <p className="t-body-sm">Reading the inbox…</p>
          </div>
        ) : files.length === 0 ? (
          <div className="empty">
            <Icon name="inbox" size={28} />
            <p className="t-body">The inbox is empty.</p>
            <p className="t-body-sm t-faint">Drop some invoices to get started.</p>
          </div>
        ) : (
          <div className="table-scroll">
            <table className="data">
              <thead>
                <tr>
                  <th className="col-check">
                    <input
                      type="checkbox"
                      checked={allSelected}
                      aria-label={allSelected ? 'Clear selection' : 'Select every invoice'}
                      onChange={() =>
                        setSelected(allSelected ? new Set() : new Set(files.map((f) => f.name)))
                      }
                    />
                  </th>
                  <th>Document</th>
                  <th className="num">Size</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {files.map((f) => (
                  <tr
                    key={f.name}
                    aria-selected={selected.has(f.name)}
                    tabIndex={0}
                    onClick={() => toggle(f.name)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        toggle(f.name);
                      }
                    }}
                  >
                    <td className="col-check">
                      <input
                        type="checkbox"
                        checked={selected.has(f.name)}
                        onChange={() => toggle(f.name)}
                        onClick={(e) => e.stopPropagation()}
                        aria-label={`Select ${f.name}`}
                      />
                    </td>
                    <td className="cell-file">
                      <Icon name="doc" size={14} className="t-faint" />
                      {f.name}
                    </td>
                    <td className="num">{kb(f.sizeBytes)}</td>
                    <td>
                      {f.parked ? (
                        <Chip tone="success" icon="check">
                          Parked
                        </Chip>
                      ) : f.processed ? (
                        <Chip tone="info" icon="check">
                          Validated
                        </Chip>
                      ) : (
                        <Chip tone="neutral" icon="inbox">
                          New
                        </Chip>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {runtime.source !== 'live' ? (
          <p className="notice notice-warn intake-offline">
            <Icon name="warning" size={14} />
            The backend is not running, so uploads and selective runs are unavailable. The
            workspace is showing seeded data.
          </p>
        ) : null}
      </div>
    </div>
  );
}
