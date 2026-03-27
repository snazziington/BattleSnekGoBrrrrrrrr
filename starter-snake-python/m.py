# Welcome to
# __________         __    __  .__                               __
# \______   \_____ _/  |__/  |_|  |   ____   ______ ____ _____  |  | __ ____
#  |    |  _/\__  \\   __\   __\  | _/ __ \ /  ___//    \\__  \ |  |/ // __ \
#  |    |   \ / __ \|  |  |  | |  |_\  ___/ \___ \|   |  \/ __ \|    <\  ___/
#  |________/(______/__|  |__| |____/\_____>______>___|__(______/__|__\\_____>
#
# This file can be a nice home for your Battlesnake logic and helper functions.
#
# To get you started we've included code to prevent your Battlesnake from moving backwards.
# For more info see docs.battlesnake.com

import random
import numpy as np
import typing

# info is called when you create your Battlesnake on play.battlesnake.com
# and controls your Battlesnake's appearance
# TIP: If you open your Battlesnake URL in a browser you should see this data
def info() -> typing.Dict:
    print("INFO")

    return {
        "apiversion": "1",
        "author": "Snazziington",  # TODO: Your Battlesnake Username
        "color": "#6B57E0",  # TODO: Choose color
        "head": "beluga",  # TODO: Choose head
        "tail": "do-sammy",  # TODO: Choose tail
    }

# start is called when your Battlesnake begins a game
def start(game_state: typing.Dict):
    print("GAME START")

# end is called when your Battlesnake finishes a game
def end(game_state: typing.Dict):
    print("GAME OVER\n")

# move is called on every turn and returns your next move
# Valid moves are "up", "down", "left", or "right"
# See https://docs.battlesnake.com/api/example-move for available data
collisionScore = -100

def move(game_state: typing.Dict) -> typing.Dict:

    # Snake Head + Neck
    myHead  = game_state["you"]["body"][0]
    tailIndex = len(game_state["you"]["body"]) - 1
    print(tailIndex)

    myTail = game_state["you"]["body"][tailIndex]
    print(myTail)

    # Board dimensions
    boardWidth = game_state['board']['width']
    boardHeight = game_state['board']['height']
    boardWalls = [[-1, boardWidth], [-1, boardHeight]]

    # Scores of each direction initialise as 0
    score = [0, 0, 0, 0] # up, down, left, right

    # For each possible move:
    # [0] = x vector, [1] = y vector, [2] = string direction
    moves = [[0, 1, "up"], [0, -1, "down"], [-1, 0, "left"], [1, 0, "right"]]
    
    print("MOVE:", {game_state['turn']})
    for n in range (0, 4):
        print("N: ", n)
        print("moves[n]", moves[n])
        print("moves[n][0]", moves[n][0])
        print("moves[n][1]", moves[n][1])
        x = myHead["x"] + moves[n][0]
        y = myHead["y"] + moves[n][1]
        nextMove = [x, y]
        
        print("If moving ", moves[n][2], ", head will be at: ", nextMove)

        # Colliding with Self
        for bodyPart in game_state["you"]["body"]:
            if bodyPart == myTail and game_state['turn'] > 2:
                ...
            else:
                bodyCoords = [bodyPart["x"], bodyPart["y"]]

                print(bodyCoords, nextMove)
                if bodyCoords == nextMove:
                    score[n] += collisionScore
                    print("Cannot move ", moves[n][2], ", will collide with body")

        if nextMove [0] == boardWidth or nextMove [0] == -1 or nextMove [1] == boardHeight or nextMove [1] == -1:
            score[n] += collisionScore
            print("Cannot move ", moves[n][2], ", will collide with wall")

        print("Score for moving", moves[n][2], "is: ", score[n])

    print("All scores: ", score)
    maxScore = max(score) # is 0 [-100, -100, 0, 0]
    scoreValues = np.array([score[0], score[1], score[2], score[3]])
    print(scoreValues)

    ii = np.where(scoreValues == maxScore)[0]
    print(ii)
    nextMove = random.choice(ii)
    print(random.choice(ii))
    print("The max scoring direction is ", moves[nextMove][2], "so we'll move that way!")
    return {"move": moves[nextMove][2]}

        # Colliding with barrier

    # We've included code to prevent your Battlesnake from moving backwards
    # I think what I need to do is the following;
    # So I need to write a for loop which will iterate through each direction
    # So it'd be like "for each in range of moves"
        # And maybe the range of moves could be like, [0, 1] to represent moving up, [1, 0] to move right etc
        # So that I can just write code like "Add "
        # Then in the for loop it'd be like
        # If move == left

    # Maybe I should also make functions which are like checkIfBodyCollision
        # And this function just whether the next move will cause the snake to collide w/ their body
        # If yes, reduce score by like. a million lmao
        # If not, add nothing to score


# Start server when `python main.py` is run
if __name__ == "__main__":
    from server import run_server

    run_server({"info": info, "start": start, "move": move, "end": end})
