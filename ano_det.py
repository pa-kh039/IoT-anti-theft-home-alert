import sys
sys.path.insert(0,"/home/parth/Desktop/iot/anomaly_detection/config_folder")  #this folder has the .py file which contains configurations like api_key, phone number, etc.
import conf, json, time, math, statistics
from boltiot import Sms, Bolt

def compute_bounds(history_data,frame_size,factor):
    if len(history_data)<frame_size :
        return None

    if len(history_data)>frame_size :
        del history_data[0:len(history_data)-frame_size]     #delete the history beyond the last 'frame_size' no. of data points
    Mn=statistics.mean(history_data)
    sumofsquares=0
    for data in history_data :
        sumofsquares += math.pow((data-Mn),2)
    variance=sumofsquares / frame_size
    standard_deviation=math.sqrt(variance)
    Zn = factor * standard_deviation
    High_bound = history_data[frame_size-1]+Zn   #last observed data point +- factor*StandardDeviation
    Low_bound = history_data[frame_size-1]-Zn
    return [High_bound,Low_bound]

mybolt = Bolt(conf.API_KEY, conf.DEVICE_ID)
sms = Sms(conf.SSID, conf.AUTH_TOKEN, conf.TO_NUMBER, conf.FROM_NUMBER)
history_data=[]

while True:
    response = mybolt.analogRead('A0') 	#reading the birghtness value returned by the IoT device (LDR) from pin A0
    data = json.loads(response)
    if data['success'] != 1:
        print("There was an error while retriving the data.")
        print("This is the error:"+data['value'])
        print()
        time.sleep(10)
        continue

    print ("This is the value "+data['value'])
    sensor_value=0
    try:
        sensor_value = int(data['value'])
    except e:
        print("There was an error while parsing the response: ",e)
        print()
        continue

    bound = compute_bounds(history_data,conf.FRAME_SIZE,conf.MUL_FACTOR)
    if not bound:
        required_data_count=conf.FRAME_SIZE-len(history_data)
        print("Not enough data to compute Z-score. Need ",required_data_count," more data points")
        print()
        history_data.append(int(data['value']))
        time.sleep(5)	#will collect data next time after 5 seconds
        continue

    try:
        if sensor_value > bound[0] :
            print ("The light level increased suddenly. Sending an SMS.")
            response = sms.send_sms("ALERT !! Someone apparently turned on the lights. The light level increased suddenly.")
            print("This is the response from Twilio",str(response))
            print("Status of sms:",str(response.status))
            
        elif sensor_value < bound[1]:
            print ("The light level decreased suddenly. Sending an SMS.")
            response = sms.send_sms("ALERT !! Someone apparently turned off the lights. The light level increased suddenly.")
            print("This is the response from Twilio",str(response))
            print("Status of sms:",str(response.status))
        history_data.append(sensor_value);
    except Exception as e:
        print ("Error",e)
    print()
    time.sleep(10)   #will collect data next time after 10 seconds
