# AWS Marketplace Preparation Guide

This document outlines the steps needed to prepare MikroTik CHR images for AWS Marketplace submission.

## Current Status

🚧 **In Progress** - This repository provides the foundation for marketplace-ready CHR images but requires additional steps for marketplace submission.

## Prerequisites for Marketplace Submission

### 1. Licensing Requirements
- [ ] Verify MikroTik licensing agreements for marketplace distribution
- [ ] Ensure compliance with MikroTik CHR license terms
- [ ] Obtain necessary commercial redistribution permissions

### 2. AWS Marketplace Requirements
- [ ] AWS Partner Network (APN) membership
- [ ] Seller account setup in AWS Marketplace Management Portal
- [ ] Tax and banking information configured

### 3. Image Hardening Checklist
- [ ] Security baseline compliance (CIS benchmarks)
- [ ] Vulnerability scanning and remediation
- [ ] Remove or secure development/debug tools
- [ ] Implement CloudWatch monitoring integration
- [ ] Configure automated security updates where applicable

## Image Preparation Process

### Phase 1: Base Image Hardening
1. **Security Configuration**
   ```bash
   # Disable unnecessary services
   /ip service disable www
   /ip service disable telnet
   /ip service disable ftp
   /ip service disable api
   
   # Configure secure SSH settings
   /ip service set ssh port=22 address=0.0.0.0/0
   
   # Implement firewall rules
   /ip firewall filter
   add chain=input action=accept connection-state=established,related
   add chain=input action=accept protocol=icmp
   add chain=input action=accept dst-port=22,8729 protocol=tcp
   add chain=input action=drop
   ```

2. **CloudWatch Integration**
   - Install CloudWatch agent for monitoring
   - Configure log forwarding to CloudWatch Logs
   - Set up custom metrics for CHR-specific monitoring

### Phase 2: Testing and Validation
1. **Multi-Region Testing**
   - Test deployment across all AWS regions
   - Validate instance types: t3.micro to c5.24xlarge
   - Test ARM64 (Graviton) instances: t4g, c6g, m6g series

2. **Performance Benchmarking**
   - Network throughput testing
   - Latency measurements
   - Resource utilization monitoring
   - CHR license limitation validation

3. **Security Validation**
   - Penetration testing
   - Compliance scanning (SOC2, PCI DSS if applicable)
   - Vulnerability assessment

### Phase 3: Documentation Package
1. **User Documentation**
   - Deployment guides
   - Configuration examples
   - Troubleshooting guides
   - Best practices documentation

2. **Technical Documentation**
   - Architecture diagrams
   - Network configuration templates
   - CloudFormation templates
   - Terraform modules

### Phase 4: Marketplace Submission
1. **Product Information**
   - Product description and features
   - Pricing model (BYOL, hourly, etc.)
   - Support information
   - Usage instructions

2. **AMI Submission**
   - Submit hardened AMIs for each architecture
   - Provide scanning reports
   - Include support contact information

## Implementation Roadmap

### Phase 1: Foundation (Current)
- [x] Multi-architecture build system
- [x] Automated password rotation
- [x] Basic security configuration
- [x] AWS deployment documentation

### Phase 2: Hardening (Upcoming)
- [ ] Advanced security configuration
- [ ] CloudWatch integration
- [ ] Compliance scanning
- [ ] Performance optimization

### Phase 3: Testing (Future)
- [ ] Comprehensive testing suite
- [ ] Multi-region validation
- [ ] Performance benchmarking
- [ ] Security assessment

### Phase 4: Submission (Future)
- [ ] AWS Partner onboarding
- [ ] Marketplace listing creation
- [ ] AMI submission and approval
- [ ] Launch and monitoring

## Current Limitations

### Architecture Support
- **AMD64**: Fully supported
- **ARM64**: Uses x86 CHR image (performance impact)
  - Note: MikroTik doesn't currently provide native ARM64 CHR images
  - Consider emulation overhead in pricing/performance documentation

### CHR License Limitations
- Free CHR limited to 1Mbps throughput
- Paid licenses required for higher performance
- Marketplace pricing should account for license costs

### Security Considerations
- Default password rotation (good for security)
- SSH enabled by default (required for management)
- Firewall rules need customer customization

## Getting Started with Marketplace Prep

For organizations interested in pursuing AWS Marketplace listing:

1. **Assess Requirements**
   - Review MikroTik licensing terms
   - Evaluate AWS Partner Network requirements
   - Determine target market and pricing strategy

2. **Contact Stakeholders**
   - Reach out to MikroTik for licensing clarification
   - Connect with AWS Partner team
   - Engage security compliance consultants

3. **Develop Timeline**
   - Licensing negotiations: 2-4 weeks
   - Image hardening: 4-6 weeks
   - Testing and validation: 3-4 weeks
   - Marketplace submission: 2-3 weeks
   - **Total estimated timeline: 3-4 months**

## Support and Contacts

- **Repository Issues**: [GitHub Issues](https://github.com/CalebSargeant/mikrotik-chr/issues)
- **MikroTik Licensing**: [MikroTik Sales](https://mikrotik.com/contact)
- **AWS Partner Network**: [APN Portal](https://aws.amazon.com/partners/)
- **Marketplace Support**: [AWS Marketplace Seller Guide](https://docs.aws.amazon.com/marketplace/latest/userguide/)

---

*This document is a planning guide and does not constitute legal or business advice. Consult with appropriate legal and business professionals for marketplace submission decisions.*