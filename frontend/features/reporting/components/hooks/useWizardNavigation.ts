import { useState } from 'react';

interface UseWizardNavigationProps {
  reportScope: 'DEAL' | 'TRANCHE' | '';
  onValidationError: (message: string) => void;
  validateStep: (step: number) => { isValid: boolean; errors: Array<{ message: string }> };
}

export const useWizardNavigation = ({ 
  reportScope, 
  onValidationError,
  validateStep 
}: UseWizardNavigationProps) => {
  const [currentStep, setCurrentStep] = useState<number>(1);

  // Calculate total steps based on report scope
  const getTotalSteps = () => {
    return reportScope === 'DEAL' ? 4 : 5;
  };

  // Calculate display step (adjust for skipped steps)
  const getDisplayStep = () => {
    return reportScope === 'DEAL' && currentStep > 3 ? currentStep - 1 : currentStep;
  };

  // Navigate to next step with validation
  const nextStep = () => {
    // Validate current step before proceeding
    const validation = validateStep(currentStep);
    if (!validation.isValid) {
      // Show validation errors to user
      validation.errors.forEach((error: any) => {
        onValidationError(error.message);
      });
      return;
    }

    let nextStepNum = currentStep + 1;
    
    // Skip step 3 (tranche selection) for DEAL scope reports
    if (currentStep === 2 && reportScope === 'DEAL') {
      nextStepNum = 4; // Jump to field selection
    }
    
    if (nextStepNum <= 5) setCurrentStep(nextStepNum);
  };

  // Navigate to previous step
  const prevStep = () => {
    let prevStepNum = currentStep - 1;
    
    // Skip step 3 (tranche selection) for DEAL scope reports when going backwards
    if (currentStep === 4 && reportScope === 'DEAL') {
      prevStepNum = 2; // Jump back to deal selection
    }
    
    if (prevStepNum >= 1) setCurrentStep(prevStepNum);
  };

  // Reset to first step
  const resetToFirstStep = () => {
    setCurrentStep(1);
  };

  // Jump to specific step (with validation)
  const goToStep = (step: number) => {
    if (step >= 1 && step <= 5) {
      setCurrentStep(step);
    }
  };

  return {
    currentStep,
    totalSteps: getTotalSteps(),
    displayStep: getDisplayStep(),
    nextStep,
    prevStep,
    resetToFirstStep,
    goToStep,
    isFirstStep: currentStep === 1,
    isLastStep: currentStep === getTotalSteps()
  };
};