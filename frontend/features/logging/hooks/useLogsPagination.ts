// frontend/features/logging/hooks/useLogsPagination.ts
import { useState, useEffect, useMemo } from 'react';

interface UseLogsPaginationProps {
  totalCount: number;
  limit: number;
  currentOffset: number;
  onOffsetChange: (offset: number) => void;
}

export const useLogsPagination = ({ 
  totalCount, 
  limit, 
  currentOffset, 
  onOffsetChange 
}: UseLogsPaginationProps) => {
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Calculate total pages
  const totalPages = Math.ceil(totalCount / limit);

  // Update current page when offset changes
  useEffect(() => {
    const page = Math.floor(currentOffset / limit) + 1;
    setCurrentPage(page);
  }, [currentOffset, limit]);

  // Handle page change
  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      const newOffset = (page - 1) * limit;
      onOffsetChange(newOffset);
    }
  };

  // Generate pagination items for rendering
  const paginationItems = useMemo(() => {
    const items = [];
    const maxVisiblePages = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
    
    // Adjust if we're near the end
    if (endPage - startPage + 1 < maxVisiblePages) {
      startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }
    
    // First ellipsis
    if (startPage > 1) {
      items.push({
        type: 'ellipsis',
        key: 'start-ellipsis',
        disabled: true,
        label: '...'
      });
    }
    
    // Page numbers
    for (let i = startPage; i <= endPage; i++) {
      items.push({
        type: 'page',
        key: i,
        page: i,
        active: currentPage === i,
        disabled: currentPage === i,
        label: i.toString()
      });
    }
    
    // Last ellipsis
    if (endPage < totalPages) {
      items.push({
        type: 'ellipsis',
        key: 'end-ellipsis',
        disabled: true,
        label: '...'
      });
    }
    
    return items;
  }, [currentPage, totalPages]);

  // Navigation functions
  const goToFirstPage = () => handlePageChange(1);
  const goToPreviousPage = () => handlePageChange(currentPage - 1);
  const goToNextPage = () => handlePageChange(currentPage + 1);
  const goToLastPage = () => handlePageChange(totalPages);

  // Pagination info
  const getPaginationInfo = () => {
    if (totalCount === 0) return 'No logs available';
    
    const start = currentOffset + 1;
    const end = Math.min(currentOffset + limit, totalCount);
    
    return `Showing ${start} to ${end} of ${totalCount} logs`;
  };

  return {
    // State
    currentPage,
    totalPages,
    paginationItems,
    
    // Actions
    handlePageChange,
    goToFirstPage,
    goToPreviousPage,
    goToNextPage,
    goToLastPage,
    
    // Helpers
    getPaginationInfo
  };
};