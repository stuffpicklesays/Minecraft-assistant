import math
from javascript import require
pathfinder = require('mineflayer-pathfinder')
GoalNear = pathfinder.goals.GoalNear
Vec3 = require('vec3')
import time
from waiting import wait

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

def find_container(bot,mode='chest',r=10):
    mcData = require('minecraft-data')(bot.version)
    chest_id = mcData.blocksByName[mode].id
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

def is_daytime(bot):
    return bot.time.isDay

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

def where(bot):
    pos = bot.entity.position
    return (pos.x, pos.y, pos.z)

from vec3 import Vec3
import math



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
    dist_squared = ((p.x - t.x)**2 + (p.y - t.y)**2 + (p.z - t.z)**2)

    if dist_squared > 9:
        goal = GoalNear(t.x, t.y, t.z, 3)
        bot.pathfinder.setGoal(goal)

def follow_thread(bot, player_name, stop_event):
    global is_following
    is_following = True
    come(bot, player_name)
    while stop_event.is_set() == False:
        if not is_following:
            break
        p = bot.entity.position
        t = bot.players[player_name].entity.position
        dist_squared = ((p.x - t.x)**2 + (p.y - t.y)**2 + (p.z - t.z)**2)
        if dist_squared > 7:
            come(bot, player_name)
            wait(1, stop_event)
        else:
            bot.pathfinder.setGoal(None)
            wait(0.05, stop_event)