import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================
# CONFIGURATION
# ==========================================
# Target URL for the 06:15 PM show
TARGET_URL = "https://in.bookmyshow.com/movies/hyderabad/seat-layout/ET00478890/ALUC/154/20260322"

TELEGRAM_BOT_TOKEN = "8714091099:AAG6tSvocWMfe1n-qkKrne15szBRXdQah6U"
MY_ADMIN_CHAT_ID = "1094319911" 

CHECK_INTERVAL_SECONDS = 60 # 2 minutes to respect anti-bot limits
MAX_CONSECUTIVE_FAILURES = 3

# ==========================================
# TELEGRAM ALERT
# ==========================================
def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": MY_ADMIN_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass

# ==========================================
# SELENIUM SETUP
# ==========================================
def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--log-level=3") 
    return webdriver.Chrome(options=chrome_options)

# ==========================================
# CORE MONITORING LOGIC (DOUBLE SCANNER)
# ==========================================
# ==========================================
# CORE MONITORING LOGIC (PREFIX-PROOF)
# ==========================================
def check_premium_seats(driver):
    """Checks the modal for both Director Choice and exact Gold status."""
    driver.get(TARGET_URL)
    status = {"dc_open": False, "gold_open": False}
    
    try:
        # Wait for the "How many seats?" modal
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'How many seats?')]"))
        )
    except Exception:
        print("Modal didn't load. URL might have expired.")
        return status
        
    time.sleep(2) # Give text time to render

    # 1. Check DIRECTOR CHOICE (Already immune to 3D/IMAX prefixes)
    try:
        dc_xpath = "//*[contains(text(), 'DIRECTOR CHOICE')]/.."
        dc_block = driver.find_element(By.XPATH, dc_xpath).text.upper()
        if "SOLD OUT" not in dc_block:
            status["dc_open"] = True
    except Exception:
        pass 

    # 2. Check EXACT GOLD (Prefix-proof and dot-proof)
    try:
        # Find ALL blocks that contain "GOLD"
        gold_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'GOLD')]/..")
        
        for el in gold_elements:
            block_text = el.text.upper()
            
            # The text looks like: "3D GOLD\n₹395\nAVAILABLE"
            # We split it to look only at the first line
            lines = block_text.split('\n')
            if not lines: 
                continue
                
            category_name = lines[0].strip()
            
            # Check if the category name ENDS with exactly "GOLD"
            if category_name.endswith("GOLD"):
                if "SOLD OUT" not in block_text:
                    status["gold_open"] = True
                break # Found our target Gold, no need to check the dotted one
                
    except Exception as e:
        print(f"Error checking Gold: {e}")

    return status

# ==========================================
# MAIN EXECUTION LOOP
# ==========================================
def main():
    print("Initializing Double-Barrel Sniper...")
    
    startup_msg = (
        "🎯 <b>DOUBLE-BARREL SNIPER ACTIVE</b> 🎯\n\n"
        "Monitoring the <b>10:30 AM</b> show.\n"
        "Tracking targets:\n"
        "1️⃣ DIRECTOR CHOICE\n"
        "2️⃣ UPPER GOLD\n\n"
        "Checking every 2 minutes. May the upgrade odds be in your favor, Commander Sathvik! 🕵️‍♂️🍿"
    )
    send_telegram_alert(startup_msg)
    
    consecutive_failures = 0
    dc_alerted = False
    gold_alerted = False
    
    while True:
        # Exit condition: Both seats have opened and alerted
        if dc_alerted and gold_alerted:
            print("Both Director Choice and Gold targets have been acquired. Exiting script.")
            break

        driver = None
        try:
            driver = setup_driver()
            status = check_premium_seats(driver)
            
            # --- TARGET 1: DIRECTOR CHOICE ---
            if status["dc_open"] and not dc_alerted:
                msg = f"🚨 <b>DIRECTOR CHOICE UNBLOCKED!</b> 🚨\n\nUpgrade your seats NOW for 10:30 AM: {TARGET_URL}"
                send_telegram_alert(msg)
                dc_alerted = True
                print("Director Choice unlocked!")

            # --- TARGET 2: EXACT GOLD ---
            if status["gold_open"] and not gold_alerted:
                msg = f"🚨 <b>TARGET GOLD UNBLOCKED!</b> 🚨\n\nThe exact Gold seats for 10:30 AM are open: {TARGET_URL}"
                send_telegram_alert(msg)
                gold_alerted = True
                print("Gold unlocked!")
            
            # Status logging
            if not status["dc_open"] and not status["gold_open"]:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Both targets still blocked. Checking again in {CHECK_INTERVAL_SECONDS}s.")
            elif status["dc_open"] and not status["gold_open"]:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] DC open, waiting for Gold. Checking again in {CHECK_INTERVAL_SECONDS}s.")
            elif status["gold_open"] and not status["dc_open"]:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Gold open, waiting for DC. Checking again in {CHECK_INTERVAL_SECONDS}s.")

            consecutive_failures = 0 
            
        except Exception as e:
            consecutive_failures += 1
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Connection Error (Wi-Fi down or URL expired). Failure #{consecutive_failures}")
            
            # Send a warning on the 3rd failure just in case Wi-Fi is fine but the URL broke
            if consecutive_failures == MAX_CONSECUTIVE_FAILURES:
                warning_msg = "⚠️ <b>SNIPER WARNING</b>\nFailed 3 times in a row. If your internet is working, the BookMyShow session URL might have expired!"
                send_telegram_alert(warning_msg) 
                
            # NO 'break' COMMAND HERE! 
            # The bot will just keep looping and waiting in the dark until Wi-Fi returns.
                
        finally:
            if driver:
                driver.quit()
                
        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()