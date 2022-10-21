from ._anvil_designer import Agent_FeedbackTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from datetime import datetime

class Agent_Feedback(Agent_FeedbackTemplate):
  def __init__(self, **properties):
    
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.sort_drop.items = [("Sort by date", "datetime"), ("Sort by name", "user")]
    feedback = anvil.server.call('get_feedback')


    self.repeating_panel_3.items = app_tables.open_hours.search()


#APPOINTMENTS
  def sort_drop_change(self, **event_args):
    """This method is called when an item is selected"""
    current_bookings, past_bookings = anvil.server.call('get_bookings', self.sort_drop.selected_value)
    self.repeating_panel_1.items = feedback


  def appointments_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    if self.appointments_card.visible:
      self.appointments_card.visible = False
    else:
      self.appointments_card.visible = True


  def clear_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    save_clicked = alert("Are you sure you want to cancel all your past appointments?",
                   large=True,
                   buttons=[("yes", True), ("Cancel", False)])
    if save_clicked:
      anvil.server.call('delete_past_appointments')
      get_open_form().content_panel.clear()
      get_open_form().content_panel.add_component(Agent_Appointments())
