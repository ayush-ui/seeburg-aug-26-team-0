import boto3
import json
import os
import time
from boto3.session import Session

# Initialize AWS session with region from environment variable
region = os.environ.get('AWS_REGION', 'us-east-1')
boto_session = Session(region_name=region)
print(f"Using AWS region: {region}")

# Create Cognito User Pool
cognito_client = boto3.client('cognito-idp', region_name=region)

# Create user pool with OAuth2 support 
user_pool_response = cognito_client.create_user_pool(
    PoolName='sap-mcp-user-pool-m2m-' + str(int(time.time())),
    Policies={
        'PasswordPolicy': {
            'MinimumLength': 8,
            'RequireUppercase': True,
            'RequireLowercase': True,
            'RequireNumbers': True,
            'RequireSymbols': True,
            'TemporaryPasswordValidityDays': 7
        },
        'SignInPolicy': {
            'AllowedFirstAuthFactors': ['PASSWORD']
        }
    },
    DeletionProtection='INACTIVE',
    MfaConfiguration='OFF',
    EmailConfiguration={
        'EmailSendingAccount': 'COGNITO_DEFAULT'
    },
    AdminCreateUserConfig={
        'AllowAdminCreateUserOnly': False
    },
    AccountRecoverySetting={
        'RecoveryMechanisms': [
            {'Priority': 1, 'Name': 'verified_email'},
            {'Priority': 2, 'Name': 'verified_phone_number'}
        ]
    },
    VerificationMessageTemplate={
        'DefaultEmailOption': 'CONFIRM_WITH_CODE'
    },
    UserAttributeUpdateSettings={
        'AttributesRequireVerificationBeforeUpdate': []
    }
)

user_pool_id = user_pool_response['UserPool']['Id']
print(f"Created User Pool: {user_pool_id}")

# Create resource server with read and write scopes 
timestamp = str(int(time.time()))
resource_server_response = cognito_client.create_resource_server(
    UserPoolId=user_pool_id,
    Identifier=f'sap-mcp-m2m-resource-server-{timestamp}',
    Name='M2M Resource Server',
    Scopes=[
        {
            'ScopeName': 'read',
            'ScopeDescription': 'Read access for M2M clients'
        },
        {
            'ScopeName': 'write',
            'ScopeDescription': 'Write access for M2M clients'
        }
    ]
)
resource_server_id = resource_server_response['ResourceServer']['Identifier']
print(f"Created Resource Server: {resource_server_id}")

# Create user pool domain for OAuth2 endpoints
domain_name = f"sap-strands-m2m-{timestamp}"
try:
    cognito_client.create_user_pool_domain(
        Domain=domain_name,
        UserPoolId=user_pool_id
    )
    print(f"Created User Pool Domain: {domain_name}")
except cognito_client.exceptions.InvalidParameterException as e:
    if "already exists" in str(e):
        print(f"Domain {domain_name} already exists")
    else:
        raise

# Create client for client credentials flow 
client_credentials_response = cognito_client.create_user_pool_client(
    UserPoolId=user_pool_id,
    ClientName=f'sap-mcp-m2m-client-{timestamp}',
    GenerateSecret=True,
    RefreshTokenValidity=30,
    ExplicitAuthFlows=['ALLOW_REFRESH_TOKEN_AUTH'],
    SupportedIdentityProviders=['COGNITO'],
    CallbackURLs=['https://bedrock-agentcore.us-east-1.amazonaws.com/identities/oauth2/callback'],
    AllowedOAuthFlows=['client_credentials'],
    AllowedOAuthScopes=[f'{resource_server_id}/read', f'{resource_server_id}/write'],
    AllowedOAuthFlowsUserPoolClient=True,
    EnableTokenRevocation=True,
    EnablePropagateAdditionalUserContextData=False,
    AuthSessionValidity=3
)

client_credentials_id = client_credentials_response['UserPoolClient']['ClientId']
client_credentials_secret = client_credentials_response['UserPoolClient']['ClientSecret']
print(f"Created Client Credentials Client: {client_credentials_id}")

# OAuth2 endpoints
oauth2_domain = f"https://{domain_name}.auth.{region}.amazoncognito.com"
token_endpoint = f"{oauth2_domain}/oauth2/token"
authorize_endpoint = f"{oauth2_domain}/oauth2/authorize"
discovery_url = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration"

# Store OAuth2 configuration in Secrets Manager
oauth2_config = {
    'user_pool_id': user_pool_id,
    'resource_server_id': resource_server_id,
    'client_credentials_id': client_credentials_id,
    'client_credentials_secret': client_credentials_secret,
    'region': region,
    'domain': oauth2_domain,
    'token_endpoint': token_endpoint,
    'authorize_endpoint': authorize_endpoint,
    'discovery_url': discovery_url
}

secrets_client = boto3.client('secretsmanager', region_name=region)
try:
    secrets_client.create_secret(
        Name='sap_mcp_server/cognito/oauth2_config',
        Description='OAuth2 Cognito configuration for SAP MCP server',
        SecretString=json.dumps(oauth2_config)
    )
    print("✓ OAuth2 configuration stored in Secrets Manager")
except secrets_client.exceptions.ResourceExistsException:
    secrets_client.update_secret(
        SecretId='sap_mcp_server/cognito/oauth2_config',
        SecretString=json.dumps(oauth2_config)
    )
    print("✓ OAuth2 configuration updated in Secrets Manager")

print(f"✓ OAuth2 Setup complete!")
print(f"✓ User Pool ID: {user_pool_id}")
print(f"✓ Resource Server ID: {resource_server_id}")
print(f"✓ Client ID (Client Credentials): {client_credentials_id}")
print(f"✓ OAuth2 Domain: {oauth2_domain}")
print(f"✓ Token Endpoint: {token_endpoint}")
print(f"✓ Authorize Endpoint: {authorize_endpoint}")
print(f"\nTest with:")
print(f"curl -X POST {token_endpoint} \\")
print(f"  -H 'Content-Type: application/x-www-form-urlencoded' \\")
print(f"  -d 'grant_type=client_credentials&client_id={client_credentials_id}&client_secret={client_credentials_secret}&scope={resource_server_id}/read'")