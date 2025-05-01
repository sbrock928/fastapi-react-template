// resources.js - Combined management for users and employees
// Configuration for different resource types
const resourceConfig = {
    users: {
        apiEndpoint: '/users',
        modalId: 'userModal',
        modalTitleId: 'userModalTitle',
        tableSection: 'userTableSection',
        formId: 'userForm',
        idField: 'userId',
        fields: {
            username: 'username',
            email: 'userEmail',
            full_name: 'userFullName'
        },
        displayName: 'User',
        fieldMapping: {
            // Maps form field IDs to API field names
            username: 'username',
            userEmail: 'email',
            userFullName: 'full_name'
        }
    },
    employees: {
        apiEndpoint: '/employees',
        modalId: 'employeeModal',
        modalTitleId: 'employeeModalTitle',
        tableSection: 'employeeTableSection',
        formId: 'employeeForm',
        idField: 'employeeId',
        fields: {
            employee_id: 'employeeIdField',
            email: 'employeeEmail',
            full_name: 'employeeFullName',
            department: 'department',
            position: 'position'
        },
        displayName: 'Employee',
        fieldMapping: {
            // Maps form field IDs to API field names
            employeeIdField: 'employee_id',
            employeeEmail: 'email',
            employeeFullName: 'full_name',
            department: 'department',
            position: 'position'
        }
    }
};

// Current resource type (default: users)
let currentResourceType = 'users';

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    // Set up resource type selector
    const resourceTypeSelect = document.getElementById('resourceTypeSelect');
    resourceTypeSelect.addEventListener('change', function() {
        currentResourceType = this.value;
        updateResourceView();
    });

    // Initialize with users view
    updateResourceView();
});

// Update the view based on selected resource type
function updateResourceView() {
    // Update resource type text
    document.getElementById('resourceType').textContent = resourceConfig[currentResourceType].displayName;
    
    // Hide all table sections
    Object.keys(resourceConfig).forEach(type => {
        document.getElementById(resourceConfig[type].tableSection).style.display = 'none';
    });
    
    // Show current resource table
    document.getElementById(resourceConfig[currentResourceType].tableSection).style.display = 'block';
}

// Open the appropriate modal for adding/editing a resource
function openModal(resourceId = null) {
    const config = resourceConfig[currentResourceType];
    const modal = new bootstrap.Modal(document.getElementById(config.modalId));
    const form = document.getElementById(config.formId);
    
    // Clear previous validation errors
    clearValidationErrors();
    
    // Set modal title
    document.getElementById(config.modalTitleId).textContent = 
        resourceId ? `Edit ${config.displayName}` : `Add ${config.displayName}`;
    
    // Set resource ID
    document.getElementById(config.idField).value = resourceId || '';
    
    if (resourceId) {
        // Fetch resource data for editing
        fetch(`${config.apiEndpoint}/${resourceId}`)
            .then(response => response.json())
            .then(data => {
                // Populate form fields based on resource type
                Object.keys(config.fields).forEach(apiField => {
                    const formField = config.fields[apiField];
                    const value = data[apiField];
                    if (value !== undefined) {
                        document.getElementById(formField).value = value;
                    }
                });
            });
    } else {
        form.reset();
    }
    
    modal.show();
}

// Clear validation errors from forms
function clearValidationErrors() {
    document.querySelectorAll('.invalid-feedback').forEach(el => el.textContent = '');
    document.querySelectorAll('.form-control').forEach(el => el.classList.remove('is-invalid'));
}

// Show validation error for a specific field
function showValidationError(fieldId, message) {
    const field = document.getElementById(fieldId);
    if (field) {
        field.classList.add('is-invalid');
        field.nextElementSibling.textContent = message;
    }
}

// Handle validation errors from API
function handleValidationErrors(error, resourceType) {
    console.log('Error:', error);  
    const config = resourceConfig[resourceType];
    
    if (error.detail) {
        if (Array.isArray(error.detail)) {
            // Handle Pydantic validation errors (422)
            error.detail.forEach(err => {
                const apiField = err.loc[err.loc.length - 1];
                const formField = config.fields[apiField];
                showValidationError(formField || apiField, err.msg);
            });
        } else if (typeof error.detail === 'object') {
            // Handle custom validation errors (400)
            Object.entries(error.detail).forEach(([apiField, message]) => {
                const formField = config.fields[apiField];
                showValidationError(formField || apiField, message);
            });
        } else {
            // Handle string error messages
            showValidationError(Object.values(config.fields)[0], error.detail);
        }
    } else {
        console.error('Unhandled error:', error);
        alert('An unexpected error occurred');
    }
}

// Save the current resource (create or update)
function saveResource(resourceType) {
    const config = resourceConfig[resourceType];
    const resourceId = document.getElementById(config.idField).value;
    const resourceData = {};
    
    // Get form data
    Object.entries(config.fieldMapping).forEach(([formField, apiField]) => {
        const value = document.getElementById(formField).value;
        if (value) {
            resourceData[apiField] = value;
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
        // Hide modal and reload page
        const modal = bootstrap.Modal.getInstance(document.getElementById(config.modalId));
        modal.hide();
        window.location.reload();
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
        .then(() => window.location.reload());
    }
}

// Set up input event listeners for validation reset
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.form-control').forEach(input => {
        input.addEventListener('input', () => {
            input.classList.remove('is-invalid');
            input.nextElementSibling.textContent = '';
        });
    });
});