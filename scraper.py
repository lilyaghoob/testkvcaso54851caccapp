import requests
from bs4 import BeautifulSoup
import jdatetime
import pytz
from datetime import datetime, timedelta
import time
import os

# تنظیمات زمان
tehran_tz = pytz.timezone('Asia/Tehran')

def format_text(text):
    if not text: return ""
    rlm = "\u200F"
    lines = text.strip().split('\n')
    return "\n".join([f"{rlm}{line}" for line in lines])

def run_scraper_logic(input_file, output_file):
    if not os.path.exists(input_file):
        print(f"فایل {input_file} پیدا نشد. صرف‌نظر شد.")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        channels = [line.strip().replace('@', '') for line in f if line.strip()]

    all_posts = []
    now_utc = datetime.now(pytz.utc)
    cutoff_time = now_utc - timedelta(hours=24)

    for channel in channels:
        print(f"در حال استخراج از {input_file}: {channel}...")
        url = f"https://t.me/s/{channel}"
        try:
            res = requests.get(url, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            messages = soup.select('.tgme_widget_message')
            
            for msg in messages:
                # خط قرمز ۱: فیلتر کردن پست‌های نظرسنجی
                if msg.select_one('.tgme_widget_message_poll'):
                    continue
                
                # خط قرمز ۲: فیلتر کردن پیام‌های سرویس (مثل Pinned a photo یا ایجاد کانال)
                if msg.select_one('.tgme_widget_message_service'):
                    continue

                time_tag = msg.select_one('time')
                if not time_tag or not time_tag.has_attr('datetime'):
                    continue
                
                post_dt_utc = datetime.fromisoformat(time_tag['datetime'].replace('Z', '+00:00'))
                if post_dt_utc < cutoff_time:
                    continue

                # استخراج متن
                text_div = msg.select_one('.tgme_widget_message_text')
                if text_div:
                    for br in text_div.find_all("br"): br.replace_with("\n")
                    post_text = text_div.get_text().strip()
                else:
                    post_text = ""

                # چون فرمودید "مهم متنه"، فقط در صورتی که متن وجود داشته باشد پست را اضافه می‌کنیم
                if post_text:
                    dt_tehran = post_dt_utc.astimezone(tehran_tz)
                    shamsi_date = jdatetime.datetime.fromgregorian(datetime=dt_tehran)
                    
                    all_posts.append({
                        'timestamp': post_dt_utc,
                        'channel': channel,
                        'text': post_text,
                        'time_str': dt_tehran.strftime('%H:%M'),
                        'date_str': shamsi_date.strftime('%Y/%m/%d')
                    })

        except Exception as e:
            print(f"خطا در کانال {channel}: {e}")
        time.sleep(1.2)

    # مرتب‌سازی بر اساس زمان (جدیدترین اول)
    all_posts.sort(key=lambda x: x['timestamp'], reverse=True)

    # ساخت محتوای فایل
    output_content = ""
    for post in all_posts:
        entry = f"src :@{post['channel']}\n"
        # بخش تگ رسانه کاملاً از خروجی حذف شد
        entry += f"{format_text(post['text'])}\n"
        entry += f"{post['time_str']}\n"
        entry += f"{post['date_str']}\n"
        output_content += entry + "\n\n\n\n"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output_content.strip())
    print(f"خروجی در {output_file} با {len(all_posts)} پست ذخیره شد.")

def main():
    # اجرای اسکرپر برای لیست اول
    run_scraper_logic('channels1.txt', 'output1.txt')
    
    # اجرای اسکرپر برای لیست دوم
    run_scraper_logic('channels2.txt', 'output2.txt')

if __name__ == "__main__":
    main()
