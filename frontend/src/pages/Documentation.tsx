import { useEffect } from 'react';

const Documentation = () => {
  // Initialize Bootstrap collapse functionality after component mounts
  useEffect(() => {
    // Bootstrap functionality will be initialized automatically
    // because we're including the Bootstrap bundle JS in our main.tsx
  }, []);

  return (
    <div>
      <h1>Documentation</h1>
      <p>Reference documentation for the Vibes + Hype system.</p>

      <div className="row mt-4">
        <div className="col-md-4 mb-4">
          <div className="card">
            <div className="card-header">
              <h5 className="card-title mb-0">User Guide</h5>
            </div>
            <div className="card-body">
              <p className="card-text">Learn how to use the Vibes + Hype application effectively.</p>
              <a href="#" className="btn btn-primary">View User Guide</a>
            </div>
          </div>
        </div>

        <div className="col-md-4 mb-4">
          <div className="card">
            <div className="card-header">
              <h5 className="card-title mb-0">API Reference</h5>
            </div>
            <div className="card-body">
              <p className="card-text">Technical reference for the Vibes + Hype API endpoints.</p>
              <a href="#" className="btn btn-primary">View API Docs</a>
            </div>
          </div>
        </div>

        <div className="col-md-4 mb-4">
          <div className="card">
            <div className="card-header">
              <h5 className="card-title mb-0">Release Notes</h5>
            </div>
            <div className="card-body">
              <p className="card-text">Details about new features and bug fixes in each version.</p>
              <a href="#" className="btn btn-primary">View Release Notes</a>
            </div>
          </div>
        </div>
      </div>

      <div className="card mt-4">
        <div className="card-header">
          <h5 className="mb-0">Frequently Asked Questions</h5>
        </div>
        <div className="card-body">
          <div className="accordion" id="faqAccordion">
            <div className="accordion-item">
              <h2 className="accordion-header" id="headingOne">
                <button className="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#collapseOne" aria-expanded="true" aria-controls="collapseOne">
                  How do I add a new user?
                </button>
              </h2>
              <div id="collapseOne" className="accordion-collapse collapse show" aria-labelledby="headingOne" data-bs-parent="#faqAccordion">
                <div className="accordion-body">
                  To add a new user, navigate to the <strong>Resources</strong> tab, ensure you are on the "Users" section, then click the "Add User" button in the top right corner. Fill out the required information in the form and submit.
                </div>
              </div>
            </div>
            
            <div className="accordion-item">
              <h2 className="accordion-header" id="headingTwo">
                <button className="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseTwo" aria-expanded="false" aria-controls="collapseTwo">
                  How can I export reports?
                </button>
              </h2>
              <div id="collapseTwo" className="accordion-collapse collapse" aria-labelledby="headingTwo" data-bs-parent="#faqAccordion">
                <div className="accordion-body">
                  From the <strong>Reporting</strong> page, select the report you want to export. After generating the report, click the "Export CSV" button in the top right corner of the report card.
                </div>
              </div>
            </div>
            
            <div className="accordion-item">
              <h2 className="accordion-header" id="headingThree">
                <button className="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseThree" aria-expanded="false" aria-controls="collapseThree">
                  Where can I view system logs?
                </button>
              </h2>
              <div id="collapseThree" className="accordion-collapse collapse" aria-labelledby="headingThree" data-bs-parent="#faqAccordion">
                <div className="accordion-body">
                  System logs can be accessed from the <strong>Logs</strong> page. You can filter logs by time range and search for specific information. Detailed information about each request is available by clicking the "Details" button.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Documentation
