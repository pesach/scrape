import os
from dotenv import load_dotenv
import boto3

load_dotenv()

session = boto3.session.Session()
s3 = session.client(
    service_name='s3',
    endpoint_url=os.getenv("B2_ENDPOINT_URL"),
    aws_access_key_id=os.getenv("B2_APPLICATION_KEY_ID"),
    aws_secret_access_key=os.getenv("B2_APPLICATION_KEY"),
)

bucket = os.getenv("B2_BUCKET_NAME")

response = s3.list_objects_v2(Bucket=bucket)
for obj in response.get("Contents", []):
    key = obj["Key"]
    url = f"{os.getenv('B2_ENDPOINT_URL')}/{bucket}/{key}"
    print(url)
