# -*- coding: utf-8 -*-
import sys
import json
import os

sys.path.append(r"C:\Program Files (x86)\PTI\PSSE34\PSSPY27")
os.environ['PATH'] += ";" + r"C:\Program Files (x86)\PTI\PSSE34\PSSPY27"

import psse34
import dyntools

if len(sys.argv) < 2:
    print("Uso: lector_out_legacy.py <archivo.out> [<nombre_canal>]")
    sys.exit(1)

filepath = sys.argv[1]
chnf = dyntools.CHNF(filepath)
_, ch_id, ch_data = chnf.get_data()

# Solo listar canales si no se especificó canal específico
if len(sys.argv) == 2:
    print(json.dumps({"canales": ch_id}))
else:
    channel_name = sys.argv[2]
    for key, name in ch_id.items():
        if name == channel_name:
            print(json.dumps({"time": ch_data['time'], "valores": ch_data[key]}))
            break