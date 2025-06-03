// frontend/features/resources/ResourcesRefactored.tsx
import { useState } from 'react';
import { resourceConfig } from '@/config';
import { ResourceModal } from './components';
import { usePagination } from '@/hooks';
import { 
  useResourcesData,
  useResourcesFiltering,
  useResourcesModal,
  useResourcesTable
} from './hooks';
import type { ResourceConfig } from '@/types';

const Resources = () => {
  // Resource type state
  const [activeResource, setActiveResource] = useState<string>('');

  // Data management hook
  const {
    items,
    isLoading,
    loadResources,
    deleteResource,
    getCurrentConfig,
    getVisibleColumns
  } = useResourcesData({ activeResource });

  // Filtering hook
  const {
    filterText,
    filteredItems,
    setFilterText,
    clearFilter,
    getFilterSummary,
    isFilterActive
  } = useResourcesFiltering({ items, activeResource });

  // Modal management hook
  const {
    currentItem,
    showModal,
    modalMode,
    showCreateModal,
    showEditModal,
    handleModalClose,
    handleResourceSaved,
    canShowModal
  } = useResourcesModal({ 
    activeResource, 
    onResourceSaved: loadResources 
  });

  // Table rendering hook
  const {
    formatCellContent,
    showEmptyState,
    showLoadingState,
    showTableData,
    getEmptyStateMessage
  } = useResourcesTable({ 
    filteredItems, 
    isLoading, 
    filterText 
  });

  // Pagination hook
  const getPagination = usePagination<any>({ initialPage: 1, itemsPerPage: 10 });
  const pagination = getPagination(filteredItems);

  // Handle resource type change
  const handleResourceTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const resourceType = e.target.value;
    setActiveResource(resourceType);
    setFilterText('');
  };

  // Get current config safely
  const currentConfig = getCurrentConfig();

  // Render main content
  const renderMainContent = () => {
    if (showLoadingState) {
      return (
        <div className="text-center py-4">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="mt-2">Loading resources...</p>
        </div>
      );
    }

    if (showEmptyState) {
      return (
        <div className="alert alert-info">
          {getEmptyStateMessage()}
        </div>
      );
    }

    if (showTableData) {
      return renderResourceTable();
    }

    return null;
  };

  // Render resource table
  const renderResourceTable = () => {
    const visibleColumns = getVisibleColumns();
    
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
                  {visibleColumns.map((column: any) => (
                    <td key={column.field}>
                      {formatCellContent(item, column)}
                    </td>
                  ))}
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
            Showing {filteredItems.length === 0 ? 0 : pagination.startIndex + 1} to {pagination.endIndex} of {filteredItems.length} {currentConfig?.displayName.toLowerCase()}s
            {getFilterSummary()}
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
              <i className="bi bi-plus-circle"></i> Add New {currentConfig?.displayName}
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
                {Object.entries(resourceConfig).map(([key, config]: [string, ResourceConfig]) => (
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
                  {isFilterActive() && (
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
          
          {renderMainContent()}
        </div>
      </div>

      {/* Resource Modal */}
      {canShowModal() && currentItem && showModal && (
        <ResourceModal
          resourceType={activeResource}
          resourceConfig={currentConfig!}
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