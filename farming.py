import time
from waiting import wait
import math
from utils import mine
from javascript import require

pathfinder = require('mineflayer-pathfinder')
GoalNear = pathfinder.goals.GoalNear
Vec3 = require('vec3')

def farming_thread(bot, stop_event):
    """
    This function runs in the background.
    It loops forever until is_farming becomes False.
    """
    global state
    
    # Wait for bot to be ready
    mcData = require('minecraft-data')(bot.version)
    wheat_seeds_id = mcData.itemsByName['wheat_seeds'].id
    
    # Wait for inventory to be ready
    for i in range(10):
        try:
            if bot.inventory and bot.inventory.items():
                break
        except:
            pass
        time.sleep(0.5)
    
    count = 0
    while stop_event.is_set() == False:
        # Count wheat seeds properly
        try:
            wheat_amount = sum(item.count for item in bot.inventory.items() if item.type == wheat_seeds_id)
        except Exception as e:
            print(f"Error counting wheat seeds: {e}")
            wheat_amount = 0

        count += 1
        if count % 10 == 0:
            pickup_farm_drops(bot, stop_event)
        wheat_block = find_grown_wheat(bot)
        if wheat_block:
            mine(bot, wheat_block)
            wait(0.1, stop_event)
        planted = replant(bot, stop_event)
        planted2 = replant(bot, stop_event)
        planted3 = replant(bot, stop_event)

        wait(0.1, stop_event) 
        if not wheat_block and not (planted or planted2 or planted3):
            bot.chat("No more crops to harvest or plant. Waiting 20 seconds...")
            wait(20, stop_event)
        else:
            wait(0.2, stop_event)


def pickup_farm_drops(bot,stop_event):
    starting_pos = bot.entity.position
    picked_up_ids = set()  # Track which entities we've already tried
    attempts = 0  # Safety counter
    max_attempts = 10  # Maximum iterations before giving up
    max_time = 8
    time_started = time.time()
    global state
    while True:
        if time.time() - time_started > max_time:
            print("Pickup time exceeded max time, stopping.")
            break
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
            
            if dist < min_dist and dist < 4: # Only target items within 4 blocks
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
                    
                wait(0.1, stop_event)
                
            bot.pathfinder.setGoal(None) # Stop moving
    # Return to starting position
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
                





def replant(bot,stop_event):
    mcData = require('minecraft-data')(bot.version)

    seeds = None
    for attempt in range(5):
        try:
            if not bot.inventory:
                raise Exception("Inventory not ready")
                
            seeds = bot.inventory.findInventoryItem(mcData.itemsByName['wheat_seeds'].id)
            break
        except Exception as e:
            print(f"Waiting for inventory... ({e})")
            wait(1, stop_event)
            
    if not seeds:
        print("No seeds found or inventory error.")
        return False
    try:
        bot.equip(seeds, 'hand')
    except Exception:
        pass 
    
    farmland_id = mcData.blocksByName['farmland'].id
    
    found_blocks = bot.findBlocks({
        'matching': farmland_id,
        'maxDistance': 50,
        'count': 500
    })

    target_block = None
    for pos in found_blocks:
        block = bot.blockAt(pos)
        block_above = bot.blockAt(pos.offset(0, 1, 0))
        if block_above and block_above.name == 'air':
            target_block = block
            break
    if not target_block:
        print("No suitable farmland found for planting.")
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
                wait(0.1, stop_event)
                continue

            current_dist = math.sqrt((current_pos.x - t.x)**2 + (current_pos.y - t.y)**2 + (current_pos.z - t.z)**2)
            
            if current_dist <= 4.5:
                break
                

            if not bot.pathfinder.isMoving():
                bot.pathfinder.setGoal(goal)
            
            wait(0.5, stop_event)
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