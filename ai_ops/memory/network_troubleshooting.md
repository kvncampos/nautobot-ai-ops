# Network Troubleshooting Patterns

## Device Unreachable

1. Check device status in Nautobot (Active vs Offline/Failed)
2. Verify primary IP assignment exists
3. Check interface status (enabled, link up)
4. Trace cable path to upstream device
5. Verify site/location for physical access info
6. Check config context for management details

## Circuit Down

1. Check circuit status (Active, Offline, Provisioning)
2. Review both terminations (A-side and Z-side)
3. Verify provider and provider account info
4. Check commit rate and bandwidth details
5. Look for related circuits at same site
6. Check cable connections at termination points

## IP Conflict or Missing

1. Search IP address across all VRFs
2. Check prefix utilization (available vs assigned)
3. Verify interface assignment
4. Check for duplicate assignments in same prefix
5. Verify VRF and VLAN association
6. Review prefix status (Active, Reserved, Deprecated)

## Missing or Unknown Device

- Search by name (exact and partial with `q` param)
- Search by serial number
- Search by primary IP address
- Search by site/location
- Search by device role or type
- Check inventory items for component serial numbers

## Capacity Planning Queries

- **Rack space**: Check rack units available (u_height vs occupied)
- **Port availability**: Count interfaces by type and status
- **IP space**: Check prefix utilization percentage
- **Power**: Review power port allocations per rack
- **Circuit capacity**: Review commit rates and bandwidth

## Common Resolution Steps

- Always verify data in Nautobot before making changes
- Cross-reference with multiple object types (device + interface + cable)
- Check object changelog for recent modifications
- Use tags and custom fields for additional context
