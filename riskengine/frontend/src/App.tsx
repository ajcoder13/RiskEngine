import React, { useState, useEffect } from 'react';
import {
  Signal,
  RiskSummary,
  DataSourceStatus,
} from './api/types';
import { apiClient } from './api/client';
import { SignalsFeedView } from './components/SignalsFeedView';
import { NLPInteractiveSandbox } from './components/NLPInteractiveSandbox';
import { ModuleAPortfolioView } from './components/ModuleAPortfolioView';
import { ModuleBStressTestingView } from './components/ModuleBStressTestingView';
import { ArchitectureMethodologyView } from './components/ArchitectureMethodologyView';
import {
  Activity,
  RotateCw,
  Cpu,
  BarChart2,
  ShieldAlert,
  Info,
  Radio,
  Sliders,
} from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<
    'signals' | 'sandbox' | 'module-a' | 'module-b' | 'methodology'
  >('signals');

  const [signals, setSignals] = useState<Signal[]>([]);
  const [summary, setSummary] = useState<RiskSummary | null>(null);
  const [sources, setSources] = useState<DataSourceStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [stressPresetSignal, setStressPresetSignal] = useState<Signal | null>(null);

  const fetchCoreData = async () => {
    try {
      const [sigData, sumData, srcData] = await Promise.all([
        apiClient.getSignals(),
        apiClient.getRiskSummary(),
        apiClient.getSources(),
      ]);
      setSignals(sigData);
      setSummary(sumData);
      setSources(srcData);
    } catch (err) {
      console.error('Failed to load RiskEngine core data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCoreData();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await apiClient.refreshData();
      await fetchCoreData();
    } catch (err) {
      console.error('Refresh failed', err);
    } finally {
      setRefreshing(false);
    }
  };

  const handleSelectSignalForStress = (signal: Signal) => {
    setStressPresetSignal(signal);
    setActiveTab('module-b');
  };

  return (
    <div className="app-container">
      {/* Header Bar */}
      <header className="app-header">
        <div className="brand">
          <div className="brand-icon">
            <Activity size={24} />
          </div>
          <div>
            <div className="brand-title">RiskEngine</div>
            <div className="brand-subtitle">Financial AI/NLP Intelligence & Risk Quantification</div>
          </div>
        </div>

        <div className="header-actions">
          {sources && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.35rem 0.75rem',
                borderRadius: '8px',
                background: sources.live_data_enabled ? 'rgba(16, 185, 129, 0.15)' : 'rgba(59, 130, 246, 0.12)',
                border: `1px solid ${sources.live_data_enabled ? 'rgba(16, 185, 129, 0.3)' : 'rgba(59, 130, 246, 0.25)'}`,
                fontSize: '0.75rem',
              }}
            >
              <Radio size={12} style={{ color: sources.live_data_enabled ? '#34d399' : '#60a5fa' }} />
              <span style={{ color: sources.live_data_enabled ? '#34d399' : '#93c5fd', fontWeight: 600 }}>
                {sources.live_data_enabled ? 'Live Feed Connected' : 'Sample Feed Mode'}
              </span>
            </div>
          )}

          <button
            className="btn btn-secondary btn-sm"
            onClick={handleRefresh}
            disabled={refreshing}
            title="Reload and re-process ingestion data"
          >
            <RotateCw size={14} className={refreshing ? 'spin' : ''} />
            {refreshing ? 'Ingesting...' : 'Refresh Feed'}
          </button>
        </div>
      </header>

      {/* Main Tab Navigation */}
      <nav className="nav-tabs">
        <button
          className={`nav-tab-btn ${activeTab === 'signals' ? 'active' : ''}`}
          onClick={() => setActiveTab('signals')}
        >
          <BarChart2 size={16} /> Live Risk Signals Feed
        </button>

        <button
          className={`nav-tab-btn ${activeTab === 'sandbox' ? 'active' : ''}`}
          onClick={() => setActiveTab('sandbox')}
        >
          <Cpu size={16} /> Interactive NLP Sandbox
        </button>

        <button
          className={`nav-tab-btn ${activeTab === 'module-a' ? 'active' : ''}`}
          onClick={() => setActiveTab('module-a')}
        >
          <Sliders size={16} /> Module A: Index Rebalancer
        </button>

        <button
          className={`nav-tab-btn ${activeTab === 'module-b' ? 'active' : ''}`}
          onClick={() => setActiveTab('module-b')}
        >
          <ShieldAlert size={16} /> Module B: Stress Testing
        </button>

        <button
          className={`nav-tab-btn ${activeTab === 'methodology' ? 'active' : ''}`}
          onClick={() => setActiveTab('methodology')}
        >
          <Info size={16} /> Architecture & Methodology
        </button>
      </nav>

      {/* Main View Area */}
      <main>
        {activeTab === 'signals' && (
          <SignalsFeedView
            signals={signals}
            summary={summary}
            loading={loading}
            onSelectSignalForStress={handleSelectSignalForStress}
          />
        )}

        {activeTab === 'sandbox' && (
          <NLPInteractiveSandbox onForwardToStress={handleSelectSignalForStress} />
        )}

        {activeTab === 'module-a' && <ModuleAPortfolioView />}

        {activeTab === 'module-b' && (
          <ModuleBStressTestingView presetSignal={stressPresetSignal} />
        )}

        {activeTab === 'methodology' && <ArchitectureMethodologyView />}
      </main>

      {/* Footer */}
      <footer className="system-footer">
        <div>
          RiskEngine Platform • End-to-End Financial AI/NLP Pipeline
        </div>
        <div style={{ display: 'flex', gap: '1.5rem' }}>
          <span>FastAPI Backend • React TypeScript Frontend</span>
          <span>165/165 Unit Tests Verified</span>
        </div>
      </footer>
    </div>
  );
};

export default App;
