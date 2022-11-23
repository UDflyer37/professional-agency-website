from ._anvil_designer import ContactTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .contact_us import contact_us
from .email_us import email_us


class Contact(ContactTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

  def contact_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    alert(contact_us(item=self.item), large=True, buttons=[("Close", False)])
    if self.contact_card.visible:
        self.contact_card.visible = False
    else:
        self.contact_card.visible = True

  def email_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    alert(email_us(item=self.item), large=True, buttons=[("Submit", True), ("Close", False)])
    if self.email_card.visible:
        self.email_card.visible = False
        self.email_template_card.visible = False
    else:
        self.email_card.visible = True




