import requests
from bs4 import BeautifulSoup

BASE_URL = "https://usos.wat.edu.pl/kontroler.php?_action=katalog2/osoby/pracownicyJednostki&jed_org_kod=A000000&page="
OUTPUT_FILE = "employees/pracownicy.html"

html_content = ""
for page in range(1, 54):
    url = BASE_URL + str(page)
    response = requests.get(url)
    if response.status_code == 200:
        html_content += response.text + "\n\n<!-- Strona {} -->\n\n".format(page)
    else:
        print(f"Błąd podczas pobierania strony {page}: {response.status_code}")

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Pobrano strony i zapisano w {OUTPUT_FILE}")

with open("employees/pracownicy.html", "r", encoding="utf-8") as file:
    html_content = file.read()

soup = BeautifulSoup(html_content, "html.parser")

employees = []

for entry in soup.find_all("td", class_="uwb-staffuser-panel"):
    name_tag = entry.find("b")
    degree = entry.find("a", class_="no-badge uwb-photo-panel-title")
    
    if name_tag and degree:
        full_name = name_tag.text.strip()
        degree_text = degree.text.replace(full_name, "").strip()
        employees.append(f"{degree_text} {full_name}")

output_path = "employees/lista_pracownikow.txt"
with open(output_path, "w", encoding="utf-8") as output_file:
    for employee in employees:
        output_file.write(employee + "\n")

print(f"Lista pracowników została zapisana do: {output_path}")