#!/usr/bin/env python3

# dmd_tetris from https://github.com/colas-sebastien/dmd-games
# https://gist.github.com/timurbakibayev/1f683d34487362b0f36280989c80960c

from PIL import Image, ImageDraw
from dmd_simulator.dmd_player import DmdPlayer
from dmd_simulator.dmd_font import DmdFont
import random
from importlib import resources as impresources
import time
import sdl2

colors = [
    (  0,   0,   0),
    (255,   0,   0),
    (  0, 255,   0),
    (255, 255, 255),
    (255, 255,   0),
    (  0, 255, 255),
    (255,   0, 255),
]

class Figure:
    x = 0
    y = 0

    figures = [
        [[1, 5, 9, 13], [4, 5, 6, 7]],
        [[4, 5, 9, 10], [2, 6, 5, 9]],
        [[6, 7, 9, 10], [1, 5, 6, 10]],
        [[1, 2, 5, 9], [0, 4, 5, 6], [1, 5, 9, 8], [4, 5, 6, 10]],
        [[1, 2, 6, 10], [5, 6, 7, 9], [2, 6, 10, 11], [3, 5, 6, 7]],
        [[1, 4, 5, 6], [1, 4, 5, 9], [4, 5, 6, 9], [1, 5, 6, 9]],
        [[1, 2, 5, 6]],
    ]

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.type = random.randint(0, len(self.figures) - 1)
        self.color = random.randint(1, len(colors) - 1)
        self.rotation = 0

    def image(self):
        return self.figures[self.type][self.rotation]

    def rotate(self):
        self.rotation = (self.rotation + 1) % len(self.figures[self.type])

class DMDConf:
    port=6789
    host="localhost"
    width=128
    height=32    
    bock_size=3
    x_shift=1
    y_shift=23
    height_blocks=34
    width_blocks=10

class Tetris:
    def __init__(self, width, height):
        self.level = 1
        self.score = 0
        self.state = "start"
        self.field = []
        self.height = 0
        self.width = 0
        self.x = 100
        self.y = 60
        self.zoom = 20
        self.figure = None
    
        self.height = height
        self.width = width
        self.field = []
        self.score = 0
        for i in range(height):
            new_line = []
            for j in range(width):
                new_line.append(0)
            self.field.append(new_line)

    def new_figure(self):
        self.figure = Figure(3, 0)

    def intersects(self):
        intersection = False
        for i in range(4):
            for j in range(4):
                if i * 4 + j in self.figure.image():
                    if i + self.figure.y > self.height - 1 or \
                            j + self.figure.x > self.width - 1 or \
                            j + self.figure.x < 0 or \
                            self.field[i + self.figure.y][j + self.figure.x] > 0:
                        intersection = True
        return intersection

    def break_lines(self):
        lines = 0
        for i in range(1, self.height):
            zeros = 0
            for j in range(self.width):
                if self.field[i][j] == 0:
                    zeros += 1
            if zeros == 0:
                lines += 1
                for i1 in range(i, 1, -1):
                    for j in range(self.width):
                        self.field[i1][j] = self.field[i1 - 1][j]
        self.score += lines ** 2

    def go_space(self):
        while not self.intersects():
            self.figure.y += 1
        self.figure.y -= 1
        self.freeze()

    def go_down(self):
        self.figure.y += 1
        if self.intersects():
            self.figure.y -= 1
            self.freeze()

    def freeze(self):
        for i in range(4):
            for j in range(4):
                if i * 4 + j in self.figure.image():
                    self.field[i + self.figure.y][j + self.figure.x] = self.figure.color
        self.break_lines()
        self.new_figure()
        if self.intersects():
            self.state = "gameover"

    def go_side(self, dx):
        old_x = self.figure.x
        self.figure.x += dx
        if self.intersects():
            self.figure.x = old_x

    def rotate(self):
        old_rotation = self.figure.rotation
        self.figure.rotate()
        if self.intersects():
            self.figure.rotation = old_rotation

    def args():
        return DMDConf

def dmd_tetris_launch() -> None:
    conf=Tetris.args()
    client=DmdPlayer.connect(conf)
    width  = conf.width
    height = conf.height
    layer = "main"
    header = DmdPlayer.getHeader(width, height, layer, width * height * 2) # RGB565
    dmdresroot = impresources.files("dmd_simulator")
    dmdrespath = dmdresroot.joinpath("data/tetris")

    dmdfont=DmdFont("minogram_6x10")

    # Define some colors
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    RED   = (255,   0,   0)

    # Loop until the user clicks the close button.
    done = False
    clock = time.time()
    fps = 25
    fps_step = 1.0 / fps
    game = Tetris(conf.width_blocks, conf.height_blocks) 
    counter = 0

    joysticks = {}

    pressing_down = False

    DmdPlayer.sendImageFile(header,client,0,dmdrespath.joinpath("dmd-tetris.png"),128,32,True)

    sdl2.SDL_Init(sdl2.SDL_INIT_JOYSTICK | sdl2.SDL_INIT_GAMECONTROLLER)

    done=False
    while not done:
        if game.figure is None:
            game.new_figure()
        counter += 1
        if counter > 100000:
            counter = 0

        if counter % (fps // game.level // 2) == 0 or pressing_down:
            if game.state == "start":
                game.go_down()

        event = sdl2.SDL_Event()
        while sdl2.SDL_PollEvent(event) != 0:
            if event.type == sdl2.SDL_QUIT:
                done = True

            if event.type == sdl2.SDL_CONTROLLERBUTTONDOWN:
                if event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_A:
                    game.rotate()
                if event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_B:
                    game.go_space()
                if event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_X:
                    if game.state != "start":
                        done = True                  
                if event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_Y:
                    game.__init__(conf.width_blocks, conf.height_blocks)
                if event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_START:
                    if game.state == "start":
                        game.state = "pause"
                    else:
                        game.state = "start"

                if event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:
                    game.go_side(-1)
                if event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT:
                    game.go_side(1)
                if event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
                    pressing_down=True

            if event.type == sdl2.SDL_CONTROLLERBUTTONUP:
                if event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
                    pressing_down=False

            if event.type == sdl2.SDL_CONTROLLERDEVICEADDED:
                joy = sdl2.SDL_GameControllerOpen(event.cdevice.which)
                if joy:
                    joysticks[event.cdevice.which] = joy

            if event.type == sdl2.SDL_CONTROLLERDEVICEREMOVED:
                del joysticks[event.cdevice.which]

            # joystick (not in controller database for automatic buttons)
            if event.type == sdl2.SDL_JOYBUTTONDOWN:
                if sdl2.SDL_IsGameController(event.jdevice.which) == False:
                    if event.jbutton.button == 0:
                        game.rotate()
                    if event.jbutton.button == 1:
                        game.go_space()
                    if event.jbutton.button == 2:
                        if game.state != "start":
                            done = True
                    if event.jbutton.button == 6:
                        game.__init__(conf.width_blocks, conf.height_blocks)
                    if event.jbutton.button == 7:
                        if game.state == "start":
                            game.state = "pause"
                        else:
                            game.state = "start"

            if event.type == sdl2.SDL_JOYHATMOTION:
                if sdl2.SDL_IsGameController(event.jdevice.which) == False:
                    if event.jhat.hat == 0:
                        if event.jhat.value == 8: # left
                            game.go_side(-1)
                        elif event.jhat.value == 2: # right
                            game.go_side(1)

                        if event.jhat.value == 4: # down
                            pressing_down=True
                        elif event.jhat.value == 1 or event.jhat.value == 0: # up or center
                            pressing_down=False

            if event.type == sdl2.SDL_JOYDEVICEADDED:
                if sdl2.SDL_IsGameController(event.jdevice.which) == False:
                    joy = sdl2.SDL_JoystickOpen(event.jdevice.which)
                    if joy:
                        joysticks[event.jdevice.which] = joy

            if event.type == sdl2.SDL_JOYDEVICEREMOVED:
                if sdl2.SDL_IsGameController(event.jdevice.which) == False:
                    del joysticks[event.jdevice.which]

        im = Image.new("RGBA", (width, height))        
        
        for i in range(game.height):
            for j in range(game.width):                
                if game.field[i][j] > 0:
                    for a in range(conf.bock_size):
                        for b in range(conf.bock_size):
                            im.putpixel((width - conf.bock_size - (i*conf.bock_size+a)-conf.y_shift, j*conf.bock_size+b+conf.x_shift), colors[game.field[i][j]])
        
        if game.figure is not None:
            for i in range(4):
                for j in range(4):
                    p = i * 4 + j
                    if p in game.figure.image():
                        for a in range(conf.bock_size):
                            for b in range(conf.bock_size):
                                im.putpixel((width - conf.bock_size - ((i + game.figure.y)*conf.bock_size+a)-conf.y_shift, (j + game.figure.x)*conf.bock_size+b+conf.x_shift), colors[game.figure.color])

        dmdfont.puttext(im,"Score",1,116,1,WHITE)

        str_score=str(game.score)
        dmdfont.puttext(im,str_score,1,104,13-(len(str_score)-1)*3,WHITE)        

        if game.state == "gameover":
            draw = ImageDraw.Draw(im)
            draw.rectangle([60,2,82,29],BLACK,RED,1)
            dmdfont.puttext(im,"GAME",1,70,4,WHITE)
            dmdfont.puttext(im,"OVER",1,60,4,WHITE)
        if game.state == "pause":
            draw = ImageDraw.Draw(im)
            draw.rectangle([0,0,106,31],BLACK)
            dmdfont.puttext(im,"PAUSE",1,70,1,WHITE)            

        DmdPlayer.sendFrame(header, client, layer, DmdPlayer.imageConvert(im, True))

        # pause
        new_time = time.time()
        if new_time < clock + fps_step:
            time.sleep(fps_step - (new_time - clock))
        clock = new_time

    im = Image.new("RGBA", (width, height))
    DmdPlayer.sendFrame(header, client, layer, DmdPlayer.imageConvert(im, True))

    client.close()
    for joystick in joysticks:
        if sdl2.SDL_IsGameController(joystick):
            sdl2.SDL_GameControllerClose(joysticks[joystick])
        else:
            sdl2.SDL_JoystickClose(joysticks[joystick])

if __name__ == '__main__':
    dmd_tetris_launch()
