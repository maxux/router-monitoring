#!/bin/bash
tmux new-session -d -s monitoring
tmux split-window -t monitoring -v
tmux select-layout -t monitoring even-vertical
