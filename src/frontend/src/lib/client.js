/**
 * Live backend client.
 *
 * Talks to the FastAPI service, which reads the documents, validates every
 * invoice against SAP through the MCP server, and performs the single write.
 *
 * If the backend is not running, `api` in ./api.js falls back to the seeded
 * demo data so the workspace still opens. The banner in the app shows which
 * source is live, so the two are never confused.
 */

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function call(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (body.detail) detail = body.detail;
    } catch {
      /* the body was not JSON; the status is all we have */
    }
    throw new Error(detail);
  }
  return response.json();
}

/** Rewrite relative PDF paths so the browser fetches them from the backend. */
function absolutePdfUrls(batch) {
  return {
    ...batch,
    outcomes: batch.outcomes.map((o) => ({
      ...o,
      invoice: { ...o.invoice, pdfUrl: `${BASE}${o.invoice.pdfUrl}` },
    })),
  };
}

export const live = {
  async health() {
    return call('/api/health');
  },

  async login(username, password) {
    // Deliberately client-side: the demo sign-in is a stub, not an auth
    // boundary, and pretending otherwise by adding an endpoint would suggest
    // a guarantee that does not exist.
    if (username === 'admin' && password === 'admin') {
      return { ok: true, user: { name: 'Admin', initials: 'AD' } };
    }
    return { ok: false, error: 'Incorrect username or password. Try admin / admin.' };
  },

  async getBatch() {
    return absolutePdfUrls(await call('/api/batches/latest'));
  },

  async runBatch(files) {
    return absolutePdfUrls(
      await call('/api/batches', { method: 'POST', body: JSON.stringify({ files: files ?? null }) }),
    );
  },

  async inbox() {
    return call('/api/inbox');
  },

  async upload(fileList) {
    // multipart, so the Content-Type header is left to the browser to set
    // with its own boundary.
    const form = new FormData();
    for (const file of fileList) form.append('files', file, file.name);
    const response = await fetch(`${BASE}/api/uploads`, { method: 'POST', body: form });
    if (!response.ok) throw new Error(`Upload failed: HTTP ${response.status}`);
    return response.json();
  },

  async approve(batchId, references) {
    return call(`/api/batches/${batchId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ references }),
    });
  },

  async park(batchId, token, references) {
    return call(`/api/batches/${batchId}/park`, {
      method: 'POST',
      body: JSON.stringify({ token, references }),
    });
  },

  async guidance(sopRef) {
    return call(`/api/guidance?sopRef=${encodeURIComponent(sopRef)}`);
  },

  async chat(batchId, reference, question) {
    return call('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ batchId, reference, question }),
    });
  },

  async reportCatalogue() {
    return call('/api/reports');
  },

  async generateReport(id, batchId) {
    return call(`/api/reports/${id}?batchId=${encodeURIComponent(batchId)}`);
  },
};

/** Is the backend up? Decided once at start-up, shown in the header. */
export async function backendReachable() {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 2500);
    const response = await fetch(`${BASE}/api/health`, { signal: controller.signal });
    clearTimeout(timer);
    return response.ok ? await response.json() : null;
  } catch {
    return null;
  }
}
