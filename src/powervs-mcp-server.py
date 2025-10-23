import logging
import os
import yaml
# install fastmcp
from fastmcp import FastMCP
from powervs_client import PowerVSClient


mcp = FastMCP("PowerVS MCP Server")

# Set up logging
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)


def load_config():
    """Load config from YAML file if environment variables are missing."""
    config_file = "config.yaml"
    if os.path.exists(config_file):
        print("MBM configuration file exists")
        try:
            with open(config_file, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load {config_file}: {e}")
    else:
        print("MBM unable to find the configuration file")
    return {}

# Load environment variables first, else fallback to config.yaml
_config = load_config()

# Initialize PowerVS client
powervs_client = PowerVSClient()

print("=== PowerVS Configuration ===")
print(f"Base URL: {powervs_client.base_url}")
print(f"Cloud Instance ID: {powervs_client.cloud_instance_id}")
print(f"Account ID: {powervs_client.account_id}")



@mcp.tool()
async def fetch_powervs_vms():
    """List all the Virtual machines from PowerVS."""
    return powervs_client.get_all_vms()


@mcp.tool()
async def fetch_powervs_vms_by_health_status(health_status: str):
    """
    Get Power VS virtual machines filtered by their health status (OK, CRITICAL, ERROR, WARNING, UNKNOWN)
    """
    return powervs_client.fetch_vms_by_health_status(health_status)


@mcp.tool()
async def fetch_powervs_critical_vms():
    """
    Get all Power VS virtual machines in CRITICAL health state
    """
    return powervs_client.get_critical_vms()


@mcp.tool()
async def fetch_powervs_all_workspaces():
    """
    Get all Power VS workspaces for the tenant
    """
    return powervs_client.get_all_workspaces()


#@mcp.tool()
async def fetch_powervs_vms_from_all_workspaces():
    """
    Get all Power VS virtual machines across all the workspaces for a tenant provided
    """
    return powervs_client.fetch_vms_from_all_workspaces()


@mcp.tool()
async def fetch_powervs_vm_network_health(vm_id: str):
    """
    Get network interface health informtion for a Power VS VM instance
    """
    return powervs_client.get_network_health(vm_id)


@mcp.tool()
async def fetch_powervs_vm_storage_health(vm_id: str):
    """
    Get storage health data for a Power VS VM instance
    """
    return powervs_client.get_storage_health(vm_id)


@mcp.tool()
async def fetch_powervs_vm_health(vm_id: str):
    """
    Get complete health details of Power VS VM including storage and network
    """
    return powervs_client.get_vm_health(vm_id)


@mcp.tool()
async def fetch_powervs_all_images():
    """
    Get all available Power VS images in the workspace
    """
    return powervs_client.get_all_images_in_workspace()


@mcp.tool()
async def fetch_powervs_image_details(image_id: str):
    """
    Get detailed information for a Power VS specific image
    """
    return powervs_client.get_image_details(image_id)


@mcp.tool()
async def fetch_powervs_all_networks():
    """
    Get all networks in the Power VS workspace
    """
    return powervs_client.get_networks_in_workspace()


@mcp.tool()
async def fetch_powervs_vm_snapshots(vm_id: str):
    """
    Get all snapshots for a Power VS VM
    """
    return powervs_client.get_vm_snapshots(vm_id)


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8002)
