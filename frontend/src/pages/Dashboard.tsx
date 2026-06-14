import React from "react";
import { Link } from "react-router";
import { Zap } from "lucide-react";

export default function Dashboard() {
  return (
    <div className="bloomberg-panel p-6">
      <div className="flex flex-col items-center text-center gap-3">
        <div className="w-12 h-12 rounded-full bg-[#00e1b7]/10 flex items-center justify-center">
          <Zap className="w-5 h-5 text-[#00e1b7]" />
        </div>
        <div>
          <h3 className="text-sm font-medium text-[#d0e7f4]">Quick Upload</h3>
          <p className="text-xs text-[#64748b] mt-1">
            Drag and drop PDFs or browse files
          </p>
        </div>
        <Link to="/library" className="bloomberg-btn text-sm w-full">
          Upload Document
        </Link>
      </div>
    </div>
  );
}
