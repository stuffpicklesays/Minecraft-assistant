lines = {}

lines["welcome"] = ["Sup guys!", "Hi guys", "Hello everyone!", "Hey folks!", "What's up!"]

lines["farming"] = [
    "Oh, absolutely, because I wasn’t *already* thrilled to work.",
    "Right away! Can’t wait to touch the soil with all the excitement I have.",
    "Of course, boss! Let me drop everything and embrace my inner farmer.",
    "Sure thing, nothing I love more than following orders in the dirt.",
    "Oh yes, planting seeds is exactly how I pictured spending my day.",
    "Right, because I clearly had nothing better to do.",
    "Sure, I’ll get right on that… living the dream.",
    "Absolutely, who needs fun when you have fields to work?",
    "Of course, I live to serve… the crops.",
    "Sure thing, let me just pretend this is my idea of fun."
]

lines["already"] = [
    "I'm already _, you muppet!",
    "I'm already _, do you think I'm that slow?",
    "I'm already _, get with the program!",
]

lines["night"]  = ["Good night everyone!", "Time to sleep!", "Going to bed now!", "Sweet dreams!", "See you in the morning!"]
lines['nobed'] = ["Can someone sleep pls?", "I'm gonna die out here!", "It's night time, can someone sleep?", "Anyone got a bed?", "Place a white bed for me to sleep in!"]
lines['sleepfailed'] = ["You guys didn't help me sleep :( I'm leaving", "Why didn't anyone help me sleep? D:", "I can't sleep, I'm outta here!", "No one helped me sleep, goodbye!"]
lines["playersleeped"] = ["Thanks for sleeping guys!","Phew, that was a close one!", "Nearly died to mobs there! Thanks for sleeping"]
lines["bedfound"] = ["YAY SOMEONE PLACED A BED! GOING TO SLEEP!", "Awesome, a bed! Time to sleep!", "Sweet, a bed appeared! Off to sleep I go!"]

def say(key,delay=1,replace=None):
    import random, time
    time.sleep(delay)
    line = random.choice(lines[key])
    if replace:
        line = line.replace('_',replace)
    return line