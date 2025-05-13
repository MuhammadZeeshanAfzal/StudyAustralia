import time
import json
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver import ChromeOptions

# --------------------- Setup ---------------------
options = ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--disable-browser-side-navigation")
options.page_load_strategy = 'eager'

driver_path = r"D:\Web_Scraping\StudyAustralia\driver\chromedriver-win64\chromedriver.exe"
service = Service(driver_path)
driver = webdriver.Chrome(service=service, options=options)
driver.set_page_load_timeout(30)
wait = WebDriverWait(driver, 10)

CSV_PATH = r"D:\Web_Scraping\StudyAustralia\study_australia_courses2.csv"
JSON_PATH = r"D:\Web_Scraping\StudyAustralia\study_australia_courses2.json"
all_records = []

# --------------------- Helper ---------------------
def get_text(xpath: str, timeout: int = 5) -> str:
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        return el.text.strip().replace("\n", " ").replace("\t", " ")
    except (NoSuchElementException, TimeoutException):
        return "NaN"

def get_additional_details() -> list:
    details = {
        "Course Detail":    get_text(r'//*[@id="main-content"]/div/div[2]/div[1]/p[1]'),
        "Qualification":    get_text(r'//*[@id="main-content"]/div/div[2]/div[1]/p[2]').replace("Qualification:", "").strip(),
        "Course Structure": get_text(r'//*[@id="main-content"]/div/div[2]/div[1]/p[3]').replace("Course structure:", "").strip(),
    }

    # Expand details
    button_xpath = r'//*[@id="main-content"]/div/div[2]/div[1]/div/div[1]/div/button'
    try:
        btn = wait.until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
        driver.execute_script("arguments[0].scrollIntoView();", btn)
        btn.click()
        time.sleep(1)
    except Exception:
        return [{**details,
                 "CRICOS Code": "NaN",
                 "Attendance Option": "NaN",
                 "Tuition Cost": "NaN",
                 "Full Address": "NaN",
                 "CRICOS Count": 0
                }]

    # Dynamically locate all CRICOS strong tags to count entries
    entries_xpath = r'//*[@id="main-content"]/div/div[2]/div[1]/div/div[1]/div[2]/div/div/div/div/div[1]/p[1]/strong'
    cricos_elements = driver.find_elements(By.XPATH, entries_xpath)
    cricos_count = len(cricos_elements)
    print(f"ℹ️  Found {cricos_count} CRICOS entries (strong tags) in expanded section.")

    records = []
    # Iterate only the number of found CRICOS entries
    for idx in range(1, cricos_count + 1):
        base = f'//*[@id="main-content"]/div/div[2]/div[1]/div/div[1]/div[2]/div/div/div[{idx}]/div/div[1]'
        cricos    = get_text(base + '/p[1]').replace("CRICOS Code:", "").strip()
        addr1     = get_text(base + '/p[4]')
        addr2     = get_text(base + '/p[5]')
        addr3     = get_text(base + '/p[6]')
        attendance= get_text(base + '/ul/li/p')
        tuition   = get_text(base + '/p[9]').replace("Estimated total course cost:", "").strip()

        records.append({**details,
                        "CRICOS Code": cricos or "NaN",
                        "Attendance Option": attendance or "NaN",
                        "Tuition Cost": tuition or "NaN",
                        "Full Address": " ".join(p for p in [addr1, addr2, addr3] if p and p != "NaN"),
                        "CRICOS Count": cricos_count
                       })

    # If none valid, return placeholder
    return records or [{**details,
                        "CRICOS Code": "NaN",
                        "Attendance Option": "NaN",
                        "Tuition Cost": "NaN",
                        "Full Address": "NaN",
                        "CRICOS Count": 0
                       }]

# --------------------- Main Loop (Pages 1 to 100) ---------------------
for page in range(201, 301):
    url = f"https://search.studyaustralia.gov.au/courses?page={page}"
    print(f"📄 Scraping Page {page} - {url}")
    driver.get(url)
    wait.until(EC.presence_of_element_located((By.ID, "app")))

    page_records = []
    for i in range(1, 11):
        base = f'//*[@id="app"]/main/div/div/div[{i}]'
        try:
            course     = get_text(base + '/div/div[2]/h3/strong/a')
            institute  = get_text(base + '/div/div[2]/a')
            branch     = get_text(base + '/div/div[2]/p[1]')
            duration   = get_text(base + '/div/div[2]/p[2]').replace("Duration:", "").strip()
            cost       = get_text(base + '/div/div[2]/p[3]').replace("Estimated total course cost:", "").strip()
            start_date = get_text(base + '/div/div[2]/p[4]').replace("Start date:", "").strip()

            learn_more_xpath = base + '/div/div[2]/ul/li[2]/a'
            link = wait.until(EC.element_to_be_clickable((By.XPATH, learn_more_xpath)))
            driver.execute_script("arguments[0].scrollIntoView();", link)
            link.click()
            wait.until(EC.presence_of_element_located((By.ID, "main-content")))

            entries = get_additional_details()

            driver.execute_script("window.history.go(-1)")
            wait.until(EC.presence_of_element_located((By.ID, "app")))

        except Exception as e:
            print(f"⚠️  Course {i} on page {page} failed: {e}")
            entries = [{
                "Course": "NaN", "Institute": "NaN", "Branch": "NaN",
                "Duration": "NaN", "Cost": "NaN", "Start Date": "NaN",
                "Course Detail": "NaN", "Qualification": "NaN", "Course Structure": "NaN",
                "CRICOS Code": "NaN", "Attendance Option": "NaN",
                "Tuition Cost": "NaN", "Full Address": "NaN",
                "CRICOS Count": 0
            }]

        for entry in entries:
            full_entry = {
                "Course": course,
                "Institute": institute,
                "Branch": branch,
                "Duration": duration,
                "Cost": cost,
                "Start Date": start_date,
                **entry
            }
            all_records.append(full_entry)
            page_records.append(full_entry)

    df = pd.DataFrame(page_records)
    df.to_csv(CSV_PATH, mode='w' if page == 1 else 'a', header=(page == 1), index=False, encoding='utf-8')
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    if len(page_records) < 10:
        print(f"ℹ️ Page {page} returned only {len(page_records)} items.")

driver.quit()
print("✅ Scraping complete. Data for pages 1–100 saved.")
