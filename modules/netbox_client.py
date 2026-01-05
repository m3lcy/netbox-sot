import pynetbox
from modules.config import NETBOX_URL, NETBOX_TOKEN

def get_netbox_client():
    if not NETBOX_TOKEN:
        raise ValueError("No NetBox token available - check config")

    nb = pynetbox.api(
        url = NETBOX_URL,
        token = NETBOX_TOKEN,
        threading = True,      
    )
    nb.http_session.timeout = (5, 30)  
    return nb

def get_interface_type(name):
    name = name.lower()
    if 'gigabit' in name or 'gi' in name:
        return '1000base-t'
    elif 'fast' in name or 'fa' in name:
        return '100base-tx'
    elif 'serial' in name or 'se' in name:
        return 't3' 
    elif 'vlan' in name:
        return 'virtual'
    elif 'loopback' in name:
        return 'virtual'
    else: 
        raise ValueError(f"Unknown interface type: {name}")