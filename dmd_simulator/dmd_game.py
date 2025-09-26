#!/usr/bin/env python3

import argparse
import sdl2
from dmd_simulator.dmd_player import DmdPlayer
from dmd_simulator.dmd_font   import DmdFont
from importlib import resources as impresources
import time
from PIL import Image
import threading 
from websockets.sync.server import serve



class Controller:    
    right_was_pressed=False
    left_was_pressed=False
    pressing_right=False
    pressing_left=False

    def __init__(self):
        pass

    def pollEvent(self):
        pass

    def stop(self):
        pass

    def RightWasPressed(self):
        if self.right_was_pressed:
            self.right_was_pressed=False
            return True
        else:
            return False
    
    def LeftWasPressed(self):
        if self.left_was_pressed:
            self.left_was_pressed=False
            return True
        else:
            return False

class GamePadController(Controller):

    joysticks = {}

    def __init__(self):
        sdl2.SDL_Init(sdl2.SDL_INIT_JOYSTICK | sdl2.SDL_INIT_GAMECONTROLLER)
    
    def pollEvent(self):
        #return super().pollEvent()
        event = sdl2.SDL_Event()
        while sdl2.SDL_PollEvent(event) != 0:
            # Joystick added/removed
            if event.type == sdl2.SDL_CONTROLLERDEVICEADDED:
                joy = sdl2.SDL_GameControllerOpen(event.cdevice.which)
                if joy:
                    self.joysticks[event.cdevice.which] = joy
            if event.type == sdl2.SDL_CONTROLLERDEVICEREMOVED:
                del self.joysticks[event.cdevice.which]          
            if event.type == sdl2.SDL_JOYDEVICEADDED:
                if sdl2.SDL_IsGameController(event.jdevice.which) == False:
                    joy = sdl2.SDL_JoystickOpen(event.jdevice.which)
                    if joy:
                        self.joysticks[event.jdevice.which] = joy
            if event.type == sdl2.SDL_JOYDEVICEREMOVED:
                if sdl2.SDL_IsGameController(event.jdevice.which) == False:
                    del self.joysticks[event.jdevice.which]                     

            # If some arrows did pressed - change direction
            if (event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT):
                if (not self.pressing_left):
                    self.left_was_pressed=True
                self.pressing_left=True                  
            if (event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT):
                if (not self.pressing_right):
                    self.right_was_pressed=True
                self.pressing_right=True

            if event.type == sdl2.SDL_CONTROLLERBUTTONUP:
                if event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:
                    self.pressing_left=False
                if event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT:
                    self.pressing_right=False

            if event.type == sdl2.SDL_JOYHATMOTION:
                if sdl2.SDL_IsGameController(event.jdevice.which) == False:
                    if event.jhat.hat == 0:
                        if event.jhat.value == 8: # left
                            self.pressing_left=True
                            self.pressing_right=False
                            self.left_was_pressed=True
                        elif event.jhat.value == 2: # right
                            self.pressing_right=True
                            self.pressing_left=False
                            self.right_was_pressed=True
                        elif event.jhat.value == 1 or event.jhat.value == 0:
                            self.pressing_left=False
                            self.pressing_right=False             
    def stop(self):
        for joystick in self.joysticks:
            if sdl2.SDL_IsGameController(joystick):
                sdl2.SDL_GameControllerClose(self.joysticks[joystick])
            else:
                sdl2.SDL_JoystickClose(self.joysticks[joystick])

class WSContoller(Controller,threading.Thread):
    def __init__(self,host,port):
        threading.Thread.__init__(self)         
        self.host=host
        self.port=port
        self.start() 

    def run(self): 
        with serve(self.get_event, self.host, self.port) as server:
            server.serve_forever()       

    def get_event(self,websocket): 
        for message in websocket:   
            if   message=="right":     
                self.right_was_pressed=True
            elif message=="left":
                self.left_was_pressed=True        

class DmdGame:
    def __init__(self,game_name,font_ld,font_hd):
        # Parsing configuration
        parser = argparse.ArgumentParser(prog="dmd_"+game_name+".py")
        self.args(parser)
        parser.parse_args(namespace=self)        
        if self.hd:
            self.width  = 256
            self.height = 64
            self.font=DmdFont(font_hd)
        else:
            self.font=DmdFont(font_ld)
        self.game_name=game_name   
        # Connecting DMD Server
        self.layer=self.game_name
        self.client=DmdPlayer.connect(self)
        self.header = DmdPlayer.getHeader(self.width, self.height, self.layer, self.width * self.height * 2) # RGB565
        # Display Splash Screen or Not
        if (not self.nosplashscreen):
            dmdresroot = impresources.files("dmd_simulator")
            dmdrespath = dmdresroot.joinpath("data/"+self.game_name)             
            DmdPlayer.sendImageFile(self.header,self.client,0,dmdrespath.joinpath("dmd-"+self.game_name+".png"),self.width,self.height,True)
            time.sleep(self.splashscreendelay)
        if (self.enablews):
            self.controller=WSContoller(self.wshost,self.wsport)
        else:
            self.controller=GamePadController()
    
    def newFrame(self):
        self.frame = Image.new("RGBA", (self.width, self.height))
    
    def sendFrame(self):
        DmdPlayer.sendFrame(self.header, self.client, self.layer, DmdPlayer.imageConvert(self.frame, True))

    def drawScore(self):
        pass

    def drawGameOver(self):
        pass

    def displayScore(self):
        if (not self.noscoredisplay):
            self.drawScore()
    
    def displayGameOver(self):
        if (not self.noscoredisplay):
            #self.newFrame()
            self.drawScore()   
            self.drawGameOver()    
            self.sendFrame()
            time.sleep(self.splashscreendelay)

    def end(self):
        self.controller.stop()
        self.client.close()
            
    def args(self,parser):
        parser.add_argument("-p", "--port", type=int,       default=6789,           help="network connexion port (default 6789)")
        parser.add_argument("--host",                       default="localhost",    help="dmd server host (default localhost)")
        parser.add_argument("--width",      type=int,       default=128,            help="dmd width (default 128)")
        parser.add_argument("--height",     type=int,       default= 32,            help="dmd height (default 32)")
        parser.add_argument("--hd",                         action="store_true",    help="hd format, equivalent of --width 256 --height 64")
        parser.add_argument("--noscoredisplay",             action="store_true",    help="don't display score")
        parser.add_argument("--nosplashscreen",             action="store_true",    help="don't display the splashscreen")
        parser.add_argument("--splashscreendelay",type=int, default=2,              help="time to display the splashscreen(default 2s)")
        parser.add_argument("--enablews",                   action="store_true",    help="enable WebSocket remote control")
        parser.add_argument("--wshost",                     default="0.0.0.0",      help="WebSocket host (default 0.0.0.0)")
        parser.add_argument("--wsport",     type=int,       default=8080,           help="WebSocket port (default 8080)")

            
