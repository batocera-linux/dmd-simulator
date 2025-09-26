#!/usr/bin/env python3

# dmd-snake
#
# Based on the code
# https://github.com/GeorgeZhukov/python-snake/blob/master/snake.py

import math
import time
import sys
from random import randint
from PIL import Image, ImageDraw
from dmd_simulator.dmd_player import DmdPlayer
from dmd_simulator.dmd_font import DmdFont
from dmd_simulator.dmd_game import DmdGame
import time
import sdl2

colors = [
    (  0,   0,   0),
    (  0, 255,   0),
    (255,   0,   0),    
    (255, 255,   0),
    (255, 255,   0),
    (  0, 255, 255),
    (255,   0, 255),
]

WHITE = (255, 255, 255)



class Field:
    def __init__(self, width, height):
        self.width  = width
        self.height = height
        self.snake_coords = []
        self._generate_field()
        self.add_entity()

    def add_entity(self):        
        while(True):
            x = randint(0, self.width-1)
            y = randint(0, self.height-1)
            entity = [x, y]
            if entity not in self.snake_coords:
                self.field[x][y] = 3
                break

    def _generate_field(self):
        self.field = [[0 for y in range(self.height)] for x in range(self.width)]

    def _clear_field(self):        
        self.field = [[j if j!= 1 and j!= 2 else 0 for j in i] for i in self.field]

    def render(self):
        self._clear_field()

        # Render snake on the field
        for x, y in self.snake_coords:
            self.field[x][y] = 1

        # Mark head
        head = self.snake_coords[-1]
        self.field[head[0]][head[1]] = 2  

    def get_entity_pos(self):
        for y in range(self.height):
            for x in range(self.width):
                if self.field[x][y] == 3:
                    return [x, y]
        return [-1, -1]

    def is_snake_eat_entity(self):
        entity = self.get_entity_pos()
        head = self.snake_coords[-1]
        return entity == head

class Snake(DmdGame):
    def __init__(self,game_name,font_ld,font_hd):
        super().__init__(game_name,font_ld,font_hd)

        self.width_blocks=math.floor(self.width/self.block_size)
        self.height_blocks=math.floor(self.height/self.block_size)
        self.alive=True
        self.direction = 0        
        # directions:
        # - 0: right
        # - 1: up
        # - 2: left
        # - 3: down

        # Init basic coords
        self.coords = [[0, 0], [0, 1], [0, 2], [0, 3]]
        
    def set_direction(self, dir):
        self.direction = (self.direction + dir)%4

    def level_up(self):
        # get last point direction
        a = self.coords[0]
        b = self.coords[1]

        tail = a[:]

        if a[0] < b[0]:
            tail[0]-=1
        elif a[1] < b[1]:
            tail[1]-=1
        elif a[0] > b[0]:
            tail[0]+=1
        elif a[1] > b[1]:
            tail[1]+=1

        tail = self._check_limit(tail)
        self.coords.insert(0, tail)

        self.speed=self.speed*self.acceleration

    def is_alive(self):
        head = self.coords[-1]
        snake_body = self.coords[:-1]
        return head not in snake_body

    def _check_limit(self, point):
        # Check field limit
        if point[0] > self.width_blocks-1:
            point[0] = 0
        elif point[0] < 0:
            point[0] = self.width_blocks -1
        elif point[1] < 0:
            point[1] = self.height_blocks -1
        elif point[1] > self.height_blocks-1:
            point[1] = 0
        return point

    def move(self):
        # Determine head coords
        head = self.coords[-1][:]

        # Calc new head coords
        if   self.direction == 1:
            head[1]-=1
        elif self.direction == 3:
            head[1]+=1
        elif self.direction == 0:
            head[0]+=1
        elif self.direction == 2:
            head[0]-=1

        # Check field limit
        head = self._check_limit(head)

        del(self.coords[0])
        self.coords.append(head)
        self.field.snake_coords = self.coords

        self.alive=self.is_alive()

        # check if snake eat an entity
        if self.field.is_snake_eat_entity():
            self.level_up()
            self.field.add_entity()

    def set_field(self, field):
        self.field = field
    
    def args(self,parser):        
        super().args(parser)            
        parser.add_argument("--block_size",     type=int,   default=4,      help="game block size in pixels (default 4)")
        parser.add_argument("--speed",          type=float, default=0.3,    help="Initial speed in seconds (default 0.3)")
        parser.add_argument("--acceleration",   type=float, default=0.95,   help="Acceleration speed=speed*acceleration (default 0.95)")

    def drawScore(self):
        txt="Score"
        self.font.puttext(self.frame,txt,0,round((self.width-(len(txt)-1)*6)/2),2,WHITE)
        txt=str(len(self.field.snake_coords)-4)
        self.font.puttext(self.frame,txt,0,round((self.width-(len(txt)-1)*6)/2),12,WHITE)         

    def drawGameOver(self):
        txt="Game Over"
        self.font.puttext(self.frame,txt,0,round((self.width-(len(txt)-1)*6)/2),20,WHITE)
        

def dmd_snake_launch() -> None:    
    snake=Snake("snake","minogram_6x10","minogram_6x10")

    # Init field
    field = Field(snake.width_blocks, snake.height_blocks)
    snake.set_field(field)
    
    while snake.alive:
        snake.controller.pollEvent()

        if (snake.controller.LeftWasPressed()):
            snake.set_direction(+1)
        
        if (snake.controller.RightWasPressed()):
            snake.set_direction(-1)

        # Move snake
        snake.move()
        
        # Render field
        field.render()
        snake.newFrame()

        im=snake.frame

        for y in range(snake.height_blocks):
            for x in range(snake.width_blocks):
                if (field.field[x][y]!=0):
                    for a in range(snake.block_size):
                        for b in range(snake.block_size):
                            im.putpixel((x*snake.block_size+a, y*snake.block_size+b), colors[field.field[x][y]])                
                if (field.field[x][y]==2):
                    if (snake.direction==0):
                        im.putpixel((x*snake.block_size+snake.block_size-1, y*snake.block_size), colors[0])
                        im.putpixel((x*snake.block_size+snake.block_size-1, y*snake.block_size+snake.block_size-1), colors[0])
                    elif (snake.direction==1):
                        im.putpixel((x*snake.block_size, y*snake.block_size), colors[0])
                        im.putpixel((x*snake.block_size+snake.block_size-1, y*snake.block_size), colors[0])
                    elif (snake.direction==2):
                        im.putpixel((x*snake.block_size, y*snake.block_size), colors[0])
                        im.putpixel((x*snake.block_size, y*snake.block_size+snake.block_size-1), colors[0])
                    elif (snake.direction==3):
                        im.putpixel((x*snake.block_size, y*snake.block_size+snake.block_size-1), colors[0])
                        im.putpixel((x*snake.block_size+snake.block_size-1, y*snake.block_size+snake.block_size-1), colors[0])        
        snake.displayScore()
        snake.sendFrame()
        time.sleep(snake.speed)

    snake.displayGameOver()
    snake.end()

    
if __name__ == '__main__':
    dmd_snake_launch()
