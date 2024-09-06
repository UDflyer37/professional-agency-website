from ._anvil_designer import Agent_ResourcesTemplate
from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import stripe.checkout
import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class Agent_Resources(Agent_ResourcesTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.client_resources()
    self.agent_resources()
    self.phone_numbers()
    self.faqs()

  def client_resources(self, **event_args):
    app_tables.client_resources.client_readable()
    self.repeating_panel_client_resources.items=app_tables.client_resources.search(tables.order_by("main_title"))

  def agent_resources(self, **event_args):
    app_tables.agent_resources.client_readable()
    self.repeating_panel_agent_resources.items=app_tables.agent_resources.search(tables.order_by("main_title"))

  def phone_numbers(self, **event_args):
    app_tables.phone_numbers.client_readable()
    self.repeating_panel_phone_numbers.items=app_tables.phone_numbers.search(tables.order_by("user"))

  def faqs(self, **event_args):
      app_tables.faqs.client_readable()
      self.repeating_panel_FAQ.items=app_tables.faqs.search(tables.order_by("question"))
 

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
    self.agent_resources()
    self.repeating_panel_agent_resources.scroll_into_view(smooth=True)
    self.add_agent_resource_card.visible=False
    self.agent_URL_text_area.text = ""
    self.agent_main_title_text_box.text = "" 
    self.agent_link_title_text_box.text = ""

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
    self.client_resources()
    self.repeating_panel_client_resources.scroll_into_view(smooth=True)
    self.add_client_resource_card.visible=False
    self.client_URL_text_area.text = ""
    self.client_main_title_text_box.text = "" 
    self.client_link_title_text_box.text = ""

  def client_resource_cancel_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.client_main_title_text_box.text = ""
    self.client_link_title_text_box.text = ""
    self.client_URL_text_area.text = ""
    self.add_client_resource_card.visible=False

  def phone_numbers_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    if self.phone_numbers_card.visible==False:
      self.phone_numbers_card.visible=True
    else:
      self.phone_numbers_card.visible=False

  def add_phone_number_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.add_phone_number_card.visible=True

  def add_phone_number_cancel_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.contact_name_text_box.text = ""
    self.phone_number_text_box.text = ""
    self.add_phone_number_card.visible=False

  def add_phone_number_confirm_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    n = self.phone_number_text_box.text
    app_tables.phone_numbers.client_writable()
    app_tables.phone_numbers.add_row(user=self.contact_name_text_box.text, 
                                       phone= format(int(n[:-1]), ",").replace(",", "-") + n[-1])                        
    self.phone_numbers()
    self.repeating_panel_phone_numbers.scroll_into_view(smooth=True)
    self.add_phone_number_card.visible=False
    self.contact_name_text_box.text = ""
    self.phone_number_text_box.text = "" 

  def FAQ_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    if self.FAQ_card.visible==False:
      self.FAQ_card.visible=True
    else:
      self.FAQ_card.visible=False

  def add_faq_button_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.add_faq_card.visible=True

  def add_faq_confirm_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    app_tables.faqs.client_writable()
    app_tables.faqs.add_row(question = self.question_text_box.text,
                            answer = self.answer_text_box.text)
    self.faqs()
    self.repeating_panel_FAQ.scroll_into_view(smooth=True)
    self.add_faq_card.visible=False
    self.question_text_box.text = ""
    self.answer_text_box.text = "" 

  def add_faq_cancel_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.add_faq_card.visible=False
    self.question_text_box.text = ""
    self.answer_text_box.text = "" 




    


















