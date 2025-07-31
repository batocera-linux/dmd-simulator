# description
dmd-simulator is a server that aims to simulate a real dmd into a browser.

dmd-play is a client that connect on the server to load images (png and animatd gif) or videos or texts.

dmd-play and dmd-simulator communicates via a tcp connexion.

dmd-simulator and the browser communicates via websockets.

dmd-tetris is a tetris game your can play with a pad.

# build
``$ virtualenv venv``

``$ source venv/bin/activate``

``$ pip install .``

# execute
``$ dmd-simulator``
or
``$ DMD_WIDTH=64 DMD_HEIGHT=64 dmd-simulator``

run in browser : http://localhost:8080/?size=12&top=200&mode=led

## url optionnal options
- mode includes: led | flat
- size : pixel size
- top  : border from the top

# play an image from the client
<code>$ python3 dmd-play.py -f file.png
$ python3 dmd-play.py -f file.gif
$ python3 dmd-play.py -v file.mp4
$ python3 dmd-play.py -t "Hello world"
$ python3 dmd-play.py --help
options:
  -h, --help            show this help message and exit
  -f FILE, --file FILE
  -v VIDEO, --video VIDEO
  -t TEXT, --text TEXT
  --font FONT           path to the font file
  --clear               clear the screen
  --overlay             restore the previous frames once finished
  --overlay-time OVERLAY_TIME
                        time to pause fixed images for the overlay in ms
  --moving-text         always makes the text to move, even if text fits
  --fixed-text          never makes the text to move, prefer to adjust size
  -r RED, --red RED     red text color
  -g GREEN, --green GREEN
                        green text color
  -b BLUE, --blue BLUE  blue text color
  -s SPEED, --speed SPEED
                        sleep time during each text position (in milliseconds)
  -m MOVE, --move MOVE  text movement each time
  --once                don't loop forever
  -p PORT, --port PORT  network connexion port
  --host HOST           dmd server host
  --width WIDTH         dmd width
  --height HEIGHT       dmd height
</code>

# examples
![Alt text](demo/helloworld.png "Hello world")
![Alt text](demo/zelda_led.png "zelda led")
![Alt text](demo/zelda_flat.png "zelda flat")
