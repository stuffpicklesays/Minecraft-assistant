from javascript import require, On
import time
import math
import threading
from farming import farming_thread
from sleep import sleep_thread
from utils import is_daytime, come, where, follow_thread
from chatlines import lines
from depot import get_depot
mineflayer = require('mineflayer')
viewer = require('prismarine-viewer').mineflayer

mcData = require('minecraft-data')('1.21.1')
global depots
depots = []

lines = {}
lines['nobed'] = ["Can someone sleep pls?", "I'm gonna die out here!", "It's night time, can someone sleep?", "Anyone got a bed?", "Place a white bed for me to sleep in!"]
lines['sleepfailed'] = ["You guys didn't help me sleep :( I'm leaving", "Why didn't anyone help me sleep? D:", "I can't sleep, I'm outta here!", "No one helped me sleep, goodbye!"]
RANGE_GOAL = 1
BOT_USERNAME = 'barrythebot'

testmode = False


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

def state_machine():
    global active_states
    last_state = ''  # track last state
    active_states = {}  # map of state name to (thread, stop_event)
    

    while True: 
        
        current_state = state[0] if state else None
        # States to start
        if current_state != last_state:
            s = current_state
            if s == 'farming':
                stop_event = threading.Event()
                t = threading.Thread(target=farming_thread, args=(bot, stop_event))
                t.daemon = True
                t.start()
                active_states[s] = (t, stop_event)
                print(f"Started state: {s}")
            if s == 'sleeping':
                stop_event = threading.Event()
                t = threading.Thread(target=sleep_thread, args=(bot, stop_event))
                t.daemon = True
                t.start()
                active_states[s] = (t, stop_event)
                print(f"Started state: {s}")
            elif s and s.startswith('follow '):
                target_player = s[len('follow '):]
                stop_event = threading.Event()
                t = threading.Thread(target=follow_thread, args=(bot, target_player, stop_event))
                t.daemon = True
                t.start()
                active_states[s] = (t, stop_event)
                print(f"Started state: {s}")
            elif s and s.startswith('deposit '):
                from depot import store_items_in_depot
                item_names = s[len('deposit '):].split(" ")
                items_to_store = []
                for item in bot.inventory.items():
                    if item.name in item_names:
                        items_to_store.append(item)
                stop_event = threading.Event()
                t = threading.Thread(target=lambda: store_items_in_depot(bot, depots, items_to_store))
                t.daemon = True
                t.start()
                active_states[s] = (t, stop_event)
                print(f"Started state: {s}")
            
            #stopping
            s = last_state
            if s and s in active_states:
                t, stop_event = active_states[s]
                stop_event.set()
                t.join()
                del active_states[s]
                print(f"Stopped state: {s}")

        last_state = current_state
        time.sleep(0.5)  # small delay for main loop

def watch_thread():
    while True:
        time.sleep(1)
        if not is_daytime(bot):
            if state:
                if state[0] != 'sleeping':
                    state.insert(0, 'sleeping')
            else:
                state.append('sleeping')
        else:
            if 'sleeping' in state:
                state.remove('sleeping')

def add_state(state_name,priority=0):
    if state_name not in state:
        if priority == 0:
            state.append(state)
        for i in state:
            if priority > 0:
                state.insert(0,i)
            else:
                state.append(i)

@On(bot, 'spawn')
def spawned(*args):
  import random
  from chatlines import lines
  print("I spawned 👋")
  bot.chat(random.choice(lines["welcome"]))

  movements = pathfinder.Movements(bot)

@On(bot, 'chat')
def handleMsg(this, sender, message, *args):
    from chatlines import lines, say
    import random
    print("Got message", sender, message)
    if sender == BOT_USERNAME:
        return
    elif message == "!farm":
        if 'farming' not in state:
            state.insert(0,'farming')
            bot.chat(say('farming'))
        else:
            bot.chat(say('already',replace='farming'))
            
    elif message == "!stop":
        state.clear()
    elif message == "!where":
        where(bot)
    elif message == "!come":
        state.clear()
        target_player = sender
        bot.chat(f"Coming to {target_player}!")
        come(bot, target_player)
    elif message == "!follow":
        if f'follow {sender}' not in state:
            state.insert(0,f'follow {sender}')
            bot.chat(f"Following {sender}!")
        else:
            bot.chat(say('already',replace='following'))

    elif message == "!sleep":
        bot.chat("Going to sleep if possible...")
        if 'sleeping' not in state:
            state.insert(0,'sleeping')
        else:
            bot.chat(say('already',replace='trying to sleep'))

    elif message == "!depot add":
        from utils import gotonear
        bot.chat("Ok, I'll remember the depot location.")
        #go to player's position to mark depot
        gotonear(bot, bot.players[sender].entity.position, 1)
        depots.append(bot.entity.position)
    elif message == "!depot list":
        if not depots:
            bot.chat("No depot locations set.")
        else:
            for i, depot in enumerate(depots):
                bot.chat(f"Depot {i+1}: {depot}")
    elif message == "!depot clear":
        depots.clear()
        bot.chat("Cleared all depot locations.")
    elif message == "!deposit":
        from depot import store_items_in_depot
        state.clear()  # Stop other activities
        
        items_to_store = []
        for item in bot.inventory.items():
            if item.name not in ['wheat_seeds', 'carrot', 'potato', 'beetroot_seeds']:
                items_to_store.append(item)
        
        if not items_to_store:
            bot.chat("No items to deposit.")
        else:
            state.insert(0, 'deposit ' + " ".join(items_to_store))        
    
    elif message == "!debug":
        global active_states
        bot.chat(f"Current state: {state}")
        bot.chat(f"Current position: {where(bot)}")
        bot.chat(f"Active states: {active_states.keys()}")


@On(bot, "end")
def handle(*args):
  print("Bot ended!", args)



if __name__ == "__main__":
    #start state machine thread
    t = threading.Thread(target=state_machine)
    t.daemon = True
    t.start()
    #start watch thread
    t2 = threading.Thread(target=watch_thread)
    t2.daemon = True
    t2.start()
    #keep main thread alive
    while True:
        time.sleep(1)