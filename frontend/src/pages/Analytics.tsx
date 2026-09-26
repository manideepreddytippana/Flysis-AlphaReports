import React, { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { Loader2, TrendingUp, FileText, HardDrive, BarChart3 } from "lucide-react";

const COLORS = ["#00e1b7", "#eab308", "#ef4444"];

export default function Analytics() {
  const { data: statsData, isLoading: isLoadingStats } = useQuery({
    queryKey: ["documentStats"],
    queryFn: () => api.documents.stats(),
  });

  const { data: docsData, isLoading: isLoadingDocs } = useQuery({
    queryKey: ["documentsAnalytics"],
    queryFn: () => api.documents.list(1, 100),
  });

  const { uploadsOverTime, statusDistribution, avgPages, avgSize } = useMemo(() => {
    const docs = docsData?.items || [];
    
    const statusCounts = { ready: 0, processing: 0, error: 0 };
    docs.forEach((doc: any) => {
      if (statusCounts[doc.status as keyof typeof statusCounts] !== undefined) {
        statusCounts[doc.status as keyof typeof statusCounts]++;
      }
    });
    const statusDistribution = [
      { name: "Ready", value: statusCounts.ready },
      { name: "Processing", value: statusCounts.processing },
      { name: "Error", value: statusCounts.error },
    ];

    // Uploads over time
    const dateGroups: Record<string, number> = {};
    docs.forEach((doc: any) => {
      if (doc.uploaded_at) {
        const date = new Date(doc.uploaded_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        dateGroups[date] = (dateGroups[date] || 0) + 1;
      }
    });
    
    // Sort by date
    const uploadsOverTime = Object.entries(dateGroups)
      .map(([date, count]) => ({ date, count }))
      .reverse();

    // Calculates Averages for document data 
    const totalPages = docs.reduce((acc: number, doc: any) => acc + (doc.page_count || 0), 0);
    const totalSize = docs.reduce((acc: number, doc: any) => acc + (doc.file_size || 0), 0);
    const avgPages = docs.length ? Math.round(totalPages / docs.length) : 0;
    const avgSizeInMB = docs.length ? (totalSize / docs.length / (1024 * 1024)).toFixed(2) : "0";

    return { uploadsOverTime, statusDistribution, avgPages, avgSize: avgSizeInMB };
  }, [docsData]);

  if (isLoadingStats || isLoadingDocs) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 text-[#00e1b7] animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 bloomberg-scrollbar overflow-auto h-[calc(100vh-4rem)]">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-[#d0e7f4]">Analytics Overview</h1>
          <p className="text-sm text-[#64748b] mt-1">
            Deep dive into your document processing metrics and usage stats.
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bloomberg-panel p-5 flex flex-col gap-2">
          <div className="flex items-center gap-2 text-[#64748b]">
            <TrendingUp className="w-4 h-4" />
            <span className="text-xs font-medium uppercase tracking-wider">Total Uploads</span>
          </div>
          <div className="text-3xl font-semibold text-[#d0e7f4]">
            {statsData?.total || 0}
          </div>
        </div>
        
        <div className="bloomberg-panel p-5 flex flex-col gap-2">
          <div className="flex items-center gap-2 text-[#64748b]">
            <FileText className="w-4 h-4" />
            <span className="text-xs font-medium uppercase tracking-wider">Avg Pages / Doc</span>
          </div>
          <div className="text-3xl font-semibold text-[#d0e7f4]">
            {avgPages}
          </div>
        </div>

        <div className="bloomberg-panel p-5 flex flex-col gap-2">
          <div className="flex items-center gap-2 text-[#64748b]">
            <HardDrive className="w-4 h-4" />
            <span className="text-xs font-medium uppercase tracking-wider">Avg File Size</span>
          </div>
          <div className="text-3xl font-semibold text-[#d0e7f4]">
            {avgSize} <span className="text-base text-[#64748b] font-normal">MB</span>
          </div>
        </div>

        <div className="bloomberg-panel p-5 flex flex-col gap-2">
          <div className="flex items-center gap-2 text-[#64748b]">
            <BarChart3 className="w-4 h-4" />
            <span className="text-xs font-medium uppercase tracking-wider">Total Pages Processed</span>
          </div>
          <div className="text-3xl font-semibold text-[#d0e7f4]">
            {statsData?.totalPages || 0}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        {/*Uploads over time chart*/}
        <div className="bloomberg-panel p-6 lg:col-span-2">
          <h2 className="text-sm font-medium text-[#d0e7f4] mb-6">Document Uploads Over Time</h2>
          <div className="h-72">
            {uploadsOverTime.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={uploadsOverTime} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1b1f2a" vertical={false} />
                  <XAxis 
                    dataKey="date" 
                    stroke="#64748b" 
                    fontSize={12} 
                    tickLine={false} 
                    axisLine={false} 
                  />
                  <YAxis 
                    stroke="#64748b" 
                    fontSize={12} 
                    tickLine={false} 
                    axisLine={false} 
                    allowDecimals={false}
                  />
                  <Tooltip 
                    cursor={{ fill: '#1b1f2a', opacity: 0.4 }}
                    contentStyle={{ backgroundColor: '#0b0f19', borderColor: '#1b1f2a', borderRadius: '8px' }}
                    itemStyle={{ color: '#00e1b7' }}
                  />
                  <Bar dataKey="count" fill="#00e1b7" radius={[4, 4, 0, 0]} maxBarSize={50} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-[#64748b] text-sm">
                No data available yet
              </div>
            )}
          </div>
        </div>

        {/* Document status distribution chart */}
        <div className="bloomberg-panel p-6">
          <h2 className="text-sm font-medium text-[#d0e7f4] mb-6">Document Status Distribution</h2>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={statusDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                  stroke="none"
                >
                  {statusDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0b0f19', borderColor: '#1b1f2a', borderRadius: '8px' }}
                  itemStyle={{ color: '#d0e7f4' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          
          <div className="flex justify-center gap-6 mt-4">
            {statusDistribution.map((entry, index) => (
              <div key={entry.name} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }}></div>
                <span className="text-xs text-[#64748b]">{entry.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
