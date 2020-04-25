from gpiozero import MotionSensor, LED
from picamera import PiCamera
from signal import pause
from time import sleep
from datetime import date
import time
import sys
import logging
import boto3
from botocore.exceptions import ClientError
import io
from PIL import Image
import json
import lcd

# Initiliaze components
pir = MotionSensor(4) # Pin 4
led = LED(16) # Pin 16
camera = PiCamera()
today = date.today()
today_date = today.strftime("%d/%m/%y")

# Count images taken in one run
i = 0

def stop_camera():    
    lcd.setText("")
    lcd.setRGB(0, 0, 0)
    print("\nNo motion")
    led.off()
    print("Camera off")
    camera.stop_preview()


def take_photo():
    # bucket = S3 bucket where the images are stored
    bucket = "fyp-caller-images"
    print("\nMotion")
    
    camera.start_preview()
    sleep(5)
    global i
    i = i + 1
    print("Camera " + str(i))    
    # CAUTION!! Overwrites images starting from image_1
    camera.capture('/home/pi/final-year-project/image_%s.jpg' % i)
    newImage = ('/home/pi/final-year-project/image_%s.jpg' % i)
    print("A photo has been taken")
    camera.stop_preview()
    target_file = ('image_%s.jpg' % i)
    # Upload new image to S3 bucket
    upload_file(newImage, bucket, target_file, True)
    sleep(5)
    
def detect_face(photo):
    client = boto3.client('rekognition')
    bucket = 'fyp-caller-images'
    
    response = client.detect_faces(Image={'S3Object': {'Bucket':bucket, 'Name':photo}},
                                   Attributes=['ALL'])
    if (len(response['FaceDetails']) == 1):
        led.on()
        lcd.setText("Motion")
        lcd.setRGB(0, 128, 64)
        # compare
        face_matches = compare_faces(client, photo, bucket)
        print("Face matches: " + str(face_matches))     
        
        # Run AWS Rekognition facial recognition algorithm
        # Compares source file with target file in the bucket
        if(face_matches == 1):
            result = nameMatch
            target = photo
            name_result, jpg = result.split('.')
            name_target, jpg = target.split('.')
            print(name_target + " is matching with " + name_result)
            
            
            t = time.localtime()
            current_time = time.strftime("%H:%M", t)
            
            # Writing to text file
            f = open("caller_name.txt", "w+")
            f.write(name_result)
            f.close()
            
            l = open("last_caller.txt", "w+")
            l.write(name_result + " was the last person at your door at " + today_date + " " + current_time)
            l.close()
            
            k = open("status.txt", "w+")
            known = "true"
            k.write(known)
            k.close()
            
            # Write to Caller log file and upload to s3
            with open("caller_log.txt", "a") as text_file:
                text_file.write("\n" + today_date + " " + current_time + " - " + name_result)
            upload_file('/home/pi/final-year-project/caller_log.txt', "caller-details", "caller_log.txt", False)
            
            # Upload to S3 bucket 'caller-names'
            upload_file('/home/pi/final-year-project/caller_name.txt', "caller-details", "caller_name.txt", False)
            upload_file('/home/pi/final-year-project/last_caller.txt', "caller-details", "last_caller.txt", False)
            upload_file('/home/pi/final-year-project/status.txt', "caller-details", "status.txt", False)
            lcd.setText(name_result + " is at the door!")
            lcd.setRGB(0, 255, 0)
        else:
            face_count=face_details(client, photo)
            print("Faces detected: " + str(face_count))
        
    else:
        print("No face")
        return False
    
    
    
    return True

def upload_file(newImage, bucket, target_file, detect):
    # Create a connection with AWS
    s3_client = boto3.client('s3')
    sleep(1)
    try:
        # Pushing file up to S3      (source file, bucket, target file)
        response = s3_client.upload_file(newImage, bucket, target_file)
        bucketUpload = "images-bucket-test-20075632"
        
        if detect:
            detect_face(target_file)        
                    
    except ClientError as e:
        logging.error(e)
        return False
    return True

def face_details(client, target_file):
    print("No matches")
    response_detail = client.detect_faces(Image={'S3Object': {'Bucket':'fyp-caller-images', 'Name':target_file}},
                                          Attributes=['ALL'])
    print('Detected faces for ' + target_file)
    for faceDetail in response_detail['FaceDetails']:
        print('The detected face is between ' + str(faceDetail['AgeRange']['Low'])
              + ' and ' + str(faceDetail['AgeRange']['High']) + ' years old.')
        #print('Here are some other attributes: ')
        #print(json.dumps(faceDetail, indent=4, sort_keys=True))
    
    spectacles = faceDetail['Eyeglasses']['Value']
    if spectacles:
        eyeglasses = " They were wearing eyeglasses."
    else:
        eyeglasses = " They were not wearing eyeglasses."
    
    sunnies = faceDetail['Sunglasses']['Value']
    if sunnies:
        sunglasses = " They were wearing sunglasses."
    else:
        sunglasses = " They weren't wearing sunglasses."
    
    smileEv = faceDetail['Smile']['Value']
    if smileEv:
        smile = " They were smiling."
    else:
        smile = " They weren't smiling."
    
    if (faceDetail['Gender']['Value'] == "male" or faceDetail['Gender']['Value'] == "Male"):
        beardEv = faceDetail['Beard']['Value']
        if beardEv:
            beard = " They had a beard."
        else:
            beard = " They didn't have a beard."
        mustEv = faceDetail['Mustache']['Value']
        if mustEv:
            mustache = " They had a mustache."
        else:
            mustache = " They didn't have a mustache."
        
        details = ("A " + faceDetail['Gender']['Value'] + ", aged between " + str(faceDetail['AgeRange']['Low']) + " & "
                + str(faceDetail['AgeRange']['High']) + " is at your door!" + eyeglasses + sunglasses
                   + mustache + beard + smile)
        
    elif (faceDetail['Gender']['Value'] == "female" or faceDetail['Gender']['Value'] == "Female"):
        
        details = ("A " + faceDetail['Gender']['Value'] + ", aged between " + str(faceDetail['AgeRange']['Low']) + " & "
                + str(faceDetail['AgeRange']['High']) + " is at your door!" + eyeglasses + sunglasses + smile)
        
    t = time.localtime()
    current_time = time.strftime("%H:%M", t)
    details_time = ("A " + faceDetail['Gender']['Value'] + ", aged between " + str(faceDetail['AgeRange']['Low']) + " & "
                + str(faceDetail['AgeRange']['High']) + " was at your door at " + today_date + " " + current_time)
    
    
    s = open("status.txt", "w+")
    known = "false"
    s.write(known)
    s.close()
    
    l = open("last_caller.txt", "w+")
    l.write(details_time)
    l.close()
    
    u = open("caller_unknown.txt", "w+")
    u.write(details)
    u.close()
            
    # Write to Caller log file and upload to s3
    with open("caller_log.txt", "a") as text_file:
        text_file.write("\n" + today_date + " "  + current_time + " - Stranger (" + faceDetail['Gender']['Value'] + ")")
    upload_file('/home/pi/final-year-project/caller_log.txt', "caller-details", "caller_log.txt", False)
    # Upload to S3 bucket 'caller-names'
    upload_file('/home/pi/final-year-project/status.txt', "caller-details", "status.txt", False)
    upload_file('/home/pi/final-year-project/last_caller.txt', "caller-details", "last_caller.txt", False)
    upload_file('/home/pi/final-year-project/caller_unknown.txt', "caller-details", "caller_unknown.txt", False)
    print(details)
    
    
    lcd.setRGB(255, 0, 0)
    lcd.setText(current_time +": A " + faceDetail['Gender']['Value'] + " is at the door!")
    time.sleep(2)
    lcd.setText(current_time +":Aged between " + str(faceDetail['AgeRange']['Low']) + " & "
                + str(faceDetail['AgeRange']['High']))
    
    
    return len(response_detail['FaceDetails'])
    
def compare_faces(client, target_file, bucket):
    print("\nCompare Faces")
    #print("Source: " + sourceFile)
    print("Target: " + target_file)
    #print(bucket)
    
    # Counter
    j = 0
    
        
    s3_connection = boto3.resource('s3')
    
    # Declaring a non string bucket value for iteration
    bucket1 = s3_connection.Bucket('alexa-admin-2007563204634-env')

    # Iterate through all objects (i.e images) in the bucket
    for obj in bucket1.objects.all():
        # Key = current image
        key = obj.key
        # AWS compare_faces algorithm, comparing current image with target image
        response = client.compare_faces(SimilarityThreshold=80,
                                        SourceImage={'S3Object': {'Bucket':'alexa-admin-2007563204634-env', 'Name':key}},
                                        TargetImage={'S3Object': {'Bucket':'fyp-caller-images', 'Name':target_file}})
        
        for faceMatch in response['FaceMatches']:
            position = faceMatch['Face']['BoundingBox']
            similarity = str(faceMatch['Similarity'])
            global nameMatch
            nameMatch = key
            print(nameMatch + " The face at " + str(position['Left']) + " " +
                  str(position['Top']) +
                  " matches with " + similarity + "% confidence")
            if len(response['FaceMatches'])==1:
                j = j + 1
            return j
    return response['FaceMatches']
    
# When motion detected begin 'take_photo' method
pir.when_motion = take_photo
# When no motion detected run the 'stop_camera' method
pir.when_no_motion = stop_camera    
pause()
 
