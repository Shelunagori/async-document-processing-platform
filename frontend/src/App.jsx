import { useEffect, useMemo, useState } from 'react';
import {
  downloadProcessedResult,
  getTask,
  listDocuments,
  login,
  register,
  searchDocuments,
  uploadBatch,
  uploadDocument,
} from './api';

const INITIAL_AUTH = { username: '', email: '', password: '' };

export default function App() {
  const [authForm, setAuthForm] = useState(INITIAL_AUTH);
  const [token, setToken] = useState(() => localStorage.getItem('access_token') || '');
  const [documents, setDocuments] = useState([]);
  const [taskId, setTaskId] = useState('');
  const [taskResult, setTaskResult] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [batchSummary, setBatchSummary] = useState(null);
  const [message, setMessage] = useState('');

  const isAuthenticated = useMemo(() => Boolean(token), [token]);

  useEffect(() => {
    if (!token) {
      return;
    }
    refreshDocuments();
  }, [token]);

  async function refreshDocuments() {
    try {
      const data = await listDocuments(token);
      setDocuments(data);
    } catch (error) {
      setMessage(`Unable to load documents: ${error.message}`);
    }
  }

  async function onRegister(event) {
    event.preventDefault();
    try {
      await register({
        username: authForm.username,
        email: authForm.email,
        password: authForm.password,
      });
      setMessage('Registration completed. You can now log in.');
    } catch (error) {
      setMessage(`Registration failed: ${error.message}`);
    }
  }

  async function onLogin(event) {
    event.preventDefault();
    try {
      const data = await login({
        username: authForm.username,
        password: authForm.password,
      });
      setToken(data.access);
      localStorage.setItem('access_token', data.access);
      setMessage('Logged in successfully.');
    } catch (error) {
      setMessage(`Login failed: ${error.message}`);
    }
  }

  function onLogout() {
    setToken('');
    localStorage.removeItem('access_token');
    setDocuments([]);
    setTaskResult(null);
    setSearchResults([]);
    setMessage('Logged out.');
  }

  async function onUpload(event) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    try {
      const data = await uploadDocument(token, file);
      setTaskId(data.processing_task?.id || '');
      setMessage(`Uploaded ${data.original_filename}.`);
      await refreshDocuments();
    } catch (error) {
      setMessage(`Upload failed: ${error.message}`);
    } finally {
      event.target.value = '';
    }
  }

  async function onBatchUpload(event) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    try {
      const data = await uploadBatch(token, file);
      setBatchSummary(data);
      setMessage(
        `Batch upload complete. Accepted ${data.accepted_count}, rejected ${data.rejected_count}.`
      );
      await refreshDocuments();
    } catch (error) {
      setMessage(`Batch upload failed: ${error.message}`);
    } finally {
      event.target.value = '';
    }
  }

  async function onDownloadResult(documentId) {
    try {
      const { blob, filename } = await downloadProcessedResult(token, documentId);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
      setMessage('Processed result downloaded.');
    } catch (error) {
      setMessage(`Download failed: ${error.message}`);
    }
  }

  async function onTaskLookup(event) {
    event.preventDefault();
    if (!taskId) {
      setMessage('Task ID is required.');
      return;
    }
    try {
      const data = await getTask(token, taskId);
      setTaskResult(data);
      setMessage('Task fetched successfully.');
    } catch (error) {
      setMessage(`Task lookup failed: ${error.message}`);
    }
  }

  async function onSearch(event) {
    event.preventDefault();
    if (!searchTerm.trim()) {
      setMessage('Search query is required.');
      return;
    }
    try {
      const data = await searchDocuments(token, searchTerm);
      setSearchResults(data.results || []);
      setMessage(`Found ${data.count} result(s).`);
    } catch (error) {
      setMessage(`Search failed: ${error.message}`);
    }
  }

  return (
    <div className="page">
      <header className="hero">
        <h1>Async Document Platform</h1>
        <p>Upload PDF/DOCX files, process them in background workers, and search extracted insights.</p>
      </header>

      {!isAuthenticated ? (
        <section className="panel auth-panel">
          <h2>Authentication</h2>
          <form className="grid-form" onSubmit={onLogin}>
            <label>
              Username
              <input
                value={authForm.username}
                onChange={(e) => setAuthForm({ ...authForm, username: e.target.value })}
                required
              />
            </label>
            <label>
              Email (for register)
              <input
                type="email"
                value={authForm.email}
                onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })}
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={authForm.password}
                onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })}
                required
              />
            </label>
            <div className="actions">
              <button type="submit">Login</button>
              <button type="button" className="secondary" onClick={onRegister}>
                Register
              </button>
            </div>
          </form>
        </section>
      ) : (
        <>
          <section className="panel">
            <div className="panel-head">
              <h2>Upload Document</h2>
              <button className="secondary" onClick={onLogout}>Logout</button>
            </div>
            <input type="file" accept=".pdf,.docx" onChange={onUpload} />
            <p className="hint">Single file upload (PDF, DOCX)</p>
          </section>

          <section className="panel">
            <h2>Batch Upload</h2>
            <input type="file" accept=".zip" onChange={onBatchUpload} />
            <p className="hint">Upload a ZIP archive containing PDF/DOCX files.</p>
            {batchSummary && (
              <pre className="code-block">{JSON.stringify(batchSummary, null, 2)}</pre>
            )}
          </section>

          <section className="panel">
            <h2>Task Status</h2>
            <form className="inline-form" onSubmit={onTaskLookup}>
              <input value={taskId} onChange={(e) => setTaskId(e.target.value)} placeholder="Task UUID" />
              <button type="submit">Check</button>
            </form>
            {taskResult && <pre className="code-block">{JSON.stringify(taskResult, null, 2)}</pre>}
          </section>

          <section className="panel">
            <h2>Search Processed Documents</h2>
            <form className="inline-form" onSubmit={onSearch}>
              <input
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search text"
              />
              <button type="submit">Search</button>
            </form>
            <div className="results">
              {searchResults.map((result) => (
                <article key={result.id} className="result-card">
                  <h3>{result.original_filename}</h3>
                  <p>{result.snippet || result.summary || 'No preview available.'}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="panel">
            <h2>Your Documents</h2>
            <div className="results">
              {documents.map((doc) => (
                <article key={doc.id} className="result-card">
                  <h3>{doc.original_filename}</h3>
                  <p>Status: {doc.status}</p>
                  <p>Chunks: {doc.chunk_count}</p>
                  <p>Task: {doc.processing_task?.id || 'Not available'}</p>
                  {doc.status === 'PROCESSED' && (
                    <button className="secondary" onClick={() => onDownloadResult(doc.id)}>
                      Download Results
                    </button>
                  )}
                </article>
              ))}
            </div>
          </section>
        </>
      )}

      {message && <footer className="message">{message}</footer>}
    </div>
  );
}
