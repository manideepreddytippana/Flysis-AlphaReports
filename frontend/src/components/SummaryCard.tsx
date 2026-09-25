import { useState } from 'react'
import { Sparkles, BookOpen, TrendingUp, ListChecks, BarChart3, Lightbulb, AlertTriangle, FileText, ChevronUp, ChevronDown } from 'lucide-react'

export interface ParsedSummary {
  summary: string
  sections: Array<{ title: string; content: string }>
  key_metrics: Array<{ name: string; value: string; significance: string }>
  recommendations: string[]
}

export function parseSummary(raw: string): ParsedSummary {
  const fallback: ParsedSummary = {
    summary: raw,
    sections: [],
    key_metrics: [],
    recommendations: [],
  }

  try {
    let text = raw.trim()
    if (text.startsWith('```')) {
      text = text.replace(/^```(?:json)?\n?/, '').replace(/\n?```$/, '')
    }
    const parsed = JSON.parse(text)
    return {
      summary: parsed.summary || raw,
      sections: Array.isArray(parsed.sections) ? parsed.sections : [],
      key_metrics: Array.isArray(parsed.key_metrics) ? parsed.key_metrics : [],
      recommendations: Array.isArray(parsed.recommendations) ? parsed.recommendations : [],
    }
  } catch {
    const jsonMatch = raw.match(/\{[\s\S]*"summary"[\s\S]*\}/)
    if (jsonMatch) {
      try {
        const parsed = JSON.parse(jsonMatch[0])
        return {
          summary: parsed.summary || raw,
          sections: Array.isArray(parsed.sections) ? parsed.sections : [],
          key_metrics: Array.isArray(parsed.key_metrics) ? parsed.key_metrics : [],
          recommendations: Array.isArray(parsed.recommendations) ? parsed.recommendations : [],
        }
      } catch {
        // fall through
      }
    }
    return fallback
  }
}

const sectionIcons: Record<string, React.ReactNode> = {
  'executive overview': <BookOpen className="w-3.5 h-3.5" />,
  'key findings': <TrendingUp className="w-3.5 h-3.5" />,
  'methodology': <ListChecks className="w-3.5 h-3.5" />,
  'methodology notes': <ListChecks className="w-3.5 h-3.5" />,
  'quantitative highlights': <BarChart3 className="w-3.5 h-3.5" />,
  'implications': <Lightbulb className="w-3.5 h-3.5" />,
  'implications/recommendations': <Lightbulb className="w-3.5 h-3.5" />,
  'recommendations': <Lightbulb className="w-3.5 h-3.5" />,
  'risk factors': <AlertTriangle className="w-3.5 h-3.5" />,
  'risks': <AlertTriangle className="w-3.5 h-3.5" />,
}

function getSectionIcon(title: string) {
  const key = title.toLowerCase().trim()
  for (const [pattern, icon] of Object.entries(sectionIcons)) {
    if (key.includes(pattern)) return icon
  }
  return <FileText className="w-3.5 h-3.5" />
}

export function ExecutiveSummaryCard({ summary }: { summary: string }) {
  const data = parseSummary(summary)
  const [expandedSections, setExpandedSections] = useState<Record<number, boolean>>(
    Object.fromEntries(data.sections.map((_, i) => [i, true]))
  )

  const toggleSection = (idx: number) => {
    setExpandedSections(prev => ({ ...prev, [idx]: !prev[idx] }))
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#00e1b7] to-[#00b894] flex items-center justify-center">
          <Sparkles className="w-3.5 h-3.5 text-[#0b0f19]" />
        </div>
        <h3 className="text-sm font-semibold text-[#d0e7f4]">AI Executive Summary</h3>
      </div>

      {/* Overview Card */}
      <div className="bg-gradient-to-br from-[#121828] to-[#0e1422] border border-[#1b1f2a] rounded-xl p-5">
        <p className="text-sm text-[#d0e7f4] leading-relaxed">
          {data.summary}
        </p>
      </div>

      {/* Sections */}
      {data.sections.length > 0 && (
        <div className="space-y-2">
          {data.sections.map((section, i) => (
            <div
              key={i}
              className="bg-[#121828] border border-[#1b1f2a] rounded-lg overflow-hidden transition-all duration-200 hover:border-[#2a3040]"
            >
              <button
                onClick={() => toggleSection(i)}
                className="w-full flex items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-[#1b1f2a]/30"
              >
                <div className="w-6 h-6 rounded-md bg-[#00e1b7]/10 text-[#00e1b7] flex items-center justify-center shrink-0">
                  {getSectionIcon(section.title)}
                </div>
                <span className="text-xs font-semibold text-[#d0e7f4] flex-1 truncate">
                  {section.title}
                </span>
                {expandedSections[i] ? (
                  <ChevronUp className="w-3.5 h-3.5 text-[#64748b] shrink-0" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5 text-[#64748b] shrink-0" />
                )}
              </button>
              {expandedSections[i] && (
                <div className="px-4 pb-4 pt-0">
                  <div className="pl-9">
                    <div className="text-xs text-[#a0b4c0] leading-relaxed whitespace-pre-line">
                      {section.content}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Key Metrics */}
      {data.key_metrics.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="w-3.5 h-3.5 text-[#3b6978]" />
            <h4 className="text-xs font-semibold text-[#3b6978] uppercase tracking-wider">Key Metrics</h4>
          </div>
          <div className="grid grid-cols-1 gap-2">
            {data.key_metrics.map((metric, i) => (
              <div
                key={i}
                className="bg-[#121828] border border-[#1b1f2a] rounded-lg p-3 flex items-start gap-3 transition-all hover:border-[#2a3040]"
              >
                <div className="w-8 h-8 rounded-lg bg-[#00e1b7]/8 border border-[#00e1b7]/20 flex items-center justify-center shrink-0 mt-0.5">
                  <span className="text-xs font-bold text-[#00e1b7]">{i + 1}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-xs font-semibold text-[#d0e7f4] truncate">{metric.name}</span>
                  </div>
                  <div className="text-sm font-bold text-[#00e1b7] mb-1">{metric.value}</div>
                  <p className="text-[10px] text-[#64748b] leading-relaxed">{metric.significance}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {data.recommendations.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Lightbulb className="w-3.5 h-3.5 text-[#3b6978]" />
            <h4 className="text-xs font-semibold text-[#3b6978] uppercase tracking-wider">Recommendations</h4>
          </div>
          <div className="bg-[#121828] border border-[#1b1f2a] rounded-lg divide-y divide-[#1b1f2a]">
            {data.recommendations.map((rec, i) => (
              <div key={i} className="flex items-start gap-3 px-4 py-3">
                <div className="w-5 h-5 rounded-full bg-[#00e1b7]/10 flex items-center justify-center shrink-0 mt-0.5">
                  <span className="text-[10px] font-bold text-[#00e1b7]">{i + 1}</span>
                </div>
                <p className="text-xs text-[#a0b4c0] leading-relaxed">{rec}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
