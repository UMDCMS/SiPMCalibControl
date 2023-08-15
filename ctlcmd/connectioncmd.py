"""
  connectioncmd.py

  Commands that are used to manage the connection to the server (i.e) the hardwares hosted on the server.
"""

import ctlcmd.cmdbase as cmdbase
import cmod.fmt as fmt
import argparse


class establish_exclusive_connection_server(cmdbase.controlcmd):
    """
    @brief Attempt to establish the exclusive connection to the server.
    """

    def __init__(self, cmd):
        cmdbase.controlcmd.__init__(self, cmd)

    def run(self, args):
        """
        For the sake of clarity, device settings is split into each of their
        functions. Notice that all function should have exception guards so the
        subsequent settings can still be set if settings for one particular device
        is bad or not available.
        """
        try:
            response = self.client.send_request("Connect")
            if response == "Connected":
                self.printout(
                    "Successfully established exclusive connection to server."
                )
            else:
                self.printerr(
                    "Failed to establish exclusive connection to server. Can still make requests to read data."
                )
        except RuntimeError as err:
            self.printerr(str(err))
            self.printerr(
                "Failed to establish exclusive connection to server. Can still make requests to read data."
            )


class release_exclusive_connection_server(cmdbase.controlcmd):
    """
    @brief Attempt to release the exclusive connection to the server.
    """

    def __init__(self, cmd):
        cmdbase.controlcmd.__init__(self, cmd)

    def run(self, args):
        """ """
        try:
            response = self.client.send_request("Release")
            if response != "Released":
                self.printmsg("Released exclusive connection to server.")
            else:
                self.printerr(
                    "Failed to release exclusive connection to server. Can still make requests to read data."
                )
        except RuntimeError as err:
            self.printerr(str(err))
            self.printerr(
                "Failed to establish exclusive connection to server. Can still make requests to read data."
            )
