import json
import datetime
import os

from cmod.board import CmdType

# TODO: add custom cmd abstractions for all the "calculate_*" functions later, if needed

# NOTE: "uses visual system commands"
class Conditions(object):
  def __init__(self, cmd):
    self.cmd = cmd
    self.logger = cmd.devlog("Conditions")
    # gantry conditions should be stored as a dictionary with the following keys:
    #   {
    #     "fov_to_gantry_coordinates": {
    #       'z': 5,
    #       "transform": [[xx, xy],[yx, yy]]
    #     },
    #     "lumi_vs_fov_center": {
    #       'z': 5,
    #       "separation": [[xx, xy],[yx, yy]]
    #     },
        # "use_count": 0
    #   }
    self.gantry_conditions = {}
    self.gantry_conditions_use_count = 0
    self.gantry_conditions_filename = None
    self.h_list = []

  # loads gantry conditions from a file and returns True if successful, False otherwise
  def load_gantry_conditions(self, file):
    self.gantry_conditions_filename = file
    conditions = json.loads(open(file, 'r').read())
    try:
      self.gantry_conditions = {
        "FOV_to_gantry_coordinates": {
          "z": conditions["FOV_to_gantry_coordinates"]["z"],
          "transform": conditions["FOV_to_gantry_coordinates"]["data"]["transform"]
        },
        "lumi_vs_FOV_center": {
          "z": conditions["lumi_vs_FOV_center"]["z"],
          "separation": conditions["lumi_vs_FOV_center"]["data"]["separation"]
        },
        "use_count": conditions["use_count"] if "use_count" in conditions else 0
      }
      
      self.increment_use_count()

      self.h_list = [self.gantry_conditions["lumi_vs_FOV_center"]["data"]["separation"]]

      return True
    except KeyError as e:
      self.logger.error(e)
      self.logger.error("""
        The gantry conditions file does not contain the required gantry conditions:
        'FOV_to_gantry_coordinates', and 'lumi_vs_FOV_center'. Please check the
        file and the required format and try again.""")
      # TODO: might want to add logic that if the required conditions are not provided, run the process to calculate those that are missing or even all of them as don't want to trust an "incomplete" set of conditions
      return False

  # saves gantry conditions to a file
  def save_gantry_conditions(self):
    if self.gantry_conditions_filename is None:
      self.create_gantry_conditions_filename()
      self.increment_use_count()

    with open(self.gantry_conditions_filename, 'w') as f:
      f.write(json.dumps(self.gantry_conditions, indent=2))
  
  # returns the gantry conditions
  def get_gantry_conditions(self):
    return self.gantry_conditions
  
  def update_gantry_and_sipm_conditions(self, cmd, detid, z):
    if cmd == CmdType.VISUALCENTERDET:
      if cmd.board.lumi_coord_hasz(detid, z):
        h = cmd.board.get_lumi_coord(detid, z)-cmd.board.get_vis_coord(detid, z)
        cmd.board.add_lumi_vis_separation(detid, z, h)
        # check if we have multiple H values out of tolerance with each other,
        if self.is_h_valid(self.h_list, h, 0.5):
          self.h_list.append(h)
          self.gantry_conditions["lumi_vs_FOV_center"]["separation"] = ((self.gantry_conditions["lumi_vs_FOV_center"]['data']["separation"]*len(self.h_list)) + h) /  (len(self.h_list)+1)
        # TODO: add the else: an error should be raised such that the operator knows that something is wrong (maybe the gantry head dislodged or was tugged
    elif cmd == CmdType.HALIGN:
      if cmd.board.vis_coord_hasz(detid, z):
        h = cmd.board.get_lumi_coord(detid, z)-cmd.board.get_vis_coord(detid, z)
        cmd.board.add_lumi_vis_separation(detid, z, h)

        # check if we have multiple H values out of tolerance with each other,
        if self.is_h_valid(self.h_list, h, 0.5):
          self.h_list.append(h)
          self.gantry_conditions["lumi_vs_FOV_center"]["separation"] = ((self.gantry_conditions["lumi_vs_FOV_center"]["separation"]*len(self.h_list)) + h) /  (len(self.h_list)+1)
        # TODO: add the else: an error should be raised such that the operator knows that something is wrong (maybe the gantry head dislodged or was tugged
    elif cmd == CmdType.VISUALHSCAN:
      visM = cmd.board.getVisM(id, 5)
      self.gantry_conditions['FOV_to_gantry_coordinates']['z'] = visM['z']
      self.gantry_conditions['FOV_to_gantry_coordinates']['transform'] = visM['data']['transform']

    self.save_gantry_conditions()

  def is_h_valid(self, h_list, h, tolerance):
    """
    Checks if the h value is within tolerance of the h values in the h_list
    """
    for h_i in h_list:
      if abs(h_i-h) > tolerance:
        return False
    return True

  # increments the use count
  def increment_use_count(self):
    self.gantry_conditions.gc_use_count += 1
    # update the use count antry_ionditionsn the latest conditions file
    # get the latest conditions file
    filename = Conditions.get_latest_gantry_conditions_filename()
    # save the conditions to the file
    self.save_gantry_conditions(filename)

  # define get, calculate functions for the data quality(long term) conditions and the board conditions
  def get_board_conditions(self):
    pass
  
  def calculate_board_conditions(self):
    pass

  # TODO: a function to load data quality(long term) conditions from a file
  # TODO: a function to save data quality(long term) conditions to a file
  # TODO: a getter for the data quality(long term) conditions
  # TODO: implement the data quality(long term) conditions calculation
  def get_data_quality_conditions(self):
    pass
  
  def calculate_data_quality_conditions(self):
    pass
  
  @staticmethod
  def get_gantry_conditions_directory():
    """
    Making the string represent the gantry conditions storage dire\ctory.
    """
    return 'conditions/gantry'

  def create_gantry_conditions_filename(self):
    """
    Returning the string corresponding to the filename for a new set of gantry conditions.
    """
    self.gantry_conditions_filename = '{dir}/{timestamp}.json'.format(dir=Conditions.get_gantry_conditions_directory(),
                                                    timestamp=datetime.datetime.now().strftime('%Y%m%d-%H%M'))
    
    return self.filename
  
  @staticmethod
  def get_latest_gantry_conditions_filename():
    """
    Returning the string corresponding to the filename for the latest set of gantry conditions.
    """
    directory = Conditions.get_gantry_conditions_directory()
    # Get a list of file names in the directory
    file_names = os.listdir(directory)
    # sort the file names by date if the format ofd the filename is '%Y%m%d-%H%M'.json
    if len(file_names) > 0:
      file_names.sort(key=lambda x: datetime.datetime.strptime(x, '%Y%m%d-%H%M.json'))
      # return the latest file name
      return file_names[-1]
    else:
      return None
