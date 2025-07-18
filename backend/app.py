import argparse
import time
import logging
import re
import os
import subprocess
import google.generativeai as genai
from flask import Flask, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from icalendar import Calendar
from datetime import timedelta, date, datetime, timezone

# --- Argument Parser Configuration ---
parser = argparse.ArgumentParser(description='ICS Stats App Backend')
parser.add_argument('-l', '--local', action='store_true', help='Use local LLM for analysis.')
parser.add_argument('-o', '--online', action='store_true', help='Use online LLM (Gemini) for analysis.')
parser.add_argument('--gemini-api-key', type=str, help='Your Gemini API key.')
args = parser.parse_args()

# --- Gemini API Configuration ---
if args.online:
    if not args.gemini_api_key:
        print("Error: --gemini-api-key is required when using --online mode.")
        exit(1)
    genai.configure(api_key=args.gemini_api_key)

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.py.log"),
    ]
)
# --- End Logging Configuration ---

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=100 * 1024 * 1024)

def is_overseas_travel_online(summaries):
    if not summaries:
        return []

    try:
        prompt = (
            "Analizza i seguenti eventi del calendario e determina per ognuno se si tratta di un viaggio all'estero. "
            "Io vivo a Bristol(UK). Rispondi solo con 'si' o 'no' per ogni evento, in una lista ordinata.\n\n"
            "Regole:\n"
            "- Se l'evento è in una città del Regno Unito (es. Londra, Bristol), rispondi 'no'.\n"
            "- Se si tratta di una visita di parenti o amici a me nel Regno Unito, rispondi 'no'.\n"
            "- Se si tratta di un viaggio di qualcun altro, tipo Erika, rispondi 'no'.\n"
            "- Se l'evento è stato annullato o cancellato, rispondi 'no'.\n"
            "- Se l'evento implica un mio viaggio fuori dal Regno Unito, rispondi 'si'.\n\n"
            "Eventi da analizzare:\n"
        )
        for i, summary in enumerate(summaries):
            prompt += f"{i+1}. {summary}\n"

        logging.info(f"Gemini prompt:\n---\n{prompt}\n---")

        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)

        logging.info(f"Gemini response:\n---\n{response.text}\n---")

        # Extracting the text and splitting into a list of 'si' or 'no'
        results_text = response.text.strip().lower().split('\n')
        results = [line.split('. ')[1] for line in results_text if '. ' in line]

        return [res == 'si' for res in results]

    except Exception as e:
        logging.error(f"An unexpected error occurred during online analysis: {e}", exc_info=True)
        return [False] * len(summaries)

def is_overseas_travel(summary):
    if not summary:
        return False

    try:
        prompt = (f"Devo capire se un evento del mio calendario indica un mio viaggio "
                  f"all'estero. Io vivo in Inghilterra. Regole: "
                  f"- Se e' in una citta' UK (es. Londra, Bristol), rispondi no "
                  f"- Se e' una visita di parenti o amici a me in UK, rispondi no "
                  f"- Se e' un evento annullato o cancellato, rispondi no "
                  f"- Se io viaggio fuori dal Regno Unito, rispondi si. "
                  f"Rispondi solo con si o no. Evento: {summary}")
        command = [
            "D:/Coding/ics-stats-app/LLM/llama-b5904-bin-win-cuda-12.4-x64/llama-cli.exe",
            "-m", "D:/Coding/ics-stats-app/LLM/model/phi-2/Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf",
            "-st",
            "-p", f'"{prompt}"'
        ]
        
        llama_cli_dir = "D:/Coding/ics-stats-app/LLM/llama-b5904-bin-win-cuda-12.4-x64"
        

        process = subprocess.Popen(
            command,
            cwd=llama_cli_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            stdin=subprocess.DEVNULL
        )

        try:
            stdout, stderr = process.communicate(timeout=300) # 5 minutes timeout
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            logging.error(f"llama-cli.exe process timed out after 300 seconds for summary: '{summary}'")
            return False
        returncode = process.returncode
        
        
        
        full_stdout = stdout.strip() if stdout else ""
        full_stderr = stderr.strip() if stderr else ""

        if returncode != 0:
            logging.error(f"Error running llama-cli.exe: Process returned non-zero exit code {returncode}. Stderr: {full_stderr}")
            return False

        is_travel = False
        decision_reason = "No clear 'sì' or 'no' answer found in LLM output."

        raw_output = full_stdout.strip()
        answer = "unknown"
        try:
            # Find the part after 'assistant'
            assistant_part = raw_output.split('<|im_start|> assistant')[1]
            # Find the part before '[end of text]'
            answer_part = assistant_part.split('[end of text]')[0]
            answer = answer_part.strip()
        except (IndexError, AttributeError):
            # Fallback for cases where parsing fails or output is not as expected
            answer = raw_output
            logging.warning(f"Could not parse LLM output for '{summary}'. Using raw output: {raw_output}")

        logging.info(f"LLM raw stdout for '{summary}': {answer}")

        output = answer.lower()

        # Check for 'sì' or 'yes' anywhere in the output
        if re.search(r'\bsì\b|\byes\b', output, re.IGNORECASE):
            is_travel = True
            decision_reason = "Found 'sì'/'yes' in LLM output."
        # Check for 'no' anywhere in the output, only if 'sì'/'yes' was not found
        elif re.search(r'\bno\b', output, re.IGNORECASE):
            is_travel = False
            decision_reason = "Found 'no' in LLM output."
        
        # If neither 'sì'/'yes' nor 'no' is found, log a warning
        if not re.search(r'\bsì\b|\byes\b|\bno\b', output, re.IGNORECASE):
            logging.warning(f"LLM output for '{summary}' did not contain a clear 'sì' or 'no'. Output: {output}")

        
        return is_travel

    except Exception as e:
        logging.error(f"An unexpected error occurred while processing summary '{summary}': {e}", exc_info=True)
        return False

@socketio.on('upload')
def handle_upload(data):
    file_content = data['file']
    sid = request.sid
    
    try:
        gcal = Calendar.from_ical(file_content.encode('utf-8'))
        socketio.start_background_task(analyze_calendar, gcal, sid)
    except Exception as e:
        logging.error(f"Failed to parse .ics file: {e}")
        emit('error', {'error': str(e)})

def filter_contained_events(events):
    if not events:
        return []

    # Sort events by duration, descending
    events.sort(key=lambda x: (x[2] - x[1]), reverse=True)

    filtered_events = []
    for i, event in enumerate(events):
        is_contained = False
        for j, other_event in enumerate(events):
            if i == j:
                continue

            # Check if event is contained within other_event
            if other_event[1] <= event[1] and event[2] <= other_event[2]:
                is_contained = True
                break
        
        if not is_contained:
            filtered_events.append(event)
            
    return filtered_events

def merge_overlapping_intervals(intervals):
    if not intervals:
        return []

    # Sort intervals by their start time
    intervals.sort(key=lambda x: x[1]) # Sort by dtstart

    merged = []
    for interval in intervals:
        # interval is (summary, dtstart, dtend)
        current_start = interval[1]
        current_end = interval[2]
        current_summary = interval[0]

        if not merged or merged[-1][2] < current_start:
            # If merged is empty or current interval does not overlap with the last merged one
            merged.append(interval)
        else:
            # There is an overlap, merge with the last interval
            # Take the earlier summary if needed, or just keep the first one
            # For simplicity, we'll just extend the end time of the last merged interval
            merged[-1] = (merged[-1][0], merged[-1][1], max(merged[-1][2], current_end))
    return merged

def analyze_calendar(cal, sid):
    events = [comp for comp in cal.walk() if comp.name == "VEVENT"]
    total_events = len(events)
    
    timeline_events = []
    trip_events_count = 0

    multi_day_events = []
    for component in events:
        summary = component.get("summary", "No Summary").to_ical().decode("utf-8", "ignore").lower()
        dtstart_prop = component.get('dtstart')
        dtend_prop = component.get('dtend')

        if not dtstart_prop or not dtend_prop:
            continue

        dtstart = dtstart_prop.dt
        dtend = dtend_prop.dt

        if isinstance(dtstart, date) and not isinstance(dtstart, datetime):
            dtstart = datetime.combine(dtstart, datetime.min.time())
        if isinstance(dtend, date) and not isinstance(dtend, datetime):
            dtend = datetime.combine(dtend, datetime.min.time())

        # Normalize all datetimes to UTC
        if dtstart.tzinfo is None:
            dtstart = dtstart.replace(tzinfo=timezone.utc)
        else:
            dtstart = dtstart.astimezone(timezone.utc)

        if dtend.tzinfo is None:
            dtend = dtend.replace(tzinfo=timezone.utc)
        else:
            dtend = dtend.astimezone(timezone.utc)

        # If dtend is exactly midnight, subtract a microsecond to make it end on the previous day
        if dtend.hour == 0 and dtend.minute == 0 and dtend.second == 0 and dtend.microsecond == 0:
            dtend -= timedelta(microseconds=1)

        is_multi_day = (dtend - dtstart).days > 0

        if is_multi_day:
            multi_day_events.append((summary, dtstart, dtend))

    if args.online:
        summaries = [event[0] for event in multi_day_events]
        results = is_overseas_travel_online(summaries)
        
        overseas_events = []
        for i, (summary, dtstart, dtend) in enumerate(multi_day_events):
            if results[i]:
                overseas_events.append((summary, dtstart, dtend))
        
        # Merge overlapping events before calculating days and displaying on timeline
        merged_overseas_events = merge_overlapping_intervals(overseas_events)

        for i, (summary, dtstart, dtend) in enumerate(merged_overseas_events):
            timeline_events.append({
                "id": i,
                "content": summary,
                "start": dtstart.isoformat(),
                "end": dtend.isoformat()
            })
    else: # local processing
        overseas_events = []
        for summary, dtstart, dtend in multi_day_events:
            logging.info(f"Analyzing multi-day event: '{summary}'")
            if is_overseas_travel(summary):
                overseas_events.append((summary, dtstart, dtend))

        # Merge overlapping events before calculating days and displaying on timeline
        merged_overseas_events = merge_overlapping_intervals(overseas_events)

        for i, (summary, dtstart, dtend) in enumerate(merged_overseas_events):
            timeline_events.append({
                "id": i,
                "content": summary,
                "start": dtstart.isoformat(),
                "end": dtend.isoformat()
            })
        
    days_last_year, events_last_year = calculate_days_overseas(merged_overseas_events, 1)
    days_last_5_years, events_last_5_years = calculate_days_overseas(merged_overseas_events, 5)
    
    socketio.emit('result', {"timeline": timeline_events, "days_last_year": days_last_year, "events_last_year": events_last_year, "days_last_5_years": days_last_5_years, "events_last_5_years": events_last_5_years}, to=sid)

def calculate_days_overseas(events, years):
    total_days = 0
    relevant_events = []
    now = datetime.now(timezone.utc)
    start_date_limit = now - timedelta(days=365 * years)

    for summary, dtstart, dtend in events:
        # Ensure dtstart and dtend are timezone-aware
        if dtstart.tzinfo is None:
            dtstart = dtstart.replace(tzinfo=timezone.utc)
        if dtend.tzinfo is None:
            dtend = dtend.replace(tzinfo=timezone.utc)

        # Calculate overlap with the last 'years' period
        overlap_start = max(dtstart, start_date_limit)
        overlap_end = min(dtend, now)

        if overlap_start < overlap_end:
            duration = overlap_end - overlap_start
            days_in_period = duration.days
            total_days += days_in_period
            relevant_events.append({
                "content": summary,
                "start": overlap_start.isoformat(),
                "end": overlap_end.isoformat(),
                "days": days_in_period
            })

    return total_days, relevant_events


if __name__ == "__main__":
    if not args.local and not args.online:
        print("Please specify either -l (local) or -o (online) mode.")
    else:
        logging.info("Starting Flask-SocketIO server.")
        socketio.run(app, debug=True, use_reloader=False, port=5001)