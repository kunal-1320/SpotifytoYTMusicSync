import logging
import json
import os
import asyncio
from spotify_scraper import SpotifyClient
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from datetime import datetime
from flask import Flask
from threading import Thread

# --- FAKE WEB SERVER (FOR RENDER) ---
app = Flask('')

@app.route('/')
def home():
    return "I am alive! The bot is running."

def run_http():
    # Render assigns a port automatically via environment variable, or defaults to 8080
    port_to_use = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port_to_use)

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# --- CONFIGURATION ---
# No API keys needed! SpotifyScraper works without authentication.
# List of public playlist URLs to monitor
TARGET_PLAYLISTS = [
    
    "https://open.spotify.com/playlist/478BJCqpYQbRiykf7Eiyy3",
    "https://open.spotify.com/playlist/7DNHlHAEBDT2X3KlZL37eF",
    "https://open.spotify.com/playlist/4Yea4r8ikm3tlt94REeebO",
    "https://open.spotify.com/playlist/6ysV3igBXcX6F3A1P1fwyr",
    "https://open.spotify.com/playlist/6zEcBH3X2RkTtSQI4fTn8v",
    "https://open.spotify.com/playlist/2mDOIweym9G4Uwww6pM7jI",
    "https://open.spotify.com/playlist/729v7DfFsNrSRvY5QCQad2",

"https://open.spotify.com/playlist/2XgBQIJKjArcbF2Smfjxc2",

]

# --- TELEGRAM CONFIG ---
TELEGRAM_BOT_TOKEN = "8385519811:AAGs1cq5t6x4VkAx7KdGLa-viXBB56lPleQ"
ALLOWED_USER_ID = 6425844407

# --- SETTINGS ---
CHECK_INTERVAL_SEC = 300
STATE_FILE = "playlist_state.json"

# --- BOT VERSION & STATE ---
BOT_VERSION = "6.0"
BOT_START_TIME = datetime.now()
MONITORING_PAUSED = False
NEW_SONGS_DETECTED = 0

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- SPOTIFY SCRAPER HELPERS ---

def scrape_playlist(playlist_url):
    """Scrape a playlist using SpotifyScraper. Returns playlist info dict or None on error."""
    client = None
    try:
        client = SpotifyClient()
        playlist = client.get_playlist_info(playlist_url)
        return playlist
    except Exception as e:
        logging.error(f"Error scraping playlist {playlist_url}: {e}")
        return None
    finally:
        if client:
            try:
                client.close()
            except Exception:
                pass

def get_playlist_id_from_url(url):
    """Extract playlist ID from a Spotify URL."""
    # URL format: https://open.spotify.com/playlist/{id}
    return url.strip().rstrip('/').split('/')[-1].split('?')[0]

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f: return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, 'w') as f: json.dump(state, f, indent=4)

def get_track_key(track):
    """Create a unique key for a track based on name + artist."""
    name = track.get('name', 'Unknown')
    artist = track.get('artists', [{}])[0].get('name', 'Unknown') if track.get('artists') else 'Unknown'
    return f"{name} ||| {artist}"

def initialize_state():
    """Initialize state file with current track data on first run (no notifications sent)."""
    if os.path.exists(STATE_FILE):
        return  # State already exists, don't overwrite
    
    logging.info("First run detected - initializing state with current playlist data...")
    state = {}
    for url in TARGET_PLAYLISTS:
        pid = get_playlist_id_from_url(url)
        playlist = scrape_playlist(url)
        if playlist:
            tracks = playlist.get('tracks', [])
            track_keys = [get_track_key(t) for t in tracks]
            state[pid] = {
                'count': len(tracks),
                'track_keys': track_keys
            }
            logging.info(f"  Initialized '{playlist.get('name', '?')}' with {len(tracks)} tracks")
        else:
            logging.warning(f"  Could not scrape playlist {pid} during initialization")
    
    save_state(state)
    logging.info("State initialization complete.")

# --- BUTTONS ---
MAIN_KEYBOARD = [['🔍 Check & Status', '📂 Playlists'], ['📊 Stats', '⚙️ Config'], ['⏸️ Pause', '▶️ Resume'], ['🎵 Spotilast']]
MARKUP = ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)

# --- BOT COMMANDS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ **Access Denied**")
        return
    welcome_msg = f"""🛰️ **Utility Terminal v{BOT_VERSION}**

✅ System is online and monitoring.
⏱️ Pulse: {CHECK_INTERVAL_SEC}s
🔓 Mode: No-API (Web Scraper)

💡 Use the buttons below or type /help."""
    await update.message.reply_text(welcome_msg, parse_mode='Markdown', reply_markup=MARKUP)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ **Access Denied** - You are not authorized to use this bot.")
        return
    help_text = """📖 **Terminal Menu:**

**🔍 Monitor:**
- Check & Status: Manual scan + system report
- Playlists: List active collections
- Stats: Resource metrics

**⚙️ Controls:**
- Pause/Resume: Toggle monitoring
- Config: View parameters
- About: System info"""
    await update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=MARKUP)

async def get_status_msg():
    global MONITORING_PAUSED
    uptime = datetime.now() - BOT_START_TIME
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    status_icon = "⏸️" if MONITORING_PAUSED else "✅"
    status_text = "SUSPENDED" if MONITORING_PAUSED else "ACTIVE"
    
    return f"""📊 **System Status:**

{status_icon} Monitor: **{status_text}**
⏱️ Interval: {CHECK_INTERVAL_SEC}s
⏰ Uptime: {hours}h {minutes}m {seconds}s
🚨 Events Logged: {NEW_SONGS_DETECTED}
🔓 Mode: No-API (Web Scraper)

{'⚠️ Monitoring suspended.' if MONITORING_PAUSED else '✅ Monitoring active.'}"""

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ **Access Denied**")
        return
    
    await update.message.reply_text("📊 **Retrieving metrics...**")
    try:
        total_playlists = len(TARGET_PLAYLISTS)
        state = load_state()
        monitored_playlists = len(state)
        
        uptime = datetime.now() - BOT_START_TIME
        days = uptime.days
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        
        stats_msg = f"""📈 **Resource Metrics:**

📂 Collections: {total_playlists}
📊 Monitored: {monitored_playlists}
🚨 Events: {NEW_SONGS_DETECTED}
⏰ Uptime: {days}d {hours % 24}h {minutes}m
📅 Launch: {BOT_START_TIME.strftime('%Y-%m-%d %H:%M:%S')}
🔓 Mode: No-API (Web Scraper)"""
        await update.message.reply_text(stats_msg, parse_mode='Markdown', reply_markup=MARKUP)
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching statistics: {e}")

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ **Access Denied**")
        return
    
    about_msg = f"""ℹ️ **System Information**

🤖 Build: {BOT_VERSION}
📝 Status: Optimized monitoring utility.
🔓 Mode: No-API (Web Scraper)

✨ **Core:**
• Pulse tracking
• Event logging
• Remote terminal access
• No Spotify API key required"""
    await update.message.reply_text(about_msg, parse_mode='Markdown', reply_markup=MARKUP)

async def config_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ **Access Denied**")
        return
    
    config_msg = f"""⚙️ **Configuration:**

🤖 **Parameters:**
• Interval: {CHECK_INTERVAL_SEC}s
• Playlists: {len(TARGET_PLAYLISTS)} configured
• Auth: `None required (Scraper)`

🔔 **State:**
• Status: {'⏸️ SUSPENDED' if MONITORING_PAUSED else '✅ ACTIVE'}"""
    await update.message.reply_text(config_msg, parse_mode='Markdown', reply_markup=MARKUP)

async def pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ **Access Denied**")
        return
    
    global MONITORING_PAUSED
    if MONITORING_PAUSED:
        await update.message.reply_text("ℹ️ System already suspended.")
    else:
        MONITORING_PAUSED = True
        await update.message.reply_text("⏸️ **Monitoring Suspended**", reply_markup=MARKUP)

async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ **Access Denied**")
        return
    
    global MONITORING_PAUSED
    if not MONITORING_PAUSED:
        await update.message.reply_text("ℹ️ System active.")
    else:
        MONITORING_PAUSED = False
        await update.message.reply_text("▶️ **Monitoring Resumed**", reply_markup=MARKUP)

async def force_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ **Access Denied**")
        return
    await update.message.reply_text("🔎 **Scanning pulse point...**", parse_mode='Markdown')
    await monitor_task(context)
    status_msg = await get_status_msg()
    await update.message.reply_text(status_msg, parse_mode='Markdown', reply_markup=MARKUP)

async def list_playlists(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ **Access Denied**")
        return
    
    await update.message.reply_text("📂 **Retrieving active collections...**")
    try:
        playlist_items = []
        for url in TARGET_PLAYLISTS:
            playlist = scrape_playlist(url)
            if playlist:
                playlist_items.append({
                    'name': playlist.get('name', 'Unknown'),
                    'track_count': playlist.get('track_count', 0),
                    'url': url,
                    'tracks': playlist.get('tracks', [])
                })
            else:
                pid = get_playlist_id_from_url(url)
                playlist_items.append({
                    'name': f'Playlist ({pid[:8]}...)',
                    'track_count': '?',
                    'url': url,
                    'tracks': []
                })
        
        context.user_data['playlist_cache'] = playlist_items
        msg = "📂 **Active Collections:**\n\n"
        
        for idx, item in enumerate(playlist_items):
            msg += f"{idx+1}. **{item['name']}** ({item['track_count']} items)\n"
        
        msg += "\n💡 *Usage:* Type `/latest 1` to view items in a collection."
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=MARKUP)
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching playlists: {e}")

async def show_latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ **Access Denied**")
        return
    if not context.args:
        await update.message.reply_text("⚠️ **Usage:** `/latest <number>`", parse_mode='Markdown')
        return
    try:
        selection_index = int(context.args[0]) - 1
        cached_playlists = context.user_data.get('playlist_cache')
        if not cached_playlists or selection_index < 0 or selection_index >= len(cached_playlists):
            await update.message.reply_text("❌ Selection out of range. Use /playlists first.")
            return
        target = cached_playlists[selection_index]
    except ValueError:
        await update.message.reply_text("❌ Invalid input.", parse_mode='Markdown')
        return

    await update.message.reply_text(f"📥 Fetching all songs for '{target['name']}'...")
    try:
        # If tracks were already cached from playlist listing, use those
        tracks = target.get('tracks', [])
        if not tracks:
            # Re-scrape to get fresh data
            playlist = scrape_playlist(target['url'])
            if playlist:
                tracks = playlist.get('tracks', [])
        
        full_message = f"📂 **Items in '{target['name']}':**\n\n"
        for item in reversed(tracks):
            track_name = item.get('name', 'Unknown')
            artist_name = item.get('artists', [{}])[0].get('name', 'Unknown') if item.get('artists') else "Unknown"
            full_message += f"• {track_name} - {artist_name}\n"
        
        if not tracks:
            full_message += "📭 No tracks found or playlist is empty.\n"
        
        chunks = [full_message[i:i+4000] for i in range(0, len(full_message), 4000)]
        for chunk in chunks: await update.message.reply_text(chunk, reply_markup=MARKUP)
    except Exception as e: 
        await update.message.reply_text(f"❌ Error: {e}")

async def spotilast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Fetches and displays the most recently added song for all monitored playlists.
    """
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ **Access Denied**")
        return
    
    await update.message.reply_text("🎵 **Fetching Spotilast data...**\n⏳ This may take a moment.")
    
    results_message = "🎵 **Spotilast - Most Recent Songs**\n" + "="*40 + "\n\n"
    found_any = False
    
    for url in TARGET_PLAYLISTS:
        playlist = scrape_playlist(url)
        if not playlist:
            pid = get_playlist_id_from_url(url)
            results_message += f"📂 **Playlist ({pid[:8]}...)**\n"
            results_message += f"  ❌ Error: Could not scrape playlist.\n\n"
            continue
        
        found_any = True
        playlist_name = playlist.get('name', 'Unknown')
        tracks = playlist.get('tracks', [])
        
        results_message += f"📂 **{playlist_name}**\n"
        
        if tracks:
            last_track = tracks[-1]
            song_name = last_track.get('name', 'Unknown')
            artists = ', '.join([a.get('name', 'Unknown') for a in last_track.get('artists', [])]) or 'Unknown'
            
            results_message += f"  🎵 *{song_name}*\n"
            results_message += f"  🎤 {artists}\n\n"
        else:
            results_message += "  📭 This playlist is empty.\n\n"
    
    if not found_any:
        results_message += "ℹ️ Could not retrieve any playlists.\n"
    
    results_message += "\n" + "="*40 + "\n✅ **Done!**"
    
    chunks = [results_message[i:i+4000] for i in range(0, len(results_message), 4000)]
    for chunk in chunks:
        await update.message.reply_text(chunk, parse_mode='Markdown', reply_markup=MARKUP)

# --- BACKGROUND MONITOR ---

async def monitor_task(bot_context):
    """Monitor playlists for changes. bot_context can be a Context or Application (both have .bot)."""
    global MONITORING_PAUSED, NEW_SONGS_DETECTED
    
    # Skip monitoring if paused
    if MONITORING_PAUSED:
        return
    
    previous_state = load_state()
    current_state = {}
    
    try:
        for url in TARGET_PLAYLISTS:
            pid = get_playlist_id_from_url(url)
            playlist = scrape_playlist(url)
            
            if not playlist:
                # Keep old state on error so we don't lose track
                if pid in previous_state:
                    current_state[pid] = previous_state[pid]
                continue
            
            pname = playlist.get('name', f'Playlist ({pid[:8]}...)')
            tracks = playlist.get('tracks', [])
            current_track_keys = [get_track_key(t) for t in tracks]
            current_state[pid] = {
                'count': len(tracks),
                'track_keys': current_track_keys
            }
            
            # Get previous track keys
            prev_data = previous_state.get(pid)
            if prev_data is None:
                # First time seeing this playlist — initialize without notifications
                logging.info(f"New playlist detected: {pname} ({len(tracks)} tracks) — no notification on first scan.")
                continue
            
            # Handle migration from old format (plain integer) to new format (dict)
            if isinstance(prev_data, int):
                # Old format: just a count. Can't do name comparison, skip this cycle.
                logging.info(f"Migrating state for '{pname}' from old format. Will detect changes next cycle.")
                continue
            
            prev_track_keys = set(prev_data.get('track_keys', []))
            current_track_keys_set = set(current_track_keys)
            
            # Find genuinely new tracks (in current but not in previous)
            new_keys = current_track_keys_set - prev_track_keys
            
            if new_keys:
                logging.info(f"Found {len(new_keys)} new track(s) in '{pname}'")
                # Send notifications for new tracks
                for track in tracks:
                    key = get_track_key(track)
                    if key in new_keys:
                        track_name = track.get('name', 'Unknown')
                        artist = track.get('artists', [{}])[0].get('name', 'Unknown') if track.get('artists') else "Unknown"
                        msg = f"🚨 **Update Logged**\nSource: *{pname}*\nRef: *{track_name}* - *{artist}*"
                        try:
                            await bot_context.bot.send_message(chat_id=ALLOWED_USER_ID, text=msg, parse_mode='Markdown')
                            NEW_SONGS_DETECTED += 1
                        except Exception as send_err:
                            logging.error(f"Failed to send notification: {send_err}")
        
        save_state(current_state)
    except Exception as e: 
        logging.error(f"Monitor Error: {e}")

# --- BACKGROUND MONITOR LOOP (NO APScheduler NEEDED) ---

async def background_monitor(application):
    """Standalone asyncio loop that runs monitor_task every CHECK_INTERVAL_SEC."""
    logging.info(f"Background monitor started — checking every {CHECK_INTERVAL_SEC}s")
    # Wait a bit before first check so the bot is fully ready
    await asyncio.sleep(15)
    
    while True:
        try:
            logging.info("Background monitor: running scheduled check...")
            # Create a minimal context-like object that has bot access
            await monitor_task(application)
        except Exception as e:
            logging.error(f"Background monitor error: {e}")
        
        await asyncio.sleep(CHECK_INTERVAL_SEC)

# --- MAIN ENGINE ---

if __name__ == '__main__':
    # 1. Start the Fake Web Server in a separate thread
    keep_alive()

    # 2. Initialize playlist state on first run (won't spam existing songs)
    initialize_state()

    # 3. Start the Bot
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Register all command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('stats', stats_command))
    application.add_handler(CommandHandler('about', about_command))
    application.add_handler(CommandHandler('config', config_command))
    application.add_handler(CommandHandler('pause', pause_command))
    application.add_handler(CommandHandler('resume', resume_command))
    application.add_handler(CommandHandler('check', force_check))
    application.add_handler(CommandHandler('playlists', list_playlists))
    application.add_handler(CommandHandler('latest', show_latest))
    application.add_handler(CommandHandler('spotilast', spotilast_command))

    # Add MessageHandlers for Keyboard Buttons
    from telegram.ext import MessageHandler, filters
    async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        if text == '🔍 Check & Status': await force_check(update, context)
        elif text == '📂 Playlists': await list_playlists(update, context)
        elif text == '📊 Stats': await stats_command(update, context)
        elif text == '⚙️ Config': await config_command(update, context)
        elif text == '⏸️ Pause': await pause_command(update, context)
        elif text == '▶️ Resume': await resume_command(update, context)
        elif text == '🎵 Spotilast': await spotilast_command(update, context)

    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_buttons))

    # 4. Start background monitor as an asyncio task (no APScheduler needed)
    async def post_init(app):
        app.create_task(background_monitor(app))
    
    application.post_init = post_init
    
    print("🤖 Cloud Bot Started (No-API Scraper Mode)...")
    application.run_polling()
