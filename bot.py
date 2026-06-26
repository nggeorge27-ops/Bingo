import asyncio
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "8639765842:AAGXjOV6yss8HlIb2NYG2y73FenMM4A5X38"

games = {}

def play_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🎮 PLAY", callback_data="play")]])

def play_again_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔄 PLAY AGAIN", callback_data="play")]])

def grid_keyboard(chat_id, user_id):
    game = games.get(chat_id, {})
    selected = set()
    if game and user_id in game.get('players', {}):
        selected = set(game['players'][user_id]['selected'])
    keyboard = []
    for start in range(1, 201, 8):
        row = []
        for n in range(start, min(start + 8, 201)):
            label = f"🟠{n}" if n in selected else str(n)
            row.append(InlineKeyboardButton(label, callback_data=f"pick_{n}"))
        keyboard.append(row)
    count = len(selected)
    keyboard.append([InlineKeyboardButton(f"✅ Done ({count}/3 selected)", callback_data="done")])
    return InlineKeyboardMarkup(keyboard)

def generate_card():
    ranges = [(1,15),(16,30),(31,45),(46,60),(61,75)]
    card = []
    for lo, hi in ranges:
        card.append(random.sample(range(lo, hi+1), 5))
    card[2][2] = 0
    return card

def embed_lucky(card, lucky):
    ranges = [(1,15),(16,30),(31,45),(46,60),(61,75)]
    for ln in lucky:
        for ci,(lo,hi) in enumerate(ranges):
            if lo <= ln <= hi:
                for row in range(5):
                    if card[ci][row] not in lucky and card[ci][row] != 0:
                        card[ci][row] = ln
                        break
                break
    return card

def card_text(card, called=None, win=False):
    if called is None: called = set()
    lines = ["🔵B  🟣I  🟡N  🟢G  🟠O", "─"*20]
    for row in range(5):
        cells = []
        for col in range(5):
            v = card[col][row]
            if v == 0:
                cells.append(" ⭐ ")
            elif v in called:
                cells.append("🟩" if win else "✅")
            else:
                cells.append(f"{v:3}")
        lines.append(" ".join(cells))
    return "\n".join(lines)

def check_win(card, called):
    def hit(v): return v == 0 or v in called
    for row in range(5):
        if all(hit(card[col][row]) for col in range(5)): return True
    for col in range(5):
        if all(hit(card[col][row]) for row in range(5)): return True
    if all(hit(card[i][i]) for i in range(5)): return True
    if all(hit(card[i][4-i]) for i in range(5)): return True
    corners = [card[0][0],card[4][0],card[0][4],card[4][4]]
    if all(hit(c) for c in corners): return True
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎱 *Welcome to BINGO!*\n\nTap PLAY to join a game!",
        reply_markup=play_keyboard(), parse_mode='Markdown')

async def play_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    user = query.from_user
    if chat_id not in games or games[chat_id]['state'] == 'ended':
        games[chat_id] = {'state': 'waiting', 'players': {}, 'called': [], 'card_counter': 0}
    game = games[chat_id]
    if game['state'] == 'playing':
        await query.answer("Game already started! Wait for next round.", show_alert=True)
        return
    if user.id not in game['players']:
        game['players'][user.id] = {'name': user.first_name, 'selected': [], 'card': None, 'card_no': 0}
    else:
        game['players'][user.id]['selected'] = []
        game['players'][user.id]['card'] = None
    await query.message.reply_text(
        f"🎯 *{user.first_name}, pick 1-3 lucky numbers (1-200)!*\n"
        f"Tap numbers below, then tap Done\n\nSelected: none yet",
        reply_markup=grid_keyboard(chat_id, user.id), parse_mode='Markdown')

async def pick_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    user = query.from_user
    number = int(query.data.split("_")[1])
    game = games.get(chat_id)
    if not game or user.id not in game['players']:
        await query.answer("Tap PLAY first!", show_alert=True)
        return
    player = game['players'][user.id]
    selected = player['selected']
    if number in selected:
        selected.remove(number)
        await query.answer(f"Removed {number}")
    elif len(selected) >= 3:
        await query.answer("Max 3 numbers! Remove one first.", show_alert=True)
        return
    else:
        selected.append(number)
        await query.answer(f"{number} selected!")
    sel_text = ", ".join(str(n) for n in selected) if selected else "none yet"
    try:
        await query.edit_message_text(
            f"🎯 *{user.first_name}, pick 1-3 lucky numbers (1-200)!*\n"
            f"Tap numbers below, then tap Done\n\nSelected: *{sel_text}*",
            reply_markup=grid_keyboard(chat_id, user.id), parse_mode='Markdown')
    except: pass

async def done_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    user = query.from_user
    game = games.get(chat_id)
    if not game or user.id not in game['players']:
        await query.answer("Tap PLAY first!", show_alert=True)
        return
    player = game['players'][user.id]
    if player['card'] is not None:
        await query.answer("You already have a card!", show_alert=True)
        return
    game['card_counter'] += 1
    card = generate_card()
    if player['selected']:
        card = embed_lucky(card, player['selected'])
    player['card'] = card
    player['card_no'] = game['card_counter']
    lucky_text = f"Lucky: {', '.join(str(n) for n in player['selected'])}" if player['selected'] else "No lucky numbers"
    ct = card_text(card)
    await query.edit_message_text(
        f"🃏 *{user.first_name} - Card #{player['card_no']}*\n"
        f"{lucky_text}\n\n```\n{ct}\n```\nWaiting for game to start...",
        parse_mode='Markdown')
    await query.answer("Card ready!")
    ready = {uid: p for uid, p in game['players'].items() if p['card'] is not None}
    count = len(ready)
    bot = context.bot
    if count < 2:
        await bot.send_message(chat_id,
            f"✅ *{user.first_name}* is ready! (Card #{player['card_no']})\n"
            f"👥 {count} player ready - need at least 2!\nOthers tap /start to join!",
            parse_mode='Markdown')
    else:
        if game['state'] == 'waiting':
            game['state'] = 'countdown'
            await bot.send_message(chat_id,
                f"✅ *{user.first_name}* is ready!\n👥 {count} players ready!\n"
                f"⏳ Game starts in *30 seconds!*\nOthers can still tap /start to join!",
                parse_mode='Markdown')
            asyncio.create_task(countdown(bot, chat_id))
        else:
            await bot.send_message(chat_id,
                f"✅ *{user.first_name}* joined! (Card #{player['card_no']})\n👥 {count} players ready!",
                parse_mode='Markdown')

async def countdown(bot, chat_id):
    await asyncio.sleep(20)
    game = games.get(chat_id)
    if not game or game['state'] != 'countdown': return
    ready = sum(1 for p in game['players'].values() if p['card'])
    await bot.send_message(chat_id, f"⏳ *10 seconds left!* ({ready} players ready)", parse_mode='Markdown')
    await asyncio.sleep(10)
    game = games.get(chat_id)
    if not game or game['state'] != 'countdown': return
    ready_players = {uid: p for uid, p in game['players'].items() if p['card']}
    if len(ready_players) < 2:
        await bot.send_message(chat_id, "❌ Not enough players! Game cancelled.\n\nTap /start to try again!")
        games.pop(chat_id, None)
        return
    game['state'] = 'playing'
    names = [p['name'] for p in ready_players.values()]
    await bot.send_message(chat_id,
        f"🚀 *BINGO STARTS NOW!*\n\n👥 Players: {', '.join(names)}\n\n"
        f"🎱 Number called every 5 seconds\nFirst to complete row/column/diagonal/4 corners wins! 🏆",
        parse_mode='Markdown')
    asyncio.create_task(call_loop(bot, chat_id))

async def call_loop(bot, chat_id):
    game = games.get(chat_id)
    if not game: return
    numbers = list(range(1, 201))
    random.shuffle(numbers)
    for number in numbers:
        game = games.get(chat_id)
        if not game or game['state'] != 'playing': return
        game['called'].append(number)
        called_set = set(game['called'])
        await bot.send_message(chat_id,
            f"🎱 *{number}*\nCalled: {len(game['called'])}/200  |  Last 5: {game['called'][-5:]}",
            parse_mode='Markdown')
        for uid, player in list(game['players'].items()):
            if player['card'] and check_win(player['card'], called_set):
                if game.get('state') == 'playing':
                    await announce_winner(bot, chat_id, uid)
                    return
        await asyncio.sleep(5)
    game = games.get(chat_id)
    if game and game['state'] == 'playing':
        await bot.send_message(chat_id, "🏁 All 200 numbers called! No winner.", reply_markup=play_again_keyboard())
        games.pop(chat_id, None)

async def announce_winner(bot, chat_id, winner_uid):
    game = games.get(chat_id)
    if not game: return
    game['state'] = 'ended'
    player = game['players'][winner_uid]
    called_set = set(game['called'])
    ct = card_text(player['card'], called_set, win=True)
    await bot.send_message(chat_id,
        f"👑🎉 *BINGO! {player['name']} WINS!* 🎉👑\n\n"
        f"🃏 *CARTEL #{player['card_no']}*\n\n```\n{ct}\n```\n\n"
        f"🎱 Numbers called: {len(game['called'])}/200\n"
        f"Tap below to play again! 👇",
        reply_markup=play_again_keyboard(), parse_mode='Markdown')
    games.pop(chat_id, None)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(play_pressed, pattern="^play$"))
    app.add_handler(CallbackQueryHandler(pick_number, pattern=r"^pick_\d+$"))
    app.add_handler(CallbackQueryHandler(done_pressed, pattern="^done$"))
    print("Bingo Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
