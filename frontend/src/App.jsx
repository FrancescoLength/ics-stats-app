import React, { useState, useEffect } from 'react';
import io from 'socket.io-client';
import Eligibility from './components/Eligibility';
import WorkingTime from './components/WorkingTime';
import './App.css';

const socket = io('http://localhost:5001');

function App() {
  const [file, setFile] = useState(null);
  const [timelineData, setTimelineData] = useState(null);
  const [citizenshipInfo, setCitizenshipInfo] = useState(null);
  const [workingTimeInfo, setWorkingTimeInfo] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('Eligibility');

  useEffect(() => {
    socket.on('result', (data) => {
      setTimelineData(data.timeline);
      setCitizenshipInfo(data.citizenship_info);
      setWorkingTimeInfo(data.working_time_info);
      setLoading(false);
    });

    socket.on('error', (data) => {
      setError(data.error);
      setLoading(false);
    });

    return () => {
      socket.off('result');
      socket.off('error');
    };
  }, []);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleUpload = () => {
    if (!file) {
      setError('Please select a file first.');
      return;
    }

    setLoading(true);
    setError(null);
    setTimelineData(null);
    setWorkingTimeInfo(null);

    const reader = new FileReader();
    reader.onload = (e) => {
      if (socket.connected) {
        socket.emit('upload', { file: e.target.result });
      } else {
        setError("Socket not connected. Please try again.");
        setLoading(false);
      }
    };
    reader.readAsText(file);
  };

  const renderTab = () => {
    switch (activeTab) {
      case 'Eligibility':
        return <Eligibility timelineData={timelineData} citizenshipInfo={citizenshipInfo} />;
      case 'WorkingTime':
        return <WorkingTime workingTimeInfo={workingTimeInfo} />;
      // Add other components here for other tabs
      default:
        return <Eligibility timelineData={timelineData} citizenshipInfo={citizenshipInfo} />;
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>ICS Stats</h1>
        <p>Upload your .ics file to analyze your calendar data.</p>
      </header>
      <main className="App-main">
        <div className="upload-section">
          <input type="file" onChange={handleFileChange} accept=".ics" />
          <button onClick={handleUpload} disabled={loading}>
            {loading ? 'Analyzing...' : 'Analyze Calendar'}
          </button>
          {error && <p className="error">{error}</p>}
          {loading && <div className="loading-spinner"></div>}
        </div>
        <nav className="App-nav">
          <button onClick={() => setActiveTab('Eligibility')} className={activeTab === 'Eligibility' ? 'active' : ''}>
            Eligibility Calculator
          </button>
          <button onClick={() => setActiveTab('WorkingTime')} className={activeTab === 'WorkingTime' ? 'active' : ''}>
            Working Time
          </button>
          {/* Add more buttons for new tabs */}
        </nav>
        <div className="App-content">
          {renderTab()}
        </div>
      </main>
    </div>
  );
}

export default App;