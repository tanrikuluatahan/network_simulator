import subprocess
import random
import time
from dotenv import load_dotenv
import os


# Load environment variables from .env file
load_dotenv()

# Get employees from the .env file (split the comma-separated values into a list)
employees = os.getenv("EMPLOYEES", "").split(",")

# Wait for the containers to be up (adjust time as needed)
time.sleep(30)  

# Function to send email from one employee to another
def send_email(sender, receiver):
    # Create the mail command
    email_command = f'echo "Test email from {sender}" | mail -s "Test Email" {receiver}@localdomain.test'
    
    # Execute the command inside the sender container
    try:
        subprocess.run(
            ["docker", "exec", sender, "sh", "-c", email_command], 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        print(f"{sender} sent an email to {receiver}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to send email from {sender} to {receiver}: {e.stderr.decode()}")

# Simulate sending emails for a specific duration or number of times
def simulate_email_exchange(repeat=5):
    for _ in range(repeat):
        sender = random.choice(employees)
        receiver = random.choice([emp for emp in employees if emp != sender])  # Make sure sender != receiver
        
        send_email(sender, receiver)
        
        # Wait for some time before sending the next email (adjust time as needed)
        time.sleep(random.randint(10, 20))

if __name__ == "__main__":
    simulate_email_exchange()
