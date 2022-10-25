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
    self.repeating_panel_client_resources.items=app_tables.client_resources.search(tables.order_by("main_title"))
    
    app_tables.agent_resources.client_readable()
    self.repeating_panel_agent_resources.items=app_tables.agent_resources.search(tables.order_by("main_title"))
 

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

  def add_agent_resources_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.add_agent_resource_card.visible=True

  def agent_resource_confirm_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    app_tables.agent_resources.client_writable()
    app_tables.agent_resources.add_row(URL=self.agent_URL_text_area.text, 
                                       main_title=self.agent_main_title_text_box.text,
                                       link_title=self.agent_link_title_text_box.text)

    get_open_form().content_panel.clear()
    get_open_form().content_panel.add_component(Agent_Resources())

  def agent_resource_cancel_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.agent_main_title_text_box.text = ""
    self.agent_link_title_text_box.text = ""
    self.agent_URL_text_area.text = ""
    self.add_agent_resource_card.visible=False

  def add_client_resources_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.add_client_resource_card.visible=True

  def client_resource_confirm_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    app_tables.client_resources.client_writable()
    app_tables.client_resources.add_row(URL=self.client_URL_text_area.text, 
                                        main_title=self.client_main_title_text_box.text,
                                        link_title=self.client_link_title_text_box.text)
  
    get_open_form().content_panel.clear()
    get_open_form().content_panel.add_component(Agent_Resources())

  def client_resource_cancel_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.client_main_title_text_box.text = ""
    self.client_link_title_text_box.text = ""
    self.client_URL_text_area.text = ""
    self.add_client_resource_card.visible=False














