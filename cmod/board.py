"""
 board.py


 Python classes used to handling detector layout and board configurations, and
 positional calibration results. More details will be provided in the per class
 documentations.
"""
import cmod.gcoder as gcoder
import json
import logging
from enum import Enum


# class BoardType(Enum):
#   # add more board types as needed
#   PROD = 'prod'
#   REF = 'ref'
#   TEST = 'test'

class CmdType(Enum):
  # add more commands as needed
  VISUALCENTERDET = 'visualcenterdet'
  VISUALHSCAN = 'visualhscan'
  HALIGN = 'halign'

class Detector(object):
 """
 A detector element is defined as an object with a specific readout mode, a
 corresponding channel, and at least one set of (default) coordinates. The
 handling of the detector. No name will be given for the detector element here,
 that will be handled by the parent "Board" class.


 The calibrated coordinates (either the visually calibrated coordinates and the
 accompanying transformation matrix, or the luminosity aligned coordinates will
 be stored as a dictionary, with the z operation value used for obtaining the
 calibration used as the key.)
 """
 def __init__(self, jsonmap, board):
   self.mode = int(jsonmap['mode'])
   self.channel = int(jsonmap['channel'])
   self.coordinates = {
     "default": jsonmap['coordinates']['default'],
     "calibrated": jsonmap['coordinates']['calibrated'] if not (len(jsonmap['coordinates']['calibrated']) == 0) else [] # a stack
    }


   # TODO: add the conditions calculated per detector
   # self.vis_coord = {}
   # self.vis_M = {}
   # self.lumi_coord = {}
   self.logger = board.cmd.devlog("Det")


   # Additional parsing.
   if (self.orig_coord[0] > gcoder.GCoder.max_x() or  #
       self.orig_coord[1] > gcoder.GCoder.max_y() or  #
       self.orig_coord[0] < 0 or self.orig_coord[1] < 0):
     self.logger.warning(f"""
       The specified detector position (x:{self.orig_coord[0]},
       y:{self.orig_coord[1]}) is outside of the gantry boundaries
       (0-{gcoder.GCoder.max_x()},0-{gcoder.GCoder.max_y()}). The expected
       detector position will be not adjusted, but gantry motion might not
       reach it. Which mean any results may be wrong.""")
       # TODO: handle this in the gantry motions when cannot reach sipm


 def __str__(self):
   return str(self.__dict__)


 def __dict__(self):
   return {
       'mode': self.mode,
       'channel': self.channel,
       'coordinates': self.coordinates,
       # 'Luminosity coordinates': self.lumi_coord,
       # 'Visual coordinates': self.vis_coord,
       # 'FOV transformation': self.vis_M
   }




class Board(object):
 """
 Class for storing a board type an a list of det x-y positions
 """
 def __init__(self, cmd):
   self.type = ""
   self.description = ""
   self.detectors = []
   self.calib_routines = []
#    TODO: add the board conditions
   self.conditions = {}


   self.cmd = cmd # Reference to main object
   self.logger = self.cmd.devlog("Board")


 def clear(self):
   self.type = ""
   self.description = ""
   self.detectors = []
   self.calib_routines = []
   self.conditions = {}


 def load_board(self, file):
   if any(self.get_all_detectors()) or not self.empty():
     self.logger.warning("""
       The current session is not empty. Loading a new board will erase any
       existing configuration for the current session""")


   # only load the board if the file contains the required fields
   if 'type' in jsonmap and 'description' in jsonmap and 'detectors' in jsonmap and len(jsonmap['detectors'].keys()) > 0:
       jsonmap = json.loads(open(file, 'r').read())
       self.type = jsonmap['type']
       self.description = jsonmap['description']
       self.calib_routines = jsonmap['calib_routines'] if 'calib_routines' in jsonmap else []
       self.conditions = jsonmap['conditions'] if 'conditions' in jsonmap else {}

       for det in jsonmap['detectors']:
          self.detectors.append(Detector(det, self))
   else:
   #   TODO add documentation for format of the config file
     self.logger.error("""
       The board config file does not contain the required fields: 'type', 'description', and 'detectors'. Please check the
       file and the required format and try again.""")
     return

 def get_detector(self, detid):
   # -1 as detid is the detector's index in the list + 1
   return self.detectors[detid-1]


 def get_all_detectors(self):
   return self.detectors


#   def calib_dets(self):
#    return sorted([k for k in self.get_all_detectors() if int(k) < 0], reverse=True)


#    def add_calib_det(self, detid, mode=-1, channel=-1):
#     if detid not in self.get_all_detectors() and int(detid) < 0:
#         self.detectors[detid] = Detector({
#             "mode": mode,
#             "channel": channel,
#             "default coordinates": [-100, -100]
#         }, self)

 # Get/Set calibration measures with additional parsing
#   TODO: revisit while implementing conditions
 def add_vis_coord(self, detid, z, data, filename):
   self.detectors[detid-1]['coordinates']['calibrated'].append({
     'command': 'visualcenterdet',
     z: self.roundz(z),
     'data': {
       'coordinates': data,
       'file': filename
     }
    })


 def add_visM(self, detid, z, data, filename):
   self.detectors[detid-1]['coordinates']['calibrated'].append({
     'command': 'visualhscan',
     'z': self.roundz(z),
     'data': {
        'transform': data,
        'file': filename
     }
    })


 def add_lumi_coord(self, detid, z, data):
   self.detectors[detid-1]['coordinates']['calibrated'].append({
     'command': 'halign',
     z: self.roundz(z),
     'data': {
       'coordinates': data
     }
    })

 def get_latest_entry(self, detid, commandname, z=None):
   for i in range(len(self.detectors[detid-1]['coordinates']['calibrated'])-1, -1, -1):
     entry = self.detectors[detid-1]['coordinates']['calibrated'][i]
     if entry['command'] == commandname and (z is None or entry['z'] == self.roundz(z)):
       return entry
   return None

 def get_vis_coord(self, detid, z):
   return self.get_latest_entry(detid, 'visualcenterdet', z)


 def get_visM(self, detid, z):
   return self.get_latest_entry(detid, 'visualhscan', z)

 def get_lumi_coord(self, detid, z):
   return self.get_latest_entry(detid, 'halign', z)

 def add_lumi_vis_separation(self, detid, z, h):
   self.detectors[detid-1]['coordinates']['calibrated'].append({
     'command': 'lumi_vis_separation', 
     'z': self.roundz(z), 
     'data': {
       'separation': h
     }
                                   })

 def vis_coord_hasz(self, detid, z):
   return self.get_latest_entry(detid, 'visualcenterdet', z) is not None


 def visM_hasz(self, detid, z):
   return self.get_latest_entry(detid, 'visualhscan', z) is not None


 def lumi_coord_hasz(self, detid, z):
   return self.get_latest_entry(detid, 'halign', z) is not None


# TODO: why is this needed??
 def empty(self):
   for detid in range(0, len(self.detectors)):
     if (self.get_latest_entry(detid, 'visualcenterdet') is not None or self.get_latest_entry(detid, 'visualhscan') is not None or self.get_latest_entry(detid, 'halign') is not None):
       return False
   return True


 @staticmethod
 def roundz(rawz):
   return round(rawz, 1)




## In file unit testing
if __name__ == "__main__":
 board = Board()
 board.load_board('cfg/reference_single.json')
 for det in board.detectors:
   print(det)
