import React from 'react';
import { PDFHighlight } from '../types';

interface PDFHighlightOverlayProps {
  highlights: PDFHighlight[];
  activeHighlightId: string | null;
  containerWidth: number;
  containerHeight: number;
}

const PDFHighlightOverlay: React.FC<PDFHighlightOverlayProps> = ({
  highlights,
  activeHighlightId,
  containerWidth,
  containerHeight,
}) => {
  const getSeverityColors = (severity: 'error' | 'warning' | 'info', isActive: boolean) => {
    const opacity = isActive ? 0.4 : 0.25;
    const borderOpacity = isActive ? 1 : 0.6;

    switch (severity) {
      case 'error':
        return {
          bg: `rgba(239, 68, 68, ${opacity})`,
          border: `rgba(239, 68, 68, ${borderOpacity})`,
        };
      case 'warning':
        return {
          bg: `rgba(245, 158, 11, ${opacity})`,
          border: `rgba(245, 158, 11, ${borderOpacity})`,
        };
      case 'info':
        return {
          bg: `rgba(59, 130, 246, ${opacity})`,
          border: `rgba(59, 130, 246, ${borderOpacity})`,
        };
      default:
        return {
          bg: `rgba(107, 114, 128, ${opacity})`,
          border: `rgba(107, 114, 128, ${borderOpacity})`,
        };
    }
  };

  return (
    <div
      className="absolute inset-0 pointer-events-none"
      style={{ width: containerWidth, height: containerHeight }}
    >
      {highlights.map((highlight) => {
        const isActive = highlight.id === activeHighlightId;
        const colors = getSeverityColors(highlight.severity, isActive);

        // Convert normalized coordinates (0-1) to percentages
        const left = highlight.bbox.left * 100;
        const top = highlight.bbox.top * 100;
        const width = (highlight.bbox.right - highlight.bbox.left) * 100;
        const height = (highlight.bbox.bottom - highlight.bbox.top) * 100;

        return (
          <div
            key={highlight.id}
            className={`absolute transition-all duration-300 ${
              isActive ? 'animate-pulse z-10' : 'z-0'
            }`}
            style={{
              left: `${left}%`,
              top: `${top}%`,
              width: `${width}%`,
              height: `${height}%`,
              backgroundColor: colors.bg,
              border: `2px solid ${colors.border}`,
              borderRadius: '4px',
              boxShadow: isActive ? `0 0 12px ${colors.border}` : 'none',
            }}
          />
        );
      })}
    </div>
  );
};

export default PDFHighlightOverlay;
