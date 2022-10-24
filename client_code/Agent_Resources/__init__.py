from ._anvil_designer import Agent_ResourcesTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class Agent_Resources(Agent_ResourcesTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    self.repeating_panel_1=app_tables.web_resources.get(title=title,URL=URL)

#    app_tables.bookings.add_row(name=name.capitalize().strip(), datetime=date, user=email.lower().strip())
