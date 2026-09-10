import os
import sys
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd

# --- Настройки ---
BASE_URL = "https://www.cv.ee/en/search"  # <-- ПРАВИЛЬНЫЙ URL
MAX_PAGES = 3  # Для теста, потом можно увеличить

def setup_driver():
    """Настраивает Selenium для работы в GitHub Actions (headless)."""
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver

def parse_jobs(html):
    """Извлекает вакансии из HTML."""
    soup = BeautifulSoup(html, "html.parser")
    jobs = []

    # !!! СЕЛЕКТОРЫ НИЖЕ — ВРЕМЕННЫЕ, ИХ НУЖНО ЗАМЕНИТЬ !!!
    # Сейчас они основаны на том, что мы видим на странице cv.ee/en/search:
    # есть ссылки с href="/vacancy/..."
    cards = soup.select("div, article")  # Пока собираем всё, потом уточним

    for card in cards:
        # Ищем ссылку на вакансию
        link = card.select_one("a[href*='/vacancy/']")
        if not link:
            continue

        title = link.get_text(strip=True)
        if not title:
            continue

        # Пытаемся найти компанию и локацию (пока как N/A)
        company = "N/A"
        location = "N/A"

        jobs.append({
            "title": title,
            "company": company,
            "location": location,
            "url": "https://www.cv.ee" + link.get("href", "")
        })

    # Убираем дубликаты по URL
    seen = set()
    unique_jobs = []
    for job in jobs:
        if job["url"] not in seen:
            seen.add(job["url"])
            unique_jobs.append(job)

    return unique_jobs

def main():
    driver = setup_driver()
    all_jobs = []

    try:
        for page in range(1, MAX_PAGES + 1):
            url = BASE_URL if page == 1 else f"{BASE_URL}?page={page}"
            print(f"Загрузка страницы {page}: {url}")
            driver.get(url)

            # Ждём появления ссылок на вакансии
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/vacancy/']"))
                )
            except Exception:
                print(f"  Не дождались загрузки вакансий на странице {page}")
                continue

            time.sleep(3)

            html = driver.page_source
            jobs = parse_jobs(html)
            print(f"  Найдено уникальных вакансий: {len(jobs)}")
            all_jobs.extend(jobs)

            time.sleep(2)

    finally:
        driver.quit()

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
