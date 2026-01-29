import React from 'react';
import Icon from '../../../components/AppIcon';
import { AnalysisResult } from '../types';

interface DetailedReasoningSidebarProps {
  result: AnalysisResult | null;
}

const DetailedReasoningSidebar: React.FC<DetailedReasoningSidebarProps> = ({
  result,
}) => {
  if (!result) {
    return (
      <aside className="h-full bg-card border-l border-border flex flex-col items-center justify-center p-6">
        <Icon
          name="FileSearch"
          size={64}
          className="text-text-secondary opacity-30 mb-4"
        />
        <p className="text-sm text-text-secondary text-center">
          Select an analysis to view detailed reasoning
        </p>
      </aside>
    );
  }

  const auditTrail = [
    {
      timestamp: new Date(result.uploadDate),
      action: 'Document Uploaded',
      icon: 'Upload',
    },
    {
      timestamp: new Date(result.uploadDate.getTime() + 5000),
      action: 'AI Analysis Started',
      icon: 'Play',
    },
    {
      timestamp: new Date(result.uploadDate.getTime() + 15000),
      action: 'Compliance Check Complete',
      icon: 'CheckCircle',
    },
    {
      timestamp: new Date(result.uploadDate.getTime() + 20000),
      action: 'Report Generated',
      icon: 'FileText',
    },
  ];

  return (
    <aside className="h-full bg-card border-l border-border flex flex-col overflow-hidden">
      <div className="p-4 border-b border-border">
        <h2 className="text-lg font-semibold text-foreground">
          Detailed Analysis
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <div>
          <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
            <Icon name="Brain" size={18} strokeWidth={2} />
            AI Reasoning Breakdown
          </h3>
          <div className="bg-muted/30 rounded-lg p-4">
            <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-line">
              {result.reasoning}
            </p>
          </div>
        </div>

        {result.confidenceLevel && (
          <div>
            <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
              <Icon name="TrendingUp" size={18} strokeWidth={2} />
              Confidence Metrics
            </h3>
            <div className="space-y-3">
              <div className="bg-muted/30 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-text-secondary">
                    Overall Confidence
                  </span>
                  <span className="text-sm font-semibold text-foreground">
                    {result.confidenceLevel}%
                  </span>
                </div>
                <div className="h-2 bg-background rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all duration-500"
                    style={{ width: `${result.confidenceLevel}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        <div>
          <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
            <Icon name="Clock" size={18} strokeWidth={2} />
            Audit Trail
          </h3>
          <div className="space-y-3">
            {auditTrail.map((entry, index) => (
              <div key={index} className="flex items-start gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <Icon
                    name={entry.icon}
                    size={16}
                    className="text-primary"
                    strokeWidth={2}
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground">
                    {entry.action}
                  </p>
                  <p className="text-xs text-text-secondary">
                    {entry.timestamp.toLocaleTimeString('en-US', {
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                    })}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {result.knowledgeBaseVersion && (
          <div>
            <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
              <Icon name="Database" size={18} strokeWidth={2} />
              System Information
            </h3>
            <div className="bg-muted/30 rounded-lg p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-text-secondary">KB Version</span>
                <span className="text-xs font-medium text-foreground">
                  {result.knowledgeBaseVersion}
                </span>
              </div>
              {result.apiResponseTime && (
                <div className="flex items-center justify-between">
                  <span className="text-xs text-text-secondary">API Response</span>
                  <span className="text-xs font-medium text-foreground">
                    {result.apiResponseTime}ms
                  </span>
                </div>
              )}
              <div className="flex items-center justify-between">
                <span className="text-xs text-text-secondary">Analysis ID</span>
                <span className="text-xs font-medium text-foreground font-mono">
                  {result.id}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};

export default DetailedReasoningSidebar;