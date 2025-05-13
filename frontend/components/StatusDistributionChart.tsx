import React from 'react';

interface StatusItem {
  status_code: number;
  count: number;
  description: string;
}

interface StatusDistributionChartProps {
  distribution: StatusItem[];
  onStatusClick: (statusCategory: string) => void;
}

const StatusDistributionChart: React.FC<StatusDistributionChartProps> = ({ 
  distribution, 
  onStatusClick 
}) => {
  // Calculate total for percentages
  const total = distribution.reduce((sum, item) => sum + item.count, 0);

  // Group by description
  const groupedDistribution = distribution.reduce((acc, item) => {
    if (!acc[item.description]) {
      acc[item.description] = {
        description: item.description,
        count: 0,
        statusCodes: []
      };
    }
    acc[item.description].count += item.count;
    acc[item.description].statusCodes.push(item.status_code);
    return acc;
  }, {} as Record<string, { description: string; count: number; statusCodes: number[] }>);

  // Convert to array for rendering
  const statusGroups = Object.values(groupedDistribution);

  // Define colors for different status groups
  const getColorForGroup = (description: string): string => {
    switch (description) {
      case 'Success': return '#28a745';
      case 'Redirection': return '#fd7e14';
      case 'Client Error': return '#dc3545';
      case 'Server Error': return '#6f42c1';
      default: return '#93186C'; // Changed from #6c757d to match our new theme
    }
  };

  return (
    <div className="card mb-4">
      <div className="card-header bg-primary text-white">
        <h5 className="mb-0">Status Code Distribution</h5>
      </div>
      <div className="card-body">
        {total === 0 ? (
          <div className="text-center py-3">
            <p className="text-muted">No log data available for the selected time period.</p>
          </div>
        ) : (
          <>
            {/* Wrap the progress bars in a container with proper overflow handling */}
            <div className="d-flex flex-column mb-3 w-100 overflow-hidden">
              {statusGroups.map(group => (
                <div 
                  key={group.description}
                  className="status-group mb-2 w-100"
                >
                  <div className="d-flex align-items-center">
                    <span className="status-label me-2" style={{ minWidth: '120px' }}>
                      {group.description}:
                    </span>
                    <div 
                      className="progress flex-grow-1" 
                      style={{ height: '24px', cursor: 'pointer' }}
                      onClick={() => {
                        onStatusClick(group.description);
                      }}
                      title={`${group.count} logs with ${group.description} status codes (${Math.round((group.count / total) * 100)}%)`}
                    >
                      <div 
                        className="progress-bar"
                        role="progressbar"
                        style={{ 
                          width: `${Math.round((group.count / total) * 100)}%`, 
                          backgroundColor: getColorForGroup(group.description) 
                        }}
                        aria-valuenow={(group.count / total) * 100}
                        aria-valuemin={0}
                        aria-valuemax={100}
                      >
                        {group.count > 0 ? `${Math.round((group.count / total) * 100)}%` : ''}
                      </div>
                    </div>
                    <span className="ms-2 text-nowrap" style={{ minWidth: '80px' }}>
                      ({group.count} logs)
                    </span>
                  </div>
                </div>
              ))}
            </div>
            <div className="d-flex flex-wrap justify-content-around mt-3">
              {statusGroups.map(group => (
                <div key={group.description} className="text-center mb-2">
                  <span 
                    className="badge rounded-pill px-3 py-2"
                    style={{ backgroundColor: getColorForGroup(group.description), cursor: 'pointer' }}
                    onClick={() => onStatusClick(group.description)}
                  >
                    {group.description}: {group.count} logs
                  </span>
                </div>
              ))}
            </div>
            <div className="text-center mt-3">
              <small className="text-muted">Click on a status category to filter logs</small>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default StatusDistributionChart;
