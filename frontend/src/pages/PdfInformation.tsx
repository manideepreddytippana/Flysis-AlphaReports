import { useState, useEffect } from "react";
import { useParams, Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, Loader2, Download, Copy, CheckCircle2 } from "lucide-react";
import { api } from "@/api/client";

export default function PdfInformationPage() {
  const { id } = useParams<{ id: string }>();
  const docId = Number(id);
  const [copied, setCopied] = useState(false);

  const { data: doc, isLoading: isLoadingDoc } = useQuery({
    queryKey: ["document", docId],
    queryFn: () => api.documents.get(docId),
  });

  const { data: dataJson, isLoading: isLoadingData, error } = useQuery({
    queryKey: ["documentDataJson", doc?.python_doc_id],
    queryFn: () => api.documents.dataJson(doc?.python_doc_id),
    enabled: !!doc?.python_doc_id,
  });

  const handleCopy = () => {
    if (!dataJson) return;
    navigator.clipboard.writeText(JSON.stringify(dataJson, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!dataJson || !doc) return;
    const blob = new Blob([JSON.stringify(dataJson, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${doc.original_name.replace(/\.[^/.]+$/, "")}_data.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (isLoadingDoc || isLoadingData) {
    return (
      <div className="flex h-[calc(100vh-4rem)] items-center justify-center bg-[#161d2e]">
        <Loader2 className="w-8 h-8 text-[#00e1b7] animate-spin" />
      </div>
    );
  }

  if (error || !doc) {
    return (
      <div className="flex h-[calc(100vh-4rem)] flex-col items-center justify-center bg-[#161d2e] gap-4">
        <p className="text-[#d0e7f4]">Document data not found or still processing.</p>
        <Link to={`/document/${id}`} className="text-[#00e1b7] hover:underline">
          Go back to document
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-[#161d2e] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 bg-[#0b0f19] border-b border-[#1b1f2a] shrink-0">
        <div className="flex items-center gap-4">
          <Link
            to={`/document/${id}`}
            className="flex items-center gap-2 text-[#64748b] hover:text-[#d0e7f4] transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
            <span className="text-sm font-medium">Back to Document</span>
          </Link>
          <div className="h-4 w-px bg-[#1b1f2a]" />
          <div>
            <h1 className="text-sm font-semibold text-[#d0e7f4]">
              {doc.original_name} — Raw Data.json
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleCopy}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[#1b1f2a] text-[#d0e7f4] hover:bg-[#1b1f2a] transition-all text-xs font-medium"
          >
            {copied ? <CheckCircle2 className="w-4 h-4 text-[#00e1b7]" /> : <Copy className="w-4 h-4" />}
            {copied ? "Copied" : "Copy JSON"}
          </button>
          <button
            onClick={handleDownload}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#00e1b7]/10 text-[#00e1b7] hover:bg-[#00e1b7]/20 border border-[#00e1b7]/20 transition-all text-xs font-medium"
          >
            <Download className="w-4 h-4" />
            Download JSON
          </button>
        </div>
      </div>

      {/* JSON Viewer */}
      <div className="flex-1 overflow-auto p-6 bloomberg-scrollbar">
        <div className="bg-[#0b0f19] border border-[#1b1f2a] rounded-xl overflow-hidden shadow-2xl h-full flex flex-col">
          <div className="bg-[#121828] px-4 py-2 border-b border-[#1b1f2a] flex items-center justify-between shrink-0">
            <span className="text-xs font-mono text-[#3b6978]">data.json</span>
            <span className="text-[10px] text-[#64748b]">
              {dataJson ? `${JSON.stringify(dataJson).length.toLocaleString()} bytes` : "Empty"}
            </span>
          </div>
          <div className="flex-1 overflow-auto p-4 bloomberg-scrollbar">
            <pre className="text-xs font-mono text-[#a0b4c0] leading-relaxed">
              {dataJson ? JSON.stringify(dataJson, null, 2) : "No data available"}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
