import boto3
import json
import os
import requests

def test_deployed_mcp_server():
    # Use region from environment variable
    region = os.environ.get('AWS_REGION', 'us-east-1')
    print(f"Using AWS region: {region}")
    
    try:
        # Get stored configuration
        ssm_client = boto3.client('ssm', region_name=region)
        secrets_client = boto3.client('secretsmanager', region_name=region)
        
        # Get Agent ARN
        agent_arn_response = ssm_client.get_parameter(Name='/sap_mcp_server/runtime/agent_arn')
        agent_arn = agent_arn_response['Parameter']['Value']
        print(f"✓ Retrieved Agent ARN: {agent_arn}")
        
        # Get OAuth2 Cognito configuration
        response = secrets_client.get_secret_value(SecretId='sap_mcp_server/cognito/oauth2_config')
        cognito_config = json.loads(response['SecretString'])
        print("✓ Retrieved OAuth2 Cognito configuration")
        
        # Get OAuth2 token using client credentials flow
        token_data = {
            'grant_type': 'client_credentials',
            'client_id': cognito_config['client_credentials_id'],
            'client_secret': cognito_config['client_credentials_secret'],
            'scope': f"{cognito_config['resource_server_id']}/read {cognito_config['resource_server_id']}/write"
        }
        
        token_response = requests.post(
            cognito_config['token_endpoint'],
            data=token_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        if token_response.status_code != 200:
            raise Exception(f"OAuth2 token request failed: {token_response.text}")
            
        bearer_token = token_response.json()['access_token']
        print("✓ Successfully obtained OAuth2 token")
        
        # Construct MCP URL
        encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
        mcp_url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
        
        headers = {
            "authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        print(f"🔄 Testing connection to: {mcp_url}")
        
        # Test with proper MCP JSON-RPC format
        test_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "invoke_sap_odata_service",
                "arguments": {
                    "odata_api_url": "https://YOUR-SAP-HOSTNAME/sap/opu/odata/sap/API_SUPPLIERINVOICE_PROCESS_SRV/A_SupplierInvoice(SupplierInvoice='5100000092',FiscalYear='2017')?$expand=to_SuplrInvcItemPurOrdRef",
                    "http_method": "GET"
                }
            }
        }

        response = requests.post(
            mcp_url,
            headers=headers,
            json=test_payload,
            timeout=30
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing MCP server: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_deployed_mcp_server()