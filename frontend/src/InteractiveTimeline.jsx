import React, { useEffect, useRef, useState } from 'react';
import { Timeline, DataSet } from 'vis-timeline/standalone';
import 'vis-timeline/styles/vis-timeline-graph2d.min.css';
import './TimelineCustom.css';
import moment from 'moment';

const InteractiveTimeline = ({ data }) => {
  const timelineRef = useRef(null);
  const timelineInstance = useRef(null);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [viewMode, setViewMode] = useState('month'); // Default view mode

  useEffect(() => {
    if (timelineRef.current && data && data.length > 0) {
      console.log("Raw data received:", data);

      const items = new DataSet(data.map(item => {
        const startDate = moment.utc(item.start).subtract(16, 'days').add(12, 'hours').toDate();

        let endDate = null;
        if (item.end) {
          endDate = moment.utc(item.end).subtract(16, 'days').add(12, 'hours').toDate();
        } else {
          endDate = moment.utc(item.start).subtract(16, 'days').add(12, 'hours').toDate();
        }

        // If dtend is exactly midnight, subtract a millisecond to make it end on the previous day
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

      console.log("Items DataSet content:", items.get());

      data.forEach(item => {
        console.log(`Item ID: ${item.id}, Content: ${item.content}, Start: ${item.start}, End: ${item.end}`);
      });

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
        console.log("Initializing vis-timeline with ref:", timelineRef.current);
        timelineInstance.current = new Timeline(timelineRef.current, items, options);
        console.log("vis-timeline instance created:", timelineInstance.current);

        // Add event listener for item selection
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
        console.log("Updating vis-timeline items.");
        timelineInstance.current.setItems(items);
      }

      // Find the latest event and set the timeline window to it
      if (items.length > 0) {
        const latestEvent = items.max('start');
        if (latestEvent) { // Add this check
          // Set the window to show the full month of the latest event
          const startOfMonth = moment(latestEvent.start).startOf('month').toDate();
          const endOfMonth = moment(latestEvent.start).endOf('month').toDate();
          timelineInstance.current.setWindow(startOfMonth, endOfMonth);
        }
      }

    } else if (timelineInstance.current) {
      // Clear the timeline if no data
      timelineInstance.current.setItems(new DataSet());
    }
  }, [data]);

  

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
    <div className="card">
      <h2>Overseas Trips Timeline</h2>
      <div className="timeline-navigation-controls">
        <button onClick={() => navigateTimeline('prev', 'year')}>&lt;&lt; Year</button>
        <button onClick={() => navigateTimeline('prev', 'month')}>&lt; Month</button>
        <button onClick={() => navigateTimeline('next', 'month')}>Month &gt;</button>
        <button onClick={() => navigateTimeline('next', 'year')}>Year &gt;&gt;</button>
      </div>
      <div ref={timelineRef} style={{ width: '100%', height: '500px' }}></div>
      {!data || data.length === 0 && <p>No data available to display the timeline.</p>}

      {selectedEvent && (
        <div className="event-details-modal">
          <div className="event-details-content">
            <h3>{selectedEvent.content}</h3>
            <p><strong>Start:</strong> {new Date(selectedEvent.start).toLocaleString()}</p>
            {selectedEvent.end && <p><strong>End:</strong> {new Date(selectedEvent.end).toLocaleString()}</p>}
            {/* Add more details as needed from selectedEvent.originalItem */}
            <button onClick={handleCloseDetails}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default InteractiveTimeline;