import anvil.google.auth, anvil.google.drive, anvil.google.mail
from anvil.google.drive import app_files
import anvil.email
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime

@anvil.server.callable
def add_contact_info(name, email, topic, question):
  app_tables.contact.add_row(
    name=name, 
    email=email, 
    topic=topic,
    question=question, 
    time=datetime.now()
  )
  anvil.email.send(to="andi.otto@yahoo.com",
                   subject=f"Question from {name}: {topic}",
                   text=f"You've received a new web contact from {name}! \nTopic: {topic} \nEmail address: {email} \nQuestion: {question}")


