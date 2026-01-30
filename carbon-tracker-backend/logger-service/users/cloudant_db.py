from ibmcloudant.cloudant_v1 import CloudantV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_cloud_sdk_core.api_exception import ApiException
from decouple import config

def get_cloudant_client():
    """
    Returns an authenticated Cloudant client using credentials from .env.
    """
    api_key = config("CLOUDANT_APIKEY", default=None)
    url = config("CLOUDANT_URL", default=None)

    if not api_key or not url:
        print("CRITICAL: CLOUDANT_APIKEY or CLOUDANT_URL is missing in .env")
        return None
    
    try:
        # Connect to IBM Cloud using IAM Authentication
        authenticator = IAMAuthenticator(api_key)
        client = CloudantV1(authenticator=authenticator)
        client.set_service_url(url)
        return client
    except Exception as e:
        print(f"Error initializing Cloudant client: {e}")
        return None

def save_activity_log(data):
    """
    Saves a dictionary (JSON) to the 'activity-logs' database in Cloudant.
    """
    client = get_cloudant_client()
    if not client:
        return False

    db_name = "activity-logs"
    
    # Check if DB exists, if not create it
    try:
        client.get_database_information(db=db_name).get_result()
    except ApiException as ae:
        if ae.code == 404:
            print(f"Database '{db_name}' not found. Creating it...")
            try:
                client.put_database(db=db_name).get_result()
            except ApiException as creation_error:
                print(f"Error creating database: {creation_error}")
                return False
        else:
            print(f"Error checking database: {ae}")
            return False
    
    # Save the document
    try:
        print(f"DEBUG: Saving log for {data.get('username')} to Cloudant...")
        response = client.post_document(
            db=db_name,
            document=data
        ).get_result()
        
        if response.get('ok'):
            print("DEBUG: Successfully saved to Cloudant.")
            return True
        else:
            print("DEBUG: Cloudant accepted request but returned 'not ok'.")
            return False

    except ApiException as e:
        print(f"CRITICAL CLOUDANT ERROR: {e}")
        return False

def get_user_logs_cloudant(username):
    """
    Fetches all activity logs for a specific username from Cloudant.
    """
    client = get_cloudant_client()
    if not client:
        return []

    db_name = "activity-logs"
    
    try:
        print(f"DEBUG: Fetching logs for '{username}' from Cloudant...")
        
        # Cloudant Query (Mango Query)
        selector = {"username": {"$eq": username}}
        
        result = client.post_find(
            db=db_name,
            selector=selector,
            limit=100  # Limit to 100 most recent logs for performance
        ).get_result()
        
        docs = result.get('docs', [])
        print(f"DEBUG: Found {len(docs)} logs in Cloudant.")
        return docs

    except ApiException as e:
        if e.code == 404:
            print(f"DEBUG: Database '{db_name}' does not exist yet (No logs).")
            return []
        print(f"Error fetching logs from Cloudant: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []
    