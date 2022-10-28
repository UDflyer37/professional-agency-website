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
    self.sort_drop.items = [("Sort by date", "datetime"), ("Sort by name", "name"),("Sort by topic", "topic")]
    self.repeating_panel_1.items = anvil.server.call('get_feedback')


  def refresh(self, **event_args):
    self.repeating_panel_1.items = anvil.server.call('get_feedback')

  
  def sort_drop_change(self, **event_args):
    """This method is called when an item is selected"""
    feedback = anvil.server.call('get_feedback', self.sort_drop.selected_value)
    self.repeating_panel_1.items = feedback


  def clear_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    save_clicked = alert("Are you sure you want to delete all your past feedback?",
                   large=False,
                   buttons=[("Delete", True), ("Cancel", False)])
    if save_clicked:
      anvil.server.call('delete_past_feedback')
      self.refresh()
