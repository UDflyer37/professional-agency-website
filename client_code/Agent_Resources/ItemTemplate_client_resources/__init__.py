from ._anvil_designer import ItemTemplate_client_resourcesTemplate
from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import stripe.checkout
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .. import Agent_Resources

class ItemTemplate_client_resources(ItemTemplate_client_resourcesTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)


  def refresh(self, **event_args):
    app_tables.client_resources.client_readable()
    self.parent.items=app_tables.client_resources.search(tables.order_by("main_title"))
    

  def edit_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    if self.text_card.visible==True:
      self.text_card.visible=False
    else:
      self.text_card.visible=True
      self.main_title_text_box.text = self.item['main_title']
      self.link_title_text_box.text = self.item['link_title']
      self.URL_text_box.text = self.item['URL']

  def confirm_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    app_tables.agent_resources.client_writable()
    self.item['main_title'] = self.main_title_text_box.text
    self.item['link_title'] = self.link_title_text_box.text
    self.item['URL'] = self.URL_text_box.text
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

    





    

