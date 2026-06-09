import requests
from bs4 import BeautifulSoup
import re

def scrape_person_credits(person_id, search_filter):
    url = f"https://www.themoviedb.org/person/{person_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8"
    }
    response = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    target_heading = "Darsteller" if search_filter == "Schauspieler" else "Regie"
    results = []
    
    # Try finding the specific heading first
    found_table = False
    for h3 in soup.find_all("h3"):
        if h3.text.strip() == target_heading:
            table = h3.find_next_sibling("table")
            if table:
                found_table = True
                for credit_table in table.find_all("table", class_="credit_group"):
                    year_td = credit_table.find("td", class_="year")
                    year = year_td.text.strip() if year_td else "k.A."
                    if not year or year == "—":
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
                                    results.append({
                                        "tmdb_id": tmdb_id,
                                        "titel": title,
                                        "jahr": year
                                    })
                break
                
    # Fallback to general links if specific table not found
    if not found_table:
        print("Table not found, falling back to general links...")
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            match = re.search(r'^/movie/(\d+)', href)
            if match:
                tmdb_id = int(match.group(1))
                if tmdb_id not in seen:
                    seen.add(tmdb_id)
                    title = a.text.strip()
                    if title:
                        results.append({
                            "tmdb_id": tmdb_id,
                            "titel": title,
                            "jahr": "k.A."
                        })
                        
    return results

if __name__ == '__main__':
    print("=== Christopher Nolan (Regie) ===")
    credits_nolan = scrape_person_credits("525", "Regisseur")
    for c in credits_nolan[:5]:
        print(c)

    print("\n=== Adam Sandler (Darsteller) ===")
    credits_sandler = scrape_person_credits("19292", "Schauspieler")
    for c in credits_sandler[:5]:
        print(c)
