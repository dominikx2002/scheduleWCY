import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

# 🔹 ID grupy i URL
GROUP_ID = "WCY22KC2S0"
URL = f"https://planzajec.wcy.wat.edu.pl/pl/rozklad?grupa_id={GROUP_ID}"

# 🔹 Godziny bloków zajęć
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


# 🔹 Liczenie liczby zajęć dla każdego przedmiotu i typu zajęć
def count_total_lessons(lessons):
    total_lessons = {}
    for lesson in lessons:
        subject_key = (lesson["full_subject"], lesson["type_full"])  # Klucz jako (przedmiot, typ zajęć)
        if subject_key in total_lessons:
            total_lessons[subject_key] += 1
        else:
            total_lessons[subject_key] = 1
    return total_lessons


# 🔹 Parsowanie planu zajęć
def parse_schedule(html):
    soup = BeautifulSoup(html, "html.parser")
    lessons = []

    for lesson in soup.find_all("div", class_="lesson"):
        try:
            date_str = lesson.find("span", class_="date").text.strip()
            block_id = lesson.find("span", class_="block_id").text.strip()

            subject_element = lesson.find("span", class_="name")
            subject_lines = [line.strip() for line in subject_element.stripped_strings]

            if len(subject_lines) < 4:
                print(f"⚠️ Błąd: Zbyt mało danych w {subject_lines}")
                continue

            subject_short = subject_lines[0]  # np. "Nsk"
            lesson_type = subject_lines[1]  # np. "(w)"
            room = subject_lines[2].replace(",", "").strip()  # np. "313 S"

            # 🔹 Wydobycie numeru zajęć - tylko liczba z nawiasu []
            lesson_number_match = re.search(r"\[(\d+)\]", subject_lines[3])
            lesson_number = lesson_number_match.group(1) if lesson_number_match else "Brak"

            # 🔹 Pobieranie pełnej nazwy przedmiotu z "info"
            info_element = lesson.find("span", class_="info")
            full_subject_info = info_element.text.strip() if info_element else "Nieznana nazwa"

            # 🔹 Usunięcie części oznaczającej typ zajęć i prowadzącego z pełnej nazwy przedmiotu
            full_subject_cleaned = re.sub(r" - \(.+\) - .*", "", full_subject_info).strip()

            # 🔹 Pobranie pełnego imienia i nazwiska prowadzącego
            lecturer_match = re.search(r"- \(.+\) - ((?:dr |prof\. |inż\. )?[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+) ([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)", full_subject_info)
            if lecturer_match:
                lecturer = f"{lecturer_match.group(2)} {lecturer_match.group(1)}"  # Imię Nazwisko
            else:
                lecturer = "-"

            # 🔹 Pełna nazwa typu zajęć
            lesson_type_full = {
                "(w)": "Wykład",
                "(L)": "Laboratorium",
                "(ć)": "Ćwiczenia",
                "(P)": "Projekt",
                "(inne)": "inne",
            }.get(lesson_type, "Nieznany")

            # 🔹 Tworzenie daty i czasu zajęć
            date_obj = datetime.strptime(date_str, "%Y_%m_%d")
            start_time, end_time = BLOCK_TIMES.get(block_id, ("00:00", "00:00"))
            start_datetime = datetime.strptime(start_time, "%H:%M").replace(
                year=date_obj.year, month=date_obj.month, day=date_obj.day
            )
            end_datetime = datetime.strptime(end_time, "%H:%M").replace(
                year=date_obj.year, month=date_obj.month, day=date_obj.day
            )

            lessons.append({
                "date": date_str,
                "start": start_datetime,
                "end": end_datetime,
                "subject": subject_short,
                "type": lesson_type,
                "type_full": lesson_type_full,
                "room": room,
                "lesson_number": lesson_number,
                "full_subject": full_subject_cleaned,
                "lecturer": lecturer,
            })

        except Exception as e:
            print(f"⚠️ Błąd parsowania zajęć: {e}")

    # 🔹 Liczenie liczby wszystkich zajęć dla każdego przedmiotu i typu zajęć
    total_lessons_dict = count_total_lessons(lessons)

    # 🔹 Formatowanie numerów zajęć w stylu "1/10" (dla każdego typu osobno)
    for lesson in lessons:
        key = (lesson["full_subject"], lesson["type_full"])
        lesson["lesson_number"] = f"{lesson['lesson_number']}/{total_lessons_dict.get(key, '?')}"

    print(f"✅ Znaleziono {len(lessons)} zajęć.")
    return lessons


# 🔹 Generowanie pliku .ics (kalendarza)
def generate_ics(lessons, filename="schedule.ics"):
    ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//WATplan//EN\nCALSCALE:GREGORIAN\n"

    for lesson in lessons:
        start = lesson['start'].strftime("%Y%m%dT%H%M%S")
        end = lesson['end'].strftime("%Y%m%dT%H%M%S")

        summary = f"{lesson['subject']} {lesson['type']}"
        location = lesson['room']
        description = f"{lesson['full_subject']}\nRodzaj zajęć: {lesson['type_full']}\nNr zajęć: {lesson['lesson_number']}\nProwadzący: {lesson['lecturer']}"

        ics_content += f"""BEGIN:VEVENT
DTSTART:{start}
DTEND:{end}
SUMMARY:{summary}
LOCATION:{location}
DESCRIPTION:{description}
END:VEVENT
"""

    ics_content += "END:VCALENDAR\n"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(ics_content)

    print(f"✅ Plik kalendarza zapisany jako {filename}")


# 🔹 Uruchomienie skryptu
html = fetch_schedule()
lessons = parse_schedule(html)
generate_ics(lessons)
