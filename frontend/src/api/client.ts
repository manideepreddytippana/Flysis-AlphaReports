const API_BASE = "/api/v1";

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMessage = "An error occurred";
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
    } catch {
      errorMessage = response.statusText || errorMessage;
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

export const api = {
  auth: {
    me: () => fetchApi<any>("/auth/me"),
    devLogin: () => fetchApi<any>("/auth/dev-login", { method: "POST" }),
    logout: () => fetchApi<any>("/auth/logout", { method: "POST" }),
  },
  documents: {
    list: (page = 1, limit = 20) =>
      fetchApi<any>(`/documents?page=${page}&limit=${limit}`),
    get: (id: number) => fetchApi<any>(`/documents/${id}`),
    stats: () => fetchApi<any>("/documents/stats/overview"),
    upload: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return fetchApi<any>("/documents/upload", {
        method: "POST",
        body: formData,
      });
    },
    delete: (id: number) =>
      fetchApi<any>(`/documents/${id}`, { method: "DELETE" }),
    extract: {
      full: (docId: string) =>
        fetchApi<any>(`/documents/${docId}/extract/full`, { method: "POST" }),
      tables: (docId: string) =>
        fetchApi<any>(`/documents/${docId}/extract/tables`, { method: "POST" }),
      summary: (docId: string, style = "detailed") =>
        fetchApi<any>(`/documents/${docId}/extract/summary`, {
          method: "POST",
          body: JSON.stringify({ style }),
        }),
    },
    text: (docId: string, page?: number) =>
      fetchApi<any>(`/documents/${docId}/text${page ? `?page=${page}` : ""}`),
    dataJson: (docId: string) =>
      fetchApi<any>(`/documents/${docId}/data.json`),
    index: (docId: string, chunkSize = 512, overlap = 128) =>
      fetchApi<any>(`/documents/${docId}/index`, {
        method: "POST",
        body: JSON.stringify({ chunk_size: chunkSize, overlap }),
      }),
    search: (docId: string, query: string, topK = 5) =>
      fetchApi<any>(`/documents/${docId}/search`, {
        method: "POST",
        body: JSON.stringify({ query, top_k: topK }),
      }),
  },
  llm: {
    chat: (docId: string | undefined, messages: any[], useRag = false) =>
      fetchApi<any>("/llm/chat", {
        method: "POST",
        body: JSON.stringify({ doc_id: docId, messages, use_rag: useRag }),
      }),
    analyze: (docId: string) =>
      fetchApi<any>("/llm/analyze", {
        method: "POST",
        body: JSON.stringify({ doc_id: docId }),
      }),
  },
};
