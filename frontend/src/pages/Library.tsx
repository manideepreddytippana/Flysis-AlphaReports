import { useState, useRef, useCallback } from "react";
import { Link } from "react-router";
import {
  Upload,
  FileText,
  Search,
  Trash2,
  Loader2,
  CheckCircle2,
  AlertCircle,
  ArrowUpRight,
  FolderOpen,
} from "lucide-react";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function LibraryPage() {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: docsData, isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.documents.list(1, 100),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.documents.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  const addSelectedFiles = useCallback((files: File[]) => {
    const validFiles = files.filter(f => f.type === "application/pdf");
    const rejectedCount = files.length - validFiles.length;

    if (rejectedCount > 0) {
      setUploadError("Only PDF files are supported.");
    } else {
      setUploadError(null);
    }

    setSelectedFiles(validFiles);
  }, []);

  const handleUploadAndAnalyze = useCallback(async () => {
    if (selectedFiles.length === 0) return;

    setIsUploading(true);
    setUploadError(null);

    try {
      for (const file of selectedFiles) {
        await api.documents.upload(file);
      }

      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      setSelectedFiles([]);
    } catch (error) {
      setUploadError(
        error instanceof Error ? error.message : "Failed to upload PDF"
      );
    } finally {
      setIsUploading(false);
    }
  }, [queryClient, selectedFiles]);

  const docs = docsData?.items || [];

  const filteredDocs = docs.filter((doc: any) => {
    const matchesSearch =
      doc.original_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.filename?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "all" || doc.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      addSelectedFiles(Array.from(e.dataTransfer.files));
    },
    [addSelectedFiles]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      addSelectedFiles(Array.from(e.target.files || []));
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
    [addSelectedFiles]
  );

  return (
    <div className="p-6 space-y-6 bloomberg-scrollbar overflow-auto h-[calc(100vh-4rem)]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-[#d0e7f4]">
            Document Library
          </h1>
          <p className="text-sm text-[#64748b] mt-1">
            {docs.length} documents ·{" "}
            {docs.filter((d: any) => d.status === "ready").length} ready
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="bloomberg-btn flex items-center gap-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isUploading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Upload className="w-4 h-4" />
            )}
            Choose PDF
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            multiple
            className="hidden"
            onChange={handleFileSelect}
          />
        </div>
      </div>

      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-all ${
          isDragging
            ? "border-[#00e1b7] bg-[#00e1b7]/5"
            : "border-[#1b1f2a] hover:border-[#3b6978] hover:bg-[#121828]/50"
        }`}
      >
        <Upload
          className={`w-8 h-8 mx-auto mb-3 ${isDragging ? "text-[#00e1b7]" : "text-[#3b6978]"}`}
        />
        <p className="text-sm text-[#d0e7f4]">
          {isDragging
            ? "Drop PDFs here"
            : "Drag and drop PDFs here, or click Upload"}
        </p>
        <p className="text-xs text-[#64748b] mt-1">Maximum file size: 50MB</p>
      </div>

      {selectedFiles.length > 0 && (
        <div className="bloomberg-panel p-4 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-sm font-medium text-[#d0e7f4]">
                Selected file{selectedFiles.length > 1 ? "s" : ""}
              </h2>
              <p className="text-xs text-[#64748b] mt-1">
                Preview the file to be uploaded, then start the upload and analysis.
              </p>
            </div>
            <button
              onClick={() => setSelectedFiles([])}
              className="text-xs text-[#64748b] hover:text-[#d0e7f4] transition-colors"
            >
              Clear
            </button>
          </div>

          <div className="space-y-2">
            {selectedFiles.map(file => (
              <div
                key={`${file.name}-${file.size}-${file.lastModified}`}
                className="flex items-center justify-between gap-4 rounded-lg border border-[#1b1f2a] bg-[#121828] px-4 py-3"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-10 h-10 rounded-lg bg-[#00e1b7]/10 flex items-center justify-center shrink-0">
                    <FileText className="w-4 h-4 text-[#00e1b7]" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-[#d0e7f4] truncate">
                      {file.name}
                    </p>
                    <p className="text-xs text-[#64748b]">
                      {formatFileSize(file.size)} · PDF ready for upload
                    </p>
                  </div>
                </div>
                <button
                  onClick={() =>
                    setSelectedFiles(prev =>
                      prev.filter(
                        current =>
                          `${current.name}-${current.size}-${current.lastModified}` !==
                          `${file.name}-${file.size}-${file.lastModified}`
                      )
                    )
                  }
                  className="text-xs text-[#64748b] hover:text-red-400 transition-colors shrink-0"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <p className="text-xs text-[#64748b]">
              {selectedFiles.length} file{selectedFiles.length > 1 ? "s" : ""} selected
            </p>
            <button
              onClick={handleUploadAndAnalyze}
              disabled={isUploading}
              className="bloomberg-btn flex items-center justify-center gap-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isUploading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Upload className="w-4 h-4" />
              )}
              Upload and Analyze
            </button>
          </div>

          {uploadError && (
            <p className="text-xs text-red-400">
              {uploadError}
            </p>
          )}
        </div>
      )}

      <div className="flex items-center gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#64748b]" />
          <input
            type="text"
            placeholder="Search documents..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full h-9 bg-[#161d2e] border border-[#1b1f2a] rounded-lg pl-10 pr-4 text-sm text-[#d0e7f4] placeholder:text-[#64748b] focus:border-[#00e1b7] focus:ring-1 focus:ring-[#00e1b7]/20 transition-all"
          />
        </div>
        <div className="flex items-center gap-1 bg-[#161d2e] border border-[#1b1f2a] rounded-lg p-1">
          {(["all", "ready", "processing", "error"] as const).map(status => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`px-3 py-1.5 text-xs rounded-md transition-all ${
                statusFilter === status
                  ? "bg-[#00e1b7]/10 text-[#00e1b7]"
                  : "text-[#64748b] hover:text-[#d0e7f4]"
              }`}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="bloomberg-panel overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[#1b1f2a]">
              <th className="text-left p-3 text-xs font-medium text-[#3b6978] uppercase tracking-wider">
                Document
              </th>
              <th className="text-left p-3 text-xs font-medium text-[#3b6978] uppercase tracking-wider">
                Pages
              </th>
              <th className="text-left p-3 text-xs font-medium text-[#3b6978] uppercase tracking-wider">
                Size
              </th>
              <th className="text-left p-3 text-xs font-medium text-[#3b6978] uppercase tracking-wider">
                Status
              </th>
              <th className="text-left p-3 text-xs font-medium text-[#3b6978] uppercase tracking-wider">
                Uploaded
              </th>
              <th className="text-right p-3 text-xs font-medium text-[#3b6978] uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1b1f2a]">
            {filteredDocs.map(doc => (
              <tr
                key={doc.id}
                className="group hover:bg-[#1b1f2a]/50 transition-all"
              >
                <td className="p-3">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded bg-[#00e1b7]/10 flex items-center justify-center shrink-0">
                      <FileText className="w-4 h-4 text-[#00e1b7]" />
                    </div>
                    <div className="min-w-0">
                      <Link
                        to={`/document/${doc.id}`}
                        className="text-sm font-medium text-[#d0e7f4] hover:text-[#00e1b7] transition-colors truncate block"
                      >
                        {doc.original_name}
                      </Link>
                      <span className="text-xs text-[#64748b]">
                        {doc.filename}
                      </span>
                    </div>
                  </div>
                </td>
                <td className="p-3">
                  <span
                    className="text-sm text-[#d0e7f4]"
                    style={{ fontFamily: "JetBrains Mono" }}
                  >
                    {doc.page_count}
                  </span>
                </td>
                <td className="p-3">
                  <span
                    className="text-sm text-[#64748b]"
                    style={{ fontFamily: "JetBrains Mono" }}
                  >
                    {formatFileSize(doc.file_size)}
                  </span>
                </td>
                <td className="p-3">
                  <span
                    className={`inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded-full ${
                      doc.status === "ready"
                        ? "bg-[#00e1b7]/10 text-[#00e1b7]"
                        : doc.status === "processing"
                          ? "bg-yellow-500/10 text-yellow-500"
                          : "bg-red-500/10 text-red-400"
                    }`}
                  >
                    {doc.status === "ready" ? (
                      <CheckCircle2 className="w-3 h-3" />
                    ) : doc.status === "processing" ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <AlertCircle className="w-3 h-3" />
                    )}
                    {doc.status.charAt(0).toUpperCase() + doc.status.slice(1)}
                  </span>
                </td>
                <td className="p-3">
                  <span className="text-xs text-[#64748b]">
                    {doc.uploaded_at ? formatDate(doc.uploaded_at) : "-"}
                  </span>
                </td>
                <td className="p-3">
                  <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Link
                      to={`/document/${doc.id}`}
                      className="w-8 h-8 flex items-center justify-center rounded hover:bg-[#00e1b7]/10 text-[#64748b] hover:text-[#00e1b7] transition-all"
                      title="Open"
                    >
                      <ArrowUpRight className="w-4 h-4" />
                    </Link>
                    <button
                      onClick={() => {
                        if (
                          confirm(
                            "Are you sure you want to delete this document?"
                          )
                        ) {
                          deleteMutation.mutate(doc.id);
                        }
                      }}
                      className="w-8 h-8 flex items-center justify-center rounded hover:bg-red-500/10 text-[#64748b] hover:text-red-400 transition-all"
                      title="Delete"
                      disabled={deleteMutation.isPending}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filteredDocs.length === 0 && (
          <div className="p-12 text-center">
            <FolderOpen className="w-12 h-12 mx-auto mb-3 text-[#3b6978]" />
            <p className="text-sm text-[#64748b]">No documents found</p>
            <p className="text-xs text-[#64748b] mt-1">
              Try adjusting your search or filters
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
