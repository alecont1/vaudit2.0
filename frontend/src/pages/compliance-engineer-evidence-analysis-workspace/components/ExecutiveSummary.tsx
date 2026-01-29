import React from 'react';
import Icon from '../../../components/AppIcon';
import { ValidationStatus, AnalysisFinding } from '../types';

interface ExecutiveSummaryProps {
  status: ValidationStatus;
  findings: AnalysisFinding[];
  fileName: string;
  validatedAt: Date;
}

const ExecutiveSummary: React.FC<ExecutiveSummaryProps> = ({
  status,
  findings,
  fileName,
  validatedAt,
}) => {
  const errorCount = findings.filter((f) => f.severity === 'error').length;
  const warningCount = findings.filter((f) => f.severity === 'warning').length;
  const infoCount = findings.filter((f) => f.severity === 'info').length;

  const getStatusConfig = () => {
    switch (status) {
      case 'APPROVED':
        return {
          icon: 'CheckCircle',
          label: 'Aprovado',
          bgClass: 'bg-success/10',
          textClass: 'text-success',
          borderClass: 'border-success',
        };
      case 'REJECTED':
        return {
          icon: 'XCircle',
          label: 'Rejeitado',
          bgClass: 'bg-error/10',
          textClass: 'text-error',
          borderClass: 'border-error',
        };
      case 'REVIEW_NEEDED':
        return {
          icon: 'AlertTriangle',
          label: 'Revisao Necessaria',
          bgClass: 'bg-warning/10',
          textClass: 'text-warning',
          borderClass: 'border-warning',
        };
      case 'PENDING':
        return {
          icon: 'Clock',
          label: 'Pendente',
          bgClass: 'bg-muted/50',
          textClass: 'text-text-secondary',
          borderClass: 'border-border',
        };
      case 'FAILED':
        return {
          icon: 'XOctagon',
          label: 'Falhou',
          bgClass: 'bg-error/10',
          textClass: 'text-error',
          borderClass: 'border-error',
        };
      default:
        return {
          icon: 'HelpCircle',
          label: 'Desconhecido',
          bgClass: 'bg-muted/50',
          textClass: 'text-text-secondary',
          borderClass: 'border-border',
        };
    }
  };

  const getSummaryText = (): string => {
    if (status === 'APPROVED') {
      return 'Documento validado com sucesso. Todos os criterios de conformidade foram atendidos.';
    }

    if (status === 'REJECTED') {
      const criticalFindings = findings.filter((f) => f.severity === 'error');
      if (criticalFindings.length > 0) {
        const mainIssue = criticalFindings[0];
        return `Documento rejeitado: ${mainIssue.message}`;
      }
      return 'Documento rejeitado devido a problemas criticos de conformidade.';
    }

    if (status === 'REVIEW_NEEDED') {
      return 'Documento requer revisao manual. Alguns itens precisam de verificacao adicional.';
    }

    return 'Aguardando processamento do documento.';
  };

  const getRecommendedAction = (): string => {
    if (status === 'APPROVED') {
      return 'Nenhuma acao necessaria. O documento pode ser arquivado.';
    }

    if (status === 'REJECTED') {
      const criticalFindings = findings.filter((f) => f.severity === 'error');
      if (criticalFindings.some((f) => f.rule_id?.includes('calibration') || f.rule_id?.includes('expired'))) {
        return 'Solicite um novo certificado de calibracao atualizado.';
      }
      if (criticalFindings.some((f) => f.rule_id?.includes('serial'))) {
        return 'Verifique o numero de serie do equipamento e solicite correcao.';
      }
      return 'Corrija os problemas identificados e reenvie o documento.';
    }

    if (status === 'REVIEW_NEEDED') {
      return 'Revise manualmente os itens sinalizados antes de aprovar.';
    }

    return 'Aguarde a conclusao do processamento.';
  };

  const statusConfig = getStatusConfig();

  return (
    <div className="bg-card border border-border rounded-lg p-6 mb-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-foreground mb-1">
            Resumo Executivo
          </h2>
          <p className="text-sm text-text-secondary">
            {fileName} - Validado em{' '}
            {new Date(validatedAt).toLocaleDateString('pt-BR', {
              day: '2-digit',
              month: 'short',
              year: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
        </div>

        <div
          className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-sm border-2 ${statusConfig.bgClass} ${statusConfig.textClass} ${statusConfig.borderClass}`}
        >
          <Icon name={statusConfig.icon as any} size={20} strokeWidth={2.5} />
          <span>{statusConfig.label}</span>
        </div>
      </div>

      <div className="flex gap-4 mb-4">
        {errorCount > 0 && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-error/10 rounded-md">
            <Icon name="XCircle" size={16} className="text-error" />
            <span className="text-sm font-medium text-error">
              {errorCount} {errorCount === 1 ? 'Erro' : 'Erros'}
            </span>
          </div>
        )}
        {warningCount > 0 && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-warning/10 rounded-md">
            <Icon name="AlertTriangle" size={16} className="text-warning" />
            <span className="text-sm font-medium text-warning">
              {warningCount} {warningCount === 1 ? 'Aviso' : 'Avisos'}
            </span>
          </div>
        )}
        {infoCount > 0 && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-primary/10 rounded-md">
            <Icon name="Info" size={16} className="text-primary" />
            <span className="text-sm font-medium text-primary">
              {infoCount} {infoCount === 1 ? 'Info' : 'Infos'}
            </span>
          </div>
        )}
        {errorCount === 0 && warningCount === 0 && infoCount === 0 && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-success/10 rounded-md">
            <Icon name="CheckCircle" size={16} className="text-success" />
            <span className="text-sm font-medium text-success">
              Nenhum problema encontrado
            </span>
          </div>
        )}
      </div>

      <div className="space-y-3">
        <div className="bg-muted/30 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <Icon name="FileText" size={18} className="text-text-secondary mt-0.5" />
            <div>
              <p className="text-sm font-medium text-foreground mb-1">Resumo</p>
              <p className="text-sm text-text-secondary">{getSummaryText()}</p>
            </div>
          </div>
        </div>

        <div className="bg-muted/30 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <Icon name="Lightbulb" size={18} className="text-primary mt-0.5" />
            <div>
              <p className="text-sm font-medium text-foreground mb-1">
                Acao Recomendada
              </p>
              <p className="text-sm text-text-secondary">{getRecommendedAction()}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExecutiveSummary;
