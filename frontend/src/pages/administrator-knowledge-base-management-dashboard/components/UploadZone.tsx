import React, { useCallback, useState } from 'react';
import Icon from '../../../components/AppIcon';
import Button from '../../../components/ui/Button';
import { UploadProgress } from '../types';

interface UploadZoneProps {
  onFilesSelected: (files: File[]) => void;
  uploadProgress: UploadProgress[];
  isUploading: boolean;
}

const UploadZone: React.FC<UploadZoneProps> = ({
  onFilesSelected,
  uploadProgress,
  isUploading,
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
        (file) => file.type === 'application/pdf'
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
      e.target.value = '';
    },
    [onFilesSelected]
  );

  return (
    <div className="bg-card rounded-lg border border-border shadow-sm p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-foreground">
          Knowledge Base Upload
        </h2>
        <div className="flex items-center gap-2 text-sm text-text-secondary">
          <Icon name="Info" size={16} strokeWidth={2} />
          <span>PDF files only, up to 100 files</span>
        </div>
      </div>

      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative border-2 border-dashed rounded-lg p-12 transition-all duration-200 ${
          isDragging
            ? 'border-primary bg-primary/5' :'border-border bg-muted/30 hover:border-primary/50 hover:bg-muted/50'
        }`}
      >
        <input
          type="file"
          id="file-upload"
          multiple
          accept=".pdf"
          onChange={handleFileInput}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          disabled={isUploading}
        />

        <div className="flex flex-col items-center justify-center gap-4 pointer-events-none">
          <div className="flex items-center justify-center w-16 h-16 rounded-full bg-primary/10">
            <Icon
              name="Upload"
              size={32}
              color="var(--color-primary)"
              strokeWidth={2}
            />
          </div>

          <div className="text-center">
            <p className="text-lg font-medium text-foreground mb-1">
              {isDragging
                ? 'Drop files here' :'Drag and drop PDF files here'}
            </p>
            <p className="text-sm text-text-secondary">
              or click to browse your computer
            </p>
          </div>

          <Button
            variant="outline"
            iconName="FolderOpen"
            iconPosition="left"
            className="pointer-events-auto"
            disabled={isUploading}
          >
            Browse Files
          </Button>
        </div>
      </div>

      {uploadProgress.length > 0 && (
        <div className="mt-6 space-y-3">
          <h3 className="text-sm font-medium text-foreground">
            Upload Progress ({uploadProgress.length} files)
          </h3>
          {uploadProgress.map((file, index) => (
            <div
              key={index}
              className="bg-muted/50 rounded-lg p-4 border border-border"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <Icon
                    name={
                      file.status === 'complete'
                        ? 'CheckCircle2'
                        : file.status === 'error' ?'XCircle' :'FileText'
                    }
                    size={20}
                    color={
                      file.status === 'complete'
                        ? 'var(--color-success)'
                        : file.status === 'error' ?'var(--color-error)' :'var(--color-primary)'
                    }
                    strokeWidth={2}
                  />
                  <span className="text-sm font-medium text-foreground truncate">
                    {file.filename}
                  </span>
                </div>
                <span className="text-sm text-text-secondary ml-4">
                  {file.progress}%
                </span>
              </div>

              <div className="w-full bg-border rounded-full h-2 overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 ${
                    file.status === 'complete'
                      ? 'bg-success'
                      : file.status === 'error' ?'bg-error' :'bg-primary'
                  }`}
                  style={{ width: `${file.progress}%` }}
                />
              </div>

              {file.error && (
                <p className="text-xs text-error mt-2">{file.error}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default UploadZone;