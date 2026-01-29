import React, { useState, useEffect, useCallback } from 'react';
import RoleBasedHeader from '../../components/ui/RoleBasedHeader';
import UploadZone from './components/UploadZone';
import CategoryFilter from './components/CategoryFilter';
import DocumentTable from './components/DocumentTable';
import BulkActionToolbar from './components/BulkActionToolbar';
import DocumentPreview from './components/DocumentPreview';
import SearchBar from './components/SearchBar';
import {
  KnowledgeDocument,
  ComplianceCategory,
  UploadProgress,
  FilterState,
  DocumentMetadata,
  SortConfig,
} from './types';

const AdministratorKnowledgeBaseDashboard: React.FC = () => {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [filteredDocuments, setFilteredDocuments] = useState<
    KnowledgeDocument[]
  >([]);
  const [selectedDocument, setSelectedDocument] =
    useState<KnowledgeDocument | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [filterState, setFilterState] = useState<FilterState>({
    category: 'all',
    status: 'all',
    searchQuery: '',
    dateRange: { start: null, end: null },
  });
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    field: 'uploadDate',
    direction: 'desc',
  });

  const categories: ComplianceCategory[] = [
    {
      id: 'iso-27001',
      name: 'ISO 27001',
      documentCount: 45,
      subcategories: [
        { id: 'iso-27001-controls', name: 'Security Controls', documentCount: 23 },
        { id: 'iso-27001-policies', name: 'Policies', documentCount: 22 },
      ],
    },
    {
      id: 'gdpr',
      name: 'GDPR',
      documentCount: 38,
      subcategories: [
        { id: 'gdpr-articles', name: 'Articles', documentCount: 20 },
        { id: 'gdpr-guidelines', name: 'Guidelines', documentCount: 18 },
      ],
    },
    {
      id: 'soc2',
      name: 'SOC 2',
      documentCount: 32,
      subcategories: [
        { id: 'soc2-trust', name: 'Trust Principles', documentCount: 15 },
        { id: 'soc2-criteria', name: 'Criteria', documentCount: 17 },
      ],
    },
    { id: 'hipaa', name: 'HIPAA', documentCount: 28 },
    { id: 'pci-dss', name: 'PCI DSS', documentCount: 25 },
  ];

  const mockDocuments: KnowledgeDocument[] = [
    {
      id: 'doc-001',
      filename: 'ISO_27001_Information_Security_Controls.pdf',
      uploadDate: new Date('2024-01-15T10:30:00'),
      fileSize: 2457600,
      category: 'ISO 27001',
      status: 'active',
      lastModified: new Date('2024-01-20T14:22:00'),
      uploadedBy: 'Sarah Johnson',
      version: '2.1',
      tags: ['security', 'controls', 'compliance'],
      description:
        'Comprehensive guide to ISO 27001 information security controls implementation and best practices.',
    },
    {
      id: 'doc-002',
      filename: 'GDPR_Data_Protection_Guidelines.pdf',
      uploadDate: new Date('2024-01-18T09:15:00'),
      fileSize: 3145728,
      category: 'GDPR',
      status: 'active',
      lastModified: new Date('2024-01-22T11:45:00'),
      uploadedBy: 'Michael Chen',
      version: '1.5',
      tags: ['gdpr', 'data protection', 'privacy'],
      description:
        'Official GDPR guidelines for data protection and privacy compliance in the European Union.',
    },
    {
      id: 'doc-003',
      filename: 'SOC2_Trust_Services_Criteria.pdf',
      uploadDate: new Date('2024-01-20T13:45:00'),
      fileSize: 1835008,
      category: 'SOC 2',
      status: 'processing',
      lastModified: new Date('2024-01-20T13:45:00'),
      uploadedBy: 'Emily Rodriguez',
      version: '3.0',
      tags: ['soc2', 'trust services', 'audit'],
      description:
        'SOC 2 Trust Services Criteria documentation for security, availability, and confidentiality assessments.',
    },
    {
      id: 'doc-004',
      filename: 'HIPAA_Privacy_Rule_Implementation.pdf',
      uploadDate: new Date('2024-01-12T16:20:00'),
      fileSize: 2097152,
      category: 'HIPAA',
      status: 'active',
      lastModified: new Date('2024-01-19T10:30:00'),
      uploadedBy: 'David Martinez',
      version: '2.3',
      tags: ['hipaa', 'privacy', 'healthcare'],
      description:
        'HIPAA Privacy Rule implementation guide for healthcare organizations and covered entities.',
    },
    {
      id: 'doc-005',
      filename: 'PCI_DSS_Payment_Security_Standards.pdf',
      uploadDate: new Date('2024-01-10T11:00:00'),
      fileSize: 2621440,
      category: 'PCI DSS',
      status: 'archived',
      lastModified: new Date('2024-01-15T09:15:00'),
      uploadedBy: 'Jennifer Lee',
      version: '1.8',
      tags: ['pci', 'payment security', 'compliance'],
      description:
        'PCI DSS payment card industry data security standards for secure payment processing.',
    },
    {
      id: 'doc-006',
      filename: 'ISO_27001_Risk_Assessment_Framework.pdf',
      uploadDate: new Date('2024-01-22T14:30:00'),
      fileSize: 1572864,
      category: 'ISO 27001',
      status: 'pending',
      lastModified: new Date('2024-01-22T14:30:00'),
      uploadedBy: 'Robert Taylor',
      version: '1.0',
      tags: ['risk assessment', 'iso 27001', 'framework'],
      description:
        'Risk assessment framework and methodology for ISO 27001 compliance implementation.',
    },
    {
      id: 'doc-007',
      filename: 'GDPR_Breach_Notification_Procedures.pdf',
      uploadDate: new Date('2024-01-08T10:45:00'),
      fileSize: 1310720,
      category: 'GDPR',
      status: 'active',
      lastModified: new Date('2024-01-16T13:20:00'),
      uploadedBy: 'Amanda White',
      version: '2.0',
      tags: ['gdpr', 'breach notification', 'incident response'],
      description:
        'GDPR data breach notification procedures and timeline requirements for compliance officers.',
    },
    {
      id: 'doc-008',
      filename: 'SOC2_Security_Monitoring_Controls.pdf',
      uploadDate: new Date('2024-01-25T09:30:00'),
      fileSize: 2883584,
      category: 'SOC 2',
      status: 'active',
      lastModified: new Date('2024-01-25T15:45:00'),
      uploadedBy: 'Christopher Brown',
      version: '1.2',
      tags: ['soc2', 'monitoring', 'security controls'],
      description:
        'SOC 2 security monitoring controls and continuous compliance assessment procedures.',
    },
    {
      id: 'doc-009',
      filename: 'HIPAA_Security_Rule_Technical_Safeguards.pdf',
      uploadDate: new Date('2024-01-14T12:15:00'),
      fileSize: 2359296,
      category: 'HIPAA',
      status: 'active',
      lastModified: new Date('2024-01-21T11:00:00'),
      uploadedBy: 'Jessica Anderson',
      version: '3.1',
      tags: ['hipaa', 'security rule', 'technical safeguards'],
      description:
        'HIPAA Security Rule technical safeguards implementation guide for electronic protected health information.',
    },
    {
      id: 'doc-010',
      filename: 'PCI_DSS_Network_Security_Requirements.pdf',
      uploadDate: new Date('2024-01-17T15:00:00'),
      fileSize: 1966080,
      category: 'PCI DSS',
      status: 'active',
      lastModified: new Date('2024-01-23T10:30:00'),
      uploadedBy: 'Matthew Wilson',
      version: '2.5',
      tags: ['pci dss', 'network security', 'requirements'],
      description:
        'PCI DSS network security requirements and implementation guidelines for cardholder data environments.',
    },
  ];

  useEffect(() => {
    setDocuments(mockDocuments);
    setFilteredDocuments(mockDocuments);
  }, []);

  useEffect(() => {
    let filtered = [...documents];

    if (filterState.category !== 'all') {
      filtered = filtered.filter((doc) =>
        doc.category.toLowerCase().includes(filterState.category.toLowerCase())
      );
    }

    if (filterState.status !== 'all') {
      filtered = filtered.filter((doc) => doc.status === filterState.status);
    }

    if (filterState.searchQuery) {
      const query = filterState.searchQuery.toLowerCase();
      filtered = filtered.filter(
        (doc) =>
          doc.filename.toLowerCase().includes(query) ||
          doc.category.toLowerCase().includes(query) ||
          doc.description.toLowerCase().includes(query) ||
          doc.tags.some((tag) => tag.toLowerCase().includes(query))
      );
    }

    filtered.sort((a, b) => {
      const aValue = a[sortConfig.field];
      const bValue = b[sortConfig.field];

      if (aValue instanceof Date && bValue instanceof Date) {
        return sortConfig.direction === 'asc'
          ? aValue.getTime() - bValue.getTime()
          : bValue.getTime() - aValue.getTime();
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortConfig.direction === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortConfig.direction === 'asc'
          ? aValue - bValue
          : bValue - aValue;
      }

      return 0;
    });

    setFilteredDocuments(filtered);
  }, [documents, filterState, sortConfig]);

  const handleFilesSelected = useCallback((files: File[]) => {
    setIsUploading(true);
    const newProgress: UploadProgress[] = files.map((file) => ({
      filename: file.name,
      progress: 0,
      status: 'uploading',
    }));
    setUploadProgress(newProgress);

    files.forEach((file, index) => {
      const interval = setInterval(() => {
        setUploadProgress((prev) => {
          const updated = [...prev];
          if (updated[index].progress < 100) {
            updated[index].progress += 10;
          } else {
            updated[index].status = 'processing';
            clearInterval(interval);

            setTimeout(() => {
              setUploadProgress((prev) => {
                const final = [...prev];
                final[index].status = 'complete';
                return final;
              });

              const newDoc: KnowledgeDocument = {
                id: `doc-${Date.now()}-${index}`,
                filename: file.name,
                uploadDate: new Date(),
                fileSize: file.size,
                category: 'ISO 27001',
                status: 'active',
                lastModified: new Date(),
                uploadedBy: 'System Administrator',
                version: '1.0',
                tags: ['new', 'uploaded'],
                description: 'Recently uploaded document',
              };

              setDocuments((prev) => [newDoc, ...prev]);
            }, 1000);
          }
          return updated;
        });
      }, 200);
    });

    setTimeout(() => {
      setIsUploading(false);
      setTimeout(() => setUploadProgress([]), 3000);
    }, files.length * 2500);
  }, []);

  const handleCategorySelect = useCallback((categoryId: string) => {
    setFilterState((prev) => ({ ...prev, category: categoryId }));
  }, []);

  const handleSearch = useCallback((query: string) => {
    setFilterState((prev) => ({ ...prev, searchQuery: query }));
  }, []);

  const handleStatusFilter = useCallback((status: string) => {
    setFilterState((prev) => ({ ...prev, status }));
  }, []);

  const handleSort = useCallback((config: SortConfig) => {
    setSortConfig(config);
  }, []);

  const handleDocumentClick = useCallback((document: KnowledgeDocument) => {
    setSelectedDocument(document);
  }, []);

  const handleSaveMetadata = useCallback((metadata: DocumentMetadata) => {
    setDocuments((prev) =>
      prev.map((doc) =>
        doc.id === metadata.id
          ? {
              ...doc,
              filename: metadata.filename,
              category: metadata.category,
              tags: metadata.tags,
              description: metadata.description,
              version: metadata.version,
              lastModified: new Date(),
            }
          : doc
      )
    );
  }, []);

  const handleBulkCategorize = useCallback(() => {
    console.log('Bulk categorize:', selectedIds);
  }, [selectedIds]);

  const handleBulkDelete = useCallback(() => {
    setDocuments((prev) => prev.filter((doc) => !selectedIds.includes(doc.id)));
    setSelectedIds([]);
  }, [selectedIds]);

  const handleBulkArchive = useCallback(() => {
    setDocuments((prev) =>
      prev.map((doc) =>
        selectedIds.includes(doc.id) ? { ...doc, status: 'archived' as const } : doc
      )
    );
    setSelectedIds([]);
  }, [selectedIds]);

  const handleBulkActivate = useCallback(() => {
    setDocuments((prev) =>
      prev.map((doc) =>
        selectedIds.includes(doc.id) ? { ...doc, status: 'active' as const } : doc
      )
    );
    setSelectedIds([]);
  }, [selectedIds]);

  const handleExport = useCallback(() => {
    console.log('Exporting documents...');
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'u') {
        e.preventDefault();
        document.getElementById('file-upload')?.click();
      }
      if (e.key === 'Delete' && selectedIds.length > 0) {
        handleBulkDelete();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedIds, handleBulkDelete]);

  return (
    <div className="min-h-screen bg-background">
      <RoleBasedHeader userRole="admin" />

      <main className="pt-20 pb-8 px-4 lg:px-6">
        <div className="max-w-[1600px] mx-auto">
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-foreground mb-2">
              Knowledge Base Management
            </h1>
            <p className="text-text-secondary">
              Manage compliance documentation and standards for organizational
              audit processes
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-3">
              <CategoryFilter
                categories={categories}
                selectedCategory={filterState.category}
                onCategorySelect={handleCategorySelect}
              />
            </div>

            <div className="lg:col-span-6 space-y-6">
              <UploadZone
                onFilesSelected={handleFilesSelected}
                uploadProgress={uploadProgress}
                isUploading={isUploading}
              />

              <SearchBar
                onSearch={handleSearch}
                onStatusFilter={handleStatusFilter}
                onExport={handleExport}
              />

              <BulkActionToolbar
                selectedCount={selectedIds.length}
                onCategorize={handleBulkCategorize}
                onDelete={handleBulkDelete}
                onArchive={handleBulkArchive}
                onActivate={handleBulkActivate}
                onClearSelection={() => setSelectedIds([])}
              />

              <DocumentTable
                documents={filteredDocuments}
                selectedIds={selectedIds}
                onSelectionChange={setSelectedIds}
                onDocumentClick={handleDocumentClick}
                onSort={handleSort}
                sortConfig={sortConfig}
              />
            </div>

            <div className="lg:col-span-3">
              <DocumentPreview
                document={selectedDocument}
                onClose={() => setSelectedDocument(null)}
                onSave={handleSaveMetadata}
              />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default AdministratorKnowledgeBaseDashboard;