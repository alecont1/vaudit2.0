import React, { useMemo } from 'react';
import Icon from '../../../components/AppIcon';
import FindingItem from './FindingItem';
import { AnalysisFinding, SeverityFilter, SortOrder } from '../types';

interface FindingsListProps {
  findings: AnalysisFinding[];
  selectedFindingId: string | null;
  onFindingSelect: (finding: AnalysisFinding) => void;
  sortOrder: SortOrder;
  onSortChange: (order: SortOrder) => void;
  severityFilter: SeverityFilter;
  onFilterChange: (filter: SeverityFilter) => void;
}

const FindingsList: React.FC<FindingsListProps> = ({
  findings,
  selectedFindingId,
  onFindingSelect,
  sortOrder,
  onSortChange,
  severityFilter,
  onFilterChange,
}) => {
  const severityPriority: Record<string, number> = {
    error: 0,
    warning: 1,
    info: 2,
  };

  const filteredAndSortedFindings = useMemo(() => {
    let result = [...findings];

    // Filter by severity
    if (severityFilter !== 'all') {
      result = result.filter((f) => f.severity === severityFilter);
    }

    // Sort
    result.sort((a, b) => {
      switch (sortOrder) {
        case 'severity':
          return severityPriority[a.severity] - severityPriority[b.severity];
        case 'page':
          return (a.page || 0) - (b.page || 0);
        case 'rule_id':
          return a.rule_id.localeCompare(b.rule_id);
        default:
          return 0;
      }
    });

    return result;
  }, [findings, severityFilter, sortOrder]);

  const filterOptions: { value: SeverityFilter; label: string; icon: string; count: number }[] = [
    {
      value: 'all',
      label: 'Todos',
      icon: 'List',
      count: findings.length,
    },
    {
      value: 'error',
      label: 'Erros',
      icon: 'XCircle',
      count: findings.filter((f) => f.severity === 'error').length,
    },
    {
      value: 'warning',
      label: 'Avisos',
      icon: 'AlertTriangle',
      count: findings.filter((f) => f.severity === 'warning').length,
    },
    {
      value: 'info',
      label: 'Info',
      icon: 'Info',
      count: findings.filter((f) => f.severity === 'info').length,
    },
  ];

  const sortOptions: { value: SortOrder; label: string }[] = [
    { value: 'severity', label: 'Severidade' },
    { value: 'page', label: 'Pagina' },
    { value: 'rule_id', label: 'Regra' },
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-border">
        <h3 className="text-sm font-semibold text-foreground mb-3">
          Problemas Encontrados
        </h3>

        {/* Filters */}
        <div className="flex flex-wrap gap-2 mb-3">
          {filterOptions.map((option) => (
            <button
              key={option.value}
              onClick={() => onFilterChange(option.value)}
              className={`
                inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors
                ${
                  severityFilter === option.value
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted/50 text-text-secondary hover:bg-muted'
                }
              `}
            >
              <Icon name={option.icon as any} size={14} />
              {option.label}
              <span
                className={`
                  px-1.5 py-0.5 rounded-full text-[10px]
                  ${
                    severityFilter === option.value
                      ? 'bg-primary-foreground/20 text-primary-foreground'
                      : 'bg-muted text-text-secondary'
                  }
                `}
              >
                {option.count}
              </span>
            </button>
          ))}
        </div>

        {/* Sort */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-secondary">Ordenar por:</span>
          <select
            value={sortOrder}
            onChange={(e) => onSortChange(e.target.value as SortOrder)}
            className="text-xs bg-muted/50 border border-border rounded-md px-2 py-1 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            {sortOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Findings List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {filteredAndSortedFindings.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Icon
              name="CheckCircle"
              size={48}
              className="text-success mb-3"
            />
            <p className="text-sm font-medium text-foreground mb-1">
              Nenhum problema encontrado
            </p>
            <p className="text-xs text-text-secondary">
              {severityFilter !== 'all'
                ? 'Tente mudar o filtro de severidade'
                : 'O documento esta em conformidade'}
            </p>
          </div>
        ) : (
          filteredAndSortedFindings.map((finding) => (
            <FindingItem
              key={finding.rule_id}
              finding={finding}
              isSelected={selectedFindingId === finding.rule_id}
              onSelect={() => onFindingSelect(finding)}
            />
          ))
        )}
      </div>

      {/* Summary Footer */}
      <div className="p-4 border-t border-border bg-muted/30">
        <div className="flex items-center justify-between text-xs text-text-secondary">
          <span>
            Mostrando {filteredAndSortedFindings.length} de {findings.length}{' '}
            {findings.length === 1 ? 'item' : 'itens'}
          </span>
          {selectedFindingId && (
            <button
              onClick={() => onFindingSelect(null as any)}
              className="text-primary hover:text-primary/80"
            >
              Limpar selecao
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default FindingsList;
