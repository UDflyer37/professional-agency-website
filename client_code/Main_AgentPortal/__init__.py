from ._anvil_designer import Main_AgentPortalTemplate
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
from ..Agent_Feedback import Agent_Feedback
from ..Agent_Resources import Agent_Resources
from ..Agent_Appointments import Agent_Appointments
from ..Agent_Portal import Agent_Portal



class Main_AgentPortal(Main_AgentPortalTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.content_panel.add_component(Agent_Portal(), full_width_row=True)

    self.refresh()
    self.dom_nodes['home'].addEventListener('click', self._home_link_click)
    self.dom_nodes['appointments'].addEventListener('click', self._appointments_link_click)
    self.dom_nodes['resources'].addEventListener('click', self._resources_link_click)
    self.dom_nodes['feedback'].addEventListener('click', self._feedback_link_click)
    
  def _home_link_click(self, event):
    # Prevent default form submission
    event.preventDefault()
    self.content_panel.clear()
    self.content_panel.add_component(Agent_Portal(), full_width_row=True)

  def _appointments_link_click(self, event):
    # Prevent default form submission
    event.preventDefault()
    self.content_panel.clear()
    self.content_panel.add_component(Agent_Appointments(), full_width_row=True)
    
  def _resources_link_click(self, event):
    # Prevent default form submission
    event.preventDefault()
    self.content_panel.clear()
    self.content_panel.add_component(Agent_Resources(), full_width_row=True)

  def _feedback_link_click(self, event):
    # Prevent default form submission
    event.preventDefault()
    self.content_panel.clear()
    self.content_panel.add_component(Agent_Feedback(), full_width_row=True)

  def refresh(self, **event_args):
    app_tables.quotes.client_readable()
    global quotes
    quotes = [r['quotes'] for r in app_tables.quotes.search()]

  def resources_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.content_panel.clear()
    self.content_panel.add_component(Agent_Resources(), full_width_row=True)

  def feedback_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.content_panel.clear()
    self.content_panel.add_component(Agent_Feedback(), full_width_row=True)

  def home_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.content_panel.clear()
    self.content_panel.add_component(Agent_Portal(), full_width_row=True)

  def bottom_resources_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.resources_link_click()

  def bottom_feedback_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.feedback_link_click()

  def appointments_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.content_panel.clear()
    self.content_panel.add_component(Agent_Appointments(), full_width_row=True)

  def customer_portal_click(self, **event_args):
    """This method is called when the link is clicked"""
    save_clicked = alert("Are you sure you want to return to the customer portal? You will be logged out.",
                   large=False,
                   buttons=[("Yes", True), ("Cancel", False)])
    if save_clicked:
      anvil.users.logout()
      open_form('Main')
      return

  def bottom_appointments_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.appointments_link_click()

  def timer_1_tick(self, **event_args):
    """This method is called Every [interval] seconds. Does not trigger if [interval] is 0."""
    quote = random.choice(quotes)
    self.call_js('change_text', quote)
