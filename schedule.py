import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import os

GROUP_ID = "WCY22KC2S0"
URL = f"https://planzajec.wcy.wat.edu.pl/pl/rozklad?grupa_id={GROUP_ID}"

BLOCK_TIMES = {
    "block1": ("08:00", "09:35"),
    "block2": ("09:50", "11:25"),
    "block3": ("11:40", "13:15"),
    "block4": ("13:30", "15:05"),
    "block5": ("16:00", "17:35"),
    "block6": ("17:50", "19:25"),
    "block7": ("19:40", "21:15"),
}

def load_lecturer_titles():
    lecturer_dict = {}
    file_path = "employees/lista_pracownikow.txt"  

    if not os.path.exists(file_path):
        print(f"Plik {file_path} nie istnieje! Stopnie naukowe nie zostaną dodane.")
        return lecturer_dict

    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            match = re.match(r"(.+?)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)", line)
            if match:
                title = match.group(1).strip()  
                name = match.group(2).strip()   
                surname = match.group(3).strip()  
                lecturer_dict[f"{name} {surname}"] = title  

    return lecturer_dict


def fetch_schedule():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}
    response = requests.get(URL, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Błąd pobierania strony! Kod: {response.status_code}")
    return response.text

def count_total_lessons(lessons):
    """Zlicza łączną liczbę zajęć dla każdego przedmiotu i typu zajęć"""
    total_lessons = {}
    for lesson in lessons:
        key = (lesson["full_subject"], lesson["type_full"])
        if key in total_lessons:
            total_lessons[key] += 1
        else:
            total_lessons[key] = 1
    return total_lessons

def parse_schedule(html, academic_titles):
    soup = BeautifulSoup(html, "html.parser")
    lessons = []

    for lesson in soup.find_all("div", class_="lesson"):
        try:
            date_str = lesson.find("span", class_="date").text.strip()
            block_id = lesson.find("span", class_="block_id").text.strip()
            subject_element = lesson.find("span", class_="name")
            subject_lines = [line.strip() for line in subject_element.stripped_strings]

            if len(subject_lines) < 4:
                continue

            subject_short = subject_lines[0]
            lesson_type = subject_lines[1]
            room = subject_lines[2].replace(",", "").strip()
            lesson_number_match = re.search(r"\[(\d+)\]", subject_lines[3])
            lesson_number = lesson_number_match.group(1) if lesson_number_match else "Brak"
            
            info_element = lesson.find("span", class_="info")
            full_subject_info = info_element.text.strip() if info_element else "Nieznana nazwa"
            full_subject_cleaned = re.sub(r" - \(.+\) - .*", "", full_subject_info).strip()
            
            lecturer_match = re.search(r"- \(.+\) - ((?:dr |prof\. |inż\. )?[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+) ([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)", full_subject_info)
            if lecturer_match:
                lecturer_name = f"{lecturer_match.group(2)} {lecturer_match.group(1)}"
                lecturer_with_title = academic_titles.get(lecturer_name, "") + " " + lecturer_name
            else:
                lecturer_with_title = "-"
            
            lesson_type_full = {
                "(w)": "Wykład",
                "(L)": "Laboratorium",
                "(ć)": "Ćwiczenia",
                "(P)": "Projekt",
                "(inne)": "inne",
            }.get(lesson_type, "Nieznany")
            
            date_obj = datetime.strptime(date_str, "%Y_%m_%d")
            start_time, end_time = BLOCK_TIMES.get(block_id, ("00:00", "00:00"))
            start_datetime = datetime.strptime(start_time, "%H:%M").replace(year=date_obj.year, month=date_obj.month, day=date_obj.day)
            end_datetime = datetime.strptime(end_time, "%H:%M").replace(year=date_obj.year, month=date_obj.month, day=date_obj.day)
            
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
                "lecturer": lecturer_with_title,
            })
        except Exception as e:
            print(f"Błąd parsowania zajęć: {e}")
    
    total_lessons_dict = count_total_lessons(lessons)

    for lesson in lessons:
        key = (lesson["full_subject"], lesson["type_full"])
        lesson["lesson_number"] = f"{lesson['lesson_number']}/{total_lessons_dict.get(key, '?')}" 

    return lessons

def generate_ics(lessons, filename="schedule.ics", group_id = GROUP_ID):
    ics_content = f"BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//scheduleWCY//EN\nCALSCALE:GREGORIAN\nX-WR-CALNAME:{group_id}\n"
    
    for lesson in lessons:
        start = lesson['start'].strftime("%Y%m%dT%H%M%S")
        end = lesson['end'].strftime("%Y%m%dT%H%M%S")
        
        summary = f"{lesson['subject']} {lesson['type']}"
        location = lesson['room']
        description = f"{lesson['full_subject']}\\nRodzaj zajęć: {lesson['type_full']}\\nNr zajęć: {lesson['lesson_number']}\\nProwadzący: {lesson['lecturer']}"
        
        ics_content += f"""BEGIN:VEVENT\nDTSTART:{start}\nDTEND:{end}\nSUMMARY:{summary}\nLOCATION:{location}\nDESCRIPTION:{description}\nEND:VEVENT\n"""
    
    ics_content += "END:VCALENDAR\n"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(ics_content)
    print(f"Plik kalendarza '{group_id}' zapisany jako {filename}")

academic_titles = load_lecturer_titles()
html = fetch_schedule()
lessons = parse_schedule(html, academic_titles)
generate_ics(lessons)
