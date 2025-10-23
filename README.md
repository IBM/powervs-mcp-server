# IBM Power Virtual Server MCP (Model Context Protocol) Server
This repository is an example MCP (Model Context Protocol) server for IBM Power Virtual Server.

> **DISCLAIMER**: This is a sample MCP server for reference and is not officially affiliated with, endorsed by, or supported by IBM. This MCP server utilizes the [IBM Power Virtual Server](https://www.ibm.com/products/power-virtual-server) External APIs.

This open-sourced Model Context Protocol (MCP) server will help [IBM Power Virtual Server](https://www.ibm.com/products/power-virtual-server)  to integrate in the Agentic-AI ecosystem. It will help users to bring their AI-Agents for seamless observability and diagnosis of their virtual machines registered with [IBM Power Virtual Server](https://www.ibm.com/products/power-virtual-server) .

## 🚀 Features

- **Observability Tools**: Leverage key [IBM Power Virtual Server](https://www.ibm.com/products/power-virtual-server) monitoring capabilities via an MCP interface.
- **Extensible Design**: Easily integrate additional Power Virtual Server APIs for future expansions.
- **Pythonic**: Allowing ease of use and extension for AI developers

## 🛠️ Tools
Listed below are the tools which are presently exposed thought the MCP server:
### 1. `fetch_powervs_vms`

   - **Description**: List all the Virtual machines from PowerVS.
   - **Returns**: List all the virtual machines across all the workspaces and across data centers registered with the IBM account.

### 2. `fetch_powervs_vms_by_health_status`

   - **Description**: Get Power VS virtual machines filtered by their health status.
   - **Inputs**:
     - `health_status`: The probable health status are OK, CRITICAL, ERROR, WARNING, UNKNOWN.
   - **Returns**: List all the virtual machines across all the workspaces and across data centers notifications filtered by health status.

### 3. `fetch_powervs_critical_vms`

   - **Description**: Get all Power VS virtual machines in CRITICAL health state.
   - **Returns**: List all the virtual machines across all the workspaces and across data centers notifications in CRITICAL health state.

### 4. `fetch_powervs_all_workspaces`

   - **Description**: Get all Power VS workspaces for the tenant.
   - **Returns**: List all the workspaces across all the data centers registered with the IBM account.

### 5. `fetch_powervs_vm_network_health`

   - **Description**: Get network interface health informtion for a Power VS VM instance.
   - **Inputs**:
     - `vm_id` *(string)*: Unique system id for the virtual server.
   - **Returns**: Details of network health of a virtual server.

### 6. `fetch_powervs_vm_storage_health`

   - **Description**: Get storage health data for a Power VS VM instance.  
   - **Inputs**:
     - `vm_id` *(string)*: Unique system id for the virtual server.
   - **Returns**: Details of storage health of a virtual server.

### 7. `fetch_powervs_vm_health`

   - **Description**: Get complete health details of Power VS VM including storage and network.  
   - **Inputs**:
     - `vm_id` *(string)*: Unique system id for the virtual server.
   - **Returns**: Details of holistic health of a virtual server that includes storage and network.
    
### 8. `fetch_powervs_all_images`

   - **Description**: Get all available Power VS images in the workspace.
   - **Returns**: List all Power VS images within a workspace, do pass CRN to fetch this information.

### 9. `fetch_powervs_image_details`

   - **Description**: Get detailed information for a Power VS specific image.  
   - **Inputs**:
     - `image_id` *(string)*: Unique system id for the Power VS image.
   - **Returns**: Details of the Power VS image.

### 10. `fetch_powervs_all_networks`

   - **Description**: Get all networks in the Power VS workspace.
   - **Returns**: List all networks of a Power VS workspace, do pass CRN to fetch this information.

### 11. `fetch_powervs_vm_snapshots`

   - **Description**: Get all snapshots for a Power VS VM.  
   - **Inputs**:
      - `vm_id` *(string)*: Unique system id for the virtual server.
   - **Returns**: List all the snapshots of a specifed VM.

## 🧪 Setup

### Set up your environment
### Step 1: Build the container image:
```podman build -t powervs_mcp_server:latest -f Containerfile .```

### Step 2: Run the container:
You need to pass ACCOUNT_ID and API_KEY as mandatory attribute and CRN (workspace CRN) would be optional used only if needed to target a specific PowerVS workspace. This can either be set inside the config.yaml or pass it as runtime environment variables to podman or docker container
```
podman run -d --name powervs_mcp_server \
-p 8002:8002 \
-e ACCOUNT_ID=<POWERVS_ACCOUNT_ID> \
-e API_KEY=<POWERVS_API_KEY> \
-e CRN=<CRN>
localhost/powervs_mcp_server
```
You could also override default 8002 port by passing ```USER_DEFINED_PORT```:
```
podman run -d --name powervs_mcp_server \
-p <PORT_ON_HOST>:<USER_DEFINED_PORT> \
-e MCP_SERVER_PORT=<USER_DEFINED_PORT>
-e ACCOUNT_ID=<POWERVS_ACCOUNT_ID> \
-e API_KEY=<POWERVS_API_KEY> \
-e CRN=<CRN>
localhost/powervs_mcp_server
```
### IBM Power VS Credentials

Tools in this MCP Server invokes [IBM Power VS APIs](https://cloud.ibm.com/apidocs/power-cloud) APIs and hence needs API key for a working setup. Refer [Generating a IBM Cloud API Key](https://cloud.ibm.com/docs/account?topic=account-userapikey&interface=ui#create_user_key) to generate REST API key for your tenant / account ID. 

Add below values to `src/config.yaml` file:

```yaml
account_id: <IBM Cloud tentant or account ID>
api_key: <IBM Cloud API Key>
base_url: <Serivce broker URL>
crn: <IBM Power VS CRN of workspace that needs to be targeted>
```

## 🖥️ Usage with Langchain MCP Client

Here is the MCP client configuration details:

```json
{
    "powervsserver": {
        "transport": "streamable_http",
        "url": "http://127.0.0.1:8002/mcp",
    }
}
```

## 🐞 Testing and Debugging

We recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) for testing and debugging. You can run the inspector with:

   ```bash
   npx @modelcontextprotocol/inspector
   ```
   The inspector will provide a URL you can open in your browser to see logs and send requests manually.



## 📄 License

This project is licensed under the [Apache License, Version 2.0](./LICENSE).
