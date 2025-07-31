#!/usr/bin/env python3

from PIL import Image
from dmd import DmdPlayer
from dmdfont import DmdFont
import time

class DMDConf:
    port=6789
    host="localhost"
    endian="big"
    width=128
    height=32    
    bock_size=3
    x_shift=1
    y_shift=23

if __name__ == '__main__':

    coord=[[58,1],[116,4],[73,20],[1,16]]
    DmdPlayer.endianness=DMDConf.endian
    client=DmdPlayer.connect(DMDConf)
    width  = DMDConf.width
    height = DMDConf.height
    layer = "main"
    header = DmdPlayer.getHeader(width, height, layer, width * height * 2) # RGB565

    dmdfont=DmdFont("minogram_6x10")

    
    im = Image.new("RGBA", (width, height))
    for test in range(4):        
        dmdfont.puttext(im,"TesT",test,coord[test][0],coord[test][1],(255,255,255))

    DmdPlayer.sendFrame(header, client, layer, DmdPlayer.imageConvert(im, True))

    time.sleep(1)

    im = Image.new("RGBA", (width, height))
    for test in range(4):        
        dmdfont.puttext(im,"TesT",test+4,coord[test][0],coord[test][1],(255,255,255))

    DmdPlayer.sendFrame(header, client, layer, DmdPlayer.imageConvert(im, True))

    time.sleep(1)

    im = Image.new("RGBA", (width, height))
    for test in range(4):        
        dmdfont.puttext(im,"TesT",test,coord[test][0],coord[test][1],(255,255,255))

    DmdPlayer.sendFrame(header, client, layer, DmdPlayer.imageConvert(im, True))

    time.sleep(1)
        
    client.close()




