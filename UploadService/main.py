from fastapi import FastAPI, Request
import git
import os
import boto3
import logging
import uuid
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI()

origins = [
    "http://localhost",
    "http://127.0.0.1:3000",
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def health():
    return {"message" : "site is up"}

class GithubUrl(BaseModel):
    github_url : str

@app.post("/collect_files")
async def collect_files_and_push_to_s3_bucket(request : Request, giturl : GithubUrl):
    github_url = giturl.github_url
    # check for valid github url
    # if not github_url.startswith("https://github.com"):
    #     return {"message" : "Invalid github url"}

    # path for the local directory where the repo will be cloned
    homedir = os.path.expanduser("~")
    local_des = os.path.join(homedir, "Repos")

    # delete the directory if it already exists
    if os.path.exists(local_des):
        os.system(f"rm -rf {local_des}/")

    # clone the repo
    try:
        git.Repo.clone_from(github_url, local_des)
    except Exception as e:
        return {"message" : f"Either Repo is private or doesn't exist"} 

    # creating a bucket
    s3 = boto3.client("s3", aws_access_key_id=os.getenv("AWS_ACCESS_KEY"), aws_secret_access_key=os.getenv("AWS_SECRET"))
    unique_id = str(uuid.uuid4()).replace("-", "").lower()[:7]
    print(unique_id)
    unique_bucket_name = "bucket" + unique_id
    s3.create_bucket(Bucket=unique_bucket_name)

    logger.info(f"Bucket {unique_bucket_name} created successfully")
    # upload files to the bucket    
    def upload_files_to_s3_bucket(local_des, unique_bucket_name):
        for root, dirs, files in os.walk(local_des):
            for file in files:
                file_path = os.path.join(root, file)
                s3_key = os.path.relpath(file_path, local_des)
                s3.upload_file(file_path, unique_bucket_name, s3_key)
    
    try:
        upload_files_to_s3_bucket(local_des, unique_bucket_name)
    except Exception as e:
        return {"message" : f"Error while uploading files to s3 bucket {e}"}

    # setting up the aws sqs

    sqs = boto3.client("sqs", 
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY"), 
        aws_secret_access_key=os.getenv("AWS_SECRET"),
        region_name=os.getenv("AWS_REGION"))

    logger.info(f"SQS client created successfully")

    # send message to sqs
    async def send_message_to_sqs(unique_bucket_name):
        try:
            response = sqs.send_message(
                QueueUrl=os.getenv("AWS_SQS_URL"),
                MessageBody=unique_bucket_name
            )
            
            logger.info(f"Message sent to SQS for bucket {unique_bucket_name}: {response}")
            return response
        except Exception as e:
            logger.error(f"Error sending message to SQS: {e}")
            return {"message": f"Error sending message to SQS: {e}"}

        return response
    # logger.info(f"Sending message to sqs for bucket {unique_bucket_name}")
    try:
        await send_message_to_sqs(unique_bucket_name)
    except Exception as e:
        return {"message" : f"Error while sending message to sqs {e}"}

    response = {
        "message" : f"Successfully pushed to s3 {github_url}",
        "unique_id" : unique_id
    }

    return response
