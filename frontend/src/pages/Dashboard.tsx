import React from "react";
import { Link } from "react-router";
import { Zap, FileText, CheckCircle2, Loader2, AlertCircle, HardDrive, Server, ArrowUpRight } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function Dashboard() {
  const { data: statsData, isLoading: isLoadingStats } = useQuery({
    queryKey: ["documentStats"],
    queryFn: () => api.documents.stats(),
  });

  const { data: recentDocs, isLoading: isLoadingDocs } = useQuery({
    queryKey: ["recentDocuments"],
    queryFn: () => api.documents.list(1, 5),
  });

  const docs = recentDocs?.items || [];
  const systemStatus = statsData?.processing > 0 ? "Processing" : "Idle";

  return (
    <div className="p-6 space-y-6 bloomberg-scrollbar overflow-auto h-[calc(100vh-4rem)]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-[#d0e7f4]">Dashboard</h1>
          <p className="text-sm text-[#64748b] mt-1">Overview of your documents and system status.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bloomberg-panel p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-[#64748b]">Total Documents</h3>
            <FileText className="w-4 h-4 text-[#3b6978]" />
          </div>
          <div className="text-2xl font-semibold text-[#d0e7f4]">
            {isLoadingStats ? "-" : statsData?.total || 0}
          </div>
        </div>

        <div className="bloomberg-panel p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-[#64748b]">Processed Documents</h3>
            <CheckCircle2 className="w-4 h-4 text-[#00e1b7]" />
          </div>
          <div className="text-2xl font-semibold text-[#d0e7f4]">
            {isLoadingStats ? "-" : statsData?.ready || 0}
          </div>
        </div>

        <div className="bloomberg-panel p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-[#64748b]">Processing / Error</h3>
            <div className="flex gap-2">
              <Loader2 className="w-4 h-4 text-yellow-500" />
              <AlertCircle className="w-4 h-4 text-red-500" />
            </div>
          </div>
          <div className="text-2xl font-semibold text-[#d0e7f4]">
            {isLoadingStats ? "-" : `${statsData?.processing || 0} / ${statsData?.error || 0}`}
          </div>
        </div>

        <div className="bloomberg-panel p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-[#64748b]">Total Pages Extracted</h3>
            <HardDrive className="w-4 h-4 text-[#3b6978]" />
          </div>
          <div className="text-2xl font-semibold text-[#d0e7f4]">
            {isLoadingStats ? "-" : statsData?.totalPages || 0}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-lg font-medium text-[#d0e7f4]">Recent Activity</h2>
          <div className="bloomberg-panel overflow-hidden">
            {isLoadingDocs ? (
              <div className="p-8 flex justify-center">
                <Loader2 className="w-6 h-6 animate-spin text-[#00e1b7]" />
              </div>
            ) : docs.length > 0 ? (
              <table className="w-full text-left">
                <thead className="border-b border-[#1b1f2a]">
                  <tr>
                    <th className="p-3 text-xs font-medium text-[#3b6978] uppercase">Document</th>
                    <th className="p-3 text-xs font-medium text-[#3b6978] uppercase">Status</th>
                    <th className="p-3 text-xs font-medium text-[#3b6978] uppercase hidden sm:table-cell">Uploaded</th>
                    <th className="p-3 text-xs font-medium text-[#3b6978] uppercase text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1b1f2a]">
                  {docs.map((doc: any) => (
                    <tr key={doc.id} className="group hover:bg-[#1b1f2a]/50 transition-all">
                      <td className="p-3">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded bg-[#00e1b7]/10 flex items-center justify-center shrink-0">
                            <FileText className="w-4 h-4 text-[#00e1b7]" />
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-[#d0e7f4] truncate">{doc.original_name}</p>
                            <p className="text-xs text-[#64748b]">{formatFileSize(doc.file_size)}</p>
                          </div>
                        </div>
                      </td>
                      <td className="p-3">
                         <span className={`inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded-full ${
                            doc.status === "ready" ? "bg-[#00e1b7]/10 text-[#00e1b7]" :
                            doc.status === "processing" ? "bg-yellow-500/10 text-yellow-500" :
                            "bg-red-500/10 text-red-400"
                          }`}>
                            {doc.status.charAt(0).toUpperCase() + doc.status.slice(1)}
                         </span>
                      </td>
                      <td className="p-3 text-xs text-[#64748b] hidden sm:table-cell">
                        {doc.uploaded_at ? formatDate(doc.uploaded_at) : "-"}
                      </td>
                      <td className="p-3 text-right">
                        <Link to={`/document/${doc.id}`} className="inline-flex items-center justify-center w-8 h-8 rounded hover:bg-[#00e1b7]/10 text-[#64748b] hover:text-[#00e1b7] transition-all">
                          <ArrowUpRight className="w-4 h-4" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-8 text-center text-sm text-[#64748b]">No recent documents found.</div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="bloomberg-panel p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-[#1b1f2a] flex items-center justify-center">
                <Server className="w-5 h-5 text-[#3b6978]" />
              </div>
              <div>
                <h3 className="text-sm font-medium text-[#d0e7f4]">System Status</h3>
                <p className="text-xs text-[#64748b]">Backend Extraction Engine</p>
              </div>
            </div>
            <div className="flex items-center justify-between p-3 rounded bg-[#161d2e] border border-[#1b1f2a]">
              <span className="text-sm text-[#64748b]">Status</span>
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${systemStatus === "Processing" ? "bg-yellow-500 animate-pulse" : "bg-[#00e1b7]"}`}></span>
                <span className="text-sm font-medium text-[#d0e7f4]">{systemStatus}</span>
              </div>
            </div>
          </div>

          <div className="bloomberg-panel p-6">
            <div className="flex flex-col items-center text-center gap-3">
              <div className="w-12 h-12 rounded-full bg-[#00e1b7]/10 flex items-center justify-center">
                <Zap className="w-5 h-5 text-[#00e1b7]" />
              </div>
              <div>
                <h3 className="text-sm font-medium text-[#d0e7f4]">Quick Upload</h3>
                <p className="text-xs text-[#64748b] mt-1">
                  Upload new PDFs to the library
                </p>
              </div>
              <Link to="/library" className="bloomberg-btn text-sm w-full mt-2 block">
                Go to Library
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
