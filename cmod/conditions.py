import json
import datetime
import os

# NOTE: "uses visual system commands"
class Conditions(object):
  def __init__(self, cmd):
    self.cmd = cmd
    self.logger = cmd.devlog("Conditions")
    # gantry conditions should be stored as a dictionary
    self.gantry_conditions = {}
    self.gantry_conditions_use_count = 0
    self.gantry_conditions_filename = ""
    self.h_list = []

  # loads gantry conditions from a file and returns True if successful, False otherwise
  def load_gantry_conditions(self, file):
    orig_gantry_conditions = self.gantry_conditions.copy()

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

      self.gantry_conditions_filename = file
      self.increment_use_count()

      self.h_list = [self.gantry_conditions["lumi_vs_FOV_center"]["data"]["separation"]]

      return True
    except KeyError as e:
      self.gantry_conditions = orig_gantry_conditions
      # warning: the gantry conditions file does not contain the required fields so the gantry conditions will not be loaded
      self.logger.warn(f"""
        The gantry conditions file does not contain the required fields. Program will continue without loading the gantry conditions in {file}. {e}
      """)
      return False

  # saves gantry conditions to a file
  def save_gantry_conditions(self, filename=""):
    if filename != "":
      self.gantry_conditions_filename = filename
    if self.gantry_conditions_filename == "":
      self.create_gantry_conditions_filename()
      self.increment_use_count()

    with open(self.gantry_conditions_filename, 'w') as f:
      f.write(json.dumps(self.gantry_conditions, indent=2))
  
  # returns the gantry conditions
  def get_gantry_conditions(self):
    return self.gantry_conditions
  
  def update_gantry_and_sipm_conditions(self, cmd_name, detid, z):
    if cmd_name == 'visualcenterdet':
      if self.cmd.board.lumi_coord_hasz(detid, z):
        h = self.cmd.board.get_lumi_coord(detid, z)-self.cmd.board.get_vis_coord(detid, z)
        self.cmd.board.add_lumi_vis_separation(detid, z, h)
        # check if we have multiple H values out of tolerance with each other,
        if self.is_h_valid(self.h_list, h, 0.5):
          self.h_list.append(h)
          self.gantry_conditions["lumi_vs_FOV_center"]["separation"] = ((self.gantry_conditions["lumi_vs_FOV_center"]['data']["separation"]*len(self.h_list)) + h) /  (len(self.h_list)+1)
        # TODO: add the else: an error should be raised such that the operator knows that something is wrong (maybe the gantry head dislodged or was tugged
    elif cmd_name == 'halign':
      if self.cmd.board.vis_coord_hasz(detid, z):
        h = self.cmd.board.get_lumi_coord(detid, z)-self.cmd.board.get_vis_coord(detid, z)
        self.cmd.board.add_lumi_vis_separation(detid, z, h)

        # check if we have multiple H values out of tolerance with each other,
        if self.is_h_valid(self.h_list, h, 0.5):
          self.h_list.append(h)
          self.gantry_conditions["lumi_vs_FOV_center"]["separation"] = ((self.gantry_conditions["lumi_vs_FOV_center"]["separation"]*len(self.h_list)) + h) /  (len(self.h_list)+1)
        # TODO: add the else: an error should be raised such that the operator knows that something is wrong (maybe the gantry head dislodged or was tugged
    elif cmd_name == 'visualhscan':
      visM = self.cmd.board.get_visM(id, 5)
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
    self.gantry_conditions.use_count += 1
    # update the use count gantry_conditions the latest conditions file
    # get the latest conditions file
    try:
      filename = Conditions.get_latest_gantry_conditions_filename()
      # save the conditions to the file
      self.save_gantry_conditions(filename)
    except FileNotFoundError as e:
      self.logger.error(e)
      self.logger.error("""
        Failed to save the updated gantry conditions use_count. The gantry conditions file does not exist. Please check the
        file and the required format and try again.""")

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
    
    return self.gantry_conditions_filename
  
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
