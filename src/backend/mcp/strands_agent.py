
from strands import Agent, tool
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client
import argparse, json, boto3, logging, sys
from strands.models import BedrockModel

logger = logging.getLogger()
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
if not logger.handlers: logger.addHandler(console_handler)
for name in ['boto3', 'botocore']: logging.getLogger(name).setLevel(logging.WARNING); logging.getLogger(name).addHandler(console_handler)
for name in ['httpx', 'mcp', 'strands']: logging.getLogger(name).setLevel(logging.WARNING)


@tool
def search_sap_api_knowledge_base(query: str) -> str:
    """CRITICAL: Query OpenAPI schemas for exact SAP OData API URLs. MUST return complete URLs with hostname, service path, and parameters.
    
    MANDATORY: All URLs MUST use hostname: https://sap-workshop-720f09b6b2563946.events.sap.aws.dev
    
    Examples:
    - Sales Order: https://sap-workshop-720f09b6b2563946.events.sap.aws.dev/sap/opu/odata/sap/API_SALES_ORDER_SRV/A_SalesOrder('127')
    - Sales Order Items: https://sap-workshop-720f09b6b2563946.events.sap.aws.dev/sap/opu/odata/sap/API_SALES_ORDER_SRV/A_SalesOrder('127')/to_Item
    - GL Account filtered: https://sap-workshop-720f09b6b2563946.events.sap.aws.dev/sap/opu/odata/sap/API_GLACCOUNTLINEITEM/GLAccountLineItem?$filter=CompanyCode eq '1010' and IsReversal eq true
    
    NEVER fabricate URLs. ONLY use exact paths from OpenAPI schema.
    """
    response = boto3.client('bedrock-agent-runtime', region_name='us-east-1').retrieve(knowledgeBaseId="M6GBMOSKQX", retrievalQuery={'text': query})
    results = [result.get('content', {}).get('text', '') for result in response.get('retrievalResults', []) if result.get('content', {}).get('text', '')]
    return '\n\n'.join(results) if results else "No relevant information found in knowledge base."
    


@tool
def search_sap_sops(query: str) -> str:
    """CRITICAL: Query SAP Standard Operating Procedures for process exceptions and resolution steps.
    
    MUST return: Exception identification criteria and exact resolution steps as OData API actions.
    
    NEVER invent exceptions or resolutions. ONLY return documented procedures from knowledge base.
    """
    response = boto3.client('bedrock-agent-runtime', region_name='us-east-1').retrieve(knowledgeBaseId="HRQMR9REUC", retrievalQuery={'text': query})
    results = [result.get('content', {}).get('text', '') for result in response.get('retrievalResults', []) if result.get('content', {}).get('text', '')]
    return '\n\n'.join(results) if results else "No relevant information found in knowledge base."



mcp_client = MCPClient(lambda: streamablehttp_client("http://localhost:8000/mcp"))
model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0")

def strands_agent_bedrock(payload):
    user_input = payload.get("prompt")
    logger.info(f"User input: {user_input}")
    with mcp_client:
        agent = Agent(model=model, tools=[*mcp_client.list_tools_sync(), search_sap_api_knowledge_base, search_sap_sops], system_prompt="MANDATORY WORKFLOW: 1) Use search_sap_sops to understand process context and exceptions. 2) Use search_sap_api_knowledge_base to get exact OData URLs. 3) Execute URLs via MCP tools. 4) Chain API calls passing parameters between them. CRITICAL: For Sales Orders, ALWAYS call A_SalesOrder header first to get details before calling related entities (to_Item, to_Partner, to_ScheduleLine). Relationships: Header(1):Item(many), Item(1):Partner(many), Item(1):ScheduleLine(many). NEVER skip header call when only order number provided.")
        return agent(user_input).message['content'][0]['text']

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=str)
    args = parser.parse_args()
    payload = json.loads(args.payload)
    response = strands_agent_bedrock(payload)
    