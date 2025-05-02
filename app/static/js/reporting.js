// filepath: /Users/stephenbrock/PycharmProjects/Vibez/app/static/js/reporting.js
// reporting.js - Report generation and export functionality

// Configuration for different report types
const reportConfig = {
    users_by_creation: {
        apiEndpoint: '/api/reports/users-by-creation',
        title: 'Users by Creation Date',
        columns: [
            { field: 'date', header: 'Date', type: 'date' },
            { field: 'count', header: 'Number of Users', type: 'number' },
            { field: 'cumulative', header: 'Cumulative Users', type: 'number' }
        ],
        parameters: [
            { 
                field: 'date_range', 
                label: 'Date Range', 
                type: 'select',
                options: [
                    { value: 'last_7_days', label: 'Last 7 Days' },
                    { value: 'last_30_days', label: 'Last 30 Days' },
                    { value: 'last_90_days', label: 'Last 90 Days' },
                    { value: 'year_to_date', label: 'Year to Date' },
                    { value: 'all_time', label: 'All Time' }
                ]
            }
        ]
    },
    employees_by_department: {
        apiEndpoint: '/api/reports/employees-by-department',
        title: 'Employees by Department',
        columns: [
            { field: 'department', header: 'Department', type: 'text' },
            { field: 'count', header: 'Number of Employees', type: 'number' },
            { field: 'percentage', header: 'Percentage', type: 'percentage' }
        ],
        parameters: []
    },
    resource_counts: {
        apiEndpoint: '/api/reports/resource-counts',
        title: 'Resource Counts Summary',
        columns: [
            { field: 'resource_type', header: 'Resource Type', type: 'text' },
            { field: 'count', header: 'Count', type: 'number' }
        ],
        parameters: []
    }
};

// Current report data
let currentReportData = [];
let currentReportType = '';

// Pagination variables
let currentReportPage = 1;
const reportItemsPerPage = 10;
let totalReportPages = 1;

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    // Set up report selector
    const reportSelect = document.getElementById('reportSelect');
    reportSelect.addEventListener('change', function() {
        currentReportType = this.value;
        updateReportParameters();
    });

    // Set up run report button
    document.getElementById('runReportBtn').addEventListener('click', runReport);

    // Set up export buttons
    document.getElementById('exportCsvBtn').addEventListener('click', () => exportReport('csv'));
    document.getElementById('exportXlsxBtn').addEventListener('click', () => exportReport('xlsx'));
});

// Update parameter inputs based on selected report
function updateReportParameters() {
    const config = reportConfig[currentReportType];
    if (!config) return;
    
    const parametersContainer = document.getElementById('reportParametersContainer');
    parametersContainer.innerHTML = '';
    
    config.parameters.forEach(param => {
        const formGroup = document.createElement('div');
        formGroup.className = 'mb-3';
        
        const label = document.createElement('label');
        label.htmlFor = param.field;
        label.className = 'form-label';
        label.textContent = param.label;
        
        let input;
        
        if (param.type === 'select') {
            input = document.createElement('select');
            input.className = 'form-select';
            
            param.options.forEach(option => {
                const optionElem = document.createElement('option');
                optionElem.value = option.value;
                optionElem.textContent = option.label;
                input.appendChild(optionElem);
            });
        } else if (param.type === 'date') {
            input = document.createElement('input');
            input.type = 'date';
            input.className = 'form-control';
        } else {
            input = document.createElement('input');
            input.type = param.type || 'text';
            input.className = 'form-control';
        }
        
        input.id = param.field;
        input.name = param.field;
        if (param.required) input.required = true;
        
        formGroup.appendChild(label);
        formGroup.appendChild(input);
        parametersContainer.appendChild(formGroup);
    });
}

// Run the selected report
function runReport() {
    const reportType = currentReportType;
    if (!reportType) {
        alert('Please select a report to run');
        return;
    }
    
    const config = reportConfig[reportType];
    
    // Show loading overlay
    document.getElementById('loadingOverlay').classList.remove('d-none');
    
    // Collect parameters
    const parameters = {};
    config.parameters.forEach(param => {
        const field = document.getElementById(param.field);
        if (field) {
            parameters[param.field] = field.value;
        }
    });
    
    // Call API to run report
    fetch(config.apiEndpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(parameters)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => Promise.reject(err));
        }
        return response.json();
    })
    .then(data => {
        // Store report data for potential export
        currentReportData = data;
        
        // Display report results
        displayReportResults(data, config);
        
        // Show results card
        document.getElementById('reportResultsCard').classList.remove('d-none');
        
        // Update report title
        document.getElementById('reportTitle').textContent = config.title;
    })
    .catch(error => {
        console.error('Error running report:', error);
        alert('Error running report: ' + (error.detail || 'Unknown error'));
    })
    .finally(() => {
        // Hide loading overlay
        document.getElementById('loadingOverlay').classList.add('d-none');
    });
}

// Display report results in the table
function displayReportResults(data, config) {
    // Reset pagination to first page when running a new report
    currentReportPage = 1;
    
    // Store the complete data set
    currentReportData = data;
    
    // Clear existing table
    const tableHeader = document.getElementById('reportTableHeader');
    const tableBody = document.getElementById('reportTableBody');
    tableHeader.innerHTML = '';
    tableBody.innerHTML = '';
    
    // Create header row
    const headerRow = document.createElement('tr');
    config.columns.forEach(column => {
        const th = document.createElement('th');
        th.textContent = column.header;
        headerRow.appendChild(th);
    });
    tableHeader.appendChild(headerRow);
    
    // Create data rows
    if (data.length === 0) {
        const emptyRow = document.createElement('tr');
        const emptyCell = document.createElement('td');
        emptyCell.colSpan = config.columns.length;
        emptyCell.className = 'text-center';
        emptyCell.textContent = 'No data found';
        emptyRow.appendChild(emptyCell);
        
        // Hide pagination if no data
        document.getElementById('reportPagination')?.classList.add('d-none');
    } else {
        // Calculate total pages and ensure current page is valid
        totalReportPages = Math.ceil(data.length / reportItemsPerPage);
        if (currentReportPage > totalReportPages) {
            currentReportPage = totalReportPages;
        } else if (currentReportPage < 1) {
            currentReportPage = 1;
        }
        
        // Calculate start and end indices for current page
        const startIndex = (currentReportPage - 1) * reportItemsPerPage;
        const endIndex = Math.min(startIndex + reportItemsPerPage, data.length);
        
        // Get current page data
        const currentPageData = data.slice(startIndex, endIndex);
        
        // Render current page data
        currentPageData.forEach(item => {
            const row = document.createElement('tr');
            
            config.columns.forEach(column => {
                const td = document.createElement('td');
                
                // Format cell based on type
                if (column.type === 'number') {
                    td.className = 'report-num-cell';
                    td.textContent = item[column.field]?.toLocaleString() || '0';
                } else if (column.type === 'percentage') {
                    td.className = 'report-num-cell';
                    td.textContent = (item[column.field] * 100).toFixed(2) + '%';
                } else if (column.type === 'date') {
                    td.className = 'report-date-cell';
                    td.textContent = formatDate(item[column.field]);
                } else {
                    td.textContent = item[column.field] || '';
                }
                
                row.appendChild(td);
            });
            
            tableBody.appendChild(row);
        });
        
        // Add pagination controls
        renderReportPagination(data.length);
    }
}

// Render pagination controls for reports
function renderReportPagination(totalItems) {
    // Get or create pagination container
    let paginationContainer = document.getElementById('reportPagination');
    
    if (!paginationContainer) {
        // Create pagination container if it doesn't exist
        paginationContainer = document.createElement('nav');
        paginationContainer.id = 'reportPagination';
        paginationContainer.setAttribute('aria-label', 'Report pagination');
        paginationContainer.className = 'mt-3';
        
        // Find the table container to append pagination after it
        const tableContainer = document.querySelector('#reportResultsCard .table-responsive');
        if (tableContainer && tableContainer.parentNode) {
            tableContainer.parentNode.insertBefore(paginationContainer, tableContainer.nextSibling);
        }
    }
    
    // Show pagination container
    paginationContainer.classList.remove('d-none');
    
    // Calculate total pages
    totalReportPages = Math.ceil(totalItems / reportItemsPerPage);
    
    // Create pagination HTML
    let paginationHTML = `
        <ul class="pagination justify-content-center">
            <li class="page-item ${currentReportPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="prev">&laquo;</a>
            </li>
    `;
    
    // Determine which page numbers to show
    let startPage = Math.max(1, currentReportPage - 2);
    let endPage = Math.min(totalReportPages, startPage + 4);
    
    // Adjust if we're showing fewer than 5 pages
    if (endPage - startPage < 4) {
        startPage = Math.max(1, endPage - 4);
    }
    
    // Add page numbers
    for (let i = startPage; i <= endPage; i++) {
        paginationHTML += `
            <li class="page-item ${i === currentReportPage ? 'active' : ''}">
                <a class="page-link" href="#" data-page="${i}">${i}</a>
            </li>
        `;
    }
    
    paginationHTML += `
            <li class="page-item ${currentReportPage === totalReportPages ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="next">&raquo;</a>
            </li>
        </ul>
        <div class="text-center mt-2">
            <small>Showing ${totalItems === 0 ? 0 : (currentReportPage - 1) * reportItemsPerPage + 1} to ${Math.min(currentReportPage * reportItemsPerPage, totalItems)} of ${totalItems} rows</small>
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
                if (currentReportPage > 1) {
                    currentReportPage--;
                    refreshReportTable();
                }
            } else if (page === 'next') {
                if (currentReportPage < totalReportPages) {
                    currentReportPage++;
                    refreshReportTable();
                }
            } else {
                currentReportPage = parseInt(page);
                refreshReportTable();
            }
        });
    });
}

// Refresh the report table with the current page data
function refreshReportTable() {
    const config = reportConfig[currentReportType];
    if (!config || !currentReportData.length) return;
    
    const tableBody = document.getElementById('reportTableBody');
    tableBody.innerHTML = '';
    
    // Calculate start and end indices for current page
    const startIndex = (currentReportPage - 1) * reportItemsPerPage;
    const endIndex = Math.min(startIndex + reportItemsPerPage, currentReportData.length);
    
    // Get current page data
    const currentPageData = currentReportData.slice(startIndex, endIndex);
    
    // Render current page data
    currentPageData.forEach(item => {
        const row = document.createElement('tr');
        
        config.columns.forEach(column => {
            const td = document.createElement('td');
            
            // Format cell based on type
            if (column.type === 'number') {
                td.className = 'report-num-cell';
                td.textContent = item[column.field]?.toLocaleString() || '0';
            } else if (column.type === 'percentage') {
                td.className = 'report-num-cell';
                td.textContent = (item[column.field] * 100).toFixed(2) + '%';
            } else if (column.type === 'date') {
                td.className = 'report-date-cell';
                td.textContent = formatDate(item[column.field]);
            } else {
                td.textContent = item[column.field] || '';
            }
            
            row.appendChild(td);
        });
        
        tableBody.appendChild(row);
    });
    
    // Update pagination controls
    renderReportPagination(currentReportData.length);
}

// Format a date for display
function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    }).format(date);
}

// Export report data to CSV or XLSX
function exportReport(format) {
    if (currentReportData.length === 0) {
        alert('No data to export');
        return;
    }
    
    const config = reportConfig[currentReportType];
    const fileName = config.title.replace(/\s+/g, '_').toLowerCase() + '_' + 
                    new Date().toISOString().split('T')[0];
    
    if (format === 'csv') {
        exportToCsv(fileName, config);
    } else if (format === 'xlsx') {
        exportToXlsx(fileName, config);
    }
}

// Export data to CSV format
function exportToCsv(fileName, config) {
    // Prepare headers
    const headers = config.columns.map(col => col.header);
    
    // Prepare rows
    const rows = currentReportData.map(item => {
        return config.columns.map(column => {
            // Format value based on column type
            if (column.type === 'number') {
                return item[column.field] || '0';
            } else if (column.type === 'percentage') {
                return ((item[column.field] || 0) * 100).toFixed(2) + '%';
            } else if (column.type === 'date') {
                return item[column.field] || '';
            } else {
                return item[column.field] || '';
            }
        });
    });
    
    // Convert to CSV
    const csvContent = [
        headers.join(','),
        ...rows.map(row => row.join(','))
    ].join('\n');
    
    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    downloadFile(url, fileName + '.csv');
}

// Export data to XLSX format (server-side)
function exportToXlsx(fileName, config) {
    // Prepare the data for export
    const exportData = {
        reportType: currentReportType,
        data: currentReportData,
        fileName: fileName
    };
    
    // Call API endpoint to generate XLSX
    fetch('/api/reports/export-xlsx', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(exportData)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => Promise.reject(err));
        }
        return response.blob();
    })
    .then(blob => {
        const url = URL.createObjectURL(blob);
        downloadFile(url, fileName + '.xlsx');
    })
    .catch(error => {
        console.error('Error exporting to XLSX:', error);
        alert('Error exporting to XLSX: ' + (error.detail || 'Unknown error'));
    });
}

// Helper function to trigger download
function downloadFile(url, fileName) {
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}