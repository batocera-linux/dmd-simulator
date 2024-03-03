FROM ubuntu:23.10

RUN apt update && apt install -y python3-numpy python3-aiohttp python3-websockets python3-pillow fonts-dejavu-core && apt-get clean && rm -rf /var/lib/apt/lists/*
COPY dmd-simulator.py dmd-play.py /usr/bin/

EXPOSE 8080
EXPOSE 53533
EXPOSE 53534
CMD python3 /usr/bin/dmd-simulator.py --dmd-host ""
