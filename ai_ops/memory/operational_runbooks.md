# Operational Runbooks

## New Site Deployment

1. Create Site with region, tenant, and physical address
2. Create Locations within site (floors, rooms, cages)
3. Create Racks with proper u_height and numbering
4. Allocate Prefixes for site (management, user, infrastructure)
5. Create VLANs and VLAN Groups for site
6. Create Circuits with provider and terminations
7. Add Devices to racks with proper roles and types
8. Assign interfaces, IPs, and cable connections
9. Set primary IP on each device for management

## Device Commissioning

1. Verify device type exists (create if needed with manufacturer)
2. Create device with site, rack, position, role, and status=Planned
3. Add/verify interfaces match device type template
4. Assign management IP from appropriate prefix
5. Set primary IP (primary_ip4 or primary_ip6)
6. Create cable connections to upstream devices
7. Add config context for device-specific settings
8. Update status to Staged, then Active after validation

## Circuit Provisioning

1. Verify provider exists (create if needed)
2. Create circuit with type, provider, commit rate
3. Create A-side termination (your site)
4. Create Z-side termination (remote site or provider network)
5. Assign interface and cable at each termination
6. Update status: Planned -> Provisioning -> Active

## IP Address Allocation

1. Identify appropriate prefix (check VRF, site, role)
2. Check prefix utilization for available space
3. Find next available IP or use specific address
4. Create IP address with status, tenant, DNS name
5. Assign to device interface
6. Set as primary IP if it's the management address

## Change Verification

- **Before**: Document current state (status, IPs, connections)
- **After**: Verify all changed objects reflect new state
- **Check**: Related objects updated (cables, IPs, interfaces)
- **Review**: Changelog entries for audit trail
- **Validate**: No orphaned or conflicting objects remain
