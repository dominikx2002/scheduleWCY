import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# 🔹 ID grupy i URL (zmień na własne)
GROUP_ID = "WCY22KC2S0"
URL = f"https://planzajec.wcy.wat.edu.pl/pl/rozklad?grupa_id={GROUP_ID}"

# 🔹 Godziny bloków zajęć (z Twojego HTML)
BLOCK_TIMES = {
    "block1": ("08:00", "09:35"),
    "block2": ("09:50", "11:25"),
    "block3": ("11:40", "13:15"),
    "block4": ("13:30", "15:05"),
    "block5": ("16:00", "17:35"),
    "block6": ("17:50", "19:25"),
    "block7": ("19:40", "21:15"),
}

# 🔹 Pobieranie strony
def fetch_schedule():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    
    response = requests.get(URL, headers=headers)
    if response.status_code != 200:
        raise Exception(f"❌ Błąd pobierania strony! Kod: {response.status_code}")

    return response.text

# 🔹 Parsowanie danych
def parse_schedule(html):
    soup = BeautifulSoup(html, 'html.parser')
    lessons = []

    # 🔹 Znalezienie wszystkich zajęć
    for lesson in soup.find_all("div", class_="lesson"):
        date_str = lesson.find("span", class_="date").text.strip()  # Data zajęć w formacie YYYY_MM_DD
        block_id = lesson.find("span", class_="block_id").text.strip()  # Numer bloku np. "block3"
        subject_info = lesson.find("span", class_="info").text.strip()  # Pełna nazwa zajęć + prowadzący
        
        # 🔹 Przetwarzanie daty i godzin
        try:
            date_obj = datetime.strptime(date_str, "%Y_%m_%d")
            start_time, end_time = BLOCK_TIMES.get(block_id, ("00:00", "00:00"))
            start_datetime = datetime.strptime(start_time, "%H:%M").replace(year=date_obj.year, month=date_obj.month, day=date_obj.day)
            end_datetime = datetime.strptime(end_time, "%H:%M").replace(year=date_obj.year, month=date_obj.month, day=date_obj.day)
        except ValueError:
            continue  # Pomijamy błędne wartości

        # 🔹 Dodanie zajęć do listy
        lessons.append({
            "date": date_str,
            "start": start_datetime,
            "end": end_datetime,
            "subject": subject_info
        })

    print(f"✅ Znaleziono {len(lessons)} zajęć.")
    return lessons

# 🔹 Generowanie pliku iCalendar (.ics)
def generate_ics(lessons, filename="schedule.ics"):
    ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//WATplan//EN\nCALSCALE:GREGORIAN\n"

    for lesson in lessons:
        start = lesson['start'].strftime("%Y%m%dT%H%M%S")
        end = lesson['end'].strftime("%Y%m%dT%H%M%S")
        summary = lesson['subject']

        ics_content += f"""BEGIN:VEVENT
DTSTART:{start}
DTEND:{end}
SUMMARY:{summary}
END:VEVENT
"""

    ics_content += "END:VCALENDAR\n"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(ics_content)
    
    print(f"✅ Plik kalendarza zapisany jako {filename}")

# 🔹 Wykonanie skryptu
html = fetch_schedule()
lessons = parse_schedule(html)
generate_ics(lessons)
