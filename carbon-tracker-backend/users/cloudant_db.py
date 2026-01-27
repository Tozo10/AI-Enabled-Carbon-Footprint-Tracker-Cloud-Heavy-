from ibmcloudant.cloudant_v1 import CloudantV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from decouple import config

def get_cloudant_client():
    """
    Returns an authenticated Cloudant client.
    """
    # Load credentials from .env
    api_key = config("CLOUDANT_APIKEY")
    url = config("CLOUDANT_URL")
    
    # Connect to IBM Cloud using IAM Authentication
    authenticator = IAMAuthenticator(api_key)
    client = CloudantV1(authenticator=authenticator)
    client.set_service_url(url)
    return client

def save_activity_log(data):
    """
    Saves a dictionary (JSON) to the 'activity-logs' database in Cloudant.
    """
    client = get_cloudant_client()
    db_name = "activity-logs"
    
    # Check if DB exists, if not create it (safe to run every time)
    try:
        # Try to get info about the DB to see if it exists
        client.get_database_information(db=db_name).get_result()
    except:
        print(f"Database {db_name} not found. Creating it...")
        client.put_database(db=db_name).get_result()
    
    # Save the document
    response = client.post_document(
        db=db_name,
        document=data
    ).get_result()
    
    return response

def get_user_logs_cloudant(username):
    """
    Fetches all activity logs for a specific username from Cloudant.
    """
    client = get_cloudant_client()
    db_name = "activity-logs"
    
    try:
        selector = {"username": {"$eq": username}}
        result = client.post_find(
            db=db_name,
            selector=selector
        ).get_result()
        return result['docs']
    except Exception as e:
        print(f"Error fetching logs from Cloudant: {e}")
        return []