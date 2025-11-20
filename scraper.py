import feedparser
import json
import datetime
import os
import hashlib
import time
import google.generativeai as genai
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

# 1. 設定檔案路徑與 RSS 來源
DATA_FILE = 'bear_data.json'
RSS_URL = 'https://news.google.com/rss/search?q=熊+出没+when:1d&hl=ja&gl=JP&ceid=JP:ja'

# 設定 Gemini API 金鑰 (從 GitHub Secrets 讀取)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 初始化 Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("⚠️ 警告: 未檢測到 GEMINI_API_KEY，將無法進行地點解析。")

def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    # 按日期倒序排列
    data.sort(key=lambda x: x['date'], reverse=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def ask_gemini_for_location(title):
    """
    使用 Gemini AI 從新聞標題中提取最精確的日本地點名稱。
    """
    if not GEMINI_API_KEY:
        return None

    try:
        model = genai.GenerativeModel('gemini-1.5-flash') # 使用較快且便宜的模型
        prompt = f"""
        你是一個日本地理專家。請從以下新聞標題中提取最詳細的「出沒地點」。
        規則：
        1. 只回傳地點名稱（例如：北海道札幌市、秋田県北秋田市）。
        2. 不需要任何解釋或額外文字。
        3. 如果標題中完全沒有具體地點，請回傳 "None"。
        
        新聞標題: {title}
        """
        response = model.generate_content(prompt)
        location_text = response.text.strip()
        
        if "None" in location_text or not location_text:
            return None
        
        # 清理可能多餘的符號
        return location_text.replace("\n", "").replace("。", "")
    except Exception as e:
        print(f"❌ Gemini API 錯誤: {e}")
        return None

def get_coordinates_from_address(address):
    """
    使用 Geopy (OpenStreetMap) 將地址轉換為經緯度
    """
    geolocator = Nominatim(user_agent="bear_map_bot_v1")
    try:
        # 加上 "Japan" 確保搜尋範圍在日本
        location = geolocator.geocode(f"{address}, Japan", timeout=10)
        if location:
            return {"lat": location.latitude, "lng": location.longitude}
    except (GeocoderTimedOut, Exception) as e:
        print(f"⚠️ Geocoding 錯誤 ({address}): {e}")
    return None

def update_feed():
    print(f"🔄 開始抓取新聞: {datetime.datetime.now()}")
    
    current_data = load_data()
    existing_links = {item['link'] for item in current_data}
    
    feed = feedparser.parse(RSS_URL)
    new_entries = []

    for entry in feed.entries:
        # 檢查是否已經存在
        if entry.link in existing_links:
            continue

        title = entry.title
        published = entry.published_parsed
        pub_date = datetime.datetime(*published[:6]).strftime("%Y-%m-%d %H:%M:%S")
        
        # 簡單過濾：只抓取標題含有「熊」或「クマ」的新聞
        if "熊" not in title and "クマ" not in title:
            continue

        print(f"🔍 分析中: {title}")

        # 1. 使用 Gemini 提取地點文字
        extracted_location = ask_gemini_for_location(title)
        
        if not extracted_location:
            print(f"   ⏭️ 跳過: 無法提取地點")
            continue
            
        print(f"   📍 Gemini 提取地點: {extracted_location}")

        # 2. 將地點文字轉為座標
        coords = get_coordinates_from_address(extracted_location)
        
        if not coords:
            print(f"   ❌ 跳過: 找不到該地點的座標")
            continue 

        # 3. 建立新數據物件
        new_item = {
            "id": hashlib.md5(entry.link.encode()).hexdigest(),
            "title": title,
            "location": extracted_location, # 儲存乾淨的地點名稱
            "lat": coords['lat'],
            "lng": coords['lng'],
            "date": pub_date,
            "link": entry.link,
            "source": entry.source.title if 'source' in entry else "Google News"
        }
        
        new_entries.append(new_item)
        print(f"   ✅ 成功加入資料！")
        
        # 禮貌性暫停，避免對 Geocoding API 請求過快
        time.sleep(1)

    if new_entries:
        current_data.extend(new_entries)
        save_data(current_data)
        print(f"💾 已更新 {len(new_entries)} 筆資料。")
    else:
        print("💤 沒有發現新資料。")

if __name__ == "__main__":
    update_feed()
