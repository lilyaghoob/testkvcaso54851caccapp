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
    # بررسی دقیق ویدئو با استفاده از HTML ارسالی شما
    is_video = msg_div.select_one('.tgme_widget_message_video_player, .tgme_widget_message_video, video, .message_video_duration') is not None
    is_photo = msg_div.select_one('.tgme_widget_message_photo_wrap') is not None
    is_gif = msg_div.select_one('.videogif') is not None
    is_doc = msg_div.select_one('.tgme_widget_message_document') is not None

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
        print(f"فایل {input_file} پیدا نشد.")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        channels = [line.strip().replace('@', '') for line in f if line.strip()]

    all_posts = []
    now_utc = datetime.now(pytz.utc)
    cutoff_time = now_utc - timedelta(hours=24)

    # هدر برای دور زدن محدودیت تلگرام و دریافت نسخه کامل سایت
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9'
    }

    for channel in channels:
        print(f"در حال استخراج از: {channel}...")
        url = f"https://t.me/s/{channel}"
        try:
            res = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # پیدا کردن تمام بلاک‌های پیام
            messages = soup.select('.tgme_widget_message')
            
            for msg in messages:
                # خط قرمز: حذف نظرسنجی و پیام‌های سیستمی (Pinned و غیره)
                if msg.select_one('.tgme_widget_message_poll') or msg.select_one('.tgme_widget_message_service'):
                    continue

                time_tag = msg.select_one('time')
                if not time_tag or not time_tag.has_attr('datetime'):
                    continue
                
                post_dt_utc = datetime.fromisoformat(time_tag['datetime'].replace('Z', '+00:00'))
                if post_dt_utc < cutoff_time:
                    continue

                # استخراج متن (کپشن ویدئو یا متن عادی)
                text_div = msg.select_one('.tgme_widget_message_text')
                post_text = ""
                if text_div:
                    # جایگزینی <br> با خط جدید برای حفظ ساختار متن
                    for br in text_div.find_all("br"):
                        br.replace_with("\n")
                    post_text = text_div.get_text().strip()

                # تشخیص نوع رسانه با متد جدید
                media_tag = get_media_tag(msg)

                # اگر متن داشت یا رسانه بود، ذخیره کن
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
            print(f"خطا در {channel}: {e}")
        time.sleep(1.5)

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
    print(f"خروجی در {output_file} با {len(all_posts)} پست آماده شد.")

def main():
    run_scraper_logic('channels1.txt', 'output1.txt')
    run_scraper_logic('channels2.txt', 'output2.txt')

if __name__ == "__main__":
    main()
