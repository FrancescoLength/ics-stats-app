import React, { useEffect, useRef, useState } from 'react';
import { Timeline, DataSet } from 'vis-timeline/standalone';
import 'vis-timeline/styles/vis-timeline-graph2d.min.css';
import moment from 'moment';
import './Eligibility.css';

function Eligibility({ timelineData, citizenshipInfo }) {
  const timelineRef = useRef(null);
  const timelineInstance = useRef(null);
  const [selectedEvent, setSelectedEvent] = useState(null);

  useEffect(() => {
    if (timelineRef.current && timelineData && timelineData.length > 0) {
      const items = new DataSet(timelineData.map(item => {
        const startDate = moment.utc(item.start).subtract(16, 'days').add(12, 'hours').toDate();

        let endDate = null;
        if (item.end) {
          endDate = moment.utc(item.end).subtract(16, 'days').add(12, 'hours').toDate();
        } else {
          endDate = moment.utc(item.start).subtract(16, 'days').add(12, 'hours').toDate();
        }

        if (endDate && endDate.getHours() === 0 && endDate.getMinutes() === 0 && endDate.getSeconds() === 0 && endDate.getMilliseconds() === 0) {
            endDate.setMilliseconds(endDate.getMilliseconds() - 1);
        }

        return {
          id: item.id,
          content: item.content,
          start: startDate,
          end: endDate,
          type: 'range',
          originalItem: item,
        };
      }));

      const options = {
        width: '100%',
        stack: true,
        showCurrentTime: true,
        zoomMin: 1000 * 60 * 60, // One hour in milliseconds (to allow for narrower day columns)
        zoomMax: 1000 * 60 * 60 * 24 * 31, // Approximately one month in milliseconds
        orientation: 'top',
        margin: {
          item: 20,
          axis: 40
        },
        editable: false,
        align: 'left',
        zoomable: false, // Disable manual zooming
        moment: function(date) {
          return moment.utc(date);
        },
        timeAxis: {
          scale: 'day',
          step: 1
        }
      };

      if (!timelineInstance.current) {
        timelineInstance.current = new Timeline(timelineRef.current, items, options);
        timelineInstance.current.on('select', (properties) => {
          if (properties.items.length > 0) {
            const selectedId = properties.items[0];
            const item = items.get(selectedId);
            setSelectedEvent(item.originalItem);
          } else {
            setSelectedEvent(null);
          }
        });
      } else {
        timelineInstance.current.setItems(items);
      }

      if (items.length > 0) {
        const latestEvent = items.max('start');
        if (latestEvent) {
          const startOfMonth = moment(latestEvent.start).startOf('month').toDate();
          const endOfMonth = moment(latestEvent.start).endOf('month').toDate();
          timelineInstance.current.setWindow(startOfMonth, endOfMonth);
        }
      }

    } else if (timelineInstance.current) {
      timelineInstance.current.setItems(new DataSet());
    }
  }, [timelineData]);

  const handleCloseDetails = () => {
    setSelectedEvent(null);
  };

  const navigateTimeline = (direction, unit) => {
    if (timelineInstance.current) {
      const currentWindow = timelineInstance.current.getWindow();
      let newStart = moment(currentWindow.start);
      let newEnd = moment(currentWindow.end);

      if (direction === 'prev') {
        newStart.subtract(1, unit);
        newEnd.subtract(1, unit);
      } else {
        newStart.add(1, unit);
        newEnd.add(1, unit);
      }

      timelineInstance.current.setWindow(newStart.toDate(), newEnd.toDate());
    }
  };

  return (
    <div className="Eligibility">
      {citizenshipInfo && (
        <div className="results-section">
          <div className="citizenship-summary card">
            <h2>Citizenship Eligibility</h2>
            <div className="citizenship-cards">
              <div className="citizenship-card">
                <h3>Last 5 Years</h3>
                <p className="days">{citizenshipInfo.days_last_5_years} / {citizenshipInfo.limit_last_5_years}</p>
                <p className="remaining">{citizenshipInfo.remaining_days_last_5_years} days remaining</p>
              </div>
              <div className="citizenship-card">
                <h3>Last Year</h3>
                <p className="days">{citizenshipInfo.days_last_year} / {citizenshipInfo.limit_last_year}</p>
                <p className="remaining">{citizenshipInfo.remaining_days_last_year} days remaining</p>
              </div>
            </div>
            {citizenshipInfo.return_date && (
              <p className="return-date">
                To remain eligible, you must not leave the UK before: 
                <strong>{moment(citizenshipInfo.return_date).format('MMMM Do, YYYY')}</strong>
              </p>
            )}
          </div>
          
          {timelineData && (
            <div className="timeline-section card">
              <h2>Overseas Trips Timeline</h2>
              <div className="timeline-navigation-controls">
                <button onClick={() => navigateTimeline('prev', 'year')}>&lt;&lt; Year</button>
                <button onClick={() => navigateTimeline('prev', 'month')}>&lt; Month</button>
                <button onClick={() => navigateTimeline('next', 'month')}>Month &gt;</button>
                <button onClick={() => navigateTimeline('next', 'year')}>Year &gt;&gt;</button>
              </div>
              <div ref={timelineRef} style={{ width: '100%', height: '500px' }}></div>
              {!timelineData || timelineData.length === 0 && <p>No data available to display the timeline.</p>}

              {selectedEvent && (
                <div className="event-details-modal">
                  <div className="event-details-content">
                    <h3>{selectedEvent.content}</h3>
                    <p><strong>Start:</strong> {new Date(selectedEvent.start).toLocaleString()}</p>
                    {selectedEvent.end && <p><strong>End:</strong> {new Date(selectedEvent.end).toLocaleString()}</p>}
                    <button onClick={handleCloseDetails}>Close</button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default Eligibility;