import React, { useState, useEffect } from 'react';
import io from 'socket.io-client';
import './App.css';
import InteractiveTimeline from './InteractiveTimeline.jsx';

const socket = io('http://localhost:5001');

function App() {
  const [file, setFile] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [daysLastYear, setDaysLastYear] = useState(0);
  const [eventsLastYear, setEventsLastYear] = useState([]);
  const [daysLast5Years, setDaysLast5Years] = useState(0);
  const [eventsLast5Years, setEventsLast5Years] = useState([]);
  const [showEventsLastYear, setShowEventsLastYear] = useState(false);
  const [showEventsLast5Years, setShowEventsLast5Years] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    socket.on('result', (data) => {
      setTimeline(data.timeline);
      setDaysLastYear(data.days_last_year);
      setEventsLastYear(data.events_last_year);
      setDaysLast5Years(data.days_last_5_years);
      setEventsLast5Years(data.events_last_5_years);
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
    setTimeline(null);

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

  return (
    <div className="App">
      <h1>Calendar Statistics</h1>
      <p>Upload your .ics file to get statistics about your events.</p>
      <input type="file" onChange={handleFileChange} accept=".ics" />
      <button onClick={handleUpload} disabled={loading}>
        {loading ? 'Analyzing...' : 'Get Stats'}
      </button>
      {error && <p className="error">{error}</p>}
      {loading && (
        <div className="loading-spinner"></div>
      )}
      {timeline && (
        <div className="card">
          <h2>Overseas Trips Timeline</h2>
          <div className="stats-cards-container">
            <div className="stat-card" onClick={() => setShowEventsLastYear(!showEventsLastYear)}>
              <h3>Last Year <span className="toggle-icon">{showEventsLastYear ? '▲' : '▼'}</span></h3>
              <p>{daysLastYear} days</p>
              {showEventsLastYear && (
                <div className="event-details-list">
                  {eventsLastYear.map((event, index) => (
                    <div key={index} className="event-detail-item">
                      <span>{event.content}</span>
                      <span>{new Date(event.start).toLocaleDateString()} - {new Date(event.end).toLocaleDateString()}</span>
                      <span>({event.days} days)</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="stat-card" onClick={() => setShowEventsLast5Years(!showEventsLast5Years)}>
              <h3>Last 5 Years <span className="toggle-icon">{showEventsLast5Years ? '▲' : '▼'}</span></h3>
              <p>{daysLast5Years} days</p>
              {showEventsLast5Years && (
                <div className="event-details-list">
                  {eventsLast5Years.map((event, index) => (
                    <div key={index} className="event-detail-item">
                      <span>{event.content}</span>
                      <span>{new Date(event.start).toLocaleDateString()} - {new Date(event.end).toLocaleDateString()}</span>
                      <span>({event.days} days)</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
          <InteractiveTimeline data={timeline} />
        </div>
      )}
    </div>
  );
}

export default App;