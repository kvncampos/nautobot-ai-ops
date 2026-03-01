# Network Concepts to Nautobot Mapping

## Layer 2 (Data Link)

- **VLAN** -> `VLAN` model (ID, name, site, group, tenant, status)
- **VLAN Group** -> `VLANGroup` model (groups VLANs, scoped to site/location)
- **Trunk/Access ports** -> Interface `mode` field (access, tagged, tagged-all)
- **MAC Address** -> searchable via device/interface queries
- **Cables** -> `Cable` model (connects two endpoints, tracks type/length/color)

## Layer 3 (Network)

- **IP Address** -> `IPAddress` model (address, VRF, tenant, interface assignment)
- **Subnet/Prefix** -> `Prefix` model (network, prefix length, VRF, VLAN, utilization)
- **VRF** -> `VRF` model (route distinguisher, import/export targets)
- **Routing** -> modeled via config context or custom fields
- **NAT** -> `IPAddress` has `nat_inside` / `nat_outside` relationships

## Physical Layer

- **Patch Panel** -> FrontPort + RearPort models
- **Cable** -> Cable model (type: CAT5e, CAT6, SMF, MMF, power, etc.)
- **Transceiver/SFP** -> InventoryItem model
- **Rack** -> Rack model (u_height, site, location, tenant)
- **Power** -> PowerPort, PowerOutlet, PowerFeed, PowerPanel

## Services and Protocols

- **DNS/DHCP/NTP** -> `Service` model (name, protocol, ports, device/VM)
- **BGP/OSPF** -> modeled via config context or BGP plugin
- **SNMP** -> config context data

## Common Abbreviations

- IPAM: IP Address Management
- DCIM: Data Center Infrastructure Management
- VRF: Virtual Routing and Forwarding
- RIR: Regional Internet Registry (ARIN, RIPE, etc.)
- ASN: Autonomous System Number
- LAG: Link Aggregation Group
- MLAG/vPC: Multi-chassis LAG
