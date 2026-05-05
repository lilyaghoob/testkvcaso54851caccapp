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
    html_str = str(msg_div).lower()
    is_video = any(x in html_str for x in ['video', 'message_video', 'player', 'js-message_video'])
    is_photo = 'photo' in html_str or 'tgme_widget_message_photo' in html_str
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

def fetch_channel_posts(channel, cutoff_time):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest' # این هدر به تلگرام می‌گوید ما دیتای کامل می‌خواهیم
    }
    
    all_channel_posts = []
    last_msg_id = None
    reached_cutoff = False
    
    # حلقه برای پیمایش به عقب در زمان (Pagination)
    while not reached_cutoff:
        url = f"https://t.me/s/{channel}"
        if last_msg_id:
            url += f"?before={last_msg_id}"
        
        try:
            res = requests.get(url, headers=headers, timeout=20)
            soup = BeautifulSoup(res.text, 'html.parser')
            messages = soup.select('.tgme_widget_message')
            
            if not messages:
                break
                
            current_batch = []
            for msg in reversed(messages): # از جدید به قدیم بررسی می‌کنیم
                # فیلتر نظرسنجی و پیام سرویس (خط قرمز)
                if msg.select_one('.tgme_widget_message_poll') or msg.select_one('.tgme_widget_message_service'):
                    continue

                time_tag = msg.select_one('time')
                if not time_tag or not time_tag.has_attr('datetime'):
                    continue
                
                post_dt_utc = datetime.fromisoformat(time_tag['datetime'].replace('Z', '+00:00'))
                
                # پیدا کردن آیدی برای درخواست بعدی
                post_url = msg.select_one('.tgme_widget_message_date')
                if post_url and post_url.has_attr('href'):
                    try:
                        last_msg_id = post_url['href'].split('/')[-1]
                    except: pass

                if post_dt_utc < cutoff_time:
                    reached_cutoff = True
                    break

                # استخراج متن با دقت بالا
                text_div = msg.select_one('.tgme_widget_message_text, .js-message_text')
                post_text = ""
                if text_div:
                    for br in text_div.find_all("br"): br.replace_with("\n")
                    post_text = text_div.get_text().strip()

                media_tag = get_media_tag(msg)

                if post_text or media_tag:
                    dt_tehran = post_dt_utc.astimezone(tehran_tz)
                    shamsi_date = jdatetime.datetime.fromgregorian(datetime=dt_tehran)
                    current_batch.append({
                        'timestamp': post_dt_utc,
                        'channel': channel,
                        'media': media_tag,
                        'text': post_text,
                        'time_str': dt_tehran.strftime('%H:%M'),
                        'date_str': shamsi_date.strftime('%Y/%m/%d')
                    })
            
            all_channel_posts.extend(current_batch)
            
            # اگر در این صفحه هیچ پستی قدیمی‌تر از کات‌اف نبود، یعنی باید باز هم به عقب برویم
            if not reached_cutoff:
                time.sleep(1.5) # جلوگیری از بلاک شدن
            else:
                break
                
        except Exception as e:
            print(f"خطا در دریافت صفحه: {e}")
            break
            
    return all_channel_posts

def run_scraper_logic(input_file, output_file):
    if not os.path.exists(input_file): return

    with open(input_file, 'r', encoding='utf-8') as f:
        channels = [line.strip().replace('@', '') for line in f if line.strip()]

    all_posts = []
    cutoff_time = datetime.now(pytz.utc) - timedelta(hours=24)

    for channel in channels:
        print(f"استخراج کامل ۲۴ ساعت اخیر: @{channel}...")
        channel_posts = fetch_channel_posts(channel, cutoff_time)
        all_posts.extend(channel_posts)
        time.sleep(2)

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
    print(f"پایان عملیات. {len(all_posts)} پست ذخیره شد.")

def main():
    run_scraper_logic('channels1.txt', 'output1.txt')
    run_scraper_logic('channels2.txt', 'output2.txt')

if __name__ == "__main__":
    main()
