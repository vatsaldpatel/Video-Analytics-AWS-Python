import concurrent.futures
import datetime
import boto3
import _pickle as cPickle
import cv2
import time
import pytz
import uuid
from imutils.video import VideoStream
import signal
import sys
import os
from imutils import paths
import progressbar
import cProfile, pstats, io

#Enter your AWS Account Credentails
your_region_name = '' 
your_aws_access_key_id = ''
your_aws_secret_access_key = '' 

# Rekognition Client
rekog_client = boto3.client("rekognition", region_name = your_region_name, aws_access_key_id = your_aws_access_key_id,
                aws_secret_access_key = your_aws_secret_access_key)
                
# S3 Configuration
s3_client = boto3.client('s3', region_name = your_region_name , aws_access_key_id = your_aws_access_key_id,
                aws_secret_access_key = your_aws_secret_access_key)
s3_bucket = "Enter Your Bucket Name"
s3_key_frames_root = "frames/"

# Kinesis Client
kinesis_client = boto3.client("kinesis", region_name = your_region_name, aws_access_key_id = your_aws_access_key_id,
                aws_secret_access_key = your_aws_secret_access_key)

collectionId = '' #Used for Face Rekognition Only ( Create new Collection Using Index-Faces.py )
kinesis_data_stream_name = "" # Enter Your Kinesis Data Stream Name....Create One if not created


labels_on_watch_list_set = [] # Detected labels stored here 

#Calculating the Timestamp
utc_dt = pytz.utc.localize(datetime.datetime.now())
now_ts_utc = (utc_dt - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds()

# The time at which camera will capture the image
sec = 2.0

# Attributes of dynamoDb
name = ''
notification_type = ''
notification_message = ''
notification_title = ''

frame_id = str(uuid.uuid4())#Unique for every image
time_stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M") # Name of the folder in which the frames are stored.

# Frame Package = The dictionary which is to be inserted in the dynamoDB
frame_package ={
                'frame_id': frame_id,
                'approx_capture_timestamp' : int(now_ts_utc),
                'rekog_labels' : labels_on_watch_list_set,  
                's3_bucket':s3_bucket,
                'notification': name + " was spotted at your door.",
                'notification_type': str(notification_type), 
                'notification_title' : name + " spotted",
                's3_video_bucket' : 'video',
                's3_key' : s3_key_frames_root +frame_id + '.jpg',
                's3_video_key' :frame_id + '.mp4',
                'external_image_id' : name
                }

#Create Directory for local storage
cwd = os.getcwd()
if os.path.isdir(cwd + '/output') == False :
	os.mkdir(cwd + '/output')
	os.mkdir(cwd + '/output/images')
	os.mkdir(cwd + '/output/videos')


def capture_frames():
    """
    Job -> Takes image frames and stores in the output/images folder.
    """
    # function to handle keyboard interrupt
    def signal_handler(sig, frame):
        print("[INFO] You pressed `ctrl + c`! Your pictures are saved" \
            " in the output directory you specified...")
        sys.exit(0)

    # construct the argument parser and parse the arguments
    output_image = 'output/images'
    delay = 0.04 #in seconds
    

    # initialize the output directory path and create the output
    # directory
    outputDir = os.path.join(output_image, time_stamp)
    os.makedirs(outputDir)

    # initialize the video stream and allow the camera sensor to warmup
    print("[INFO] warming up camera...")
    #vs = VideoStream(src=0).start()
    vs = VideoStream(usePiCamera=False, resolution=(1920, 1280),
        framerate=30).start()
    #time.sleep(0)

    # set the frame count to zero
    count = 0

    # signal trap to handle keyboard interrupt
    signal.signal(signal.SIGINT, signal_handler)
    print("[INFO] Press `ctrl + c` to exit, or 'q' to quit if you have" \
        " the display option on...")

    # loop over frames from the video stream
    while count!=100:
        # grab the next frame from the stream
        frame = vs.read()

        # draw the timestamp on the frame
        ts = datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p")
        cv2.putText(frame, ts, (10, frame.shape[0] - 10), 
            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

        # write the current frame to output directory
        filename = str(count) + ".jpg"
        cv2.imwrite(os.path.join(outputDir, filename), frame)
   
        # increment the frame count and sleep for specified number of
        # seconds
        count += 1
        time.sleep(delay)

    # close any open windows and release the video stream pointer
    print("[INFO] cleaning up...")
    vs.stop()
    
def video_making():
    """
    Job --> Takes images from output/images folder stitches it together and saves back to output/videos folder
    """
    # function to get the frame number from the image path
    def get_number(imagePath):
        return int(imagePath.split(os.path.sep)[-1][:-4])

    inputs = 'output/images/' + str(time_stamp)
    output_vid = 'output/videos'
    fps = 10

    # initialize the FourCC and video writer
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    writer = None

    # grab the paths to the images, then initialize output file name and
    # output path 
    imagePaths = list(paths.list_images(inputs))
    #outputFile = "{}.mp4".format(inputs.split(os.path.sep)[2])
    outputFile = frame_id + ".avi"
    outputPath = os.path.join(output_vid, outputFile)
    print("[INFO] building {}...".format(outputPath))

    # initialize the progress bar
    widgets = ["Building Video: ", progressbar.Percentage(), " ", 
        progressbar.Bar(), " ", progressbar.ETA()]
    pbar = progressbar.ProgressBar(maxval=len(imagePaths), 
        widgets=widgets).start()

    # loop over all sorted input image paths
    for (i, imagePath) in enumerate(sorted(imagePaths, key=get_number)):
        # load the image
        image = cv2.imread(imagePath)

        # initialize the video writer if needed
        if writer is None:
            (H, W) = image.shape[:2]
            writer = cv2.VideoWriter(outputPath, fourcc, fps,
                (W, H), True)

        # write the image to output video
        writer.write(image)
        pbar.update(i)

    # release the writer object
    print("[INFO] cleaning up...")
    pbar.finish()
    writer.release()
    video_name = "output/videos/"+frame_id
    #converter = os.system('ffmpeg -i ' +video_name+'.avi -codec copy '+video_name+'.mp4')
    #converer = os.system('ffmpeg -i' +video_name+'.avi -vcodec h264 -acodec aac -strict -2 '+video_name+'.mp4')
    conv = os.system('ffmpeg -an -i '+video_name+'.avi -vcodec libx264 -pix_fmt yuv420p -profile:v baseline -level 3 '+ video_name+'.mp4')
    
    def upload_to_s3(local_file, bucket, s3_file):
        try:
            data = open(local_file, 'rb')
            s3_client.put_object(Key="video/"+frame_id+".mp4", Body=data, Bucket = s3_bucket,ContentType = 'video/mp4')
            print("Upload succcessful")
        except FileNotFoundError:
            print("Error in uploding the video")
    
    upload_to_s3("output/videos/"+frame_id+'.mp4', s3_bucket, "video/")
    return 0 
# Capturing the image and converting into bytearray
def convert_to_bytearray():
    
    """
    This fuctions captures the image after 2.0 seconds ,
    converts it into bytearray and returns it.
    """
    #time.sleep(3)
    frame = cv2.imread('output/images/'+str(time_stamp)+'/20.jpg')
    retval, buff = cv2.imencode(".jpg", frame)
    return bytearray(buff)

def Face_detection(img_bytes):
    """
    This function takes the input the bytearray of the image.
    Job --> Does FaceRekognition of the image
    Expected Output --> Detected Person and notification_type
    """
    detected_person = ''
    notification_type = ''
    # Detecting Faces in the Immage
    faceDetectionResponse = rekog_client.detect_faces(
                   Image=
                        {
                            'Bytes': img_bytes
                        },
                        Attributes=['ALL']
                    )

    # Check Face detection in an image
    # If there is a registered face(s) into a collection
    if len(faceDetectionResponse['FaceDetails']) != 0:
        # Search the face into the collection
        rekog_face_response = rekog_client.search_faces_by_image(
        CollectionId = collectionId,
        Image={ 
            'Bytes': img_bytes  
            }, 
        FaceMatchThreshold= 70,
        MaxFaces=10
        )
        
        if rekog_face_response['FaceMatches']:
            print('Detected, ',rekog_face_response['FaceMatches'][0]['Face']['ExternalImageId'])
            detected_person += rekog_face_response['FaceMatches'][0]['Face']['ExternalImageId'] + ' '
            notification_type += 'known'
            
        else:
            notification_type += 'unknown'
            detected_person += 'unknown '
            print('No faces matched')
            
    return (detected_person, notification_type)
    
def Label_detection(img_bytes):
    """
    This function takes the input the bytearray of the image.
    Job --> Does Label Detection of the image
    Expected Output --> Set of the detected labels and JSON object received after detect_labels
    """
    labels_on_watch_list = [] # Labels from DetectLables api saved here
    
	#Detecting labels in the image
    rekog_response = rekog_client.detect_labels(
                Image={
                    'Bytes': img_bytes
                },
                MaxLabels=10,
                MinConfidence= 90.0
            )
    for label in rekog_response['Labels']: 
            labels_on_watch_list.append(label['Name']) 
     
    return (set(labels_on_watch_list), rekog_response) 
    
def Animal_Detection(labels_on_watch_list_set, rekog_response):
    """
    This function takes the input labels_on_watch_list_set and rekog_response.
    Job --> Does Animal Detection in the image
    Expected Output --> Detected Animal and notification_type
    """
    detected_animal = ''
    notification_type = ''
    flag = False
    animal_categories_list = ["Tiger","Kangaroo","Elephnat","Panda","Dog" , "Pet" , "Canine" , "Labrador Retriever" , "Puppy"]
    for c in labels_on_watch_list_set:
        for d in animal_categories_list:
            if c == d :
				flag = True
                print("Animal Detected ---- " + c)
				detected_animal = c
                break
        if flag:
            notification_type += 'animal'
            break
    
    
    return (detected_animal, notification_type)

def Gun_Detection(img_bytes):
    """
    This function takes the input the bytearray of the image.
    Job --> Does Weapon Detection in the image
    Expected Output --> Detected Weapon and notification_type
    """
    unsafe_categories_list = []
    unsafe_list_set = []
    weapons = ["Gun","Weapon Violence","Weapon", "Handgun", "Weaponry","Violence"]
    
    detected_violence = ''
    notification_type = ''
    
    response_unsafe = rekog_client.detect_moderation_labels(
                     Image={
                            'Bytes': img_bytes
                        }
                    )
                    
    for label in response_unsafe['ModerationLabels']:
                unsafe_categories_list.append(label['Name'])

    # Convert List to Set (Unique Value)
    unsafe_list_set = set(unsafe_categories_list)        
    if any(c in weapons for c in unsafe_list_set):
        print("Unsafe Content (Gun, Weapons) Detected")
		detected_violence += 'Gun'
        notification_type  = 'suspicious'
    return (detected_violence, notification_type)

def Text_detection(img_bytes):
    """
    This function takes the input img_bytes.
    Job --> Does Text Detection in the image
    Expected Output --> Set of detected text.
    """
    text_list = []
    
    response=rekog_client.detect_text( 
        Image={ 'Bytes': img_bytes }
        )
    textDetections=response['TextDetections']

    for text in textDetections:
        text_list.append(text['DetectedText'])

    return set(text_list)

def NoteworthyVehicle_Detection(labels_on_watch_list_set, text_list_set):
    """
    This function takes the input labels_on_watch_list_set and text_list_set.
    Job --> Does Ambulance/Firetruck/DeliveryVan and NoteworthyVehicle Detection in the image
    Expected Output --> detected vehicle and notification type
    """
    detected_vehicle = ''
    notification_type = ''
    empty = set([])
    
    if(text_list_set == empty):
        return("","")
    
	#for noteworthy vehicles
    ambulance_list = ["Ambulance", "AMBULANCE", "EMERGENCY", "Emergency", "ambulance", "emergency", "108"] 
    fire_truck_list = ["Fire Truck","FIRE","Fire","RESCUE","FIRE RESCUE","F I R E","FIRE&RESCUE"]
    ambulanceCar = "EMERGENCY AMBULANCE Ambulance Emergency"
    
    # For delivery Vehicle
    australiapost_van = ["AUSTRALIA POST","AUSTRALIA","POST"]
    fedex_van = ["FedEx","Fedex","FEDEX","fedex","FedEx Express","FedEx Ground"]
    courier_van= ["CouriersPlease","Couriersplease","CouriersPleas"]
    dhl_van = ["DHL","EXCELLENCE. SIMPLY DELIVERED.","EXCELLENCE.SIMPLY DELIVERED.","www.dhl.com","SIMPLY","Express&Logistic","www.dhl.co.uk","www.dhl.it"]
    startrack_van = ["STARTRACK","startrack","STAR TRACK","STARTRACK EXPRESS","STARTRACK Courier","COURIER","Courier","Powering eCommerce","ecommerce","powering ecommerce"]
    usps_van = ["www.usps.com","WWW.uspS.COM","USPS","usps","UNITED STATES POSTAL SERVICE","We Deliver For You","we deliver for you","We Deliver For You."]

    known_vehical_categories_list = ["Car", "Truck", "Van", "Vehicle", "Transportation", "Automobile", "Caravan", "Moving Van", "Wheel", "Alloy Wheel", "Tire", "Spoke", "Car Wheel", "Ambulance"]
    
	# Fire Truck and AMBULANCE Detection
    if any(c in labels_on_watch_list_set for c in known_vehical_categories_list):
        if any(c in text_list_set for c in ambulance_list):
            print("Ambulance Detected")
			detected_vehicle += 'Ambulance'
            return(detected_vehicle, 'Vehicle ')
        if any(c in text_list_set for c in fire_truck_list):
            print("FireTruck Detected")
			detected_vehicle += 'Fire Truck'
            return(detected_vehicle, 'Vehicle ')
       
    # Delivery Van Vehicles
    if any(c in text_list_set for c in dhl_van):
        print("Courier Van Detected ---" + c)
		detected_vehicle += "courier vehicle"
        return (detected_vehicle, 'Vehicle ')
    elif any(c in text_list_set for c in australiapost_van):
        print("Courier Van Detected ---" + c)
		detected_vehicle += "courier vehicle"
        return (detected_vehicle, 'Vehicle ')
    elif any(c in text_list_set for c in startrack_van):
        print("Courier Van Detected ---" + c)
		detected_vehicle += "courier vehicle"
        return (detected_vehicle, 'Vehicle ')
    elif any(c in text_list_set for c in usps_van):
        print("Courier Van Detected ---" + c)
		detected_vehicle += "courier vehicle"
        return (detected_vehicle, 'Vehicle ')
    elif any(c in text_list_set for c in fedex_van):
        print("Courier Van Detected ---" + c)
		detected_vehicle += "courier vehicle"
        return (detected_vehicle, 'Vehicle ')
    elif any(c in text_list_set for c in courier_van):
        detected_vehicle += "courier vehicle"
        return (detected_vehicle, 'Vehicle ')  
    return("","")

##Main Function to Upload all output data to AWS Cloud
def Upload_to_aws(l):
    detected_person, notification_type_face = l[0]
    labels_on_watch_list_set, rekog_response = l[1]
    detected_violence, notification_type_gun = l[3]
    text_list_set = l[4]
    detected_animal, notification_type_animal = l[2]
    detected_vehicle, notification_type_vehicle = l[5]
    
    final_notification_type = []
    final_name = []
    final_name.append(detected_person)
    final_name.append(detected_animal)
    final_name.append(detected_violence)
    final_name.append(detected_vehicle)
    
    #Removing Empty Entries
    for i in range(len(final_name)):
        try:
            final_name.remove('')
        
        except ValueError:
            pass
   
    name = ''
    notification_type = ''
    notification_message = ''
    notification_title = ''
    
	#Formating the output in readable format
    if len(final_name) == 0:
        name += 'Nothing'
    elif len(final_name) == 1:
        name += final_name[0]
    elif len(final_name) == 2:
        name += final_name[0] + 'with ' + final_name[1]
    elif len(final_name) == 3:
        name += final_name[0] + 'with ' + final_name[1] + 'and ' + final_name[2]    
    
	#Editing the display output for DyanmoDb Table
    if notification_type_gun == 'suspicious':
        notification_type = 'suspicious'
        notification_message = 'An unusual activity may have been spotted at your front Door. You should review immediately.'
        notification_title = 'Suspicious spotted'
    elif detected_vehicle == 'courier vehicle' and (notification_type_face == 'known' or notification_type_face=='unknown'):
        notification_type = 'vehicle'
        notification_message = 'A courier service personnel may have been spotted.'
        notification_title = 'Courier service personnel spotted'
    elif (detected_vehicle == 'Ambulance' or detected_vehicle == 'Fire Truck'):
        notification_type = 'vehicle'
        if detected_vehicle == 'Ambulance':
            notification_message = 'An ambulance was spotted at your door.'
            notification_title = 'Ambulance spotted'
        else:
            notification_message = 'A fire truck was spotted at your door.'
            notification_title = 'FireTruck spotted'
    elif detected_vehicle == 'courier vehicle':
        notification_type = 'vehicle'
        notification_message = 'A courier vehicle may have been spotted.'
        notification_title = 'Courier vehicle spotted'
    elif notification_type_face == 'unknown':
        notification_type = 'unknown'
        notification_message = 'An unknown was spotted at your door.'
        notification_title = 'Unknown spotted'
    elif notification_type_face == 'known':
        notification_type = 'known'
        notification_message = detected_person + ' was spotted at your door.'
        notification_title = ' Known spotted'
    elif notification_type_animal == 'animal':
        notification_type = 'animal'
        notification_message = 'An animal was spotted at your front door.'
        notification_title = 'Animal spotted'
        
    # Changing the values of the dictionary 
    frame_package['rekog_labels'] = labels_on_watch_list_set
    frame_package['notification'] = notification_message
    frame_package['notification_type'] = notification_type
    frame_package['notification_title'] = notification_title
    frame_package['external_image_id'] = name  
    print("Final Output of Whole Program")
	print("##############################")
	print(frame_package)
    frame_package['img_bytes'] = l[6]
    
	#Encoding the data and putting it on the kinesis stream
    response = kinesis_client.put_record(
                    StreamName= kinesis_data_stream_name,
                    Data=cPickle.dumps(frame_package),
                    PartitionKey="partitionkey"
                )
    
## Parallel Exceution of Each Function
with concurrent.futures.ProcessPoolExecutor() as executor:
    v0 = executor.submit(capture_frames)
    #After Image Capture wait till 20sec
	time.sleep(20)
    v1 = executor.submit(convert_to_bytearray)
    flag = True
    while flag:
        if v1.done():
            flag = False
            f2=executor.submit(Label_detection,v1.result())
            f5=executor.submit(Text_detection,v1.result())
            f1=executor.submit(Face_detection,v1.result())
            f4=executor.submit(Gun_Detection,v1.result())
    
    flag = True
    while flag:
        if f2.done():
            flag = False
            x,y = f2.result()
            f3=executor.submit(Animal_Detection,x,y)
            
    flag = True
    while flag:
        if f5.done():
            flag = False
            z = f5.result()
            x,y = f2.result()
            f6=executor.submit(NoteworthyVehicle_Detection,x,z)
            
    flag = True
    while flag:
        if f1.done() and f2.done() and f3.done() and f4.done() and f5.done() and f6.done():
            flag = False
            a = f1.result()
            b = f2.result()
            c = f3.result()
            d = f4.result()
            e = f5.result()
            f = f6.result()
            g = v1.result()
            l = [a,b,c,d,e,f,g]
            f7=executor.submit(Upload_to_aws,l)
            
    flag = True
    while flag:
        if v0.done():
            flag = False
            video = executor.submit(video_making)      

#End of Code
