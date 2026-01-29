import React, { useState } from 'react';
import Icon from '../../../components/AppIcon';
import { AnalysisResult, FilterOptions } from '../types';

interface RecentAnalysisSidebarProps {
  analyses: AnalysisResult[];
  onSelectAnalysis: (analysis: AnalysisResult) => void;
  selectedAnalysisId: string | null;
}

const RecentAnalysisSidebar: React.FC<RecentAnalysisSidebarProps> = ({
  analyses,
  onSelectAnalysis,
  selectedAnalysisId,
}) => {
  const [filters, setFilters] = useState<FilterOptions>({
    status: [],
    scoreRange: { min: 0, max: 100 },
    dateRange: { start: null, end: null },
  });

  const [showFilters, setShowFilters] = useState(false);

  const statusOptions = [
    { value: 'compliant', label: 'Compliant', color: 'bg-success' },
    { value: 'non-compliant', label: 'Non-Compliant', color: 'bg-error' },
    { value: 'pending', label: 'Pending', color: 'bg-warning' },
  ];

  const toggleStatusFilter = (status: string) => {
    setFilters((prev) => ({
      ...prev,
      status: prev.status.includes(status)
        ? prev.status.filter((s) => s !== status)
        : [...prev.status, status],
    }));
  };

  const filteredAnalyses = analyses.filter((analysis) => {
    if (filters.status.length > 0 && !filters.status.includes(analysis.status)) {
      return false;
    }
    if (
      analysis.complianceScore < filters.scoreRange.min ||
      analysis.complianceScore > filters.scoreRange.max
    ) {
      return false;
    }
    if (filters.dateRange.start && analysis.uploadDate < filters.dateRange.start) {
      return false;
    }
    if (filters.dateRange.end && analysis.uploadDate > filters.dateRange.end) {
      return false;
    }
    return true;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'compliant':
        return 'bg-success/10 text-success border-success/20';
      case 'non-compliant':
        return 'bg-error/10 text-error border-error/20';
      case 'pending':
        return 'bg-warning/10 text-warning border-warning/20';
      default:
        return 'bg-muted text-text-secondary border-border';
    }
  };

  return (
    <aside className="h-full bg-card border-r border-border flex flex-col">
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-foreground">Recent Analyses</h2>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="p-2 rounded-md hover:bg-muted transition-colors duration-150"
            aria-label="Toggle filters"
          >
            <Icon name="Filter" size={20} strokeWidth={2} />
          </button>
        </div>

        {showFilters && (
          <div className="space-y-4 animate-fade-in">
            <div>
              <label className="text-sm font-medium text-text-secondary mb-2 block">
                Status
              </label>
              <div className="flex flex-wrap gap-2">
                {statusOptions.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => toggleStatusFilter(option.value)}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 ${
                      filters.status.includes(option.value)
                        ? `${option.color} text-white`
                        : 'bg-muted text-text-secondary hover:bg-muted/80'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-text-secondary mb-2 block">
                Score Range: {filters.scoreRange.min}% - {filters.scoreRange.max}%
              </label>
              <div className="flex gap-2">
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={filters.scoreRange.min}
                  onChange={(e) =>
                    setFilters((prev) => ({
                      ...prev,
                      scoreRange: { ...prev.scoreRange, min: parseInt(e.target.value) },
                    }))
                  }
                  className="flex-1"
                />
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={filters.scoreRange.max}
                  onChange={(e) =>
                    setFilters((prev) => ({
                      ...prev,
                      scoreRange: { ...prev.scoreRange, max: parseInt(e.target.value) },
                    }))
                  }
                  className="flex-1"
                />
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {filteredAnalyses.length === 0 ? (
          <div className="text-center py-8">
            <Icon
              name="FileSearch"
              size={48}
              className="mx-auto mb-3 text-text-secondary opacity-50"
            />
            <p className="text-sm text-text-secondary">No analyses found</p>
          </div>
        ) : (
          filteredAnalyses.map((analysis) => (
            <button
              key={analysis.id}
              onClick={() => onSelectAnalysis(analysis)}
              className={`w-full text-left p-3 rounded-lg border transition-all duration-150 ${
                selectedAnalysisId === analysis.id
                  ? 'bg-primary/10 border-primary shadow-sm'
                  : 'bg-card border-border hover:bg-muted hover:border-muted'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <h3 className="text-sm font-medium text-foreground truncate flex-1 mr-2">
                  {analysis.fileName}
                </h3>
                <span
                  className={`px-2 py-0.5 rounded text-xs font-medium border ${getStatusColor(
                    analysis.status
                  )}`}
                >
                  {analysis.status}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs text-text-secondary">
                <span>{new Date(analysis.uploadDate).toLocaleDateString()}</span>
                <span className="font-semibold">{analysis.complianceScore}%</span>
              </div>
            </button>
          ))
        )}
      </div>
    </aside>
  );
};

export default RecentAnalysisSidebar;