#!/bin/bash
swayidle -w \
timeout 600 'hyprctl dispatch dpms off' \
resume 'hyprctl dispatch dpms on' \
#timeout 660 'systemctl suspend' \
#timeout 600 'swaylock' \
#before-sleep 'swaylock'
