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
    self.sort_drop.items = [("Sort by date", "datetime"), ("Sort by name", "user")]
    current_bookings, past_bookings = anvil.server.call('get_bookings')
    self.repeating_panel_1.items = current_bookings
    self.repeating_panel_2.items = past_bookings


  def sort_drop_change(self, **event_args):
    """This method is called when an item is selected"""
    current_bookings, past_bookings = anvil.server.call('get_bookings', self.sort_drop.selected_value)
    self.repeating_panel_1.items = current_bookings
    self.repeating_panel_2.items = past_bookings

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


