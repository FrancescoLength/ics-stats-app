import React from 'react';
import './WorkingTime.css';

function WorkingTime({ workingTimeInfo }) {
  return (
    <div className="WorkingTime">
      <h2>Working Time Analysis</h2>
      {workingTimeInfo ? (
        <div className="work-time-results">
          {Object.keys(workingTimeInfo).length > 0 ? (
            Object.entries(workingTimeInfo).map(([job, time]) => (
              <div className="work-time-card" key={job}>
                <h3>{job}</h3>
                <p>{time}</p>
              </div>
            ))
          ) : (
            <p>No recurring work-related events found in the calendar.</p>
          )}
        </div>
      ) : (
        <p>Upload a calendar file to see your work time analysis.</p>
      )}
    </div>
  );
}

export default WorkingTime;