import { useState, useCallback } from 'react';
import { updateUrlParam } from '@/utils/urlParams';

interface PaginationProps {
  initialPage?: number;
  itemsPerPage?: number;
  updateUrl?: boolean;
}

interface PaginationResult<T> {
  currentPage: number;
  totalPages: number;
  pageItems: T[];
  goToPage: (page: number) => void;
  goToFirstPage: () => void;
  goToPreviousPage: () => void;
  goToNextPage: () => void;
  goToLastPage: () => void;
  setItemsPerPage: (count: number) => void;
  itemsPerPage: number;
  startIndex: number;
  endIndex: number;
}

export default function usePagination<T>({
  initialPage = 1,
  itemsPerPage: initialItemsPerPage = 10,
  updateUrl = false,
}: PaginationProps): (items: T[]) => PaginationResult<T> {
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [itemsPerPage, setItemsPerPage] = useState(initialItemsPerPage);

  // Calculate total pages
  const getTotalPages = useCallback(
    (items: T[]) => Math.ceil(items.length / itemsPerPage),
    [itemsPerPage]
  );

  // Update URL if needed
  const updatePageUrl = useCallback(
    (page: number) => {
      if (updateUrl) {
        updateUrlParam('page', page.toString());
      }
    },
    [updateUrl]
  );

  // Page navigation functions
  const goToPage = useCallback(
    (page: number, items: T[]) => {
      const totalPages = getTotalPages(items);
      if (page < 1 || page > totalPages || page === currentPage) {
        return;
      }
      setCurrentPage(page);
      updatePageUrl(page);
    },
    [currentPage, getTotalPages, updatePageUrl]
  );

  const goToFirstPage = useCallback(
    () => {
      if (currentPage !== 1) {
        setCurrentPage(1);
        updatePageUrl(1);
      }
    },
    [currentPage, updatePageUrl]
  );

  const goToPreviousPage = useCallback(
    () => {
      if (currentPage > 1) {
        const newPage = currentPage - 1;
        setCurrentPage(newPage);
        updatePageUrl(newPage);
      }
    },
    [currentPage, updatePageUrl]
  );

  const goToNextPage = useCallback(
    (items: T[]) => {
      const totalPages = getTotalPages(items);
      if (currentPage < totalPages) {
        const newPage = currentPage + 1;
        setCurrentPage(newPage);
        updatePageUrl(newPage);
      }
    },
    [currentPage, getTotalPages, updatePageUrl]
  );

  const goToLastPage = useCallback(
    (items: T[]) => {
      const totalPages = getTotalPages(items);
      if (currentPage !== totalPages) {
        setCurrentPage(totalPages);
        updatePageUrl(totalPages);
      }
    },
    [currentPage, getTotalPages, updatePageUrl]
  );

  // Return the pagination object
  return useCallback(
    (items: T[]) => {
      const totalPages = getTotalPages(items);
      
      // Ensure current page is valid
      const validCurrentPage = Math.max(1, Math.min(currentPage, totalPages || 1));
      if (validCurrentPage !== currentPage) {
        setCurrentPage(validCurrentPage);
      }
      
      // Calculate start and end indices
      const startIndex = (validCurrentPage - 1) * itemsPerPage;
      const endIndex = Math.min(startIndex + itemsPerPage, items.length);
      
      return {
        currentPage: validCurrentPage,
        totalPages,
        pageItems: items.slice(startIndex, endIndex),
        goToPage: (page: number) => goToPage(page, items),
        goToFirstPage: () => goToFirstPage(),
        goToPreviousPage: () => goToPreviousPage(),
        goToNextPage: () => goToNextPage(items),
        goToLastPage: () => goToLastPage(items),
        setItemsPerPage,
        itemsPerPage,
        startIndex,
        endIndex,
      };
    },
    [
      currentPage,
      itemsPerPage,
      getTotalPages,
      goToPage,
      goToFirstPage,
      goToPreviousPage,
      goToNextPage,
      goToLastPage,
    ]
  );
}
