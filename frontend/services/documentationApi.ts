import apiClient from './apiClient';
import type { Note } from '@/types';

// Documentation API service
const documentationApi = {
  getNotes: () => apiClient.get('/user-guide/notes'),
  getNoteById: (id: number) => apiClient.get(`/user-guide/notes/${id}`),
  createNote: (note: Omit<Note, 'id' | 'created_at' | 'updated_at'>) => 
    apiClient.post('/user-guide/notes', note),
  updateNote: (id: number, note: Omit<Note, 'id' | 'created_at' | 'updated_at'>) => 
    apiClient.put(`/user-guide/notes/${id}`, note),
  deleteNote: (id: number) => apiClient.delete(`/user-guide/notes/${id}`),
};

export default documentationApi;