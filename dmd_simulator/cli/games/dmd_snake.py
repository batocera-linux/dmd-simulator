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
from importlib import resources as impresources
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

class DMDConf:
    port=6789
    host="localhost"
    width=128
    height=32    
    bock_size=4
    x_shift=1
    y_shift=23    
    width_blocks=math.floor(width/bock_size)
    height_blocks=math.floor(height/bock_size)

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

class Snake:
    def __init__(self, width, height,speed):
        self.height = height
        self.width = width        
        self.direction = 0
        self.speed=speed
        self.alive=True
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

        self.speed=self.speed*0.95

    def is_alive(self):
        head = self.coords[-1]
        snake_body = self.coords[:-1]
        return head not in snake_body

    def _check_limit(self, point):
        # Check field limit
        if point[0] > self.width-1:
            point[0] = 0
        elif point[0] < 0:
            point[0] = self.width -1
        elif point[1] < 0:
            point[1] = self.height -1
        elif point[1] > self.height-1:
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
    
    def args():
        return DMDConf


def dmd_snake_launch() -> None:
    conf=Snake.args()
    client=DmdPlayer.connect(conf)
    width  = conf.width
    height = conf.height
    layer = "main"
    header = DmdPlayer.getHeader(width, height, layer, width * height * 2) # RGB565
    dmdresroot = impresources.files("dmd_simulator")
    dmdrespath = dmdresroot.joinpath("data/snake")    

    dmdfont=DmdFont("minogram_6x10")

    # Define some colors
    WHITE = (255, 255, 255)

    # Init snake & field
    field = Field(conf.width_blocks, conf.height_blocks)
    snake = Snake(conf.width_blocks, conf.height_blocks,0.3)
    snake.set_field(field)

    joysticks = {}

    DmdPlayer.sendImageFile(header,client,0,dmdrespath.joinpath("dmd-snake.png"),128,32,True)

    sdl2.SDL_Init(sdl2.SDL_INIT_JOYSTICK | sdl2.SDL_INIT_GAMECONTROLLER)

    time.sleep(2)
    
    pressing_left=False
    pressing_right=False
    while snake.alive:
        event = sdl2.SDL_Event()
        while sdl2.SDL_PollEvent(event) != 0:
            if event.type == sdl2.SDL_QUIT:
                done = True
            # If some arrows did pressed - change direction
            # snake.set_direction(ch)
            if (event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT) and (not pressing_left):
                snake.set_direction(+1)
                pressing_left=True
            if (event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT) and (not pressing_right):
                snake.set_direction(-1)
                pressing_right=True

            if event.type == sdl2.SDL_CONTROLLERBUTTONUP:
                if event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:
                    pressing_left=False
                if event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT:
                    pressing_right=False

            if event.type == sdl2.SDL_CONTROLLERDEVICEADDED:
                joy = sdl2.SDL_GameControllerOpen(event.cdevice.which)
                if joy:
                    joysticks[event.cdevice.which] = joy

            if event.type == sdl2.SDL_CONTROLLERDEVICEREMOVED:
                del joysticks[event.cdevice.which]

            if event.type == sdl2.SDL_JOYHATMOTION:
                if sdl2.SDL_IsGameController(event.jdevice.which) == False:
                    if event.jhat.hat == 0:
                        if event.jhat.value == 8: # left
                            snake.set_direction(+1)
                            pressing_left=True
                            pressing_right=False
                        elif event.jhat.value == 2: # right
                            snake.set_direction(-1)
                            pressing_right=True
                            pressing_left=False
                        elif event.jhat.value == 1 or event.jhat.value == 0:
                            pressing_left=False
                            pressing_right=False

            if event.type == sdl2.SDL_JOYDEVICEADDED:
                if sdl2.SDL_IsGameController(event.jdevice.which) == False:
                    joy = sdl2.SDL_JoystickOpen(event.jdevice.which)
                    if joy:
                        joysticks[event.jdevice.which] = joy

            if event.type == sdl2.SDL_JOYDEVICEREMOVED:
                if sdl2.SDL_IsGameController(event.jdevice.which) == False:
                    del joysticks[event.jdevice.which]            

        # Move snake
        snake.move()
        
        # Render field
        field.render()

        im = Image.new("RGBA", (width, height))
        txt="Score"
        dmdfont.puttext(im,txt,0,round((width-(len(txt)-1)*6)/2),2,WHITE)
        txt=str(len(field.snake_coords)-4)
        dmdfont.puttext(im,txt,0,round((width-(len(txt)-1)*6)/2),12,WHITE)       

        for y in range(conf.height_blocks):
            for x in range(conf.width_blocks):
                if (field.field[x][y]!=0):
                    for a in range(conf.bock_size):
                        for b in range(conf.bock_size):
                            im.putpixel((x*conf.bock_size+a, y*conf.bock_size+b), colors[field.field[x][y]])                
                if (field.field[x][y]==2):
                    if (snake.direction==0):
                        im.putpixel((x*conf.bock_size+conf.bock_size-1, y*conf.bock_size), colors[0])
                        im.putpixel((x*conf.bock_size+conf.bock_size-1, y*conf.bock_size+conf.bock_size-1), colors[0])
                    elif (snake.direction==1):
                        im.putpixel((x*conf.bock_size, y*conf.bock_size), colors[0])
                        im.putpixel((x*conf.bock_size+conf.bock_size-1, y*conf.bock_size), colors[0])
                    elif (snake.direction==2):
                        im.putpixel((x*conf.bock_size, y*conf.bock_size), colors[0])
                        im.putpixel((x*conf.bock_size, y*conf.bock_size+conf.bock_size-1), colors[0])
                    elif (snake.direction==3):
                        im.putpixel((x*conf.bock_size, y*conf.bock_size+conf.bock_size-1), colors[0])
                        im.putpixel((x*conf.bock_size+conf.bock_size-1, y*conf.bock_size+conf.bock_size-1), colors[0])
        DmdPlayer.sendFrame(header, client, layer, DmdPlayer.imageConvert(im, True))

        time.sleep(snake.speed)

    txt="Score"
    dmdfont.puttext(im,txt,0,round((width-(len(txt)-1)*6)/2),2,WHITE)
    txt=str(len(field.snake_coords)-4)
    dmdfont.puttext(im,txt,0,round((width-(len(txt)-1)*6)/2),12,WHITE)       
    txt="Game Over"
    dmdfont.puttext(im,txt,0,round((width-(len(txt)-1)*6)/2),20,WHITE)    


    DmdPlayer.sendFrame(header, client, layer, DmdPlayer.imageConvert(im, True))

    client.close()
    for joystick in joysticks:
        if sdl2.SDL_IsGameController(joystick):
            sdl2.SDL_GameControllerClose(joysticks[joystick])
        else:
            sdl2.SDL_JoystickClose(joysticks[joystick])
    
if __name__ == '__main__':
    dmd_snake_launch()
