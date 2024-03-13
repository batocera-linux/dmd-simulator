#!/usr/bin/env python3

import sys
import argparse
import socket
import numpy as np
import asyncio
from urllib.parse      import urlparse, parse_qs
from aiohttp           import web
from websockets.server import serve

class DmdSimulator():

    def im2rgb888(im):
        data = np.frombuffer(im, dtype=np.uint16)
        R8 = ((data >> 11) << 3).astype(np.uint8)
        G8 = (((data << 5) >> 10) << 2).astype(np.uint8)
        B8 = ((data << 11) >> 8).astype(np.uint8)
        return np.dstack((R8,G8,B8))

    def convertImageRGB5652Html(image, width, height):
        image888 = DmdSimulator.im2rgb888(image)
        res = ""
        for y in range(height):
            for x in range(width):
                pix = image888[0][(y*width+x)]
                if pix[0] == 0 and pix[1] == 0 and pix[2] == 0:
                    res += "."
                else:
                    res += format(pix[0], '02x') + format(pix[1], '02x') + format(pix[2], '02x')
        return res

    async def web_handle_client_index(request):
        print("web : new connexion from {}".format(request.remote))
        q = urlparse(request.path_qs)
        p = parse_qs(q.query)
        psize = 10
        ptop  =  0
        pmode = "led"
        if "size" in p:
            psize = int(p["size"][0])
        if "top" in p:
            ptop = int(p["top"][0])
        if "mode" in p:
            if p["mode"][0] == "flat":
                pmode = "flat"
            else:
                pmode = "led"
        content = """<html>
  <head>
  <title>DMD Simulator</title>
  <script>
    window.addEventListener('load', function() {
      const websocket = new WebSocket("ws://""" + request.host.split(":")[0] + """:""" + str(DmdSimulator.wsport) + """/");
      var width = """ + str(DmdSimulator.width) +  """;

      websocket.addEventListener("message", ({data}) => {
        if(data[0] == '*') {
          document.getElementById('dmd').innerHTML = '<div style="color: white; font-size: 2em;">Nothing yet</div>';
        } else if(data[0] != '#') {
          var n = 0;
          var i = 0;
          var res = "";
          while(n < data.length) {
            if(i%width == 0) res += "<div>";
            if(data[n] == '.') {
              res += '<span class="x"> </span>';
              n++;
            } else {
              res += '<span class="p" style="background-color: #' + data[n] + data[n+1] + data[n+2] + data[n+3] + data[n+4] + data[n+5] + ';"> </span>';
              n+=6;
            }
            if(i%width == width-1) res += "</div>";
            i++;
          }
          document.getElementById('dmd').innerHTML = '<div id="overlay"></div>' + res;
        }
      });

      websocket.addEventListener("close", (event) => {
        document.getElementById('dmd').innerHTML = '<div style="color: white; font-size: 2em;">Disconnected</div>';
      });

    });
  </script>
  <style>
  body {background-color: black;}
  #dmd {background-color: black; text-align: center; padding-top: """ + str(ptop) + """px }
"""
        content += "  #overlay { position: absolute; width: 100%; height: " + str(DmdSimulator.height*(psize+2)) +  "px; }\n"
        if pmode == "led":
            content += "  #overlay { backdrop-filter: blur(1px); filter: brightness(250%); }\n"
        content += ".x { background-color: black; }\n"
        content += ".x, .p { display: inline-block; width: " + str(psize) + "px; height: " + str(psize) + "px; margin: 1px; }\n"
        if pmode == "led":
            content += ".x, .p { border-radius: " + str(psize) + "px; }\n"
            content += ".x, .p { box-shadow: inset 4px -1px " + str(psize-3) + "px -1px #151515; }\n"
        content += """
  </style>
</head>
<body>
<div style="font-family: monospace;" id="dmd" />
</body>
</html>"""
        return web.Response(text=content, content_type="text/html")

    async def run_webserver(host, port):
        print("web: starting ({}:{})".format(host, port))
        try:
            app = web.Application()
            app.add_routes([web.get('/', DmdSimulator.web_handle_client_index)])
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, host, port)
            await site.start()
            await asyncio.Future()
        except:
            print("web: stopping")
            await runner.cleanup()

    async def ws_handle_client(websocket, path):
        try:
            if DmdSimulator.wsclient is not None:
                try:
                    await DmdSimulator.wsclient.close()
                except:
                    pass
            print("ws : new connexion from {}".format(websocket.remote_address[0]))
            DmdSimulator.wsclient = websocket
            await DmdSimulator.wsclient.send(DmdSimulator.image)
            await asyncio.Future()
        finally:
            print("ws: closing client")

    async def run_wsserver(host, port):
        print("ws : starting ({}:{})".format(host, port))
        try:
            async with serve(DmdSimulator.ws_handle_client, host, port):
                await asyncio.Future()
        except:
            print("ws : stopping")
            if DmdSimulator.wsclient is not None:
                try:
                    await DmdSimulator.wsclient.close()
                except:
                    pass

    async def dmd_handle_client(reader, writer):
        isFavorite = True
        while True:
            try:
                requestHeader = (await reader.readexactly(24))
                endianness = sys.byteorder
                hcode = requestHeader[0:10]
                if hcode != bytearray("DMDStream", "utf-8") + b'\x00':
                    raise Exception("invalid header")
                #version    = requestHeader[10]
                #mode       = int.from_bytes(requestHeader[11:15], endianness)
                #width      = int.from_bytes(requestHeader[15:17], endianness)
                #height     = int.from_bytes(requestHeader[17:19], endianness)
                buffered   = requestHeader[19]
                packetsize = int.from_bytes(requestHeader[20:25], endianness)

                layer = "main"
                if buffered == 1:
                    layer = "overlay"
                if isFavorite: # for the first frame, the client is prefered (and others disconnected)
                    isFavorite = False
                    if layer == "main":
                        if DmdSimulator.dmdclient_main is not None and DmdSimulator.dmdclient_main != writer:
                            print("force closing main client")
                            DmdSimulator.dmdclient_main.close()
                        DmdSimulator.dmdclient_main  = writer
                    if layer == "overlay":
                        if DmdSimulator.dmdclient_layer is not None and DmdSimulator.dmdclient_layer != writer:
                            print("force closing layer client")
                            DmdSimulator.dmdclient_layer.close()
                        DmdSimulator.dmdclient_layer = writer

                request  = (await reader.readexactly(packetsize))
                frame = DmdSimulator.convertImageRGB5652Html(request, DmdSimulator.width, DmdSimulator.height)

                newFrame = False
                if DmdSimulator.dmdclient_main == writer: # now that there is no more await, check we did'nt changed the client
                    if layer == "main":
                        DmdSimulator.image = frame
                        newFrame = True
                if DmdSimulator.dmdclient_layer == writer: # now that there is no more await, check we did'nt changed the client
                    if layer == "overlay":
                        DmdSimulator.layer = frame
                        newFrame = True
                if newFrame and DmdSimulator.wsclient is not None:
                    try:
                        if not (layer == "main" and DmdSimulator.layer is not None):
                            await DmdSimulator.wsclient.send(frame)
                    except:
                        pass
            except:
                if DmdSimulator.dmdclient_main == writer:
                    DmdSimulator.dmdclient_main  = None
                if DmdSimulator.dmdclient_layer == writer:
                    DmdSimulator.dmdclient_layer = None
                    DmdSimulator.layer = None
                    if DmdSimulator.wsclient is not None:
                        await DmdSimulator.wsclient.send(DmdSimulator.image) # reupdate with the main image (in case of static image)
                break

    async def run_dmdserver(host, port):
        print("dmd: starting ({}:{})".format(host, port))
        try:
            server = await asyncio.start_server(DmdSimulator.dmd_handle_client, host, port)
            async with server:
                await server.serve_forever()
        except:
            print("dmd: stopping")
            
    async def run(width, height, dmd_host, dmd_port, web_host, web_port, ws_host, ws_port):
        DmdSimulator.wsclient = None
        DmdSimulator.wsport   = ws_port
        DmdSimulator.width    = width
        DmdSimulator.height   = height
        DmdSimulator.image    = '*'
        DmdSimulator.layer    = None
        DmdSimulator.dmdclient_main  = None
        DmdSimulator.dmdclient_layer = None
        try:
            await asyncio.gather(DmdSimulator.run_dmdserver(dmd_host, dmd_port), DmdSimulator.run_webserver(web_host, web_port), DmdSimulator.run_wsserver(ws_host, ws_port))
        except:
            pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="dmd-simulator")
    parser.add_argument("--width",    type=int, default=128,         help="virtual dmd width")
    parser.add_argument("--height",   type=int, default= 32,         help="virtual dmd height")
    parser.add_argument("--dmd-port", type=int, default=6789,        help="dmd listen port")
    parser.add_argument("--web-port", type=int, default=8080,        help="web listen port")
    parser.add_argument("--ws-port",  type=int, default=6790,        help="ws listen port")
    parser.add_argument("--dmd-host",           default="localhost", help="dmd listen interface address")
    parser.add_argument("--web-host",           default="",          help="web listen interface address")
    parser.add_argument("--ws-host",            default="",          help="ws listen interface address")

    args = parser.parse_args()
    asyncio.run(DmdSimulator.run(args.width, args.height, args.dmd_host, args.dmd_port, args.web_host, args.web_port, args.ws_host, args.ws_port))
