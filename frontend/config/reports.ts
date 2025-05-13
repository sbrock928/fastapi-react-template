import type { ReportConfig } from '@/types';

const reportConfig: Record<string, ReportConfig> = {
  users_by_creation: {
    apiEndpoint: '/reports/users-by-creation',
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
    apiEndpoint: '/reports/employees-by-department',
    title: 'Employees by Department',
    columns: [
      { field: 'department', header: 'Department', type: 'text' },
      { field: 'count', header: 'Number of Employees', type: 'number' },
      { field: 'percentage', header: 'Percentage', type: 'percentage' }
    ],
    parameters: []
  },
  resource_counts: {
    apiEndpoint: '/reports/resource-counts',
    title: 'Resource Counts Summary',
    columns: [
      { field: 'resource_type', header: 'Resource Type', type: 'text' },
      { field: 'count', header: 'Count', type: 'number' }
    ],
    parameters: [
      { 
        field: 'cycle_code', 
        label: 'Cycle Code', 
        type: 'select',
        dynamicOptions: 'cycle_codes',
        options: [
          { value: '', label: 'All Cycles' }
        ]
      }
    ]
  }
};

export default reportConfig;
