"""
 board.py


 Python classes used to handling detector layout and board configurations, and
 positional calibration results. More details will be provided in the per class
 documentations.
"""
from datetime import time
import cmod.gcoder as gcoder
import json
import logging

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
   try:
      self.type = jsonmap['type']
      self.mode = int(jsonmap['mode'])
      self.channel = int(jsonmap['channel'])
      self.coordinates = {
        "default": jsonmap['coordinates']['default'],
        "calibrated": jsonmap['coordinates']['calibrated'] if len(jsonmap['coordinates']['calibrated']) > 0 else [] # a stack
      }
   except KeyError as e:
     raise ValueError(e.msg)


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
       'type': self.type,
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
   self.filename = ""
   self.type = ""
   self.description = ""
   self.id = -1
   self.detectors = []
   self.calib_routines = []
#    TODO: add the board conditions
   self.conditions = {}


   self.cmd = cmd # Reference to main object
   self.logger = self.cmd.devlog("Board")


 def clear(self):
   self.filename = ""
   self.type = ""
   self.description = ""
   self.id = -1
   self.detectors = []
   self.calib_routines = []
   self.conditions = {}

 def __dict__(self):
   return {
     'filename': self.filename,
     'type': self.type,
     'description': self.description,
     'id': self.id,
     'detectors': [det.__dict__ for det in self.detectors],
     'calib_routines': self.calib_routines,
     'conditions': self.conditions
   }

 def save_board(self, filename=""):
    if not(filename == ""):
      self.filename = filename
    
    if self.filename == "":
      self.filename = f"cfg/{self.type}_{self.id}_{time.strftime('%Y%m%d-%H%M%S')}.json"
    else:
      with open(self.filename, 'w') as f:
        f.write(json.dumps(self.__dict__, indent=2))


 def load_board(self, filename):
   if any(self.get_all_detectors()) or not self.empty():
     self.logger.warning("""
       The current session is not empty. Loading a new board will erase any
       existing configuration for the current session""")

   jsonmap = json.loads(open(filename, 'r').read())
   self.filename = filename
   # only load the board if the file contains the required fields
   if 'type' in jsonmap and 'description' in jsonmap and 'detectors' in jsonmap and len(jsonmap['detectors']) > 0:
       jsonmap = json.loads(open(filename, 'r').read())
       self.type = jsonmap['type']
       self.description = jsonmap['description']
       self.id = jsonmap['id'] if 'id' in jsonmap else -1
       self.calib_routines = jsonmap['calib_routines'] if 'calib_routines' in jsonmap else []
       self.conditions = jsonmap['conditions'] if 'conditions' in jsonmap else {}

       for detid in range(1, len(jsonmap['detectors'])+1):
          det = jsonmap['detectors'][detid-1]
          try:
            self.detectors.append(Detector(det, self))
          except ValueError as e:
            self.logger.error(f"""
            Error when loading board in {filename}: The entry {detid} in the detectors list in the board config file does not contain all the  required fields: 'type', 'mode', 'channel', and 'coordinates'. Please check the entry and the required format and try again. The following exception was raised: {e.msg}
            """)
            self.clear()
            return False
       return True
   else:
   #   TODO add documentation for format of the config file
       self.logger.error("""
       The board config file does not contain the required fields: 'type', 'description', and 'detectors'. Please check the
        file and the required format and try again.""")
       self.clear()
       return False

 def get_detector(self, detid):
   # -1 as detid is the detector's index in the list + 1
   return self.detectors[detid-1]


 def get_all_detectors(self):
   return self.detectors
 
 def set_id(self, id):
   self.id = id


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
   
   self.save_board()


 def add_visM(self, detid, z, data, filename):
   self.detectors[detid-1]['coordinates']['calibrated'].append({
     'command': 'visualhscan',
     'z': self.roundz(z),
     'data': {
        'transform': data,
        'file': filename
     }
    })

   self.save_board()



 def add_lumi_coord(self, detid, z, data):
   self.detectors[detid-1]['coordinates']['calibrated'].append({
     'command': 'halign',
     z: self.roundz(z),
     'data': {
       'coordinates': data
     }
    })

   self.save_board()


 def get_latest_entry(self, detid, commandname, z=None):
   for i in range(len(self.detectors[detid-1]['coordinates']['calibrated'])-1, -1, -1):
     entry = self.detectors[detid-1]['coordinates']['calibrated'][i]
     if entry['command'] == commandname and (z is None or entry['z'] == self.roundz(z)):
       return entry
   return None
 
 def get_closest_calib_z(self, detid, commandname, current_z):
   z_lst = []

   for i in range(len(self.detectors[detid-1]['coordinates']['calibrated'])-1, -1, -1):
     entry = self.detectors[detid-1]['coordinates']['calibrated'][i]
     if entry['command'] == commandname:
       z_lst.append(entry['z'])
   return min(z_lst, key=lambda x:abs(float(x)-float(current_z)))

 def get_vis_coord(self, detid, z):
   return self.get_latest_entry(detid, 'visualcenterdet', z)


 def get_visM(self, detid, z):
   return self.get_latest_entry(detid, 'visualhscan', z)

 def get_lumi_coord(self, detid, z):
   return self.get_latest_entry(detid, 'halign', z)\
   
 def get_lumi_vis_separation(self, detid, z):
   return self.get_latest_entry(detid, 'lumi_vis_separation', z)

 def add_lumi_vis_separation(self, detid, z, h):
   self.detectors[detid-1]['coordinates']['calibrated'].append({
     'command': 'lumi_vis_separation', 
     'z': self.roundz(z), 
     'data': {
       'separation': h
     }
    })
   
   self.save_board()


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
