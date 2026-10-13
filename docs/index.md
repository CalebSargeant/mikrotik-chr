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

## Deployment Options

- **[AWS EC2 Deployment](aws-deployment.md)** - Deploy CHR on AWS EC2 instances
- **[OCI VRRP Failover](oci-vrrp-failover.md)** - High availability setup on Oracle Cloud Infrastructure
- **[AWS Marketplace Preparation](marketplace-preparation.md)** - Information about preparing images for AWS Marketplace

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
- **Manual**: Workflow dispatch from GitHub Actions - trigger when you know a new MikroTik version is available
- **Push**: Changes to `scripts/` or workflow files force rebuild automatically

## Support

- **Issues**: [GitHub Issues](https://github.com/CalebSargeant/mikrotik-chr/issues)
- **MikroTik Documentation**: [MikroTik CHR](https://mikrotik.com/product/chr)
- **AWS EC2 Documentation**: [Amazon EC2 User Guide](https://docs.aws.amazon.com/ec2/)

## License

MIT License - see [LICENSE](https://github.com/CalebSargeant/mikrotik-chr/blob/main/LICENSE) file for details.
