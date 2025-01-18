import boto3
import os
import time
from dotenv import load_dotenv
import subprocess
import logging
import uvicorn
from fastapi import FastAPI, Request
import redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

r = redis.Redis(host='localhost', port=6379, db=0)

# Set up the SQS client
sqs = boto3.client(
    "sqs",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET"),
    region_name=os.getenv("AWS_REGION")
)
s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET")
)
queue_url = os.getenv("AWS_SQS_URL")

def download_the_repo(bucket_name):

    # Download the files from the bucket
    try:
        response = s3.list_objects_v2(Bucket=bucket_name)
        # print(response)
        for obj in response.get('Contents', []):
            key = obj['Key']
            local_file = os.path.join(os.getcwd(), 'Repo' ,key)
            local_dir = os.path.dirname(local_file)
            if not os.path.exists(local_dir):
                os.makedirs(local_dir)
            # print(local_file)
            s3.download_file(bucket_name, key, local_file)
            # print(f"Downloaded {key} to {local_file}")
        logger.info(f"Downloaded the repo")
    except Exception as e:  
        print(f"Error downloading files from bucket: {e}")
    
def building_the_project():
    # Build the react project which is present in Repo folder
    try:
        current_dir = os.getcwd()
        project_dir = os.path.join(current_dir, "Repo")

        os.chdir(project_dir)
        install_result = subprocess.run(["npm", "install"], check=True, text=True, capture_output=True)
        print(install_result.stdout)

        result = subprocess.run(["npm", "run", "build"], check=True, text=True, capture_output=True)
        print(result.stdout)

        logger.info(f"Build the project")

    except Exception as e:
        print(f"Error building project: {e}")

def push_the_build_to_s3(bucket_name):
    # Push the build to the bucket
    current_dir = os.getcwd() #/Users/ksoni/Desktop/AutoDeployer/DeployService/Repo
    project_dir = os.path.join(current_dir, "build")
    print(f"Project directory: {project_dir}")

    if not os.path.exists(project_dir):
        print(f"Directory does not exist: {project_dir}")
        return

    try:
        for root, dirs, files in os.walk(project_dir): 
            pass
            for file in files:
                file_path = os.path.join(root, file)
                s3_key = os.path.relpath(file_path, project_dir)
                print(f"uploading {file_path} to {bucket_name}/build/{s3_key}") 
                try:
                    s3.upload_file(file_path, bucket_name, f"build/{s3_key}")
                    print(f"Uploaded {file_path} to {bucket_name}/build/{s3_key}")
                except Exception as e:
                    print(f"failed to upload {file_path} to {bucket_name}/build/{s3_key}")
    

        # push the bucket name to redis hashset
        logger.info(f"Pushing the bucket name to redis")
        r.hset("deployment_status", bucket_name, "deployed")


        logger.info(f"Pushed the build to S3")
        # remove the repo folder
        print(os.getcwd())
        os.system(f"rm -rf {current_dir}")
        logger.info("Removed the repo folder")


    except Exception as e:
        print(f"Error uploading files to bucket: {e}")

def poll_messages_from_sqs():
    while True:
        print(1)
        try:
            response = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=10
            )
            messages = response.get('Messages', [])
            if messages:
                for message in messages:
                    print(f"Received message: {message['Body']}")
                    # Process the message here

                    download_the_repo(message['Body'])
                    
                    building_the_project()
                    
                    push_the_build_to_s3(message['Body'])

                    # Delete the message after processing
                    sqs.delete_message(
                        QueueUrl=queue_url,
                        ReceiptHandle=message['ReceiptHandle']
                    )
                    print("Message deleted")
            else:
                print("No messages received")
        except Exception as e:
            print(f"Error receiving message from SQS: {e}")
        
        # Wait for a short period before polling again
        time.sleep(5)
    
if __name__ == "__main__":
    poll_messages_from_sqs()
    
    