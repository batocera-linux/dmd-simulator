#!/usr/bin/env python3

from PIL import Image, ImageDraw, ImageFont
import sys
import argparse
import time
import socket
import re
from datetime import datetime, timedelta
from string import Formatter

class DmdPlayer:

    def im2rgb565_fast(im):
        from numpy import array  as nparray
        from numpy import uint16 as npuint16
        data = nparray(im.convert('RGB'))
        R5 = (data[...,0]>>3).astype(npuint16) << 11
        G6 = (data[...,1]>>2).astype(npuint16) << 5
        B5 = (data[...,2]>>3).astype(npuint16)
        x = R5 | G6 | B5
        x = x.astype('>u2') # big endian
        return x.tobytes()

    def im2rgb565(im):
        data = im.convert('RGB')
        pixels = data.load()
        width, height = data.size
        rgb565_data = bytearray(width*height*2)
        n = 0
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                #rgb565_data[n:n+1] = (rgb565 & 0xFF, (rgb565 >> 8) & 0xFF) # little endian
                rgb565_data[n:n+1] = ((rgb565 >> 8) & 0xFF, rgb565 & 0xFF) # big endian
                n += 2
        return rgb565_data

    def imageConvert(im, fastMethod = True):
        return DmdPlayer.im2rgb565_fast(im)
        if fastMethod:
            return DmdPlayer.im2rgb565_fast(im)
        else:
            return DmdPlayer.im2rgb565(im)

    def getHeader(width, height, layer, nbytes):
        endianness = "big"
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
        msg = header + im
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

    def txt2image(txt, font, gradient, width, height, fillcolor, xoffset, yoffset, spacing, align):
        if gradient is not None:
            im = Image.new('L', (width, height))
            draw = ImageDraw.Draw(im)
            gradback = Image.open(gradient).resize((width, height))
            draw.multiline_text((xoffset, yoffset), txt, font=font, spacing=spacing, align=align, fill='white')
            gradback.putalpha(im)
            return gradback
        else:
            im = Image.new('RGB', (width, height))
            draw = ImageDraw.Draw(im)
            draw.multiline_text((xoffset, yoffset), txt, font=font, spacing=spacing, align=align, fill=fillcolor)
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
                    if "loop" in im.info:
                        if im.info["loop"] == 1: # if the image precise to loop only once, and once is not set, set it to 1
                            once = True
            else:
                im = DmdPlayer.imageFit(im, width, height)
                DmdPlayer.sendFrame(header, client, layer, DmdPlayer.imageConvert(im, False))
        # close the image to just play the cache
        if anim_cache is not None:
            DmdPlayer.playAnim(header, client, layer, anim_cache, once)

    def sendVideoFile(header, client, layer, file, width, height, once):
        import cv2
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

    def sendText(header, client, layer, text, color, target_width, target_height, fontfile, gradient, moving_text, fixed_text, speed, move, once, no_fit, line_spacing, align, fastMethod = True):
        #text = bytes(text, 'utf-8').decode("unicode_escape") # so that you can use '\n' # this one break utf-8 chars
        text = text.replace("\\n", "\n")
        lines = text.splitlines()
        if len(lines) < 1:
            lines = [ '' ]
        font = ImageFont.truetype(fontfile, target_height // len(lines))
        im = Image.new('RGB', (target_width, target_height))
        draw = ImageDraw.Draw(im)
        (left, top, right, bottom) = draw.multiline_textbbox((0,0), text, font=font, spacing=line_spacing, align=align)
        img_width  = int(right - left)
        img_height = int(bottom - top)
        fit = (img_width < target_width) and (img_height < target_height)
        if gradient is not None:
            no_fit = False
        if fit and (moving_text is not True or fixed_text is True): # the text fit on the screen
            im = DmdPlayer.txt2image(text, font, gradient, img_width, img_height, color, 0, -top, line_spacing, align)
            if not no_fit:
                im = DmdPlayer.imageFit(im, target_width, target_height) # an optimisation could be to directly fit with an extra argument in txt2image
            DmdPlayer.sendFrame(header, client, layer, DmdPlayer.imageConvert(im, fastMethod))
        elif not fit and (moving_text is not True or fixed_text is True): # it doesn't fix, resize
            im = DmdPlayer.txt2image(text, font, gradient, img_width, img_height, color, 0, -top, line_spacing, align)
            im = im.resize((target_width, img_height * target_width // img_width))
            if not no_fit:
                im = DmdPlayer.imageFit(im, target_width, target_height) # an optimisation could be to directly fit with an extra argument in txt2image
            DmdPlayer.sendFrame(header, client, layer, DmdPlayer.imageConvert(im, fastMethod))
        else:
            # move the text ; generate all the frames in a cache first
            anim_cache = []
            im = DmdPlayer.txt2image(text, font, gradient, img_width, img_height, color, 0, -top, line_spacing, align)
            if not no_fit:
                im = DmdPlayer.imageFit(im, target_width, target_height, False)
            reswidth, resimg_height = im.size
            for i in range(1, target_width+reswidth, move):
                new_im = Image.new('RGB', (target_width, target_height))
                new_im.paste(im, (target_width-i, 0))
                anim_cache.append({ "img": DmdPlayer.imageConvert(new_im, fastMethod), "duration": speed })
            DmdPlayer.playAnim(header, client, layer, anim_cache, once)

    def sendClock(header, client, layer, color, width, height, fontfile, gradient, speed, h12, no_seconds, clock_format, line_spacing, align):
        previousTxt = ""
        while True:
            if clock_format:
                localtime = time.strftime(clock_format, time.localtime())
            elif h12:
                if no_seconds:
                    localtime = time.strftime("%-I:%M %p", time.localtime())
                else:
                    localtime = time.strftime("%-I:%M:%S %p", time.localtime())
            else:
                if no_seconds:
                    localtime = time.strftime("%H:%M", time.localtime())
                else:
                    localtime = time.strftime("%H:%M:%S", time.localtime())
            if previousTxt != localtime:
                previousTxt = localtime
                DmdPlayer.sendText(header, client, layer, localtime, color, width, height, fontfile, gradient, False, True, speed, 0, True, False, line_spacing, align)
            time.sleep(speed/1000)

    # https://stackoverflow.com/questions/538666/format-timedelta-to-string
    def strfdelta(tdelta, fmt='{D:02}d {H:02}h {M:02}m {S:02}s', inputtype='timedelta'):
        """Convert a datetime.timedelta object or a regular number to a custom-
        formatted string, just like the stftime() method does for datetime.datetime
        objects.

        The fmt argument allows custom formatting to be specified.  Fields can
        include seconds, minutes, hours, days, and weeks.  Each field is optional.

        Some examples:
            '{D:02}d {H:02}h {M:02}m {S:02}s' --> '05d 08h 04m 02s' (default)
            '{W}w {D}d {H}:{M:02}:{S:02}'     --> '4w 5d 8:04:02'
            '{D:2}d {H:2}:{M:02}:{S:02}'      --> ' 5d  8:04:02'
            '{H}h {S}s'                       --> '72h 800s'

        The inputtype argument allows tdelta to be a regular number instead of the
        default, which is a datetime.timedelta object.  Valid inputtype strings:
            's', 'seconds',
            'm', 'minutes',
            'h', 'hours',
            'd', 'days',
            'w', 'weeks'
        """

        # Convert tdelta to integer seconds.
        if inputtype == 'timedelta':
            remainder = int(tdelta.total_seconds())
        elif inputtype in ['s', 'seconds']:
            remainder = int(tdelta)
        elif inputtype in ['m', 'minutes']:
            remainder = int(tdelta)*60
        elif inputtype in ['h', 'hours']:
            remainder = int(tdelta)*3600
        elif inputtype in ['d', 'days']:
            remainder = int(tdelta)*86400
        elif inputtype in ['w', 'weeks']:
            remainder = int(tdelta)*604800

        f = Formatter()
        desired_fields = [field_tuple[1] for field_tuple in f.parse(fmt)]
        possible_fields = ('W', 'D', 'H', 'M', 'S')
        constants = {'W': 604800, 'D': 86400, 'H': 3600, 'M': 60, 'S': 1}
        values = {}
        for field in possible_fields:
            if field in desired_fields and field in constants:
                values[field], remainder = divmod(remainder, constants[field])
        return f.format(fmt, **values)

    def sendCountdown(header, client, layer, countdown, color, width, height, fontfile, gradient, speed, countdown_header, countdown_format, countdown_format_0_day, countdown_format_0_hour, countdown_format_0_minute, line_spacing, align):
        target = datetime.strptime(countdown, '%Y-%m-%d %H:%M:%S')

        while True:
            now    = datetime.now()
            delta  = abs(target - now)
            total_seconds = delta.total_seconds()
            if (total_seconds > 0 and total_seconds < 60) or (total_seconds < 0 and total_seconds > -60):
                txt = DmdPlayer.strfdelta(delta, countdown_format_0_minute)
            elif (total_seconds > 0 and total_seconds < 3600) or (total_seconds < 0 and total_seconds > -3600):
                txt = DmdPlayer.strfdelta(delta, countdown_format_0_hour)
            elif (total_seconds > 0 and total_seconds < 86400) or (total_seconds < 0 and total_seconds > -86400):
                txt = DmdPlayer.strfdelta(delta, countdown_format_0_day)
            else:
                txt = DmdPlayer.strfdelta(delta, countdown_format)
            if countdown_header is not None:
                txt = countdown_header + "\n" + txt
            DmdPlayer.sendText(header, client, layer, txt, color, width, height, fontfile, gradient, False, True, speed, 0, True, False, line_spacing, align)
            time.sleep(speed/1000)

    def args():
        parser = argparse.ArgumentParser(prog="dmd-play")
        parser.add_argument("-f", "--file", help="image path file")
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
        parser.add_argument("--gradient", default=None,                help="gradient file (rainbow effect and more)")
        parser.add_argument("-l", "--line-spacing",  type=int, default=2, help="number of pixels between each line of text")
        parser.add_argument("--align",  type=str, default='center',    help="text alignment: center, left or right")
        parser.add_argument("-c", "--clock",  action="store_true",     help="display current time")
        parser.add_argument("--no-seconds",  action="store_true",      help="clock: display only hours and minutes, no seconds")
        parser.add_argument("--h12",  action="store_true",             help="clock: 12-hour format with AM and PM (default it 24h)")
        parser.add_argument("--clock-format", type=str, default=None,  help="clock: strftime-formatted string (superseeds --h12 and --no-seconds)")
        parser.add_argument("-C", "--countdown",                       help="display a countdown (2050-06-30 15:00:00)")
        parser.add_argument("--countdown-header",                      help="equivalent of changing all format with a prefix")
        parser.add_argument("--countdown-format",          default="{D:2}d {H:2}:{M:02}:{S:02}", help="countdown format")
        parser.add_argument("--countdown-format-0-day",    default="{H:2}:{M:02}:{S:02}",        help="countdown format when less than 1 day")
        parser.add_argument("--countdown-format-0-hour",   default="{M:2}:{S:02}",               help="countdown format when less than 1 hour")
        parser.add_argument("--countdown-format-0-minute", default="{S:2}",                      help="countdown format when less than 1 minute")
        parser.add_argument("-p", "--port", type=int, default=6789,    help="network connexion port")
        parser.add_argument("--host", default="localhost",             help="dmd server host")
        parser.add_argument("--width",  type=int, default=128,         help="dmd width")
        parser.add_argument("--height", type=int, default= 32,         help="dmd height")
        parser.add_argument("--hd",    action="store_true",            help="hd format, equivalent of --width 256 --height 64")
        return parser.parse_args()

    def connect(args):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((socket.gethostbyname(args.host), args.port))
        return client

    def run(args):
        allNone = True
        if args.file is not None:
            allNone = False
        if args.text is not None:
            allNone = False
        if args.video is not None:
            allNone = False
        if args.clear is True:
            allNone = False
        if args.clock is True:
            allNone = False
        if args.countdown is not None:
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
                text = re.sub(r'\\N', '\n', text)
            else:
                text = args.text
            DmdPlayer.sendText(header, client, layer, text, (args.red, args.green, args.blue), width, height, args.font, args.gradient, args.moving_text, args.fixed_text, args.speed, move, args.once, args.no_fit, args.line_spacing, args.align, args.moving_text is True and args.fixed_text is False)
        elif args.clock:
            DmdPlayer.sendClock(header, client, layer, (args.red, args.green, args.blue), width, height, args.font, args.gradient, args.speed, args.h12, args.no_seconds, args.clock_format, args.line_spacing, args.align)
        elif args.countdown:
            DmdPlayer.sendCountdown(header, client, layer, args.countdown, (args.red, args.green, args.blue), width, height, args.font, args.gradient, args.speed, args.countdown_header, args.countdown_format, args.countdown_format_0_day, args.countdown_format_0_hour, args.countdown_format_0_minute, args.line_spacing, args.align)
        elif args.video:
            DmdPlayer.sendVideoFile(header, client, layer, args.video, width, height, args.once)
        elif args.clear:
            DmdPlayer.sendText(header, client, layer, "", (args.red, args.green, args.blue), width, height, args.font, args.gradient, False, True, args.speed, move, True, False, args.line_spacing, args.align, False)

        if args.overlay:
            time.sleep(args.overlay_time/1000)

        client.close()

      
