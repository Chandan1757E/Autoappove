import requests
import time
import logging
import json
import os
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = '6990761692:AAGFO6kNDTOOM6fOVbveugIAWjwln-je7zM'
API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}/'

# Admin and Owner configuration
ADMIN_USER_ID = '1805971602'
OWNER_USER_ID = '1614927658'
AUTHORIZED_USERS = [ADMIN_USER_ID, OWNER_USER_ID]

# Channel name
CHANNEL_NAME = "Techno Beat's"

# File to store user data
USER_DATA_FILE = 'users.json'

def load_user_data():
    """Load user data from file"""
    try:
        if os.path.exists(USER_DATA_FILE):
            with open(USER_DATA_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading user data: {e}")
    return {'users': [], 'last_activity': {}}

def save_user_data(user_data):
    """Save user data to file"""
    try:
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(user_data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving user data: {e}")

def add_user(user_id, user_name):
    """Add user to database"""
    user_data = load_user_data()
    
    # Check if user already exists
    user_exists = False
    for user in user_data['users']:
        if user['id'] == user_id:
            user_exists = True
            break
    
    # Add new user if doesn't exist
    if not user_exists:
        user_data['users'].append({
            'id': user_id,
            'name': user_name,
            'joined_at': time.time(),
            'first_join_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    
    # Update last activity
    if 'last_activity' not in user_data:
        user_data['last_activity'] = {}
    
    user_data['last_activity'][str(user_id)] = time.time()
    
    save_user_data(user_data)
    if not user_exists:
        logger.info(f"Added user {user_name} (ID: {user_id}) to database")

def update_user_activity(user_id):
    """Update user's last activity timestamp"""
    user_data = load_user_data()
    
    if 'last_activity' not in user_data:
        user_data['last_activity'] = {}
    
    user_data['last_activity'][str(user_id)] = time.time()
    save_user_data(user_data)

def is_authorized(user_id):
    """Check if user is authorized (admin or owner)"""
    return str(user_id) in AUTHORIZED_USERS

def get_active_users_count(days=7):
    """Get count of active users in last N days"""
    user_data = load_user_data()
    
    if 'last_activity' not in user_data or not user_data['last_activity']:
        return 0
    
    cutoff_time = time.time() - (days * 24 * 60 * 60)
    active_count = 0
    
    for user_id, last_active in user_data['last_activity'].items():
        if last_active >= cutoff_time:
            active_count += 1
    
    return active_count

def get_daily_join_stats(days=7):
    """Get daily join statistics for last N days"""
    user_data = load_user_data()
    daily_stats = {}
    
    for user in user_data.get('users', []):
        if 'first_join_date' in user:
            join_date = user['first_join_date'].split()[0]  # Get only date part
            daily_stats[join_date] = daily_stats.get(join_date, 0) + 1
    
    # Sort by date and get last N days
    sorted_dates = sorted(daily_stats.keys(), reverse=True)
    return {date: daily_stats[date] for date in sorted_dates[:days]}

def bot_request(method, params=None):
    """Helper function to send parameters to Telegram API"""
    if params is None:
        params = {}
    
    url = f"{API_URL}{method}"
    try:
        response = requests.get(url, params=params, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Error in bot_request: {e}")
        return {'ok': False}

def get_updates(offset=None):
    """Get new updates from Telegram"""
    params = {'timeout': 30, 'allowed_updates': ['chat_join_request', 'message']}
    if offset:
        params['offset'] = offset
    
    try:
        response = requests.get(f"{API_URL}getUpdates", params=params, timeout=35)
        return response.json()
    except Exception as e:
        logger.error(f"Error getting updates: {e}")
        return {'ok': False, 'result': []}

def handle_updates():
    """Main function to handle updates"""
    last_update_id = None
    
    while True:
        try:
            # Get updates
            updates_data = get_updates(offset=last_update_id)
            
            if not updates_data.get('ok'):
                logger.error("Failed to get updates")
                time.sleep(5)
                continue
            
            updates = updates_data.get('result', [])
            
            for update in updates:
                last_update_id = update['update_id'] + 1
                
                # Handle chat join request
                if 'chat_join_request' in update:
                    handle_join_request(update['chat_join_request'])
                
                # Handle member departure
                if ('message' in update and 
                    'left_chat_member' in update['message']):
                    handle_left_member(update['message'])
                
                # Handle broadcast command
                if ('message' in update and 
                    'text' in update['message'] and
                    update['message']['text'].startswith('/broadcast')):
                    update_user_activity(update['message']['from']['id'])
                    handle_broadcast(update['message'])
                
                # Handle stats command
                if ('message' in update and 
                    'text' in update['message'] and
                    update['message']['text'].startswith('/stats')):
                    update_user_activity(update['message']['from']['id'])
                    handle_stats(update['message'])
                
                # Handle active command
                if ('message' in update and 
                    'text' in update['message'] and
                    update['message']['text'].startswith('/active')):
                    update_user_activity(update['message']['from']['id'])
                    handle_active_stats(update['message'])
            
            # Small delay to avoid hitting rate limits
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(5)

def handle_join_request(chat_join_request):
    """Handle and automatically approve join requests"""
    try:
        chat_id = chat_join_request['chat']['id']
        user_id = chat_join_request['from']['id']
        user_name = chat_join_request['from'].get('first_name', 'User')
        
        logger.info(f"Processing join request from user {user_id}")
        
        # Approve join request
        result = bot_request('approveChatJoinRequest', {
            'chat_id': chat_id,
            'user_id': user_id
        })
        
        if result.get('ok'):
            logger.info(f"Successfully approved join request for user {user_id}")
            
            # Add user to database and update activity
            add_user(user_id, user_name)
            
            # Welcome message to user
            welcome_text = f"Welcome {user_name} to {CHANNEL_NAME}! \nYou've officially joined our family — glad to have you here ❤️‍🔥"
            send_result = bot_request('sendMessage', {
                'chat_id': user_id,
                'text': welcome_text
            })
            
            if not send_result.get('ok'):
                logger.warning(f"Could not send welcome message to user {user_id}: {send_result}")
        else:
            logger.error(f"Failed to approve join request: {result}")
            
    except Exception as e:
        logger.error(f"Error handling join request: {e}")

def handle_left_member(message):
    """Handle when a member leaves the chat"""
    try:
        left_user = message['left_chat_member']
        user_id = left_user['id']
        user_name = left_user.get('first_name', 'User')
        
        logger.info(f"User {user_name} left the chat")
        
        # Leave message
        goodbye_text = f"{user_name} has left {CHANNEL_NAME}.\nIf there was any issue, feel free to share — I'm here to help Contact: @techno_beats"
        
        send_result = bot_request('sendMessage', {
            'chat_id': user_id,
            'text': goodbye_text
        })
        
        if send_result.get('ok'):
            logger.info(f"Goodbye message sent to {user_name}")
        else:
            logger.warning(f"Could not send goodbye message to user {user_id}: {send_result}")
        
    except Exception as e:
        logger.error(f"Error handling left member: {e}")

def handle_broadcast(message):
    """Handle broadcast command to send message to all users"""
    try:
        user_id = str(message['from']['id'])
        user_name = message['from'].get('first_name', 'User')
        
        # Check if user is authorized
        if not is_authorized(user_id):
            bot_request('sendMessage', {
                'chat_id': user_id,
                'text': "❌ You are not authorized to use this command."
            })
            return
        
        # Extract broadcast message
        command_parts = message['text'].split(' ', 1)
        if len(command_parts) < 2:
            bot_request('sendMessage', {
                'chat_id': user_id,
                'text': "❌ Usage: /broadcast <message>"
            })
            return
        
        broadcast_message = command_parts[1]
        
        # Load all users
        user_data = load_user_data()
        users = user_data.get('users', [])
        
        if not users:
            bot_request('sendMessage', {
                'chat_id': user_id,
                'text': "❌ No users found in database."
            })
            return
        
        # Send confirmation
        bot_request('sendMessage', {
            'chat_id': user_id,
            'text': f"📢 Starting broadcast to {len(users)} users..."
        })
        
        # Send broadcast to all users
        success_count = 0
        fail_count = 0
        
        for user in users:
            try:
                result = bot_request('sendMessage', {
                    'chat_id': user['id'],
                    'text': broadcast_message
                })
                
                if result.get('ok'):
                    success_count += 1
                else:
                    fail_count += 1
                
                # Small delay to avoid rate limits
                time.sleep(0.1)
                
            except Exception as e:
                fail_count += 1
                logger.error(f"Error sending broadcast to {user['name']}: {e}")
        
        # Send report to admin
        bot_request('sendMessage', {
            'chat_id': user_id,
            'text': f"📩 Broadcast Complete!\n\n✅ Success: {success_count}\n❌ Failed: {fail_count}\n📝 Total: {len(users)}"
        })
        
        logger.info(f"Broadcast completed by {user_name}: {success_count} success, {fail_count} failed")
        
    except Exception as e:
        logger.error(f"Error handling broadcast: {e}")

def handle_stats(message):
    """Handle stats command to show bot statistics"""
    try:
        user_id = str(message['from']['id'])
        
        # Check if user is authorized
        if not is_authorized(user_id):
            bot_request('sendMessage', {
                'chat_id': user_id,
                'text': "❌ You are not authorized to use this command."
            })
            return
        
        # Load user data
        user_data = load_user_data()
        users = user_data.get('users', [])
        
        # Calculate stats
        total_users = len(users)
        active_24h = get_active_users_count(1)
        active_7d = get_active_users_count(7)
        active_30d = get_active_users_count(30)
        
        # Get bot info
        bot_info = bot_request('getMe')
        bot_name = bot_info.get('result', {}).get('first_name', 'Bot')
        bot_username = bot_info.get('result', {}).get('username', '')
        
        # Get daily join stats
        daily_joins = get_daily_join_stats(7)
        daily_stats_text = ""
        for date, count in daily_joins.items():
            daily_stats_text += f"  📅 {date}: {count} users\n"
        
        if not daily_stats_text:
            daily_stats_text = "  No join data available\n"
        
        # Send stats
        stats_text = f"""🤖 {CHANNEL_NAME} Bot Statistics

📊 User Statistics:
👥 Total Users: {total_users}
🟢 Active (24h): {active_24h}
🟡 Active (7 days): {active_7d}
🟠 Active (30 days): {active_30d}

📈 Recent Joins (Last 7 days):
{daily_stats_text}
🔧 Bot Information:
🤖 Bot: @{bot_username}
📢 Channel: {CHANNEL_NAME}
🔄 Bot Status: ✅ Active and Running

Available Commands:
/broadcast - Send message to all users
/stats - Show bot statistics
/active - Detailed active user analysis"""
        
        bot_request('sendMessage', {
            'chat_id': user_id,
            'text': stats_text
        })
        
        logger.info(f"Stats command used by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error handling stats: {e}")

def handle_active_stats(message):
    """Handle active command to show detailed user activity statistics"""
    try:
        user_id = str(message['from']['id'])
        
        # Check if user is authorized
        if not is_authorized(user_id):
            bot_request('sendMessage', {
                'chat_id': user_id,
                'text': "❌ You are not authorized to use this command."
            })
            return
        
        # Load user data
        user_data = load_user_data()
        users = user_data.get('users', [])
        
        # Calculate active users for different time periods
        time_periods = [
            ("Last 24 hours", 1),
            ("Last 3 days", 3),
            ("Last 7 days", 7),
            ("Last 15 days", 15),
            ("Last 30 days", 30),
            ("Last 60 days", 60),
            ("Last 90 days", 90)
        ]
        
        active_stats_text = "📊 Active User Statistics\n\n"
        
        for period_name, days in time_periods:
            active_count = get_active_users_count(days)
            percentage = (active_count / len(users)) * 100 if users else 0
            active_stats_text += f"{period_name}:\n"
            active_stats_text += f"  👥 {active_count} users ({percentage:.1f}%)\n\n"
        
        # Total users
        active_stats_text += f"Total Registered Users: {len(users)}\n\n"
        
        # Recent activity breakdown
        if 'last_activity' in user_data:
            now = time.time()
            today = 0
            yesterday = 0
            this_week = 0
            this_month = 0
            
            for user_id_str, last_active in user_data['last_activity'].items():
                time_diff = now - last_active
                
                if time_diff <= 86400:  # 24 hours
                    today += 1
                if time_diff <= 172800:  # 48 hours
                    yesterday += 1
                if time_diff <= 604800:  # 7 days
                    this_week += 1
                if time_diff <= 2592000:  # 30 days
                    this_month += 1
            
            active_stats_text += f"Activity Breakdown:\n"
            active_stats_text += f"  🟢 Today: {today} users\n"
            active_stats_text += f"  🟡 Yesterday: {yesterday} users\n"
            active_stats_text += f"  🟠 This Week: {this_week} users\n"
            active_stats_text += f"  🔴 This Month: {this_month} users\n"
        
        bot_request('sendMessage', {
            'chat_id': user_id,
            'text': active_stats_text
        })
        
        logger.info(f"Active stats command used by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error handling active stats: {e}")

def check_bot_info():
    """Check if bot token is valid"""
    try:
        result = bot_request('getMe')
        if result.get('ok'):
            bot_info = result['result']
            logger.info(f"Bot is running: @{bot_info['username']} ({bot_info['first_name']})")
            return True
        else:
            logger.error(f"Invalid bot token: {result}")
            return False
    except Exception as e:
        logger.error(f"Error checking bot info: {e}")
        return False

if __name__ == '__main__':
    print("🤖 Starting Techno Beat's Telegram Bot...")
    print("=" * 50)
    
    # Check if bot token is valid
    if not check_bot_info():
        print("❌ Failed to start bot. Please check your bot token.")
        exit(1)
    
    print(f"✅ Bot is running successfully!")
    print(f"📢 Channel: {CHANNEL_NAME}")
    print(f"👑 Owner ID: {OWNER_USER_ID}")
    print(f"⚡ Admin ID: {ADMIN_USER_ID}")
    print("=" * 50)
    print("🔄 Bot is now listening for updates...")
    print("✅ Join request auto-approval: ENABLED")
    print("📢 Broadcast command: ENABLED")
    print("📊 Stats command: ENABLED")
    print("📈 Active user tracking: ENABLED")
    print("=" * 50)
    
    # Start handling updates
    handle_updates()