import csv
import logging
import sys
from modules.logging_utils import setup_logging
from modules.config import CSV_DIR
from modules.netbox_client import get_netbox_client

setup_logging()
logger = logging.getLogger(__name__)

try:
    nb = get_netbox_client()
except Exception as e:
    logger.critical(f"Failed to connect to NetBox: {e}")
    sys.exit(1)

def get_or_create(endpoint, filters: dict, data: dict):
    obj = endpoint.get(**filters)
    if obj:
        logger.info(f"Already exists → {data.get('name', data.get('model', data.get('slug')))}")
        return obj
    
    created = endpoint.create(data)
    logger.info(f"Created → {data.get('name', data.get('model', data.get('slug')))}")
    return created

def regions():
    path = CSV_DIR / "regions.csv"
    if not path.exists():
        logger.warning("regions.csv not found... Skipping")
        return
    
    with open(path) as f:
        for row in csv.DictReader(f):
            data = {
                "name": row["name"],
                "slug": row["slug"]
            }
            if row.get("parent"):
                parent = nb.dcim.regions.get(name=row["parent"])
                data["parent"] = parent.id
            get_or_create(nb.dcim.regions, {"name": row["name"]}, data)

def sites():
    path = CSV_DIR / "sites.csv"
    if not path.exists():
        logger.warning("sites.csv not found... Skipping")
        return
    
    with open(path) as f:
        for row in csv.DictReader(f):
            data = {
                "name": row["name"],
                "slug": row["slug"],
                "status": row.get("status", "active")
            }
            if row.get("region"):
                region = nb.dcim.regions.get(name=row["region"])
                data["region"] = region.id if region else None
            get_or_create(nb.dcim.sites, {"name": row["name"]}, data)

def manufacturers():
    path = CSV_DIR / "manufacturers.csv"
    if not path.exists():
        logger.warning("manufacturers.csv not found... Skipping")
        return
    
    with open(path) as f:
        for row in csv.DictReader(f):
            data = {
                "name": row["name"],
                "slug": row["slug"]
            }
            get_or_create(nb.dcim.manufacturers, {"name": row["name"]}, data)

def device_roles():
    path = CSV_DIR / "device_roles.csv"
    if not path.exists():
        logger.warning("device_roles.csv not found... Skipping")
        return
    
    with open(path) as f:
        for row in csv.DictReader(f):
            data = {
                "name": row["name"],
                "color": row["color"],
                "slug": row["slug"]
            }
            get_or_create(nb.dcim.device_roles, {"name": row["name"]}, data)

def device_types():
    path = CSV_DIR / "device_types.csv"
    if not path.exists():
        logger.warning("device_types.csv not found... Skipping")
        return
    
    with open(path) as f:
        for row in csv.DictReader(f):
            manu = nb.dcim.manufacturers.get(name=row["manufacturer"])
            if not manu:
                logger.error(f"Manufacturer not found: {row["manufacturer"]} → Skipping {row["model"]}")
                continue
            data = {
                "manufacturer": manu.id,
                "model": row["model"],
                "slug": row["slug"],
                "u_height": float(row.get("u_height", 1))
            }
            get_or_create(nb.dcim.device_types, {"model": row["model"]}, data)

def module_types():
    path = CSV_DIR / "module_types.csv"
    if not path.exists():
        logger.warning("module_types.csv not found... Skipping")
        return
    
    with open(path) as f:
        for row in csv.DictReader(f):
            manu = nb.dcim.manufacturers.get(name=row["manufacturer"])
            if not manu:
                logger.error(f"Manufacturer not found: {row["manufacturer"]} → Skipping {row["model"]}")
                continue
            data = {
                "manufacturer": manu.id,
                "model": row["model"]
            }
            get_or_create(nb.dcim.module_types, {"model": row["model"]}, data)

def devices():
    path = CSV_DIR / "devices.csv"
    if not path.exists():
        logger.warning("devices.csv not found... Skipping")
        return
    
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            role = nb.dcim.device_roles.get(name=row["role"])
            site = nb.dcim.sites.get(name=row["site"])
            d_type = nb.dcim.device_types.get(model=row["device_type"])

            if not all([role, site, d_type]):
                logger.error(
                    f"Skipping {row["name"]}: Missing dependencies "
                    f"(Role: {bool(role)}, Site: {bool(site)}, Type: {bool(d_type)})"
                )
                continue
            data = {
                "name": row["name"],
                "role": role.id,
                "site": site.id,
                "device_type": d_type.id,
                "status": row.get("status", "active").lower(),
            }
            get_or_create(nb.dcim.devices, {"name": row["name"]}, data)

def vlans():
    path = CSV_DIR / "vlans.csv"
    if not path.exists():
        logger.warning("vlans.csv not found... Skipping")
        return
    
    with open(path) as f:
        for row in csv.DictReader(f):
            site = nb.dcim.sites.get(name=row["site"])
            
            if not site:
                logger.error(f"Site not found: {row['site']} → Skipping VLAN {row['vid']}")
                continue
            data = {
                "vid": int(row["vid"]),
                "name": row["name"],
                "site": site.id,
                "status": row.get("status", "active").lower()
            }
            get_or_create(nb.ipam.vlans, {"vid": data["vid"], "site_id": site.id}, data)

def prefixes():
    path = CSV_DIR / "prefixes.csv"
    if not path.exists():
        logger.warning("prefixes.csv not found... Skipping")
        return
    
    with open(path) as f:
        for row in csv.DictReader(f):
            vlan_vid = int(row["vlan"])
            vlan_obj = nb.ipam.vlans.get(vid=vlan_vid)
            
            if not vlan_obj:
                logger.warning(f"VLAN {vlan_vid} not found for prefix {row['prefix']}. Creating without link.")

            data = {
                "prefix": row["prefix"],
                "status": row.get("status", "active").lower(),
                "description": row["description"],
                "vlan": vlan_obj.id if vlan_obj else None,
            }
            
            get_or_create(nb.ipam.prefixes, {"prefix": row["prefix"]}, data)

def main():
    logging.info("Starting NetBox reference data bootstrap")   # commented out functions that have already been updated so logs dont get flooded unnecessarily 
    # regions()
    # sites()
    # manufacturers()
    # device_roles()
    # device_types()
    # module_types()
    # devices()
    # vlans()
    prefixes()
    logging.info("Reference data bootstrap completed successfully!")

if __name__ == "__main__":
    main()