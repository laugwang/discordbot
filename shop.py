import pandas as pd
import os
import re
import time
from urllib.parse import quote
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import config


def parse_price(text):
    if not text:
        return None
    text = text.strip().replace(",", "")
    try:
        if '萬' in text:
            match = re.match(r'([\d.]+)', text)
            if match:
                return int(float(match.group(1)) * 10000)
        else:
            match = re.search(r'\d+', text)
            if match:
                return int(match.group(0))
    except:
        return None
    return None

def run_crawler():
    df = pd.DataFrame(columns=['關鍵字', '品名', '單價', '庫存', '瀏覽數', '連結'])
    os.makedirs("error_pages", exist_ok=True)

    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 無視窗模式

    service = Service('chromedriver.exe')
    driver = webdriver.Chrome(service=service, options=chrome_options)

    for name in config.kw:  # 每次執行時直接讀最新的 kw
        encoded_name = quote(name.encode('utf-8'))
        url = f"https://www.8591.com.tw/mallList-list.html?searchGame=859&searchServer=944&searchKey={encoded_name}&priceSort=1"
        print("🔍 爬取中:", name, "=>", url)
        time.sleep(2)
        try:
            driver.get(url)
            time.sleep(2)

            while True:
                last_height = driver.execute_script("return document.body.scrollHeight")
                while True:
                    driver.execute_script("window.scrollBy(0, 1500);")
                    time.sleep(2)
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height

                items = driver.find_elements(By.CLASS_NAME, "list-item")
                if not items:
                    df = pd.concat([df, pd.DataFrame({
                        '關鍵字': [name],
                        '品名': ['無'],
                        '單價': ['無'],
                        '庫存': ['無'],
                        '瀏覽數': ['無'],
                        '連結': [driver.current_url]
                    })], ignore_index=True)
                    break

                for item in items:
                    try:
                        title = item.find_element(By.CLASS_NAME, "show-title").text
                        link_tag = item.find_element(By.CLASS_NAME, "list-item-title-txt")
                        href = link_tag.get_attribute('href') if link_tag else ''
                        link = href if href.startswith('http') else f"https://www.8591.com.tw{href}"

                        price_text = item.find_element(By.CLASS_NAME, "list-item-price").text
                        price_parsed = parse_price(price_text)
                        price = price_parsed if price_parsed is not None else '無'

                        count_tag = item.find_element(By.CLASS_NAME, "list-item-count")
                        count_inner = count_tag.find_element(By.TAG_NAME, "div") if count_tag else None
                        count = count_inner.text.strip() if count_inner else '無'

                        view_tag = item.find_element(By.CLASS_NAME, "list-item-view")
                        view_text = view_tag.text.strip() if view_tag else '無'
                        view_parsed = parse_price(view_text)
                        view = view_parsed if view_parsed is not None else '無'

                        df = pd.concat([df, pd.DataFrame({
                            '關鍵字': [name],
                            '品名': [title],
                            '單價': [int(price) if price not in ['無', None] else '無'],
                            '庫存': [int(count) if count not in ['無', None] else '無'],
                            '瀏覽數': [int(view) if view not in ['無', None] else '無'],
                            '連結': [link]
                        })], ignore_index=True)
                    except Exception as e:
                        print(f"❌ 錯誤：{name} => {e}")
                        continue

                try:
                    next_btn = driver.find_element(By.CSS_SELECTOR, "a.next01")
                    if next_btn and next_btn.is_displayed() and next_btn.is_enabled():
                        href_attr = next_btn.get_attribute('href')
                        if href_attr and 'javascript:;' in href_attr:
                            next_btn.click()
                            time.sleep(2)
                            continue
                except Exception:
                    pass
                break

        except Exception as e:
            print(f"❌ 錯誤：{name} => {e}")
            with open(f"error_pages/error_{name}.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            df = pd.concat([df, pd.DataFrame({
                '關鍵字': [name],
                '品名': ['錯誤'],
                '單價': ['錯誤'],
                '庫存': ['錯誤'],
                '瀏覽數': ['錯誤'],
                '連結': [url]
            })], ignore_index=True)

    driver.quit()
    df.to_csv("result.csv", encoding="utf-8-sig", index=False)
    print("✅ 完成，結果已儲存為 result.csv")
