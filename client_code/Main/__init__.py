from ._anvil_designer import MainTemplate
from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import stripe.checkout
import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
import random
from anvil.tables import app_tables
from ..Home import Home
from ..About import About
from ..Contact import Contact
from ..Appointment import Appointment
from ..FAQ import FAQ
from ..Agent_Portal import Agent_Portal
from ..Main_AgentPortal import Main_AgentPortal
from ..PrivacyPolicy import PrivacyPolicy


class Main(MainTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.content_panel.add_component(Home(), full_width_row=True)

    app_tables.quotes.client_readable()
    global quotes
    quotes = [r['quotes'] for r in app_tables.quotes.search()]

    self.dom_nodes['home'].addEventListener('click', self._home_link_click)
    self.dom_nodes['appointment'].addEventListener('click', self._appointment_link_click)
    self.dom_nodes['contact'].addEventListener('click', self._contact_link_click)
    self.dom_nodes['about'].addEventListener('click', self._about_link_click)
    
  def _home_link_click(self, event):
    # Prevent default form submission
    event.preventDefault()
    self.content_panel.clear()
    self.content_panel.add_component(Home(), full_width_row=True)

  def _appointment_link_click(self, event):
    # Prevent default form submission
    event.preventDefault()
    self.content_panel.clear()
    self.content_panel.add_component(Appointment(), full_width_row=True)
    
  def _contact_link_click(self, event):
    # Prevent default form submission
    event.preventDefault()
    self.content_panel.clear()
    self.content_panel.add_component(Contact(), full_width_row=True)

  def _about_link_click(self, event):
    # Prevent default form submission
    event.preventDefault()
    self.content_panel.clear()
    self.content_panel.add_component(About(), full_width_row=True)
  
  def contact_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.content_panel.clear()
    self.content_panel.add_component(Contact(), full_width_row=True)

  def about_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.content_panel.clear()
    self.content_panel.add_component(About(), full_width_row=True)

  def home_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.content_panel.clear()
    self.content_panel.add_component(Home(), full_width_row=True)

  def bottom_about_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.about_link_click()

  def bottom_contact_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.contact_link_click()

  def appointment_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.content_panel.clear()
    self.content_panel.add_component(Appointment(), full_width_row=True)

  def faq_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.content_panel.clear()
    self.content_panel.add_component(FAQ(), full_width_row=True)

  def agent_login_click(self, **event_args):
    """This method is called when the link is clicked"""
    anvil.users.login_with_form()
    open_form('Main_AgentPortal')
    return

  def privacy_policy_click(self, **event_args):
    """This method is called when the link is clicked"""
    alert(PrivacyPolicy(), large=True, title="")

  def timer_1_tick(self, **event_args):
    """This method is called Every [interval] seconds. Does not trigger if [interval] is 0."""
    quote = random.choice(quotes)
    self.call_js('change_text', quote)






