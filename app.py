from flask import Flask, request, jsonify
import requests
import random
import string
import hashlib
import re
import os
import pyotp

app = Flask(__name__)

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
TM_HOST = "privatix-temp-mail-v1.p.rapidapi.com"
TM_HEADERS = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": TM_HOST}
TM_BASE = f"https://{TM_HOST}"

# ইউজার সেশন ট্র্যাক করার জন্য (মেমোরিতে)
user_sessions = {}

@app.route('/api/start_task', methods=['GET'])
def start_task():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "User ID required"}), 400

    try:
        domains_res = requests.get(f"{TM_BASE}/request/domains/", headers=TM_HEADERS, timeout=15)
        domains = domains_res.json()
        if not isinstance(domains, list) or not domains: 
            return jsonify({"error": "No domains found"}), 500
            
        random_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        domain = random.choice(domains)
        email = f"{random_name}{domain}"
        email_md5 = hashlib.md5(email.lower().encode()).hexdigest()
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        
        # এখানে আপনার usernames.txt থেকে লজিক বসাতে হবে
        login = "siyam_khauy_" + ''.join(random.choices(string.digits, k=3))
        
        user_sessions[user_id] = {
            "email": email,
            "password": password,
            "login": login,
            "first_name": random_name.capitalize(),
            "email_md5": email_md5,
            "twoFA": ""
        }
        
        return jsonify({
            "status": "success",
            "email": email,
            "password": password,
            "login": login,
            "first_name": random_name.capitalize()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_otp', methods=['GET'])
def get_otp():
    user_id = request.args.get('user_id')
    code_type = request.args.get('type') # '6' or '8'
    
    if user_id not in user_sessions:
        return jsonify({"error": "No active task found"}), 400
        
    md5 = user_sessions[user_id]["email_md5"]
    try:
        url = f"{TM_BASE}/request/mail/id/{md5}/"
        res = requests.get(url, headers=TM_HEADERS, timeout=15)
        messages = res.json()
        
        if isinstance(messages, dict) or not messages:
            return jsonify({"code": None})

        for msg in messages:
            subject = msg.get("mail_subject", "").lower()
            combined = (msg.get("mail_html", "") or "") + " " + (msg.get("mail_text", "") or "")
            combined = re.sub(r'<[^>]+>', ' ', combined)
            
            if code_type == '8' and ("authenticate" in subject or "meta" in subject):
                match = re.search(r'\b\d{8}\b', combined)
                if match: return jsonify({"code": match.group(0)})
            elif code_type == '6' and ("instagram" in subject or "confirmation" in subject):
                match = re.search(r'\b\d{6}\b', combined)
                if match: return jsonify({"code": match.group(0)})
                
        return jsonify({"code": None})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/submit_2fa', methods=['POST'])
def submit_2fa():
    data = request.json
    user_id = data.get('user_id')
    two_fa_key = data.get('two_fa_key', '').replace(" ", "").upper()
    
    if user_id not in user_sessions:
        return jsonify({"error": "No active task found"}), 400
        
    try:
        totp = pyotp.TOTP(two_fa_key)
        generated_code = totp.now()
        user_sessions[user_id]["twoFA"] = two_fa_key
        return jsonify({"status": "success", "generated_code": generated_code})
    except:
        return jsonify({"error": "Invalid 2FA Key"}), 400

@app.route('/api/complete_task', methods=['POST'])
def complete_task():
    data = request.json
    user_id = data.get('user_id')
    
    if user_id not in user_sessions:
        return jsonify({"error": "No active task found"}), 400
        
    session = user_sessions[user_id]
    
    # এখানে আপনার Google Apps Script-এ ডেটা পাঠানোর লজিক বসবে
    # payload = {...}
    # requests.post(WEB_APP_URL, json=payload)
    
    del user_sessions[user_id]
    return jsonify({"status": "success", "message": "Your data has received. Soon you will get feedback."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
