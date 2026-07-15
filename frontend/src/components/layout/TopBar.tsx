import { useState } from "react";
import { Link } from "react-router";
import {
  Search,
  Bell,
  Plus,
  User,
  FileText,
} from "lucide-react";
import { Button } from "@/components/ui/button";

export default function TopBar() {
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  return (
    <header className="fixed top-0 left-20 right-0 z-30 h-16 bg-[#0b0f19]/95 backdrop-blur-sm border-b border-[#1b1f2a] flex items-center px-6">
      <div className="flex items-center gap-4 min-w-[200px]">
        <Link to="/" className="flex items-center gap-2 group">
          <span className="text-lg font-semibold text-[#d0e7f4] group-hover:text-[#00e1b7] transition-colors">
            Flysis
          </span>
        </Link>
        <div className="h-5 w-px bg-[#1b1f2a]" />
        
      </div>

      <div className="flex-1 max-w-xl mx-auto px-8">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#64748b]" />
          <input
            type="text"
            placeholder="Search..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            onFocus={() => setSearchOpen(true)}
            className="w-full h-9 bg-[#161d2e] border border-[#1b1f2a] rounded-lg pl-10 pr-4 text-sm text-[#d0e7f4] placeholder:text-[#64748b] focus:border-[#00e1b7] focus:ring-1 focus:ring-[#00e1b7]/20 transition-all"
          />
          {searchOpen && searchQuery && (
            <div className="absolute top-full left-0 right-0 mt-2 bg-[#121828] border border-[#1b1f2a] rounded-lg shadow-xl z-50 overflow-hidden">
              <div className="p-3 text-xs text-[#64748b] border-b border-[#1b1f2a]">
                Search results for "{searchQuery}"
              </div>
              <div className="p-4 text-sm text-[#d0e7f4] text-center">
                <FileText className="w-8 h-8 mx-auto mb-2 text-[#3b6978]" />
                <p>Type to search documents, chats, and analytics</p>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <Link to="/library">
          <Button className="bg-[#00e1b7] hover:bg-[#00e1b7]/90 text-[#0b0f19] font-semibold text-sm h-9 px-4 gap-2">
            <Plus className="w-4 h-4" />
            New Task
          </Button>
        </Link>

        <button className="relative w-9 h-9 flex items-center justify-center rounded-lg hover:bg-[#121828] transition-colors text-[#64748b] hover:text-[#d0e7f4]">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-[#00e1b7] rounded-full" />
        </button>

        <div className="w-8 h-8 rounded-full bg-[#121828] border border-[#1b1f2a] flex items-center justify-center">
          <User className="w-4 h-4 text-[#64748b]" />
        </div>
      </div>
    </header>
  );
}
