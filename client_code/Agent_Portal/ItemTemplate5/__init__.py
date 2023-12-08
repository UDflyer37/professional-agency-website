from ._anvil_designer import ItemTemplate5Template
from anvil import *
import stripe.checkout
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .. import Agent_Portal

class ItemTemplate5(ItemTemplate5Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

  def refresh(self, **event_args):
    app_tables.quotes.client_readable()
    self.parent.items=app_tables.quotes.search(tables.order_by("quotes"))


  def edit_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    if self.text_card.visible==True:
      self.text_card.visible=False
    else:
      self.text_card.visible=True
      self.refresh_data_bindings()

  def confirm_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    app_tables.quotes.client_writable()
    self.item['quotes'] = self.main_title_text_box.text
    self.refresh()
    get_open_form().refresh()

  def reset_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.text_card.visible=False

  def delete_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    save_clicked = alert("Are you sure you want to delete this resource?",
                        large=False,
                        buttons=[("Delete", True), ("Cancel", False)])
    if save_clicked:
      self.item.delete()
      self.refresh()
      get_open_form().refresh()
