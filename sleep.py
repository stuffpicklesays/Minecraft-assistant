from utils import find_bed, gotonear, is_daytime
from waiting import wait
from chatlines import lines

def sleep_thread(bot,stop_event,prevlocation=None):
    import random
    prevstart = prevlocation
    #check if bot is already sleeping
    if bot.isSleeping:
        return
    if is_daytime(bot):
        return
    global state
    global current_minecraft_time

    prevlocation = bot.entity.position
    bed = find_bed(bot)
    if bed:
        if not prevstart:
            bot.chat(random.choice(lines['night']))
        gotonear(bot, bed.position, 3, timeout=10)
        print("Going to bed at", bed.position)
        try:
            bot.sleep(bed)
            wait(5, stop_event)
        except Exception as e:
            bot.chat(f"Couldn't sleep: {e}")
            wait(5, stop_event)
            sleep_thread(bot, stop_event, prevlocation=prevlocation)
        gotonear(bot, prevlocation, 2)
    else:
        import random
        for i in range(5):
            line = random.choice(lines['nobed'])
            bot.chat(line)
            wait(20, stop_event)
            bed = find_bed(bot)
            if bed:
                bot.chat(random.choice(lines['bedfound']))
                gotonear(bot, bed.position, 2)
                try:
                    
                    bot.sleep(bed)
                except Exception as e:
                    bot.chat(f"Couldn't sleep: {e}")
                    wait(5, stop_event)
                    sleep_thread(bot, stop_event, prevlocation=prevlocation)
                gotonear(bot, prevlocation, 2)
                break
            if is_daytime(bot):
                bot.chat(random.choice(lines['playersleeped']))
            


        if not is_daytime(bot):
            bot.chat(random.choice(lines['sleepfailed']))
            wait(2, stop_event)