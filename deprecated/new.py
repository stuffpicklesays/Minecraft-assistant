from random import random
from javascript import require, On
import time
import math
import threading

mineflayer = require('mineflayer')
viewer = require('prismarine-viewer').mineflayer

mcData = require('minecraft-data')('1.21.1')

lines = {}
lines['nobed'] = ["Can someone sleep pls?", "I'm gonna die out here!", "It's night time, can someone sleep?", "Anyone got a bed?", "Place a white bed for me to sleep in!"]
lines['sleepfailed'] = ["You guys didn't help me sleep :( I'm leaving", "Why didn't anyone help me sleep? D:", "I can't sleep, I'm outta here!", "No one helped me sleep, goodbye!"]
RANGE_GOAL = 1
BOT_USERNAME = 'barrythebot'

testmode = True


bot = mineflayer.createBot({
  'host': '192.168.1.125',
  'port': 25565 if not testmode else 25564,
  'username': BOT_USERNAME,
  'version': '1.21.1'
})
global state
state = []


pathfinder_pkg = require('mineflayer-pathfinder')

pathfinder = pathfinder_pkg.pathfinder
Movements = pathfinder_pkg.Movements
GoalNear = pathfinder_pkg.goals.GoalNear
bot.loadPlugin(pathfinder)

Vec3 = require('vec3').Vec3

def where(bot):
    pos = bot.entity.position
    print(f"Bot is at x:{pos.x} y:{pos.y} z:{pos.z}")
    bot.chat(f"My position is x:{pos.x} y:{pos.y} z:{pos.z}")

def come(bot, player_name):
    if not bot.players:
        bot.chat("Players not loaded yet!")
        return
    try:
        player = bot.players[player_name]
    except (KeyError, TypeError):
        bot.chat(f"I can't see {player_name}!")
        return
    if not player or not player.entity:
        bot.chat(f"I can't see {player_name}!")
        return
    p = bot.entity.position
    t = player.entity.position
    dist = math.sqrt((p.x - t.x)**2 + (p.y - t.y)**2 + (p.z - t.z)**2)

    if dist > 4.5:
        goal = GoalNear(t.x, t.y, t.z, 3)
        bot.pathfinder.setGoal(goal)

def follow_loop(bot, player_name):
    global is_following
    is_following = True
    come(bot, player_name)
    while True:
        if not is_following:
            break
        p = bot.entity.position
        t = bot.players[player_name].entity.position
        dist = math.sqrt((p.x - t.x)**2 + (p.y - t.y)**2 + (p.z - t.z)**2)
        if dist > 4.5:
            come(bot, player_name)
            time.sleep(0.5)
        else:
            bot.pathfinder.setGoal(None)
            time.sleep(0.5)
def stop_following(bot):
    global is_following
    is_following = False
    bot.chat("Stopping following.")

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

def find_chest(bot):
    mcData = require('minecraft-data')(bot.version)
    chest_id = mcData.blocksByName['chest'].id
    bot_pos = bot.entity.position
    chest_blocks = bot.findBlocks({
        'matching': chest_id,
        'maxDistance': 32,
        'count': 100 
    })
    
    if not chest_blocks:
        print("No chest found.") 
        return None

    chest_with_dist = []
    for pos in chest_blocks:
        block = bot.blockAt(pos)
        t = block.position
        dist = math.sqrt((bot_pos.x - t.x)**2 + (bot_pos.y - t.y)**2 + (bot_pos.z - t.z)**2)
        chest_with_dist.append((dist, block))

    chest_with_dist.sort(key=lambda x: x[0])

    closest_chest = chest_with_dist[0][1]
    return closest_chest






def farming_thread(bot):
    """
    This function runs in the background.
    It loops forever until is_farming becomes False.
    """
    global state

    
    count = 0
    if state and state[0] == 'farming':
        while state[0] == 'farming':
            count += 1
            if count % 10 == 0:
                pickup_farm_drops(bot)
            # 1. Harvest
            wheat_block = find_grown_wheat(bot)
            if wheat_block:
                mine(bot, wheat_block)
                time.sleep(0.1) # Wait for block to break
            planted = replant(bot)
            planted2 = replant(bot)  # Try planting twice to increase chances
            planted3 = replant(bot)

            time.sleep(0.1) 
            if not wheat_block and not (planted or planted2 or planted3):
                bot.chat("No more crops to harvest or plant. Waiting 20 seconds...")
                time.sleep(20)
            else:
                time.sleep(0.2)


def pickup_farm_drops(bot):
    starting_pos = bot.entity.position
    picked_up_ids = set()  # Track which entities we've already tried
    attempts = 0  # Safety counter
    max_attempts = 10  # Maximum iterations before giving up
    max_time = 8
    time_started = time.time()
    global state
    while True:
        if state[0] != 'farming':
            return
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
                    
                time.sleep(0.1)
                if state[0] != 'farming':
                    return
                
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
                


def farm_loop(bot):
    global state
    
    # If already running, don't start another thread
    try:
        if state[0] == 'farming':
            bot.chat("Already farming!")
            return
    except IndexError:
        pass

    state.insert(0, 'farming')
    bot.chat("Starting farm loop...")


def stop_farming(bot):
    global state
    if 'farming' in state:
        state.remove('farming')
    bot.chat("Stopping farm loop...")

def wait(seconds, stop_event):
    stop_event.wait(seconds)

def replant(bot):
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
        #print("No seeds found or inventory error.")
        return False
    try:
        bot.equip(seeds, 'hand')
    except Exception:
        pass 
    
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




def core_thread():
    while True:
        time.sleep(1)
        if not is_daytime():
            sleep(bot)
        entities = bot.entities
        for entity_id in entities:
            #check if hostile mob
            entity = entities[entity_id]
            if entity and entity.type == 'mob' and entity.mobType in ['Zombie', 'Skeleton', 'Creeper', 'Spider', 'Enderman']:
                dist = math.sqrt(
                    (bot.entity.position.x - entity.position.x)**2 +
                    (bot.entity.position.y - entity.position.y)**2 +
                    (bot.entity.position.z - entity.position.z)**2
                )
                if dist < 6:
                    bot.chat(f"Hostile mob detected: {entity.mobType} at distance {dist:.2f}.")
                    bot.attack(entity)

def state_machine():
    last_state_set = set()  # track last state set
    active_states = {}  # map of state name to (thread, stop_event)

    while True:
        current_state_set = set(state)

        # States to start
        for s in current_state_set - last_state_set:
            if s == 'farming':
                stop_event = threading.Event()
                t = threading.Thread(target=farming_thread, args=(bot, stop_event))
                t.daemon = True
                t.start()
                active_states[s] = (t, stop_event)
                print(f"Started state: {s}")
            if s == 'sleeping':
                stop_event = threading.Event()
                t = threading.Thread(target=sleep, args=(bot, stop_event))
                t.daemon = True
                t.start()
                active_states[s] = (t, stop_event)
                print(f"Started state: {s}")
            

        # States to stop
        for s in last_state_set - current_state_set:
            t, stop_event = active_states[s]
            stop_event.set()
            t.join()
            del active_states[s]
            print(f"Stopped state: {s}")

        last_state_set = current_state_set
        time.sleep(0.5)  # small delay for main loop

def is_daytime():
    return bot.time.isDay
def gotonear(bot,target,distance=4.5,timeout=30):
    p = bot.entity.position
    t = target
    dist = math.sqrt((p.x - t.x)**2 + (p.y - t.y)**2 + (p.z - t.z)**2)
    if dist > distance:
        goal = GoalNear(t.x, t.y, t.z, distance-0.5)
        bot.pathfinder.setGoal(goal)
        starttime = time.time()
        while True:
            if time.time() - starttime > timeout:
                print("Timeout reached in gotonear")
                break
            current_pos = bot.entity.position
            if not current_pos:
                time.sleep(0.1)
                continue
            current_dist = math.sqrt((current_pos.x - t.x)**2 + (current_pos.y - t.y)**2 + (current_pos.z - t.z)**2)
            
            if current_dist <= distance:
                break
            if not bot.pathfinder.isMoving():
                bot.pathfinder.setGoal(goal)

def find_bed(bot):
    mcDataLoader = require('minecraft-data')
    mcData = mcDataLoader(bot.version)

    bed_ids = [
        block.id
        for block in mcData.blocksArray
        if block.name.endswith('_bed')
    ]

    return bot.findBlock({
        'matching': bed_ids,
        'maxDistance': 64
    })


def sleep(bot,prevlocation=None):
    #check if bot is already sleeping
    if bot.isSleeping:
        return
    if is_daytime():
        return
    global state
    global current_minecraft_time
    state.insert(0,'sleeping')
    prevlocation = bot.entity.position
    stop_farming(bot)
    bed = find_bed(bot)
    if bed:
        bot.chat("AAAAAAAAAH IT'S NIGHT TIME GOING TO SLEEP!")
        gotonear(bot, bed.position, 2)
        try:
            bot.sleep(bed)
        except Exception as e:
            bot.chat(f"Couldn't sleep: {e}")
            time.sleep(5)
            state.remove('sleeping')
            sleep(bot,prevlocation=prevlocation)
        gotonear(bot, prevlocation, 2)
    else:
        import random
        for i in range(5):
            line = random.choice(lines['nobed'])
            bot.chat(line)
            time.sleep(20)
            bed = find_bed(bot)
            if bed:
                bot.chat("YAY SOMEONE PLACED A BED! GOING TO SLEEP!")
                gotonear(bot, bed.position, 2)
                try:
                    
                    bot.sleep(bed)
                except Exception as e:
                    bot.chat(f"Couldn't sleep: {e}")
                    time.sleep(5)
                    state.remove('sleeping')
                    sleep(bot,prevlocation=prevlocation)
                gotonear(bot, prevlocation, 2)
                break
            if is_daytime():
                bot.chat("Thanks for sleeping guys!")
            


        if not is_daytime():
            bot.chat(random.choice(lines['sleepfailed']))
            time.sleep(2)




#start core thread
t = threading.Thread(target=core_thread)
t.daemon = True
t.start()

#start farmig thread
farm_thread = threading.Thread(target=farming_thread, args=(bot,))
farm_thread.daemon = True
farm_thread.start()

@On(bot, 'spawn')
def handle(*args):
  print("I spawned 👋")

  movements = pathfinder.Movements(bot)

@On(bot, 'chat')
def handleMsg(this, sender, message, *args):
    import random
    print("Got message", sender, message)
    if sender == BOT_USERNAME:
        return
    if message == "!farm":
       bot.chat(random.choice(lines["farming"]))
       replant(bot)
    elif message == "!harvest":
        farm_loop(bot)
    elif message == "!stop":
        stop_farming(bot)
        stop_following(bot)
    elif message == "!where":
        where(bot)
    elif message == "!come":
        target_player = sender
        bot.chat(f"Coming to {target_player}!")
        come(bot, target_player)
    elif message == "!follow":
        target_player = sender
        t = threading.Thread(target=follow_loop, args=(bot, target_player))
        t.daemon = True
        t.start()
    elif message == "!sleep":
        sleep(bot)

@On(bot, "end")
def handle(*args):
  print("Bot ended!", args)