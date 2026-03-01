# Nautobot Data Model

## Object Hierarchy

- **Organization**: Tenant > Tenant Group
- **Location**: Region > Site > Location > Rack > Rack Group
- **Devices**: Manufacturer > Device Type > Device > Interfaces
- **Circuits**: Provider > Circuit Type > Circuit > Circuit Termination
- **IPAM**: RIR > Aggregate > Prefix > IP Address > VLAN > VLAN Group > VRF

## Key Relationships

- **Device** belongs to a Site/Location, has a Role, Platform, and Tenant
- **Interface** belongs to a Device; can have IP Addresses, VLANs, and Cable connections
- **Cable** connects two endpoints (Interface, FrontPort, RearPort, Console/Power ports)
- **IP Address** is assigned to an Interface; belongs to a Prefix and optionally a VRF
- **Prefix** belongs to a Site, VRF, VLAN, and Tenant; contains IP Addresses
- **VLAN** belongs to a VLAN Group and Site; associated with Prefixes and Interfaces
- **Circuit** has two Circuit Terminations (A-side and Z-side), each tied to a Site or Provider Network
- **VRF** contains Prefixes and IP Addresses; supports route distinguisher

## Common Object Statuses

- **Device**: Active, Planned, Staged, Failed, Decommissioning, Offline, Inventory
- **Circuit**: Active, Planned, Provisioning, Offline, Decommissioning, Deprovisioned
- **Prefix/IP**: Active, Reserved, Deprecated, Container (prefix only)
- **Site**: Active, Planned, Staging, Decommissioning, Retired
- **Cable**: Connected, Planned, Decommissioning

## Device Components

- Interfaces (network ports)
- Console Ports / Console Server Ports
- Power Ports / Power Outlets
- Front Ports / Rear Ports (patch panels)
- Device Bays (chassis/blade)
- Inventory Items (SFPs, line cards, etc.)

## Important Fields

- **Primary IP**: Device's management IP (primary_ip4 or primary_ip6)
- **Serial**: Unique device serial number
- **Asset Tag**: Organization-specific tracking identifier
- **Tags**: Flexible labeling for any object
- **Custom Fields**: User-defined attributes on any object
- **Config Context**: JSON configuration data merged from multiple sources
