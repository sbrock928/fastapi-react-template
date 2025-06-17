import React from 'react';

interface WizardNavigationProps {
  currentStep: number;
  totalSteps: number;
  canProceed: boolean;
  isLoading: boolean;
  isEditMode: boolean;
  onPreviousStep: () => void;
  onNextStep: () => void;
  onSave: () => void;
  title: string;
}

const WizardNavigation: React.FC<WizardNavigationProps> = ({
  currentStep,
  totalSteps,
  canProceed,
  isLoading,
  isEditMode,
  onPreviousStep,
  onNextStep,
  onSave,
  title
}) => {
  const progress = (currentStep / totalSteps) * 100;
  const isFirstStep = currentStep === 1;
  const isLastStep = currentStep === totalSteps;

  return (
    <>
      {/* Progress Bar */}
      <div className="mb-4">
        <div className="d-flex justify-content-between align-items-center mb-2">
          <h4>{title}</h4>
          <span className="badge bg-primary">
            Step {currentStep} of {totalSteps}
          </span>
        </div>
        <div className="progress">
          <div
            className="progress-bar"
            role="progressbar"
            style={{ width: `${progress}%` }}
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
          ></div>
        </div>
      </div>

      {/* Navigation Buttons */}
      <div className="d-flex justify-content-between mt-4">
        <button
          type="button"
          className="btn btn-outline-secondary"
          onClick={onPreviousStep}
          disabled={isFirstStep}
        >
          <i className="bi bi-arrow-left me-2"></i>
          Previous
        </button>

        <div>
          {!isLastStep ? (
            <button
              type="button"
              className="btn btn-primary"
              onClick={onNextStep}
              disabled={!canProceed}
            >
              Next
              <i className="bi bi-arrow-right ms-2"></i>
            </button>
          ) : (
            <button
              type="button"
              className="btn btn-success"
              onClick={onSave}
              disabled={isLoading || !canProceed}
            >
              {isLoading ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" role="status"></span>
                  {isEditMode ? 'Updating...' : 'Saving...'}
                </>
              ) : (
                <>
                  <i className="bi bi-check-circle me-2"></i>
                  {isEditMode ? 'Update Report' : 'Save Report'}
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </>
  );
};

export default WizardNavigation;