import { useState, useEffect } from 'react'
import axios from 'axios'
import ResourceModal from '../components/ResourceModal'

// Define resource configuration type
interface ResourceColumn {
  field: string;
  header: string;
  type: string;
  required?: boolean;
  minLength?: number;
  placeholder?: string;
  pattern?: string;
  options?: {value: string, text: string}[];
}

interface ResourceConfig {
  apiEndpoint: string;
  modelName: string;
  idField: string;
  columns: ResourceColumn[];
  displayName: string;
}

const resourceConfig: Record<string, ResourceConfig> = {
  users: {
    apiEndpoint: '/users',
    modelName: 'User',
    idField: 'resourceId',
    columns: [
      { field: 'id', header: 'ID', type: 'hidden' },
      { field: 'username', header: 'Username', type: 'text', required: true, minLength: 3 },
      { field: 'email', header: 'Email', type: 'email', required: true },
      { field: 'full_name', header: 'Full Name', type: 'text', required: true, minLength: 2 }
    ],
    displayName: 'User'
  },
  employees: {
    apiEndpoint: '/employees',
    modelName: 'Employee',
    idField: 'resourceId',
    columns: [
      { field: 'id', header: 'ID', type: 'hidden' },
      { field: 'employee_id', header: 'Employee ID', type: 'text', required: true, 
        placeholder: 'EMP-XXXX', pattern: '^EMP-.*' },
      { field: 'email', header: 'Email', type: 'email', required: true },
      { field: 'full_name', header: 'Full Name', type: 'text', required: true, minLength: 2 },
      { field: 'department', header: 'Department', type: 'text', required: true },
      { field: 'position', header: 'Position', type: 'text', required: true }
    ],
    displayName: 'Employee'
  },
  subscribers: {
    apiEndpoint: '/subscribers',
    modelName: 'Subscriber',
    idField: 'resourceId',
    columns: [
      { field: 'id', header: 'ID', type: 'hidden' },
      { field: 'email', header: 'Email', type: 'email', required: true },
      { field: 'full_name', header: 'Full Name', type: 'text', required: true, minLength: 2 },
      { field: 'subscription_tier', header: 'Subscription Tier', type: 'select', required: true,
        options: [
          { value: 'free', text: 'Free' },
          { value: 'basic', text: 'Basic' },
          { value: 'premium', text: 'Premium' },
          { value: 'enterprise', text: 'Enterprise' }
        ]
      },
      { field: 'signup_date', header: 'Signup Date', type: 'datetime-local', required: true },
      { field: 'last_billing_date', header: 'Last Billing Date', type: 'datetime-local', required: false },
      { field: 'is_active', header: 'Active', type: 'checkbox', required: false }
    ],
    displayName: 'Subscriber'
  }
};

// Type for resource items
type ResourceItem = Record<string, any>;

const Resources = () => {
  const [activeResource, setActiveResource] = useState<string>('users')
  const [resources, setResources] = useState<Record<string, ResourceItem[]>>({
    users: [],
    employees: [],
    subscribers: []
  })
  const [filteredResources, setFilteredResources] = useState<Record<string, ResourceItem[]>>({
    users: [],
    employees: [],
    subscribers: []
  })
  const [currentPage, setCurrentPage] = useState<number>(1)
  const [loading, setLoading] = useState<boolean>(false)
  const [showModal, setShowModal] = useState<boolean>(false)
  const [editingResource, setEditingResource] = useState<ResourceItem | null>(null)
  const [filterText, setFilterText] = useState<string>('')
  const itemsPerPage = 10
  
  useEffect(() => {
    // Get initial resource type from URL if available
    const params = new URLSearchParams(window.location.search)
    const resourceParam = params.get('type')
    if (resourceParam && Object.keys(resourceConfig).includes(resourceParam)) {
      setActiveResource(resourceParam)
    }
    
    // Get page from URL
    const pageParam = params.get('page')
    if (pageParam) {
      const page = parseInt(pageParam)
      if (!isNaN(page) && page > 0) {
        setCurrentPage(page)
      }
    }
    
    // Load all resource types
    loadAllResources()
  }, [])
  
  // Update filtered resources when resources change or filter text changes
  useEffect(() => {
    filterResources()
  }, [resources, filterText, activeResource])
  
  const loadResourceType = async (resourceType: string) => {
    setLoading(true);
    try {
      const response = await axios.get(`/api${resourceConfig[resourceType].apiEndpoint}`);
      
      // Only update the specific resource type data
      setResources(prev => ({
        ...prev,
        [resourceType]: response.data
      }));
    } catch (error) {
      console.error(`Error loading ${resourceType}:`, error);
    } finally {
      setLoading(false);
    }
  };
  
  // Initial load of all resources
  const loadAllResources = async () => {
    setLoading(true);
    try {
      // Load all resource types in parallel
      const usersPromise = axios.get(`/api${resourceConfig.users.apiEndpoint}`);
      const employeesPromise = axios.get(`/api${resourceConfig.employees.apiEndpoint}`);
      const subscribersPromise = axios.get(`/api${resourceConfig.subscribers.apiEndpoint}`);
      
      const [usersRes, employeesRes, subscribersRes] = await Promise.all([
        usersPromise, employeesPromise, subscribersPromise
      ]);
      
      setResources({
        users: usersRes.data,
        employees: employeesRes.data,
        subscribers: subscribersRes.data
      });
    } catch (error) {
      console.error('Error loading resources:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const filterResources = () => {
    if (!filterText.trim()) {
      // No filter, use all resources
      setFilteredResources({...resources})
    } else {
      // Apply filter to active resource type
      const config = resourceConfig[activeResource]
      const filtered = resources[activeResource].filter(item => {
        return config.columns.some(column => {
          if (column.type !== 'hidden' && item[column.field]) {
            return item[column.field].toString().toLowerCase().includes(filterText.toLowerCase())
          }
          return false
        })
      })
      
      setFilteredResources(prev => ({
        ...prev,
        [activeResource]: filtered
      }))
    }
  }
  
  const handleResourceTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newResourceType = e.target.value
    setActiveResource(newResourceType)
    setCurrentPage(1)
    
    // Update URL without page refresh
    updateUrlParam('type', newResourceType)
    updateUrlParam('page', '1')
  }
  
  // Update URL parameter without refreshing the page
  const updateUrlParam = (key: string, value: string) => {
    const url = new URL(window.location.href)
    url.searchParams.set(key, value)
    window.history.pushState({}, '', url.toString())
  }
  
  const handleFilterChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilterText(e.target.value)
    setCurrentPage(1)
    updateUrlParam('page', '1')
  }
  
  const clearFilter = () => {
    setFilterText('')
    setCurrentPage(1)
    updateUrlParam('page', '1')
  }
  
  const handleAddResource = () => {
    setEditingResource(null);
    setShowModal(true);
  };
  
  const handlePageChange = (page: number | string) => {
    let newPage: number;
    
    // Calculate total pages for pagination
    const data = filteredResources[activeResource] || [];
    const totalPages = Math.ceil(data.length / itemsPerPage);
    
    if (page === 'first') {
      newPage = 1;
    } else if (page === 'last') {
      newPage = totalPages;
    } else if (page === 'prev') {
      newPage = Math.max(1, currentPage - 1);
    } else if (page === 'next') {
      newPage = Math.min(totalPages, currentPage + 1);
    } else {
      newPage = page as number;
    }
    
    setCurrentPage(newPage);
    updateUrlParam('page', newPage.toString());
  };
  
  const editResource = (id: number) => {
    const resource = resources[activeResource].find(item => item.id === id);
    if (resource) {
      setEditingResource(resource);
      setShowModal(true);
    } else {
      console.error(`Resource with ID ${id} not found`);
    }
  };
  
  const deleteResource = async (id: number) => {
    // Show confirmation dialog
    if (!window.confirm(`Are you sure you want to delete this ${resourceConfig[activeResource].displayName}?`)) {
      return;
    }
    
    try {
      setLoading(true);
      await axios.delete(`/api${resourceConfig[activeResource].apiEndpoint}/${id}`);
      
      // Only reload the current resource type
      await loadResourceType(activeResource);
      
      // Show success message
      alert(`${resourceConfig[activeResource].displayName} deleted successfully`);
    } catch (error) {
      console.error(`Error deleting ${resourceConfig[activeResource].displayName}:`, error);
      alert(`Failed to delete ${resourceConfig[activeResource].displayName}. Please try again.`);
    } finally {
      setLoading(false);
    }
  };
  
  const handleModalClose = () => {
    setShowModal(false);
    setEditingResource(null);
  };
  
  const handleModalSave = async () => {
    // Only reload the active resource type after a save
    await loadResourceType(activeResource);
    setShowModal(false);
  };
  
  const renderResourceTable = () => {
    const config = resourceConfig[activeResource]
    const data = filteredResources[activeResource] || []
    
    if (loading) {
      return (
        <div className="text-center py-5">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="mt-3">Loading {config.displayName} data...</p>
        </div>
      )
    }
    
    if (data.length === 0) {
      return (
        <table className="table table-striped table-hover">
          <thead>
            <tr>
              {config.columns.map(column => 
                column.type !== 'hidden' ? (
                  <th key={column.field}>{column.header}</th>
                ) : null
              )}
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={config.columns.filter(c => c.type !== 'hidden').length + 1} className="text-center">
                No {config.displayName.toLowerCase()}s found
              </td>
            </tr>
          </tbody>
        </table>
      )
    }
    
    // Calculate pagination
    const totalPages = Math.ceil(data.length / itemsPerPage)
    const validCurrentPage = Math.max(1, Math.min(currentPage, totalPages))
    
    // Calculate start and end indices for current page
    const startIndex = (validCurrentPage - 1) * itemsPerPage
    const endIndex = Math.min(startIndex + itemsPerPage, data.length)
    
    // Get current page data
    const currentPageData = data.slice(startIndex, endIndex)
    
    return (
      <>
        <div className="table-responsive">
          <table className="table table-striped table-hover">
            <thead>
              <tr>
                {config.columns.map(column => 
                  column.type !== 'hidden' ? (
                    <th key={column.field}>{column.header}</th>
                  ) : null
                )}
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="dynamicTableBody">
              {currentPageData.map(item => (
                <tr key={item.id}>
                  {config.columns.map(column => 
                    column.type !== 'hidden' ? (
                      <td key={column.field}>
                        {column.type === 'checkbox' 
                          ? <span className={`badge ${item[column.field] ? 'bg-success' : 'bg-danger'}`}>
                              {item[column.field] ? 'Yes' : 'No'}
                            </span>
                          : (column.type === 'datetime-local' && item[column.field]
                              ? new Date(item[column.field]).toLocaleString()
                              : (item[column.field] || '')
                            )
                        }
                      </td>
                    ) : null
                  )}
                  <td>
                    <button 
                      className="btn btn-sm btn-primary me-2"
                      onClick={() => editResource(item.id)}
                    >
                      Edit
                    </button>
                    <button 
                      className="btn btn-sm btn-danger"
                      onClick={() => deleteResource(item.id)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {/* Pagination controls */}
        {totalPages > 0 && (
          <div>
            <nav aria-label="Page navigation" id="resourcePagination" className="mt-3 pagination-actions-aligned">
              <ul className="pagination">
                <li className={`page-item ${validCurrentPage === 1 ? 'disabled' : ''}`}>
                  <button 
                    className="page-link" 
                    onClick={() => handlePageChange('first')}
                    disabled={validCurrentPage === 1}
                    title="First Page"
                  >
                    <i className="bi bi-chevron-double-left"></i>
                  </button>
                </li>
                <li className={`page-item ${validCurrentPage === 1 ? 'disabled' : ''}`}>
                  <button 
                    className="page-link"
                    onClick={() => handlePageChange('prev')}
                    disabled={validCurrentPage === 1}
                    title="Previous Page"
                  >
                    &laquo;
                  </button>
                </li>
                
                {/* Page numbers */}
                {Array.from({length: Math.min(5, totalPages)}, (_, i) => {
                  // Show pages around current page
                  let startPage = Math.max(1, validCurrentPage - 2)
                  let endPage = Math.min(totalPages, startPage + 4)
                  
                  // Adjust if we're showing fewer than 5 pages
                  if (endPage - startPage < 4) {
                    startPage = Math.max(1, endPage - 4)
                  }
                  
                  const pageNum = i + startPage
                  
                  if (pageNum <= endPage) {
                    return (
                      <li 
                        key={pageNum} 
                        className={`page-item ${pageNum === validCurrentPage ? 'active' : ''}`}
                      >
                        <button 
                          className="page-link"
                          onClick={() => handlePageChange(pageNum)}
                        >
                          {pageNum}
                        </button>
                      </li>
                    )
                  }
                  return null
                })}
                
                <li className={`page-item ${validCurrentPage === totalPages ? 'disabled' : ''}`}>
                  <button 
                    className="page-link"
                    onClick={() => handlePageChange('next')}
                    disabled={validCurrentPage === totalPages}
                    title="Next Page"
                  >
                    &raquo;
                  </button>
                </li>
                <li className={`page-item ${validCurrentPage === totalPages ? 'disabled' : ''}`}>
                  <button 
                    className="page-link"
                    onClick={() => handlePageChange('last')}
                    disabled={validCurrentPage === totalPages}
                    title="Last Page"
                  >
                    <i className="bi bi-chevron-double-right"></i>
                  </button>
                </li>
              </ul>
            </nav>
            
            <div className="mt-2 pagination-info">
              <small>
                Showing {data.length === 0 ? 0 : startIndex + 1} to {endIndex} of {data.length} {config.displayName.toLowerCase()}s
              </small>
            </div>
          </div>
        )}
      </>
    )
  }
  
  return (
    <div>
      <h1>Resource Management</h1>
      <p>Manage users, employees, and subscribers in the system.</p>
      
      <div className="row mb-4">
        <div className="col-md-6">
          <div className="d-flex align-items-center">
            <label htmlFor="resourceTypeSelect" className="me-2">Resource Type:</label>
            <select 
              id="resourceTypeSelect" 
              className="form-select" 
              value={activeResource}
              onChange={handleResourceTypeChange}
              style={{ width: 'auto' }}
            >
              {Object.entries(resourceConfig).map(([key, config]) => (
                <option key={key} value={key}>
                  {config.displayName}s
                </option>
              ))}
            </select>
          </div>
        </div>
        
        <div className="col-md-6">
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
              onChange={handleFilterChange}
            />
            {filterText && (
              <button 
                className="btn btn-outline-secondary" 
                type="button"
                id="clearFilterBtn"
                onClick={clearFilter}
                title="Clear filter"
              >
                <i className="bi bi-x"></i>
              </button>
            )}
          </div>
        </div>
      </div>
      
      <div className="card">
        <div className="card-header d-flex justify-content-between align-items-center">
          <h5 className="mb-0" id="resourceType">{resourceConfig[activeResource].displayName} List</h5>
          <button 
            className="btn btn-primary"
            onClick={handleAddResource}
          >
            <i className="bi bi-plus-circle"></i> Add {resourceConfig[activeResource].displayName}
          </button>
        </div>
        <div className="card-body">
          {renderResourceTable()}
        </div>
      </div>
      
      {showModal && (
        <ResourceModal
          resourceType={activeResource}
          resourceConfig={resourceConfig[activeResource]}
          onClose={handleModalClose}
          onSave={handleModalSave}
          editingResource={editingResource}
        />
      )}
    </div>
  )
}

export default Resources
