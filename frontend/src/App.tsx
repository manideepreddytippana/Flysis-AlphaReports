import { Routes, Route } from "react-router";
import MainLayout from "./components/layout/MainLayout";
import DashboardPage from "./pages/Dashboard";
import LibraryPage from "./pages/Library";
import DocumentViewerPage from "./pages/DocumentViewer";
import PdfInformationPage from "./pages/PdfInformation";
import AnalyticsPage from "./pages/Analytics";
import NotFound from "./pages/NotFound";

export default function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/document/:id" element={<DocumentViewerPage />} />
        <Route path="/pdf-information/:id" element={<PdfInformationPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
