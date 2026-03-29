import random
import numpy as np
import typing

# region Battlesnake Game Initialisation
# info is called when you create your Battlesnake on play.battlesnake.com
# and controls your Battlesnake's appearance
# TIP: If you open your Battlesnake URL in a browser you should see this data
def info() -> typing.Dict:
    print("INFO")

    return {
       "apiversion":"1",
       "author":"Snazziington",  # TODO: Your Battlesnake Username
       "color":"#6B57E0",  # TODO: Choose color
       "head":"beluga",  # TODO: Choose head
       "tail":"do-sammy",  # TODO: Choose tail
    }

# start is called when your Battlesnake begins a game
def start(game_state: typing.Dict):
    print("GAME START")

# end is called when your Battlesnake finishes a game
def end(game_state: typing.Dict):
    print("GAME OVER\n")

# endregion

# move is called on every turn and returns your next move
# Valid moves are"up","down","left", or"right"

collisionScore = -100

def wallCollision(game_state: typing.Dict, nextMove, boardWidth, boardHeight):
    if nextMove['x'] == boardWidth or nextMove['x'] == -1 or nextMove['y'] == boardHeight or nextMove['y'] == -1:
        return True
    
def checkSnakeTiles(game_state: typing.Dict):
    snakeBodyTiles = list()

    for snake in game_state["board"]["snakes"]:
        snakeBody = snake["body"]
        for xy in snakeBody:
            snakeBodyTiles.append(xy)
    return snakeBodyTiles

def move(game_state: typing.Dict) -> typing.Dict:
    print("MOVE:", {game_state['turn']})

    print("Check Snake Tiles:", checkSnakeTiles(game_state))

    # region Initialisation
    # Snake Head + Neck
    myHead  = game_state["you"]["body"][0]
    tailIndex = len(game_state["you"]["body"]) - 1

    myTail = game_state["you"]["body"][tailIndex]

    # Board dimensions
    boardWidth = game_state['board']['width']
    boardHeight = game_state['board']['height']

    # Scores of each direction initialise as 0
    score = [0, 0, 0, 0] # up, down, left, right
    # For each possible move:
    # [0] = x vector, [1] = y vector, [2] = string direction
    moves = [[0, 1,"up"], [0, -1,"down"], [-1, 0,"left"], [1, 0,"right"]]
    
    # endregion

    # Check Collisions
    for n in range (0, 4): # For each possible move (up, down, left, right)
        nextMove = {'x': 0, 'y': 0}
        nextMove['x'] = myHead["x"] + moves[n][0]
        nextMove['y'] = myHead["y"] + moves[n][1]

        # New coords of head if doing this move
        print("Compare:", nextMove, myTail)
        print("If moving", moves[n][2],", head will be at:", nextMove)

        # Snake can chase own tail if safe
        if nextMove == myTail and game_state['turn'] > 2 and game_state["you"]["health"] != 100:
                return
        # Avoid Wall Collisions
        elif wallCollision(game_state, nextMove, boardWidth, boardHeight):
                score[n] += collisionScore
                print("Cannot move", moves[n][2],", will collide with wall")

        # Avoid Snake Collisions
        elif nextMove in checkSnakeTiles(game_state):
                    print("Check Snake Tiles:", checkSnakeTiles(game_state))
                    score[n] += collisionScore
                    print("Cannot move", moves[n][2],", will collide with a body")

        print("Score for moving", moves[n][2],"is:", score[n])

    # Flood Fill
    # for possible moves above -100, check which place has more area

    # Food
    # For possible moves above -100, check nearest food source
    
    print("All scores:", score)
    maxScore = max(score) # Maximum score found in the score array
    scoreValues = np.array([score[0], score[1], score[2], score[3]]) # We use numpy here so we can use ".where"
    bestMoves = np.where(scoreValues == maxScore)[0]
    print("The best possible moves are:", bestMoves)

    nextMove = random.choice(bestMoves)
    print("The next move is", moves[nextMove][2])
    return {"move": moves[nextMove][2]}

# Start server when `python main.py` is run
if __name__ =="__main__":
    from server import run_server

    run_server({"info": info,"start": start,"move": move,"end": end})
