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

    app_tables.client_resources.client_readable()
    self.repeating_panel_client_resources.items=app_tables.client_resources.search(tables.order_by("main title"))
    
    app_tables.agent_resources.client_readable()
    self.repeating_panel_agent_resources.items=app_tables.agent_resources.search(tables.order_by("main title"))

    
#    app_tables.bookings.add_row(name=name.capitalize().strip(), datetime=date, user=email.lower().strip())

  def client_resources_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    if self.client_resources_card.visible==False:
      self.client_resources_card.visible=True
    else:
      self.client_resources_card.visible=False

  def agent_resources_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    if self.agent_resources_card.visible==False:
      self.agent_resources_card.visible=True
    else:
      self.agent_resources_card.visible=False


