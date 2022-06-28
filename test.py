import smtplib
import imghdr
from email.message import EmailMessage
Sender_Email = "emailpythontest12345@gmail.com"
Reciever_Email = "codeitbro@gmail.com"
newMessage = EmailMessage()                         
newMessage['Subject'] = "Predicted PDF" 
newMessage['From'] = "smart_switch@yahoo.com"                  
newMessage['To'] = ["balajisri648@gmail.com","t.harish2478@gmail.com"]                  
newMessage.set_content('Bill For Power Consumption') 
with open('output\Bill.pdf', 'rb') as f:
    file_data = f.read()
    file_name = f.name
newMessage.add_attachment(file_data, maintype='application', subtype='octet-stream', filename=file_name)
with smtplib.SMTP_SSL('smtp.mail.yahoo.com', 465) as smtp:
    smtp.ehlo()
    smtp.login("smart_switch@yahoo.com", "asvkuuofjlnvgore")              
    smtp.send_message(newMessage)
