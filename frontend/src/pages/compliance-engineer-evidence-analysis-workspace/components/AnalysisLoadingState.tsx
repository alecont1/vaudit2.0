import React from 'react';
import Icon from '../../../components/AppIcon';

const AnalysisLoadingState: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 animate-fade-in">
      <div className="relative mb-6">
        <div className="absolute inset-0 animate-ping">
          <div className="w-24 h-24 rounded-full bg-primary/20" />
        </div>
        <div className="relative flex items-center justify-center w-24 h-24 rounded-full bg-primary/10">
          <div className="text-4xl animate-bounce">🤖</div>
        </div>
      </div>

      <h3 className="text-xl font-semibold text-foreground mb-2">
        AI is auditing...
      </h3>

      <p className="text-sm text-text-secondary text-center max-w-md mb-6">
        Our AI is analyzing your evidence document against compliance standards.
        This typically takes 10-30 seconds.
      </p>

      <div className="flex items-center gap-2 text-sm text-text-secondary">
        <div className="animate-spin">
          <Icon name="Loader2" size={20} strokeWidth={2} />
        </div>
        <span>Processing document...</span>
      </div>

      <div className="mt-8 w-full max-w-md">
        <div className="h-2 bg-muted rounded-full overflow-hidden">
          <div className="h-full bg-primary animate-pulse" style={{ width: '60%' }} />
        </div>
      </div>
    </div>
  );
};

export default AnalysisLoadingState;