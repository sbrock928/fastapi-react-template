import { useEffect, useState } from 'react';
import axios from 'axios';

interface Note {
  id: number;
  title: string;
  content: string;
  category: string;
  created_at: string;
  updated_at: string | null;
}

type DocType = 'swagger' | 'redoc';

const Documentation = () => {
  const [showApiFrame, setShowApiFrame] = useState(false);
  const [showUserGuide, setShowUserGuide] = useState(false);
  const [notes, setNotes] = useState<Note[]>([]);
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(false);
  const [docType, setDocType] = useState<DocType>('swagger');
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    category: 'general'
  });
  
  // Load notes when user guide is shown
  useEffect(() => {
    if (showUserGuide) {
      loadNotes();
    }
  }, [showUserGuide]);

  const loadNotes = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/user-guide/notes');
      setNotes(response.data);
    } catch (error) {
      console.error('Error loading notes:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApiDocsClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    setShowApiFrame(true);
    setShowUserGuide(false);
  };

  const handleUserGuideClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    setShowUserGuide(true);
    setShowApiFrame(false);
  };

  const handleDocTypeChange = (type: DocType) => {
    setDocType(type);
  };

  const getDocumentationUrl = () => {
    return docType === 'swagger' ? '/api/docs' : '/api/redoc';
  };

  const handleNoteClick = (note: Note) => {
    setSelectedNote(note);
    setEditing(false);
  };

  const handleAddNew = () => {
    setFormData({
      title: '',
      content: '',
      category: 'general'
    });
    setSelectedNote(null);
    setEditing(true);
  };

  const handleEditNote = () => {
    if (selectedNote) {
      setFormData({
        title: selectedNote.title,
        content: selectedNote.content,
        category: selectedNote.category
      });
      setEditing(true);
    }
  };

  const handleDeleteNote = async () => {
    if (!selectedNote || !window.confirm('Are you sure you want to delete this note?')) {
      return;
    }

    try {
      setLoading(true);
      await axios.delete(`/api/user-guide/notes/${selectedNote.id}`);
      await loadNotes();
      setSelectedNote(null);
    } catch (error) {
      console.error('Error deleting note:', error);
      alert('Failed to delete note.');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      setLoading(true);
      
      if (selectedNote) {
        // Update existing note
        await axios.put(`/api/user-guide/notes/${selectedNote.id}`, formData);
      } else {
        // Create new note
        await axios.post('/api/user-guide/notes', formData);
      }
      
      await loadNotes();
      setEditing(false);
      setSelectedNote(null);
    } catch (error) {
      console.error('Error saving note:', error);
      alert('Failed to save note.');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setEditing(false);
    setFormData({
      title: '',
      content: '',
      category: 'general'
    });
  };

  const renderUserGuide = () => {
    if (loading) {
      return (
        <div className="text-center py-4">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
        </div>
      );
    }

    return (
      <div className="row">
        <div className="col-md-4">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h5>User Guide Notes</h5>
            <button className="btn btn-sm btn-primary" onClick={handleAddNew}>
              <i className="bi bi-plus-circle"></i> Add Note
            </button>
          </div>
          <div className="list-group">
            {notes.length === 0 ? (
              <div className="text-center py-3 text-muted">
                <p>No notes available.</p>
                <p>Click "Add Note" to create your first note.</p>
              </div>
            ) : (
              notes.map(note => (
                <button
                  key={note.id}
                  className={`list-group-item list-group-item-action ${selectedNote?.id === note.id ? 'active' : ''}`}
                  onClick={() => handleNoteClick(note)}
                >
                  <div className="d-flex w-100 justify-content-between">
                    <h6 className="mb-1">{note.title}</h6>
                    <small className="text-muted">{note.category}</small>
                  </div>
                  <small>{new Date(note.updated_at || note.created_at).toLocaleDateString()}</small>
                </button>
              ))
            )}
          </div>
        </div>
        <div className="col-md-8">
          {editing ? (
            <div className="card">
              <div className="card-header">
                <h5>{selectedNote ? 'Edit Note' : 'Add New Note'}</h5>
              </div>
              <div className="card-body">
                <form onSubmit={handleSubmit}>
                  <div className="mb-3">
                    <label htmlFor="title" className="form-label">Title</label>
                    <input
                      type="text"
                      className="form-control"
                      id="title"
                      name="title"
                      value={formData.title}
                      onChange={handleInputChange}
                      required
                    />
                  </div>
                  <div className="mb-3">
                    <label htmlFor="category" className="form-label">Category</label>
                    <select
                      className="form-select"
                      id="category"
                      name="category"
                      value={formData.category}
                      onChange={handleInputChange}
                    >
                      <option value="general">General</option>
                      <option value="resources">Resources</option>
                      <option value="reporting">Reporting</option>
                      <option value="logs">Logs</option>
                      <option value="api">API</option>
                    </select>
                  </div>
                  <div className="mb-3">
                    <label htmlFor="content" className="form-label">Content</label>
                    <textarea
                      className="form-control"
                      id="content"
                      name="content"
                      rows={10}
                      value={formData.content}
                      onChange={handleInputChange}
                      required
                    ></textarea>
                    <small className="text-muted">Supports markdown formatting</small>
                  </div>
                  <div className="d-flex gap-2">
                    <button type="submit" className="btn btn-primary">Save</button>
                    <button type="button" className="btn btn-secondary" onClick={handleCancel}>Cancel</button>
                  </div>
                </form>
              </div>
            </div>
          ) : selectedNote ? (
            <div className="card">
              <div className="card-header d-flex justify-content-between align-items-center">
                <h5>{selectedNote.title}</h5>
                <div>
                  <button className="btn btn-sm btn-outline-primary me-2" onClick={handleEditNote}>
                    <i className="bi bi-pencil"></i> Edit
                  </button>
                  <button className="btn btn-sm btn-outline-danger" onClick={handleDeleteNote}>
                    <i className="bi bi-trash"></i> Delete
                  </button>
                </div>
              </div>
              <div className="card-body">
                <div className="mb-2">
                  <span className="badge bg-secondary">{selectedNote.category}</span>
                  <small className="text-muted ms-2">
                    {selectedNote.updated_at 
                      ? `Updated: ${new Date(selectedNote.updated_at).toLocaleString()}` 
                      : `Created: ${new Date(selectedNote.created_at).toLocaleString()}`}
                  </small>
                </div>
                <div className="content-area">
                  {selectedNote.content.split('\n').map((paragraph, i) => (
                    <p key={i}>{paragraph}</p>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-5">
              <p>Select a note from the list or create a new one.</p>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div style={{ width: '100%', maxWidth: '100%', overflow: 'hidden' }}>
      <h3>Documentation</h3>
      <p>Reference documentation for the Vibes + Hype system.</p>

      {showApiFrame ? (
        <div className="card mt-4 mb-4" style={{ width: '100%' }}>
          <div className="card-header bg-primary text-white d-flex justify-content-between align-items-center">
            <div className="d-flex align-items-center">
              <h5 className="mb-0">API Documentation</h5>
              <div className="btn-group ms-3">
                <button
                  type="button"
                  className={`btn btn-sm ${docType === 'swagger' ? 'btn-light' : 'btn-outline-light'}`}
                  onClick={() => handleDocTypeChange('swagger')}
                >
                  Swagger
                </button>
                <button
                  type="button"
                  className={`btn btn-sm ${docType === 'redoc' ? 'btn-light' : 'btn-outline-light'}`}
                  onClick={() => handleDocTypeChange('redoc')}
                >
                  ReDoc
                </button>
              </div>
            </div>
            <button 
              className="btn btn-sm btn-outline-light" 
              onClick={() => setShowApiFrame(false)}
              title="Back to Documentation"
            >
              <i className="bi bi-x-lg"></i> Close
            </button>
          </div>
          <div className="card-body p-0">
            <iframe 
              src={getDocumentationUrl()} 
              style={{ 
                width: '100%', 
                height: '800px', 
                border: 'none',
                display: 'block'
              }}
              title="API Documentation"
            />
          </div>
        </div>
      ) : showUserGuide ? (
        <div className="card mt-4 mb-4">
          <div className="card-header bg-primary text-white d-flex justify-content-between align-items-center">
            <div className="d-flex align-items-center">
              <h5 className="mb-0">User Guide</h5>
            </div>
            <button 
              className="btn btn-sm btn-outline-light" 
              onClick={() => setShowUserGuide(false)}
            >
              <i className="bi bi-x-lg"></i> Close
            </button>
          </div>
          <div className="card-body">
            {renderUserGuide()}
          </div>
        </div>
      ) : (
        <div className="row mt-4">
          <div className="col-md-4 mb-4">
            <div className="card">
              <div className="card-header bg-primary text-white">
                <h5 className="card-title mb-0">User Guide</h5>
              </div>
              <div className="card-body">
                <p className="card-text">Learn how to use the Vibes + Hype application effectively.</p>
                <a href="#" className="btn" style={{ backgroundColor: '#93186C', color: 'white' }} onClick={handleUserGuideClick}>View User Guide</a>
              </div>
            </div>
          </div>

          <div className="col-md-4 mb-4">
            <div className="card">
              <div className="card-header bg-primary text-white">
                <h5 className="card-title mb-0">API Reference</h5>
              </div>
              <div className="card-body">
                <p className="card-text">Technical reference for the Vibes + Hype API endpoints.</p>
                <a href="#" className="btn" style={{ backgroundColor: '#93186C', color: 'white' }} onClick={handleApiDocsClick}>View API Docs</a>
              </div>
            </div>
          </div>

          <div className="col-md-4 mb-4">
            <div className="card">
              <div className="card-header bg-primary text-white">
                <h5 className="card-title mb-0">Release Notes</h5>
              </div>
              <div className="card-body">
                <p className="card-text">Details about new features and bug fixes in each version.</p>
                <button 
                  className="btn" 
                  style={{ backgroundColor: '#93186C', color: 'white' }}
                  disabled 
                  title="Coming soon"
                >
                  View Release Notes
                  <small className="ms-2 badge bg-secondary">Coming Soon</small>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {!showApiFrame && !showUserGuide && (
        <div className="card mt-4">
          <div className="card-header bg-primary text-white">
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
      )}
    </div>
  )
}

export default Documentation
