from gpiozero import MotionSensor, LED
from picamera import PiCamera
from signal import pause
from time import sleep
import sys
import logging
import boto3
from botocore.exceptions import ClientError
import io
from PIL import Image
import json

# Initiliaze components
pir = MotionSensor(4) # Pin 4
led = LED(16) # Pin 16
camera = PiCamera()

# Count images taken in one run
i = 0

def stop_camera():
    print("\nNo motion")
    led.off()
    print("Camera off")
    camera.stop_preview()

# bucket = S3 bucket where the images are stored
def take_photo(bucket = "fyp-caller-images"):
    print("\nMotion")
    led.on()
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
    upload_file(newImage, bucket, target_file)
    sleep(10)

def upload_file(newImage, bucket, target_file):
    # Create a connection with AWS
    s3_client = boto3.client('s3')
    sleep(1)
    try:
        # Pushing file up to S3      (source file, bucket, target file)
        response = s3_client.upload_file(newImage, bucket, target_file)
        bucketUpload = "images-bucket-test-20075632"
        
        # Create a connection with Rekognition
        client=boto3.client('rekognition')
        # Run AWS Rekognition facial recognition algorithm
        # Compares source file with target file in the bucket
        face_matches = compare_faces(client, target_file, bucketUpload)
        print("Face matches: " + str(face_matches))
        
        
        
        if(face_matches == 1):
            result = nameMatch
            target = target_file
            name_result, jpg = result.split('.')
            name_target, jpg = target.split('.')
            print(name_target + " is matching with " + name_result)
            
            # Create a connection to Lambda
            lambda_client = boto3.client('lambda')
        
            # Input for the Lambda function
            params = { 'Name' : name_result }
        
            # Invoke the function
            response_lambda = lambda_client.invoke(
                FunctionName='testFunction',
                LogType='Tail',
                Payload=json.dumps(params)
                )
            # Output from function
            print(response_lambda['Payload'].read())
        else:
            face_count=face_details(client, target_file)
            print("Faces detected: " + str(face_count))
                    
    except ClientError as e:
        logging.error(e)
        return False
    return True

def face_details(client, target_file):
    print("No matches")
    response_detail = client.detect_faces(Image={'S3Object': {'Bucket':'fyp-caller-images', 'Name':target_file}}, Attributes=['ALL'])
    print('Detected faces for ' + target_file)
    for faceDetail in response_detail['FaceDetails']:
        print('The detected face is between ' + str(faceDetail['AgeRange']['Low'])
              + ' and ' + str(faceDetail['AgeRange']['High']) + ' years old.')
        print('Here are some other attributes: ')
        print(json.dumps(faceDetail, indent=4, sort_keys=True))
    # Create a connection to Lambda
    lambda_client_uk = boto3.client('lambda')
    # Input for the Lambda function
    params = { 'AgeLow' : faceDetail['AgeRange']['Low'],
               'AgeHigh' : faceDetail['AgeRange']['High'],
               'Gender': faceDetail['Gender']['Value'],
               'Eyeglasses': faceDetail['Eyeglasses']['Value'],
               'Sunglasses': faceDetail['Sunglasses']['Value'],
               'Beard': faceDetail['Beard']['Value'],
               'Mustache': faceDetail['Mustache']['Value'],
               'Smile': faceDetail['Smile']['Value'],}
    # Invoke the function
    response_lambda_uk = lambda_client_uk.invoke(
        FunctionName='describeUnknownCaller',
        LogType='Tail',
        Payload=json.dumps(params)
        )
    # Output from function
    print(response_lambda_uk['Payload'].read())
    return len(response_detail['FaceDetails'])
    
def compare_faces(client, target_file, bucket):
    print("\nCompare Faces")
    #print("Source: " + sourceFile)
    print("Target: " + target_file)
    #print(bucket)
    
    # Counter
    j = 0
    
        
    s3_connection = boto3.resource('s3')
    
    # Declaring a non string bucket value
    bucket1 = s3_connection.Bucket('images-bucket-test-20075632')
    bucketCaller = "fyp-caller-images"
    # Iterate through all objects (i.e images) in the bucket
    for obj in bucket1.objects.all():
        # Key = current image
        key = obj.key
        # AWS compare_faces algorithm, comparing current image with target image
        response = client.compare_faces(SimilarityThreshold=80,
                                        SourceImage={'S3Object': {'Bucket':bucket, 'Name':key}},
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
 