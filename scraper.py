import feedparser
import json
import datetime
import os
import hashlib
import re

# 1. 設定檔案路徑與 RSS 來源
DATA_FILE = 'bear_data.json'
RSS_URL = 'https://news.google.com/rss/search?q=熊+出没+when:1d&hl=ja&gl=JP&ceid=JP:ja'

# 2. 簡易座標對照表 (實際專案建議接 Google Maps API 或 Nominatim)
PREFECTURE_COORDS = {
    "北海道": {"lat": 43.066666, "lng": 141.35},
    "札幌":   {"lat": 43.061771, "lng": 141.354506},
    "青森":   {"lat": 40.822222, "lng": 140.7475},
    "岩手":   {"lat": 39.703611, "lng": 141.156389},
    "宮城":   {"lat": 38.268222, "lng": 140.869417},
    "秋田":   {"lat": 39.716667, "lng": 140.1025},
    "山形":   {"lat": 38.255556, "lng": 140.339722},
    "福島":   {"lat": 37.760833, "lng": 140.474722},
    "長野":   {"lat": 36.648056, "lng": 138.194722},
    "新潟":   {"lat": 37.902222, "lng": 139.023611},
    "富山":   {"lat": 36.695278, "lng": 137.211389},
    "石川":   {"lat": 36.594444, "lng": 136.625556},
    "福井":   {"lat": 36.064722, "lng": 136.219444},
    "群馬":   {"lat": 36.390556, "lng": 139.060278},
    "栃木":   {"lat": 36.565833, "lng": 139.883611}
}

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

def get_coordinates(text):
    """
    從標題或描述中提取地名並返回座標。
    這是一個簡化版，優先匹配具體城市，再匹配縣。
    """
    for place, coords in PREFECTURE_COORDS.items():
        if place in text:
            # 為了避免所有點都重疊，這裡可以加入微小的隨機偏移 (jitter)
            # 但為了演示清晰，先直接返回中心點
            return coords
    return None # 找不到地點

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
        # 將 struct_time 轉為字串
        pub_date = datetime.datetime(*published[:6]).strftime("%Y-%m-%d %H:%M:%S")
        
        # 簡單過濾：只抓取標題含有「熊」或「クマ」的新聞
        if "熊" not in title and "クマ" not in title:
            continue

        # 嘗試解析地點
        coords = get_coordinates(title)
        
        # 如果找不到地點，預設不加入，或者可以設為日本中心點並標記為「地點未詳」
        if not coords:
            continue 

        # 建立新數據物件
        new_item = {
            "id": hashlib.md5(entry.link.encode()).hexdigest(),
            "title": title,
            "location": "新聞報導地點", # 這裡可以更進階用 NLP 提取
            "lat": coords['lat'],
            "lng": coords['lng'],
            "date": pub_date,
            "link": entry.link,
            "source": entry.source.title if 'source' in entry else "Google News"
        }
        
        new_entries.append(new_item)
        print(f"✅ 發現新目擊: {title} ({pub_date})")

    if new_entries:
        current_data.extend(new_entries)
        save_data(current_data)
        print(f"💾 已更新 {len(new_entries)} 筆資料。")
    else:
        print("💤 沒有發現新資料。")

if __name__ == "__main__":
    update_feed()
