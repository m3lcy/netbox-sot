import os
import re
import yaml
import logging
import sys
from modules.netbox_client import get_netbox_client, get_interface_type
from modules.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

try:
    nb = get_netbox_client()
except Exception as e:
    logger.critical(f"Failed to connect to NetBox: {e}")
    sys.exit(1)

DATA_DIR = "data/devices/interfaces"

def expand_interface_range(name_range):
    if '-' not in name_range:
        return [name_range]
    
    match = re.match(r"(.*\/)([0-9]+)-([0-9]+)", name_range)
    
    if not match:
        match = re.match(r"([a-zA-Z]+)([0-9]+)-([0-9]+)", name_range)
        if not match:
            return [name_range]
    
    prefix, start, end = match.groups()
    return [f"{prefix}{i}" for i in range(int(start), int(end) + 1)]

def get_vlan_id(vid, site_id):
    if not vid:
        return None
    vlan = nb.ipam.vlans.get(vid=int(vid), site_id=site_id) 
    return vlan.id if vlan else None

def sync_interfaces():
    if not os.path.exists(DATA_DIR):
        logger.error(f"Directory {DATA_DIR} not found.")
        return

    files = [f for f in os.listdir(DATA_DIR) if f.endswith("_interfaces.yaml")]
    
    for filename in files:
        device_name = filename.replace("_interfaces.yaml", "")
        logger.info(f"=== Syncing Interfaces for {device_name} ===")

        try:
            device = nb.dcim.devices.get(name=device_name)
            if not device:
                logger.warning(f"Device {device_name} not found in NetBox.")
                continue

            with open(os.path.join(DATA_DIR, filename), 'r') as f:
                content = yaml.safe_load(f)
                interface_list = content.get('interfaces', [])

            existing_intfs = {i.name: i for i in nb.dcim.interfaces.filter(device_id=device.id)}

            for entry in interface_list:
                raw_name = entry.get('name')
                description = entry.get('description', "")
                enabled = not entry.get('shutdown', False)
                
                yaml_mode = entry.get('mode', '').lower()
                nb_mode = None
                untagged_vlan_id = None

                if yaml_mode == 'trunk':
                    nb_mode = 'tagged'
                    untagged_vlan_id = get_vlan_id(entry.get('native_vlan'), device.site.id)
                elif yaml_mode == 'access':
                    nb_mode = 'access'
                    untagged_vlan_id = get_vlan_id(entry.get('access_vlan'), device.site.id)

                names = expand_interface_range(raw_name)
                
                for name in names:
                    if_type = get_interface_type(name)
                    
                    if name in existing_intfs:
                        target = existing_intfs[name]
                        current_mode = getattr(target.mode, "value", None)
                        current_vlan = getattr(target.untagged_vlan, "id", None)

                        if (target.type.value != if_type or 
                            target.description != description or
                            target.enabled != enabled or
                            current_mode != nb_mode or 
                            current_vlan != untagged_vlan_id):
                            
                            logger.info(f"Updating {name} on {device_name}")
                            target.update({
                                "type": if_type,
                                "description": description,
                                "enabled": enabled,
                                "mode": nb_mode,
                                "untagged_vlan": untagged_vlan_id
                            })
                    else:
                        logger.info(f"Creating {name} ({if_type}) on {device_name}")
                        nb.dcim.interfaces.create(
                            device=device.id,
                            name=name,
                            type=if_type,
                            description=description,
                            enabled=enabled,
                            mode=nb_mode,
                            untagged_vlan=untagged_vlan_id
                        )

        except Exception as e:
            logger.error(f"Error processing {device_name}: {e}")

if __name__ == "__main__":
    sync_interfaces()