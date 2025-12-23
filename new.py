from javascript import require, On
import time
import math
import threading

mineflayer = require('mineflayer')
mcData = require('minecraft-data')('1.21')


RANGE_GOAL = 1
BOT_USERNAME = 'python'

bot = mineflayer.createBot({
  'host': '192.168.1.125',
  'port': 25564,
  'username': BOT_USERNAME
})

pathfinder_pkg = require('mineflayer-pathfinder')

pathfinder = pathfinder_pkg.pathfinder
Movements = pathfinder_pkg.Movements
GoalNear = pathfinder_pkg.goals.GoalNear
bot.loadPlugin(pathfinder)

Vec3 = require('vec3').Vec3

print("Started mineflayer")
def mine(bot,block):
    p = bot.entity.position
    t = block.position
    dist = math.sqrt((p.x - t.x)**2 + (p.y - t.y)**2 + (p.z - t.z)**2)

    if dist > 4.5:
        goal = GoalNear(t.x, t.y, t.z, 3)
        bot.pathfinder.setGoal(goal)
        while True:
            current_pos = bot.entity.position
            if not current_pos:
                time.sleep(0.1)
                continue
            current_dist = math.sqrt((current_pos.x - t.x)**2 + (current_pos.y - t.y)**2 + (current_pos.z - t.z)**2)
            
            if current_dist <= 4.5:
                break
            if not bot.pathfinder.isMoving():
                bot.pathfinder.setGoal(goal)
            time.sleep(0.5)
    try:
        bot.dig(block)
    except Exception as e:
        print(f"Error: {e}")
is_farming = False
def farming_thread(bot):
    """
    This function runs in the background.
    It loops forever until is_farming becomes False.
    """
    global is_farming
    count = 0
    
    while is_farming:
        count += 1
        if count % 5 == 0:
            bot.chat(f"Picking up farm drops...")
            pickup_farm_drops(bot)
        # 1. Harvest
        wheat_block = find_grown_wheat(bot)
        if wheat_block:
            mine(bot, wheat_block)
            time.sleep(0.1) # Wait for block to break
        planted = replant(bot)
        time.sleep(0.1) 
        if not wheat_block and not planted:
            stop_farming(bot)
            bot.chat("No more crops to harvest or plant. Stopping farm loop.")
        else:
            time.sleep(0.2)

def pickup_farm_drops(bot):
    starting_pos = bot.entity.position
    picked_up_ids = set()  # Track which entities we've already tried
    attempts = 0  # Safety counter
    max_attempts = 10  # Maximum iterations before giving up
    while True:
        if not is_farming:
            return
        entities = bot.entities
        dropped_candidates = []
        attempts += 1
        if attempts > max_attempts:
            print(f"Reached max pickup attempts ({max_attempts}), stopping.")
            break

        
        mcData = require('minecraft-data')(bot.version)
        
        # IDs we care about
        wheat_id = mcData.itemsByName['wheat'].id
        seed_id = mcData.itemsByName['wheat_seeds'].id

        for entity_id in entities:
            if entity_id in picked_up_ids:
                continue  # Already tried this one
            entity = entities[entity_id]

            if entity:
                if entity.type == 'other':
                    dropped_candidates.append(entity)

        if not dropped_candidates:
            print("No items to pick up.")
            break
        bot_pos = bot.entity.position
        if not bot_pos: return

        closest_drop = None
        min_dist = 999

        for item in dropped_candidates:
            p = item.position
            dist = math.sqrt((bot_pos.x - p.x)**2 + (bot_pos.y - p.y)**2 + (bot_pos.z - p.z)**2)
            
            if dist < min_dist and dist < 10: # Only target items within 10 blocks
                min_dist = dist
                closest_drop = item
        if not closest_drop:
            break
        picked_up_ids.add(closest_drop.id)
        if closest_drop:
            print(f"Moving to pickup item at {closest_drop.position}")
            goal = GoalNear(closest_drop.position.x, closest_drop.position.y, closest_drop.position.z, 1)
            bot.pathfinder.setGoal(goal)
            
            for _ in range(20): 
                if not bot.entity.position: break
                
                d = math.sqrt((bot.entity.position.x - closest_drop.position.x)**2 + 
                              (bot.entity.position.y - closest_drop.position.y)**2 + 
                              (bot.entity.position.z - closest_drop.position.z)**2)
                if d < 1: # Close enough to pickup
                    break
                    
                time.sleep(0.5)
                
            bot.pathfinder.setGoal(None) # Stop moving
    # Return to starting position
    bot.chat("Returning to starting position...")
    goal = GoalNear(starting_pos.x, starting_pos.y, starting_pos.z, 1)
    bot.pathfinder.setGoal(goal)
    p = bot.entity.position
    t = starting_pos
    dist = math.sqrt((p.x - t.x)**2 + (p.y - t.y)**2 + (p.z - t.z)**2)
    if dist > 2:        
        goal = GoalNear(t.x, t.y, t.z, 3)
        bot.pathfinder.setGoal(goal)
        for _ in range(20): 
            if not bot.entity.position: break
            p = bot.entity.position
            d = math.sqrt((p.x - t.x)**2 + (p.y - t.y)**2 + (p.z - t.z)**2)
            if d < 1: # Close enough to pickup
                break
                


def farm_loop(bot):
    global is_farming
    
    # If already running, don't start another thread
    if is_farming:
        bot.chat("Already farming!")
        return

    is_farming = True
    bot.chat("Starting farm loop...")
    

    t = threading.Thread(target=farming_thread, args=(bot,))
    t.daemon = True
    t.start()

def stop_farming(bot):
    global is_farming
    is_farming = False
    bot.chat("Stopping farm loop...")


def replant(bot):
    retries = 0
    while not getattr(bot, "inventory", None):
        if retries > 10:
            print("Inventory never loaded. Skipping replant.")
            return False
        if getattr(bot, "inventory", None):
            break
        time.sleep(0.5)
        retries += 1
    if not getattr(bot, "inventory", None): 
        bot.chat("Inventory not ready"); return
    seeds = bot.inventory.findInventoryItem(mcData.itemsByName['wheat_seeds'].id)
    bot.equip(seeds, 'hand')
    
    farmland_id = mcData.blocksByName['farmland'].id
    
    found_blocks = bot.findBlocks({
        'matching': farmland_id,
        'maxDistance': 32,
        'count': 100
    })

    target_block = None
    for pos in found_blocks:
        block = bot.blockAt(pos)
        block_above = bot.blockAt(pos.offset(0, 1, 0))
        if block_above and block_above.name == 'air':
            target_block = block
            break
    if not target_block:
        return
    p = bot.entity.position
    t = target_block.position
    
    # Simple 3D distance formula
    dist = math.sqrt((p.x - t.x)**2 + (p.y - t.y)**2 + (p.z - t.z)**2)

    if dist > 4.5:        
        goal = GoalNear(t.x, t.y, t.z, 3)
        bot.pathfinder.setGoal(goal)

        while True:

            current_pos = bot.entity.position

            if not current_pos:
                time.sleep(0.1)
                continue

            current_dist = math.sqrt((current_pos.x - t.x)**2 + (current_pos.y - t.y)**2 + (current_pos.z - t.z)**2)
            
            if current_dist <= 4.5:
                break

            if not bot.pathfinder.isMoving():
                bot.pathfinder.setGoal(goal)
            
            time.sleep(0.5)
    try:
        bot.placeBlock(target_block, Vec3(0, 1, 0))
        return True
    except Exception as e:
        print(f"Error: {e}")

def find_grown_wheat(bot):
    mcData = require('minecraft-data')(bot.version)
    wheat_id = mcData.blocksByName['wheat'].id
    bot_pos = bot.entity.position
    wheat_blocks = bot.findBlocks({
        'matching': wheat_id,
        'maxDistance': 32,
        'count': 100 
    })
    
    ready_wheat = []

    for pos in wheat_blocks:
        block = bot.blockAt(pos)
        if int(block._properties['age']) == 7:
            ready_wheat.append(block)

    if not ready_wheat:
        # This is not an error, just no crops are ready.
        # print("No grown wheat found.") 
        return None

    # 2. Calculate distances in Python BEFORE sorting
    # This creates a list of tuples: (distance, block_object)
    wheat_with_dist = []
    for block in ready_wheat:
        t = block.position
        dist = math.sqrt((bot_pos.x - t.x)**2 + (bot_pos.y - t.y)**2 + (bot_pos.z - t.z)**2)
        wheat_with_dist.append((dist, block))

    # 3. Sort the list based on distance (the first item in the tuple)
    wheat_with_dist.sort(key=lambda x: x[0])

    # 4. Return the block object from the closest tuple
    closest_wheat = wheat_with_dist[0][1]
    return closest_wheat


@On(bot, 'spawn')
def handle(*args):
  print("I spawned 👋")
  movements = pathfinder.Movements(bot)

@On(bot, 'chat')
def handleMsg(this, sender, message, *args):
    print("Got message", sender, message)
    if sender == BOT_USERNAME:
        return
    if message == "!farm":
       bot.chat("Starting farming!")
       replant(bot)
    elif message == "!harvest":
        farm_loop(bot)


@On(bot, "end")
def handle(*args):
  print("Bot ended!", args)