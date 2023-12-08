from ._anvil_designer import ItemTemplate_FAQTemplate
from anvil import *
import stripe.checkout
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .. import Agent_Resources

class ItemTemplate_FAQ(ItemTemplate_FAQTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
              
  def refresh(self, **event_args):
    app_tables.faqs.client_readable()
    self.parent.items=app_tables.faqs.search(tables.order_by("question"))


  def edit_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    if self.text_card.visible==True:
      self.text_card.visible=False
    else: 
      self.text_card.visible=True
      self.question_text_box.text = self.item['question']
      self.answer_text_box.text = self.item['answer']
    
  def confirm_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    app_tables.faqs.client_writable()
    self.item['question'] = self.question_text_box.text
    self.item['answer'] = self.answer_text_box.text
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
