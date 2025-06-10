import type { CalculationForm } from '@/types/calculations';

/**
 * Generate full SQL preview for calculation
 */
export const getFullSQLPreview = (calculation: CalculationForm): string => {
  if (!calculation.function_type || !calculation.source || !calculation.source_field) {
    return 'Select aggregation function, source model, and field to see SQL preview';
  }

  // Build the aggregation expression
  let aggregationExpr = '';
  const sourceField = `${calculation.source.toLowerCase()}.${calculation.source_field}`;
  
  if (calculation.function_type === 'WEIGHTED_AVG') {
    const weightField = calculation.weight_field ? 
      `${calculation.source.toLowerCase()}.${calculation.weight_field}` : 
      '[weight_field_required]';
    aggregationExpr = `sum(${sourceField} * ${weightField}) / NULLIF(sum(${weightField}), 0)`;
  } else if (calculation.function_type === 'RAW') {
    aggregationExpr = sourceField;
  } else {
    aggregationExpr = `${calculation.function_type.toLowerCase()}(${sourceField})`;
  }

  // Build FROM and JOIN clauses based on required models
  const requiredModels = new Set(['Deal']); // Always need Deal
  
  // Add required models based on source
  if (calculation.source === 'Tranche' || calculation.level === 'tranche') {
    requiredModels.add('Tranche');
  }
  if (calculation.source === 'TrancheBal') {
    requiredModels.add('Tranche'); // TrancheBal requires Tranche join
    requiredModels.add('TrancheBal');
  }

  // Build GROUP BY columns for aggregated functions
  const groupByColumns = [];
  if (calculation.function_type !== 'RAW') {
    groupByColumns.push('deal.dl_nbr');
    if (requiredModels.has('TrancheBal')) {
      groupByColumns.push('tranchebal.cycle_cde');
    }
    if (calculation.level === 'tranche' && requiredModels.has('Tranche')) {
      groupByColumns.push('tranche.tr_id');
    }
  }

  // Build SELECT columns - include GROUP BY fields for aggregated calculations
  const selectColumns = [];
  
  if (calculation.function_type === 'RAW') {
    // For RAW calculations, include all relevant fields
    selectColumns.push('deal.dl_nbr AS deal_number');
    selectColumns.push('tranchebal.cycle_cde AS cycle_code');
    if (calculation.level === 'tranche') {
      selectColumns.push('tranche.tr_id AS tranche_id');
    }
  } else {
    // For aggregated calculations, include GROUP BY fields in SELECT
    selectColumns.push('deal.dl_nbr AS deal_number');
    if (requiredModels.has('TrancheBal')) {
      selectColumns.push('tranchebal.cycle_cde AS cycle_code');
    }
    if (calculation.level === 'tranche' && requiredModels.has('Tranche')) {
      selectColumns.push('tranche.tr_id AS tranche_id');
    }
  }
  
  // Add the calculation result
  const calcName = calculation.name || 'Calculation Result';
  selectColumns.push(`${aggregationExpr} AS "${calcName}"`);

  let fromClause = 'FROM deal';
  if (requiredModels.has('Tranche')) {
    fromClause += ' JOIN tranche ON deal.dl_nbr = tranche.dl_nbr';
  }
  if (requiredModels.has('TrancheBal')) {
    fromClause += ' JOIN tranchebal ON tranche.dl_nbr = tranchebal.dl_nbr AND tranche.tr_id = tranchebal.tr_id';
  }

  // Build WHERE clause
  const whereConditions = [];
  whereConditions.push("deal.dl_nbr IN (101, 102, 103)");
  if (requiredModels.has('Tranche')) {
    whereConditions.push("tranche.tr_id IN ('A', 'B')");
  }
  if (requiredModels.has('TrancheBal')) {
    whereConditions.push("tranchebal.cycle_cde = 202404");
  }

  // Build GROUP BY clause for aggregated functions
  let groupByClause = '';
  if (calculation.function_type !== 'RAW' && groupByColumns.length > 0) {
    groupByClause = ` GROUP BY ${groupByColumns.join(', ')}`;
  }

  // Combine all parts with proper formatting
  const sqlParts = [
    `SELECT ${selectColumns.join(', ')}`,
    fromClause,
    `WHERE ${whereConditions.join(' AND ')}`
  ];
  
  if (groupByClause) {
    sqlParts.push(groupByClause.trim()); // Remove leading space
  }
  
  return sqlParts.join('\n');
};