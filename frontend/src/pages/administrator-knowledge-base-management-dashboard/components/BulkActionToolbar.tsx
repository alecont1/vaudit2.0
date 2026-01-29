import React from 'react';

import Button from '../../../components/ui/Button';


interface BulkActionToolbarProps {
  selectedCount: number;
  onCategorize: () => void;
  onDelete: () => void;
  onArchive: () => void;
  onActivate: () => void;
  onClearSelection: () => void;
}

const BulkActionToolbar: React.FC<BulkActionToolbarProps> = ({
  selectedCount,
  onCategorize,
  onDelete,
  onArchive,
  onActivate,
  onClearSelection,
}) => {
  if (selectedCount === 0) return null;

  return (
    <div className="bg-primary text-primary-foreground rounded-lg shadow-elevated p-4 mb-4 animate-slide-in-right">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary-foreground/20">
            <span className="text-sm font-semibold">{selectedCount}</span>
          </div>
          <span className="text-sm font-medium">
            {selectedCount === 1
              ? '1 document selected'
              : `${selectedCount} documents selected`}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            iconName="Tag"
            iconPosition="left"
            onClick={onCategorize}
            className="text-primary-foreground hover:bg-primary-foreground/10"
          >
            Categorize
          </Button>

          <Button
            variant="ghost"
            size="sm"
            iconName="CheckCircle2"
            iconPosition="left"
            onClick={onActivate}
            className="text-primary-foreground hover:bg-primary-foreground/10"
          >
            Activate
          </Button>

          <Button
            variant="ghost"
            size="sm"
            iconName="Archive"
            iconPosition="left"
            onClick={onArchive}
            className="text-primary-foreground hover:bg-primary-foreground/10"
          >
            Archive
          </Button>

          <Button
            variant="ghost"
            size="sm"
            iconName="Trash2"
            iconPosition="left"
            onClick={onDelete}
            className="text-primary-foreground hover:bg-primary-foreground/10"
          >
            Delete
          </Button>

          <div className="w-px h-6 bg-primary-foreground/20 mx-2" />

          <Button
            variant="ghost"
            size="sm"
            iconName="X"
            onClick={onClearSelection}
            className="text-primary-foreground hover:bg-primary-foreground/10"
            aria-label="Clear selection"
          />
        </div>
      </div>
    </div>
  );
};

export default BulkActionToolbar;