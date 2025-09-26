#!/usr/bin/env python3

"""WebSocket Client to test remote control of the game"""

from websockets.sync.client import connect
import argparse

def message(args):
    with connect("ws://"+args.wshost+":"+str(args.wsport)) as websocket:
        websocket.send(args.action)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="ws_client.py")
    parser.add_argument("--wshost",                     default="0.0.0.0",      help="WebSocket host (default 0.0.0.0)")
    parser.add_argument("--wsport",     type=int,       default=8080,           help="WebSocket port (default 8080)")    
    parser.add_argument("--action",                     default="right",        help="action: left or right (default right)")
    args=parser.parse_args()     
    message(args)