from utils import find_container, gotonear
def get_depot(bot,depots):
    import math
    if not depots:
        return None
    p = bot.entity.position
    closest_depot = None
    min_dist = float('inf')
    for depot in depots:
        dist = ((p.x - depot.x)**2 + (p.y - depot.y)**2 + (p.z - depot.z)**2)
        if dist < min_dist:
            min_dist = dist
            closest_depot = depot
    return closest_depot

def store_items_in_depot(bot,depots,items):
    from javascript import require, On
    import time
    mcDataLoader = require('minecraft-data')(bot.version)
    newitems = []
    for item in items:
        itemid = mcDataLoader.itemsByName[item.name].id
        newitems.append(itemid)
    items=newitems
    depot_pos = get_depot(bot, depots)
    if not depot_pos:
        bot.chat("No depot location set.")
        return False
    
    gotonear(bot, depot_pos, 1)
    time.sleep(1)  # Give it a moment to stabilize position
    
    chest = find_container(bot)
    if not chest:
        bot.chat("Couldn't find a chest at the depot location.")
        return False
    
    gotonear(bot, chest.position, 4.4)
    time.sleep(0.5)
    
    try:
        container_promise = bot.openContainer(chest)
        time.sleep(0.5)
        
        container = bot.currentWindow
        inventory = bot.inventory
        if container:
            for item_id in items:
                #number of items to deposit (sum up counts from all matching items)
                num_to_deposit = sum(item.count for item in inventory.items() if item.type == item_id)
                if num_to_deposit > 0:
                    try:
                        deposit_promise = container.deposit(item_id, None, num_to_deposit, None)
                        On(deposit_promise, 'then')  # Wait for promise to resolve
                        time.sleep(0.2)
                        bot.chat(f"Deposited {num_to_deposit} of {mcDataLoader.items[item_id].name} into depot.")
                    except Exception as e:
                        print(f"Error depositing item {item_id}: {e}")
            
            time.sleep(0.3)
            bot.closeWindow(container)
            bot.chat("Items deposited successfully.")
            return True
        else:
            bot.chat("Failed to open chest.")
            return False
                
    except Exception as e:
        print(f"Error opening container: {e}")
        bot.chat("Failed to open chest.")
        return False