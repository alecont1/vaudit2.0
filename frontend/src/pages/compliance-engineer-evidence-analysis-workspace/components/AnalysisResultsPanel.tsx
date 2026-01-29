import React from 'react';
import Icon from '../../../components/AppIcon';
import Button from '../../../components/ui/Button';
import ComplianceScoreGauge from './ComplianceScoreGauge';
import { AnalysisResult } from '../types';

interface AnalysisResultsPanelProps {
  result: AnalysisResult;
  onDownloadReport: () => void;
  onNewAnalysis: () => void;
}

const AnalysisResultsPanel: React.FC<AnalysisResultsPanelProps> = ({
  result,
  onDownloadReport,
  onNewAnalysis,
}) => {
  const getStatusBadge = () => {
    const baseClasses = 'inline-flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-sm border-2';
    
    if (result.status === 'compliant') {
      return (
        <div className={`${baseClasses} bg-success/10 text-success border-success`}>
          <Icon name="CheckCircle" size={20} strokeWidth={2.5} />
          <span>Compliant</span>
        </div>
      );
    }
    
    return (
      <div className={`${baseClasses} bg-error/10 text-error border-error`}>
        <Icon name="XCircle" size={20} strokeWidth={2.5} />
        <span>Non-Compliant</span>
      </div>
    );
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="bg-card border border-border rounded-lg p-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-foreground mb-1">
              Analysis Complete
            </h3>
            <p className="text-sm text-text-secondary">
              Document: {result.fileName}
            </p>
          </div>
          {getStatusBadge()}
        </div>

        <div className="flex items-center justify-center py-8 mb-6 bg-muted/30 rounded-lg">
          <ComplianceScoreGauge score={result.complianceScore} size={220} />
        </div>

        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-muted/50 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Icon name="Calendar" size={16} className="text-text-secondary" />
              <span className="text-xs font-medium text-text-secondary">
                Analysis Date
              </span>
            </div>
            <p className="text-sm font-semibold text-foreground">
              {new Date(result.uploadDate).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              })}
            </p>
          </div>

          <div className="bg-muted/50 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Icon name="FileText" size={16} className="text-text-secondary" />
              <span className="text-xs font-medium text-text-secondary">
                File Type
              </span>
            </div>
            <p className="text-sm font-semibold text-foreground uppercase">
              {result.fileType}
            </p>
          </div>

          {result.confidenceLevel && (
            <div className="bg-muted/50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Icon name="TrendingUp" size={16} className="text-text-secondary" />
                <span className="text-xs font-medium text-text-secondary">
                  Confidence Level
                </span>
              </div>
              <p className="text-sm font-semibold text-foreground">
                {result.confidenceLevel}%
              </p>
            </div>
          )}

          {result.apiResponseTime && (
            <div className="bg-muted/50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Icon name="Zap" size={16} className="text-text-secondary" />
                <span className="text-xs font-medium text-text-secondary">
                  Response Time
                </span>
              </div>
              <p className="text-sm font-semibold text-foreground">
                {result.apiResponseTime}ms
              </p>
            </div>
          )}
        </div>

        <div className="bg-muted/30 rounded-lg p-4 mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Icon name="Brain" size={20} className="text-primary" strokeWidth={2} />
            <h4 className="text-sm font-semibold text-foreground">AI Reasoning</h4>
          </div>
          <div className="prose prose-sm max-w-none">
            <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-line">
              {result.reasoning}
            </p>
          </div>
        </div>

        {result.knowledgeBaseVersion && (
          <div className="flex items-center gap-2 text-xs text-text-secondary mb-6">
            <Icon name="Database" size={14} strokeWidth={2} />
            <span>Knowledge Base Version: {result.knowledgeBaseVersion}</span>
          </div>
        )}

        <div className="flex gap-3">
          <Button
            variant="default"
            size="lg"
            fullWidth
            iconName="Download"
            iconPosition="left"
            onClick={onDownloadReport}
          >
            Download Audit Report
          </Button>
          <Button
            variant="outline"
            size="lg"
            iconName="Plus"
            iconPosition="left"
            onClick={onNewAnalysis}
          >
            New Analysis
          </Button>
        </div>
      </div>
    </div>
  );
};

export default AnalysisResultsPanel;