import type { ResourceConfig } from '@/types';

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
      { field: 'department', header: 'Department', type: 'select', required: true, 
        options: [
          { value: 'Engineering', text: 'Engineering' },
          { value: 'Marketing', text: 'Marketing' },
          { value: 'Sales', text: 'Sales' },
          { value: 'HR', text: 'HR' },
          { value: 'Finance', text: 'Finance' },
          { value: 'Product', text: 'Product' }
        ],
        hasDependents: true },
      { field: 'position', header: 'Position', type: 'select', required: true, dependsOn: 'department' }
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
          { value: 'FREE', text: 'Free' },
          { value: 'BASIC', text: 'Basic' },
          { value: 'PREMIUM', text: 'Premium' },
          { value: 'ENTERPRISE', text: 'Enterprise' }
        ]
      },
      { field: 'signup_date', header: 'Signup Date', type: 'datetime-local', required: true },
      { field: 'last_billing_date', header: 'Last Billing Date', type: 'datetime-local', required: false },
      { field: 'is_active', header: 'Active', type: 'checkbox', required: false }
    ],
    displayName: 'Subscriber'
  }
};

export default resourceConfig;
