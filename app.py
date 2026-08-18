import json
import os
import subprocess
import uuid as uuid_lib
import time
from flask import Flask, request, render_template_string, make_response, redirect, session

app = Flask(__name__)
app.secret_key = os.urandom(24)  # برای سشن

CONFIG_PATH = "/usr/local/etc/xray/config.json"
LOG_FILE = "/tmp/xray_status.log"
PASSWORD_FILE = "/app/password.txt"

# ========== توابع مدیریت رمز ==========

def get_password():
    """دریافت رمز از فایل، اگر نبود admin رو پیش‌فرض بگیر"""
    try:
        with open(PASSWORD_FILE, 'r') as f:
            return f.read().strip()
    except:
        # اگر فایل نبود، رمز پیش‌فرض رو بساز
        set_password("admin")
        return "admin"

def set_password(new_password):
    """ذخیره رمز جدید در فایل"""
    with open(PASSWORD_FILE, 'w') as f:
        f.write(new_password.strip())

def check_auth():
    """بررسی لاگین بودن کاربر"""
    return session.get('logged_in', False)

def login_required(f):
    """دکوریتور برای محافظت از صفحات"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not check_auth():
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

# ========== دیکشنری ترجمه ==========
TRANSLATIONS = {
    "fa": {
        "title": "🕸️ پنل اسپایدر پک",
        "version": "نسخه ۲.۰",
        "status_label": "📡 وضعیت Xray",
        "online": "آنلاین ✅",
        "offline": "آفلاین ❌",
        "clients_label": "👥 کلاینت‌های فعال",
        "domain_label": "🌐 دامنه",
        "uuid_label": "UUID جدید",
        "uuid_placeholder": "خالی بذارید تا خودکار ساخته شود",
        "path_label": "مسیر (Path)",
        "path_placeholder": "مثلا /spider",
        "port_label": "پورت اینباند (اختیاری)",
        "port_placeholder": "پیش‌فرض: 10086",
        "update_btn": "🔄 بروزرسانی و ری‌استارت",
        "restart_btn": "🔁 ری‌استارت Xray",
        "reset_btn": "🔄 بازنشانی کامل",
        "copy_btn": "📋 کپی لینک",
        "copied_msg": "✅ لینک کپی شد!",
        "log_label": "📝 آخرین رویداد",
        "footer": "اسپایدر پک · ساخته شده با ❤️ برای Railway",
        "persian": "فارسی",
        "english": "انگلیسی",
        "no_log": "هیچ رویدادی ثبت نشده",
        "restart_log": "ری‌استارت در",
        "update_log": "بروزرسانی شد! مسیر: {path}، پورت: {port}",
        # بخش لاگین
        "login_title": "🔐 ورود به پنل",
        "password_label": "رمز عبور",
        "login_btn": "ورود",
        "wrong_password": "❌ رمز عبور اشتباه است!",
        "logout_btn": "🚪 خروج",
        "settings_title": "⚙️ تنظیمات پنل",
        "new_password_label": "رمز عبور جدید",
        "confirm_password_label": "تکرار رمز عبور",
        "change_password_btn": "تغییر رمز",
        "password_changed": "✅ رمز عبور با موفقیت تغییر کرد!",
        "password_mismatch": "❌ رمزها مطابقت ندارند!",
        "back_to_panel": "← بازگشت به پنل"
    },
    "en": {
        "title": "🕸️ Spider Pack Panel",
        "version": "v2.0",
        "status_label": "📡 Xray Status",
        "online": "Online ✅",
        "offline": "Offline ❌",
        "clients_label": "👥 Active Clients",
        "domain_label": "🌐 Domain",
        "uuid_label": "New UUID",
        "uuid_placeholder": "Leave empty to auto-generate",
        "path_label": "Path",
        "path_placeholder": "e.g. /spider",
        "port_label": "Inbound Port (Optional)",
        "port_placeholder": "Default: 10086",
        "update_btn": "🔄 Update & Restart",
        "restart_btn": "🔁 Restart Xray",
        "reset_btn": "🔄 Full Reset",
        "copy_btn": "📋 Copy Link",
        "copied_msg": "✅ Link copied!",
        "log_label": "📝 Last Event",
        "footer": "Spider Pack · Made with ❤️ for Railway",
        "persian": "Persian",
        "english": "English",
        "no_log": "No events recorded",
        "restart_log": "Restarted at",
        "update_log": "Updated! Path: {path}, Port: {port}",
        # Login section
        "login_title": "🔐 Login to Panel",
        "password_label": "Password",
        "login_btn": "Login",
        "wrong_password": "❌ Wrong password!",
        "logout_btn": "🚪 Logout",
        "settings_title": "⚙️ Panel Settings",
        "new_password_label": "New Password",
        "confirm_password_label": "Confirm Password",
        "change_password_btn": "Change Password",
        "password_changed": "✅ Password changed successfully!",
        "password_mismatch": "❌ Passwords do not match!",
        "back_to_panel": "← Back to Panel"
    }
}

# ========== توابع زبان ==========

def get_lang():
    return request.cookies.get('lang', 'fa')

def get_text(key, **kwargs):
    lang = get_lang()
    text = TRANSLATIONS.get(lang, TRANSLATIONS['fa']).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text

# ========== قالب صفحه لاگین ==========
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ text('login_title') }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
            direction: {{ 'rtl' if lang == 'fa' else 'ltr' }};
        }
        .card {
            max-width: 400px;
            width: 100%;
            background: #1e293b;
            border-radius: 24px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.6);
            border: 1px solid #334155;
        }
        h1 {
            font-size: 28px;
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #3b82f6;
            padding-bottom: 15px;
        }
        form {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        label {
            font-size: 14px;
            color: #cbd5e1;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        input {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 12px 16px;
            color: #f1f5f9;
            font-size: 15px;
            transition: 0.2s;
        }
        input:focus {
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59,130,246,0.3);
        }
        .btn {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 40px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: 0.2s;
        }
        .btn:hover { background: #2563eb; transform: scale(1.02); }
        .error {
            background: #7f1d1d;
            color: #fca5a5;
            padding: 10px 16px;
            border-radius: 12px;
            font-size: 14px;
            text-align: center;
        }
        .lang-switcher {
            display: flex;
            justify-content: center;
            gap: 8px;
            margin-top: 20px;
        }
        .lang-btn {
            background: #334155;
            color: #94a3b8;
            border: none;
            padding: 6px 14px;
            border-radius: 30px;
            font-size: 13px;
            cursor: pointer;
            transition: 0.2s;
            text-decoration: none;
        }
        .lang-btn.active {
            background: #3b82f6;
            color: white;
        }
        .lang-btn:hover { opacity: 0.8; }
        .footer {
            margin-top: 20px;
            text-align: center;
            color: #64748b;
            font-size: 12px;
        }
    </style>
</head>
<body>
<div class="card">
    <h1>🔐 {{ text('login_title') }}</h1>
    {% if error %}
        <div class="error">{{ error }}</div>
    {% endif %}
    <form method="POST">
        <label>
            {{ text('password_label') }}
            <input type="password" name="password" placeholder="••••••••" required>
        </label>
        <button type="submit" class="btn">{{ text('login_btn') }}</button>
    </form>
    <div class="lang-switcher">
        <a href="/set_lang/fa?next=/login" class="lang-btn {{ 'active' if lang == 'fa' else '' }}">{{ text('persian') }}</a>
        <a href="/set_lang/en?next=/login" class="lang-btn {{ 'active' if lang == 'en' else '' }}">{{ text('english') }}</a>
    </div>
    <div class="footer">
        {{ text('footer') }}
    </div>
</div>
</body>
</html>
"""

# ========== قالب پنل اصلی (با دکمه خروج و تنظیمات) ==========
PANEL_TEMPLATE = """
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ text('title') }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
            direction: {{ 'rtl' if lang == 'fa' else 'ltr' }};
        }
        .card {
            max-width: 700px;
            width: 100%;
            background: #1e293b;
            border-radius: 24px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.6);
            border: 1px solid #334155;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #3b82f6;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }
        h1 {
            font-size: 28px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        h1 small {
            font-size: 14px;
            font-weight: normal;
            color: #94a3b8;
            margin-left: 10px;
        }
        .header-actions {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        .header-actions .btn-sm {
            background: #334155;
            color: #94a3b8;
            border: none;
            padding: 6px 14px;
            border-radius: 30px;
            font-size: 13px;
            cursor: pointer;
            transition: 0.2s;
            text-decoration: none;
        }
        .header-actions .btn-sm:hover {
            background: #475569;
            color: #e2e8f0;
        }
        .header-actions .btn-sm.danger:hover {
            background: #dc2626;
            color: white;
        }
        .lang-switcher {
            display: flex;
            gap: 4px;
        }
        .lang-btn {
            background: #334155;
            color: #94a3b8;
            border: none;
            padding: 4px 12px;
            border-radius: 30px;
            font-size: 12px;
            cursor: pointer;
            transition: 0.2s;
            text-decoration: none;
        }
        .lang-btn.active {
            background: #3b82f6;
            color: white;
        }
        .lang-btn:hover { opacity: 0.8; }
        .status-badge {
            display: inline-block;
            padding: 4px 14px;
            border-radius: 40px;
            font-size: 13px;
            font-weight: bold;
        }
        .online { background: #22c55e; color: #052e16; }
        .offline { background: #ef4444; color: #7f1d1d; }
        .info-row {
            display: flex;
            justify-content: space-between;
            background: #0f172a;
            padding: 12px 18px;
            border-radius: 16px;
            margin: 15px 0;
            font-size: 14px;
        }
        .info-row span:first-child { color: #94a3b8; }
        .info-row span:last-child { font-weight: 600; }
        form {
            display: flex;
            flex-direction: column;
            gap: 16px;
            margin: 20px 0;
        }
        label {
            font-size: 14px;
            color: #cbd5e1;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        input {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 12px 16px;
            color: #f1f5f9;
            font-size: 15px;
            transition: 0.2s;
        }
        input:focus {
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59,130,246,0.3);
        }
        .btn-group {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }
        .btn {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 40px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: 0.2s;
            flex: 1;
            min-width: 120px;
        }
        .btn:hover { background: #2563eb; transform: scale(1.02); }
        .btn-danger { background: #ef4444; }
        .btn-danger:hover { background: #dc2626; }
        .btn-secondary { background: #475569; }
        .btn-secondary:hover { background: #334155; }
        .link-box {
            background: #0f172a;
            border-radius: 16px;
            padding: 16px;
            margin: 20px 0;
            border: 1px solid #334155;
            position: relative;
        }
        .link-box pre {
            white-space: pre-wrap;
            word-break: break-all;
            font-size: 13px;
            color: #e2e8f0;
            margin-bottom: 10px;
        }
        .copy-btn {
            background: #3b82f6;
            border: none;
            color: white;
            padding: 6px 18px;
            border-radius: 30px;
            font-size: 13px;
            cursor: pointer;
            transition: 0.2s;
        }
        .copy-btn:hover { background: #2563eb; }
        .log-area {
            background: #0f172a;
            border-radius: 12px;
            padding: 12px 16px;
            font-size: 13px;
            color: #94a3b8;
            border: 1px solid #1e293b;
            margin-top: 10px;
            max-height: 60px;
            overflow-y: auto;
        }
        .footer {
            margin-top: 20px;
            text-align: center;
            color: #64748b;
            font-size: 12px;
        }
        @media (max-width: 500px) {
            .card { padding: 20px; }
            .btn-group { flex-direction: column; }
            .header { flex-direction: column; gap: 10px; align-items: stretch; }
            .header-actions { justify-content: center; }
            .lang-switcher { justify-content: center; }
        }
    </style>
</head>
<body>
<div class="card">
    <div class="header">
        <h1>
            🕸️ {{ text('title') }}
            <small>{{ text('version') }}</small>
        </h1>
        <div class="header-actions">
            <a href="/settings" class="btn-sm">⚙️</a>
            <a href="/logout" class="btn-sm danger">🚪</a>
            <div class="lang-switcher">
                <a href="/set_lang/fa?next=/" class="lang-btn {{ 'active' if lang == 'fa' else '' }}">{{ text('persian') }}</a>
                <a href="/set_lang/en?next=/" class="lang-btn {{ 'active' if lang == 'en' else '' }}">{{ text('english') }}</a>
            </div>
        </div>
    </div>

    <div class="info-row">
        <span>{{ text('status_label') }}</span>
        <span>
            <span class="status-badge {{ 'online' if status == 'online' else 'offline' }}">
                {{ text('online') if status == 'online' else text('offline') }}
            </span>
        </span>
    </div>
    <div class="info-row">
        <span>{{ text('clients_label') }}</span>
        <span>{{ clients_count }}</span>
    </div>
    <div class="info-row">
        <span>{{ text('domain_label') }}</span>
        <span>{{ domain }}</span>
    </div>

    <form method="POST">
        <label>
            {{ text('uuid_label') }}
            <input type="text" name="uuid" value="{{ uuid }}" placeholder="{{ text('uuid_placeholder') }}">
        </label>
        <label>
            {{ text('path_label') }}
            <input type="text" name="path" value="{{ path }}" placeholder="{{ text('path_placeholder') }}">
        </label>
        <label>
            {{ text('port_label') }}
            <input type="number" name="port" value="{{ port }}" placeholder="{{ text('port_placeholder') }}">
        </label>
        <div class="btn-group">
            <button type="submit" class="btn">{{ text('update_btn') }}</button>
        </div>
    </form>

    <div class="link-box">
        <pre id="vlessLink">vless://{{ uuid }}@{{ domain }}:443?encryption=none&security=tls&sni={{ domain }}&fp=chrome&type=ws&host={{ domain }}&path={{ path }}#SpiderPack</pre>
        <button class="copy-btn" onclick="copyLink()">{{ text('copy_btn') }}</button>
    </div>

    <div style="display: flex; gap: 10px; margin-top: 10px;">
        <form method="POST" action="/restart" style="flex:1;">
            <button type="submit" class="btn btn-secondary" style="width:100%;">{{ text('restart_btn') }}</button>
        </form>
        <form method="POST" action="/reset" style="flex:1;">
            <button type="submit" class="btn btn-danger" style="width:100%;">{{ text('reset_btn') }}</button>
        </form>
    </div>

    <div class="log-area">
        {{ text('log_label') }}: {{ log_message }}
    </div>

    <div class="footer">
        {{ text('footer') }}
    </div>
</div>

<script>
function copyLink() {
    const link = document.getElementById('vlessLink').innerText;
    navigator.clipboard.writeText(link).then(() => {
        alert('{{ text('copied_msg') }}');
    }).catch(() => {
        const range = document.createRange();
        range.selectNode(document.getElementById('vlessLink'));
        window.getSelection().removeAllRanges();
        window.getSelection().addRange(range);
        document.execCommand('copy');
        alert('{{ text('copied_msg') }}');
    });
}
</script>
</body>
</html>
"""

# ========== قالب صفحه تنظیمات ==========
SETTINGS_TEMPLATE = """
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ text('settings_title') }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
            direction: {{ 'rtl' if lang == 'fa' else 'ltr' }};
        }
        .card {
            max-width: 500px;
            width: 100%;
            background: #1e293b;
            border-radius: 24px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.6);
            border: 1px solid #334155;
        }
        h1 {
            font-size: 28px;
            text-align: center;
            border-bottom: 2px solid #3b82f6;
            padding-bottom: 15px;
            margin-bottom: 30px;
        }
        .back-link {
            display: inline-block;
            color: #94a3b8;
            text-decoration: none;
            margin-bottom: 20px;
            transition: 0.2s;
        }
        .back-link:hover { color: #e2e8f0; }
        form {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        label {
            font-size: 14px;
            color: #cbd5e1;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        input {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 12px 16px;
            color: #f1f5f9;
            font-size: 15px;
            transition: 0.2s;
        }
        input:focus {
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59,130,246,0.3);
        }
        .btn {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 40px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: 0.2s;
        }
        .btn:hover { background: #2563eb; transform: scale(1.02); }
        .success {
            background: #064e3b;
            color: #6ee7b7;
            padding: 10px 16px;
            border-radius: 12px;
            font-size: 14px;
            text-align: center;
        }
        .error {
            background: #7f1d1d;
            color: #fca5a5;
            padding: 10px 16px;
            border-radius: 12px;
            font-size: 14px;
            text-align: center;
        }
        .footer {
            margin-top: 20px;
            text-align: center;
            color: #64748b;
            font-size: 12px;
        }
    </style>
</head>
<body>
<div class="card">
    <a href="/" class="back-link">← {{ text('back_to_panel') }}</a>
    <h1>⚙️ {{ text('settings_title') }}</h1>
    {% if success %}
        <div class="success">{{ success }}</div>
    {% endif %}
    {% if error %}
        <div class="error">{{ error }}</div>
    {% endif %}
    <form method="POST">
        <label>
            {{ text('new_password_label') }}
            <input type="password" name="new_password" placeholder="••••••••" required>
        </label>
        <label>
            {{ text('confirm_password_label') }}
            <input type="password" name="confirm_password" placeholder="••••••••" required>
        </label>
        <button type="submit" class="btn">{{ text('change_password_btn') }}</button>
    </form>
    <div class="footer">
        {{ text('footer') }}
    </div>
</div>
</body>
</html>
"""

# ========== توابع مدیریت Xray ==========

def get_domain():
    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN") or os.environ.get("RAILWAY_STATIC_URL") or "your-domain.up.railway.app"
    return domain.replace("https://", "").replace("http://", "")

def read_config():
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except:
        return None

def write_config(uuid, path, port=10086):
    config = {
        "log": { "loglevel": "warning" },
        "inbounds": [
            {
                "listen": "127.0.0.1",
                "port": port,
                "protocol": "vless",
                "settings": {
                    "clients": [ { "id": uuid, "flow": "xtls-rprx-vision" } ],
                    "decryption": "none"
                },
                "streamSettings": {
                    "network": "ws",
                    "wsSettings": { "path": path }
                }
            }
        ],
        "outbounds": [ { "protocol": "freedom" } ]
    }
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)

def restart_xray():
    subprocess.run(["pkill", "-f", "xray"], capture_output=True)
    subprocess.Popen(["xray", "-c", CONFIG_PATH], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    lang = get_lang()
    with open(LOG_FILE, 'w') as f:
        f.write(f"{TRANSLATIONS.get(lang, TRANSLATIONS['fa'])['restart_log']} {time.ctime()}")

def get_clients_count():
    config = read_config()
    if config and "inbounds" in config and len(config["inbounds"]) > 0:
        return len(config["inbounds"][0].get("settings", {}).get("clients", []))
    return 0

def check_status():
    result = subprocess.run(["pgrep", "-f", "xray"], capture_output=True)
    return "online" if result.returncode == 0 else "offline"

def get_log():
    try:
        with open(LOG_FILE, 'r') as f:
            return f.read().strip()
    except:
        return ""

# ========== مسیرها ==========

@app.route('/login', methods=['GET', 'POST'])
def login():
    lang = get_lang()
    error = None
    
    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        if password == get_password():
            session['logged_in'] = True
            return redirect('/')
        else:
            error = get_text('wrong_password')
    
    return render_template_string(LOGIN_TEMPLATE, lang=lang, text=get_text, error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/login')

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    lang = get_lang()
    domain = get_domain()
    current_uuid = ""
    current_path = "/spider"
    current_port = 10086
    log_msg = get_log()

    if not log_msg:
        log_msg = get_text('no_log')

    config = read_config()
    if config and "inbounds" in config and len(config["inbounds"]) > 0:
        clients = config["inbounds"][0].get("settings", {}).get("clients", [])
        if clients:
            current_uuid = clients[0].get("id", "")
        ws_settings = config["inbounds"][0].get("streamSettings", {}).get("wsSettings", {})
        current_path = ws_settings.get("path", "/spider")
        current_port = config["inbounds"][0].get("port", 10086)

    if request.method == 'POST':
        new_uuid = request.form.get("uuid", "").strip()
        new_path = request.form.get("path", "").strip()
        new_port = request.form.get("port", "").strip()

        if not new_uuid:
            new_uuid = str(uuid_lib.uuid4())
        if not new_path:
            new_path = "/spider"
        if not new_path.startswith("/"):
            new_path = "/" + new_path
        try:
            new_port = int(new_port) if new_port else 10086
        except:
            new_port = 10086

        write_config(new_uuid, new_path, new_port)
        restart_xray()
        current_uuid = new_uuid
        current_path = new_path
        current_port = new_port
        log_msg = get_text('update_log', path=new_path, port=new_port)

    status = check_status()
    clients_count = get_clients_count()

    return render_template_string(
        PANEL_TEMPLATE,
        lang=lang,
        text=get_text,
        domain=domain,
        uuid=current_uuid,
        path=current_path,
        port=current_port,
        status=status,
        clients_count=clients_count,
        log_message=log_msg
    )

@app.route('/restart', methods=['POST'])
@login_required
def restart_only():
    restart_xray()
    return index()

@app.route('/reset', methods=['POST'])
@login_required
def reset_all():
    write_config(str(uuid_lib.uuid4()), "/spider", 10086)
    restart_xray()
    return index()

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    lang = get_lang()
    success = None
    error = None
    
    if request.method == 'POST':
        new_pass = request.form.get('new_password', '').strip()
        confirm_pass = request.form.get('confirm_password', '').strip()
        
        if not new_pass or len(new_pass) < 4:
            error = "رمز عبور باید حداقل ۴ کاراکتر باشد."
        elif new_pass != confirm_pass:
            error = get_text('password_mismatch')
        else:
            set_password(new_pass)
            success = get_text('password_changed')
    
    return render_template_string(SETTINGS_TEMPLATE, lang=lang, text=get_text, success=success, error=error)

@app.route('/set_lang/<lang>')
def set_lang(lang):
    if lang not in ['fa', 'en']:
        lang = 'fa'
    next_url = request.args.get('next', '/')
    resp = make_response(redirect(next_url))
    resp.set_cookie('lang', lang, max_age=60*60*24*30)
    return resp

# ========== اجرای اولیه ==========

if __name__ == '__main__':
    # اطمینان از وجود رمز پیش‌فرض
    if not os.path.exists(PASSWORD_FILE):
        set_password("admin")
    
    if not read_config():
        write_config(str(uuid_lib.uuid4()), "/spider", 10086)
        restart_xray()
    
    app.run(host='127.0.0.1', port=5000)
