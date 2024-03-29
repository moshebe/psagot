import requests
import logging
import sys
import os
import time

file_handler = logging.FileHandler(filename='/tmp/meitav.log')
stdout_handler = logging.StreamHandler(sys.stdout)
handlers = [file_handler, stdout_handler]
if os.environ.get('VERBOSE'):
    log_level = logging.DEBUG
else:
    log_level = logging.INFO

logging.basicConfig(
    level=log_level,
    format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    handlers=handlers
)

logger = logging.getLogger('meitav')

session = requests.Session()

BASE_URL='https://sparkmeitav.ordernet.co.il/api'
RETRIES=3
RETRY_DELAY=5

def get_auth_key(username, password):
    url = f'{BASE_URL}/Auth/Authenticate'
    res = requests.post(url, json={'username': username, 'password': password})
    if (res.status_code != 200):
        raise Exception('unable to authenticate')
    
    payload = res.json()
    logger.debug(f'got auth key response: {payload}')

    if payload['a'] != 'Success':
        raise Exception(f"invalid auth result: {payload['a']}")
    
    return payload['l']
    

def get_accounts_keys(session):
    url = f'{BASE_URL}/DataProvider/GetStaticData'
    res = session.get(url)
    if res.status_code != 200:
        raise Exception(f'unable to list accounts, status: {res.status_code} {res.text}')
    
    payload = res.json()
    logger.debug(f'got accounts keys response: {payload}')
    return list(map(lambda i: i['_k'], list(filter(lambda i: i['b'] == 'ACC', payload))[0]['a']))

def get_account_balance(session, account_key):
    url = f'{BASE_URL}/Account/GetAccountSecurities?accountKey={account_key}'
    res = session.get(url)
    if res.status_code != 200:
        raise Exception(f'unable to get account balance, status: {res.status_code} {res.text}')
    
    payload = res.json()
    logger.debug(f'got account balance response: {payload}')
    return payload['a']['o']

def publish_result(content):
    if os.environ.get('TELEGRAM_DISABLED'):
        return
    tg_token = os.environ.get('TELEGRAM_TOKEN')
    if not tg_token:
        raise Exception('missing telegram token')
    
    tg_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not tg_chat_id:
        raise Exception('missing telegram chat id')
    
    res = requests.get("https://api.telegram.org/bot{token}/sendMessage?chat_id={chat}&text={text}".format(token=tg_token, chat=tg_chat_id, text=content))
    if res.status_code != 200:
        raise Exception('unable to send telegram notification, status: {} message: {}'.format(res.status_code, res.text))

    logger.debug('content was publish on telegram successfully')

def get_securities(session, account_key):
    url = f'{BASE_URL}/Account/GetAccountSecurities?accountKey={account_key}'
    res = session.get(url)
    if res.status_code != 200:
        raise Exception(f'unable to get account securities, status: {res.status_code} {res.text}')
    payload = res.json()
    return payload['a']['a']


def get_statistics_per_share(session, account_key):
    url = f'{BASE_URL}/Account/GetHoldings?accountKey={account_key}'
    res = session.get(url)
    if res.status_code != 200:
        raise Exception(f'unable to get account holdings, status: {res.status_code} {res.text}')
    
    payload = res.json()
    logger.debug(f'got account holdings response: {payload}')
    
    summary = ''
    total_cost = 0
    total_value = 0

    for holding in payload:        
        name = holding['i']
        if name == 'CASH DEPOSIT':
            logger.info(f"fetching account '{account_key}' securities information")
            securities = get_securities(session, account_key)
            logger.info(f"account '{account_key}' securities balance: {securities}")

            total_value += securities
            total_cost += securities
            summary += f"""{name}
    balance: {securities:,}
    ------------------
    """        
        else:            
            cost = holding['bh']
            if cost <= 0:
                continue
            value = holding['bf']
            
            profit = (value - cost)
            profit_precents = (profit / cost) * 100

            total_cost += cost
            total_value += value

            summary += f"""share: {name}
    balance: {value:,}
    deposits: {cost:,.2f}
    profit: {profit:,.2f}
    return: {profit_precents:,.2f}%
    ------------------
    """

    total_profit = (total_value - total_cost)
    total_return = (total_profit / total_cost) * 100
    summary += f"""Total:
balance: {total_value:,}
deposits: {total_cost:,.2f}
profit: {total_profit:,.2f}
return: {total_return:,.2f}%
"""
    return summary

try:
    logger.info('starting...')
    
    username = os.environ.get('MEITAV_USERNAME')
    if not username:
        raise Exception('username was not set')

    password = os.environ.get('MEITAV_PASSWORD')
    if not password:
        raise Exception('password was not set')

    account_key = os.environ.get('MEITAV_ACCOUNT_KEY')
    if not account_key:
        logger.info("no account key was supplied. don't worry, i'll try to figure it out")

    i=0
    succeeded = False
    while i < RETRIES and not succeeded:
        try:        
            logger.debug(f"authenticating user: '{username}'")
            auth_key = get_auth_key(username, password)
            session.headers.update({                
                'Authorization': f"Bearer {auth_key}",
            })
            
            if not account_key:
                logger.debug(f"try finding accounts keys for user: '{username}'")
                accounts = get_accounts_keys(session)
                logger.debug(f"found user accounts: '{accounts}'")
                if not accounts:
                    raise Exception('not accounts were found for this user')

                account_key = accounts[0]

            logger.info(f"fetching account '{account_key}' holdings information")
            holdings_info = get_statistics_per_share(session, account_key)
            logger.info(holdings_info)
            publish_result(f'Holding:\n {holdings_info}')

            succeeded = True
        except Exception as e:
            logger.error(f'failed to fetch balance on retry ({i+1}/{RETRIES}) error: {e}')
            time.sleep(RETRY_DELAY)
        i += 1    
        
    logger.info('done.')
except Exception as e:
    logger.error(e)