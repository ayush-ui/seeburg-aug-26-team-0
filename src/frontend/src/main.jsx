import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

// Roboto is vendored, not fetched from a CDN, so the demo works offline.
import '@fontsource/roboto/300.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto-mono/400.css';

import './styles/tokens.css';
import './styles/base.css';
import './styles/app.css';

import App from './App.jsx';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
