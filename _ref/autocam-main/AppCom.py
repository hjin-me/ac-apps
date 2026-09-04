def initialize():
    global runningorder, event, ABot_Talking, ABot_Enabled

    runningorder = ''  # Ex: '4|2|3|1|' where integers are the drivers index
    event = ''  # Ex: 'leaderchange' 'positionchange' etc. clear event after handling message
    ABot_Talking = False
    ABot_Enabled = False
    
    return