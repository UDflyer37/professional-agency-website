from ._anvil_designer import RowTemplate1Template
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ...Agent_Contact import Agent_Contact
from .. import Agent_Appointments

class RowTemplate1(RowTemplate1Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

  
  def email_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    alert(Agent_Contact(item=self.item), large=True)
    
  def delete_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    save_clicked = alert("Are you sure you want to cancel this appointment? The customer will be notified.",
                   large=False,
                   buttons=[("Yes", True), ("Cancel", False)])
    if save_clicked:
      anvil.server.call('delete_booking', self.item)
      get_open_form().content_panel.clear()
      get_open_form().content_panel.add_component(Agent_Appointments())
      