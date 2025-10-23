import requests
import logging
import os
import yaml
import time

logger = logging.getLogger(__name__)

WORKSPACE_CACHE_TTL = 1800
VM_CACHE_TTL = 300


class PowerVSClient:

    def __init__(self):
        # Load config from YAML file if environment variables are missing
        config = self._load_config()

        self.api_key = os.getenv("API_KEY", config.get("api_key", ""))
        self.account_id = os.getenv("ACCOUNT_ID", config.get("account_id", ""))
        self.base_url = os.getenv("BASE_URL", config.get("base_url", ""))

        if not self.api_key or not self.account_id:
            raise ValueError("API_KEY and ACCOUNT_ID are required")
        
        # Take CRN if it's provided
        self.crn = os.getenv("CRN", config.get("crn", ""))
        # Extract cloud instance id from CRN
        self.cloud_instance_id = self._extract_cloud_instance_id_from_crn() if self.crn else ""
        
        # List of all workspace objects
        self._workspaces = None
        # Timestamp when workspace data is cached
        self._workspaces_time = None
        
        # Mapping of VM to corresponding workspaces
        self._vm_workspace = {}
        # Timestamp when VM to workspace mapping is cached
        self._vm_workspace_time = None
        
    def _load_config(self):
        """Load config from YAML file if environment variables are missing."""
        config_file = os.path.join(os.path.dirname(__file__), "config.yaml")
        print(config_file)
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


    def _get_headers(self, workspace_crn=None):
        """
        Get headers for API calls
        """
        token = self.get_iam_token()
        if not token:
            return None

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if workspace_crn:
            headers["CRN"] = workspace_crn

        return headers

    def _extract_cloud_instance_id_from_crn(self):
        """
        Extract the cloud instance ID from CRN
        """
        if not self.crn:
            return ""
        try:
            parts = self.crn.split(':')
            return parts[7] if len(parts) >= 8 else ""
        except:
            return ""
    
    def _extract_workspace_from_crn(self, crn):
        """
        Extract the workspace details from CRN
        """
        if not crn:
            return None
        try:
            parts = crn.split(':')
            if len(parts) >= 8:
                return {
                    'workspace_id': parts[7],
                    'region': parts[5]
                }
        except:
            pass
        return None
    
    def _get_workspace_for_vm(self, vm_id):
        """
        Get the workspace details for a VM
        """
        # Check if VM cache expired and refresh if needed
        if self._vm_workspace_time:
            age = time.time() - self._vm_workspace_time
            if age > VM_CACHE_TTL:
                logger.info(f"VM cache expired ({age:.0f}s old) | Refreshing the data")
                self.fetch_vms_from_all_workspaces()
        
        # First check for VM details in cache
        if vm_id in self._vm_workspace:
            ws = self._vm_workspace[vm_id]
            workspace_id = ws['workspace_id']
            region = ws['region']
            workspace_url = ws.get('url', self.base_url)
            workspace_crn = f"crn:v1:staging:public:power-iaas:{region}:a/{self.account_id}:{workspace_id}::"
            return workspace_id, workspace_crn, workspace_url
        
        # Return the crn and cloud instance id
        if self.crn and self.cloud_instance_id:
            return self.cloud_instance_id, self.crn, self.base_url
        
        return None, None, None
    
    def _fetch_vms_from_workspace(self, workspace_id, workspace_crn, workspace_url):
        """
        Fetch all VMs from a workspace
        """
        headers = self._get_headers(workspace_crn)
        if not headers:
            return None, "Failed to get headers"

        url = f"{workspace_url}/pcloud/v1/cloud-instances/{workspace_id}/pvm-instances"
        try:
            response = requests.get(url, headers=headers, timeout=240)
            if response.status_code == 200:
                return response.json(), None
            else:
                return None, f"HTTP {response.status_code}"
        except Exception as e:
            return None, str(e)

    def _build_vm_detail(self, pvm, workspace_info=None):
        """
        Build VM details
        """
        vm_detail = {
            "vmName": pvm.get("serverName"),
            "vmID": pvm.get("pvmInstanceID"),
            "operatingSystem": pvm.get("osType"),
            "systemType": pvm.get("sysType"),
            "vmStatus": pvm.get("status"),
            "health": pvm.get("health", {"status": "UNKNOWN"}),
            "crn": pvm.get("crn", "")
        }

        if workspace_info:
            vm_detail.update({
                "workspaceName": workspace_info.get("name"),
                "workspaceRegion": workspace_info.get("region"),
            })

        return vm_detail

    def get_iam_token(self):
        """Get Token"""
        url = "https://iam.cloud.ibm.com/identity/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        data = {
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": self.api_key
        }
        try:
            response = requests.post(
                url, headers=headers, data=data, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return "", e
        try:
            result = response.json()
            return result['access_token']
        except (ValueError, KeyError) as e:
            return "", e

    def get_all_vms(self):
        """
        Get all VMs
         - Return VMs from specific workspace if CRN is present
         - Return VMs from all workspaces if CRN is not present
        """
        if self.crn and self.cloud_instance_id:
            return self.fetch_vms_from_specific_workspace()
        else:
            return self.fetch_vms_from_all_workspaces()

    def fetch_vms_from_specific_workspace(self):
        """
        Get all VMs in the workspace
        """
        headers = self._get_headers(self.crn)
        if not headers:
            return []

        url = f"{self.base_url}/pcloud/v1/cloud-instances/{self.cloud_instance_id}/pvm-instances"
        print("REQUEST:")
        print(f"GET {url}")
        for k, v in headers.items():
            print(f"{k}: {v}")

        try:
            response = requests.get(url, headers=headers, timeout=120)
            responses = response.json()
            vm_list = []
            for pvm in responses['pvmInstances']:
                vm_detail = self._build_vm_detail(pvm)
                vm_list.append(vm_detail)
            print(vm_list)
            return vm_list
        except requests.RequestException as e:
            logger.error('Error occured while trying to query power VS ')
            logger.error(e.response)
            logger.exception(e.with_traceback)
            print("Request exception : ", e)
            return []
        except ValueError as e:  # JSON decoding error
            logger.error('Error occured while decoding Power VS response ')
            logger.exception(e.with_traceback)
            print("ValueError exception : ", e)
            return []

    def get_all_workspaces(self):
        """
        Fetch all workspaces in this account
        """
        # Check if cache exists and is not expired
        if self._workspaces is not None and self._workspaces_time:
            age = time.time() - self._workspaces_time
            if age <= WORKSPACE_CACHE_TTL:
                return self._workspaces
            logger.info(f"Workspace cache expired ({age:.0f}s old) | Refreshing the data.")
        
        # Return cached data if available
        if self._workspaces is not None and not self._workspaces_time:
            return self._workspaces
        
        # Make live API call, fetch the data and cache it
        headers = self._get_headers()
        if not headers:
            return []

        url = f"{self.base_url}/v1/workspaces"
        try:
            data = requests.get(url, headers=headers, timeout=120)
            response = data.json()
            workspace_list = []
            for workspace in response.get('workspaces', []):
                workspace_detail = {
                    "id": workspace.get("id"),
                    "name": workspace.get("name"),
                    "region": workspace.get("location", {}).get("region"),
                    "url": workspace.get("location", {}).get("url", self.base_url)
                }
                workspace_list.append(workspace_detail)
            
            # Cache the workspace data with timestamp
            self._workspaces = workspace_list
            self._workspaces_time = time.time()
            return workspace_list
        except Exception as e:
            logger.error(f"Failed to fetch workspaces: {e}")
            # Return existing cache data as fallback
            if self._workspaces is not None:
                logger.warning(f"Using existing workspace cache itself.")
                return self._workspaces
            return []

    def get_network_health(self, vm_id, vm_data=None):
        """
        Get health of network interfaces
        """
        workspace_id, workspace_crn, workspace_url = self._get_workspace_for_vm(vm_id)
        if not workspace_id:
            return {"error": "VM not found."}
        
        headers = self._get_headers(workspace_crn)
        if not headers:
            return {"error": "Failed to get headers"}

        if vm_data is None:
            vm_url = f"{workspace_url}/pcloud/v1/cloud-instances/{workspace_id}/pvm-instances/{vm_id}"
            vm_response = requests.get(vm_url, headers=headers, timeout=120)
            vm_data = vm_response.json()

        active_network_interfaces = []
        down_network_interfaces = []

        vm_networks = vm_data.get('networks', [])
        for network in vm_networks:
            network_id = network.get("networkID")
            nw_interface_url = f"{self.base_url}/v1/networks/{network_id}/network-interfaces"
            nw_interface_response = requests.get(
                nw_interface_url, headers=headers, timeout=120)
            nw_interface_data = nw_interface_response.json()

            for interface in nw_interface_data.get('networkInterfaces', []):
                if interface.get('pvmInstance', {}).get('pvmInstanceID') == vm_id:
                    if interface.get('status') == 'ACTIVE':
                        active_network_interfaces.append(
                            interface.get('ipAddress'))
                    else:
                        down_network_interfaces.append(
                            interface.get('ipAddress'))

        return {
            "network_health": {
                "status": "OK" if len(down_network_interfaces) == 0 else "CRITICAL"
            },
            "interfaces_down": down_network_interfaces
        }

    def get_storage_health(self, vm_id):
        """
        Get storage health based on health of attached volumes
        """
        workspace_id, workspace_crn, workspace_url = self._get_workspace_for_vm(vm_id)
        if not workspace_id:
            return {"error": "VM not found."}
        
        headers = self._get_headers(workspace_crn)
        if not headers:
            return {"error": "Failed to get headers"}

        volumes_url = f"{workspace_url}/pcloud/v1/cloud-instances/{workspace_id}/pvm-instances/{vm_id}/volumes"
        volumes_response = requests.get(
            volumes_url, headers=headers, timeout=120)
        volumes_data = volumes_response.json()

        # Need to check all volume status and review all available state's
        healthy_volume_states = ['in-use', 'available',
                                 'creating', 'attaching', 'detaching']
        unhealthy_volumes = []

        for volume in volumes_data.get('volumes', []):
            volume_state = volume.get('state', '')

            if volume_state not in healthy_volume_states:
                unhealthy_volumes.append({
                    "name": volume.get('name'),
                    "state": volume_state
                })
        return {
            "storage_health": {
                "status": "OK" if len(unhealthy_volumes) == 0 else "CRITICAL"
            },
            "unhealthy_volumes": unhealthy_volumes
        }

    def fetch_vms_by_health_status(self, health_status):
        """
        Get VMs filtered by health status (OK, CRITICAL, ERROR, WARNING, UNKNOWN)
        """
        if self.crn and self.cloud_instance_id:
            headers = self._get_headers(self.crn)
            if not headers:
                return {"error": "Failed to get headers"}

            url = f"{self.base_url}/pcloud/v1/cloud-instances/{self.cloud_instance_id}/pvm-instances"
            try:
                response = requests.get(url, headers=headers, timeout=120)
                responses = response.json()
                all_vms = []
                for pvm in responses['pvmInstances']:
                    vm_detail = self._build_vm_detail(pvm)
                    all_vms.append(vm_detail)
            except:
                all_vms = []
        else:
            result = self.fetch_vms_from_all_workspaces()
            all_vms = result.get('vms', [])

        filtered_vms = []
        for vm in all_vms:
            health_dict = vm.get("health", {"status": "UNKNOWN"})
            if isinstance(health_dict, dict):
                vm_health = health_dict.get("status", "UNKNOWN")
            else:
                vm_health = "UNKNOWN"

            if vm_health.upper() == health_status.upper():
                filtered_vms.append(vm)

        return {
            "total_vms": len(filtered_vms),
            "vms": filtered_vms
        }

    def get_critical_vms(self):
        """
        Get all VMs in CRITICAL health state
        """
        return self.fetch_vms_by_health_status("CRITICAL")

    def fetch_vms_from_all_workspaces(self):
        """
        Get VMs from all workspaces
        """
        all_workspaces = self.get_all_workspaces()
        if not all_workspaces:
            return {"error": "No workspaces found"}

        vm_list = []
        self._vm_workspace = {}
        # Initialzing the counters
        health_summary = {
            "OK": 0,
            "CRITICAL": 0,
            "WARNING": 0,
            "ATTENTION": 0
        }
        
        status_summary = {
            "ACTIVE": 0,
            "ERROR": 0,
            "SHUTOFF": 0
        }

        for workspace in all_workspaces:
            workspace_id = workspace.get("id")
            workspace_name = workspace.get("name")
            workspace_region = workspace.get("region")
            workspace_url = workspace.get("url", self.base_url)

            if not workspace_id:
                continue

            """
            Example CRN format of each workspace
            DAL10_Workspace - crn:v1:staging:public:power-iaas:dal10:a/<account_id>:<cloud_instance_id>::
            DAL12_Workspace - crn:v1:staging:public:power-iaas:dal12:a/<account_id>:<cloud_instance_id>::
            DAL13_Workspace - crn:v1:staging:public:power-iaas:dal13:a/<account_id>:<cloud_instance_id>::
            """
            # Setting CRN for each workspace
            workspace_crn = f"crn:v1:staging:public:power-iaas:{workspace_region}:a/{self.account_id}:{workspace_id}::"

            vm_data, error = self._fetch_vms_from_workspace(
                workspace_id, workspace_crn, workspace_url)
            if error:
                print(f"Skipping {workspace_name} | Error {error}")
                continue

            print(f"Workspace {workspace_name} | Status 200")
            if 'pvmInstances' not in vm_data:
                print(f"Skipping {workspace_name}: No pvmInstance data")
                continue

            workspace_info = {
                "name": workspace_name,
                "region": workspace_region
            }

            for pvm in vm_data['pvmInstances']:
                vm_detail = self._build_vm_detail(pvm, workspace_info)
                vm_list.append(vm_detail)

                # Cache VM to workspace mapping
                vm_id = vm_detail.get("vmID")
                if vm_id:
                    self._vm_workspace[vm_id] = {
                        'workspace_id': workspace_id,
                        'region': workspace_region,
                        'url': workspace_url
                    }

                # Build health and status based summary
                health_status = vm_detail.get("health", {}).get("status", "UNKNOWN").upper()
                vm_status = vm_detail.get("vmStatus", "UNKNOWN").upper()

                # Updating the health & status summary count
                if health_status in health_summary:
                    health_summary[health_status] += 1
                if vm_status in status_summary:
                    status_summary[vm_status] += 1
        
        # Set timestamp for vm to workspace caching
        self._vm_workspace_time = time.time()

        return {
            "total_vms": len(vm_list),
            "total_workspaces": len(all_workspaces),
            "health_summary": health_summary,
            "status_summary": status_summary,
            "vms": vm_list
        }
    

    def get_vm_health(self, vm_id):
        """
        Get complete health details of VM including storage and network health
        """
        workspace_id, workspace_crn, workspace_url = self._get_workspace_for_vm(vm_id)
        if not workspace_id:
            return {"error": "VM not found."}
        
        headers = self._get_headers(workspace_crn)
        if not headers:
            return {"error": "Failed to get headers"}

        vm_url = f"{workspace_url}/pcloud/v1/cloud-instances/{workspace_id}/pvm-instances/{vm_id}"
        try:
            vm_response = requests.get(vm_url, headers=headers, timeout=240)
            vm_data = vm_response.json()

            network_result = self.get_network_health(vm_id, vm_data)
            storage_result = self.get_storage_health(vm_id)

            overall_status = "OK"
            if network_result["network_health"]["status"] == "CRITICAL" or storage_result["storage_health"]["status"] == "CRITICAL":
                overall_status = "CRITICAL"

            return {
                "vmName": vm_data.get("serverName"),
                "vmID": vm_id,
                "overall_health": overall_status,
                "vm_status": vm_data.get("status"),
                "network_health": network_result["network_health"]["status"],
                "storage_health": storage_result["storage_health"]["status"],
                "network_issues": network_result.get("interfaces_down", []),
                "storage_issues": storage_result.get("unhealthy_volumes", [])
            }
        except Exception as e:
            return {"error": f"Failed to get health for VM {vm_id}: {str(e)}"}
        
    def get_all_images_in_workspace(self):
        """
        Get all available images in the workspace
        """
        if not self.crn or not self.cloud_instance_id:
            return {"error": "Configure CRN in config.yaml to list images in a specific workspace."}
        
        headers = self._get_headers(self.crn)
        if not headers:
            return {"error": "Failed to get headers"}

        img_url = f"{self.base_url}/pcloud/v1/cloud-instances/{self.cloud_instance_id}/images"
        try:
            response = requests.get(img_url, headers=headers, timeout=120)
            image_data = response.json()

            image_list = []
            for image in image_data.get('images', []):
                image_obj = {
                    "imageID": image.get('imageID'),
                    "name": image.get('name'),
                    "operatingSystem": image.get("specifications", {}).get("operatingSystem"),
                    "state": image.get('state'),
                }
                image_list.append(image_obj)
            return {
                "total_images": len(image_list),
                "images": image_list
            }
        except Exception as e:
            logger.error(f'Error occurred while getting images: {e}')
            return {"error": f"Failed to get images: {str(e)}"}
        
    
    def get_image_details(self, image_id):
        """
        Get detailed information for an image
        Args:
            image_id: ID of the image
        """
        if not self.crn or not self.cloud_instance_id:
            return {"error": "Configure CRN in config.yaml to get image details."}
        
        headers = self._get_headers(self.crn)
        if not headers:
            return {"error": "Failed to get headers"}

        img_url = f"{self.base_url}/pcloud/v1/cloud-instances/{self.cloud_instance_id}/images/{image_id}"
        try:
            response = requests.get(img_url, headers=headers, timeout=120)
            image_data = response.json()
            specs = image_data.get("specifications", {})
            return {
                "imageID": image_data.get("imageID"),
                "name": image_data.get("name"),
                "description": image_data.get("description"),
                "state": image_data.get("state"),
                "size": image_data.get("size"),
                "storageType": image_data.get("storageType"),
                "storagePool": image_data.get("storagePool"),
                "operatingSystem": specs.get("operatingSystem"),
                "architecture": specs.get("architecture"),
                "imageType": specs.get("imageType"),
                "creationDate": image_data.get("creationDate"),
                "lastUpdateDate": image_data.get("lastUpdateDate"),
                "servers": image_data.get("servers", []),
                "volumes": image_data.get("volumes", [])
            }
        except Exception as e:
            logger.error(f'Error occurred while getting image details: {e}')
            return {
                "error": f"Failed to get image details: {str(e)}"
            }

    def get_networks_in_workspace(self):
        """
        Get all networks in the workspace
        """
        if not self.crn or not self.cloud_instance_id:
            return {"error": "Configure CRN in config.yaml to list networks in a specific workspace."}
        
        headers = self._get_headers(self.crn)
        if not headers:
            return {"error": "Failed to get headers"}
        network_url = f"{self.base_url}/pcloud/v1/cloud-instances/{self.cloud_instance_id}/networks"

        try:
            response = requests.get(network_url, headers=headers, timeout=120)
            networks_data = response.json()
            network_list = []
            for network in networks_data.get('networks', []):
                ip_metrics = network.get('ipAddressMetrics', {})
                network_detail = {
                    "networkID": network.get("networkID"),
                    "name": network.get("name"),
                    "type": network.get("type"),
                    "cidr": network.get("cidr"),
                    "gateway": network.get("gateway"),
                    "dnsServers": network.get("dnsServers", []),
                    "vlanID": network.get("vlanID"),
                    "ipAddressMetrics": {
                        "total": ip_metrics.get("total", 0),
                        "available": ip_metrics.get("available", 0),
                        "used": ip_metrics.get("used", 0),
                        "utilization": ip_metrics.get("utilization", 0)
                    }
                }
                network_list.append(network_detail)
            return {
                "total_networks": len(network_list),
                "networks": network_list
            }
        except Exception as e:
            logger.error(f'Error occurred while getting the networks: {e}')
            return {
                "error": f"Failed to get the networks: {str(e)}"
            }


    def get_vm_snapshots(self, vm_id):
        """
        Get all snapshots for an instance
        Args:
            vm_id: ID of the instance
        """
        workspace_id, workspace_crn, workspace_url = self._get_workspace_for_vm(vm_id)
        if not workspace_id:
            return {"error": "VM not found."}
        
        headers = self._get_headers(workspace_crn)
        if not headers:
            return {"error": "Failed to get headers"}
        snapshot_list = []
        vm_snap_url = f"{workspace_url}/pcloud/v1/cloud-instances/{workspace_id}/pvm-instances/{vm_id}/snapshots"
        try:
            response = requests.get(vm_snap_url, headers=headers, timeout=120)
            snapshots_data = response.json()
            for snapshot in snapshots_data.get('snapshots', []):
                snapshot_detail = {
                    "snapshotID": snapshot.get("snapshotID"),
                    "name": snapshot.get("name"),
                    "description": snapshot.get("description"),
                    "status": snapshot.get("status"),
                    "creationDate": snapshot.get("creationDate"),
                    "lastUpdateDate": snapshot.get("lastUpdateDate"),
                    "pvmInstanceID": snapshot.get("pvmInstanceID"),
                    "volumeSnapshots": snapshot.get("volumeSnapshots", [])
                }
                snapshot_list.append(snapshot_detail)
            return {
                "vmID": vm_id,
                "total_snapshots": len(snapshot_list),
                "snapshots": snapshot_list
            }
        except Exception as e:
            logger.error(f'Error occurred while getting snapshots: {e}')
            return {"error": f"Failed to get the instance snapshots: {str(e)}"}