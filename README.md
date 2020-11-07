# AWS-Rekognition for Video Analytics Using Python
We here implement Advance Scene Detection Analytics across Edge and Cloud resources.The proposal uses AWS(Amazon Web Services) as a base platform for implementation.
It is an attempt to mimic the scenario described in the paper 
[Demonstration of a Cloud-based Software Framework for Video Analytics Application using Low-Cost IoT Devices](https://arxiv.org/abs/2010.07680).
For more detailed explantation of paper watch this video [A Cloud-based Smart Doorbell using Low-Cost COTS Devices](https://www.youtube.com/watch?v=42mx4Z2PDwA).

**The Salient Features of implementaion are :** 
* Known/Unknown Face Detection
* Animal Detection like Dog, Cat, Kangaroo etc.
* Unsafe Content Detection like Knife, Guns, Weapons.
* NoteWorthy Vehicle Detections like Ambulance, Fire Truck, Courier Vans (FedEx, DHL etc.)

***
# AWS Services Used
* AWS Rekognition - For advance scence detection in a video
* AWS Kinesis - For uploading video analytics data of edge to AWS cloud.
* AWS DynamoDB - For storing video analytics data in Cloud.
* AWS S3- For storing videos and frames (images) of edge at Cloud.
* AWS Lambda - For handling all events of Cloud.

***
# Configuration of AWS Services
**1. AWS Kinesis :**
Create a data stream to get data from edge.


**2. AWS DynamoDb :**
Create a Table in DynamoDB with partion key as **"frame_id"**.
Create Table with following cloumns :
![Table-Columns-Name](https://github.com/ResearchTrio/AWS-Rekognition-Python/blob/main/Column_Name.jpg)


**3. AWS S3 :**
Create a S3 bucket and create two folders with names **“frames” & “video”** in it.
![S3-Directory](https://github.com/ResearchTrio/AWS-Rekognition-Python/blob/main/S3_Directory.jpg)


**4. AWS Lambda :**
Create a Lambda Function with all permissions IAM Role and add **“Kinesis” & “DynamoDB”** as Triggers.
Paste the [lamda_function.py](https://github.com/ResearchTrio/AWS-Rekognition-Python/blob/main/lambda_function.py) code in your lambda function

***

# Edge Implementation
Run [main-video-analytic-code.py](https://github.com/ResearchTrio/AWS-Rekognition-Python/blob/main/main-video-analytic-code.py) on Edge Device(Laptop, Raspberry PI)

***

# Output 

* **Edge Output**

![edge-output](https://github.com/ResearchTrio/AWS-Rekognition-Python/blob/main/edge_output.png)

* **DynamoDB Output**

![dynamodb-output](https://github.com/ResearchTrio/AWS-Rekognition-Python/blob/main/dynamodb_output.jpg)

