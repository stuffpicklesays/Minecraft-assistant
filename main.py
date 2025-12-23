from javascript import require, On, Once, AsyncTask, once, off
mineflayer = require('mineflayer')
mcData = require('minecraft-data')('1.21')
pathfinder = require('mineflayer-pathfinder')

BOT_USERNAME = 'BarryTheBot'
bot = mineflayer.createBot({
    'host': '192.168.1.125',
    'port': 25564,
    'username': BOT_USERNAME,
    'hideErrors': False,
    'version': '1.21'
})

#load pathfinder plugin
bot.loadPlugin(pathfinder.pathfinder)
defaultMovements = pathfinder.Movements(bot, mcData)
# Avoid pathfinder auto-digging through hard blocks like stone; we dig targets manually
defaultMovements.canDig = False
bot.pathfinder.setMovements(defaultMovements)

STONE_LIKE_IDS = set([
    mcData.blocksByName['stone'].id,
    mcData.blocksByName['deepslate'].id
])

pathfinder_pkg = require('mineflayer-pathfinder')

# Extract the classes you need
pathfinder = pathfinder_pkg.pathfinder
Movements = pathfinder_pkg.Movements
GoalNear = pathfinder_pkg.goals.GoalNear

global is_looping
is_looping = False

def dbg(msg):
    # Console-only debug helper
    print(f"[DEBUG] {msg}")

def find(bot, message):
        try:
            args = message.split(" ")
            if len(args) < 2:
                bot.chat("Please specify a block name. Usage: !find <block_name>")
                return

            block_name = args[1]
            block = search_for_block(bot, block_name)

            if block:
                pos = block.position
                bot.chat(f"Found {block_name} at x:{int(pos.x)}, y:{int(pos.y)}, z:{int(pos.z)}")
            else:
                bot.chat(f"Could not find any {block_name} nearby.")

        except Exception as e:
            print(f"Error: {e}")
            bot.chat(f"Error finding block: {e}")

@On(bot, 'login')
def login(bot):
    bot_socket = bot._client.socket
    print(f"{BOT_USERNAME} has logged in to {bot_socket.server if bot_socket.server else bot_socket._host}")
    bot.chat('Hello World!')

@On(bot, 'error')
def error(bot, err):
    print(f"Error: {err}")

@On(bot, 'kicked')
def kicked(bot, reason, loggedIn):
    print(f"Kicked: {reason}")

def search_for_block(bot, block_name):
    try:
        block_id = mcData.blocksByName[block_name].id
    except KeyError:
        bot.chat(f"Block '{block_name}' not found in Minecraft data.")
        return None

    def is_exposed(block):
        # Prefer blocks with an open face so we do not need to mine through stone to reach them
        for dx, dy, dz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
            neighbor = bot.blockAt(block.position.offset(dx, dy, dz))
            if neighbor is None:
                return True
            if neighbor.boundingBox == 'empty':
                return True
            if neighbor.type in STONE_LIKE_IDS:
                continue
            if neighbor.diggable:
                return True
        return False

    # Gather several candidates and pick the first exposed one
    positions = bot.findBlocks({
        'matching': block_id,
        'maxDistance': 64,
        'count': 50
    })

    for pos in positions:
        candidate = bot.blockAt(pos)
        if candidate and is_exposed(candidate):
            return candidate

    # Fallback to any block if no exposed option exists
    return bot.findBlock({
        'matching': block_id,
        'maxDistance': 64
    })

gathering_active = False
current_gathering_block = None
gather_cycle = 0

def gather(bot, message):
    global gathering_active, current_gathering_block, gather_cycle
    
    args = message.split(" ")
    if len(args) < 2:
        bot.chat("Usage: !gather <block_name>")
        return

    block_name = args[1]
    gathering_active = True
    current_gathering_block = block_name
    gather_cycle += 1
    cycle_id = gather_cycle
    dbg(f"Gather start cycle={cycle_id} block={block_name}")
    
    bot.chat(f"Starting continuous gathering of {block_name}. Use !stop to interrupt.")
    gather_next_block(bot, block_name, cycle_id)

def gather_next_block(bot, block_name, cycle_id):
    global gathering_active

    dbg(f"gather_next_block cycle={cycle_id} active={gathering_active}")
    
    if not gathering_active:
        dbg(f"cycle={cycle_id} aborted: gathering not active")
        return
    
    block = search_for_block(bot, block_name)

    if not block:
        bot.chat(f"No more {block_name} found nearby. Stopping.")
        gathering_active = False
        dbg(f"cycle={cycle_id} no block found; stopping")
        return
    dbg(f"cycle={cycle_id} found block pos=({block.position.x},{block.position.y},{block.position.z})")

    dig_done = False

    def on_dig_complete(err):
        global gathering_active
        nonlocal dig_done
        dig_done = True
        if err:
            print(f"Dig error: {err}")
            bot.chat(f"Failed to dig {block_name}.")
            gathering_active = False
            dbg(f"cycle={cycle_id} dig error: {err}")
        else:
            bot.chat(f"Collected {block_name}!")
            dbg(f"cycle={cycle_id} dig complete")

            if gathering_active:
                # Clear current goal and schedule next search on the next physics tick
                bot.pathfinder.setGoal(None)
                bot.once('physicsTick', lambda *a: gather_next_block(bot, block_name, cycle_id))
            else:
                dbg(f"cycle={cycle_id} gathering no longer active after dig")

    def on_digging_completed_event(*args):
        if dig_done:
            dbg(f"cycle={cycle_id} diggingCompleted event but already handled")
            return
        dbg(f"cycle={cycle_id} diggingCompleted event fallback")
        if gathering_active:
            bot.pathfinder.setGoal(None)
            bot.once('physicsTick', lambda *a: gather_next_block(bot, block_name, cycle_id))

    def dig_watchdog(*args):
        if dig_done:
            return
        dbg(f"cycle={cycle_id} dig watchdog fired; restarting search")
        if gathering_active:
            bot.pathfinder.setGoal(None)
            bot.once('physicsTick', lambda *a: gather_next_block(bot, block_name, cycle_id))

    def on_goal_reached(*args):
        if not gathering_active:
            dbg(f"cycle={cycle_id} goal reached but gathering inactive")
            return
        bot.chat(f"Reached {block_name}. Digging...")
        dbg(f"cycle={cycle_id} goal reached -> digging")
        bot.lookAt(block.position) 

        # Track dig completion via callback, event, and watchdog
        nonlocal dig_done
        dig_done = False
        bot.once('diggingCompleted', on_digging_completed_event)
        bot.waitForTicks(10, dig_watchdog)
        bot.dig(block, on_dig_complete)

    goal = pathfinder.goals.GoalBlock(block.position.x, block.position.y, block.position.z)
    dbg(f"cycle={cycle_id} setting goal to block pos=({block.position.x},{block.position.y},{block.position.z})")
    bot.pathfinder.setGoal(goal)
    bot.once('goal_reached', on_goal_reached)

def stop_gathering(bot):
    global gathering_active
    gathering_active = False
    bot.pathfinder.setGoal(None)
    bot.chat("Gathering stopped.")
    dbg("Gather stopped by command")
Vec3 = require('vec3').Vec3

def plant(bot):
    if not hasattr(bot, 'inventory') or bot.inventory is None:
        print("Bot disconnected.")
        return

    seeds = bot.inventory.findInventoryItem(mcData.itemsByName['wheat_seeds'].id)
    if not seeds:
        print("No seeds found.")
        return

    print(f"I have {seeds.count} seeds.")
    
    bot.equip(seeds, 'hand')

    farmland_id = mcData.blocksByName['farmland'].id
    
    found_blocks = bot.findBlocks({
        'matching': farmland_id,
        'maxDistance': 32,
        'count': 10
    })

    target_block = None
    for pos in found_blocks:
        block = bot.blockAt(pos)
        block_above = bot.blockAt(pos.offset(0, 1, 0))
        if block_above and block_above.name == 'air':
            target_block = block
            break
    
    if not target_block:
        print("No valid farmland found.")
        return
    if not target_block:
        print("No valid farmland found.")
        return

    distance = bot.entity.position.distanceTo(target_block.position)

    if distance > 4.5:
        bot.chat("Moving closer to plant...")
        
        # Setup navigation movements
        defaultMove = Movements(bot, mcData)
        bot.pathfinder.setMovements(defaultMove)
        
        goal = GoalNear(target_block.position.x, target_block.position.y, target_block.position.z, 3)
        
        bot.pathfinder.setGoal(goal)

        return 

    bot.equip(seeds, 'hand')
    p = target_block.position
    
    def on_place_finished(err):
        if err: print(f"Error: {err}")
        else: bot.chat("Planted!")

    try:
        bot.placeBlock(target_block, Vec3(0, 1, 0), on_place_finished)
    except Exception as e:
        print(f"Error: {e}")





def start_farming_loop(bot):
    global is_looping
    if is_looping: return
    is_looping = True
    bot.chat("Starting farming loop!")
    plant_cycle(bot)

def stop_farming_loop(bot):
    global is_looping
    is_looping = False
    bot.chat("Stopping farming loop.")
    bot.pathfinder.setGoal(None) # Stop moving

def plant_cycle(bot):
    global is_looping
    if not is_looping: return

    seeds = bot.inventory.findInventoryItem(mcData.itemsByName['wheat_seeds'].id)
    if not seeds:
        bot.chat("No seeds left! Stopping.")
        is_looping = False
        return

    farmland_id = mcData.blocksByName['farmland'].id
    found_blocks = bot.findBlocks({
        'matching': farmland_id,
        'maxDistance': 32,
        'count': 20
    })

    target_block = None
    for pos in found_blocks:
        block = bot.blockAt(pos)
        block_above = bot.blockAt(pos.offset(0, 1, 0))
        if block_above and block_above.name == 'air':
            target_block = block
            break
    
    if not target_block:
        bot.chat("No empty farmland found. Retrying in 5s...")
        bot.setTimeout(lambda: plant_cycle(bot), 5000)
        return


    dist = bot.entity.position.distanceTo(target_block.position)
    if dist > 4.0:
        goal = GoalNear(target_block.position.x, target_block.position.y, target_block.position.z, 3)
        bot.pathfinder.setGoal(goal)

        def on_goal_reached(err=None):
            plant_cycle(bot)

        bot.once('goal_reached', on_goal_reached)
        return

    bot.equip(seeds, 'hand')
    
    def on_place_finished(err):
        if err:
            print(f"Plant error: {err}")
        plant_cycle(bot)

    try:
        bot.placeBlock(target_block, Vec3(0, 1, 0), on_place_finished)
    except Exception as e:
        print(f"Error: {e}")
        bot.setTimeout(lambda: plant_cycle(bot), 1000)




@On(bot, 'chat')
def handle_chat(bot, username, message, *args):
    if username == bot.username:
        dbg("Ignoring self chat")
        return
    dbg(f"Chat received from {username}: {message}")
    
    if message.startswith("!find"):
        find(bot, message)
    elif message.startswith("!gather"):
        gather(bot, message)
    elif message.startswith("!stop"):
        stop_gathering(bot)
        stop_farming_loop(bot)
    elif message == "!plant":
        start_farming_loop(bot)
