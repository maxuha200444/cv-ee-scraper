import os
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
import pandas as pd

# --- Настройки ---
BASE_URL = "https://www.cv.ee/en/job-list"  # Уточним позже
MAX_PAGES = 3  # Сколько страниц спарсить (для теста)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

def fetch_page(url):
    """Загружает страницу и возвращает HTML."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Ошибка загрузки {url}: {e}")
        return None

def parse_jobs(html):
    """Извлекает вакансии из HTML. Селекторы нужно будет уточнить."""
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    # !!! Селекторы-заглушки, заменим после разведки сайта !!!
    cards = soup.select(".job-card, .vacancy-item, article")
    for card in cards:
        title = card.select_one(".job-title, h3, .title")
        company = card.select_one(".company-name, .employer")
        location = card.select_one(".location, .city")
        if not title:
            continue
        jobs.append({
            "title": title.get_text(strip=True),
            "company": company.get_text(strip=True) if company else "N/A",
            "location": location.get_text(strip=True) if location else "N/A",
        })
    return jobs

def main():
    all_jobs = []
    for page in range(1, MAX_PAGES + 1):
        url = BASE_URL if page == 1 else f"{BASE_URL}?page={page}"
        print(f"Загрузка страницы {page}: {url}")
        html = fetch_page(url)
        if not html:
            continue
        jobs = parse_jobs(html)
        print(f"  Найдено вакансий: {len(jobs)}")
        all_jobs.extend(jobs)
        time.sleep(2)  # Вежливая пауза между запросами

    df = pd.DataFrame(all_jobs)
    print(f"Всего собрано: {len(df)}")

    if len(df) < 5:
        sys.exit(f"Слишком мало данных ({len(df)}). Скрипт остановлен.")

    os.makedirs("data", exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    csv_path = f"data/cv_ee_jobs_{date_str}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"CSV сохранён: {csv_path}")

if __name__ == "__main__":
    main()
