import requests
import time
import pandas as pd
import re
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0"
}

def split_address(address):
    address = address.replace('\u3000', ' ').replace('　', ' ').strip()

    # 都道府県を抽出
    pref_match = re.match(r"^(.+?[都道府県])(.+)$", address)
    if not pref_match:
        return "", "", "", ""
    pref = pref_match.group(1)
    rest = pref_match.group(2).strip()

    # 市区町村を複数連続でまとめて抽出
    city_match = re.match(r"^((?:.+?[市区町村区])+)(.+)?$", rest)
    if not city_match:
        return pref, "", "", ""
    city = city_match.group(1)
    rest_after_city = city_match.group(2).strip() if city_match.group(2) else ""

    # 番地と建物名を分割
    if rest_after_city:
        parts = re.split(r"[ ]+", rest_after_city)
        block = parts[0]
        building = " ".join(parts[1:]) if len(parts) > 1 else ""
    else:
        block = ""
        building = ""

    return pref, city, block, building


# ➤ 店舗の情報を取得
def fetch_store_info(store_url):
    try:
        res = requests.get(store_url, headers=headers)
        res.encoding = res.apparent_encoding  # 文字化け対策
        time.sleep(3)
        soup = BeautifulSoup(res.text, "html.parser")

        # 店名取得
        name = ""
        if soup.find("h1"):  # h1タグ
            name = soup.find("h1").text.strip()
        elif soup.find("h2"):  # h2タグ
            name = soup.find("h2").text.strip()
        elif soup.title:
            name = soup.title.text.strip().split(" - ")[0]

        # 電話番号取得
        tel = ""
        tel_tag = soup.find(string=re.compile(r"\d{2,4}-\d{2,4}-\d{4}"))
        if tel_tag:
            tel = tel_tag.strip()

        # 住所を取得
        address = ""
        address_tag = soup.select_one("span.region")
        building_tag = soup.select_one("span.locality")

        address = address_tag.get_text(strip=True) if address_tag else ""
        building = building_tag.get_text(strip=True) if building_tag else ""

        prefecture, city, block, _ = split_address(address)
        # split_addressの4つ目はbuildingとして扱わないので_にしておく

        return {
            "店舗名": name,
            "電話番号": tel,
            "メールアドレス": "",
            "都道府県": prefecture,
            "市区町村": city,
            "番地": block,
            "建物名": building,
            "URL": "",
            "SSL": ""
        }
    except Exception as e:
        print(f"Error scraping {store_url}: {e}")
        return {}



# 店舗一覧ページから個別店舗ページのURLを収集（ページネーション対応）
def get_store_urls():
    base_url = "https://r.gnavi.co.jp/eki/0000136/izakaya/kods00007/rs/"
    store_urls = []
    page = 1
    while len(store_urls) < 50:
        url = base_url if page == 1 else f"{base_url}?p={page}"
        res = requests.get(url, headers=headers)
        res.encoding = res.apparent_encoding
        time.sleep(3)
        soup = BeautifulSoup(res.text, "html.parser")
        links = soup.find_all("a", href=True)
        for link in links:
            href = link["href"]
            # 店舗詳細ページのみ抽出（10～13桁の英数字IDのみ許可）
            if re.match(r"https://r\.gnavi\.co\.jp/[a-z0-9]{10,13}/$", href):
                store_urls.append(href)
        store_urls = list(dict.fromkeys(store_urls))  # 重複排除
        if len(links) == 0 or len(store_urls) >= 50:
            break
        page += 1
    return store_urls[:50]

# ➤ メイン処理
def main():
    urls = get_store_urls()
    print(f"取得対象URL数: {len(urls)} 件")
    results = [fetch_store_info(url) for url in urls]
    df = pd.DataFrame(results)
    df.to_csv("1-1.csv", index=False, encoding="utf-8-sig")
    print("✅ 完了しました：1-1.csv が出力されました")

if __name__ == "__main__":
    main()