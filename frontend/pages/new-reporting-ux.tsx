import { useState, useEffect } from 'react';

// Mock data - this would come from your API
const mockDeals = [
  {
    id: 1,
    name: "GSAMP Trust 2024-1",
    originator: "Goldman Sachs",
    deal_type: "RMBS",
    total_principal: 2500000000,
    credit_rating: "AAA",
    yield_rate: 0.0485,
    closing_date: "2024-01-15"
  },
  {
    id: 2,
    name: "Wells Fargo Commercial 2024-A",
    originator: "Wells Fargo",
    deal_type: "CMBS",
    total_principal: 1800000000,
    credit_rating: "AA+",
    yield_rate: 0.0520,
    closing_date: "2024-02-20"
  },
  {
    id: 3,
    name: "Chase Auto Receivables 2024-1",
    originator: "JPMorgan Chase",
    deal_type: "Auto ABS",
    total_principal: 1200000000,
    credit_rating: "AAA",
    yield_rate: 0.0395,
    closing_date: "2024-03-10"
  }
];

const mockTranches = {
  1: [
    { id: 1, name: "Class A-1", class_name: "A-1", principal_amount: 1500000000, interest_rate: 0.0450, credit_rating: "AAA", payment_priority: 1 },
    { id: 2, name: "Class A-2", class_name: "A-2", principal_amount: 750000000, interest_rate: 0.0485, credit_rating: "AAA", payment_priority: 2 },
    { id: 3, name: "Class B", class_name: "B", principal_amount: 200000000, interest_rate: 0.0650, credit_rating: "AA", payment_priority: 3 },
    { id: 4, name: "Class C", class_name: "C", principal_amount: 50000000, interest_rate: 0.0950, credit_rating: "A", payment_priority: 4 }
  ],
  2: [
    { id: 5, name: "Senior A", class_name: "A", principal_amount: 1260000000, interest_rate: 0.0500, credit_rating: "AA+", payment_priority: 1 },
    { id: 6, name: "Subordinate B", class_name: "B", principal_amount: 360000000, interest_rate: 0.0720, credit_rating: "A", payment_priority: 2 },
    { id: 7, name: "Junior C", class_name: "C", principal_amount: 180000000, interest_rate: 0.1050, credit_rating: "BBB", payment_priority: 3 }
  ],
  3: [
    { id: 8, name: "Class A", class_name: "A", principal_amount: 960000000, interest_rate: 0.0375, credit_rating: "AAA", payment_priority: 1 },
    { id: 9, name: "Class B", class_name: "B", principal_amount: 180000000, interest_rate: 0.0480, credit_rating: "AA", payment_priority: 2 },
    { id: 10, name: "Class C", class_name: "C", principal_amount: 60000000, interest_rate: 0.0750, credit_rating: "A", payment_priority: 3 }
  ]
};

const mockSavedReports = [
  { id: 1, name: "Monthly AAA Deals Report", scope: "DEAL", created_date: "2024-01-15", deal_count: 5, tranche_count: 0 },
  { id: 2, name: "RMBS Tranche Analysis", scope: "TRANCHE", created_date: "2024-02-01", deal_count: 3, tranche_count: 12 },
  { id: 3, name: "High-Yield Securities", scope: "TRANCHE", created_date: "2024-02-15", deal_count: 2, tranche_count: 8 }
];

const NewReportingUX = () => {
  // State for the wizard steps
  const [currentStep, setCurrentStep] = useState(1);
  const [reportBuilderMode, setReportBuilderMode] = useState(false);
  
  // Report configuration state
  const [reportName, setReportName] = useState('');
  const [reportScope, setReportScope] = useState('');
  const [selectedDeals, setSelectedDeals] = useState([]);
  const [selectedTranches, setSelectedTranches] = useState({});
  
  // UI state
  const [deals, setDeals] = useState(mockDeals);
  const [tranches, setTranches] = useState({});
  const [savedReports, setSavedReports] = useState(mockSavedReports);
  const [selectedSavedReport, setSelectedSavedReport] = useState('');
  const [loading, setLoading] = useState(false);

  // Format currency
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      notation: 'compact',
      maximumFractionDigits: 1
    }).format(amount);
  };

  // Format percentage
  const formatPercent = (rate) => {
    return (rate * 100).toFixed(2) + '%';
  };

  // Load tranches for selected deals
  useEffect(() => {
    const loadTranches = async () => {
      const newTranches = {};
      for (const dealId of selectedDeals) {
        newTranches[dealId] = mockTranches[dealId] || [];
      }
      setTranches(newTranches);
    };
    
    if (selectedDeals.length > 0) {
      loadTranches();
    }
  }, [selectedDeals]);

  // Handle deal selection
  const handleDealToggle = (dealId) => {
    setSelectedDeals(prev => {
      if (prev.includes(dealId)) {
        // Remove deal and its tranches
        const newSelected = prev.filter(id => id !== dealId);
        setSelectedTranches(prevTranches => {
          const newTranches = { ...prevTranches };
          delete newTranches[dealId];
          return newTranches;
        });
        return newSelected;
      } else {
        return [...prev, dealId];
      }
    });
  };

  // Handle tranche selection
  const handleTrancheToggle = (dealId, trancheId) => {
    setSelectedTranches(prev => {
      const dealTranches = prev[dealId] || [];
      const newDealTranches = dealTranches.includes(trancheId)
        ? dealTranches.filter(id => id !== trancheId)
        : [...dealTranches, trancheId];
      
      return {
        ...prev,
        [dealId]: newDealTranches
      };
    });
  };

  // Handle select all tranches for a deal
  const handleSelectAllTranches = (dealId) => {
    const allTrancheIds = (tranches[dealId] || []).map(t => t.id);
    setSelectedTranches(prev => ({
      ...prev,
      [dealId]: allTrancheIds
    }));
  };

  // Wizard navigation
  const nextStep = () => {
    if (currentStep < 4) setCurrentStep(currentStep + 1);
  };

  const prevStep = () => {
    if (currentStep > 1) setCurrentStep(currentStep - 1);
  };

  // Save report configuration
  const saveReportConfig = async () => {
    setLoading(true);
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const newReport = {
      id: Date.now(),
      name: reportName,
      scope: reportScope,
      created_date: new Date().toISOString().split('T')[0],
      deal_count: selectedDeals.length,
      tranche_count: reportScope === 'TRANCHE' ? 
        Object.values(selectedTranches).flat().length : 0
    };
    
    setSavedReports(prev => [newReport, ...prev]);
    setReportBuilderMode(false);
    setCurrentStep(1);
    
    // Reset form
    setReportName('');
    setReportScope('');
    setSelectedDeals([]);
    setSelectedTranches({});
    
    setLoading(false);
    
    // Show success toast (you'd use your actual toast system)
    alert('Report configuration saved successfully!');
  };

  // Render wizard step content
  const renderWizardStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="row g-3">
            <div className="col-12">
              <h5 className="mb-3">Step 1: Report Configuration</h5>
            </div>
            <div className="col-md-6">
              <label htmlFor="reportName" className="form-label">Report Name</label>
              <input
                type="text"
                id="reportName"
                className="form-control"
                value={reportName}
                onChange={(e) => setReportName(e.target.value)}
                placeholder="Enter report name"
              />
            </div>
            <div className="col-md-6">
              <label htmlFor="reportScope" className="form-label">Report Scope</label>
              <select
                id="reportScope"
                className="form-select"
                value={reportScope}
                onChange={(e) => setReportScope(e.target.value)}
              >
                <option value="">Select scope...</option>
                <option value="DEAL">Deal Level (One row per deal)</option>
                <option value="TRANCHE">Tranche Level (Multiple rows per deal)</option>
              </select>
            </div>
            <div className="col-12">
              <div className="alert alert-info">
                <strong>Deal Level:</strong> Returns aggregated data with one row per deal.<br/>
                <strong>Tranche Level:</strong> Returns detailed data with one row per selected tranche.
              </div>
            </div>
          </div>
        );

      case 2:
        return (
          <div>
            <h5 className="mb-3">Step 2: Select Deals</h5>
            <div className="row">
              {deals.map(deal => (
                <div key={deal.id} className="col-md-6 mb-3">
                  <div className={`card h-100 ${selectedDeals.includes(deal.id) ? 'border-primary' : ''}`}>
                    <div className="card-body">
                      <div className="form-check mb-2">
                        <input
                          className="form-check-input"
                          type="checkbox"
                          id={`deal-${deal.id}`}
                          checked={selectedDeals.includes(deal.id)}
                          onChange={() => handleDealToggle(deal.id)}
                        />
                        <label className="form-check-label fw-bold" htmlFor={`deal-${deal.id}`}>
                          {deal.name}
                        </label>
                      </div>
                      <div className="small text-muted">
                        <div><strong>Originator:</strong> {deal.originator}</div>
                        <div><strong>Type:</strong> {deal.deal_type}</div>
                        <div><strong>Principal:</strong> {formatCurrency(deal.total_principal)}</div>
                        <div><strong>Rating:</strong> <span className="badge bg-success">{deal.credit_rating}</span></div>
                        <div><strong>Yield:</strong> {formatPercent(deal.yield_rate)}</div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="alert alert-warning">
              Selected {selectedDeals.length} deal{selectedDeals.length !== 1 ? 's' : ''}
            </div>
          </div>
        );

      case 3:
        if (reportScope !== 'TRANCHE') {
          return (
            <div>
              <h5 className="mb-3">Step 3: Deal-Level Configuration</h5>
              <div className="alert alert-success">
                <i className="bi bi-check-circle me-2"></i>
                Your deal-level report is configured! You've selected {selectedDeals.length} deal{selectedDeals.length !== 1 ? 's' : ''} 
                and will get one row per deal with aggregated data.
              </div>
              <div className="card">
                <div className="card-header">
                  <h6 className="mb-0">Selected Deals Summary</h6>
                </div>
                <div className="card-body">
                  {selectedDeals.map(dealId => {
                    const deal = deals.find(d => d.id === dealId);
                    return (
                      <div key={dealId} className="d-flex justify-content-between align-items-center py-2 border-bottom">
                        <div>
                          <strong>{deal.name}</strong>
                          <div className="small text-muted">{deal.deal_type} • {deal.originator}</div>
                        </div>
                        <div className="text-end">
                          <div>{formatCurrency(deal.total_principal)}</div>
                          <div className="small text-muted">{deal.credit_rating}</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          );
        }

        return (
          <div>
            <h5 className="mb-3">Step 3: Select Tranches</h5>
            {selectedDeals.map(dealId => {
              const deal = deals.find(d => d.id === dealId);
              const dealTranches = tranches[dealId] || [];
              const selectedDealTranches = selectedTranches[dealId] || [];
              
              return (
                <div key={dealId} className="card mb-3">
                  <div className="card-header d-flex justify-content-between align-items-center">
                    <h6 className="mb-0">{deal.name}</h6>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-primary"
                      onClick={() => handleSelectAllTranches(dealId)}
                    >
                      Select All ({dealTranches.length})
                    </button>
                  </div>
                  <div className="card-body">
                    <div className="row">
                      {dealTranches.map(tranche => (
                        <div key={tranche.id} className="col-md-6 mb-2">
                          <div className={`p-2 border rounded ${selectedDealTranches.includes(tranche.id) ? 'border-primary bg-light' : ''}`}>
                            <div className="form-check">
                              <input
                                className="form-check-input"
                                type="checkbox"
                                id={`tranche-${tranche.id}`}
                                checked={selectedDealTranches.includes(tranche.id)}
                                onChange={() => handleTrancheToggle(dealId, tranche.id)}
                              />
                              <label className="form-check-label" htmlFor={`tranche-${tranche.id}`}>
                                <strong>{tranche.name}</strong>
                              </label>
                            </div>
                            <div className="small text-muted mt-1">
                              <div>Principal: {formatCurrency(tranche.principal_amount)}</div>
                              <div>Rate: {formatPercent(tranche.interest_rate)} • Rating: {tranche.credit_rating}</div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })}
            <div className="alert alert-warning">
              Selected {Object.values(selectedTranches).flat().length} tranche{Object.values(selectedTranches).flat().length !== 1 ? 's' : ''} 
              across {selectedDeals.length} deal{selectedDeals.length !== 1 ? 's' : ''}
            </div>
          </div>
        );

      case 4:
        return (
          <div>
            <h5 className="mb-3">Step 4: Review & Save</h5>
            <div className="card">
              <div className="card-header">
                <h6 className="mb-0">Report Configuration Summary</h6>
              </div>
              <div className="card-body">
                <dl className="row">
                  <dt className="col-sm-3">Report Name:</dt>
                  <dd className="col-sm-9">{reportName}</dd>
                  
                  <dt className="col-sm-3">Report Scope:</dt>
                  <dd className="col-sm-9">
                    <span className={`badge ${reportScope === 'DEAL' ? 'bg-primary' : 'bg-info'}`}>
                      {reportScope} Level
                    </span>
                  </dd>
                  
                  <dt className="col-sm-3">Selected Deals:</dt>
                  <dd className="col-sm-9">{selectedDeals.length} deal{selectedDeals.length !== 1 ? 's' : ''}</dd>
                  
                  {reportScope === 'TRANCHE' && (
                    <>
                      <dt className="col-sm-3">Selected Tranches:</dt>
                      <dd className="col-sm-9">{Object.values(selectedTranches).flat().length} tranche{Object.values(selectedTranches).flat().length !== 1 ? 's' : ''}</dd>
                    </>
                  )}
                  
                  <dt className="col-sm-3">Expected Output:</dt>
                  <dd className="col-sm-9">
                    {reportScope === 'DEAL' 
                      ? `${selectedDeals.length} row${selectedDeals.length !== 1 ? 's' : ''} (one per deal)`
                      : `${Object.values(selectedTranches).flat().length} row${Object.values(selectedTranches).flat().length !== 1 ? 's' : ''} (one per tranche)`
                    }
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h3>Deal & Tranche Reporting</h3>
      </div>

      {/* Configure Reports Card - Enhanced */}
      <div className="card mb-4">
        <div className="card-header bg-success text-white d-flex justify-content-between align-items-center">
          <h5 className="card-title mb-0">Configure Reports</h5>
          {reportBuilderMode && (
            <button 
              type="button"
              className="btn btn-outline-light btn-sm"
              onClick={() => {
                setReportBuilderMode(false);
                setCurrentStep(1);
              }}
            >
              <i className="bi bi-x-lg"></i> Cancel
            </button>
          )}
        </div>
        <div className="card-body">
          {reportBuilderMode ? (
            <>
              {/* Progress indicator */}
              <div className="progress mb-4" style={{height: '8px'}}>
                <div 
                  className="progress-bar" 
                  role="progressbar" 
                  style={{width: `${(currentStep / 4) * 100}%`}}
                  aria-valuenow={currentStep} 
                  aria-valuemin="0" 
                  aria-valuemax="4"
                ></div>
              </div>
              
              {/* Step indicators */}
              <div className="d-flex justify-content-between mb-4">
                {[1, 2, 3, 4].map(step => (
                  <div key={step} className={`text-center ${currentStep >= step ? 'text-primary' : 'text-muted'}`}>
                    <div className={`rounded-circle d-inline-flex align-items-center justify-content-center ${
                      currentStep >= step ? 'bg-primary text-white' : 'bg-light'
                    }`} style={{width: '32px', height: '32px', fontSize: '14px'}}>
                      {currentStep > step ? <i className="bi bi-check"></i> : step}
                    </div>
                    <div className="small mt-1">
                      {step === 1 && 'Setup'}
                      {step === 2 && 'Deals'}
                      {step === 3 && (reportScope === 'TRANCHE' ? 'Tranches' : 'Review')}
                      {step === 4 && 'Save'}
                    </div>
                  </div>
                ))}
              </div>

              {/* Step content */}
              {renderWizardStep()}

              {/* Navigation buttons */}
              <div className="d-flex justify-content-between mt-4">
                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  onClick={prevStep}
                  disabled={currentStep === 1}
                >
                  <i className="bi bi-arrow-left"></i> Previous
                </button>
                
                <div>
                  {currentStep < 4 ? (
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={nextStep}
                      disabled={
                        (currentStep === 1 && (!reportName || !reportScope)) ||
                        (currentStep === 2 && selectedDeals.length === 0) ||
                        (currentStep === 3 && reportScope === 'TRANCHE' && Object.values(selectedTranches).flat().length === 0)
                      }
                    >
                      Next <i className="bi bi-arrow-right"></i>
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-success"
                      onClick={saveReportConfig}
                      disabled={loading}
                    >
                      {loading ? (
                        <>
                          <span className="spinner-border spinner-border-sm me-2"></span>
                          Saving...
                        </>
                      ) : (
                        <>
                          <i className="bi bi-save"></i> Save Report Configuration
                        </>
                      )}
                    </button>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="row g-3">
              <div className="col-md-8">
                <label htmlFor="existingReportSelect" className="form-label">Saved Report Configurations</label>
                <select
                  id="existingReportSelect"
                  className="form-select"
                  value={selectedSavedReport}
                  onChange={(e) => setSelectedSavedReport(e.target.value)}
                >
                  <option value="">Select a saved report...</option>
                  {savedReports.map(report => (
                    <option key={report.id} value={report.id}>
                      {report.name} ({report.scope} Level • {report.deal_count} deals
                      {report.scope === 'TRANCHE' && ` • ${report.tranche_count} tranches`})
                    </option>
                  ))}
                </select>
              </div>
              <div className="col-md-4 d-flex align-items-end gap-2">
                <button
                  type="button"
                  className="btn btn-success"
                  onClick={() => setReportBuilderMode(true)}
                >
                  <i className="bi bi-plus-lg"></i> Create New Report
                </button>
                <button
                  type="button"
                  className="btn btn-outline-primary"
                  disabled={!selectedSavedReport}
                >
                  <i className="bi bi-pencil"></i> Edit
                </button>
                <button
                  type="button"
                  className="btn btn-outline-danger"
                  disabled={!selectedSavedReport}
                >
                  <i className="bi bi-trash"></i> Delete
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Run Reports Card */}
      <div className="card mb-4">
        <div className="card-header bg-primary text-white">
          <h5 className="card-title mb-0">Run Reports</h5>
        </div>
        <div className="card-body">
          <div className="row g-3">
            <div className="col-md-6">
              <label htmlFor="reportSelect" className="form-label">Select Report</label>
              <select
                id="reportSelect"
                className="form-select"
                value={selectedSavedReport}
                onChange={(e) => setSelectedSavedReport(e.target.value)}
              >
                <option value="" disabled>Choose a report...</option>
                {savedReports.map(report => (
                  <option key={report.id} value={report.id}>
                    {report.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="col-md-6">
              <label htmlFor="cycleCode" className="form-label">Cycle Code</label>
              <select id="cycleCode" className="form-select">
                <option value="">Select cycle...</option>
                <option value="2024-01">2024-01 (January 2024)</option>
                <option value="2024-02">2024-02 (February 2024)</option>
                <option value="2024-03">2024-03 (March 2024)</option>
              </select>
            </div>
            
            <div className="col-12 mt-3 d-flex gap-2">
              <button
                type="button"
                className="btn"
                style={{ backgroundColor: '#93186C', color: 'white' }}
                disabled={!selectedSavedReport}
              >
                <i className="bi bi-play-fill"></i> Run Report
              </button>
              
              <button
                type="button"
                className="btn btn-outline-secondary"
                disabled={true}
                title="Coming soon: Schedule reports to run automatically"
              >
                <i className="bi bi-calendar-event"></i> Schedule Report
                <span className="badge bg-info ms-2" style={{ fontSize: '0.7rem' }}>Coming Soon</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Sample Results Preview */}
      <div className="card">
        <div className="card-header text-white d-flex justify-content-between align-items-center" 
             style={{ backgroundColor: '#93186C' }}>
          <h5 className="card-title mb-0">Sample Report Results Preview</h5>
          <div className="btn-group">
            <button className="btn btn-sm btn-light">
              <i className="bi bi-file-earmark-text"></i> Export CSV
            </button>
            <button className="btn btn-sm btn-light ms-2">
              <i className="bi bi-file-earmark-excel"></i> Export XLSX
            </button>
          </div>
        </div>
        <div className="card-body">
          <div className="table-responsive">
            <table className="table table-striped">
              <thead>
                <tr>
                  <th>Deal Name</th>
                  <th>Originator</th>
                  <th>Principal Amount</th>
                  <th>Credit Rating</th>
                  <th>Yield Rate</th>
                  <th>Deal Type</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>GSAMP Trust 2024-1</td>
                  <td>Goldman Sachs</td>
                  <td>$2.5B</td>
                  <td><span className="badge bg-success">AAA</span></td>
                  <td>4.85%</td>
                  <td>RMBS</td>
                </tr>
                <tr>
                  <td>Wells Fargo Commercial 2024-A</td>
                  <td>Wells Fargo</td>
                  <td>$1.8B</td>
                  <td><span className="badge bg-success">AA+</span></td>
                  <td>5.20%</td>
                  <td>CMBS</td>
                </tr>
                <tr>
                  <td>Chase Auto Receivables 2024-1</td>
                  <td>JPMorgan Chase</td>
                  <td>$1.2B</td>
                  <td><span className="badge bg-success">AAA</span></td>
                  <td>3.95%</td>
                  <td>Auto ABS</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className="mt-2">
            <small className="text-muted">
              Showing 3 of 3 rows • This is sample data demonstrating the new report structure
            </small>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NewReportingUX;