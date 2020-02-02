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
    newImage = ('/home/pi/Documents/image_%s.jpg' % i)
    print("A photo has been taken")
    camera.stop_preview()
    object_name = ('image_%s.jpg' % i)
    # Upload new image to S3 bucket
    upload_file(newImage, bucket, object_name)
    sleep(10)

def upload_file(newImage, bucket, object_name):
    # Create a connection with AWS
    s3_client = boto3.client('s3')
    source_file = 'laurie.jpg'
    sourceFile = source_file
    targetFile = object_name
    sleep(1)
    try:
        # Pushing file up to S3      (source file, bucket, target file)
        response = s3_client.upload_file(newImage, bucket, object_name)
        # Run AWS Rekognition facial recognition algorithm
        # Compares source file with target file in the bucket
        face_matches = compare_faces(sourceFile, targetFile, bucket)
        print("Face matches: " + str(face_matches))
        
        if(face_matches == 1):
            print("It's " + source_file)
        else:
            print("No matches")
    except ClientError as e:
        logging.error(e)
        return False
    return True
    
def compare_faces(sourceFile, targetFile, bucket):
    print("\nCompare Faces")
    print("Source: " + sourceFile)
    print("Target: " + targetFile)
    print(bucket)
    
    # Create a connection with Rekognition
    client=boto3.client('rekognition')
    
    s3_connection = boto3.resource('s3')
    # Get source and target files from bucket
    s3_object_source = s3_connection.Object(bucket, sourceFile)
    s3_object_target = s3_connection.Object(bucket,targetFile)
    s3_response_source = s3_object_source.get()
    s3_response_target = s3_object_target.get()
    
    # Read and open files
    stream_source = io.BytesIO(s3_response_source['Body'].read())
    stream_target = io.BytesIO(s3_response_target['Body'].read())
    imageSource = Image.open(stream_source)
    imageTarget = Image.open(stream_target)
    
    # AWS compare_faces algorithm
    response = client.compare_faces(SimilarityThreshold=80,
                                    SourceImage={'S3Object': {'Bucket':bucket, 'Name':sourceFile}},
                                   TargetImage={'S3Object': {'Bucket':bucket, 'Name':targetFile}})
    
    for faceMatch in response['FaceMatches']:
        position = faceMatch['Face']['BoundingBox']
        similarity = str(faceMatch['Similarity'])
        print("The face at " + str(position['Left']) + " " +
              str(position['Top']) +
              " matches with " + similarity + "% confidence")
       
    imageSource.show()
    imageTarget.show()
    imageSource.close()
    imageTarget.close()
    return len(response['FaceMatches'])
    print("Done")
    
# When motion detected begin 'take_photo' method
pir.when_motion = take_photo
# When no motion detected run the 'stop_camera' method
pir.when_no_motion = stop_camera    
pause()
 