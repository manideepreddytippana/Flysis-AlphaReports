import { Link } from "react-router";
import { ArrowLeft, FileQuestion } from "lucide-react";

export default function NotFoundPage() {
  return (
    <div className="min-h-screen bg-[#0b0f19] flex items-center justify-center">
      <div className="text-center">
        <div className="w-20 h-20 rounded-full bg-[#121828] border border-[#1b1f2a] flex items-center justify-center mx-auto mb-6">
          <FileQuestion className="w-10 h-10 text-[#3b6978]" />
        </div>
        <h1 className="text-4xl font-bold text-[#d0e7f4] mb-2">404</h1>
        <p className="text-[#64748b] mb-6">Page not found</p>
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-[#00e1b7] hover:text-[#00e1b7]/80 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </Link>
      </div>
    </div>
  );
}
