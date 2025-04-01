from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import os
import uuid
import json
import random
import string
from datetime import datetime, timedelta
from pathlib import Path

app = Flask(name)
CORS(app)
app.secret_key = 'oth'

# إعدادات المسارات
BASE_DIR = Path(file).resolve().parent
DATA_DIR = BASE_DIR / "data"
os.makedirs(DATA_DIR, exist_ok=True)
USER_FILE = DATA_DIR / "user.json"

# تهيئة ملف البيانات إذا لم يكن موجوداً
if not USER_FILE.exists():
    with open(USER_FILE, 'w', encoding='utf-8') as f:
        json.dump({"users": {}, "sessions": {}, "verification_codes": {}}, f, indent=4)

async def load_data():
    """تحميل جميع البيانات من الملف بشكل غير متزامن"""
    await asyncio.sleep(0)
    with open(USER_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

async def save_data(data):
    """حفظ جميع البيانات في الملف بشكل غير متزامن"""
    await asyncio.sleep(0)
    with open(USER_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

async def generate_verification_code():
    """إنشاء كود تحقق عشوائي"""
    await asyncio.sleep(0)
    return ''.join(random.choices(string.digits, k=6))

@app.route('/api/register', methods=['GET'])
async def register():
    data = request.args
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'status': 'error', 'message': 'جميع الحقول مطلوبة'}), 400

    all_data = await load_data()
    if username in all_data['users']:
        return jsonify({'status': 'error', 'message': 'اسم المستخدم موجود بالفعل'}), 400

    user_id = str(uuid.uuid4())
    all_data['users'][username] = {
        'id': user_id,
        'username': username,
        'email': email,
        'password': password,
        'created_at': datetime.now().isoformat()
    }
    await save_data(all_data)

    return jsonify({'status': 'success', 'message': 'تم التسجيل بنجاح'})

@app.route('/api/login', methods=['GET'])
async def login():
    data = request.args
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'status': 'error', 'message': 'اسم المستخدم وكلمة المرور مطلوبان'}), 400

    all_data = await load_data()
    user_data = all_data['users'].get(username)

    if not user_data or user_data['password'] != password:
        return jsonify({'status': 'error', 'message': 'بيانات الدخول غير صحيحة'}), 401

    verification_code = await generate_verification_code()
    expires_at = (datetime.now() + timedelta(minutes=5)).isoformat()
    all_data['verification_codes'][username] = {'code': verification_code, 'expires_at': expires_at}
    await save_data(all_data)

    return jsonify({'status': 'pending', 'message': 'تم إنشاء كود التحقق.', 'verification_code': verification_code})

@app.route('/api/verify_login', methods=['GET'])
async def verify_login():
    data = request.args
    username = data.get('username')
    verification_code = data.get('verification_code')

    if not username or not verification_code:
        return jsonify({'status': 'error', 'message': 'اسم المستخدم وكود التحقق مطلوبان'}), 400

    all_data = await load_data()
    stored_code = all_data['verification_codes'].get(username)

    if not stored_code:
        return jsonify({'status': 'error', 'message': 'لم يتم إرسال كود تحقق لهذا المستخدم'}), 400

    if datetime.now() > datetime.fromisoformat(stored_code['expires_at']):
        return jsonify({'status': 'error', 'message': 'انتهت صلاحية كود التحقق'}), 400

    if stored_code['code'] != verification_code:
        return jsonify({'status': 'error', 'message': 'كود التحقق غير صحيح'}), 400

    del all_data['verification_codes'][username]
    session_id = str(uuid.uuid4())
    all_data['sessions'][session_id] = {
        'session_id': session_id,
        'user_id': all_data['users'][username]['id'],
        'username': username,
        'created_at': datetime.now().isoformat(),
        'last_active': datetime.now().isoformat()
    }
    await save_data(all_data)

    return jsonify({'status': 'success', 'message': 'تم تسجيل الدخول بنجاح', 'session_id': session_id, 'user': {'username': username, 'email': all_data['users'][username]['email']}})

if name == 'main':
    app.run()
