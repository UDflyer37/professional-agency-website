from ._anvil_designer import RowTemplate1Template
from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import stripe.checkout
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ...Agent_Contact import Agent_Contact
from .. import Agent_Feedback

class RowTemplate1(RowTemplate1Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

  def refresh(self, **event_args):
    self.parent.items = anvil.server.call('get_feedback')
    
  def email_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    alert(Agent_Contact(item=self.item), large=True)
    
  def delete_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    save_clicked = alert("Are you sure you want to delete this? ",
                   large=False,
                   buttons=[("Delete", True), ("Cancel", False)])
    if save_clicked:
      anvil.server.call('delete_feedback', self.item)
      self.refresh()
