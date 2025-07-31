#!/usr/bin/env python3

from dmd_simulator.dmd_player import DmdPlayer

def dmd_play_launch() -> None:
    args=DmdPlayer.args()
    DmdPlayer.run(args)

if __name__ == '__main__':
    dmd_play_launch()
