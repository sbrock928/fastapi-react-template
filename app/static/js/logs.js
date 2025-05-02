/**
 * Logs management JavaScript
 * Handles fetching, displaying, and filtering log data
 */

// Logs page functionality
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const logsTableBody = document.getElementById('logsTableBody');
    const timeRangeSelect = document.getElementById('timeRangeSelect');
    const refreshButton = document.getElementById('refreshLogs');
    const loadMoreButton = document.getElementById('loadMoreBtn');
    const totalCountSpan = document.getElementById('totalCount');
    const filterInput = document.getElementById('logFilterInput');
    
    // State variables
    let currentOffset = 0;
    const limit = 50;
    let allLogs = [];
    let filteredLogs = [];
    
    // Load initial logs
    loadLogs();
    
    // Event listeners
    refreshButton.addEventListener('click', () => {
        currentOffset = 0;
        loadLogs();
    });
    
    timeRangeSelect.addEventListener('change', () => {
        currentOffset = 0;
        loadLogs();
    });
    
    loadMoreButton.addEventListener('click', () => {
        currentOffset += limit;
        loadLogs(true); // Append mode
    });
    
    filterInput.addEventListener('input', filterLogs);
    
    // Function to load logs from the API
    function loadLogs(append = false) {
        const hours = timeRangeSelect.value;
        const url = `/api/logs/?limit=${limit}&offset=${currentOffset}&hours=${hours}`;
        
        if (!append) {
            logsTableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-4">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="mt-2">Loading logs...</p>
                    </td>
                </tr>
            `;
        }
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (!append) {
                    allLogs = data;
                    filteredLogs = [...data];
                } else {
                    allLogs = [...allLogs, ...data];
                    filteredLogs = [...allLogs];
                }
                
                renderLogs();
                
                // Hide load more button if no more data
                loadMoreButton.style.display = data.length < limit ? 'none' : 'block';
            })
            .catch(error => {
                console.error('Error fetching logs:', error);
                logsTableBody.innerHTML = `
                    <tr>
                        <td colspan="7" class="text-center text-danger py-4">
                            Error loading logs. Please try again.
                        </td>
                    </tr>
                `;
            });
    }
    
    // Function to filter logs based on user input
    function filterLogs() {
        const filterText = filterInput.value.toLowerCase();
        
        if (!filterText.trim()) {
            filteredLogs = [...allLogs];
        } else {
            filteredLogs = allLogs.filter(log => {
                return (
                    log.method.toLowerCase().includes(filterText) ||
                    log.path.toLowerCase().includes(filterText) ||
                    log.status_code.toString().includes(filterText) ||
                    (log.client_ip && log.client_ip.toLowerCase().includes(filterText))
                );
            });
        }
        
        renderLogs();
    }
    
    // Function to render logs to the table
    function renderLogs() {
        if (filteredLogs.length === 0) {
            logsTableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-4">
                        No logs found. Try changing your filter or time range.
                    </td>
                </tr>
            `;
            totalCountSpan.textContent = '0 logs';
            return;
        }
        
        let tableHTML = '';
        
        filteredLogs.forEach(log => {
            // Format date
            const date = new Date(log.timestamp);
            const formattedDate = date.toLocaleString();
            
            // Format status with color
            let statusClass = 'bg-success';
            if (log.status_code >= 400) statusClass = 'bg-danger';
            else if (log.status_code >= 300) statusClass = 'bg-warning';
            
            tableHTML += `
                <tr>
                    <td>${formattedDate}</td>
                    <td><span class="badge bg-primary">${log.method}</span></td>
                    <td>${log.path}</td>
                    <td><span class="badge ${statusClass}">${log.status_code}</span></td>
                    <td>${log.client_ip || 'unknown'}</td>
                    <td>${log.processing_time ? log.processing_time.toFixed(2) + ' ms' : 'N/A'}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-secondary" 
                                onclick="showLogDetails(${log.id})">
                            Details
                        </button>
                    </td>
                </tr>
            `;
        });
        
        logsTableBody.innerHTML = tableHTML;
        totalCountSpan.textContent = `${filteredLogs.length} logs`;
    }
});

// Function to show log details in modal
function showLogDetails(logId) {
    // Find the log in the filtered logs
    fetch(`/api/logs/?limit=1&offset=0&log_id=${logId}`)
        .then(response => response.json())
        .then(data => {
            if (data.length === 0) {
                console.error('Log not found');
                return;
            }
            
            const log = data[0];
            
            // Populate modal fields
            document.getElementById('detailTimestamp').textContent = new Date(log.timestamp).toLocaleString();
            document.getElementById('detailMethod').textContent = log.method;
            document.getElementById('detailPath').textContent = log.path;
            document.getElementById('detailStatus').textContent = log.status_code;
            document.getElementById('detailIp').textContent = log.client_ip || 'Unknown';
            document.getElementById('detailTime').textContent = log.processing_time ? log.processing_time.toFixed(2) : 'N/A';
            
            // Format JSON for headers and body
            try {
                const headers = JSON.parse(log.request_headers || '{}');
                document.getElementById('detailHeaders').textContent = JSON.stringify(headers, null, 2);
            } catch (e) {
                document.getElementById('detailHeaders').textContent = log.request_headers || 'No headers captured';
            }
            
            try {
                // Try to parse as JSON first
                const bodyObj = JSON.parse(log.request_body || '{}');
                document.getElementById('detailBody').textContent = JSON.stringify(bodyObj, null, 2);
            } catch (e) {
                // If not valid JSON, just show as is
                document.getElementById('detailBody').textContent = log.request_body || 'No body captured';
            }
            
            // Show the modal
            const modal = new bootstrap.Modal(document.getElementById('logDetailsModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error fetching log details:', error);
        });
}