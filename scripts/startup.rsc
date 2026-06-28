# First-boot configuration for CHR cloud images.
# Injected offline as /rw/autorun.scr on partition 2 (ext3 "RouterOS") of the raw image.
# RouterOS reads /rw/autorun.scr exactly once on first boot, runs each line as a
# console command, then clears it. NOTE: the file MUST be /rw/autorun.scr (.scr, under
# rw/) — a file at the partition root or named .rsc is NOT executed.
:log info "Running autorun.scr - CHR Multi-Architecture Image"

# Set admin password FIRST. RouterOS v7 forces an interactive "expired password"
# change on the first login of a blank-password user, which would otherwise block
# automated SSH/password access. Setting it here (system context, not a login) disarms it.
/user set admin password="PLACEHOLDER_PASSWORD"

/system identity set name=chr

# Enable management services for cloud access
/ip service enable ssh
/ip service set ssh port=22
/ip service enable api-ssl
/ip service set api-ssl port=8729

# Enable DHCP client on ether1 (standard cloud/EC2/OCI setup)
/ip dhcp-client add interface=ether1 disabled=no

:log info "CHR configuration applied successfully"
