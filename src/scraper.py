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
BASE_URL = "https://www.cv.ee/en/search"  # Правильный URL
MAX_PAGES = 3  # Для теста, потом можно увеличить

def setup_driver():
    """Настраивает Selenium для работы в GitHub Actions (headless)."""
    options = Options()
    options.add_argument('--headless=new')  # Фоновый режим
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
    """Извлекает вакансии из HTML. ЗАМЕНИТЕ селекторы на реальные!"""
    soup = BeautifulSoup(html, "html.parser")
    jobs = []

    # !!! ЭТИ СЕЛЕКТОРЫ НУЖНО НАЙТИ ЧЕРЕЗ F12 НА САЙТЕ cv.ee !!!
    # Ниже — лишь пример, основанный на фрагменте HTML из результатов поиска.
    # Реальные классы могут отличаться.
    cards = soup.select(".vacancy-item, .job-card, article")  # <-- ЗАМЕНИТЕ

    for card in cards:
        title_elem = card.select_one("a[href*='/vacancy/']")  # Ссылка на вакансию
        company_elem = card.select_one(".employer, .company")  # <-- ЗАМЕНИТЕ
        location_elem = card.select_one(".location, .city")    # <-- ЗАМЕНИТЕ

        if not title_elem:
            continue

        jobs.append({
            "title": title_elem.get_text(strip=True),
            "company": company_elem.get_text(strip=True) if company_elem else "N/A",
            "location": location_elem.get_text(strip=True) if location_elem else "N/A",
            "url": title_elem.get("href", "")
        })
    return jobs

def main():
    driver = setup_driver()
    all_jobs = []

    try:
        for page in range(1, MAX_PAGES + 1):
            url = BASE_URL if page == 1 else f"{BASE_URL}?page={page}"
            print(f"Загрузка страницы {page}: {url}")
            driver.get(url)

            # Ждём, пока на странице появятся карточки вакансий
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/vacancy/']"))
                )
            except Exception:
                print(f"  Не дождались загрузки вакансий на странице {page}")
                continue

            time.sleep(3)  # Дополнительная пауза для подгрузки контента

            html = driver.page_source
            jobs = parse_jobs(html)
            print(f"  Найдено вакансий: {len(jobs)}")
            all_jobs.extend(jobs)

            time.sleep(2)  # Вежливая пауза между страницами

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
