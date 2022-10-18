from ._anvil_designer import Agent_AppointmentsTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class Agent_Appointments(Agent_AppointmentsTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.

  def appointments_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    if self.appointments_card.visible:
      self.appointments_card.visible = False
    else:
      self.appointments_card.visible = True

  def settings_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    if self.settings_card.visible:
        self.settings_card.visible = False
    else:
        self.settings_card.visible = True


