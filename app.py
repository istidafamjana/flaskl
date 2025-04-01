from flask import Flask, request, jsonify, redirect, render_template
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
import os
import uuid
import json
import random
import string
from datetime import datetime, timedelta
from pathlib import Path

app = Flask(__name__)
CORS(app)
app.secret_key = 'oth'

# إعدادات المسارات
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
os.makedirs(DATA_DIR, exist_ok=True)
USER_FILE = DATA_DIR / "user.json"

# تهيئة ملف البيانات إذا لم يكن موجوداً
if not USER_FILE.exists():
    with open(USER_FILE, 'w', encoding='utf-8') as f:
        json.dump({"users": {}, "sessions": {}, "verification_codes": {}}, f, indent=4)

def load_data():
    """تحميل جميع البيانات من الملف"""
    with open(USER_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        print("Loaded data:", data)  # Debugging
        return data

def save_data(data):
    """حفظ جميع البيانات في الملف"""
    with open(USER_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        print("Saved data:", data)  # Debugging

def generate_verification_code():
    """إنشاء كود تحقق عشوائي"""
    return ''.join(random.choices(string.digits, k=6))

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not username or not email or not password:
            return jsonify({'status': 'error', 'message': 'جميع الحقول مطلوبة'}), 400

        all_data = load_data()
        if username in all_data['users']:
            return jsonify({'status': 'error', 'message': 'اسم المستخدم موجود بالفعل'}), 400

        # حفظ بيانات المستخدم
        user_id = str(uuid.uuid4())
        all_data['users'][username] = {
            'id': user_id,
            'username': username,
            'email': email,
            'password': generate_password_hash(password),
            'created_at': datetime.now().isoformat()
        }
        save_data(all_data)

        return jsonify({'status': 'success', 'message': 'تم التسجيل بنجاح'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'status': 'error', 'message': 'اسم المستخدم وكلمة المرور مطلوبان'}), 400

        all_data = load_data()
        user_data = all_data['users'].get(username)

        if not user_data or not check_password_hash(user_data['password'], password):
            return jsonify({'status': 'error', 'message': 'بيانات الدخول غير صحيحة'}), 401

        # إنشاء كود تحقق عشوائي
        verification_code = generate_verification_code()
        expires_at = (datetime.now() + timedelta(minutes=5)).isoformat()

        # حفظ كود التحقق
        all_data['verification_codes'][username] = {
            'code': verification_code,
            'expires_at': expires_at
        }
        save_data(all_data)

        # إرجاع كود التحقق في الاستجابة
        return jsonify({
            'status': 'pending',
            'message': 'تم إنشاء كود التحقق. يرجى إدخاله لإكمال تسجيل الدخول.',
            'verification_code': verification_code  # عرض الكود في الاستجابة
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/verify_login', methods=['POST'])
def verify_login():
    try:
        data = request.get_json()
        username = data.get('username')
        verification_code = data.get('verification_code')

        if not username or not verification_code:
            return jsonify({'status': 'error', 'message': 'اسم المستخدم وكود التحقق مطلوبان'}), 400

        all_data = load_data()
        stored_code = all_data['verification_codes'].get(username)

        if not stored_code:
            return jsonify({'status': 'error', 'message': 'لم يتم إرسال كود تحقق لهذا المستخدم'}), 400

        # التحقق من انتهاء صلاحية الكود
        if datetime.now() > datetime.fromisoformat(stored_code['expires_at']):
            return jsonify({'status': 'error', 'message': 'انتهت صلاحية كود التحقق'}), 400

        # التحقق من صحة الكود
        if stored_code['code'] != verification_code:
            return jsonify({'status': 'error', 'message': 'كود التحقق غير صحيح'}), 400

        # حذف كود التحقق بعد الاستخدام الناجح
        del all_data['verification_codes'][username]
        save_data(all_data)

        # إنشاء جلسة جديدة
        session_id = str(uuid.uuid4())
        all_data['sessions'][session_id] = {
            'session_id': session_id,
            'user_id': all_data['users'][username]['id'],
            'username': username,
            'created_at': datetime.now().isoformat(),
            'last_active': datetime.now().isoformat()
        }
        save_data(all_data)

        return jsonify({
            'status': 'success',
            'message': 'تم تسجيل الدخول بنجاح',
            'session_id': session_id,
            'user': {
                'username': username,
                'email': all_data['users'][username]['email']
            }
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/')
def home():
    return redirect('/register')

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)