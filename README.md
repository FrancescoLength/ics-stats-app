# ICS Stats App
<img width="1554" height="685" alt="immagine" src="https://github.com/user-attachments/assets/31cc5e06-eb58-402f-8e6d-13a88ea85fea" />

A web application that allows users to upload an `.ics` calendar file and visualize statistics and a timeline of their events.

## Features

*   **ICS File Upload:** Easily upload your `.ics` calendar files.
*   **Event Statistics:** View aggregated statistics, including days spent on events in the last year and last 5 years.
*   **Interactive Timeline:** Visualize your events on an interactive timeline, with navigation controls for year and month.
*   **Event Details:** Click on timeline events to see detailed information.

## Technologies Used

### Frontend
*   **React:** A JavaScript library for building user interfaces.
*   **Vite:** A fast build tool for modern web projects.
*   **vis-timeline:** A dynamic, browser-based visualization library for displaying events.
*   **Moment.js:** A JavaScript date library for parsing, validating, manipulating, and formatting dates.
*   **Socket.IO Client:** For real-time communication with the backend.

### Backend
*   **Python:** The programming language used for the backend.
*   **Flask:** A micro web framework for Python.
*   **Flask-SocketIO:** Integrates Socket.IO with Flask for real-time communication.
*   **icalendar:** A Python library for parsing iCalendar files.

## Setup and Running the Project

To get this project up and running on your local machine, follow these steps:

### Prerequisites

Make sure you have the following installed:
*   Node.js (LTS version recommended) and npm (comes with Node.js)
*   Python 3.x
*   pip (Python package installer)

### 1. Backend Setup

Navigate to the `backend` directory, install the required Python packages, and start the Flask server.

```bash
cd backend
pip install -r requirements.txt
python app.py
```
The backend server will typically run on `http://localhost:5001`.

### 2. Frontend Setup

Open a new terminal, navigate to the `frontend` directory, install the Node.js dependencies, and start the Vite development server.

```bash
cd frontend
npm install
npm start
```
The frontend application will typically run on `http://localhost:5173` (or another port if 5173 is in use).

### 3. Usage

1.  Once both the backend and frontend servers are running, open your web browser and go to the frontend URL (e.g., `http://localhost:5173`).
2.  Use the file input to select your `.ics` calendar file.
3.  Click "Get Stats" to upload the file and see the statistics and timeline.
4.  Navigate the timeline using the "Previous Year", "Next Year", "Previous Month", and "Next Month" buttons.
5.  Click on events in the timeline to view more details.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
