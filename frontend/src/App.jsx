import React, { useState, useEffect } from 'react';
import { 
  Briefcase, 
  Building2, 
  Bell, 
  Terminal, 
  Search, 
  CheckCircle2, 
  Trash2, 
  ExternalLink, 
  Plus, 
  RefreshCw, 
  Play, 
  Check, 
  AlertCircle, 
  Calendar, 
  MapPin, 
  Sparkles,
  Info
} from 'lucide-react';

const API_BASE = "http://localhost:8000/api";

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [jobs, setJobs] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [settings, setSettings] = useState({
    telegram_enabled: false,
    telegram_token: '',
    telegram_chat_id: '',
    discord_enabled: false,
    discord_webhook_url: '',
    email_enabled: false,
    email_smtp_server: '',
    email_smtp_port: 587,
    email_sender: '',
    email_password: '',
    email_recipient: '',
    scraper_interval_hours: 12
  });
  const [logs, setLogs] = useState([]);
  const [scraperStatus, setScraperStatus] = useState({
    is_running: false,
    last_run: null,
    last_run_jobs_added: 0,
    last_run_status: 'Idle'
  });

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCompany, setSelectedCompany] = useState('');
  const [selectedSource, setSelectedSource] = useState('');

  // UI States
  const [loading, setLoading] = useState(false);
  const [scraperRunning, setScraperRunning] = useState(false);
  const [toast, setToast] = useState(null);
  
  // Forms
  const [newCompany, setNewCompany] = useState({ name: '', domain: '' });
  const [savingSettings, setSavingSettings] = useState(false);
  const [testLoading, setTestLoading] = useState({});

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // --- Fetch Data functions ---
  const fetchJobs = async () => {
    try {
      setLoading(true);
      const url = new URL(`${API_BASE}/jobs`);
      if (searchQuery) url.searchParams.append('search', searchQuery);
      if (selectedCompany) url.searchParams.append('company', selectedCompany);
      if (selectedSource) url.searchParams.append('source', selectedSource);

      const res = await fetch(url);
      const data = await res.json();
      setJobs(data);
    } catch (e) {
      console.error(e);
      showToast("Failed to fetch jobs list", "error");
    } finally {
      setLoading(false);
    }
  };

  const fetchCompanies = async () => {
    try {
      const res = await fetch(`${API_BASE}/companies`);
      const data = await res.json();
      setCompanies(data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchSettings = async () => {
    try {
      const res = await fetch(`${API_BASE}/settings`);
      const data = await res.json();
      setSettings(data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchLogs = async () => {
    try {
      const res = await fetch(`${API_BASE}/scraper/logs`);
      const data = await res.json();
      setLogs(data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchScraperStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/scraper/status`);
      const data = await res.json();
      setScraperStatus(data);
      setScraperRunning(data.is_running);
    } catch (e) {
      console.error(e);
    }
  };

  // Sync data on load and when filters change
  useEffect(() => {
    fetchCompanies();
    fetchSettings();
    fetchScraperStatus();
    fetchLogs();
  }, []);

  useEffect(() => {
    fetchJobs();
  }, [searchQuery, selectedCompany, selectedSource]);

  // Poll scraper status if it is running
  useEffect(() => {
    let intervalId;
    if (scraperRunning) {
      intervalId = setInterval(() => {
        fetchScraperStatus();
        fetchJobs();
        fetchLogs();
      }, 5000);
    }
    return () => clearInterval(intervalId);
  }, [scraperRunning]);

  // --- Actions ---
  const handleTriggerScraper = async () => {
    try {
      setScraperRunning(true);
      const res = await fetch(`${API_BASE}/scraper/run`, { method: 'POST' });
      const data = await res.json();
      showToast(data.message, "success");
      fetchScraperStatus();
    } catch (e) {
      showToast("Failed to trigger scraper", "error");
      setScraperRunning(false);
    }
  };

  const handleAddCompany = async (e) => {
    e.preventDefault();
    if (!newCompany.name.trim() || !newCompany.domain.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/companies`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newCompany)
      });
      if (res.ok) {
        showToast(`Added ${newCompany.name} to target tracking list.`);
        setNewCompany({ name: '', domain: '' });
        fetchCompanies();
      } else {
        const err = await res.json();
        showToast(err.detail || "Error adding company", "error");
      }
    } catch (e) {
      showToast("Network error occurred", "error");
    }
  };

  const handleDeleteCompany = async (id, name) => {
    if (!confirm(`Are you sure you want to stop tracking ${name}?`)) return;
    try {
      const res = await fetch(`${API_BASE}/companies/${id}`, { method: 'DELETE' });
      if (res.ok) {
        showToast(`Removed ${name} from tracking.`);
        fetchCompanies();
      }
    } catch (e) {
      showToast("Error deleting company", "error");
    }
  };

  const handleDeleteJob = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/jobs/${id}`, { method: 'DELETE' });
      if (res.ok) {
        setJobs(jobs.filter(j => j.id !== id));
        showToast("Job opening removed.");
      }
    } catch (e) {
      showToast("Error deleting job", "error");
    }
  };

  const handleToggleVerifyJob = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/jobs/${id}/verify`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setJobs(jobs.map(j => j.id === id ? { ...j, is_verified: data.is_verified } : j));
        showToast(data.is_verified ? "Job verified as legitimate." : "Job verification cleared.");
      }
    } catch (e) {
      showToast("Failed to update job status", "error");
    }
  };

  const handleSaveSettings = async (e) => {
    e.preventDefault();
    setSavingSettings(true);
    try {
      const res = await fetch(`${API_BASE}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      if (res.ok) {
        showToast("Alert and Schedule settings saved successfully.");
        fetchSettings();
      }
    } catch (e) {
      showToast("Failed to save settings", "error");
    } finally {
      setSavingSettings(false);
    }
  };

  const handleTestNotification = async (channel) => {
    setTestLoading(prev => ({ ...prev, [channel]: true }));
    try {
      const res = await fetch(`${API_BASE}/settings/test-notification`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel })
      });
      if (res.ok) {
        const data = await res.json();
        showToast(data.message);
      } else {
        const err = await res.json();
        showToast(err.detail || "Test alert failed", "error");
      }
    } catch (e) {
      showToast("Test notification failed to dispatch", "error");
    } finally {
      setTestLoading(prev => ({ ...prev, [channel]: false }));
    }
  };

  // Helper date formatter
  const formatDate = (isoString) => {
    if (!isoString) return 'N/A';
    const date = new Date(isoString);
    return date.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="app-container">
      {/* Toast Notification */}
      {toast && (
        <div style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          zIndex: 9999,
          background: toast.type === 'error' ? 'rgba(239, 68, 68, 0.95)' : 'rgba(16, 185, 129, 0.95)',
          color: 'white',
          padding: '16px 24px',
          borderRadius: '12px',
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.3)',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          fontFamily: 'var(--font-sans)',
          fontWeight: 600,
          backdropFilter: 'blur(8px)',
          animation: 'slideUp 0.3s ease-out'
        }}>
          {toast.type === 'error' ? <AlertCircle size={20} /> : <CheckCircle2 size={20} />}
          <span>{toast.message}</span>
        </div>
      )}

      {/* Sidebar navigation */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <Sparkles size={22} />
          </div>
          <span className="brand-text">Antigravity Jobs</span>
        </div>

        <nav>
          <ul className="nav-links">
            <li className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
              <Briefcase />
              <span>Job Feed</span>
            </li>
            <li className={`nav-item ${activeTab === 'companies' ? 'active' : ''}`} onClick={() => setActiveTab('companies')}>
              <Building2 />
              <span>Target Companies</span>
            </li>
            <li className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`} onClick={() => setActiveTab('settings')}>
              <Bell />
              <span>Notifications</span>
            </li>
            <li className={`nav-item ${activeTab === 'logs' ? 'active' : ''}`} onClick={() => setActiveTab('logs')}>
              <Terminal />
              <span>Scraper Logs</span>
            </li>
          </ul>
        </nav>

        {/* Scraper Status Panel at the bottom of Sidebar */}
        <div style={{
          marginTop: 'auto',
          padding: '16px',
          background: 'rgba(255, 255, 255, 0.02)',
          border: '1px solid var(--border-color)',
          borderRadius: '12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: scraperRunning ? 'var(--secondary)' : 'var(--accent-success)',
              animation: scraperRunning ? 'pulse 1.5s infinite' : 'none'
            }} />
            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)' }}>
              Scraper {scraperRunning ? 'Scraping...' : 'Idle'}
            </span>
          </div>
          <button 
            onClick={handleTriggerScraper} 
            disabled={scraperRunning} 
            className="btn btn-primary"
            style={{ width: '100%', padding: '8px 16px', fontSize: '13px' }}
          >
            {scraperRunning ? (
              <>
                <RefreshCw size={14} className="spinner" />
                <span>Running...</span>
              </>
            ) : (
              <>
                <Play size={14} />
                <span>Run Scraper Now</span>
              </>
            )}
          </button>
        </div>
      </aside>

      {/* Main Panel Content */}
      <main className="main-content">
        
        {/* DASHBOARD TAB */}
        {activeTab === 'dashboard' && (
          <>
            <div className="content-header">
              <div className="header-title">
                <h1>fresher job feed</h1>
                <p>Verified openings for 0-1 years of experience in Tier 2 product companies</p>
              </div>
              <button onClick={fetchJobs} className="btn btn-secondary">
                <RefreshCw size={16} />
                <span>Refresh Feed</span>
              </button>
            </div>

            {/* KPI Cards */}
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-icon blue">
                  <Briefcase size={24} />
                </div>
                <div className="stat-info">
                  <div className="stat-value">{jobs.length}</div>
                  <div className="stat-label">Matching Jobs</div>
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon indigo">
                  <Building2 size={24} />
                </div>
                <div className="stat-info">
                  <div className="stat-value">{companies.length}</div>
                  <div className="stat-label">Companies Tracked</div>
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon green">
                  <CheckCircle2 size={24} />
                </div>
                <div className="stat-info">
                  <div className="stat-value">
                    {jobs.filter(j => j.is_verified).length}
                  </div>
                  <div className="stat-label">Legit Verified Links</div>
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon orange">
                  <Info size={24} />
                </div>
                <div className="stat-info">
                  <div className="stat-value" style={{ fontSize: '13px', lineHeight: 1.2 }}>
                    {scraperStatus.last_run ? formatDate(scraperStatus.last_run).split(',')[0] : 'Never'}
                  </div>
                  <div className="stat-label">Last Scraper Run</div>
                </div>
              </div>
            </div>

            {/* Filters panel */}
            <div className="filter-panel">
              <div className="search-wrapper">
                <Search />
                <input 
                  type="text" 
                  placeholder="Search SDE, frontend, intern roles..." 
                  className="input-field"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>

              <select 
                className="select-field" 
                value={selectedCompany} 
                onChange={(e) => setSelectedCompany(e.target.value)}
              >
                <option value="">All Companies</option>
                {companies.map(c => (
                  <option key={c.id} value={c.name}>{c.name}</option>
                ))}
              </select>

              <select 
                className="select-field"
                value={selectedSource}
                onChange={(e) => setSelectedSource(e.target.value)}
              >
                <option value="">All Platforms</option>
                <option value="linkedin">LinkedIn</option>
                <option value="indeed">Indeed</option>
                <option value="unstop">Unstop Challenges</option>
              </select>
            </div>

            {/* Jobs feed layout */}
            {loading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: '60px' }}>
                <RefreshCw size={36} className="spinner" style={{ color: 'var(--primary-light)' }} />
              </div>
            ) : jobs.length === 0 ? (
              <div className="empty-state">
                <Briefcase />
                <h3>No fresher openings found</h3>
                <p>Try running the scraper or tweaking your filters to discover recent jobs.</p>
              </div>
            ) : (
              <div className="job-grid">
                {jobs.map(job => (
                  <div key={job.id} className="job-card">
                    <div>
                      <div className="job-header">
                        <span className="job-company-badge">{job.company}</span>
                        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                          <span className={`job-source-tag ${job.source.toLowerCase()}`}>
                            {job.source}
                          </span>
                          <button 
                            onClick={() => handleDeleteJob(job.id)} 
                            className="action-icon"
                            style={{ padding: '4px' }}
                            title="Delete this listing"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>

                      <h3 className="job-title">{job.title}</h3>

                      <div className="job-meta">
                        <div className="job-meta-item">
                          <MapPin />
                          <span>{job.location || 'India'}</span>
                        </div>
                        <div className="job-meta-item">
                          <Calendar />
                          <span>Scraped: {formatDate(job.date_scraped)}</span>
                        </div>
                        <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                          <span className="tag-fresher">0-1 yoe</span>
                          {job.is_verified && (
                            <span style={{
                              background: 'rgba(16, 185, 129, 0.1)',
                              color: 'var(--accent-success)',
                              border: '1px solid rgba(16, 185, 129, 0.2)',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              fontSize: '11px',
                              fontWeight: 600,
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '3px'
                            }}>
                              <CheckCircle2 size={10} /> Verified Legit Link
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="job-actions">
                      <button 
                        onClick={() => handleToggleVerifyJob(job.id)} 
                        className={`btn ${job.is_verified ? 'btn-secondary' : 'btn-primary'}`}
                        style={{ padding: '8px', flex: '0 0 46px' }}
                        title={job.is_verified ? "Mark as Unverified" : "Mark as Verified"}
                      >
                        {job.is_verified ? <Check size={18} style={{ color: 'var(--accent-success)' }} /> : <CheckCircle2 size={18} />}
                      </button>
                      
                      <a 
                        href={job.url} 
                        target="_blank" 
                        rel="noreferrer" 
                        className="btn btn-primary"
                        style={{ textDecoration: 'none' }}
                      >
                        <span>Apply Direct</span>
                        <ExternalLink size={14} />
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* TARGET COMPANIES TAB */}
        {activeTab === 'companies' && (
          <>
            <div className="content-header">
              <div className="header-title">
                <h1>target tier 2 companies</h1>
                <p>Manage the list of software product companies to monitor for jobs</p>
              </div>
            </div>

            <div className="company-container">
              {/* Add company form */}
              <div className="company-form-panel">
                <div className="content-card">
                  <h2 className="content-card-title">Add Company</h2>
                  <form onSubmit={handleAddCompany}>
                    <div className="form-group">
                      <label>Company Name</label>
                      <input 
                        type="text" 
                        className="input-box" 
                        placeholder="e.g. PhonePe"
                        value={newCompany.name}
                        onChange={(e) => setNewCompany(prev => ({ ...prev, name: e.target.value }))}
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label>Official Domain Name</label>
                      <input 
                        type="text" 
                        className="input-box" 
                        placeholder="e.g. phonepe.com"
                        value={newCompany.domain}
                        onChange={(e) => setNewCompany(prev => ({ ...prev, domain: e.target.value }))}
                        required
                      />
                    </div>
                    <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '12px' }}>
                      <Plus size={16} />
                      <span>Track Company</span>
                    </button>
                  </form>
                </div>
              </div>

              {/* Company list table */}
              <div className="company-list-panel">
                <div className="content-card" style={{ padding: '0px', overflow: 'hidden' }}>
                  <div style={{ padding: '24px 32px', borderBottom: '1px solid var(--border-color)' }}>
                    <h2 style={{ fontSize: '18px', fontWeight: 600 }}>Currently Tracking ({companies.length})</h2>
                  </div>
                  <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
                    <table className="company-table">
                      <thead>
                        <tr>
                          <th>Company</th>
                          <th>Official Domain</th>
                          <th className="company-action-cell">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {companies.map(c => (
                          <tr key={c.id}>
                            <td style={{ fontWeight: 600 }}>{c.name}</td>
                            <td style={{ color: 'var(--text-secondary)' }}>{c.domain}</td>
                            <td className="company-action-cell">
                              <button onClick={() => handleDeleteCompany(c.id, c.name)} className="action-icon" title="Delete">
                                <Trash2 size={16} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        {/* SETTINGS / NOTIFICATIONS TAB */}
        {activeTab === 'settings' && (
          <>
            <div className="content-header">
              <div className="header-title">
                <h1>alert settings & scheduler</h1>
                <p>Configure notification channels and automation schedules</p>
              </div>
            </div>

            <form onSubmit={handleSaveSettings} className="settings-container">
              {/* Left Settings Controls */}
              <div className="settings-sidebar">
                <div className="content-card" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <h2 className="content-card-title">Notification Channels</h2>
                  
                  {/* Telegram Toggle */}
                  <div className="switch-group">
                    <span style={{ fontWeight: 600, fontSize: '14px' }}>Telegram Bot Alerts</span>
                    <label className="switch">
                      <input 
                        type="checkbox"
                        checked={settings.telegram_enabled}
                        onChange={(e) => setSettings(prev => ({ ...prev, telegram_enabled: e.target.checked }))}
                      />
                      <span className="slider"></span>
                    </label>
                  </div>

                  {/* Discord Toggle */}
                  <div className="switch-group">
                    <span style={{ fontWeight: 600, fontSize: '14px' }}>Discord Webhook Alerts</span>
                    <label className="switch">
                      <input 
                        type="checkbox"
                        checked={settings.discord_enabled}
                        onChange={(e) => setSettings(prev => ({ ...prev, discord_enabled: e.target.checked }))}
                      />
                      <span className="slider"></span>
                    </label>
                  </div>

                  {/* Email Toggle */}
                  <div className="switch-group">
                    <span style={{ fontWeight: 600, fontSize: '14px' }}>SMTP Email Digests</span>
                    <label className="switch">
                      <input 
                        type="checkbox"
                        checked={settings.email_enabled}
                        onChange={(e) => setSettings(prev => ({ ...prev, email_enabled: e.target.checked }))}
                      />
                      <span className="slider"></span>
                    </label>
                  </div>
                </div>

                <div className="content-card" style={{ marginTop: '24px' }}>
                  <h2 className="content-card-title">Scraper Schedule</h2>
                  <div className="form-group">
                    <label>Scrape Frequency (Hours)</label>
                    <select 
                      className="select-field" 
                      style={{ width: '100%', background: 'rgba(15, 23, 42, 0.6)' }}
                      value={settings.scraper_interval_hours}
                      onChange={(e) => setSettings(prev => ({ ...prev, scraper_interval_hours: parseInt(e.target.value) }))}
                    >
                      <option value={2}>Every 2 Hours</option>
                      <option value={6}>Every 6 Hours</option>
                      <option value={12}>Every 12 Hours</option>
                      <option value={24}>Every 24 Hours (Daily)</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Right Settings configurations */}
              <div className="settings-main">
                {/* Telegram Config Panel */}
                {settings.telegram_enabled && (
                  <div className="content-card" style={{ marginBottom: '24px' }}>
                    <h3 className="content-card-title" style={{ borderColor: 'var(--primary-glow)' }}>Telegram Configuration</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                      <div className="form-group">
                        <label>Bot API Token</label>
                        <input 
                          type="password" 
                          className="input-box" 
                          placeholder="API Token from BotFather"
                          value={settings.telegram_token || ''}
                          onChange={(e) => setSettings(prev => ({ ...prev, telegram_token: e.target.value }))}
                        />
                      </div>
                      <div className="form-group">
                        <label>Chat ID</label>
                        <input 
                          type="text" 
                          className="input-box" 
                          placeholder="Your Telegram User/Chat ID"
                          value={settings.telegram_chat_id || ''}
                          onChange={(e) => setSettings(prev => ({ ...prev, telegram_chat_id: e.target.value }))}
                        />
                      </div>
                    </div>
                    <button 
                      type="button" 
                      onClick={() => handleTestNotification('telegram')}
                      disabled={testLoading['telegram']}
                      className="btn btn-secondary" 
                      style={{ marginTop: '12px' }}
                    >
                      {testLoading['telegram'] ? <RefreshCw size={14} className="spinner" /> : <Bell size={14} />}
                      <span>Test Telegram Dispatcher</span>
                    </button>
                  </div>
                )}

                {/* Discord Config Panel */}
                {settings.discord_enabled && (
                  <div className="content-card" style={{ marginBottom: '24px' }}>
                    <h3 className="content-card-title" style={{ borderColor: 'var(--secondary-glow)' }}>Discord Configuration</h3>
                    <div className="form-group">
                      <label>Webhook URL</label>
                      <input 
                        type="password" 
                        className="input-box" 
                        placeholder="https://discord.com/api/webhooks/..."
                        value={settings.discord_webhook_url || ''}
                        onChange={(e) => setSettings(prev => ({ ...prev, discord_webhook_url: e.target.value }))}
                      />
                    </div>
                    <button 
                      type="button" 
                      onClick={() => handleTestNotification('discord')}
                      disabled={testLoading['discord']}
                      className="btn btn-secondary" 
                      style={{ marginTop: '12px' }}
                    >
                      {testLoading['discord'] ? <RefreshCw size={14} className="spinner" /> : <Bell size={14} />}
                      <span>Test Discord Webhook</span>
                    </button>
                  </div>
                )}

                {/* Email Config Panel */}
                {settings.email_enabled && (
                  <div className="content-card" style={{ marginBottom: '24px' }}>
                    <h3 className="content-card-title">SMTP Email Configuration</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '16px', marginBottom: '16px' }}>
                      <div className="form-group">
                        <label>SMTP Server Host</label>
                        <input 
                          type="text" 
                          className="input-box" 
                          placeholder="e.g. smtp.gmail.com"
                          value={settings.email_smtp_server || ''}
                          onChange={(e) => setSettings(prev => ({ ...prev, email_smtp_server: e.target.value }))}
                        />
                      </div>
                      <div className="form-group">
                        <label>SMTP Port</label>
                        <input 
                          type="number" 
                          className="input-box" 
                          value={settings.email_smtp_port}
                          onChange={(e) => setSettings(prev => ({ ...prev, email_smtp_port: parseInt(e.target.value) }))}
                        />
                      </div>
                    </div>
                    
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                      <div className="form-group">
                        <label>Sender Address (From)</label>
                        <input 
                          type="email" 
                          className="input-box" 
                          placeholder="sender@gmail.com"
                          value={settings.email_sender || ''}
                          onChange={(e) => setSettings(prev => ({ ...prev, email_sender: e.target.value }))}
                        />
                      </div>
                      <div className="form-group">
                        <label>Sender SMTP Password</label>
                        <input 
                          type="password" 
                          className="input-box" 
                          placeholder="App Password for Gmail"
                          value={settings.email_password || ''}
                          onChange={(e) => setSettings(prev => ({ ...prev, email_password: e.target.value }))}
                        />
                      </div>
                    </div>

                    <div className="form-group">
                      <label>Recipient Address (To)</label>
                      <input 
                        type="email" 
                        className="input-box" 
                        placeholder="your-email@example.com"
                        value={settings.email_recipient || ''}
                        onChange={(e) => setSettings(prev => ({ ...prev, email_recipient: e.target.value }))}
                      />
                    </div>
                    
                    <button 
                      type="button" 
                      onClick={() => handleTestNotification('email')}
                      disabled={testLoading['email']}
                      className="btn btn-secondary" 
                      style={{ marginTop: '12px' }}
                    >
                      {testLoading['email'] ? <RefreshCw size={14} className="spinner" /> : <Bell size={14} />}
                      <span>Test Email Digest</span>
                    </button>
                  </div>
                )}

                {/* Save Button */}
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <button type="submit" disabled={savingSettings} className="btn btn-primary" style={{ padding: '14px 28px' }}>
                    {savingSettings ? <RefreshCw size={16} className="spinner" /> : <CheckCircle2 size={16} />}
                    <span>Save Config & Apply Schedules</span>
                  </button>
                </div>
              </div>
            </form>
          </>
        )}

        {/* SCRAPER LOGS TAB */}
        {activeTab === 'logs' && (
          <>
            <div className="content-header">
              <div className="header-title">
                <h1>scraper logs & executions</h1>
                <p>Inspect output logs and diagnostics from the background aggregation runs</p>
              </div>
              <button onClick={fetchLogs} className="btn btn-secondary">
                <RefreshCw size={16} />
                <span>Refresh Log Entries</span>
              </button>
            </div>

            <div className="content-card" style={{ padding: '0px', overflow: 'hidden' }}>
              <table className="log-table">
                <thead>
                  <tr style={{ background: 'rgba(255, 255, 255, 0.02)' }}>
                    <th style={{ padding: '16px 20px', color: 'var(--text-secondary)' }}>Timestamp</th>
                    <th style={{ padding: '16px 20px', color: 'var(--text-secondary)' }}>Status</th>
                    <th style={{ padding: '16px 20px', color: 'var(--text-secondary)' }}>Jobs Scraped</th>
                    <th style={{ padding: '16px 20px', color: 'var(--text-secondary)' }}>Jobs Added</th>
                    <th style={{ padding: '16px 20px', color: 'var(--text-secondary)' }}>Log Message</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.length === 0 ? (
                    <tr>
                      <td colSpan="5" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                        No scraper runs recorded yet.
                      </td>
                    </tr>
                  ) : (
                    logs.map(log => (
                      <tr key={log.id}>
                        <td>{formatDate(log.timestamp)}</td>
                        <td>
                          <span className={`log-status ${log.status.toLowerCase()}`}>
                            {log.status}
                          </span>
                        </td>
                        <td style={{ fontWeight: 600 }}>{log.jobs_scraped}</td>
                        <td style={{ fontWeight: 600, color: 'var(--accent-success)' }}>{log.jobs_added}</td>
                        <td style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>{log.log_message}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
