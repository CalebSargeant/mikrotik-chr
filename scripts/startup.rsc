:log info "Running autorun.rsc - CHR Multi-Architecture Image"
/system/identity set name=chr

# Enable interfaces for proper network access
/ip service enable ssh
/ip service enable api-ssl
/ip service set ssh port=22
/ip service set api-ssl port=8729

# Enable DHCP client on ether1 (common EC2/cloud setup)
/ip dhcp-client add interface=ether1 disabled=no

# Set admin password (will be replaced by build process with rotating password)
/user/set admin password="PLACEHOLDER_PASSWORD"

:log info "CHR configuration applied successfully"
