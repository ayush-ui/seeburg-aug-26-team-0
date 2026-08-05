try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from fastmcp import FastMCP
from starlette.responses import JSONResponse
import logging
import requests
import base64
import json
import sys
from requests.exceptions import RequestException
import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(console_handler)

# Configure requests logging
requests_logger = logging.getLogger('requests')
requests_logger.setLevel(logging.INFO)
requests_logger.addHandler(console_handler)

# Initialize FastMCP with stateless_http=True for AgentCore Runtime compatibility
mcp = FastMCP(host="0.0.0.0", stateless_http=True)

def get_csrf_token(api_endpoint: str, auth_b64: str) -> tuple:
    """Get CSRF token and cookies for SAP OData API calls"""
    parts = api_endpoint.split('/')
    base_path = '/'.join(parts[:8]) + '/'
    headers = {
        'x-csrf-token': 'Fetch', 
        'Accept': 'application/json', 
        'Authorization': f'Basic {auth_b64}', 
        'Content-Type': 'application/json'
    }
    logger.info("Attempting to fetch CSRF token...")
    response = requests.get(base_path, headers=headers, timeout=30)
    logger.info(f"CSRF token response status: {response.status_code}")
    csrf_token = response.headers.get('x-csrf-token')
    cookie_dict = requests.utils.dict_from_cookiejar(response.cookies)
    logger.info("Successfully retrieved CSRF token and cookies")
    return csrf_token, cookie_dict

def get_credentials():
    """Retrieve SAP credentials from AWS Secrets Manager"""
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId='sap-s4h-credentials')
    return json.loads(response['SecretString'])

@mcp.tool()
def invoke_sap_odata_service(odata_api_url: str, http_method: str = "GET", request_body: str = None) -> str:
    """This tool calls the SAP OData API URL with specified HTTP method and optional request body
    
    Args:
        odata_api_url: The complete SAP OData API URL
        http_method: HTTP method (GET, POST, PUT, PATCH, DELETE)
        request_body: JSON string for POST/PUT/PATCH requests
    """
    logger.info(f"Invoking SAP OData service: {http_method} {odata_api_url}")
    http_method = http_method.upper()
    
    # Get credentials from AWS Secrets Manager
    creds = get_credentials()
    username = creds['username']
    password = creds['password']
    
    # Prepare authentication
    auth_string = f"{username}:{password}"
    auth_bytes = auth_string.encode('ascii')
    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
    
    # Get CSRF token and cookies
    csrf_token, cookie_dict = get_csrf_token(odata_api_url, auth_b64)
    
    # Prepare headers
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'x-csrf-token': csrf_token,
        'Authorization': f'Basic {auth_b64}'
    }
    
    # Add cookies if available
    if cookie_dict:
        cookie_string = '; '.join([f"{name}={value}" for name, value in cookie_dict.items()])
        headers['Cookie'] = cookie_string
    
    logger.info(f"Making {http_method} request to {odata_api_url}")
    logger.info(f"Headers: {headers}")
    if request_body:
        logger.info(f"Request body: {request_body}")
    
    # Make the API call
    response = requests.request(
        method=http_method,
        url=odata_api_url,
        headers=headers,
        data=request_body if request_body else None,
        timeout=30,
        verify=True
    )
    
    logger.info(f"Response status code: {response.status_code}")
    logger.info(f"Response headers: {response.headers}")
    
    if response.content:
        try:
            data = response.json()
            return json.dumps(data, indent=2)
        except json.JSONDecodeError:
            return response.text
    else:
        return f"Request successful. Status: {response.status_code}"

if __name__ == "__main__":
    # Run with streamable-http transport for AgentCore Runtime
    mcp.run(transport="streamable-http")