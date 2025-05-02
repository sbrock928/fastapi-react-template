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
    } else {
        data.forEach(item => {
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
    }
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