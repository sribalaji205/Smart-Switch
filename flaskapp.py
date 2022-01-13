#html 2 pdf convert
from xhtml2pdf import pisa 

#For Sending Email
import yagmail

#Flask Webapp Packages
from flask import Flask, request, render_template,redirect,url_for
from threading import Timer
import  webbrowser

#Arduino Port Packages
import serial
import csv
import time

# Ploting packages
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt

from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()

# Date wrangling
from datetime import datetime, timedelta

# Data wrangling
import pandas as pd 

# The deep learning class
from deep_model import DeepModelTS

# Reading the configuration file
import yaml

# Directory managment 
import os

#Global Variables
flag=False
f=None
value=""
arduino=None
startpro=""
stoppro=""
generater=""
process=None
pflag=True
data="RealTimeSampleData.csv"

# Utility function
def convert_html_to_pdf(source_html, output_filename):
    # open output file for writing (truncated binary)
    result_file = open(output_filename, "w+b")

    # convert HTML to PDF
    pisa_status = pisa.CreatePDF(
            source_html,                # the HTML to convert
            dest=result_file)           # file handle to recieve result

    # close output file
    result_file.close()                 # close output file

    # return False on success and True on errors
    return pisa_status.err
app = Flask(__name__)

@app.route('/')
def index():
    global value
    return render_template("index.html",value=value)

@app.route('/startProcess',methods=['POST']) 
def startProcess():
    global flag
    global value
    global data
    if(flag==False):
        flag=True
        global arduino
        
        #Get the POST value and check for '.csv' in that value
        
        data=request.form['filename']
        if(data[-4:]==".csv"):
            data=data
        else:
            data+=".csv"
        print(data)
        
        #Create a Serial object with port,baudrate same as in arduino ino file
        
        arduino = serial.Serial(port='COM3',baudrate=9600,timeout=1)
        if(arduino.isOpen() == False):
            arduino.open()
        global f
        
        #Open csv file in append mode
        
        f= open('input/'+data, 'a+',newline='')
        w = csv.writer(f, delimiter = ',')
        time.sleep(2)
        
        #Open file to get No. of Rows
        
        file = open('input/'+data)
        reader = csv.reader(file)
        lines= len(list(reader))
        
        #Add header row to that file if lines '0'
        
        if(lines==0):
            writer = csv.DictWriter(f, fieldnames=["Datetime", "Watts"])
            writer.writeheader()
            
        while(flag==True and f.closed==False and arduino.isOpen()==True):
            
            #Get the serial output using readline() and convert it to string
            value = (arduino.readline().decode('utf-8').rstrip())
            
            #Set the values in (datetime,value) format
            value=datetime.now().strftime('%d-%m-%Y - %H:%M:%S.%f')[:-3]+","+str(value)
            
            #Write value into csv file
            if(f.closed==False):
                w.writerow(value.split(','))
            print(value)
    else:
        value="staerrport"
    return render_template("form.html",value=value)

@app.route('/stopProcess')
def stopProcess():
    global flag
    global value
    
    #Close the port connection and csv file if port is Open
    
    if(flag==True):
        flag=False
        global f
        global arduino
        f.close()
        arduino.close()
        value="stpsucclose"

    else:
        value="stperrport"
    return render_template("form.html",value=value)


@app.route('/generate')
def generate():
    global flag
    global value
    global data
    if(flag==False):
        
        # Reading the hyper parameters for the pipeline
        with open(f'{os.getcwd()}\\conf.yml') as file:
            conf = yaml.load(file, Loader=yaml.FullLoader)

        # Reading the data
        print(data)
        d = pd.read_csv('input/'+data)
        d['Datetime'] = [datetime.strptime(x, '%d-%m-%Y - %H:%M:%S.%f') for x in d['Datetime']]

        # Making sure there are no duplicated data
        # If there are some duplicates we average the data during those duplicated days
        ##d = d.groupby('Datetime', as_index=False)['Watts'].mean()

        # Sorting the values
        d.sort_values('Datetime', inplace=True)

        # Initiating the class 
        deep_learner = DeepModelTS(
            data=d, 
            Y_var='Watts',
            lag=conf.get('lag'),
            LSTM_layer_depth=conf.get('LSTM_layer_depth'),
            epochs=10,
            train_test_split=conf.get('train_test_split') # The share of data that will be used for validation
        )

        # Fitting the model 
        deep_learner.LSTModel()

        # Making the prediction on the validation set
        # Only applicable if train_test_split in the conf.yml > 0
        yhat = deep_learner.predict()

        if len(yhat) > 0:

            # Constructing the forecast dataframe
            fc = d.tail(len(yhat)).copy()
            fc.reset_index(inplace=True)
            fc['forecast'] = yhat

            # Ploting the forecasts
            plt.figure(figsize=(12, 8))
            for dtype in ['Watts', 'forecast']:
                plt.plot(
                    'Datetime',
                    dtype,
                    data=fc,
                    label=dtype,
                    alpha=0.8
                )
            plt.legend()
            plt.grid()
            ##plt.show()   
            plt.savefig("output/trainingdata.png")
            #plt.show(block=False)
            plt.close()
            #print("reached")
        # Forecasting n steps ahead
        
        # Creating the model using full data and forecasting n steps ahead
        deep_learner = DeepModelTS(
            data=d, 
            Y_var='Watts',
            lag=24,
            LSTM_layer_depth=64,
            epochs=10,
            train_test_split=0 
        )

        # Fitting the model 
        deep_learner.LSTModel()

        # Forecasting n steps ahead
        n_ahead = 168
        yhat = deep_learner.predict_n_ahead(n_ahead)
        yhat = [y[0][0] for y in yhat]

        # Amount Calculation
        units=0.0
        for i in yhat:
            units=units+i;
        if(units < 50):
            amt = units * 2.60
            extra = 25
        elif(units <= 100):
            amt = 130 + ((units - 50) * 3.25)
            extra = 35
        elif(units <= 200):
            amt = 130 + 162.50 + ((units - 100) * 5.26)
            extra = 45
        else:
            amt = 130 + 162.50 + 526 + ((units - 200) * 8.45)
            extra = 75
        bill = amt + extra
        
        date=datetime.now().strftime('%d-%m-%Y')
        name="Sharan"
        custno=1234
        city="Madurai"
        pincode="625020"
        source_html = """<html>
        <head>
        <style>
        @page{
        size:A4 landscape;
        @frame content_frame {          /* Content Frame */
            left: 25pt; width: 800pt; top: 25pt; height: 700pt;
          }
          background-image: url("https://img.freepik.com/free-photo/old-paper-texture-background_118047-1365.jpg?size=626&ext=jpg");
        }
        body{
        font-family:Times New Roman;
        }
        .fonts{
        font-size:18px;
        text-align:center;
        }
        .head{
        font-size:22px;
        }
        .pad{
        padding:6px;
        border-radius:10px;
        }
        th{
        padding:10px;
        }
        .alignleft{
        text-align:left;
        }
        .alignright{
        text-align:right;
        }
        .space{
        width:58%;
        }
        </style>
        </head>
        <body>
        <div class="head">
        <p style="text-align:center; font-size:25px;">Tamil Nadu Electricity Board</p>
        <table width=100%>
        <tr>
        <td>Name</td>
        <td class="space alignleft">"""+str(name)+"""</td>
        <td>City</td>
        <td>"""+str(city)+"""</td>
        </tr>
        <tr>
        <td>Customer No.</td>
        <td class="space alignleft">"""+str(custno)+"""</td>
        <td>Pincode</td>
        <td>"""+str(pincode)+"""</td>
        </tr>
        <tr>
        <td>Date</td>
        <td class="space alignleft">"""+str(date)+"""</td>
        <td>Units</td>
        <td>"""+str(round(units,3))+"""</td>
        </tr>
        </table>
        </center>
        </div>

        <br>
        <br>
        <br>

        <div>
        <table align=center width=68% border=1>
        <tr class="fonts">
        <th>No.</th>
        <th>Details</th>
        <th>Amount</th>
        </tr>
        <tr style="height:300px;" class="fonts">
        <td class="pad">16412</td>
        <td class="pad">CC Charges</td>
        <td class="pad">"""+str(round(bill,2))+"""</td>
        </tr>
        </table>
        </div>
        </body>
        </html>
        """
        output_filename = "output/Bill.pdf"

        convert_html_to_pdf(source_html,output_filename)
        #call the html to pdf conversion function

        

        # Constructing the forecast dataframe
        fc = d.tail(400).copy() 
        fc['type'] = 'original'

        last_date = max(fc['Datetime'])
        hat_frame = pd.DataFrame({
            'Datetime': [last_date + timedelta(hours=x + 1) for x in range(n_ahead)], 
            'Watts': yhat,
            'type': 'forecast'
        })

        fc = fc.append(hat_frame)
        fc.reset_index(inplace=True, drop=True)

        # Ploting the forecasts 
        plt.figure(figsize=(12, 8))
        for col_type in ['original', 'forecast']:
            plt.plot(
                'Datetime', 
                'Watts', 
                data=fc[fc['type']==col_type],
                label=col_type
                )

        plt.legend()
        plt.grid()
        #print("reached")
        plt.savefig("output/prediction.png")
        #plt.show(block=False)
        plt.close()
        value="gensucc"
        # initiating connection with SMTP server
        yag = yagmail.SMTP("pysmtp.project@gmail.com", 
                   "qwerty12345!@#")

        # Adding multiple attachments and mailing them
        yag.send(["sharanvel2000@gmail.com","t.harish2478@gmail.com","sribalaji055cse@gmail.com"],"Electricity Consumed and Bill",
                 contents="<h2>Electricity Bill and Units Consumed</h2><p><b>Units: "+str(units)+"</b></p><p><b>Bill   : "+str(round(bill,2))+"</b></p>",
                 attachments=["output/prediction.png","output/Bill.pdf"])
        print("success")

    else:
        value="generrport"
    return render_template("form.html",value=value)

@app.route("/formcontrol")
def formcontrol():
    return render_template("form.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/circuit")
def circuit():
    return render_template("circuit.html")

def open_browser():
      webbrowser.open_new('http://127.0.0.1:5000/')


if __name__ == "__main__":
      Timer(1,open_browser).start()
      app.run()
