from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
import time
import pandas as pd
import re
import csv

def split_address(address):
    match = re.match(r"(.+?[都道府県])\s*(.+?[市区町村区])\s*([0-9０-９\-丁目番地号]+)?\s*(.*)", address)
    if match:
        return match.groups()
    return ("", "", "", "")

def fetch_store_info(driver, store_url):
    try:
        driver.get(store_url)
        time.sleep(3)

        # 店名
        name = ""
        try:
            name = driver.find_element(By.TAG_NAME, "h1").text.strip()
        except Exception:
            pass

        # 電話番号
        tel = ""
        try:
            tel_candidates = driver.find_elements(By.XPATH, "//*[contains(text(), '0')]")
            for cand in tel_candidates:
                
                match = re.search(r"(0\d{1,4}[-‐ー－]?\d{1,4}[-‐ー－]?\d{3,4})", cand.text)
                if match:
                    tel = match.group(1)
                    break
        except Exception:
            pass

        # 住所
        address = ""
        try:
            labels = driver.find_elements(By.XPATH, "//*[contains(text(), '住所')]")
            for label in labels:
                try:
                    sibling = label.find_element(By.XPATH, "following-sibling::*[1]")
                    addr_candidate = sibling.text.strip()
                    # 住所らしいか簡易チェック（都道府県名が含まれているか）
                    if re.search(r"[都道府県]", addr_candidate):
                        address = addr_candidate
                        break
                except Exception:
                    continue
        except Exception:
            pass

        if not address:
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text
                match = re.search(r"([一-龥]{2,10}[都道府県].{2,50}?[市区町村].{0,30}?[0-9０-９\-丁目番地号\s]{2,30})", body_text)
                if match:
                    address = match.group().strip()
            except Exception:
                pass

        # ホームページURL
        mail = ""
        url = ""
        try:
            homepage_link = driver.find_element(By.XPATH, "//a[contains(text(), 'お店のホームページ') or contains(text(), 'オフィシャルページ')]")
            homepage_href = homepage_link.get_attribute("href")
            if homepage_href:
                url = homepage_href
        except Exception:
            pass

        prefecture, city, block, building = split_address(address)
        ssl = url.startswith("https://") if url else False

        return {
            "店舗名": name,
            "電話番号": tel,
            "メールアドレス": mail,
            "都道府県": prefecture,
            "市区町村": city,
            "番地": block,
            "建物名": building,
            "URL": url,
            "SSL": ssl
        }
    except Exception as e:
        print(f"Error scraping {store_url}: {e}")
        return {}

def get_store_urls(driver):
    base_url = "https://r.gnavi.co.jp/eki/0000136/izakaya/kods00007/rs/"
    driver.get(base_url)
    time.sleep(3)
    store_urls = []
    prev_count = 0
    while len(store_urls) < 50:
        links = driver.find_elements(By.XPATH, "//a[contains(@href, 'https://r.gnavi.co.jp/')]")
        for link in links:
            href = link.get_attribute("href")
            if href and re.match(r"https://r\.gnavi\.co\.jp/[a-z0-9]+/?", href):
                if re.search(r"/info/", href):
                    continue
                href = re.sub(r"([?#].*)$", "", href)
                if not href.endswith("/"):
                    href += "/"
                store_urls.append(href)

        store_urls = list(dict.fromkeys(store_urls))
        if len(store_urls) >= 50 or len(store_urls) == prev_count:
            break
        prev_count = len(store_urls)

        try:
            next_button = driver.find_element(By.LINK_TEXT, ">")
            if not next_button.is_displayed() or not next_button.is_enabled():
                break
            next_button.click()
            time.sleep(3)
        except NoSuchElementException:
            break
    return store_urls[:50]

def main():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--user-agent=Mozilla/5.0")
    driver = webdriver.Chrome(options=options)
    try:
        urls = get_store_urls(driver)
        print(f"取得対象URL数: {len(urls)} 件")
        results = [fetch_store_info(driver, url) for url in urls]
        results = [r for r in results if r]
        df = pd.DataFrame(results)
        df = df.applymap(lambda x: str(x).replace('\n', ' ').replace(',', ' ') if x else "")
        df.to_csv("1-2.csv", index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
        print("✅ 完了しました：1-2.csv が出力されました")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
