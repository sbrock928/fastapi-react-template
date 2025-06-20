import { useState } from 'react';

interface UseWizardNavigationProps {
  onValidationError: (message: string) => void;
  validateStep: (step: number) => { isValid: boolean; errors: Array<{ message: string }> };
}

export const useWizardNavigation = ({ 
  onValidationError,
  validateStep 
}: UseWizardNavigationProps) => {
  const [currentStep, setCurrentStep] = useState<number>(1);

  // Calculate total steps - reduced from 5 to 4 steps after combining deal and tranche selection
  const getTotalSteps = () => {
    return 4;
  };

  // Calculate display step - no adjustments needed since no steps are skipped
  const getDisplayStep = () => {
    return currentStep;
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
    
    // No longer skip step 3 for DEAL scope reports - tranches are now required for both
    
    if (nextStepNum <= 4) setCurrentStep(nextStepNum);
  };

  // Navigate to previous step
  const prevStep = () => {
    let prevStepNum = currentStep - 1;
    
    // No longer skip step 3 for DEAL scope reports - tranches are now required for both
    
    if (prevStepNum >= 1) setCurrentStep(prevStepNum);
  };

  // Reset to first step
  const resetToFirstStep = () => {
    setCurrentStep(1);
  };

  // Jump to specific step (with validation)
  const goToStep = (step: number) => {
    if (step >= 1 && step <= 4) {
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