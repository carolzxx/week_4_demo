import os
import time
import requests
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
from duckduckgo_search.exceptions import DuckDuckGoSearchException

# Directory to save results
RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

def fetch_and_save_webpage(url, filename):
    """
    Fetches the content of a webpage and saves it to the results directory.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)

        # Extract text content using BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        page_text = soup.get_text()

        # Save to file
        file_path = os.path.join(RESULTS_DIR, filename)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(page_text)

        print(f"✅ Saved: {file_path}")
        return file_path

    except requests.RequestException as e:
        print(f"❌ Error fetching {url}: {e}")
        return None

def search_and_save(query):
    """
    Searches DuckDuckGo for 3 URLs based on a query and saves their content.
    """
    print(f"🔍 Searching DuckDuckGo for: {query}")
    results = []

    try:
        with DDGS() as ddgs:
            # Add a small delay before making the request
            time.sleep(5)
            search_results = list(ddgs.text(query, max_results=3))

            if not search_results:
                print("⚠️ No results found.")
                return

            for idx, result in enumerate(search_results):
                url = result.get("href", "")
                if not url:
                    continue

                filename = f"{query.replace(' ', '_')}_{idx + 1}.txt"
                saved_path = fetch_and_save_webpage(url, filename)

                if saved_path:
                    results.append({"title": result.get("title", "No Title"), "link": url, "file": saved_path})

    except DuckDuckGoSearchException as e:
        if "Ratelimit" in str(e):
            print("⏳ Rate limit hit! Please try again later.")
        else:
            print(f"❌ Search error: {e}")

    return results

if __name__ == "__main__":
    query = input("Enter your search query: ")
    search_and_save(query)
