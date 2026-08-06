from bedrock_agentcore_starter_toolkit import Runtime
from boto3.session import Session
import boto3
import json
import os

# Use region from environment variable (pre-configured in VS Code)
region = os.environ.get('AWS_REGION', 'us-east-1')
boto_session = Session(region_name=region)
print(f"Using AWS region: {region}")

# Get OAuth2 Cognito configuration from Secrets Manager (stored by setup_cognito_oauth2.py)
secrets_client = boto3.client('secretsmanager', region_name=region)
try:
    response = secrets_client.get_secret_value(SecretId='sap_mcp_server/cognito/oauth2_config')
    cognito_config = json.loads(response['SecretString'])
    print("✓ Retrieved OAuth2 Cognito configuration from Secrets Manager")
except Exception as e:
    print(f"❌ Error retrieving OAuth2 Cognito config: {e}")
    exit(1)

# Initialize AgentCore Runtime with fresh state
runtime = Runtime()

# Use a unique agent name to avoid conflicts
import time
agent_name = f"sap_mcp_server_{int(time.time())}"
print(f"Creating new agent: {agent_name}")

# Configure authentication
auth_config = {
    "customJWTAuthorizer": {
        "allowedClients": [cognito_config['client_credentials_id']],
        "discoveryUrl": cognito_config['discovery_url'],
    }
}

# Do not print `cognito_config` - it carries client_credentials_secret.
print(f"Using Cognito client: {cognito_config['client_credentials_id']}")

print("Configuring AgentCore Runtime...")
response = runtime.configure(
    entrypoint="sap_mcp_server.py",
    auto_create_execution_role=True,
    auto_create_ecr=True,
    requirements_file="requirements.txt",
    region=region,
    authorizer_configuration=auth_config,
    protocol="MCP",
    agent_name=agent_name
)
print("Configuration completed ✓")

# Launch MCP Server to AgentCore Runtime
print("Launching SAP MCP server to AgentCore Runtime...")
print("This may take several minutes...")
launch_result = runtime.launch()
print("Launch completed ✓")
print(f"Agent ARN: {launch_result.agent_arn}")
print(f"Agent ID: {launch_result.agent_id}")

# Check Deployment Status
import time

status_response = runtime.status()
status = status_response.endpoint['status']
end_status = ['READY', 'CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED']

while status not in end_status:
    time.sleep(10)
    status_response = runtime.status()
    status = status_response.endpoint['status']
    print(f"Status: {status}")

print(f"Final Status: {status}")

# Store Agent ARN for Task 02
ssm_client = boto3.client('ssm', region_name=region)
ssm_client.put_parameter(
    Name='/sap_mcp_server/runtime/agent_arn',
    Value=launch_result.agent_arn,
    Type='String',
    Description='Agent ARN for SAP MCP server',
    Overwrite=True
)

print("✓ Agent ARN stored in Parameter Store")
print(f"Agent ARN: {launch_result.agent_arn}")
print("✓ Deployment completed successfully!")