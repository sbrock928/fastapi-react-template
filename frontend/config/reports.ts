import type { ReportConfig } from '@/types';

const reportConfig: Record<string, ReportConfig> = {
  employees_by_department: {
    apiEndpoint: '/reports/employees-by-department',
    title: 'Employees by Department',
    columns: [
      { field: 'department', header: 'Department', type: 'text' },
      { field: 'count', header: 'Number of Employees', type: 'number' },
      { field: 'percentage', header: 'Percentage', type: 'percentage' }
    ]
  },
  resource_counts: {
    apiEndpoint: '/reports/resource-counts',
    title: 'Resource Counts Summary',
    columns: [
      { field: 'resource_type', header: 'Resource Type', type: 'text' },
      { field: 'count', header: 'Count', type: 'number' }
    ]
  }
};

export default reportConfig;
