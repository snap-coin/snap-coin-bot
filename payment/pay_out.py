import asyncio
import secrets
import sqlite3
import os
import string
from dotenv import load_dotenv
import logging

import requests

load_dotenv("assets.env")
load_dotenv(".env")

logger = logging.getLogger('snap.payout')

async def get_pending_withdrawals():
    db = os.getenv("REWARDS_DB", "rewards.db")
    conn = None
    try:
        conn = sqlite3.connect(db)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT r.user_id, r.reward_name, r.reward_amount, a.wallet_address
            FROM rewards r
            JOIN addresses a ON r.user_id = a.user_id
            WHERE r.reward_amount > 0
            AND a.wallet_address IS NOT NULL
            AND a.wallet_address != ''
        ''')
        
        pending = cursor.fetchall()
    
        conn.close()
        return pending

    except sqlite3.Error as e:
        logger.error("Database error: %s", e)
        if conn:
            conn.close()
        return []
    

async def request_payout(interval = int(os.getenv("PAYOUT_INTERVAL_SECONDS", "86400"))):  # default to 24 hours
    while True:
        pending = await get_pending_withdrawals()
        if pending:
            receivers = [
                [wallet_address, round(reward_amount, 4)]
                for user_id, reward_name, reward_amount, wallet_address in pending
            ]
            
            reference = generate_base36()
            
            secret_key = os.getenv("SECRET_KEY")

            data = {
                "secret_key": secret_key,
                "status_reference_wallet": reference,
                "receivers": receivers,
            }
            
            try:
                link = os.getenv("FAUCET_LINK")
            
                headers = {
                    'Content-Type': 'application/json'
                }
                
                req = requests.post(link, json=data, headers=headers, timeout=10)
                
                logger.info("Requested payout for %d users with total amount %.4f", len(receivers), sum(r[1] for r in receivers))
                
                logger.info("Payout request response: %d - %s", req.status_code, req.text)
            
                # TODO: If successful, schedule a task to check status in a 5 minutes then mark the rewards as paid in the database + post on discord channel
            except requests.exceptions.RequestException as e:
                logger.error("Payout request failed: %s", e)
        else:
            logger.info("No pending withdrawals found")
        
        await asyncio.sleep(interval)

        
def generate_base36(length=30):
    chars = string.digits + string.ascii_lowercase
    return ''.join(secrets.choice(chars) for _ in range(length))


def get_withdrawal_status(reference):
    url = f"{os.getenv('FAUCET_LINK')}/get-withdrawals/{reference}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            logger.error("Failed to get withdrawal status: %d - %s", resp.status_code, resp.text)
            return None
    except requests.exceptions.RequestException as e:
        logger.error("Error checking withdrawal status: %s", e)
        return None