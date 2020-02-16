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
def take_photo(bucket = "images-bucket-test-20075632"):
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
        
        # Run AWS Rekognition facial recognition algorithm
        # Compares source file with target file in the bucket
        face_matches = compare_faces(target_file, bucket)
        print("Face matches: " + str(face_matches))
        
        if(face_matches == 1):
            result = nameMatch
            target = target_file
            name_result, jpg = result.split('.')
            name_target, jpg = target.split('.')
            print(name_target + " is matching with " + name_result)
        else:
            print("No matches")
        
    except ClientError as e:
        logging.error(e)
        return False
    return True
    
def compare_faces(target_file, bucket):
    print("\nCompare Faces")
    #print("Source: " + sourceFile)
    print("Target: " + target_file)
    #print(bucket)
    
    # Counter
    j = 0
    
    # Create a connection with Rekognition
    client=boto3.client('rekognition')
    
    s3_connection = boto3.resource('s3')
    # Get source and target files from bucket
    #s3_object_source = s3_connection.Object(bucket, sourceFile)
    s3_object_target = s3_connection.Object(bucket,target_file)
    
    #s3_response_source = s3_object_source.get()
    s3_response_target = s3_object_target.get()
    
    # Read and open files
    #stream_source = io.BytesIO(s3_response_source['Body'].read())
    stream_target = io.BytesIO(s3_response_target['Body'].read())
    #imageSource = Image.open(stream_source)
    imageTarget = Image.open(stream_target)
    
    # Declaring a non string bucket value
    bucket1 = s3_connection.Bucket('images-bucket-test-20075632')
    # Iterate through all objects (i.e images) in the bucket
    for obj in bucket1.objects.all():
        # Key = current image
        key = obj.key
        # AWS compare_faces algorithm, comparing current image with target image
        response = client.compare_faces(SimilarityThreshold=80,
                                        SourceImage={'S3Object': {'Bucket':bucket, 'Name':key}},
                                        TargetImage={'S3Object': {'Bucket':bucket, 'Name':target_file}})
        
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
 