import React from 'react';
import Icon from '../../../components/AppIcon';
import { AnalysisFinding } from '../types';

interface FindingItemProps {
  finding: AnalysisFinding;
  isSelected: boolean;
  onSelect: () => void;
}

const FindingItem: React.FC<FindingItemProps> = ({
  finding,
  isSelected,
  onSelect,
}) => {
  const getSeverityConfig = () => {
    switch (finding.severity) {
      case 'error':
        return {
          icon: 'XCircle',
          bgClass: 'bg-error/10',
          borderClass: 'border-error',
          iconClass: 'text-error',
          labelClass: 'text-error',
          label: 'Erro',
        };
      case 'warning':
        return {
          icon: 'AlertTriangle',
          bgClass: 'bg-warning/10',
          borderClass: 'border-warning',
          iconClass: 'text-warning',
          labelClass: 'text-warning',
          label: 'Aviso',
        };
      case 'info':
        return {
          icon: 'Info',
          bgClass: 'bg-primary/10',
          borderClass: 'border-primary',
          iconClass: 'text-primary',
          labelClass: 'text-primary',
          label: 'Info',
        };
      default:
        return {
          icon: 'HelpCircle',
          bgClass: 'bg-muted/50',
          borderClass: 'border-border',
          iconClass: 'text-text-secondary',
          labelClass: 'text-text-secondary',
          label: 'Desconhecido',
        };
    }
  };

  const getStatusBadge = () => {
    switch (finding.status) {
      case 'APPROVED':
        return (
          <span className="text-xs px-2 py-0.5 bg-success/10 text-success rounded-full">
            Aprovado
          </span>
        );
      case 'REJECTED':
        return (
          <span className="text-xs px-2 py-0.5 bg-error/10 text-error rounded-full">
            Rejeitado
          </span>
        );
      case 'REVIEW_NEEDED':
        return (
          <span className="text-xs px-2 py-0.5 bg-warning/10 text-warning rounded-full">
            Revisar
          </span>
        );
      default:
        return null;
    }
  };

  const severityConfig = getSeverityConfig();

  return (
    <div
      onClick={onSelect}
      className={`
        p-4 rounded-lg border-2 cursor-pointer transition-all
        ${isSelected ? `${severityConfig.bgClass} ${severityConfig.borderClass}` : 'bg-card border-border hover:border-primary/50'}
      `}
    >
      <div className="flex items-start gap-3">
        <div className={`p-1.5 rounded-md ${severityConfig.bgClass}`}>
          <Icon
            name={severityConfig.icon as any}
            size={18}
            className={severityConfig.iconClass}
          />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs font-medium ${severityConfig.labelClass}`}>
              {severityConfig.label}
            </span>
            {getStatusBadge()}
            {finding.page && (
              <span className="text-xs text-text-secondary">
                Pag. {finding.page}
              </span>
            )}
          </div>

          <h4 className="text-sm font-medium text-foreground mb-1 truncate">
            {finding.rule_name}
          </h4>

          <p className="text-sm text-text-secondary line-clamp-2 mb-2">
            {finding.message}
          </p>

          {(finding.found_value || finding.expected_value) && (
            <div className="flex flex-col gap-1 text-xs">
              {finding.found_value && (
                <div className="flex items-center gap-2">
                  <span className="text-text-secondary">Encontrado:</span>
                  <span className="text-foreground font-mono bg-muted/50 px-1.5 py-0.5 rounded">
                    {finding.found_value}
                  </span>
                </div>
              )}
              {finding.expected_value && (
                <div className="flex items-center gap-2">
                  <span className="text-text-secondary">Esperado:</span>
                  <span className="text-foreground font-mono bg-muted/50 px-1.5 py-0.5 rounded">
                    {finding.expected_value}
                  </span>
                </div>
              )}
            </div>
          )}

          {finding.bbox && finding.page && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onSelect();
              }}
              className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors"
            >
              <Icon name="ExternalLink" size={12} />
              Ver no documento
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default FindingItem;
