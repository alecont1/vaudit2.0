import React, { useState } from 'react';
import Icon from '../../../components/AppIcon';
import Button from '../../../components/ui/Button';
import Input from '../../../components/ui/Input';
import Select from '../../../components/ui/Select';
import { KnowledgeDocument, DocumentMetadata } from '../types';

interface DocumentPreviewProps {
  document: KnowledgeDocument | null;
  onClose: () => void;
  onSave: (metadata: DocumentMetadata) => void;
}

const DocumentPreview: React.FC<DocumentPreviewProps> = ({
  document,
  onClose,
  onSave,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [metadata, setMetadata] = useState<DocumentMetadata | null>(
    document
      ? {
          id: document.id,
          filename: document.filename,
          category: document.category,
          tags: document.tags,
          description: document.description,
          version: document.version,
        }
      : null
  );

  if (!document || !metadata) {
    return (
      <div className="bg-card rounded-lg border border-border shadow-sm p-6">
        <div className="flex flex-col items-center justify-center py-16">
          <div className="flex items-center justify-center w-16 h-16 rounded-full bg-muted mb-4">
            <Icon
              name="FileText"
              size={32}
              color="var(--color-text-secondary)"
              strokeWidth={2}
            />
          </div>
          <p className="text-sm text-text-secondary">
            Select a document to view details
          </p>
        </div>
      </div>
    );
  }

  const categoryOptions = [
    { value: 'ISO 27001', label: 'ISO 27001' },
    { value: 'GDPR', label: 'GDPR' },
    { value: 'SOC 2', label: 'SOC 2' },
    { value: 'HIPAA', label: 'HIPAA' },
    { value: 'PCI DSS', label: 'PCI DSS' },
  ];

  const handleSave = () => {
    onSave(metadata);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setMetadata({
      id: document.id,
      filename: document.filename,
      category: document.category,
      tags: document.tags,
      description: document.description,
      version: document.version,
    });
    setIsEditing(false);
  };

  return (
    <div className="bg-card rounded-lg border border-border shadow-sm overflow-hidden">
      <div className="flex items-center justify-between p-4 border-b border-border bg-muted/30">
        <h3 className="text-sm font-semibold text-foreground">
          Document Details
        </h3>
        <Button
          variant="ghost"
          size="icon"
          iconName="X"
          onClick={onClose}
          aria-label="Close preview"
        />
      </div>

      <div className="p-6 space-y-6 max-h-[calc(100vh-300px)] overflow-y-auto">
        <div className="flex items-center justify-center w-full h-48 bg-muted/50 rounded-lg border border-border">
          <div className="text-center">
            <Icon
              name="FileText"
              size={48}
              color="var(--color-text-secondary)"
              strokeWidth={1.5}
            />
            <p className="text-sm text-text-secondary mt-2">PDF Preview</p>
          </div>
        </div>

        <div className="space-y-4">
          <Input
            label="Filename"
            type="text"
            value={metadata.filename}
            onChange={(e) =>
              setMetadata({ ...metadata, filename: e.target.value })
            }
            disabled={!isEditing}
          />

          <Select
            label="Category"
            options={categoryOptions}
            value={metadata.category}
            onChange={(value) =>
              setMetadata({ ...metadata, category: value as string })
            }
            disabled={!isEditing}
          />

          <Input
            label="Version"
            type="text"
            value={metadata.version}
            onChange={(e) =>
              setMetadata({ ...metadata, version: e.target.value })
            }
            disabled={!isEditing}
          />

          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Tags
            </label>
            <div className="flex flex-wrap gap-2">
              {metadata.tags.map((tag, index) => (
                <span
                  key={index}
                  className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary border border-primary/20"
                >
                  {tag}
                  {isEditing && (
                    <button
                      onClick={() =>
                        setMetadata({
                          ...metadata,
                          tags: metadata.tags.filter((_, i) => i !== index),
                        })
                      }
                      className="hover:text-error transition-colors"
                    >
                      <Icon name="X" size={12} strokeWidth={2} />
                    </button>
                  )}
                </span>
              ))}
              {isEditing && (
                <button className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-muted text-text-secondary border border-border hover:border-primary hover:text-primary transition-colors">
                  <Icon name="Plus" size={12} strokeWidth={2} />
                  Add Tag
                </button>
              )}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Description
            </label>
            <textarea
              value={metadata.description}
              onChange={(e) =>
                setMetadata({ ...metadata, description: e.target.value })
              }
              disabled={!isEditing}
              rows={4}
              className="w-full px-3 py-2 text-sm text-foreground bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed resize-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border">
            <div>
              <p className="text-xs text-text-secondary mb-1">Uploaded By</p>
              <p className="text-sm font-medium text-foreground">
                {document.uploadedBy}
              </p>
            </div>
            <div>
              <p className="text-xs text-text-secondary mb-1">File Size</p>
              <p className="text-sm font-medium text-foreground">
                {(document.fileSize / (1024 * 1024)).toFixed(2)} MB
              </p>
            </div>
            <div>
              <p className="text-xs text-text-secondary mb-1">Upload Date</p>
              <p className="text-sm font-medium text-foreground">
                {new Intl.DateTimeFormat('en-US', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                }).format(document.uploadDate)}
              </p>
            </div>
            <div>
              <p className="text-xs text-text-secondary mb-1">Last Modified</p>
              <p className="text-sm font-medium text-foreground">
                {new Intl.DateTimeFormat('en-US', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                }).format(document.lastModified)}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between gap-3 p-4 border-t border-border bg-muted/30">
        {isEditing ? (
          <>
            <Button variant="outline" onClick={handleCancel}>
              Cancel
            </Button>
            <Button variant="default" onClick={handleSave} iconName="Save">
              Save Changes
            </Button>
          </>
        ) : (
          <>
            <Button
              variant="outline"
              iconName="Download"
              iconPosition="left"
              fullWidth
            >
              Download
            </Button>
            <Button
              variant="default"
              iconName="Edit"
              iconPosition="left"
              onClick={() => setIsEditing(true)}
              fullWidth
            >
              Edit Metadata
            </Button>
          </>
        )}
      </div>
    </div>
  );
};

export default DocumentPreview;