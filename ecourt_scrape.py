from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import pandas as pd
import time
import re

# WSL OPTIONS SETUP
options = webdriver.ChromeOptions()
# options.add_argument("--headless=new") # Debugging only.
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()), options=options
)


def scrape_judicial_data():
    try:
        driver.get("https://services.ecourts.gov.in/ecourtindia_v6/?p=casestatus/index")
        input("\n\nPress enter after the rows are visible.")

        all_hearing_records = []
        wait = WebDriverWait(driver, 16)

        rows = driver.find_elements(
            By.XPATH, "//table[contains(@class, 'table')]//tr[td]"
        )
        num_cases = len(rows)
        print(f"Detected {num_cases} cases.")

        for i in range(num_cases):
            try:
                # Click View button for every case in table
                wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//a[contains(text(), 'View')]")
                    )
                )
                current_view_buttons = driver.find_elements(
                    By.XPATH, "//a[contains(text(), 'View')]"
                )
                target_button = current_view_buttons[i]
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", target_button
                )
                time.sleep(1)
                driver.execute_script("arguments[0].click();", target_button)

                print(f"[{i+1}/{num_cases}] Case opened. Extracting data...", end="")
                time.sleep(3)

                # LISTING THE CNR
                try:
                    # Scan the entire page source for the 16-digit MHCC pattern
                    match = re.search(r"MHCC[A-Z0-9]{12}", driver.page_source)
                    if match:
                        cnr_val = match.group(0)
                        cnr_val = cnr_val.split("(")[0].strip()
                    else:
                        cnr_val = f"CASE_ID_{i+1}"

                    print(f"Extracted: {cnr_val}", end="\n")

                except Exception as e:
                    print(f"CNR Extraction failed on case {i+1}: {e}")
                    cnr_val = f"ERROR_ID_{i+1}"

                # HISTORY TABLE SCRAPING
                try:
                    history_section = driver.find_element(
                        By.XPATH,
                        "//div[contains(@class, 'history_table')] | //table[contains(@class, 'history_table')]",
                    )
                    h_rows = history_section.find_elements(By.TAG_NAME, "tr")
                except:
                    h_rows = driver.find_elements(
                        By.XPATH, "//table[contains(@class, 'history_table')]//tr[td]"
                    )

                case_history_count = 0
                for row in h_rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) == 4:
                        first_col_text = cols[0].text.strip()
                        if first_col_text.lower() != "judge":
                            all_hearing_records.append(
                                {
                                    "cnr_number": cnr_val,
                                    "judge": first_col_text,
                                    "business_date": cols[1].text.strip(),
                                    "hearing_date": cols[2].text.strip(),
                                    "purpose": cols[3].text.strip(),
                                }
                            )
                            case_history_count += 1

                print(f"Captured {case_history_count} rows for CNR: {cnr_val}")

                # BACK NAVIGATION
                try:
                    back_btn = driver.find_element(
                        By.XPATH,
                        "//button[contains(text(), 'Back')] | //input[@value='Back']",
                    )
                    driver.execute_script("arguments[0].click();", back_btn)
                except:
                    driver.execute_script("window.history.go(-1)")

                wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//table[contains(@class, 'table')]")
                    )
                )
                time.sleep(1)

            except Exception as e:
                print(f"Skipping case {i+1} due to error: {e}")
                driver.execute_script("window.history.go(-1)")
                time.sleep(3)
                continue

        # Save
        if all_hearing_records:
            df = pd.DataFrame(all_hearing_records)
            df.to_csv("mumbai_court_history_v2.csv", index=False)
            print(f"Captured {len(df)} records.")
        else:
            print("Array empty.")

    finally:
        driver.quit()


if __name__ == "__main__":
    scrape_judicial_data()
