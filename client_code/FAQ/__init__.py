from ._anvil_designer import FAQTemplate
from anvil import *
import stripe.checkout
import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class FAQ(FAQTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    app_tables.faqs.client_readable()
    self.repeating_panel_1.items=app_tables.faqs.search(tables.order_by("question"))