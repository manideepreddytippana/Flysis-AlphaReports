import { Link, useLocation } from "react-router";
import {
  LayoutDashboard,
  FolderOpen,
  BarChart3,
  Settings,
  Microscope,
} from "lucide-react";

const navItems = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/" },
  { icon: FolderOpen, label: "Library", path: "/library" },
  { icon: BarChart3, label: "Analytics", path: "/analytics" },
];

const bottomItems = [{ icon: Settings, label: "Settings", path: "#" }];

export default function Sidebar() {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-20 bg-[#0b0f19] border-r border-[#1b1f2a] flex flex-col items-center py-6">
      <div className="mb-8">
        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[#00e1b7] to-[#3b6978] flex items-center justify-center">
          <Microscope className="w-5 h-5 text-[#0b0f19]" />
        </div>
      </div>

      <nav className="flex-1 flex flex-col items-center gap-2">
        {navItems.map(item => {
          const active = isActive(item.path);
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`w-12 h-12 rounded-lg flex items-center justify-center transition-all relative group ${
                active
                  ? "bg-[#121828] text-[#00e1b7] border-l-2 border-[#00e1b7]"
                  : "text-[#64748b] hover:bg-[#121828] hover:text-[#d0e7f4]"
              }`}
              title={item.label}
            >
              <item.icon className="w-5 h-5" />
              {active && (
                <span className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-[#00e1b7] rounded-l-full" />
              )}
              <span className="absolute left-full ml-3 px-2 py-1 bg-[#121828] text-[#d0e7f4] text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none border border-[#1b1f2a]">
                {item.label}
              </span>
            </Link>
          );
        })}
      </nav>

      <div className="flex flex-col items-center gap-2">
        {bottomItems.map(item => (
          <button
            key={item.label}
            onClick={() => {}}
            className="w-12 h-12 rounded-lg flex items-center justify-center text-[#64748b] hover:bg-[#121828] hover:text-[#d0e7f4] transition-all group relative"
            title={item.label}
          >
            <item.icon className="w-5 h-5" />
            <span className="absolute left-full ml-3 px-2 py-1 bg-[#121828] text-[#d0e7f4] text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none border border-[#1b1f2a]">
              {item.label}
            </span>
          </button>
        ))}
      </div>
    </aside>
  );
}
