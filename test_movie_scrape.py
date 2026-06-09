import requests
from bs4 import BeautifulSoup
import urllib.parse
import re

def run_test():
    query = "Batman"
    escaped_query = urllib.parse.quote(query)
    url = f"https://www.themoviedb.org/search?query={escaped_query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8"
    }
    response = requests.get(url, headers=headers, timeout=10)
    print("Status code:", response.status_code)

    soup = BeautifulSoup(response.text, 'html.parser')
    cards = soup.find_all("div", class_="comp:media-card")
    print("Cards found:", len(cards))

    results = []
    for card in cards:
        link = card.find("a", href=True)
        if link:
            href = link["href"]
            match = re.search(r'^/movie/(\d+)', href)
            if match:
                tmdb_id = int(match.group(1))
                title_el = card.find("h2")
                title = title_el.text.strip() if title_el else ""
                if not title:
                    title = link.text.strip()
                try:
                    print(f"Match found: {title} (ID: {tmdb_id})")
                except UnicodeEncodeError:
                    print(f"Match found: {title.encode('ascii', 'ignore').decode()} (ID: {tmdb_id})")
                results.append(tmdb_id)

    print("Total matches found:", len(results))

if __name__ == "__main__":
    run_test()
