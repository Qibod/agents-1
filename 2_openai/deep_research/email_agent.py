import os
from typing import Dict

import sendgrid
from sendgrid.helpers.mail import Email, Mail, Content, To
from agents import Agent, function_tool


@function_tool
def send_email(subject: str, html_body: str) -> Dict[str, str]:
    """Send an email with the given subject and HTML body"""
    api_key = os.environ.get("SENDGRID_API_KEY")
    if not api_key:
        raise ValueError("SENDGRID_API_KEY environment variable is not set")
    
    try:
        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        from_email = Email("vr.work.ams@gmail.com")  # put your verified sender here
        to_email = To("vr.work.ams@gmail.com")  # put your recipient here
        content = Content("text/html", html_body)
        mail = Mail(from_email, to_email, subject, content).get()
        
        response = sg.client.mail.send.post(request_body=mail)
        status_code = response.status_code
        print(f"Email response status: {status_code}")
        
        if status_code == 202:
            return {"status": "success", "message": "Email queued for delivery"}
        elif status_code == 403:
            error_msg = (
                "HTTP Error 403: Forbidden\n\n"
                "This usually means:\n"
                "1. Your API key doesn't have 'Mail Send' permissions\n"
                "2. The sender email (vr.work.ams@gmail.com) is not verified in SendGrid\n"
                "3. Your SendGrid account has restrictions\n\n"
                "**To fix:**\n"
                "- Go to SendGrid Dashboard → Settings → API Keys\n"
                "- Ensure your API key has 'Mail Send' permission\n"
                "- Verify your sender email in SendGrid Dashboard → Settings → Sender Authentication"
            )
            raise Exception(error_msg)
        else:
            raise Exception(f"Unexpected status code {status_code} from SendGrid")
            
    except Exception as e:
        error_msg = str(e)
        # Check if it's already a formatted error message
        if "403" in error_msg or "Forbidden" in error_msg:
            # Re-raise with the same message if it's already formatted
            if "This usually means" in error_msg:
                raise
            else:
                # Format the error message
                raise Exception(
                    f"SendGrid 403 Forbidden Error: {error_msg}\n\n"
                    "This usually means:\n"
                    "1. Your API key doesn't have 'Mail Send' permissions\n"
                    "2. The sender email is not verified in SendGrid\n"
                    "3. Your SendGrid account has restrictions"
                )
        else:
            # Re-raise other exceptions as-is
            raise Exception(f"SendGrid error: {error_msg}")


INSTRUCTIONS = """You are able to send a nicely formatted HTML email based on a detailed report.
You will be provided with a detailed report. You should use your tool to send one email, providing the 
report converted into clean, well presented HTML with an appropriate subject line."""

email_agent = Agent(
    name="Email agent",
    instructions=INSTRUCTIONS,
    tools=[send_email],
    model="gpt-4o-mini",
)
