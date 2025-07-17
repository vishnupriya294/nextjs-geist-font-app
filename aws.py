import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AWSIntegration:
    def __init__(self):
        self.s3_client = None
        self.dynamodb = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize AWS clients with error handling"""
        try:
            # Initialize S3 client
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
            )
            
            # Initialize DynamoDB resource
            self.dynamodb = boto3.resource(
                'dynamodb',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
            )
            
            logger.info("AWS clients initialized successfully")
            
        except NoCredentialsError:
            logger.warning("AWS credentials not found. AWS features will be disabled.")
        except Exception as e:
            logger.error(f"Error initializing AWS clients: {e}")
    
    def upload_file_to_s3(self, file_path, bucket_name, object_name=None):
        """Upload a file to S3 bucket"""
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return False
        
        if object_name is None:
            object_name = os.path.basename(file_path)
        
        try:
            self.s3_client.upload_file(file_path, bucket_name, object_name)
            logger.info(f"File {file_path} uploaded to {bucket_name}/{object_name}")
            return True
        except FileNotFoundError:
            logger.error(f"File {file_path} not found")
            return False
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            return False
    
    def download_file_from_s3(self, bucket_name, object_name, file_path):
        """Download a file from S3 bucket"""
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return False
        
        try:
            self.s3_client.download_file(bucket_name, object_name, file_path)
            logger.info(f"File downloaded from {bucket_name}/{object_name} to {file_path}")
            return True
        except ClientError as e:
            logger.error(f"Error downloading file from S3: {e}")
            return False
    
    def store_user_data_dynamodb(self, table_name, user_data):
        """Store user data in DynamoDB"""
        if not self.dynamodb:
            logger.error("DynamoDB client not initialized")
            return False
        
        try:
            table = self.dynamodb.Table(table_name)
            response = table.put_item(Item=user_data)
            logger.info(f"User data stored in DynamoDB table {table_name}")
            return True
        except ClientError as e:
            logger.error(f"Error storing data in DynamoDB: {e}")
            return False
    
    def get_user_data_dynamodb(self, table_name, user_id):
        """Retrieve user data from DynamoDB"""
        if not self.dynamodb:
            logger.error("DynamoDB client not initialized")
            return None
        
        try:
            table = self.dynamodb.Table(table_name)
            response = table.get_item(Key={'user_id': user_id})
            return response.get('Item')
        except ClientError as e:
            logger.error(f"Error retrieving data from DynamoDB: {e}")
            return None

# Global AWS integration instance
aws_integration = AWSIntegration()

# Convenience functions
def upload_to_s3(file_path, bucket_name, object_name=None):
    return aws_integration.upload_file_to_s3(file_path, bucket_name, object_name)

def download_from_s3(bucket_name, object_name, file_path):
    return aws_integration.download_file_from_s3(bucket_name, object_name, file_path)

def store_user_data(table_name, user_data):
    return aws_integration.store_user_data_dynamodb(table_name, user_data)

def get_user_data(table_name, user_id):
    return aws_integration.get_user_data_dynamodb(table_name, user_id)
