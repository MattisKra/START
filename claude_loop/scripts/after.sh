#!/bin/zsh
G=$1; cd "/Users/leo/Desktop/[PUBLIC] Road to Start HACK"
python3 -I work/scripts/tx.py work/tx $G $G && python3 -I work/scripts/ref.py work/tx work/ex work/ref.txt && sed -n "/^=== game $G /,\$p" work/ref.txt && python3 -I work/scripts/acc.py work/tx $G $G | cut -c1-260 && python3 -I work/scripts/eval.py work/tx $G | cut -c1-220
