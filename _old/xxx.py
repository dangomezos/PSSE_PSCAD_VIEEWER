# -*- coding: utf-8 -*-
# import sys, os
# PSSE = r"C:\Program Files (x86)\PTI\PSSE34\PSSPY27"
# sys.path.append(PSSE)
# os.environ['PATH'] = os.environ['PATH'] + ';' +PSSE


# import psse34

# import dyntools

# print("Dyntools from:", dyntools.__file__)

# # chnf = dyntools.CHNF(r"C:\Users\dgome\Downloads\31HW1ap-eq_2_clusters_V5_BF_IND.out")  # Mueve el archivo aquí primero
# chnf = dyntools.CHNF(r"C:\Users\dgome\Downloads\AVR_Step.out")
# short_title, chanid, chandata = chnf.get_data()

# print("Channels:", chanid)
import psse35
import dyntools
chnf = dyntools.CHNF(r"C:\Users\dgome\Downloads\AVR_Step.out")
print(chnf.__dict__.keys())