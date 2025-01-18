from fastapi import FastAPI, Request
from fastapi.responses import Response
from pydantic import BaseModel
import os
import boto3
import redis
from fastapi.middleware.cors import CORSMiddleware

origins = [
    "http://localhost",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

r = redis.Redis(host='localhost', port=6379, db=0)

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET")
)

@app.get('/status/')
def check_deploy_status(id : str):
    """
    This function is used to check the status of the deployment
    """
    unique_id = id
    # check if the bucket exists
    res = r.hget("deployment_status", unique_id)
    print(res)
    return {"msg" : res}



@app.get("/{full_path:path}")
def request_api(full_path : str, request : Request):
    """
    This function is used to get the files from the bucket
    and serve them to the browser
    """
    sub_host = request.headers["host"].split(".")[0]
    print(sub_host)
    bucket_name = f"bucket{sub_host}"

    # serve the files to the browser
    response = s3.get_object(Bucket=bucket_name, Key=f"build/{full_path}")
    contents = response["Body"].read()


    if full_path.endswith(".html"):
        content_type = "text/html"
    elif full_path.endswith(".css"):
        content_type = "text/css"
    elif full_path.endswith(".js"):
        content_type = "application/javascript"
    elif full_path.endswith(".png"):
        content_type = "image/png"
    elif full_path.endswith(".jpg") or full_path.endswith(".jpeg"):
        content_type = "image/jpeg"
    elif full_path.endswith(".gif"):
        content_type = "image/gif"
    elif full_path.endswith(".svg"):
        content_type = "image/svg+xml"
    else:
        content_type = "application/octet-stream"

    return Response(content=contents, media_type=content_type)
