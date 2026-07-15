import { Outlet } from "react-router";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";

export default function MainLayout() {
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
