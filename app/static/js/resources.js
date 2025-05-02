// resources.js - Dynamic resource management based on SQLModels
// Configuration for different resource types
const resourceConfig = {
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
    }
};

// Current resource type (default: users)
let currentResourceType = 'users';
let resourceData = {};

// Pagination variables
let currentPage = 1;
const itemsPerPage = 10;
let totalPages = 1;

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    // Set up resource type selector
    const resourceTypeSelect = document.getElementById('resourceTypeSelect');
    resourceTypeSelect.addEventListener('change', function() {
        currentResourceType = this.value;
        // Update URL with the new resource type
        updateUrlParam('type', currentResourceType);
        updateResourceView();
    });

    // Set up save button event listener
    document.getElementById('saveResourceBtn').addEventListener('click', function() {
        saveResource(currentResourceType);
    });

    // Initial resource data setup
    resourceData = {
        users: usersData || [],
        employees: employeesData || []
    };

    // Set the initial resource type from the server-provided value if available
    if (typeof initialResourceType !== 'undefined' && resourceConfig[initialResourceType]) {
        currentResourceType = initialResourceType;
    } else {
        // Check URL parameters as fallback
        const urlParams = new URLSearchParams(window.location.search);
        const typeParam = urlParams.get('type');
        if (typeParam && resourceConfig[typeParam]) {
            currentResourceType = typeParam;
        }
    }
    
    // Update the select element to match the current resource type
    resourceTypeSelect.value = currentResourceType;

    // Initialize with proper view
    updateResourceView();
});

// Update URL parameter without refreshing the page
function updateUrlParam(key, value) {
    const url = new URL(window.location);
    url.searchParams.set(key, value);
    window.history.pushState({}, '', url);
}

// Update the view based on selected resource type
function updateResourceView() {
    const config = resourceConfig[currentResourceType];
    
    // Update resource type text
    document.getElementById('resourceType').textContent = config.displayName;
    
    // Check URL parameters for page number
    const urlParams = new URLSearchParams(window.location.search);
    const pageParam = urlParams.get('page');
    if (pageParam) {
        currentPage = parseInt(pageParam) || 1;
    } else {
        currentPage = 1; // Reset to first page when changing resource type
    }
    
    // Render table
    renderResourceTable(config);
}

// Render the resource table with dynamic columns and data
function renderResourceTable(config) {
    // Render table header
    const headerRow = document.createElement('tr');
    config.columns.forEach(column => {
        if (column.type !== 'hidden') {
            const th = document.createElement('th');
            th.textContent = column.header;
            headerRow.appendChild(th);
        }
    });
    
    // Add action column header
    const actionTh = document.createElement('th');
    actionTh.textContent = 'Actions';
    headerRow.appendChild(actionTh);
    
    // Update header
    const tableHeader = document.getElementById('dynamicTableHeader');
    tableHeader.innerHTML = '';
    tableHeader.appendChild(headerRow);
    
    // Render table body with data
    const tableBody = document.getElementById('dynamicTableBody');
    tableBody.innerHTML = '';
    
    const data = resourceData[currentResourceType] || [];
    
    if (data.length === 0) {
        const emptyRow = document.createElement('tr');
        const emptyCell = document.createElement('td');
        emptyCell.colSpan = config.columns.filter(c => c.type !== 'hidden').length + 1;
        emptyCell.textContent = `No ${config.displayName.toLowerCase()}s found`;
        emptyCell.className = 'text-center';
        emptyRow.appendChild(emptyCell);
        tableBody.appendChild(emptyRow);
        
        // Hide pagination when no data
        document.getElementById('resourcePagination')?.classList.add('d-none');
    } else {
        // Calculate total pages and ensure current page is valid
        totalPages = Math.ceil(data.length / itemsPerPage);
        if (currentPage > totalPages) {
            currentPage = totalPages;
        } else if (currentPage < 1) {
            currentPage = 1;
        }
        
        // Calculate start and end indices for current page
        const startIndex = (currentPage - 1) * itemsPerPage;
        const endIndex = Math.min(startIndex + itemsPerPage, data.length);
        
        // Get current page data
        const currentPageData = data.slice(startIndex, endIndex);
        
        // Render current page data
        currentPageData.forEach(item => {
            const row = document.createElement('tr');
            
            // Add data cells
            config.columns.forEach(column => {
                if (column.type !== 'hidden') {
                    const td = document.createElement('td');
                    td.textContent = item[column.field] || '';
                    row.appendChild(td);
                }
            });
            
            // Add action buttons
            const actionTd = document.createElement('td');
            
            const editBtn = document.createElement('button');
            editBtn.className = 'btn btn-sm btn-primary me-2';
            editBtn.textContent = 'Edit';
            editBtn.onclick = () => editResource(item.id);
            
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'btn btn-sm btn-danger';
            deleteBtn.textContent = 'Delete';
            deleteBtn.onclick = () => deleteResource(item.id);
            
            actionTd.appendChild(editBtn);
            actionTd.appendChild(deleteBtn);
            row.appendChild(actionTd);
            
            tableBody.appendChild(row);
        });
        
        // Render pagination controls
        renderPagination(data.length);
    }
}

// Render pagination controls
function renderPagination(totalItems) {
    // Get or create pagination container
    let paginationContainer = document.getElementById('resourcePagination');
    
    if (!paginationContainer) {
        // Create pagination container if it doesn't exist
        paginationContainer = document.createElement('nav');
        paginationContainer.id = 'resourcePagination';
        paginationContainer.setAttribute('aria-label', 'Resource pagination');
        paginationContainer.className = 'mt-3';
        
        // Find the table container to append pagination after it
        const tableContainer = document.querySelector('.table-responsive');
        if (tableContainer && tableContainer.parentNode) {
            tableContainer.parentNode.insertBefore(paginationContainer, tableContainer.nextSibling);
        }
    }
    
    // Show pagination container
    paginationContainer.classList.remove('d-none');
    
    // Calculate total pages
    totalPages = Math.ceil(totalItems / itemsPerPage);
    
    // Create pagination HTML
    let paginationHTML = `
        <ul class="pagination justify-content-center">
            <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="prev">&laquo;</a>
            </li>
    `;
    
    // Determine which page numbers to show
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    
    // Adjust if we're showing fewer than 5 pages
    if (endPage - startPage < 4) {
        startPage = Math.max(1, endPage - 4);
    }
    
    // Add page numbers
    for (let i = startPage; i <= endPage; i++) {
        paginationHTML += `
            <li class="page-item ${i === currentPage ? 'active' : ''}">
                <a class="page-link" href="#" data-page="${i}">${i}</a>
            </li>
        `;
    }
    
    paginationHTML += `
            <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="next">&raquo;</a>
            </li>
        </ul>
        <div class="text-center mt-2">
            <small>Showing ${totalItems === 0 ? 0 : (currentPage - 1) * itemsPerPage + 1} to ${Math.min(currentPage * itemsPerPage, totalItems)} of ${totalItems} ${resourceConfig[currentResourceType].displayName.toLowerCase()}s</small>
        </div>
    `;
    
    // Update pagination container
    paginationContainer.innerHTML = paginationHTML;
    
    // Add click handlers to pagination links
    paginationContainer.querySelectorAll('.page-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const page = this.dataset.page;
            
            if (page === 'prev') {
                if (currentPage > 1) {
                    currentPage--;
                    renderResourceTable(resourceConfig[currentResourceType]);
                }
            } else if (page === 'next') {
                if (currentPage < totalPages) {
                    currentPage++;
                    renderResourceTable(resourceConfig[currentResourceType]);
                }
            } else {
                currentPage = parseInt(page);
                renderResourceTable(resourceConfig[currentResourceType]);
            }
            
            // Update URL with the page number
            updateUrlParam('page', currentPage);
        });
    });
}

// Open the resource modal for adding/editing
function openModal(resourceId = null) {
    const config = resourceConfig[currentResourceType];
    const modal = new bootstrap.Modal(document.getElementById('resourceModal'));
    
    // Clear previous validation errors
    clearValidationErrors();
    
    // Set modal title
    document.getElementById('resourceModalTitle').textContent = 
        resourceId ? `Edit ${config.displayName}` : `Add ${config.displayName}`;
    
    // Set resource ID
    document.getElementById('resourceId').value = resourceId || '';
    
    // Generate form fields dynamically
    const formContainer = document.getElementById('dynamicFormFields');
    formContainer.innerHTML = '';
    
    config.columns.forEach(column => {
        if (column.field !== 'id') {  // Don't show ID field in the form
            const formGroup = document.createElement('div');
            formGroup.className = 'mb-3';
            
            const label = document.createElement('label');
            label.htmlFor = column.field;
            label.className = 'form-label';
            label.textContent = column.header;
            
            const input = document.createElement('input');
            input.type = column.type;
            input.className = 'form-control';
            input.id = column.field;
            input.name = column.field;
            
            if (column.required) input.required = true;
            if (column.minLength) input.minLength = column.minLength;
            if (column.pattern) input.pattern = column.pattern;
            if (column.placeholder) input.placeholder = column.placeholder;
            
            // Add input event listener for validation reset
            input.addEventListener('input', () => {
                input.classList.remove('is-invalid');
                input.nextElementSibling?.remove();
            });
            
            const feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            
            formGroup.appendChild(label);
            formGroup.appendChild(input);
            formGroup.appendChild(feedback);
            formContainer.appendChild(formGroup);
        }
    });
    
    if (resourceId) {
        // Fetch resource data for editing
        fetch(`${config.apiEndpoint}/${resourceId}`)
            .then(response => response.json())
            .then(data => {
                // Populate form fields
                config.columns.forEach(column => {
                    const input = document.getElementById(column.field);
                    if (input && data[column.field] !== undefined) {
                        input.value = data[column.field];
                    }
                });
            });
    } else {
        // Clear form for new resource
        document.getElementById('resourceForm').reset();
    }
    
    modal.show();
}

// Clear validation errors from forms
function clearValidationErrors() {
    // Hide the validation summary
    const validationSummary = document.getElementById('validationSummary');
    if (validationSummary) {
        validationSummary.classList.add('d-none');
        validationSummary.innerHTML = 'Please fix the validation errors below.';
    }
    
    document.querySelectorAll('.invalid-feedback').forEach(el => {
        el.textContent = '';
    });
    document.querySelectorAll('.form-control').forEach(el => {
        el.classList.remove('is-invalid');
    });
}

// Show validation error for a specific field
function showValidationError(fieldId, message) {
    // Show the validation summary
    const validationSummary = document.getElementById('validationSummary');
    if (validationSummary) {
        validationSummary.classList.remove('d-none');
    }
    
    const field = document.getElementById(fieldId);
    if (field) {
        field.classList.add('is-invalid');
        
        // Find or create the invalid feedback element
        let feedback = field.nextElementSibling;
        if (!feedback || !feedback.classList.contains('invalid-feedback')) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            field.parentNode.insertBefore(feedback, field.nextSibling);
        }
        
        feedback.textContent = message;
    } else {
        console.warn(`Field with ID '${fieldId}' not found in the form`);
        // If field not found, show error in the validation summary
        if (validationSummary) {
            const errorItem = document.createElement('p');
            errorItem.className = 'mb-0';
            errorItem.textContent = `${fieldId}: ${message}`;
            validationSummary.appendChild(errorItem);
        }
    }
}

// Handle validation errors from API
function handleValidationErrors(error, resourceType) {
    console.log('Error:', error);
    
    if (error.detail) {
        if (Array.isArray(error.detail)) {
            // Handle Pydantic validation errors (422)
            error.detail.forEach(err => {
                const fieldPath = err.loc;
                // Skip the first element which is usually 'body'
                const apiField = fieldPath[fieldPath.length - 1];
                showValidationError(apiField, err.msg);
            });
        } else if (typeof error.detail === 'object') {
            // Handle custom validation errors (400)
            Object.entries(error.detail).forEach(([apiField, message]) => {
                showValidationError(apiField, message);
            });
        } else {
            // Handle string error messages
            const firstField = document.querySelector('#dynamicFormFields .form-control');
            if (firstField) {
                showValidationError(firstField.id, error.detail);
            } else {
                alert(error.detail);
            }
        }
    } else if (error.errors) {
        // Handle validation errors in newer FastAPI/Pydantic versions
        error.errors.forEach(err => {
            if (err.loc && err.loc.length > 0) {
                // Skip the first element which is usually 'body'
                const apiField = err.loc[err.loc.length - 1];
                showValidationError(apiField, err.msg);
            }
        });
    } else {
        console.error('Unhandled error:', error);
        alert('An unexpected error occurred');
    }
}

// Save the current resource (create or update)
function saveResource(resourceType) {
    const config = resourceConfig[resourceType];
    const resourceId = document.getElementById('resourceId').value;
    const form = document.getElementById('resourceForm');
    
    // Basic form validation
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    const resourceData = {};
    
    // Collect form data for all fields
    config.columns.forEach(column => {
        if (column.field !== 'id') {  // Skip ID field
            const field = document.getElementById(column.field);
            if (field && field.value) {
                resourceData[column.field] = field.value;
            }
        }
    });

    const method = resourceId ? 'PATCH' : 'POST';
    const url = resourceId ? `${config.apiEndpoint}/${resourceId}` : config.apiEndpoint;

    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(resourceData)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => Promise.reject(err));
        }
        return response.json();
    })
    .then(() => {
        // Hide modal and reload page with the current resource type preserved
        const modal = bootstrap.Modal.getInstance(document.getElementById('resourceModal'));
        modal.hide();
        window.location.href = `/resources?type=${currentResourceType}`;
    })
    .catch(error => handleValidationErrors(error, resourceType));
}

// Edit a resource
function editResource(resourceId) {
    openModal(resourceId);
}

// Delete a resource
function deleteResource(resourceId) {
    const config = resourceConfig[currentResourceType];
    
    if (confirm(`Are you sure you want to delete this ${config.displayName.toLowerCase()}?`)) {
        fetch(`${config.apiEndpoint}/${resourceId}`, {
            method: 'DELETE'
        })
        .then(() => {
            // Reload the page with the resource type preserved
            window.location.href = `/resources?type=${currentResourceType}`;
        });
    }
}