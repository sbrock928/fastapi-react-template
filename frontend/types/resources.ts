// Resource-specific types
export interface ResourceColumn {
  field: string;
  header: string;
  type: string;
  required?: boolean;
  minLength?: number;
  placeholder?: string;
  pattern?: string;
  options?: {value: string, text: string}[];
  hasDependents?: boolean;  // Indicates this field affects other fields
  dependsOn?: string;       // Indicates this field depends on another field
}

export interface ResourceConfig {
  apiEndpoint: string;
  modelName: string;
  idField: string;
  columns: ResourceColumn[];
  displayName: string;
}

export type ResourceItem = Record<string, any>;