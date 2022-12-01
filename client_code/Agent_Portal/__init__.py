from ._anvil_designer import Agent_PortalTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class Agent_Portal(Agent_PortalTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    self.quotes()

  def quotes(self, **event_args):
      app_tables.quotes.client_readable()
      self.repeating_panel_1.items=app_tables.quotes.search(tables.order_by("quotes"))

  def add_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.add_card.visible = True

  def confirm_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    app_tables.quotes.client_writable()
    app_tables.quotes.add_row(quotes=self.title_text_box.text)
    self.quotes()
    self.repeating_panel_1.scroll_into_view(smooth=True)
    self.add_card.visible=False
    self.title_text_box.text = ""
    get_open_form().refresh()

  def cancel_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.title_text_box.text = ""
    self.add_card.visible=False



    