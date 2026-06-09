import requests
from bs4 import BeautifulSoup
import urllib.parse
import re

def run_test():
    query = "Adam Sandler"
    escaped_query = urllib.parse.quote(query)
    url = f"https://www.themoviedb.org/search/person?query={escaped_query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8"
    }
    response = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')

    person_id = None
    # Find the first person link that matches the format "/person/\d+"
    for a in soup.find_all("a", href=True):
        href = a["href"]
        match = re.search(r'^/person/(\d+)', href)
        if match:
            person_id = match.group(1)
            print("Found person ID:", person_id, "Href:", href)
            break

    if person_id:
        # Now scrape the person's page
        person_url = f"https://www.themoviedb.org/person/{person_id}"
        print("Fetching person profile:", person_url)
        resp = requests.get(person_url, headers=headers, timeout=10)
        person_soup = BeautifulSoup(resp.text, 'html.parser')
        
        movies = []
        for credit_table in person_soup.find_all("table", class_="credit_group"):
            year_td = credit_table.find("td", class_="year")
            year = year_td.text.strip() if year_td else "k.A."
            if not year or year == "—":
                year = "k.A."
            else:
                year_match = re.search(r'\b(19\d\d|20\d\d)\b', year)
                if year_match:
                    year = year_match.group(1)
                else:
                    year = "k.A."
            
            for row in credit_table.find_all("tr"):
                role_td = row.find("td", class_="role")
                if role_td:
                    link = role_td.find("a", href=True)
                    if link:
                        href = link["href"]
                        match = re.search(r'^/movie/(\d+)', href)
                        if match:
                            tmdb_id = int(match.group(1))
                            title = link.text.strip()
                            movies.append((tmdb_id, title, year))
                
        print(f"\nFound {len(movies)} movie links in filmography:")
        # De-duplicate
        seen = set()
        unique_movies = []
        for m in movies:
            if m[0] not in seen and m[1]:
                seen.add(m[0])
                unique_movies.append(m)
                
        for m in unique_movies[:20]:
            print(f"Movie ID: {m[0]}, Title: '{m[1]}', Year: {m[2]}")
    else:
        print("No person found.")

if __name__ == "__main__":
    run_test()
