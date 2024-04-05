#!/usr/bin/env python3

from PIL import Image, ImageDraw, ImageFont
import sys
import numpy as np
import argparse
import time
import socket
import re

feature_video = False
try:
    import cv2
    feature_video = True
except:
    pass

class DmdPlayer:

    def im2rgb565(im):
        data = np.array(im.convert('RGB'))
        R5 = (data[...,0]>>3).astype(np.uint16) << 11
        G6 = (data[...,1]>>2).astype(np.uint16) << 5
        B5 = (data[...,2]>>3).astype(np.uint16)
        return R5 | G6 | B5

    def imageConvert(im):
        return DmdPlayer.im2rgb565(im)
        #return np.array(im.convert('RGB'))

    def getHeader(width, height, layer, nbytes):
        endianness = sys.byteorder
        version = 1
        mode    = 3 # rgb565
        if layer == "main":
            buffered = 1
            disconnectOthers = 1
        else:
            buffered = 0
            disconnectOthers = 0
        header  = bytearray("DMDStream", "utf-8") + b'\x00'
        header += version.to_bytes(1, endianness)
        header += mode   .to_bytes(4, endianness)
        header += width  .to_bytes(2, endianness) + height.to_bytes(2, endianness) + buffered.to_bytes(1, endianness) + disconnectOthers.to_bytes(1, endianness)
        header += nbytes .to_bytes(4, endianness)
        return header

    def sendFrame(header, client, layer, im):
        msg = header + im.tobytes()
        msglen = len(msg)
        totalsent = 0
        while totalsent < msglen:
            sent = client.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            totalsent = totalsent + sent
        
    def imageFit(im, width, height, padding = True):
        img_width, img_height = im.size
        woffset = 0
        hoffset = 0
        if img_height == 0 or img_width == 0:
            return Image.new("RGBA", (width, height))

        if(img_width / img_height > width / height):
            new_width = width
            if padding:
                new_height = round(width * img_height / img_width)
            else:
                new_height = height
            if padding:
                hoffset = (height - new_height) // 2
        else:
            if padding:
                new_width = round(height * img_width / img_height)
            else:
                new_width = width
            new_height = height
            if padding:
                woffset = (width - new_width) // 2
        im = im.resize((new_width, new_height))
        # need rgba conversion for alpha_composite
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        new_im = Image.new(im.mode, (width, height))
        # alpha_composite required over paste
        new_im.alpha_composite(im, (woffset, hoffset))
        return new_im

    def txt2image(txt, font, width, height, fillcolor, xoffset, yoffset):
        im = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(im)
        draw.text((xoffset, yoffset), txt, font=font, fill=fillcolor)
        return im
    
    def sendImageFile(header, client, layer, file, width, height, once):
        anim_cache = None
        with Image.open(file) as im:
            if hasattr(im, 'is_animated') and im.is_animated:
                # just fill the cache
                anim_cache = []
                for n in range(im.n_frames):
                    anim_cache.append({ "img": DmdPlayer.imageConvert(DmdPlayer.imageFit(im, width, height)), "duration": im.info["duration"] })
                    im.seek(n)
            else:
                im = DmdPlayer.imageFit(im, width, height)
                DmdPlayer.sendFrame(header, client, layer, DmdPlayer.imageConvert(im))
        # close the image to just play the cache
        if anim_cache is not None:
            DmdPlayer.playAnim(header, client, layer, anim_cache, once)

    def sendVideoFile(header, client, layer, file, width, height, once):
        while True:
          cap = cv2.VideoCapture(file)
          fps = cap.get(cv2.CAP_PROP_FPS)
          last_rendering = None
          print("fps:{}".format(fps))
          nskip = fps // 20 # skip some frames to not overload too much ; no more than 20 fps
          f = 0
          while(cap.isOpened()):
            ret, cv2_im = cap.read()
            if not ret:
                break;
            if nskip > 0 and f % nskip == 0:
                im = Image.fromarray(cv2.cvtColor(cv2_im, cv2.COLOR_BGR2RGB))
                im = DmdPlayer.imageFit(im, width, height)
                DmdPlayer.sendFrame(header, client, layer, DmdPlayer.imageConvert(im))
            if last_rendering is not None:
                now = time.time()
                d = now - last_rendering;
                if d < 1/fps:
                    time.sleep(1/fps - d)
            last_rendering = time.time()
            f +=1
          cap.release()
          if once:
              break

    def playAnim(header, client, layer, anim, once):
        while True:
            for n in range(len(anim)):
                ts = time.time()
                DmdPlayer.sendFrame(header, client, layer, anim[n]["img"])
                # just to a more homogene animation by removing time lost in system calls
                spent_ts = time.time() - ts
                delay = anim[n]["duration"]/1000
                if(delay > spent_ts):
                    time.sleep(delay - spent_ts)
            if once:
                break

    def sendText(header, client, layer, text, color, target_width, target_height, fontfile, moving_text, fixed_text, speed, move, once, no_fit):
        font = ImageFont.truetype(fontfile, target_height)
        (left, top, right, bottom) = font.getbbox(text)
        img_width  = right - left
        img_height = bottom - top
        fit = img_width < target_width
        if fit and (moving_text is not True or fixed_text is True): # the text fit on the screen
            im = DmdPlayer.txt2image(text, font, img_width, img_height, color, 0, -top)
            if not no_fit:
                im = DmdPlayer.imageFit(im, target_width, target_height) # an optimisation could be to directly fit with an extra argument in txt2image
            DmdPlayer.sendFrame(header, client, layer, DmdPlayer.imageConvert(im))
        elif not fit and (moving_text is not True or fixed_text is True): # it doesn't fix, resize
            im = DmdPlayer.txt2image(text, font, img_width, img_height, color, 0, -top)
            im = im.resize((target_width, img_height * target_width // img_width))
            if not no_fit:
                im = DmdPlayer.imageFit(im, target_width, target_height) # an optimisation could be to directly fit with an extra argument in txt2image
            DmdPlayer.sendFrame(header, client, layer, DmdPlayer.imageConvert(im))
        else:
            # move the text ; generate all the frames in a cache first
            anim_cache = []
            im = DmdPlayer.txt2image(text, font, img_width, img_height, color, 0, -top)
            if not no_fit:
                im = DmdPlayer.imageFit(im, target_width, target_height, False)
            reswidth, resimg_height = im.size
            for i in range(1, target_width+reswidth, move):
                new_im = Image.new('RGB', (target_width, target_height))
                new_im.paste(im, (target_width-i, 0))
                anim_cache.append({ "img": DmdPlayer.imageConvert(new_im), "duration": speed })
            DmdPlayer.playAnim(header, client, layer, anim_cache, once)

    def run(feature_video):
        parser = argparse.ArgumentParser(prog="dmd-play")
        parser.add_argument("-f", "--file", help="image path file")
        if feature_video:
            parser.add_argument("-v", "--video", help="video path file")
        parser.add_argument("-t", "--text", help="text")
        parser.add_argument("--font", default="/usr/share/fonts/dejavu/DejaVuSans.ttf", help="path to the font file")
        parser.add_argument("--clear", action="store_true",            help="clear the screen")
        parser.add_argument("--overlay", action="store_true",          help="restore the previous frames once finished")
        parser.add_argument("--overlay-time", type=int, default=1000,  help="time to pause fixed images for the overlay in ms")
        parser.add_argument("--moving-text", action="store_true",      help="always makes the text to move, even if text fits")
        parser.add_argument("--fixed-text",  action="store_true",      help="never makes the text to move, prefer to adjust size")
        parser.add_argument("--caps",  action="store_true",            help="convert text in all caps")
        parser.add_argument("--no-fit",  action="store_true",          help="keep font aspect ratio (easier to read for moving text)")
        parser.add_argument("-r", "--red",   type=int, default=255,    help="red text color level (0-255)")
        parser.add_argument("-g", "--green", type=int, default=0,      help="green text color level (0-255)")
        parser.add_argument("-b", "--blue",  type=int, default=0,      help="blue text color level (0-255)")
        parser.add_argument("-s", "--speed", type=int, default=60,     help="sleep time during each text position (in milliseconds)")
        parser.add_argument("-m", "--move",  type=int, default=2,      help="text movement each time")
        parser.add_argument("--once",  action="store_true",            help="don't loop forever")
        parser.add_argument("-c", "--clock",  action="store_true",     help="display current time")
        parser.add_argument("--no-seconds",  action="store_true",      help="clock: display only hours and minutes, no seconds")
        parser.add_argument("--h12",  action="store_true",             help="clock: 12-hour format with AM and PM (default it 24h)")
        parser.add_argument("-p", "--port", type=int, default=6789,    help="network connexion port")
        parser.add_argument("--host", default="localhost",             help="dmd server host")
        parser.add_argument("--width",  type=int, default=128,         help="dmd width")
        parser.add_argument("--height", type=int, default= 32,         help="dmd height")
        parser.add_argument("--hd",    action="store_true",            help="hd format, equivalent of --width 256 --height 64")
        args = parser.parse_args()

        allNone = True
        if args.file is not None:
            allNone = False
        if args.text is not None:
            allNone = False
        if feature_video and args.video is not None:
            allNone = False
        if args.clear is True:
            allNone = False
        if args.clock is True:
            allNone = False

        if allNone:
            sys.stderr.write("Missing something to play\n")
            return

        # connect
        layer = "main"
        if args.overlay:
            layer = "overlay"
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((socket.gethostbyname(args.host), args.port))
        width  = args.width
        height = args.height
        if args.hd:
            width  = 256
            height = 64
        header = DmdPlayer.getHeader(width, height, layer, width * height * 2) # RGB565
        if args.move < 1:
            move = 1
        else:
            move = args.move

        if args.file:
            DmdPlayer.sendImageFile(header, client, layer, args.file, width, height, args.once)
        elif args.text:
            if args.caps:
                text = args.text.upper()
            else:
                text = args.text
            DmdPlayer.sendText(header, client, layer, text, (args.red, args.green, args.blue), width, height, args.font, args.moving_text, args.fixed_text, args.speed, move, args.once, args.no_fit)
        elif args.clock:
            while True:
                if args.h12:
                    if args.no_seconds:
                        localtime = time.strftime("%-I:%M %p", time.localtime())
                    else:
                        localtime = time.strftime("%-I:%M:%S %p", time.localtime())
                else:
                    if args.no_seconds:
                        localtime = time.strftime("%H:%M", time.localtime())
                    else:
                        localtime = time.strftime("%H:%M:%S", time.localtime())
                DmdPlayer.sendText(header, client, layer, localtime, (args.red, args.green, args.blue), width, height, args.font, False, args.fixed_text, args.speed, move, True, False)
                time.sleep(args.speed/1000)
        elif feature_video and args.video:
            DmdPlayer.sendVideoFile(header, client, layer, args.video, width, height, args.once)
        elif args.clear:
            DmdPlayer.sendText(header, client, layer, "", (args.red, args.green, args.blue), width, height, args.font, False, True, args.speed, move, True, False)

        if args.overlay:
            time.sleep(args.overlay_time/1000)

        client.close()

if __name__ == '__main__':
    DmdPlayer.run(feature_video)
