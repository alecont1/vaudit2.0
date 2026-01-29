import React, { useState } from 'react';
import Icon from '../../../components/AppIcon';
import Button from '../../../components/ui/Button';
import { Checkbox } from '../../../components/ui/Checkbox';
import { KnowledgeDocument, SortConfig } from '../types';

interface DocumentTableProps {
  documents: KnowledgeDocument[];
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  onDocumentClick: (document: KnowledgeDocument) => void;
  onSort: (config: SortConfig) => void;
  sortConfig: SortConfig;
}

const DocumentTable: React.FC<DocumentTableProps> = ({
  documents,
  selectedIds,
  onSelectionChange,
  onDocumentClick,
  onSort,
  sortConfig,
}) => {
  const [hoveredRow, setHoveredRow] = useState<string | null>(null);

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      onSelectionChange(documents.map((doc) => doc.id));
    } else {
      onSelectionChange([]);
    }
  };

  const handleSelectOne = (id: string, checked: boolean) => {
    if (checked) {
      onSelectionChange([...selectedIds, id]);
    } else {
      onSelectionChange(selectedIds.filter((selectedId) => selectedId !== id));
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (date: Date): string => {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  const getStatusColor = (status: KnowledgeDocument['status']) => {
    switch (status) {
      case 'active':
        return 'bg-success/10 text-success border-success/20';
      case 'archived':
        return 'bg-muted text-text-secondary border-border';
      case 'pending':
        return 'bg-warning/10 text-warning border-warning/20';
      case 'processing':
        return 'bg-primary/10 text-primary border-primary/20';
      default:
        return 'bg-muted text-text-secondary border-border';
    }
  };

  const handleSort = (field: keyof KnowledgeDocument) => {
    const direction =
      sortConfig.field === field && sortConfig.direction === 'asc' ?'desc' :'asc';
    onSort({ field, direction });
  };

  const renderSortIcon = (field: keyof KnowledgeDocument) => {
    if (sortConfig.field !== field) {
      return <Icon name="ChevronsUpDown" size={14} strokeWidth={2} />;
    }
    return sortConfig.direction === 'asc' ? (
      <Icon name="ChevronUp" size={14} strokeWidth={2} />
    ) : (
      <Icon name="ChevronDown" size={14} strokeWidth={2} />
    );
  };

  return (
    <div className="bg-card rounded-lg border border-border shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-muted/50 border-b border-border">
            <tr>
              <th className="px-4 py-3 text-left w-12">
                <Checkbox
                  checked={
                    documents.length > 0 &&
                    selectedIds.length === documents.length
                  }
                  onChange={(e) => handleSelectAll(e.target.checked)}
                  aria-label="Select all documents"
                />
              </th>
              <th className="px-4 py-3 text-left">
                <button
                  onClick={() => handleSort('filename')}
                  className="flex items-center gap-2 text-xs font-semibold text-foreground hover:text-primary transition-colors"
                >
                  Filename
                  {renderSortIcon('filename')}
                </button>
              </th>
              <th className="px-4 py-3 text-left">
                <button
                  onClick={() => handleSort('category')}
                  className="flex items-center gap-2 text-xs font-semibold text-foreground hover:text-primary transition-colors"
                >
                  Category
                  {renderSortIcon('category')}
                </button>
              </th>
              <th className="px-4 py-3 text-left">
                <button
                  onClick={() => handleSort('status')}
                  className="flex items-center gap-2 text-xs font-semibold text-foreground hover:text-primary transition-colors"
                >
                  Status
                  {renderSortIcon('status')}
                </button>
              </th>
              <th className="px-4 py-3 text-left">
                <button
                  onClick={() => handleSort('fileSize')}
                  className="flex items-center gap-2 text-xs font-semibold text-foreground hover:text-primary transition-colors"
                >
                  Size
                  {renderSortIcon('fileSize')}
                </button>
              </th>
              <th className="px-4 py-3 text-left">
                <button
                  onClick={() => handleSort('uploadDate')}
                  className="flex items-center gap-2 text-xs font-semibold text-foreground hover:text-primary transition-colors"
                >
                  Upload Date
                  {renderSortIcon('uploadDate')}
                </button>
              </th>
              <th className="px-4 py-3 text-left">
                <button
                  onClick={() => handleSort('lastModified')}
                  className="flex items-center gap-2 text-xs font-semibold text-foreground hover:text-primary transition-colors"
                >
                  Last Modified
                  {renderSortIcon('lastModified')}
                </button>
              </th>
              <th className="px-4 py-3 text-center w-24">
                <span className="text-xs font-semibold text-foreground">
                  Actions
                </span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {documents.map((doc) => (
              <tr
                key={doc.id}
                onMouseEnter={() => setHoveredRow(doc.id)}
                onMouseLeave={() => setHoveredRow(null)}
                className={`transition-colors duration-150 ${
                  selectedIds.includes(doc.id)
                    ? 'bg-primary/5'
                    : hoveredRow === doc.id
                    ? 'bg-muted/30' :''
                }`}
              >
                <td className="px-4 py-3">
                  <Checkbox
                    checked={selectedIds.includes(doc.id)}
                    onChange={(e) => handleSelectOne(doc.id, e.target.checked)}
                    aria-label={`Select ${doc.filename}`}
                  />
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => onDocumentClick(doc)}
                    className="flex items-center gap-2 text-sm text-foreground hover:text-primary transition-colors group"
                  >
                    <Icon
                      name="FileText"
                      size={16}
                      strokeWidth={2}
                      className="text-text-secondary group-hover:text-primary"
                    />
                    <span className="font-medium truncate max-w-xs">
                      {doc.filename}
                    </span>
                  </button>
                </td>
                <td className="px-4 py-3">
                  <span className="text-sm text-text-secondary">
                    {doc.category}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(
                      doc.status
                    )}`}
                  >
                    {doc.status === 'active' && (
                      <Icon name="CheckCircle2" size={12} strokeWidth={2} />
                    )}
                    {doc.status === 'processing' && (
                      <Icon name="Loader2" size={12} strokeWidth={2} />
                    )}
                    {doc.status === 'pending' && (
                      <Icon name="Clock" size={12} strokeWidth={2} />
                    )}
                    {doc.status === 'archived' && (
                      <Icon name="Archive" size={12} strokeWidth={2} />
                    )}
                    {doc.status.charAt(0).toUpperCase() + doc.status.slice(1)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-sm text-text-secondary">
                    {formatFileSize(doc.fileSize)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-sm text-text-secondary">
                    {formatDate(doc.uploadDate)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-sm text-text-secondary">
                    {formatDate(doc.lastModified)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      iconName="Eye"
                      onClick={() => onDocumentClick(doc)}
                      aria-label="View document"
                    />
                    <Button
                      variant="ghost"
                      size="icon"
                      iconName="Download"
                      aria-label="Download document"
                    />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {documents.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 px-4">
          <div className="flex items-center justify-center w-16 h-16 rounded-full bg-muted mb-4">
            <Icon
              name="FileX"
              size={32}
              color="var(--color-text-secondary)"
              strokeWidth={2}
            />
          </div>
          <p className="text-lg font-medium text-foreground mb-1">
            No documents found
          </p>
          <p className="text-sm text-text-secondary">
            Upload PDF files to get started
          </p>
        </div>
      )}
    </div>
  );
};

export default DocumentTable;