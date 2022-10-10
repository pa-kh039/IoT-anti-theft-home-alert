import sys
# sys.path.append("/home/parth/Desktop/iot/anomaly_detection/config_folder")  #this folder has the .py file which contains configurations like api_key, phone number, etc.
sys.path.insert(0, '/home/parth/Desktop/miscellaneous/iot/anomaly_detection/config_folder/.')
import json, time, math, statistics
from conf import API_KEY,DEVICE_ID,SSID,AUTH_TOKEN,TO_NUMBER,FROM_NUMBER,MAILGUN_API_KEY,SANDBOX_URL,SENDER_EMAIL,RECIPIENT_EMAIL,FRAME_SIZE,MUL_FACTOR
from boltiot import Email, Sms, Bolt

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

mybolt = Bolt(API_KEY(), DEVICE_ID())
sms = Sms(SSID(), AUTH_TOKEN(), TO_NUMBER(), FROM_NUMBER())
history_data=[]
mailer = Email(MAILGUN_API_KEY(), SANDBOX_URL(), SENDER_EMAIL(), RECIPIENT_EMAIL())

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

    bound = compute_bounds(history_data,FRAME_SIZE(),MUL_FACTOR())
    if not bound:
        required_data_count=FRAME_SIZE()-len(history_data)
        print("Not enough data to compute Z-score. Need ",required_data_count," more data points")
        print()
        history_data.append(int(data['value']))
        time.sleep(5)	#will collect data next time after 5 seconds
        continue

    if sensor_value > bound[0] :
        try:
            print ("The light level increased suddenly. Sending an SMS...")
            response = sms.send_sms("ALERT !! Someone apparently turned on the lights. The light level increased suddenly.")
            print("This is the response from Twilio",str(response))
            print("Status of sms:",str(response.status))
        except:
            print("Encountered error while sending SMS.....")
        print()
        try:
            print("Now sending email...")
            response2 = mailer.send_email("ALERT !!","Someone apparently turned on the lights. The light level increased suddenly.")
            response2_text = json.loads(response2.text)
            print("Response received from Mailgun is: " + str(response2_text['message']))
        except:
            print("Encountered error while sending email.....")
        print()
    elif sensor_value < bound[1]:
        try:
            print ("The light level decreased suddenly. Sending an SMS...")
            response = sms.send_sms("ALERT !! Someone apparently turned off the lights. The light level decreased suddenly.")
            print("This is the response from Twilio",str(response))
            print("Status of sms:",str(response.status))
        except Exception as e:
            print("Encountered error while sending SMS.....")
            print ("Error",e)
        print()
        try:
            print("Now sending email...")
            response2 = mailer.send_email("ALERT !!","Someone apparently turned off the lights. The light level decreased suddenly.")
            response2_text = json.loads(response2.text)
            print("Response received from Mailgun is: " + str(response2_text['message']))
        except Exception as e:
            print("Encountered error while sending email.....")
            print ("Error",e)
            print()
    else:
        print()
    history_data.append(sensor_value)
    # print()
    time.sleep(10)   #will collect data next time after 10 seconds
