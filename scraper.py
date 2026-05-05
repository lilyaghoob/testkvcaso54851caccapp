import requests
from bs4 import BeautifulSoup
import jdatetime
import pytz
from datetime import datetime, timedelta
import time
import os

# تنظیمات زمان
tehran_tz = pytz.timezone('Asia/Tehran')

def get_media_tag(msg_div):
    # جستجوی سراسری در کل بدنه پیام برای پیدا کردن نشانه‌های ویدئو یا عکس
    html_str = str(msg_div).lower()
    
    is_video = any(x in html_str for x in ['video', 'message_video', 'player', 'duration'])
    is_photo = 'photo' in html_str and 'tgme_widget_message_photo_wrap' in html_str
    is_gif = 'videogif' in html_str
    is_doc = 'document' in html_str

    if is_photo and is_video: return "[عکس و ویدئو]"
    if is_gif: return "[گیف]"
    if is_video: return "[ویدئو]"
    if is_photo: return "[عکس]"
    if is_doc: return "[فایل]"
    return ""

def format_text(text):
    if not text: return ""
    rlm = "\u200F"
    lines = text.strip().split('\n')
    return "\n".join([f"{rlm}{line}" for line in lines])

def run_scraper_logic(input_file, output_file):
    if not os.path.exists(input_file):
        print(f"فایل {input_file} یافت نشد.")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        channels = [line.strip().replace('@', '') for line in f if line.strip()]

    all_posts = []
    now_utc = datetime.now(pytz.utc)
    cutoff_time = now_utc - timedelta(hours=24)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    for channel in channels:
        print(f"در حال بررسی کانال: @{channel}...")
        url = f"https://t.me/s/{channel}"
        try:
            res = requests.get(url, headers=headers, timeout=20)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # تغییر استراتژی: پیدا کردن تمام دیوهایی که اتریبیوت data-post دارند
            # این کار باعث می‌شه پست‌های ویدئویی که کلاس‌های متفاوتی دارن هم صید بشن
            messages = soup.find_all('div', {'data-post': True})
            
            for msg in messages:
                # خط قرمزها: نظرسنجی و پیام‌های سیستمی
                if msg.select_one('.tgme_widget_message_poll') or 'tgme_widget_message_service' in msg.get('class', []):
                    continue

                time_tag = msg.select_one('time')
                if not time_tag or not time_tag.has_attr('datetime'):
                    continue
                
                post_dt_utc = datetime.fromisoformat(time_tag['datetime'].replace('Z', '+00:00'))
                if post_dt_utc < cutoff_time:
                    continue

                # استخراج متن با متد منعطف: هر جا که کلاس text یا message_text دیدی بردار
                text_div = msg.find(class_=lambda x: x and ('text' in x or 'js-message_text' in x))
                post_text = ""
                if text_div:
                    for br in text_div.find_all("br"):
                        br.replace_with("\n")
                    post_text = text_div.get_text().strip()

                media_tag = get_media_tag(msg)

                if post_text or media_tag:
                    dt_tehran = post_dt_utc.astimezone(tehran_tz)
                    shamsi_date = jdatetime.datetime.fromgregorian(datetime=dt_tehran)
                    
                    all_posts.append({
                        'timestamp': post_dt_utc,
                        'channel': channel,
                        'media': media_tag,
                        'text': post_text,
                        'time_str': dt_tehran.strftime('%H:%M'),
                        'date_str': shamsi_date.strftime('%Y/%m/%d')
                    })

        except Exception as e:
            print(f"خطا در @{channel}: {e}")
        time.sleep(2) # وقفه کمی بیشتر برای اطمینان از عدم بلاک

    all_posts.sort(key=lambda x: x['timestamp'], reverse=True)

    output_content = ""
    for post in all_posts:
        entry = f"src :@{post['channel']}\n"
        if post['media']: entry += f"{post['media']}\n"
        if post['text']: entry += f"{format_text(post['text'])}\n"
        entry += f"{post['time_str']}\n"
        entry += f"{post['date_str']}\n"
        output_content += entry + "\n\n\n\n"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output_content.strip())
    print(f"عملیات موفق: {len(all_posts)} پست در {output_file} ذخیره شد.")

def main():
    run_scraper_logic('channels1.txt', 'output1.txt')
    run_scraper_logic('channels2.txt', 'output2.txt')

if __name__ == "__main__":
    main()
