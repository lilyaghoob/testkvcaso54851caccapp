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
    """
    بررسی دقیق انواع مدیا در پست تلگرام.
    سلکتورها برای پوشش کامل انواع نمایش ویدیو در نسخه وب به‌روزرسانی شدند.
    """
    # تشخیص عکس
    has_photo = msg_div.select_one('.tgme_widget_message_photo_wrap') is not None
    
    # --- اصلاح اصلی: تشخیص جامع ویدیو ---
    # تلگرام وب از کلاس‌های مختلفی برای ویدیو استفاده می‌کند. ما همه را چک می‌کنیم:
    has_video = (
        msg_div.select_one('.tgme_widget_message_video') is not None or          # کلاس استاندارد ویدیو
        msg_div.select_one('.tgme_widget_message_video_player') is not None or   # مدیاپلیر اختصاصی
        msg_div.select_one('video') is not None or                                # تگ خام ویدیوی HTML5
        msg_div.select_one('.tgme_widget_message_roundvideo_wrap') is not None   # ویدیوی نوت (دایره‌ای)
    )
    
    # تشخیص نظرسنجی، فایل و گیف
    has_poll = msg_div.select_one('.tgme_widget_message_poll') is not None
    has_doc = msg_div.select_one('.tgme_widget_message_document') is not None
    has_gif = msg_div.select_one('.videogif') is not None # گیف‌ها معمولاً کلاس اختصاصی دارند
    
    # تشخیص پیام صوتی (Voice)
    has_voice = msg_div.select_one('.tgme_widget_message_voice_player') is not None

    # اولویت‌بندی خروجی
    if has_photo and has_video: return "[عکس و ویدئو]"
    if has_voice: return "[پیام صوتی]"
    if has_gif: return "[گیف]"
    if has_photo: return "[عکس]"
    if has_video: return "[ویدئو]"
    if has_poll: return "[نظرسنجی]"
    if has_doc: return "[فایل]"
    return ""

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
            # ارسال درخواست با User-Agent برای شبیه‌سازی مرورگر واقعی
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            res = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            messages = soup.select('.tgme_widget_message')
            
            for msg in messages:
                # نادیده گرفتن پیام‌های سیستمی (مثل "Pinned a photo")
                if msg.select_one('.tgme_widget_message_service'):
                    continue

                time_tag = msg.select_one('time')
                if not time_tag or not time_tag.has_attr('datetime'):
                    continue
                
                post_dt_utc = datetime.fromisoformat(time_tag['datetime'].replace('Z', '+00:00'))
                if post_dt_utc < cutoff_time:
                    continue

                text_div = msg.select_one('.tgme_widget_message_text')
                if text_div:
                    for br in text_div.find_all("br"): br.replace_with("\n")
                    # حفظ ساختار HTML ساده برای برخی متن‌ها اگر لازم بود، اما get_text امن‌تر است
                    post_text = text_div.get_text()
                else:
                    post_text = ""

                # فراخوانی تابع اصلاح شده
                media_tag = get_media_tag(msg)

                # اگر پست متنی بود یا مدیای قابل تشخیصی داشت، آن را ذخیره کن
                if post_text.strip() or media_tag:
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
            print(f"خطا در کانال {channel}: {e}")
        time.sleep(1.2)

    # مرتب‌سازی بر اساس زمان (جدیدترین اول)
    all_posts.sort(key=lambda x: x['timestamp'], reverse=True)

    # ساخت محتوای فایل
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
    print(f"خروجی در {output_file} با {len(all_posts)} پست ذخیره شد.")

def main():
    # اجرای اسکرپر برای لیست اول
    run_scraper_logic('channels1.txt', 'output1.txt')
    
    # اجرای اسکرپر برای لیست دوم
    run_scraper_logic('channels2.txt', 'output2.txt')

# اصلاح: سینتکس استاندارد پایتون برای اجرای اصلی
if __name__ == "__main__":
    main()
