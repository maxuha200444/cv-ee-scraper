import os
import re
import sys
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

print(">>> СБОРЩИК ЧИСЛА ВАКАНСИЙ <<<")

BASE_URL = "https://www.cv.ee/en/search"
HISTORY_FILE = "data/cv_ee_history.csv"


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


def extract_total(driver):
    """Достаёт число из 'Show 3977 job ads' или из заголовка '(3977):'."""
    # Способ 1: кнопка "Show X job ads"
    try:
        btn = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-testid^="search-form-button-show-jobs"]')
            )
        )
        text = btn.text
        print(f"  Текст кнопки: {text!r}")
        match = re.search(r'(\d[\d\s]*)\s*job', text)
        if match:
            return int(match.group(1).replace(" ", ""))
    except Exception as e:
        print(f"  Не нашли кнопку: {e}")

    # Способ 2: заголовок "(3977):"
    try:
        total_elem = driver.find_element(
            By.CSS_SELECTOR, '[data-testid="search-results-total"]'
        )
        text = total_elem.text
        print(f"  Текст заголовка: {text!r}")
        match = re.search(r'(\d[\d\s]*)', text)
        if match:
            return int(match.group(1).replace(" ", ""))
    except Exception as e:
        print(f"  Не нашли заголовок: {e}")

    return None


def main():
    driver = setup_driver()
    total = None

    try:
        print(f"Загрузка: {BASE_URL}")
        driver.get(BASE_URL)
        total = extract_total(driver)
    finally:
        driver.quit()

    if total is None:
        sys.exit("Не удалось извлечь число вакансий.")

    today = datetime.now().strftime("%Y-%m-%d")
    print(f"Сегодня {today}: {total} вакансий")

    # --- Обновляем историю ---
    os.makedirs("data", exist_ok=True)

    if os.path.exists(HISTORY_FILE):
        history = pd.read_csv(HISTORY_FILE)
    else:
        history = pd.DataFrame(columns=["date", "total_jobs"])

    # Убираем сегодняшнюю запись, если уже есть (защита от повторов)
    history = history[history["date"] != today]

    new_row = pd.DataFrame([{"date": today, "total_jobs": total}])
    history = pd.concat([history, new_row], ignore_index=True)
    history = history.sort_values("date").reset_index(drop=True)

    history.to_csv(HISTORY_FILE, index=False, encoding="utf-8-sig")
    print(f"История сохранена: {HISTORY_FILE} ({len(history)} записей)")

    # --- Строим график ---
    if len(history) < 2:
        print("Для графика нужно минимум 2 точки. Пока пропускаем.")
        return

    history["date"] = pd.to_datetime(history["date"])

    plt.figure(figsize=(12, 6))
    plt.plot(history["date"], history["total_jobs"],
             marker="o", linewidth=2, color="steelblue")
    plt.title("CV.ee: количество вакансий по дням")
    plt.xlabel("Дата")
    plt.ylabel("Всего вакансий")
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    plot_path = "data/cv_ee_chart.png"
    plt.savefig(plot_path)
    print(f"График сохранён: {plot_path}")
    print("\nПоследние 5 записей:")
    print(history.tail(5).to_string(index=False))


if __name__ == "__main__":
    main()
