import React from 'react';
import type { PreviewData } from '@/types/calculations';

interface SqlPreviewModalProps {
  isOpen: boolean;
  previewData: PreviewData | null;
  previewLoading: boolean;
  onClose: () => void;
}

const SqlPreviewModal: React.FC<SqlPreviewModalProps> = ({
  isOpen,
  previewData,
  previewLoading,
  onClose
}) => {
  if (!isOpen) return null;

  return (
    <div className="modal show d-block" tabIndex={-1} style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-xl modal-dialog-scrollable">
        <div className="modal-content" style={{ borderRadius: '12px', overflow: 'hidden' }}>
          <div className="modal-header bg-primary">
            <h5 className="modal-title">
              <i className="bi bi-code-square me-2"></i>
              SQL Preview
            </h5>
            <button
              type="button"
              className="btn-close btn-close-white"
              onClick={onClose}
            ></button>
          </div>
          
          <div className="modal-body" style={{ padding: '1.5rem' }}>
            {previewLoading ? (
              <div 
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                  alignItems: 'center',
                  padding: '3rem 0'
                }}
              >
                <div className="spinner-border text-primary mb-3" role="status">
                  <span className="visually-hidden">Loading...</span>
                </div>
                <span style={{ color: '#6c757d', fontSize: '0.9rem' }}>
                  Generating SQL preview...
                </span>
              </div>
            ) : previewData ? (
              <div>
                {/* Calculation Details */}
                <div 
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                    gap: '1rem',
                    marginBottom: '1.5rem'
                  }}
                >
                  <div 
                    style={{
                      backgroundColor: '#f8f9fa',
                      borderRadius: '8px',
                      padding: '1rem',
                      border: '1px solid #e9ecef'
                    }}
                  >
                    <h6 
                      style={{
                        color: '#6c757d',
                        fontSize: '0.875rem',
                        fontWeight: '600',
                        marginBottom: '0.5rem',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px'
                      }}
                    >
                      Calculation Details
                    </h6>
                    <div style={{ fontSize: '0.9rem', color: '#495057' }}>
                      <div className="mb-2">
                        <strong>Name:</strong> {previewData.calculation_name}
                      </div>
                      <div>
                        <strong>Level:</strong>{' '}
                        <span 
                          style={{
                            display: 'inline-block',
                            padding: '0.25em 0.6em',
                            fontSize: '0.75em',
                            fontWeight: '700',
                            backgroundColor: '#6c757d',
                            color: '#fff',
                            borderRadius: '0.375rem'
                          }}
                        >
                          {previewData.aggregation_level}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <div 
                    style={{
                      backgroundColor: '#f8f9fa',
                      borderRadius: '8px',
                      padding: '1rem',
                      border: '1px solid #e9ecef'
                    }}
                  >
                    <h6 
                      style={{
                        color: '#6c757d',
                        fontSize: '0.875rem',
                        fontWeight: '600',
                        marginBottom: '0.5rem',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px'
                      }}
                    >
                      Sample Parameters
                    </h6>
                    <div style={{ fontSize: '0.9rem', color: '#495057' }}>
                      <div className="mb-1">
                        <strong>Deals:</strong> {previewData.sample_parameters?.deals?.join(', ') || 'N/A'}
                      </div>
                      <div className="mb-1">
                        <strong>Tranches:</strong> {previewData.sample_parameters?.tranches?.join(', ') || 'N/A'}
                      </div>
                      <div>
                        <strong>Cycle:</strong> {previewData.sample_parameters?.cycle || 'N/A'}
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* SQL Query */}
                <div className="mb-3">
                  <div 
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '0.75rem'
                    }}
                  >
                    <h6 
                      style={{
                        color: '#6c757d',
                        fontSize: '0.875rem',
                        fontWeight: '600',
                        marginBottom: '0',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px'
                      }}
                    >
                      Raw Execution SQL
                    </h6>
                    <button
                      className="btn btn-sm btn-outline-secondary"
                      onClick={() => {
                        if (previewData?.generated_sql) {
                          navigator.clipboard.writeText(previewData.generated_sql);
                        }
                      }}
                      title="Copy SQL to clipboard"
                      style={{
                        border: '1px solid #dee2e6',
                        backgroundColor: '#ffffff',
                        color: '#495057'
                      }}
                    >
                      <i className="bi bi-clipboard me-1"></i>
                      Copy
                    </button>
                  </div>
                  <div 
                    style={{
                      backgroundColor: '#ffffff',
                      color: '#212529',
                      border: '1px solid #dee2e6',
                      borderRadius: '8px',
                      padding: '1rem',
                      maxHeight: '400px',
                      overflowY: 'auto',
                      fontFamily: "'Consolas', 'Monaco', 'Courier New', monospace",
                      boxShadow: 'inset 0 1px 3px rgba(0, 0, 0, 0.1)'
                    }}
                  >
                    <pre 
                      style={{ 
                        fontSize: '0.875rem',
                        lineHeight: '1.4',
                        margin: '0',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        color: '#212529'
                      }}
                    >
                      {previewData.generated_sql}
                    </pre>
                  </div>
                  <div 
                    style={{
                      fontSize: '0.8rem',
                      color: '#6c757d',
                      marginTop: '0.5rem',
                      fontStyle: 'italic'
                    }}
                  >
                    This is the exact same SQL that executes when this calculation runs in a report.
                  </div>
                </div>
              </div>
            ) : (
              <div 
                style={{
                  textAlign: 'center',
                  padding: '3rem 0',
                  color: '#6c757d'
                }}
              >
                <i 
                  className="bi bi-exclamation-circle"
                  style={{
                    fontSize: '3rem',
                    marginBottom: '1rem',
                    display: 'block'
                  }}
                ></i>
                <p>No preview data available</p>
              </div>
            )}
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SqlPreviewModal;