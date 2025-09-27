# AWS EC2 Deployment Guide

This guide provides detailed instructions for deploying MikroTik CHR images on Amazon Web Services EC2.

## Prerequisites

- AWS CLI configured with appropriate permissions
- Basic understanding of EC2, VPC, and Security Groups
- SSH key pair for EC2 access

## Deployment Methods

### Method 1: Flash Existing EC2 Instance (Easiest)

This method transforms an existing Ubuntu EC2 instance into a CHR router.

#### Step 1: Launch Base Instance

```bash
# Launch Ubuntu 22.04 LTS instance
aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --instance-type t3.micro \
    --key-name your-key-pair \
    --security-group-ids sg-xxxxxxxxx \
    --subnet-id subnet-xxxxxxxxx \
    --block-device-mappings '[{
        "DeviceName": "/dev/sda1",
        "Ebs": {
            "VolumeSize": 10,
            "VolumeType": "gp3",
            "DeleteOnTermination": true
        }
    }]' \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=CHR-Router}]'
```

#### Step 2: Connect and Flash CHR

```bash
# SSH into the instance
ssh -i your-key.pem ubuntu@<instance-public-ip>

# Download and run the flash script
curl -sSL https://raw.githubusercontent.com/CalebSargeant/mikrotik-chr/main/scripts/flash.sh | sudo bash

# The instance will reboot automatically
# Wait 2-3 minutes for the reboot to complete
```

#### Step 3: Access CHR Router

```bash
# SSH to the CHR router (password from latest release notes)
ssh admin@<instance-public-ip>

# Or access WebFig
# Navigate to: https://<instance-public-ip>:8729
```

### Method 2: Custom AMI Creation

Create reusable AMIs for consistent deployments.

#### Step 1: Create Base CHR Instance

Follow Method 1 to create and flash a CHR instance.

#### Step 2: Create AMI

```bash
# Stop the instance (optional but recommended)
aws ec2 stop-instances --instance-ids i-xxxxxxxxx

# Create AMI
aws ec2 create-image \
    --instance-id i-xxxxxxxxx \
    --name "MikroTik-CHR-$(date +%Y%m%d)" \
    --description "Pre-configured MikroTik CHR router" \
    --no-reboot
```

#### Step 3: Launch from Custom AMI

```bash
# Launch instances from your custom AMI
aws ec2 run-instances \
    --image-id ami-xxxxxxxxx \
    --instance-type t3.micro \
    --key-name your-key-pair \
    --security-group-ids sg-xxxxxxxxx \
    --subnet-id subnet-xxxxxxxxx
```

## Security Configuration

### Security Group Setup

Create a security group with minimal required access:

```bash
# Create security group
aws ec2 create-security-group \
    --group-name chr-router-sg \
    --description "MikroTik CHR Router Security Group" \
    --vpc-id vpc-xxxxxxxxx

# Allow SSH from your IP
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxxx \
    --protocol tcp \
    --port 22 \
    --cidr YOUR.IP.ADDRESS/32

# Allow API-SSL from your IP  
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxxx \
    --protocol tcp \
    --port 8729 \
    --cidr YOUR.IP.ADDRESS/32

# Allow ICMP for troubleshooting
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxxx \
    --protocol icmp \
    --port -1 \
    --cidr YOUR.IP.ADDRESS/32
```

## Network Configuration Examples

### Basic Router Setup

```bash
# Configure WAN interface (ether1 typically gets DHCP from EC2)
/ip dhcp-client print
# Should show ether1 with DHCP client enabled

# Configure LAN interface (if you have multiple interfaces)
/ip address add address=192.168.1.1/24 interface=ether2

# Enable DHCP server for LAN
/ip pool add name=lan-pool ranges=192.168.1.100-192.168.1.200
/ip dhcp-server add name=lan-dhcp interface=ether2 address-pool=lan-pool
/ip dhcp-server network add address=192.168.1.0/24 gateway=192.168.1.1 dns-server=8.8.8.8,8.8.4.4

# Configure masquerade NAT
/ip firewall nat add chain=srcnat out-interface=ether1 action=masquerade
```

## Instance Types and Performance

### Recommended Instance Types

| Use Case | Instance Type | vCPU | Memory | Network |
|----------|---------------|------|---------|---------|
| Basic Router | t3.micro | 2 | 1 GB | Up to 5 Gbps |
| Small Office | t3.small | 2 | 2 GB | Up to 5 Gbps |
| Medium Office | t3.medium | 2 | 4 GB | Up to 5 Gbps |
| High Performance | c6i.large | 2 | 4 GB | Up to 25 Gbps |
| ARM64 (Graviton) | t4g.micro | 2 | 1 GB | Up to 5 Gbps |

## Troubleshooting

### Common Issues

1. **Cannot SSH after flashing**
   - Wait 3-5 minutes for CHR to fully boot
   - Check security group allows SSH (port 22)
   - Verify instance is running and accessible

2. **CHR not getting DHCP**
   ```bash
   # Check DHCP client status
   /ip dhcp-client print
   
   # Renew DHCP lease
   /ip dhcp-client renew [find interface=ether1]
   ```

3. **WebFig not accessible**
   - Ensure security group allows port 8729
   - Check if API-SSL is enabled: `/ip service print`
   - Try HTTPS (not HTTP): `https://ip:8729`

### Diagnostic Commands

```bash
# System information
/system resource print
/system license print

# Network interfaces
/interface print
/ip address print
/ip route print

# Services status
/ip service print
```

## Support and Resources

- **AWS Documentation**: [EC2 User Guide](https://docs.aws.amazon.com/ec2/)
- **MikroTik Documentation**: [CHR Manual](https://help.mikrotik.com/docs/display/ROS/CHR)
- **Repository Issues**: [GitHub Issues](https://github.com/CalebSargeant/mikrotik-chr/issues)