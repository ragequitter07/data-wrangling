from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# WSL OPTIONS SETUP
options = webdriver.ChromeOptions()
# options.add_argument("--headless=new") # Debugging only.
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()), options=options
)


def scout_judicial_data():
    try:
        print("Opening e-courts data site")
        driver.get("https://services.ecourts.gov.in/ecourtindia_v6/?p=casestatus/index")
        input("\n\nPress enter after the rows are visible.")

        # Wait until the table rows actually exist
        print("Scraping table data...")
        wait = WebDriverWait(driver, 20)
        rows = wait.until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//table[contains(@class, 'table')]//tr[td]")
            )
        )

        cases = []
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 4:
                # e-Courts table: [Index, Case No, Petitioner/Respondent, CNR]
                case_data = {
                    "case_no": cols[1].text.strip(),
                    "petitioner_vs_respondent": cols[2].text.strip(),
                    "cnr_number": cols[3].text.strip(),
                }
                cases.append(case_data)

        if not cases:
            print("Warning: Array is still empty. Copying the html.")
            with open("debug_page.html", "w") as f:
                f.write(driver.page_source)
        else:
            print(f"captured {len(cases)} cases!")
            for c in cases[:5]:
                print(
                    f"CNR: {c['cnr_number']} | Names: {c['petitioner_vs_respondent']}"
                )

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    scout_judicial_data()
