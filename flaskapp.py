from flask import Flask, request, render_template,redirect,url_for
from threading import Timer
import  webbrowser
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
        data=request.form['filename']
        if(data[-4:]==".csv"):
            data=data
        else:
            data+=".csv"
        print(data)
        arduino = serial.Serial(port='COM3',baudrate=9600,timeout=1)
        ##print(arduino.isOpen())
        if(arduino.isOpen() == False):
            arduino.open()
        ##date=datetime.now()

        global f
        f= open('input/'+data, 'a+',newline='')
        w = csv.writer(f, delimiter = ',')
        time.sleep(2)
        file = open('input/'+data)
        reader = csv.reader(file)
        lines= len(list(reader))
        if(lines==0):
            writer = csv.DictWriter(f, fieldnames=["Datetime", "Watts"])
            writer.writeheader()
        while(flag==True and f.closed==False and arduino.isOpen()==True):
        ##    date=datetime.now()
            value = (arduino.readline().decode('utf-8').rstrip())
            ##print(serial)
            value=datetime.now().strftime('%d-%m-%Y - %H:%M:%S.%f')[:-3]+","+str(value)
            if(f.closed==False):
                w.writerow(value.split(','))
            print(value)
    else:
        #messagebox.showinfo("Error","Port is already running")
        #easygui.msgbox("This is a message!", title="simple gui")
        #js2py.eval_js("alert('Error,Port is already running')")
        value="staerrport"
    return redirect(url_for("index"))

@app.route('/stopProcess')
def stopProcess():
    global flag
    global value
    if(flag==True):
        flag=False
        global f
        global arduino
        f.close()
        arduino.close()
        #messagebox.showinfo("Success","Serial Port is successfully closed")
        #easygui.msgbox("This is a message!", title="simple gui")
        #js2py.eval_js("alert('Success,Serial Port is successfully closed')")
        value="stpsucclose"

    else:
        #messagebox.showinfo("Error","Error in Closing Serial Port")
        #easygui.msgbox("This is a message!", title="simple gui")
        #js2py.eval_js("alert('Error in Closing Serial Port')")
        value="stperrport"
    return redirect(url_for("index"))


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
            plt.savefig("trainingdata.png")
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
        plt.savefig("predict.png")
        #plt.show(block=False)
        plt.close()
        #messagebox.showinfo("Success","Successfully Generated")
        #print(threading.currentThread().getName())
        #easygui.msgbox("This is a message!", title="simple gui")
        #js2py.eval_js("alert('Success, Successfully Generated')")
        value="gensucc"

    else:
        #messagebox.showinfo("Error","Please stop the Serial Port")
        #easygui.msgbox("This is a message!", title="simple gui")
        #js2py.eval_js("alert('Error, Please stop the Serial Port')")
        value="generrport"
    return redirect(url_for("index"))

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
