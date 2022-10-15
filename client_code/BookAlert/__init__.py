from ._anvil_designer import BookAlertTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class BookAlert(BookAlertTemplate):
  def __init__(self,time, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    
    self.datetime_label.text = time.strftime("%A %d %b %Y at %I:%M %p")