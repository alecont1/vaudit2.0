import React, { useState, useEffect } from 'react';
import Icon from '../../../components/AppIcon';

import Select from '../../../components/ui/Select';

interface SearchBarProps {
  onSearch: (query: string) => void;
  onStatusFilter: (status: string) => void;
  onExport: () => void;
}

const SearchBar: React.FC<SearchBarProps> = ({
  onSearch,
  onStatusFilter,
  onExport,
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      onSearch(searchQuery);
    }, 300);

    return () => clearTimeout(debounceTimer);
  }, [searchQuery, onSearch]);

  const statusOptions = [
    { value: 'all', label: 'All Status' },
    { value: 'active', label: 'Active' },
    { value: 'archived', label: 'Archived' },
    { value: 'pending', label: 'Pending' },
    { value: 'processing', label: 'Processing' },
  ];

  return (
    <div className="bg-card rounded-lg border border-border shadow-sm p-4">
      <div className="flex items-center gap-3">
        <div className="flex-1 relative">
          <Icon
            name="Search"
            size={18}
            strokeWidth={2}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary pointer-events-none"
          />
          <input
            type="text"
            placeholder="Search documents by filename, category, or content..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 text-sm text-foreground bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-foreground transition-colors"
              aria-label="Clear search"
            >
              <Icon name="X" size={16} strokeWidth={2} />
            </button>
          )}
        </div>

        <div className="w-48">
          <Select
            options={statusOptions}
            value="all"
            onChange={(value) => onStatusFilter(value as string)}
            placeholder="Filter by status"
          />
        </div>

        <button
          onClick={onExport}
          className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-foreground bg-background border border-border rounded-md hover:bg-muted transition-colors"
        >
          <Icon name="Download" size={18} strokeWidth={2} />
          <span>Export</span>
        </button>
      </div>

      <div className="flex items-center gap-2 mt-3 text-xs text-text-secondary">
        <Icon name="Info" size={14} strokeWidth={2} />
        <span>
          Use Ctrl+F for quick search • Del to delete selected • Ctrl+U to
          upload
        </span>
      </div>
    </div>
  );
};

export default SearchBar;