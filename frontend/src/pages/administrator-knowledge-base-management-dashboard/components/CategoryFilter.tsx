import React from 'react';
import Icon from '../../../components/AppIcon';
import { ComplianceCategory } from '../types';

interface CategoryFilterProps {
  categories: ComplianceCategory[];
  selectedCategory: string;
  onCategorySelect: (categoryId: string) => void;
}

const CategoryFilter: React.FC<CategoryFilterProps> = ({
  categories,
  selectedCategory,
  onCategorySelect,
}) => {
  const renderCategory = (category: ComplianceCategory, level: number = 0) => {
    const isSelected = selectedCategory === category.id;
    const hasSubcategories =
      category.subcategories && category.subcategories.length > 0;

    return (
      <div key={category.id}>
        <button
          onClick={() => onCategorySelect(category.id)}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-sm transition-colors duration-150 ${
            isSelected
              ? 'bg-primary text-primary-foreground font-medium'
              : 'text-text-secondary hover:bg-muted hover:text-foreground'
          }`}
          style={{ paddingLeft: `${12 + level * 16}px` }}
        >
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <Icon
              name={hasSubcategories ? 'FolderOpen' : 'Folder'}
              size={16}
              strokeWidth={2}
            />
            <span className="truncate">{category.name}</span>
          </div>
          <span
            className={`text-xs px-2 py-0.5 rounded-full ${
              isSelected
                ? 'bg-primary-foreground/20'
                : 'bg-muted text-text-secondary'
            }`}
          >
            {category.documentCount}
          </span>
        </button>

        {hasSubcategories &&
          category.subcategories!.map((sub) => renderCategory(sub, level + 1))}
      </div>
    );
  };

  return (
    <div className="bg-card rounded-lg border border-border shadow-sm p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-foreground">
          Compliance Categories
        </h3>
        <button
          onClick={() => onCategorySelect('all')}
          className="text-xs text-primary hover:underline"
        >
          Clear
        </button>
      </div>

      <div className="space-y-1 max-h-[600px] overflow-y-auto">
        <button
          onClick={() => onCategorySelect('all')}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-sm transition-colors duration-150 ${
            selectedCategory === 'all' ?'bg-primary text-primary-foreground font-medium' :'text-text-secondary hover:bg-muted hover:text-foreground'
          }`}
        >
          <div className="flex items-center gap-2">
            <Icon name="LayoutGrid" size={16} strokeWidth={2} />
            <span>All Documents</span>
          </div>
          <span
            className={`text-xs px-2 py-0.5 rounded-full ${
              selectedCategory === 'all' ?'bg-primary-foreground/20' :'bg-muted text-text-secondary'
            }`}
          >
            {categories.reduce((sum, cat) => sum + cat.documentCount, 0)}
          </span>
        </button>

        {categories.map((category) => renderCategory(category))}
      </div>
    </div>
  );
};

export default CategoryFilter;