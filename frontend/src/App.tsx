import { Routes, Route } from "react-router";
import MainLayout from "./components/layout/MainLayout";
import DashboardPage from "./pages/Dashboard";
import LibraryPage from "./pages/Library";
import DocumentViewerPage from "./pages/DocumentViewer";
import AnalyticsPage from "./pages/Analytics";
import Login from "./pages/Login";
import NotFound from "./pages/NotFound";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<MainLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/document/:id" element={<DocumentViewerPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
