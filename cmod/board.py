"""
 board.py


 Python classes used to handling detector layout and board configurations, and
 positional calibration results. More details will be provided in the per class
 documentations.
"""
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
   self.mode = int(jsonmap['mode'])
   self.channel = int(jsonmap['channel'])
   self.coordinates = {
     "default": jsonmap['default_coordinates'],
     "calibrated": []
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
       'default coordinates': self.orig_coord,
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
   # TODO: revisit condition after revisiting self.empty
   if any(self.get_all_detectors()) or not self.empty():
     self.logger.warning("""
       The current session is not empty. Loading a new board will erase any
       existing configuration for the current session""")


   # only load the board if the file contains the required fields
   if 'type' in jsonmap and 'description' in jsonmap and 'detectors' in jsonmap and len(jsonmap['detectors'].keys()) > 0:
       jsonmap = json.loads(open(file, 'r').read())
       self.type = jsonmap['type']
       self.description = jsonmap['description']
       self.detectors = jsonmap['detectors']
       self.calib_routines = jsonmap['calib_routines'] if 'calib_routines' in jsonmap else []
       self.conditions = jsonmap['conditions'] if 'conditions' in jsonmap else {}
   else:
   #   TODO add documentation for format of the config file
     self.logger.error("""
       The board config file does not contain the required fields: 'type', 'description', and 'detectors'. Please check the
       file and the required format and try again.""")
     return


   # for det in jsonmap['detectors']:
   #   self.detectors.append(Detector(det))


  


#   def load_calib_file(self, file):
   # if not self.empty():
   #   self.logger.warning("""
   #    The current session is not empty. Loading a new boardtype will erase any
   #    existing configuration for the current session""")
   # jsonmap = json.loads(open(file, 'r').read())


   # for det in jsonmap:
   #   if det not in self.detectors:
   #     if int(det) >= 0:
   #       self.logger.warning("""
   #         Detector recorded in the calibration file but not defined in the
   #         calibration, ignoring""")
   #       continue
   #     else:
   #       self.add_calib_det(det)


   #   def format_dict(original_dict):
   #     return {float(z): original_dict[z] for z in original_dict}


   #   self.detectors[det].lumi_coord = format_dict(
   #       jsonmap[det]['Luminosity coordinates'])
   #   self.detectors[det].vis_coord = format_dict(
   #       jsonmap[det]['Visual coordinates'])
   #   self.detectors[det].vis_M = format_dict(jsonmap[det]['FOV transformation'])


#   def save_calib_file(self, file):
#     dicttemp = {det: self.detectors[det].__dict__() for det in self.detectors}


#     with open(file, 'w') as f:
#       f.write(json.dumps(dicttemp, indent=2))


 def get_detector(self, detid):
   # -1 as detid is the detector's index in the list + 1
   return self.detectors[detid-1]


 def get_all_detectors(self):
   return self.detectors


#   def calib_dets(self):
   return sorted([k for k in self.get_all_detectors() if int(k) < 0], reverse=True)


#   def add_calib_det(self, detid, mode=-1, channel=-1):
   detid = str(detid)
   if detid not in self.get_all_detectors() and int(detid) < 0:
     self.detectors[detid] = Detector({
         "mode": mode,
         "channel": channel,
         "default coordinates": [-100, -100]
     }, self)


 # Get/Set calibration measures with additional parsing
#   TODO: revisit while implementing conditions
#   def add_vis_coord(self, det, z, data):
#     det = str(det)
#     self.detectors[det].vis_coord[self.roundz(z)] = data


#   def add_visM(self, det, z, data):
#     det = str(det)
#     self.detectors[det].vis_M[self.roundz(z)] = data


#   def add_lumi_coord(self, det, z, data):
#     det = str(det)
#     self.detectors[det].lumi_coord[self.roundz(z)] = data


#   def get_vis_coord(self, det, z):
#     det = str(det)
#     return self.detectors[det].vis_coord[self.roundz(z)]


#   def get_visM(self, det, z):
#     det = str(det)
#     return self.detectors[det].vis_M[self.roundz(z)]


#   def get_lumi_coord(self, det, z):
#     det = str(det)
#     return self.detectors[det].lumi_coord[self.roundz(z)]


#   def vis_coord_hasz(self, det, z):
#     det = str(det)
#     return self.roundz(z) in self.detectors[det].vis_coord


#   def visM_hasz(self, det, z):
#     det = str(det)
#     return self.roundz(z) in self.detectors[det].vis_M


#   def lumi_coord_hasz(self, det, z):
   det = str(det)
   return self.roundz(z) in self.detectors[det].lumi_coord


# TODO: revisit after implementing conditions
 def empty(self):
#     for det in self.detectors:
#       if (any(self.detectors[det].vis_coord) or any(self.detectors[det].vis_M)
#           or any(self.detectors[det].lumi_coord)):
#         return False
   return True


 @staticmethod
 def roundz(rawz):
   return round(rawz, 1)




## In file unit testing
if __name__ == "__main__":
 board = Board()
 board.load_board('cfg/reference_single.json')
#   print(board.detectors['-100'])
 for det in board.detectors:
   print(det)
 board.save_calib_file('test.json')






# TODO: a function to load gantry conditions from a file
# TODO: a function to save gantry conditions to a file
# TODO: a getter for the gantry conditions
# TODO: implement the gantry conditions calculation
# NOTE: "uses visual system commands"
# gantry conditions should be stored as a dictionary with the following keys:
#   {
#     "FOV_to_gantry_coordinates": {
#       "diff": [0, 0, 0]
#     },
#     "lumi_vs_FOV_center": {
#       "diff": [0,0,0],
#       "FOV_center": [0, 0, 0],
#       "lumi_center": [0, 0, 0]
#     },
#   }


# TODO: a function to load data quality(long term) conditions from a file
# TODO: a function to save data quality(long term) conditions to a file
# TODO: a getter for the data quality(long term) conditions
# TODO: implement the data quality(long term) conditions calculation


