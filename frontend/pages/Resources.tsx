import { useState, useEffect } from 'react';
import { resourcesApi } from '@/services/api';
import resourceConfig from '@/config/resources';
import usePagination from '@/hooks/usePagination';
import type { ResourceItem } from '@/types';
import ResourceModal from '@/components/ResourceModal';
import { useToast } from '@/context/ToastContext';

const Resources = () => {
  // State variables
  const [activeResource, setActiveResource] = useState<string>('');
  const [items, setItems] = useState<ResourceItem[]>([]);
  const [filteredItems, setFilteredItems] = useState<ResourceItem[]>([]);
  const [filterText, setFilterText] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [currentItem, setCurrentItem] = useState<ResourceItem | null>(null);
  const [showModal, setShowModal] = useState<boolean>(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  
  // Use the toast hook
  const { showToast } = useToast();
  
  // Replace pagination state with usePagination hook
  const getPagination = usePagination<ResourceItem>({ initialPage: 1, itemsPerPage: 10 });
  const pagination = getPagination(filteredItems);

  // Fetch resources when resource type changes
  useEffect(() => {
    if (activeResource) {
      loadResources();
    }
  }, [activeResource]);

  // Filter items when filter text changes
  useEffect(() => {
    filterItems();
  }, [filterText, items]);

  // Load resources from API
  const loadResources = async () => {
    if (!activeResource) return;

    setIsLoading(true);
    try {
      const config = resourceConfig[activeResource];
      const response = await resourcesApi.getAll(config.apiEndpoint);
      setItems(response.data);
      setFilteredItems(response.data);
    } catch (error) {
      console.error('Error loading resources:', error);
      showToast('Error loading resources', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // Filter items based on search input
  const filterItems = () => {
    if (!activeResource || !items.length) {
      setFilteredItems([]);
      return;
    }

    if (!filterText.trim()) {
      setFilteredItems(items);
      return;
    }

    const config = resourceConfig[activeResource];
    const searchableColumns = config.columns.filter((col: { type: string; searchable?: boolean }) => 
      col.type !== 'hidden' && col.type !== 'password'
    );

    const filtered = items.filter(item => {
      return searchableColumns.some((column: { field: string }) => {
        const value = item[column.field];
        if (value !== undefined && value !== null) {
          return String(value).toLowerCase().includes(filterText.toLowerCase());
        }
        return false;
      });
    });

    setFilteredItems(filtered);
  };

  // Clear filter
  const clearFilter = () => {
    setFilterText('');
  };

  // Show create modal
  const showCreateModal = () => {
    const emptyItem: ResourceItem = {};
    
    // Initialize with empty values or defaults
    if (activeResource) {
      const config = resourceConfig[activeResource];
      config.columns.forEach((col: { type: string; field: string; options?: Array<{value: string | number}> }) => {
        if (col.type === 'checkbox') {
          emptyItem[col.field] = false;
        } else if (col.type === 'select' && col.options && col.options.length > 0) {
          emptyItem[col.field] = col.options[0].value;
        } else {
          emptyItem[col.field] = '';
        }
      });
    }
    
    setCurrentItem(emptyItem);
    setModalMode('create');
    setShowModal(true);
  };

  // Show edit modal
  const showEditModal = (item: ResourceItem) => {
    setCurrentItem({...item});
    setModalMode('edit');
    setShowModal(true);
  };

  // Handle modal close
  const handleModalClose = () => {
    setShowModal(false);
  };

  // Handle resource saved
  const handleResourceSaved = () => {
    loadResources();
    setShowModal(false);
  };

  // Delete resource
  const deleteResource = async (item: ResourceItem) => {
    if (!activeResource) return;
    
    if (!confirm(`Are you sure you want to delete this ${resourceConfig[activeResource].displayName}?`)) {
      return;
    }
    
    setIsLoading(true);
    
    try {
      const config = resourceConfig[activeResource];
      const itemId = item[config.idField] || item.id;
      
      await resourcesApi.delete(config.apiEndpoint, itemId);
      
      // Show success toast notification
      showToast(`Successfully deleted ${config.displayName}`, 'success');
      
      loadResources();
    } catch (error) {
      console.error('Error deleting resource:', error);
      showToast(`Error deleting ${resourceConfig[activeResource].displayName}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle resource type change
  const handleResourceTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const resourceType = e.target.value;
    setActiveResource(resourceType);
    setFilterText('');
  };

  // Render resource table
  const renderResourceTable = () => {
    if (!activeResource) return null;
    
    const config = resourceConfig[activeResource];
    
    if (filteredItems.length === 0) {
      return (
        <div className="alert alert-info">
          {filterText
            ? 'No resources match your search criteria.'
            : 'No resources available. Click "Add New" to create one.'}
        </div>
      );
    }
    
    // Get visible columns (not hidden)
    const visibleColumns = config.columns.filter((col: { type: string }) => col.type !== 'hidden');
    
    return (
      <>
        <div className="table-responsive">
          <table className="table table-striped table-hover">
            <thead>
              <tr>
                {visibleColumns.map((column: { field: string; header: string }) => (
                  <th key={column.field}>{column.header}</th>
                ))}
                <th className="text-end">Actions</th>
              </tr>
            </thead>
            <tbody>
              {pagination.pageItems.map((item, idx) => (
                <tr key={item.id || idx}>
                  {visibleColumns.map((column: { field: string; type: string; options?: Array<{value: string | number; text: string}> }) => {
                    let cellContent = item[column.field];
                    
                    // Format cell content based on type
                    if (column.type === 'checkbox') {
                      cellContent = cellContent ? '✅' : '❌';
                    } else if (column.type === 'select' && column.options) {
                      const option = column.options.find((opt: {value: string | number; text: string}) => opt.value === cellContent);
                      cellContent = option ? option.text : cellContent;
                    }
                    
                    return (
                      <td key={column.field}>
                        {cellContent !== undefined && cellContent !== null
                          ? String(cellContent)
                          : '-'}
                      </td>
                    );
                  })}
                  <td className="text-end">
                    <button
                      className="btn btn-sm btn-outline-primary me-2"
                      onClick={() => showEditModal(item)}
                    >
                      <i className="bi bi-pencil"></i> Edit
                    </button>
                    <button
                      className="btn btn-sm btn-outline-danger"
                      onClick={() => deleteResource(item)}
                    >
                      <i className="bi bi-trash"></i> Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {pagination.totalPages > 1 && (
          <nav aria-label="Resource pagination" className="mt-3">
            <ul className="pagination">
              <li className={`page-item ${pagination.currentPage === 1 ? 'disabled' : ''}`}>
                <button 
                  className="page-link" 
                  onClick={pagination.goToFirstPage}
                  disabled={pagination.currentPage === 1}
                >
                  <i className="bi bi-chevron-double-left"></i>
                </button>
              </li>
              <li className={`page-item ${pagination.currentPage === 1 ? 'disabled' : ''}`}>
                <button 
                  className="page-link"
                  onClick={pagination.goToPreviousPage}
                  disabled={pagination.currentPage === 1}
                >
                  &laquo;
                </button>
              </li>
              
              {Array.from({length: Math.min(5, pagination.totalPages)}, (_, i) => {
                let startPage = Math.max(1, pagination.currentPage - 2);
                let endPage = Math.min(pagination.totalPages, startPage + 4);
                
                if (endPage - startPage < 4) {
                  startPage = Math.max(1, endPage - 4);
                }
                
                const pageNum = i + startPage;
                
                if (pageNum <= endPage) {
                  return (
                    <li 
                      key={pageNum} 
                      className={`page-item ${pageNum === pagination.currentPage ? 'active' : ''}`}
                    >
                      <button 
                        className="page-link"
                        onClick={() => pagination.goToPage(pageNum)}
                      >
                        {pageNum}
                      </button>
                    </li>
                  );
                }
                return null;
              })}
              
              <li className={`page-item ${pagination.currentPage === pagination.totalPages ? 'disabled' : ''}`}>
                <button 
                  className="page-link"
                  onClick={pagination.goToNextPage}
                  disabled={pagination.currentPage === pagination.totalPages}
                >
                  &raquo;
                </button>
              </li>
              <li className={`page-item ${pagination.currentPage === pagination.totalPages ? 'disabled' : ''}`}>
                <button 
                  className="page-link"
                  onClick={pagination.goToLastPage}
                  disabled={pagination.currentPage === pagination.totalPages}
                >
                  <i className="bi bi-chevron-double-right"></i>
                </button>
              </li>
            </ul>
          </nav>
        )}
        
        <div className="mt-2">
          <small className="text-muted">
            Showing {filteredItems.length === 0 ? 0 : pagination.startIndex + 1} to {pagination.endIndex} of {filteredItems.length} {config.displayName.toLowerCase()}s
            {filterText && ` (filtered from ${items.length} total)`}
          </small>
        </div>
      </>
    );
  };

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h3>Resource Management</h3>
      </div>

      <div className="card mb-4">
        <div className="card-header bg-primary text-white d-flex justify-content-between align-items-center">
          <h5 className="card-title mb-0">Resources</h5>
          
          {activeResource && (
            <button 
              className="btn btn-light btn-sm" 
              onClick={showCreateModal}
              disabled={isLoading}
            >
              <i className="bi bi-plus-circle"></i> Add New {resourceConfig[activeResource].displayName}
            </button>
          )}
        </div>
        <div className="card-body">
          <div className="row mb-4">
            <div className="col-md-6">
              <label htmlFor="resourceTypeSelect" className="form-label">Resource Type</label>
              <select 
                id="resourceTypeSelect" 
                className="form-select" 
                value={activeResource}
                onChange={handleResourceTypeChange}
              >
                <option value="">Select a resource type...</option>
                {Object.entries(resourceConfig).map(([key, config]) => (
                  <option key={key} value={key}>
                    {config.displayName}s
                  </option>
                ))}
              </select>
            </div>
            
            {activeResource && (
              <div className="col-md-6">
                <label htmlFor="resourceFilterInput" className="form-label">Filter</label>
                <div className="input-group">
                  <span className="input-group-text">
                    <i className="bi bi-search"></i>
                  </span>
                  <input 
                    type="text" 
                    id="resourceFilterInput" 
                    className="form-control" 
                    placeholder="Filter resources..." 
                    value={filterText}
                    onChange={(e) => setFilterText(e.target.value)}
                  />
                  {filterText && (
                    <button 
                      className="btn btn-outline-secondary" 
                      type="button"
                      onClick={clearFilter}
                      title="Clear filter"
                    >
                      <i className="bi bi-x"></i>
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
          
          {isLoading && !showModal ? (
            <div className="text-center py-4">
              <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
              <p className="mt-2">Loading resources...</p>
            </div>
          ) : (
            renderResourceTable()
          )}
        </div>
      </div>

      {/* Resource Modal */}
      {activeResource && currentItem && showModal && (
        <ResourceModal
          resourceType={activeResource}
          resourceConfig={resourceConfig[activeResource]}
          onClose={handleModalClose}
          onSave={handleResourceSaved}
          editingResource={modalMode === 'edit' ? currentItem : null}
          show={showModal}
        />
      )}
    </div>
  );
};

export default Resources;
