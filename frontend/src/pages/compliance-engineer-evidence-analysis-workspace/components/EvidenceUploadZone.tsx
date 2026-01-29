import React, { useCallback, useState } from 'react';
import Icon from '../../../components/AppIcon';

import { FileUpload } from '../types';

interface EvidenceUploadZoneProps {
  onFilesSelected: (files: File[]) => void;
  isAnalyzing: boolean;
  uploadQueue: FileUpload[];
}

const EvidenceUploadZone: React.FC<EvidenceUploadZoneProps> = ({
  onFilesSelected,
  isAnalyzing,
  uploadQueue,
}) => {
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const files = Array.from(e.dataTransfer.files).filter(
        (file) =>
          file.type === 'application/pdf' || file.type.startsWith('image/')
      );

      if (files.length > 0) {
        onFilesSelected(files);
      }
    },
    [onFilesSelected]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files ? Array.from(e.target.files) : [];
      if (files.length > 0) {
        onFilesSelected(files);
      }
    },
    [onFilesSelected]
  );

  return (
    <div className="space-y-4">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative border-2 border-dashed rounded-lg p-8 transition-all duration-200 ${
          isDragging
            ? 'border-primary bg-primary/5 scale-[1.02]'
            : 'border-border bg-card hover:border-primary/50 hover:bg-muted/30'
        }`}
      >
        <input
          type="file"
          id="evidence-upload"
          multiple
          accept=".pdf,image/*"
          onChange={handleFileInput}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          disabled={isAnalyzing}
        />

        <div className="text-center pointer-events-none">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-4">
            <Icon name="Upload" size={32} className="text-primary" strokeWidth={2} />
          </div>

          <h3 className="text-lg font-semibold text-foreground mb-2">
            Upload Evidence Documents
          </h3>

          <p className="text-sm text-text-secondary mb-4">
            Drag and drop your files here, or click to browse
          </p>

          <div className="flex items-center justify-center gap-4 text-xs text-text-secondary">
            <div className="flex items-center gap-1">
              <Icon name="FileText" size={16} strokeWidth={2} />
              <span>PDF</span>
            </div>
            <div className="flex items-center gap-1">
              <Icon name="Image" size={16} strokeWidth={2} />
              <span>Images</span>
            </div>
            <div className="flex items-center gap-1">
              <Icon name="Layers" size={16} strokeWidth={2} />
              <span>Up to 50 files</span>
            </div>
          </div>
        </div>
      </div>

      {uploadQueue.length > 0 && (
        <div className="space-y-2 animate-fade-in">
          <h4 className="text-sm font-medium text-foreground">Upload Queue</h4>
          {uploadQueue.map((upload) => (
            <div
              key={upload.id}
              className="flex items-center gap-3 p-3 bg-muted rounded-lg"
            >
              <div className="flex-shrink-0">
                <Icon
                  name={upload.status === 'error' ? 'AlertCircle' : 'FileText'}
                  size={20}
                  className={
                    upload.status === 'error' ? 'text-error' : 'text-primary'
                  }
                  strokeWidth={2}
                />
              </div>

              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate">
                  {upload.file.name}
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <div className="flex-1 h-1.5 bg-background rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${
                        upload.status === 'error' ?'bg-error'
                          : upload.status === 'complete' ?'bg-success' :'bg-primary'
                      }`}
                      style={{ width: `${upload.progress}%` }}
                    />
                  </div>
                  <span className="text-xs text-text-secondary">
                    {upload.progress}%
                  </span>
                </div>
                {upload.error && (
                  <p className="text-xs text-error mt-1">{upload.error}</p>
                )}
              </div>

              <div className="flex-shrink-0">
                {upload.status === 'complete' && (
                  <Icon name="CheckCircle" size={20} className="text-success" />
                )}
                {upload.status === 'analyzing' && (
                  <div className="animate-spin">
                    <Icon name="Loader2" size={20} className="text-primary" />
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default EvidenceUploadZone;