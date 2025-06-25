import React, { useState, useEffect } from 'react';
import { Modal, Button, Form, Alert, Spinner, Row, Col, Card, Badge } from 'react-bootstrap';
import { useToast } from '@/context/ToastContext';
import { calculationsApi } from '@/services/calculationsApi';

interface DependentCalculationModalProps {
  show: boolean;
  onHide: () => void;
  onSuccess: () => void;
}

interface AvailableCalculation {
  id: string;
  display_name: string;
  type: 'user' | 'system';
  reference: string;
  variable_name: string;
  description: string;
  group_level: string;
  formula: string;
}

interface ExpressionValidation {
  is_valid: boolean;
  error?: string;
  referenced_variables: string[];
  declared_variables: string[];
  dependency_mapping: Record<string, string>;
  expression_preview: string;
}

interface ExpressionToken {
  type: 'variable' | 'operator' | 'function' | 'literal' | 'parenthesis';
  value: string;
  displayValue?: string;
  id: string;
}

const ExpressionBuilder: React.FC<{
  selectedCalculations: AvailableCalculation[];
  expression: string;
  onChange: (expression: string) => void;
  isInvalid?: boolean;
  errorMessage?: string;
}> = ({
  selectedCalculations,
  expression,
  onChange,
  isInvalid,
  errorMessage
}) => {
  const [tokens, setTokens] = useState<ExpressionToken[]>([]);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Convert expression string to tokens
  useEffect(() => {
    parseExpressionToTokens(expression);
  }, [expression]);

  // Convert tokens to expression string
  useEffect(() => {
    const newExpression = tokens.map(token => token.value).join(' ');
    if (newExpression !== expression) {
      onChange(newExpression);
    }
  }, [tokens]);

  const parseExpressionToTokens = (expr: string) => {
    // Simple parser - in production you'd want a more robust one
    const parts = expr.split(/(\$\{[^}]+\}|\+|\-|\*|\/|\(|\)|,)/g).filter(p => p.trim());
    const newTokens: ExpressionToken[] = parts.map((part, index) => {
      const trimmed = part.trim();
      if (trimmed.startsWith('${') && trimmed.endsWith('}')) {
        const varName = trimmed.slice(2, -1);
        const calc = selectedCalculations.find(c => c.variable_name === varName);
        return {
          type: 'variable',
          value: trimmed,
          displayValue: calc?.display_name || varName,
          id: `token-${index}`
        };
      } else if (['+', '-', '*', '/'].includes(trimmed)) {
        return {
          type: 'operator',
          value: trimmed,
          id: `token-${index}`
        };
      } else if (['(', ')'].includes(trimmed)) {
        return {
          type: 'parenthesis',
          value: trimmed,
          id: `token-${index}`
        };
      } else if (['CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'COALESCE'].includes(trimmed.toUpperCase())) {
        return {
          type: 'function',
          value: trimmed.toUpperCase(),
          id: `token-${index}`
        };
      } else {
        return {
          type: 'literal',
          value: trimmed,
          id: `token-${index}`
        };
      }
    });
    setTokens(newTokens);
  };

  const addToken = (token: Omit<ExpressionToken, 'id'>) => {
    const newToken = { ...token, id: `token-${Date.now()}-${Math.random()}` };
    setTokens(prev => [...prev, newToken]);
  };

  const removeToken = (tokenId: string) => {
    setTokens(prev => prev.filter(t => t.id !== tokenId));
  };

  const clearExpression = () => {
    setTokens([]);
  };

  const insertTemplate = (template: 'case_when' | 'coalesce' | 'simple_math') => {
    const templates = {
      case_when: [
        { type: 'function', value: 'CASE' },
        { type: 'function', value: 'WHEN' },
        { type: 'literal', value: 'condition' },
        { type: 'function', value: 'THEN' },
        { type: 'literal', value: 'value1' },
        { type: 'function', value: 'ELSE' },
        { type: 'literal', value: 'value2' },
        { type: 'function', value: 'END' }
      ],
      coalesce: [
        { type: 'function', value: 'COALESCE(' },
        { type: 'literal', value: 'value1' },
        { type: 'literal', value: ',' },
        { type: 'literal', value: '0' },
        { type: 'parenthesis', value: ')' }
      ],
      simple_math: [
        { type: 'literal', value: 'value1' },
        { type: 'operator', value: '+' },
        { type: 'literal', value: 'value2' }
      ]
    };

    const templateTokens = templates[template].map((token, index) => ({
      ...token,
      id: `template-${Date.now()}-${index}`
    })) as ExpressionToken[];

    setTokens(prev => [...prev, ...templateTokens]);
  };

  return (
    <Card className="expression-builder">
      <Card.Header className="d-flex justify-content-between align-items-center">
        <h6 className="mb-0">Expression Builder</h6>
        <div>
          <Button
            variant="outline-secondary"
            size="sm"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="me-2"
          >
            {showAdvanced ? 'Simple Mode' : 'Advanced Mode'}
          </Button>
          <Button variant="outline-danger" size="sm" onClick={clearExpression}>
            Clear All
          </Button>
        </div>
      </Card.Header>
      <Card.Body>
        {/* Variables Section */}
        <div className="mb-3 button-section">
          <small className="text-muted fw-bold section-label">Variables:</small>
          <div className="mt-1">
            {selectedCalculations.length === 0 ? (
              <small className="text-muted">Select dependencies above to see available variables</small>
            ) : (
              selectedCalculations.map((calc) => (
                <Button
                  key={calc.id}
                  variant="outline-primary"
                  size="sm"
                  className="me-2 mb-1"
                  onClick={() => addToken({
                    type: 'variable',
                    value: `\${${calc.variable_name}}`,
                    displayValue: calc.display_name
                  })}
                >
                  <i className="bi bi-plus me-1"></i>
                  {calc.display_name}
                </Button>
              ))
            )}
          </div>
        </div>

        {/* Operators Section */}
        <div className="mb-3 button-section">
          <small className="text-muted fw-bold section-label">Operators:</small>
          <div className="mt-1">
            {[
              { symbol: '+', label: 'Add' },
              { symbol: '-', label: 'Subtract' },
              { symbol: '*', label: 'Multiply' },
              { symbol: '/', label: 'Divide' },
              { symbol: '=', label: 'Equals' },
              { symbol: '>', label: 'Greater than' },
              { symbol: '<', label: 'Less than' }
            ].map((op) => (
              <Button
                key={op.symbol}
                variant="outline-secondary"
                size="sm"
                className="me-2 mb-1"
                onClick={() => addToken({ type: 'operator', value: op.symbol })}
                title={op.label}
              >
                {op.symbol}
              </Button>
            ))}
          </div>
        </div>

        {/* Functions and Parentheses */}
        <div className="mb-3 button-section">
          <small className="text-muted fw-bold section-label">Functions & Parentheses:</small>
          <div className="mt-1">
            <Button
              variant="outline-info"
              size="sm"
              className="me-2 mb-1"
              onClick={() => addToken({ type: 'parenthesis', value: '(' })}
            >
              (
            </Button>
            <Button
              variant="outline-info"
              size="sm"
              className="me-2 mb-1"
              onClick={() => addToken({ type: 'parenthesis', value: ')' })}
            >
              )
            </Button>
            <Button
              variant="outline-success"
              size="sm"
              className="me-2 mb-1"
              onClick={() => addToken({ type: 'function', value: 'COALESCE(' })}
            >
              COALESCE
            </Button>
            {showAdvanced && (
              <>
                <Button
                  variant="outline-warning"
                  size="sm"
                  className="me-2 mb-1"
                  onClick={() => addToken({ type: 'function', value: 'CASE' })}
                >
                  CASE
                </Button>
                <Button
                  variant="outline-warning"
                  size="sm"
                  className="me-2 mb-1"
                  onClick={() => addToken({ type: 'function', value: 'WHEN' })}
                >
                  WHEN
                </Button>
                <Button
                  variant="outline-warning"
                  size="sm"
                  className="me-2 mb-1"
                  onClick={() => addToken({ type: 'function', value: 'THEN' })}
                >
                  THEN
                </Button>
                <Button
                  variant="outline-warning"
                  size="sm"
                  className="me-2 mb-1"
                  onClick={() => addToken({ type: 'function', value: 'ELSE' })}
                >
                  ELSE
                </Button>
                <Button
                  variant="outline-warning"
                  size="sm"
                  className="me-2 mb-1"
                  onClick={() => addToken({ type: 'function', value: 'END' })}
                >
                  END
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Quick Templates */}
        <div className="mb-3 button-section">
          <small className="text-muted fw-bold section-label">Quick Templates:</small>
          <div className="mt-1">
            <Button
              variant="outline-dark"
              size="sm"
              className="me-2 mb-1"
              onClick={() => insertTemplate('simple_math')}
            >
              <i className="bi bi-calculator me-1"></i>
              Simple Math
            </Button>
            <Button
              variant="outline-dark"
              size="sm"
              className="me-2 mb-1"
              onClick={() => insertTemplate('coalesce')}
            >
              <i className="bi bi-shield-check me-1"></i>
              Null Check
            </Button>
            {showAdvanced && (
              <Button
                variant="outline-dark"
                size="sm"
                className="me-2 mb-1"
                onClick={() => insertTemplate('case_when')}
              >
                <i className="bi bi-diagram-3 me-1"></i>
                Conditional Logic
              </Button>
            )}
          </div>
        </div>

        {/* Expression Preview */}
        <div className="mb-3">
          <small className="text-muted fw-bold section-label">Expression Preview:</small>
          <div className="border rounded p-2 mt-1 expression-preview" style={{ minHeight: '60px', backgroundColor: '#f8f9fa' }}>
            {tokens.length === 0 ? (
              <small className="text-muted">Your expression will appear here as you build it</small>
            ) : (
              <div className="d-flex flex-wrap align-items-center">
                {tokens.map((token) => (
                  <Badge
                    key={token.id}
                    bg={
                      token.type === 'variable' ? 'primary' :
                      token.type === 'operator' ? 'secondary' :
                      token.type === 'function' ? 'success' :
                      token.type === 'parenthesis' ? 'info' : 'light'
                    }
                    className="me-1 mb-1 position-relative"
                    style={{ fontSize: '0.9em', cursor: 'pointer' }}
                    onClick={() => removeToken(token.id)}
                    title="Click to remove"
                  >
                    {token.displayValue || token.value}
                    <i className="bi bi-x-circle-fill ms-1" style={{ fontSize: '0.7em' }}></i>
                  </Badge>
                ))}
              </div>
            )}
          </div>
          {isInvalid && errorMessage && (
            <Alert variant="danger" className="mt-2 py-2">
              <i className="bi bi-exclamation-triangle me-2"></i>
              {errorMessage}
            </Alert>
          )}
        </div>

        {/* Raw Expression (for advanced users) */}
        {showAdvanced && (
          <div>
            <small className="text-muted fw-bold section-label">Raw Expression (Advanced):</small>
            <Form.Control
              as="textarea"
              rows={3}
              value={expression}
              onChange={(e) => onChange(e.target.value)}
              placeholder="You can also edit the raw expression here..."
              style={{ fontFamily: 'monospace', fontSize: '0.9em' }}
              className="mt-1"
            />
          </div>
        )}
      </Card.Body>
    </Card>
  );
};

export const DependentCalculationModal: React.FC<DependentCalculationModalProps> = ({
  show,
  onHide,
  onSuccess
}) => {
  const { showToast } = useToast();
  
  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    group_level: 'tranche',
    result_column_name: '',
    calculation_dependencies: [] as string[],
    calculation_expression: ''
  });
  
  // UI state
  const [loading, setLoading] = useState(false);
  const [availableCalculations, setAvailableCalculations] = useState<AvailableCalculation[]>([]);
  const [expressionValidation, setExpressionValidation] = useState<ExpressionValidation | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Load available calculations when modal opens
  useEffect(() => {
    if (show) {
      loadAvailableCalculations();
      resetForm();
    }
  }, [show]);

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      group_level: 'tranche',
      result_column_name: '',
      calculation_dependencies: [],
      calculation_expression: ''
    });
    setErrors({});
    setExpressionValidation(null);
  };

  const loadAvailableCalculations = async () => {
    try {
      const response = await calculationsApi.getAvailableCalculationsForDependencies();
      setAvailableCalculations(response.available_calculations);
    } catch (error) {
      console.error('Error loading available calculations:', error);
      showToast('Failed to load available calculations', 'error');
    }
  };

  const validateExpression = async () => {
    if (!formData.calculation_expression.trim() || formData.calculation_dependencies.length === 0) {
      setExpressionValidation(null);
      return;
    }

    setLoading(true);
    try {
      const response = await calculationsApi.validateCalculationExpression({
        expression: formData.calculation_expression,
        dependencies: formData.calculation_dependencies
      });
      setExpressionValidation(response);
      
      if (!response.is_valid) {
        setErrors(prev => ({ ...prev, calculation_expression: response.error || 'Invalid expression' }));
      } else {
        setErrors(prev => {
          const newErrors = { ...prev };
          delete newErrors.calculation_expression;
          return newErrors;
        });
      }
    } catch (error) {
      console.error('Error validating expression:', error);
      setExpressionValidation({
        is_valid: false,
        error: 'Failed to validate expression',
        referenced_variables: [],
        declared_variables: [],
        dependency_mapping: {},
        expression_preview: formData.calculation_expression
      });
    } finally {
      setLoading(false);
    }
  };

  // Validate expression when dependencies or expression change
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      validateExpression();
    }, 500); // Debounce validation

    return () => clearTimeout(timeoutId);
  }, [formData.calculation_expression, formData.calculation_dependencies]);

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    
    // Clear field-specific errors
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const handleDependencyToggle = (calculationId: string) => {
    const newDependencies = formData.calculation_dependencies.includes(calculationId)
      ? formData.calculation_dependencies.filter(id => id !== calculationId)
      : [...formData.calculation_dependencies, calculationId];
    
    handleInputChange('calculation_dependencies', newDependencies);
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    }

    if (!formData.result_column_name.trim()) {
      newErrors.result_column_name = 'Result column name is required';
    } else if (!/^[a-zA-Z][a-zA-Z0-9_]*$/.test(formData.result_column_name)) {
      newErrors.result_column_name = 'Result column name must be a valid SQL identifier';
    }

    if (formData.calculation_dependencies.length === 0) {
      newErrors.calculation_dependencies = 'At least one dependency is required';
    }

    if (!formData.calculation_expression.trim()) {
      newErrors.calculation_expression = 'Expression is required';
    }

    if (expressionValidation && !expressionValidation.is_valid) {
      newErrors.calculation_expression = expressionValidation.error || 'Invalid expression';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setLoading(true);
    try {
      await calculationsApi.createDependentCalculation(formData);
      showToast('Dependent calculation created successfully!', 'success');
      onSuccess();
      onHide();
    } catch (error: any) {
      console.error('Error creating dependent calculation:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to create dependent calculation';
      showToast(errorMessage, 'error');
    } finally {
      setLoading(false);
    }
  };

  const selectedCalculations = availableCalculations.filter(calc => 
    formData.calculation_dependencies.includes(calc.reference)
  );

  return (
    <Modal show={show} onHide={onHide} size="xl" backdrop="static">
      <Modal.Header closeButton>
        <Modal.Title>
          <i className="bi bi-diagram-3 me-2"></i>
          Create Dependent Calculation
        </Modal.Title>
      </Modal.Header>
      
      <Form onSubmit={handleSubmit}>
        <Modal.Body>
          <Alert variant="info" className="mb-4">
            <div className="d-flex align-items-start">
              <i className="bi bi-info-circle me-3 mt-1"></i>
              <div>
                <h6 className="alert-heading mb-2">Dependent Calculations</h6>
                <p className="mb-2">
                  Create calculations that use the results of other calculations. Perfect for complex business logic
                  like "Net Interest Distribution" that depends on multiple other calculations.
                </p>
                <ul className="mb-0">
                  <li><strong>Example:</strong> Net Interest = Interest Distribution - Investment Income</li>
                  <li><strong>Use Variables:</strong> Reference other calculations using <code>${'variable_name'}</code> syntax</li>
                  <li><strong>SQL Expressions:</strong> Use standard SQL expressions with CASE, COALESCE, etc.</li>
                </ul>
              </div>
            </div>
          </Alert>

          <Row>
            {/* Left Column - Basic Information */}
            <Col md={6}>
              <Card className="h-100">
                <Card.Header>
                  <h6 className="mb-0">Basic Information</h6>
                </Card.Header>
                <Card.Body>
                  <Form.Group className="mb-3">
                    <Form.Label>Name <span className="text-danger">*</span></Form.Label>
                    <Form.Control
                      type="text"
                      value={formData.name}
                      onChange={(e) => handleInputChange('name', e.target.value)}
                      isInvalid={!!errors.name}
                      placeholder="e.g., Net Interest Distribution"
                    />
                    <Form.Control.Feedback type="invalid">
                      {errors.name}
                    </Form.Control.Feedback>
                  </Form.Group>

                  <Form.Group className="mb-3">
                    <Form.Label>Description</Form.Label>
                    <Form.Control
                      as="textarea"
                      rows={3}
                      value={formData.description}
                      onChange={(e) => handleInputChange('description', e.target.value)}
                      placeholder="Describe what this calculation does..."
                    />
                  </Form.Group>

                  <Form.Group className="mb-3">
                    <Form.Label>Group Level <span className="text-danger">*</span></Form.Label>
                    <Form.Select
                      value={formData.group_level}
                      onChange={(e) => handleInputChange('group_level', e.target.value)}
                    >
                      <option value="deal">Deal Level</option>
                      <option value="tranche">Tranche Level</option>
                    </Form.Select>
                  </Form.Group>

                  <Form.Group className="mb-3">
                    <Form.Label>Result Column Name <span className="text-danger">*</span></Form.Label>
                    <Form.Control
                      type="text"
                      value={formData.result_column_name}
                      onChange={(e) => handleInputChange('result_column_name', e.target.value)}
                      isInvalid={!!errors.result_column_name}
                      placeholder="e.g., net_interest_distribution"
                    />
                    <Form.Control.Feedback type="invalid">
                      {errors.result_column_name}
                    </Form.Control.Feedback>
                    <Form.Text className="text-muted">
                      Must be a valid SQL identifier (letters, numbers, underscores)
                    </Form.Text>
                  </Form.Group>
                </Card.Body>
              </Card>
            </Col>

            {/* Right Column - Dependencies */}
            <Col md={6}>
              <Card className="h-100">
                <Card.Header>
                  <h6 className="mb-0">
                    Dependencies <span className="text-danger">*</span>
                    <small className="text-muted ms-2">
                      ({formData.calculation_dependencies.length} selected)
                    </small>
                  </h6>
                </Card.Header>
                <Card.Body style={{ maxHeight: '400px', overflowY: 'auto' }}>
                  {availableCalculations.length === 0 ? (
                    <div className="text-center text-muted">
                      <Spinner animation="border" size="sm" className="me-2" />
                      Loading available calculations...
                    </div>
                  ) : (
                    <div className="calculation-dependencies">
                      {availableCalculations.map((calc) => (
                        <div key={calc.id} className="mb-2">
                          <Form.Check
                            type="checkbox"
                            id={`dep-${calc.id}`}
                            checked={formData.calculation_dependencies.includes(calc.reference)}
                            onChange={() => handleDependencyToggle(calc.reference)}
                            label={
                              <div>
                                <strong>{calc.display_name}</strong>
                                <br />
                                <small className="text-muted">
                                  {calc.type === 'user' ? 'User Aggregation' : 'System SQL'} • 
                                  {calc.group_level} level • 
                                  Variable: <code>${calc.variable_name}</code>
                                </small>
                                {calc.description && (
                                  <>
                                    <br />
                                    <small className="text-info">{calc.description}</small>
                                  </>
                                )}
                              </div>
                            }
                          />
                        </div>
                      ))}
                    </div>
                  )}
                  {errors.calculation_dependencies && (
                    <Alert variant="danger" className="mt-2 py-2">
                      {errors.calculation_dependencies}
                    </Alert>
                  )}
                </Card.Body>
              </Card>
            </Col>
          </Row>

          {/* Expression Section */}
          <Row className="mt-3">
            <Col>
              <ExpressionBuilder
                selectedCalculations={selectedCalculations}
                expression={formData.calculation_expression}
                onChange={(expr) => handleInputChange('calculation_expression', expr)}
                isInvalid={!!errors.calculation_expression}
                errorMessage={errors.calculation_expression}
              />
              
              {/* Expression Validation */}
              {expressionValidation && (
                <Alert 
                  variant={expressionValidation.is_valid ? 'success' : 'danger'}
                  className="py-2 mt-3"
                >
                  {expressionValidation.is_valid ? (
                    <div>
                      <i className="bi bi-check-circle me-2"></i>
                      Expression is valid!
                      {expressionValidation.referenced_variables.length > 0 && (
                        <div className="mt-1">
                          <small>
                            References: {expressionValidation.referenced_variables.map(v => `\${${v}}`).join(', ')}
                          </small>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div>
                      <i className="bi bi-exclamation-triangle me-2"></i>
                      {expressionValidation.error}
                    </div>
                  )}
                </Alert>
              )}
            </Col>
          </Row>
        </Modal.Body>
        
        <Modal.Footer>
          <Button variant="secondary" onClick={onHide} disabled={loading}>
            Cancel
          </Button>
          <Button 
            variant="primary" 
            type="submit" 
            disabled={loading || (expressionValidation ? !expressionValidation.is_valid : false)}
          >
            {loading ? (
              <>
                <Spinner animation="border" size="sm" className="me-2" />
                Creating...
              </>
            ) : (
              'Create Dependent Calculation'
            )}
          </Button>
        </Modal.Footer>
      </Form>
    </Modal>
  );
};