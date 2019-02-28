#! /bin/bash

nohup stdbuf -oL python natchk.py s2 &>> nat.log &
