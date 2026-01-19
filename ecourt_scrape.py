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
import os

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

                # LISTING THE CNR - FIXED VERSION
                try:
                    # Wait for the case detail section to load
                    wait.until(lambda d: "Registration Date" in d.page_source)
                    time.sleep(1)

                    # Try to find CNR in a specific container first (adjust selector as needed)
                    # Common patterns: look for CNR label or case number field
                    cnr_val = None

                    # Strategy 1: Look for CNR label and extract adjacent value
                    try:
                        cnr_element = driver.find_element(
                            By.XPATH,
                            "//td[contains(text(), 'CNR') or contains(text(), 'Case Number')]/following-sibling::td[1]",
                        )
                        cnr_text = cnr_element.text.strip()
                        match = re.search(r"MHCC[A-Z0-9]{12}", cnr_text)
                        if match:
                            cnr_val = match.group(0)
                    except:
                        pass

                    # Strategy 2: Look in the main case details container only
                    if not cnr_val:
                        try:
                            # Find the case detail container (adjust selector based on actual page structure)
                            case_detail_container = driver.find_element(
                                By.XPATH,
                                "//div[contains(@class, 'case-detail') or contains(@class, 'modal-body') or contains(@id, 'case')]",
                            )
                            container_html = case_detail_container.get_attribute(
                                "innerHTML"
                            )
                            match = re.search(r"MHCC[A-Z0-9]{12}", container_html)
                            if match:
                                cnr_val = match.group(0)
                        except:
                            pass

                    # Strategy 3: Get all visible text elements and find CNR
                    if not cnr_val:
                        try:
                            # Get only currently visible elements
                            visible_elements = driver.find_elements(
                                By.XPATH, "//*[contains(text(), 'MHCC')]"
                            )
                            for elem in visible_elements:
                                if elem.is_displayed():
                                    match = re.search(r"MHCC[A-Z0-9]{12}", elem.text)
                                    if match:
                                        cnr_val = match.group(0)
                                        break
                        except:
                            pass

                    # Fallback: Use case index if no CNR found
                    if not cnr_val:
                        cnr_val = f"CASE_ID_{i+1}"

                    cnr_val = cnr_val.split("(")[0].strip()
                    print(f"Extracted: {cnr_val}", end="\n")

                except Exception as e:
                    print(f"CNR Extraction failed on case {i+1}: {e}")
                    cnr_val = f"ERROR_ID_{i+1}"

                # MASTER DATA EXTRACTION
                try:
                    # Force a wait for the specific TEXT 'Registration Date' to appear
                    wait.until(lambda d: "Registration Date" in d.page_source)
                    time.sleep(1)  # Extra 'settle' time for the slow UI

                    reg_label = driver.find_element(
                        By.XPATH, "//td[contains(., 'Registration Date')]"
                    )
                    reg_date_val = reg_label.find_element(
                        By.XPATH, "./following-sibling::td"
                    ).text.strip()

                    pet_section = driver.find_element(
                        By.XPATH, "//*[contains(text(), 'Petitioner and Advocate')]"
                    )
                    pet_cell = pet_section.find_element(By.XPATH, "./following::td[1]")
                    petitioner_val = pet_cell.text.split("\n")[0].split(")")[-1].strip()

                    print(
                        f"[{i+1}/{num_cases}] MASTER DATA: {petitioner_val} | Registered: {reg_date_val}"
                    )
                except Exception as master_err:
                    print(
                        f"\nMaster Data Error on case {i+1}: Browser timed out on rendering."
                    )
                    petitioner_val, reg_date_val = "Unknown", "Unknown"

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
                                    "petitioner": petitioner_val,
                                    "registration_date": reg_date_val,
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
            filename = "mumbai_court_master_data.csv"
            file_exists = os.path.isfile(filename)
            # Save with 'a' (append) mode
            df.to_csv(filename, mode="a", index=False, header=not file_exists)

            print(f"\nAppended {len(df)} records to {filename}.")
        else:
            print("No data captured to append.")

    finally:
        driver.quit()


if __name__ == "__main__":
    scrape_judicial_data()
