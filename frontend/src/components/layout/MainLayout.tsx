import { Outlet } from "react-router";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import { useAuth } from "@/hooks/useAuth";
import { Loader2 } from "lucide-react";

export default function MainLayout() {
  const { isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="h-screen w-screen bg-[#0b0f19] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 text-[#00e1b7] animate-spin" />
          <span className="text-sm text-[#64748b]">Loading...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0b0f19]">
      <Sidebar />
      <TopBar />
      <main className="ml-20 pt-16 min-h-screen">
        <Outlet />
      </main>
    </div>
  );
}
