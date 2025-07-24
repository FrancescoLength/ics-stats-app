import os
from datetime import timedelta, date, datetime, timezone
import argparse
import logging
import google.generativeai as genai
from flask import Flask, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from icalendar import Calendar

# --- Argument Parser Configuration ---
parser = argparse.ArgumentParser(description='ICS Stats App Backend')
parser.add_argument('--gemini-api-key', type=str, required=True, help='Your Gemini API key.')
args = parser.parse_args()

# --- Gemini API Configuration ---
gemini_api_key = os.getenv('GEMINI_API_KEY') or args.gemini_api_key

if not gemini_api_key:
    print("Error: --gemini-api-key is required.")
    exit(1)
genai.configure(api_key=gemini_api_key)

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


def is_work_related_event(event_names):
    if not event_names:
        return []

    try:
        prompt = (
            "You are a knowledgeable event analyst with a keen understanding of business naming conventions and event categorization.\n"
            "Your task is to evaluate a list of event names to determine whether each name is likely associated with a company name.\n\n"
            "Please respond with a list that includes the same event name followed by 'si' or 'no'. Do not include any additional explanations.\n"
            "---\n\n"
            "Your response should be formatted like this:\n"
            "- [Nome Evento 1]: si/no\n"
            "- [Nome Evento 2]: si/no\n"
            "- [Nome Evento 3]: si/no\n"
            "- [Nome Evento 4]: si/no\n"
            "- [Nome Evento 5]: si/no\n"
            "---\n\n"
            "Ensure that your evaluation considers the common characteristics of company names. The events has in the tittle only the name of the company not else. Pay attention to any potential ambiguities in the names provided.\n"
            "---\n\n"
            "Example of how to respond:\n"
            "- Google: si\n"
            "- Yoga: no\n"
            "- Coca-Cola: si\n"  
            "- Microsoft: si\n"
            "---\n\n"
            "Here is the list to evaluate:\n\n"
        )
        for name in event_names:
            prompt += f"- {name}\n"

        logging.info(f"Gemini work-related prompt:\n---\n{prompt}\n---")

        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)

        logging.info(f"Gemini work-related response:\n---\n{response.text}\n---")

        # Parse the response to get a list of work-related event names
        work_event_names = []
        for line in response.text.strip().split('\n'):
            if line.endswith(': si') or line.endswith(', SI'):
                # Extract the event name, removing the leading "- " and trailing ": sì"
                event_name = line.split(':')[0].strip().lstrip('- ').strip()
                work_event_names.append(event_name.lower())
        
        return work_event_names

    except Exception as e:
        logging.error(f"An unexpected error occurred during work-related analysis: {e}", exc_info=True)
        return []


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
    
    # --- Work Time Analysis ---
    summary_counts = {}
    summary_total_durations = {}
    
    for component in events:
        summary = component.get("summary", "No Summary").to_ical().decode("utf-8", "ignore").lower()
        dtstart_prop = component.get('dtstart')
        dtend_prop = component.get('dtend')

        if not dtstart_prop or not dtend_prop:
            continue

        dtstart = dtstart_prop.dt
        dtend = dtend_prop.dt

        # Normalize datetimes (similar to citizenship analysis)
        if isinstance(dtstart, date) and not isinstance(dtstart, datetime):
            dtstart = datetime.combine(dtstart, datetime.min.time())
        if isinstance(dtend, date) and not isinstance(dtend, datetime):
            dtend = datetime.combine(dtend, datetime.min.time())

        if dtstart.tzinfo is None: dtstart = dtstart.replace(tzinfo=timezone.utc)
        else: dtstart = dtstart.astimezone(timezone.utc)

        if dtend.tzinfo is None: dtend = dtend.replace(tzinfo=timezone.utc)
        else: dtend = dtend.astimezone(timezone.utc)

        # If dtend is exactly midnight, subtract a microsecond to make it end on the previous day
        if dtend.hour == 0 and dtend.minute == 0 and dtend.second == 0 and dtend.microsecond == 0:
            dtend -= timedelta(microseconds=1)

        duration = dtend - dtstart

        summary_counts[summary] = summary_counts.get(summary, 0) + 1
        summary_total_durations[summary] = summary_total_durations.get(summary, timedelta()) + duration

    potential_work_events = []
    for summary, count in summary_counts.items():
        if count > 1 and summary_total_durations.get(summary, timedelta()) >= timedelta(hours=24):
            potential_work_events.append(summary)

    logging.info(f"Found potential work events (count > 1 and total duration >= 24 hours): {potential_work_events}")

    work_event_names = is_work_related_event(potential_work_events)

    work_time_info = calculate_work_time(events, work_event_names)

    # --- Citizenship Analysis (existing logic) ---
    timeline_events = []
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

        if dtstart.tzinfo is None: dtstart = dtstart.replace(tzinfo=timezone.utc)
        else: dtstart = dtstart.astimezone(timezone.utc)

        if dtend.tzinfo is None: dtend = dtend.replace(tzinfo=timezone.utc)
        else: dtend = dtend.astimezone(timezone.utc)

        if dtend.hour == 0 and dtend.minute == 0 and dtend.second == 0 and dtend.microsecond == 0:
            dtend -= timedelta(microseconds=1)

        if (dtend - dtstart).days > 0:
            multi_day_events.append((summary, dtstart, dtend))

    travel_summaries = [event[0] for event in multi_day_events]
    travel_results = is_overseas_travel_online(travel_summaries)

    overseas_events = []
    for i, (summary, dtstart, dtend) in enumerate(multi_day_events):
        if travel_results[i]:
            overseas_events.append((summary, dtstart, dtend))

    merged_overseas_events = merge_overlapping_intervals(overseas_events)

    for i, (summary, dtstart, dtend) in enumerate(overseas_events):
        timeline_events.append({
            "id": i,
            "content": summary,
            "start": dtstart.isoformat(),
            "end": dtend.isoformat()
        })

    citizenship_info = calculate_citizenship_eligibility(merged_overseas_events)

    # --- Emit results ---
    socketio.emit('result', {
        "timeline": timeline_events,
        "citizenship_info": citizenship_info,
        "working_time_info": work_time_info
    }, to=sid)

def calculate_citizenship_eligibility(events):
    now = datetime.now(timezone.utc)
    
    # Calculate days overseas in the last 1 and 5 years
    days_last_year, _ = calculate_days_overseas(events, 1)
    days_last_5_years, _ = calculate_days_overseas(events, 5)

    # Citizenship rule limits
    limit_last_year = 90
    limit_last_5_years = 450

    # Calculate remaining days
    remaining_days_last_year = limit_last_year - days_last_year
    remaining_days_last_5_years = limit_last_5_years - days_last_5_years

    # Calculate the date to return to meet the requirements
    return_date_1_year = now + timedelta(days=days_last_year - limit_last_year) if days_last_year > limit_last_year else None
    return_date_5_years = now + timedelta(days=days_last_5_years - limit_last_5_years) if days_last_5_years > limit_last_5_years else None

    # Determine the latest return date required
    final_return_date = None
    if return_date_1_year and return_date_5_years:
        final_return_date = max(return_date_1_year, return_date_5_years)
    elif return_date_1_year:
        final_return_date = return_date_1_year
    elif return_date_5_years:
        final_return_date = return_date_5_years
        
    return {
        "days_last_year": days_last_year,
        "limit_last_year": limit_last_year,
        "remaining_days_last_year": remaining_days_last_year,
        "days_last_5_years": days_last_5_years,
        "limit_last_5_years": limit_last_5_years,
        "remaining_days_last_5_years": remaining_days_last_5_years,
        "return_date": final_return_date.isoformat() if final_return_date else None
    }

def calculate_work_time(events, work_event_names):
    work_events = {}
    for event in events:
        summary = event.get("summary", "No Summary").to_ical().decode("utf-8", "ignore").lower()
        if summary in work_event_names:
            dtstart_prop = event.get('dtstart')
            dtend_prop = event.get('dtend')

            if not dtstart_prop or not dtend_prop:
                continue

            dtstart = dtstart_prop.dt
            dtend = dtend_prop.dt

            if isinstance(dtstart, date) and not isinstance(dtstart, datetime):
                dtstart = datetime.combine(dtstart, datetime.min.time())
            if isinstance(dtend, date) and not isinstance(dtend, datetime):
                dtend = datetime.combine(dtend, datetime.min.time())

            duration = dtend - dtstart
            if summary not in work_events:
                work_events[summary] = timedelta()
            work_events[summary] += duration

    # Format the results
    formatted_work_time = {}
    for name, total_duration in work_events.items():
        days = total_duration.days
        hours, remainder = divmod(total_duration.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        years, days = divmod(days, 365)
        months, days = divmod(days, 30)

        formatted_duration = []
        if years > 0:
            formatted_duration.append(f"{years} {'year' if years == 1 else 'years'}")
        if months > 0:
            formatted_duration.append(f"{months} {'month' if months == 1 else 'months'}")
        if days > 0:
            formatted_duration.append(f"{days} {'day' if days == 1 else 'days'}")
        if hours > 0:
            formatted_duration.append(f"{hours} {'hour' if hours == 1 else 'hours'}")
        if minutes > 0:
            formatted_duration.append(f"{minutes} {'minute' if minutes == 1 else 'minutes'}")

        formatted_work_time[name.capitalize()] = ", ".join(formatted_duration) if formatted_duration else "0 minutes"

    return formatted_work_time

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
    logging.info("Starting Flask-SocketIO server.")
    socketio.run(app, debug=True, use_reloader=False, port=5001)