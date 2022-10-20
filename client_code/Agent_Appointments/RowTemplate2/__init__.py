from ._anvil_designer import RowTemplate2Template
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ...Contact import Contact
from .. import Agent_Appointments

class RowTemplate2(RowTemplate2Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

  def email_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    alert(Contact(item=self.item), large=True)
    
  def delete_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    save_clicked = alert("Are you sure you want to cancel this booking? The customer will be notified.",
                   large=True,
                   buttons=[("yes", True), ("Cancel", False)])
    if save_clicked:
      anvil.server.call('delete_booking', self.item)
      get_open_form().content_panel.clear()
      get_open_form().content_panel.add_component(AllBookings())