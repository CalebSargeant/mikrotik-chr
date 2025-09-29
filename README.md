<!-- Quality & Security Overview -->
[![CodeQL](https://github.com/CalebSargeant/mikrotik-chr/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/CalebSargeant/mikrotik-chr/actions/workflows/github-code-scanning/codeql)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=CalebSargeant_mikrotik-chr&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=CalebSargeant_mikrotik-chr)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=CalebSargeant_mikrotik-chr&metric=security_rating&token=ebfb6b12c8469925ada2be9a1af34b9679e55d40)](https://sonarcloud.io/summary/new_code?id=CalebSargeant_mikrotik-chr)
[![Known Vulnerabilities](https://snyk.io/test/github/calebsargeant/reusable-workflows/badge.svg)](https://snyk.io/test/github/calebsargeant/reusable-workflows)

<!-- Code Quality & Maintainability -->
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=CalebSargeant_mikrotik-chr&metric=sqale_rating&token=ebfb6b12c8469925ada2be9a1af34b9679e55d40)](https://sonarcloud.io/summary/new_code?id=CalebSargeant_mikrotik-chr)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=CalebSargeant_mikrotik-chr&metric=reliability_rating&token=ebfb6b12c8469925ada2be9a1af34b9679e55d40)](https://sonarcloud.io/summary/new_code?id=CalebSargeant_mikrotik-chr)
[![Technical Debt](https://sonarcloud.io/api/project_badges/measure?project=CalebSargeant_mikrotik-chr&metric=sqale_index&token=ebfb6b12c8469925ada2be9a1af34b9679e55d40)](https://sonarcloud.io/summary/new_code?id=CalebSargeant_mikrotik-chr)

<!-- Code Metrics -->
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=CalebSargeant_mikrotik-chr&metric=coverage&token=ebfb6b12c8469925ada2be9a1af34b9679e55d40)](https://sonarcloud.io/summary/new_code?id=CalebSargeant_mikrotik-chr)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=CalebSargeant_mikrotik-chr&metric=bugs&token=ebfb6b12c8469925ada2be9a1af34b9679e55d40)](https://sonarcloud.io/summary/new_code?id=CalebSargeant_mikrotik-chr)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=CalebSargeant_mikrotik-chr&metric=vulnerabilities&token=ebfb6b12c8469925ada2be9a1af34b9679e55d40)](https://sonarcloud.io/summary/new_code?id=CalebSargeant_mikrotik-chr)
[![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=CalebSargeant_mikrotik-chr&metric=code_smells&token=ebfb6b12c8469925ada2be9a1af34b9679e55d40)](https://sonarcloud.io/summary/new_code?id=CalebSargeant_mikrotik-chr)

<!-- Project Stats -->
[![Lines of Code](https://sonarcloud.io/api/project_badges/measure?project=CalebSargeant_mikrotik-chr&metric=ncloc&token=ebfb6b12c8469925ada2be9a1af34b9679e55d40)](https://sonarcloud.io/summary/new_code?id=CalebSargeant_mikrotik-chr)
[![Duplicated Lines (%)](https://sonarcloud.io/api/project_badges/measure?project=CalebSargeant_mikrotik-chr&metric=duplicated_lines_density&token=ebfb6b12c8469925ada2be9a1af34b9679e55d40)](https://sonarcloud.io/summary/new_code?id=CalebSargeant_mikrotik-chr)

# MikroTik CHR Multi-Architecture Images

This repository automatically builds pre-configured MikroTik Cloud Hosted Router (CHR) images for both **AMD64** and **ARM64** architectures, optimized for cloud deployments.

## Features

- ✅ **Multi-Architecture Support**: AMD64 and ARM64 builds
- 🔄 **Rotating Passwords**: Admin password rotates with each build for enhanced security
- 🌐 **Cloud-Ready Configuration**: DHCP client enabled, SSH and API-SSL accessible
- ☁️ **AWS EC2 Compatible**: Ready-to-deploy EC2 images
- 🚀 **Smart Automated Builds**: Only builds when new CHR versions are detected
- 📦 **Unified Releases**: Single release with both architectures as downloadable assets

## Quick Start

### Download Pre-built Images

Visit our [Releases](https://github.com/CalebSargeant/mikrotik-chr/releases) page to download the latest unified release containing:
- `chr-amd64.img.gz` - For Intel/AMD x86-64 systems
- `chr-arm64.img.gz` - For ARM64 systems (including AWS Graviton)

Each release includes **both architectures** as downloadable assets, with a single rotating admin password shared between both images.

### Default Configuration

Each image comes pre-configured with:
- **System Identity**: `chr`
- **SSH Access**: Enabled on port 22
- **API-SSL**: Enabled on port 8729
- **DHCP Client**: Enabled on ether1 interface
- **Admin Password**: Displayed in the release notes (rotates with each build)

## AWS EC2 Deployment

### Option 1: Direct EC2 Instance (Recommended)

1. **Launch a base EC2 instance** (Ubuntu 22.04 LTS recommended)
   ```bash
   # Instance requirements:
   # - Instance type: t3.micro or larger
   # - Storage: At least 10GB EBS volume
   # - Security groups: Allow SSH (22), API-SSL (8729)
   ```

2. **Deploy CHR image using our flash script**:
   ```bash
   # SSH into your EC2 instance
   curl -sSL https://raw.githubusercontent.com/CalebSargeant/mikrotik-chr/main/scripts/flash.sh | sudo bash
   ```

3. **Access your CHR router**:
   - SSH: `ssh admin@<your-ec2-ip>`
   - WebFig: `https://<your-ec2-ip>:8729` (accept self-signed certificate)
   - Password: Check the latest release notes for the current admin password

### Option 2: Custom AMI Creation

1. **Create a custom AMI** from a flashed instance:
   ```bash
   # After flashing CHR to an instance, create AMI
   aws ec2 create-image --instance-id i-1234567890abcdef0 --name "MikroTik-CHR-$(date +%Y%m%d)"
   ```

2. **Launch instances from your custom AMI** for consistent deployments

### Security Group Configuration

Ensure your EC2 security group allows:
```
Inbound Rules:
- SSH (22/tcp) from your IP
- HTTPS (8729/tcp) from your IP  # For WebFig/API access
- Custom rules for your specific routing needs
```

## Manual Deployment

### Linux/Generic Cloud Deployment

1. **Download the appropriate image**:
   ```bash
   # For AMD64 systems
   wget https://github.com/CalebSargeant/mikrotik-chr/releases/latest/download/chr-amd64.img.gz
   
   # For ARM64 systems  
   wget https://github.com/CalebSargeant/mikrotik-chr/releases/latest/download/chr-arm64.img.gz
   ```

2. **Flash to disk** (⚠️ This will erase the target disk):
   ```bash
   # Decompress and write to disk (adjust /dev/sdX as needed)
   gunzip -c chr-amd64.img.gz | sudo dd of=/dev/sda bs=1M status=progress
   
   # Reboot to CHR
   sudo reboot
   ```

## Accessing Your CHR Router

### Default Credentials
- **Username**: `admin`  
- **Password**: Check the release notes for the current password

### Access Methods
1. **SSH**: `ssh admin@<router-ip>`
2. **WebFig (HTTPS)**: `https://<router-ip>:8729`
3. **API**: Port 8729 with SSL

### First Login Steps
1. Change the admin password immediately
2. Configure additional users if needed
3. Set up your routing configuration
4. Configure firewall rules as appropriate

## AWS Marketplace Preparation

> **Note**: This section documents the process for preparing images for AWS Marketplace submission.

### Prerequisites for Marketplace
- [ ] Hardened security configuration
- [ ] Compliance with AWS Marketplace requirements
- [ ] Proper licensing arrangements with MikroTik
- [ ] Testing across multiple EC2 instance types

### Marketplace Submission Process
1. **Image Preparation**: Use our automated builds as base images
2. **Security Hardening**: Additional security configurations for marketplace
3. **Testing**: Comprehensive testing across AWS regions and instance types
4. **Documentation**: Complete user guides and deployment documentation
5. **Submission**: Follow AWS Marketplace partner onboarding process

*For detailed marketplace preparation, contact the repository maintainers.*

## Development

### Building Locally

```bash
# Clone repository
git clone https://github.com/CalebSargeant/mikrotik-chr.git
cd mikrotik-chr

# Generate password and modify startup script
./scripts/generate-password.sh

# Manual build process (requires root privileges)
sudo ./scripts/inject.sh
```

### Workflow Triggers & Smart Building
- **Daily**: Automatic version check at 03:00 UTC - only builds when new MikroTik versions are detected
- **Manual**: Workflow dispatch from GitHub Actions
- **Push**: Changes to `scripts/` or workflow files force rebuild

### Version Checking
```bash
# Check for new versions manually
./scripts/check-version.sh
```

The workflow intelligently:
- ✅ Only runs builds when a new MikroTik CHR version is available
- ✅ Creates unified releases with both AMD64 and ARM64 images as assets
- ✅ Caches downloads and uses marketplace actions for reliability
- ✅ Skips builds if no version changes detected

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/CalebSargeant/mikrotik-chr/issues)
- **MikroTik Documentation**: [MikroTik CHR](https://mikrotik.com/product/chr)
- **AWS EC2 Documentation**: [Amazon EC2 User Guide](https://docs.aws.amazon.com/ec2/)
