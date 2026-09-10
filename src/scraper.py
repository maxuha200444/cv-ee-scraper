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
import matplotlib
matplotlib.use("Agg")  # Без GUI — обязательно для GitHub Actions
import matplotlib.pyplot as plt

print(">>> ЗАПУЩЕНА ФИНАЛЬНАЯ ВЕРСИЯ <<<")

BASE_URL = "https://www.cv.ee/en/search"


def setup_driver():
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
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )


def parse_jobs(html):
    soup = BeautifulSoup(html, "html.parser")
    jobs = []

    cards = soup.select('li[data-testid^="vacancies-list-item-"]')
    print(f"  Найдено карточек в HTML: {len(cards)}")

    for card in cards:
        title_elem = card.select_one('a[data-testid^="vacancy-item-link-title-"]')
        company_elem = card.select_one('a[data-testid^="vacancy-item-link-employer-"]')
        location_elem = card.select_one('div[data-testid^="vacancy-item-location-"]')
        salary_elem = card.select_one('div[data-testid^="vacancy-item-salary-"]')
        date_elem = card.select_one('div[data-testid^="vacancy-item-date-published-"]')

        if not title_elem:
            continue

        title = title_elem.get_text(strip=True)
        if not title:
            continue

        href = title_elem.get("href", "")
        url = f"https://www.cv.ee{href}" if href.startswith("/") else href

        company = company_elem.get_text(strip=True) if company_elem else "N/A"
        location = location_elem.get_text(strip=True) if location_elem else "N/A"
        salary = salary_elem.get_text(strip=True) if salary_elem else "N/A"
        date_pub = date_elem.get_text(strip=True) if date_elem else "N/A"

        jobs.append({
            "title": title,
            "company": company,
            "location": location,
            "salary": salary,
            "date": date_pub,
            "url": url
        })

    return jobs


def main():
    driver = setup_driver()
    all_jobs = []

    try:
        print(f"Загрузка страницы: {BASE_URL}")
        driver.get(BASE_URL)

        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'li[data-testid^="vacancies-list-item-"]')
                )
            )
        except Exception:
            print("  Не дождались загрузки вакансий")
            os.makedirs("data", exist_ok=True)
            with open("data/debug_page.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            sys.exit("Вакансии не найдены. HTML сохранён в data/debug_page.html")

        time.sleep(3)
        html = driver.page_source
        all_jobs = parse_jobs(html)

    finally:
        driver.quit()

    df = pd.DataFrame(all_jobs)
    print(f"Всего собрано вакансий: {len(df)}")

    if len(df) < 5:
        sys.exit(f"Слишком мало данных ({len(df)}). Скрипт остановлен.")

    os.makedirs("data", exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")

    # --- Сохраняем CSV ---
    csv_path = f"data/cv_ee_jobs_{date_str}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"CSV сохранён: {csv_path}")

    # --- Строим график: топ-10 городов ---
    # Берём первую часть локации до "/" (например, "Tallinn / Hybrid" -> "Tallinn")
    df["city"] = df["location"].str.split("/").str[0].str.strip()
    top_cities = df["city"].value_counts().head(10)

    plt.figure(figsize=(12, 6))
    top_cities.plot(kind="bar", color="skyblue")
    plt.title(f"Top 10 cities by number of vacancies on CV.ee ({date_str})")
    plt.xlabel("City")
    plt.ylabel("Number of vacancies")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    plot_path = f"data/cv_ee_chart_{date_str}.png"
    plt.savefig(plot_path)
    print(f"График сохранён: {plot_path}")

    # --- Сводка по топ-компаниям ---
    print("\nТоп-10 компаний по количеству вакансий:")
    print(df["company"].value_counts().head(10).to_string())


if __name__ == "__main__":
    main()
