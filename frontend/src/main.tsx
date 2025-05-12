import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.tsx'
import './index.css'
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap-icons/font/bootstrap-icons.css'

// Import Bootstrap JS
import * as bootstrap from 'bootstrap'

// Make bootstrap available globally for modal functionality
window.bootstrap = bootstrap;

// Add responsive viewport meta tag programmatically if not in HTML
const setViewportMeta = () => {
  if (!document.querySelector('meta[name="viewport"]')) {
    const meta = document.createElement('meta');
    meta.name = 'viewport';
    meta.content = 'width=device-width, initial-scale=1.0, shrink-to-fit=no';
    document.getElementsByTagName('head')[0].appendChild(meta);
  }
};

setViewportMeta();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
