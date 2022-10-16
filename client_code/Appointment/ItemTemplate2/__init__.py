from ._anvil_designer import ItemTemplate2Template
from anvil import *
import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class ItemTemplate2(ItemTemplate2Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

  def radio_button_1_clicked(self, **event_args):
    """This method is called when this radio button is selected"""
    self.parent.raise_event("x-select-time", time=self.item)
