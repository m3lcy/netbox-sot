import os
import yaml
import logging
import sys
import ipaddress
from modules.netbox_client import get_netbox_client
from modules.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

try:
    nb = get_netbox_client()
except Exception as e:
    logger.critical(f"Failed to connect to NetBox: {e}")
    sys.exit(1)

DATA_DIR = "data/devices/interfaces"

def get_cidr(ip, mask):
    if not ip or not mask:
        return None
    try:
        return str(ipaddress.IPv4Interface(f"{ip}/{mask}"))
    except ValueError:
        return None

def process_ip_in_netbox(address, interface_obj, role):
    nb_role = role if role else None
    
    nb_ip = nb.ipam.ip_addresses.get(address=address)

    if not nb_ip:
        logger.info(f"Creating IP {address} ({role if role else 'primary'}) on {interface_obj.name}")
        return nb.ipam.ip_addresses.create(
            address=address,
            status="active",
            role=nb_role,
            assigned_object_type="dcim.interface",
            assigned_object_id=interface_obj.id
        )
    else:
        current_role = getattr(nb_ip.role, 'value', None)
        if (nb_ip.assigned_object_id != interface_obj.id or current_role != nb_role):
            logger.info(f"Updating IP {address} assignment/role on {interface_obj.name}")
            nb_ip.update({
                "assigned_object_type": "dcim.interface",
                "assigned_object_id": interface_obj.id,
                "role": nb_role
            })
        return nb_ip

def sync_ips():
    if not os.path.exists(DATA_DIR):
        logger.error(f"Directory {DATA_DIR} not found.")
        return

    files = [f for f in os.listdir(DATA_DIR) if f.endswith("_interfaces.yaml")]
    
    for filename in files:
        device_name = filename.replace("_interfaces.yaml", "")
        logger.info(f"=== Syncing IPs for {device_name} ===")

        try:
            device = nb.dcim.devices.get(name=device_name)
            if not device:
                logger.warning(f"Device {device_name} not found in NetBox.")
                continue

            with open(os.path.join(DATA_DIR, filename), 'r') as f:
                content = yaml.safe_load(f)
                interface_list = content.get('interfaces', [])

            nb_interfaces = {i.name: i for i in nb.dcim.interfaces.filter(device_id=device.id)}

            for entry in interface_list:
                intf_name = entry.get('name')
                
                if '-' in intf_name or intf_name not in nb_interfaces:
                    continue
                
                target_interface = nb_interfaces[intf_name]

                ip_val = entry.get('ip_address')
                mask_val = entry.get('subnet_mask')
                cidr = get_cidr(ip_val, mask_val)

                if cidr:
                    role = 'loopback' if 'Loopback' in intf_name else ''
                    nb_ip_obj = process_ip_in_netbox(cidr, target_interface, role)

                    if intf_name == "Loopback0":
                        if not device.primary_ip4 or device.primary_ip4.id != nb_ip_obj.id:
                            logger.info(f"Setting {cidr} as Primary IPv4 for {device_name}")
                            device.update({"primary_ip4": nb_ip_obj.id})

                vrrp_block = entry.get('vrrp')
                if vrrp_block and vrrp_block.get('ip'):
                    vrrp_cidr = get_cidr(vrrp_block.get('ip'), mask_val)
                    if vrrp_cidr:
                        process_ip_in_netbox(vrrp_cidr, target_interface, role='vrrp')

        except Exception as e:
            logger.error(f"Unexpected error processing {device_name}: {e}")

if __name__ == "__main__":
    sync_ips()