from ._anvil_designer import ItemTemplate_phone_numbersTemplate
from anvil import *
import stripe.checkout
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .. import Agent_Resources

class ItemTemplate_phone_numbers(ItemTemplate_phone_numbersTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

  def refresh(self, **event_args):
    app_tables.phone_numbers.client_readable()
    self.parent.items=app_tables.phone_numbers.search(tables.order_by("user"))
 

  def edit_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    if self.text_card.visible==True:
      self.text_card.visible=False
    else:
      self.text_card.visible=True
      self.user_text_box.text = self.item['user']
      self.phone_text_box.text = self.item['phone']

  def confirm_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    app_tables.phone_numbers.client_writable()
    self.item['user'] = self.user_text_box.text
    self.item['phone'] = self.phone_text_box.text
    self.refresh()

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
