# First-boot configuration for CHR cloud images.
# Injected offline as /rw/autorun.scr on partition 2 (ext3 "RouterOS") of the raw image.
# RouterOS reads /rw/autorun.scr exactly once on first boot, runs each line as a
# console command, then clears it. NOTE: the file MUST be /rw/autorun.scr (.scr, under
# rw/) — a file at the partition root or named .rsc is NOT executed.
:log info "Running autorun.scr - CHR Multi-Architecture Image"

# Set admin password FIRST. RouterOS v7 forces an interactive "expired password"
# change on the first login of a blank-password user, which would otherwise block
# automated SSH/password access. Setting it here (system context, not a login) disarms it.
# Random and never shown: admin logs in with the instance's SSH key, imported below.
/user set admin password=[:rndstr length=32]

/system identity set name=chr

# Enable management services for cloud access
/ip service enable ssh
/ip service set ssh port=22
/ip service enable api-ssl
/ip service set api-ssl port=8729

# Enable DHCP client on ether1 (standard cloud/EC2/OCI setup)
# Stock CHR already has one, and an error here would stop the rest of this file.
:if ([:len [/ip dhcp-client find interface=ether1]] = 0) do={ /ip dhcp-client add interface=ether1 disabled=no }

# Add admin's SSH keys from instance metadata: OCI IMDSv2, then AWS IMDSv2. Retries every
# 10 s until a key is in, or for 10 minutes, then removes itself.
/system script add name=imds-ssh-key policy=ftp,read,write,policy,test,sensitive source={
  :local d ""
  :do {
    :set d ([/tool fetch url="http://169.254.169.254/opc/v2/instance/metadata/ssh_authorized_keys" http-header-field="Authorization:Bearer Oracle" output=user as-value]->"data")
  } on-error={
    :do {
      :local t ([/tool fetch url="http://169.254.169.254/latest/api/token" http-method=put http-header-field="X-aws-ec2-metadata-token-ttl-seconds:60" output=user as-value]->"data")
      :set d ([/tool fetch url="http://169.254.169.254/latest/meta-data/public-keys/0/openssh-key" http-header-field="X-aws-ec2-metadata-token:$t" output=user as-value]->"data")
    } on-error={}
  }
  :while ([:len $d] > 0) do={
    :local e [:find $d "\n"]
    :if ([:typeof $e] = "nil") do={ :set e [:len $d] }
    :local k [:pick $d 0 $e]
    :set d [:pick $d ($e + 1) [:len $d]]
    :if ([:pick $k ([:len $k] - 1)] = "\r") do={ :set k [:pick $k 0 ([:len $k] - 1)] }
    :if ([:len $k] > 0) do={
      :do { /user ssh-keys add user=admin key=$k } on-error={ :log warning "imds-ssh-key: skipped a key RouterOS does not accept" }
    }
  }
  :local done ([:len [/user ssh-keys find user=admin]] > 0)
  :if ($done || [/system scheduler get [find name=imds-ssh-key] run-count] >= 60) do={
    :if ($done) do={
      :log info "imds-ssh-key: admin SSH keys added from instance metadata"
    } else={
      :log warning "imds-ssh-key: no SSH key in instance metadata after 10 minutes, admin has no usable login"
    }
    # A job removing its own scheduler is interrupted, so a separate job cleans up.
    :execute script={ :delay 1s; /system scheduler remove [find name=imds-ssh-key]; /system script remove [find name=imds-ssh-key] }
  }
}
/system scheduler add name=imds-ssh-key start-time=startup interval=10s policy=ftp,read,write,policy,test,sensitive on-event="/system script run imds-ssh-key"

:log info "CHR configuration applied successfully"
